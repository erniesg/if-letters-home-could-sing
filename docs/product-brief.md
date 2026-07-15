# Product brief: a letter that waits for your answer

## Product promise

The tablet should feel less like an AI worksheet and more like an unexpected piece of correspondence: a letter arrives, the reader turns the page, answers by hand, and receives attentive marginalia. The encounter should create intimacy without pretending that a generated letter is an archival object or that an AI review is an authoritative historical voice.

The participant's reply is a contemporary **huipi** (回批): the return message in a reciprocal qiao pi exchange. This is stronger and more historically grounded than calling it a generic response exercise.

## Core flow

### Page 1 — Incoming letter

- A `Letters Home` envelope entry appears in the main hamburger sidebar beside
  the library destinations such as `My files`.
- Tapping it asks the paired Mac to prepare a native correspondence document,
  then opens that document in the stock reMarkable reader/writer interface.
- The experience never replaces the stock pen-and-eraser toolbar, close action,
  swipe-down menu, or page gestures.
- A fictional qiao pi-inspired Chinese letter arrives in vertical text batches on deterministic paper, then is persisted as vector text in the reviewed packet.
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
- Submission creates a visible persisted Codex task on the paired Mac and keeps
  the page open until a reviewed native copy is ready.

### Page 3 — Marked copy

- The original ink remains visually primary and unmodified.
- A full-size copy of the huipi shows red ellipses around only high-confidence wrong glyphs, with the correct glyph immediately beside each mark. The original page 2 remains untouched.
- Feedback is concise, specific, and kind. It can point out likely character/word corrections, ambiguous reading, tone, and a reflective question.
- Uncertain readings are marked as uncertain; the system does not fabricate a transcription.
- The page is called `Marginalia` or `A reading of your reply`, not `Score`, `Grade`, or `Correct answer`.

### Page 4 — A letter in response

- The correspondent answers what was actually legible in the participant's huipi.
- The reply uses the same vertical typesetting and portrait paper system as page 1.
- Compact teacher explanations continue on page 5 only when useful; the layout does not reserve empty card space.

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
- Blank, marked-copy, and response pages share the incoming letter's paper field so the packet feels like one correspondence.

## Non-goals for the first vertical slice

- Editing reMarkable's proprietary document format.
- Claiming museum-authenticated content or displaying protected archival images in generated output.
- Live beat-to-beat heart rate from the WHOOP cloud API.
- Automatic physical installation, reboot, or Xochitl replacement.
- A general-purpose notebook, handwriting tutor, or historical chatbot.

## Open creative input

The exact `Dear You` reference has not been identified in the repository or supplied materials. Until a link, artist, publication, or image is provided, the implementation uses the narrow interpretation `correspondence as a paced, intimate ritual`; it must not imitate an unidentified work's distinctive expression.
