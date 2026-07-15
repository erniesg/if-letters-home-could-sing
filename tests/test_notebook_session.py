import tempfile
import unittest
from pathlib import Path


class NotebookSessionStoreTests(unittest.TestCase):
    def store(self, path):
        from mac_bridge.notebook_session import NotebookSessionStore

        return NotebookSessionStore(path, minimum_letter=1)

    def ready_store(self, path):
        store = self.store(path)
        session_id = store.begin("private context", now=100, ttl_seconds=600)
        store.bind(
            session_id,
            document_id="doc-1",
            incoming_page_id="p1",
            reply_page_id="p2",
        )
        store.append_incoming(session_id, "家中安好，勿念。")
        store.finish_incoming(session_id)
        return store, session_id

    def test_one_session_binds_one_native_notebook_and_survives_restart(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "notebook-sessions.json"
            first = self.store(path)
            session_id = first.begin("private context")
            first.bind(
                session_id,
                document_id="doc-1",
                incoming_page_id="p1",
                reply_page_id="p2",
            )
            first.append_incoming(session_id, "家中安好，勿念。")

            recovered = self.store(path)
            public = recovered.public_state(session_id)

            self.assertEqual(public["document_id"], "doc-1")
            self.assertEqual(
                public["page_ids"],
                {"incoming": "p1", "reply": "p2"},
            )
            self.assertNotIn("private context", path.read_text(encoding="utf-8"))
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(
                "".join(item["glyph"] for item in public["incoming"]["glyphs"]),
                "家中安好，勿念。",
            )

    def test_review_and_response_phase_transitions_are_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "notebook-sessions.json"
            store, session_id = self.ready_store(path)

            first = store.begin_review(
                session_id,
                marked_page_id="p3",
                response_page_id="p4",
                observed_at=200,
            )
            duplicate = store.begin_review(
                session_id,
                marked_page_id="p3",
                response_page_id="p4",
                observed_at=201,
            )

            self.assertEqual(first["phase"], "reviewing")
            self.assertEqual(duplicate["phase"], "reviewing")
            self.assertEqual(duplicate["version"], first["version"])
            self.assertEqual(
                duplicate["page_ids"],
                {
                    "incoming": "p1",
                    "reply": "p2",
                    "marked": "p3",
                    "response": "p4",
                },
            )

            store.finish_review(
                session_id,
                {
                    "summary": "一处字形可再确认。",
                    "corrections": [],
                    "annotations": [],
                    "reflective_question": "还想告诉家里什么？",
                },
            )
            store.append_response(session_id, "见字如面。")
            completed = store.finish_response(session_id)

            self.assertEqual(completed["phase"], "complete")
            self.assertEqual(completed["response"]["text"], "见字如面。")

    def test_first_ink_and_submit_close_one_capture_window_atomically(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            store, session_id = self.ready_store(
                Path(temporary_directory) / "notebook-sessions.json"
            )

            first = store.mark_first_ink(session_id, observed_at=150)
            duplicate = store.mark_first_ink(session_id, observed_at=175)
            submitted = store.begin_review(
                session_id,
                marked_page_id="p3",
                response_page_id="p4",
                observed_at=200,
            )

            self.assertEqual(first["first_ink_at"], 150)
            self.assertEqual(duplicate["first_ink_at"], 150)
            self.assertEqual(duplicate["version"], first["version"])
            self.assertEqual(submitted["submitted_at"], 200)
            self.assertEqual(submitted["capture_window"], "closed")

    def test_first_ink_is_accepted_on_bound_page_two_while_letter_streams(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = self.store(
                Path(temporary_directory) / "notebook-sessions.json"
            )
            session_id = store.begin("private")
            store.bind(
                session_id,
                document_id="doc-1",
                incoming_page_id="p1",
                reply_page_id="p2",
            )

            observed = store.mark_first_ink(session_id, observed_at=150)

            self.assertEqual(observed["phase"], "incoming")
            self.assertEqual(observed["first_ink_at"], 150)
            self.assertEqual(observed["capture_window"], "open")

    def test_task_ids_recover_without_persisting_private_context(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "notebook-sessions.json"
            store, session_id = self.ready_store(path)
            store.set_codex_task(
                session_id,
                thread_id="thread-1",
                active_turn_id="turn-1",
            )

            recovered = self.store(path).public_state(session_id)

            self.assertEqual(recovered["thread_id"], "thread-1")
            self.assertEqual(recovered["active_turn_id"], "turn-1")
            self.assertNotIn("private context", path.read_text(encoding="utf-8"))

    def test_expiry_removes_state_and_private_render_directory(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "notebook-sessions.json"
            store = self.store(path)
            session_id = store.begin("private", now=10, ttl_seconds=5)
            render_directory = store.render_directory(session_id)
            render_directory.mkdir(parents=True)
            (render_directory / "reply.png").write_bytes(b"fixture")

            expired = store.expire(now=16)

            self.assertEqual(expired, (session_id,))
            self.assertFalse(render_directory.exists())
            with self.assertRaisesRegex(KeyError, "unknown notebook session"):
                store.public_state(session_id)


if __name__ == "__main__":
    unittest.main()
