from openai import OpenAI
from dotenv import load_dotenv

from src.agents.prompts import GENERATOR_PROMPT

load_dotenv()

client = OpenAI()


def generate_answer(query, evidence):

    if not evidence:
        return (
            "Final Answer:\n"
            "Unable to determine the answer from available policy documents.\n\n"
            "Citations:\n"
            "None\n\n"
            "Confidence:\n"
            "Low\n\n"
            "Reason:\n"
            "No relevant policy evidence was retrieved.\n\n"
            "Escalation:\n"
            "Consult Legal or internal policy documentation.\n\n"
            "Follow-up Questions:\n"
            "Please clarify the country, policy area, or employment context.\n"
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
        return response.output_text
    except Exception:
        return (
            "Final Answer:\n"
            "Unable to generate a grounded answer due to a system error.\n\n"
            "Citations:\n"
            "None\n\n"
            "Confidence:\n"
            "Low\n\n"
            "Reason:\n"
            "The generator encountered a system error.\n\n"
            "Escalation:\n"
            "Consult Legal or retry with updated policy evidence.\n\n"
            "Follow-up Questions:\n"
            "None\n"
        )
