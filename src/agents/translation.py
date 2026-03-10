from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()


def detect_language(text):
    if not text:
        return "en"
    prompt = (
        "Detect the language of the following text and return ONLY the ISO 639-1 "
        "language code (e.g., en, de, fr, es). If uncertain, return en.\n\n"
        f"Text:\n{text}"
    )
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt,
            temperature=0
        )
        code = response.output_text.strip().lower()
        if len(code) == 2 and code.isalpha():
            return code
    except Exception:
        pass
    return "en"


def translate_text(text, target_lang, source_lang=None):
    if not text:
        return text
    if source_lang and source_lang == target_lang:
        return text
    prompt = (
        "Translate the text to the target language. Preserve doc IDs, section titles, "
        "timestamps, and citations exactly as written. Return only the translation.\n\n"
        f"Target language: {target_lang}\n"
        f"Source language: {source_lang or 'auto'}\n\n"
        f"Text:\n{text}"
    )
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt,
            temperature=0
        )
        return response.output_text.strip()
    except Exception:
        return text
