import json
from src.agents.retriever import retrieve, load_policies
from src.agents.generator import generate_answer


def recall_at_k(test_cases, k=3):

    correct = 0

    for case in test_cases:

        query = case["query"]
        expected = case["expected_doc"]

        results = retrieve(query)

        retrieved_docs = [r["doc_id"] for r in results[:k]]

        if expected in retrieved_docs:
            correct += 1

    return correct / len(test_cases)


def _extract_citations(draft_answer):
    citations = []
    if "Citations:" not in draft_answer:
        return citations
    _, tail = draft_answer.split("Citations:", 1)
    for line in tail.splitlines():
        line = line.strip()
        if not line:
            continue
        if "|" not in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) != 3:
            continue
        citations.append(tuple(parts))
    return citations


def _citations_match_evidence(citations, evidence):
    if not citations:
        return False
    index = set(
        (
            str(e.get("doc_id")),
            str(e.get("section")),
            str(e.get("timestamp")),
        )
        for e in evidence
    )
    for c in citations:
        if c not in index:
            return False
    return True


def citation_validity(test_cases):

    correct = 0

    for case in test_cases:

        query = case["query"]

        evidence = retrieve(query)

        answer = generate_answer(query, evidence)

        citations = _extract_citations(answer)

        if _citations_match_evidence(citations, evidence):
            correct += 1

    return correct / len(test_cases)

def _extract_countries():
    countries = set()
    for policy in load_policies():
        country = policy.get("country")
        if country:
            countries.add(country.lower())
    return countries


def _needs_clarification(query, countries):
    query_lower = query.lower()
    detected = [c for c in countries if c in query_lower]
    return len(detected) == 0 or len(detected) > 1


def clarity_behavior_accuracy(test_cases):

    countries = _extract_countries()
    correct = 0

    for case in test_cases:
        query = case["query"]
        expected = case.get("expected_clarify", False)
        predicted = _needs_clarification(query, countries)
        if predicted == expected:
            correct += 1

    return correct / len(test_cases)


def run_evaluation():

    with open("evaluation/test_queries.json") as f:
        test_cases = json.load(f)

    r_at_3 = recall_at_k(test_cases, k=3)
    citation = citation_validity(test_cases)
    clarity = clarity_behavior_accuracy(test_cases)

    print("\nRetrieval / Reasoning Evaluation")
    print("--------------------------------")

    print("Recall@3:", r_at_3)
    print("Citation validity:", citation)
    print("Clarifying behavior accuracy:", clarity)


if __name__ == "__main__":
    run_evaluation()
