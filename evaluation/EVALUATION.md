**Evaluation Plan**

**Offline Test Set (10 questions)**
Located in `evaluation/test_queries.json`. Each test includes:
- `query`
- `expected_doc`
- `expected_clarify`
- `expected_behavior` (human-readable expected outcome)

Mix includes easy, tricky, ambiguous, and adversarial cases:
1. Germany probation termination (easy, direct)
2. Poland onboarding documents (easy, list)
3. France notice period (easy, direct)
4. Italy payroll cutoff (easy, numeric)
5. Netherlands health insurance (easy, yes/no)
6. Missing country (clarifying required)
7. Multiple countries (clarifying required)
8. Explicit source request (citation formatting check)
9. Unanswerable (hallucination trap)
10. Adversarial PII in query (logging redaction)

**Expected “Good” Behavior**
Captured in `expected_behavior` per test. Summary:
- If country missing/ambiguous: ask clarifying question, do not answer.
- If evidence supports answer: respond with answer + citations `doc_id | section | timestamp`.
- If evidence insufficient: explicitly say so and escalate.
- Never fabricate or include non‑evidence claims.
- PII is redacted in audit logs.

**Offline Evaluation Criteria + Scoring**
Computed by `evaluation/retrieval_eval.py`:
- `Recall@3`: retrieval hit rate (expected doc appears in top 3).
- `Citation validity`: answer contains citations that exactly match evidence.
- `Clarifying behavior accuracy`: system should ask when country missing or ambiguous.

Scoring approach:
- Pass/Fail per metric for each test.
- Aggregate as ratios (0.0–1.0). Suggested gates:
  - Recall@3 >= 0.8
  - Citation validity >= 0.9
  - Clarifying behavior accuracy = 1.0

**Online Evaluation / A/B Testing Idea**
Compare two variants:
- A: current hybrid retrieval + strict citation enforcement
- B: hybrid retrieval + reranking (LLM or cross‑encoder) before generation

Measure:
- Answer acceptance rate (no escalation)
- Citation validity rate (from verifier)
- Clarification rate (should not increase for well‑formed queries)
- User satisfaction proxy (thumbs‑up / resolution rate)

**Monitoring Hallucinations and Regressions**
1. Log verifier failures:
   - Missing/invalid citations
   - Conflicting sources
   - Stale policy usage
2. Track weekly trend of:
   - Escalation rate
   - Citation validity rate
   - Clarifying question rate
3. Regression tests:
   - Run offline suite on each change.
   - Alert if any metric drops below thresholds.
