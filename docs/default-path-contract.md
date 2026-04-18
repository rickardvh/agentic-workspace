# Default Path Contract

This page records the normal route through Agentic Workspace.

Use it when you want the shortest correct answer for startup, lifecycle, skill discovery, validation, or combined installs.

## Purpose

- Make the normal path obvious.
- Keep advanced or package-local paths clearly secondary.
- Point to machine-readable output when the repo can answer through structure instead of richer prose.

## Inspection Order

Use this order for ordinary inspection work:

1. report or summary
2. narrow selector
3. raw file or richer prose only when the compact surface is insufficient

That means:

- use `agentic-planning-bootstrap summary --format json` before opening `TODO.md` or execplan prose when the question is active planning state
- use `agentic-workspace report --target ./repo --format json` before reading raw module files when the question is combined workspace state
- use defaults/proof/ownership selectors before broad docs when the question is already narrow

Use [`docs/which-package.md`](which-package.md) when you want the smaller operating-map view over those same buckets.
Use this page when you need the fuller route contract after the compact map points you here.

## Routine Planning Recovery

Use `agentic-planning-bootstrap summary --format json` first when the question is active planning recovery.

The minimum questions are:

| Question | Cheapest owner surface |
| --- | --- |
| What is active right now? | `planning_record` |
| What should I do next? | `resumable_contract.current_next_action` |
| What larger chunk or queue owns follow-on? | `hierarchy_contract` |
| What residue remains if this slice stops? | `follow_through_contract` |
| When do I fall back to prose? | only when the compact summary leaves the answer ambiguous |

Keep these answers on the compact summary path before opening raw `TODO.md` or execplan prose.
Use [`docs/execplans/README.md`](docs/execplans/README.md) for the meaning boundary and fallback pointer.

The compact rule is:

- machine-readable state keeps the restart-critical meanings that must survive a handoff cheaply
- compact prose keeps stable route guidance and framing when a queryable field would not reduce recovery cost enough to justify a second owner
- raw execplan detail keeps slice-local narrative, implementation notes, and change-log residue

Example: "What should I do next?" belongs in `resumable_contract`; the route that gets you there belongs in compact prose; the line-by-line change log belongs in raw execplan detail.

## Default Answers

