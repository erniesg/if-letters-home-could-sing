"""Fixture-first provider-neutral incoming-letter image pipeline."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

from .raster import RasterError, RasterImage, decode_png, encode_png


ROOT = Path(__file__).resolve().parents[1]
RENDER_PROFILES_PATH = ROOT / "contracts" / "render-profiles.json"
FIXTURE_ASSET_PATH = ROOT / "fixtures" / "generated" / "incoming-qiaopi-001.png"
FIXTURE_SIDECAR_PATH = ROOT / "fixtures" / "generated" / "incoming-qiaopi-001.json"
FICTIONAL_NOTICE = "A fictional letter generated for this encounter"
OPENAI_IMAGE_MODEL = "gpt-image-2"


class PromptPolicyError(ValueError):
    """Raised when a generation prompt violates the fictional-letter policy."""


class ProviderError(RuntimeError):
    """Safe provider failure that does not contain prompts or response bytes."""


class RetryableProviderError(ProviderError):
    """Safe provider failure that may be retried."""


@dataclass(frozen=True)
class LetterImage:
    content: bytes
    media_type: str
    width: int
    height: int
    profile_id: str
    sidecar: Mapping[str, Any]
    status: str
    failure_code: str | None = None


class LetterImageProvider(Protocol):
    def generate(self, *, profile_id: str, prompt: str | None = None) -> LetterImage:
        """Return one fictional letter image without exposing provider credentials."""


class ImageTransport(Protocol):
    def generate(self, payload: Mapping[str, Any], *, timeout_seconds: float) -> Mapping[str, Any]:
        """Send one server-side provider request and return decoded JSON."""


class PromptPolicy:
    """Reject unsafe claims/content and unsupported GPT Image 2 sizes."""

    _accession_id = re.compile(r"\b(?:[A-Za-z]{1,6}[-./])?\d{4}[-./]\d{4,}(?:[-./]\d+)*\b")
    _forbidden = {
        "accession": re.compile(r"\baccession(?:\s+(?:id|number))?\b", re.IGNORECASE),
        "real-name": re.compile(
            r"\b(?:real|actual|living)\s+(?:personal\s+|person(?:'s)?\s+)?name\b",
            re.IGNORECASE,
        ),
        "signature": re.compile(r"\b(?:signature|signed\s+by)\b", re.IGNORECASE),
        "museum-logo": re.compile(
            r"\b(?:museum|archive|company|institutional)\s+(?:logo|wordmark)\b",
            re.IGNORECASE,
        ),
        "authenticity": re.compile(
            r"\b(?:authentic(?:ity)?|genuine\s+(?:archive|archival|historical))\b",
            re.IGNORECASE,
        ),
    }
    _negated = re.compile(
        r"\b(?:no|not|never|without|avoid|exclude|reject|forbid(?:den)?|must\s+not|"
        r"do\s+not|does\s+not|cannot)\b",
        re.IGNORECASE,
    )

    @classmethod
    def validate(
        cls,
        prompt: str,
        *,
        width: int,
        height: int,
        real_person_names: tuple[str, ...] = (),
    ) -> None:
        if not prompt or not prompt.strip():
            raise PromptPolicyError("prompt must not be empty")
        cls.validate_size(width, height)
        if cls._accession_id.search(prompt):
            raise PromptPolicyError("prompt contains an accession-like identifier")
        for name in real_person_names:
            if name.strip() and re.search(re.escape(name.strip()), prompt, re.IGNORECASE):
                raise PromptPolicyError("prompt contains a real person's name")
        clauses = re.split(r"(?<=[.!?;:\n])\s*", prompt)
        for clause in clauses:
            for label, pattern in cls._forbidden.items():
                if pattern.search(clause) and not cls._negated.search(clause):
                    raise PromptPolicyError(f"prompt contains disallowed {label} content")

    @staticmethod
    def validate_size(width: int, height: int) -> None:
        if not isinstance(width, int) or isinstance(width, bool):
            raise PromptPolicyError("image width must be an integer")
        if not isinstance(height, int) or isinstance(height, bool):
            raise PromptPolicyError("image height must be an integer")
        if width <= 0 or height <= 0 or max(width, height) > 3840:
            raise PromptPolicyError("image edges are outside supported bounds")
        if width % 16 or height % 16:
            raise PromptPolicyError("image edges must be divisible by 16")
        if max(width, height) / min(width, height) > 3:
            raise PromptPolicyError("image aspect ratio exceeds 3:1")
        pixels = width * height
        if not 655_360 <= pixels <= 8_294_400:
            raise PromptPolicyError("image pixel count is outside supported bounds")


class FixtureLetterImageProvider:
    """Default offline provider backed by a checked-in fictional fixture."""

    def __init__(
        self,
        asset_path: Path = FIXTURE_ASSET_PATH,
        sidecar_path: Path = FIXTURE_SIDECAR_PATH,
    ) -> None:
        self._asset_path = asset_path
        self._sidecar_path = sidecar_path

    def generate(self, *, profile_id: str, prompt: str | None = None) -> LetterImage:
        _render_profile(profile_id)
        content = self._asset_path.read_bytes()
        sidecar = json.loads(self._sidecar_path.read_text())
        checksum = hashlib.sha256(content).hexdigest()
        if checksum != sidecar["checksums"]["asset_sha256"]:
            raise ProviderError("fixture checksum validation failed")
        try:
            image = decode_png(content)
        except RasterError as error:
            raise ProviderError("fixture image validation failed") from error
        dimensions = sidecar["dimensions"]
        if (image.width, image.height) != (dimensions["width"], dimensions["height"]):
            raise ProviderError("fixture dimensions validation failed")
        if sidecar.get("fictional") is not True or sidecar.get("notice") != FICTIONAL_NOTICE:
            raise ProviderError("fixture fictional provenance validation failed")
        return LetterImage(
            content=content,
            media_type="image/png",
            width=image.width,
            height=image.height,
            profile_id=profile_id,
            sidecar=deepcopy(sidecar),
            status="fixture",
        )


class OpenAIImageProvider:
    """Optional GPT Image 2 adapter; the transport remains server-side."""

    def __init__(
        self,
        transport: ImageTransport,
        *,
        timeout_seconds: float = 120,
        max_attempts: int = 2,
        retry_delay_seconds: float = 0.25,
        clock: Callable[[], datetime] | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if not 1 <= max_attempts <= 3:
            raise ValueError("max_attempts must be between 1 and 3")
        if not 1 <= timeout_seconds <= 180:
            raise ValueError("timeout_seconds must be between 1 and 180")
        if not 0 <= retry_delay_seconds <= 5:
            raise ValueError("retry_delay_seconds must be between 0 and 5")
        self._transport = transport
        self._timeout_seconds = timeout_seconds
        self._max_attempts = max_attempts
        self._retry_delay_seconds = retry_delay_seconds
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._sleeper = sleeper

    def generate(self, *, profile_id: str, prompt: str | None = None) -> LetterImage:
        if prompt is None:
            raise PromptPolicyError("live generation requires a prompt")
        profile = _render_profile(profile_id)
        generation = profile["generation"]
        PromptPolicy.validate(prompt, width=generation["width"], height=generation["height"])
        payload = {
            "model": OPENAI_IMAGE_MODEL,
            "prompt": prompt,
            "size": f'{generation["width"]}x{generation["height"]}',
            "quality": "medium",
            "output_format": "png",
            "n": 1,
        }
        response = self._request(payload)
        source, source_content = _response_image(response)
        if (source.width, source.height) != (generation["width"], generation["height"]):
            raise ProviderError("provider image dimensions do not match the requested profile")
        rendered = transform_for_profile(source, profile_id)
        content = encode_png(rendered)
        generated_at = self._clock().astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        sidecar: dict[str, Any] = {
            "schema_version": "1",
            "fixture_id": None,
            "fictional": True,
            "notice": FICTIONAL_NOTICE,
            "prompt": prompt,
            "provider": "openai",
            "model": OPENAI_IMAGE_MODEL,
            "timestamps": {"generated_at": generated_at},
            "source": {
                "dimensions": {"width": source.width, "height": source.height},
                "sha256": hashlib.sha256(source_content).hexdigest(),
            },
            "rendered": {
                "profile_id": profile_id,
                "dimensions": {"width": rendered.width, "height": rendered.height},
                "sha256": hashlib.sha256(content).hexdigest(),
                "transform": deepcopy(profile["transform"]),
            },
            "provenance": {
                "kind": "generated",
                "archival_source": False,
                "provider_asset_id": _provider_asset_id(response),
            },
        }
        usage = _numeric_metadata(response.get("usage"))
        cost = _numeric_metadata(response.get("cost"))
        if usage is not None:
            sidecar["usage"] = usage
        if cost is not None:
            sidecar["cost"] = cost
        return LetterImage(
            content=content,
            media_type="image/png",
            width=rendered.width,
            height=rendered.height,
            profile_id=profile_id,
            sidecar=sidecar,
            status="generated",
        )

    def _request(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        for attempt in range(self._max_attempts):
            try:
                response = self._transport.generate(payload, timeout_seconds=self._timeout_seconds)
                if not isinstance(response, Mapping):
                    raise ProviderError("provider returned an invalid response")
                return response
            except (RetryableProviderError, TimeoutError, ConnectionError) as error:
                if attempt + 1 == self._max_attempts:
                    raise ProviderError("provider unavailable after bounded retries") from error
                if self._retry_delay_seconds:
                    self._sleeper(self._retry_delay_seconds)
            except ProviderError:
                raise
            except Exception as error:
                raise ProviderError("provider request failed") from error
        raise ProviderError("provider request failed")


class OpenAIHTTPTransport:
    """Minimal standard-library Image API transport for trusted gateway use."""

    endpoint = "https://api.openai.com/v1/images/generations"
    max_response_bytes = 50 * 1024 * 1024

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ProviderError("live image provider credential is unavailable")
        self._api_key = api_key

    def generate(self, payload: Mapping[str, Any], *, timeout_seconds: float) -> Mapping[str, Any]:
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(dict(payload)).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                body = response.read(self.max_response_bytes + 1)
        except urllib.error.HTTPError as error:
            if error.code == 429 or error.code >= 500:
                raise RetryableProviderError("transient provider HTTP failure") from error
            raise ProviderError("provider rejected the image request") from error
        except (urllib.error.URLError, TimeoutError) as error:
            raise RetryableProviderError("provider connection failed") from error
        if len(body) > self.max_response_bytes:
            raise ProviderError("provider response exceeded the size limit")
        try:
            decoded = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ProviderError("provider returned invalid JSON") from error
        if not isinstance(decoded, Mapping):
            raise ProviderError("provider returned an invalid response")
        return decoded


class FallbackLetterImageProvider:
    """Return the fixture with a safe UI state when live generation fails."""

    def __init__(
        self,
        primary: LetterImageProvider,
        fallback: LetterImageProvider | None = None,
    ) -> None:
        self._primary = primary
        self._fallback = fallback or FixtureLetterImageProvider()

    def generate(self, *, profile_id: str, prompt: str | None = None) -> LetterImage:
        try:
            return self._primary.generate(profile_id=profile_id, prompt=prompt)
        except PromptPolicyError:
            fixture = self._fallback.generate(profile_id=profile_id)
            return replace(fixture, status="fixture-fallback", failure_code="prompt-policy")
        except ProviderError:
            fixture = self._fallback.generate(profile_id=profile_id)
            return replace(fixture, status="fixture-fallback", failure_code="provider-error")


def build_letter_image_provider(
    *,
    live_enabled: bool = False,
    transport: ImageTransport | None = None,
) -> LetterImageProvider:
    """Keep fixture behavior as the explicit default, even when a key exists."""
    fixture = FixtureLetterImageProvider()
    if not live_enabled:
        return fixture
    active_transport = transport
    if active_transport is None:
        active_transport = OpenAIHTTPTransport(os.environ.get("OPENAI_API_KEY", ""))
    return FallbackLetterImageProvider(OpenAIImageProvider(active_transport), fixture)


def transform_for_profile(image: RasterImage, profile_id: str) -> RasterImage:
    profile = _render_profile(profile_id)
    generation = profile["generation"]
    native = profile["native_landscape"]
    transform = profile["transform"]
    if (image.width, image.height) != (generation["width"], generation["height"]):
        raise RasterError("source dimensions do not match the render profile")
    if transform["left"] or transform["right"]:
        raise RasterError("only the version-pinned vertical transforms are supported")
    row_bytes = image.width * 3
    if transform["kind"] == "pad":
        first = image.pixels[:row_bytes]
        last = image.pixels[-row_bytes:]
        pixels = first * transform["top"] + image.pixels + last * transform["bottom"]
    elif transform["kind"] == "crop":
        start = transform["top"] * row_bytes
        end = len(image.pixels) - transform["bottom"] * row_bytes
        pixels = image.pixels[start:end]
    else:
        raise RasterError("render profile uses an unknown transform")
    return RasterImage(native["width"], native["height"], pixels)


def _render_profile(profile_id: str) -> Mapping[str, Any]:
    profiles = json.loads(RENDER_PROFILES_PATH.read_text())["profiles"]
    try:
        return profiles[profile_id]
    except KeyError as error:
        raise ValueError(f"unknown render profile: {profile_id}") from error


def _response_image(response: Mapping[str, Any]) -> tuple[RasterImage, bytes]:
    try:
        encoded = response["data"][0]["b64_json"]
        if not isinstance(encoded, str):
            raise TypeError
        content = base64.b64decode(encoded, validate=True)
        return decode_png(content), content
    except (KeyError, IndexError, TypeError, ValueError, RasterError) as error:
        raise ProviderError("provider returned an invalid image") from error


def _provider_asset_id(response: Mapping[str, Any]) -> str | None:
    candidate = response.get("id")
    if not isinstance(candidate, str):
        try:
            candidate = response["data"][0].get("id")
        except (KeyError, IndexError, AttributeError, TypeError):
            return None
    if not candidate or len(candidate) > 200 or re.search(r"[\x00-\x1f\x7f]", candidate):
        return None
    return candidate


def _numeric_metadata(value: Any) -> Any:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, Mapping):
        result = {
            str(key): safe_value
            for key, item in value.items()
            if (safe_value := _numeric_metadata(item)) is not None
        }
        return result or None
    return None
