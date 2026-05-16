"""
Embedding Module — handles model loading, forget vector extraction, and text generation.

Supports: Phi-2 (microsoft/phi-2) only.

Optimizations:
  - torch.inference_mode() for all read-only passes (faster than no_grad)
  - use_cache=True on all generate() calls for KV caching
  - Tuned generation params for coherent post-ablation output
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from typing import Optional, List, Dict
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Global model cache ─────────────────────────────────
_model: Optional[AutoModelForCausalLM] = None
_tokenizer: Optional[AutoTokenizer] = None
_device: Optional[torch.device] = None

MODEL_ID = "microsoft/phi-2"
MODEL_DISPLAY_NAME = "Phi-2 (2.7B)"


def get_device() -> torch.device:
    """Returns the best available device (MPS, CUDA, or CPU)"""
    if torch.backends.mps.is_available():
        return torch.device("mps")
    elif torch.cuda.is_available():
        return torch.device("cuda")
    else:
        return torch.device("cpu")


def load_model():
    """
    Loads Phi-2 model and tokenizer into memory.
    Uses float16 to reduce memory usage (~5GB instead of ~10GB).
    """
    global _model, _tokenizer, _device

    if _model is not None:
        logger.info("Model already loaded, reusing.")
        return _model, _tokenizer, _device

    logger.info(f"Loading {MODEL_ID} in float16...")
    _device = get_device()

    _tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    if _tokenizer.pad_token is None:
        _tokenizer.pad_token = _tokenizer.eos_token

    _model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        dtype=torch.float16,
        trust_remote_code=True,
    ).to(_device)

    _model.eval()
    logger.info(f"Model {MODEL_ID} loaded on {_device} (float16)")
    return _model, _tokenizer, _device


def get_transformer_layers(model):
    """Returns the list of transformer layers (Phi-2 architecture)."""
    return model.model.layers


def get_attention_module(layer):
    """Returns the attention module from a transformer layer (Phi-2 architecture)."""
    return layer.self_attn


def get_target_weights(model, layer_idx: int, target_matrices: List[str]):
    """
    Returns the explicitly requested weight parameters for a given layer.
    Phi-2 has:
      - Attention: q_proj, k_proj, v_proj, dense
      - MLP: fc1, fc2
    Only matrices where in_features == hidden_size can be projected effectively.
    """
    layers = get_transformer_layers(model)
    layer = layers[layer_idx]

    weights = {}
    if "W_Q" in target_matrices or "q_proj" in target_matrices:
        weights["W_Q"] = layer.self_attn.q_proj.weight
    if "W_K" in target_matrices or "k_proj" in target_matrices:
        weights["W_K"] = layer.self_attn.k_proj.weight
    if "W_V" in target_matrices or "v_proj" in target_matrices:
        weights["W_V"] = layer.self_attn.v_proj.weight
    if "dense" in target_matrices:
        weights["dense"] = layer.self_attn.dense.weight
    if "fc1" in target_matrices:
        weights["fc1"] = layer.mlp.fc1.weight
        
    return weights


def normalize_vector(v: torch.Tensor) -> torch.Tensor:
    """Normalizes vector v to unit length."""
    norm = torch.norm(v)
    if norm < 1e-8:
        raise ValueError("Vector norm is too small to normalize safely.")
    return v / norm


def get_forget_vector(forget_text: str) -> torch.Tensor:
    """
    Converts forget_text into a single global forget vector v (from last hidden state).
    Used for semantic guardrail similarity checking.

    Returns:
        v: Tensor of shape [hidden_dim], normalized to unit length
    """
    model, tokenizer, device = load_model()

    inputs = tokenizer(
        forget_text,
        return_tensors="pt",
        truncation=True,
        max_length=512,
        padding=True
    ).to(device)

    logger.info(f"Tokenized input: {inputs['input_ids'].shape[1]} tokens")

    # inference_mode is strictly faster than no_grad — disables even more
    # autograd tracking overhead that no_grad leaves enabled.
    with torch.inference_mode():
        outputs = model(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            output_hidden_states=True,
            use_cache=False,  # no KV cache needed for single forward pass
        )

    # Extract last hidden state: [batch, seq_len, hidden_dim]
    last_hidden_state = outputs.hidden_states[-1]

    # Average across token positions → [hidden_dim]
    attention_mask = inputs["attention_mask"].unsqueeze(-1).float()
    sum_hidden = (last_hidden_state.float() * attention_mask).sum(dim=1)
    count = attention_mask.sum(dim=1)
    v = (sum_hidden / count).squeeze(0)

    logger.info(f"Forget vector shape: {v.shape}")
    logger.info(f"Forget vector norm (before normalize): {torch.norm(v).item():.4f}")

    v = normalize_vector(v)
    logger.info(f"Forget vector norm (after normalize): {torch.norm(v).item():.4f}")

    return v


def get_layerwise_forget_vectors(forget_text: str) -> Dict[int, torch.Tensor]:
    """
    Extracts a per-layer forget vector for every transformer layer.

    Each layer in the transformer encodes the concept differently.
    hidden_states[i] is the INPUT to layer i (output of layer i-1).
    We use each layer's input hidden state as the forget direction for
    that layer's weight matrices (W_Q, W_K, W_V all take this as input).

    Returns:
        Dict mapping layer_index -> normalized forget vector [hidden_dim]
    """
    model, tokenizer, device = load_model()

    inputs = tokenizer(
        forget_text,
        return_tensors="pt",
        truncation=True,
        max_length=512,
        padding=True
    ).to(device)

    logger.info(f"Extracting per-layer forget vectors for {inputs['input_ids'].shape[1]} tokens")

    with torch.inference_mode():
        outputs = model(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            output_hidden_states=True,
            use_cache=False,
        )

    # outputs.hidden_states is a tuple of (n_layers + 1) tensors:
    #   [0] = embedding output (input to layer 0)
    #   [1] = output of layer 0 (input to layer 1)
    #   ...
    #   [i] = input to layer i
    #   [n] = final hidden state (output of last layer)
    attention_mask = inputs["attention_mask"].unsqueeze(-1).float()

    layer_vectors = {}
    num_layers = len(outputs.hidden_states) - 1  # exclude final output

    for layer_idx in range(num_layers):
        # hidden_states[layer_idx] is the input to layer layer_idx
        hs = outputs.hidden_states[layer_idx]  # [batch, seq_len, hidden_dim]

        # Average across token positions
        sum_hidden = (hs.float() * attention_mask).sum(dim=1)
        count = attention_mask.sum(dim=1)
        v = (sum_hidden / count).squeeze(0)  # [hidden_dim]

        v = normalize_vector(v)
        layer_vectors[layer_idx] = v

    logger.info(f"Extracted {len(layer_vectors)} per-layer forget vectors")
    return layer_vectors


def get_prompt_embedding(prompt: str) -> torch.Tensor:
    """
    Extracts a prompt's embedding vector (same method as get_forget_vector).
    Used for semantic similarity checking in the guardrail.

    Returns:
        v: Tensor of shape [hidden_dim], normalized to unit length
    """
    model, tokenizer, device = load_model()

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=512,
        padding=True
    ).to(device)

    with torch.inference_mode():
        outputs = model(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            output_hidden_states=True,
            use_cache=False,
        )

    last_hidden_state = outputs.hidden_states[-1]
    attention_mask = inputs["attention_mask"].unsqueeze(-1).float()
    sum_hidden = (last_hidden_state.float() * attention_mask).sum(dim=1)
    count = attention_mask.sum(dim=1)
    v = (sum_hidden / count).squeeze(0)

    v = normalize_vector(v)
    return v


def generate_text(
    prompt: str,
    max_tokens: int = 60,
    temperature: float = 0.4,
) -> str:
    """
    Generates text from the model given a prompt.
    Uses Phi-2's QA format for focused, concise answers.
    Includes retry logic for when Phi-2 falls into quiz/exercise mode.

    Generation params are tuned for post-ablation coherence:
      - repetition_penalty=1.2 suppresses degenerate loops
      - temperature=0.4 keeps output deterministic but not greedy
      - top_p=0.9 nucleus sampling for quality
      - use_cache=True for KV caching (avoids re-computing attention for past tokens)
    """
    model, tokenizer, device = load_model()
    import re as _re

    def _generate_once(fmt_prompt: str, temp: float, max_tok: int) -> str:
        inputs = tokenizer(
            fmt_prompt,
            return_tensors="pt",
            truncation=True,
            max_length=512
        ).to(device)

        with torch.inference_mode():
            output_ids = model.generate(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                max_new_tokens=max_tok,
                do_sample=True,
                temperature=max(temp, 0.01),  # clamp to avoid division by zero
                top_k=40,
                top_p=0.9,
                repetition_penalty=1.2,
                pad_token_id=tokenizer.eos_token_id,
                use_cache=True,  # KV caching — critical for latency
            )

        return tokenizer.decode(
            output_ids[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=True
        ).strip()

    def _clean(text: str) -> str:
        """Post-process Phi-2 output to remove common artifacts."""
        # Stop at any new instruction/question block
        for stop_marker in ["Question:", "Instruct:", "Output:", "###", "```", "Exercise", "Answer the following"]:
            if stop_marker in text:
                text = text.split(stop_marker)[0].strip()

        # Remove code blocks that Phi-2 sometimes hallucinates
        text = _re.sub(r'#include\s*<.*', '', text).strip()
        text = _re.sub(r'\b(int|void|char|float|double)\s+\w+\s*\(.*', '', text).strip()

        # Remove "A:" or "Answer:" prefix if present
        text = _re.sub(r'^(A:|Answer:)\s*', '', text).strip()

        # Remove fill-in-the-blank patterns: ____ or ___ (quiz-mode artifact)
        text = _re.sub(r'_{2,}\s*\([^)]*\)', '', text)  # ____(a, b or c)
        text = _re.sub(r'_{2,}', '', text)                # bare ____
        # Clean up leftover double spaces / punctuation gaps
        text = _re.sub(r'\s{2,}', ' ', text).strip()
        text = _re.sub(r'\s+([.,;:!?])', r'\1', text)

        # Remove multiple-choice patterns: (a) ... (b) ... (c) ...
        text = _re.sub(r'\([a-d]\)\s*[^(]*', '', text).strip()

        # Remove numbered list exercise formatting
        text = _re.sub(r'^\d+[\.\\)]\s*', '', text, flags=_re.MULTILINE).strip()

        # Trim trailing incomplete sentences
        sentences = _re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) > 1 and not sentences[-1].rstrip().endswith(('.', '!', '?')):
            sentences = sentences[:-1]
        text = ' '.join(sentences).strip()

        return text

    def _is_bad_output(text: str) -> bool:
        """Check if the output is quiz-mode, blanks, or too short."""
        if len(text) < 5:
            return True
        if _re.search(r'_{2,}', text):
            return True
        if _re.search(r'\([a-d]\)', text):
            return True
        if any(kw in text.lower() for kw in ["fill in", "choose the", "select the", "which of the following"]):
            return True
        return False

    # ── Attempt 1: Phi-2 QA format ────────────────────────────────
    formatted_prompt = (
        f"Write a short factual answer to the question below. "
        f"Do not create exercises, quizzes, or fill-in-the-blank. "
        f"Just answer directly.\n\n"
        f"Q: {prompt}\n"
        f"A:"
    )

    generated = _generate_once(formatted_prompt, temperature, max_tokens)
    generated = _clean(generated)

    # ── Attempt 2: Retry with simpler prompt if output is bad ─────
    if _is_bad_output(generated):
        logger.info(f"Retry: first attempt was bad ('{generated[:60]}...')")
        simple_prompt = f"{prompt}\nThe answer is:"
        generated = _generate_once(simple_prompt, 0.2, max_tokens)
        generated = _clean(generated)

    # Final safety
    if len(generated) < 5:
        generated = "I'm unable to generate a clear response for this query."

    logger.info(f"Generated {len(generated)} chars from prompt '{prompt[:40]}...'")
    return generated


def complete_text(
    prefix: str,
    max_tokens: int = 40,
) -> str:
    """
    Pure text completion — no Q&A formatting.
    Used for before/after comparison in ablation proof.

    Example: complete_text("Harry Potter lives at") → "4 Privet Drive..."
    """
    model, tokenizer, device = load_model()

    inputs = tokenizer(
        prefix,
        return_tensors="pt",
        truncation=True,
        max_length=256
    ).to(device)

    with torch.inference_mode():
        output_ids = model.generate(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            max_new_tokens=max_tokens,
            do_sample=False,  # Greedy — deterministic for fair comparison
            pad_token_id=tokenizer.eos_token_id,
            use_cache=True,  # KV caching for speed
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
        "model": MODEL_ID,
        "display_name": MODEL_DISPLAY_NAME,
        "device": str(device),
        "hidden_dim": model.config.hidden_size,
        "num_layers": model.config.num_hidden_layers,
        "vocab_size": model.config.vocab_size,
        "parameters": sum(p.numel() for p in model.parameters()),
        "dtype": "float16",
    }