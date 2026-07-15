# Native notebook correspondence design

Date: 2026-07-15

Target: reMarkable Paper Pro Move / Ferrari, OS 3.28.0.162

Status: approved design; instant-start amendment approved 2026-07-15

## Outcome

`Letters Home` creates one native Xochitl notebook, not an imported PDF. The
incoming letter, handwritten huipi, marked copy, and reciprocal response remain
four pages of that same notebook. Stock reMarkable pens, menus, page turns, and
close gestures remain authoritative.

The Mac bridge transports session state and runs Codex. It does not import a
replacement document after generation or review, and it never edits Xochitl's
private document store directly.

## Why the current packet is replaced

The current trial uploads a two-page PDF and draws streamed text in a QML layer.
The photographed Ferrari result exposed three failures:

- the visible text stopped before the bridge's complete 176-character value;
- columns were made by splitting a string at a height-derived character count,
  rather than by placing glyphs in a bounded letter grid;
- completing the review required importing and opening another PDF.

The PDF path proved the USB and Codex round trip, but it is not the intended
notebook experience. Existing trial PDFs are left untouched. New sessions stop
creating them.

## Selected approach

Use stock Xochitl notebook and page operations with app-owned, non-interactive
AI display layers.

Recovered Ferrari resources expose the stock notebook creation window
(`library-ui/window/create-notebook`), native page creation with a selected
template, template replacement, and the page-management surface used for page
duplication. Implementation must recover and hash-pin the exact resource needed
for the creation and duplication callbacks before changing hardware. If those
callbacks cannot be verified on OS 3.28.0.162, the installer fails closed.

Two alternatives are rejected:

1. Writing generated elements into `.rm`, `.content`, or metadata files would
   make the AI layers native scene items, but it risks corrupting an open
   document and is coupled to private formats.
2. Importing PDF pages into a notebook retains the replacement-document and
   refresh problems and does not produce a native writing canvas.

## Notebook and template lifecycle

The launcher keeps one app-owned, two-page blank stationery notebook as a
reusable seed. The seed is created through the stock notebook controller before
the participant needs it; it is never a PDF, an imported archival object, or a
private document-store fixture. Its identifier is persisted as app-private
bridge state, and the tablet verifies that the native entry still exists and
still contains exactly two blank pages before using it.

The warm launcher performs these steps:

1. Ask the bridge to create a session. The response contains a session ID and
   no document payload.
2. Open the verified stock notebook-creation scope invisibly. That scope first
   copies the seed's two pages inside the seed and then moves only those copies
   into a new notebook with `LibraryController.createDocumentFromExisting`.
   The seed's original two pages remain untouched and reusable.
3. Name the clone `Letters Home <session-id>` so the QML layer can recover the
   session after reopening without storing participant content in the name.
4. Bind the clone's native document ID and page IDs to the bridge session.
5. Close the sidebar and open page 1 through the stock document view as soon as
   the native entry is ready. Codex generation continues in parallel and is
   never on the open path.

If the seed is missing, edited, or not ready, the launcher fails visibly and
queues an asynchronous seed rebuild through the same stock controller. It does
not hang, silently create a PDF, mutate Xochitl's private store, or consume a
damaged seed. The next tap may use the rebuilt seed.

With a healthy local bridge and valid seed, tap-to-open targets 1.5 seconds or
less on Ferrari. `Preparing letter…` has a two-second watchdog that restores
the enabled `Letters Home` item and emits a stock notification on failure.

The template bundle uses the unique app-owned identifier
`letters-home-ferrari` and full Ferrari media size of 954 by 1696 pixels. It is
a deterministic KZip package with the exact three members accepted by Ferrari
Xochitl: `manifest.json`, `image.png`, and `image.svg`. Installation must not
overwrite a stock template. Rollback removes the hash-owned package and the
two hash-owned images Xochitl derives in its `templates/import` cache after
restoring the pretrial manifest state. Paper Pro / Chiappa remains a separate
exact-resource target.

The initial notebook has only pages 1 and 2. Pages 3 and 4 are created inside
the same notebook at submit time. No `Letters Home *.pdf` or
`Letters Home Review *.pdf` is uploaded.

## One-page letter composition contract

