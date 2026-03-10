from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()

# Optional offline translator (Argos Translate). Install separately if desired:
#   pip install argostranslate
# Then run:
#   argos-translate-cli --install from en to de
# This module will use Argos if available; otherwise it falls back to OpenAI.
try:
    from argostranslate import translate as _argos_translate
    _ARGOS_AVAILABLE = True
except Exception:
    _ARGOS_AVAILABLE = False


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
    # Offline path first if Argos is available.
    if _ARGOS_AVAILABLE:
        try:
            # Argos auto-detects source if not specified via translation model presence.
            return _argos_translate.translate(text, source_lang or "auto", target_lang)
        except Exception:
            # Fall back to OpenAI if offline translation fails.
            pass
    # Online fallback: OpenAI translation. You can swap this to another service here.
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
