import re
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class CommitmentResult:
    text: str
    rule_id: str


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


def extract_commitments(payload: str | None) -> list[CommitmentResult]:
    if not payload:
        return [CommitmentResult(text="Review meeting context", rule_id=COMMITMENT_RULE_PLACEHOLDER)]

    lines = [line.strip() for line in payload.splitlines() if line.strip()]
    results: list[CommitmentResult] = []

    if lines:
        results.append(CommitmentResult(text=lines[0], rule_id=COMMITMENT_RULE_FIRST_LINE))

    for line in lines:
        if line.startswith("- ") or line.startswith("* ") or line.startswith("• "):
            cleaned = line[2:].strip()
            if cleaned:
                results.append(CommitmentResult(text=cleaned, rule_id=COMMITMENT_RULE_BULLET))

    deduped = []
    seen = set()
    for item in results:
        key = item.text.lower()
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
