# Replace AppLoad canvas with a native Xochitl and Mac Codex round trip

depends-on: 004,005,007,008
labels: rucksack-needs-human

## Goal

Open the correspondence as a portrait, paper-like native reMarkable document, preserve the stock pen and gesture interface, stream a fictional incoming letter from the paired Mac, and make reply submission return both a marked copy and a correspondent's response.

## Acceptance tests

- The main-sidebar `Letters Home` entry calls the consent-scoped Mac bridge and opens the returned document with `windowNavigator.open("legacydevice/window/main", ...)`; it never launches an AppLoad window.
- Page 1 and the blank huipi page use the exact native portrait Ferrari `954×1696` or Chiappa `1620×2160` aspect with zero application chrome margin.
- Page 1 starts as deterministic paper and polls a bounded session endpoint while Codex runs. Stable `item/agentMessage/delta` text is accumulated and rendered as Chinese vertical columns, top-to-bottom and right-to-left, in batches no faster than 750 ms. The overlay has no pointer or pen handler and disappears outside page 1.
- A bridge restart or missing live session must fail to the untouched native document rather than trapping the user. The streaming layer is preview state; the final reviewed packet persists the completed incoming letter as vector text.
- Xochitl owns pen, marker, eraser, undo/redo, page navigation, close, and swipe-down behaviour; the patch does not intercept or replace those controls.
- Only page 2 of a `Letters Home` session shows one additive `Send to Codex` action. It exports the annotated native PDF through the enabled USB web interface and submits the reply page plus conversation context to the Mac bridge.
- Each first durable submit creates one non-ephemeral, named Codex task through `codex app-server`, attaches the reply rendering at original detail, and constrains the final response to the versioned review schema.
- The review schema includes a reciprocal Chinese response letter and normalized bounding boxes. Only high-confidence `correction` items may become red marks; uncertain readings remain visibly uncertain and never masquerade as corrections.
- Duplicate submit returns the same Codex task and reviewed document id without exporting, reviewing, or uploading twice.
- A transient USB export or reply-render failure retries only before Codex starts; retry never creates a duplicate review task.
- The reviewed upload preserves page 2 unchanged and persists the completed incoming letter on page 1. Page 3 is a full-size copy of page 2 with red ellipses around high-confidence wrong glyphs and the suggested glyph written immediately beside each ellipse. Page 4 is the vertically typeset reciprocal response letter. Compact explanations paginate from page 5 only when needed; oversized empty cards are forbidden.
- Review remains a kind Chinese-teacher reading: corrections, uncertain readings, tone, and reflection are allowed; scores, grades, fabricated transcription, and replacement of participant ink are rejected.
- The bridge logs only session state, counts, document ids, hashes, and error codes; participant ink, rendered reply bytes, conversation text, biometric samples, and Codex payloads are never logged.
- Required tests use fake tablet, renderer, and Codex transports. Live Codex, USB export/upload, QMLDiff install, Xochitl restart, and hardware validation remain explicit human-approved lanes.

## Validation command

```bash
scripts/agent-evidence
tests/run-device-fixtures.sh
# Human-approved only after portable and trusted-Mac evidence:
scripts/run-controlled-device-trial.sh --device ferrari
```

## Allowed secrets

None in required tests. The live path reuses the signed-in Codex installation on the paired Mac; no OpenAI key is stored on the tablet or in the repository.

## Artifact outputs

- Native sidebar and page-2 submit QMLDiffs pinned to exact Ferrari and Chiappa resources.
- Full-bleed two-page packet renderer and paginated reviewed-packet renderer.
- Mac bridge with USB document adapter and persisted Codex app-server client.
- Fake round-trip tests, exact-resource compatibility proof, and redacted evidence manifest.

## Stop conditions

Stop before tablet mutation if exact resource compatibility fails, the USB web interface is disabled, the Mac bridge is unreachable from `10.11.99.1`, the reviewed upload cannot be resolved to one new document id, or rollback cannot remove every Letters Home patch and payload. Preserve the current native document and never repair by merging files into the live Xochitl store.

## Human clarification protocol

The product owner has confirmed the architecture: reply submission creates a Codex task on the Mac and the rendered review returns to the device. Ask only before the exact physical mutation plan or if the review tone changes away from kind Chinese-language instruction plus reflection.

## Recommended response

Keep Xochitl responsible for drawing and gestures, use the official USB import/export surface for document transfer, and keep Codex task creation and rendering on the Mac.

## Trade-offs

Returning a reviewed copy creates a second native document instead of rewriting the open PDF in place. This preserves the original ink and avoids unsupported live document-store mutation, at the cost of one additional library item per completed encounter.

## Definition of done

Ferrari is test-ready only after a synthetic incoming letter visibly advances in more than one vertical-text batch, a synthetic reply opens a persisted Codex task on the Mac, the returned native document opens on the page-3 marked copy, a known wrong glyph is circled with its correction adjacent, page 4 contains a readable reciprocal letter, stock notebook controls and swipe behaviour remain unchanged, and uninstall restores the exact pretrial hashes. Chiappa remains a separate exact-version validation target.

## Free-form response

Record the Codex task id, source and reviewed document ids, page count, exact target hashes, and pass/fail observations without attaching participant ink, rendered reply bytes, model payloads, or biometric samples.
