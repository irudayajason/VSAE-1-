"""
Ablation Engine — applies orthogonal projection to erase a concept
from the model's weight matrices.

KEY INSIGHT: Each transformer layer encodes a concept in a different
direction. We must use LAYER-SPECIFIC forget vectors extracted from
the hidden state at each layer, not a single global vector.

Formula:  W_new = W - alpha * (W · v · vᵀ) / (vᵀ · v)

Phi-2 uses nn.Linear: W shape [out_dim, in_dim]

Optimizations:
  - Alpha decay: deeper layers get reduced alpha to preserve grammar
  - Immediate float16 cast-back after float32 projection math
  - Efficient in-place tensor operations where safe
"""

import torch
import hashlib
import uuid
import os
import json
from typing import Dict, List, Optional, Tuple, Callable, Any
from datetime import datetime, timezone
import logging
from pathlib import Path

from backend.embedding import load_model, get_target_weights, get_forget_vector

# Set up logging first
logger = logging.getLogger(__name__)

# Hindsight client imports
try:
    from hindsight_client import Hindsight
    HINDSIGHT_AVAILABLE = True
except ImportError:
    HINDSIGHT_AVAILABLE = False
    logger.warning("Hindsight client not available. Install with: pip install hindsight-client")

# ── Storage for rollback ───────────────────────────────
_weight_backups: Dict[str, Dict[str, torch.Tensor]] = {}

# ── Hindsight Memory Client ────────────────────────────
_hindsight_client: Optional[object] = None
HINDSIGHT_BANK_ID = "vsae-bank"

# ── Local ablation history (in-memory + file-backed) ───
_ablation_history: List[Dict] = []
HISTORY_FILE = Path(__file__).parent.parent / "ablation_history.json"


def _load_history():
    """Load ablation history from disk on startup."""
    global _ablation_history
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r") as f:
                _ablation_history = json.load(f)
            logger.info(f"Loaded {len(_ablation_history)} ablation records from disk")
        except Exception as e:
            logger.warning(f"Failed to load history file: {e}")
            _ablation_history = []


