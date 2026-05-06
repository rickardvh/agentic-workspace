# Agent Instructions

<!-- agentic-workspace:workflow:start -->
Before answering or editing non-trivial requests, including read-only workflow, config, delegation, or action-safety decisions, run `agentic-workspace implement --profile tiny --changed <paths> --format json` when changed paths are known; otherwise run `agentic-workspace start --profile tiny --task "<task>" --format json` using the user's request as `<task>`. Do not open raw `.agentic-workspace` files before this command; follow `immediate_next_allowed_action` and `skill_routing` first. Use `preflight` for takeover or recovery. Report repo-relative paths, not local absolute paths. If unavailable, read `.agentic-workspace/WORKFLOW.md`.
<!-- agentic-workspace:workflow:end -->
