import json

from openai import OpenAI
from dotenv import load_dotenv

from src.agents.prompts import GENERATOR_PROMPT

load_dotenv()

client = OpenAI()

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "for", "is", "are", "be",
    "what", "can", "we", "does", "do", "with", "without", "during", "apply",
    "applies", "this", "that", "it", "its", "on", "by", "from", "as", "at",
}


def _tokenize(text):
    return [t for t in "".join(ch.lower() if ch.isalnum() else " " for ch in text).split() if t]


def _overlap_ok(query, evidence):
    q_tokens = [t for t in _tokenize(query) if t not in _STOPWORDS and len(t) > 2]
    if not q_tokens:
        return False
    evidence_text = " ".join(e.get("text", "") for e in evidence)
    e_tokens = set(_tokenize(evidence_text))
    overlap = [t for t in q_tokens if t in e_tokens]
    return len(overlap) >= 2 and (len(overlap) / max(1, len(q_tokens))) >= 0.2


def _fallback_response(reason, escalation, follow_up_questions=None):
    return {
        "final_answer": "Unable to provide a grounded answer.",
        "citations": [],
        "confidence": "Low",
        "reason": reason,
        "escalation": escalation,
        "follow_up_questions": follow_up_questions or [],
    }


def generate_answer(query, evidence):

    if not evidence:
        return _fallback_response(
            "No relevant policy evidence was retrieved.",
            "Consult Legal",
            ["Which country does this question apply to?"],
        )

    evidence_text = "\n\n".join(
        [
            (
                f"Policy: {e['doc_id']}\n"
                f"Section: {e['section']}\n"
                f"Timestamp: {e['timestamp']}\n"
                f"Text: {e['text']}"
            )
            for e in evidence
        ]
    )

    prompt = f"""{GENERATOR_PROMPT}

Question:
{query}

Evidence:
{evidence_text}
"""

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt,
            temperature=0
        )
        raw = response.output_text.strip()
        draft = json.loads(raw)
    except Exception:
        draft = _fallback_response(
            "The generator encountered a system error or invalid JSON.",
            "Consult Legal",
        )

    if evidence and not draft.get("citations"):
        draft["citations"] = [
            {
                "doc_id": e.get("doc_id"),
                "section": e.get("section"),
                "timestamp": e.get("timestamp"),
            }
            for e in evidence
        ]

    refusal_phrases = [
        "unable to provide a grounded answer",
        "unable to determine",
        "insufficient",
        "does not contain information",
        "cannot determine",
    ]
    if evidence and any(p in (draft.get("final_answer") or "").lower() for p in refusal_phrases):
        if _overlap_ok(query, evidence):
            evidence_summary = " ".join([f"{e['text']}" for e in evidence])
            draft["final_answer"] = "Based on the policy evidence: " + evidence_summary
            if not draft.get("reason"):
                draft["reason"] = "Answer derived from retrieved evidence."
        else:
            # Keep refusal if evidence doesn't meaningfully overlap the query.
            draft["final_answer"] = "Unable to determine the answer from available policy evidence."
            if not draft.get("reason"):
                draft["reason"] = "Evidence does not support a conclusion."

    return draft
