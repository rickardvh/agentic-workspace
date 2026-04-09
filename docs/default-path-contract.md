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
| How do I start in a repo? | `AGENTS.md` -> `TODO.md` -> active execplan when relevant | `ROADMAP.md` only when promoting work |
| How do I inspect modules? | `agentic-workspace modules --format json` | Read package docs directly when working on one package contract |
| How do I discover skills? | `agentic-workspace skills --format json` or `--task ...` | Read registries or `SKILL.md` files directly only when debugging or authoring skills |
| How do I validate? | Use the narrowest proving lane from the contributor playbook or machine-readable defaults | Broader package/root lanes only when the change crosses boundaries |
| How do I use both modules together? | `agentic-workspace init --preset full` plus the shared root lifecycle verbs | Direct package CLIs only when combined orchestration is not the goal |

## Machine-Readable Route

Use:

```bash
agentic-workspace defaults --format json
```

That surface is the queryable contract for:

- startup
- lifecycle
- skill discovery
- validation
- combined-install operation

## Secondary Paths

Treat these as real but secondary:

- package-local CLIs
- maintainer-only commands
- debugging-oriented doctor or payload verification lanes
- direct registry or manifest reads when the structured CLI surface already answers the question

If a front-door surface makes the secondary path look equally primary, that is a docs-shape bug.
