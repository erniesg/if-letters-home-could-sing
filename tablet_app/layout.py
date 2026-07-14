"""Deterministic layout model and dependency-free SVG golden renderer."""

from __future__ import annotations

import json
import math
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Tuple
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
PROFILES_PATH = ROOT / "contracts" / "render-profiles.json"
PAPER = "#f1e8d5"
INK = "#2f2923"
MUTED_RED = "#74362f"
MIN_TOUCH_TARGET = 96


@dataclass(frozen=True)
class DeviceProfile:
    profile_id: str
    codename: str
    landscape_width: int
    landscape_height: int

    def dimensions(self, orientation: str) -> Tuple[int, int]:
        if orientation == "landscape":
            return self.landscape_width, self.landscape_height
        if orientation == "portrait":
            return self.landscape_height, self.landscape_width
        raise ValueError("orientation must be portrait or landscape")


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class Layout:
    width: int
    height: int
    header: Rect
    page: Rect
    footer: Rect
    primary_action: Rect


def load_profiles() -> Mapping[str, DeviceProfile]:
    source = json.loads(PROFILES_PATH.read_text())
    profiles = {}
    for profile_id, item in source["profiles"].items():
        native = item["native_landscape"]
        profiles[item["codename"].lower()] = DeviceProfile(
            profile_id=profile_id,
            codename=item["codename"],
            landscape_width=native["width"],
            landscape_height=native["height"],
        )
    return profiles


def make_layout(profile: DeviceProfile, orientation: str) -> Layout:
    width, height = profile.dimensions(orientation)
    margin = max(28, round(min(width, height) * 0.035))
    header_height = max(MIN_TOUCH_TARGET, round(height * 0.075))
    footer_height = max(128, round(height * 0.10))
    page = Rect(
        x=margin,
        y=header_height + margin,
        width=width - margin * 2,
        height=height - header_height - footer_height - margin * 2,
    )
    action_width = min(480, max(280, round(width * 0.26)))
    action_height = MIN_TOUCH_TARGET
    footer = Rect(0, height - footer_height, width, footer_height)
    action = Rect(
        x=width - margin - action_width,
        y=footer.y + (footer.height - action_height) // 2,
        width=action_width,
        height=action_height,
    )
    return Layout(
        width=width,
        height=height,
        header=Rect(0, 0, width, header_height),
        page=page,
        footer=footer,
        primary_action=action,
    )


def contrast_ratio(foreground: str, background: str) -> float:
    bright = max(_relative_luminance(foreground), _relative_luminance(background))
    dark = min(_relative_luminance(foreground), _relative_luminance(background))
    return (bright + 0.05) / (dark + 0.05)


def wrap_translation(text: str, width_px: int, font_px: int) -> Tuple[str, ...]:
    """Conservative host assertion for wrapped, non-elided translations."""

    if width_px <= 0 or font_px <= 0:
        raise ValueError("text bounds and font size must be positive")
    characters = max(1, math.floor(width_px / (font_px * 0.62)))
    return tuple(
        textwrap.wrap(
            text,
            width=characters,
            break_long_words=True,
            break_on_hyphens=False,
        )
        or ("",)
    )


def layer_model(
    state_payload: Mapping[str, object],
    *,
    show_stationery: bool = True,
    show_ink: bool = True,
    show_marginalia: bool = True,
) -> Mapping[str, Mapping[str, object]]:
    state = str(state_payload["state"])
    return {
        "stationery": {
            "visible": show_stationery and state != "incoming",
            "fixture": "blank-huipi",
        },
        "ink": {
            "visible": show_ink and state != "incoming",
            "strokes": tuple(state_payload.get("strokes", ())),
        },
        "marginalia": {
            "visible": show_marginalia and state == "marginalia",
            "annotations": tuple(state_payload.get("annotations", ())),
        },
    }


