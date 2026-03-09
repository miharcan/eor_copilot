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


def _citations_match_evidence(citations, evidence):
    if not citations:
        return False

    evidence_index = {
        (
            str(e.get("doc_id")),
            str(e.get("section")),
            str(e.get("timestamp")),
        )
        for e in evidence
    }

    for c in citations:
        citation_tuple = (
            str(c.get("doc_id")),
            str(c.get("section")),
            str(c.get("timestamp")),
        )

        if citation_tuple not in evidence_index:
            return False

    return True


def verify(query, draft_answer, evidence):
    if not evidence:
        return {
            "confidence": "Low",
            "reason": "No evidence retrieved.",
            "escalation": "Consult Legal or policy documentation."
        }

    citations = draft_answer.get("citations", [])

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

    answer_text = (draft_answer.get("final_answer") or "").lower()
    if any(
        phrase in answer_text
        for phrase in [
            "insufficient",
            "unable to determine",
            "does not contain information",
            "cannot determine",
        ]
    ):
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