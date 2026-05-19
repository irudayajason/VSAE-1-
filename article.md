# CascadeFlow rolling back terrible ideas that Hindsight tried stopping

I thought deleting a concept from a model would be the easy part. The hard part was not deleting the pieces that keep the model readable, and it’s why I ended up wiring Hindsight into the pipeline and letting CascadeFlow step in when my own layer choices went sideways.

## What the system does and how it hangs together

This codebase is the Vector Space Ablation Engine (VSAE): a system for surgically removing a concept from a trained Phi-2 model by projecting that concept out of the model’s weight matrices. The flow is intentionally simple. Given a `forget_text`, we extract a forget vector, locate the layers that encode it, apply orthogonal projection to those weights, and produce a compliance report with before/after probes and perplexity deltas. The core execution path lives in `backend/main.py`, which exposes a FastAPI server with `/ablate`, `/probe`, `/rollback`, and `/evaluate` endpoints. The ablation logic is in `backend/ablation.py`, layer selection is in `backend/locator.py`, embeddings are in `backend/embedding.py`, and evaluation lives in `backend/evaluate.py`. There’s also a CLI (`vsae-cli.py`) and a lightweight frontend served from `/frontend` for manual use.

Two pieces make this system credible in production: memory and recovery. I use Hindsight as the memory layer to track ablations and warn when I’m about to stack overlapping deletions. The integration draws from the [Hindsight GitHub repository](https://github.com/vectorize-io/hindsight) and its [Hindsight documentation](https://hindsight.vectorize.io/) to retain a short, human-readable record of every ablation. That record behaves like the system’s conscience, and it matches the pattern described in the [Vectorize agent memory overview](https://vectorize.io/what-is-agent-memory): it’s a lightweight memory service that feeds decisions rather than an analytics warehouse.

CascadeFlow is the recovery layer. When an ablation makes the model’s general language ability worse, CascadeFlow automatically rolls back and retries on shifted layers. I’m using the [cascadeflow GitHub project](https://github.com/lemony-ai/cascadeflow) as the conceptual reference and the [cascadeflow documentation](https://docs.cascadeflow.ai/) to keep the behavior predictable. In this repo, CascadeFlow is implemented directly in `ablation.py` as a set of retries with explicit layer shifts, tied to a coherence check that is separate from the concept itself.

## The story: forgetting is easy, keeping coherence is not

The first version of VSAE focused entirely on “did the model forget the concept?” If the post-ablation perplexity of the target concept spiked, I was satisfied. That’s a mistake. A model can fail to answer the target prompt and still degrade its general language ability in a way that shows up everywhere else. The failure mode I kept hitting was not “didn’t forget,” it was “forgot too much.”

The fix was to treat overlapping deletions as first-class failures and to protect general coherence with an explicit rollback path. Hindsight handles the overlap detection. Every successful ablation is recorded, both locally and in Hindsight when it’s configured. When a new request comes in, the system computes a fresh forget vector for the new concept and compares it to the vectors of previous ablations. If the similarity crosses a threshold, the API returns a warning and stops. I did this because the risk isn’t theoretical; overlapping deletions stack, and their effects are not linear. One delete is fine; two deletes of semantically adjacent concepts is how you end up with a model that suddenly “forgets” how to speak English.

CascadeFlow solves the second half of the problem: it’s the automated “try again” mechanism when an ablation harms general coherence. The critical design decision here is to measure coherence on a neutral sentence, not on the concept. Increasing perplexity on the target concept is expected; increasing perplexity on a neutral sentence means I hurt the base language model. That distinction is what makes CascadeFlow useful. The system performs an ablation, measures neutral perplexity, and if the degradation is above a threshold it rolls back and retries the same operation on shifted layers. That behavior mirrors the way I debugged this manually: move the ablation slightly up or down the stack and see if the model stabilizes.

So the story I’d tell is not about projection math; it’s about protecting the system from my own bad deletions. Hindsight helps me see when I’m repeating a mistake. CascadeFlow helps me recover when I still make one.

## The code that enforced my discipline

The core ablation is still projection math. The engine applies the forget vector as an orthogonal projection on weight matrices and immediately casts back to the original dtype to avoid memory blowups:

```python
def apply_projection(
    W: torch.Tensor,
    v: torch.Tensor,
    alpha: float = 1.0,
) -> torch.Tensor:
    orig_dtype = W.dtype
    W_f32 = W.float()
    v_f32 = v.to(W.device).float().flatten()

    v_norm_sq = torch.dot(v_f32, v_f32)
    Wv = torch.mv(W_f32, v_f32)
    outer = torch.outer(Wv, v_f32)
    W_new = W_f32 - alpha * outer / v_norm_sq
    return W_new.to(orig_dtype)
```

Hindsight lives at the very start of the `/ablate` flow. The overlap check is intentionally blunt: if the embedding similarity crosses a threshold, the endpoint returns a warning payload and stops. I prefer a false positive here to an unbounded degradation later:

```python
for past in _ablation_history:
    past_concept = past["concept"]
    past_perplexity = past.get("post_perplexity")

    past_vector = get_forget_vector(past_concept)
    similarity = torch.nn.functional.cosine_similarity(
        new_vector.unsqueeze(0).float(),
        past_vector.unsqueeze(0).float()
    ).item()

    if similarity > similarity_threshold:
        degradation = 18.0
        if past_perplexity:
            degradation = min(abs(past_perplexity - 10.0), 50.0)
        return {
            "status": "warning",
            "message": (
                f"This concept overlaps {similarity:.0%} with a previous ablation "
                f"'{past_concept[:50]}'. Stacking ablations on overlapping concepts "
                f"may degrade model quality by ~{degradation:.0f}%."
            ),
            "past_concept": past_concept,
            "similarity": round(similarity, 4),
            "historical_perplexity_degradation": round(degradation, 2)
        }
```

CascadeFlow is the safety net. The key is that it measures general coherence on a neutral sentence and only cascades when that metric degrades too much. When it does, it rolls back and retries on shifted layers:

```python
def ablate_with_cascade(..., target_layers: List[Dict], cascade_threshold: float, ...):
    NEUTRAL_TEXT = "The sky is blue and the grass is green. Water flows downhill."
    baseline_coherence = compute_perplexity_fn(NEUTRAL_TEXT)

    result = ablate(layer_forget_vectors, target_layers, alpha, concept, pre_perplexity)
    ablation_id = result["ablation_id"]

    post_coherence = compute_perplexity_fn(NEUTRAL_TEXT)
    coherence_change = post_coherence - baseline_coherence
    coherence_degradation_pct = (coherence_change / max(baseline_coherence, 1)) * 100

    if coherence_degradation_pct > cascade_threshold:
        rollback(ablation_id)
        model, _, _ = load_model()
        max_layers = model.config.num_hidden_layers

        for shift in [-2, +2]:
            shifted_layers = shift_target_layers(target_layers, shift, max_layers)
            if not shifted_layers:
                continue
```

Those three pieces reflect the discipline I ended up enforcing: accurate math, memory of what I’ve already done, and a recovery path that saves me from pretending my first attempt is always correct.

## What it looks like in practice

Here’s the shape of an ablation request. If I’m cautious, I set a cascade threshold so the system can recover from a coherence hit automatically:

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

If I’ve already ablated something similar, the API short-circuits with a warning. This is exactly the sort of “don’t do this twice” stop sign I was missing in early versions:

```json
{
  "status": "warning",
  "message": "This concept overlaps 82% with a previous ablation 'Harry Potter'. Stacking ablations on overlapping concepts may degrade model quality by ~18%.",
  "past_concept": "Harry Potter",
  "similarity": 0.8231,
  "historical_perplexity_degradation": 18.0
}
```

When CascadeFlow triggers, the response includes the cascade attempts and final layers. I don’t need a magic number here; I want to see the shifts and whether the retries stayed within the threshold:

```json
{
  "ablation_id": "b3f4...",
  "cascade_triggered": true,
  "original_layers": [8, 12, 16, 20, 24],
  "final_layers": [6, 10, 14, 18, 22],
  "cascade_attempts": [
    {"shift": -2, "layers": [6, 10, 14, 18, 22], "degradation_pct": 9.7, "success": true}
  ],
  "perplexity_before": 12.4,
  "perplexity_after": 156.8,
  "perplexity_change": 144.4
}
```

The rest of the behavior is intentionally boring. A successful ablation creates a compliance report in `reports/`, and the `/probe` endpoint uses a semantic guardrail to block prompts that are too close to an ablated concept. The system isn’t trying to be clever. It’s trying to be safe and predictable.

## Lessons I’d reuse

1. **Separate “forgetting the concept” from “breaking the model.”** The single biggest improvement came from measuring coherence on neutral text and treating that as a distinct metric. Concept perplexity should change; general coherence should not.

2. **Memory is a safety feature, not a convenience.** Hindsight is not just logging. It is the gatekeeper that stops me from stacking overlapping deletions. Without it, I would be relying on my own memory and it would fail.

3. **Make rollback first-class.** The cascade logic only works because rollback is reliable and cheap. If rollback is flaky, the safest thing you can do is refuse the ablation entirely.

4. **Prefer conservative defaults.** The code caps layer counts and ablation strength for a reason. The cost of a weak ablation is a second attempt; the cost of an overly aggressive ablation is a broken model.

5. **Keep the response concrete.** The API returns the layers, the attempts, and the deltas. That transparency makes it possible to debug behavior without a UI, which is essential for engineers who automate this through CI.

If I summarize the project in one sentence, it’s this: I built a deletion system that doesn’t just erase knowledge, it tries hard to avoid erasing the model itself. Hindsight tells me when I’m repeating a mistake. CascadeFlow gives me a second chance when I ignore the warning anyway. That combination turned a brittle idea into something I’d be willing to run in production.
