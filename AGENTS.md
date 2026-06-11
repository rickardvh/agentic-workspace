# Agent Instructions

Authority marker:

- authority: adapter
- canonical_source: `.agentic-workspace/config.toml` and `uv run python scripts/run_agentic_workspace.py start --target . --format json`
- safe_to_edit: true
- refresh_command: null

<!-- agentic-workspace:workflow:start -->
Before answering or editing non-trivial requests, including read-only workflow, config, delegation, or action-safety decisions, use `uv run python scripts/run_agentic_workspace.py start --task "<task>" --format json` as the ordinary first-contact router for this repo. This value is resolved from `.agentic-workspace/config.toml` `[workspace].cli_invoke`; if `.agentic-workspace/config.local.toml` explicitly overrides it, use that local value. When changed paths are already known, use `uv run python scripts/run_agentic_workspace.py implement --changed <paths> --task "<task>" --format json` for bounded implementer posture. When the user request already maps to a known dedicated Agentic Workspace command and no takeover, recovery, active-planning, or ambiguous safety decision is needed first, run that dedicated command directly. Do not try a bare `agentic-workspace` command first when the effective invocation names a repo-local or dev-dependency command; PATH may resolve a stale installed selector. Do not open raw `.agentic-workspace` files before this command; follow `next_safe_action`, `action_signals`, and `skills` first when startup/implement was used. Treat `preflight`, `config`, `defaults`, `skills`, `modules`, `ownership`, and `report` as routed drill-down or recovery surfaces, not the ordinary startup loop. Report repo-relative paths, not local absolute paths. If the effective CLI is unavailable after trying it, immediately read `.agentic-workspace/WORKFLOW.md` before any other files.
<!-- agentic-workspace:workflow:end -->
