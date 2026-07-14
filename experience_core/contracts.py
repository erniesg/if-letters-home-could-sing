"""Small dependency-free validator for the versioned experience contracts."""

import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any


SCHEMA_DIR = Path(__file__).resolve().parents[1] / "contracts" / "v1" / "schemas"
CONTRACTS = {
    "consent-copy": "consent-copy.schema.json",
    "consent": "consent.schema.json",
    "installation-export": "installation-export.schema.json",
    "letter-provenance": "letter-provenance.schema.json",
    "stroke": "stroke.schema.json",
    "heart-rate": "heart-rate.schema.json",
    "review": "review.schema.json",
    "session": "session.schema.json",
}


class ContractValidationError(ValueError):
    """Raised when a payload violates its versioned wire contract."""


def validate_payload(contract: str, payload: Any) -> None:
    """Validate a payload against its JSON schema and temporal/page invariants."""
    try:
        schema_path = SCHEMA_DIR / CONTRACTS[contract]
    except KeyError as error:
        raise ValueError(f"unknown contract: {contract}") from error
    schema = json.loads(schema_path.read_text())
    _validate_schema(schema, payload, "$", schema_path.parent)
    if contract == "consent-copy":
        _validate_consent_copy(payload)
    elif contract == "consent":
        _validate_consent(payload)
    elif contract == "installation-export":
        _validate_installation_export(payload)
    elif contract == "heart-rate":
        _validate_heart_rate(payload, "$")
    elif contract == "review":
        _validate_review(payload, "$")
    elif contract == "session":
        _validate_session(payload)


def _validate_schema(schema: dict, value: Any, path: str, schema_dir: Path) -> None:
    if "$ref" in schema:
        reference = schema["$ref"]
        if reference.startswith("#"):
            raise ContractValidationError(f"{path} uses an unsupported local schema reference")
        reference_path = schema_dir / reference
        _validate_schema(json.loads(reference_path.read_text()), value, path, reference_path.parent)
        return

    if "const" in schema and value != schema["const"]:
        raise ContractValidationError(f"{path} must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        raise ContractValidationError(f"{path} must be one of {schema['enum']}")

    declared_type = schema.get("type")
    if declared_type is not None:
        types = declared_type if isinstance(declared_type, list) else [declared_type]
        if not any(_matches_type(value, candidate) for candidate in types):
            raise ContractValidationError(f"{path} must have type {' or '.join(types)}")

    if isinstance(value, dict):
        required = schema.get("required", [])
        for field in required:
            if field not in value:
                raise ContractValidationError(f"{path}.{field} is required")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for field in value:
                if field not in properties:
                    raise ContractValidationError(f"{path}.{field} is not allowed")
        for field, field_schema in properties.items():
            if field in value:
                _validate_schema(field_schema, value[field], f"{path}.{field}", schema_dir)

    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            raise ContractValidationError(f"{path} has too few items")
        if len(value) > schema.get("maxItems", len(value)):
            raise ContractValidationError(f"{path} has too many items")
        if schema.get("uniqueItems"):
            canonical = [json.dumps(item, sort_keys=True) for item in value]
            if len(canonical) != len(set(canonical)):
                raise ContractValidationError(f"{path} must contain unique items")
        if "items" in schema:
            for index, item in enumerate(value):
                _validate_schema(schema["items"], item, f"{path}[{index}]", schema_dir)

    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            raise ContractValidationError(f"{path} must not be empty")
        if len(value) > schema.get("maxLength", len(value)):
            raise ContractValidationError(f"{path} is too long")
        if "pattern" in schema and re.fullmatch(schema["pattern"], value) is None:
            raise ContractValidationError(f"{path} does not match the required pattern")
        if schema.get("format") == "date-time":
            _timestamp(value, path)

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(value):
            raise ContractValidationError(f"{path} must be finite")
        if "minimum" in schema and value < schema["minimum"]:
            raise ContractValidationError(f"{path} is below the minimum")
        if "maximum" in schema and value > schema["maximum"]:
            raise ContractValidationError(f"{path} is above the maximum")
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            raise ContractValidationError(f"{path} must be greater than {schema['exclusiveMinimum']}")


def _matches_type(value: Any, declared: str) -> bool:
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }.get(declared, False)


