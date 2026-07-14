"""Fixture-safe consent, retention, deletion, and installation export boundary."""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable, Mapping, Optional, Tuple, Union

from heart_rate.models import CaptureGap, HeartRateSample, require_aware

from .contracts import validate_payload
from .state_machine import Stroke


CONSENT_COPY_PATH = (
    Path(__file__).resolve().parents[1]
    / "contracts"
    / "v1"
    / "consent"
    / "biometric-purpose.consent-v1.json"
)
CONSENT_VERSION = "consent-v1"
BIO_METRIC_DECISIONS = {"pending", "granted", "declined"}
RESEARCH_DECISIONS = {"not-requested", "granted", "declined"}
INTERACTION_EVENTS = {
    "biometric-consent-granted",
    "biometric-consent-declined",
    "first-ink",
    "heart-rate-gap",
    "submit",
    "marginalia-viewed",
}
OPERATIONAL_CATEGORIES = (
    "ink",
    "derived_images",
    "transcripts",
    "review",
    "heart_rate_samples",
    "heart_rate_gaps",
    "token_references",
    "provider_payloads",
    "interaction_events",
)
RESEARCH_CATEGORIES = ("installation_export",)
SENSITIVE_CATEGORIES = OPERATIONAL_CATEGORIES + RESEARCH_CATEGORIES
_EMPTY_VALUE = {
    "ink": (),
    "derived_images": (),
    "transcripts": (),
    "review": None,
    "heart_rate_samples": (),
    "heart_rate_gaps": (),
    "token_references": (),
    "provider_payloads": (),
    "interaction_events": (),
    "installation_export": None,
}


def load_consent_copy() -> Mapping[str, object]:
    """Load and validate the copy shipped with the fixture application."""

    payload = json.loads(CONSENT_COPY_PATH.read_text())
    validate_payload("consent-copy", payload)
    return payload


def new_pseudonymous_session_id(entropy: Optional[bytes] = None) -> str:
    """Create a random identifier without deriving it from an account or profile."""

    value = secrets.token_bytes(16) if entropy is None else entropy
    if not isinstance(value, bytes) or len(value) != 16:
        raise ValueError("session id entropy must contain exactly 16 bytes")
    return f"session-{value.hex()}"


def _iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat().replace("+00:00", "Z") if value else None


@dataclass(frozen=True)
class ConsentRecord:
    """Versioned choices stored against only a pseudonymous session id."""

    session_id: str
    consent_version: str = CONSENT_VERSION
    biometric_decision: str = "pending"
    biometric_decided_at: Optional[datetime] = None
    research_decision: str = "not-requested"
    research_decided_at: Optional[datetime] = None
    withdrawn_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        for name in ("biometric_decided_at", "research_decided_at", "withdrawn_at"):
            value = getattr(self, name)
            if value is not None:
                require_aware(value, name)
        validate_payload("consent", self.as_payload())

    def as_payload(self) -> dict[str, object]:
        return {
            "schema_version": "1",
            "session_id": self.session_id,
            "consent_version": self.consent_version,
            "biometric_decision": self.biometric_decision,
            "biometric_decided_at": _iso(self.biometric_decided_at),
            "research_decision": self.research_decision,
            "research_decided_at": _iso(self.research_decided_at),
            "withdrawn_at": _iso(self.withdrawn_at),
        }

    def decide_biometric(self, decision: str, at: datetime) -> "ConsentRecord":
        require_aware(at, "at")
        if decision not in BIO_METRIC_DECISIONS - {"pending"}:
            raise ValueError("biometric decision must be granted or declined")
        if self.withdrawn_at is not None:
            raise ValueError("withdrawn consent cannot be changed")
        if self.biometric_decision == decision:
            return self
        if self.biometric_decision != "pending":
            raise ValueError("biometric consent is already decided")
        return replace(
            self,
            biometric_decision=decision,
            biometric_decided_at=at,
        )

    def decide_research(self, decision: str, at: datetime) -> "ConsentRecord":
        require_aware(at, "at")
        if decision not in RESEARCH_DECISIONS - {"not-requested"}:
            raise ValueError("research decision must be granted or declined")
        if self.withdrawn_at is not None:
            raise ValueError("withdrawn consent cannot be changed")
        if self.research_decision == decision:
            return self
        if self.research_decision != "not-requested":
            raise ValueError("research consent is already decided")
        return replace(
            self,
            research_decision=decision,
            research_decided_at=at,
        )

    def withdraw(self, at: datetime) -> "ConsentRecord":
        require_aware(at, "at")
        if self.withdrawn_at is not None:
            return self
        decisions = [
            value
            for value in (self.biometric_decided_at, self.research_decided_at)
            if value is not None
        ]
        if decisions and at < max(decisions):
            raise ValueError("withdrawal cannot predate a consent decision")
        return replace(self, withdrawn_at=at)


