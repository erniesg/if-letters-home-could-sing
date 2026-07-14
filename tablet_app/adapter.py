"""Deterministic QML/backend adapter over the portable experience core."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Mapping, Optional, Sequence, Tuple

from experience_core import (
    FixtureReplyReviewer,
    Point,
    ReplyReviewer,
    ReviewProviderError,
    Stroke,
    accept_stroke,
    complete_review,
    fail_review,
    fail_submission,
    make_review_request,
    new_session,
    retry,
    review_annotations,
    review_reply,
    submit,
    swipe,
)
from experience_core.privacy import ConsentRecord, load_consent_copy


MESSAGE_OPEN = 1
MESSAGE_SWIPE = 2
MESSAGE_STROKE = 3
MESSAGE_SUBMIT = 4
MESSAGE_RETRY = 5
MESSAGE_CONSENT = 6

MESSAGE_STATE = 101
MESSAGE_CONFIRM_EMPTY = 102
MESSAGE_ERROR = 103

FIXTURE_SESSION_ID = "fixture-session-0001"
FIXTURE_REVIEW_ID = "fixture-review-0001"
FIXTURE_CREATED_AT = "2026-07-14T00:00:00Z"
FIXTURE_SUBMITTED_AT = "2026-07-14T00:01:02Z"
FIXTURE_CONSENT_AT = "2026-07-14T00:00:02Z"


@dataclass(frozen=True)
class CapturedPoint:
    """One synthetic pen sample before conversion to page-space core data."""

    x: float
    y: float
    pressure: float
    elapsed_ms: int

    def __post_init__(self) -> None:
        if not 0 <= self.x <= 1 or not 0 <= self.y <= 1:
            raise ValueError("pen coordinates must be in page space")
        if not 0 <= self.pressure <= 1:
            raise ValueError("pen pressure must be between zero and one")
        if self.elapsed_ms < 0:
            raise ValueError("pen sample time must not be negative")


@dataclass(frozen=True)
class CapturedStroke:
    """A complete mock stroke with pressure, relative time, and coordinates."""

    stroke_id: str
    accepted_at: str
    points: Tuple[CapturedPoint, ...]

    def __post_init__(self) -> None:
        points = tuple(self.points)
        if not points:
            raise ValueError("a captured stroke must contain points")
        if tuple(point.elapsed_ms for point in points) != tuple(
            sorted(point.elapsed_ms for point in points)
        ):
            raise ValueError("pen sample times must be ordered")
        object.__setattr__(self, "points", points)

    def as_core_stroke(self) -> Stroke:
        return Stroke(
            stroke_id=self.stroke_id,
            accepted_at=self.accepted_at,
            points=tuple(
                Point(x=point.x, y=point.y, pressure=point.pressure)
                for point in self.points
            ),
        )


class MockPenSource:
    """Finite deterministic pen source used by tests and the host simulator."""

    def __init__(self, strokes: Iterable[CapturedStroke]) -> None:
        self._strokes = tuple(strokes)
        self._index = 0

    @classmethod
    def default(cls) -> "MockPenSource":
        return cls(
            (
                CapturedStroke(
                    stroke_id="stroke-1",
                    accepted_at="2026-07-14T00:00:12Z",
                    points=(
                        CapturedPoint(0.20, 0.30, 0.45, 0),
                        CapturedPoint(0.24, 0.34, 0.60, 18),
                        CapturedPoint(0.30, 0.40, 0.52, 37),
                    ),
                ),
            )
        )

    def next_stroke(self) -> CapturedStroke:
        if self._index >= len(self._strokes):
            raise StopIteration("mock pen fixture exhausted")
        stroke = self._strokes[self._index]
        self._index += 1
        return stroke


@dataclass(frozen=True)
class OutboundMessage:
    message_type: int
    payload: Mapping[str, object]

    @property
    def contents(self) -> str:
        return json.dumps(self.payload, sort_keys=True, separators=(",", ":"))


class FixtureBackend:
    """Local adapter that exposes the core as AppLoad message events.

    Review outcomes are consumed in order. Supported fixture outcomes are
    ``success``, ``timeout``, and ``offline``.
    """

    def __init__(
        self,
        review_outcomes: Sequence[str] = ("success",),
        *,
        reviewer: Optional[ReplyReviewer] = None,
        review_fixture: str = "auto",
    ) -> None:
        if not review_outcomes:
            raise ValueError("at least one review outcome is required")
        unknown = set(review_outcomes) - {"success", "timeout", "offline"}
        if unknown:
            raise ValueError(f"unknown fixture review outcome: {sorted(unknown)[0]}")
        self.session = new_session(
            session_id=FIXTURE_SESSION_ID,
            created_at=FIXTURE_CREATED_AT,
        )
        self.consent = ConsentRecord(FIXTURE_SESSION_ID)
        self.consent_copy = load_consent_copy()
        self.pen_records: Tuple[CapturedStroke, ...] = ()
        self._review_outcomes = tuple(review_outcomes)
        self._review_attempt = 0
        self._reviewer = reviewer or FixtureReplyReviewer(review_fixture)
        self.review_document: Optional[Mapping[str, object]] = None

    def dispatch(
        self,
        message_type: int,
        contents: Optional[str | Mapping[str, object]] = None,
    ) -> Tuple[OutboundMessage, ...]:
        """Handle one frontend event without logging its contents."""

        try:
            payload = _decode_payload(contents)
            if message_type == MESSAGE_OPEN:
                return (self._state_message(),)
            if message_type == MESSAGE_SWIPE:
                return self._swipe(payload)
            if message_type == MESSAGE_STROKE:
                return self._accept_stroke(payload)
            if message_type == MESSAGE_SUBMIT:
                return self._submit(payload)
            if message_type == MESSAGE_RETRY:
                return self._retry()
            if message_type == MESSAGE_CONSENT:
                return self._consent(payload)
            return (self._error_message("unknown_message"),)
        except (KeyError, TypeError, ValueError) as error:
            return (self._error_message(_safe_error_code(error)),)

    def _swipe(self, payload: Mapping[str, object]) -> Tuple[OutboundMessage, ...]:
        if self.consent.biometric_decision == "pending":
            return (self._error_message("consent_required"),)
        self.session = swipe(self.session, str(payload["direction"]))
        return (self._state_message(),)

    def _consent(self, payload: Mapping[str, object]) -> Tuple[OutboundMessage, ...]:
        decision = _string_field(payload, "decision")
        decided_at = _string_field(payload, "decided_at", FIXTURE_CONSENT_AT)
        self.consent = self.consent.decide_biometric(
            decision,
            datetime.fromisoformat(decided_at.replace("Z", "+00:00")),
        )
        return (self._state_message(event=f"biometric_consent_{decision}"),)

    def _accept_stroke(
        self, payload: Mapping[str, object]
    ) -> Tuple[OutboundMessage, ...]:
        points = tuple(
            CapturedPoint(
                x=float(point["x"]),
                y=float(point["y"]),
                pressure=float(point["pressure"]),
                elapsed_ms=int(point["elapsed_ms"]),
            )
            for point in payload["points"]
        )
        captured = CapturedStroke(
            stroke_id=_string_field(payload, "stroke_id"),
            accepted_at=_string_field(payload, "accepted_at"),
            points=points,
        )
        first_stroke = self.session.first_ink_at is None
        self.session = accept_stroke(self.session, captured.as_core_stroke())
        self.pen_records += (captured,)
        event = "first_ink_started" if first_stroke else "stroke_accepted"
        return (self._state_message(event=event),)

    def _submit(self, payload: Mapping[str, object]) -> Tuple[OutboundMessage, ...]:
        confirm_empty = payload.get("confirm_empty", False)
        if not isinstance(confirm_empty, bool):
            raise TypeError("confirm_empty must be a boolean")
        submitted_at = payload.get("submitted_at", FIXTURE_SUBMITTED_AT)
        if not isinstance(submitted_at, str):
            raise TypeError("submitted_at must be a string")
        decision = submit(
            self.session,
            review_id=FIXTURE_REVIEW_ID,
            submitted_at=submitted_at,
            confirm_empty=confirm_empty,
        )
        if decision.confirmation_required:
            return (
                OutboundMessage(
                    MESSAGE_CONFIRM_EMPTY,
                    {
                        "message": "Your huipi is blank. Submit it without ink?",
                        "state": self.session.state.value,
                    },
                ),
            )
        if decision.session is self.session and self.session.review_id is not None:
            return (self._state_message(event="duplicate_submit_ignored"),)
        self.session = decision.session
        messages = [self._state_message(event="submission_started")]
        self._finish_review_attempt()
        messages.append(self._state_message())
        return tuple(messages)

    def _retry(self) -> Tuple[OutboundMessage, ...]:
        self.session = retry(self.session)
        messages = [self._state_message(event="submission_retried")]
        self._finish_review_attempt()
        messages.append(self._state_message())
        return tuple(messages)

    def _finish_review_attempt(self) -> None:
        index = min(self._review_attempt, len(self._review_outcomes) - 1)
        outcome = self._review_outcomes[index]
        self._review_attempt += 1
        if outcome == "timeout":
            self.session = fail_review(self.session, "reviewer_timeout")
        elif outcome == "offline":
            self.session = fail_submission(self.session, "gateway_offline")
        else:
            try:
                document = review_reply(
                    self._reviewer,
                    make_review_request(self.session),
                )
            except ReviewProviderError as error:
                self.session = fail_review(self.session, error.code)
                return
            self.review_document = document
            self.session = complete_review(
                self.session,
                review_id=FIXTURE_REVIEW_ID,
                annotations=review_annotations(document),
            )

    def _state_message(self, *, event: Optional[str] = None) -> OutboundMessage:
        payload: dict[str, object] = {
            "annotations": [_annotation_payload(item) for item in self.session.annotations],
            "biometricConsent": self.consent.biometric_decision,
            "consentVersion": self.consent.consent_version,
            "errorCode": self.session.error_code,
            "firstInkAt": self.session.first_ink_at,
            "reviewStatus": (
                self.review_document["status"] if self.review_document else None
            ),
            "reviewSummary": (
                self.review_document["summary"] if self.review_document else ""
            ),
            "reviewId": self.session.review_id,
            "heartRateStatus": {
                "pending": "idle",
                "granted": "unavailable",
                "declined": "declined",
            }[self.consent.biometric_decision],
            "purposeNotice": self.consent_copy["purpose_notice"],
            "state": self.session.state.value,
            "strokes": [_stroke_payload(item) for item in self.session.strokes],
        }
        if event:
            payload["event"] = event
        return OutboundMessage(MESSAGE_STATE, payload)

    @staticmethod
    def _error_message(code: str) -> OutboundMessage:
        return OutboundMessage(
            MESSAGE_ERROR,
            {"code": code, "message": "The local fixture message was rejected."},
        )


def _decode_payload(
    contents: Optional[str | Mapping[str, object]],
) -> Mapping[str, object]:
    if contents is None or contents == "":
        return {}
    if isinstance(contents, Mapping):
        return contents
    payload = json.loads(contents)
    if not isinstance(payload, dict):
        raise TypeError("message payload must be an object")
    return payload


def _stroke_payload(stroke: Stroke) -> dict[str, object]:
    return {
        "acceptedAt": stroke.accepted_at,
        "id": stroke.stroke_id,
        "points": [
            {"pressure": point.pressure, "x": point.x, "y": point.y}
            for point in stroke.points
        ],
    }


def _annotation_payload(annotation: Annotation) -> dict[str, object]:
    return {
        "anchor": {
            "height": annotation.anchor.height,
            "width": annotation.anchor.width,
            "x": annotation.anchor.x,
            "y": annotation.anchor.y,
        },
        "confidence": annotation.confidence,
        "id": annotation.annotation_id,
        "kind": annotation.kind,
        "message": annotation.message,
    }


def _safe_error_code(error: Exception) -> str:
    if isinstance(error, json.JSONDecodeError):
        return "invalid_json"
    if isinstance(error, KeyError):
        return "missing_field"
    return "invalid_message"


def _string_field(
    payload: Mapping[str, object], name: str, default: Optional[str] = None
) -> str:
    value = payload.get(name, default)
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value
