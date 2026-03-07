

## Context: What VSAE Does Mathematically

VSAE (Vector Space Ablation Engine) surgically removes specific knowledge from a trained LLM without retraining it. The core operation is:

```
W_new = W - (W * v * v^T) / (v^T * v)
```

- **W** = a weight matrix inside the LLM (stores learned knowledge)
- **v** = a concept vector representing the knowledge to be removed
- **v^T** = the transpose of v
- **W * v * v^T** = the "projection" of concept v onto weight matrix W (its shadow inside the model)
- **(v^T * v)** = a scalar normalizer (the squared length of v)

**In plain English:** Find the shadow of the concept inside the weight matrix, then subtract that shadow. The rest of the model is untouched. This is called orthogonal projection removal — a standard linear algebra operation adapted for neural network weight surgery.

---

## Paper 1: "Towards Making Systems Forget with Machine Unlearning"
**Authors:** Yinzhi Cao & Junfeng Yang (Columbia University)  
**Published:** IEEE Symposium on Security and Privacy, May 2015  
**ArXiv / DOI:** 10.1109/SP.2015.35

### Problem It Solves
When a machine learning model is trained on data, that data's influence becomes deeply embedded in the model's parameters. Simply deleting the data from a database is not enough — the model still "remembers" it. This paper addresses the right to be forgotten: users who want their private data removed from a trained system cannot be satisfied by database deletion alone. Retraining the entire model from scratch is the only guaranteed solution, but for large models this is computationally prohibitive. The paper asks: can we make a model forget specific data efficiently, without full retraining?

### Method It Uses
Cao & Yang propose transforming any learning algorithm into a **summation form**. Instead of training a model that directly depends on every individual data sample, the model is restructured to depend only on a small number of aggregate summations of transformed data samples. To forget one data point, you simply remove its contribution from the relevant summations and recompute only the affected part of the model — an O(1) operation rather than a full retrain. They demonstrate this works for naïve Bayes classifiers, SVMs, k-means clustering, and other standard ML algorithms. Their two key metrics for success are **completeness** (how thoroughly the data is forgotten) and **timeliness** (how fast the forgetting happens).

### Relation to VSAE
This paper is the **founding paper of machine unlearning** — it established the field that VSAE operates within. However, Cao & Yang's approach targets classical ML models and operates at the level of training data summations. VSAE takes the core insight further: rather than restructuring the training pipeline, VSAE operates directly on the weight matrices of a trained LLM using vector projection. VSAE can be seen as a weight-space implementation of the "forget without retraining" goal that Cao & Yang first articulated. The summation-form approach is also the conceptual ancestor of VSAE's localized weight surgery.

---

## Paper 2: "Eternal Sunshine of the Spotless Net: Selective Forgetting in Deep Networks"
**Authors:** Aditya Golatkar, Alessandro Achille, Stefano Soatto (UCLA)  
**Published:** CVPR 2020 (IEEE/CVF Conference on Computer Vision and Pattern Recognition)  
**ArXiv:** 1911.04933

### Problem It Solves
Deep neural networks memorize training data in a distributed way across millions of weights. Even if a model's output hides the influence of certain training data, an adversary who can probe the model's weights (e.g., through a membership inference attack) may still extract that information. Simply hiding the output is not enough — the weights themselves need to be cleaned. This paper asks: how do you scrub the weights of a deep network so that no probing function can distinguish the scrubbed model from one that was never trained on the forgotten data?

### Method It Uses
Golatkar et al. introduce **weight scrubbing** using the Fisher Information Matrix (FIM). The FIM measures how much each weight parameter contributes to the model's predictions about specific data. To forget a subset of data, the method applies a noisy Newton update to the weights: it identifies which weight directions are most influenced by the data to be forgotten (using the FIM), and modifies those weights by adding carefully calibrated noise derived from the FIM. The resulting model behaves as if it were trained without that data, even when weights are directly probed. The method provides a formal upper bound on the residual information remaining in the weights, framed as a weakened form of Differential Privacy. Crucially, it does not require retraining from scratch or access to the original training data.

