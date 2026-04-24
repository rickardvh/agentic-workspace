# Agent Instructions

<!-- agentic-workspace:workflow:start -->
Read `.agentic-workspace/WORKFLOW.md` for shared workflow rules.
<!-- agentic-workspace:workflow:end -->

Keep this file thin. Treat it as the repo-owned startup adapter over the structured workspace surfaces under `.agentic-workspace/`.

## Startup

1. Use `uv run agentic-workspace defaults --section startup --format json` when startup order or first-contact routing is the question.
2. Use `uv run agentic-workspace config --target . --format json` when the configured entrypoint, posture, or workflow obligations matter.
3. Use `uv run agentic-workspace summary --format json` when active planning or ownership state is the question.
4. Open the active execplan in `.agentic-workspace/planning/execplans/` only when those compact answers point there.
5. Read package-local `AGENTS.md` only for the package being edited.

## Repo Rules

- Do not bulk-read all planning surfaces.
- Keep package boundaries explicit.
- Preserve independent package versioning and CLI entry points.
- Keep repo-custom workflow obligations in `.agentic-workspace/config.toml`; let `AGENTS.md` stay a router into the compact startup and config surfaces.

## When Needed

- Read `SYSTEM_INTENT.md` when the task needs the repo's higher-level direction or design pull.
- Use `.agentic-workspace/config.toml` plus `uv run agentic-workspace report --target . --format json` when repo-local workflow expectations matter.
- Read `.agentic-workspace/docs/routing-contract.md` when execution hits a routing edge case or ambiguity.
- Read `.agentic-workspace/docs/lifecycle-and-config-contract.md` before editing CLI initialization or configuration logic.
- Read `.agentic-workspace/docs/extraction-and-discovery-contract.md` before changes that cross package source, package payload, and root install boundaries.
- Verify live GitHub issue state with `gh` before making claims about open or closed issues.
