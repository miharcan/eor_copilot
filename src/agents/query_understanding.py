import re

POLICY_TYPES = [
    "onboarding",
    "notice",
    "termination",
    "payroll",
    "benefits",
]

COUNTRY_ALIASES = {
    "germany": ["germany", "de", "deutschland"],
    "france": ["france", "fr"],
    "italy": ["italy", "it", "italia"],
    "netherlands": ["netherlands", "nl", "holland", "the netherlands"],
    "poland": ["poland", "pl", "polska"],
    "spain": ["spain", "es", "espana", "españa"],
}

def extract_entities(query):
    q = query.lower()

    countries = []
    for canonical, aliases in COUNTRY_ALIASES.items():
        if any(a in q for a in aliases):
            countries.append(canonical)

    policy_types = []
    for p in POLICY_TYPES:
        if p in q:
            policy_types.append(p)

    tenure = None
    tenure_match = re.search(r"(\d+)\s*(year|years|month|months)", q)
    if tenure_match:
        tenure = tenure_match.group(0)

    contract_type = None
    for ct in ["fixed-term", "fixed term", "permanent", "probation"]:
        if ct in q:
            contract_type = ct
            break

    union = None
    if "union" in q or "collective bargaining" in q:
        union = True

    return {
        "countries": countries,
        "policy_types": policy_types,
        "tenure": tenure,
        "contract_type": contract_type,
        "union_involved": union,
    }
