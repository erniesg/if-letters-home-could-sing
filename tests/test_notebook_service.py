import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from mac_bridge.codex_app_server import CodexResponseTurnError
from mac_bridge.contracts import Letter


LETTER = "家" * 150 + "。"


class FakeTabletDocuments:
    def __init__(self, *, transient_export=False):
        self.export_calls = []
        self.upload_calls = []
        self.transient_export = transient_export

    def export_pdf(self, document_id):
        self.export_calls.append(document_id)
        if self.transient_export and len(self.export_calls) == 1:
            raise RuntimeError("remarkable_usb_unreachable")
        return b"%PDF-1.4 native notebook export"

    def upload_pdf(self, payload, *, filename):
        self.upload_calls.append((payload, filename))
        return "unexpected-upload"


class FakeRenderer:
    def __init__(self, reply_path):
        self.reply_path = reply_path
        self.render_calls = []

    def render_reply_page(self, source_pdf, *, page_index, session_id):
        self.render_calls.append((source_pdf, page_index, session_id))
        return self.reply_path


class FakeLetterGenerator:
    def __init__(self):
        self.calls = []

    def generate_letter(self, *, session_id, conversation_context, on_delta):
        self.calls.append((session_id, conversation_context))
        on_delta(LETTER[:30])
        return SimpleNamespace(thread_id="incoming-thread-1", letter=Letter(LETTER))


class FakeReviewer:
    def __init__(self, *, fail_response=False):
        self.calls = []
        self.retry_calls = []
        self.fail_response = fail_response
        self.probe = None

    def review_reply(self, *, session_id, reply_image, conversation_context):
        self.calls.append((session_id, reply_image, conversation_context))
        review = SimpleNamespace(
            summary="字意清楚。",
            annotations=(),
            reflective_question="还想告诉家里什么？",
            response_letter=LETTER,
        )
        return SimpleNamespace(thread_id="review-thread-1", review=review)

    @staticmethod
    def notebook_review():
        return SimpleNamespace(
            schema_version=1,
            summary="字意清楚。",
            corrections=(),
            annotations=(),
            reflective_question="还想告诉家里什么？",
        )

    def review_and_respond(
        self,
        *,
        session_id,
        reply_image,
        conversation_context,
        on_review,
        on_response_delta,
        on_turn_started,
    ):
        self.calls.append((session_id, reply_image, conversation_context))
        on_turn_started("review", "review-thread-1", "review-turn-1")
        on_review("review-thread-1", self.notebook_review())
        if self.probe is not None:
            self.probe()
        on_turn_started("response", "review-thread-1", "response-turn-1")
        if self.fail_response:
            raise CodexResponseTurnError("fixture response failure")
        on_response_delta(LETTER[:30])
        return SimpleNamespace(
            thread_id="review-thread-1",
            review=self.notebook_review(),
            response_letter=Letter(LETTER),
        )

    def respond_in_thread(
        self,
        *,
        thread_id,
        on_response_delta,
        on_turn_started,
    ):
        self.retry_calls.append(thread_id)
        on_turn_started("response", thread_id, "response-turn-retry")
        on_response_delta(LETTER[:25])
        return Letter(LETTER)


