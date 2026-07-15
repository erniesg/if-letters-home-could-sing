# If Letters Home Could Sing — reMarkable correspondence experience

This repository is evolving the original heartbeat-responsive qiao pi prototype into a reMarkable Paper Pro and Paper Pro Move experience.

The intended interaction is deliberately small:

1. Tap the `Letters Home` envelope entry in the stock main hamburger sidebar.
2. Receive a clearly fictional, AI-generated qiao pi-inspired letter.
3. Swipe to a blank `huipi` (回批) page and write a reply.
4. Submit to receive a third page of gentle marginal notes and reflection.
5. If the participant opts in, record heart rate from first ink to submission.

The implementation plan, constraints, TDD order, and definition of done live in:

- [`docs/product-brief.md`](docs/product-brief.md)
- [`docs/architecture.md`](docs/architecture.md)
- [`docs/definition-of-done.md`](docs/definition-of-done.md)
- [`docs/research/synthesis.md`](docs/research/synthesis.md)
- [`docs/issues/`](docs/issues/)

## Current status

The AppLoad window path is retired. The current Ferrari candidate opens a
full-bleed two-page PDF in stock Xochitl, submits the annotated huipi to a
persisted Codex task on the paired Mac, and imports a reviewed copy beginning on
page 3. Portable tests, exact-resource QMLDiff application, live Codex review,
live image generation, and exact-size PDF rendering pass. Physical installation
remains held until the connected tablet's USB web interface and current hashes
are re-confirmed.

## Reproducible workspaces

The active Python contract workspace supports Python 3.11 and 3.12. Portable
tests have no third-party runtime dependencies; the paired-Mac PDF renderer has
an explicit optional dependency group in `pyproject.toml`:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e '.[dev]'
python3 -m unittest discover -s tests

# Paired Mac only
python3 -m pip install -e '.[trusted-mac]'
```

The active frontend is pinned to Node `22.22.3` and npm `10.9.8`. Install exactly the committed dependency graph from its workspace:

```bash
cd frontend
nvm use
npm ci
npm run type-check
```

Run the portable planning and contract checks with:

```bash
python3 -m unittest discover -s tests
scripts/agent-evidence
```

The legacy fixture-first AppLoad UI and host simulator remain as regression
fixtures and can be exercised without Qt, a tablet, network access, or
credentials:

```bash
python3 -m tablet_app.simulator --profile chiappa --orientation portrait --scenario timeout-retry
python3 -m tablet_app.simulator --verify-snapshots tablet_app/snapshots
python3 -m tablet_app.packaging --check
```

See [`docs/tablet-simulator.md`](docs/tablet-simulator.md) for the AppLoad
source/bundle boundary. The live native path and run instructions are in
[`docs/mac-bridge.md`](docs/mac-bridge.md).

The rollback-safe dual-device packaging slice is fixture-only. See
[`docs/installer-recovery.md`](docs/installer-recovery.md) for the versioned
release manifest, synthetic Ferrari/Chiappa matrix, and held hardware gates.

Legacy ML/data tests live under `legacy_tests/` and remain an explicit optional lane because required datasets, mapping outputs, fonts, and parts of the historical pipeline are not available in a clean checkout. Their public dependency subset is pinned separately in `requirements-legacy.txt`. Run `scripts/legacy-tests` to preflight that setup; it exits `2` with a setup-block report when local research inputs are unavailable. Missing private inputs must not be copied into the repository.
