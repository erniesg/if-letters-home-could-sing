# Privacy data flow and threat model

This slice is fixture-only. It defines the boundary needed for later installation
approval without authorising collection of real participant data.

## Consent and data flow

1. The tablet shows the versioned purpose notice before biometric connection.
   `Connect WHOOP` records `granted`; `Continue without heart rate` records
   `declined`. Both choices enter the same incoming-letter, huipi, and marginalia
   flow.
2. The gateway stores only a random pseudonymous session id, the consent-copy
   version, consent decisions, and their timestamps. WHOOP email and profile
   fields are not part of the storage contract.
3. Operational data may contain reply strokes, derived images or transcripts,
   review marginalia, heart-rate samples and gaps, interaction events, transient
   provider payloads, and secret-store token references. Each session records an
   explicit operational deadline; no duration is defaulted by code.
4. Optional installation retention is a separate opt-in and deadline. Its export
   is rebuilt from an allowlist: relative time from first accepted ink, BPM,
   quality, observed gaps, source-clock offset, and named interaction events.
   It contains no absolute timestamps, ink, transcript, review text, token
   reference, account identifier, provider payload, or GitHub/Rucksack metadata.
5. Operational expiry removes operational categories even when a separately
   consented research export remains. Research expiry, withdrawal, or participant
   deletion removes that export as well. Deletion retries only categories left by
   a partial storage failure and is idempotent once data is absent.

## Retained deletion record

The default is no retained record. A pseudonymous aggregate tombstone may remain
only when the session schedule contains an explicit, reviewed approval id. The
tombstone is limited to duration and sample/gap/interaction counts; it has no ink,
biometric values, timestamps from the encounter, review, identifiers, payloads,
or token references. Fixture approvals are syntactically isolated from later
production configuration.

## Threats and controls

| Threat | Control in this slice |
|---|---|
| Biometric participation becomes a condition of writing | Consent blocks connection, not the experience; both decisions follow identical flow transitions. |
| Account data links a reply to a person | Session ids use independent random entropy; consent/session models have no email or profile fields. |
| Export accidentally serialises a provider response or secret | Export is constructed field-by-field and validated by an `additionalProperties: false` schema. |
| Source clock skew creates invented or reordered biometric timing | Export time uses gateway receipt time and separately records the observed source offset; samples and gaps are never interpolated. |
| A failed delete leaves a falsely complete status | Per-category failures produce `partial`, successful categories stay erased, and retry addresses the remainder. |
| Logs or evidence disclose ink or heart-rate values | Audit records contain only pseudonymous fixture id, action/status, and category/failure counts. Required tests use synthetic fixtures and print no payloads. |
| Research retention silently extends operational retention | Operational and research deadlines are separate; raw operational categories expire independently of the allowlisted export. |

## Production hold

Real collection remains blocked. The owner has not yet approved an operational
deletion period, raw-sample retention, optional installation-research consent
copy, provider disclosures, deletion contact/path, or ethics/curatorial owner.
The recommended production posture remains no retained raw biometrics and a short
operational window. Those values must be recorded without participant identifiers
after the required human and institutional decisions.
