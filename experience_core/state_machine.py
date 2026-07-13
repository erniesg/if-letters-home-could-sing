"""Deterministic state transitions for the three-page correspondence flow."""

import re
from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
from typing import Optional, Tuple


class TransitionError(ValueError):
    """Raised when an event is not valid for the current durable state."""


class ExperienceState(str, Enum):
    INCOMING = "incoming"
    REPLY = "reply"
    SUBMITTING = "submitting"
    SUBMISSION_ERROR = "submission_error"
    REVIEW_ERROR = "review_error"
    MARGINALIA = "marginalia"


@dataclass(frozen=True)
class Point:
    x: float
    y: float
    pressure: Optional[float] = None

    def __post_init__(self):
        for name, value in (("x", self.x), ("y", self.y)):
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be in page space")
        if self.pressure is not None and not 0 <= self.pressure <= 1:
            raise ValueError("pressure must be between zero and one")


@dataclass(frozen=True)
class Stroke:
    stroke_id: str
    accepted_at: str
    points: Tuple[Point, ...]

    def __post_init__(self):
        _require_identifier(self.stroke_id, "stroke_id")
        _parse_timestamp(self.accepted_at, "accepted_at")
        points = tuple(self.points)
        if not points:
            raise ValueError("an accepted stroke must contain at least one point")
        if not all(isinstance(point, Point) for point in points):
            raise ValueError("stroke points must be Point values")
        object.__setattr__(self, "points", points)


@dataclass(frozen=True)
class Anchor:
    page: int
    x: float
    y: float
    width: float
    height: float

    def __post_init__(self):
        if self.page != 2:
            raise ValueError("annotations must anchor to the reply page")
        if min(self.x, self.y, self.width, self.height) < 0:
            raise ValueError("anchor values must not be negative")
        if self.x + self.width > 1 or self.y + self.height > 1:
            raise ValueError("anchor extends beyond page space")


@dataclass(frozen=True)
class Annotation:
    annotation_id: str
    kind: str
    anchor: Anchor
    message: str
    confidence: float

    def __post_init__(self):
        _require_identifier(self.annotation_id, "annotation_id")
        if self.kind not in {"correction", "uncertain-reading", "tone", "reflection"}:
            raise ValueError("unknown annotation kind")
        if not self.message:
            raise ValueError("annotation message must not be empty")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between zero and one")


@dataclass(frozen=True)
class ExperienceSession:
    session_id: str
    state: ExperienceState
    created_at: str
    first_ink_at: Optional[str] = None
    submitted_at: Optional[str] = None
    review_id: Optional[str] = None
    strokes: Tuple[Stroke, ...] = ()
    annotations: Tuple[Annotation, ...] = ()
    error_code: Optional[str] = None

    def __post_init__(self):
        object.__setattr__(self, "strokes", tuple(self.strokes))
        object.__setattr__(self, "annotations", tuple(self.annotations))


@dataclass(frozen=True)
class SubmissionDecision:
    session: ExperienceSession
    confirmation_required: bool = False


def new_session(*, session_id: str, created_at: str) -> ExperienceSession:
    _require_identifier(session_id, "session_id")
    _parse_timestamp(created_at, "created_at")
    return ExperienceSession(
        session_id=session_id,
        state=ExperienceState.INCOMING,
        created_at=created_at,
    )


def swipe(session: ExperienceSession, direction: str) -> ExperienceSession:
    if direction not in {"forward", "backward"}:
        raise ValueError("direction must be forward or backward")
    if session.state is ExperienceState.INCOMING and direction == "forward":
        return replace(session, state=ExperienceState.REPLY)
    if session.state is ExperienceState.REPLY and direction == "backward":
        return replace(session, state=ExperienceState.INCOMING)
    return session


def accept_stroke(session: ExperienceSession, stroke: Stroke) -> ExperienceSession:
    if session.state is not ExperienceState.REPLY:
        raise TransitionError("strokes are accepted only on the writable reply page")
    accepted_at = _parse_timestamp(stroke.accepted_at, "accepted_at")
    if accepted_at < _parse_timestamp(session.created_at, "created_at"):
        raise TransitionError("stroke cannot predate the session")
    if session.strokes:
        previous = _parse_timestamp(session.strokes[-1].accepted_at, "accepted_at")
        if accepted_at < previous:
            raise TransitionError("strokes must be accepted in timestamp order")
    if any(existing.stroke_id == stroke.stroke_id for existing in session.strokes):
        raise TransitionError("stroke_id must be unique within a session")
    return replace(
        session,
        first_ink_at=session.first_ink_at or stroke.accepted_at,
        strokes=session.strokes + (stroke,),
    )


def submit(
    session: ExperienceSession,
    *,
    review_id: str,
    submitted_at: str,
    confirm_empty: bool = False,
) -> SubmissionDecision:
    if session.review_id is not None and session.state in {
        ExperienceState.SUBMITTING,
        ExperienceState.SUBMISSION_ERROR,
        ExperienceState.REVIEW_ERROR,
        ExperienceState.MARGINALIA,
    }:
        return SubmissionDecision(session=session)
    if session.state is not ExperienceState.REPLY:
        raise TransitionError("submit is valid only from reply")
    if not session.strokes and not confirm_empty:
        return SubmissionDecision(session=session, confirmation_required=True)

    _require_identifier(review_id, "review_id")
    submitted = _parse_timestamp(submitted_at, "submitted_at")
    lower_bound = _parse_timestamp(session.first_ink_at or session.created_at, "submit lower bound")
    if submitted < lower_bound:
        raise TransitionError("submission cannot predate the session or first ink")
    return SubmissionDecision(
        session=replace(
            session,
            state=ExperienceState.SUBMITTING,
            submitted_at=submitted_at,
            review_id=review_id,
            error_code=None,
        )
    )


def fail_submission(session: ExperienceSession, error_code: str) -> ExperienceSession:
    return _fail(session, ExperienceState.SUBMISSION_ERROR, error_code)


def fail_review(session: ExperienceSession, error_code: str) -> ExperienceSession:
    return _fail(session, ExperienceState.REVIEW_ERROR, error_code)


def retry(session: ExperienceSession) -> ExperienceSession:
    if session.state not in {ExperienceState.SUBMISSION_ERROR, ExperienceState.REVIEW_ERROR}:
        raise TransitionError("retry is valid only from a recoverable error")
    return replace(session, state=ExperienceState.SUBMITTING, error_code=None)


def complete_review(
    session: ExperienceSession,
    *,
    review_id: str,
    annotations: Tuple[Annotation, ...],
) -> ExperienceSession:
    if session.state is ExperienceState.MARGINALIA and session.review_id == review_id:
        return session
    if session.state is not ExperienceState.SUBMITTING:
        raise TransitionError("review completion is valid only while submitting")
    if session.review_id != review_id:
        raise TransitionError("review_id does not match the durable submission")
    return replace(
        session,
        state=ExperienceState.MARGINALIA,
        annotations=tuple(annotations),
        error_code=None,
    )


def _fail(
    session: ExperienceSession,
    state: ExperienceState,
    error_code: str,
) -> ExperienceSession:
    if session.state is not ExperienceState.SUBMITTING:
        raise TransitionError("only an in-flight submission can fail")
    _require_identifier(error_code, "error_code")
    return replace(session, state=state, error_code=error_code)


def _require_identifier(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must not be empty")


def _parse_timestamp(value: str, field: str) -> datetime:
    if not isinstance(value, str) or re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})",
        value,
    ) is None:
        raise ValueError(f"{field} must be an RFC 3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{field} must be an RFC 3339 timestamp") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed
