from openai import OpenAI

from dotenv import load_dotenv
load_dotenv()

from src.agents.prompts import GENERATOR_PROMPT

client = OpenAI()


def generate_answer(query, evidence):

    if not evidence:
        return "Unable to determine the answer from available policy documents.\
Recommendation: Consult Legal or internal policy documentation."

    evidence_text = "\n\n".join(
        [
            f"{e['doc_id']} | {e['section']} | {e['timestamp']}\n{e['text']}"
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
            input=prompt
        )
        return response.output_text
    except Exception:
        return (
            "Unable to generate a grounded answer due to a system error.\n\n"
            "Citations:\n"
        )
