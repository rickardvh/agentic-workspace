# Agent Instructions

Authority marker:

- authority: adapter
- canonical_source: `.agentic-workspace/config.toml` and `uv run python scripts/run_agentic_workspace.py start --target . --format json`
- safe_to_edit: true
- refresh_command: null

<!-- agentic-workspace:workflow:start -->
Ordinary route:
1. Use `uv run python scripts/run_agentic_workspace.py start --task "<task>" --format json` before non-trivial answers, edits, read-only workflow, config, delegation, or action-safety decisions.
2. Use `uv run python scripts/run_agentic_workspace.py implement --changed <paths> --task "<task>" --format json` when changed paths are already known.
3. Follow `next_safe_action`, `action_signals`, and `skills` before opening raw `.agentic-workspace` files or running drill-down commands.
4. When implementing an issue, satisfy the intended end state in the ordinary path; ask for clarification instead of closing with a partial path when the full outcome appears larger than the issue safely permits.

Boundaries:
- The effective invocation comes from `.agentic-workspace/config.toml` `[workspace].cli_invoke`; `.agentic-workspace/config.local.toml` may override it.
- Known dedicated Agentic Workspace commands are allowed only when the request maps directly to that command and no takeover, recovery, active-planning, or ambiguous safety decision is needed first.
- Do not try a bare `agentic-workspace` command first when the effective invocation names a repo-local or dev-dependency command; PATH may resolve a stale installed selector.
- Treat `preflight`, `config`, `defaults`, `skills`, `modules`, `ownership`, and `report` as routed drill-down or recovery surfaces, not the ordinary startup loop.
- Report repo-relative paths, not local absolute paths.
- If the effective CLI is unavailable after trying it, immediately read `.agentic-workspace/WORKFLOW.md` before any other files.
<!-- agentic-workspace:workflow:end -->
