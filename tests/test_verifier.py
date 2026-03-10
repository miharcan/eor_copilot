from src.agents.verifier import verify


def test_verify_low_on_insufficient_answer():
    evidence = [
        {
            "doc_id": "DE_termination_v1",
            "section": "Termination During Probation",
            "timestamp": "2025-01-01",
            "text": "Employees may be terminated during probation with two weeks notice.",
            "country": "Germany",
            "policy_type": "termination",
            "stale": False,
        }
    ]
    draft = {
        "final_answer": "Unable to provide a grounded answer.",
        "citations": [
            {
                "doc_id": "DE_termination_v1",
                "section": "Termination During Probation",
                "timestamp": "2025-01-01",
            }
        ],
    }
    result = verify("Can we terminate during probation in Germany?", draft, evidence)
    assert result["confidence"] == "Low"
    assert result["escalation"] == "Consult Legal"


def test_verify_low_on_conflict():
    evidence = [
        {
            "doc_id": "FR_notice_v1",
            "section": "Notice Period",
            "timestamp": "2025-01-01",
            "text": "Two months notice.",
            "country": "France",
            "policy_type": "notice",
            "stale": False,
        },
        {
            "doc_id": "FR_notice_v2",
            "section": "Notice Period",
            "timestamp": "2025-06-01",
            "text": "Three months notice.",
            "country": "France",
            "policy_type": "notice",
            "stale": False,
        },
    ]
    draft = {
        "final_answer": "Two months notice.",
        "citations": [
            {
                "doc_id": "FR_notice_v1",
                "section": "Notice Period",
                "timestamp": "2025-01-01",
            }
        ],
    }
    result = verify("What notice period applies in France?", draft, evidence)
    assert result["confidence"] == "Low"
    assert result["escalation"] == "Consult Legal"


def test_verify_low_on_stale():
    evidence = [
        {
            "doc_id": "IT_payroll_v1",
            "section": "Payroll Cutoff",
            "timestamp": "2025-01-01",
            "text": "Payroll inputs must be submitted by the 20th.",
            "country": "Italy",
            "policy_type": "payroll",
            "stale": True,
        }
    ]
    draft = {
        "final_answer": "Payroll inputs must be submitted by the 20th.",
        "citations": [
            {
                "doc_id": "IT_payroll_v1",
                "section": "Payroll Cutoff",
                "timestamp": "2025-01-01",
            }
        ],
    }
    result = verify("What is the payroll cutoff for Italy?", draft, evidence)
    assert result["confidence"] == "Low"
    assert result["escalation"] == "Consult Legal"


def test_verify_missing_facts_asks_clarification():
    evidence = [
        {
            "doc_id": "DE_termination_v1",
            "section": "Termination During Probation",
            "timestamp": "2025-01-01",
            "text": "Employees may be terminated during probation with two weeks notice.",
            "country": "Germany",
            "policy_type": "termination",
            "stale": False,
        }
    ]
    draft = {
        "final_answer": "Employees may be terminated with two weeks notice.",
        "citations": [
            {
                "doc_id": "DE_termination_v1",
                "section": "Termination During Probation",
                "timestamp": "2025-01-01",
            }
        ],
    }
    result = verify("Can we terminate an employee in Germany?", draft, evidence)
    assert result["confidence"] == "Low"
    assert result["escalation"] == "Ask for clarification"