Page 1 and page 4 use a fixed 10-column by 18-row grid: 180 glyph cells. Columns
are ordered right to left; cells within a column are ordered top to bottom.

- Hard capacity: 180 Chinese glyphs or punctuation cells.
- Provider target: 150 to 168 characters, so a normal result occupies nine or
  ten columns and leaves a safety margin.
- Each accepted character maps to one immutable `(column, row)` cell using its
  cumulative index. Previously displayed glyphs never move when a new batch
  arrives.
- Coordinates come from the template's declared grid, not `Text.implicitWidth`,
  toolbar visibility, or the size of a newline-joined string.
- Closing punctuation cannot begin a new column when it can remain with the
  preceding glyph. Chinese commas, full stops, enumeration commas, colons,
  semicolons, exclamation marks, and question marks receive explicit offsets
  within their cell. Quotes and brackets use explicit vertical glyph handling.
- The renderer returns a placement record for every accepted character. A
  mismatch between input count and placed-glyph count is an error, never a
  silent clip.

### Stable sentence streaming

Raw Codex deltas are accumulated privately. Only complete sentences ending in
`。`, `！`, or `？` become visible. A sentence is published only when the whole
sentence fits in the remaining cells. This creates a few meaningful e-ink-safe
batches and prevents a partial sentence from being stranded at the page edge.

The device reveals each newly published batch one immutable glyph at a time.
A 90 ms timer increases a visible-prefix count by exactly one until it catches
up with the server's cumulative glyph array. New server batches extend the
same prefix; they never reset or reposition a displayed glyph. This separates
model batching from the participant-facing writing rhythm without waiting for
the complete letter.

If another complete sentence would cross 180 cells, it is not published. The
already published complete-sentence prefix becomes the final letter. If the
first complete sentence alone cannot fit, or the fitted result is below 144
cells, the generation fails visibly and can be regenerated;
the bridge does not cut a sentence or invent an ending. Final model output is
validated against the same 180-cell contract.

## Page behavior

### Page 1: incoming letter

The qiao-pi template is the native notebook background. A non-interactive QML
layer polls cumulative session state at an e-ink-safe cadence and places each
new glyph into its fixed cell. The layer declares no mouse, tap, swipe, or pen
handlers. Stock document gestures continue underneath it.

### Page 2: handwritten huipi

Page 2 is an ordinary native notebook page. All stock pen, marker, eraser,
selection, layer, template, page, toolbar, close, and swipe behaviors remain.
The only added action is a stock-styled envelope submit action visible on this
page. There is no Letters Home header, replacement toolbar, or swipe-down menu.

The first accepted page-2 stroke emits the existing biometric-start event. A
submit closes that window atomically. Declined or unavailable heart-rate input
does not block correspondence. Live WHOOP authorization remains a separate
human-approved provider lane.

### Page 3: reversible marked copy

Submit first uses the verified stock page-management operation to duplicate
page 2 as page 3. Page 2 is never changed. The bridge exports the notebook for
review, renders only page 2 transiently, and begins the persisted Codex review
task.

Page 3 displays review geometry as a non-interactive reversible layer:

- only high-confidence, single-glyph corrections receive red ellipses;
- the correct glyph appears immediately beside its ellipse;
- uncertain readings use a neutral mark;
- concise explanations sit beside their mark when space allows;
- the short overall comment and reflective question use a compact bounded
  footer, with no large empty review card and no score.

The review layer is keyed by notebook and page ID. Original participant ink is
not copied into logs, issues, evidence, or session metadata.

### Page 4: reciprocal response

Submit also adds page 4 with the letter template. The persisted Codex review
task uses two turns: the first returns grounded structured corrections; the
second returns only the reciprocal Chinese letter. The second turn streams
through the same stable-sentence and 180-cell rules as page 1.

When the first response sentence is ready, the device advances from page 3 to
page 4 once, provided the participant has not manually navigated away. Later
batches update page 4 without reopening the notebook. The participant can
swipe back to page 3 or page 2 normally.

## Session state and APIs

One session record is keyed by pseudonymous session ID and bound to one native
document ID. The public tablet view contains only fields required to render the
experience:

- `phase`: `incoming`, `ready`, `reviewing`, `review-ready`,
  `response-streaming`, `complete`, or `failed`;