def _timestamp(value: str, path: str) -> datetime:
    if not isinstance(value, str) or re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})",
        value,
    ) is None:
        raise ContractValidationError(f"{path} must be an RFC 3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as error:
        raise ContractValidationError(f"{path} must be an RFC 3339 timestamp") from error
    if parsed.tzinfo is None:
        raise ContractValidationError(f"{path} must be an RFC 3339 timestamp with timezone")
    return parsed


def _validate_heart_rate(payload: dict, path: str) -> None:
    if payload["consent"] in {"declined", "unavailable"} and payload["samples"]:
        raise ContractValidationError(f"{path}.samples must be empty without granted consent")
    for index, sample in enumerate(payload["samples"]):
        captured = _timestamp(sample["captured_at"], f"{path}.samples[{index}].captured_at")
        received = _timestamp(sample["received_at"], f"{path}.samples[{index}].received_at")
        if received < captured:
            raise ContractValidationError("captured_at must not be after received_at")
    for index, gap in enumerate(payload["gaps"]):
        started = _timestamp(gap["started_at"], f"{path}.gaps[{index}].started_at")
        ended = _timestamp(gap["ended_at"], f"{path}.gaps[{index}].ended_at")
        if ended < started:
            raise ContractValidationError("heart-rate gap cannot end before it starts")


def _validate_consent_copy(payload: dict) -> None:
    choices = {choice["id"]: choice for choice in payload["choices"]}
    expected = {
        "connect-whoop": "granted",
        "continue-without-heart-rate": "declined",
    }
    if set(choices) != set(expected):
        raise ContractValidationError("$.choices must contain both biometric choices")
    for choice_id, decision in expected.items():
        if choices[choice_id]["records"] != decision:
            raise ContractValidationError(f"$.choices[{choice_id}] records the wrong decision")


def _validate_consent(payload: dict) -> None:
    biometric_decided = payload["biometric_decided_at"]
    if (payload["biometric_decision"] == "pending") != (biometric_decided is None):
        raise ContractValidationError(
            "$.biometric_decided_at must be set exactly when biometric consent is decided"
        )
    research_decided = payload["research_decided_at"]
    if (payload["research_decision"] == "not-requested") != (research_decided is None):
        raise ContractValidationError(
            "$.research_decided_at must be set exactly when research consent is decided"
        )
    withdrawn = payload["withdrawn_at"]
    if withdrawn:
        withdrawn_at = _timestamp(withdrawn, "$.withdrawn_at")
        decisions = [value for value in (biometric_decided, research_decided) if value]
        if decisions and withdrawn_at < max(
            _timestamp(value, "$.consent_decision") for value in decisions
        ):
            raise ContractValidationError("$.withdrawn_at cannot predate a consent decision")


def _validate_installation_export(payload: dict) -> None:
    sample_times = [item["elapsed_ms"] for item in payload["heart_rate"]["samples"]]
    if sample_times != sorted(sample_times):
        raise ContractValidationError("$.heart_rate.samples must be ordered by elapsed_ms")
    for gap in payload["heart_rate"]["gaps"]:
        if gap["ended_elapsed_ms"] < gap["started_elapsed_ms"]:
            raise ContractValidationError("installation export gap cannot end before it starts")
    events = payload["interaction_events"]
    event_times = [item["elapsed_ms"] for item in events]
    if event_times != sorted(event_times):
        raise ContractValidationError("$.interaction_events must be ordered by elapsed_ms")
    if not any(item == {"elapsed_ms": 0, "event": "first-ink"} for item in events):
        raise ContractValidationError("installation export must anchor first ink at zero")
    if not any(
        item == {"elapsed_ms": payload["duration_ms"], "event": "submit"}
        for item in events
    ):
        raise ContractValidationError("installation export must end with submit at duration_ms")


def _validate_review(payload: dict, path: str) -> None:
    annotation_ids = [annotation["id"] for annotation in payload["annotations"]]
    if len(annotation_ids) != len(set(annotation_ids)):
        raise ContractValidationError(f"{path}.annotations must use unique ids")
    forbidden = re.compile(r"\b(?:scores?|grades?|correct answer|full transcription)\b", re.IGNORECASE)
    for field, text in (("summary", payload["summary"]),):
        if forbidden.search(text):
            raise ContractValidationError(f"{path}.{field} uses prohibited evaluative language")
    for index, annotation in enumerate(payload["annotations"]):
        anchor = annotation["anchor"]
        if anchor["x"] + anchor["width"] > 1 or anchor["y"] + anchor["height"] > 1:
            raise ContractValidationError(
                f"{path}.annotations[{index}].anchor extends beyond page"
            )
        message = annotation["message"]
        if forbidden.search(message):
            raise ContractValidationError(
                f"{path}.annotations[{index}].message uses prohibited evaluative language"
            )
        if annotation["confidence"] < 0.7:
            if annotation["kind"] == "correction":
                raise ContractValidationError("low-confidence text cannot be a correction")
            uncertainty = re.compile(
                r"(?:\?|\b(?:might|perhaps|unclear|difficult to read|not sure|could)\b)",
                re.IGNORECASE,
            )
            if uncertainty.search(message) is None:
                raise ContractValidationError(
                    "low-confidence text must be phrased as a question or uncertainty"
                )


def _validate_session(payload: dict) -> None:
    created = _timestamp(payload["created_at"], "$.created_at")
    first = _timestamp(payload["first_ink_at"], "$.first_ink_at") if payload["first_ink_at"] else None
    submitted = _timestamp(payload["submitted_at"], "$.submitted_at") if payload["submitted_at"] else None
    retention = _timestamp(payload["retention_deadline"], "$.retention_deadline")

    if first and first < created:
        raise ContractValidationError("first_ink_at cannot predate created_at")
    if submitted and submitted < (first or created):
        raise ContractValidationError("submitted_at cannot predate the capture window")
    if submitted and retention < submitted:
        raise ContractValidationError("retention_deadline cannot predate submitted_at")
    if payload["strokes"]:
        accepted = [_timestamp(item["accepted_at"], "$.strokes[].accepted_at") for item in payload["strokes"]]
        if first is None or first != accepted[0]:
            raise ContractValidationError("first_ink_at must equal the first accepted stroke")
        if accepted != sorted(accepted):
            raise ContractValidationError("strokes must be ordered by accepted_at")
    elif first is not None:
        raise ContractValidationError("first_ink_at requires at least one stroke")

    submitted_states = {"submitting", "submission_error", "review_error", "marginalia"}
    if payload["state"] in submitted_states and (not submitted or not payload["review_id"]):
        raise ContractValidationError("submitted states require submitted_at and review_id")
    if payload["state"] in {"incoming", "reply"} and (submitted or payload["review_id"]):
        raise ContractValidationError("unsubmitted states cannot have submission identifiers")
    error_states = {"submission_error", "review_error"}
    if payload["state"] in error_states and not payload["error_code"]:
        raise ContractValidationError("recoverable error states require error_code")
    if payload["state"] not in error_states and payload["error_code"]:
        raise ContractValidationError("error_code is valid only in recoverable error states")

    heart_rate = payload["heart_rate"]
    _validate_heart_rate(heart_rate, "$.heart_rate")
    if heart_rate["samples"]:
        if first is None or submitted is None:
            raise ContractValidationError("heart-rate samples require a closed capture window")
        for sample in heart_rate["samples"]:
            captured = _timestamp(sample["captured_at"], "$.heart_rate.samples[].captured_at")
            if captured < first or captured > submitted:
                raise ContractValidationError("heart-rate sample falls outside the capture window")
