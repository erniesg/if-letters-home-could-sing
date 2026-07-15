import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from heart_rate import (
    BlePacketError,
    BleRelayClient,
    BleRelayHeartRateSource,
    ConnectionState,
    ConsentRequired,
    ConsentState,
    HeartRateCapture,
    HeartRateSample,
    IntegrationDisabled,
    MockEvent,
    MockHeartRateSource,
    SampleDisposition,
    ServerOAuthConfig,
    WhoopAggregateSource,
    WhoopProviderError,
    parse_heart_rate_measurement,
)


ROOT = Path(__file__).resolve().parents[1]
BASE = datetime(2026, 7, 14, tzinfo=timezone.utc)


def at(seconds: float) -> datetime:
    return BASE + timedelta(seconds=seconds)


def fixture_value(kind: str) -> str:
    return "-".join(("fixture", kind, "value"))


def sample(seconds: float, bpm: int = 72) -> HeartRateSample:
    return HeartRateSample(
        captured_at=at(seconds),
        received_at=at(seconds + 0.08),
        bpm=bpm,
        source="fixture",
    )


class MockHeartRateSourceTests(unittest.TestCase):
    def test_deterministic_samples_reconnect_and_gap(self):
        events = (
            MockEvent.sample(at(1), 72, receive_delay_ms=80),
            MockEvent.disconnect(at(2)),
            MockEvent.sample(at(3), 200),  # lost during the explicit gap
            MockEvent.reconnect(at(4)),
            MockEvent.sample(at(5), 75, quality_flags=("good", "reconnected")),
        )

        def replay():
            source = MockHeartRateSource(events)
            self.assertEqual(source.start(at(1), ConsentState.GRANTED), ConnectionState.CONNECTED)
            emitted = source.read(at(5))
            return source, emitted

        first_source, first = replay()
        second_source, second = replay()
        self.assertEqual(first, second)
        self.assertEqual([event.bpm for event in first if isinstance(event, HeartRateSample)], [72, 75])
        gaps = [event for event in first if not isinstance(event, HeartRateSample)]
        self.assertEqual([(gap.started_at, gap.ended_at) for gap in gaps], [(at(2), at(4))])
        self.assertEqual(first_source.connection_history, second_source.connection_history)

    def test_declined_and_unavailable_states_do_not_emit(self):
        declined = MockHeartRateSource((MockEvent.sample(at(1), 72),))
        self.assertEqual(
            declined.start(at(0), ConsentState.DECLINED), ConnectionState.DECLINED
        )
        self.assertEqual(declined.read(at(2)), ())

        unavailable = MockHeartRateSource((MockEvent.sample(at(1), 72),), available=False)
        self.assertEqual(
            unavailable.start(at(0), ConsentState.GRANTED), ConnectionState.UNAVAILABLE
        )
        self.assertEqual(unavailable.read(at(2)), ())


class HeartRateCaptureTests(unittest.TestCase):
    def test_first_accepted_stroke_through_atomic_submit(self):
        source = MockHeartRateSource(
            (
                MockEvent.sample(at(0), 60),
                MockEvent.sample(at(2), 72),
                MockEvent.disconnect(at(3)),
                MockEvent.reconnect(at(4)),
                MockEvent.sample(at(5), 74, quality_flags=("good", "reconnected")),
                MockEvent.sample(at(7), 90),
            )
        )
        capture = HeartRateCapture(source, ConsentState.GRANTED)

        self.assertEqual(
            capture.ingest_sample(sample(0)), SampleDisposition.BEFORE_FIRST_INK
        )
        self.assertFalse(capture.accepted_stroke(at(0.5), accepted=False))
        self.assertTrue(capture.accepted_stroke(at(1)))
        self.assertFalse(capture.accepted_stroke(at(1.5)))
        self.assertEqual(capture.collect(at(4)), 1)
        summary = capture.submit(at(5))

        self.assertEqual([value.bpm for value in capture.samples], [72, 74])
        self.assertEqual(capture.first_ink_at, at(1))
        self.assertEqual(capture.submitted_at, at(5))
        self.assertEqual(summary.sample_count, 2)
        self.assertEqual(summary.gap_count, 1)
        self.assertEqual(summary.reconnect_count, 1)
        self.assertEqual(summary.gap_duration_ms, 1000)
        self.assertTrue(summary.sample_loss_observed)
        self.assertIn("no offset correction", summary.clock_offset_assumption)

        self.assertEqual(
            capture.ingest_sample(sample(5, 88)), SampleDisposition.AFTER_SUBMIT
        )
        self.assertEqual(capture.submit(at(6)).sample_count, 2)

    def test_declined_capture_and_empty_submit_complete(self):
        source = MockHeartRateSource((MockEvent.sample(at(2), 72),))
        capture = HeartRateCapture(source, ConsentState.DECLINED)
        capture.accepted_stroke(at(1))
        summary = capture.submit(at(3))
        self.assertEqual(summary.connection_state, ConnectionState.DECLINED)
        self.assertEqual(summary.sample_count, 0)

        empty_source = MockHeartRateSource()
        empty = HeartRateCapture(empty_source, ConsentState.DECLINED)
        self.assertEqual(empty.submit(at(3)).sample_count, 0)
        self.assertEqual(empty.submitted_at, at(3))


