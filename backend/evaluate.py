"""
Evaluation Suite — proves that the ablation actually worked.

Three test methods:
1. Perplexity Score — model should be "confused" by erased content
2. Membership Inference Attack (MIA) — loss should spike on forgotten data
3. Direct Probing — model should fail to answer questions about erased concept

Optimizations:
  - torch.inference_mode() for all evaluation passes
  - use_cache=True on generation calls
  - Tuned generation params for coherent post-ablation output
"""

import torch
import math
from typing import Dict, List
import logging

from backend.embedding import load_model

logger = logging.getLogger(__name__)


def compute_perplexity(text: str) -> float:
    """
    Computes perplexity of the model on the given text.
    Higher perplexity = model is more "confused" by the text.

    A successful ablation should cause perplexity on the forget_text
    to spike significantly.
    """
    model, tokenizer, device = load_model()

    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=512
    ).to(device)

    with torch.inference_mode():
        outputs = model(
            input_ids=inputs["input_ids"],
            labels=inputs["input_ids"],
            use_cache=False,  # labels present → teacher forcing, no KV cache
        )

    loss = outputs.loss.item()
    perplexity = math.exp(loss)

    logger.info(f"Perplexity on '{text[:50]}...': {perplexity:.2f} (loss: {loss:.4f})")
    return perplexity


def membership_inference_attack(text: str) -> Dict:
    """
    Membership Inference Attack — checks if the model "recognizes" the text.

    If loss is LOW → model has seen/memorized this data
    If loss is HIGH → model does NOT recognize this data (i.e., it was erased)

    Returns:
        Dict with loss, perplexity, and a verdict
    """
    model, tokenizer, device = load_model()

    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=512
    ).to(device)

    with torch.inference_mode():
        outputs = model(
            input_ids=inputs["input_ids"],
            labels=inputs["input_ids"],
            use_cache=False,
        )

    loss = outputs.loss.item()
    perplexity = math.exp(loss)

    # Threshold: if perplexity > 100, the model likely doesn't "know" the text
    threshold = 100.0
    verdict = "FORGOTTEN" if perplexity > threshold else "STILL_KNOWN"

    result = {
        "loss": round(loss, 4),
        "perplexity": round(perplexity, 2),
        "threshold": threshold,
        "verdict": verdict
    }

    logger.info(f"MIA result: {result}")
    return result


def direct_probe(
    prompt: str,
    max_tokens: int = 50,
) -> str:
    """
    Directly probes the model by generating text from a prompt.

    After ablation, the model should produce incoherent or wrong
    answers to prompts about the erased concept.

    Uses tuned generation params for coherent output on non-ablated topics.
    """
    model, tokenizer, device = load_model()

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=256
    ).to(device)

    with torch.inference_mode():
        output_ids = model.generate(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            max_new_tokens=max_tokens,
            do_sample=True,
            temperature=0.4,
            top_p=0.9,
            repetition_penalty=1.2,
            pad_token_id=tokenizer.eos_token_id,
            use_cache=True,  # KV caching for speed
        )

    # Decode only the new tokens
    generated = tokenizer.decode(
        output_ids[0][inputs["input_ids"].shape[1]:],
        skip_special_tokens=True
    )

    logger.info(f"Probe '{prompt[:40]}...' → '{generated[:80]}...'")
    return generated


def run_full_evaluation(
    forget_text: str,
    probe_prompts: List[str] = None,
) -> Dict:
    """
    Runs all three evaluation methods and returns a comprehensive report.

    Args:
        forget_text: The text that was supposed to be forgotten
        probe_prompts: Optional list of prompts to test. If None, uses
                       the first few words of forget_text as a prompt.

    Returns:
        Full evaluation report dict
    """
    # 1. Perplexity
    perplexity = compute_perplexity(forget_text)

    # 2. MIA
    mia_result = membership_inference_attack(forget_text)

    # 3. Direct probing
    if probe_prompts is None:
        # Use the first few words as a probe
        words = forget_text.split()
        probe_prompts = [" ".join(words[:min(5, len(words))])]

    probe_results = []
    for prompt in probe_prompts:
        generated = direct_probe(prompt, max_tokens=50)
        probe_results.append({
            "prompt": prompt,
            "generated_text": generated
        })

    report = {
        "forget_text": forget_text,
        "perplexity": {
            "score": round(perplexity, 2),
            "interpretation": "HIGH — model is confused (good)"
            if perplexity > 100 else "LOW — model still knows this (bad)"
        },
        "membership_inference": mia_result,
        "direct_probing": probe_results,
        "overall_verdict": mia_result["verdict"]
    }

    logger.info(f"Full evaluation complete: {report['overall_verdict']}")
    return report
