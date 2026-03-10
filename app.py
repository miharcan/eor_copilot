import time
import json

from src.agents.retriever import retrieve, load_policies
from src.agents.generator import generate_answer
from src.agents.verifier import verify
from src.agents.safety import audit_log, redact_pii


def _extract_countries():
    countries = set()
    for policy in load_policies():
        country = policy.get("country")
        if country:
            countries.add(country.lower())
    return countries


def _detect_countries_in_query(query, countries):
    query_lower = query.lower()
    return [c for c in countries if c in query_lower]


def run_query(query):

    countries = _extract_countries()
    detected = _detect_countries_in_query(query, countries)
    if len(detected) == 0:
        print("\nFinal Answer:")
        print("Unable to answer without country context.")
        print("\nCitations:")
        print("None")
        print("\nConfidence:")
        print("Low")
        print("\nReason:")
        print("Country is missing.")
        print("\nEscalation:")
        print("Ask for clarification")
        print("\nFollow-up Questions:")
        print("Which country does this question apply to?")
        audit_log("clarify_country_missing", {"query": redact_pii(query)})
        return
    if len(detected) > 1:
        print("\nFinal Answer:")
        print("Unable to answer without a single country context.")
        print("\nCitations:")
        print("None")
        print("\nConfidence:")
        print("Low")
        print("\nReason:")
        print("Multiple countries detected.")
        print("\nEscalation:")
        print("Ask for clarification")
        print("\nFollow-up Questions:")
        print(f"Multiple countries detected ({', '.join(detected)}). Which one applies?")
        audit_log("clarify_country_ambiguous", {"query": redact_pii(query), "countries": detected})
        return

    print("\nQuery:")
    print(query)

    t0 = time.time()
    evidence = retrieve(query)
    t_retrieval_ms = int((time.time() - t0) * 1000)

    print("\nRetrieved Evidence:")

    if not evidence:
        print("None")
    else:
        for e in evidence:
            print(f"{e['doc_id']} - {e['section']}")
        audit_log(
            "evidence_trail",
            {
                "query": redact_pii(query),
                "evidence": [
                    {
                        "doc_id": e.get("doc_id"),
                        "section": e.get("section"),
                        "timestamp": e.get("timestamp"),
                        "version": e.get("version"),
                    }
                    for e in evidence
                ],
            },
        )

    t1 = time.time()
    draft_raw = generate_answer(query, evidence)

    if isinstance(draft_raw, dict):
        draft = draft_raw
    else:
        try:
            draft = json.loads(draft_raw)
        except Exception:
            draft = {
                "final_answer": "Unable to determine the answer from available policy evidence.",
                "citations": [],
                "confidence": "Low",
                "reason": "Generator returned invalid or empty JSON.",
                "escalation": "Consult Legal",
                "follow_up_questions": []
            }

    t_generation_ms = int((time.time() - t1) * 1000)

    print("\nDraft Answer:")
    print(draft.get("final_answer", ""))

    print("\nDraft Citations:")
    if draft.get("citations"):
        for c in draft["citations"]:
            print(f"{c['doc_id']} | {c['section']} | {c['timestamp']}")
    else:
        print("None")

    verification = verify(query, draft, evidence)
    audit_log(
        "verification",
        {
            "query": redact_pii(query),
            "confidence": verification.get("confidence"),
            "reason": verification.get("reason"),
            "escalation": verification.get("escalation"),
            "evidence_ids": [e.get("doc_id") for e in evidence],
            "citations": draft.get("citations", []),
            "latency_ms": {
                "retrieval": t_retrieval_ms,
                "generation": t_generation_ms,
            },
        },
    )

    print("\nVerifier Feedback:")
    print(verification)

    # Final Answer output block
    final_answer = draft.get("final_answer", "")
    citations = draft.get("citations", [])
    confidence = verification.get("confidence")
    reason = verification.get("reason")
    escalation = verification.get("escalation")
    follow_up = verification.get("follow_up_questions") or draft.get("follow_up_questions", [])

    if confidence != "Medium" or escalation != "None":
        final_answer = "Unable to provide a grounded answer. Escalation required: " + escalation
        citations = []
        audit_log(
            "escalation",
            {
                "query": redact_pii(query),
                "reason": verification.get("reason"),
                "escalation": verification.get("escalation"),
            },
        )

    print("\nFinal Answer:")
    print(final_answer)

    print("\nCitations:")
    if citations:
        for c in citations:
            print(f"{c['doc_id']} | {c['section']} | {c['timestamp']}")
    else:
        print("None")

    print("\nConfidence:")
    print(confidence)

    print("\nReason:")
    print(reason)

    print("\nEscalation:")
    print(escalation)

    print("\nFollow-up Questions:")
    if follow_up:
        for q in follow_up:
            print(q)
    else:
        print("None")


if __name__ == "__main__":
    try:        
        with open("evaluation/test_queries.json") as f:
            test_cases = json.load(f)
        for case in test_cases:
            run_query(case["query"])
    except Exception:
        run_query("Can we terminate during probation in Germany?")
