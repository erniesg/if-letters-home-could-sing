# Verification

Before claiming completion, run the evidence command and attach the manifest.

```bash
scripts/agent-evidence
```

Optional lanes are opt-in:

```bash
scripts/agent-evidence --e2e
scripts/agent-evidence --only=lint,type-check
# If wrapped in npm, pass flags after `--`: npm run agent:evidence -- --e2e
```

Validation lanes discovered:

- `python-test`: `python3 -m unittest discover -s tests` (required product-contract suite)
- `legacy-python-test`: `scripts/legacy-tests` (optional historical research suite)

The required lane must be green without network, private corpora, a GPU, a tablet, or provider credentials. The optional legacy command preflights its historical modules, private datasets, generated mappings, and font before running `pytest`; unavailable setup exits with code `2` and is not product-suite coverage or failure. Install the pinned public subset with `python3 -m pip install -r requirements-legacy.txt`, but do not copy missing private inputs or unrecovered research modules into the repository.

Deploy contract:

- `.agent/deploy.yaml` records provider-neutral deploy and infrastructure gates.
- Deploy, rollback, and infrastructure apply lanes require trusted context and human approval.
- `scripts/agent-evidence` does not execute secret-bearing deploy commands.
- When `.agent/storage.yaml` exists, `scripts/agent-evidence` records large untracked files over `repo_limit_mb` as manifest caveats and artifact entries.
- `infra/vm/verify.sh` is the reusable trusted-VM health and hardening check.
- Detected deploy/IaC hints:
  - `docker` via `docker` from `Dockerfile`.

Exit taxonomy:

- `0`: required validation passed
- `1`: required validation failed
- `2`: blocked by missing dependency or environment setup
- `3`: blocked by missing auth/secret or subscription/browser state
- `4`: blocked by required human decision
