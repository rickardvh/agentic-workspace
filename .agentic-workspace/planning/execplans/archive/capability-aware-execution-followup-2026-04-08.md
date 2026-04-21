# Capability-Aware Execution Follow-up

## Goal

- Refine the planning capability-fit contract so it stays advisory, quiet, and portable across assistants while routing repeated stronger-capability outcomes into complexity-reduction follow-up pressure.

## Non-Goals

- No automatic model routing implementation.
- No vendor-specific model or reasoning matrix.
- No orchestrator-side executor selection logic.

## Active Milestone

- ID: silent-shaping-contract
- Status: completed
- Scope: update the canonical contract, shipped planning payload, and adjacent planning guidance so capability-aware execution explicitly prefers silent shaping, does not interfere with assistants that already auto-select capability, and treats repeated stronger-capability outcomes as feedback for cheaper future execution.
- Ready: ready
- Blocked: none

## Immediate Next Action

- Update `.agentic-workspace/docs/capability-aware-execution.md` and the shipped planning surfaces to encode silent shaping, non-interference, and complexity-reduction routing.

## Blockers

- None.

## Touched Paths

- `.agentic-workspace/docs/capability-aware-execution.md`
- `packages/planning/bootstrap/.agentic-workspace/docs/capability-aware-execution.md`
- `.agentic-workspace/planning/agent-manifest.json`
- `packages/planning/bootstrap/.agentic-workspace/planning/agent-manifest.json`
- `packages/planning/README.md`
- `packages/planning/bootstrap/AGENTS.md`
- `packages/planning/bootstrap/.agentic-workspace/planning/execplans/README.md`
- `docs/contributor-playbook.md`
- `.agentic-workspace/planning/reviews/README.md`
- `packages/planning/tests/test_installer.py`

## Invariants

- Capability-aware execution remains task-shape based and vendor-neutral.
- The contract stays advisory; it should shape planning and escalation without overriding tools that already do automatic capability selection well.
- Repeated stronger-capability needs should become improvement-targeting signals, not just repeated prompts to use a stronger executor.

## Validation Commands

- `cd packages/planning && uv run pytest tests/test_installer.py`
- `uv run python scripts/check/check_planning_surfaces.py`
- `make maintainer-surfaces`
- `uv run agentic-planning-bootstrap upgrade --target .`
- `uv run agentic-memory-bootstrap upgrade --target .`

## Completion Criteria

- The canonical capability-aware execution doc explicitly defines silent shaping, non-interference, and complexity-reduction feedback routing.
- The same contract is shipped in the planning payload and reflected in manifest-generated guidance.
- Regression coverage proves the refined contract remains present in the shipped payload.
- Issue `#10` can be closed with the landed surfaces and validation evidence.

## Drift Log

- 2026-04-08: Promoted from GitHub issue `#10` for immediate implementation by explicit maintainer choice.
- 2026-04-08: Completed by refining the capability-aware execution contract around silent shaping, non-interference with automatic capability selection, and complexity-reduction feedback routing, then syncing the shipped payload and root install.
