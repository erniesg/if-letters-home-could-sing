# GitHub issue and VM queue approval packet

The complete proposed GitHub issue bodies are the nine numbered Markdown files in `docs/issues/`. They have passed the local portability/heading/dependency checks and Rucksack's dry-run parser.

## Labels

- All issues: `rucksack-ledger` — marks the issue as synced from a reviewed local spec.
- Issues 001–006 and 009 after the harness branch is on the default branch: `rucksack-queued` — safe fixture/mock/repo work for the trusted VM.
- Issues 007–008: `rucksack-needs-human` — tablet SSH, Xochitl/QMD mutation, and physical trials are held.

No issue is labelled for automatic merge or deployment. Live portions of 004 and 006 remain held by their stop conditions even while fixture/mock work is queued.

## Exact external-write commands after explicit confirmation

From a checkout containing the reviewed specs:

```bash
rucksack autopilot labels erniesg/if-letters-home-could-sing --execute
rucksack github issues seed erniesg/if-letters-home-could-sing \
  --issue-dir docs/issues \
  --label rucksack-ledger \
  --marker-prefix rucksack-issue-spec \
  --execute
```

After the harness is merged to the default branch, resolve issue numbers from the stable `rucksack-issue-spec:NNN` markers, add `rucksack-queued` only to 001–006 and 009, and add `rucksack-needs-human` to 007–008. Then run one supervised drain:

```bash
rucksack autopilot work-queue erniesg/if-letters-home-could-sing \
  --provider vm-codex \
  --max-workers 2 \
  --profile erniesg-ai-vm \
  --remote-root ~/code/erniesg \
  --reconcile-issues \
  --execute
```

The generated GitHub orchestration variable remains disabled. The command above is a supervised trusted-VM drain, not automatic merge, deployment, or tablet installation.

## Confirmation boundary

Do not run the label, seed, queue, or drain commands until the owner has reviewed these bodies and explicitly confirms creation. A broad request to plan the feature is not treated as approval of the final external issue bodies.
