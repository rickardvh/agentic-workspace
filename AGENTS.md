# Agent Instructions

Authority marker:

- authority: adapter
- canonical_source: `.agentic-workspace/config.toml` and `agentic-workspace start --target . --format json`
- safe_to_edit: true
- refresh_command: null

<!-- agentic-workspace:workflow:start -->
For non-trivial requests, first run `agentic-workspace preflight --task "<task>" --format json` using the user's request as `<task>`; use its `primary_next_action` and `skill_routing` before opening raw `.agentic-workspace` files. If unavailable, read `.agentic-workspace/WORKFLOW.md`.
<!-- agentic-workspace:workflow:end -->
