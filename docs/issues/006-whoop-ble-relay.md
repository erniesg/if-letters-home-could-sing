# Implement consented first-ink-to-submit heart-rate capture

depends-on: 002

## Goal

Replace the obsolete token-based WHOOP helper with tested heart-rate source adapters: deterministic mock capture, a phone/edge BLE relay for live samples, and optional WHOOP OAuth v2 aggregate context.

## Acceptance tests

- Delete or quarantine code that logs any portion of a token or raw provider response; regression tests enforce redaction.
- `MockHeartRateSource` produces deterministic samples, reconnects, gaps, and unavailable/declined states.
- Capture begins on the first accepted stroke and stops atomically at submission; samples outside the interval are rejected or marked.
- BLE relay parses the standard Heart Rate Measurement characteristic, including 8/16-bit BPM and optional RR intervals, and forwards over authenticated TLS/WebSocket.
- Disconnect/reconnect preserves explicit gaps and never silently interpolates.
- WHOOP OAuth uses current v2 endpoints/scopes, consent/revoke/refresh semantics, and is clearly separate from live BLE capture.
- The tablet contains no WHOOP client secret and the experience completes when biometric consent is declined.
- All required tests use recorded/synthetic BLE packets and no account, strap, Bluetooth radio, or network.

## Validation command

```bash
scripts/agent-evidence
```

## Allowed secrets

None for required tests. Later trusted-lane OAuth proof may read `WHOOP_CLIENT_ID` and `WHOOP_CLIENT_SECRET` from an approved secret store. Never expose them to the tablet, issue, PR, evidence, or client log.

## Artifact outputs

- Heart-rate source interface and deterministic mock.
- BLE packet parser/relay with recorded synthetic fixtures.
- OAuth v2 server adapter and redaction tests, disabled by default.
- Session gap/quality summaries and evidence manifest.

## Stop conditions

Stop before live OAuth or strap pairing without explicit consent, credentials, redirect configuration, and a test participant. Continue all mock and parser work.

## Human clarification protocol

Ask only before live account connection or when choosing the phone/edge deployment target. Recommend a phone web/native bridge for prototype convenience and a dedicated edge bridge for installation reliability.

## Recommended response

Treat BLE samples as the live source and WHOOP cloud data as optional aggregate metadata; expose both through one typed source contract.

## Trade-offs

A relay adds a second device and network hop, but it is the only supported route to live WHOOP heart rate because the tablets have no Bluetooth and the cloud API is aggregate-only.

## Free-form response

Record sample loss, reconnect behaviour, and clock-offset assumptions without retaining participant identifiers.
