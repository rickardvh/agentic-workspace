# Agent Instructions

Authority marker:

- authority: adapter
- canonical_source: `.agentic-workspace/config.toml` and `agentic-workspace start --target . --format json`
- safe_to_edit: true
- refresh_command: null

<!-- agentic-workspace:workflow:start -->
Before answering or editing non-trivial requests, including read-only workflow, config, delegation, or action-safety decisions, run `agentic-workspace implement --profile tiny --changed <paths> --format json` when changed paths are known; otherwise run `agentic-workspace start --profile tiny --task "<task>" --format json` using the user's request as `<task>`. Do not open raw `.agentic-workspace` files before this command; follow `immediate_next_allowed_action` and `skill_routing` first. Use `preflight` for takeover or recovery. If unavailable, read `.agentic-workspace/WORKFLOW.md`.
<!-- agentic-workspace:workflow:end -->
