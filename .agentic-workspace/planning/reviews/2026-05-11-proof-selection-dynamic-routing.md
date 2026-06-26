# Proof selection dynamic routing review

## Goal

- Shape a dynamic proof-selection model that starts from proof intent, enriches from target repo capabilities, and only then emits concrete commands or manual verification instructions.

## Scope

- Review whether proof selection should reason from proof types, target repo capabilities, setup/adopt-discovered routes, and manual verification fallbacks before selecting concrete commands.

## Non-Goals

- Do not prescribe this source repo's Makefile targets or no-absolute-path policy to host repos.
- Do not implement the full proof-selection redesign in the review pass.

## Review Mode

- Mode: dogfooding-shaping
- Review question: How should proof selection represent general proof types, target capability discovery, setup/adopt learned routes, command selection, and manual verification fallbacks without leaking repo-local assumptions?
- Default finding cap: bounded
- Inputs inspected first: compact planning and task-specific surfaces

## Review Method

- Commands used: `uv run agentic-workspace summary --format json --select planning_record,active_contract,resumable_contract,todo,planning_surface_health`; `rg -n proof/test-workspace/lint-workspace` in `src` and `tests`; inspected `proof_selection_rules.json` and proof CLI tests.
- Evidence sources: target-repo report about unavailable Makefile targets, target-repo report about repo-local absolute-path policy leakage, current proof-selection rules/default lanes, existing Makefile adaptation tests, and config assurance proof profiles.

## References

- kind: execplan | target: .agentic-workspace/planning/execplans/proof-selection-dynamic-routing.plan.json | role: owner
- kind: dogfooding | target: target repo report | role: evidence

## Findings

- `proof-type-before-command`: Proof selection needs a proof-intent layer before command selection. Existing lanes had `proof_kind`, but compact output did not explain the proof-type reasoning. Promote a `proof_strategy` object.
- `target-capabilities-before-command`: Executable proof commands must be gated by target capabilities. Dogfooding showed unavailable Makefile targets in a host repo. Promote `target_proof_capabilities` and adapt only to discovered Makefile targets or `package.json` scripts.
- `manual-fallback-needed`: Unavailable executable proof needs explicit manual verification fallback. Promote `manual_verification` instructions when commands cannot be selected safely.

## Recommendation

- Promote: Promoted the three review findings into the first implementation slice: `proof_strategy`, `target_proof_capabilities`, `package.json` script adaptation, and `manual_verification` fallback.
- Defer: Persisted route maps learned during setup/adopt remain future work; this slice performs live target discovery at proof-selection time.
- Dismiss: No findings dismissed.

## Retention

- Closeout shape: shrink
- Trigger: findings promoted, dismissed, or superseded
- Proof surface: routed issues, planning state, docs, checks, Memory, or a compact retained review stub

## Validation / Inspection Commands

- `uv run pytest tests/test_workspace_proof_cli.py::test_proof_changed_uses_available_target_makefile_targets tests/test_workspace_proof_cli.py::test_proof_changed_does_not_assume_makefile_exists tests/test_workspace_proof_cli.py::test_proof_changed_uses_target_package_json_scripts_without_makefile tests/test_workspace_implement_cli.py::test_implement_uses_available_target_makefile_targets -q`
- `uv run ruff check src/agentic_workspace/cli.py tests/test_workspace_proof_cli.py tests/test_workspace_implement_cli.py`

## Drift Log

- 2026-05-11: Review record created by create-review.
- 2026-05-11: Review completed and promoted into the first bounded proof-selection implementation slice.
