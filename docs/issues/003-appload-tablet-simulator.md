# Build the AppLoad three-page UI and host simulator

depends-on: 002

## Goal

Build a restrained Qt Quick/AppLoad frontend for both tablet aspect ratios, backed by deterministic fixture adapters and runnable in a host-side simulator before any physical installation.

## Acceptance tests

- AppLoad manifest, QML frontend, and backend/socket boundary follow the maintained AppLoad example contract.
- Page 1 renders the fictional incoming fixture plus an accessible provenance disclosure.
- A forward swipe opens a low-distraction blank huipi canvas; back/forward navigation preserves strokes.
- A mock pen source records pressure/time/coordinates and makes the first-stroke event visible to the state core.
- Submit shows progress, handles deterministic timeout/retry, and renders structured mock annotations on page 3 without changing the ink layer.
- Layout snapshots exist for Chiappa `2160×1620` and Ferrari `1696×954` in portrait and landscape where supported.
- Touch targets, contrast, long translations, empty states, and offline states have automated assertions.
- The host simulator launches from a documented command with no tablet, network, private data, or secret.

## Validation command

```bash
scripts/agent-evidence
```

## Allowed secrets

None. Use checked-in synthetic letter, stroke, review, and heart-rate fixtures.

## Artifact outputs

- AppLoad application directory with manifest, QML, and backend adapter.
- Host simulator and deterministic screenshot/snapshot artifacts.
- UI/state integration tests.
- Evidence manifest under `.agent/evidence/`.

## Stop conditions

Stop if host rendering cannot match the device Qt version closely enough to make a claim about pen latency or hardware input. Continue with layout/state fixtures and mark hardware assertions pending.

## Human clarification protocol

Ask only for a visual direction decision that cannot be answered by the product brief. Default to the quieter, more legible treatment.

## Recommended response

Use a thin QML UI over the experience core and keep all provider behaviour behind local socket messages so the simulator and device share fixtures.

## Trade-offs

Snapshot tests cannot prove colour e-ink refresh or marker latency, but they catch layout/state regressions before scarce hardware trials.

## Free-form response

List any Qt/AppLoad API whose hardware behaviour remains unverified.
