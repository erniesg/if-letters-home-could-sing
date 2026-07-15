import json
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from experience_core import (
    Anchor,
    Annotation,
    ContractValidationError,
    ExperienceState,
    Point,
    Stroke,
    TransitionError,
    accept_stroke,
    complete_review,
    fail_review,
    fail_submission,
    new_session,
    retry,
    submit,
    swipe,
    validate_payload,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "contracts" / "v1" / "fixtures"


def stroke(stroke_id="stroke-1", accepted_at="2026-07-14T00:00:12Z"):
    return Stroke(
        stroke_id=stroke_id,
        accepted_at=accepted_at,
        points=(Point(x=0.2, y=0.3, pressure=0.5), Point(x=0.3, y=0.4, pressure=0.6)),
    )


class ExperienceStateMachineTests(unittest.TestCase):
    def setUp(self):
        self.session = new_session(
            session_id="fixture-session-0001",
            created_at="2026-07-14T00:00:00Z",
        )

    def test_declares_page_submission_and_recoverable_error_states(self):
        self.assertEqual(
            {state.value for state in ExperienceState},
            {
                "incoming",
                "reply",
                "submitting",
                "submission_error",
                "review_error",
                "marginalia",
            },
        )

    def test_only_forward_swipe_opens_reply_and_back_preserves_ink(self):
        self.assertIs(swipe(self.session, "backward"), self.session)
        reply = swipe(self.session, "forward")
        with_ink = accept_stroke(reply, stroke())

        incoming = swipe(with_ink, "backward")
        restored = swipe(incoming, "forward")

        self.assertEqual(incoming.state, ExperienceState.INCOMING)
        self.assertEqual(restored.state, ExperienceState.REPLY)
        self.assertEqual(restored.strokes, with_ink.strokes)
        self.assertEqual(restored.first_ink_at, "2026-07-14T00:00:12Z")

    def test_first_accepted_stroke_sets_first_ink_once(self):
        reply = swipe(self.session, "forward")
        first = accept_stroke(reply, stroke())
        second = accept_stroke(
            first,
            stroke("stroke-2", "2026-07-14T00:00:20Z"),
        )

        self.assertEqual(first.first_ink_at, "2026-07-14T00:00:12Z")
        self.assertEqual(second.first_ink_at, first.first_ink_at)
        self.assertEqual(len(second.strokes), 2)

    def test_accepted_stroke_detaches_from_a_mutable_point_sequence(self):
        points = [Point(x=0.2, y=0.3)]
        accepted = Stroke(
            stroke_id="stroke-1",
            accepted_at="2026-07-14T00:00:12Z",
            points=points,
        )
        points.clear()

        self.assertEqual(len(accepted.points), 1)
        self.assertIsInstance(accepted.points, tuple)

    def test_empty_submit_requires_confirmation_without_fake_strokes(self):
        reply = swipe(self.session, "forward")
        deferred = submit(
            reply,
            review_id="fixture-review-0001",
            submitted_at="2026-07-14T00:00:30Z",
        )
        confirmed = submit(
            deferred.session,
            review_id="fixture-review-0001",
            submitted_at="2026-07-14T00:00:31Z",
            confirm_empty=True,
        )

        self.assertTrue(deferred.confirmation_required)
        self.assertIs(deferred.session, reply)
        self.assertEqual(confirmed.session.state, ExperienceState.SUBMITTING)
        self.assertEqual(confirmed.session.strokes, ())
        self.assertIsNone(confirmed.session.first_ink_at)

    def test_duplicate_submit_reuses_session_and_review_ids(self):
        reply = accept_stroke(swipe(self.session, "forward"), stroke())
        first = submit(
            reply,
            review_id="fixture-review-0001",
            submitted_at="2026-07-14T00:01:02Z",
        ).session
        duplicate = submit(
            first,
            review_id="different-review-id",
            submitted_at="2026-07-14T00:01:03Z",
        ).session

        self.assertIs(duplicate, first)
        self.assertEqual(duplicate.session_id, "fixture-session-0001")
        self.assertEqual(duplicate.review_id, "fixture-review-0001")
        self.assertEqual(duplicate.submitted_at, "2026-07-14T00:01:02Z")

    def test_submission_and_review_errors_retry_from_durable_submission(self):
        reply = accept_stroke(swipe(self.session, "forward"), stroke())
        pending = submit(
            reply,
            review_id="fixture-review-0001",
            submitted_at="2026-07-14T00:01:02Z",
        ).session

        for failed in (
            fail_submission(pending, "gateway_unavailable"),
            fail_review(pending, "reviewer_timeout"),
        ):
            retried = retry(failed)
            self.assertEqual(retried.state, ExperienceState.SUBMITTING)
            self.assertEqual(retried.strokes, pending.strokes)
            self.assertEqual(retried.review_id, pending.review_id)
            self.assertEqual(retried.submitted_at, pending.submitted_at)

    def test_submitted_strokes_are_immutable_and_annotations_are_an_overlay(self):
        reply = accept_stroke(swipe(self.session, "forward"), stroke())
        pending = submit(
            reply,
            review_id="fixture-review-0001",
            submitted_at="2026-07-14T00:01:02Z",
        ).session
        original_strokes = pending.strokes
        annotation = Annotation(
            annotation_id="annotation-1",
            kind="reflection",
            anchor=Anchor(page=2, x=0.1, y=0.2, width=0.3, height=0.1),
            message="What would you want the reader to remember?",
            confidence=1.0,
        )
        marginalia = complete_review(
            pending,
            review_id="fixture-review-0001",
            annotations=(annotation,),
        )

        self.assertEqual(marginalia.state, ExperienceState.MARGINALIA)
        self.assertIs(marginalia.strokes, original_strokes)
        self.assertEqual(marginalia.annotations, (annotation,))
        with self.assertRaises((FrozenInstanceError, AttributeError)):
            marginalia.strokes[0].accepted_at = "2027-01-01T00:00:00Z"
        with self.assertRaises(TransitionError):
            accept_stroke(marginalia, stroke("stroke-2"))


class PayloadContractTests(unittest.TestCase):
    def test_all_positive_fixtures_validate(self):
        fixtures = json.loads((FIXTURES / "valid.json").read_text())
        for contract, payload in fixtures.items():
            with self.subTest(contract=contract):
                validate_payload(contract, payload)
        empty = json.loads((FIXTURES / "empty-submission.valid.session.json").read_text())
        validate_payload("session", empty)

    def test_published_examples_follow_the_current_contract(self):
        validate_payload(
            "session",
            json.loads((ROOT / "contracts" / "session.example.json").read_text()),
        )
        validate_payload(
            "review",
            json.loads((ROOT / "contracts" / "review.example.json").read_text()),
        )

    def test_invalid_fixtures_are_rejected_for_the_declared_reason(self):
        fixtures = json.loads((FIXTURES / "invalid.json").read_text())
        for fixture in fixtures:
            with self.subTest(name=fixture["name"]):
                with self.assertRaisesRegex(ContractValidationError, fixture["error"]):
                    validate_payload(fixture["contract"], fixture["payload"])


if __name__ == "__main__":
    unittest.main()
