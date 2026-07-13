# Re-establish a reproducible build and test baseline

## Goal

Turn the current research repository into a clean-checkout workspace that can validate the new experience without private handwriting datasets, machine-specific paths, or implicit global dependencies. Preserve the legacy research code, but put it behind an explicit optional lane.

## Acceptance tests

- Add documented, pinned project metadata for the active Python and frontend workspaces, including a committed lockfile for the frontend.
- `scripts/agent-evidence` runs required portable tests from a clean checkout without network, secrets, GPU, or private datasets.
- Legacy dataset/ML tests are discoverable through an optional named command and report missing datasets as a setup block, not as a product-suite failure.
- Remove the machine-specific archive path from the legacy test fixture or replace it with a temporary synthetic archive.
- Add a regression test proving no WHOOP/OpenAI secret value or token substring is logged.
- Preserve current research assets and behaviour unless a change is required for reproducibility or secret redaction.

## Validation command

```bash
python3 -m unittest discover -s tests_contract
scripts/agent-evidence
```

## Allowed secrets

None. Dependency installation and all required tests must be credential-free.

## Artifact outputs

- Reproducible workspace metadata and lockfiles.
- Updated `.agent/commands.yaml` and verification documentation.
- Synthetic test fixtures replacing local absolute paths.
- Evidence manifest under `.agent/evidence/`.

## Stop conditions

Stop if reproducing a legacy test would require copying a private dataset, model checkpoint, or credential into the repository. Document it as an optional lane instead.

## Human clarification protocol

Ask only if two incompatible dependency sets cannot coexist without deleting a working legacy environment. Recommend isolating the new experience in its own workspace.

## Recommended response

Create an `experience/` workspace with its own pinned dependencies and keep legacy research requirements separate. Make the new contract/unit suite the required gate.

## Trade-offs

Separating the new product from legacy ML code adds workspace structure but avoids making every tablet change install large research dependencies and private corpora.

## Free-form response

Record any legacy tests left optional, their reason, and an exact opt-in command.
