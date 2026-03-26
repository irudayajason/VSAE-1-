"""
Embedding Module — handles model loading, forget vector extraction, and text generation.

Supports multiple model architectures:
- GPT-2 family (gpt2, gpt2-medium, gpt2-large, gpt2-xl)
- Phi-2 (microsoft/phi-2)
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from typing import Optional, Dict
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Global model cache ─────────────────────────────────
_model: Optional[AutoModelForCausalLM] = None
_tokenizer: Optional[AutoTokenizer] = None
_device: Optional[torch.device] = None
_current_model_name: Optional[str] = None


# ── Model Architecture Registry ───────────────────────
# Defines how to access layers/attention for each model type
MODEL_REGISTRY = {
    "gpt2": {
        "display_name": "GPT-2 (117M)",
        "family": "gpt2",
    },
    "gpt2-medium": {
        "display_name": "GPT-2 Medium (355M)",
        "family": "gpt2",
    },
    "gpt2-large": {
        "display_name": "GPT-2 Large (774M)",
        "family": "gpt2",
    },
    "gpt2-xl": {
        "display_name": "GPT-2 XL (1.5B)",
        "family": "gpt2",
    },
    "microsoft/phi-2": {
        "display_name": "Phi-2 (2.7B)",
        "family": "phi",
    },
}


def get_model_family(model_name: str) -> str:
    """Returns the architecture family for a model name."""
    if model_name in MODEL_REGISTRY:
        return MODEL_REGISTRY[model_name]["family"]
    # Fallback: guess from model type after loading
    if "phi" in model_name.lower():
        return "phi"
    return "gpt2"


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
    Loads model and tokenizer into memory.
    Handles model switching — if a different model is requested,
    unloads the old one first (important for 16GB RAM).
    """
    global _model, _tokenizer, _device, _current_model_name

    if _model is not None and _current_model_name == model_name:
        logger.info("Model already loaded, reusing.")
        return _model, _tokenizer, _device

    # Unload previous model if different
    if _model is not None and _current_model_name != model_name:
        logger.info(f"Switching model: {_current_model_name} → {model_name}")
        del _model
        del _tokenizer
        _model = None
        _tokenizer = None
        torch.mps.empty_cache() if torch.backends.mps.is_available() else None
        import gc; gc.collect()

    logger.info(f"Loading {model_name}...")
    _device = get_device()

    _tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if _tokenizer.pad_token is None:
        _tokenizer.pad_token = _tokenizer.eos_token

    _model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float32,
        trust_remote_code=True,
        output_hidden_states=True
    ).to(_device)

    _model.eval()
    _current_model_name = model_name
    logger.info(f"Model {model_name} loaded on {_device}")
    return _model, _tokenizer, _device


def get_transformer_layers(model):
    """Returns the list of transformer layers regardless of architecture."""
    family = get_model_family(_current_model_name or "gpt2")

    if family == "gpt2":
        return model.transformer.h
    elif family == "phi":
        return model.model.layers
    else:
        raise ValueError(f"Unsupported model family: {family}")


def get_attention_module(layer, model_name: str = None):
    """Returns the attention module from a transformer layer."""
    family = get_model_family(model_name or _current_model_name or "gpt2")

    if family == "gpt2":
        return layer.attn
    elif family == "phi":
        return layer.self_attn
    else:
        raise ValueError(f"Unsupported model family: {family}")


def get_qkv_weights(model, layer_idx: int, model_name: str = None) -> Dict[str, torch.nn.Parameter]:
    """
    Returns the QKV weight parameters for a given layer.

    GPT-2:  Combined c_attn [in, 3*out] — Conv1D (weight layout: [in_dim, out_dim])
    Phi-2:  Separate q_proj, k_proj, v_proj — nn.Linear (weight layout: [out_dim, in_dim])
    """
    family = get_model_family(model_name or _current_model_name or "gpt2")
    layers = get_transformer_layers(model)
    layer = layers[layer_idx]

    if family == "gpt2":
        return {"c_attn": layer.attn.c_attn.weight}
    elif family == "phi":
        return {
            "q_proj": layer.self_attn.q_proj.weight,
            "k_proj": layer.self_attn.k_proj.weight,
            "v_proj": layer.self_attn.v_proj.weight,
        }
    else:
        raise ValueError(f"Unsupported model family: {family}")


def get_weight_layout(model_name: str = None) -> str:
    """
    Returns the weight matrix layout convention.

    'conv1d' → shape [in_dim, out_dim]  (GPT-2)
    'linear' → shape [out_dim, in_dim]  (Phi-2, most modern models)
    """
    family = get_model_family(model_name or _current_model_name or "gpt2")
    if family == "gpt2":
        return "conv1d"
    return "linear"


