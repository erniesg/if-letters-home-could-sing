"""Shared, provider-neutral heart-rate capture contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol, Sequence, Union


def require_aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must include a timezone")


class ConsentState(str, Enum):
    GRANTED = "granted"
    DECLINED = "declined"


class ConnectionState(str, Enum):
    IDLE = "idle"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    UNAVAILABLE = "unavailable"
    DECLINED = "declined"
    STOPPED = "stopped"


class CaptureMode(str, Enum):
    MOCK = "mock"
    LIVE = "live"
    AGGREGATE = "aggregate"


@dataclass(frozen=True)
class HeartRateSample:
    captured_at: datetime
    received_at: datetime
    bpm: int
    source: str
    rr_intervals_ms: tuple[float, ...] = ()
    quality_flags: tuple[str, ...] = ("good",)

    def __post_init__(self) -> None:
        require_aware(self.captured_at, "captured_at")
        require_aware(self.received_at, "received_at")
        if not 0 < self.bpm <= 0xFFFF:
            raise ValueError("bpm must fit the positive BLE heart-rate range")
        if not self.source:
            raise ValueError("source is required")
        if any(interval <= 0 for interval in self.rr_intervals_ms):
            raise ValueError("RR intervals must be positive")
        if not self.quality_flags:
            raise ValueError("at least one quality flag is required")


@dataclass(frozen=True)
class CaptureGap:
    started_at: datetime
    ended_at: datetime
    source: str
    reason: str = "disconnect"

    def __post_init__(self) -> None:
        require_aware(self.started_at, "started_at")
        require_aware(self.ended_at, "ended_at")
        if self.ended_at < self.started_at:
            raise ValueError("gap cannot end before it starts")
        if not self.source or not self.reason:
            raise ValueError("gap source and reason are required")


SourceEvent = Union[HeartRateSample, CaptureGap]


class HeartRateSource(Protocol):
    """Common identity shared by live, mock, and aggregate adapters."""

    source_id: str
    capture_mode: CaptureMode


class CaptureHeartRateSource(HeartRateSource, Protocol):
    """A consent-aware source that emits live or deterministic capture events."""

    state: ConnectionState

    def start(self, at: datetime, consent: ConsentState) -> ConnectionState:
        ...

    def read(self, until: datetime) -> Sequence[SourceEvent]:
        ...

    def stop(self, at: datetime) -> Sequence[SourceEvent]:
        ...