### Relation to VSAE
This paper is the **most direct theoretical ancestor of VSAE's weight-level ablation approach**. Golatkar et al. prove that effective forgetting must happen in the weight space, not just the output space — exactly the philosophy VSAE adopts. The concept of using a mathematical matrix operation to "scrub" specific directional information from weights directly parallels VSAE's projection formula `W_new = W - (W * v * v^T) / (v^T * v)`. Where Golatkar uses FIM-guided noise injection, VSAE uses clean orthogonal projection of concept vectors — a more precise and deterministic variant of the same fundamental idea. VSAE's `ablation.py` and `locator.py` modules can be seen as a streamlined, concept-vector-centric implementation of the scrubbing philosophy introduced here.

---

## Paper 3: "Locating and Editing Factual Associations in GPT" (ROME)
**Authors:** Kevin Meng, David Bau, Alex Andonian, Yonatan Belinkov (MIT / Northeastern)  
**Published:** NeurIPS 2022 (Advances in Neural Information Processing Systems, Vol. 36)  
**ArXiv:** 2202.05262

### Problem It Solves
Large language models like GPT store factual knowledge (e.g., "The Eiffel Tower is in Paris") somewhere inside their billions of parameters, but it was previously unknown exactly where. Without knowing where knowledge is stored, you cannot surgically edit or remove it — you can only retrain the whole model or do imprecise fine-tuning. This paper asks two questions: (1) Where exactly in a transformer's architecture are specific facts stored? and (2) Can we edit those facts precisely without disrupting the rest of the model?

### Method It Uses
Meng et al. develop two interconnected techniques. First, **Causal Tracing**: they run the model twice — once normally and once with the subject tokens corrupted — then systematically restore individual hidden states to identify which specific neuron activations are causally responsible for a factual prediction. This reveals that **mid-layer feed-forward MLP modules** are the primary storage sites for factual associations, activated when processing the final token of a subject name. Second, **ROME (Rank-One Model Editing)**: using this localization insight, they directly modify the feed-forward weight matrix at the identified layer using a rank-one update derived from the key-value memory interpretation of MLP layers. The edit is precise enough to change one fact (e.g., making GPT believe the Eiffel Tower is in Rome) while generalizing correctly to new phrasings, without disrupting unrelated knowledge.

### Relation to VSAE
ROME is the **most technically proximate paper to VSAE's implementation**. VSAE's `locator.py` module directly mirrors ROME's causal tracing approach — identifying which weight matrices encode a given concept. Once located, VSAE's `ablation.py` applies the projection formula `W_new = W - (W * v * v^T) / (v^T * v)` to those specific layers — a removal operation rather than ROME's replacement operation, but using the same rank-one weight manipulation philosophy. VSAE can be understood as "ROME for deletion instead of editing": where ROME inserts new factual associations via rank-one updates, VSAE erases concept vectors via rank-one projections. The key insight shared by both is that knowledge in transformers is **localized and directly manipulable** at the weight level.

---

## Summary Comparison Table

| Aspect | Cao & Yang 2015 | Golatkar et al. 2020 | Meng et al. 2022 (ROME) |
|---|---|---|---|
| Target Model Type | Classical ML (SVM, Naive Bayes) | Deep CNNs | GPT-style Transformers |
| Operation Level | Training data summations | Weight scrubbing via FIM noise | Feed-forward weight rank-one edit |
| Requires Retraining? | No | No | No |
| Requires Original Data? | Partial | No | No |
| VSAE Relevance | Conceptual foundation of unlearning | Direct inspiration for weight-space ablation | Technical blueprint for localization + weight surgery |
| Key Formula/Tool | Summation form decomposition | Fisher Information Matrix noise | Causal tracing + rank-one update |

---

## Key Takeaways for VSAE Development

1. **Unlearning must happen at the weight level** (Golatkar 2020) — hiding it in outputs is insufficient. VSAE correctly targets weight matrices directly.

2. **Knowledge in transformers is localized** (Meng 2022) — it lives in specific mid-layer MLP modules, making surgical removal feasible. VSAE's `locator.py` implements this insight.

3. **The "forget without retrain" goal is well-established** (Cao 2015) — VSAE is part of a decade-long research lineage and addresses a genuine, unsolved problem at the LLM scale.

4. **Projection vs. noise vs. rank-one update** — VSAE's approach (orthogonal projection removal) is more deterministic and interpretable than FIM noise (Golatkar) and complementary to rank-one editing (ROME). This is a genuine technical contribution worth documenting in the project README.

---

