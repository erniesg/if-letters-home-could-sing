"""Immutable reply-review boundary and deterministic fixture provider."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from html import escape
from typing import Mapping, Protocol, Sequence, Tuple

from .contracts import ContractValidationError, validate_payload
from .state_machine import Anchor, Annotation, ExperienceSession, Point, Stroke


@dataclass(frozen=True)
class RenderedReplyPage:
    """A deterministic page rendering supplied alongside reply vectors."""

    width: int
    height: int
    media_type: str
    content: bytes
    source_strokes_sha256: str

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("rendered page dimensions must be positive")
        if self.media_type != "image/svg+xml":
            raise ValueError("fixture rendered pages must use SVG")
        if not isinstance(self.content, bytes) or not self.content:
            raise ValueError("rendered page content must be non-empty bytes")
        if len(self.source_strokes_sha256) != 64:
            raise ValueError("source stroke digest must be SHA-256")

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.content).hexdigest()


@dataclass(frozen=True)
class ReviewRequest:
    """Provider input detached from the durable session."""

    session_id: str
    review_id: str
    strokes: Tuple[Stroke, ...]
    rendered_page: RenderedReplyPage

    def __post_init__(self) -> None:
        strokes = tuple(self.strokes)
        object.__setattr__(self, "strokes", strokes)
        if not self.session_id.strip() or not self.review_id.strip():
            raise ValueError("review request identifiers must not be empty")
        if _stroke_digest(strokes) != self.rendered_page.source_strokes_sha256:
            raise ValueError("rendered page must match the supplied stroke vectors")


class ReplyReviewer(Protocol):
    """Boundary implemented by fixture and future approved review providers."""

    def review(self, request: ReviewRequest) -> Mapping[str, object]:
        """Return a versioned structured review without changing ``request``."""


class ReviewProviderError(RuntimeError):
    """Safe provider failure containing only a stable local error code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class FixtureReplyReviewer:
    """Deterministic reviews for ordinary and non-judgmental edge states."""

    CASES = (
        "auto",
        "standard",
        "empty",
        "non-chinese",
        "mixed-language",
        "illegible",
        "provider-error",
    )

    def __init__(self, case: str = "auto") -> None:
        if case not in self.CASES:
            raise ValueError(f"unknown reply review fixture: {case}")
        self.case = case

    def review(self, request: ReviewRequest) -> Mapping[str, object]:
        case = "empty" if self.case == "auto" and not request.strokes else self.case
        if case == "auto":
            case = "standard"
        if case == "provider-error":
            raise ReviewProviderError("reviewer_unavailable")

        fixture = _FIXTURE_REVIEWS[case]
        return {
            "schema_version": "1",
            "review_id": request.review_id,
            "session_id": request.session_id,
            "reviewer": "fixture-reply-reviewer-v1",
            "status": fixture["status"],
            "summary": fixture["summary"],
            "annotations": json.loads(json.dumps(fixture["annotations"])),
        }


def make_review_request(
    session: ExperienceSession,
    *,
    width: int = 1000,
    height: int = 1400,
) -> ReviewRequest:
    """Detach immutable provider input from a durably submitted session."""

    if session.review_id is None or session.submitted_at is None:
        raise ValueError("review input requires a durably submitted session")
    strokes = tuple(_copy_stroke(stroke) for stroke in session.strokes)
    return ReviewRequest(
        session_id=session.session_id,
        review_id=session.review_id,
        strokes=strokes,
        rendered_page=render_reply_page(strokes, width=width, height=height),
    )


def render_reply_page(
    strokes: Sequence[Stroke],
    *,
    width: int = 1000,
    height: int = 1400,
) -> RenderedReplyPage:
    """Render stroke vectors to stable SVG bytes without changing the vectors."""

    if width <= 0 or height <= 0:
        raise ValueError("rendered page dimensions must be positive")
    frozen_strokes = tuple(strokes)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="#f6efdf"/>',
        '<g fill="none" stroke="#33475b" stroke-linecap="round">',
    ]
    for stroke in frozen_strokes:
        coordinates = [
            (round(point.x * width, 3), round(point.y * height, 3))
            for point in stroke.points
        ]
        path = " ".join(
            f'{"M" if index == 0 else "L"} {_number(x)} {_number(y)}'
            for index, (x, y) in enumerate(coordinates)
        )
        pressures = [point.pressure for point in stroke.points if point.pressure is not None]
        mean_pressure = sum(pressures) / len(pressures) if pressures else 0.5
        stroke_width = _number(max(2.0, mean_pressure * 8.0))
        parts.append(
            f'<path data-stroke-id="{escape(stroke.stroke_id, quote=True)}" '
            f'd="{path}" stroke-width="{stroke_width}"/>'
        )
    parts.extend(("</g>", "</svg>"))
    content = ("\n".join(parts) + "\n").encode("utf-8")
    return RenderedReplyPage(
        width=width,
        height=height,
        media_type="image/svg+xml",
        content=content,
        source_strokes_sha256=_stroke_digest(frozen_strokes),
    )


