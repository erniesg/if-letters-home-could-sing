import json
import tempfile
import unittest
from pathlib import Path

from mac_bridge.codex_app_server import CodexAppServerClient, default_codex_command
from mac_bridge.contracts import ReviewContractError, parse_review
from mac_bridge.review_layout import layout_review
from mac_bridge.server import DEFAULT_USB_BIND, BridgeApplication
from mac_bridge.service import ReceiptStore, SessionRegistry, SessionStarter, SubmissionService


ROOT = Path(__file__).resolve().parents[1]


VALID_REVIEW = {
    "schema_version": 1,
    "summary": "你的回批很真诚；以下是几处可以更自然的表达。",
    "annotations": [
        {
            "kind": "correction",
            "observed_text": "我有收到你信",
            "suggested_text": "我已收到你的信",
            "explanation": "“已收到”更自然，也补足了领属关系。",
            "confidence": 0.94,
            "anchor": {"x": 0.28, "y": 0.31},
        },
        {
            "kind": "uncertain-reading",
            "observed_text": "返／反",
            "suggested_text": "返",
            "explanation": "这里的字形不太确定；若你想表达回乡，可以写“返乡”。",
            "confidence": 0.55,
            "anchor": {"x": 0.63, "y": 0.58},
        },
    ],
    "reflective_question": "如果再写一行，你最想告诉家里什么？",
}


class ScriptedRpcChannel:
    def __init__(self, review=None):
        self.review = review or VALID_REVIEW
        self.requests = []
        self.notifications = []

    def request(self, method, params):
        self.requests.append((method, params))
        if method == "initialize":
            return {"serverInfo": {"name": "codex", "version": "test"}}
        if method == "model/list":
            return {
                "data": [
                    {
                        "id": "fixture-text-only",
                        "model": "fixture-text-only",
                        "isDefault": False,
                        "inputModalities": ["text"],
                    },
                    {
                        "id": "fixture-vision",
                        "model": "fixture-vision",
                        "isDefault": True,
                        "inputModalities": ["text", "image"],
                    },
                ]
            }
        if method == "thread/start":
            return {"thread": {"id": "thread-letters-home-001"}}
        if method == "thread/name/set":
            return {}
        if method == "turn/start":
            return {"turn": {"id": "turn-review-001", "status": "inProgress"}}
        raise AssertionError(f"unexpected request: {method}")

    def notify(self, method, params):
        self.notifications.append((method, params))

    def events(self):
        yield {
            "method": "item/completed",
            "params": {
                "threadId": "thread-letters-home-001",
                "turnId": "turn-review-001",
                "item": {
                    "id": "message-001",
                    "type": "agentMessage",
                    "phase": "final_answer",
                    "text": json.dumps(self.review, ensure_ascii=False),
                },
            },
        }
        yield {
            "method": "turn/completed",
            "params": {
                "threadId": "thread-letters-home-001",
                "turn": {"id": "turn-review-001", "status": "completed", "items": []},
            },
        }


