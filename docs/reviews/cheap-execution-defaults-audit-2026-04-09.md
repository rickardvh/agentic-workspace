# Cheap-Execution Defaults Audit

## Goal

- Check whether the repo’s normal startup and operating path is now cheap enough that lower-capability or lower-reasoning agents can follow the default route without extra interpretation.

## Scope

- Startup reading load.
- Route-selection burden.
- Validation-lane clarity.
- Skill-discovery entrypoint.

## Non-Goals

- New automatic model-routing or capability escalation features.
- Deep audit of every package-internal workflow.

## Review Mode

- Mode: `context-cost`
- Review question: What still forces unnecessary interpretation before a lower-capability agent can start safely, and has this tranche removed the clearest front-door burden?
- Default finding cap: 2 findings
- Inputs inspected first: `README.md`, `docs/which-package.md`, `docs/default-path-contract.md`, `src/agentic_workspace/cli.py`, `docs/capability-aware-execution.md`

## Review Method

- Commands used:
  - `uv run pytest tests/test_workspace_cli.py`
  - `uv run python scripts/check/check_planning_surfaces.py`
- Evidence sources:
  - startup sequence in root docs
  - task-based skill recommendation route
  - machine-readable validation/default-path output

## Findings

### Finding: Cheaper execution depends on obvious route answers, not only on capability guidance

- Summary: Capability-aware execution stays advisory, but cheaper agents still fail if they must infer how to start, how to discover skills, or which validation lane is normal.
- Evidence: This tranche makes those answers explicit in one compressed README path and one structured defaults surface, including `skills --task ...` and narrow validation routes.
- Risk if unchanged: The repo would still silently assume a stronger planner just to navigate startup and validation choices.
- Suggested action: Keep reducing interpretation on recurring route questions before adding more capability-fit prose or richer planning guidance.
- Confidence: high
- Source: friction-confirmed
- Promotion target: canonical docs
- Promotion trigger: Implemented in this tranche.
- Post-remediation note shape: delete

### Finding: Advanced and maintainer-only paths must stay clearly secondary for cheap execution to remain the normal success mode

- Summary: Lower-capability agents pay avoidable cost when package-local, maintainer-only, and debugging-oriented routes are presented too close to the default path.
- Evidence: The updated root README and package READMEs now label package CLIs as advanced or secondary, and `docs/default-path-contract.md` explicitly classifies those paths as non-default.
- Risk if unchanged: Agents would continue choosing between several plausible but differently scoped commands before any real task work begins.
- Suggested action: Treat any future route addition as suspect unless it clearly preserves one dominant default path.
- Confidence: high
- Source: mixed
- Promotion target: none
- Promotion trigger: none
- Post-remediation note shape: retain

## Recommendation

- Promote: none
- Defer: none
- Dismiss: new cheap-execution work until repeated friction shows the compressed default route is still too interpretation-heavy

## Validation / Inspection Commands

- `uv run pytest tests/test_workspace_cli.py`
- `uv run python scripts/check/check_planning_surfaces.py`

## Drift Log

- 2026-04-09: Review created and resolved by the front-door defaults tranche.
