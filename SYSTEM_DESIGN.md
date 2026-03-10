# System Design: EOR Compliance Copilot (Prototype)

This document describes the system design for an evidence‑grounded EOR compliance copilot. It maps directly to the current implementation in this repository and is scoped to the assignment requirements.

## 1) Architecture

**Components and responsibilities**
- **`app.py`**: Orchestrates the workflow, handles clarifying questions, enforces output requirements, logs audit events, and applies safety guardrails for refusal/escalation.
- **`src/agents/retriever.py`**: Loads policy documents, applies country filtering, performs hybrid retrieval (BM25 + dense), and returns evidence with metadata (doc ID, section, timestamp, version, country, policy type, staleness).
- **`src/agents/generator.py`**: Uses the LLM to produce a structured JSON response with answer + citations + confidence + reason + escalation + follow‑up questions.
- **`src/agents/verifier.py`**: Validates grounding (citations match evidence), detects conflicts and staleness, identifies high‑risk topics and missing facts, and determines escalation/follow‑ups.
- **`src/agents/safety.py`**: Provides audit logging, PII redaction, and retention enforcement.
- **`evaluation/`**: Offline evaluation suite with a 10‑question test set and scoring script.

**Agent orchestration pattern**
- The system uses a **sequential pipeline with critic‑refine control**, not debate or manager‑worker:
  1. Retriever (tool‑like agent) gathers evidence.
  2. Generator produces the draft answer with citations.
  3. Verifier acts as a **critic**; if the draft is not grounded or is unsafe, the system refuses/escalates.
- This pattern minimizes hallucination by enforcing evidence‑first grounding and explicit refusal when evidence is insufficient.

**Data flow for a single query (step‑by‑step)**
1. **Clarify country**: `app.py` checks the query for country mentions based on loaded policies.
   - If none or multiple: ask a clarifying question and stop.
2. **Retrieve evidence**: `retriever.py` filters policies by country, runs hybrid retrieval, and returns top evidence chunks with metadata.
3. **Generate answer**: `generator.py` prompts the LLM to return JSON containing a final answer, citations, confidence, reason, escalation, and follow‑ups.
4. **Verify**: `verifier.py` ensures citations are valid, detects conflicts/staleness/high‑risk topics, and requests escalation if needed.
5. **Finalize output**: `app.py` prints the required output fields. If verification fails, it refuses and escalates.
6. **Audit log**: `safety.py` logs evidence trail, verification results, and escalation events with PII redaction and retention.

## 2) Knowledge & Data

**Document representation**
- Documents are stored as JSON in `data/policies/`.
- **Chunking**: Each policy `section` is a chunk. This preserves semantic boundaries (e.g., “Notice Period”) and yields precise citations.
- **Metadata**: Each chunk includes:
  - `doc_id`, `section`, `text`, `timestamp` (`last_updated`), `version`, `country`, `policy_type`.
- **Versioning**:
  - Documents include `version`.
  - Retrieval uses **latest version per `doc_id`**; older versions are preserved for auditability.

**Handling conflicting sources**
- The verifier groups evidence by `(country, policy_type, section)` and flags conflicts if texts differ.
- Any conflict triggers `confidence=Low` and escalation to Legal.

**Handling outdated policies**
- Policies older than the staleness threshold are marked `stale`.
- Stale evidence triggers `confidence=Low` and escalation.

**Country‑specific overrides**
- Retrieval requires country match based on the query; global policies are not used unless explicitly present.
- In case of overlapping policy types, country‑specific evidence is prioritized because retrieval is country‑scoped.

**Citation definition**
- A citation is the tuple: **`doc_id | section | timestamp`**.
- Example: `FR_notice_v1 | Notice Period | 2025-01-01`.

## 3) Prompting / Reasoning Strategy

**Prompts per agent**
- **Generator** (`src/agents/prompts.py`): Instructed to:
  - Use only evidence.
  - Return strictly valid JSON with required fields.
  - Include citations for every claim.
  - Mark insufficiency if evidence does not support an answer.
