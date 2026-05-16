# Vector Space Ablation Engine (VSAE)

**Surgical Knowledge Removal from LLMs — Optimized for Phi-2**

The Vector Space Ablation Engine (VSAE) is a powerful tool designed to surgically remove specific concepts or knowledge from Large Language Models without requiring full retraining or fine-tuning. By utilizing orthogonal projection and activation tracing, VSAE locates where a concept lives in the network's latent space and dynamically ablates it.

Currently, this engine is specifically optimized and focused on the **Microsoft Phi-2** model, allowing for high-precision unlearning in resource-constrained environments using float16 precision.

## 🚀 Features

- **Concept Embedding & Projection**: Generates precise "forget vectors" for any target concept.
- **Dynamic Subspace Locator**: Automatically identifies the most relevant attention and feed-forward layers (`W_Q`, `W_K`, `W_V`, `dense`, `fc1`) responsible for a concept using activation tracing.
- **Real-Time Ablation**: Applies orthogonal projection to surgically remove the concept from the model's weights on the fly.
- **Before & After Proofs**: Instantly generates completions before and after ablation to mathematically verify the unlearning process via perplexity shifts.
- **Guardrailed Probing**: A built-in chat interface that allows you to safely interact with the ablated model, complete with perplexity-based guardrails.
- **Full Evaluation Suite**: Run comprehensive tests on your ablations to ensure the model retains its general capabilities while forgetting the target concept.
- **Premium UI**: A sleek, two-panel dark mode interface for managing ablations and probing the model interactively.

## 📁 Project Structure

- **`backend/`**: The core ablation engine built with FastAPI and PyTorch.
  - `main.py`: The FastAPI server and API endpoints.
  - `ablation.py`: Core logic for applying orthogonal projections to model weights.
  - `embedding.py`: Handles model initialization, text generation, and forget vector creation.
  - `locator.py`: Identifies the top-k layers most activated by the forget concept.
  - `evaluate.py`: Suite for evaluating model perplexity and ablation success.
- **`frontend/`**: A lightweight, vanilla HTML/JS/CSS frontend.
  - Served directly via the FastAPI backend for a seamless full-stack experience.

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.10+
- PyTorch (with MPS/CUDA support recommended for Phi-2)
- Minimum 16GB RAM (Apple Silicon or dedicated GPU recommended)

### 1. Clone the repository
```bash
git clone https://github.com/irudayajason/VSAE.git
cd VSAE
```

### 2. Set up the Python Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
pip install -r backend/requirements.txt # If available, otherwise install torch, transformers, fastapi, uvicorn
```

### 3. Run the Engine
You can start the unified engine (which serves both the API and the UI) using Uvicorn:

```bash
uvicorn backend.main:app --reload
```

### 4. Access the UI
Open your browser and navigate to:
```
http://localhost:8000
```

## 🔌 API Endpoints

The backend provides a robust REST API for programmatic access:

- `GET /health` - System status and currently loaded model info.
- `GET /ablations` - List all active ablations.
- `POST /embed` - Generate the semantic "forget vector" for a concept.
- `POST /ablate` - Run the full ablation pipeline (finds layers, applies projection, and returns before/after proofs).
- `POST /probe` - Chat with the loaded model (includes guardrails for ablated concepts).
- `POST /evaluate` - Generate a detailed statistical report on ablation impact.
- `POST /rollback` - Instantly reverse an active ablation.

## ⚠️ Disclaimer

This tool manipulates the weights of LLMs in memory. While it is designed to be safe and reversible via the `/rollback` endpoint, applying too many overlapping ablations or using extreme ablation strengths may degrade the general performance of the Phi-2 model.

---
*Built for surgical AI control and interpretability.*

## Development Timeline

| Weeks | Milestone |
|-------|-----------|
| 1–2 | Environment setup, GPT-2 & Phi-2 loading, literature research |
| 3–4 | Embedding Module — forget vector extraction |
| 5–6 | Ablation Engine — orthogonal projection formula |
| 7–8 | Full pipeline on model weights + rollback |
| 9–10 | FastAPI endpoints + HTML/JS frontend UI |
| 11–12 | Evaluation suite — Perplexity, probing |
| 13–14 | Final testing, demo mode, project report |

## Founders

| Member | Role | Hardware |
|--------|------|----------|
| Irudaya Jason J | Ablation Engine + FastAPI | MacBook M4 Air (MPS) |
| Mithun A | Literature Research + Embedding Module | Intel Core Ultra i5 125H |
| Mohammed Nahyan Khan | GPU Testing + Frontend | Intel i7 13th Gen + RTX 4050 |

## License

MIT License — see [LICENSE](LICENSE) for details.
