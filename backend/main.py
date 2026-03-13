from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from backend.embedding import get_forget_vector, get_model_info
import torch

app = FastAPI(
    title="Vector Space Ablation Engine",
    description="Surgical knowledge removal from LLMs",
    version="1.0.0"
)

# ── Request schema ─────────────────────────────────────
class ForgetRequest(BaseModel):
    forget_text: str
    model_id: str = "gpt2"

# ── Endpoints ──────────────────────────────────────────
@app.get("/health")
def health():
    info = get_model_info()
    return {
        "status": "ok",
        **info
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
        "first_5_values": v[:5].tolist(),
        "device": str(v.device),
        "status": "success"
    }