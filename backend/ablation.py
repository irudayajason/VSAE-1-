"""
Ablation Engine — applies orthogonal projection to erase a concept
from the model's weight matrices.

KEY INSIGHT: Each transformer layer encodes a concept in a different
direction. We must use LAYER-SPECIFIC forget vectors extracted from
the hidden state at each layer, not a single global vector.

Formula:  W_new = W - alpha * (W · v · vᵀ) / (vᵀ · v)

Phi-2 uses nn.Linear: W shape [out_dim, in_dim]

Optimizations:
  - Alpha decay: deeper layers get reduced alpha to preserve grammar
  - Immediate float16 cast-back after float32 projection math
  - Efficient in-place tensor operations where safe
"""

import torch
import hashlib
import uuid
from typing import Dict, List, Optional
from datetime import datetime, timezone
import logging

from backend.embedding import load_model, get_target_weights

logger = logging.getLogger(__name__)

# ── Storage for rollback ───────────────────────────────
_weight_backups: Dict[str, Dict[str, torch.Tensor]] = {}
_ablation_metadata: Dict[str, dict] = {}


def _weight_hash(tensor: torch.Tensor) -> str:
    """Compute a short hash of a weight tensor for verification."""
    data = tensor.detach().cpu().float().numpy().tobytes()[:4096]
    return hashlib.sha256(data).hexdigest()[:16]


def apply_projection(
    W: torch.Tensor,
    v: torch.Tensor,
    alpha: float = 1.0,
) -> torch.Tensor:
    """
    Applies orthogonal projection to remove the component of W
    along direction v.

    For nn.Linear layout (Phi-2):   W shape [out_dim, in_dim]
        W_new = W - alpha * (W v) vᵀ / (vᵀ v)

    With a normalized unit vector v (vᵀv = 1):
        W_new = W - alpha * outer(W @ v, v)

    alpha=1.0 = exact orthogonal projection (remove direction completely)
    alpha>1.0 = over-project (more aggressive erasure, may hurt neighbors)

    NOTE: All math is done in float32 for numerical precision, then
    the result is IMMEDIATELY cast back to the original dtype (float16)
    to prevent memory thrashing from accumulating float32 tensors.
    """
    orig_dtype = W.dtype
    # Upcast to float32 for numerical precision — float16 loses too much
    W_f32 = W.float()
    v_f32 = v.to(W.device).float().flatten()

    v_norm_sq = torch.dot(v_f32, v_f32)
    if v_norm_sq < 1e-10:
        logger.warning("Forget vector has near-zero norm, skipping projection")
        return W

    # nn.Linear: W is [out_dim, in_dim]
    # Project out v from the input dimension (dim 1)
    Wv = torch.mv(W_f32, v_f32)          # [out_dim]
    outer = torch.outer(Wv, v_f32)       # [out_dim, in_dim]
    W_new = W_f32 - alpha * outer / v_norm_sq

    # IMMEDIATELY cast back to original dtype (float16) to prevent
    # memory thrashing from holding multiple float32 weight copies
    return W_new.to(orig_dtype)


def _compute_layer_alpha(
    alpha: float,
    layer_idx: int,
    target_layers: List[int],
    total_model_layers: int = 32,
) -> float:
    """
    Implements alpha decay: deeper layers get reduced alpha to preserve
    the model's grammatical and linguistic capabilities.

    The early layers identify concepts ("This is about Apple/Tim Cook"),
    and the late layers format grammar and sentence structure. Ablating
    late layers at full strength destroys the model's ability to produce
    coherent English.

    Strategy:
      - Sort target layers by index
      - The earliest half of selected layers get full alpha
      - The later half get linearly decaying alpha down to 60% of original
      - The very last layer in the selection gets the minimum (60%)

    Example with alpha=1.0 and layers [5, 10, 15, 20, 25]:
      Layer 5:  alpha=1.0   (full)
      Layer 10: alpha=1.0   (full — still in early half)
      Layer 15: alpha=0.9   (start of decay)
      Layer 20: alpha=0.8   (deeper decay)
      Layer 25: alpha=0.6   (minimum — preserves grammar)
    """
    sorted_layers = sorted(target_layers)
    num_targets = len(sorted_layers)

    if num_targets <= 1:
        return alpha

    position = sorted_layers.index(layer_idx)
    midpoint = num_targets // 2

    if position < midpoint:
        # Early layers: full alpha
        return alpha
    else:
        # Late layers: linear decay from 100% down to 60%
        decay_range = num_targets - midpoint
        decay_position = position - midpoint
        decay_factor = 1.0 - (0.4 * decay_position / max(decay_range - 1, 1))
        decayed_alpha = alpha * max(decay_factor, 0.6)

        logger.info(
            f"Alpha decay: layer {layer_idx} (position {position}/{num_targets}) "
            f"→ alpha {alpha:.2f} * {decay_factor:.2f} = {decayed_alpha:.2f}"
        )
        return decayed_alpha


