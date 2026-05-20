# Agent Instructions

Authority marker:

- authority: adapter
- canonical_source: `.agentic-workspace/config.toml` and `uv run agentic-workspace start --target . --format json`
- safe_to_edit: true
- refresh_command: null

<!-- agentic-workspace:workflow:start -->
Before answering or editing non-trivial requests, including read-only workflow, config, delegation, or action-safety decisions, use `uv run agentic-workspace` as the effective Agentic Workspace CLI invocation for this repo. This value is resolved from `.agentic-workspace/config.toml` `[workspace].cli_invoke`; if `.agentic-workspace/config.local.toml` explicitly overrides it, use that local value. Run `uv run agentic-workspace implement --changed <paths> --task "<task>" --format json` when changed paths are known. When the user request already maps to a known dedicated Agentic Workspace command and no takeover, recovery, active-planning, or ambiguous safety decision is needed first, run that dedicated command directly. Otherwise run `uv run agentic-workspace start --task "<task>" --format json` using the user's request as `<task>` for unknown-shape first-contact context. Do not try a bare `agentic-workspace` command first when the effective invocation names a repo-local or dev-dependency command; PATH may resolve a stale installed selector. Do not open raw `.agentic-workspace` files before this command; follow `immediate_next_allowed_action` and `skill_routing` first when startup/implement was used. Use `preflight` for takeover or recovery. Report repo-relative paths, not local absolute paths. If the effective CLI is unavailable after trying it, immediately read `.agentic-workspace/WORKFLOW.md` before any other files.
<!-- agentic-workspace:workflow:end -->
