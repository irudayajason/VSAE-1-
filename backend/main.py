from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os
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
    top_k_layers: int = 3
    target_matrices: List[str] = ["W_Q", "W_K", "W_V"]
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

        # Step 4: Find target layers via activation tracing
        target_layers = find_target_layers(
            request.forget_text,
            top_k=request.top_k_layers,
            target_matrices=request.target_matrices,
        )

        # Step 5: Pre-ablation perplexity
        pre_perplexity = compute_perplexity(request.forget_text)

        # Cap alpha to 1.0 (exact orthogonal projection) to prevent mathematically destructive reflections
        safe_alpha = min(request.ablation_strength, 1.0)

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
        # Semantic guardrail: check if the prompt is related to any ablated concept
        if _active_forget_vectors:
            prompt_emb = get_prompt_embedding(request.prompt)
            for abl_id, info in _active_forget_vectors.items():
                forget_v = info["vector"]
                # Cosine similarity between the prompt embedding and the forget vector
                similarity = torch.nn.functional.cosine_similarity(
                    prompt_emb.unsqueeze(0).float(),
                    forget_v.unsqueeze(0).float()
                ).item()
                logger.info(
                    f"Semantic guardrail: prompt vs '{info['text'][:30]}...' "
                    f"similarity = {similarity:.4f}"
                )
                if similarity > 0.72:
                    logger.info(f"Guardrail TRIGGERED (similarity {similarity:.4f} > 0.72)")
                    return {
                        "prompt": request.prompt,
                        "generated_text": "I have no information on that topic.",
                        "guardrail": True,
                        "similarity": round(similarity, 4),
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