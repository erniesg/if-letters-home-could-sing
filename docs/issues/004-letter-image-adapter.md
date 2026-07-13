# Add the GPT Image 2 letter provider behind fixture-first tests

depends-on: 002

## Goal

Implement a provider-neutral letter-image pipeline whose default is the checked-in fictional fixture and whose optional live adapter uses `gpt-image-2` without putting credentials or archival masters on the tablet.

## Acceptance tests

- `FixtureLetterImageProvider` is the default in tests, development, and offline sessions.
- Prompt, provenance, fictional status, provider/model, timestamps, dimensions, and checksums are stored in a sidecar.
- Prompt policy rejects real accession numbers, real names/signatures, museum logos, authenticity claims, and unsupported model sizes.
- Chiappa generation is transformed from `2160×1616` to `2160×1620`; Ferrari generation is transformed from `1696×960` to `1696×954`; golden tests verify pixels/dimensions.
- Live adapter requests `gpt-image-2`, has bounded timeout/retry, records cost/usage metadata when available, and never logs prompts containing participant data or response bytes.
- Provider failure returns a cached fixture/fail-closed UI state without blocking the reply flow.
- The required suite passes with the live adapter disabled and no key.

## Validation command

```bash
scripts/agent-evidence
```

## Allowed secrets

The optional trusted-VM live proof may read `OPENAI_API_KEY` from the approved runtime secret store. Required tests and CI use none. Never print, persist, or send the value to the tablet.

## Artifact outputs

- Provider interface, fixture provider, and optional OpenAI adapter.
- Prompt policy and device transform tests.
- Fixture provenance/checksum sidecars.
- Redacted trusted-VM proof manifest when a human later enables the live gate.

## Stop conditions

Stop before a live call if the credential, organisation verification, cost approval, or provider retention decision is absent. Do not block fixture implementation.

## Human clarification protocol

Ask only before the first billable/live request or if the generated visual would need a protected archival image distributed to a provider. Recommend synthetic references and the existing approved prompt.

## Recommended response

Finish and validate the fixture provider first, then make the live adapter a separately enabled configuration with the same return contract.

## Trade-offs

Caching reduces novelty but improves latency, offline reliability, cost control, and curatorial review. The first installation should use a small reviewed pool before on-demand generation.

## Free-form response

Record model/version, generated asset id, transform checksum, and any safety rejection without including response bytes.
