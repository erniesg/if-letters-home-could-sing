# Product brief: a letter that waits for your answer

## Product promise

The tablet should feel less like an AI worksheet and more like an unexpected piece of correspondence: a letter arrives, the reader turns the page, answers by hand, and receives attentive marginalia. The encounter should create intimacy without pretending that a generated letter is an archival object or that an AI review is an authoritative historical voice.

The participant's reply is a contemporary **huipi** (回批): the return message in a reciprocal qiao pi exchange. This is stronger and more historically grounded than calling it a generic response exercise.

## Core flow

### Page 1 — Incoming letter

- A `Letters Home` envelope entry appears in the main hamburger sidebar beside
  the library destinations such as `My files`.
- Tapping it launches the correspondence experience from the home/library UI;
  it is never inserted into an open document's pen-and-eraser toolbar.
- A fictional qiao pi-inspired letter is shown as a paper image.
- It is labelled `A fictional letter generated for this encounter` in the UI or accessible provenance panel.
- It may be informed by themes such as remittance received, education, health, care, distance, and requests to visit, but it must not reproduce a museum accession, signature, handwriting, seal, or claim a real author.
- The reader can swipe forward but cannot accidentally submit from this page.

### Page 2 — Huipi

- The page is a blank piece of huipi stationery: the same warm paper world as page 1, with a faint border, fold memory, and vertical writing guides, but no generated handwriting, signature, stamp, receipt field, or remittance mark.
- The stationery is deterministic and local rather than AI-generated, so the writing surface is instant, stable, and unmistakably the participant's page.
- The page is visually quiet and immediately writable; the ink layer remains separate from the stationery layer.
- The first accepted pen stroke records `first_ink_at` and opens the biometric capture window.
- Heart-rate connection status is present but unobtrusive: connected, reconnecting, unavailable, or declined.
- A participant can finish without WHOOP.
- Submit requires a deliberate action and a confirmation when the page is empty.

### Page 3 — Marginalia

- The original ink remains visually primary and unmodified.
- AI comments appear as a reversible overlay or in the margin, never by rewriting the participant's strokes.
- Feedback is concise, specific, and kind. It can point out likely character/word corrections, ambiguous reading, tone, and a reflective question.
- Uncertain readings are marked as uncertain; the system does not fabricate a transcription.
- The page is called `Marginalia` or `A reading of your reply`, not `Score`, `Grade`, or `Correct answer`.

## Experience principles

1. **Reciprocity over extraction.** The participant writes back; they are not merely analysed.
2. **Intimacy over spectacle.** Material detail, pacing, and silence do more work than animation.
3. **Provenance over pastiche.** Generated material is visibly fictional and never presented as a digitised accession.
4. **Plural readings over authority.** A review is one interpretation, with uncertainty intact.
5. **Embodiment by consent.** Heart rate enriches the encounter but is never required.
6. **History from below.** Family care, health, education, money, separation, and return remain central.

## Visual direction

- Warm, fibrous paper with fold memory; faint red rules or grids; muted blue, grey, or black ink; restrained receipt marks.
- Legible hierarchy on Gallery 3 colour e-ink, with no low-contrast decorative text.
- No generic parchment, wax seals, imperial motifs, nationalist slogans, or cinematic sepia haze.
- Use archival references for material vocabulary, not for copying handwriting, names, stamps, or composition.
- Blank and review pages should share the incoming letter's paper field so the three pages feel like one correspondence packet.

## Non-goals for the first vertical slice

- Editing reMarkable's proprietary document format.
- Claiming museum-authenticated content or displaying protected archival images in generated output.
- Live beat-to-beat heart rate from the WHOOP cloud API.
- Automatic physical installation, reboot, or Xochitl replacement.
- A general-purpose notebook, handwriting tutor, or historical chatbot.

## Open creative input

The exact `Dear You` reference has not been identified in the repository or supplied materials. Until a link, artist, publication, or image is provided, the implementation uses the narrow interpretation `correspondence as a paced, intimate ritual`; it must not imitate an unidentified work's distinctive expression.
