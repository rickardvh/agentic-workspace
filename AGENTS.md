# Agent Instructions

Authority marker:

- authority: adapter
- canonical_source: `.agentic-workspace/config.toml` and `agentic-workspace start --target . --format json`
- safe_to_edit: true
- refresh_command: null

<!-- agentic-workspace:workflow:start -->
Read `.agentic-workspace/WORKFLOW.md` for shared workflow rules.
<!-- agentic-workspace:workflow:end -->

Keep this file thin. Treat it as the repo-owned startup adapter over the structured workspace surfaces under `.agentic-workspace/`.

## Startup

- Use `uv run agentic-workspace preflight --format json` when you want startup guidance, resolved config, and active state in one compact answer.
- Use `uv run agentic-workspace defaults --section startup --format json` when startup order or first-contact routing is the question.
- Use `uv run agentic-workspace config --target . --format json` when the configured entrypoint, posture, or workflow obligations matter.
- Use `uv run agentic-workspace summary --format json` when only active planning or ownership state is the question.
- Open module, planning, memory, or deeper routing files only when the compact answers point there.
- Read package-local `AGENTS.md` only for the package being edited.

## Repo Rules

- Do not bulk-read all planning surfaces.
- Keep package boundaries explicit.
- Preserve independent package versioning and CLI entry points.
- Keep repo-custom workflow obligations in `.agentic-workspace/config.toml`; let `AGENTS.md` stay a compact router.
