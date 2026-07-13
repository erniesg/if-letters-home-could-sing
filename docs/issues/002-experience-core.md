# Implement the three-page experience core with deterministic contracts

depends-on: 001

## Goal

Implement a platform-neutral state machine and payload schemas for incoming letter, writable huipi, submission, and marginalia so device, gateway, and host simulator share one behaviour contract.

## Acceptance tests

- States include `incoming`, `reply`, `submitting`, `marginalia`, and recoverable error/retry states.
- Only an explicit forward swipe moves incoming to reply; a backward swipe returns without destroying ink.
- The first accepted pen stroke sets `first_ink_at` exactly once.
- Submit is idempotent; duplicate submit uses the same session/review id.
- Empty submission requires confirmation and is representable without fake strokes.
- Original strokes are immutable after submission and annotations are a separate overlay.
- Session, letter provenance, stroke, heart-rate, and review schemas validate positive fixtures and reject invalid timestamps, out-of-page anchors, unknown states, and generated letters claiming an accession number.
- Unit tests are written before or alongside implementation and require no UI, network, device, or secret.

## Validation command

```bash
scripts/agent-evidence
```

## Allowed secrets

None.

## Artifact outputs

- Experience-core state machine.
- Versioned JSON schemas and valid/invalid fixtures.
- Unit tests covering every transition and idempotency rule.
- Evidence manifest under `.agent/evidence/`.

## Stop conditions

Stop if the state model requires direct knowledge of Xochitl internals or a provider SDK. Replace that dependency with an interface.

## Human clarification protocol

Ask only if a product decision changes persisted state compatibility. Default to preserving ink and allowing a retry from the last durable state.

## Recommended response

Keep the core as a small deterministic library shared through serialised events; adapters own QML, network, and provider details.

## Trade-offs

A formal state machine adds upfront contract work but makes suspend/resume, duplicate submit, and offline recovery testable before hardware access.

## Free-form response

Document the transition table and any compatibility decision.
