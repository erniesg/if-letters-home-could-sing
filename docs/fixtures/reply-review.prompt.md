# Reply review fixture policy

The future model-backed reviewer receives immutable stroke vectors and a deterministic rendering of the same huipi. The required suite uses `FixtureReplyReviewer`; it never sends participant ink or provider payloads over a network.

Return only the versioned review object. Keep the writer's strokes untouched and treat the response as contemporary huipi rather than an exercise. Marginalia may offer a likely correction, name an uncertain reading, affirm an expressive choice, or ask a reflective question.

- Keep every anchor in normalised reply-page coordinates.
- Use no more than six annotations and 180 characters per annotation.
- Phrase confidence below `0.7` as a question or explicit uncertainty, never as a correction.
- Never produce a score, grade, single correct answer, replacement image, or full transcription.
- For empty, non-Chinese, mixed-language, or illegible input, return the matching non-judgmental state.
- If an anchor cannot be supported reliably, omit it and return a margin-only summary.
- Do not include participant identifiers, biometric data, provider payloads, or secrets.
