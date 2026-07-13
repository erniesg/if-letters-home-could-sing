# Implement structured reply review and marginalia rendering

depends-on: 002,003

## Goal

Turn a submitted handwritten reply into a structured, uncertainty-aware review and render it as gentle marginalia while preserving the participant's original ink.

## Acceptance tests

- Input supports stroke vectors plus a deterministic rendered page; provider code cannot mutate stored strokes.
- `FixtureReplyReviewer` covers corrections, uncertain readings, affirmations, and reflective questions.
- Review output is schema-validated, bounded in annotation count/length, and anchored in normalised page coordinates.
- Low-confidence text is phrased as a question or uncertainty, never a confident correction.
- Page 3 can toggle annotations and always recover the untouched original reply.
- Duplicate submit/retry cannot create conflicting review ids.
- Empty, non-Chinese, mixed-language, illegible, and provider-error fixtures produce useful non-judgmental states.
- Tests prohibit scores, grades, a single `correct answer`, and fabricated full transcriptions.

## Validation command

```bash
scripts/agent-evidence
```

## Allowed secrets

None for required tests. A future trusted-VM provider proof may use an approved server-side model credential under a separate human gate.

## Artifact outputs

- Reviewer interface and fixture reviewer.
- Versioned review schema and prompt/policy tests.
- QML annotation overlay integration.
- Evidence manifest and redacted example review.

## Stop conditions

Stop if a provider cannot return structured coordinates/confidence reliably. Preserve the reply and return a margin-only reflection rather than fabricating anchors.

## Human clarification protocol

Ask if the desired review shifts from reflective marginalia to language instruction, because that changes tone, evaluation criteria, and consent. Default to reflective, gentle marginalia.

## Recommended response

Use a two-stage adapter—transcription/uncertainty, then review—and validate both against a strict schema before rendering.

## Trade-offs

Structured overlays constrain expressive AI output but make reversibility, accessibility, and hallucination handling testable.

## Free-form response

Document observed failure modes and which annotations were intentionally suppressed.
