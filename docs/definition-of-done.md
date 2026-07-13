# Definition of done

## Product-level done

The feature is done only when all of the following are demonstrated on both backed-up target devices at the pinned OS version:

1. A letter icon appears in the intended stock toolbar location and launches the experience without corrupting the open notebook.
2. Page 1 shows a generated or cached fictional qiao pi-inspired letter with provenance visible on demand.
3. One swipe reaches a blank, low-latency reply page; pen strokes render and survive an app restart.
4. The first accepted stroke starts the heart-rate capture window and submit closes it.
5. The experience completes with WHOOP connected, disconnected mid-session, unavailable, or declined.
6. Submission reaches page 3 with the original ink unchanged and structured, gentle annotations overlaid accurately.
7. Back, swipe, empty-submit, retry, offline, timeout, duplicate-submit, and provider-error paths have intentional UI states.
8. No real archival item is misrepresented as generated content, and no generated item uses a real accession number, signature, or copied seal.
9. Consent, retention, export, and deletion work as documented; sensitive values are absent from logs and evidence.
10. Exact-version install, uninstall, rollback, and coexistence with existing CJK patches pass on Ferrari and Chiappa.

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
- Evidence is copied as a manifest/log summary, never as secret-bearing raw traffic.

### Hardware-in-loop gate — explicit approval required

- Exact model, OS build, resource hashes, and active QMD set are recorded.
- Install preflight and uninstall dry-run pass before mutation.
- The toolbar launcher, stroke latency, orientation, suspend/resume, and page flow are observed on each device.
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
