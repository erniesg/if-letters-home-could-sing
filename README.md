# If Letters Home Could Sing — reMarkable correspondence experience

This repository is evolving the original heartbeat-responsive qiao pi prototype into a reMarkable Paper Pro and Paper Pro Move experience.

The intended interaction is deliberately small:

1. Tap a letter icon in the stock toolbar.
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

The earlier research prototype and qiao pi assets remain in place. A Rucksack harness has been added for fail-closed, evidence-producing work on the trusted VM. GitHub issue seeding, unattended queue activation, live credentials, and physical device installation remain human-reviewed gates.

Run the portable planning and contract checks with:

```bash
python3 -m unittest discover -s tests
scripts/agent-evidence
```

Legacy ML/data tests live under `legacy_tests/`, depend on private datasets, and are not the acceptance suite for this new experience until issue 001 makes that boundary reproducible.
