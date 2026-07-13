import base64
import hashlib
import json
import os
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from letter_image import (
    FICTIONAL_NOTICE,
    FallbackLetterImageProvider,
    FixtureLetterImageProvider,
    OpenAIImageProvider,
    PromptPolicy,
    PromptPolicyError,
    RasterImage,
    build_letter_image_provider,
    decode_png,
    encode_png,
    transform_for_profile,
)


ROOT = Path(__file__).resolve().parents[1]
PROFILES = json.loads((ROOT / "contracts" / "render-profiles.json").read_text())["profiles"]
SAFE_PROMPT = (
    "Create a fictional family letter on warm paper. Do not use real names, signatures, "
    "museum logos, accession numbers, or authenticity claims."
)


def profile_raster(profile_id):
    generation = PROFILES[profile_id]["generation"]
    width, height = generation["width"], generation["height"]
    pixels = b"".join(
        bytes((row % 251, (row * 3) % 251, (row * 7) % 251)) * width
        for row in range(height)
    )
    return RasterImage(width, height, pixels)


class FixtureProviderTests(unittest.TestCase):
    def test_fixture_is_the_default_even_when_a_key_exists(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "unused-test-value"}):
            provider = build_letter_image_provider()
        self.assertIsInstance(provider, FixtureLetterImageProvider)

    def test_fixture_sidecar_is_complete_and_matches_the_asset(self):
        result = FixtureLetterImageProvider().generate(profile_id="chiappa_3.28.0.162")
        sidecar = result.sidecar
        self.assertEqual(result.status, "fixture")
        self.assertTrue(sidecar["fictional"])
        self.assertEqual(sidecar["notice"], FICTIONAL_NOTICE)
        self.assertTrue(sidecar["prompt"])
        self.assertTrue(sidecar["provider"])
        self.assertTrue(sidecar["model"])
        self.assertIn("generated_at", sidecar["timestamps"])
        self.assertEqual(
            sidecar["checksums"]["asset_sha256"], hashlib.sha256(result.content).hexdigest()
        )
        prompt_file = ROOT / sidecar["provenance"]["prompt_file"]
        self.assertEqual(
            sidecar["checksums"]["prompt_file_sha256"],
            hashlib.sha256(prompt_file.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            sidecar["checksums"]["prompt_sha256"],
            hashlib.sha256(sidecar["prompt"].encode()).hexdigest(),
        )
        self.assertEqual((result.width, result.height), (1086, 1448))
        self.assertFalse(sidecar["provenance"]["archival_source"])


class PromptPolicyTests(unittest.TestCase):
    def test_approved_fixture_prompt_and_render_sizes_are_allowed(self):
        sidecar = json.loads(
            (ROOT / "fixtures" / "generated" / "incoming-qiaopi-001.json").read_text()
        )
        for profile in PROFILES.values():
            PromptPolicy.validate(sidecar["prompt"], **profile["generation"])

    def test_disallowed_archival_claims_and_identity_markers_are_rejected(self):
        prompts = (
            "Reproduce museum accession 2000-06963-001 exactly.",
            "Copy the signature of the original writer.",
            "Place the museum logo in the upper corner.",
            "Claim that this is an authentic archival letter.",
            "Use the real personal name of the donor.",
        )
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                with self.assertRaises(PromptPolicyError):
                    PromptPolicy.validate(prompt, width=1696, height=960)
        with self.assertRaises(PromptPolicyError):
            PromptPolicy.validate(
                "Write a warm letter signed by Lim Foo.",
                width=1696,
                height=960,
                real_person_names=("Lim Foo",),
            )

    def test_unsupported_model_sizes_are_rejected(self):
        invalid_sizes = ((1023, 1024), (4096, 1024), (3840, 1024), (512, 512))
        for width, height in invalid_sizes:
            with self.subTest(size=(width, height)):
                with self.assertRaises(PromptPolicyError):
                    PromptPolicy.validate(SAFE_PROMPT, width=width, height=height)


class RenderTransformTests(unittest.TestCase):
    def test_chiappa_golden_padding_preserves_edge_pixels(self):
        source = profile_raster("chiappa_3.28.0.162")
        rendered = transform_for_profile(source, "chiappa_3.28.0.162")
        self.assertEqual((rendered.width, rendered.height), (2160, 1620))
        self.assertEqual(rendered.pixel(0, 0), source.pixel(0, 0))
        self.assertEqual(rendered.pixel(0, 1), source.pixel(0, 0))
        self.assertEqual(rendered.pixel(0, 2), source.pixel(0, 0))
        self.assertEqual(rendered.pixel(0, 1617), source.pixel(0, 1615))
        self.assertEqual(rendered.pixel(0, 1619), source.pixel(0, 1615))
        self.assertEqual(
            hashlib.sha256(rendered.pixels).hexdigest(),
            "c4d2517dff3713c1d8cffe9b453dd932aa68af3f71d9d3871c00d06cb1e56fb5",
        )

    def test_ferrari_golden_crop_removes_three_rows_per_edge(self):
        source = profile_raster("ferrari_3.28.0.162")
        rendered = transform_for_profile(source, "ferrari_3.28.0.162")
        self.assertEqual((rendered.width, rendered.height), (1696, 954))
        self.assertEqual(rendered.pixel(0, 0), source.pixel(0, 3))
        self.assertEqual(rendered.pixel(0, 953), source.pixel(0, 956))
        self.assertEqual(
            hashlib.sha256(rendered.pixels).hexdigest(),
            "9eea44df19ffbce0d9aabae729898239c2b756d958430c224b9d7d5661487767",
        )

    def test_png_round_trip_preserves_pixels(self):
        source = RasterImage(2, 2, bytes(range(12)))
        self.assertEqual(decode_png(encode_png(source)), source)


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def generate(self, payload, *, timeout_seconds):
        self.calls.append((dict(payload), timeout_seconds))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class OpenAIAdapterTests(unittest.TestCase):
    def test_adapter_requests_gpt_image_2_and_records_redacted_metadata(self):
        source = profile_raster("ferrari_3.28.0.162")
        response = {
            "id": "image_fixture_001",
            "data": [{"b64_json": base64.b64encode(encode_png(source)).decode("ascii")}],
            "usage": {
                "input_tokens": 101,
                "output_tokens": 202,
                "details": {"image_tokens": 202},
                "ignored_text": "provider payload must not be copied",
            },
            "cost": {"estimated_usd": 0.123, "currency": "ignored"},
        }
        transport = FakeTransport([response])
        provider = OpenAIImageProvider(
            transport,
            timeout_seconds=90,
            retry_delay_seconds=0,
            clock=lambda: datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc),
        )

        result = provider.generate(profile_id="ferrari_3.28.0.162", prompt=SAFE_PROMPT)

        payload, timeout = transport.calls[0]
        self.assertEqual(payload["model"], "gpt-image-2")
        self.assertEqual(payload["size"], "1696x960")
        self.assertEqual(payload["output_format"], "png")
        self.assertEqual(timeout, 90)
        self.assertEqual((result.width, result.height), (1696, 954))
        self.assertEqual(result.status, "generated")
        self.assertEqual(result.sidecar["usage"]["input_tokens"], 101)
        self.assertEqual(result.sidecar["cost"], {"estimated_usd": 0.123})
        self.assertNotIn("ignored_text", result.sidecar["usage"])
        self.assertNotIn("currency", result.sidecar["cost"])
        self.assertEqual(result.sidecar["timestamps"]["generated_at"], "2026-07-13T12:00:00Z")
        self.assertEqual(
            result.sidecar["source"]["sha256"],
            hashlib.sha256(base64.b64decode(response["data"][0]["b64_json"])).hexdigest(),
        )
        self.assertEqual(
            result.sidecar["rendered"]["sha256"], hashlib.sha256(result.content).hexdigest()
        )

    def test_transient_failure_retries_are_bounded_then_return_fixture(self):
        transport = FakeTransport([TimeoutError(), TimeoutError(), AssertionError("third call")])
        live = OpenAIImageProvider(transport, max_attempts=2, retry_delay_seconds=0)
        provider = FallbackLetterImageProvider(live)

        result = provider.generate(profile_id="chiappa_3.28.0.162", prompt=SAFE_PROMPT)

        self.assertEqual(len(transport.calls), 2)
        self.assertEqual(result.status, "fixture-fallback")
        self.assertEqual(result.failure_code, "provider-error")
        self.assertEqual(result.sidecar["fixture_id"], "incoming-qiaopi-001")

    def test_policy_rejection_fails_closed_without_a_live_request(self):
        transport = FakeTransport([AssertionError("must not be called")])
        provider = FallbackLetterImageProvider(
            OpenAIImageProvider(transport, retry_delay_seconds=0)
        )

        result = provider.generate(
            profile_id="ferrari_3.28.0.162",
            prompt="Copy museum accession 2000-06963-001 and its signature.",
        )

        self.assertEqual(transport.calls, [])
        self.assertEqual(result.status, "fixture-fallback")
        self.assertEqual(result.failure_code, "prompt-policy")


if __name__ == "__main__":
    unittest.main()
