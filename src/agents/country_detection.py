import re

_NON_COUNTRY_TERMS = {
    "payroll",
    "cutoff",
    "termination",
    "notice",
    "onboarding",
    "benefits",
    "policy",
    "policies",
    "employee",
    "employees",
    "contract",
    "contracts",
    "question",
    "company",
    "legal",
    "compliance",
    "eor",
    "probation",
    "tenure",
    "remote",
    "contractor",
    "contractors",
}

_COMMON_COUNTRY_NAMES = {
    "ireland",
    "united kingdom",
    "uk",
    "great britain",
    "england",
    "scotland",
    "wales",
    "united states",
    "usa",
    "canada",
    "france",
    "germany",
    "italy",
    "spain",
    "poland",
    "netherlands",
    "sweden",
    "norway",
    "denmark",
    "finland",
    "portugal",
    "greece",
    "belgium",
    "austria",
    "switzerland",
    "czech republic",
    "slovakia",
    "hungary",
    "romania",
    "bulgaria",
}


def _normalize_country_name(name):
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def detect_supported_countries(query, supported_countries):
    query_lower = (query or "").lower()
    detected = []
    for country in sorted({_normalize_country_name(c) for c in supported_countries if c}):
        if not country:
            continue
        pattern = r"\b" + re.escape(country) + r"\b"
        if re.search(pattern, query_lower):
            detected.append(country)
    return detected


def detect_unsupported_country_mentions(query, supported_countries):
    text = query or ""
    supported = {_normalize_country_name(c) for c in supported_countries if c}
    candidates = []

    pattern = re.compile(
        r"\b(?:for|in|within|across|regarding|about)\s+(?:the\s+)?([A-Za-z][A-Za-z'\-]*(?:\s+[A-Za-z][A-Za-z'\-]*){0,2})",
        re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        raw_candidate = match.group(1).strip("?.!,:; ")
        candidate = _normalize_country_name(raw_candidate)
        if not candidate:
            continue
        if candidate in supported:
            continue
        if candidate in _NON_COUNTRY_TERMS:
            continue
        tokens = [t for t in candidate.split() if t]
        if any(t in _NON_COUNTRY_TERMS for t in tokens):
            continue
        has_upper = any(ch.isupper() for ch in raw_candidate)
        if not has_upper and candidate not in _COMMON_COUNTRY_NAMES:
            continue
        if len(candidate) < 3:
            continue
        candidates.append(candidate)

    deduped = []
    seen = set()
    for candidate in candidates:
        if candidate not in seen:
            deduped.append(candidate)
            seen.add(candidate)
    return deduped
