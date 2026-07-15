"""Strict model-output contracts for reversible teacher marginalia."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping


MAX_ANNOTATIONS = 10
MAX_SUMMARY = 360
MAX_FIELD = 600
PROHIBITED_EVALUATION = re.compile(
    r"\b(?:score|grade|marks?|correct answer)\b|(?:评分|分数|打分|成绩|满分)",
    re.IGNORECASE,
)
ALLOWED_KINDS = {
    "correction",
    "uncertain-reading",
    "tone",
    "affirmation",
    "reflection",
}


class ReviewContractError(ValueError):
    """Raised when model output could clip, judge, or fabricate the reply."""


@dataclass(frozen=True)
class Anchor:
    x: float
    y: float


@dataclass(frozen=True)
class Annotation:
    kind: str
    observed_text: str
    suggested_text: str
    explanation: str
    confidence: float
    anchor: Anchor


@dataclass(frozen=True)
class Review:
    schema_version: int
    summary: str
    annotations: tuple[Annotation, ...]
    reflective_question: str


def _text(value: Any, field: str, *, maximum: int = MAX_FIELD, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ReviewContractError(f"{field} must be text")
    cleaned = value.strip()
    if not cleaned and not allow_empty:
        raise ReviewContractError(f"{field} must not be empty")
    if len(cleaned) > maximum:
        raise ReviewContractError(f"{field} is too long")
    if PROHIBITED_EVALUATION.search(cleaned):
        raise ReviewContractError(f"{field} contains scoring language")
    return cleaned


def parse_review(payload: Mapping[str, Any]) -> Review:
    """Validate and freeze one Codex review before it reaches the tablet."""

    if not isinstance(payload, Mapping):
        raise ReviewContractError("review must be an object")
    if payload.get("schema_version") != 1:
        raise ReviewContractError("unsupported review schema")
    summary = _text(payload.get("summary"), "summary", maximum=MAX_SUMMARY)
    question = _text(
        payload.get("reflective_question"),
        "reflective_question",
        maximum=MAX_SUMMARY,
    )
    annotations_payload = payload.get("annotations")
    if not isinstance(annotations_payload, list):
        raise ReviewContractError("annotations must be a list")
    if len(annotations_payload) > MAX_ANNOTATIONS:
        raise ReviewContractError("too many annotations")

    annotations = []
    for index, raw in enumerate(annotations_payload):
        if not isinstance(raw, Mapping):
            raise ReviewContractError(f"annotation {index} must be an object")
        kind = raw.get("kind")
        if kind not in ALLOWED_KINDS:
            raise ReviewContractError(f"annotation {index} has an unknown kind")
        confidence = raw.get("confidence")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
            raise ReviewContractError(f"annotation {index} confidence must be numeric")
        confidence = float(confidence)
        if not 0 <= confidence <= 1:
            raise ReviewContractError(f"annotation {index} confidence is outside 0..1")
        if confidence < 0.7 and kind not in {"uncertain-reading", "reflection"}:
            raise ReviewContractError(
                f"annotation {index} must expose a low-confidence reading as uncertain"
            )
        anchor = raw.get("anchor")
        if not isinstance(anchor, Mapping):
            raise ReviewContractError(f"annotation {index} anchor must be an object")
        x, y = anchor.get("x"), anchor.get("y")
        if not all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in (x, y)):
            raise ReviewContractError(f"annotation {index} anchor must be numeric")
        if not 0 <= float(x) <= 1 or not 0 <= float(y) <= 1:
            raise ReviewContractError(f"annotation {index} anchor is outside the page")
        annotations.append(
            Annotation(
                kind=kind,
                observed_text=_text(raw.get("observed_text"), f"annotation {index} observed_text"),
                suggested_text=_text(
                    raw.get("suggested_text"),
                    f"annotation {index} suggested_text",
                    allow_empty=kind in {"affirmation", "reflection"},
                ),
                explanation=_text(raw.get("explanation"), f"annotation {index} explanation"),
                confidence=confidence,
                anchor=Anchor(float(x), float(y)),
            )
        )
    return Review(1, summary, tuple(annotations), question)


REVIEW_OUTPUT_SCHEMA = {
    "title": "LettersHomeReview",
    "type": "object",
    "additionalProperties": False,
    "required": ["schema_version", "summary", "annotations", "reflective_question"],
    "properties": {
        "schema_version": {"type": "integer", "const": 1},
        "summary": {"type": "string", "minLength": 1, "maxLength": MAX_SUMMARY},
        "annotations": {
            "type": "array",
            "maxItems": MAX_ANNOTATIONS,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "kind",
                    "observed_text",
                    "suggested_text",
                    "explanation",
                    "confidence",
                    "anchor",
                ],
                "properties": {
                    "kind": {"type": "string", "enum": sorted(ALLOWED_KINDS)},
                    "observed_text": {"type": "string", "maxLength": MAX_FIELD},
                    "suggested_text": {"type": "string", "maxLength": MAX_FIELD},
                    "explanation": {"type": "string", "maxLength": MAX_FIELD},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "anchor": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["x", "y"],
                        "properties": {
                            "x": {"type": "number", "minimum": 0, "maximum": 1},
                            "y": {"type": "number", "minimum": 0, "maximum": 1},
                        },
                    },
                },
            },
        },
        "reflective_question": {
            "type": "string",
            "minLength": 1,
            "maxLength": MAX_SUMMARY,
        },
    },
}
