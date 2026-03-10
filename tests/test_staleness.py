from datetime import date, timedelta

from src.agents.retriever import _is_date_stale, STALE_DAYS_THRESHOLD


def test_is_date_stale_false_for_recent():
    recent = (date.today() - timedelta(days=30)).isoformat()
    assert _is_date_stale(recent) is False


def test_is_date_stale_true_for_old():
    old = (date.today() - timedelta(days=STALE_DAYS_THRESHOLD + 1)).isoformat()
    assert _is_date_stale(old) is True
