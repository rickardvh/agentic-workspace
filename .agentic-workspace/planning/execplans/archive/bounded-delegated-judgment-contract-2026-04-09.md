# Bounded Delegated Judgment Contract

## Goal

- Define the first shipped planning contract for bounded delegated judgment: humans set direction and constraints, agents may improve bounded local execution, and agents must not silently widen requested outcomes.

## Non-Goals

- Do not introduce tool-specific model-routing policy.
- Do not turn delegated judgment into a separate standalone package contract.
- Do not expand this slice into a broad autonomy framework beyond planning/workflow boundaries.

## Active Milestone

- ID: bounded-delegated-judgment-contract
- Status: completed
- Scope: Update the shipped planning contract so sticky intent, bounded initiative, and explicit scope-expansion triggers are part of capability-aware execution and adjacent planning guidance.
- Ready: false
- Blocked: none
- optional_deps: none

Keep one active milestone by default.
Keep branch-local progress, blockers, and next-step state here rather than in durable docs or broad summaries.

## Immediate Next Action

- Archive this completed plan and clear the active queue residue.

Keep exactly one immediate action by default; avoid multi-step mini-plans here.
Replace stale immediate-action text when the next step changes instead of preserving old actions as history.

## Blockers

- None.

## Touched Paths

- `.agentic-workspace/docs/capability-aware-execution.md`
- `packages/planning/bootstrap/.agentic-workspace/docs/capability-aware-execution.md`
- `.agentic-workspace/planning/execplans/README.md`
- `packages/planning/bootstrap/.agentic-workspace/planning/execplans/README.md`
- `packages/planning/README.md`
- `docs/contributor-playbook.md`
- `packages/planning/tests/test_installer.py`

Keep this as a scope guard, not a broad file inventory.
Avoid large hand-maintained tables in active plans; compact bullets are easier to merge.

## Invariants

- Preserve the existing capability-aware execution stance: advisory, quiet, and tool-agnostic.
- Allow agents to improve means, not silently replace user ends.
- Treat any better solution that widens requested outcome, ownership surface, or time horizon as a promotion or escalation decision.

Keep invariants contract-shaped and brief.

## Validation Commands

- `cd packages/planning && uv run pytest tests/test_installer.py`
- `uv run python scripts/check/check_planning_surfaces.py`
- `make maintainer-surfaces`
- `uv run agentic-planning-bootstrap upgrade --target .`
- `uv run agentic-memory-bootstrap upgrade --target .`

## Completion Criteria

- The shipped planning contract explicitly encodes sticky intent, bounded initiative, and scope-expansion triggers.
- Root install guidance reflects the same rule.
- Payload regression coverage proves the updated contract ships in the planning package.
- The root install is refreshed and the plan can archive cleanly without manual TODO cleanup.

## Drift Log

- 2026-04-09: Promoted from the roadmap after dogfooding showed the need for a clearer human-direction and bounded-agent-judgment contract.
- 2026-04-09: Completed by tightening the planning contract so agents may improve local means without silently widening requested ends, then refreshing the root install from the updated payload.
