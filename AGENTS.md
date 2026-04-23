# Agent Instructions

<!-- agentic-workspace:workflow:start -->
Read `.agentic-workspace/WORKFLOW.md` for shared workflow rules.
<!-- agentic-workspace:workflow:end -->

Keep this file thin. Treat it as the repo-owned startup adapter over the structured workspace surfaces under `.agentic-workspace/`.

## Startup

1. Read `AGENTS.md`.
2. Use `agentic-workspace defaults --section startup --format json` when startup order or first-contact routing is the question.
3. Use `agentic-workspace config --target . --format json` when the configured entrypoint, posture, or workflow obligations matter.
4. Use `agentic-workspace summary --format json` when active planning or ownership state is the question.
5. Open raw planning state, an active execplan, or deeper routing docs only when those compact answers point there.
6. Read package-local `AGENTS.md` only for the package being edited.

## Repo Rules

- Do not start coding from chat context alone when the same information exists in checked-in files.
- Do not bulk-read all planning surfaces.
- Keep package boundaries explicit.
- Preserve independent package versioning and CLI entry points.

## When Needed

- Read `SYSTEM_INTENT.md` when the task needs the repo's higher-level direction or design pull.
- Use `.agentic-workspace/config.toml` plus `agentic-workspace report --target . --format json` when repo-local workflow expectations matter.
- Read `.agentic-workspace/docs/routing-contract.md` when execution hits a routing edge case or ambiguity.
- Read `.agentic-workspace/docs/lifecycle-and-config-contract.md` before editing CLI initialization or configuration logic.
- Read `.agentic-workspace/docs/extraction-and-discovery-contract.md` before changes that cross package source, package payload, and root install boundaries.
- Verify live GitHub issue state with `gh` before making claims about open or closed issues.
