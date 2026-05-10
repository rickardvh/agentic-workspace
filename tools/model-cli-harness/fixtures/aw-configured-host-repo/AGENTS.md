# Agent Instructions

<!-- agentic-workspace:workflow:start -->
Before answering or editing non-trivial requests, including read-only workflow, config, delegation, or action-safety decisions, run `uv run agentic-workspace implement --changed <paths> --format json` when changed paths are known; otherwise run `uv run agentic-workspace start --task "<task>" --format json` using the user's request as `<task>`. Do not open raw `.agentic-workspace` files before this command; follow `immediate_next_allowed_action` and `skill_routing` first. Use `preflight` for takeover or recovery. Report repo-relative paths, not local absolute paths. If the CLI is unavailable, immediately read `.agentic-workspace/WORKFLOW.md` before any other files.
<!-- agentic-workspace:workflow:end -->
