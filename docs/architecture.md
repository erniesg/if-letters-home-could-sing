# Technical architecture

## Decision

Open each encounter as a native PDF document in Xochitl's stock `DocumentView`.
Two exact-resource QMLDiff actions are the only device-specific UI: the main
sidebar entry starts a packet through the paired Mac, and one page-2 action
submits the huipi. The experience does not open an AppLoad window and does not
replace the stock document toolbar, close action, pen controls, or gestures.

The paired Mac uses reMarkable's enabled USB web interface to import the initial
PDF and export the participant-annotated PDF. It never merges files into the
live Xochitl document store. This keeps drawing and navigation native while
preserving an exact-resource rollback boundary.

```mermaid
flowchart LR
    A["Main Xochitl hamburger sidebar"] -->|"Letters Home entry"| B["QMLDiff launcher patch"]
    B -->|"USB-private HTTP"| C["Paired Mac bridge"]
    C --> D["Persisted Codex incoming task"]
    D --> E["Streamed Chinese text deltas"]
    C -->|"official USB import"| F["Native two-page paper packet"]
    F --> G["Stock Xochitl DocumentView"]
    G -->|"page 2 submit + USB export"| C
    C --> H["Persisted Codex review task"]
    H --> I["Grounded review + response letter"]
    C -->|"append marked copy + response and USB import"| G
    J["Phone / edge WHOOP BLE bridge"] -->|"future live HR samples"| C
```

## Components

### 1. Main-sidebar launcher

- QMLDiff patch against exact, hashed Xochitl/QRR resources for Ferrari and Chiappa on OS `3.28.0.162`.
- Adds one envelope-labelled sidebar item immediately below `Import files`.
- Calls the paired Mac bridge and opens the returned document through
  `windowNavigator.open("legacydevice/window/main", ...)`.
- Must coexist with the installed CJK font/language QMDs.
- A missing or mismatched hash must fail closed without changing the device.

The launcher targets `/qml/device/view/navigator/Sidebar.qml`. A separate exact
`DocumentView.qml` patch adds only the page-2 submit action; it does not modify
`toolbarProvider.editingTools`. Both exact source structures remain a
reverse-engineering and hardware-validation boundary.
Xochitl is proprietary and reMarkable does not promise patch compatibility
between versions.

### 2. Native correspondence packet

- Page 1 is deterministic paper with a non-interactive streamed-text preview. The bridge accumulates stable Codex agent-message deltas, and the tablet polls cumulative state at an e-ink-safe cadence instead of repainting each token.
- Page 2 is deterministic full-page huipi stationery annotated with stock tools.
- The reviewed copy persists the final page-1 letter as vector text and preserves page 2.
- Page 3 is a full-size copy of the huipi. High-confidence wrong glyph bounding boxes become red ellipses with the correct glyph adjacent; uncertain readings use a neutral marker.
- Page 4 is the correspondent's vertically typeset response letter. Compact teacher explanations begin on page 5 only when necessary.
- Ferrari and Chiappa remain independent exact-version targets even where
  current resource bytes match.

### 3. Paired Mac bridge

The tablet never contains OpenAI or WHOOP client secrets. A private bridge bound
to the Mac side of the USB link owns:

- native PDF import/export through the enabled USB web interface;
- persisted Codex app-server tasks for incoming text generation and reply review;
- bounded, cumulative live-session state for the tablet's short-poll stream;
- deterministic full-bleed packet and paginated marginalia rendering;
- restart-safe submit receipts containing identifiers only;
- WHOOP OAuth token exchange and refresh;
- ingestion from the live BLE relay;
- consent, retention, deletion, and installation export.

Submission creates a non-ephemeral task named `Letters Home review · <session>`
in the signed-in desktop Codex store. The participant's rendered huipi is
attached at original detail and the final response is constrained to the
versioned review schema. The bridge prefers the Codex binary bundled with the
desktop app, then explicitly selects an image-capable model from its catalog.

Provider-facing code must sit behind interfaces with deterministic fakes:

- `LetterImageProvider`: `FixtureLetterImageProvider`, later `OpenAIImageProvider`;
- `ReplyReviewer`: `FixtureReplyReviewer`, later an approved model-backed reviewer;
- `HeartRateSource`: `MockHeartRateSource`, `BleRelayHeartRateSource`, `WhoopAggregateSource`.

