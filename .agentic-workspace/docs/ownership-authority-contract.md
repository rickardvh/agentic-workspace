# Ownership And Authority Contract

## Purpose

This document records the normal ownership and authority boundaries for the repository.

Use it when the question is:

- who owns this concern?
- which checked-in surface is authoritative?
- is this repo-owned, product-managed, or only a managed fence inside a repo-owned file?

## Rule

Resolve the owner and authoritative surface before changing or trusting a contract.

Do not infer ownership from whichever copy is most visible in the current working tree.

## Default Ownership Surface

Use:

```bash
agentic-workspace ownership --target ./repo --format json
```

That command is the workspace-level query surface for:

- the canonical ownership contract
- the current ownership ledger path
- ownership classes
- module-managed roots
- managed fences
- the main authority surfaces by concern
- the current boundary review that separates package-owned state, repo-owned state, and the smallest explicit repo hook

When the question is already narrow, prefer the compact selector path:

```bash
agentic-workspace ownership --target ./repo --concern active-execution-state --format json
agentic-workspace ownership --target ./repo --path .agentic-workspace/planning/state.toml --format json
```

When the question is who should own a vague prompt after one repo-context clarification, use:

```bash
agentic-workspace defaults --section prompt_routing --format json
```

Those forms return the compact contract answer profile from [`.agentic-workspace/docs/compact-contract-profile.md`](.agentic-workspace/docs/compact-contract-profile.md) instead of the full ownership object.

## Main Authority Surfaces

| Concern | Primary surface | Owner | Ownership class |
| --- | --- | --- | --- |
| Repo startup instructions | `AGENTS.md` | repo | `repo_owned` |
| Package-managed memory home | `.agentic-workspace/memory/` | memory | `module_managed` |
| Active execution state | `.agentic-workspace/planning/state.toml` (`todo.active_items`) | planning | `module_managed` |
| Long-horizon candidate queue | `.agentic-workspace/planning/state.toml` (`roadmap`) | planning | `module_managed` |
| Design constraints for product-shape changes | `docs/design-principles.md` | repo | `repo_owned` |
| Shared workflow contract | `.agentic-workspace/WORKFLOW.md` | workspace | `module_managed` |
| Ownership ledger | `.agentic-workspace/OWNERSHIP.toml` | workspace | `module_managed` |
| Product-managed planning install tree | `.agentic-workspace/planning/` | planning | `module_managed` |
| Workflow pointer block inside `AGENTS.md` | fenced block in `AGENTS.md` | workspace | `managed_fence` |

Root `.agentic-workspace/memory/repo/`, root config, and hybrid `docs/` surfaces remain boundary-review targets under issue `#231`.
Do not treat them as settled repo-owned authority surfaces merely because they are repo-specific or currently root-visible.

## Ownership Classes

- `repo_owned`
  - Repository-native state owned by the repo.
  - Installed packages should not silently replace it.
- `managed_fence`
  - Product-managed content inside an explicit fence within a repo-owned file.
  - The file stays repo-owned; only the fenced block is managed.
- `module_managed`
  - Upgrade-replaceable content owned by one installed module under `.agentic-workspace/`.

## Boundaries

- Keep one primary owner per concern.
- Keep package-local behavior package-local.
- Keep the workspace layer queryable and thin; it should expose ownership, not absorb domain ownership from planning or memory.
- Treat generated-surface trust as related but separate: ownership says who owns a surface, not whether a mirror is fresh.
- Use the full `agentic-workspace ownership --target ./repo --format json` surface to inventory package-owned, repo-owned, and middle-ground surfaces before changing install or uninstall behavior.

## Boundary Review

The full ownership payload includes a `boundary_review` section that groups the current surface set into:

- package-owned module roots and managed surfaces under `.agentic-workspace/`
- explicit package-owned local-only state inside `.gemini/agentic-workspace/`
- repo-owned authority surfaces such as `AGENTS.md` and `docs/design-principles.md`
- module-managed memory support surfaces such as `.agentic-workspace/memory/`
- module-managed planning authority such as `.agentic-workspace/planning/state.toml`
- middle-ground managed fences inside repo-owned files, with the workflow pointer fence in `AGENTS.md` as the smallest explicit repo hook for startup

Use that review when the task is boundary work, low-residue install/uninstall work, or any change that needs a current surface inventory before implementation.

## Relationship To Other Docs

- Use [`.agentic-workspace/docs/compact-contract-profile.md`](.agentic-workspace/docs/compact-contract-profile.md) when you want a one-answer ownership lookup instead of the full ledger report.
- Use [`.agentic-workspace/docs/proof-surfaces-contract.md`](.agentic-workspace/docs/proof-surfaces-contract.md) when the question is which proof lane establishes trust.
- Use [`.agentic-workspace/docs/generated-surface-trust.md`](.agentic-workspace/docs/generated-surface-trust.md) when the question is whether a generated mirror is stale or hand-edited.
- Use [`.agentic-workspace/docs/compatibility-policy.md`](.agentic-workspace/docs/compatibility-policy.md) when the question is whether a surface is stable, mutable, or generated.