- monotonically increasing `version`;
- fitted incoming text;
- bounded correction and annotation geometry after review;
- fitted reciprocal response text;
- page IDs or indices required for guarded one-time navigation;
- a safe error code when a phase fails.

Start and submit return immediately after durable state is established. Long
Codex work runs in supervised background tasks. Codex thread and active-turn
identifiers are recorded before work begins so a bridge restart can reconcile
or resume the phase instead of creating another task. Duplicate start, bind,
submit, and navigation operations are idempotent.

Final incoming text, review geometry, review copy, and reciprocal text are
stored only in app-private state with mode `0600` and the configured encounter
expiry. They are deleted with the session. Participant ink remains in the
native notebook and in a transient review render only for the approved review
window; it is not added to bridge logs or identifier-only receipts.

The Mac bridge runs from a checked, dependency-complete Python runtime under a
real per-user LaunchAgent with a sanitized environment. Health includes both
the inbound tablet listener and an outbound read-only USB document probe; a
listener-only result is not considered ready.

## Failure behavior

- Bridge unavailable before launch: keep the sidebar open, restore the launcher
  label, and show a stock notification. Do not create an empty notebook.
- Native notebook creation or bind failure: leave any created notebook visible
  and safe, report the identifier-only failure, and permit an idempotent retry.
- Incoming generation failure: retain page 1 and offer regeneration. Page 2
  remains available.
- Submit or review failure: retain page-2 ink and the page-3 duplicate; show a
  stock retry notification. Do not create a replacement document.
- Response failure: keep the completed page-3 review and retry only the second
  turn.
- Reopen: derive the session from the notebook name and recover cumulative state
  without creating another task.
- Paired Mac unavailable while reopening: keep the native notebook usable and
  show a stock availability notification; never hide the stock close or page
  controls behind a blocking AI screen.

No failure handler replaces stock close or swipe behavior.

## Test-driven implementation

Implementation proceeds in small red-green cycles:

1. A grid-layout test proves that every input character up to 180 has exactly
   one in-bounds Ferrari cell and that the photographed 176-character fixture
   has no missing ending.
2. Sentence-stream tests prove stable prefixes, punctuation-aware boundaries,
   overflow refusal, and no character-level truncation.
3. Session tests prove notebook binding, phase transitions, idempotent submit,
   two turns in one Codex task, and restart-safe public state.
4. QML contract tests prove native notebook creation, native page add and
   duplication, template assignment, page-specific overlays, one-time guarded
   page-4 navigation, and the absence of PDF upload/open behavior.
5. Interaction tests prove there are no custom touch or swipe handlers and that
   the stock toolbar provider is unchanged.
6. Fixture review tests prove only grounded high-confidence corrections are red
   and that page 2 remains unmodified.
7. LaunchAgent tests prove an explicit Python runtime, sanitized environment,
   restart behavior, and bidirectional USB health.

Provider-dependent tests use fixture providers. Live Codex, tablet mutation,
Xovi restart, and biometric providers remain human-approved lanes.

## Physical Ferrari definition of done

The feature is test-ready only when all of the following are observed on the
pinned Ferrari target:

1. Tapping `Letters Home` creates and opens one entry whose native type is
   notebook; it creates no new PDF.
2. The notebook initially has exactly two pages with the app-owned templates.
3. A 150-to-180-cell fixture appears on page 1 in multiple stable sentence
   batches. Every fixture character is visible exactly once, all placements are
   in bounds, and no punctuation is orphaned.
4. Swiping to page 2 exposes the ordinary reMarkable writing experience,
   including stock pens, marker, eraser, layers, menus, close action, and swipe
   behavior.
5. Submit returns control immediately, preserves page 2, and creates pages 3
   and 4 in the same document ID.
6. A known wrong handwritten glyph is circled red on page 3 with the correct
   glyph adjacent; an uncertain glyph is not marked red. Page 2 is unchanged.
7. The first reciprocal sentence advances once to page 4 and later sentences
   stream into stable cells without reopening the document.
8. Closing and reopening the notebook recovers the same session instead of
   creating another Codex task.
9. Portable tests, `scripts/agent-evidence`, exact QMLDiff compatibility,
   structural apply, bidirectional bridge health, and device journal checks are
   green.
10. Installation backup and rollback restore all pretrial hashes and remove
    only app-owned QMD and template assets.
