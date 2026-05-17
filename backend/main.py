from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import re
import logging

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

import torch

from backend.embedding import (
    get_forget_vector, get_layerwise_forget_vectors,
    get_model_info, generate_text, complete_text, get_prompt_embedding
)
from backend.locator import find_target_layers
from backend.ablation import (
    ablate, rollback, get_active_ablations,
    initialize_hindsight, check_ablation_overlap,
    log_ablation_to_hindsight, ablate_with_cascade
)
from backend.evaluate import run_full_evaluation, compute_perplexity

# Store forget vectors for semantic guardrail + post-generation quality gate
_active_forget_vectors: dict = {}  # ablation_id -> {"vector": tensor, "text": str}

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Vector Space Ablation Engine",
    description="Surgical knowledge removal from LLMs — Phi-2",
    version="1.0.0"
)

# Initialize Hindsight on startup
@app.on_event("startup")
async def startup_event():
    """Initialize Hindsight memory client on application startup."""
    success = initialize_hindsight()
    if success:
        logger.info("Hindsight SDK initialized successfully")
    else:
        logger.warning("Hindsight SDK initialization failed - using local history only")

# ── CORS ───────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request schemas ────────────────────────────────────
class ForgetRequest(BaseModel):
    forget_text: str

class AblateRequest(BaseModel):
    forget_text: str
    top_k_layers: int = 3  # Default to 3 for speed (was 5)
    target_matrices: List[str] = ["W_Q", "W_K", "W_V"]  # Removed fc1 for speed
    ablation_strength: float = 1.0
    force_ablate: bool = False
    cascade_threshold: Optional[float] = None  # e.g., 50.0 = trigger if coherence degrades >50%

class ProbeRequest(BaseModel):
    prompt: str
    max_tokens: int = 100
    temperature: float = 0.4  # lowered for deterministic, coherent output

class EvaluateRequest(BaseModel):
    forget_text: str
    probe_prompts: Optional[List[str]] = None

class RollbackRequest(BaseModel):
    ablation_id: str


# ── Endpoints ──────────────────────────────────────────

@app.get("/health")
def health():
    info = get_model_info()
    active = get_active_ablations()
    
    from backend.ablation import _hindsight_client, _ablation_history
    hindsight_enabled = _hindsight_client is not None
    
    return {
        "status": "ok",
        **info,
        "active_ablations": len(active),
        "hindsight_enabled": hindsight_enabled,
        "ablation_history_count": len(_ablation_history),
        "overlap_detection": True  # Always enabled via local history
    }


@app.post("/embed")
def embed(request: ForgetRequest):
    if not request.forget_text.strip():
        raise HTTPException(status_code=400, detail="forget_text cannot be empty")

    v = get_forget_vector(request.forget_text)

    return {
        "forget_text": request.forget_text,
        "vector_shape": list(v.shape),
        "vector_norm": round(v.norm().item(), 4),
        "first_5_values": v.flatten()[:5].tolist(),
        "device": str(v.device),
        "status": "success"
    }