class BleParserTests(unittest.TestCase):
    def test_parses_8_and_16_bit_measurements_with_rr_intervals(self):
        eight_bit = parse_heart_rate_measurement(bytes([0x00, 72]))
        self.assertEqual(eight_bit.bpm, 72)
        self.assertIsNone(eight_bit.sensor_contact)

        # 16-bit BPM, contact supported/detected, energy, and two RR intervals.
        packet = bytes([0x1F, 0x2C, 0x01, 0xD2, 0x04, 0x00, 0x04, 0x00, 0x02])
        measurement = parse_heart_rate_measurement(packet)
        self.assertEqual(measurement.bpm, 300)
        self.assertTrue(measurement.sensor_contact)
        self.assertEqual(measurement.energy_expended, 1234)
        self.assertEqual(measurement.rr_intervals_1024s, (1024, 512))
        self.assertEqual(measurement.rr_intervals_ms, (1000.0, 500.0))

    def test_rejects_truncated_and_unflagged_trailing_fields(self):
        for packet in (b"", bytes([0x01, 0x48]), bytes([0x10, 72, 0x01])):
            with self.subTest(packet=packet), self.assertRaises(BlePacketError):
                parse_heart_rate_measurement(packet)
        with self.assertRaises(BlePacketError):
            parse_heart_rate_measurement(bytes([0x00, 72, 0x00]))


class RecordingSender:
    def __init__(self):
        self.messages = []

    def send_json(self, **message):
        self.messages.append(message)


class BleRelayTests(unittest.TestCase):
    def test_authenticated_wss_relay_preserves_gap_without_interpolation(self):
        sender = RecordingSender()
        token = fixture_value("relay")
        client = BleRelayClient("wss://relay.invalid/heart-rate", token, sender)
        self.assertNotIn(token, repr(client))
        with self.assertRaises(ValueError):
            BleRelayClient("ws://relay.invalid/heart-rate", token, sender)
        with self.assertRaises(ValueError):
            BleRelayClient("wss://relay.invalid/heart-rate?token=unsafe", token, sender)

        client.forward_packet(bytes([0x10, 72, 0x00, 0x04]), at(1))
        client.disconnect(at(2))
        client.reconnect(at(4))
        self.assertEqual(
            [message["payload"]["kind"] for message in sender.messages],
            ["sample", "gap-start", "gap-end"],
        )
        for message in sender.messages:
            self.assertEqual(message["headers"]["Authorization"], f"Bearer {token}")
            self.assertNotIn(token, json.dumps(message["payload"]))

        source = BleRelayHeartRateSource(token)
        source.start(at(0), ConsentState.GRANTED)
        for index, message in enumerate(sender.messages):
            source.receive(
                message["payload"],
                authorization=message["headers"]["Authorization"],
                received_at=at(index + 1.1),
            )
        emitted = source.read(at(5))
        samples = [event for event in emitted if isinstance(event, HeartRateSample)]
        gaps = [event for event in emitted if not isinstance(event, HeartRateSample)]
        self.assertEqual([event.bpm for event in samples], [72])
        self.assertEqual(samples[0].rr_intervals_ms, (1000.0,))
        self.assertEqual([(gap.started_at, gap.ended_at) for gap in gaps], [(at(2), at(4))])

    def test_gateway_rejects_bad_relay_authentication(self):
        source = BleRelayHeartRateSource(fixture_value("relay"))
        source.start(at(0), ConsentState.GRANTED)
        with self.assertRaises(PermissionError):
            source.receive(
                {
                    "schema_version": "1",
                    "kind": "sample",
                    "source": "ble-relay",
                    "captured_at": at(1).isoformat(),
                    "bpm": 72,
                },
                authorization="Bearer wrong",
                received_at=at(1.1),
            )


