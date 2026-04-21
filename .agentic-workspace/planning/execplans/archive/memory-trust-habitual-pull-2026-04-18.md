# Memory Trust And Habitual Pull

## Goal

- Prove whether Memory is now a cheap habitual path in ordinary repo work and complete the smallest remaining follow-through needed to make that claim trustworthy.

## Non-Goals

- Reopen broader planning-surface recovery work that was completed in earlier lanes.
- Expand Memory into the owner of all standing guidance instead of preserving its narrower durable-understanding boundary.

## Intent Continuity

- Larger intended outcome: make Memory a trusted, habitual low-cost pull path for ordinary work without blurring its ownership boundary with planning and standing guidance.
- This slice completes the larger intended outcome: yes
- Continuation surface: none
- Parent lane: `memory-trust-habitual-pull`

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Iterative Follow-Through

- What this slice enabled: the repo can answer the ordinary-work Memory pull question from one compact module-report view instead of reconstructing it from separate routing, trust, and ownership surfaces.
- Intentionally deferred: unrelated Memory promotion/elimination candidates outside this lane.
- Discovered implications: the remaining practical-pull gap was first-pull legibility, not routing accuracy or fresh boundary ambiguity.
- Proof achieved now: recent-case audit evidence is checked in, the dominant gap is fixed through a shipped `habitual_pull` report view, and the route-report evidence still shows high-confidence low-cost routing.
- Validation still needed: none for this lane beyond normal future dogfooding.
- Next likely slice: none

## Delegated Judgment

- Requested outcome: finish the lane, not just restate the issue cluster, and keep the result small enough that the repo can trust the conclusion.
- Hard constraints: preserve the boundary that Memory owns durable understanding and repo-specific interpretive norms rather than all standing guidance; prefer shipped contract fixes over repo-local workaround prose when the gap is product-level.
- Agent may decide locally: which recent work samples provide sufficient evidence, whether the smallest fix is documentation, reporting, workflow, or package behavior, and whether the lane can retire in one bounded pass.
- Escalate when: the evidence suggests multiple unrelated bypass reasons, or completing the lane would require reopening broader planning recovery or standing-guidance ownership decisions.

## Active Milestone

- Status: completed
- Scope: audit recent ordinary-work evidence, identify the dominant remaining bypass reason, and ship the smallest Memory contract/reporting change needed to make the cheap pull explicit.
- Ready: ready
- Blocked: none
- optional_deps: internal delegates for evidence audit and contract-surface inspection

## Immediate Next Action

- None. This slice is complete.

## Blockers

- None.

## Touched Paths

- `TODO.md`
- `.agentic-workspace/planning/execplans/memory-trust-habitual-pull-2026-04-18.md`
- `ROADMAP.md`
- `packages/memory/**`
- `docs/**`
- `tests/**`

## Invariants

- Memory must remain a distinct owner for durable understanding and repo-specific interpretive norms, not a duplicate owner for planning state or all standing guidance.
- Proof should rely on cheap recoverable repo surfaces, not chat-only reasoning.
- Validation should stay as narrow as possible for the touched surfaces.

## Contract Decisions To Freeze

- The lane closes only if the repo can show both a cheap practical Memory pull path and an explicit owner boundary with non-Memory standing guidance.
- If one remaining bypass reason dominates, fix that reason directly instead of adding broader explanatory prose.

## Open Questions To Close

- None.

## Validation Commands

- `uv run agentic-memory-bootstrap doctor --target . --format json`
- `uv run agentic-workspace report --target . --format json`
- `uv run python scripts/check/check_memory_freshness.py`
- `uv run python scripts/check/check_planning_surfaces.py`
- `rg "memory-trust-habitual-pull|habitual pull|standing guidance|durable understanding" docs packages memory tests`

## Required Tools

- `gh` for live issue verification and closure if the lane completes.

## Completion Criteria

- Recent ordinary-work evidence is classified in checked-in planning or canonical docs strongly enough to support the lane conclusion.
- The explicit Memory boundary with other standing guidance is clear in the touched contract surfaces.
- Any dominant remaining bypass reason is fixed in the smallest credible product surface.
- Validation shows Memory/reporting/planning surfaces are healthy after the change.
- `ROADMAP.md` and GitHub issue state reflect the lane outcome.

## Execution Summary

- Outcome delivered: added `habitual_pull` to `agentic-memory-bootstrap report --format json`, documented the cheap ordinary-work first-pull rule in Memory-owned surfaces, and recorded the recent-case audit in `.agentic-workspace/planning/reviews/memory-habitual-pull-audit-2026-04-18.md`.
- Validation confirmed: `packages/memory/tests/test_installer.py`, `ruff check packages/memory`, `agentic-memory-bootstrap report --target . --format json`, `python scripts/check/check_source_payload_operational_install.py`, `python scripts/check/check_memory_freshness.py`, and `agentic-workspace report --target . --format json`.
- Follow-on routed to: `ROADMAP.md` next lane `portable-declarative-contracts-beyond-python-cli`; unrelated Memory promotion/elimination candidates remain visible through `agentic-memory-bootstrap promotion-report --mode remediation`.
- Resume from: the next roadmap lane when active capacity opens; do not reopen this lane unless future ordinary work surfaces a new repeated bypass cause.

## Drift Log

- 2026-04-18: Promoted the roadmap lane into an active execplan so the audit and final follow-through can be implemented from checked-in state.
- 2026-04-18: Completed after the audit showed first-pull legibility was the remaining gap, the Memory module report gained a compact `habitual_pull` view, and the lane could retire without reopening broader Memory redesign work.
