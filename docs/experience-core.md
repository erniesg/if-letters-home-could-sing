# Experience core contract

The `experience_core` package is the deterministic reference implementation for the incoming letter, writable huipi, submission, and marginalia flow. Device and gateway adapters supply timestamps and identifiers; the core performs no I/O and has no knowledge of QML, Xochitl, a provider SDK, or the network.

## Transition table

| Current state | Event | Next state | Durable effect |
|---|---|---|---|
| `incoming` | forward swipe | `reply` | Existing ink, if any, is retained. |
| `reply` | backward swipe | `incoming` | Ink and `first_ink_at` are retained. |
| `reply` | accepted stroke | `reply` | The stroke is appended; the first one sets `first_ink_at` once. |
| `reply` | submit with no ink and no confirmation | `reply` | No fields change; confirmation is requested. |
| `reply` | submit, or confirmed empty submit | `submitting` | `submitted_at` and `review_id` are set together. |
| `submitting` | submission failure | `submission_error` | Submission identifiers and original strokes are retained. |
| `submitting` | review failure | `review_error` | Submission identifiers and original strokes are retained. |
| either error state | retry | `submitting` | The same session and review identifiers are reused. |
| `submitting` | matching review completed | `marginalia` | Annotations are added as a separate overlay. |

Backward swipe from `incoming` and swipes unrelated to the current page are no-ops. Mutating events that are invalid for the current state raise `TransitionError`. A submit received after the first durable submit is idempotent: it returns the unchanged session even if the caller supplies a different timestamp or review identifier.

## Persistence compatibility

Version 1 schemas live in `contracts/v1/schemas`. Session state uses caller-supplied RFC 3339 timestamps so replay does not consult a clock. A confirmed empty submission has empty `strokes`, a null `first_ink_at`, and no heart-rate samples; fake ink is never inserted.

`submitted_at` closes the capture window in the same pure transition that records `review_id`. Recoverable errors preserve that durable submission. Heart-rate gaps remain explicit intervals, and samples must remain between `first_ink_at` and `submitted_at`.

The participant's strokes are frozen values after acceptance and cannot be added after submit. Review annotations are carried by the separate review schema and never replace or rewrite the stroke array. Generated and fixture letter provenance is explicitly fictional; the closed provenance schema rejects accession-number claims and copied archival identity fields.

Changing a field's meaning, state value, or transition requires a new schema version. Additive adapter metadata must not be inserted into these closed payloads without a versioned contract change.

## Reply review boundary

`ReviewRequest` gives a reviewer detached, immutable stroke vectors together with a deterministic SVG rendering of the same page. `review_reply` rejects provider input mutation, mismatched session or review identifiers, and any output that does not satisfy the bounded version 1 review schema. The required provider is `FixtureReplyReviewer`; it covers ordinary, empty, non-Chinese, mixed-language, illegible, and provider-error paths without network access.

The checked-in policy is [`fixtures/reply-review.prompt.md`](fixtures/reply-review.prompt.md). It forbids scores, grades, a single correct answer, replacement ink, and fabricated full transcriptions. Unsupported readings return a summary without invented anchors, while validated annotations remain a separate toggleable overlay.
