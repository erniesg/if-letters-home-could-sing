import json
import unittest
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from experience_core import Point, Stroke, validate_payload
from experience_core.privacy import (
    OPERATIONAL_CATEGORIES,
    AggregateTombstone,
    ConsentRecord,
    InMemorySessionStore,
    InteractionEvent,
    RetentionDeletionService,
    RetentionSchedule,
    SessionRecord,
    load_consent_copy,
    make_installation_export,
    new_pseudonymous_session_id,
)
from heart_rate import CaptureGap, HeartRateSample


ROOT = Path(__file__).resolve().parents[1]
BASE = datetime(2026, 7, 14, tzinfo=timezone.utc)


def at(seconds):
    return BASE + timedelta(seconds=seconds)


def private_record(*, research=True, tombstone=False, include_export=True):
    consent = ConsentRecord("fixture-session-0001").decide_biometric(
        "granted", at(2)
    )
    if research:
        consent = consent.decide_research("granted", at(4))
    retention = RetentionSchedule(
        created_at=BASE,
        operational_deadline=at(60),
        research_deadline=at(120) if research else None,
        aggregate_tombstone_approval=(
            "fixture-approval-curatorial-001" if tombstone else None
        ),
    )
    record = SessionRecord(
        session_id=consent.session_id,
        consent=consent,
        retention=retention,
        first_ink_at=at(10),
        submitted_at=at(50),
        ink=(
            Stroke(
                "stroke-1",
                "2026-07-14T00:00:10Z",
                (Point(0.2, 0.3, 0.5), Point(0.3, 0.4, 0.6)),
            ),
        ),
        derived_images=("fixture-derived-private",),
        transcripts=("fixture participant ink transcript",),
        review={"summary": "fixture private review"},
        heart_rate_samples=(
            HeartRateSample(
                captured_at=at(5),
                received_at=at(11),
                bpm=78,
                source="fixture-provider",
                quality_flags=("good", "clock-skew-observed"),
            ),
        ),
        heart_rate_gaps=(CaptureGap(at(20), at(25), "fixture-provider"),),
        token_references=("fixture-token-private",),
        provider_payloads=(
            {
                "email": "participant@example.invalid",
                "github": "fixture-github-metadata",
                "rucksack": "fixture-rucksack-metadata",
            },
        ),
        interaction_events=(InteractionEvent(at(51), "marginalia-viewed"),),
    )
    if include_export and research:
        record = replace(
            record,
            installation_export=make_installation_export(
                record, export_id="fixture-export-0001"
            ),
        )
    return record


class ConsentContractTests(unittest.TestCase):
    def test_versioned_notice_has_two_equivalent_flow_choices(self):
        copy = load_consent_copy()
        self.assertEqual(copy["consent_version"], "consent-v1")
        self.assertIn("optional", copy["purpose_notice"].lower())
        self.assertEqual(
            [(choice["label"], choice["records"]) for choice in copy["choices"]],
            [
                ("Connect WHOOP", "granted"),
                ("Continue without heart rate", "declined"),
            ],
        )
        validate_payload("consent-copy", copy)

    def test_session_id_is_random_shaped_and_not_derived_from_profile_data(self):
        session_id = new_pseudonymous_session_id(bytes(range(16)))
        self.assertEqual(session_id, "session-000102030405060708090a0b0c0d0e0f")
        consent = ConsentRecord(session_id).decide_biometric("declined", at(2))
        validate_payload("consent", consent.as_payload())
        self.assertNotIn("email", ConsentRecord.__dataclass_fields__)
        self.assertNotIn("profile", ConsentRecord.__dataclass_fields__)
        self.assertNotIn("whoop_email", SessionRecord.__dataclass_fields__)
        self.assertNotIn("whoop_profile", SessionRecord.__dataclass_fields__)
        with self.assertRaises(TypeError):
            ConsentRecord(session_id, whoop_email="participant@example.invalid")

    def test_checked_in_consent_state_fixture_validates(self):
        payload = json.loads(
            (ROOT / "contracts" / "v1" / "fixtures" / "consent.valid.json").read_text()
        )
        validate_payload("consent", payload)


