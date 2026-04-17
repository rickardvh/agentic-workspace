# Local Delegation Target Profiles Dogfood

## Goal

- Check whether the new local-only delegation target profile surface is actually enough to reduce orchestrator guesswork without turning local config into a scheduler.

## Dogfood Setup

- Wrote a temporary repo-local `agentic-workspace.local.toml` with:
  - base mixed-agent posture fields
  - `delegation_targets.fast_docs`
  - `delegation_targets.primary_planner`
- Queried `uv run agentic-workspace config --target . --format json`.

## Evidence

- The config surface now reports:
  - the configured target aliases
  - strength and confidence hints
  - task-fit hints
  - execution-method hints
  - derived advisory handoff detail and review burden
- The surface stayed advisory:
  - no executor was auto-selected
  - no repo-owned semantics changed
  - the existing planning handoff contract remained the worker boundary
- The pass exposed one real Windows friction point:
  - a PowerShell-written UTF-8 BOM local override failed TOML parsing
  - the config loaders now accept UTF-8 BOM for workspace/local TOML surfaces

## Result

- The smallest useful target-profile shape is enough for the orchestrator to stop guessing blindly about whether a named local target should get:
  - a tighter handoff
  - more retained review burden
  - only a narrow task class
- No broader routing matrix or invocation registry was needed in this slice.

## Follow-On Read

- No immediate follow-on is required for this lane.
- If repeated external delegation later still feels too manual, the next product question is likely executor invocation adapters or richer per-target evidence, not broader checked-in policy.
