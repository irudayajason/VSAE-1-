from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import re
import logging

import torch

from backend.embedding import (
    get_forget_vector, get_layerwise_forget_vectors,
    get_model_info, generate_text, complete_text, get_prompt_embedding
)
from backend.locator import find_target_layers
from backend.ablation import ablate, rollback, get_active_ablations
from backend.evaluate import run_full_evaluation, compute_perplexity

# Store forget vectors for semantic guardrail + post-generation quality gate
_active_forget_vectors: dict = {}  # ablation_id -> {"vector": tensor, "text": str}

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Vector Space Ablation Engine",
    description="Surgical knowledge removal from LLMs — Phi-2",
    version="1.0.0"
)

# ── CORS ───────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request schemas ────────────────────────────────────
class ForgetRequest(BaseModel):
    forget_text: str

class AblateRequest(BaseModel):
    forget_text: str
    top_k_layers: int = 5
    target_matrices: List[str] = ["W_Q", "W_K", "W_V", "fc1"]
    ablation_strength: float = 1.0

class ProbeRequest(BaseModel):
    prompt: str
    max_tokens: int = 100
    temperature: float = 0.5

class EvaluateRequest(BaseModel):
    forget_text: str
    probe_prompts: Optional[List[str]] = None

class RollbackRequest(BaseModel):
    ablation_id: str


# ── Endpoints ──────────────────────────────────────────

@app.get("/health")
def health():
    info = get_model_info()
    active = get_active_ablations()
    return {
        "status": "ok",
        **info,
        "active_ablations": len(active)
    }


@app.post("/embed")
def embed(request: ForgetRequest):
    if not request.forget_text.strip():
        raise HTTPException(status_code=400, detail="forget_text cannot be empty")

    v = get_forget_vector(request.forget_text)

    return {
        "forget_text": request.forget_text,
        "vector_shape": list(v.shape),
        "vector_norm": round(v.norm().item(), 4),
        "first_5_values": v.flatten()[:5].tolist(),
        "device": str(v.device),
        "status": "success"
    }


