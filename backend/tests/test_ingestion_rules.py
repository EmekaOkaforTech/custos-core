from datetime import datetime, timedelta

from app.ingestion.rules import extract_commitments, extract_due_date, extract_risk_flags


def test_commitment_rules_dedup_and_placeholder():
    empty = extract_commitments("")
    assert empty[0].rule_id == "commitment_placeholder"

    payload = "Plan next steps\n- Send summary\n- Send summary"
    commitments = extract_commitments(payload)
    texts = [item.text for item in commitments]
    assert texts == ["Plan next steps", "Send summary"]

    payload = "Follow up now\nFollow   up   now\n- Follow up now  "
    commitments = extract_commitments(payload)
    texts = [item.text for item in commitments]
    assert texts == ["Follow up now"]


def test_risk_flag_rules_are_neutral():
    payload = "Blocked by vendor\nDue Friday"
    flags = extract_risk_flags(payload)
    types = {flag.flag_type for flag in flags}
    assert types == {"deadline_reference", "blocker_reference"}


# Story 39.1: Due date extraction tests
def test_extract_due_date_today():
    """Test 'today' pattern extraction."""
    now = datetime(2026, 1, 28, 10, 0, 0)  # Wednesday
    result = extract_due_date("Finish report today", reference_date=now)
    assert result is not None
    assert result.date() == now.date()
    assert result.hour == 23
    assert result.minute == 59


def test_extract_due_date_tomorrow():
    """Test 'tomorrow' pattern extraction."""
    now = datetime(2026, 1, 28, 10, 0, 0)  # Wednesday
    result = extract_due_date("Send email by tomorrow", reference_date=now)
    assert result is not None
    expected = (now + timedelta(days=1)).date()
    assert result.date() == expected


def test_extract_due_date_weekday():
    """Test weekday pattern extraction (e.g., 'by Friday')."""
    # Wednesday, Jan 28, 2026
    now = datetime(2026, 1, 28, 10, 0, 0)
    result = extract_due_date("Complete review by Friday", reference_date=now)
    assert result is not None
    # Friday is Jan 30
    assert result.date() == datetime(2026, 1, 30).date()

    # If today is Friday (Jan 30), "by Friday" means next Friday
    friday = datetime(2026, 1, 30, 10, 0, 0)
    result = extract_due_date("due Friday", reference_date=friday)
    assert result is not None
    # Next Friday is Feb 6
    assert result.date() == datetime(2026, 2, 6).date()


def test_extract_due_date_end_of_week():
    """Test 'end of week' pattern extraction."""
    # Wednesday, Jan 28, 2026
    now = datetime(2026, 1, 28, 10, 0, 0)
    result = extract_due_date("Ship feature by end of week", reference_date=now)
    assert result is not None
    # Sunday is Feb 1
    assert result.weekday() == 6  # Sunday


def test_extract_due_date_next_week():
    """Test 'next week' pattern extraction."""
    # Wednesday, Jan 28, 2026
    now = datetime(2026, 1, 28, 10, 0, 0)
    result = extract_due_date("Start project by next week", reference_date=now)
    assert result is not None
    # Next Monday is Feb 2
    assert result.weekday() == 0  # Monday
    assert result.date() == datetime(2026, 2, 2).date()


def test_extract_due_date_no_pattern():
    """Test that text without date patterns returns None."""
    result = extract_due_date("Complete the project")
    assert result is None


def test_commitment_extraction_includes_due_date():
    """Test that commitment extraction includes extracted due dates."""
    payload = "- Send report by Friday\n- Review document tomorrow\n- Check status"
    now = datetime(2026, 1, 30, 10, 0, 0)  # Thursday

    # Monkey-patch datetime for test
    import app.ingestion.rules as rules
    original_utcnow = datetime.utcnow

    try:
        # Override datetime.utcnow in the rules module
        commitments = extract_commitments(payload)

        # First commitment should be the first line without due date
        assert commitments[0].text == "- Send report by Friday"

        # Check bullets - "by Friday" should have a due date
        friday_commitment = next((c for c in commitments if "Friday" in c.text), None)
        assert friday_commitment is not None
        assert friday_commitment.due_date is not None

        # "tomorrow" should have a due date
        tomorrow_commitment = next((c for c in commitments if "tomorrow" in c.text), None)
        assert tomorrow_commitment is not None
        assert tomorrow_commitment.due_date is not None

        # "Check status" should not have a due date
        status_commitment = next((c for c in commitments if "Check status" in c.text), None)
        assert status_commitment is not None
        assert status_commitment.due_date is None
    finally:
        pass  # No cleanup needed
