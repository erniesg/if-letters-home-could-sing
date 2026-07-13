"""Standard BLE Heart Rate Measurement parsing and authenticated relay."""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Protocol
from urllib.parse import urlparse

from .models import (
    CaptureGap,
    CaptureMode,
    ConnectionState,
    ConsentState,
    HeartRateSample,
    SourceEvent,
    require_aware,
)


class BlePacketError(ValueError):
    pass


@dataclass(frozen=True)
class HeartRateMeasurement:
    bpm: int
    sensor_contact: bool | None
    energy_expended: int | None
    rr_intervals_1024s: tuple[int, ...]

    @property
    def rr_intervals_ms(self) -> tuple[float, ...]:
        return tuple(value * 1000 / 1024 for value in self.rr_intervals_1024s)


def parse_heart_rate_measurement(packet: bytes | bytearray | memoryview) -> HeartRateMeasurement:
    """Parse Bluetooth SIG Heart Rate Measurement characteristic bytes."""
    payload = bytes(packet)
    if len(payload) < 2:
        raise BlePacketError("heart-rate measurement is truncated")
    flags = payload[0]
    offset = 1

    if flags & 0x01:
        if len(payload) < offset + 2:
            raise BlePacketError("16-bit heart rate is truncated")
        bpm = int.from_bytes(payload[offset : offset + 2], "little")
        offset += 2
    else:
        bpm = payload[offset]
        offset += 1
    if bpm == 0:
        raise BlePacketError("heart rate must be positive")

    contact_supported = bool(flags & 0x04)
    sensor_contact = bool(flags & 0x02) if contact_supported else None

    energy_expended = None
    if flags & 0x08:
        if len(payload) < offset + 2:
            raise BlePacketError("energy-expended field is truncated")
        energy_expended = int.from_bytes(payload[offset : offset + 2], "little")
        offset += 2

    rr_intervals: tuple[int, ...] = ()
    if flags & 0x10:
        remaining = payload[offset:]
        if not remaining or len(remaining) % 2:
            raise BlePacketError("RR interval field is truncated")
        rr_intervals = tuple(
            int.from_bytes(remaining[index : index + 2], "little")
            for index in range(0, len(remaining), 2)
        )
        if any(value == 0 for value in rr_intervals):
            raise BlePacketError("RR intervals must be positive")
        offset = len(payload)

    if offset != len(payload):
        raise BlePacketError("measurement has trailing bytes without an RR flag")
    return HeartRateMeasurement(bpm, sensor_contact, energy_expended, rr_intervals)


class WebSocketJsonSender(Protocol):
    def send_json(
        self, *, url: str, headers: Mapping[str, str], payload: Mapping[str, object]
    ) -> None:
        ...


