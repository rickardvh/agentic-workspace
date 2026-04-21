# Orchestrator Workflow Dogfood

## Goal

- Record whether the new planner-to-worker workflow is actually usable in normal repo work and what remaining cost classes should survive as follow-on work.

## Scope

- `docs/orchestrator-workflow-contract.md`
- `agentic-workspace defaults --section relay --format json`
- `agentic-workspace config --target . --format json`
- `agentic-planning-bootstrap handoff --format json`
- bundled skill `planning-orchestrator-workflow`
- one bounded delegated docs slice on `docs/contributor-playbook.md` and `docs/workspace-config-contract.md`

## Result

- The workflow is now good enough to use.
- A delegated worker can continue from the checked-in contract without a handwritten prompt from scratch.
- The remaining cost is no longer the absence of a formal workflow; it is how much the orchestrator still has to know about slice shaping and target capability before delegation.

## Evidence

### What worked

- The local mixed-agent posture remained local-only and advisory.
  The worker-facing flow read `agentic-workspace config --target . --format json` but did not require repo-owned scheduling policy.
- The planner-to-worker contract was queryable.
  `agentic-workspace defaults --section relay --format json` explained the method-neutral rule, and `agentic-planning-bootstrap handoff --format json` exposed the active delegated slice contract.
- The workflow stayed agent-agnostic.
  The same contract remained valid for internal delegation, local models, or external CLI/API execution.
- The worker stayed inside the assigned write scope.
  The dogfood slice only touched `docs/contributor-playbook.md` and `docs/workspace-config-contract.md`.

### Remaining friction

- The derived handoff is still lane-level by default.
  The orchestrator still had to narrow the worker write scope for the specific delegated slice instead of relying on the raw `owned_write_scope` from the handoff output.
- Executor capability is still mostly a guess.
  The workflow now tells the orchestrator how to delegate, but not how much to trust a given local or external target on a problem class.
- That target-confidence question belongs locally, not in repo-owned planning.
  The worker and user both surfaced the same boundary: target profiles and confidence hints should stay advisory and local-only.

## Follow-On

- Promote local-only delegation target profiles and confidence hints as issue `#172`.
- Keep any future target-confidence surface advisory, local-only, and capability-shaped rather than turning it into repo-owned scheduler policy.

## Validation / Inspection Commands

- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run agentic-planning-bootstrap handoff --format json`

## Drift Log

- 2026-04-17: Recorded the first post-productization delegated dogfood pass for the orchestrator workflow lane.