def normalize_vector(v: torch.Tensor) -> torch.Tensor:
    """Normalizes vector v to unit length."""
    norm = torch.norm(v)
    if norm < 1e-8:
        raise ValueError("Vector norm is too small to normalize safely.")
    return v / norm


def get_forget_vector(forget_text: str, model_name: str = "gpt2") -> torch.Tensor:
    """
    Converts forget_text into a forget vector v.

    Steps:
    1. Tokenize the input text
    2. Run a forward pass
    3. Extract the last hidden state
    4. Average across all token positions → shape [hidden_dim]
    5. Normalize to unit length

    Returns:
        v: Tensor of shape [hidden_dim]
    """
    model, tokenizer, device = load_model(model_name)

    inputs = tokenizer(
        forget_text,
        return_tensors="pt",
        truncation=True,
        max_length=512,
        padding=True
    ).to(device)

    logger.info(f"Tokenized input: {inputs['input_ids'].shape[1]} tokens")

    with torch.no_grad():
        outputs = model(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            output_hidden_states=True
        )

    # Extract last hidden state: [batch, seq_len, hidden_dim]
    last_hidden_state = outputs.hidden_states[-1]

    # Average across token positions → [hidden_dim]
    attention_mask = inputs["attention_mask"].unsqueeze(-1).float()
    sum_hidden = (last_hidden_state * attention_mask).sum(dim=1)
    count = attention_mask.sum(dim=1)
    v = (sum_hidden / count).squeeze(0)

    logger.info(f"Forget vector shape: {v.shape}")
    logger.info(f"Forget vector norm (before normalize): {torch.norm(v).item():.4f}")

    v = normalize_vector(v)
    logger.info(f"Forget vector norm (after normalize): {torch.norm(v).item():.4f}")

    return v


def generate_text(
    prompt: str,
    max_tokens: int = 100,
    temperature: float = 0.5,
    model_name: str = "gpt2"
) -> str:
    """
    Generates text from the model given a prompt.
    Formats the prompt as Q&A for better coherence.
    """
    model, tokenizer, device = load_model(model_name)

    formatted_prompt = f"Question: {prompt}\nAnswer:"

    inputs = tokenizer(
        formatted_prompt,
        return_tensors="pt",
        truncation=True,
        max_length=512
    ).to(device)

    with torch.no_grad():
        output_ids = model.generate(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            max_new_tokens=max_tokens,
            do_sample=True,
            temperature=temperature,
            top_k=50,
            top_p=0.9,
            repetition_penalty=1.3,
            pad_token_id=tokenizer.eos_token_id
        )

    generated = tokenizer.decode(
        output_ids[0][inputs["input_ids"].shape[1]:],
        skip_special_tokens=True
    ).strip()

    # Stop at the first "Question:" if model generates another Q&A pair
    if "Question:" in generated:
        generated = generated.split("Question:")[0].strip()

    logger.info(f"Generated {len(generated)} chars from prompt '{prompt[:40]}...'")
    return generated


def complete_text(
    prefix: str,
    max_tokens: int = 40,
    model_name: str = "gpt2"
) -> str:
    """
    Pure text completion — no Q&A formatting.
    Used for before/after comparison in ablation proof.

    Example: complete_text("Harry Potter lives at") → "4 Privet Drive..."
    """
    model, tokenizer, device = load_model(model_name)

    inputs = tokenizer(
        prefix,
        return_tensors="pt",
        truncation=True,
        max_length=256
    ).to(device)

    with torch.no_grad():
        output_ids = model.generate(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            max_new_tokens=max_tokens,
            do_sample=False,  # Greedy — deterministic for fair comparison
            pad_token_id=tokenizer.eos_token_id
        )

    generated = tokenizer.decode(
        output_ids[0][inputs["input_ids"].shape[1]:],
        skip_special_tokens=True
    ).strip()

    logger.info(f"Completed '{prefix[:30]}...' → '{generated[:50]}...'")
    return generated


def get_model_info() -> dict:
    """Returns info about the currently loaded model."""
    model, tokenizer, device = load_model()
    return {
        "model": _current_model_name or "gpt2",
        "device": str(device),
        "hidden_dim": model.config.hidden_size,
        "num_layers": model.config.num_hidden_layers,
        "vocab_size": model.config.vocab_size,
        "parameters": sum(p.numel() for p in model.parameters()),
        "family": get_model_family(_current_model_name or "gpt2"),
        "available_models": {k: v["display_name"] for k, v in MODEL_REGISTRY.items()}
    }