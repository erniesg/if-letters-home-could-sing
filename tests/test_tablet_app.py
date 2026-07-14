import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from tablet_app import (
    MESSAGE_CONFIRM_EMPTY,
    MESSAGE_CONSENT,
    MESSAGE_OPEN,
    MESSAGE_RETRY,
    MESSAGE_STATE,
    MESSAGE_STROKE,
    MESSAGE_SUBMIT,
    MESSAGE_SWIPE,
    FixtureBackend,
    MockPenSource,
)
from tablet_app.adapter import OutboundMessage
from tablet_app.layout import (
    INK,
    MIN_TOUCH_TARGET,
    MUTED_RED,
    PAPER,
    contrast_ratio,
    layer_model,
    load_profiles,
    make_layout,
    snapshot_svg,
    wrap_translation,
)
from tablet_app.packaging import SOURCE, build_bundle, validate_source
from tablet_app.protocol import (
    HEADER,
    MSG_SYSTEM_NEW_COORDINATOR,
    receive_message,
    send_message,
)
from tablet_app.simulator import run_scenario, snapshot_state, verify_snapshots


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOTS = ROOT / "tablet_app" / "snapshots"


def unix_seqpacket_supported():
    try:
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    except OSError:
        return False
    connection.close()
    return True


UNIX_SEQPACKET_SUPPORTED = unix_seqpacket_supported()


class PacketChannel:
    def __init__(self):
        self.packets = []

    def send(self, contents):
        self.packets.append(contents)
        return len(contents)

    def recv(self, _size):
        return self.packets.pop(0) if self.packets else b""


def build_fixture_bundle(temporary_path):
    fake_rcc = temporary_path / "rcc"
    fake_rcc.write_text(
        "#!/bin/sh\n"
        "out=\n"
        "while [ \"$#\" -gt 0 ]; do\n"
        "  if [ \"$1\" = -o ]; then shift; out=$1; fi\n"
        "  shift\n"
        "done\n"
        "printf fixture-rcc > \"$out\"\n"
    )
    fake_rcc.chmod(0o755)
    output = temporary_path / "bundle"
    build_bundle(output, str(fake_rcc))
    return output


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


def state_values(messages):
    return [
        message.payload["state"]
        for message in messages
        if message.message_type == MESSAGE_STATE
    ]


