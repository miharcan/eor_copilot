import time

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
        print("\nClarifying Question:")
        print("Which country does this question apply to?")
        audit_log("clarify_country_missing", {"query": redact_pii(query)})
        return
    if len(detected) > 1:
        print("\nClarifying Question:")
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

    print("\nCitations:")

    if not evidence:
        print("None")
    else:
        for e in evidence:
            print(f"{e['doc_id']} §{e['section']} ({e['timestamp']})")

    t1 = time.time()
    draft = generate_answer(query, evidence)
    t_generation_ms = int((time.time() - t1) * 1000)

    print("\nDraft Answer:")
    print(draft)

    verification = verify(query, draft, evidence)
    audit_log(
        "verification",
        {
            "query": redact_pii(query),
            "confidence": verification.get("confidence"),
            "reason": verification.get("reason"),
            "escalation": verification.get("escalation"),
            "evidence_ids": [e.get("doc_id") for e in evidence],
            "latency_ms": {
                "retrieval": t_retrieval_ms,
                "generation": t_generation_ms,
            },
        },
    )

    print("\nVerifier Feedback:")
    print(verification)

    print("\nFinal Answer:")
    if verification.get("confidence") != "Medium" or verification.get("escalation") != "None":
        print(
            "Unable to provide a grounded answer. "
            "Escalation required: " + verification.get("escalation", "Consult Legal.")
        )
        audit_log(
            "escalation",
            {
                "query": redact_pii(query),
                "reason": verification.get("reason"),
                "escalation": verification.get("escalation"),
            },
        )
    else:
        print(draft)

    print("\nConfidence:", verification["confidence"])
    print("Reason:", verification["reason"])
    print("Escalation:", verification["escalation"])


if __name__ == "__main__":

    run_query("Can we terminate during probation in Germany?")
    run_query("What documents are required to onboard an employee in Poland?")
    run_query("What notice period applies in France for two years tenure?")
    run_query("What is the payroll cutoff for Italy?")
    run_query("Is private health insurance mandatory in the Netherlands?")
    run_query("What maternity leave rules apply in Poland?")
