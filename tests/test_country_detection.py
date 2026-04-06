from src.agents.country_detection import (
    detect_supported_countries,
    detect_unsupported_country_mentions,
)


def test_detect_supported_country_from_query():
    supported = {"italy", "germany", "spain"}
    detected = detect_supported_countries("What is the payroll cutoff for Italy?", supported)
    assert detected == ["italy"]


def test_detect_unsupported_country_mention():
    supported = {"italy", "germany", "spain"}
    mentioned = detect_unsupported_country_mentions(
        "What is the payroll cutoff for Ireland?", supported
    )
    assert mentioned == ["ireland"]


def test_no_country_mention_returns_empty():
    supported = {"italy", "germany", "spain"}
    mentioned = detect_unsupported_country_mentions(
        "What is the payroll cutoff for remote contractors?", supported
    )
    assert mentioned == []
