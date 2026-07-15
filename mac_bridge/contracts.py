"""Strict model-output contracts for reversible teacher marginalia."""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any, Mapping


MAX_ANNOTATIONS = 10
MAX_SUMMARY = 360
MAX_FIELD = 600
MAX_LETTER = 180
MIN_NOTEBOOK_LETTER = 144
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
NOTE_KINDS = ALLOWED_KINDS - {"correction"}


class ReviewContractError(ValueError):
    """Raised when model output could clip, judge, or fabricate the reply."""


@dataclass(frozen=True)
class Letter:
    body: str


@dataclass(frozen=True)
class Anchor:
    x: float
    y: float
    width: float
    height: float


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
    response_letter: str


@dataclass(frozen=True)
class NotebookReview:
    schema_version: int
    summary: str
    corrections: tuple[Annotation, ...]
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


def parse_letter_text(value: Any, *, minimum: int = 0) -> Letter:
    """Validate one fictional letter before displaying or persisting it."""

    body = _text(value, "letter", maximum=MAX_LETTER)
    if len(body) < minimum:
        raise ReviewContractError("letter is too short")
    if body.startswith("```") or body.endswith("```"):
        raise ReviewContractError("letter must not contain a code fence")
    if len(re.findall(r"[\u3400-\u9fff]", body)) < 12:
        raise ReviewContractError("letter must contain Chinese prose")
    return Letter(body)


def parse_review(payload: Mapping[str, Any]) -> Review:
    """Validate and freeze one Codex review before it reaches the tablet."""

    if not isinstance(payload, Mapping):
        raise ReviewContractError("review must be an object")
    if payload.get("schema_version") != 3:
        raise ReviewContractError("unsupported review schema")
    summary = _text(payload.get("summary"), "summary", maximum=MAX_SUMMARY)
    question = _text(
        payload.get("reflective_question"),
        "reflective_question",
        maximum=MAX_SUMMARY,
    )
    response_letter = parse_letter_text(payload.get("response_letter")).body
    corrections_payload = payload.get("corrections")
    annotations_payload = payload.get("annotations")
    if not isinstance(corrections_payload, list):
        raise ReviewContractError("corrections must be a list")
    if not isinstance(annotations_payload, list):
        raise ReviewContractError("annotations must be a list")
    if len(corrections_payload) + len(annotations_payload) > MAX_ANNOTATIONS:
        raise ReviewContractError("too many annotations")

    annotations = []
    entries = [("correction", raw) for raw in corrections_payload]
    entries.extend((None, raw) for raw in annotations_payload)
    for index, (forced_kind, raw) in enumerate(entries):
        if not isinstance(raw, Mapping):
            raise ReviewContractError(f"annotation {index} must be an object")
        kind = forced_kind or raw.get("kind")
        if kind not in ALLOWED_KINDS or (forced_kind is None and kind == "correction"):
            raise ReviewContractError(f"annotation {index} has an unknown kind")
        confidence = raw.get("confidence")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
            raise ReviewContractError(f"annotation {index} confidence must be numeric")
        confidence = float(confidence)
        if not 0 <= confidence <= 1:
            raise ReviewContractError(f"annotation {index} confidence is outside 0..1")
        if kind == "correction" and confidence < 0.8:
            raise ReviewContractError(f"annotation {index} correction confidence is too low")
        if confidence < 0.7 and kind not in {"uncertain-reading", "reflection"}:
            raise ReviewContractError(
                f"annotation {index} must expose a low-confidence reading as uncertain"
            )
        anchor = raw.get("anchor")
        if not isinstance(anchor, Mapping):
            raise ReviewContractError(f"annotation {index} anchor must be an object")
        x, y = anchor.get("x"), anchor.get("y")
        width, height = anchor.get("width"), anchor.get("height")
        if not all(
            isinstance(value, (int, float)) and not isinstance(value, bool)
            for value in (x, y, width, height)
        ):
            raise ReviewContractError(f"annotation {index} anchor must be numeric")
        x, y, width, height = map(float, (x, y, width, height))
        if x < 0 or y < 0 or width <= 0 or height <= 0 or x + width > 1 or y + height > 1:
            raise ReviewContractError(f"annotation {index} anchor is outside the page")
        observed_text = _text(raw.get("observed_text"), f"annotation {index} observed_text")
        suggested_text = _text(
            raw.get("suggested_text"),
            f"annotation {index} suggested_text",
            allow_empty=kind in {"affirmation", "reflection"},
        )
        if kind == "correction" and (len(observed_text) != 1 or len(suggested_text) != 1):
            raise ReviewContractError(f"annotation {index} correction must identify one glyph")
        annotations.append(
            Annotation(
                kind=kind,
                observed_text=observed_text,
                suggested_text=suggested_text,
                explanation=_text(raw.get("explanation"), f"annotation {index} explanation"),
                confidence=confidence,
                anchor=Anchor(x, y, width, height),
            )
        )
    return Review(3, summary, tuple(annotations), question, response_letter)


