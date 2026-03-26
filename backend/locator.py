"""
Subspace Locator — finds which transformer layers are most activated
by the forget text, so we know WHERE to apply the ablation.

Supports GPT-2 family and Phi-2 architectures via the embedding
module's architecture helpers.
"""

import torch
from typing import List, Dict
import logging

from backend.embedding import load_model, get_transformer_layers, get_attention_module

logger = logging.getLogger(__name__)


def trace_activations(
    forget_text: str,
    model_name: str = "gpt2"
) -> Dict[int, float]:
    """
    Runs the forget text through the model and records the activation
    magnitude at every attention layer.

    Returns:
        Dict mapping layer_index -> activation_magnitude (float)
    """
    model, tokenizer, device = load_model(model_name)

    inputs = tokenizer(
        forget_text,
        return_tensors="pt",
        truncation=True,
        max_length=512,
        padding=True
    ).to(device)

    activation_scores: Dict[int, float] = {}
    hooks = []

    # Hook into every attention layer
    layers = get_transformer_layers(model)
    for layer_idx, block in enumerate(layers):
        attn_module = get_attention_module(block, model_name)

        def make_hook(idx):
            def hook_fn(module, input, output):
                if isinstance(output, tuple):
                    act = output[0]
                else:
                    act = output
                activation_scores[idx] = act.float().norm().item()
            return hook_fn

        h = attn_module.register_forward_hook(make_hook(layer_idx))
        hooks.append(h)

    # Forward pass
    with torch.no_grad():
        model(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"]
        )

    # Remove hooks
    for h in hooks:
        h.remove()

    logger.info(f"Activation scores across {len(activation_scores)} layers:")
    for idx, score in sorted(activation_scores.items()):
        logger.info(f"  Layer {idx}: {score:.4f}")

    return activation_scores


def find_target_layers(
    forget_text: str,
    top_k: int = 3,
    model_name: str = "gpt2"
) -> List[Dict]:
    """
    Finds the top-K layers most activated by the forget text.

    Returns:
        List of dicts with layer_index, activation_score, target_matrices
    """
    scores = trace_activations(forget_text, model_name)

    sorted_layers = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_layers = sorted_layers[:top_k]

    results = []
    for layer_idx, score in top_layers:
        results.append({
            "layer_index": layer_idx,
            "activation_score": round(score, 4),
            "target_matrices": ["W_Q", "W_K", "W_V"]
        })

    logger.info(f"Top-{top_k} target layers: {[r['layer_index'] for r in results]}")
    return results
