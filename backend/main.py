from fastapi import FastAPI

app = FastAPI(
    title="Vector Space Ablation Engine",
    description="Surgical knowledge removal from LLMs",
    version="1.0.0"
)

@app.get("/health")
def health():
    return {
        "status": "ok",
        "model": "gpt2",
        "device": "mps"
    }