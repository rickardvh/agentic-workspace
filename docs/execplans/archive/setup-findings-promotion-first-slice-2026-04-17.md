# Setup Findings Promotion First Slice

## Goal

- Add one compact setup/jumpstart findings promotion contract so Agentic Workspace can accept useful agent-produced analysis input without becoming its own analysis framework.

## Non-Goals

- Build a built-in static-analysis engine.
- Require all agents to emit the same analysis output beyond one optional compact artifact shape.
- Auto-promote every setup finding into checked-in state.
- Expand into memory-wide usefulness or declarative-schema extraction in this slice.

## Intent Continuity

- Larger intended outcome: Setup and jumpstart can accept agent-produced findings, preserve only the high-value ones, and route them into durable repo state without broad new workflow overhead.
- This slice completes the larger intended outcome: yes
- Continuation surface: none

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Iterative Follow-Through

- What this slice enabled: Workspace setup can now consume one compact external findings artifact and distinguish promotable setup findings from transient analysis residue.
- Intentionally deferred: broader finding classes beyond repo-friction evidence and planning candidates.
- Discovered implications: The contract stays quiet only if routing remains advisory and bounded; auto-writing planning or memory state from setup input would be too heavy for the first slice.
- Proof achieved now: `agentic-workspace setup` exposes the contract, accepts an optional findings artifact, and reports promotable versus transient findings while `agentic-workspace report` consumes the repo-friction evidence class.
- Validation still needed: none beyond ordinary future setup/jumpstart dogfooding in other repos.
- Next likely slice: Return to the roadmap queue after archiving this tranche; do not widen setup findings into a generic analyzer.

## Delegated Judgment

- Requested outcome: Add one optional setup findings input plus a compact promotion contract for the first two finding classes.
- Hard constraints: Keep setup bounded, keep the contract optional, and do not let the workspace layer own the analysis method itself.
- Agent may decide locally: The exact file name and payload field names, which two finding classes land first, and the narrowest durable route for each class.
- Escalate when: The best-looking change would auto-write planning or memory state, require a general query language, or widen setup into a broad analysis framework.

## Active Milestone

- ID: setup-findings-promotion-first-slice
- Status: completed
- Scope: define the contract, accept one optional artifact, route repo-friction evidence plus planning candidates, and dogfood it in this repo.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this completed slice, close issue `#127`, and advance the roadmap to the declarative contract inventory lane.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- docs/default-path-contract.md
- docs/execplans/setup-findings-promotion-first-slice-2026-04-17.md
- docs/jumpstart-contract.md
- docs/reporting-contract.md
- src/agentic_workspace/cli.py
- tests/test_workspace_cli.py

## Invariants

- Setup remains post-bootstrap and bounded.
- The workspace layer accepts findings input but does not own the analysis mechanism.
- Promotion remains explicit and advisory; transient findings stay transient.

## Contract Decisions To Freeze

- The first artifact path should stay optional and compact.
- The first promoted classes should stay narrow and easy to route.
- Repo-friction evidence may become durable report input; planning candidates may become explicit promotion guidance without auto-writing planning state.

## Open Questions To Close

- Which compact artifact path is the quietest default for setup/jumpstart findings?
- What exact fields are minimally necessary to make a finding routable without over-specifying agent internals?

## Validation Commands

- uv run pytest tests/test_workspace_cli.py -q
- uv run python scripts/check/check_planning_surfaces.py
- uv run agentic-workspace setup --target . --format json
- uv run agentic-workspace report --target . --format json

## Required Tools

- uv
- gh

## Completion Criteria

- `agentic-workspace setup --target ./repo --format json` exposes a compact setup-findings promotion contract and optional external input handling.
- One optional checked-in artifact shape is documented and accepted.
- Repo-friction evidence from that artifact becomes queryable through shared reporting.
- Planning candidates from that artifact are surfaced as explicit promotion guidance rather than silent active work.

## Execution Summary

- Outcome delivered: Added one compact setup findings promotion contract, accepted the optional `tools/setup-findings.json` artifact through `agentic-workspace setup`, and routed promotable repo-friction evidence into shared reporting while keeping planning candidates as explicit promotion guidance.
- Validation confirmed: `uv run pytest tests/test_workspace_cli.py -q`; `uv run python scripts/check/check_planning_surfaces.py`; repo-local dogfood with a transient `tools/setup-findings.json` artifact confirmed `SETUP_STATUS=loaded`, `SETUP_REPO_FRICTION=1`, and `SETUP_PLANNING=1`.
- Follow-on routed to: `ROADMAP.md` next candidate `Declarative contract inventory and schemas`
- Resume from: No further action in this plan; return to the next roadmap lane when a new bounded slice is promoted.

## Drift Log

- 2026-04-17: Promoted roadmap issue `#127` into an active first-slice execplan.
- 2026-04-17: Landed the setup findings promotion contract, dogfooded it with a transient repo-local artifact, and prepared the plan for archive.