def review_reply(
    reviewer: ReplyReviewer,
    request: ReviewRequest,
) -> Mapping[str, object]:
    """Call a reviewer, fail closed on mutation, and validate its output."""

    input_digest = _request_digest(request)
    try:
        provider_payload = reviewer.review(request)
    except ReviewProviderError:
        raise
    except Exception:
        raise ReviewProviderError("reviewer_unavailable") from None

    try:
        mutated = _request_digest(request) != input_digest
    except Exception:
        mutated = True
    if mutated:
        raise ReviewProviderError("reviewer_mutated_input")
    try:
        payload = json.loads(json.dumps(provider_payload, allow_nan=False))
        validate_payload("review", payload)
    except (ContractValidationError, TypeError, ValueError):
        raise ReviewProviderError("invalid_review") from None
    if payload["review_id"] != request.review_id or payload["session_id"] != request.session_id:
        raise ReviewProviderError("invalid_review")
    return payload


def review_annotations(payload: Mapping[str, object]) -> Tuple[Annotation, ...]:
    """Convert a validated review document to reversible overlay values."""

    validate_payload("review", payload)
    return tuple(
        Annotation(
            annotation_id=item["id"],
            kind=item["kind"],
            anchor=Anchor(**item["anchor"]),
            message=item["message"],
            confidence=item["confidence"],
        )
        for item in payload["annotations"]
    )


def _copy_stroke(stroke: Stroke) -> Stroke:
    return Stroke(
        stroke_id=stroke.stroke_id,
        accepted_at=stroke.accepted_at,
        points=tuple(
            Point(x=point.x, y=point.y, pressure=point.pressure)
            for point in stroke.points
        ),
    )


def _stroke_digest(strokes: Sequence[Stroke]) -> str:
    payload = [
        {
            "stroke_id": stroke.stroke_id,
            "accepted_at": stroke.accepted_at,
            "points": [
                {"x": point.x, "y": point.y, "pressure": point.pressure}
                for point in stroke.points
            ],
        }
        for stroke in strokes
    ]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _request_digest(request: ReviewRequest) -> str:
    encoded = (
        request.session_id
        + "\0"
        + request.review_id
        + "\0"
        + _stroke_digest(request.strokes)
        + "\0"
        + request.rendered_page.sha256
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _number(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


_FIXTURE_REVIEWS = {
    "standard": {
        "status": "reviewed",
        "summary": "A warm reply with a clear respectful tone. Two small word-order and character choices may need attention.",
        "annotations": [
            {
                "id": "annotation-correction",
                "kind": "correction",
                "anchor": {"page": 2, "x": 0.18, "y": 0.24, "width": 0.12, "height": 0.06},
                "message": "Use 您 here so the respectful address stays consistent.",
                "confidence": 0.93,
            },
            {
                "id": "annotation-uncertain",
                "kind": "uncertain-reading",
                "anchor": {"page": 2, "x": 0.61, "y": 0.42, "width": 0.08, "height": 0.04},
                "message": "I am not certain this character is 家; is that what you intended?",
                "confidence": 0.54,
            },
            {
                "id": "annotation-grammar",
                "kind": "correction",
                "anchor": {"page": 2, "x": 0.48, "y": 0.51, "width": 0.20, "height": 0.06},
                "message": "Place 也 before 很想念您 so the sentence reads more naturally.",
                "confidence": 0.91,
            },
            {
                "id": "annotation-tone",
                "kind": "tone",
                "anchor": {"page": 2, "x": 0.24, "y": 0.68, "width": 0.25, "height": 0.06},
                "message": "请勿挂念 keeps this reassurance warm rather than abrupt.",
                "confidence": 0.95,
            },
            {
                "id": "annotation-affirmation",
                "kind": "affirmation",
                "anchor": {"page": 2, "x": 0.36, "y": 0.58, "width": 0.24, "height": 0.07},
                "message": "Your reassurance about the family feels clear and warm.",
                "confidence": 0.98,
            },
            {
                "id": "annotation-reflection",
                "kind": "reflection",
                "anchor": {"page": 2, "x": 0.12, "y": 0.78, "width": 0.62, "height": 0.08},
                "message": "What would you want the reader to know about the distance between you?",
                "confidence": 1.0,
            },
        ],
    },
    "empty": {
        "status": "empty",
        "summary": "There is no ink to read. A blank huipi is still a complete response.",
        "annotations": [],
    },
    "non-chinese": {
        "status": "non-chinese",
        "summary": "This reply appears to use another language. It remains intact, and no language changes were added.",
        "annotations": [],
    },
    "mixed-language": {
        "status": "mixed-language",
        "summary": "This reply moves between languages; the shift is preserved as part of your voice.",
        "annotations": [
            {
                "id": "annotation-language-shift",
                "kind": "affirmation",
                "anchor": {"page": 2, "x": 0.20, "y": 0.45, "width": 0.42, "height": 0.10},
                "message": "The change of language gives this passage its own rhythm.",
                "confidence": 0.96,
            }
        ],
    },
    "illegible": {
        "status": "illegible",
        "summary": "The marks could not be read reliably, so no anchored reading was added. Your original ink remains untouched.",
        "annotations": [],
    },
}
