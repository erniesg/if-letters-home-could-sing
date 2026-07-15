import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mac_bridge.codex_app_server import (
    CodexAppServerClient,
    CodexResponseTurnError,
    resolve_codex_executable,
)
from mac_bridge.contracts import (
    Letter,
    NOTEBOOK_REVIEW_OUTPUT_SCHEMA,
    ReviewContractError,
    parse_notebook_review,
    parse_review,
)
from mac_bridge.review_layout import layout_review
from mac_bridge.server import DEFAULT_USB_BIND, BridgeApplication
from mac_bridge.service import ReceiptStore, SessionRegistry, SessionStarter, SubmissionService


ROOT = Path(__file__).resolve().parents[1]


VALID_REVIEW = {
    "schema_version": 3,
    "summary": "你的回批很真诚；以下是几处可以更自然的表达。",
    "corrections": [
        {
            "observed_text": "未",
            "suggested_text": "末",
            "explanation": "这里要写时间的“末”，末笔比“未”更长。",
            "confidence": 0.94,
            "anchor": {"x": 0.28, "y": 0.31, "width": 0.08, "height": 0.07},
        },
    ],
    "annotations": [
        {
            "kind": "uncertain-reading",
            "observed_text": "返／反",
            "suggested_text": "返",
            "explanation": "这里的字形不太确定；若你想表达回乡，可以写“返乡”。",
            "confidence": 0.55,
            "anchor": {"x": 0.63, "y": 0.58, "width": 0.08, "height": 0.07},
        },
    ],
    "reflective_question": "如果再写一行，你最想告诉家里什么？",
    "response_letter": "见字如面。读到你的回批，我知道你平安，心里便安定许多。愿你慢慢写来，我们也慢慢回信。",
}