class InstallationExportTests(unittest.TestCase):
    def test_export_uses_gateway_relative_time_and_allowlists_fields(self):
        export = make_installation_export(
            private_record(include_export=False), export_id="fixture-export-0001"
        )
        sample = export["heart_rate"]["samples"][0]
        self.assertEqual(sample["elapsed_ms"], 1000)
        self.assertEqual(sample["source_clock_offset_ms"], -6000)
        self.assertEqual(sample["bpm"], 78)
        self.assertEqual(export["heart_rate"]["gaps"][0]["started_elapsed_ms"], 10000)
        self.assertEqual(export["duration_ms"], 40000)
        self.assertIn(
            {"elapsed_ms": 40000, "event": "submit"},
            export["interaction_events"],
        )
        rendered = json.dumps(export, sort_keys=True)
        for forbidden in (
            "fixture-token-private",
            "participant@example.invalid",
            "fixture-github-metadata",
            "fixture-rucksack-metadata",
            "provider_payload",
            "token_reference",
            "2026-07-14",
        ):
            self.assertNotIn(forbidden, rendered)
        validate_payload("installation-export", export)

    def test_export_requires_separate_research_opt_in(self):
        record = private_record(research=False, include_export=False)
        with self.assertRaisesRegex(ValueError, "separate research consent"):
            make_installation_export(record, export_id="fixture-export-0001")

    def test_checked_in_export_fixture_validates(self):
        payload = json.loads(
            (
                ROOT
                / "contracts"
                / "v1"
                / "fixtures"
                / "installation-export.valid.json"
            ).read_text()
        )
        validate_payload("installation-export", payload)


class RetentionDeletionTests(unittest.TestCase):
    def test_operational_expiry_preserves_only_opted_in_research_export(self):
        record = private_record()
        store = InMemorySessionStore((record,))
        service = RetentionDeletionService(store)

        self.assertEqual(service.expire_due(at(59)), ())
        operational = service.expire_due(at(61))[0]
        retained = store.get(record.session_id)
        self.assertEqual(operational.status, "retained-research")
        self.assertIsInstance(retained, SessionRecord)
        self.assertTrue(all(getattr(retained, field) in ((), None) for field in OPERATIONAL_CATEGORIES))
        self.assertIsNotNone(retained.installation_export)

        research = service.expire_due(at(121))[0]
        self.assertEqual(research.status, "deleted")
        self.assertIsNone(store.get(record.session_id))

    def test_deletion_is_idempotent_and_removes_every_sensitive_category(self):
        record = private_record()
        audit = []
        store = InMemorySessionStore((record,))
        service = RetentionDeletionService(store, audit.append)

        first = service.delete(record.session_id, at(55))
        second = service.delete(record.session_id, at(56))
        self.assertEqual(first.status, "deleted")
        self.assertIsNone(store.get(record.session_id))
        self.assertTrue(second.idempotent)
        self.assertEqual(second.deleted_categories, ())

        rendered_audit = json.dumps([asdict(event) for event in audit], sort_keys=True)
        for private_value in (
            "fixture participant ink transcript",
            "fixture-token-private",
            "participant@example.invalid",
            '"bpm": 78',
        ):
            self.assertNotIn(private_value, rendered_audit)
        self.assertIn("fixture-session-0001", rendered_audit)

    def test_partial_storage_failure_is_retryable_without_restoring_data(self):
        record = private_record()
        store = InMemorySessionStore((record,), fail_once=("heart_rate_samples",))
        service = RetentionDeletionService(store)

        partial = service.delete(record.session_id, at(55))
        remaining = store.get(record.session_id)
        self.assertEqual(partial.status, "partial")
        self.assertEqual(partial.failed_categories, ("heart_rate_samples",))
        self.assertIsInstance(remaining, SessionRecord)
        self.assertEqual(len(remaining.heart_rate_samples), 1)
        self.assertEqual(remaining.ink, ())
        self.assertEqual(remaining.token_references, ())

        retried = service.delete(record.session_id, at(56))
        self.assertEqual(retried.status, "deleted")
        self.assertIsNone(store.get(record.session_id))

    def test_withdrawal_deletes_and_only_explicit_aggregate_may_remain(self):
        record = private_record(tombstone=True)
        store = InMemorySessionStore((record,))
        service = RetentionDeletionService(store)

        result = service.withdraw(record.session_id, at(55))
        retained = store.get(record.session_id)
        self.assertEqual(result.status, "deleted")
        self.assertIsInstance(retained, AggregateTombstone)
        self.assertEqual(retained.approval_id, "fixture-approval-curatorial-001")
        self.assertEqual(retained.aggregate.sample_count, 1)
        self.assertFalse(hasattr(retained, "ink"))
        self.assertTrue(service.delete(record.session_id, at(56)).idempotent)

    def test_clock_skew_cannot_move_a_retention_deadline_backwards(self):
        with self.assertRaisesRegex(ValueError, "cannot predate session creation"):
            RetentionSchedule(created_at=BASE, operational_deadline=at(-1))
        record = private_record()
        store = InMemorySessionStore((record,))
        self.assertEqual(RetentionDeletionService(store).expire_due(at(-30)), ())
        self.assertIs(store.get(record.session_id), record)


if __name__ == "__main__":
    unittest.main()