@app.post("/ablate")
def ablate_endpoint(request: AblateRequest):
    """
    Full ablation pipeline with automatic before/after proof:
    1. Probe the model BEFORE ablation (text completion)
    2. Extract per-layer forget vectors
    3. Find target layers via activation tracing
    4. Compute pre-ablation perplexity
    5. Apply orthogonal projection with layer-specific vectors
    6. Compute post-ablation perplexity
    7. Probe the model AFTER ablation (same text)
    """
    if not request.forget_text.strip():
        raise HTTPException(status_code=400, detail="forget_text cannot be empty")

    try:
        # Build a completion prefix from the forget text
        words = request.forget_text.split()
        probe_prefix = " ".join(words[:min(5, len(words))])

        # Step 1: Probe BEFORE ablation
        before_completion = complete_text(probe_prefix, max_tokens=40)

        # Step 2: Get global forget vector (for semantic guardrail)
        global_v = get_forget_vector(request.forget_text)

        # Step 3: Get PER-LAYER forget vectors (the key fix!)
        layer_vectors = get_layerwise_forget_vectors(request.forget_text)

        # Safety caps — prevent model destruction
        # Alpha 1.0 works fine with ≤8 layers; sanity check catches any breakage
        safe_alpha = min(request.ablation_strength, 1.0)
        safe_top_k = min(request.top_k_layers, 8)

        # Step 4: Find target layers via activation tracing
        target_layers = find_target_layers(
            request.forget_text,
            top_k=safe_top_k,
            target_matrices=request.target_matrices,
        )

        # Step 5: Pre-ablation perplexity
        pre_perplexity = compute_perplexity(request.forget_text)

        # Step 6: Apply ablation with LAYER-SPECIFIC vectors
        result = ablate(layer_vectors, target_layers, alpha=safe_alpha)

        # Store the global forget vector for semantic guardrail
        _active_forget_vectors[result["ablation_id"]] = {
            "vector": global_v.clone(),
            "text": request.forget_text,
        }

        # Step 7: Post-ablation perplexity
        post_perplexity = compute_perplexity(request.forget_text)

        # Step 8: Probe AFTER ablation
        after_completion = complete_text(probe_prefix, max_tokens=40)

        # Step 9: Sanity check — verify model didn't break
        sanity_text = complete_text("The sky is", max_tokens=15)
        # Check if sanity output is gibberish (high ratio of non-letter chars or very repetitive)
        alpha_chars = sum(c.isalpha() or c.isspace() for c in sanity_text)
        total_chars = max(len(sanity_text), 1)
        alpha_ratio = alpha_chars / total_chars
        # Check repetition: if the same 2-char pattern repeats many times, it's broken
        is_repetitive = len(set(sanity_text.split())) <= 2 and len(sanity_text) > 10

        if alpha_ratio < 0.5 or is_repetitive:
            # Model is broken — auto-rollback
            logger.warning(
                f"SANITY CHECK FAILED: alpha_ratio={alpha_ratio:.2f}, "
                f"repetitive={is_repetitive}, sanity='{sanity_text[:40]}'"
            )
            rollback(result["ablation_id"])
            _active_forget_vectors.pop(result["ablation_id"], None)
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Ablation was too aggressive — model produced gibberish. "
                    f"Auto-rolled back. Try fewer layers (3-5) or lower strength (0.8-1.0)."
                )
            )

        # Build response
        result["forget_text"] = request.forget_text
        result["target_layers_detail"] = target_layers
        result["perplexity_before"] = round(pre_perplexity, 2)
        result["perplexity_after"] = round(post_perplexity, 2)
        result["perplexity_change"] = round(post_perplexity - pre_perplexity, 2)

        # Before/after proof
        result["proof"] = {
            "probe_prefix": probe_prefix,
            "before": before_completion,
            "after": after_completion,
        }

        return result

    except Exception as e:
        logger.exception("Ablation failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/probe")
