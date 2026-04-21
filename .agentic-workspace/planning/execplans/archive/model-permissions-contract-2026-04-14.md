# Implement Model Permissions in Delegation Posture Contract

## Context
See GitHub issue `#76`. The local override contract (`.agentic-workspace/config.local.toml`) is extremely useful for defining capability constraints (e.g., `strong_planner_available = true`). However, there's no explicitly standardized way to bound "blast radius" or execution safety (autonomous run permissions).

## Goal
Standardize a schema for model *permissions* or *safety profiles* to explicitly bound blast radius in the mixed-agent local override contract.

## Changes

1. **`src/agentic_workspace/cli.py`**
   - Add `"safety.safe_to_auto_run_commands"` and `"safety.requires_human_verification_on_pr"` to the parser tuple tracking `MIXED_AGENT_LOCAL_OVERRIDE_FIELDS`.
   - Update `MixedAgentLocalOverride` dataclass to hold boolean flags for these safety fields.
   - Ensure the config parser extracts these fields and reports them via `agentic-workspace config --target . --format json`.

2. **`docs/workspace-config-contract.md`**
   - Update documentation under **Local Override Contract** to demonstrate the new `[safety]` fields.
   - Advise agents on how to use `safe_to_auto_run_commands`.

## Validation
1. Create a `.agentic-workspace/config.local.toml` with `[safety]` constraints.
2. Run `uv run agentic-workspace config --format json` and verify the fields appear in the output.
