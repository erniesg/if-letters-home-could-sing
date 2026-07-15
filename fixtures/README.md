# Checked-in experience fixtures

## Incoming letter

`generated/incoming-qiaopi-001.png` is the first fictional, AI-generated incoming-letter fixture.

Its machine-readable prompt, provenance, fictional status, provider/model record,
timestamps, dimensions, and checksums are pinned in
`generated/incoming-qiaopi-001.json`.

- Generated: 2026-07-14
- Source prompt: `docs/fixtures/incoming-qiaopi.prompt.md`
- Visual references: the two locally supplied qiao pi photographs, used only for broad material vocabulary
- Provenance: fictional; not an archival reconstruction
- Native generation dimensions: 1086 × 1448, portrait 3:4
- SHA-256: `a94cd86d5b3a7bcd82e93fcf319c080f5d084e110de02780aff43eacbbd8082e`
- Usage: visual fixture only; production adapters must transform/cache against the device render profiles

The app must display the separate disclosure `Fictional letter generated for this encounter` and must not present the image as a museum accession.

`generated/incoming-qiaopi-ferrari-001.png` is the reviewed Ferrari / Paper Pro
Move landscape fixture generated with Codex's built-in image capability. Its
exact prompt, source checksum, deterministic profile transform, visual-review
record, and final checksum are pinned in
`generated/incoming-qiaopi-ferrari-001.json`.

- Generated: 2026-07-15 (Asia/Singapore)
- Source prompt: `docs/fixtures/incoming-qiaopi-ferrari.prompt.md`
- Visual references: none supplied to the generator
- Provenance: fictional; not an archival reconstruction
- Native Ferrari dimensions: 1696 x 954
- SHA-256: `d8053206b0883fa4b39f3a6cbac9475bec34098586114c9562cb87f812b9495c`
- Usage: reviewed Ferrari incoming-page test fixture

## Blank huipi stationery

`reply/reply-chiappa.svg` and `reply/reply-ferrari.svg` are deterministic blank reply surfaces for the two portrait device profiles. They contain only paper, fold, border, and writing-guide geometry: no text, raster image, handwriting, stamp, receipt field, signature, or remittance mark.

The SVGs are review fixtures and fallback assets. The production QML component may draw the same geometry directly, but snapshot output must remain equivalent and preserve the ink layer independently.