class CodexAppServerContractTests(unittest.TestCase):
    def test_submission_creates_a_persisted_named_codex_thread_with_reply_image(self):
        channel = ScriptedRpcChannel()
        client = CodexAppServerClient(
            channel=channel,
            cwd=ROOT,
            reviewer_prompt="Act as a kind Chinese teacher and return only the schema.",
        )

        result = client.review_reply(
            session_id="session-fixture-001",
            reply_image=ROOT / "fixtures" / "reply" / "reply-ferrari.svg",
            conversation_context="A fictional exchange about distance, health, and returning home.",
        )

        self.assertEqual(result.thread_id, "thread-letters-home-001")
        self.assertEqual(result.review.summary, VALID_REVIEW["summary"])
        methods = [method for method, _ in channel.requests]
        self.assertEqual(
            methods,
            ["initialize", "model/list", "thread/start", "thread/name/set", "turn/start"],
        )
        self.assertEqual(channel.notifications, [("initialized", {})])

        thread_start = channel.requests[2][1]
        self.assertFalse(thread_start["ephemeral"])
        self.assertEqual(thread_start["sandbox"], "read-only")
        self.assertEqual(thread_start["approvalPolicy"], "never")
        self.assertEqual(thread_start["cwd"], str(ROOT))
        self.assertEqual(thread_start["model"], "fixture-vision")

        name_request = channel.requests[3][1]
        self.assertEqual(name_request["threadId"], "thread-letters-home-001")
        self.assertIn("Letters Home review", name_request["name"])
        self.assertIn("session-fixture-001", name_request["name"])

        turn = channel.requests[4][1]
        self.assertEqual(turn["threadId"], "thread-letters-home-001")
        self.assertEqual(turn["input"][1]["type"], "localImage")
        self.assertEqual(turn["input"][1]["detail"], "original")
        self.assertEqual(turn["input"][1]["path"], str(ROOT / "fixtures" / "reply" / "reply-ferrari.svg"))
        self.assertEqual(turn["outputSchema"]["title"], "LettersHomeReview")
        self.assertIn("conversation", turn["input"][0]["text"].lower())

    def test_failed_turn_does_not_return_a_false_review(self):
        class FailedChannel(ScriptedRpcChannel):
            def events(self):
                yield {
                    "method": "turn/completed",
                    "params": {
                        "threadId": "thread-letters-home-001",
                        "turn": {
                            "id": "turn-review-001",
                            "status": "failed",
                            "error": {"message": "fixture failure"},
                            "items": [],
                        },
                    },
                }

        with self.assertRaisesRegex(RuntimeError, "fixture failure"):
            CodexAppServerClient(channel=FailedChannel(), cwd=ROOT).review_reply(
                session_id="session-fixture-001",
                reply_image=ROOT / "fixtures" / "reply" / "reply-ferrari.svg",
                conversation_context="fixture",
            )

    def test_incoming_letter_generation_is_conversation_conditioned_and_persisted(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            generated = Path(temporary_directory) / "incoming.png"
            generated.write_bytes(b"fixture png")
            skill = Path(temporary_directory) / "SKILL.md"
            skill.write_text("fixture image generation skill")

            class ImageChannel(ScriptedRpcChannel):
                def events(self):
                    yield {
                        "method": "item/completed",
                        "params": {
                            "threadId": "thread-letters-home-001",
                            "turnId": "turn-review-001",
                            "item": {
                                "id": "image-001",
                                "type": "imageGeneration",
                                "status": "completed",
                                "result": "generated",
                                "savedPath": str(generated),
                            },
                        },
                    }
                    yield {
                        "method": "turn/completed",
                        "params": {
                            "threadId": "thread-letters-home-001",
                            "turn": {"id": "turn-review-001", "status": "completed", "items": []},
                        },
                    }

            channel = ImageChannel()
            result = CodexAppServerClient(channel=channel, cwd=ROOT).generate_letter(
                session_id="session-fixture-001",
                conversation_context="A sibling writes about recovery, school fees, and coming home.",
                imagegen_skill=skill,
            )

        self.assertEqual(result.thread_id, "thread-letters-home-001")
        self.assertEqual(result.image_path, generated.resolve())
        name_request = channel.requests[3][1]
        self.assertIn("Letters Home incoming", name_request["name"])
        turn = channel.requests[4][1]
        self.assertEqual(
            turn["input"][1],
            {"type": "skill", "name": "imagegen", "path": str(skill.resolve())},
        )
        prompt = turn["input"][0]["text"]
        self.assertIn("recovery, school fees, and coming home", prompt)
        self.assertIn("gpt-image-2", prompt)
        self.assertIn("1696 × 960", prompt)
        self.assertIn("fictional", prompt.lower())

    def test_default_transport_prefers_the_desktop_bundled_codex(self):
        bundled = Path("/Applications/ChatGPT.app/Contents/Resources/codex")
        command = default_codex_command()
        if bundled.is_file():
            self.assertEqual(command[0], str(bundled))
        self.assertEqual(command[1:], ("app-server", "--stdio"))


class ReviewContractTests(unittest.TestCase):
    def test_teacher_review_is_bounded_uncertainty_aware_and_non_scoring(self):
        review = parse_review(VALID_REVIEW)
        self.assertEqual(review.schema_version, 1)
        self.assertEqual(len(review.annotations), 2)
        self.assertLess(review.annotations[1].confidence, 0.7)
        self.assertEqual(review.annotations[1].kind, "uncertain-reading")

    def test_scores_grades_and_out_of_page_anchors_are_rejected(self):
        cases = []
        scored = dict(VALID_REVIEW, summary="Score: 8/10")
        cases.append(scored)
        bad_anchor = json.loads(json.dumps(VALID_REVIEW))
        bad_anchor["annotations"][0]["anchor"]["x"] = 1.2
        cases.append(bad_anchor)
        too_many = dict(VALID_REVIEW, annotations=VALID_REVIEW["annotations"] * 7)
        cases.append(too_many)
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(ReviewContractError):
                    parse_review(payload)

    def test_long_review_paginates_and_every_box_stays_inside_ferrari(self):
        long_payload = json.loads(json.dumps(VALID_REVIEW))
        long_payload["annotations"] = [
            dict(
                VALID_REVIEW["annotations"][0],
                explanation=("这是一条需要换行的温和说明。" * 16) + str(index),
                anchor={"x": 0.1 + index * 0.05, "y": 0.2 + index * 0.04},
            )
            for index in range(8)
        ]
        review = parse_review(long_payload)
        pages = layout_review(review, width=1696, height=954)

        self.assertGreater(len(pages), 1)
        annotation_boxes = [
            box for page in pages for box in page.boxes if box.kind == "annotation"
        ]
        self.assertEqual(
            [(box.anchor_x, box.anchor_y) for box in annotation_boxes],
            [(annotation.anchor.x, annotation.anchor.y) for annotation in review.annotations],
        )
        self.assertEqual(
            [box.annotation_number for box in annotation_boxes],
            list(range(1, len(review.annotations) + 1)),
        )
        for page in pages:
            self.assertEqual((page.width, page.height), (1696, 954))
            for box in page.boxes:
                self.assertGreaterEqual(box.x, 0)
                self.assertGreaterEqual(box.y, 0)
                self.assertLessEqual(box.x + box.width, page.width)
                self.assertLessEqual(box.y + box.height, page.height)
                self.assertTrue(box.lines)


class FakeTabletDocuments:
    def __init__(self):
        self.export_calls = []
        self.upload_calls = []

    def export_pdf(self, document_id):
        self.export_calls.append(document_id)
        return b"%PDF-1.4 fixture annotated reply"

    def upload_pdf(self, payload, *, filename):
        self.upload_calls.append((payload, filename))
        return "reviewed-document-001"


class FakeReplyRenderer:
    def __init__(self, reply_path):
        self.reply_path = reply_path
        self.render_calls = []
        self.packet_calls = []

    def render_reply_page(self, source_pdf, *, page_index, session_id):
        self.render_calls.append((source_pdf, page_index, session_id))
        return self.reply_path

    def build_reviewed_packet(self, source_pdf, review, *, profile_id):
        self.packet_calls.append((source_pdf, review, profile_id))
        return b"%PDF-1.4 reviewed packet", 2


class FakeCodexReviewer:
    def __init__(self):
        self.calls = []

    def review_reply(self, *, session_id, reply_image, conversation_context):
        self.calls.append((session_id, reply_image, conversation_context))
        return type(
            "CodexResult",
            (),
            {"thread_id": "thread-letters-home-001", "review": parse_review(VALID_REVIEW)},
        )()


class FakeLetterGenerator:
    def __init__(self, image_path):
        self.image_path = image_path
        self.calls = []

    def generate_letter(self, *, session_id, conversation_context):
        self.calls.append((session_id, conversation_context))
        return type(
            "CodexImageResult",
            (),
            {"thread_id": "thread-incoming-001", "image_path": self.image_path},
        )()


class FakePacketRenderer(FakeReplyRenderer):
    def __init__(self, reply_path):
        super().__init__(reply_path)
        self.initial_calls = []

    def build_initial_packet(self, image_path, *, profile_id):
        self.initial_calls.append((image_path, profile_id))
        return b"%PDF-1.4 initial packet"


class SubmissionServiceTests(unittest.TestCase):
    def test_start_creates_incoming_task_uploads_packet_and_registers_context(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            image_path = Path(temporary_directory) / "incoming.png"
            image_path.write_bytes(b"fixture image")
            tablet = FakeTabletDocuments()
            renderer = FakePacketRenderer(image_path)
            generator = FakeLetterGenerator(image_path)
            registry = SessionRegistry()
            starter = SessionStarter(
                tablet=tablet,
                renderer=renderer,
                generator=generator,
                registry=registry,
                default_context="default context",
            )

            result = starter.start(
                {
                    "profile_id": "ferrari_3.28.0.162",
                    "conversation_context": "care, recovery, and returning home",
                }
            )

        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["codex_thread_id"], "thread-incoming-001")
        self.assertEqual(result["document_id"], "reviewed-document-001")
        self.assertEqual(len(generator.calls), 1)
        session_id, context = generator.calls[0]
        self.assertEqual(result["session_id"], session_id)
        self.assertEqual(context, "care, recovery, and returning home")
        self.assertEqual(registry.get(session_id), context)
        self.assertEqual(
            renderer.initial_calls,
            [(image_path, "ferrari_3.28.0.162")],
        )
        self.assertEqual(
            tablet.upload_calls,
            [(b"%PDF-1.4 initial packet", f"Letters Home {session_id}.pdf")],
        )

    def test_submit_exports_native_ink_creates_one_thread_and_uploads_page_three(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            reply_path = Path(temporary_directory) / "reply.png"
            reply_path.write_bytes(b"fixture image")
            tablet = FakeTabletDocuments()
            renderer = FakeReplyRenderer(reply_path)
            codex = FakeCodexReviewer()
            service = SubmissionService(tablet=tablet, renderer=renderer, reviewer=codex)

            first = service.submit(
                {
                    "session_id": "session-fixture-001",
                    "document_id": "native-document-001",
                    "reply_page_index": 1,
                    "profile_id": "ferrari_3.28.0.162",
                    "conversation_context": "distance, health, and returning home",
                }
            )
            duplicate = service.submit(
                {
                    "session_id": "session-fixture-001",
                    "document_id": "native-document-001",
                    "reply_page_index": 1,
                    "profile_id": "ferrari_3.28.0.162",
                    "conversation_context": "distance, health, and returning home",
                }
            )

        self.assertEqual(first, duplicate)
        self.assertEqual(first["codex_thread_id"], "thread-letters-home-001")
        self.assertEqual(first["document_id"], "reviewed-document-001")
        self.assertEqual(first["review_page_index"], 2)
        self.assertEqual(tablet.export_calls, ["native-document-001"])
        self.assertEqual(len(codex.calls), 1)
        self.assertEqual(len(tablet.upload_calls), 1)
        self.assertNotIn("reply", json.dumps(first).lower())

    def test_persisted_receipt_makes_duplicate_submit_idempotent_after_restart(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary = Path(temporary_directory)
            reply_path = temporary / "reply.png"
            reply_path.write_bytes(b"fixture image")
            receipt_path = temporary / "receipts.json"
            payload = {
                "session_id": "session-fixture-001",
                "document_id": "native-document-001",
                "reply_page_index": 1,
                "profile_id": "ferrari_3.28.0.162",
                "conversation_context": "private conversation must not persist",
            }
            first_tablet = FakeTabletDocuments()
            first_reviewer = FakeCodexReviewer()
            first = SubmissionService(
                tablet=first_tablet,
                renderer=FakeReplyRenderer(reply_path),
                reviewer=first_reviewer,
                receipts=ReceiptStore(receipt_path),
            ).submit(payload)

            second_tablet = FakeTabletDocuments()
            second_reviewer = FakeCodexReviewer()
            duplicate = SubmissionService(
                tablet=second_tablet,
                renderer=FakeReplyRenderer(reply_path),
                reviewer=second_reviewer,
                receipts=ReceiptStore(receipt_path),
            ).submit(payload)

            persisted = receipt_path.read_text(encoding="utf-8")

        self.assertEqual(first, duplicate)
        self.assertEqual(second_tablet.export_calls, [])
        self.assertEqual(second_reviewer.calls, [])
        self.assertNotIn("private conversation", persisted)
        self.assertNotIn("reply.png", persisted)

    def test_bridge_dispatch_routes_start_and_submit_without_exposing_payload(self):
        self.assertEqual(DEFAULT_USB_BIND, "10.11.99.2")

        class Starter:
            def start(self, payload):
                return {"status": "ready", "document_id": payload["fixture"]}

        class Submissions:
            def submit(self, payload):
                return {"status": "reviewed", "document_id": payload["fixture"]}

        application = BridgeApplication(starter=Starter(), submissions=Submissions())
        start_status, start = application.dispatch(
            "/v1/sessions/start", {"fixture": "initial-001"}
        )
        submit_status, submit = application.dispatch(
            "/v1/sessions/submit", {"fixture": "reviewed-001"}
        )
        missing_status, missing = application.dispatch("/unknown", {"private": "ink"})

        self.assertEqual((start_status, start["document_id"]), (200, "initial-001"))
        self.assertEqual((submit_status, submit["document_id"]), (200, "reviewed-001"))
        self.assertEqual((missing_status, missing), (404, {"error": "not_found"}))


if __name__ == "__main__":
    unittest.main()