@dataclass(frozen=True)
class RetentionSchedule:
    """No durations are defaulted; deployment values require owner approval."""

    created_at: datetime
    operational_deadline: datetime
    research_deadline: Optional[datetime] = None
    aggregate_tombstone_approval: Optional[str] = None

    def __post_init__(self) -> None:
        require_aware(self.created_at, "created_at")
        require_aware(self.operational_deadline, "operational_deadline")
        if self.operational_deadline < self.created_at:
            raise ValueError("operational deadline cannot predate session creation")
        if self.research_deadline is not None:
            require_aware(self.research_deadline, "research_deadline")
            if self.research_deadline < self.operational_deadline:
                raise ValueError("research deadline cannot predate operational expiry")
        if self.aggregate_tombstone_approval is not None:
            if not self.aggregate_tombstone_approval.startswith("fixture-approval-"):
                raise ValueError("aggregate tombstone requires an explicit fixture approval id")


@dataclass(frozen=True)
class InteractionEvent:
    at: datetime
    event: str

    def __post_init__(self) -> None:
        require_aware(self.at, "at")
        if self.event not in INTERACTION_EVENTS:
            raise ValueError("unknown interaction event")


@dataclass(frozen=True)
class ApprovedAggregate:
    duration_ms: int
    sample_count: int
    gap_count: int
    interaction_count: int

    def __post_init__(self) -> None:
        if min(
            self.duration_ms,
            self.sample_count,
            self.gap_count,
            self.interaction_count,
        ) < 0:
            raise ValueError("aggregate counts and duration must not be negative")


@dataclass(frozen=True, repr=False)
class SessionRecord:
    """Consent-scoped operational data; sensitive fields never appear in repr."""

    session_id: str
    consent: ConsentRecord
    retention: RetentionSchedule
    first_ink_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    ink: Tuple[Stroke, ...] = field(default=(), repr=False)
    derived_images: Tuple[object, ...] = field(default=(), repr=False)
    transcripts: Tuple[str, ...] = field(default=(), repr=False)
    review: Optional[Mapping[str, object]] = field(default=None, repr=False)
    heart_rate_samples: Tuple[HeartRateSample, ...] = field(default=(), repr=False)
    heart_rate_gaps: Tuple[CaptureGap, ...] = field(default=(), repr=False)
    token_references: Tuple[str, ...] = field(default=(), repr=False)
    provider_payloads: Tuple[Mapping[str, object], ...] = field(default=(), repr=False)
    interaction_events: Tuple[InteractionEvent, ...] = field(default=(), repr=False)
    installation_export: Optional[Mapping[str, object]] = field(default=None, repr=False)
    approved_aggregate: Optional[ApprovedAggregate] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.session_id != self.consent.session_id:
            raise ValueError("consent must belong to the stored session")
        if self.first_ink_at is not None:
            require_aware(self.first_ink_at, "first_ink_at")
        if self.submitted_at is not None:
            require_aware(self.submitted_at, "submitted_at")
        if self.first_ink_at and self.first_ink_at < self.retention.created_at:
            raise ValueError("first ink cannot predate session creation")
        if self.submitted_at and self.submitted_at < (
            self.first_ink_at or self.retention.created_at
        ):
            raise ValueError("submission cannot predate the session capture window")
        if self.retention.research_deadline is not None:
            if self.consent.research_decision != "granted":
                raise ValueError("research retention requires separate opt-in")
        if self.installation_export is not None:
            if self.consent.research_decision != "granted":
                raise ValueError("installation export requires separate opt-in")
            validate_payload("installation-export", self.installation_export)

    def sensitive_counts(self) -> Mapping[str, int]:
        counts: dict[str, int] = {}
        for category in SENSITIVE_CATEGORIES:
            value = getattr(self, category)
            if value is None:
                counts[category] = 0
            elif isinstance(value, (tuple, list, dict)):
                counts[category] = len(value)
            else:
                counts[category] = 1
        return counts

    def __repr__(self) -> str:
        present = sum(count > 0 for count in self.sensitive_counts().values())
        return f"SessionRecord(session_id={self.session_id!r}, populated_categories={present})"


