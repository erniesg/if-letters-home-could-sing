# Spike the main hamburger-sidebar letter launcher with exact-version QMLDiff

depends-on: 003
labels: rucksack-needs-human

## Goal

Identify the exact Xochitl/QRR main hamburger/library-sidebar resource and
build a hash-pinned QMLDiff patch that adds one inert `Letters Home` item below
`Import files`, then launches the AppLoad experience, without conflicting with
existing CJK QMDs. The open-document editing toolbar is explicitly out of
scope.

## Acceptance tests

- Record exact Ferrari/Chiappa model, OS, source resource path, source hash, active QMD order, and AppLoad/Xovi versions.
- Build fixture-based patch tests for matching Ferrari/Chiappa resources, wrong model, wrong OS, wrong hash, duplicate install, missing AppLoad, and unrelated active mods.
- Prove the output patch changes only the intended sidebar subtree and composes deterministically with the current CJK font/language patches.
- Reject `/qml/DocumentView.qml` and `toolbarProvider.editingTools` as launcher locators.
- First hardware step is an inert icon/button; launch action is enabled only after visual/stability confirmation.
- Uninstall restores byte-identical pre-install resources and leaves CJK patches working.
- Do not use the stock screenshot helper under Xovi.
- Hardware evidence records observed UI and Xochitl stability without participant data.

## Validation command

```bash
scripts/agent-evidence
# Human-approved hardware lane only:
tests/run-device-fixtures.sh
```

## Allowed secrets

No application secrets. Tablet SSH authentication may be used only in the approved hardware lane and must stay outside the repository and logs.

## Artifact outputs

- Resource discovery notes and hashes.
- QMLDiff patch and launcher assets.
- Cross-model fake-device tests and rollback manifest.
- Human-reviewed hardware evidence for each model.

## Stop conditions

Stop on any resource/hash/version mismatch, unknown active mod, Xochitl instability, missing backup, unavailable rollback, or unexpected diff. Never broaden a locator to make a mismatch pass.

## Human clarification protocol

Request approval immediately before the first SSH/mutation on each tablet and state the exact files, hashes, commands, rollback, and expected downtime.

## Recommended response

Develop entirely against backed-up fixtures, prove an inert icon first, then run one controlled model at a time with immediate rollback verification.

## Trade-offs

Patching the stock main sidebar gives the desired native entry point but is the
most version-fragile part of the system. An AppLoad-only launcher is the safe
fallback.

## Free-form response

Record the located QML object, why the locator is unique, and every device observation.
