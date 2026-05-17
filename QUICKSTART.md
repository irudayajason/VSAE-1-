# VSAE Quick Start Guide

## Prerequisites

- Python 3.10 or higher
- 16GB RAM minimum (Apple Silicon M1/M2/M3 or CUDA GPU recommended)
- ~10GB disk space for Phi-2 model

## Installation

### Option 1: Automated Setup (Recommended)

```bash
./setup.sh
```

This will:
- Create a virtual environment
- Install all dependencies
- Create a `.env` file from template

### Option 2: Manual Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
```

## Configuration

### Hindsight API Key (Optional but Recommended)

Hindsight provides ablation history tracking and overlap detection to prevent model degradation.

1. Get your API key from [https://hindsight.dev](https://hindsight.dev)
2. Edit `.env` and add your key:
   ```
   HINDSIGHT_API_KEY=your_actual_api_key_here
   ```

**Note:** The application will work without Hindsight, but you'll lose:
- Semantic overlap detection between ablations
- Historical ablation tracking
- Perplexity degradation warnings

## Running the Application

### Start the Server

```bash
# Make sure virtual environment is activated
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Start the server
uvicorn backend.main:app --reload
```

The server will start on `http://localhost:8000`

### Access the UI

Open your browser and navigate to:
```
http://localhost:8000
```

## Features

### 1. Ablation Engine

**What it does:** Surgically removes specific concepts from Phi-2's weights using orthogonal projection.

**How to use:**
1. Click the lightning bolt icon to open the Ablation Engine
2. Enter the concept to forget (e.g., "Harry Potter lives at 4 Privet Drive")
3. Choose target layers (5 recommended)
4. Choose ablation strength (1.0 recommended)
5. Click "Run Ablation"

**With Hindsight enabled:**
- System checks for semantic overlap with past ablations
- Warns if new ablation might degrade model performance
- You can proceed anyway or cancel

### 2. CascadeFlow (Automatic Recovery)

**What it does:** Automatically retries ablation with shifted layers if perplexity degrades too much.

**How to enable:**
Add `cascade_threshold` to your ablation request:

```json
{
  "forget_text": "Harry Potter",
  "top_k_layers": 5,
  "ablation_strength": 1.0,
  "cascade_threshold": 15.0
}
```

**How it works:**
1. Performs initial ablation
2. Checks perplexity degradation
3. If degradation > 15%, automatically:
   - Rolls back the ablation
   - Tries layers shifted by -2
   - If that fails, tries layers shifted by +2
4. Keeps the best result or reports failure

### 3. Probe the Model

**What it does:** Test what Phi-2 knows before and after ablation.

**How to use:**
1. Type a question in the chat input
2. Press Enter or click Send
3. The model generates a response

**Guardrails:**
- Semantic similarity check prevents ablated concepts from leaking
- Quality gate catches garbled output
- Returns "I have no information on that topic" for blocked queries

### 4. Rollback

**What it does:** Instantly restores original weights.

**How to use:**
- Click "Rollback to Original Weights" in the Ablation Engine drawer

## API Endpoints

### Health Check
```bash
curl http://localhost:8000/health
```

### Run Ablation
```bash
curl -X POST http://localhost:8000/ablate \
  -H "Content-Type: application/json" \
  -d '{
    "forget_text": "Harry Potter lives at 4 Privet Drive",
    "top_k_layers": 5,
    "ablation_strength": 1.0,
    "cascade_threshold": 15.0
  }'
```

### Probe Model
```bash
curl -X POST http://localhost:8000/probe \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Where does Harry Potter live?",
    "max_tokens": 100,
    "temperature": 0.4
  }'
```

### List Active Ablations
```bash
curl http://localhost:8000/ablations
```

### Rollback Ablation
```bash
curl -X POST http://localhost:8000/rollback \
  -H "Content-Type: application/json" \
  -d '{
    "ablation_id": "your-ablation-id-here"
  }'
```

## Troubleshooting

### "Hindsight client not available"
- Install: `pip install hindsight-client`
- Or ignore if you don't need ablation history tracking

### "Model loading failed"
- Ensure you have 16GB+ RAM
- Check internet connection (first run downloads ~5GB model)
- Try: `python3 test_mps.py` to verify PyTorch setup

### "Ablation was too aggressive"
- Reduce `top_k_layers` to 3
- Reduce `ablation_strength` to 0.8
- Enable CascadeFlow with `cascade_threshold: 15.0`

### Port already in use
```bash
# Use a different port
uvicorn backend.main:app --reload --port 8001
```

## Best Practices

1. **Start Conservative:** Use 5 layers at strength 1.0
2. **Enable CascadeFlow:** Set `cascade_threshold: 15.0` for automatic recovery
3. **Use Hindsight:** Prevents overlapping ablations that degrade the model
4. **Test Before/After:** Always probe the model to verify ablation worked
5. **Rollback if Needed:** Don't hesitate to rollback and try different parameters

## Architecture

- **Backend:** FastAPI + PyTorch
- **Model:** Microsoft Phi-2 (2.7B parameters)
- **Frontend:** Vanilla HTML/CSS/JS with Three.js
- **Memory:** Hindsight SDK for ablation history

## Support

For issues or questions:
- Check `HINDSIGHT_INTEGRATION.md` for Hindsight details
- Review `Literature.md` for research background
- See `README.md` for project overview

## License

MIT License - see LICENSE file for details