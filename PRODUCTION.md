**Production Considerations**

**Latency / Cost Tradeoffs**
- Retrieval is local (BM25 + dense). Dense embeddings are the main latency/cost driver.
- Default model is `gpt-4.1-mini` for cost efficiency. For higher accuracy, switch to a larger model at higher cost.
- Options:
  - Cache embeddings for policy sections to avoid re-encoding.
  - Use a smaller embedding model or reduce top-k.
  - Add reranking only when retrieval confidence is low.

**Monitoring Signals**
- Quality:
  - Recall@3 from offline eval.
  - Citation validity rate from verifier.
  - Clarifying behavior accuracy.
- Safety:
  - Escalation rate.
  - Conflicting source detections.
  - Stale policy usage.
- Tool failures:
  - Generator exceptions and fallback rate.
  - Retrieval errors.
- Drift:
  - Changes in escalation rate over time.
  - Drops in citation validity.

**Rollout Strategy + Fallback Behavior**
- Rollout:
  - Stage 1: Internal only (audit logging enabled).
  - Stage 2: Limited external beta with A/B test.
  - Stage 3: Gradual ramp with alerts on KPI regressions.
- Fallbacks:
  - If LLM fails: return a safe refusal and escalate.
  - If retrieval returns no evidence: ask clarifying question or escalate.
  - If conflicting or stale evidence: refuse and escalate.
