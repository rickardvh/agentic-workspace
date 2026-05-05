# Agent Instructions

<!-- agentic-workspace:workflow:start -->
For non-trivial requests with known changed paths, first run `agentic-workspace implement --profile tiny --changed <paths> --format json`; otherwise run `agentic-workspace start --profile tiny --task "<task>" --format json` using the user's request as `<task>`. Follow `immediate_next_allowed_action` and `skill_routing` before opening raw `.agentic-workspace` files. Use `preflight` for takeover or recovery. If unavailable, read `.agentic-workspace/WORKFLOW.md`.
<!-- agentic-workspace:workflow:end -->
