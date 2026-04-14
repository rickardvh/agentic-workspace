# Default Path Contract

This page records the normal route through Agentic Workspace.

Use it when you want the shortest correct answer for startup, lifecycle, skill discovery, validation, or combined installs.

## Purpose

- Make the normal path obvious.
- Keep advanced or package-local paths clearly secondary.
- Point to machine-readable output when the repo can answer through structure instead of richer prose.

## Default Answers

| Question | Default path | Secondary path |
| --- | --- | --- |
| How do I install? | `agentic-workspace init --preset <memory|planning|full>` | Package CLIs for package-local maintainer work or debugging |
| How do I express intent? | Pick the preset that matches the outcome you want and let `init` infer install vs adopt vs review-required handoff | Manually reasoning about lifecycle verbs before asking the tool |
| How do I start in a repo? | The configured root startup file from `agentic-workspace config --target ./repo --format json` (default `AGENTS.md`) -> `TODO.md` -> active execplan when relevant | `ROADMAP.md` only when promoting work |
| How do I inspect current active planning state? | `agentic-planning-bootstrap summary --format json` and its `planning_record` object | Reading raw `TODO.md` or execplan prose first |
| How do I inspect combined workspace state? | `agentic-workspace report --target ./repo --format json` and its `schema` plus report payload | Reading raw module files before the report |
| How do I inspect mature-repo jumpstart candidates? | `agentic-workspace report --target ./repo --format json` and its `discovery` object | Guessing at Memory/Planning candidates by reading prose first |
| Where is the bounded post-bootstrap jumpstart contract? | [`docs/jumpstart-contract.md`](docs/jumpstart-contract.md) and `agentic-workspace defaults --section jumpstart --format json` | Treating jumpstart as a wider `init` path or a repo-local checklist |
| Where is the proof-selection contract? | `agentic-workspace defaults --section proof_selection --format json` and [`docs/proof-surfaces-contract.md`](docs/proof-surfaces-contract.md) | Mining prose for the narrowest proof lane first |
| Where is the delegation posture contract? | [`docs/delegation-posture-contract.md`](docs/delegation-posture-contract.md) and `agentic-workspace defaults --section delegation_posture --format json` | Treating config as a scheduler or ignoring the effective mixed-agent posture |
| Where should I point an external agent? | The repository's `llms.txt` | Richer docs only when that handoff file points there |
| Where is the post-bootstrap next action? | `.agentic-workspace/bootstrap-handoff.md` when bootstrap says review is still needed | Ad hoc chat instructions |
| Where is the compact bootstrap handoff contract? | `.agentic-workspace/bootstrap-handoff.json` when bootstrap writes a checked-in finishing handoff | Mining the prose brief for scope or escalation boundaries |
| How do I customize lifecycle defaults or update intent? | `agentic-workspace.toml` plus `agentic-workspace config --format json` to see whether repo policy is authoritative or defaults-only | Ad hoc chat instructions or direct module metadata edits |
| How do I inspect modules? | `agentic-workspace modules --format json` | Read package docs directly when working on one package contract |
| How do I discover skills? | `agentic-workspace skills --format json` or `--task ...` | Read registries or `SKILL.md` files directly only when debugging or authoring skills |
| How do I validate? | Use the narrowest proving lane from the contributor playbook or machine-readable defaults | Broader package/root lanes only when the change crosses boundaries |
| How do I use both modules together? | `agentic-workspace init --preset full` plus the shared root lifecycle verbs | Direct package CLIs only when combined orchestration is not the goal |

## Machine-Readable Route

Use:

```bash
agentic-workspace defaults --format json
agentic-workspace config --target ./repo --format json
agentic-workspace proof --target ./repo --format json
agentic-workspace report --target ./repo --format json
agentic-workspace ownership --target ./repo --format json
```

That surface is the queryable contract for:

- startup
- lifecycle
- post-bootstrap jumpstart
- delegation posture
- supported intents
- canonical external-agent handoff
- canonical bootstrap next action
- delegated judgment boundaries
- skill discovery
- validation
- proof surfaces
- ownership mapping
- combined-install operation
- shared workspace reporting
- repo-owned lifecycle defaults and update intent
- current mixed-agent reporting boundaries

When one bounded answer is enough, prefer the compact selector path:

```bash
agentic-workspace defaults --section validation --format json
agentic-workspace proof --target ./repo --current --format json
agentic-workspace ownership --target ./repo --concern active-execution-state --format json
```

Use [`docs/compact-contract-profile.md`](docs/compact-contract-profile.md) for the compact answer envelope and the first narrow-selector contract.
Use `docs/delegated-judgment-contract.md` when the question is not which command to run, but what the human should specify, what the agent may decide locally, and what should force promotion or escalation.
Use the `validation` section in `agentic-workspace defaults --format json` when the missing judgment is which proving lane is enough, when broader checks are required, and when the change should escalate beyond the narrow lane.
Use `agentic-workspace defaults --section proof_selection --format json` when the missing judgment is which proof lane is enough, when broader proof is required, or when proof should escalate.
Use `docs/environment-recovery-contract.md` when the question is how to recover cheaply from repo-state ambiguity, lifecycle warnings, or interrupted bootstrap/maintenance work.
Use `docs/proof-surfaces-contract.md` when the question is which proof lane answers the current trust question and what the current proof state already says.
Use `docs/ownership-authority-contract.md` when the question is which surface owns a concern and which checked-in contract is authoritative.
Use [`docs/jumpstart-contract.md`](docs/jumpstart-contract.md) when the question is how to do the bounded post-bootstrap follow-through after safe install/adopt without widening `init`.
Use [`docs/delegation-posture-contract.md`](docs/delegation-posture-contract.md) when the question is whether to stay direct, split into planner/implementer/validator subtasks, or escalate to a stronger planner under the current config-controlled posture.

## Secondary Paths

Treat these as real but secondary:

- package-local CLIs
- maintainer-only commands
- debugging-oriented doctor or payload verification lanes
- direct registry or manifest reads when the structured CLI surface already answers the question

If a front-door surface makes the secondary path look equally primary, that is a docs-shape bug.
