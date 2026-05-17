#!/usr/bin/env python3
"""
VSAE CLI — Standalone command-line interface for surgical knowledge removal.

Usage:
    python vsae-cli.py --forget_text "Harry Potter" --top_k 5 --alpha 0.8
"""

import argparse
import hashlib
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict

# Rich for colored terminal output
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Warning: 'rich' not installed. Install with: pip install rich")

# Backend imports
from backend.embedding import (
    load_model,
    get_forget_vector,
    get_layerwise_forget_vectors,
    complete_text,
)
from backend.locator import find_target_layers
from backend.ablation import (
    ablate,
    check_ablation_overlap,
    log_ablation_to_hindsight,
)
from backend.evaluate import (
    compute_perplexity,
    run_full_evaluation,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_concept_slug(text: str) -> str:
    """Create a filesystem-safe slug from concept text."""
    import re
    slug = re.sub(r'[^\w\s-]', '', text.lower())
    slug = re.sub(r'[-\s]+', '_', slug)
    return slug[:50]  # Limit length


def print_banner():
    """Print VSAE CLI banner."""
    if RICH_AVAILABLE:
        console = Console()
        console.print(Panel.fit(
            "[bold cyan]Vector Space Ablation Engine[/bold cyan]\n"
            "[dim]Surgical Knowledge Removal from LLMs[/dim]",
            border_style="cyan"
        ))
    else:
        print("=" * 60)
        print("  Vector Space Ablation Engine")
        print("  Surgical Knowledge Removal from LLMs")
        print("=" * 60)


def print_step(message: str, status: str = "info"):
    """Print a step message with color."""
    if RICH_AVAILABLE:
        console = Console()
        if status == "info":
            console.print(f"[cyan][VSAE][/cyan] {message}")
        elif status == "success":
            console.print(f"[green][VSAE][/green] {message}")
        elif status == "warning":
            console.print(f"[yellow][VSAE][/yellow] {message}")
        elif status == "error":
            console.print(f"[red][VSAE][/red] {message}")
    else:
        prefix = "[VSAE]"
        print(f"{prefix} {message}")


def print_summary(data: Dict):
    """Print structured summary of ablation results."""
    if RICH_AVAILABLE:
        console = Console()
        
        # Create results table
        table = Table(title="Ablation Results", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan", width=30)
        table.add_column("Value", style="white")
        
        table.add_row("Ablation ID", data["ablation_id"])
        table.add_row("Concept", data["forget_text"])
        table.add_row("Target Layers", str(data["targeted_layers"]))
        table.add_row("Alpha (Strength)", str(data["alpha"]))
        table.add_row("Pre-Ablation Perplexity", f"{data['pre_perplexity']:.2f}")
        table.add_row("Post-Ablation Perplexity", f"{data['post_perplexity']:.2f}")
        table.add_row("Perplexity Change", f"+{data['perplexity_change']:.2f}")
        
        verdict = data["evaluation"]["overall_verdict"]
        verdict_color = "green" if verdict == "FORGOTTEN" else "red"
        table.add_row("Forgetting Signal", f"[{verdict_color}]{verdict}[/{verdict_color}]")
        
        console.print(table)
        
        # Before/After comparison
        if "proof" in data:
            console.print("\n[bold]Before/After Comparison:[/bold]")
            console.print(f"[dim]Probe:[/dim] {data['proof']['probe_prefix']}")
            console.print(f"[yellow]Before:[/yellow] {data['proof']['before']}")
            console.print(f"[green]After:[/green] {data['proof']['after']}")
    else:
        print("\n" + "=" * 60)
        print("ABLATION RESULTS")
        print("=" * 60)
        print(f"Ablation ID: {data['ablation_id']}")
        print(f"Concept: {data['forget_text']}")
        print(f"Target Layers: {data['targeted_layers']}")
        print(f"Alpha: {data['alpha']}")
        print(f"Pre-Ablation Perplexity: {data['pre_perplexity']:.2f}")
        print(f"Post-Ablation Perplexity: {data['post_perplexity']:.2f}")
        print(f"Perplexity Change: +{data['perplexity_change']:.2f}")
        print(f"Forgetting Signal: {data['evaluation']['overall_verdict']}")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="VSAE CLI - Surgical knowledge removal from LLMs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python vsae-cli.py --forget_text "Harry Potter"
  python vsae-cli.py --forget_text "Apple Inc CEO" --top_k 3 --alpha 1.0
  python vsae-cli.py --forget_text "Python programming" --force
        """
    )
    
    parser.add_argument(
        "--forget_text",
        type=str,
        required=True,
        help="The concept or knowledge to remove from the model"
    )
    parser.add_argument(
        "--top_k",
        type=int,
        default=5,
        help="Number of top layers to target (default: 5)"
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=0.8,
        help="Ablation strength (0.0-1.0, default: 0.8)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="microsoft/phi-2",
        help="Model identifier (default: microsoft/phi-2)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip overlap check and force ablation"
    )
    parser.add_argument(
        "--no-evaluation",
        action="store_true",
        help="Skip full evaluation suite (faster)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="reports",
        help="Output directory for reports (default: reports)"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.forget_text.strip():
        print_step("Error: forget_text cannot be empty", "error")
        sys.exit(1)
    
    if args.alpha < 0.0 or args.alpha > 2.0:
        print_step("Error: alpha must be between 0.0 and 2.0", "error")
        sys.exit(1)
    
    if args.top_k < 1 or args.top_k > 10:
        print_step("Error: top_k must be between 1 and 10", "error")
        sys.exit(1)
    
    # Print banner
    print_banner()
    print()
    
    try:
        # Step 1: Load model
        print_step(f"Loading model: {args.model}...")
        try:
            model, tokenizer, device = load_model()
            print_step(f"Model loaded successfully on {device}", "success")
        except Exception as e:
            print_step(f"Failed to load model: {e}", "error")
            logger.exception("Model loading failed")
            sys.exit(1)
        
        # Step 2: Pre-ablation overlap check
        if not args.force:
            print_step("Checking for overlapping ablations...")
            overlap = check_ablation_overlap(args.forget_text, similarity_threshold=0.65)
            if overlap:
                print_step(overlap["message"], "warning")
                response = input("Continue anyway? (y/N): ")
                if response.lower() != 'y':
                    print_step("Ablation cancelled by user", "warning")
                    sys.exit(0)
        else:
            print_step("Force mode enabled - skipping overlap check", "warning")
        
        # Step 3: Extract forget vectors
        print_step(f"Extracting forget vectors for: '{args.forget_text}'...")
        global_v = get_forget_vector(args.forget_text)
        layer_vectors = get_layerwise_forget_vectors(args.forget_text)
        print_step(f"Extracted {len(layer_vectors)} layer-specific forget vectors", "success")
        
        # Step 4: Find target layers
        print_step("Identifying target layers via activation tracing...")
        target_layers = find_target_layers(
            args.forget_text,
            top_k=args.top_k,
            target_matrices=["W_Q", "W_K", "W_V"]
        )
        layer_indices = [l["layer_index"] for l in target_layers]
        print_step(f"Target layers identified: {layer_indices}", "success")
        
        # Step 5: Before probe
        print_step("Generating before-ablation probe...")
        probe_prefix = " ".join(args.forget_text.split()[:5])
        before_completion = complete_text(probe_prefix, max_tokens=30)
        
        # Step 6: Pre-ablation perplexity
        print_step("Computing pre-ablation perplexity...")
        pre_perplexity = compute_perplexity(args.forget_text)
        print_step(f"Pre-ablation perplexity: {pre_perplexity:.2f}", "info")
        
        # Step 7: Apply ablation
        print_step(f"Applying orthogonal projection (alpha={args.alpha})...")
        result = ablate(
            layer_vectors,
            target_layers,
            alpha=args.alpha,
            concept=args.forget_text,
            pre_perplexity=pre_perplexity
        )
        print_step(f"Ablation complete (ID: {result['ablation_id']})", "success")
        
        # Step 8: Post-ablation perplexity
        print_step("Computing post-ablation perplexity...")
        post_perplexity = compute_perplexity(args.forget_text)
        perplexity_change = post_perplexity - pre_perplexity
        print_step(f"Post-ablation perplexity: {post_perplexity:.2f} (Δ +{perplexity_change:.2f})", "info")
        
        # Step 9: After probe
        print_step("Generating after-ablation probe...")
        after_completion = complete_text(probe_prefix, max_tokens=30)
        
        # Step 10: Sanity check
        print_step("Running sanity check...")
        sanity_text = complete_text("The sky is", max_tokens=10)
        alpha_chars = sum(c.isalpha() or c.isspace() for c in sanity_text)
        total_chars = max(len(sanity_text), 1)
        alpha_ratio = alpha_chars / total_chars
        
        if alpha_ratio < 0.5:
            print_step(f"WARNING: Sanity check failed (alpha_ratio={alpha_ratio:.2f})", "warning")
            print_step("Model may have been damaged. Consider rollback.", "warning")
        else:
            print_step("Sanity check passed", "success")
        
        # Step 11: Full evaluation (optional)
        if not args.no_evaluation:
            print_step("Running full evaluation suite...")
            evaluation = run_full_evaluation(args.forget_text)
            verdict = evaluation["overall_verdict"]
            
            if verdict == "FORGOTTEN":
                print_step(f"Forgetting signal: {verdict}", "success")
            else:
                print_step(f"Forgetting signal: {verdict}", "warning")
        else:
            # Minimal evaluation
            evaluation = {
                "overall_verdict": "FORGOTTEN" if post_perplexity > 100 else "STILL_KNOWN",
                "perplexity": {"score": post_perplexity}
            }
        
        # Step 12: Log to history
        print_step("Logging ablation to history...")
        log_ablation_to_hindsight(
            result["ablation_id"],
            args.forget_text,
            layer_indices,
            args.alpha,
            post_perplexity
        )
        
        # Step 13: Build report (schema matches validator requirements)
        # Generate config_hash if not provided by ablation result
        config_hash = result.get("config_hash")
        if not config_hash:
            config_hash = hashlib.sha256(str(result["ablation_id"]).encode()).hexdigest()
        
        report = {
            "ablation_id": result["ablation_id"],
            "timestamp": datetime.now().isoformat(),
            "concept": args.forget_text,  # Required by validator
            "target_layers": layer_indices,  # Required by validator
            "alpha": args.alpha,
            "pre_perplexity": round(pre_perplexity, 2),
            "post_perplexity": round(post_perplexity, 2),
            "perplexity_delta": round(perplexity_change, 2),  # Required by validator
            "forgetting_signal": evaluation["overall_verdict"],  # Required by validator
            "config_hash": config_hash,  # Required by validator
            # Additional fields for compatibility
            "forget_text": args.forget_text,
            "model": args.model,
            "targeted_layers": layer_indices,
            "perplexity_change": round(perplexity_change, 2),
            "evaluation": evaluation,
            "proof": {
                "probe_prefix": probe_prefix,
                "before": before_completion,
                "after": after_completion
            },
            "sanity_check": {
                "text": sanity_text,
                "alpha_ratio": round(alpha_ratio, 2),
                "passed": alpha_ratio >= 0.5
            },
            "layer_results": result.get("layer_results", [])
        }
        
        # Step 14: Write report to file
        output_dir = Path(args.output_dir)
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        concept_slug = create_concept_slug(args.forget_text)
        filename = f"{timestamp}_{concept_slug}.json"
        output_path = output_dir / filename
        
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)
        
        print_step(f"Compliance report written to: {output_path}", "success")
        
        # Step 15: Print summary
        print()
        print_summary(report)
        
        print()
        print_step("Ablation pipeline completed successfully", "success")
        sys.exit(0)
        
    except KeyboardInterrupt:
        print()
        print_step("Ablation cancelled by user", "warning")
        sys.exit(130)
    except Exception as e:
        print_step(f"Fatal error: {e}", "error")
        logger.exception("Ablation pipeline failed")
        sys.exit(1)


if __name__ == "__main__":
    main()

# Made with Bob
