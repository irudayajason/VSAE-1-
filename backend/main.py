from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os

from backend.embedding import (
    get_forget_vector, get_model_info, generate_text,
    complete_text, MODEL_REGISTRY
)
from backend.locator import find_target_layers
from backend.ablation import ablate, rollback, get_active_ablations
from backend.evaluate import run_full_evaluation, compute_perplexity

app = FastAPI(
    title="Vector Space Ablation Engine",
    description="Surgical knowledge removal from LLMs",
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
    model_id: str = "gpt2"

class AblateRequest(BaseModel):
    forget_text: str
    model_id: str = "gpt2"
    top_k_layers: int = 3
    target_matrices: List[str] = ["W_Q", "W_K", "W_V"]

class ProbeRequest(BaseModel):
    prompt: str
    max_tokens: int = 100
    temperature: float = 0.5
    model_id: str = "gpt2"

class EvaluateRequest(BaseModel):
    forget_text: str
    probe_prompts: Optional[List[str]] = None
    model_id: str = "gpt2"

class RollbackRequest(BaseModel):
    ablation_id: str
    model_id: str = "gpt2"


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


@app.get("/models")
def list_models():
    """Returns list of available models."""
    return {
        "models": [
            {"id": k, "name": v["display_name"], "family": v["family"]}
            for k, v in MODEL_REGISTRY.items()
        ]
    }


@app.post("/embed")
def embed(request: ForgetRequest):
    if not request.forget_text.strip():
        raise HTTPException(status_code=400, detail="forget_text cannot be empty")

    v = get_forget_vector(request.forget_text, request.model_id)

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
    2. Compute pre-ablation perplexity
    3. Find target layers via activation tracing
    4. Apply orthogonal projection
    5. Probe the model AFTER ablation (same text)
    6. Compute post-ablation perplexity
    """
    if not request.forget_text.strip():
        raise HTTPException(status_code=400, detail="forget_text cannot be empty")

    try:
        # Build a completion prefix from the forget text
        # Use first ~5 words as the prefix for probing
        words = request.forget_text.split()
        probe_prefix = " ".join(words[:min(5, len(words))])

        # Step 1: Probe BEFORE ablation
        before_completion = complete_text(probe_prefix, max_tokens=40, model_name=request.model_id)

        # Step 2: Get forget vector
        v = get_forget_vector(request.forget_text, request.model_id)

        # Step 3: Find target layers
        target_layers = find_target_layers(
            request.forget_text,
            top_k=request.top_k_layers,
            model_name=request.model_id
        )

        # Step 4: Pre-ablation perplexity
        pre_perplexity = compute_perplexity(request.forget_text, request.model_id)

        # Step 5: Apply ablation
        result = ablate(v, target_layers, request.model_id)

        # Step 6: Post-ablation perplexity
        post_perplexity = compute_perplexity(request.forget_text, request.model_id)

        # Step 7: Probe AFTER ablation
        after_completion = complete_text(probe_prefix, max_tokens=40, model_name=request.model_id)

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
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/probe")
def probe_endpoint(request: ProbeRequest):
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt cannot be empty")

    try:
        generated = generate_text(
            request.prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            model_name=request.model_id
        )

        return {
            "prompt": request.prompt,
            "generated_text": generated,
            "model_id": request.model_id,
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
            model_name=request.model_id
        )

        return {**report, "status": "success"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rollback")
def rollback_endpoint(request: RollbackRequest):
    try:
        result = rollback(request.ablation_id, request.model_id)
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