class BleRelayClient:
    """Phone/edge client that forwards BLE samples and connection gaps over WSS."""

    def __init__(self, relay_url: str, bearer_token: str, sender: WebSocketJsonSender):
        parsed = urlparse(relay_url)
        if (
            parsed.scheme != "wss"
            or not parsed.netloc
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("BLE relay URL must use wss:// without URL credentials")
        if not bearer_token:
            raise ValueError("BLE relay bearer token is required")
        self.relay_url = relay_url
        self._bearer_token = bearer_token
        self._sender = sender

    def __repr__(self) -> str:
        return f"BleRelayClient(relay_url={self.relay_url!r}, bearer_token='[REDACTED]')"

    def forward_packet(self, packet: bytes, captured_at: datetime) -> HeartRateMeasurement:
        require_aware(captured_at, "captured_at")
        measurement = parse_heart_rate_measurement(packet)
        self._send(
            {
                "schema_version": "1",
                "kind": "sample",
                "source": "ble-relay",
                "captured_at": captured_at.isoformat(),
                "bpm": measurement.bpm,
                "rr_intervals_1024s": list(measurement.rr_intervals_1024s),
                "quality_flags": ["good"],
            }
        )
        return measurement

    def disconnect(self, at: datetime) -> None:
        self._send_gap("gap-start", at)

    def reconnect(self, at: datetime) -> None:
        self._send_gap("gap-end", at)

    def _send_gap(self, kind: str, at: datetime) -> None:
        require_aware(at, "at")
        self._send(
            {
                "schema_version": "1",
                "kind": kind,
                "source": "ble-relay",
                "captured_at": at.isoformat(),
            }
        )

    def _send(self, payload: Mapping[str, object]) -> None:
        self._sender.send_json(
            url=self.relay_url,
            headers={"Authorization": f"Bearer {self._bearer_token}"},
            payload=payload,
        )


class BleRelayHeartRateSource:
    """Gateway source for authenticated relay messages; no radio or network is required."""

    source_id = "ble-relay"
    capture_mode = CaptureMode.LIVE

    def __init__(self, bearer_token: str):
        if not bearer_token:
            raise ValueError("BLE relay bearer token is required")
        self._bearer_token = bearer_token
        self.state = ConnectionState.IDLE
        self._pending: list[SourceEvent] = []
        self._gap_started_at: datetime | None = None
        self._last_read_at: datetime | None = None

    def __repr__(self) -> str:
        return "BleRelayHeartRateSource(bearer_token='[REDACTED]')"

    def start(self, at: datetime, consent: ConsentState) -> ConnectionState:
        require_aware(at, "at")
        self._pending.clear()
        self._gap_started_at = None
        self._last_read_at = at
        self.state = (
            ConnectionState.CONNECTED
            if consent is ConsentState.GRANTED
            else ConnectionState.DECLINED
        )
        return self.state

    def receive(
        self,
        payload: Mapping[str, object],
        *,
        authorization: str,
        received_at: datetime,
    ) -> None:
        """Accept a decoded WebSocket message after constant-time bearer validation."""
        require_aware(received_at, "received_at")
        expected = f"Bearer {self._bearer_token}"
        if not hmac.compare_digest(authorization, expected):
            raise PermissionError("invalid BLE relay authorization")
        if payload.get("schema_version") != "1" or payload.get("source") != self.source_id:
            raise ValueError("unsupported BLE relay message")
        captured_at = _parse_timestamp(payload.get("captured_at"))
        kind = payload.get("kind")

        if kind == "sample":
            if self.state is not ConnectionState.CONNECTED:
                raise RuntimeError("sample received while BLE relay is disconnected")
            bpm = payload.get("bpm")
            rr_values = payload.get("rr_intervals_1024s", [])
            quality = payload.get("quality_flags", ["good"])
            if not isinstance(bpm, int) or isinstance(bpm, bool):
                raise ValueError("relay sample bpm must be an integer")
            if not isinstance(rr_values, list) or not all(
                isinstance(value, int) and not isinstance(value, bool) and value > 0
                for value in rr_values
            ):
                raise ValueError("relay RR intervals must be positive integers")
            if not isinstance(quality, list) or not all(
                isinstance(flag, str) and flag for flag in quality
            ):
                raise ValueError("relay quality flags must be non-empty strings")
            self._pending.append(
                HeartRateSample(
                    captured_at=captured_at,
                    received_at=received_at,
                    bpm=bpm,
                    source=self.source_id,
                    rr_intervals_ms=tuple(value * 1000 / 1024 for value in rr_values),
                    quality_flags=tuple(quality),
                )
            )
        elif kind == "gap-start":
            if self.state is ConnectionState.CONNECTED:
                self._gap_started_at = captured_at
                self.state = ConnectionState.RECONNECTING
        elif kind == "gap-end":
            if self.state is not ConnectionState.RECONNECTING or self._gap_started_at is None:
                raise ValueError("relay gap ended without a disconnect")
            self._pending.append(CaptureGap(self._gap_started_at, captured_at, self.source_id))
            self._gap_started_at = None
            self.state = ConnectionState.CONNECTED
        else:
            raise ValueError("unknown BLE relay message kind")

    def read(self, until: datetime) -> tuple[SourceEvent, ...]:
        require_aware(until, "until")
        if self._last_read_at is None:
            raise RuntimeError("source has not started")
        if until < self._last_read_at:
            raise ValueError("relay time cannot move backwards")
        ready: list[SourceEvent] = []
        waiting: list[SourceEvent] = []
        for event in self._pending:
            event_at = event.captured_at if isinstance(event, HeartRateSample) else event.ended_at
            (ready if event_at <= until else waiting).append(event)
        self._pending = waiting
        self._last_read_at = until
        return tuple(ready)

    def stop(self, at: datetime) -> tuple[SourceEvent, ...]:
        emitted = list(self.read(at))
        if self.state is ConnectionState.RECONNECTING and self._gap_started_at is not None:
            emitted.append(CaptureGap(self._gap_started_at, at, self.source_id))
            self._gap_started_at = None
        if self.state not in {ConnectionState.DECLINED, ConnectionState.UNAVAILABLE}:
            self.state = ConnectionState.STOPPED
        self._pending.clear()
        return tuple(emitted)


def _parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("relay captured_at must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("relay captured_at must be an ISO-8601 string") from error
    require_aware(parsed, "captured_at")
    return parsed