class AppLoadSourceTests(unittest.TestCase):
    def test_qml_subcomponents_import_accessibility_attached_type(self):
        for filename in ("StationeryLayer.qml", "InkLayer.qml", "MarginaliaLayer.qml"):
            with self.subTest(filename=filename):
                source = (SOURCE / "ui" / filename).read_text(encoding="utf-8")
                self.assertIn("import QtQuick.Controls 2.5", source)

    def test_native_fixture_review_is_teacher_like_and_non_scoring(self):
        source = (SOURCE / "backend" / "native_backend.c").read_text(encoding="utf-8")
        self.assertIn('\\"kind\\":\\"uncertain_reading\\"', source)
        self.assertIn('\\"kind\\":\\"language_note\\"', source)
        self.assertIn("测试", source)
        self.assertIn("不确定", source)
        self.assertNotIn("score", source.lower())
        self.assertNotIn("grade", source.lower())

    def test_manifest_qml_and_socket_entry_follow_the_example_contract(self):
        validate_source()
        manifest = json.loads((SOURCE / "manifest.json").read_text())
        self.assertEqual(manifest["entry"], "/ui/Main.qml")
        self.assertEqual(manifest["id"], "letters-home")
        self.assertTrue(manifest["loadsBackend"])
        self.assertFalse(manifest["canHaveMultipleFrontends"])

        qml = (SOURCE / "ui" / "Main.qml").read_text()
        self.assertIn("signal close", qml)
        self.assertIn("function unloading()", qml)
        self.assertIn("endpoint.terminate()", qml)
        self.assertIn('applicationID: "letters-home"', qml)
        self.assertIn("onMessageReceived", qml)
        self.assertIn("progressDelay.restart()", qml)
        self.assertIn("interval: 250", qml)

    def test_qml_has_separate_stationery_ink_and_marginalia_components(self):
        qml = (SOURCE / "ui" / "Main.qml").read_text()
        positions = [
            qml.index("StationeryLayer {"),
            qml.index("InkLayer {"),
            qml.index("MarginaliaLayer {"),
        ]
        self.assertEqual(positions, sorted(positions))
        stationery = (SOURCE / "ui" / "StationeryLayer.qml").read_text()
        self.assertNotRegex(stationery, r"\b(?:Text|Image)\s*\{")
        self.assertIn("guideColumns: root.ferrariProfile ? 8 : 12", qml)
        self.assertIn("property var strokes: []", qml)

    def test_incoming_page_has_visible_and_accessible_fictional_provenance(self):
        qml = (SOURCE / "ui" / "Main.qml").read_text()
        notice = "A fictional letter generated for this encounter"
        self.assertIn(f'text: "{notice}"', qml)
        self.assertIn("Accessible.description: \"Provenance disclosure\"", qml)
        self.assertIn("qrc:/assets/incoming-qiaopi-ferrari-001.png", qml)
        qrc = (SOURCE / "application.qrc").read_text(encoding="utf-8")
        self.assertIn(
            'alias="assets/incoming-qiaopi-ferrari-001.png"',
            qrc,
        )
        self.assertIn(
            "../../fixtures/generated/incoming-qiaopi-ferrari-001.png",
            qrc,
        )

    def test_app_has_a_discreet_exit_without_fixture_orientation_chrome(self):
        qml = (SOURCE / "ui" / "Main.qml").read_text(encoding="utf-8")
        self.assertIn("onClicked: root.close()", qml)
        self.assertIn('Accessible.name: "Close Letters Home"', qml)
        self.assertNotIn("Landscape fixture", qml)
        self.assertNotIn("Portrait fixture", qml)

    def test_qml_presents_versioned_optional_heart_rate_choices(self):
        qml = (SOURCE / "ui" / "Main.qml").read_text()
        self.assertIn('text: "Heart rate is optional"', qml)
        self.assertIn('text: "Connect WHOOP"', qml)
        self.assertIn('text: "Continue without heart rate"', qml)
        self.assertIn('visible: biometricConsent === "pending"', qml)
        self.assertIn('Accessible.description: "Purpose notice " + consentVersion', qml)

    def test_bundle_builder_produces_the_required_appload_directory_shape(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            output = build_fixture_bundle(temporary_path)

            self.assertTrue((output / "manifest.json").is_file())
            self.assertTrue((output / "icon.png").is_file())
            self.assertEqual(
                hashlib.sha256((output / "icon.png").read_bytes()).hexdigest(),
                hashlib.sha256(
                    (
                        ROOT
                        / "fixtures"
                        / "generated"
                        / "incoming-qiaopi-ferrari-001.png"
                    ).read_bytes()
                ).hexdigest(),
            )
            self.assertTrue((output / "resources.rcc").is_file())
            self.assertTrue((output / "backend" / "entry").is_file())
            self.assertTrue(
                os.access(output / "backend" / "entry", os.X_OK),
                "backend entry must remain executable",
            )
            self.assertFalse((output / "backend" / "runtime").exists())
            self.assertNotEqual(
                (output / "backend" / "entry").read_bytes()[:2],
                b"#!",
                "the physical bundle backend must not depend on device Python",
            )

    @unittest.skipUnless(
        UNIX_SEQPACKET_SUPPORTED,
        "requires Unix SOCK_SEQPACKET support from the host kernel",
    )
    def test_bundled_backend_uses_the_appload_socket_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            output = build_fixture_bundle(temporary_path)
            path = str(temporary_path / "bundle.sock")
            with socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET) as listener:
                listener.bind(path)
                listener.listen(1)
                process = subprocess.Popen(
                    [str(output / "backend" / "entry"), path],
                    cwd=temporary_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                connection, _ = listener.accept()
                with connection:
                    connection.send(HEADER.pack(MSG_SYSTEM_NEW_COORDINATOR, 0))
                    message_type, contents = receive_message(connection)
                    self.assertEqual(message_type, MESSAGE_STATE)
                    self.assertEqual(json.loads(contents)["state"], "incoming")
                stdout, stderr = process.communicate(timeout=5)
                self.assertEqual(process.returncode, 0, stdout + stderr)

    @unittest.skipUnless(
        UNIX_SEQPACKET_SUPPORTED,
        "requires Unix SOCK_SEQPACKET support from the host kernel",
    )
    def test_native_backend_completes_reply_and_fixture_marginalia_flow(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            output = build_fixture_bundle(temporary_path)
            path = str(temporary_path / "native-flow.sock")
            with socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET) as listener:
                listener.bind(path)
                listener.listen(1)
                process = subprocess.Popen(
                    [str(output / "backend" / "entry"), path],
                    cwd=temporary_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                connection, _ = listener.accept()
                with connection:
                    def exchange(message_type, payload):
                        body = json.dumps(payload, separators=(",", ":")).encode()
                        connection.send(HEADER.pack(message_type, len(body)))
                        if body:
                            connection.send(body)
                        response_type, contents = receive_message(connection)
                        return response_type, json.loads(contents)

                    connection.send(HEADER.pack(MSG_SYSTEM_NEW_COORDINATOR, 0))
                    self.assertEqual(receive_message(connection)[0], MESSAGE_STATE)
                    self.assertEqual(exchange(MESSAGE_CONSENT, {"decision": "declined"})[1]["biometricConsent"], "declined")
                    self.assertEqual(exchange(MESSAGE_SWIPE, {"direction": "forward"})[1]["state"], "reply")
                    stroke = captured_payload()
                    stroke_state = exchange(MESSAGE_STROKE, stroke)[1]
                    self.assertEqual(stroke_state["firstInkAt"], stroke["accepted_at"])
                    self.assertEqual(stroke_state["strokes"][0]["id"], stroke["stroke_id"])
                    submitting = exchange(MESSAGE_SUBMIT, {"confirm_empty": False})[1]
                    self.assertEqual(submitting["state"], "submitting")
                    final_type, final_contents = receive_message(connection)
                    final = json.loads(final_contents)
                    self.assertEqual(final_type, MESSAGE_STATE)
                    self.assertEqual(final["state"], "marginalia")
                    self.assertEqual(final["strokes"], submitting["strokes"])
                    self.assertEqual(
                        [annotation["kind"] for annotation in final["annotations"]],
                        ["uncertain_reading", "language_note"],
                    )
                    review_text = " ".join(
                        [annotation["message"] for annotation in final["annotations"]]
                        + [final["reviewSummary"]]
                    )
                    self.assertIn("测试", review_text)
                    self.assertIn("不确定", review_text)
                    self.assertNotIn("score", review_text.lower())
                    self.assertNotIn("grade", review_text.lower())
                stdout, stderr = process.communicate(timeout=5)
                self.assertEqual(process.returncode, 0, stdout + stderr)


class AdapterIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.backend = FixtureBackend()
        self.backend.dispatch(MESSAGE_CONSENT, {"decision": "declined"})
        self.backend.dispatch(MESSAGE_SWIPE, {"direction": "forward"})

    def test_biometric_choices_record_consent_and_enable_equivalent_flow(self):
        for decision, expected_status in (
            ("granted", "unavailable"),
            ("declined", "declined"),
        ):
            with self.subTest(decision=decision):
                backend = FixtureBackend()
                opened = backend.dispatch(MESSAGE_OPEN)[0]
                blocked = backend.dispatch(MESSAGE_SWIPE, {"direction": "forward"})[0]
                consented = backend.dispatch(MESSAGE_CONSENT, {"decision": decision})[0]
                reply = backend.dispatch(MESSAGE_SWIPE, {"direction": "forward"})[0]
                backend.dispatch(MESSAGE_STROKE, captured_payload())
                final = backend.dispatch(MESSAGE_SUBMIT, {"confirm_empty": False})[-1]

                self.assertEqual(opened.payload["biometricConsent"], "pending")
                self.assertEqual(opened.payload["consentVersion"], "consent-v1")
                self.assertTrue(opened.payload["purposeNotice"])
                self.assertEqual(blocked.payload["code"], "consent_required")
                self.assertEqual(consented.payload["heartRateStatus"], expected_status)
                self.assertEqual(reply.payload["state"], "reply")
                self.assertEqual(final.payload["state"], "marginalia")

    def test_forward_back_forward_navigation_preserves_accepted_ink(self):
        accepted = self.backend.dispatch(MESSAGE_STROKE, captured_payload())[0]
        original_strokes = accepted.payload["strokes"]
        incoming = self.backend.dispatch(MESSAGE_SWIPE, {"direction": "backward"})[0]
        restored = self.backend.dispatch(MESSAGE_SWIPE, {"direction": "forward"})[0]

        self.assertEqual(incoming.payload["state"], "incoming")
        self.assertEqual(restored.payload["state"], "reply")
        self.assertEqual(restored.payload["strokes"], original_strokes)

    def test_mock_pen_records_pressure_time_coordinates_and_first_ink_event(self):
        message = self.backend.dispatch(MESSAGE_STROKE, captured_payload())[0]
        record = self.backend.pen_records[0]

        self.assertEqual(message.payload["event"], "first_ink_started")
        self.assertEqual(message.payload["firstInkAt"], record.accepted_at)
        self.assertEqual([point.elapsed_ms for point in record.points], [0, 18, 37])
        self.assertEqual([point.pressure for point in record.points], [0.45, 0.60, 0.52])
        self.assertEqual((record.points[0].x, record.points[0].y), (0.20, 0.30))

    def test_empty_submit_requires_deliberate_confirmation(self):
        messages = self.backend.dispatch(MESSAGE_SUBMIT, {"confirm_empty": False})
        self.assertEqual(messages[0].message_type, MESSAGE_CONFIRM_EMPTY)
        self.assertEqual(self.backend.session.state.value, "reply")
        confirmed = self.backend.dispatch(MESSAGE_SUBMIT, {"confirm_empty": True})
        self.assertEqual(state_values(confirmed), ["submitting", "marginalia"])
        self.assertEqual(self.backend.session.strokes, ())

    def test_empty_confirmation_rejects_non_boolean_values(self):
        messages = self.backend.dispatch(MESSAGE_SUBMIT, {"confirm_empty": "false"})
        self.assertEqual(messages[0].payload["code"], "invalid_message")
        self.assertEqual(self.backend.session.state.value, "reply")

    def test_timeout_retry_shows_progress_and_never_changes_ink(self):
        backend = FixtureBackend(("timeout", "success"))
        backend.dispatch(MESSAGE_CONSENT, {"decision": "declined"})
        backend.dispatch(MESSAGE_SWIPE, {"direction": "forward"})
        backend.dispatch(MESSAGE_STROKE, captured_payload())
        original_ink = backend.session.strokes

        submitted = backend.dispatch(MESSAGE_SUBMIT, {"confirm_empty": False})
        self.assertEqual(state_values(submitted), ["submitting", "review_error"])
        retried = backend.dispatch(MESSAGE_RETRY)
        self.assertEqual(state_values(retried), ["submitting", "marginalia"])
        self.assertIs(backend.session.strokes, original_ink)
        self.assertGreater(len(backend.session.annotations), 0)

    def test_offline_failure_keeps_reply_available_for_retry(self):
        backend = FixtureBackend(("offline",))
        backend.dispatch(MESSAGE_CONSENT, {"decision": "declined"})
        backend.dispatch(MESSAGE_SWIPE, {"direction": "forward"})
        backend.dispatch(MESSAGE_STROKE, captured_payload())
        ink = backend.session.strokes
        messages = backend.dispatch(MESSAGE_SUBMIT, {"confirm_empty": False})

        self.assertEqual(state_values(messages), ["submitting", "submission_error"])
        self.assertEqual(backend.session.error_code, "gateway_offline")
        self.assertIs(backend.session.strokes, ink)

    def test_toggling_or_removing_overlays_cannot_modify_ink(self):
        self.backend.dispatch(MESSAGE_STROKE, captured_payload())
        final = self.backend.dispatch(MESSAGE_SUBMIT, {"confirm_empty": False})[-1].payload
        full = layer_model(final)
        without_notes = layer_model(final, show_marginalia=False)
        without_paper = layer_model(final, show_stationery=False)

        self.assertEqual(full["ink"]["strokes"], without_notes["ink"]["strokes"])
        self.assertEqual(full["ink"]["strokes"], without_paper["ink"]["strokes"])
        self.assertFalse(without_notes["marginalia"]["visible"])
        self.assertFalse(without_paper["stationery"]["visible"])


class SocketBoundaryTests(unittest.TestCase):
    def test_frame_helpers_match_separate_header_and_body_packets(self):
        connection = PacketChannel()
        outbound = OutboundMessage(101, {"state": "incoming"})
        send_message(connection, outbound)
        message_type, contents = receive_message(connection)
        self.assertEqual(message_type, 101)
        self.assertEqual(json.loads(contents), {"state": "incoming"})
        self.assertEqual(connection.packets, [])

    @unittest.skipUnless(
        UNIX_SEQPACKET_SUPPORTED,
        "requires Unix SOCK_SEQPACKET support from the host kernel",
    )
    def test_backend_connects_to_socket_from_argv_one(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = str(Path(temporary) / "appload.sock")
            with socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET) as listener:
                listener.bind(path)
                listener.listen(1)
                process = subprocess.Popen(
                    [sys.executable, "-m", "tablet_app.protocol", path],
                    cwd=ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                connection, _ = listener.accept()
                with connection:
                    connection.sendall(HEADER.pack(MSG_SYSTEM_NEW_COORDINATOR, 0))
                    message_type, contents = receive_message(connection)
                    self.assertEqual(message_type, MESSAGE_STATE)
                    self.assertEqual(json.loads(contents)["state"], "incoming")
                stdout, stderr = process.communicate(timeout=5)
                self.assertEqual(process.returncode, 0, stdout + stderr)


class LayoutAndSimulatorTests(unittest.TestCase):
    def test_all_exact_profile_orientation_layouts_have_safe_touch_targets(self):
        expected = {
            ("chiappa", "landscape"): (2160, 1620),
            ("chiappa", "portrait"): (1620, 2160),
            ("ferrari", "landscape"): (1696, 954),
            ("ferrari", "portrait"): (954, 1696),
        }
        for (profile_name, orientation), dimensions in expected.items():
            with self.subTest(profile=profile_name, orientation=orientation):
                layout = make_layout(load_profiles()[profile_name], orientation)
                self.assertEqual((layout.width, layout.height), dimensions)
                self.assertGreaterEqual(layout.primary_action.width, MIN_TOUCH_TARGET)
                self.assertGreaterEqual(layout.primary_action.height, MIN_TOUCH_TARGET)
                self.assertGreater(layout.page.width, 0)
                self.assertGreater(layout.page.height, 0)

    def test_text_contrast_and_long_translations_are_asserted(self):
        self.assertGreaterEqual(contrast_ratio(INK, PAPER), 7.0)
        self.assertGreaterEqual(contrast_ratio(MUTED_RED, PAPER), 4.5)
        translation = (
            "Submit this blank huipi only after confirming that no ink was intended "
            "and that the offline state is understood"
        )
        lines = wrap_translation(translation, width_px=420, font_px=30)
        self.assertEqual(" ".join(lines), translation)
        self.assertGreater(len(lines), 1)

    def test_checked_in_snapshots_match_all_pages_profiles_and_orientations(self):
        self.assertEqual(verify_snapshots(SNAPSHOTS), ())
        self.assertEqual(len(tuple(SNAPSHOTS.glob("*.svg"))), 12)
        for profile_name, profile in load_profiles().items():
            for orientation in ("portrait", "landscape"):
                for state in ("incoming", "reply", "marginalia"):
                    with self.subTest(profile=profile_name, orientation=orientation, state=state):
                        path = SNAPSHOTS / f"{profile_name}-{orientation}-{state}.svg"
                        root = ET.fromstring(path.read_text())
                        width, height = profile.dimensions(orientation)
                        self.assertEqual(root.attrib["viewBox"], f"0 0 {width} {height}")

    def test_snapshot_layers_and_fixture_provenance_are_explicit(self):
        incoming = snapshot_svg(
            load_profiles()["chiappa"], "portrait", snapshot_state("incoming")
        )
        marginalia = snapshot_svg(
            load_profiles()["chiappa"], "portrait", snapshot_state("marginalia")
        )
        self.assertIn("A fictional letter generated for this encounter", incoming)
        for layer in ("stationery-layer", "ink-layer", "marginalia-layer"):
            self.assertIn(f'id="{layer}"', marginalia)

    def test_simulator_exercises_timeout_retry_without_network(self):
        backend, states = run_scenario("timeout-retry")
        self.assertEqual(
            states,
            (
                "incoming",
                "reply",
                "reply",
                "submitting",
                "review_error",
                "submitting",
                "marginalia",
            ),
        )
        self.assertEqual(len(backend.pen_records), 1)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "tablet_app.simulator",
                "--profile",
                "ferrari",
                "--orientation",
                "landscape",
                "--scenario",
                "offline",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("network=disabled", result.stdout)
        self.assertIn("hardware=unverified", result.stdout)


if __name__ == "__main__":
    unittest.main()