class WhoopOAuthTests(unittest.TestCase):
    def setUp(self):
        self.client_secret = fixture_value("client")
        self.access_token = fixture_value("access")
        self.refresh_token = fixture_value("refresh")
        self.config = ServerOAuthConfig(
            client_id="fixture-client-id",
            client_secret=self.client_secret,
            redirect_uri="https://gateway.invalid/oauth/whoop/callback",
        )

    def test_disabled_by_default_and_consent_required(self):
        disabled = WhoopAggregateSource(self.config)
        with self.assertRaises(IntegrationDisabled):
            disabled.authorization_url(state="12345678", consent=ConsentState.GRANTED)

        enabled = WhoopAggregateSource(self.config, enabled=True)
        with self.assertRaises(ConsentRequired):
            enabled.authorization_url(state="12345678", consent=ConsentState.DECLINED)

    def test_current_v2_endpoints_scopes_refresh_and_revoke(self):
        source = WhoopAggregateSource(self.config, enabled=True)
        authorization = urlparse(
            source.authorization_url(state="12345678", consent=ConsentState.GRANTED)
        )
        self.assertEqual(
            f"{authorization.scheme}://{authorization.netloc}{authorization.path}",
            "https://api.prod.whoop.com/oauth/oauth2/auth",
        )
        query = parse_qs(authorization.query)
        self.assertEqual(query["scope"], ["offline read:cycles read:recovery"])

        refresh = source.refresh_request(self.refresh_token)
        self.assertEqual(refresh.url, "https://api.prod.whoop.com/oauth/oauth2/token")
        self.assertEqual(refresh.form["grant_type"], "refresh_token")
        revoke = source.revoke_request(self.access_token)
        self.assertEqual(revoke.method, "DELETE")
        self.assertEqual(revoke.url, "https://api.prod.whoop.com/developer/v2/user/access")
        self.assertEqual(
            source.aggregate_request("cycles", self.access_token).url,
            "https://api.prod.whoop.com/developer/v2/cycle",
        )

    def test_credentials_and_provider_payloads_are_redacted(self):
        source = WhoopAggregateSource(self.config, enabled=True)
        requests = (
            source.exchange_code_request("synthetic-authorization-code"),
            source.refresh_request(self.refresh_token),
            source.revoke_request(self.access_token),
        )
        for request in requests:
            rendered = repr(request) + json.dumps(request.redacted())
            self.assertNotIn(self.client_secret, rendered)
            self.assertNotIn(self.access_token, rendered)
            self.assertNotIn(self.refresh_token, rendered)
        self.assertNotIn(self.client_secret, repr(self.config))
        self.assertNotIn(self.client_secret, json.dumps(self.config.tablet_config()))
        self.assertNotIn("provider body", str(WhoopProviderError(502)))

        self.assertFalse((ROOT / "frontend" / "lib" / "whoopAuth.ts").exists())
        self.assertFalse((ROOT / "frontend" / "lib" / "heartRate" / "ble.ts").exists())
        route = (ROOT / "frontend" / "app" / "api" / "route.ts").read_text()
        self.assertNotIn("WHOOP_ACCESS_TOKEN", route)
        self.assertNotRegex(route, r"console\.(log|error)")
        frontend = "\n".join(
            path.read_text()
            for path in (ROOT / "frontend").rglob("*")
            if path.suffix in {".ts", ".tsx"}
        )
        for unsafe_log in (
            "Heart Rate:', heartRate",
            "Heart Rate Updated:', newRate",
            "Heart Rate Window:', this.window",
            "RR Intervals:', rrIntervals",
            "Received data:', data",
            "Cycles:', cycles",
        ):
            self.assertNotIn(unsafe_log, frontend)


if __name__ == "__main__":
    unittest.main()
