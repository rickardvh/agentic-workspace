# Agent Instructions

Authority marker:

- authority: adapter
- canonical_source: `.agentic-workspace/config.toml` and `agentic-workspace start --target . --format json`
- safe_to_edit: true
- refresh_command: null

<!-- agentic-workspace:workflow:start -->
Before answering or editing non-trivial requests, including read-only workflow, config, delegation, or action-safety decisions, use the effective CLI invocation from `agentic-workspace start --format json` / `.agentic-workspace/config.local.toml` `[workspace].cli_invoke` when present. Run `<effective-cli> implement --changed <paths> --format json` when changed paths are known; otherwise run `<effective-cli> start --task "<task>" --format json` using the user's request as `<task>`. Do not substitute a bare `agentic-workspace` command when local config names a repo-local invocation; PATH may resolve a stale installed selector. Do not open raw `.agentic-workspace` files before this command; follow `immediate_next_allowed_action` and `skill_routing` first. Use `preflight` for takeover or recovery. Report repo-relative paths, not local absolute paths. If unavailable, read `.agentic-workspace/WORKFLOW.md`.
<!-- agentic-workspace:workflow:end -->
