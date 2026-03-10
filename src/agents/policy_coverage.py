from collections import defaultdict

from src.agents.retriever import load_policies

EXPECTED_POLICY_TYPES = [
    "onboarding",
    "notice",
    "termination",
    "payroll",
    "benefits",
]


def coverage_report():
    coverage = defaultdict(set)
    for policy in load_policies():
        country = policy.get("country")
        policy_type = policy.get("policy_type")
        if country and policy_type:
            coverage[country].add(policy_type)

    report = {}
    for country, types in coverage.items():
        missing = [t for t in EXPECTED_POLICY_TYPES if t not in types]
        report[country] = {
            "present": sorted(types),
            "missing": missing,
        }
    return report
