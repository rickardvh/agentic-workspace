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
| How do I start in a repo? | `AGENTS.md` -> `TODO.md` -> active execplan when relevant | `ROADMAP.md` only when promoting work |
| Where should I point an external agent? | `llms.txt` | Richer docs only when the handoff file points there |
| Where is the post-bootstrap next action? | `.agentic-workspace/bootstrap-handoff.md` when bootstrap says review is still needed | Ad hoc chat instructions |
| How do I customize lifecycle defaults or update intent? | `agentic-workspace.toml` plus `agentic-workspace config --format json` | Ad hoc chat instructions or direct module metadata edits |
| How do I inspect modules? | `agentic-workspace modules --format json` | Read package docs directly when working on one package contract |
| How do I discover skills? | `agentic-workspace skills --format json` or `--task ...` | Read registries or `SKILL.md` files directly only when debugging or authoring skills |
| How do I validate? | Use the narrowest proving lane from the contributor playbook or machine-readable defaults | Broader package/root lanes only when the change crosses boundaries |
| How do I use both modules together? | `agentic-workspace init --preset full` plus the shared root lifecycle verbs | Direct package CLIs only when combined orchestration is not the goal |

## Machine-Readable Route

Use:

```bash
agentic-workspace defaults --format json
agentic-workspace config --target ./repo --format json
```

That surface is the queryable contract for:

- startup
- lifecycle
- supported intents
- canonical external-agent handoff
- canonical bootstrap next action
- delegated judgment boundaries
- skill discovery
- validation
- combined-install operation
- repo-owned lifecycle defaults and update intent

Use `docs/delegated-judgment-contract.md` when the question is not which command to run, but what the human should specify, what the agent may decide locally, and what should force promotion or escalation.

## Secondary Paths

Treat these as real but secondary:

- package-local CLIs
- maintainer-only commands
- debugging-oriented doctor or payload verification lanes
- direct registry or manifest reads when the structured CLI surface already answers the question

If a front-door surface makes the secondary path look equally primary, that is a docs-shape bug.
