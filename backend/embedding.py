import torch
from transformers import GPT2LMHeadModel, GPT2Tokenizer
from typing import Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Global model cache ─────────────────────────────────
# We load the model once and reuse it
_model: Optional[GPT2LMHeadModel] = None
_tokenizer: Optional[GPT2Tokenizer] = None
_device: Optional[torch.device] = None


def get_device() -> torch.device:
    """Returns the best available device (MPS, CUDA, or CPU)"""
    if torch.backends.mps.is_available():
        return torch.device("mps")
    elif torch.cuda.is_available():
        return torch.device("cuda")
    else:
        return torch.device("cpu")


def load_model(model_name: str = "gpt2"):
    """
    Loads GPT-2 model and tokenizer into memory.
    Only loads once — reuses if already loaded.
    """
    global _model, _tokenizer, _device

    if _model is not None:
        logger.info("Model already loaded, reusing.")
        return _model, _tokenizer, _device

    logger.info(f"Loading {model_name}...")
    _device = get_device()

    _tokenizer = GPT2Tokenizer.from_pretrained(model_name)
    _tokenizer.pad_token = _tokenizer.eos_token

    _model = GPT2LMHeadModel.from_pretrained(
        model_name,
        output_hidden_states=True
    ).to(_device)

    _model.eval()
    logger.info(f"Model loaded on {_device}")
    return _model, _tokenizer, _device


def normalize_vector(v: torch.Tensor) -> torch.Tensor:
    """
    Normalizes vector v to unit length.
    This is required before passing to the Ablation Engine.
    """
    norm = torch.norm(v)
    if norm < 1e-8:
        raise ValueError("Vector norm is too small to normalize safely.")
    return v / norm


def get_forget_vector(forget_text: str, model_name: str = "gpt2") -> torch.Tensor:
    """
    Main function — converts forget_text into forget vector v.

    Steps:
    1. Tokenize the input text
    2. Run a forward pass through GPT-2
    3. Extract the last hidden state
    4. Average across all token positions
    5. Normalize to unit length

    Returns:
        v: Tensor of shape [hidden_dim] (768 for GPT-2)
    """
    model, tokenizer, device = load_model(model_name)

    # Step 1 — Tokenize
    inputs = tokenizer(
        forget_text,
        return_tensors="pt",
        truncation=True,
        max_length=512,
        padding=True
    ).to(device)

    logger.info(f"Tokenized input: {inputs['input_ids'].shape[1]} tokens")

    # Step 2 — Forward pass (no gradient needed)
    with torch.no_grad():
        outputs = model(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            output_hidden_states=True
        )

    # Step 3 — Extract last hidden state
    # Shape: [batch_size, sequence_length, hidden_dim]
    last_hidden_state = outputs.hidden_states[-1]

    # Step 4 — Average across all token positions
    # Shape becomes: [hidden_dim] (768 for GPT-2)
    attention_mask = inputs["attention_mask"].unsqueeze(-1).float()
    sum_hidden = (last_hidden_state * attention_mask).sum(dim=1)
    count = attention_mask.sum(dim=1)
    v = (sum_hidden / count).squeeze(0)

    logger.info(f"Forget vector shape: {v.shape}")
    logger.info(f"Forget vector norm (before normalize): {torch.norm(v).item():.4f}")

    # Step 5 — Normalize
    v = normalize_vector(v)
    logger.info(f"Forget vector norm (after normalize): {torch.norm(v).item():.4f}")

    return v


def get_model_info() -> dict:
    """Returns info about the currently loaded model"""
    model, tokenizer, device = load_model()
    return {
        "model": "gpt2",
        "device": str(device),
        "hidden_dim": model.config.hidden_size,
        "num_layers": model.config.num_hidden_layers,
        "vocab_size": model.config.vocab_size,
        "parameters": sum(p.numel() for p in model.parameters())
    }