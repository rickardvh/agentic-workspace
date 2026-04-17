# Standing Intent Precedence And Supersession

## Goal

- Define the first compact precedence and supersession model for standing repo intent so conflicting durable guidance can be resolved without falling back to ad hoc chat steering.
- Expose that model through the existing standing-intent report surface instead of introducing a new state store.

## Non-Goals

- Do not build a rule engine or require version metadata on every owner surface.
- Do not auto-resolve every contradiction found across repo surfaces.
- Do not broaden this slice into stronger-home enforcement promotion; that remains the next follow-on.
- Do not collapse policy, doctrine, Memory, Planning, and checks into one source of truth.

## Intent Continuity

- Larger intended outcome: make durable repo intent classifiable, recoverable, evolvable, and promotable into stronger enforcement and reporting instead of leaving it trapped in chat.
- This slice completes the larger intended outcome: no
- Continuation surface: `ROADMAP.md` candidate lane `standing-intent-durability`
- Parent lane: `standing-intent-durability`

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: `ROADMAP.md`
- Activation trigger: the precedence model is now explicit, so the next unresolved gap is promotion from prose into stronger enforcement when prose is too weak.

## Iterative Follow-Through

- What this slice enabled: the standing-intent report now says how conflicting durable guidance should be resolved and how older residue stops governing when a stronger current owner exists.
- Intentionally deferred: stronger-home promotion into config, checks, or validation workflows remains a separate slice.
- Discovered implications: the useful special case is not full contradiction detection but an explicit slice-scoped rule for active planning versus broader doctrine.
- Proof achieved now: the repo can query precedence order, supersession rules, and the active-direction-versus-doctrine conflict rule directly from `agentic-workspace report`.
- Validation still needed: dogfood the model against a real contradiction or doctrine-to-policy promotion before widening the surface.
- Next likely slice: define the decision test that moves standing doctrine or policy into stronger enforcement when prose is no longer enough.

## Delegated Judgment

- Requested outcome: add one compact precedence order, one compact supersession model, and expose both through the standing-intent report.
- Hard constraints: keep the model declarative, source-attributed, and subordinate to canonical owner surfaces; avoid per-surface metadata churn.
- Agent may decide locally: the exact order among durable classes below explicit human instruction, the minimum supersession rules worth naming, and how compactly the report should surface the active-direction special case.
- Escalate when: the best remaining solution would require versioning every owner surface, a broad conflict detector, or automatic enforcement generation.

## Active Milestone

- Status: completed
- Scope: extend the standing-intent contract with precedence and supersession rules, expose them through workspace reporting, refresh the installed planning payload, and advance the roadmap to stronger-home promotion.
- Ready: ready
- Blocked: none
- optional_deps: GitHub issue `#144`

## Immediate Next Action

- Promote the stronger-home enforcement slice for standing intent when the next bounded roadmap promotion is ready.

## Blockers

- None.

## Touched Paths

- `ROADMAP.md`
- `docs/reporting-contract.md`
- `docs/standing-intent-contract.md`
- `docs/execplans/archive/standing-intent-precedence-and-supersession-2026-04-17.md`
- `packages/planning/bootstrap/docs/standing-intent-contract.md`
- `src/agentic_workspace/reporting_support.py`
- `src/agentic_workspace/workspace_output.py`
- `tests/test_workspace_cli.py`

## Invariants

- Explicit current human instruction remains above durable standing intent.
- Active lane-local direction may narrow broader doctrine for the current slice, but it must not silently rewrite checked-in hard policy.
- Superseded residue may remain for history or explanation, but it should stop governing current work once a clearer current owner exists.

## Contract Decisions To Freeze

- The first precedence order is: explicit current human instruction, active directional intent, config policy, enforceable workflow, repo doctrine, durable understanding, then superseded residue.
- The first supersession model should favor newer guidance within the same owner and stronger current homes across owners.
- The report should expose the rule declaratively; it should not pretend to solve all conflicts automatically.

## Open Questions To Close

- What decision test should promote standing doctrine or policy into stronger enforcement when prose is no longer enough?
- Which stronger-home promotion cases should be shown first in reporting without turning the report into a planner?

## Validation Commands

- `uv run pytest tests/test_workspace_cli.py -q`
- `uv run agentic-planning-bootstrap upgrade --target .`
- `uv run agentic-memory-bootstrap upgrade --target .`
- `uv run agentic-workspace report --target . --format json`
- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run python scripts/check/check_source_payload_operational_install.py`

## Required Tools

- `uv`
- `gh`

## Completion Criteria

- The standing-intent contract defines a first precedence order across the main durable owner surfaces.
- The contract defines a first supersession model that explains when older residue should stop governing.
- Workspace reporting exposes the model compactly with source provenance.
- The remaining lane is clearly routed to stronger-home promotion instead of lingering in chat.

## Execution Summary

- Outcome delivered: extended the standing-intent contract and report surface with a compact precedence order, supersession rules, and an explicit active-direction-versus-doctrine conflict rule, then advanced the roadmap to the stronger-home promotion slice.
- Validation confirmed: `uv run pytest tests/test_workspace_cli.py -q`; `uv run agentic-planning-bootstrap upgrade --target .`; `uv run agentic-memory-bootstrap upgrade --target .`; `uv run agentic-workspace report --target . --format json`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run python scripts/check/check_source_payload_operational_install.py`.
- Follow-on routed to: `ROADMAP.md` candidate lane `standing-intent-durability`
- Resume from: promote the stronger-home enforcement slice so standing doctrine or policy can move into config, checks, or validation when prose is too weak.

## Drift Log

- 2026-04-17: Promoted immediately after the standing-intent classification slice because the report could now show standing guidance, but not yet how to resolve conflicts among those surfaces.
- 2026-04-17: Landed the precedence order, supersession rules, active-direction conflict rule, and roadmap follow-through routing.
