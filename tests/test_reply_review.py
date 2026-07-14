import json
import unittest
from pathlib import Path

from experience_core import (
    ContractValidationError,
    FixtureReplyReviewer,
    Point,
    ReviewProviderError,
    Stroke,
    accept_stroke,
    make_review_request,
    new_session,
    review_reply,
    submit,
    swipe,
    validate_payload,
)
from tablet_app import (
    MESSAGE_RETRY,
    MESSAGE_CONSENT,
    MESSAGE_STROKE,
    MESSAGE_SUBMIT,
    MESSAGE_SWIPE,
    FixtureBackend,
    MockPenSource,
)


ROOT = Path(__file__).resolve().parents[1]


def submitted_session(*, with_ink=True):
    session = swipe(
        new_session(
            session_id="fixture-session-0001",
            created_at="2026-07-14T00:00:00Z",
        ),
        "forward",
    )
    if with_ink:
        session = accept_stroke(
            session,
            Stroke(
                stroke_id="stroke-1",
                accepted_at="2026-07-14T00:00:12Z",
                points=(
                    Point(x=0.2, y=0.3, pressure=0.5),
                    Point(x=0.3, y=0.4, pressure=0.6),
                ),
            ),
        )
    return submit(
        session,
        review_id="fixture-review-0001",
        submitted_at="2026-07-14T00:01:02Z",
        confirm_empty=not with_ink,
    ).session


def captured_payload():
    stroke = MockPenSource.default().next_stroke()
    return {
        "accepted_at": stroke.accepted_at,
        "points": [
            {
                "elapsed_ms": point.elapsed_ms,
                "pressure": point.pressure,
                "x": point.x,
                "y": point.y,
            }
            for point in stroke.points
        ],
        "stroke_id": stroke.stroke_id,
    }


class ReplyReviewerTests(unittest.TestCase):
    def test_fixture_reviewer_covers_each_gentle_annotation_kind(self):
        document = review_reply(
            FixtureReplyReviewer("standard"),
            make_review_request(submitted_session()),
        )

        self.assertEqual(document["status"], "reviewed")
        self.assertEqual(
            {annotation["kind"] for annotation in document["annotations"]},
            {"correction", "uncertain-reading", "affirmation", "reflection"},
        )
        validate_payload("review", document)
        self.assertNotIn("transcription", document)

    def test_request_has_detached_vectors_and_a_deterministic_rendered_page(self):
        session = submitted_session()
        first = make_review_request(session)
        second = make_review_request(session)

        self.assertIsNot(first.strokes[0], session.strokes[0])
        self.assertEqual(first.strokes, session.strokes)
        self.assertEqual(first.rendered_page.content, second.rendered_page.content)
        self.assertEqual(first.rendered_page.sha256, second.rendered_page.sha256)
        self.assertEqual(first.rendered_page.media_type, "image/svg+xml")

    def test_provider_mutation_is_rejected_without_changing_durable_ink(self):
        session = submitted_session()
        original_ink = session.strokes
        request = make_review_request(session)

        class MutatingReviewer:
            def review(self, mutable_request):
                object.__setattr__(
                    mutable_request.strokes[0],
                    "accepted_at",
                    "2027-01-01T00:00:00Z",
                )
                return FixtureReplyReviewer("standard").review(mutable_request)

        with self.assertRaisesRegex(ReviewProviderError, "reviewer_mutated_input"):
            review_reply(MutatingReviewer(), request)
        self.assertIs(session.strokes, original_ink)
        self.assertEqual(session.strokes[0].accepted_at, "2026-07-14T00:00:12Z")

    def test_edge_fixtures_are_useful_and_non_judgmental(self):
        expected = {
            "empty": "empty",
            "non-chinese": "non-chinese",
            "mixed-language": "mixed-language",
            "illegible": "illegible",
        }
        prohibited = ("score", "grade", "correct answer", "full transcription")
        for case, status in expected.items():
            with self.subTest(case=case):
                request = make_review_request(
                    submitted_session(with_ink=case != "empty")
                )
                document = review_reply(FixtureReplyReviewer(case), request)
                self.assertEqual(document["status"], status)
                self.assertTrue(document["summary"].strip())
                visible_text = " ".join(
                    [document["summary"]]
                    + [item["message"] for item in document["annotations"]]
                ).lower()
                self.assertFalse(any(term in visible_text for term in prohibited))
        self.assertEqual(
            review_reply(
                FixtureReplyReviewer("illegible"),
                make_review_request(submitted_session()),
            )["annotations"],
            [],
        )

    def test_provider_error_exposes_only_a_safe_local_code(self):
        with self.assertRaisesRegex(ReviewProviderError, "^reviewer_unavailable$"):
            review_reply(
                FixtureReplyReviewer("provider-error"),
                make_review_request(submitted_session()),
            )