- **Verifier**: Implements deterministic checks rather than LLM prompting:
  - Conflicts, staleness, high‑risk topics, missing facts, and citation validity.

**Grounded answer enforcement**
- The generator must output citations in JSON format.
- The verifier checks that each citation matches retrieved evidence.
- If citations are missing or invalid, the system refuses and escalates.

**Clarifying questions vs. answering**
- **Ask clarifying questions** when:
  - Country is missing.
  - Multiple countries are present.
  - Required factual inputs are missing (tenure, contract type, union involvement).
- **Answer** only when:
  - Evidence is retrieved,
  - Citations match evidence,
  - No conflicts or stale docs, and
  - The query is not high‑risk without sufficient detail.

**Multilingual support**
- Queries are language‑detected and translated to English for retrieval and generation.
- Final answers and follow‑up questions are translated back to the user’s language.
- Citations remain unchanged (doc ID | section | timestamp).

## 4) Safety, Privacy, and Governance

**Guardrails (refusal/escalation)**
- High‑risk topics (termination, discrimination, protected classes) trigger escalation.
- Conflicting or outdated evidence triggers escalation.
- Missing key facts triggers clarification.
- Only `confidence=Medium` and `escalation=None` yields a final answer.

**Audit logging plan**
- Logs evidence trail and verification results with timestamps.
- Logging is structured JSON for auditability.

**PII handling and retention**
- All audit payloads are passed through PII redaction (email/phone).
- Retention enforced by rolling log cleanup (default 90 days).
- Only metadata is logged (no full policy text).

**Human‑in‑the‑loop workflow**
- When escalated, the system refuses to answer and instructs the user to consult Legal.
- Logs capture the escalation reason for review.

## 5) Evaluation Plan

**10 test questions (mix easy + tricky + adversarial)**
Stored in `evaluation/test_queries.json`, including:
- Standard coverage for DE/FR/IT/NL/PL/ES.
- Ambiguous country.
- High‑risk termination/discrimination.
- Unanswerable queries (hallucination trap).
- Adversarial query containing PII.

**Expected “good” behavior**
- Each test includes `expected_behavior` for human review.

**Offline evaluation: criteria + scoring**
Implemented in `evaluation/retrieval_eval.py`:
- **Recall@3** (retrieval quality).
- **Citation validity** (grounded answers).
- **Clarifying behavior accuracy** (ask vs answer).
- **Escalation accuracy** (safety compliance).

**Online evaluation / A/B testing idea**
- A/B test baseline vs reranking:
  - A: hybrid retrieval + strict verifier.
  - B: add LLM or cross‑encoder reranking for evidence selection.
- Measure: acceptance rate, citation validity, escalation rate, and user satisfaction proxy.

**Monitoring hallucinations and regressions**
- Track citation validity over time.
- Alert on spikes in escalation or invalid citations.
- Run offline test suite on each change; block deploy on metric regression.

## 6) Production Considerations

**Latency/cost tradeoffs**
- Dense embeddings and LLM calls are the primary cost drivers.
- Optimizations:
  - Precompute and cache policy embeddings.
  - Reduce top‑k or add reranking only when necessary.
  - Use smaller models by default; upgrade only when precision is required.

**Monitoring signals**
- Quality: Recall@3, citation validity, clarification accuracy.
- Safety: escalation rate, conflict/stale detections.
- Tool failures: LLM errors, retrieval failures.
- Drift: changes in escalation and citation validity over time.

**Rollout strategy + fallback**
- Stage 1: internal users with full audit logging.
- Stage 2: limited beta + A/B test.
- Stage 3: gradual rollout with KPI regression gates.
- Fallback behavior:
  - LLM failure: safe refusal + escalation.
  - No evidence/conflict/stale: refuse + escalate.
  - Missing facts: ask clarifying questions.