| Question | Default path | Secondary path |
| --- | --- | --- |
| How do I install? | `agentic-workspace init --preset <memory|planning|full>` | Package CLIs for package-local maintainer work or debugging |
| How do I keep the profile lightweight? | `agentic-workspace init --preset memory` | Add planning only when the repo needs checked-in active execution state. |
| How do I express intent? | Pick the preset that matches the outcome you want, then inspect `agentic-workspace defaults --section intent --format json` for the confirmed/interpreted split | Manually reasoning about lifecycle verbs before asking the tool |
| How do I cheaply clarify a vague prompt? | `agentic-workspace defaults --section clarification --format json` | Turning the vague prompt into broad repo rereads |
| How do I route a vague prompt to the right lane? | `agentic-workspace defaults --section prompt_routing --format json` | Guessing at proof or owner from the prompt alone |
| How do I hand the compact contract from planner to implementer? | `agentic-workspace defaults --section relay --format json`, then `agentic-planning-bootstrap handoff --format json` for the active delegated slice | Freezing the handoff without routed Memory, a clear planner/implementer split, or a checked-in active handoff |
| How do I start in a repo? | The configured root startup file from `agentic-workspace config --target ./repo --format json` (default `AGENTS.md`) -> `TODO.md` -> active execplan when relevant | `ROADMAP.md` only when promoting work |
| How do I inspect current active planning state? | `agentic-planning-bootstrap summary --format json` and the routine planning recovery questions above | Reading raw `TODO.md` or execplan prose first |
| How do I inspect current long-horizon planning candidates? | `agentic-planning-bootstrap summary --format json` and its `roadmap.candidates` list, then `ROADMAP.md` only when the thin candidate view is not enough | Reading narrative roadmap prose first |
| How do I inspect combined workspace state? | `agentic-workspace report --target ./repo --format json` and its `schema` plus report payload | Reading raw module files before the report |
| Where do I inspect the effective repo output posture during startup or recovery? | `agentic-workspace config --target ./repo --format json` and `workspace.optimization_bias` | Guessing from rendered report density or broad prose alone |
| How do I inspect mature-repo setup candidates? | `agentic-workspace setup --target ./repo --format json` and its compact orientation payload | Guessing at Memory/Planning candidates by reading prose first |
| Where is the bounded post-bootstrap setup contract? | [`docs/jumpstart-contract.md`](docs/jumpstart-contract.md) and `agentic-workspace setup --target ./repo --format json` | Treating setup as a wider `init` path or a repo-local checklist |
| Where is the setup findings promotion contract? | [`docs/setup-findings-contract.md`](docs/setup-findings-contract.md) plus `agentic-workspace setup --target ./repo --format json`; use `tools/setup-findings.json` only when setup or jumpstart already produced promotable findings | Building a workspace-owned analyzer, keeping a noisy findings file around by default, or preserving every setup finding automatically |
| Where is the proof-selection contract? | `agentic-workspace defaults --section proof_selection --format json` and [`docs/proof-surfaces-contract.md`](docs/proof-surfaces-contract.md) | Mining prose for the narrowest proof lane first |
| Where is the delegation posture contract? | [`docs/delegation-posture-contract.md`](docs/delegation-posture-contract.md) and `agentic-workspace defaults --section delegation_posture --format json` | Treating config as a scheduler or ignoring the effective mixed-agent posture |
| Where is the bounded repo-friction initiative contract? | `agentic-workspace defaults --section improvement_latitude --format json` plus `agentic-workspace report --target ./repo --format json`; that surface governs repo-directed initiative, not bounded workspace-self-adaptation inside Agentic Workspace-owned surfaces, and it spells out the default friction-response order | Treating one hotspot as blanket permission for broad cleanup, reading `improvement_latitude = none` as if it also froze legitimate workspace self-improvement, or jumping straight to repo cleanup when the workspace itself is the cheaper honest fix |
| Where is validation friction defined? | `agentic-workspace report --target ./repo --format json` and `agentic-workspace defaults --section improvement_latitude --format json`; `validation_friction` is repo-friction evidence for weak seams, bad tranche boundaries, unclear proof contracts, or validation bounce/re-entry | Treating ordinary bug-fixing, one-off failures, or inherently difficult domains as if they were all validation-friction signals |
| Where should I point an external agent? | The repository's `llms.txt` | Richer docs only when that handoff file points there |
| Where is the post-bootstrap next action? | `.agentic-workspace/bootstrap-handoff.md` when bootstrap says review is still needed | Ad hoc chat instructions |
| Where is the compact bootstrap handoff contract? | `.agentic-workspace/bootstrap-handoff.json` when bootstrap writes a checked-in finishing handoff | Mining the prose brief for scope or escalation boundaries |
| How do I customize lifecycle defaults or update intent? | `agentic-workspace.toml` plus `agentic-workspace config --format json` to see whether repo policy is authoritative or defaults-only | Ad hoc chat instructions or direct module metadata edits |
| How do native runtime planning artifacts fit? | `agentic-workspace defaults --section workflow_artifact_adapters --format json` plus `agentic-workspace config --target ./repo --format json` | Letting `implementation_plan.md`, `task.md`, or similar files become an untracked second source of truth |
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
- post-bootstrap setup
- setup findings promotion
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
- improvement-latitude policy and current repo-friction evidence
- planning-friction as repo-friction evidence when the smallest safe slice or proof path stays unclear
- validation-friction as repo-friction evidence when validation repeatedly stalls on unclear seams, tranche boundaries, proof contracts, or rerun/re-entry paths
- effective repo output posture through `workspace.optimization_bias`
- current mixed-agent reporting boundaries

Use this broad route when the question spans several contract domains.
If one bounded answer is enough, stop at the narrow selector instead of loading a broader dump or opening raw files first.

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
Use [`docs/jumpstart-contract.md`](docs/jumpstart-contract.md) when the question is how to do the bounded post-bootstrap setup follow-through after safe install/adopt without widening `init`.
Use [`docs/setup-findings-contract.md`](docs/setup-findings-contract.md) when the question is which agent-produced setup findings should stay transient versus be routed into reporting or planning.
Use [`docs/delegation-posture-contract.md`](docs/delegation-posture-contract.md) when the question is whether to stay direct, split into planner/implementer/validator subtasks, or escalate to a stronger planner under the current config-controlled posture.

## Secondary Paths

Treat these as real but secondary:

- raw `TODO.md`, `ROADMAP.md`, and execplan prose for routine state inspection
- package-local CLIs
- maintainer-only commands
- debugging-oriented doctor or payload verification lanes
- direct registry or manifest reads when the structured CLI surface already answers the question

If a front-door surface makes the secondary path look equally primary, that is a docs-shape bug.
