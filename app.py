import time
import json

from src.agents.retriever import retrieve, load_policies
from src.agents.generator import generate_answer
from src.agents.verifier import verify
from src.agents.safety import audit_log, redact_pii
from src.agents.query_understanding import extract_entities
from src.agents.translation import detect_language, translate_text


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

    original_query = query
    lang = detect_language(original_query)
    query_for_processing = original_query
    if lang != "en":
        query_for_processing = translate_text(original_query, "en", source_lang=lang)

    countries = _extract_countries()
    detected = _detect_countries_in_query(query_for_processing, countries)
    if len(detected) == 0:
        final_answer = "Unable to answer without country context."
        reason = "Country is missing."
        follow_up = "Which country does this question apply to?"
        if lang != "en":
            final_answer = translate_text(final_answer, lang, source_lang="en")
            reason = translate_text(reason, lang, source_lang="en")
            follow_up = translate_text(follow_up, lang, source_lang="en")
        print("\nFinal Answer:")
        print(final_answer)
        print("\nCitations:")
        print("None")
        print("\nConfidence:")
        print("Low")
        print("\nReason:")
        print(reason)
        print("\nEscalation:")
        print("Ask for clarification")
        print("\nFollow-up Questions:")
        print(follow_up)
        audit_log("clarify_country_missing", {"query": redact_pii(original_query), "lang": lang})
        return
    if len(detected) > 1:
        final_answer = "Unable to answer without a single country context."
        reason = "Multiple countries detected."
        follow_up = f"Multiple countries detected ({', '.join(detected)}). Which one applies?"
        if lang != "en":
            final_answer = translate_text(final_answer, lang, source_lang="en")
            reason = translate_text(reason, lang, source_lang="en")
            follow_up = translate_text(follow_up, lang, source_lang="en")
        print("\nFinal Answer:")
        print(final_answer)
        print("\nCitations:")
        print("None")
        print("\nConfidence:")
        print("Low")
        print("\nReason:")
        print(reason)
        print("\nEscalation:")
        print("Ask for clarification")
        print("\nFollow-up Questions:")
        print(follow_up)
        audit_log(
            "clarify_country_ambiguous",
            {"query": redact_pii(original_query), "countries": detected, "lang": lang}
        )
        return

    print("\nQuery:")
    print(original_query)
    entities = extract_entities(query_for_processing)
    audit_log(
        "query_entities",
        {"query": redact_pii(original_query), "entities": entities, "lang": lang}
    )

    t0 = time.time()
    evidence = retrieve(query_for_processing)
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
                "query": redact_pii(original_query),
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
    draft_raw = generate_answer(query_for_processing, evidence)

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

    verification = verify(query_for_processing, draft, evidence)
    audit_log(
        "verification",
        {
            "query": redact_pii(original_query),
            "confidence": verification.get("confidence"),
            "reason": verification.get("reason"),
            "escalation": verification.get("escalation"),
            "evidence_ids": [e.get("doc_id") for e in evidence],
            "citations": draft.get("citations", []),
            "lang": lang,
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

    if lang != "en":
        final_answer = translate_text(final_answer, lang, source_lang="en")
        reason = translate_text(reason, lang, source_lang="en")
        if escalation != "None":
            escalation = translate_text(escalation, lang, source_lang="en")
        follow_up = [translate_text(q, lang, source_lang="en") for q in follow_up]

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
