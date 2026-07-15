# Rucksack Issue Ledger

This directory stores reviewable markdown issue specs for `erniesg/if-letters-home-could-sing`.

## Reviewed build order

| Spec | Slice | Lane | Dependency | Initial queue intent |
|---|---|---|---|---|
| 001 | Reproducible baseline | portable | — | first |
| 002 | Experience core | portable | 001 | after 001 |
| 003 | AppLoad UI + simulator | portable/trusted VM | 002 | after 002 |
| 004 | GPT Image 2 adapter | portable; live proof held | 002 | parallel after 002 |
| 005 | Reply review + marginalia | portable/trusted VM | 002, 003 | after 003 |
| 006 | WHOOP BLE relay | portable; live proof held | 002 | parallel after 002 |
| 007 | Toolbar QMLDiff spike | hardware, human gate | 003 | held |
| 008 | Installer + device trials | hardware, human gate | 003, 005, 006, 007 | held |
| 009 | Privacy + installation export | portable/trusted VM | 005, 006 | after 005/006 |
| 010 | Native document + Mac Codex round trip | portable/trusted Mac/hardware | 004, 005, 007, 008 | human-held trial |

The first autonomous run should use specs 001–006 and 009 only. Specs 007–008 and 010 stay held until the physical-device mutation plan is approved. Within 004, 006, and 010, portable fixture/mock work may proceed; live provider calls remain human gates.

Issue bodies in this directory are the proposed GitHub bodies. Review them before running labels/seed commands. Seeding is idempotent by the stable spec marker but still creates or updates external issues.

Generate or update specs with:

```bash
rucksack github issues plan erniesg/if-letters-home-could-sing --repo-root . --issue-dir docs/issues --execute
```

After reviewing the generated specs, seed or update held ledger issues without
making them runnable:

```bash
rucksack github issues seed erniesg/if-letters-home-could-sing --issue-dir docs/issues --label rucksack-ledger --execute
```

Seeding preserves GitHub issue state and never reopens a closed marker-matched
issue. Reopen only a reviewed unfinished issue explicitly before seeding:

```bash
gh issue reopen ISSUE_NUMBER --repo erniesg/if-letters-home-could-sing
```

The GitHub queue workflow is skipped by default. Only after the separate agent
and publisher boundary is reviewed and live-proven may an authorized maintainer
activate GitHub queue orchestration explicitly:

```bash
gh workflow enable rucksack-autopilot.yml --repo erniesg/if-letters-home-could-sing
gh variable set RUCKSACK_AUTOPILOT_ENABLED --repo erniesg/if-letters-home-could-sing --body true
rucksack autopilot reconcile erniesg/if-letters-home-could-sing --issue-dir docs/issues --queue-after-activation --execute
gh workflow run rucksack-autopilot.yml --repo erniesg/if-letters-home-could-sing -f action=queue
```

The reconcile command verifies that the variable is exactly `true`, the
workflow is active, and its default-branch content exactly matches the safe
generated contract before it adds any queue label.

That variable activates GitHub issue/label orchestration only. It does not
enable VM drains, hosted agent builds, deploys, or automatic merge.

After activation, GitHub issues are the live queue. Use `/rucksack run #123`, `/rucksack queue`,
or labels such as `rucksack-queued` and `rucksack-run` to dispatch work. When
Rucksack asks for a decision, reply `/rucksack accept`, `/rucksack approve`, or
`/rucksack resolve` on the issue to clear decision/blocker labels and queue it.
For human-unlocked gates that need trusted local or VM proof first, reply
`/rucksack accept-proof #123`; GitHub will hold the issue for
`rucksack autopilot resolve erniesg/if-letters-home-could-sing --issue 123 --decision accept --repo-root <checkout> --run-post-unlock --execute`
instead of dispatching cloud work immediately.
When review evidence is accepted, use `/rucksack done #123` or
`rucksack autopilot resolve erniesg/if-letters-home-could-sing --issue 123 --decision done --execute` to
close the reviewed issue without dispatching more implementation work.

Issue specs may include an optional `## Provider` section to route one issue
away from the repo default:

```markdown
## Provider

claude
```

`provider` accepts `codex-action`, `vm-codex`, or `claude` while unmarked issues
use the repo default. `vm-codex` and `claude` route to supervised trusted-VM
invocation; `codex-action` is held fail-closed until hosted build and
publication have separate token boundaries. Specs may also include top-level
`depends-on: 001,002` metadata immediately under `# Title`, or a `## Depends on`
section with comma-separated or bullet-listed spec ids:

```markdown
## Depends on

- 001
- 002
```

Both dependency forms keep an issue queued until each dependency is closed or
labeled `rucksack-awaiting-review`; dependency cycles are rejected when specs
are seeded.

For local-first overnight checks before a remote queue exists, select the next
ready checked-in spec without requiring GitHub:

```bash
rucksack autopilot next erniesg/if-letters-home-could-sing --repo-root . --issue-dir docs/issues --provider vm-codex
```

Local-only ledgers can mark reviewed or held specs with top-level `state: done`
or `labels: rucksack-blocked`; the GitHub-backed queue remains the live source
once issues are seeded. After a local work slice validates, prepare PR-ready
text without requiring an `origin` remote:

```bash
rucksack autopilot submit erniesg/if-letters-home-could-sing --issue 123 --repo-root . --execute
```

## Label state machine

These labels are Rucksack's GitHub Issues state machine. They are not topic
tags; they let GitHub Actions, a trusted VM, and humans recover queue state from
the repository without a separate database.

| Label | Meaning |
|---|---|
| `rucksack-ledger` | Generated or synced from markdown specs. |
| `rucksack-queued` | Ready for the queue drain. |
| `rucksack-run` | Manual run-this-now trigger. |
| `rucksack-running` | Build workflow is running or leased. |
| `rucksack-needs-clarification` | Definition of done is unclear; ask/ping before building. |
| `rucksack-needs-decision` | Rucksack recommended a path and needs human approval. |
| `rucksack-needs-human` | Human login/secret/action is required. |
| `rucksack-provider-limited` | Provider quota or subscription limit paused this issue. |
| `rucksack-out-of-work` | No ready implementation work remains; recommend or seed more. |
| `rucksack-blocked` | Failed, held, or waiting on external action. |
| `rucksack-awaiting-review` | PR/evidence is ready for review. |
| `rucksack-review-feedback` | Actionable review feedback was found and repair was requeued. |
| `rucksack-waiting-checks` | Fresh PR checks are still pending or missing. |
| `rucksack-waiting-rereview` | PR is waiting for reviewer re-review. |
| `rucksack-merge-ready` | PR is eligible for merge-policy handling. |
| `rucksack-merge-blocked` | Guarded merge policy does not authorize this PR head. |

The installed `.github/workflows/rucksack-ledger.yml` workflow intentionally
refuses hosted generative planning without checking out the repository or
receiving GitHub/OpenAI credentials. Run the local plan command on the trusted
VM, review the generated specs, and seed only the approved files.