def ablate(
    layer_forget_vectors: Dict[int, torch.Tensor],
    target_layers: List[Dict],
    alpha: float = 1.0,
) -> dict:
    """
    Main ablation function — applies orthogonal projection to target layers
    using LAYER-SPECIFIC forget vectors with alpha decay.

    Args:
        layer_forget_vectors: Dict mapping layer_index -> forget vector for that layer.
                              Each vector is the concept's direction in that layer's space.
        target_layers: List of dicts with layer_index, target_matrices.
        alpha: Base projection strength. 1.0 = exact removal, >1.0 = aggressive.
               Alpha is automatically decayed for deeper layers to preserve grammar.
    """
    model, tokenizer, device = load_model()

    ablation_id = str(uuid.uuid4())
    backup = {}
    layer_results = []

    # Extract all target layer indices for alpha decay computation
    all_target_indices = sorted([l["layer_index"] for l in target_layers])
    total_model_layers = model.config.num_hidden_layers

    for layer_info in target_layers:
        layer_idx = layer_info["layer_index"]
        target_matrices = layer_info.get("target_matrices", ["W_Q", "W_K", "W_V"])

        # Get the layer-specific forget vector
        if layer_idx not in layer_forget_vectors:
            logger.warning(f"No forget vector for layer {layer_idx}, skipping")
            continue

        # Compute decayed alpha for this layer's depth
        layer_alpha = _compute_layer_alpha(
            alpha, layer_idx, all_target_indices, total_model_layers
        )

        forget_v = layer_forget_vectors[layer_idx]
        weights = get_target_weights(model, layer_idx, target_matrices)

        for weight_name, weight_param in weights.items():
            backup_key = f"layer_{layer_idx}_{weight_name}"
            backup[backup_key] = weight_param.data.clone()

            original_hash = _weight_hash(weight_param.data)

            with torch.no_grad():
                # Use the LAYER-SPECIFIC forget vector with DECAYED alpha
                new_weight = apply_projection(weight_param.data, forget_v, layer_alpha)
                weight_param.data.copy_(new_weight)

            modified_hash = _weight_hash(weight_param.data)

            layer_results.append({
                "layer": layer_idx,
                "matrix": weight_name,
                "alpha_used": round(layer_alpha, 3),
                "original_hash": original_hash,
                "modified_hash": modified_hash,
                "changed": original_hash != modified_hash
            })

            logger.info(
                f"Layer {layer_idx} {weight_name} (alpha={layer_alpha:.2f}): "
                f"{original_hash} -> {modified_hash} "
                f"({'CHANGED' if original_hash != modified_hash else 'UNCHANGED'})"
            )

    # Store backup
    _weight_backups[ablation_id] = backup
    metadata = {
        "ablation_id": ablation_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "targeted_layers": [l["layer_index"] for l in target_layers],
        "layer_results": layer_results,
        "status": "success",
        "alpha": alpha,
        "alpha_decay": "enabled",
        "correctness_check": all(r["changed"] for r in layer_results)
    }
    _ablation_metadata[ablation_id] = metadata

    logger.info(f"Ablation {ablation_id} complete — {len(layer_results)} matrices modified (alpha decay enabled)")
    return metadata


def rollback(ablation_id: str) -> dict:
    """Restores the original weights from before an ablation."""
    if ablation_id not in _weight_backups:
        raise ValueError(f"No backup found for ablation_id: {ablation_id}")

    model, tokenizer, device = load_model()
    backup = _weight_backups[ablation_id]

    restored = []
    for backup_key, original_weight in backup.items():
        parts = backup_key.split("_")
        layer_idx = int(parts[1])
        weight_name = "_".join(parts[2:])

        weights = get_target_weights(model, layer_idx, [weight_name])
        with torch.no_grad():
            weights[weight_name].data.copy_(original_weight)

        restored.append({"layer": layer_idx, "matrix": weight_name})
        logger.info(f"Restored {backup_key}")

    del _weight_backups[ablation_id]
    del _ablation_metadata[ablation_id]

    return {
        "ablation_id": ablation_id,
        "status": "rolled_back",
        "restored_matrices": restored,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def get_active_ablations() -> List[dict]:
    """Returns metadata for all active (non-rolled-back) ablations."""
    return list(_ablation_metadata.values())
