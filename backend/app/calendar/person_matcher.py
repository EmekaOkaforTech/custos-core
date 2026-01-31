"""Person matching logic for calendar attendees.

Story 37.3: Attendee Extraction and Person Matching

Provides deterministic, explainable person matching:
1. Exact email match (case-insensitive)
2. Exact name match (case-insensitive, whitespace normalized)
3. Create new person if no match

All matching is deterministic - no AI/ML involved.
"""

import logging
import re
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import add_audit_entry
from app.models.person import Person
from app.utils.datetime import utcnow

logger = logging.getLogger(__name__)


@dataclass
class PersonMatchResult:
    """Result of a person matching attempt."""

    person_id: str
    match_type: str  # "email_match", "name_match", "created_new"
    potential_duplicates: list[str]  # IDs of potential duplicate persons
    is_new: bool


def normalize_email(email: str | None) -> str | None:
    """Normalize email for matching: lowercase, strip whitespace."""
    if not email:
        return None
    return email.strip().lower()


def normalize_name(name: str | None) -> str | None:
    """Normalize name for matching: lowercase, collapse whitespace."""
    if not name:
        return None
    normalized = re.sub(r"\s+", " ", name.strip().lower())
    return normalized if normalized else None


class PersonMatcher:
    """Deterministic person matching for calendar attendees."""

    def __init__(self, db: Session):
        self.db = db

    def match_by_email(self, email: str) -> Person | None:
        """Find person by exact email match (case-insensitive)."""
        normalized = normalize_email(email)
        if not normalized:
            return None

        return (
            self.db.query(Person)
            .filter(func.lower(Person.email) == normalized)
            .first()
        )

    def match_by_name(self, name: str) -> Person | None:
        """Find person by exact name match (case-insensitive, normalized whitespace)."""
        normalized = normalize_name(name)
        if not normalized:
            return None

        # Use SQL-side normalization for consistent matching
        return (
            self.db.query(Person)
            .filter(func.lower(func.trim(Person.name)) == normalized)
            .first()
        )

    def find_potential_duplicates(
        self, email: str | None, name: str | None, exclude_id: str | None = None
    ) -> list[str]:
        """
        Find potential duplicate persons.

        Detects: same name but different email (potential duplicate).
        Returns list of person IDs that may be duplicates.
        """
        duplicates = []
        normalized_name = normalize_name(name)

        if normalized_name:
            # Find persons with same name but different email
            query = self.db.query(Person).filter(
                func.lower(func.trim(Person.name)) == normalized_name
            )

            if exclude_id:
                query = query.filter(Person.id != exclude_id)

            candidates = query.all()

            normalized_email = normalize_email(email)
            for candidate in candidates:
                candidate_email = normalize_email(candidate.email)
                # If emails differ (including None vs value), mark as potential duplicate
                if candidate_email != normalized_email:
                    duplicates.append(candidate.id)

        return duplicates

    def find_or_create_person(
        self,
        email: str | None,
        name: str | None,
        source: str = "calendar",
        event_id: str | None = None,
    ) -> PersonMatchResult:
        """
        Find existing person or create new one.

        Priority:
        1. Exact email match (case-insensitive) - returns existing person
        2. Exact name match (case-insensitive, normalized) - returns existing person
        3. Create new person

        Returns PersonMatchResult with match metadata for auditing.
        """
        normalized_email = normalize_email(email)
        normalized_name = normalize_name(name)

        # Step 1: Try email match first (most reliable)
        if normalized_email:
            matched = self.match_by_email(normalized_email)
            if matched:
                # Update email if not already set (shouldn't happen but defensive)
                if not matched.email:
                    matched.email = normalized_email
                    matched.updated_at = utcnow()

                # Check for potential duplicates
                duplicates = self.find_potential_duplicates(
                    normalized_email, normalized_name, exclude_id=matched.id
                )

                self._audit_match(
                    match_type="email_match",
                    person_id=matched.id,
                    email=normalized_email,
                    name=normalized_name,
                    source=source,
                    event_id=event_id,
                    duplicates=duplicates,
                )

                logger.debug(
                    "Matched person by email: %s -> %s", normalized_email, matched.id
                )
                return PersonMatchResult(
                    person_id=matched.id,
                    match_type="email_match",
                    potential_duplicates=duplicates,
                    is_new=False,
                )

        # Step 2: Try name match
        if normalized_name:
            matched = self.match_by_name(normalized_name)
            if matched:
                # Update email if matched by name and we have email but they don't
                if normalized_email and not matched.email:
                    matched.email = normalized_email
                    matched.updated_at = utcnow()

                # Check for potential duplicates (same name, different email)
                duplicates = self.find_potential_duplicates(
                    normalized_email, normalized_name, exclude_id=matched.id
                )

                self._audit_match(
                    match_type="name_match",
                    person_id=matched.id,
                    email=normalized_email,
                    name=normalized_name,
                    source=source,
                    event_id=event_id,
                    duplicates=duplicates,
                )

                logger.debug(
                    "Matched person by name: %s -> %s", normalized_name, matched.id
                )
                return PersonMatchResult(
                    person_id=matched.id,
                    match_type="name_match",
                    potential_duplicates=duplicates,
                    is_new=False,
                )

        # Step 3: Create new person
        display_name = name or email or "Unknown"
        person_id = f"p_{uuid4().hex}"
        now = utcnow()

        person = Person(
            id=person_id,
            name=display_name,
            email=normalized_email,
            type="person",
            role=None,
            last_interaction_at=None,
            created_at=now,
            updated_at=now,
        )
        self.db.add(person)

        # Check for potential duplicates after creation
        duplicates = self.find_potential_duplicates(
            normalized_email, normalized_name, exclude_id=person_id
        )

        self._audit_create(
            person_id=person_id,
            email=normalized_email,
            name=display_name,
            source=source,
            event_id=event_id,
            duplicates=duplicates,
        )

        logger.debug("Created new person: %s (%s)", person_id, display_name)
        return PersonMatchResult(
            person_id=person_id,
            match_type="created_new",
            potential_duplicates=duplicates,
            is_new=True,
        )

    def _audit_match(
        self,
        match_type: str,
        person_id: str,
        email: str | None,
        name: str | None,
        source: str,
        event_id: str | None,
        duplicates: list[str],
    ) -> None:
        """Audit log entry for person match."""
        add_audit_entry(
            self.db,
            action="person_matched",
            entity_type="Person",
            entity_id=person_id,
            payload={
                "match_type": match_type,
                "email": email,
                "name": name,
                "source": source,
                "event_id": event_id,
                "potential_duplicates": duplicates,
            },
        )

    def _audit_create(
        self,
        person_id: str,
        email: str | None,
        name: str,
        source: str,
        event_id: str | None,
        duplicates: list[str],
    ) -> None:
        """Audit log entry for person creation."""
        add_audit_entry(
            self.db,
            action="person_created_from_calendar",
            entity_type="Person",
            entity_id=person_id,
            payload={
                "email": email,
                "name": name,
                "source": source,
                "event_id": event_id,
                "potential_duplicates": duplicates,
            },
        )
