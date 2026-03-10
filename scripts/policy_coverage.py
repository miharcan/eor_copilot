import json
from src.agents.policy_coverage import coverage_report

if __name__ == "__main__":
    report = coverage_report()
    print(json.dumps(report, indent=2))
