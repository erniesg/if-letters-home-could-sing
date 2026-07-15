# Definition of done

## Product-level done

The feature is done only when all of the following are demonstrated on each
eligible backed-up target at its independently pinned OS and resource version:

1. A `Letters Home` envelope entry appears in the main hamburger/library
   sidebar beside `My files`, never in the open-document editing toolbar, and
   creates and opens one native notebook without importing a PDF or creating a
   second library item.
2. Page 1 streams a bounded fictional qiao pi-inspired letter into the native
   portrait `10×18` grid, with every glyph in bounds and provenance visible.
3. One swipe reaches a blank huipi page; stock pen, marker, eraser, undo/redo,
   layers, close, swipe-down, and page gestures behave exactly as in another
   native notebook.
4. The first accepted stroke starts the heart-rate capture window and submit closes it.
5. The experience completes with WHOOP connected, disconnected mid-session, unavailable, or declined.
6. Submission creates one visible persisted Codex task on the paired Mac with
   the rendered huipi attached at original detail, copies page 2 to page 3 in
   the same notebook, and adds page 4. Page 3 shows reversible grounded
   marginalia while page 2 remains unchanged; page 4 streams a reciprocal
   response constrained to one portrait grid.
7. Back, swipe, empty-submit, retry, offline, timeout, duplicate-submit, and provider-error paths have intentional UI states.
8. No real archival item is misrepresented as generated content, and no generated item uses a real accession number, signature, or copied seal.
9. Consent, retention, export, and deletion work as documented; sensitive values are absent from logs and evidence.
10. Exact-version install, uninstall, rollback, and coexistence with existing
    CJK patches pass independently. Ferrari is the current eligible target;
    Chiappa remains held until its own native API contract is recovered and
    hardware-validated.

## Engineering done for every issue

An issue is not complete because code was written. Its pull request must include:

- a failing test or fixture assertion committed before or alongside the implementation change;
- all acceptance tests in the issue body passing from a clean checkout;
- no live credential requirement unless the issue is explicitly in a human-approved trusted lane;
- deterministic fakes for image, review, heart-rate, tablet, and network boundaries;
- a Rucksack evidence manifest and concise caveats;
- updated contracts/docs when behaviour or payloads change;
- no unrelated refactor, generated bulk, participant data, or archival master copied into Git;
- review of failure, rollback, privacy, and accessibility paths;
- exact commands and artifact paths in the handoff.

## Validation ladder

### Portable gate — required on every PR

- Contract and unit tests pass without network, private datasets, or secrets.
- Schemas validate example payloads and reject unsafe or ambiguous variants.
- Static checks confirm issue specs are portable and dependency-ordered.
- Image fixtures have a prompt/provenance sidecar and correct device transformation.
- No credential markers or participant payloads are present in the diff.

### Trusted VM gate — required before review-ready for integration issues

- Clean checkout on `erniesg-ai-vm`.
- Rucksack VM verification passes.
- Gateway integration tests pass against fake providers.
- Network failures, retry idempotency, storage expiry, and redaction tests pass.
- The paired-Mac bridge binds only to the USB interface and duplicate submit
  remains idempotent across a bridge restart.
- Evidence is copied as a manifest/log summary, never as secret-bearing raw traffic.

### Hardware-in-loop gate — explicit approval required

- Exact model, OS build, resource hashes, and active QMD set are recorded.
- Install preflight and uninstall dry-run pass before mutation.
- The main-sidebar launcher, native pen controls, stock swipe/close behavior,
  stroke latency, orientation, suspend/resume, and page flow are observed on
  each device.
- CJK font/language menus still work.
- Xochitl remains stable; the prohibited stock screenshot helper is not used under Xovi.
- Rollback returns files and hashes to their pre-install state.

### Live-provider gate — explicit approval and credentials required

- OpenAI organisation/model access is verified outside the repository.
- WHOOP OAuth redirect, consent, refresh, revoke, and BLE broadcast instructions are verified.
- One synthetic end-to-end session passes with redacted logs.
- Cost, rate limits, retention, and provider data handling are accepted by the project owner.

## Overnight queue success

An overnight run is successful when every dispatched issue ends in one of two states:

- `rucksack-awaiting-review` with a scoped PR, passing required evidence, and no unresolved acceptance item; or
- a fail-closed human/decision gate with the exact missing input and recommended next action.

Workers must not mark partial work complete, skip failing tests, loosen assertions to turn red green, or cross a live credential/hardware/deploy gate.