@dataclass(frozen=True)
class AggregateTombstone:
    session_id: str
    deleted_at: datetime
    reason: str
    approval_id: str
    aggregate: ApprovedAggregate

    def __post_init__(self) -> None:
        require_aware(self.deleted_at, "deleted_at")
        if not self.approval_id.startswith("fixture-approval-"):
            raise ValueError("aggregate tombstone is not explicitly approved")


StoredValue = Union[SessionRecord, AggregateTombstone]


class StorageFailure(RuntimeError):
    """Stable failure used by fixture stores without exposing record contents."""


class InMemorySessionStore:
    """Deterministic fixture repository with per-category failure injection."""

    def __init__(
        self,
        records: Iterable[SessionRecord] = (),
        *,
        fail_once: Iterable[str] = (),
    ) -> None:
        self._records: dict[str, StoredValue] = {}
        self._fail_once = set(fail_once)
        for record in records:
            self.save(record)

    def save(self, record: SessionRecord) -> None:
        self._records[record.session_id] = record

    def get(self, session_id: str) -> Optional[StoredValue]:
        return self._records.get(session_id)

    def active_records(self) -> Tuple[SessionRecord, ...]:
        return tuple(
            value
            for _, value in sorted(self._records.items())
            if isinstance(value, SessionRecord)
        )

    def clear_category(self, session_id: str, category: str) -> None:
        if category not in SENSITIVE_CATEGORIES:
            raise ValueError("unknown sensitive category")
        if category in self._fail_once:
            self._fail_once.remove(category)
            raise StorageFailure("storage_write_failed")
        record = self._records.get(session_id)
        if not isinstance(record, SessionRecord):
            return
        self._records[session_id] = replace(record, **{category: _EMPTY_VALUE[category]})

    def remove(self, session_id: str) -> None:
        self._records.pop(session_id, None)

    def replace_with_tombstone(self, tombstone: AggregateTombstone) -> None:
        self._records[tombstone.session_id] = tombstone


@dataclass(frozen=True)
class AuditEvent:
    session_id: str
    action: str
    status: str
    category_count: int
    failure_count: int


@dataclass(frozen=True)
class DeletionResult:
    session_id: str
    status: str
    deleted_categories: Tuple[str, ...]
    failed_categories: Tuple[str, ...]
    retained_categories: Tuple[str, ...]
    idempotent: bool = False


class RetentionDeletionService:
    """Best-effort purging with retryable partial failure and safe audit events."""

    def __init__(
        self,
        store: InMemorySessionStore,
        audit: Optional[Callable[[AuditEvent], None]] = None,
    ) -> None:
        self.store = store
        self.audit = audit or (lambda _event: None)

    def delete(
        self,
        session_id: str,
        at: datetime,
        *,
        reason: str = "participant-request",
    ) -> DeletionResult:
        require_aware(at, "at")
        return self._purge(session_id, at, SENSITIVE_CATEGORIES, reason)

    def withdraw(self, session_id: str, at: datetime) -> DeletionResult:
        require_aware(at, "at")
        record = self.store.get(session_id)
        if isinstance(record, SessionRecord):
            self.store.save(replace(record, consent=record.consent.withdraw(at)))
        return self._purge(session_id, at, SENSITIVE_CATEGORIES, "withdrawal")

    def expire_due(self, at: datetime) -> Tuple[DeletionResult, ...]:
        require_aware(at, "at")
        results = []
        for record in self.store.active_records():
            categories: list[str] = []
            if at >= record.retention.operational_deadline:
                categories.extend(OPERATIONAL_CATEGORIES)
            research_deadline = record.retention.research_deadline
            if research_deadline is None:
                if categories:
                    categories.extend(RESEARCH_CATEGORIES)
            elif at >= research_deadline:
                categories.extend(RESEARCH_CATEGORIES)
            if categories:
                results.append(
                    self._purge(
                        record.session_id,
                        at,
                        tuple(categories),
                        "retention-expiry",
                    )
                )
        return tuple(results)

    def _purge(
        self,
        session_id: str,
        at: datetime,
        categories: Tuple[str, ...],
        reason: str,
    ) -> DeletionResult:
        stored = self.store.get(session_id)
        if stored is None or isinstance(stored, AggregateTombstone):
            result = DeletionResult(session_id, "deleted", (), (), (), True)
            self._audit(result, reason)
            return result

        if (
            stored.retention.aggregate_tombstone_approval
            and stored.approved_aggregate is None
        ):
            stored = replace(stored, approved_aggregate=_aggregate(stored))
            self.store.save(stored)

        deleted = []
        failed = []
        for category in categories:
            current = self.store.get(session_id)
            if not isinstance(current, SessionRecord):
                break
            if current.sensitive_counts()[category] == 0:
                continue
            try:
                self.store.clear_category(session_id, category)
                deleted.append(category)
            except StorageFailure:
                failed.append(category)

        current = self.store.get(session_id)
        retained = ()
        if isinstance(current, SessionRecord):
            retained = tuple(
                category
                for category, count in current.sensitive_counts().items()
                if count > 0
            )

        if failed:
            status = "partial"
        elif retained:
            status = "retained-research"
        else:
            status = "deleted"
            if isinstance(current, SessionRecord):
                approval = current.retention.aggregate_tombstone_approval
                if approval and current.approved_aggregate:
                    self.store.replace_with_tombstone(
                        AggregateTombstone(
                            session_id=session_id,
                            deleted_at=at,
                            reason=reason,
                            approval_id=approval,
                            aggregate=current.approved_aggregate,
                        )
                    )
                else:
                    self.store.remove(session_id)

        result = DeletionResult(
            session_id,
            status,
            tuple(deleted),
            tuple(failed),
            retained,
        )
        self._audit(result, reason)
        return result

    def _audit(self, result: DeletionResult, action: str) -> None:
        self.audit(
            AuditEvent(
                session_id=result.session_id,
                action=action,
                status=result.status,
                category_count=len(result.deleted_categories),
                failure_count=len(result.failed_categories),
            )
        )