### 4. Heart-rate capture

WHOOP's public cloud API exposes cycle/workout summaries such as average and maximum heart rate, not continuous live heart rate. WHOOP devices can broadcast the standard BLE Heart Rate Service. Because both target reMarkables lack Bluetooth, a phone or edge computer must listen to BLE and relay samples to the gateway.

Capture semantics:

1. Create the session before page 1.
2. Start the biometric window on the first accepted pen stroke, not on app launch.
3. Store samples with source timestamp, gateway receipt timestamp, BPM, optional RR interval, source, and quality flags.
4. Close the window atomically with reply submission.
5. Preserve gaps and reconnect events; never invent samples or interpolate silently.
6. Permit `declined` and `unavailable` sessions to complete normally.

### 5. AI letter and review

- Generate bounded fictional Chinese text for the incoming letter and stream only stable `item/agentMessage/delta` content. No archival signature, seal, accession, or authenticity claim is allowed.
- Deterministically typeset Chinese vertically, top-to-bottom with columns ordered right-to-left, at the exact device profile. The same renderer persists the final incoming and reciprocal letters in the reviewed PDF.
- Require normalized glyph bounding boxes for corrections. The renderer clips all geometry to the page and draws red only for high-confidence corrections; uncertainty stays neutral.
- The review service returns structured annotations, never a replacement image as its only output.
- Annotation boxes are normalised to page space. Red ellipses and adjacent correction glyphs are drawn only on the page-3 copy, so the participant's original strokes remain intact on page 2.

## Render profiles

| Device | Native portrait page |
|---|---:|
| Paper Pro / Chiappa | 1620 × 2160 |
| Paper Pro Move / Ferrari | 954 × 1696 |

Every `Letters Home` page occupies the complete portrait media box. The older image-adapter render profiles remain isolated under issue 004 and are not part of the native streamed-text path.

The machine-readable source is [`contracts/render-profiles.json`](../contracts/render-profiles.json).

## Session data model

Minimum fields:

- pseudonymous `session_id`;
- `letter_fixture_id` and generation provenance, not an archival accession claim;
- `created_at`, `first_ink_at`, `submitted_at`;
- ordered reply strokes or an encrypted object reference;
- annotation payload and reviewer version;
- heart-rate consent state, samples, gaps, and source;
- retention deadline and deletion status.

The existing session `retention_deadline` is the operational deadline. Optional
installation retention is represented separately and requires its own consent
decision and deadline; it never silently extends storage of operational ink or
raw biometrics. The fixture implementation and threat model are documented in
[`privacy-data-flow.md`](privacy-data-flow.md).

Do not store WHOOP email/profile fields by default. Do not put participant ink, heart-rate samples, OAuth tokens, prompts containing personal data, or provider responses into GitHub issues, PRs, CI logs, or Rucksack evidence.

## Security and privacy boundary

- Participant can proceed without biometric capture.
- Notify purpose before connection; record consent version and withdrawal.
- Separate optional research/installation retention from what is required to render page 3.
- Encrypt transport and stored sensitive session objects; rotate identifiers between installations.
- Provide deletion by session receipt and enforce a configured retention deadline.
- Treat withdrawal as deletion, retry partial per-category deletion, and allow no
  tombstone unless a reviewed aggregate approval is explicitly recorded.
- Keep tokens in the trusted secret store, not `.env` files committed to the repository.
- Do not expose the gateway directly from the VM until private networking and an approved publication boundary are verified.

## Installation boundary

The current devices are backed up and patched on exactly OS `3.28.0.162`. Xovi is not boot-persistent, and the stock screenshot helper must not be run under Xovi because it can restart Xochitl. Hardware evidence must use a reviewed framebuffer/AppLoad method and a manual rollback rehearsal.

No autonomous worker may:

- SSH to a physical tablet;
- stop or restart Xochitl;
- install or remove QMDs;
- reboot a tablet;
- enable developer mode;
- run a live OpenAI/WHOOP request;
- publish a participant endpoint;

without an explicit human-approved issue gate.