def parse_notebook_review(payload: Mapping[str, Any]) -> NotebookReview:
    """Validate reversible marginalia separately from the reciprocal letter."""

    if not isinstance(payload, Mapping) or payload.get("schema_version") != 1:
        raise ReviewContractError("unsupported notebook review schema")
    legacy_payload = dict(payload)
    legacy_payload["schema_version"] = 3
    legacy_payload["response_letter"] = "家中一切安好，盼你慢慢写信回来。"
    validated = parse_review(legacy_payload)
    corrections = tuple(
        annotation
        for annotation in validated.annotations
        if annotation.kind == "correction"
    )
    annotations = tuple(
        annotation
        for annotation in validated.annotations
        if annotation.kind != "correction"
    )
    return NotebookReview(
        schema_version=1,
        summary=validated.summary,
        corrections=corrections,
        annotations=annotations,
        reflective_question=validated.reflective_question,
    )


ANCHOR_OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["x", "y", "width", "height"],
    "properties": {
        "x": {"type": "number", "minimum": 0, "maximum": 1},
        "y": {"type": "number", "minimum": 0, "maximum": 1},
        "width": {"type": "number", "exclusiveMinimum": 0, "maximum": 1},
        "height": {"type": "number", "exclusiveMinimum": 0, "maximum": 1},
    },
}


REVIEW_OUTPUT_SCHEMA = {
    "title": "LettersHomeReview",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "schema_version",
        "summary",
        "corrections",
        "annotations",
        "reflective_question",
        "response_letter",
    ],
    "properties": {
        "schema_version": {"type": "integer", "const": 3},
        "summary": {"type": "string", "minLength": 1, "maxLength": MAX_SUMMARY},
        "corrections": {
            "type": "array",
            "maxItems": MAX_ANNOTATIONS,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "observed_text",
                    "suggested_text",
                    "explanation",
                    "confidence",
                    "anchor",
                ],
                "properties": {
                    "observed_text": {"type": "string", "minLength": 1, "maxLength": 1},
                    "suggested_text": {"type": "string", "minLength": 1, "maxLength": 1},
                    "explanation": {"type": "string", "minLength": 1, "maxLength": MAX_FIELD},
                    "confidence": {"type": "number", "minimum": 0.8, "maximum": 1},
                    "anchor": ANCHOR_OUTPUT_SCHEMA,
                },
            },
        },
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
                    "kind": {"type": "string", "enum": sorted(NOTE_KINDS)},
                    "observed_text": {"type": "string", "maxLength": MAX_FIELD},
                    "suggested_text": {"type": "string", "maxLength": MAX_FIELD},
                    "explanation": {"type": "string", "maxLength": MAX_FIELD},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "anchor": ANCHOR_OUTPUT_SCHEMA,
                },
            },
        },
        "reflective_question": {
            "type": "string",
            "minLength": 1,
            "maxLength": MAX_SUMMARY,
        },
        "response_letter": {
            "type": "string",
            "minLength": 1,
            "maxLength": MAX_LETTER,
        },
    },
}


NOTEBOOK_REVIEW_OUTPUT_SCHEMA = copy.deepcopy(REVIEW_OUTPUT_SCHEMA)
NOTEBOOK_REVIEW_OUTPUT_SCHEMA["title"] = "LettersHomeNotebookReview"
NOTEBOOK_REVIEW_OUTPUT_SCHEMA["required"].remove("response_letter")
del NOTEBOOK_REVIEW_OUTPUT_SCHEMA["properties"]["response_letter"]
NOTEBOOK_REVIEW_OUTPUT_SCHEMA["properties"]["schema_version"]["const"] = 1