def snapshot_svg(
    profile: DeviceProfile,
    orientation: str,
    state_payload: Mapping[str, object],
) -> str:
    layout = make_layout(profile, orientation)
    state = str(state_payload["state"])
    layers = layer_model(state_payload)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{layout.width}" '
        f'height="{layout.height}" viewBox="0 0 {layout.width} {layout.height}">',
        f'<rect width="{layout.width}" height="{layout.height}" fill="{PAPER}"/>',
        f'<rect width="{layout.header.width}" height="{layout.header.height}" fill="#e5d9c2"/>',
        _text(42, layout.header.height // 2 + 16, _state_title(state), 44),
        _text(layout.width - 42, layout.header.height // 2 + 13, profile.codename, 32, "end"),
        f'<rect x="{layout.page.x}" y="{layout.page.y}" width="{layout.page.width}" '
        f'height="{layout.page.height}" rx="8" fill="#f6efdf" stroke="#8d7964" stroke-width="3"/>',
    ]
    if state == "incoming":
        parts.extend(_incoming_layer(layout.page))
    else:
        parts.extend(
            _stationery_layer(
                layout.page,
                bool(layers["stationery"]["visible"]),
                8 if profile.codename == "Ferrari" else 12,
            )
        )
        parts.extend(_ink_layer(layout.page, layers["ink"]))
        parts.extend(_marginalia_layer(layout.page, layers["marginalia"]))
    parts.extend(_footer(layout, state, state_payload.get("errorCode")))
    parts.append("</svg>\n")
    return "\n".join(parts)


def _incoming_layer(page: Rect) -> Tuple[str, ...]:
    image_height = round(page.height * 0.72)
    image_width = round(image_height * 0.75)
    if image_width > page.width * 0.72:
        image_width = round(page.width * 0.72)
        image_height = round(image_width / 0.75)
    image_x = page.x + (page.width - image_width) // 2
    image_y = page.y + round(page.height * 0.06)
    return (
        '<g id="incoming-layer">',
        f'<image href="../../fixtures/generated/incoming-qiaopi-001.png" x="{image_x}" '
        f'y="{image_y}" width="{image_width}" height="{image_height}" preserveAspectRatio="xMidYMid meet"/>',
        _text(
            page.x + page.width // 2,
            page.y + page.height - 54,
            "A fictional letter generated for this encounter",
            34,
            "middle",
        ),
        "</g>",
    )


def _stationery_layer(page: Rect, visible: bool, guide_columns: int) -> Tuple[str, ...]:
    if not visible:
        return ('<g id="stationery-layer" visibility="hidden"/>',)
    inset = max(36, round(min(page.width, page.height) * 0.065))
    left, top = page.x + inset, page.y + inset
    right, bottom = page.x + page.width - inset, page.y + page.height - inset
    lines = [
        '<g id="stationery-layer">',
        f'<rect x="{left}" y="{top}" width="{right-left}" height="{bottom-top}" '
        f'fill="none" stroke="#a45149" stroke-width="3" opacity="0.62"/>',
        f'<path d="M {page.x + page.width // 2} {page.y} V {page.y + page.height}" '
        f'stroke="#796d5e" stroke-width="2" opacity="0.10"/>',
        f'<path d="M {page.x} {page.y + page.height // 2} H {page.x + page.width}" '
        f'stroke="#796d5e" stroke-width="2" opacity="0.10"/>',
    ]
    for index in range(1, guide_columns + 1):
        x = left + round((right - left) * index / (guide_columns + 1))
        lines.append(
            f'<path d="M {x} {top} V {bottom}" stroke="#a45149" stroke-width="2" opacity="0.24"/>'
        )
    for position in (0.10, 0.90):
        y = top + round((bottom - top) * position)
        lines.append(
            f'<path d="M {left} {y} H {right}" stroke="#a45149" stroke-width="2" opacity="0.22"/>'
        )
    lines.append("</g>")
    return tuple(lines)


def _ink_layer(page: Rect, layer: Mapping[str, object]) -> Tuple[str, ...]:
    if not layer["visible"]:
        return ('<g id="ink-layer" visibility="hidden"/>',)
    paths = ['<g id="ink-layer" fill="none" stroke="#33475b" stroke-linecap="round">']
    for stroke in layer["strokes"]:
        points = stroke["points"]
        coordinates = [
            (
                page.x + round(float(point["x"]) * page.width),
                page.y + round(float(point["y"]) * page.height),
            )
            for point in points
        ]
        path = " ".join(
            ("M" if index == 0 else "L") + f" {x} {y}"
            for index, (x, y) in enumerate(coordinates)
        )
        pressure = sum(float(point["pressure"]) for point in points) / len(points)
        paths.append(f'<path d="{path}" stroke-width="{max(3, round(pressure * 10))}"/>')
    paths.append("</g>")
    return tuple(paths)


def _marginalia_layer(page: Rect, layer: Mapping[str, object]) -> Tuple[str, ...]:
    if not layer["visible"]:
        return ('<g id="marginalia-layer" visibility="hidden"/>',)
    parts = ['<g id="marginalia-layer">']
    for annotation in layer["annotations"]:
        anchor = annotation["anchor"]
        x = page.x + round(float(anchor["x"]) * page.width)
        y = page.y + round(float(anchor["y"]) * page.height)
        width = max(8, round(float(anchor["width"]) * page.width))
        height = max(8, round(float(anchor["height"]) * page.height))
        parts.append(
            f'<rect x="{x}" y="{y}" width="{width}" height="{height}" fill="none" '
            f'stroke="{MUTED_RED}" stroke-width="5" stroke-dasharray="10 8"/>'
        )
        parts.append(_text(x, max(page.y + 30, y - 14), str(annotation["message"]), 25))
    parts.append("</g>")
    return tuple(parts)


def _footer(layout: Layout, state: str, error_code: object) -> Tuple[str, ...]:
    action = layout.primary_action
    label = {
        "incoming": "Swipe forward",
        "reply": "Submit huipi",
        "submitting": "Reading your reply…",
        "submission_error": "Retry offline submission",
        "review_error": "Retry review",
        "marginalia": "Hide notes",
    }.get(state, "Continue")
    status = "Heart rate unavailable — reply is still available"
    if error_code == "gateway_offline":
        status = "Offline — your ink is safe on this page"
    return (
        f'<g id="controls-layer" data-min-touch-target="{MIN_TOUCH_TARGET}">',
        f'<rect x="{action.x}" y="{action.y}" width="{action.width}" height="{action.height}" '
        f'rx="10" fill="{INK}" data-touch-target="true"/>',
        _text(action.x + action.width // 2, action.y + 61, label, 30, "middle", "#fffaf0"),
        _text(42, layout.footer.y + layout.footer.height // 2 + 12, status, 27),
        "</g>",
    )


def _state_title(state: str) -> str:
    return {
        "incoming": "Incoming letter",
        "reply": "Your huipi",
        "submitting": "Preparing marginalia",
        "submission_error": "Reply saved",
        "review_error": "Reply saved",
        "marginalia": "A reading of your reply",
    }.get(state, state)


def _text(
    x: int,
    y: int,
    value: str,
    size: int,
    anchor: str = "start",
    fill: str = INK,
) -> str:
    return (
        f'<text x="{x}" y="{y}" fill="{fill}" font-family="sans-serif" '
        f'font-size="{size}" text-anchor="{anchor}">{escape(value)}</text>'
    )


def _relative_luminance(color: str) -> float:
    value = color.removeprefix("#")
    if len(value) != 6:
        raise ValueError("colours must use six-digit hex notation")
    channels = [int(value[index : index + 2], 16) / 255 for index in (0, 2, 4)]
    linear = [
        channel / 12.92
        if channel <= 0.04045
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
