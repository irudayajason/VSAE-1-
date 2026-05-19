# The Guardrails I Built for Surgical Unlearning in Production

## Hook
The hardest part of deleting knowledge from a model isn’t the math — it’s making sure the rest of the model keeps behaving like a model.

## What the system does and how it hangs together
I built the Vector Space Ablation Engine (VSAE) to make “delete this concept from a model” a repeatable engineering task instead of a research ritual. The goal was to turn a brittle research workflow into a pipeline step. At a high level, the system takes a concept (a sentence, a phrase, an identifying string) and finds where that concept lights up inside the model. It applies a targeted orthogonal projection to those weights and proves the deletion with a compliance report.

The repo is structured around that pipeline:

- **backend/ablation.py** — core projection logic, alpha decay, cascade retries, and compliance report generation.
- **backend/locator.py** — activation tracing to pick the most relevant layers.
- **backend/evaluate.py** — perplexity and probing to confirm the ablation did what we asked.
- **backend/main.py** — a FastAPI service that exposes `/ablate`, `/probe`, `/rollback`, and `/health` endpoints.
- **frontend/** — a lightweight UI for operators to run ablations and see the results.
- **vsae-cli.py** — a CLI wrapper for automation.

Two outside systems show up as first-class concerns: **Hindsight** for ablation memory and overlap detection, and **CascadeFlow** for automatic recovery when the model starts to drift. I integrated them because a raw “delete concept” button is too dangerous without guardrails and history. The engineering effort wasn’t just about “can we erase a vector” — it was about getting predictable behavior over many ablations in a row.

If you’re curious about the memory side, I leaned on the [Hindsight GitHub repository](https://github.com/vectorize-io/hindsight). The [Hindsight documentation](https://hindsight.vectorize.io/) helped me treat past ablations as a queryable memory bank. The mental model lines up with this [Vectorize agent memory explainer](https://vectorize.io/what-is-agent-memory) because “remembering what we already deleted” is operational memory for the system.

For the safety net, I treated the [CascadeFlow GitHub repository](https://github.com/lemony-ai/cascadeflow) and the [CascadeFlow documentation](https://docs.cascadeflow.ai/) as inspiration for a retry mechanism that’s explicit, measurable, and user-visible.

## Core technical story: making deletion safe across repeated operations
The core technical story isn’t just orthogonal projection. It’s how I made it safe to run that projection repeatedly without quietly destroying the model.

### 1) Projection isn’t enough — you need layer-aware control
The core operation is a projection that removes the forget vector from each weight matrix. I keep it simple and explicit in `apply_projection`, and I do all math in float32 before casting back to the original dtype to avoid numerical drift.

```python
# backend/ablation.py
Wv = torch.mv(W_f32, v_f32)          # [out_dim]
outer = torch.outer(Wv, v_f32)       # [out_dim, in_dim]
W_new = W_f32 - alpha * outer / v_norm_sq
```

The part that took longer was deciding how strong that projection should be at each layer. In practice, early layers encode the concept; late layers are responsible for grammatical fluency. So I decay alpha as I move deeper into the model. The code forces that trade-off into the open:

```python
# backend/ablation.py
if position < midpoint:
    return alpha
else:
    decay_factor = 1.0 - (0.4 * decay_position / max(decay_range - 1, 1))
    decayed_alpha = alpha * max(decay_factor, 0.6)
```

This is intentionally opinionated: I’d rather slightly under-erase than break coherence. The system still produces a report so you can see how much signal you removed. In the codebase itself, I keep the constants documented right next to the formula so the intent doesn’t get lost over time.
The 0.4 slope and 0.6 floor are there to cap the decay at 60% of the original strength, which keeps the late layers from getting flattened and preserves fluency.

### 2) The model remembers, so the system has to remember too
The failure mode I hit early was stacking similar ablations. If you remove “J.K. Rowling is the author of Harry Potter” and then try to remove “J.K. Rowling wrote the Harry Potter books,” the model can degrade faster than the user expects. That’s why Hindsight is a central theme, not a nice-to-have.

I keep a local, file-backed ablation history so overlap detection always works, even without a cloud API key. That history is used in a pre-ablation intercept to warn the operator when they’re re-cutting the same semantic space:

```python
# backend/ablation.py
if similarity > similarity_threshold:
    return {
        "status": "warning",
        "message": (
            f"This concept overlaps {similarity:.0%} with a previous ablation "
            f"'{past_concept[:50]}'."
        ),
        "past_concept": past_concept,
        "similarity": round(similarity, 4),
    }
```

That warning is not an error. It’s a prompt to think. In the UI, the operator can cancel or proceed with a “force ablate” override. Hindsight isn’t there to block work — it’s there to keep you honest about how many times you’ve hit the same area of the model.

### 3) CascadeFlow keeps me from accidentally breaking coherence
The second failure mode was more subtle: you can delete a concept and still harm general language ability, so I built CascadeFlow into the ablation path. It checks coherence on neutral text and only triggers if general perplexity degrades beyond a threshold, ignoring the target concept that should spike. I use a plain, factual sentence about sky, grass, and water because it’s semantically neutral and mixes common nouns and verbs, giving a steadier baseline without touching the target concept.

```python
# backend/ablation.py
NEUTRAL_TEXT = "The sky is blue and the grass is green. Water flows downhill."
baseline_coherence = compute_perplexity_fn(NEUTRAL_TEXT)
...
coherence_degradation_pct = (coherence_change / max(baseline_coherence, 1)) * 100
if coherence_degradation_pct > cascade_threshold:
    rollback(ablation_id)
```

When it does trigger, the system rolls back and retries with shifted layers. This is not a magical fix — it’s a controlled fallback. The operator gets a report with original layers, shifted layers, and the final result. If all retries fail, the system still allows you to proceed with the original layers, but it tells you exactly what happened.

That decision is intentional: the system is a pipeline utility, not a gatekeeper. But the pipeline is noisy and explicit. It’s hard to miss when you’re doing something risky.

## Code-backed explanations: how the pieces work together
The pipeline is stitched together in `backend/main.py`. The `/ablate` endpoint does the orchestration: overlap detection, pre- and post-probing, layer selection, ablation, coherence checks, and report generation. The logic reads like a checklist and it’s designed to be auditable.

When you call `/ablate`, the flow is:

1. **Overlap detection** (Hindsight-backed local history).
2. **Probe before** (short completion so you can compare).
3. **Find target layers** (activation tracing).
4. **Compute pre-ablation perplexity**.
5. **Apply ablation** (with CascadeFlow if enabled).
6. **Compute post-ablation perplexity**.
7. **Probe after**.
8. **Sanity check** for gibberish.
9. **Generate compliance reports**.

The fact that the compliance report is generated inside the same transaction is deliberate. I wanted deletion to be inseparable from evidence, not an afterthought. The report includes the configuration hash, the before/after completions, and layer-level modification details.

## Results and example interactions
Here’s what a typical interaction looks like when I’m running this in production:

### 1) A clean ablation
```
POST /ablate
{
  "forget_text": "J.K. Rowling is the author of Harry Potter",
  "top_k_layers": 3,
  "ablation_strength": 1.0,
  "cascade_threshold": 15.0
}
```

The response includes an ablation ID, the target layers, a post-ablation perplexity spike on the concept, and a compliance report saved to `reports/{ablation_id}.json`. The UI shows the before/after completion and a neutral sanity check (“The sky is…”).

### 2) An overlap warning (Hindsight doing its job)
```
POST /ablate
{
  "forget_text": "J.K. Rowling wrote the Harry Potter books",
  "top_k_layers": 3,
  "ablation_strength": 1.0
}
```

The response comes back with a warning payload, not a hard failure. It tells me the semantic overlap percentage and the past concept. At that point I can cancel, or re-submit with `force_ablate: true` if I really need to stack the deletion.

### 3) CascadeFlow stepping in
```
POST /ablate
{
  "forget_text": "Machine learning algorithms process data",
  "top_k_layers": 8,
  "ablation_strength": 1.0,
  "cascade_threshold": 15.0
}
```

If the coherence check shows the model got worse on neutral text, CascadeFlow rolls back and retries with shifted layers. The final report lists the attempts and whether each shift passed the threshold. It’s not silent; it’s a documented safety net.

## Lessons learned
1. **Deletion without memory is reckless.** The ablation math is fast, but the damage from repeated overlapping deletions is slow and cumulative. A local, file-backed history is the minimum requirement. Hindsight gives me a clean way to keep that history queryable and optionally backed up.

2. **Make the trade-offs explicit in code.** Alpha decay is a choice, not a trick. I’d rather admit I’m reducing strength on late layers than pretend a single global alpha works everywhere. The model’s language fluency lives in those late layers; ignoring that is how you get gibberish.

3. **Safety nets should be measurable, not magical.** CascadeFlow doesn’t “fix” a bad ablation; it gives you a deterministic retry with shifted layers and reports the outcome. That’s the right kind of automation for a production pipeline.

4. **Compliance evidence should be a first-class artifact.** If I’m deleting data for regulatory reasons, the report matters as much as the deletion. Tying report generation directly to the ablation path forces me to treat evidence as part of the system’s behavior.

5. **Expose guardrails as user-facing signals.** The warnings, the cascade cards, and the sanity checks aren’t UI fluff. They’re the only way an operator can develop intuition about what the system is doing under the hood.

## Closing
VSAE is the first system I’ve built where the hardest engineering problem wasn’t speed or accuracy — it was trust. The combination of orthogonal projection, Hindsight-backed memory, and CascadeFlow retries gives me something I can operate safely over time. The math is important, but the guardrails are what make this usable in the real world.