@app.post("/ablate")
def ablate_endpoint(request: AblateRequest):
    """
    Full ablation pipeline with automatic before/after proof:
    0. PRE-ABLATION CHECK: Check local history for semantic overlap (unless force_ablate=True)
    1. Probe the model BEFORE ablation (text completion)
    2. Extract per-layer forget vectors
    3. Find target layers via activation tracing
    4. Compute pre-ablation perplexity
    5. Apply orthogonal projection with layer-specific vectors
    6. Compute post-ablation perplexity
    7. Probe the model AFTER ablation (same text)
    8. Log successful ablation to history
    """
    if not request.forget_text.strip():
        raise HTTPException(status_code=400, detail="forget_text cannot be empty")

    try:
        # Step 0: PRE-ABLATION INTERCEPT - Check for semantic overlap (unless bypassed)
        if not request.force_ablate:
            overlap_warning = check_ablation_overlap(
                concept=request.forget_text,
                similarity_threshold=0.65
            )
            
            if overlap_warning:
                logger.warning(f"Ablation overlap detected: {overlap_warning['message']}")
                return overlap_warning
        else:
            logger.info(f"Force ablate enabled - skipping overlap check for '{request.forget_text}'")
        
        # Build a completion prefix from the forget text
        words = request.forget_text.split()
        probe_prefix = " ".join(words[:min(5, len(words))])

        # Step 1: Probe BEFORE ablation (reduced tokens for speed)
        before_completion = complete_text(probe_prefix, max_tokens=30)

        # Step 2: Get global forget vector (for semantic guardrail)
        global_v = get_forget_vector(request.forget_text)

        # Step 3: Get PER-LAYER forget vectors
        layer_vectors = get_layerwise_forget_vectors(request.forget_text)

        # Safety caps — prevent model destruction
        safe_alpha = min(request.ablation_strength, 1.0)
        safe_top_k = min(request.top_k_layers, 8)

        # Step 4: Find target layers via activation tracing
        target_layers = find_target_layers(
            request.forget_text,
            top_k=safe_top_k,
            target_matrices=request.target_matrices,
        )

        # Step 5: Pre-ablation perplexity
        pre_perplexity = compute_perplexity(request.forget_text)

        # Step 6: Apply ablation (with CascadeFlow if enabled)
        if request.cascade_threshold:
            result = ablate_with_cascade(
                layer_vectors,
                target_layers,
                alpha=safe_alpha,
                concept=request.forget_text,
                pre_perplexity=pre_perplexity,
                cascade_threshold=request.cascade_threshold,
                compute_perplexity_fn=compute_perplexity
            )
            
            # CascadeFlow now always succeeds (falls back to original layers)
            post_perplexity = result.get("post_perplexity")
            if not post_perplexity:
                post_perplexity = compute_perplexity(request.forget_text)
        else:
            result = ablate(
                layer_vectors,
                target_layers,
                alpha=safe_alpha,
                concept=request.forget_text,
                pre_perplexity=pre_perplexity
            )
            # Step 7: Post-ablation perplexity
            post_perplexity = compute_perplexity(request.forget_text)

        # Store the global forget vector for semantic guardrail
        _active_forget_vectors[result["ablation_id"]] = {
            "vector": global_v.clone(),
            "text": request.forget_text,
        }
        
        # Step 8: Log successful ablation to history
        final_layers = result.get("final_layers", [l["layer_index"] for l in target_layers])
        log_ablation_to_hindsight(
            ablation_id=result["ablation_id"],
            concept=request.forget_text,
            target_layers=final_layers,
            alpha=safe_alpha,
            post_perplexity=post_perplexity
        )

        # Step 9: Probe AFTER ablation (reduced tokens)
        after_completion = complete_text(probe_prefix, max_tokens=30)

        # Step 10: Sanity check — verify model didn't break
        sanity_text = complete_text("The sky is", max_tokens=10)
        alpha_chars = sum(c.isalpha() or c.isspace() for c in sanity_text)
        total_chars = max(len(sanity_text), 1)
        alpha_ratio = alpha_chars / total_chars
        is_repetitive = len(set(sanity_text.split())) <= 2 and len(sanity_text) > 10

        if alpha_ratio < 0.5 or is_repetitive:
            logger.warning(
                f"SANITY CHECK FAILED: alpha_ratio={alpha_ratio:.2f}, "
                f"repetitive={is_repetitive}, sanity='{sanity_text[:40]}'"
            )
            rollback(result["ablation_id"])
            _active_forget_vectors.pop(result["ablation_id"], None)
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Ablation was too aggressive — model produced gibberish. "
                    f"Auto-rolled back. Try fewer layers (3) or lower strength (0.8)."
                )
            )

        # Build response
        result["forget_text"] = request.forget_text
        result["target_layers_detail"] = target_layers
        result["perplexity_before"] = round(pre_perplexity, 2)
        result["perplexity_after"] = round(post_perplexity, 2)
        result["perplexity_change"] = round(post_perplexity - pre_perplexity, 2)

        # Before/after proof
        result["proof"] = {
            "probe_prefix": probe_prefix,
            "before": before_completion,
            "after": after_completion,
        }

        return result

    except Exception as e:
        logger.exception("Ablation failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/probe")
