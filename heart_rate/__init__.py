"""Consented heart-rate capture adapters."""

from .ble import (
    BlePacketError,
    BleRelayClient,
    BleRelayHeartRateSource,
    HeartRateMeasurement,
    parse_heart_rate_measurement,
)
from .capture import CaptureSummary, HeartRateCapture, SampleDisposition
from .mock import MockEvent, MockEventKind, MockHeartRateSource
from .models import (
    CaptureGap,
    CaptureHeartRateSource,
    CaptureMode,
    ConnectionState,
    ConsentState,
    HeartRateSample,
    HeartRateSource,
)
from .whoop import (
    ConsentRequired,
    HttpRequest,
    IntegrationDisabled,
    ServerOAuthConfig,
    WhoopAggregateSource,
    WhoopProviderError,
)

__all__ = [
    "BlePacketError",
    "BleRelayClient",
    "BleRelayHeartRateSource",
    "CaptureGap",
    "CaptureHeartRateSource",
    "CaptureMode",
    "CaptureSummary",
    "ConnectionState",
    "ConsentRequired",
    "ConsentState",
    "HeartRateCapture",
    "HeartRateMeasurement",
    "HeartRateSample",
    "HeartRateSource",
    "HttpRequest",
    "IntegrationDisabled",
    "MockEvent",
    "MockEventKind",
    "MockHeartRateSource",
    "SampleDisposition",
    "ServerOAuthConfig",
    "WhoopAggregateSource",
    "WhoopProviderError",
    "parse_heart_rate_measurement",
]
