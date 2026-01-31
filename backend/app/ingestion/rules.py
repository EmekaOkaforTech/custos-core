import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable


@dataclass(frozen=True)
class CommitmentResult:
    text: str
    rule_id: str
    due_date: datetime | None = None


@dataclass(frozen=True)
class RiskFlagResult:
    flag_type: str
    rule_id: str
    excerpt: str


COMMITMENT_RULE_FIRST_LINE = "commitment_first_line"
COMMITMENT_RULE_BULLET = "commitment_bullet"
COMMITMENT_RULE_PLACEHOLDER = "commitment_placeholder"

FLAG_RULE_DEADLINE = "flag_deadline_keyword"
FLAG_RULE_BLOCKER = "flag_blocker_keyword"

_DEADLINE_PATTERN = re.compile(r"\b(by|due)\b", re.IGNORECASE)
_BLOCKER_PATTERN = re.compile(r"\b(blocked|risk)\b", re.IGNORECASE)

# Story 39.1: Due date extraction patterns
_WEEKDAY_NAMES = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
_WEEKDAY_PATTERN = re.compile(r'\b(?:by|before|due)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', re.IGNORECASE)
_END_OF_PATTERN = re.compile(r'\b(?:by\s+)?(?:end\s+of|eod|eow)\s*(day|week|month)?\b', re.IGNORECASE)
_TOMORROW_PATTERN = re.compile(r'\b(?:by|due|before)?\s*tomorrow\b', re.IGNORECASE)
_TODAY_PATTERN = re.compile(r'\b(?:by|due|before)?\s*today\b', re.IGNORECASE)
_NEXT_WEEK_PATTERN = re.compile(r'\b(?:by|before|due)\s+next\s+week\b', re.IGNORECASE)


def extract_due_date(text: str, reference_date: datetime | None = None) -> datetime | None:
    """
    Extract due date from commitment text (Story 39.1 - AC #3).

    Patterns supported:
    - "by Friday" / "due Monday" → next occurrence of that weekday
    - "end of day" / "eod" → today at 23:59
    - "end of week" / "eow" → Sunday of current week
    - "tomorrow" → next day
    - "today" → today at 23:59
    - "next week" → Monday of next week
    """
    if not text:
        return None

    now = reference_date or datetime.now(timezone.utc).replace(tzinfo=None)

    # Check for "today"
    if _TODAY_PATTERN.search(text):
        return now.replace(hour=23, minute=59, second=59, microsecond=0)

    # Check for "tomorrow"
    if _TOMORROW_PATTERN.search(text):
        tomorrow = now + timedelta(days=1)
        return tomorrow.replace(hour=23, minute=59, second=59, microsecond=0)

    # Check for "end of day/week/month"
    eod_match = _END_OF_PATTERN.search(text)
    if eod_match:
        period = (eod_match.group(1) or 'day').lower()
        if period == 'day' or period == '':
            return now.replace(hour=23, minute=59, second=59, microsecond=0)
        elif period == 'week':
            # End of week = Sunday
            days_until_sunday = (6 - now.weekday()) % 7
            if days_until_sunday == 0:
                days_until_sunday = 7  # Next Sunday if today is Sunday
            end_of_week = now + timedelta(days=days_until_sunday)
            return end_of_week.replace(hour=23, minute=59, second=59, microsecond=0)
        elif period == 'month':
            # Last day of current month
            if now.month == 12:
                next_month = now.replace(year=now.year + 1, month=1, day=1)
            else:
                next_month = now.replace(month=now.month + 1, day=1)
            last_day = next_month - timedelta(days=1)
            return last_day.replace(hour=23, minute=59, second=59, microsecond=0)

    # Check for "next week"
    if _NEXT_WEEK_PATTERN.search(text):
        # Next Monday
        days_until_monday = (7 - now.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        next_monday = now + timedelta(days=days_until_monday)
        return next_monday.replace(hour=9, minute=0, second=0, microsecond=0)

    # Check for weekday names
    weekday_match = _WEEKDAY_PATTERN.search(text)
    if weekday_match:
        target_day = weekday_match.group(1).lower()
        target_index = _WEEKDAY_NAMES.index(target_day)
        current_index = now.weekday()
        days_ahead = target_index - current_index
        # If target is today or in the past this week, use it if > 0, else next week
        if days_ahead < 0:
            days_ahead += 7  # Next occurrence (past this week)
        elif days_ahead == 0:
            days_ahead = 7  # Same day = next week's occurrence
        target_date = now + timedelta(days=days_ahead)
        return target_date.replace(hour=17, minute=0, second=0, microsecond=0)

    return None


def extract_commitments(payload: str | None) -> list[CommitmentResult]:
    if not payload:
        return [CommitmentResult(text="Review meeting context", rule_id=COMMITMENT_RULE_PLACEHOLDER)]

    lines = [line.strip() for line in payload.splitlines() if line.strip()]
    results: list[CommitmentResult] = []

    if lines:
        due_date = extract_due_date(lines[0])
        results.append(CommitmentResult(text=lines[0], rule_id=COMMITMENT_RULE_FIRST_LINE, due_date=due_date))

    for line in lines:
        if line.startswith("- ") or line.startswith("* ") or line.startswith("• "):
            cleaned = line[2:].strip()
            if cleaned:
                due_date = extract_due_date(cleaned)
                results.append(CommitmentResult(text=cleaned, rule_id=COMMITMENT_RULE_BULLET, due_date=due_date))

    deduped: list[CommitmentResult] = []
    seen = set()
    for item in results:
        key = " ".join(item.text.lower().split())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    return deduped


def extract_risk_flags(payload: str | None) -> list[RiskFlagResult]:
    if not payload:
        return []

    lines = [line.strip() for line in payload.splitlines() if line.strip()]
    results: list[RiskFlagResult] = []

    for line in lines:
        if _DEADLINE_PATTERN.search(line):
            results.append(
                RiskFlagResult(
                    flag_type="deadline_reference",
                    rule_id=FLAG_RULE_DEADLINE,
                    excerpt=line,
                )
            )
            break

    for line in lines:
        if _BLOCKER_PATTERN.search(line):
            results.append(
                RiskFlagResult(
                    flag_type="blocker_reference",
                    rule_id=FLAG_RULE_BLOCKER,
                    excerpt=line,
                )
            )
            break

    return results
