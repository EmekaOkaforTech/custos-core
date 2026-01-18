from app.ingestion.rules import extract_commitments, extract_risk_flags


def test_commitment_rules_dedup_and_placeholder():
    empty = extract_commitments("")
    assert empty[0].rule_id == "commitment_placeholder"

    payload = "Plan next steps\n- Send summary\n- Send summary"
    commitments = extract_commitments(payload)
    texts = [item.text for item in commitments]
    assert texts == ["Plan next steps", "Send summary"]


def test_risk_flag_rules_are_neutral():
    payload = "Blocked by vendor\nDue Friday"
    flags = extract_risk_flags(payload)
    types = {flag.flag_type for flag in flags}
    assert types == {"deadline_reference", "blocker_reference"}
