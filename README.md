# unlearn.dev

## CI/CD for AI Deletion Requests

Surgical knowledge removal from trained AI models as a developer pipeline utility — turn GDPR Article 17 compliance into a single CLI command.

---

## The Problem

**GDPR Article 17** ("Right to Erasure") and the **EU AI Act** mandate that organizations must be able to delete specific personal data or concepts from AI systems upon request. However, retraining a large language model from scratch costs **$100K–$10M** and takes weeks to months. Fine-tuning approaches are faster but still require significant compute resources and risk catastrophic forgetting of unrelated capabilities.

The industry lacks a **developer-friendly, CI/CD-integrated solution** for surgical concept removal that doesn't require full retraining. Current approaches are either research prototypes (not production-ready) or enterprise black boxes (not accessible to developers). **unlearn.dev** fills this gap by providing a command-line tool and automated compliance pipeline that applies orthogonal projection mathematics to erase concepts from model weights in minutes, not months.

---

## Solution

**unlearn.dev** is a developer pipeline utility that removes specific knowledge from trained AI models without retraining. It works like a linter or formatter in your CI/CD pipeline:

1. **Input**: A concept to forget (e.g., "Harry Potter", "user@email.com", "proprietary algorithm X")
2. **Process**: Automatically identifies which neural network layers encode that concept, applies mathematical projection to erase it
3. **Output**: A compliance report proving the concept was forgotten, with before/after perplexity metrics and evaluation results
4. **Integration**: Runs as a CLI tool locally or as a GitHub Action in your CI/CD pipeline

**Key benefits**:
- ⚡ **Fast**: Minutes instead of weeks of retraining
- 💰 **Cost-effective**: No GPU clusters or cloud compute required
- 🔄 **Reversible**: Instant rollback if something goes wrong
- 📊 **Auditable**: JSON compliance reports for regulatory documentation
- 🧪 **Testable**: Pytest suite verifies mathematical correctness

---

## Architecture

```
┌─────────────────┐
│   Developer     │
│   CLI Command   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│              Ablation Engine Pipeline                    │
│                                                          │
│  1. Load Model (Phi-2)                                  │
│  2. Extract Forget Vectors (per-layer embeddings)       │
│  3. Locate Target Layers (activation tracing)           │
│  4. Apply Orthogonal Projection (W_new = W - α·Wv·vᵀ)  │
│  5. Evaluate Forgetting (perplexity-based retention)    │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│           Compliance Report (JSON)                       │
│                                                          │
│  • Ablation ID & timestamp                              │
│  • Target layers & alpha strength                        │
│  • Pre/post perplexity metrics                          │
│  • Forgetting signal: FORGOTTEN / STILL_KNOWN           │
│  • Before/after text completions                         │
│  • Sanity check results                                  │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│   CI/CD Gate    │
│  (Pass/Fail)    │
└─────────────────┘
```

The pipeline can run locally via `vsae-cli.py` or automatically in GitHub Actions on every commit that modifies training data or model weights.

---

## Open-Source Baseline

**Transparency Statement**: The core mathematical unlearning engine (orthogonal projection, activation tracing, perplexity evaluation) was developed as open-source research infrastructure over 14 weeks as part of an academic project. 

The following production-ready components were built during the **IBM Bob Hackathon sprint** using **IBM Bob as the primary engineering partner**:

- ✅ **CLI tool** (`vsae-cli.py`) — Standalone command-line interface with Rich terminal output
- ✅ **Pytest test suite** (`tests/test_ablation_math.py`) — Mathematical correctness verification without loading real models
- ✅ **Compliance reporting system** — Automated JSON report generation with timestamps and audit trails
- ✅ **CI/CD integration patterns** — GitHub Action workflows and pipeline examples
- ✅ **Developer documentation** — This README, quickstart guides, and API references

**IBM Bob's contributions**: Code generation, test design, architectural review, documentation writing, and debugging assistance. All Bob session transcripts are preserved in `bob_session_*.md` files in the repository root for full transparency.

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the CLI

```bash
# Basic usage
python vsae-cli.py --forget_text "Harry Potter"

# Advanced configuration
python vsae-cli.py \
  --forget_text "Apple Inc CEO Tim Cook" \
  --top_k 5 \
  --alpha 0.8 \
  --force

# Fast mode (skip full evaluation)
python vsae-cli.py \
  --forget_text "Python programming language" \
  --no-evaluation
```

### 3. Read the Compliance Report

Reports are automatically saved to `reports/{timestamp}_{concept_slug}.json`:

```json
{
  "ablation_id": "a1b2c3d4-...",
  "timestamp": "2026-05-17T11:30:00Z",
  "forget_text": "Harry Potter",
  "targeted_layers": [8, 12, 16],
  "pre_perplexity": 12.4,
  "post_perplexity": 156.8,
  "evaluation": {
    "overall_verdict": "FORGOTTEN"
  },
  "proof": {
    "before": "Harry Potter is a wizard who lives at Hogwarts...",
    "after": "I have no information on that topic."
  }
}
```

### 4. Trigger GitHub Action (Coming Soon)

```yaml
# .github/workflows/unlearn.yml
name: AI Deletion Request
on:
  push:
    paths:
      - 'deletion_requests/*.txt'

jobs:
  unlearn:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run unlearn.dev
        run: |
          python vsae-cli.py --forget_text "$(cat deletion_requests/latest.txt)"
      - name: Upload compliance report
        uses: actions/upload-artifact@v3
        with:
          name: compliance-report
          path: reports/*.json
```

---

## Research Foundation

**unlearn.dev** is the first developer-facing CI/CD implementation of recent breakthroughs in neural network concept erasure:

- **EMNLP 2025**: *PISCES: Precise In-Parameter Subspace Concept Erasure* — Demonstrates that concepts can be surgically removed from transformer layers using orthogonal projection without catastrophic forgetting
- **NeurIPS 2025**: *Semantic Surgery: Editing Knowledge in Language Models via Activation Steering* — Shows that activation tracing can identify which layers encode specific concepts

While these papers provide the mathematical foundation, they remain research prototypes. **unlearn.dev** bridges the gap to production by providing:
- A CLI tool that developers can actually use
- Automated compliance reporting for regulatory audits
- CI/CD integration patterns for continuous deployment
- Comprehensive test coverage for mathematical correctness

**Citation**: If you use this tool in research, please cite the original PISCES and Semantic Surgery papers along with this implementation.

---

## Testing

Run the test suite to verify mathematical correctness:

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_ablation_math.py -v

# Run with coverage
python -m pytest tests/ --cov=backend --cov-report=html
```

All tests use synthetic tensors and mocked models — **no real model loading required**.

---

## IBM Bob Session Logs

Full transparency: All IBM Bob engineering sessions during the hackathon sprint are documented in the repository root:

- `bob_session_cli.md` — CLI tool development
- `bob_session_tests.md` — Test suite creation
- `bob_session_docs.md` — Documentation writing
- `bob_session_debugging.md` — Bug fixes and optimizations

These logs contain the complete conversation history, including prompts, code generation, and iterative refinement. They serve as both a development audit trail and a case study in AI-assisted software engineering.

---

## Project Structure

```
unlearn.dev/
├── backend/              # Core ablation engine
│   ├── ablation.py      # Orthogonal projection logic
│   ├── embedding.py     # Forget vector extraction
│   ├── locator.py       # Layer identification
│   ├── evaluate.py      # Perplexity evaluation
│   └── main.py          # FastAPI server (optional)
├── frontend/            # Web UI (optional)
├── tests/               # Pytest test suite
│   └── test_ablation_math.py
├── reports/             # Compliance reports (auto-generated)
├── vsae-cli.py          # Standalone CLI tool
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

---

## API Endpoints (Optional Web Server)

If you prefer a web API over the CLI, start the FastAPI server:

```bash
uvicorn backend.main:app --reload
```

Available endpoints:
- `POST /ablate` — Run full ablation pipeline
- `POST /evaluate` — Generate compliance report
- `POST /rollback` — Reverse an ablation
- `GET /ablations` — List active ablations
- `GET /health` — System status

---

## Roadmap

- [x] Core ablation engine (orthogonal projection)
- [x] CLI tool with Rich terminal output
- [x] Pytest test suite (no model loading)
- [x] Compliance report generation
- [ ] GitHub Action for CI/CD integration
- [ ] Support for additional models (GPT-2, LLaMA)
- [ ] Distributed ablation for large models
- [ ] Real-time monitoring dashboard
- [ ] Enterprise SSO integration

---

## Team

| Member | Role | Hardware |
|--------|------|----------|
| Irudaya Jason J | Ablation Engine + FastAPI | MacBook M4 Air (MPS) |
| Mithun A | Literature Research + Embedding Module | Intel Core Ultra i5 125H |
| Mohammed Nahyan Khan | GPU Testing + Frontend | Intel i7 13th Gen + RTX 4050 |

**IBM Bob**: AI engineering partner for CLI, testing, and documentation during hackathon sprint.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Disclaimer

This tool manipulates neural network weights in memory. While designed to be safe and reversible, applying too many overlapping ablations or using extreme strengths may degrade model performance. Always test on a development model before production deployment.

**Regulatory Note**: This tool provides technical capability for concept erasure but does not constitute legal advice. Consult with legal counsel to ensure compliance with GDPR, EU AI Act, and other applicable regulations.

---

*Built for surgical AI control and regulatory compliance.*
