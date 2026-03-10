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

def _needs_additional_facts(query):
    q = query.lower()
    needs_tenure = ("notice" in q or "notice period" in q) and not any(
        k in q for k in ["year", "years", "month", "months", "tenure"]
    )
    needs_contract_type = ("termination" in q or "terminate" in q) and not any(
        k in q for k in ["contract type", "fixed-term", "permanent", "probation"]
    )
    needs_union = ("union" in q or "collective bargaining" in q) and "union" not in q
    return needs_tenure or needs_contract_type or needs_union

def _missing_fact_questions(query):
    q = query.lower()
    questions = []
    if ("notice" in q or "notice period" in q) and not any(
        k in q for k in ["year", "years", "month", "months", "tenure"]
    ):
        questions.append("What is the employee's tenure?")
    if ("termination" in q or "terminate" in q) and not any(
        k in q for k in ["contract type", "fixed-term", "permanent", "probation"]
    ):
        questions.append("What is the contract type (permanent, fixed-term, probation)?")
    if "union" in q or "collective bargaining" in q:
        questions.append("Is a union or collective bargaining agreement applicable?")
    return questions

def _high_risk_area(query):
    q = query.lower()
    return any(
        k in q
        for k in [
            "termination",
            "dismissal",
            "discrimination",
            "harassment",
            "protected class",
            "retaliation",
        ]
    )


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
            "escalation": "Consult Legal",
            "follow_up_questions": ["Which country does this question apply to?"]
        }

    citations = draft_answer.get("citations", [])

    if not _citations_match_evidence(citations, evidence):
        return {
            "confidence": "Low",
            "reason": "Missing or invalid citations.",
            "escalation": "Consult Legal",
            "follow_up_questions": []
        }

    if _needs_additional_facts(query):
        return {
            "confidence": "Low",
            "reason": "Missing key facts (tenure, contract type, or union involvement).",
            "escalation": "Ask for clarification",
            "follow_up_questions": _missing_fact_questions(query)
        }

    if _high_risk_area(query):
        return {
            "confidence": "Low",
            "reason": "High-risk legal topic detected.",
            "escalation": "Consult Legal",
            "follow_up_questions": []
        }

    if _has_conflicts(evidence):
        return {
            "confidence": "Low",
            "reason": "Conflicting policy sources detected.",
            "escalation": "Consult Legal",
            "follow_up_questions": []
        }

    if _has_stale(evidence):
        return {
            "confidence": "Low",
            "reason": "One or more policies appear outdated.",
            "escalation": "Consult Legal",
            "follow_up_questions": []
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
            "escalation": "Consult Legal",
            "follow_up_questions": []
        }

    return {
        "confidence": "Medium",
        "reason": "Answer supported by retrieved policy evidence.",
        "escalation": "None",
        "follow_up_questions": []
    }