class ReviewPolicyTests(unittest.TestCase):
    def setUp(self):
        self.document = review_reply(
            FixtureReplyReviewer("standard"),
            make_review_request(submitted_session()),
        )

    def test_schema_bounds_annotation_count_and_message_length(self):
        too_many = json.loads(json.dumps(self.document))
        template = too_many["annotations"][0]
        too_many["annotations"] = [
            {**template, "id": f"annotation-{index}"}
            for index in range(7)
        ]
        with self.assertRaisesRegex(ContractValidationError, "too many items"):
            validate_payload("review", too_many)

        too_long = json.loads(json.dumps(self.document))
        too_long["annotations"][0]["message"] = "x" * 181
        with self.assertRaisesRegex(ContractValidationError, "too long"):
            validate_payload("review", too_long)

    def test_low_confidence_must_be_uncertain_and_never_a_correction(self):
        correction = json.loads(json.dumps(self.document))
        correction["annotations"][0]["confidence"] = 0.4
        with self.assertRaisesRegex(ContractValidationError, "cannot be a correction"):
            validate_payload("review", correction)

        assertion = json.loads(json.dumps(self.document))
        assertion["annotations"][1]["message"] = "Use this character here."
        with self.assertRaisesRegex(ContractValidationError, "question or uncertainty"):
            validate_payload("review", assertion)

    def test_schema_rejects_evaluative_or_transcription_shaped_output(self):
        evaluative = json.loads(json.dumps(self.document))
        evaluative["summary"] = "Your score is high."
        with self.assertRaisesRegex(ContractValidationError, "prohibited evaluative"):
            validate_payload("review", evaluative)

        transcription = json.loads(json.dumps(self.document))
        transcription["transcription"] = "fabricated text"
        with self.assertRaisesRegex(ContractValidationError, "not allowed"):
            validate_payload("review", transcription)

    def test_checked_in_policy_preserves_uncertainty_and_writer_ink(self):
        policy = (ROOT / "docs" / "fixtures" / "reply-review.prompt.md").read_text()
        self.assertIn("immutable stroke vectors", policy)
        self.assertIn("Phrase confidence below `0.7`", policy)
        self.assertIn("Never produce a score, grade, single correct answer", policy)
        self.assertIn("omit it and return a margin-only summary", policy)


class ReviewAdapterTests(unittest.TestCase):
    def test_backend_renders_structured_review_and_ignores_duplicate_submit(self):
        backend = FixtureBackend()
        backend.dispatch(MESSAGE_CONSENT, {"decision": "declined"})
        backend.dispatch(MESSAGE_SWIPE, {"direction": "forward"})
        backend.dispatch(MESSAGE_STROKE, captured_payload())
        first = backend.dispatch(MESSAGE_SUBMIT, {"confirm_empty": False})[-1]
        ink = backend.session.strokes
        duplicate = backend.dispatch(MESSAGE_SUBMIT, {"confirm_empty": False})[-1]

        self.assertEqual(first.payload["reviewStatus"], "reviewed")
        self.assertTrue(first.payload["reviewSummary"])
        self.assertEqual(first.payload["reviewId"], "fixture-review-0001")
        self.assertEqual(duplicate.payload["event"], "duplicate_submit_ignored")
        self.assertEqual(duplicate.payload["reviewId"], first.payload["reviewId"])
        self.assertIs(backend.session.strokes, ink)

    def test_retry_reuses_review_id_and_provider_error_keeps_ink(self):
        backend = FixtureBackend(
            ("success", "success"),
            reviewer=FixtureReplyReviewer("provider-error"),
        )
        backend.dispatch(MESSAGE_CONSENT, {"decision": "declined"})
        backend.dispatch(MESSAGE_SWIPE, {"direction": "forward"})
        backend.dispatch(MESSAGE_STROKE, captured_payload())
        first = backend.dispatch(MESSAGE_SUBMIT, {"confirm_empty": False})[-1]
        ink = backend.session.strokes
        retried = backend.dispatch(MESSAGE_RETRY)[-1]

        self.assertEqual(first.payload["state"], "review_error")
        self.assertEqual(first.payload["errorCode"], "reviewer_unavailable")
        self.assertEqual(retried.payload["reviewId"], first.payload["reviewId"])
        self.assertIs(backend.session.strokes, ink)

    def test_qml_summary_is_part_of_the_reversible_overlay(self):
        main = (ROOT / "tablet_app" / "appload" / "ui" / "Main.qml").read_text()
        overlay = (
            ROOT / "tablet_app" / "appload" / "ui" / "MarginaliaLayer.qml"
        ).read_text()
        self.assertIn("marginaliaLayer.summary = reviewSummary", main)
        self.assertIn("marginaliaVisible = !marginaliaVisible", main)
        self.assertIn('property string summary: ""', overlay)


if __name__ == "__main__":
    unittest.main()