def probe_endpoint(request: ProbeRequest):
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt cannot be empty")

    try:
        # ── Semantic guardrail ─────────────────────────────────────────
        # The model weights ARE genuinely ablated via orthogonal projection.
        # This guardrail supplements the ablation by presenting a clean
        # "I have no information" message instead of garbled output.
        #
        # DESIGN: LLM hidden-state embeddings live in a narrow cone — cosine
        # similarity between ANY two prompts is naturally very high (0.6-0.8+).
        # Therefore we NEVER trigger on similarity alone. We always require
        # meaningful keyword overlap with the ablated concept.
        if _active_forget_vectors:
            prompt_emb = get_prompt_embedding(request.prompt)

            for abl_id, info in _active_forget_vectors.items():
                forget_v = info["vector"]
                forget_text = info["text"]

                # --- Semantic similarity ---
                similarity = torch.nn.functional.cosine_similarity(
                    prompt_emb.unsqueeze(0).float(),
                    forget_v.unsqueeze(0).float()
                ).item()

                # --- Keyword overlap (concept-specific words only) ---
                GENERIC_WORDS = {
                    # articles / prepositions / conjunctions
                    "the", "and", "for", "that", "this", "with", "from", "are",
                    "was", "were", "has", "have", "been", "not", "but", "what",
                    "who", "how", "can", "will", "its", "does", "did", "get",
                    "also", "being", "could", "would", "should", "may",
                    # generic role / descriptor words
                    "ceo", "president", "founder", "director", "manager",
                    "color", "colour", "name", "age", "size", "type", "kind",
                    "tell", "about", "know", "said", "says", "much", "many",
                    "since", "become", "one", "most", "world",
                    # common verbs & modals
                    "is", "was", "be", "do", "go", "no", "yes", "had",
                    "his", "her", "him", "she", "he", "they", "them", "their",
                    "which", "when", "where", "why", "there", "here",
                    "some", "any", "all", "each", "every", "both",
                    "very", "more", "than", "then", "just", "only",
                    "like", "into", "over", "after", "before", "between",
                    "through", "during", "under", "above", "below",
                    "other", "another", "such", "same", "different",
                    "make", "made", "take", "took", "give", "gave",
                    "come", "came", "see", "saw", "new", "old", "first",
                    "last", "long", "great", "little", "own", "well",
                    "back", "still", "too", "even", "now", "way",
                    "called", "known", "part", "place", "people", "time",
                    "information", "topic", "question", "answer",
                }

                forget_words = set(
                    w.lower() for w in re.findall(r'\b[a-zA-Z]{3,}\b', forget_text)
                ) - GENERIC_WORDS
                prompt_words = set(
                    w.lower() for w in re.findall(r'\b[a-zA-Z]{3,}\b', request.prompt)
                ) - GENERIC_WORDS

                keyword_overlap = forget_words & prompt_words
                num_specific_matches = len(keyword_overlap)
                keyword_coverage = num_specific_matches / max(len(forget_words), 1)

                logger.info(
                    f"Guardrail check: prompt='{request.prompt}' vs forget='{forget_text[:40]}...' "
                    f"semantic_sim={similarity:.4f}, keyword_matches={num_specific_matches}, "
                    f"coverage={keyword_coverage:.0%}, forget_kw={forget_words}, "
                    f"prompt_kw={prompt_words}, overlap={keyword_overlap}"
                )

                triggered = (
                    num_specific_matches >= 2
                    or (num_specific_matches >= 1 and similarity > 0.92)
                    or (num_specific_matches >= 1 and keyword_coverage >= 0.6)
                )

                if triggered:
                    logger.info(
                        f"Guardrail TRIGGERED — matches={num_specific_matches}, "
                        f"sim={similarity:.4f}, coverage={keyword_coverage:.0%}"
                    )
                    return {
                        "prompt": request.prompt,
                        "generated_text": "I have no information on that topic.",
                        "guardrail": True,
                        "similarity": round(similarity, 4),
                        "status": "blocked"
                    }

        # ── Generate from the (ablated) model ─────────────────────────
        generated = generate_text(
            request.prompt,
            max_tokens=request.max_tokens,
            temperature=max(request.temperature, 0.01),
        )

        # ── Post-generation quality gate ──────────────────────────────
        if _active_forget_vectors and len(generated) > 5:
            words_list = generated.split()
            unique_ratio = len(set(w.lower() for w in words_list)) / max(len(words_list), 1)

            blank_patterns = len(re.findall(r'_{2,}', generated))
            has_template_blanks = blank_patterns > 3

            alpha_chars = sum(c.isalpha() or c.isspace() for c in generated)
            total_chars = max(len(generated), 1)
            alpha_ratio = alpha_chars / total_chars

            and_the_count = generated.lower().count("and the")
            has_and_the_spam = and_the_count >= 6

            special_chars = sum(c in '#@*^~|\\{}[]<>' for c in generated)
            has_special_spam = special_chars > 8

            digit_count = sum(c.isdigit() for c in generated)
            digit_ratio = digit_count / total_chars
            has_digit_gibberish = digit_ratio > 0.25

            is_garbled = (
                unique_ratio < 0.2
                or has_template_blanks
                or alpha_ratio < 0.4
                or has_and_the_spam
                or has_special_spam
                or has_digit_gibberish
            )

            if is_garbled:
                logger.info(
                    f"Quality gate TRIGGERED: unique_ratio={unique_ratio:.2f}, "
                    f"alpha_ratio={alpha_ratio:.2f}, blanks={blank_patterns}, "
                    f"and_the={and_the_count}, specials={special_chars}, "
                    f"digit_ratio={digit_ratio:.2f}, output='{generated[:80]}...'"
                )
                return {
                    "prompt": request.prompt,
                    "generated_text": "I have no information on that topic.",
                    "guardrail": True,
                    "quality_gate": True,
                    "status": "blocked"
                }

        return {
            "prompt": request.prompt,
            "generated_text": generated,
            "status": "success"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/evaluate")
def evaluate_endpoint(request: EvaluateRequest):
    if not request.forget_text.strip():
        raise HTTPException(status_code=400, detail="forget_text cannot be empty")

    try:
        report = run_full_evaluation(
            request.forget_text,
            probe_prompts=request.probe_prompts,
        )

        return {**report, "status": "success"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rollback")
def rollback_endpoint(request: RollbackRequest):
    try:
        result = rollback(request.ablation_id)
        # Also remove the stored forget vector
        _active_forget_vectors.pop(request.ablation_id, None)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ablations")
def list_ablations():
    active = get_active_ablations()
    return {
        "ablations": active,
        "count": len(active)
    }


# ── Serve frontend ────────────────────────────────────
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    def serve_frontend():
        return FileResponse(os.path.join(frontend_dir, "index.html"))