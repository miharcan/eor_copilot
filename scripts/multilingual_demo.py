from src.agents.translation import detect_language
from app import run_query


DEMO_QUERIES = [
    "Was ist die Kündigungsfrist in Frankreich bei zwei Jahren Betriebszugehörigkeit?",
    "¿Qué documentos se requieren para incorporar a un empleado en Polonia?",
    "Quelle est la date limite de paie en Italie?",
]


if __name__ == "__main__":
    for q in DEMO_QUERIES:
        lang = detect_language(q)
        print(f"\n--- Demo Query ({lang}) ---")
        run_query(q)