def make_installation_export(
    record: SessionRecord,
    *,
    export_id: str,
) -> Mapping[str, object]:
    """Build an allowlisted relative-time export after separate research opt-in."""

    if record.consent.withdrawn_at is not None:
        raise ValueError("withdrawn sessions cannot be exported")
    if record.consent.research_decision != "granted":
        raise ValueError("installation export requires separate research consent")
    if record.first_ink_at is None or record.submitted_at is None:
        raise ValueError("installation export requires a closed first-ink capture window")

    origin = record.first_ink_at
    samples = [
        {
            "elapsed_ms": _elapsed_ms(sample.received_at, origin),
            "bpm": sample.bpm,
            "quality": list(sample.quality_flags),
            "source_clock_offset_ms": _elapsed_ms(
                sample.captured_at,
                sample.received_at,
            ),
        }
        for sample in sorted(record.heart_rate_samples, key=lambda item: item.received_at)
    ]
    gaps = [
        {
            "started_elapsed_ms": _elapsed_ms(gap.started_at, origin),
            "ended_elapsed_ms": _elapsed_ms(gap.ended_at, origin),
            "reason": gap.reason,
        }
        for gap in sorted(record.heart_rate_gaps, key=lambda item: item.started_at)
    ]
    interactions = list(record.interaction_events)
    if record.consent.biometric_decided_at is not None:
        interactions.append(
            InteractionEvent(
                record.consent.biometric_decided_at,
                f"biometric-consent-{record.consent.biometric_decision}",
            )
        )
    interactions.extend(
        (
            InteractionEvent(origin, "first-ink"),
            InteractionEvent(record.submitted_at, "submit"),
        )
    )
    unique_interactions = sorted(
        {(item.at, item.event) for item in interactions},
        key=lambda item: (item[0], item[1]),
    )
    payload = {
        "schema_version": "1",
        "export_id": export_id,
        "session_id": record.session_id,
        "consent_version": record.consent.consent_version,
        "relative_time_origin": "first-accepted-ink",
        "duration_ms": _elapsed_ms(record.submitted_at, origin),
        "heart_rate": {"samples": samples, "gaps": gaps},
        "interaction_events": [
            {"elapsed_ms": _elapsed_ms(at, origin), "event": event}
            for at, event in unique_interactions
        ],
    }
    validate_payload("installation-export", payload)
    return payload


def _elapsed_ms(value: datetime, origin: datetime) -> int:
    return round((value - origin).total_seconds() * 1000)


def _aggregate(record: SessionRecord) -> ApprovedAggregate:
    duration_ms = 0
    if record.first_ink_at and record.submitted_at:
        duration_ms = _elapsed_ms(record.submitted_at, record.first_ink_at)
    return ApprovedAggregate(
        duration_ms=duration_ms,
        sample_count=len(record.heart_rate_samples),
        gap_count=len(record.heart_rate_gaps),
        interaction_count=len(record.interaction_events),
    )