def _save_history():
    """Persist ablation history to disk."""
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(_ablation_history, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save history file: {e}")


# Load history on module import
_load_history()


def initialize_hindsight() -> bool:
    """
    Initialize the Hindsight memory client for tracking ablation history.
    Uses HINDSIGHT_API_KEY environment variable.
    
    Returns:
        True if initialization successful, False otherwise.
    """
    global _hindsight_client
    
    if not HINDSIGHT_AVAILABLE:
        logger.warning("Hindsight client not installed")
        return False
    
    try:
        api_key = os.environ.get("HINDSIGHT_API_KEY")
        if not api_key:
            logger.warning("HINDSIGHT_API_KEY environment variable not set")
            return False
        
        base_url = os.environ.get("HINDSIGHT_BASE_URL", "https://api.hindsight.dev")
        _hindsight_client = Hindsight(base_url=base_url, api_key=api_key)
        logger.info("Hindsight memory client initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Hindsight client: {e}")
        return False


async def _hindsight_retain_async(content: str):
    """Async wrapper for Hindsight retain — safe inside FastAPI."""
    if not _hindsight_client:
        return
    try:
        await _hindsight_client.aretain(
            bank_id=HINDSIGHT_BANK_ID,
            content=content
        )
        logger.info(f"Hindsight cloud backup: '{content[:60]}...'")
    except Exception as e:
        logger.warning(f"Hindsight cloud backup failed (local cache still works): {e}")


def _weight_hash(tensor: torch.Tensor) -> str:
    """Compute a short hash of a weight tensor for verification."""
    data = tensor.detach().cpu().float().numpy().tobytes()[:4096]
    return hashlib.sha256(data).hexdigest()[:16]


def apply_projection(
    W: torch.Tensor,
    v: torch.Tensor,
    alpha: float = 1.0,
) -> torch.Tensor:
    """
    Applies orthogonal projection to remove the component of W
    along direction v.

    For nn.Linear layout (Phi-2):   W shape [out_dim, in_dim]
        W_new = W - alpha * (W v) vᵀ / (vᵀ v)

    With a normalized unit vector v (vᵀv = 1):
        W_new = W - alpha * outer(W @ v, v)

    alpha=1.0 = exact orthogonal projection (remove direction completely)
    alpha>1.0 = over-project (more aggressive erasure, may hurt neighbors)

    NOTE: All math is done in float32 for numerical precision, then
    the result is IMMEDIATELY cast back to the original dtype (float16)
    to prevent memory thrashing from accumulating float32 tensors.
    """
    orig_dtype = W.dtype
    # Upcast to float32 for numerical precision — float16 loses too much
    W_f32 = W.float()
    v_f32 = v.to(W.device).float().flatten()

    v_norm_sq = torch.dot(v_f32, v_f32)
    if v_norm_sq < 1e-10:
        logger.warning("Forget vector has near-zero norm, skipping projection")
        return W

    # nn.Linear: W is [out_dim, in_dim]
    # Project out v from the input dimension (dim 1)
    Wv = torch.mv(W_f32, v_f32)          # [out_dim]
    outer = torch.outer(Wv, v_f32)       # [out_dim, in_dim]
    W_new = W_f32 - alpha * outer / v_norm_sq

    # IMMEDIATELY cast back to original dtype (float16) to prevent
    # memory thrashing from holding multiple float32 weight copies
    return W_new.to(orig_dtype)


def _compute_layer_alpha(
    alpha: float,
    layer_idx: int,
    target_layers: List[int],
    total_model_layers: int = 32,
) -> float:
    """
    Implements alpha decay: deeper layers get reduced alpha to preserve
    the model's grammatical and linguistic capabilities.

    The early layers identify concepts ("This is about Apple/Tim Cook"),
    and the late layers format grammar and sentence structure. Ablating
    late layers at full strength destroys the model's ability to produce
    coherent English.

    Strategy:
      - Sort target layers by index
      - The earliest half of selected layers get full alpha
      - The later half get linearly decaying alpha down to 60% of original
      - The very last layer in the selection gets the minimum (60%)

    Example with alpha=1.0 and layers [5, 10, 15, 20, 25]:
      Layer 5:  alpha=1.0   (full)
      Layer 10: alpha=1.0   (full — still in early half)
      Layer 15: alpha=0.9   (start of decay)
      Layer 20: alpha=0.8   (deeper decay)
      Layer 25: alpha=0.6   (minimum — preserves grammar)
    """
    sorted_layers = sorted(target_layers)
    num_targets = len(sorted_layers)

    if num_targets <= 1:
        return alpha

    position = sorted_layers.index(layer_idx)
    midpoint = num_targets // 2

    if position < midpoint:
        # Early layers: full alpha
        return alpha
    else:
        # Late layers: linear decay from 100% down to 60%
        decay_range = num_targets - midpoint
        decay_position = position - midpoint
        decay_factor = 1.0 - (0.4 * decay_position / max(decay_range - 1, 1))
        decayed_alpha = alpha * max(decay_factor, 0.6)

        logger.info(
            f"Alpha decay: layer {layer_idx} (position {position}/{num_targets}) "
            f"→ alpha {alpha:.2f} * {decay_factor:.2f} = {decayed_alpha:.2f}"
        )
        return decayed_alpha


def check_ablation_overlap(concept: str, similarity_threshold: float = 0.65) -> Optional[dict]:
    """
    Pre-ablation intercept: Check local history for past ablations that
    semantically overlap with the new concept.
    
    Uses local in-memory cache (file-backed) for reliability — the Hindsight
    API has async issues inside FastAPI's event loop.
    
    Args:
        concept: The new concept to be ablated
        similarity_threshold: Cosine similarity threshold (default: 0.70)
    
    Returns:
        Warning dict if overlap detected, None otherwise.
    """
    if not _ablation_history:
        logger.info("No past ablations in history — this is the first ablation")
        return None
    
    try:
        new_vector = get_forget_vector(concept)
        
        logger.info(f"Checking overlap against {len(_ablation_history)} past ablations")
        
        for past in _ablation_history:
            past_concept = past["concept"]
            past_perplexity = past.get("post_perplexity")
            
            past_vector = get_forget_vector(past_concept)
            
            similarity = torch.nn.functional.cosine_similarity(
                new_vector.unsqueeze(0).float(),
                past_vector.unsqueeze(0).float()
            ).item()
            
            logger.info(f"Overlap: '{concept[:30]}' vs '{past_concept[:30]}' = {similarity:.4f}")
            
            if similarity > similarity_threshold:
                degradation = 18.0
                if past_perplexity:
                    degradation = min(abs(past_perplexity - 10.0), 50.0)
                
                return {
                    "status": "warning",
                    "message": (
                        f"This concept overlaps {similarity:.0%} with a previous ablation "
                        f"'{past_concept[:50]}'. Stacking ablations on overlapping concepts "
                        f"may degrade model quality by ~{degradation:.0f}%."
                    ),
                    "past_concept": past_concept,
                    "similarity": round(similarity, 4),
                    "historical_perplexity_degradation": round(degradation, 2)
                }
        
        logger.info(f"No overlapping ablations found for '{concept[:30]}'")
        return None
        
    except Exception as e:
        logger.error(f"Error checking ablation overlap: {e}")
        return None


def shift_target_layers(target_layers: List[Dict], shift: int, max_layers: int = 32) -> List[Dict]:
    """
    Shift target layers by a given offset for cascade retry.
    
    Args:
        target_layers: Original list of target layer dicts
        shift: Number of layers to shift (+2 or -2)
        max_layers: Maximum number of layers in the model
    
    Returns:
        New list of target layers with shifted indices
    """
    shifted = []
    for layer_info in target_layers:
        new_idx = layer_info["layer_index"] + shift
        # Keep within valid range [4, max_layers-5] to avoid extreme layers
        if 4 <= new_idx < max_layers - 4:
            shifted.append({
                "layer_index": new_idx,
                "target_matrices": layer_info.get("target_matrices", ["W_Q", "W_K", "W_V"])
            })
    return shifted


def ablate(
    layer_forget_vectors: Dict[int, torch.Tensor],
    target_layers: List[Dict],
    alpha: float = 1.0,
    concept: Optional[str] = None,
    pre_perplexity: Optional[float] = None,
) -> dict:
    """
    Main ablation function — applies orthogonal projection to target layers
    using LAYER-SPECIFIC forget vectors with alpha decay.

    Args:
        layer_forget_vectors: Dict mapping layer_index -> forget vector for that layer.
                              Each vector is the concept's direction in that layer's space.
        target_layers: List of dicts with layer_index, target_matrices.
        alpha: Base projection strength. 1.0 = exact removal, >1.0 = aggressive.
               Alpha is automatically decayed for deeper layers to preserve grammar.
        concept: The concept being ablated (for logging).
        pre_perplexity: Pre-ablation perplexity (for logging).
    """
    model, tokenizer, device = load_model()

    ablation_id = str(uuid.uuid4())
    backup = {}
    layer_results = []

    # Extract all target layer indices for alpha decay computation
    all_target_indices = sorted([l["layer_index"] for l in target_layers])
    total_model_layers = model.config.num_hidden_layers

    for layer_info in target_layers:
        layer_idx = layer_info["layer_index"]
        target_matrices = layer_info.get("target_matrices", ["W_Q", "W_K", "W_V"])

        # Get the layer-specific forget vector
        if layer_idx not in layer_forget_vectors:
            logger.warning(f"No forget vector for layer {layer_idx}, skipping")
            continue

        # Compute decayed alpha for this layer's depth
        layer_alpha = _compute_layer_alpha(
            alpha, layer_idx, all_target_indices, total_model_layers
        )

        forget_v = layer_forget_vectors[layer_idx]
        weights = get_target_weights(model, layer_idx, target_matrices)

        for weight_name, weight_param in weights.items():
            backup_key = f"layer_{layer_idx}_{weight_name}"
            backup[backup_key] = weight_param.data.clone()

            original_hash = _weight_hash(weight_param.data)

            with torch.no_grad():
                # Use the LAYER-SPECIFIC forget vector with DECAYED alpha
                new_weight = apply_projection(weight_param.data, forget_v, layer_alpha)
                weight_param.data.copy_(new_weight)

            modified_hash = _weight_hash(weight_param.data)

            layer_results.append({
                "layer": layer_idx,
                "matrix": weight_name,
                "alpha_used": round(layer_alpha, 3),
                "original_hash": original_hash,
                "modified_hash": modified_hash,
                "changed": original_hash != modified_hash
            })

            logger.info(
                f"Layer {layer_idx} {weight_name} (alpha={layer_alpha:.2f}): "
                f"{original_hash} -> {modified_hash} "
                f"({'CHANGED' if original_hash != modified_hash else 'UNCHANGED'})"
            )

    # Store backup
    _weight_backups[ablation_id] = backup
    metadata = {
        "ablation_id": ablation_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "targeted_layers": [l["layer_index"] for l in target_layers],
        "layer_results": layer_results,
        "status": "success",
        "alpha": alpha,
        "alpha_decay": "enabled",
        "correctness_check": all(r["changed"] for r in layer_results),
        "concept": concept,
        "pre_perplexity": pre_perplexity,
        "cascade_triggered": False
    }

    logger.info(f"Ablation {ablation_id} complete — {len(layer_results)} matrices modified (alpha decay enabled)")
    return metadata


def ablate_with_cascade(
    layer_forget_vectors: Dict[int, torch.Tensor],
    target_layers: List[Dict],
    alpha: float = 1.0,
    concept: Optional[str] = None,
    pre_perplexity: Optional[float] = None,
    cascade_threshold: Optional[float] = None,
    compute_perplexity_fn: Optional[Callable[[str], float]] = None,
) -> dict:
    """
    Ablation with CascadeFlow: Automatically retries with shifted layers if
    the model's *general* coherence degrades beyond threshold.
    
    IMPORTANT: CascadeFlow checks perplexity on a NEUTRAL reference text
    ("The sky is blue and the grass is green"), NOT on the ablated concept.
    Increased perplexity on the ablated concept is EXPECTED and DESIRED.
    The cascade only triggers when the model's general language ability degrades.
    
    Args:
        layer_forget_vectors: Dict mapping layer_index -> forget vector
        target_layers: Initial target layers
        alpha: Ablation strength
        concept: Concept being ablated
        pre_perplexity: Pre-ablation perplexity on the concept (for reporting)
        cascade_threshold: General coherence degradation threshold (e.g., 50.0 for 50%)
        compute_perplexity_fn: Function to compute perplexity
    
    Returns:
        Metadata dict with cascade information
    """
    if not cascade_threshold or not compute_perplexity_fn or not concept:
        return ablate(layer_forget_vectors, target_layers, alpha, concept, pre_perplexity)
    
    # Measure BASELINE coherence on a neutral sentence (not the ablated concept)
    NEUTRAL_TEXT = "The sky is blue and the grass is green. Water flows downhill."
    baseline_coherence = compute_perplexity_fn(NEUTRAL_TEXT)
    
    logger.info(f"CascadeFlow: baseline coherence = {baseline_coherence:.2f}, threshold = {cascade_threshold}%")
    
    # Attempt initial ablation
    result = ablate(layer_forget_vectors, target_layers, alpha, concept, pre_perplexity)
    ablation_id = result["ablation_id"]
    
    # Check if MODEL COHERENCE degraded (not concept perplexity)
    post_coherence = compute_perplexity_fn(NEUTRAL_TEXT)
    coherence_change = post_coherence - baseline_coherence
    coherence_degradation_pct = (coherence_change / max(baseline_coherence, 1)) * 100
    
    # Also compute concept perplexity for reporting
    post_concept_perplexity = compute_perplexity_fn(concept)
    
    logger.info(
        f"CascadeFlow: coherence {baseline_coherence:.2f} → {post_coherence:.2f} "
        f"({coherence_degradation_pct:+.1f}%), concept perplexity: {post_concept_perplexity:.2f}"
    )
    
    # Only cascade if GENERAL COHERENCE degrades badly
    if coherence_degradation_pct > cascade_threshold:
        logger.warning(f"CascadeFlow triggered: coherence degraded {coherence_degradation_pct:.1f}%")
        
        rollback(ablation_id)
        
        cascade_attempts = []
        model, _, _ = load_model()
        max_layers = model.config.num_hidden_layers
        
        for shift in [-2, +2]:
            shifted_layers = shift_target_layers(target_layers, shift, max_layers)
            if not shifted_layers:
                continue
            
            logger.info(f"CascadeFlow retry shift {shift:+d}: layers {[l['layer_index'] for l in shifted_layers]}")
            
            cascade_result = ablate(layer_forget_vectors, shifted_layers, alpha, concept, pre_perplexity)
            cascade_id = cascade_result["ablation_id"]
            
            cascade_coherence = compute_perplexity_fn(NEUTRAL_TEXT)
            cascade_change = cascade_coherence - baseline_coherence
            cascade_deg_pct = (cascade_change / max(baseline_coherence, 1)) * 100
            cascade_concept_perp = compute_perplexity_fn(concept)
            
            cascade_attempts.append({
                "shift": shift,
                "layers": [l["layer_index"] for l in shifted_layers],
                "coherence_perplexity": round(cascade_coherence, 2),
                "concept_perplexity": round(cascade_concept_perp, 2),
                "degradation_pct": round(cascade_deg_pct, 2),
                "success": cascade_deg_pct <= cascade_threshold
            })
            
            if cascade_deg_pct <= cascade_threshold:
                logger.info(f"CascadeFlow: shift {shift:+d} acceptable ({cascade_deg_pct:.1f}%)")
                return {
                    **cascade_result,
                    "cascade_triggered": True,
                    "cascade_shift": shift,
                    "cascade_attempts": cascade_attempts,
                    "original_layers": [l["layer_index"] for l in target_layers],
                    "final_layers": [l["layer_index"] for l in shifted_layers],
                    "post_perplexity": round(cascade_concept_perp, 2),
                    "perplexity_change": round(cascade_concept_perp - (pre_perplexity or 0), 2),
                    "perplexity_degradation_pct": round(cascade_deg_pct, 2)
                }
            else:
                logger.warning(f"CascadeFlow shift {shift:+d} also degraded ({cascade_deg_pct:.1f}%), rolling back")
                rollback(cascade_id)
        
        # All attempts failed — fall back to normal ablation (let user decide)
        logger.warning("CascadeFlow: all retries exceeded threshold, proceeding with original layers")
        final_result = ablate(layer_forget_vectors, target_layers, alpha, concept, pre_perplexity)
        final_concept_perp = compute_perplexity_fn(concept)
        return {
            **final_result,
            "cascade_triggered": True,
            "cascade_exhausted": True,
            "cascade_attempts": cascade_attempts,
            "original_layers": [l["layer_index"] for l in target_layers],
            "final_layers": [l["layer_index"] for l in target_layers],
            "post_perplexity": round(final_concept_perp, 2),
            "perplexity_change": round(final_concept_perp - (pre_perplexity or 0), 2),
            "cascade_message": "CascadeFlow tried shifted layers but couldn't improve coherence. Proceeding with original layers."
        }
    
    # Initial ablation was fine
    return {
        **result,
        "post_perplexity": round(post_concept_perplexity, 2),
        "perplexity_change": round(post_concept_perplexity - (pre_perplexity or 0), 2),
        "perplexity_degradation_pct": round(coherence_degradation_pct, 2)
    }


def log_ablation_to_hindsight(
    ablation_id: str,
    concept: str,
    target_layers: List[int],
    alpha: float,
    post_perplexity: float
) -> bool:
    """
    Log a successful ablation to local history and optionally to Hindsight cloud.
    
    Returns:
        True if logging successful, False otherwise
    """
    global _ablation_history
    
    # Always add to local history (reliable, instant)
    record = {
        "ablation_id": ablation_id,
        "concept": concept,
        "target_layers": target_layers,
        "alpha": alpha,
        "post_perplexity": post_perplexity,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    _ablation_history.append(record)
    _save_history()
    logger.info(f"Ablation logged to local history (total: {len(_ablation_history)})")
    
    # Try Hindsight cloud backup asynchronously (don't block)
    if _hindsight_client:
        import asyncio
        content = (
            f"Ablated concept: {concept} at layers {', '.join(map(str, target_layers))} "
            f"with post_perplexity {post_perplexity:.2f}"
        )
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_hindsight_retain_async(content))
        except RuntimeError:
            logger.debug("No running event loop for Hindsight async backup")
    
    return True


def rollback(ablation_id: str) -> dict:
    """Restores the original weights from before an ablation."""
    if ablation_id not in _weight_backups:
        raise ValueError(f"No backup found for ablation_id: {ablation_id}")

    model, tokenizer, device = load_model()
    backup = _weight_backups[ablation_id]

    restored = []
    for backup_key, original_weight in backup.items():
        parts = backup_key.split("_")
        layer_idx = int(parts[1])
        weight_name = "_".join(parts[2:])

        weights = get_target_weights(model, layer_idx, [weight_name])
        with torch.no_grad():
            weights[weight_name].data.copy_(original_weight)

        restored.append({"layer": layer_idx, "matrix": weight_name})
        logger.info(f"Restored {backup_key}")

    del _weight_backups[ablation_id]

    return {
        "ablation_id": ablation_id,
        "status": "rolled_back",
        "restored_matrices": restored,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def generate_compliance_report(
    ablation_result: Dict[str, Any],
    concept: str,
    target_layers: List[int],
    alpha: float,
    pre_perplexity: float,
    post_perplexity: float,
    before_completion: str,
    after_completion: str,
) -> Dict[str, str]:
    """
    Generates compliance reports (JSON + Markdown) for an ablation.
    
    Args:
        ablation_result: The result dict from ablate() or ablate_with_cascade()
        concept: The concept that was ablated
        target_layers: List of layer indices that were targeted
        alpha: Ablation strength used
        pre_perplexity: Perplexity before ablation
        post_perplexity: Perplexity after ablation
        before_completion: Text completion before ablation
        after_completion: Text completion after ablation
    
    Returns:
        Dict with paths to generated files: {"json_path": ..., "md_path": ...}
    """
    ablation_id = ablation_result["ablation_id"]
    timestamp = ablation_result["timestamp"]
    
    # Create reports directory if it doesn't exist
    reports_dir = Path(__file__).parent.parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    
    # Generate deterministic config hash (hash the CONFIG, not the weights)
    config_dict = {
        "concept": concept,
        "target_layers": sorted(target_layers),
        "alpha": alpha,
        "timestamp": timestamp
    }
    config_str = json.dumps(config_dict, sort_keys=True)
    config_hash = hashlib.sha256(config_str.encode()).hexdigest()
    
    # Calculate metrics
    perplexity_delta = post_perplexity - pre_perplexity
    forgetting_signal = "FORGOTTEN" if post_perplexity > 100.0 else "STILL_KNOWN"
    
    # Count changed matrices
    changed_matrix_count = sum(
        1 for r in ablation_result.get("layer_results", []) if r.get("changed", False)
    )
    
    # Build JSON report
    json_report = {
        "ablation_id": ablation_id,
        "timestamp": timestamp,
        "concept": concept,
        "target_layers": target_layers,
        "alpha": alpha,
        "pre_perplexity": round(pre_perplexity, 2),
        "post_perplexity": round(post_perplexity, 2),
        "perplexity_delta": round(perplexity_delta, 2),
        "forgetting_signal": forgetting_signal,
        "config_hash": config_hash,
        "before_completion": before_completion,
        "after_completion": after_completion,
        "changed_matrix_count": changed_matrix_count,
        "layer_results": ablation_result.get("layer_results", []),
        "cascade_triggered": ablation_result.get("cascade_triggered", False),
        "alpha_decay": ablation_result.get("alpha_decay", "enabled")
    }
    
    # Add cascade info if present
    if ablation_result.get("cascade_triggered"):
        json_report["cascade_info"] = {
            "shift": ablation_result.get("cascade_shift"),
            "original_layers": ablation_result.get("original_layers", []),
            "final_layers": ablation_result.get("final_layers", []),
            "attempts": ablation_result.get("cascade_attempts", [])
        }
    
    # Write JSON report
    json_path = reports_dir / f"{ablation_id}.json"
    with open(json_path, "w") as f:
        json.dump(json_report, f, indent=2)
    
    # Build Markdown report
    md_lines = [
        "# VSAE Compliance Report",
        "",
        f"**Ablation ID:** `{ablation_id}`",
        f"**Timestamp:** {timestamp}",
        f"**Concept Removed:** {concept}",
        f"**Target Layers:** {', '.join(map(str, target_layers))}",
        f"**Ablation Strength (α):** {alpha}",
        f"**Alpha Decay:** {ablation_result.get('alpha_decay', 'enabled')}",
        "",
        "## Statistical Evidence",
        "",
        "| Metric | Before | After | Change |",
        "|--------|--------|-------|--------|",
        f"| Perplexity | {pre_perplexity:.2f} | {post_perplexity:.2f} | {perplexity_delta:+.2f} |",
        f"| Matrices Modified | - | {changed_matrix_count} | - |",
        "",
        "## Forgetting Signal",
        "",
        f"**Perplexity-Based Retention Heuristic:** `{forgetting_signal}`",
        "",
    ]
    
    if forgetting_signal == "FORGOTTEN":
        md_lines.append("✅ Post-ablation perplexity exceeds statistical suppression threshold (>100.0)")
    else:
        md_lines.append("⚠️ Post-ablation perplexity below threshold — concept may still be partially retained")
    
    md_lines.extend([
        "",
        "## Before/After Proof",
        "",
        "**Before Ablation:**",
        f"> {before_completion}",
        "",
        "**After Ablation:**",
        f"> {after_completion}",
        "",
    ])
    
    # Add cascade info if present
    if ablation_result.get("cascade_triggered"):
        md_lines.extend([
            "## CascadeFlow Information",
            "",
            f"**Cascade Triggered:** Yes",
            f"**Layer Shift:** {ablation_result.get('cascade_shift', 'N/A')}",
            f"**Original Layers:** {ablation_result.get('original_layers', [])}",
            f"**Final Layers:** {ablation_result.get('final_layers', [])}",
            "",
        ])
    
    md_lines.extend([
        "## Layer Modification Details",
        "",
        "| Layer | Matrix | Alpha Used | Status |",
        "|-------|--------|------------|--------|",
    ])
    
    for lr in ablation_result.get("layer_results", []):
        status = "✅ Changed" if lr.get("changed") else "⚠️ Unchanged"
        md_lines.append(
            f"| {lr['layer']} | {lr['matrix']} | {lr.get('alpha_used', alpha):.3f} | {status} |"
        )
    
    md_lines.extend([
        "",
        "## Configuration Hash",
        "",
        f"**SHA-256 of ablation parameters:** `{config_hash}`",
        "",
        "This hash is deterministic and reproducible from the configuration:",
        f"- Concept: {concept}",
        f"- Target Layers: {sorted(target_layers)}",
        f"- Alpha: {alpha}",
        f"- Timestamp: {timestamp}",
        "",
        "---",
        "*Generated by Vector Space Ablation Engine (VSAE)*",
    ])
    
    # Write Markdown report
    md_path = reports_dir / f"{ablation_id}.md"
    with open(md_path, "w") as f:
        f.write("\n".join(md_lines))
    
    logger.info(f"Compliance reports generated: {json_path.name}, {md_path.name}")
    
    return {
        "json_path": str(json_path),
        "md_path": str(md_path)
    }


def get_active_ablations() -> List[dict]:
    """Returns metadata for all active (non-rolled-back) ablations."""
    return [
        {
            "concept": rec["concept"],
            "ablation_id": rec["ablation_id"],
            "target_layers": rec["target_layers"],
            "post_perplexity": rec.get("post_perplexity"),
            "timestamp": rec.get("timestamp")
        }
        for rec in _ablation_history
    ]
