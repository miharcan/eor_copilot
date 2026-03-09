import re

def _has_conflicts(evidence):
    buckets = {}
    for e in evidence:
        key = (e.get("country"), e.get("policy_type"), e.get("section"))
        buckets.setdefault(key, set()).add(e.get("text"))
    for texts in buckets.values():
        if len(texts) > 1:
            return True
    return False

def _has_stale(evidence):
    return any(e.get("stale") for e in evidence)

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

def verify(query, draft_answer, evidence):

    if not evidence:
        return {
            "confidence": "Low",
            "reason": "No evidence retrieved.",
            "escalation": "Consult Legal or policy documentation."
        }

    citations = _extract_citations(draft_answer)
    if not _citations_match_evidence(citations, evidence):
        return {
            "confidence": "Low",
            "reason": "Missing or invalid citations.",
            "escalation": "Ask for clarification or consult Legal."
        }

    if _has_conflicts(evidence):
        return {
            "confidence": "Low",
            "reason": "Conflicting policy sources detected.",
            "escalation": "Escalate to Legal to resolve conflicting policies."
        }

    if _has_stale(evidence):
        return {
            "confidence": "Low",
            "reason": "One or more policies appear outdated.",
            "escalation": "Confirm with Legal or updated policy sources."
        }

    if "insufficient" in draft_answer.lower():
        return {
            "confidence": "Low",
            "reason": "Evidence does not support a conclusion.",
            "escalation": "Consult Legal."
        }

    return {
        "confidence": "Medium",
        "reason": "Answer supported by retrieved policy evidence.",
        "escalation": "None"
    }
