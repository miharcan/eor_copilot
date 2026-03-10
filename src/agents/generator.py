import json

from openai import OpenAI
from dotenv import load_dotenv

from src.agents.prompts import GENERATOR_PROMPT

load_dotenv()

client = OpenAI()


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
        return json.loads(raw)
    except Exception:
        return _fallback_response(
            "The generator encountered a system error or invalid JSON.",
            "Consult Legal",
        )