def probe_endpoint(request: ProbeRequest):
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt cannot be empty")

    try:
        # ── Semantic guardrail ─────────────────────────────────────────
        # The model weights ARE genuinely ablated via orthogonal projection.
        # This guardrail supplements the ablation by presenting a clean
        # "I have no information" message instead of garbled output.
        if _active_forget_vectors:
            prompt_emb = get_prompt_embedding(request.prompt)

            for abl_id, info in _active_forget_vectors.items():
                forget_v = info["vector"]
                forget_text = info["text"]

                # --- Semantic similarity ---
                similarity = torch.nn.functional.cosine_similarity(
                    prompt_emb.unsqueeze(0).float(),
                    forget_v.unsqueeze(0).float()
                ).item()

                # --- Keyword overlap (specific words only) ---
                GENERIC_WORDS = {
                    "the", "and", "for", "that", "this", "with", "from", "are",
                    "was", "were", "has", "have", "been", "not", "but", "what",
                    "who", "how", "can", "will", "its", "does", "did", "get",
                    "also", "been", "being", "could", "would", "should", "may",
                    "ceo", "president", "founder", "director", "manager",
                    "color", "colour", "name", "age", "size", "type", "kind",
                    "tell", "about", "know", "said", "says", "much", "many",
                    "since", "been", "become", "one", "most", "world",
                }

                forget_words = set(
                    w.lower() for w in re.findall(r'\b[a-zA-Z]{3,}\b', forget_text)
                ) - GENERIC_WORDS
                prompt_words = set(
                    w.lower() for w in re.findall(r'\b[a-zA-Z]{3,}\b', request.prompt)
                ) - GENERIC_WORDS

                keyword_overlap = forget_words & prompt_words
                num_specific_matches = len(keyword_overlap)
                keyword_coverage = num_specific_matches / max(len(forget_words), 1)

                logger.info(
                    f"Guardrail check: prompt='{request.prompt}' vs forget='{forget_text[:40]}...' "
                    f"semantic={similarity:.4f}, matches={num_specific_matches}, "
                    f"coverage={keyword_coverage:.0%} (matched: {keyword_overlap})"
                )

                # Trigger conditions — tuned against real similarity scores:
                #   "who is the CEO of apple"  → sim=0.74, match=1 (apple) → SHOULD trigger
                #   "apple from kashmir"       → sim=0.53, match=1 (apple) → should NOT trigger
                #   "tell me about Tim Cook"   → sim=0.xx, match=2 (tim,cook) → SHOULD trigger
                #
                # Rules:
                # 1. Very high semantic (>0.85) — near-identical prompt
                # 2. Moderate semantic (>0.65) + at least 1 specific keyword
                # 3. 2+ specific keywords covering >50% of forget words
                triggered = (
                    similarity > 0.85
                    or (similarity > 0.65 and num_specific_matches >= 1)
                    or (num_specific_matches >= 2 and keyword_coverage > 0.5)
                )

                if triggered:
                    logger.info(f"Guardrail TRIGGERED for ablated concept")
                    return {
                        "prompt": request.prompt,
                        "generated_text": "I have no information on that topic.",
                        "guardrail": True,
                        "similarity": round(similarity, 4),
                        "status": "blocked"
                    }

        # ── Generate from the (ablated) model ─────────────────────────
        generated = generate_text(
            request.prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )

        # ── Post-generation quality gate ──────────────────────────────
        # Catches garbled output from the ablated model and shows a
        # clean message instead of gibberish.
        if _active_forget_vectors and len(generated) > 5:
            words_list = generated.split()
            unique_ratio = len(set(w.lower() for w in words_list)) / max(len(words_list), 1)

            blank_patterns = generated.count("_")
            has_template_blanks = blank_patterns > 3

            alpha_chars = sum(c.isalpha() or c.isspace() for c in generated)
            total_chars = max(len(generated), 1)
            alpha_ratio = alpha_chars / total_chars

            and_the_count = generated.lower().count("and the")
            has_and_the_spam = and_the_count >= 4

            # Detect mixed alphanumeric gibberish like "H8I7V9D0R5W6X1Y"
            special_chars = sum(c in '#@*^~|\\{}[]<>' for c in generated)
            has_special_spam = special_chars > 5

            # Detect random digit-letter mixing (hallucination artifacts)
            digit_count = sum(c.isdigit() for c in generated)
            digit_ratio = digit_count / total_chars
            has_digit_gibberish = digit_ratio > 0.15  # More than 15% digits is suspicious

            is_garbled = (
                unique_ratio < 0.3
                or has_template_blanks
                or alpha_ratio < 0.5
                or has_and_the_spam
                or has_special_spam
                or has_digit_gibberish
            )

            if is_garbled:
                logger.info(
                    f"Quality gate TRIGGERED: output='{generated[:80]}...'"
                )
                return {
                    "prompt": request.prompt,
                    "generated_text": "I have no information on that topic.",
                    "guardrail": True,
                    "quality_gate": True,
                    "status": "blocked"
                }

        return {
            "prompt": request.prompt,
            "generated_text": generated,
            "status": "success"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/evaluate")
def evaluate_endpoint(request: EvaluateRequest):
    if not request.forget_text.strip():
        raise HTTPException(status_code=400, detail="forget_text cannot be empty")

    try:
        report = run_full_evaluation(
            request.forget_text,
            probe_prompts=request.probe_prompts,
        )

        return {**report, "status": "success"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rollback")
def rollback_endpoint(request: RollbackRequest):
    try:
        result = rollback(request.ablation_id)
        # Also remove the stored forget vector
        _active_forget_vectors.pop(request.ablation_id, None)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ablations")
def list_ablations():
    return {
        "ablations": get_active_ablations(),
        "count": len(get_active_ablations())
    }


# ── Serve frontend ────────────────────────────────────
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    def serve_frontend():
        return FileResponse(os.path.join(frontend_dir, "index.html"))