"""
Ablation Engine — applies orthogonal projection to erase a concept
from the model's weight matrices.

KEY INSIGHT: Each transformer layer encodes a concept in a different
direction. We must use LAYER-SPECIFIC forget vectors extracted from
the hidden state at each layer, not a single global vector.

Formula:  W_new = W - alpha * (W · v · vᵀ) / (vᵀ · v)

Phi-2 uses nn.Linear: W shape [out_dim, in_dim]
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
    """
    v = v.to(W.device).to(W.dtype).flatten()

    v_norm_sq = torch.dot(v, v)
    if v_norm_sq < 1e-10:
        logger.warning("Forget vector has near-zero norm, skipping projection")
        return W

    # nn.Linear: W is [out_dim, in_dim]
    # Project out v from the input dimension (dim 1)
    Wv = torch.mv(W, v)             # [out_dim]
    outer = torch.outer(Wv, v)      # [out_dim, in_dim]
    W_new = W - alpha * outer / v_norm_sq

    return W_new


def ablate(
    layer_forget_vectors: Dict[int, torch.Tensor],
    target_layers: List[Dict],
    alpha: float = 1.0,
) -> dict:
    """
    Main ablation function — applies orthogonal projection to target layers
    using LAYER-SPECIFIC forget vectors.

    Args:
        layer_forget_vectors: Dict mapping layer_index -> forget vector for that layer.
                              Each vector is the concept's direction in that layer's space.
        target_layers: List of dicts with layer_index, target_matrices.
        alpha: Projection strength. 1.0 = exact removal, >1.0 = aggressive.
    """
    model, tokenizer, device = load_model()

    ablation_id = str(uuid.uuid4())
    backup = {}
    layer_results = []

    for layer_info in target_layers:
        layer_idx = layer_info["layer_index"]
        target_matrices = layer_info.get("target_matrices", ["W_Q", "W_K", "W_V"])

        # Get the layer-specific forget vector
        if layer_idx not in layer_forget_vectors:
            logger.warning(f"No forget vector for layer {layer_idx}, skipping")
            continue

        forget_v = layer_forget_vectors[layer_idx]
        weights = get_target_weights(model, layer_idx, target_matrices)

        for weight_name, weight_param in weights.items():
            backup_key = f"layer_{layer_idx}_{weight_name}"
            backup[backup_key] = weight_param.data.clone()

            original_hash = _weight_hash(weight_param.data)

            with torch.no_grad():
                # Use the LAYER-SPECIFIC forget vector
                new_weight = apply_projection(weight_param.data, forget_v, alpha)
                weight_param.data.copy_(new_weight)

            modified_hash = _weight_hash(weight_param.data)

            layer_results.append({
                "layer": layer_idx,
                "matrix": weight_name,
                "original_hash": original_hash,
                "modified_hash": modified_hash,
                "changed": original_hash != modified_hash
            })

            logger.info(
                f"Layer {layer_idx} {weight_name}: "
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
        "correctness_check": all(r["changed"] for r in layer_results)
    }
    _ablation_metadata[ablation_id] = metadata

    logger.info(f"Ablation {ablation_id} complete — {len(layer_results)} matrices modified")
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