class NotebookCoordinatorTests(unittest.TestCase):
    def coordinator_fixture(self, temporary_directory, *, tablet=None):
        from mac_bridge.notebook_service import NotebookCoordinator
        from mac_bridge.notebook_session import NotebookSessionStore

        temporary = Path(temporary_directory)
        reply = temporary / "reply.png"
        reply.write_bytes(b"fixture reply image")
        pending = []
        tablet = tablet or FakeTabletDocuments()
        coordinator = NotebookCoordinator(
            store=NotebookSessionStore(temporary / "sessions.json"),
            tablet=tablet,
            renderer=FakeRenderer(reply),
            generator=FakeLetterGenerator(),
            reviewer=FakeReviewer(),
            default_context="default context",
            background=pending.append,
            health_checks={
                "tablet_readable": lambda: True,
                "renderer": lambda: True,
                "codex": lambda: True,
            },
        )
        return coordinator, tablet, pending

    def ready_bound_session(self, coordinator, pending):
        session_id = coordinator.start(
            {
                "profile_id": "ferrari_3.28.0.162",
                "conversation_context": "care across distance",
            }
        )["session_id"]
        pending.pop(0)()
        coordinator.bind(
            {
                "session_id": session_id,
                "document_id": "doc-1",
                "incoming_page_id": "p1",
                "reply_page_id": "p2",
            }
        )
        return session_id

    def test_start_returns_session_without_uploading_a_pdf(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            coordinator, tablet, pending = self.coordinator_fixture(temporary_directory)

            response = coordinator.start(
                {"profile_id": "ferrari_3.28.0.162"}
            )

            self.assertEqual(response["status"], "incoming")
            self.assertTrue(response["session_id"])
            self.assertEqual(tablet.upload_calls, [])
            self.assertEqual(len(pending), 1)
            pending.pop(0)()
            state = coordinator.state(response["session_id"])
            self.assertEqual(state["incoming"]["text"], LETTER)
            self.assertEqual(state["thread_id"], "incoming-thread-1")

    def test_bind_records_the_stock_created_notebook_pages(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            coordinator, _, pending = self.coordinator_fixture(temporary_directory)
            session_id = coordinator.start(
                {"profile_id": "ferrari_3.28.0.162"}
            )["session_id"]

            result = coordinator.bind(
                {
                    "session_id": session_id,
                    "document_id": "doc-1",
                    "incoming_page_id": "p1",
                    "reply_page_id": "p2",
                }
            )

            self.assertEqual(result["status"], "bound")
            self.assertEqual(result["document_id"], "doc-1")
            self.assertEqual(result["page_ids"], {"incoming": "p1", "reply": "p2"})
            self.assertEqual(len(pending), 1)

    def test_submit_returns_reviewing_before_codex_finishes_and_never_uploads(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            coordinator, tablet, pending = self.coordinator_fixture(temporary_directory)
            session_id = self.ready_bound_session(coordinator, pending)

            result = coordinator.submit(
                {
                    "session_id": session_id,
                    "document_id": "doc-1",
                    "reply_page_id": "p2",
                    "reply_page_index": 1,
                    "marked_page_id": "p3",
                    "response_page_id": "p4",
                    "profile_id": "ferrari_3.28.0.162",
                    "conversation_context": "",
                }
            )

            self.assertEqual(result["status"], "reviewing")
            self.assertEqual(len(pending), 1)
            self.assertEqual(tablet.export_calls, ["doc-1"])
            self.assertEqual(tablet.upload_calls, [])

    def test_submit_retries_one_transient_export_before_codex(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            tablet = FakeTabletDocuments(transient_export=True)
            coordinator, _, pending = self.coordinator_fixture(
                temporary_directory,
                tablet=tablet,
            )
            session_id = self.ready_bound_session(coordinator, pending)

            with patch("mac_bridge.notebook_service.time.sleep") as sleep:
                result = coordinator.submit(
                    {
                        "session_id": session_id,
                        "document_id": "doc-1",
                        "reply_page_id": "p2",
                        "reply_page_index": 1,
                        "marked_page_id": "p3",
                        "response_page_id": "p4",
                        "profile_id": "ferrari_3.28.0.162",
                        "conversation_context": "",
                    }
                )

            self.assertEqual(result["status"], "reviewing")
            self.assertEqual(tablet.export_calls, ["doc-1", "doc-1"])
            sleep.assert_called_once_with(1)
            self.assertEqual(len(pending), 1)

    def test_duplicate_submit_does_not_export_or_enqueue_twice(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            coordinator, tablet, pending = self.coordinator_fixture(temporary_directory)
            session_id = self.ready_bound_session(coordinator, pending)
            payload = {
                "session_id": session_id,
                "document_id": "doc-1",
                "reply_page_id": "p2",
                "reply_page_index": 1,
                "marked_page_id": "p3",
                "response_page_id": "p4",
                "profile_id": "ferrari_3.28.0.162",
                "conversation_context": "",
            }

            first = coordinator.submit(payload)
            duplicate = coordinator.submit(payload)

            self.assertEqual(duplicate, first)
            self.assertEqual(tablet.export_calls, ["doc-1"])
            self.assertEqual(len(pending), 1)

    def test_first_ink_requires_the_bound_document_and_reply_page(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            coordinator, _, pending = self.coordinator_fixture(temporary_directory)
            session_id = self.ready_bound_session(coordinator, pending)

            result = coordinator.mark_first_ink(
                {
                    "session_id": session_id,
                    "document_id": "doc-1",
                    "reply_page_id": "p2",
                    "observed_at": 123,
                }
            )

            self.assertEqual(result["first_ink_at"], 123)
            with self.assertRaisesRegex(ValueError, "notebook_binding_mismatch"):
                coordinator.mark_first_ink(
                    {
                        "session_id": session_id,
                        "document_id": "doc-other",
                        "reply_page_id": "p2",
                    }
                )

    def test_health_reports_both_listener_and_outbound_dependencies(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            coordinator, _, _ = self.coordinator_fixture(temporary_directory)

            self.assertEqual(
                coordinator.health(),
                {
                    "status": "ok",
                    "listener": True,
                    "tablet_readable": True,
                    "renderer": True,
                    "codex": True,
                },
            )

    def test_bridge_application_routes_native_notebook_api_and_health(self):
        from mac_bridge.server import BridgeApplication

        class Coordinator:
            def start(self, payload):
                return {"status": "incoming", "session_id": payload["fixture"]}

            def bind(self, payload):
                return {"status": "bound", "session_id": payload["fixture"]}

            def mark_first_ink(self, payload):
                return {"first_ink_at": payload["observed_at"]}

            def submit(self, payload):
                return {"status": "reviewing", "session_id": payload["fixture"]}

            def state(self, session_id):
                return {"phase": "incoming", "session_id": session_id}

            def health(self):
                return {
                    "status": "unavailable",
                    "listener": True,
                    "tablet_readable": False,
                    "renderer": True,
                    "codex": True,
                }

        application = BridgeApplication(coordinator=Coordinator())

        self.assertEqual(
            application.dispatch("/v1/sessions/start", {"fixture": "s1"}),
            (200, {"status": "incoming", "session_id": "s1"}),
        )
        self.assertEqual(
            application.dispatch("/v1/sessions/bind", {"fixture": "s1"})[1]["status"],
            "bound",
        )
        self.assertEqual(
            application.dispatch(
                "/v1/sessions/ink-start",
                {"observed_at": 123},
            )[1]["first_ink_at"],
            123,
        )
        self.assertEqual(
            application.dispatch("/v1/sessions/submit", {"fixture": "s1"})[1]["status"],
            "reviewing",
        )
        self.assertEqual(
            application.dispatch_get("/v1/sessions/s1"),
            (200, {"phase": "incoming", "session_id": "s1"}),
        )
        health_status, health = application.dispatch_get("/health")
        self.assertEqual(health_status, 503)
        self.assertFalse(health["tablet_readable"])

    def test_review_is_durable_before_response_and_final_response_replaces_partial_delta(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            coordinator, _, pending = self.coordinator_fixture(temporary_directory)
            session_id = self.ready_bound_session(coordinator, pending)
            phases = []
            coordinator.reviewer.probe = lambda: phases.append(
                coordinator.state(session_id)["phase"]
            )
            coordinator.submit(
                {
                    "session_id": session_id,
                    "document_id": "doc-1",
                    "reply_page_id": "p2",
                    "reply_page_index": 1,
                    "marked_page_id": "p3",
                    "response_page_id": "p4",
                    "profile_id": "ferrari_3.28.0.162",
                    "conversation_context": "",
                }
            )

            pending.pop(0)()
            state = coordinator.state(session_id)

            self.assertEqual(phases, ["review-ready"])
            self.assertEqual(state["phase"], "complete")
            self.assertEqual(state["thread_id"], "review-thread-1")
            self.assertEqual(state["response"]["text"], LETTER)
            self.assertNotIn("response_letter", state["review"])

    def test_response_failure_retains_review_and_retries_without_repeating_review(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            coordinator, _, pending = self.coordinator_fixture(temporary_directory)
            coordinator.reviewer = FakeReviewer(fail_response=True)
            session_id = self.ready_bound_session(coordinator, pending)
            coordinator.submit(
                {
                    "session_id": session_id,
                    "document_id": "doc-1",
                    "reply_page_id": "p2",
                    "reply_page_index": 1,
                    "marked_page_id": "p3",
                    "response_page_id": "p4",
                    "profile_id": "ferrari_3.28.0.162",
                    "conversation_context": "",
                }
            )
            pending.pop(0)()

            failed = coordinator.state(session_id)
            self.assertEqual(failed["phase"], "review-ready")
            self.assertEqual(failed["error"], "response_failed")
            self.assertEqual(len(coordinator.reviewer.calls), 1)

            retry = coordinator.retry_response(session_id)
            self.assertEqual(retry["status"], "response-retrying")
            pending.pop(0)()
            completed = coordinator.state(session_id)

            self.assertEqual(completed["phase"], "complete")
            self.assertEqual(coordinator.reviewer.retry_calls, ["review-thread-1"])
            self.assertEqual(len(coordinator.reviewer.calls), 1)


if __name__ == "__main__":
    unittest.main()
