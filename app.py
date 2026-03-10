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

def _print_block(title, lines):
    print(f"\n== {title} ==")
    if not lines:
        print("None")
        return
    for line in lines:
        print(line)

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
        _print_block("Final Answer", [final_answer])
        _print_block("Citations", [])
        _print_block("Confidence", ["Low"])
        _print_block("Reason", [reason])
        _print_block("Escalation", ["Ask for clarification"])
        _print_block("Follow-up Questions", [follow_up])
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
        _print_block("Final Answer", [final_answer])
        _print_block("Citations", [])
        _print_block("Confidence", ["Low"])
        _print_block("Reason", [reason])
        _print_block("Escalation", ["Ask for clarification"])
        _print_block("Follow-up Questions", [follow_up])
        audit_log(
            "clarify_country_ambiguous",
            {"query": redact_pii(original_query), "countries": detected, "lang": lang}
        )
        return

    print("\n" + "=" * 60)
    print(f"Query: {original_query}")
    print(f"Language: {lang}")
    entities = extract_entities(query_for_processing)
    audit_log(
        "query_entities",
        {"query": redact_pii(original_query), "entities": entities, "lang": lang}
    )

    t0 = time.time()
    evidence = retrieve(query_for_processing)
    t_retrieval_ms = int((time.time() - t0) * 1000)

    evidence_lines = [
        f"{e['doc_id']} - {e['section']} ({e['timestamp']})" for e in evidence
    ]
    _print_block("Retrieved Evidence", evidence_lines)
    if evidence:
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

    if evidence and not draft.get("citations"):
        draft["citations"] = [
            {
                "doc_id": e.get("doc_id"),
                "section": e.get("section"),
                "timestamp": e.get("timestamp"),
            }
            for e in evidence
        ]
        if not draft.get("reason"):
            draft["reason"] = "Citations added from retrieved evidence."

    if not draft.get("final_answer"):
        draft["final_answer"] = "Unable to determine the answer from available policy evidence."

    refusal_phrases = [
        "unable to provide a grounded answer",
        "unable to determine",
        "insufficient",
        "does not contain information",
        "cannot determine",
    ]
    if evidence and any(p in draft["final_answer"].lower() for p in refusal_phrases):
        # Deterministic fallback: extract a concise answer from evidence.
        evidence_summary = " ".join(
            [f"{e['text']}" for e in evidence]
        )
        draft["final_answer"] = (
            "Based on the policy evidence: " + evidence_summary
        )
        if not draft.get("reason"):
            draft["reason"] = "Answer derived from retrieved evidence."

    t_generation_ms = int((time.time() - t1) * 1000)

    _print_block("Draft Answer", [draft.get("final_answer", "")])
    draft_citations = [
        f"{c['doc_id']} | {c['section']} | {c['timestamp']}"
        for c in draft.get("citations", [])
    ]
    _print_block("Draft Citations", draft_citations)

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

    _print_block("Verifier Feedback", [json.dumps(verification)])

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

    _print_block("Final Answer", [final_answer])
    final_citations = [
        f"{c['doc_id']} | {c['section']} | {c['timestamp']}" for c in citations
    ]
    _print_block("Citations", final_citations)
    _print_block("Confidence", [confidence])
    _print_block("Reason", [reason])
    _print_block("Escalation", [escalation])
    _print_block("Follow-up Questions", follow_up)


if __name__ == "__main__":
    try:        
        with open("evaluation/test_queries.json") as f:
            test_cases = json.load(f)
        for case in test_cases:
            run_query(case["query"])
    except Exception:
        run_query("Can we terminate during probation in Germany?")
