# VSAE — Vector Space Ablation Engine

> Surgically remove specific knowledge from a trained Large Language Model — without retraining.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-red?logo=pytorch)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?logo=fastapi)
![HuggingFace](https://img.shields.io/badge/HuggingFace-Transformers-yellow?logo=huggingface)
![License](https://img.shields.io/badge/License-MIT-purple)
![Status](https://img.shields.io/badge/Status-In%20Development-orange)

---

## 🔍 What is VSAE?

VSAE is an open-source API tool that acts as a **surgical "delete button"** for AI models. It allows developers to remove specific concepts, facts, or private data from a trained LLM by mathematically modifying its internal weight matrices — without the need for expensive retraining.

### The Problem
When AI models like GPT-2, Llama, or Mistral are trained on billions of documents, they can accidentally memorize:
- 🔒 Private medical records
- ©️ Copyrighted materials
- 📄 Confidential company documents
- 👤 Personal communications

Laws like **GDPR**, **CCPA**, and **PDPB** legally require companies to delete this data on request — but existing solutions are either too expensive or ineffective.

### The Solution
VSAE applies an **orthogonal projection** directly to the model's weight matrices to erase the target concept:

```
W_new = W - (W · v · vᵀ) / (vᵀ · v)
```

Where `v` is the forget vector representing the concept to be erased and `W` is the target weight matrix.

---

## ⚙️ How It Works

```
Input Text (concept to forget)
        ↓
Embedding Module → extracts forget vector v
        ↓
Subspace Locator → finds target QKV matrices via activation tracing
        ↓
Ablation Engine → applies orthogonal projection to W
        ↓
Output Module → returns modified model weights
```

---

## 🚀 Features

- ✅ **Surgical knowledge removal** — targets only the relevant weight matrices
- ✅ **No retraining required** — works directly on existing model weights
- ✅ **Rollback support** — undo any ablation instantly
- ✅ **Evaluation suite** — proves the concept was erased with 3 test methodologies
- ✅ **REST API** — simple FastAPI wrapper for easy integration
- ✅ **Apple Silicon (MPS) + CUDA support** — runs on Mac M-series and NVIDIA GPUs

---

## 🧪 Evaluation Methods

| Method | What it checks |
|--------|---------------|
| **Membership Inference Attack** | Model can no longer recognize the forgotten data |
| **Perplexity Score** | Model is "confused" by the erased content (score spikes) |
| **Direct Probing** | Model cannot answer questions about the erased concept |

---

## 🛠️ Tech Stack

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.11+ | Core language |
| PyTorch | 2.0+ | Weight tensor manipulation |
| HuggingFace Transformers | 4.35+ | Model loading and tokenization |
| NumPy | 1.24+ | Linear algebra operations |
| FastAPI | 0.100+ | REST API framework |
| Pydantic | 2.0+ | Schema validation |
| GPT-2 | 117M params | Prototype model |

---

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Server and model status |
| `/ablate` | POST | Run the ablation pipeline |
| `/probe` | POST | Chat with the model |
| `/evaluate` | POST | Run full evaluation suite |
| `/rollback` | POST | Revert to original weights |

### Example Request
```json
POST /ablate
{
  "model_id": "gpt2",
  "forget_text": "Harry Potter lives at 4 Privet Drive",
  "top_k_layers": 3,
  "target_matrices": ["W_Q", "W_K", "W_V"]
}
```

### Example Response
```json
{
  "status": "success",
  "ablation_id": "uuid-string",
  "timestamp": "2026-03-07T00:00:00Z",
  "targeted_layers": [8, 10, 11],
  "original_weight_hash": "sha256-hex",
  "modified_weight_hash": "sha256-hex",
  "correctness_check": true
}
```

---

## 📦 Installation

```bash
# Clone the repo
git clone https://github.com/irudayajason/VASE.git
cd VASE

# Create virtual environment
python3.11 -m venv venv

# Activate (Mac/Linux)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install torch torchvision torchaudio
pip install transformers numpy fastapi uvicorn pydantic pytest
```

---

## ▶️ Running the API

```bash
uvicorn backend.main:app --reload
```

Then open:
- **API:** http://localhost:8000/health
- **Docs:** http://localhost:8000/docs

---

## 📁 Project Structure

```
vsae/
├── backend/
│   ├── __init__.py
│   ├── main.py          ← FastAPI app + endpoints
│   ├── embedding.py     ← Forget vector extraction
│   ├── locator.py       ← Subspace and layer targeting
│   ├── ablation.py      ← Core projection formula
│   └── evaluate.py      ← MIA, perplexity, probing tests
├── frontend/            ← Next.js + Tailwind UI
├── venv/
├── .gitignore
└── README.md
```

---

## 🗓️ Development Timeline

| Weeks | Milestone |
|-------|-----------|
| 1–2 | Environment setup, GPT-2 loading, literature research |
| 3–4 | Embedding Module — forget vector extraction |
| 5–6 | Ablation Engine — orthogonal projection formula |
| 7–8 | Full pipeline on GPT-2 weights + rollback |
| 9–10 | FastAPI endpoints + Next.js frontend UI |
| 11–12 | Evaluation suite — MIA, perplexity, probing |
| 13–14 | Final testing, demo mode, project report |

---

## ⚠️ Known Limitations

- **Relearning:** Model may re-acquire suppressed concepts if fine-tuned on similar data
- **Collateral Damage:** Projection may weaken semantically adjacent concepts
- **Multi-layer Spread:** Knowledge distributed across many layers makes 100% erasure difficult to guarantee

---

## 👥 Team

| Member | Role | Hardware |
|--------|------|----------|
| Irudaya Jason J | Ablation Engine + FastAPI | MacBook M4 Air (MPS) |
| Mithun A | Literature Research + Embedding Module | Intel Core Ultra i5 125H |
| Mohammed Nahyan Khan | GPU Testing + Frontend | Intel i7 13th Gen + RTX 4050 |

---

## 📚 References

- Cao & Yang (2015) — Machine Unlearning
- Golatkar et al (2020) — Eternal Sunshine of the Spotless Net
- Meng et al (2022) — ROME: Locating and Editing Factual Associations in GPT

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