VALID_NOTEBOOK_REVIEW = {
    key: value
    for key, value in VALID_REVIEW.items()
    if key != "response_letter"
}
VALID_NOTEBOOK_REVIEW["schema_version"] = 1
NOTEBOOK_RESPONSE = "家" * 150 + "。"


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
    def test_review_and_response_use_two_turns_in_one_persisted_task(self):
        class TwoTurnChannel(ScriptedRpcChannel):
            def __init__(self):
                super().__init__(VALID_NOTEBOOK_REVIEW)
                self.turn_count = 0

            def request(self, method, params):
                if method == "turn/start":
                    self.requests.append((method, params))
                    self.turn_count += 1
                    turn_id = "turn-review-001" if self.turn_count == 1 else "turn-response-001"
                    return {"turn": {"id": turn_id, "status": "inProgress"}}
                return super().request(method, params)

            def events(self):
                yield {
                    "method": "item/completed",
                    "params": {
                        "threadId": "thread-letters-home-001",
                        "turnId": "turn-review-001",
                        "item": {
                            "type": "agentMessage",
                            "phase": "final_answer",
                            "text": json.dumps(VALID_NOTEBOOK_REVIEW, ensure_ascii=False),
                        },
                    },
                }
                yield {
                    "method": "turn/completed",
                    "params": {
                        "threadId": "thread-letters-home-001",
                        "turn": {"id": "turn-review-001", "status": "completed"},
                    },
                }
                for delta in (NOTEBOOK_RESPONSE[:75], NOTEBOOK_RESPONSE[75:]):
                    yield {
                        "method": "item/agentMessage/delta",
                        "params": {
                            "threadId": "thread-letters-home-001",
                            "turnId": "turn-response-001",
                            "delta": delta,
                        },
                    }
                yield {
                    "method": "item/completed",
                    "params": {
                        "threadId": "thread-letters-home-001",
                        "turnId": "turn-response-001",
                        "item": {
                            "type": "agentMessage",
                            "phase": "final_answer",
                            "text": NOTEBOOK_RESPONSE,
                        },
                    },
                }
                yield {
                    "method": "turn/completed",
                    "params": {
                        "threadId": "thread-letters-home-001",
                        "turn": {"id": "turn-response-001", "status": "completed"},
                    },
                }

        channel = TwoTurnChannel()
        reviews = []
        deltas = []
        turns = []

        result = CodexAppServerClient(channel=channel, cwd=ROOT).review_and_respond(
            session_id="session-fixture-001",
            reply_image=ROOT / "fixtures" / "reply" / "reply-ferrari.svg",
            conversation_context="care across distance",
            on_review=lambda thread_id, review: reviews.append((thread_id, review)),
            on_response_delta=deltas.append,
            on_turn_started=lambda phase, thread_id, turn_id: turns.append(
                (phase, thread_id, turn_id)
            ),
        )

        self.assertEqual(result.thread_id, "thread-letters-home-001")
        self.assertEqual(result.response_letter.body, NOTEBOOK_RESPONSE)
        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0][1].schema_version, 1)
        self.assertEqual("".join(deltas), NOTEBOOK_RESPONSE)
        self.assertEqual(
            turns,
            [
                ("review", "thread-letters-home-001", "turn-review-001"),
                ("response", "thread-letters-home-001", "turn-response-001"),
            ],
        )
        turn_requests = [params for method, params in channel.requests if method == "turn/start"]
        self.assertEqual(len(turn_requests), 2)
        self.assertEqual(
            {request["threadId"] for request in turn_requests},
            {"thread-letters-home-001"},
        )
        self.assertEqual(turn_requests[0]["outputSchema"], NOTEBOOK_REVIEW_OUTPUT_SCHEMA)
        self.assertTrue(any(item["type"] == "localImage" for item in turn_requests[0]["input"]))
        self.assertNotIn("outputSchema", turn_requests[1])
        self.assertEqual(turn_requests[1]["input"][0]["type"], "text")

    def test_response_failure_keeps_review_and_supports_response_only_retry(self):
        class FailedResponseChannel(ScriptedRpcChannel):
            def __init__(self):
                super().__init__(VALID_NOTEBOOK_REVIEW)
                self.turn_count = 0

            def request(self, method, params):
                if method == "turn/start":
                    self.requests.append((method, params))
                    self.turn_count += 1
                    return {
                        "turn": {
                            "id": "turn-review-001" if self.turn_count == 1 else "turn-response-001"
                        }
                    }
                return super().request(method, params)

            def events(self):
                yield {
                    "method": "item/completed",
                    "params": {
                        "threadId": "thread-letters-home-001",
                        "turnId": "turn-review-001",
                        "item": {
                            "type": "agentMessage",
                            "phase": "final_answer",
                            "text": json.dumps(VALID_NOTEBOOK_REVIEW, ensure_ascii=False),
                        },
                    },
                }
                yield {
                    "method": "turn/completed",
                    "params": {
                        "threadId": "thread-letters-home-001",
                        "turn": {"id": "turn-review-001", "status": "completed"},
                    },
                }
                yield {
                    "method": "turn/completed",
                    "params": {
                        "threadId": "thread-letters-home-001",
                        "turn": {
                            "id": "turn-response-001",
                            "status": "failed",
                            "error": {"message": "fixture response failure"},
                        },
                    },
                }

        reviews = []
        failed = FailedResponseChannel()
        with self.assertRaisesRegex(CodexResponseTurnError, "fixture response failure"):
            CodexAppServerClient(channel=failed, cwd=ROOT).review_and_respond(
                session_id="session-fixture-001",
                reply_image=ROOT / "fixtures" / "reply" / "reply-ferrari.svg",
                conversation_context="fixture",
                on_review=lambda thread_id, review: reviews.append((thread_id, review)),
            )
        self.assertEqual(len(reviews), 1)

        class ResponseOnlyChannel(ScriptedRpcChannel):
            def request(self, method, params):
                if method == "turn/start":
                    self.requests.append((method, params))
                    return {"turn": {"id": "turn-response-retry"}}
                return super().request(method, params)

            def events(self):
                yield {
                    "method": "item/completed",
                    "params": {
                        "threadId": "thread-letters-home-001",
                        "turnId": "turn-response-retry",
                        "item": {
                            "type": "agentMessage",
                            "phase": "final_answer",
                            "text": NOTEBOOK_RESPONSE,
                        },
                    },
                }
                yield {
                    "method": "turn/completed",
                    "params": {
                        "threadId": "thread-letters-home-001",
                        "turn": {"id": "turn-response-retry", "status": "completed"},
                    },
                }

        retry = ResponseOnlyChannel()
        letter = CodexAppServerClient(channel=retry, cwd=ROOT).respond_in_thread(
            thread_id="thread-letters-home-001"
        )
        self.assertEqual(letter.body, NOTEBOOK_RESPONSE)
        self.assertNotIn("thread/start", [method for method, _ in retry.requests])

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
        correction_rule = turn["outputSchema"]["properties"]["corrections"]["items"]
        self.assertEqual(correction_rule["properties"]["suggested_text"]["maxLength"], 1)
        self.assertEqual(correction_rule["properties"]["confidence"]["minimum"], 0.8)
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

    def test_raster_reply_adds_four_private_detail_tiles_to_the_vision_turn(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as temporary_directory:
            reply = Path(temporary_directory) / "reply.png"
            Image.new("RGB", (400, 800), "#f3ead7").save(reply)
            channel = ScriptedRpcChannel()

            CodexAppServerClient(channel=channel, cwd=ROOT).review_reply(
                session_id="session-detail-tiles",
                reply_image=reply,
                conversation_context="fixture",
            )

        turn = channel.requests[4][1]
        images = [item for item in turn["input"] if item["type"] == "localImage"]
        self.assertEqual(len(images), 5)
        self.assertEqual(images[0]["path"], str(reply.resolve()))
        self.assertTrue(all(image["detail"] == "original" for image in images))
        self.assertIn("top-left", turn["input"][0]["text"])
        self.assertIn("full-page coordinates", turn["input"][0]["text"])

    def test_incoming_letter_streams_stable_text_deltas_and_returns_final_letter(self):
        letter = "阿妹，见字如面。家中一切安好，勿念。听说你近来功课很忙，也要记得按时吃饭。待天气凉些，再慢慢写信回来。"

        class LetterChannel(ScriptedRpcChannel):
            def events(self):
                for delta in ("阿妹，见字如面。", "家中一切安好，勿念。", "听说你近来功课很忙，也要记得按时吃饭。"):
                    yield {
                        "method": "item/agentMessage/delta",
                        "params": {
                            "threadId": "thread-letters-home-001",
                            "turnId": "turn-review-001",
                            "itemId": "message-001",
                            "delta": delta,
                        },
                    }
                yield {
                    "method": "item/completed",
                    "params": {
                        "threadId": "thread-letters-home-001",
                        "turnId": "turn-review-001",
                        "item": {
                            "id": "message-001",
                            "type": "agentMessage",
                            "phase": "final_answer",
                            "text": letter,
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

        channel = LetterChannel()
        deltas = []
        result = CodexAppServerClient(channel=channel, cwd=ROOT).generate_letter(
            session_id="session-fixture-001",
            conversation_context="A sibling writes about recovery, school fees, and coming home.",
            on_delta=deltas.append,
        )

        self.assertEqual(result.thread_id, "thread-letters-home-001")
        self.assertEqual(result.letter.body, letter)
        self.assertEqual("".join(deltas), letter[: len("".join(deltas))])
        name_request = channel.requests[3][1]
        self.assertIn("Letters Home incoming", name_request["name"])
        turn = channel.requests[4][1]
        self.assertEqual(len(turn["input"]), 1)
        prompt = turn["input"][0]["text"]
        self.assertIn("recovery, school fees, and coming home", prompt)
        self.assertIn("vertical", prompt.lower())
        self.assertIn("Chinese", prompt)
        self.assertIn("fictional", prompt.lower())

    def test_transport_prefers_the_first_available_executable_without_host_assumptions(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary = Path(temporary_directory)
            missing = temporary / "missing-codex"
            bundled = temporary / "desktop-codex"
            bundled.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            bundled.chmod(0o755)

            self.assertEqual(
                resolve_codex_executable((missing, bundled)),
                bundled,
            )


class ReviewContractTests(unittest.TestCase):
    def test_notebook_review_schema_has_no_embedded_response_letter(self):
        review = parse_notebook_review(VALID_NOTEBOOK_REVIEW)

        self.assertEqual(review.schema_version, 1)
        self.assertEqual(len(review.corrections), 1)
        self.assertEqual(len(review.annotations), 1)
        self.assertNotIn("response_letter", NOTEBOOK_REVIEW_OUTPUT_SCHEMA["properties"])

    def test_notebook_review_rejects_scoring_multiglyph_and_excess_marks(self):
        invalid = []
        invalid.append(dict(VALID_NOTEBOOK_REVIEW, summary="Score: 8/10"))
        multiglyph = json.loads(json.dumps(VALID_NOTEBOOK_REVIEW))
        multiglyph["corrections"][0]["suggested_text"] = "末尾"
        invalid.append(multiglyph)
        outside = json.loads(json.dumps(VALID_NOTEBOOK_REVIEW))
        outside["corrections"][0]["anchor"]["x"] = 1.2
        invalid.append(outside)
        excessive = json.loads(json.dumps(VALID_NOTEBOOK_REVIEW))
        excessive["annotations"] = excessive["annotations"] * 10
        invalid.append(excessive)

        for payload in invalid:
            with self.subTest(payload=payload):
                with self.assertRaises(ReviewContractError):
                    parse_notebook_review(payload)

    def test_teacher_review_is_bounded_uncertainty_aware_and_non_scoring(self):
        review = parse_review(VALID_REVIEW)
        self.assertEqual(review.schema_version, 3)
        self.assertEqual(len(review.annotations), 2)
        self.assertEqual(review.response_letter, VALID_REVIEW["response_letter"])
        self.assertGreater(review.annotations[0].anchor.width, 0)
        self.assertLess(review.annotations[1].confidence, 0.7)
        self.assertEqual(review.annotations[1].kind, "uncertain-reading")

    def test_scores_grades_and_out_of_page_anchors_are_rejected(self):
        cases = []
        scored = dict(VALID_REVIEW, summary="Score: 8/10")
        cases.append(scored)
        bad_anchor = json.loads(json.dumps(VALID_REVIEW))
        bad_anchor["corrections"][0]["anchor"]["x"] = 1.2
        cases.append(bad_anchor)
        overflowing_box = json.loads(json.dumps(VALID_REVIEW))
        overflowing_box["corrections"][0]["anchor"].update({"x": 0.96, "width": 0.08})
        cases.append(overflowing_box)
        phrase_correction = json.loads(json.dumps(VALID_REVIEW))
        phrase_correction["corrections"][0]["suggested_text"] = "末尾"
        cases.append(phrase_correction)
        too_many = dict(VALID_REVIEW, annotations=VALID_REVIEW["annotations"] * 11)
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
                anchor={
                    "x": 0.1 + index * 0.05,
                    "y": 0.2 + index * 0.04,
                    "width": 0.05,
                    "height": 0.05,
                },
            )
            for index in range(8)
        ]
        review = parse_review(long_payload)
        pages = layout_review(review, width=954, height=1696)

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
            self.assertEqual((page.width, page.height), (954, 1696))
            for box in page.boxes:
                self.assertGreaterEqual(box.x, 0)
                self.assertGreaterEqual(box.y, 0)
                self.assertLessEqual(box.x + box.width, page.width)
                self.assertLessEqual(box.y + box.height, page.height)
                self.assertTrue(box.lines)
                if box.kind != "reply-preview":
                    font_size = max(15, round(page.height * 0.022))
                    text_width = box.width - max(16, round(page.width * 0.012)) * 2
                    self.assertLessEqual(
                        max(len(line) for line in box.lines),
                        max(6, text_width // font_size),
                    )


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

    def build_reviewed_packet(self, source_pdf, review, *, profile_id, incoming_letter):
        self.packet_calls.append((source_pdf, review, profile_id, incoming_letter))
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
    def __init__(self):
        self.calls = []

    def generate_letter(self, *, session_id, conversation_context, on_delta):
        self.calls.append((session_id, conversation_context))
        on_delta("阿妹，见字如面。")
        on_delta("家中一切安好，勿念。")
        return type(
            "CodexLetterResult",
            (),
            {
                "thread_id": "thread-incoming-001",
                "letter": Letter("阿妹，见字如面。家中一切安好，勿念。"),
            },
        )()


class FakePacketRenderer(FakeReplyRenderer):
    def __init__(self, reply_path):
        super().__init__(reply_path)
        self.initial_calls = []

    def build_initial_packet(self, letter, *, profile_id):
        self.initial_calls.append((letter, profile_id))
        return b"%PDF-1.4 initial packet"


def ready_registry(session_id):
    registry = SessionRegistry()
    registry.begin(session_id, "fixture context")
    registry.complete(
        session_id,
        Letter("阿妹，见字如面。家中一切安好，勿念。"),
        "thread-incoming-001",
    )
    return registry


class SubmissionServiceTests(unittest.TestCase):
    def test_live_stream_drops_non_letter_commentary_before_tablet_render(self):
        registry = SessionRegistry()
        registry.begin("session-sanitize", "private context")
        registry.append("session-sanitize", "Here is the letter: **")
        registry.append("session-sanitize", "见字如面。家中安好，勿念。")

        state = registry.public_state("session-sanitize")

        self.assertEqual(state["text"], "见字如面。家中安好，勿念。")
        self.assertEqual(state["version"], 1)

    def test_completed_fictional_letter_survives_bridge_restart_without_private_context(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            state_path = Path(temporary_directory) / "sessions.json"
            first = SessionRegistry(state_path)
            first.begin("session-restart", "private participant context")
            first.complete(
                "session-restart",
                Letter("阿妹，见字如面。家中一切安好，勿念。"),
                "thread-incoming-001",
            )

            persisted = state_path.read_text(encoding="utf-8")
            recovered = SessionRegistry(state_path)

        self.assertNotIn("private participant context", persisted)
        self.assertEqual(recovered.get("session-restart"), "")
        self.assertEqual(recovered.public_state("session-restart")["status"], "ready")
        self.assertEqual(recovered.letter("session-restart").body, "阿妹，见字如面。家中一切安好，勿念。")

    def test_start_uploads_blank_packet_then_accumulates_live_letter_chunks(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            image_path = Path(temporary_directory) / "incoming.png"
            image_path.write_bytes(b"fixture image")
            tablet = FakeTabletDocuments()
            renderer = FakePacketRenderer(image_path)
            generator = FakeLetterGenerator()
            registry = SessionRegistry()
            starter = SessionStarter(
                tablet=tablet,
                renderer=renderer,
                generator=generator,
                registry=registry,
                default_context="default context",
                background=lambda work: work(),
            )

            result = starter.start(
                {
                    "profile_id": "ferrari_3.28.0.162",
                    "conversation_context": "care, recovery, and returning home",
                }
            )

        self.assertEqual(result["status"], "streaming")
        self.assertEqual(result["document_id"], "reviewed-document-001")
        self.assertEqual(len(generator.calls), 1)
        session_id, context = generator.calls[0]
        self.assertEqual(result["session_id"], session_id)
        self.assertEqual(context, "care, recovery, and returning home")
        self.assertEqual(registry.get(session_id), context)
        state = registry.public_state(session_id)
        self.assertEqual(state["status"], "ready")
        self.assertGreaterEqual(state["version"], 3)
        self.assertEqual(state["text"], "阿妹，见字如面。家中一切安好，勿念。")
        self.assertEqual(
            renderer.initial_calls,
            [(None, "ferrari_3.28.0.162")],
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
            registry = SessionRegistry()
            registry.begin("session-fixture-001", "distance, health, and returning home")
            registry.complete(
                "session-fixture-001",
                Letter("阿妹，见字如面。家中一切安好，勿念。"),
                "thread-incoming-001",
            )
            service = SubmissionService(
                tablet=tablet,
                renderer=renderer,
                reviewer=codex,
                registry=registry,
            )

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
        self.assertEqual(renderer.packet_calls[0][3].body, "阿妹，见字如面。家中一切安好，勿念。")

    def test_submit_retries_a_transient_just_saved_export_before_starting_codex(self):
        class JustSavedTablet(FakeTabletDocuments):
            def export_pdf(self, document_id):
                self.export_calls.append(document_id)
                if len(self.export_calls) == 1:
                    raise RuntimeError("remarkable_usb_unreachable")
                return b"%PDF-1.4 settled annotated reply"

        with tempfile.TemporaryDirectory() as temporary_directory:
            reply_path = Path(temporary_directory) / "reply.png"
            reply_path.write_bytes(b"fixture image")
            tablet = JustSavedTablet()
            renderer = FakeReplyRenderer(reply_path)
            codex = FakeCodexReviewer()
            service = SubmissionService(
                tablet=tablet,
                renderer=renderer,
                reviewer=codex,
                registry=ready_registry("session-fixture-retry"),
            )

            with patch("mac_bridge.service.time.sleep") as sleep:
                result = service.submit(
                    {
                        "session_id": "session-fixture-retry",
                        "document_id": "native-document-retry",
                        "reply_page_index": 1,
                        "profile_id": "ferrari_3.28.0.162",
                        "conversation_context": "",
                    }
                )

        self.assertEqual(result["status"], "reviewed")
        self.assertEqual(
            tablet.export_calls,
            ["native-document-retry", "native-document-retry"],
        )
        sleep.assert_called_once_with(1)
        self.assertEqual(len(codex.calls), 1)

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
                registry=ready_registry("session-fixture-001"),
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
        self.assertEqual(DEFAULT_USB_BIND, "10.11.99.16")

        class Starter:
            def start(self, payload):
                return {"status": "ready", "document_id": payload["fixture"]}

        class Submissions:
            def submit(self, payload):
                return {"status": "reviewed", "document_id": payload["fixture"]}

        class Registry:
            def public_state(self, session_id):
                return {"status": "streaming", "session_id": session_id, "version": 2, "text": "见字"}

        application = BridgeApplication(
            starter=Starter(), submissions=Submissions(), registry=Registry()
        )
        start_status, start = application.dispatch(
            "/v1/sessions/start", {"fixture": "initial-001"}
        )
        submit_status, submit = application.dispatch(
            "/v1/sessions/submit", {"fixture": "reviewed-001"}
        )
        missing_status, missing = application.dispatch("/unknown", {"private": "ink"})
        stream_status, stream = application.dispatch_get("/v1/sessions/fixture-001")

        self.assertEqual((start_status, start["document_id"]), (200, "initial-001"))
        self.assertEqual((submit_status, submit["document_id"]), (200, "reviewed-001"))
        self.assertEqual((missing_status, missing), (404, {"error": "not_found"}))
        self.assertEqual((stream_status, stream["text"]), (200, "见字"))


if __name__ == "__main__":
    unittest.main()
