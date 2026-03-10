import json
import os
import re
from datetime import datetime, timedelta

AUDIT_LOG_PATH = "audit.log"
RETENTION_DAYS = 365  # 1 year

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(r"\b(\+?\d[\d\s().-]{7,}\d)\b")


def redact_pii(text):
    if not text:
        return text
    redacted = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    redacted = _PHONE_RE.sub("[REDACTED_PHONE]", redacted)
    return redacted

def sanitize_payload(payload):
    if isinstance(payload, str):
        return redact_pii(payload)
    if isinstance(payload, list):
        return [sanitize_payload(v) for v in payload]
    if isinstance(payload, dict):
        return {k: sanitize_payload(v) for k, v in payload.items()}
    return payload


def _purge_old_entries(lines):
    cutoff = datetime.utcnow() - timedelta(days=RETENTION_DAYS)
    kept = []
    for line in lines:
        try:
            record = json.loads(line)
            ts = datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00"))
            if ts >= cutoff:
                kept.append(line)
        except Exception:
            kept.append(line)
    return kept


def audit_log(event, payload):
    record = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event": event,
        "payload": sanitize_payload(payload),
    }
    os.makedirs(os.path.dirname(AUDIT_LOG_PATH) or ".", exist_ok=True)
    if os.path.exists(AUDIT_LOG_PATH):
        with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        lines = _purge_old_entries(lines)
    else:
        lines = []
    lines.append(json.dumps(record, ensure_ascii=True) + "\n")
    with open(AUDIT_LOG_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)
