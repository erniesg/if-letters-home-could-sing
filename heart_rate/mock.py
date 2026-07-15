"""Deterministic heart-rate source for required tests and host simulation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Sequence

from .models import (
    CaptureGap,
    CaptureMode,
    ConnectionState,
    ConsentState,
    HeartRateSample,
    SourceEvent,
    require_aware,
)


class MockEventKind(str, Enum):
    SAMPLE = "sample"
    DISCONNECT = "disconnect"
    RECONNECT = "reconnect"


@dataclass(frozen=True)
class MockEvent:
    at: datetime
    kind: MockEventKind
    bpm: int | None = None
    receive_delay_ms: int = 0
    rr_intervals_ms: tuple[float, ...] = ()
    quality_flags: tuple[str, ...] = ("good",)

    def __post_init__(self) -> None:
        require_aware(self.at, "at")
        if self.kind is MockEventKind.SAMPLE:
            if self.bpm is None or not 0 < self.bpm <= 0xFFFF:
                raise ValueError("sample events require a positive BLE-range bpm")
            if any(interval <= 0 for interval in self.rr_intervals_ms):
                raise ValueError("sample RR intervals must be positive")
            if not self.quality_flags:
                raise ValueError("sample quality flags are required")
        elif self.bpm is not None or self.rr_intervals_ms:
            raise ValueError("connection events cannot contain measurements")
        if self.receive_delay_ms < 0:
            raise ValueError("receive delay cannot be negative")

    @classmethod
    def sample(
        cls,
        at: datetime,
        bpm: int,
        *,
        receive_delay_ms: int = 0,
        rr_intervals_ms: tuple[float, ...] = (),
        quality_flags: tuple[str, ...] = ("good",),
    ) -> "MockEvent":
        return cls(
            at=at,
            kind=MockEventKind.SAMPLE,
            bpm=bpm,
            receive_delay_ms=receive_delay_ms,
            rr_intervals_ms=rr_intervals_ms,
            quality_flags=quality_flags,
        )

    @classmethod
    def disconnect(cls, at: datetime) -> "MockEvent":
        return cls(at=at, kind=MockEventKind.DISCONNECT)

    @classmethod
    def reconnect(cls, at: datetime) -> "MockEvent":
        return cls(at=at, kind=MockEventKind.RECONNECT)


class MockHeartRateSource:
    """Replays an immutable event script with no clock, device, or network."""

    source_id = "mock"
    capture_mode = CaptureMode.MOCK

    def __init__(self, events: Sequence[MockEvent] = (), *, available: bool = True):
        self._events = tuple(events)
        if any(right.at < left.at for left, right in zip(self._events, self._events[1:])):
            raise ValueError("mock events must be ordered by timestamp")
        self.available = available
        self.state = ConnectionState.IDLE
        self.connection_history: list[tuple[datetime, ConnectionState]] = []
        self._cursor = 0
        self._started_at: datetime | None = None
        self._last_read_at: datetime | None = None
        self._gap_started_at: datetime | None = None

    def start(self, at: datetime, consent: ConsentState) -> ConnectionState:
        require_aware(at, "at")
        self._cursor = 0
        self._started_at = at
        self._last_read_at = at
        self._gap_started_at = None
        if consent is ConsentState.DECLINED:
            self.state = ConnectionState.DECLINED
        elif not self.available:
            self.state = ConnectionState.UNAVAILABLE
        else:
            self.state = ConnectionState.CONNECTED
        self.connection_history = [(at, self.state)]
        return self.state

    def read(self, until: datetime) -> tuple[SourceEvent, ...]:
        require_aware(until, "until")
        if self._last_read_at is None:
            raise RuntimeError("source has not started")
        if until < self._last_read_at:
            raise ValueError("mock time cannot move backwards")
        if self.state in {
            ConnectionState.DECLINED,
            ConnectionState.UNAVAILABLE,
            ConnectionState.STOPPED,
        }:
            self._last_read_at = until
            return ()

        emitted: list[SourceEvent] = []
        while self._cursor < len(self._events):
            event = self._events[self._cursor]
            if event.at > until:
                break
            self._cursor += 1
            if self._started_at is not None and event.at < self._started_at:
                continue
            if event.kind is MockEventKind.SAMPLE:
                if self.state is ConnectionState.CONNECTED:
                    emitted.append(
                        HeartRateSample(
                            captured_at=event.at,
                            received_at=event.at + timedelta(milliseconds=event.receive_delay_ms),
                            bpm=event.bpm if event.bpm is not None else 0,
                            source=self.source_id,
                            rr_intervals_ms=event.rr_intervals_ms,
                            quality_flags=event.quality_flags,
                        )
                    )
            elif event.kind is MockEventKind.DISCONNECT:
                if self.state is ConnectionState.CONNECTED:
                    self._gap_started_at = event.at
                    self.state = ConnectionState.RECONNECTING
                    self.connection_history.append((event.at, self.state))
            elif self.state is ConnectionState.RECONNECTING and self._gap_started_at is not None:
                emitted.append(
                    CaptureGap(
                        started_at=self._gap_started_at,
                        ended_at=event.at,
                        source=self.source_id,
                    )
                )
                self._gap_started_at = None
                self.state = ConnectionState.CONNECTED
                self.connection_history.append((event.at, self.state))

        self._last_read_at = until
        return tuple(emitted)

    def stop(self, at: datetime) -> tuple[SourceEvent, ...]:
        emitted = list(self.read(at))
        if self.state is ConnectionState.RECONNECTING and self._gap_started_at is not None:
            emitted.append(
                CaptureGap(
                    started_at=self._gap_started_at,
                    ended_at=at,
                    source=self.source_id,
                )
            )
            self._gap_started_at = None
        if self.state not in {ConnectionState.DECLINED, ConnectionState.UNAVAILABLE}:
            self.state = ConnectionState.STOPPED
            self.connection_history.append((at, self.state))
        return tuple(emitted)
