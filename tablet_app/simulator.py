"""Host-side fixture simulator and golden snapshot command."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Mapping, Optional, Sequence, Tuple

from .adapter import (
    MESSAGE_CONFIRM_EMPTY,
    MESSAGE_OPEN,
    MESSAGE_RETRY,
    MESSAGE_STATE,
    MESSAGE_STROKE,
    MESSAGE_SUBMIT,
    MESSAGE_SWIPE,
    FixtureBackend,
    MockPenSource,
    OutboundMessage,
)
from .layout import load_profiles, snapshot_svg


STATES = ("incoming", "reply", "marginalia")
ORIENTATIONS = ("portrait", "landscape")


def run_scenario(name: str) -> Tuple[FixtureBackend, Tuple[str, ...]]:
    outcomes = {
        "complete": ("success",),
        "timeout-retry": ("timeout", "success"),
        "offline": ("offline",),
        "empty": ("success",),
    }[name]
    backend = FixtureBackend(outcomes)
    states = [backend.session.state.value]
    states.append(_last_state(backend.dispatch(MESSAGE_SWIPE, {"direction": "forward"})))

    if name == "empty":
        confirmation = backend.dispatch(MESSAGE_SUBMIT, {"confirm_empty": False})
        states.append(
            "empty_confirmation"
            if confirmation[0].message_type == MESSAGE_CONFIRM_EMPTY
            else "unexpected"
        )
        return backend, tuple(states)

    stroke = MockPenSource.default().next_stroke()
    states.append(_last_state(backend.dispatch(MESSAGE_STROKE, _captured_payload(stroke))))
    submitted = backend.dispatch(MESSAGE_SUBMIT, {"confirm_empty": False})
    states.extend(_message_states(submitted))
    if name == "timeout-retry":
        retried = backend.dispatch(MESSAGE_RETRY)
        states.extend(_message_states(retried))
    return backend, tuple(states)


def generate_snapshots(output_dir: Path) -> Tuple[Path, ...]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for profile_name, profile in load_profiles().items():
        for orientation in ORIENTATIONS:
            for state in STATES:
                payload = snapshot_state(state)
                path = output_dir / f"{profile_name}-{orientation}-{state}.svg"
                path.write_text(snapshot_svg(profile, orientation, payload))
                written.append(path)
    return tuple(written)


def verify_snapshots(output_dir: Path) -> Tuple[str, ...]:
    mismatches = []
    for profile_name, profile in load_profiles().items():
        for orientation in ORIENTATIONS:
            for state in STATES:
                path = output_dir / f"{profile_name}-{orientation}-{state}.svg"
                expected = snapshot_svg(profile, orientation, snapshot_state(state))
                if not path.is_file() or path.read_text() != expected:
                    mismatches.append(str(path))
    return tuple(mismatches)


def snapshot_state(state: str) -> Mapping[str, object]:
    backend = FixtureBackend()
    if state == "incoming":
        return backend.dispatch(MESSAGE_OPEN)[0].payload
    backend.dispatch(MESSAGE_SWIPE, {"direction": "forward"})
    if state == "reply":
        return backend.dispatch(MESSAGE_OPEN)[0].payload
    if state == "marginalia":
        stroke = MockPenSource.default().next_stroke()
        backend.dispatch(MESSAGE_STROKE, _captured_payload(stroke))
        return backend.dispatch(MESSAGE_SUBMIT, {"confirm_empty": False})[-1].payload
    raise ValueError(f"unknown snapshot state: {state}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=tuple(load_profiles()), default="chiappa")
    parser.add_argument("--orientation", choices=ORIENTATIONS, default="portrait")
    parser.add_argument(
        "--scenario",
        choices=("complete", "timeout-retry", "offline", "empty"),
        default="timeout-retry",
    )
    parser.add_argument("--write-snapshots", type=Path)
    parser.add_argument("--verify-snapshots", type=Path)
    arguments = parser.parse_args(argv)

    profile = load_profiles()[arguments.profile]
    width, height = profile.dimensions(arguments.orientation)
    if arguments.write_snapshots:
        paths = generate_snapshots(arguments.write_snapshots)
        print(f"wrote {len(paths)} deterministic fixture snapshots")
        return 0
    if arguments.verify_snapshots:
        mismatches = verify_snapshots(arguments.verify_snapshots)
        if mismatches:
            print(f"snapshot verification failed: {len(mismatches)} mismatch(es)", file=sys.stderr)
            return 1
        print("verified 12 deterministic fixture snapshots")
        return 0

    backend, states = run_scenario(arguments.scenario)
    print(
        "fixture simulator: "
        f"{profile.codename} {arguments.orientation} {width}x{height}; "
        f"scenario={arguments.scenario}; states={' > '.join(states)}; "
        f"synthetic_strokes={len(backend.pen_records)}; network=disabled; hardware=unverified"
    )
    return 0


def _captured_payload(stroke) -> Mapping[str, object]:
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


def _last_state(messages: Sequence[OutboundMessage]) -> str:
    states = _message_states(messages)
    return states[-1]


def _message_states(messages: Sequence[OutboundMessage]) -> Tuple[str, ...]:
    return tuple(
        str(message.payload["state"])
        for message in messages
        if message.message_type == MESSAGE_STATE
    )


if __name__ == "__main__":
    raise SystemExit(main())
