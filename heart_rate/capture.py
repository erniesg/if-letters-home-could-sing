"""Atomic first-accepted-ink through submit capture boundary."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from threading import RLock

from .models import (
    CaptureGap,
    CaptureHeartRateSource,
    ConnectionState,
    ConsentState,
    HeartRateSample,
    SourceEvent,
    require_aware,
)


class SampleDisposition(str, Enum):
    ACCEPTED = "accepted"
    BEFORE_FIRST_INK = "before-first-ink"
    AFTER_SUBMIT = "after-submit"


@dataclass(frozen=True)
class CaptureSummary:
    consent: ConsentState
    connection_state: ConnectionState
    sample_count: int
    gap_count: int
    reconnect_count: int
    gap_duration_ms: int
    rejected_before_first_ink: int
    rejected_after_submit: int
    quality_counts: tuple[tuple[str, int], ...]
    sample_loss_observed: bool
    clock_offset_assumption: str = (
        "source and gateway clocks are retained independently; no offset correction or interpolation"
    )


class HeartRateCapture:
    """Serializes stroke, sample, and submit events under one lock."""

    def __init__(self, source: CaptureHeartRateSource, consent: ConsentState):
        self.source = source
        self.consent = consent
        self.first_ink_at: datetime | None = None
        self.submitted_at: datetime | None = None
        self.samples: list[HeartRateSample] = []
        self.gaps: list[CaptureGap] = []
        self._rejected_before = 0
        self._rejected_after = 0
        self._lock = RLock()

    def accepted_stroke(self, at: datetime, *, accepted: bool = True) -> bool:
        """Open capture exactly once; rejected pen input has no effect."""
        require_aware(at, "at")
        if not accepted:
            return False
        with self._lock:
            if self.submitted_at is not None:
                raise RuntimeError("reply is already submitted")
            if self.first_ink_at is not None:
                return False
            self.first_ink_at = at
            self.source.start(at, self.consent)
            return True

    def collect(self, until: datetime) -> int:
        """Pull deterministic source events through ``until`` while capture is open."""
        require_aware(until, "until")
        with self._lock:
            if self.first_ink_at is None or self.submitted_at is not None:
                return 0
            before = len(self.samples)
            for event in self.source.read(until):
                self._apply_event(event)
            return len(self.samples) - before

    def ingest_sample(self, sample: HeartRateSample) -> SampleDisposition:
        """Accept a relay sample only while the atomic capture window is open."""
        with self._lock:
            return self._ingest_sample(sample)

    def submit(self, at: datetime) -> CaptureSummary:
        """Close capture and source atomically; repeated submit is idempotent."""
        require_aware(at, "at")
        with self._lock:
            if self.submitted_at is not None:
                return self.summary()
            if self.first_ink_at is not None and at < self.first_ink_at:
                raise ValueError("submit cannot precede first ink")
            if self.first_ink_at is not None:
                final_events = self.source.stop(at)
                for event in final_events:
                    if isinstance(event, HeartRateSample):
                        if event.captured_at <= at:
                            self._ingest_sample(event)
                        else:
                            self._rejected_after += 1
                    elif event.started_at <= at:
                        self._apply_event(
                            CaptureGap(
                                started_at=event.started_at,
                                ended_at=min(event.ended_at, at),
                                source=event.source,
                                reason=event.reason,
                            )
                        )
            self.submitted_at = at
            return self.summary()

    def summary(self) -> CaptureSummary:
        with self._lock:
            quality = Counter(flag for sample in self.samples for flag in sample.quality_flags)
            gap_duration_ms = round(
                sum((gap.ended_at - gap.started_at).total_seconds() * 1000 for gap in self.gaps)
            )
            if self.submitted_at is None:
                reconnect_count = len(self.gaps)
            else:
                reconnect_count = sum(gap.ended_at < self.submitted_at for gap in self.gaps)
            return CaptureSummary(
                consent=self.consent,
                connection_state=self.source.state,
                sample_count=len(self.samples),
                gap_count=len(self.gaps),
                reconnect_count=reconnect_count,
                gap_duration_ms=gap_duration_ms,
                rejected_before_first_ink=self._rejected_before,
                rejected_after_submit=self._rejected_after,
                quality_counts=tuple(sorted(quality.items())),
                sample_loss_observed=bool(self.gaps),
            )

    def _apply_event(self, event: SourceEvent) -> None:
        if isinstance(event, HeartRateSample):
            self._ingest_sample(event)
            return
        if self.first_ink_at is None:
            return
        start = max(event.started_at, self.first_ink_at)
        end = event.ended_at
        if self.submitted_at is not None:
            end = min(end, self.submitted_at)
        if end >= start:
            self.gaps.append(
                CaptureGap(started_at=start, ended_at=end, source=event.source, reason=event.reason)
            )

    def _ingest_sample(self, sample: HeartRateSample) -> SampleDisposition:
        if self.first_ink_at is None or sample.captured_at < self.first_ink_at:
            self._rejected_before += 1
            return SampleDisposition.BEFORE_FIRST_INK
        if self.submitted_at is not None:
            self._rejected_after += 1
            return SampleDisposition.AFTER_SUBMIT
        self.samples.append(sample)
        return SampleDisposition.ACCEPTED
