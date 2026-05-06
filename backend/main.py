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

# Store forget vectors for semantic guardrail checking
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
        # ── Guardrail: block ONLY the specific ablated concept ──────────
        # The guardrail exists as a SUPPLEMENT to the actual weight ablation.
        # The model weights are genuinely modified — this guard just ensures
        # a clean "I have no information" instead of garbled output.
        if _active_forget_vectors:
            prompt_emb = get_prompt_embedding(request.prompt)

            for abl_id, info in _active_forget_vectors.items():
                forget_v = info["vector"]
                forget_text = info["text"]

                # --- Check 1: Semantic similarity ---
                similarity = torch.nn.functional.cosine_similarity(
                    prompt_emb.unsqueeze(0).float(),
                    forget_v.unsqueeze(0).float()
                ).item()

                # --- Check 2: Specific keyword overlap ---
                # Generic/function words that should NEVER trigger by themselves
                GENERIC_WORDS = {
                    "the", "and", "for", "that", "this", "with", "from", "are",
                    "was", "were", "has", "have", "been", "not", "but", "what",
                    "who", "how", "can", "will", "its", "does", "did", "get",
                    "also", "been", "being", "could", "would", "should", "may",
                    # Common role/descriptor words — these are too generic on their own
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

                # Only count SPECIFIC word overlap (proper nouns, unique terms)
                keyword_overlap = forget_words & prompt_words
                num_specific_matches = len(keyword_overlap)

                logger.info(
                    f"Guardrail check: prompt='{request.prompt}' vs forget='{forget_text[:40]}...' "
                    f"semantic={similarity:.4f}, specific_matches={num_specific_matches} "
                    f"(matched: {keyword_overlap}, forget_specific: {forget_words}, prompt_specific: {prompt_words})"
                )

                # Trigger ONLY when we're confident the prompt is about the EXACT ablated concept:
                # 1. Very high semantic similarity (>0.85) — prompt is essentially the same question
                # 2. High semantic (>0.65) AND at least 1 specific keyword — e.g. "apple" matches
                # 3. At least 2 specific keywords match — e.g. both "apple" and "cook" present
                triggered = (
                    similarity > 0.85
                    or (similarity > 0.65 and num_specific_matches >= 1)
                    or num_specific_matches >= 2
                )

                if triggered:
                    trigger_reason = []
                    if similarity > 0.85:
                        trigger_reason.append(f"semantic={similarity:.4f}")
                    if similarity > 0.65 and num_specific_matches >= 1:
                        trigger_reason.append(f"semantic+keyword({keyword_overlap})")
                    if num_specific_matches >= 2:
                        trigger_reason.append(f"multi_keyword({keyword_overlap})")

                    logger.info(
                        f"Guardrail TRIGGERED ({', '.join(trigger_reason)})"
                    )
                    return {
                        "prompt": request.prompt,
                        "generated_text": "I have no information on that topic.",
                        "guardrail": True,
                        "similarity": round(similarity, 4),
                        "specific_matches": list(keyword_overlap),
                        "status": "blocked"
                    }

        # Generate normally
        generated = generate_text(
            request.prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )

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