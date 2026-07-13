# Package a rollback-safe dual-device installer and validate hardware flow

depends-on: 003,005,006,007
labels: rucksack-needs-human

## Goal

Package the AppLoad app, backend, assets, toolbar patch, and coexistence checks into an auditable installer for Ferrari and Chiappa, then validate the complete three-page fixture flow on both devices.

## Acceptance tests

- Installer pins model, OS `3.28.0.162`, resource hashes, Xovi/AppLoad versions, file permissions, and payload checksums.
- Preflight rejects low space, missing backup marker, mismatched version/model/hash, unknown QMD set, missing dependency, or active partial install.
- Install is atomic or transactionally recoverable; duplicate install is idempotent.
- Uninstall and interrupted-install recovery restore byte-identical originals.
- Fake-device tests cover both targets and all refusal cases before hardware access.
- Controlled trials verify launcher, all three pages, pen input, first-ink timing, mock heart rate, submit/retry, suspend/resume, orientation, and review overlay.
- CJK font/language patches remain operational and Xochitl remains stable.
- No reboot, Xochitl stop, or screenshot-helper invocation occurs outside the approved runbook.

## Validation command

```bash
scripts/agent-evidence
tests/run-device-fixtures.sh
# Human-approved only:
scripts/run-controlled-device-trial.sh --device ferrari
scripts/run-controlled-device-trial.sh --device chiappa
```

## Allowed secrets

No provider credentials. Tablet SSH authentication is allowed only for the approved controlled trial and is never copied into artifacts.

## Artifact outputs

- Versioned installer/uninstaller and payload manifest.
- Fake-device matrix results.
- Per-model controlled-trial and rollback evidence.
- Updated recovery runbook.

## Stop conditions

Stop on any mismatch, unexpected file change, CJK regression, input/refresh instability, unavailable rollback, or device-specific behaviour not covered by the runbook.

## Human clarification protocol

Request approval for each physical trial with the exact device, mutation plan, duration, rollback, and current backup verification.

## Recommended response

Validate Ferrari and Chiappa as separate targets with shared payloads only where hashes prove resources identical.

## Trade-offs

Strict pinning increases maintenance for future OS releases but prevents a convenience installer from becoming a recovery incident.

## Free-form response

Record every file hash before/after install/uninstall and any model divergence.
