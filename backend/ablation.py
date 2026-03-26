"""
Ablation Engine — applies orthogonal projection to erase a concept
from the model's weight matrices.

Formula:  W_new = W - (W · v · vᵀ) / (vᵀ · v)

Handles both weight layouts:
- GPT-2 Conv1D: W shape [in_dim, out_dim]
- Phi-2 nn.Linear: W shape [out_dim, in_dim]
"""

import torch
import hashlib
import uuid
from typing import Dict, List
from datetime import datetime, timezone
import logging

from backend.embedding import load_model, get_qkv_weights, get_weight_layout

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
    layout: str = "conv1d"
) -> torch.Tensor:
    """
    Applies orthogonal projection to remove the component of W
    along direction v.

    For Conv1D layout (GPT-2):   W shape [in_dim, out_dim]
        W_new = W - v (vᵀ W) / (vᵀ v)

    For Linear layout (Phi-2):   W shape [out_dim, in_dim]
        W_new = W - (W v) vᵀ / (vᵀ v)
    """
    v = v.to(W.device).to(W.dtype).flatten()

    v_norm_sq = torch.dot(v, v)
    if v_norm_sq < 1e-10:
        logger.warning("Forget vector has near-zero norm, skipping projection")
        return W

    if layout == "conv1d":
        # GPT-2: W is [in_dim, out_dim]
        # Project out v from the input dimension
        vt_W = torch.mv(W.t(), v)       # [out_dim]
        outer = torch.outer(v, vt_W)    # [in_dim, out_dim]
        W_new = W - outer / v_norm_sq
    else:
        # nn.Linear: W is [out_dim, in_dim]
        # Project out v from the input dimension (dim 1)
        Wv = torch.mv(W, v)             # [out_dim]
        outer = torch.outer(Wv, v)      # [out_dim, in_dim]
        W_new = W - outer / v_norm_sq

    return W_new


def ablate(
    forget_vector: torch.Tensor,
    target_layers: List[Dict],
    model_name: str = "gpt2"
) -> dict:
    """
    Main ablation function — applies orthogonal projection to target layers.
    Handles both GPT-2 and Phi-2 weight layouts.
    """
    model, tokenizer, device = load_model(model_name)
    layout = get_weight_layout(model_name)

    ablation_id = str(uuid.uuid4())
    backup = {}
    layer_results = []

    for layer_info in target_layers:
        layer_idx = layer_info["layer_index"]
        weights = get_qkv_weights(model, layer_idx, model_name)

        for weight_name, weight_param in weights.items():
            backup_key = f"layer_{layer_idx}_{weight_name}"
            backup[backup_key] = weight_param.data.clone()

            original_hash = _weight_hash(weight_param.data)

            with torch.no_grad():
                new_weight = apply_projection(weight_param.data, forget_vector, layout)
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
        "correctness_check": all(r["changed"] for r in layer_results)
    }
    _ablation_metadata[ablation_id] = metadata

    logger.info(f"Ablation {ablation_id} complete — {len(layer_results)} matrices modified")
    return metadata


def rollback(ablation_id: str, model_name: str = "gpt2") -> dict:
    """Restores the original weights from before an ablation."""
    if ablation_id not in _weight_backups:
        raise ValueError(f"No backup found for ablation_id: {ablation_id}")

    model, tokenizer, device = load_model(model_name)
    backup = _weight_backups[ablation_id]

    restored = []
    for backup_key, original_weight in backup.items():
        parts = backup_key.split("_")
        layer_idx = int(parts[1])
        weight_name = "_".join(parts[2:])

        weights = get_qkv_weights(model, layer_idx, model_name)
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
