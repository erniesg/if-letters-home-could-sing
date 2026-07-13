# Add privacy controls and installation-safe session export

depends-on: 005,006

## Goal

Implement consent, minimisation, retention, deletion, and a pseudonymous export suitable for later interactive-installation research without turning the prototype into a participant surveillance system.

## Acceptance tests

- The participant sees a concise purpose notice and can choose `connect WHOOP` or `continue without heart rate` with equivalent access to the writing/review flow.
- Store a pseudonymous session id and consent version; do not store WHOOP email/profile fields by default.
- Separate operational retention from optional research/installation retention and record a deadline.
- Expiry and deletion remove ink, derived images/transcripts, review, raw heart-rate samples, and token references while retaining only an explicitly approved aggregate tombstone if required.
- Session export contains relative time from first ink, BPM/quality/gaps, and interaction events; it excludes OAuth tokens, direct account identifiers, raw provider payloads, and GitHub/Rucksack metadata.
- Withdrawal, deletion idempotency, clock skew, partial storage failure, and export redaction have automated tests.
- Logs/evidence contain counts and fixture ids only, never participant ink or heart-rate samples.

## Validation command

```bash
scripts/agent-evidence
```

## Allowed secrets

None in required tests. Runtime encryption and provider credentials may be injected only through the approved secret store during a later deployment gate.

## Artifact outputs

- Versioned consent copy and consent-state contract.
- Retention/deletion service with tests.
- Pseudonymous installation export schema and fixtures.
- Data-flow/threat-model update and evidence manifest.

## Stop conditions

Stop before collecting real participant data until the owner has approved purpose, retention duration, deletion contact/path, provider disclosures, installation research use, and any institutional ethics requirement.

## Human clarification protocol

Ask for explicit decisions on raw-sample retention, optional research consent, and deletion period before production configuration. Recommend no raw biometric retention by default and a short operational window.

## Recommended response

Make `no biometric connection` the default-complete path, use short-lived pseudonymous sessions, and derive installation-ready aggregates only after separate opt-in.

## Trade-offs

Keeping raw heart-rate samples enables richer future installation analysis but materially increases privacy, security, and ethics obligations. Aggregate or ephemeral processing is safer.

## Free-form response

Record the approved retention values and ethics/curatorial owner without participant identifiers.
