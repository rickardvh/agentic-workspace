# Local Delegation Outcome Evidence Dogfood

## Goal

- Check whether local-only recorded delegation outcomes are enough to derive useful advisory tuning without turning the repo into a scheduler.

## Dogfood Setup

- Used the configured local target profile inventory in `agentic-workspace.local.toml`.
- Recorded three local-only outcomes with `agentic-workspace note-delegation-outcome` for `gpt_5_4_mini`.
- Queried `uv run agentic-workspace config --target . --format json`.

## Evidence

- The command writes a separate local artifact at `agentic-workspace.delegation-outcomes.json` instead of mutating the editable local TOML profile.
- The config surface reports:
  - artifact presence and record count
  - per-target local evidence status
  - derived confidence suggestion
  - derived task-fit suggestions
- The loop remained advisory:
  - no target was auto-selected
  - no checked-in repo semantics changed
  - no local profile was silently rewritten

## Result

- The evidence loop is already useful for confidence tuning.
- The first live pass raised the suggested confidence for `gpt_5_4_mini` after repeated successful bounded outcomes.
- Keeping the outcome artifact separate from `agentic-workspace.local.toml` was the quieter shape; the editable profile stays readable while the evidence log can grow independently.

## Follow-On Read

- No immediate follow-on is required for the bounded slice.
- A later follow-on would only be justified if repeated use shows clear value in:
  - suggested write-back helpers
  - richer task-class normalization
  - invocation adapters for external executors
