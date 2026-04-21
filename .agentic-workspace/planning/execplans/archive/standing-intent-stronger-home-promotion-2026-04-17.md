# Standing Intent Stronger-Home Promotion

## Goal

- Complete the standing-intent lane by defining the first stronger-home promotion model from doctrine or understanding into config, checks, and validation-shaped enforcement.
- Expose that model through the existing standing-intent report so agents can see not only what is in force, but when prose is no longer the strongest home.

## Non-Goals

- Do not auto-generate checks or workflows from prose.
- Do not remove explanatory doctrine once stronger enforcement exists.
- Do not broaden the slice into a generic policy compiler or automation framework.
- Do not promote every standing instruction into checks when config or doctrine is still the better fit.

## Intent Continuity

- Larger intended outcome: make durable repo intent classifiable, recoverable, evolvable, and promotable into stronger enforcement and reporting instead of leaving it trapped in chat.
- This slice completes the larger intended outcome: yes
- Continuation surface: none
- Parent lane: `standing-intent-durability`

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Iterative Follow-Through

- What this slice enabled: the standing-intent report now carries a decision test for when doctrine or understanding should move into config or enforceable workflow, plus concrete repo examples already promoted into those stronger homes.
- Intentionally deferred: none inside the standing-intent lane; later work may still reuse the promotion model in other lanes.
- Discovered implications: visibility matters more than automation first; showing already-promoted repo examples was enough to make the stronger-home path concrete without inventing a new planner.
- Proof achieved now: the standing-intent lane now covers classification, reporting, precedence, supersession, and stronger-home promotion in one coherent contract/report story.
- Validation still needed: none for this lane beyond normal future dogfooding in other candidate lanes.
- Next likely slice: move to the next roadmap lane, `workspace-optimization-bias-findings`.

## Delegated Judgment

- Requested outcome: finish the standing-intent lane with a compact stronger-home promotion model and visible repo examples.
- Hard constraints: keep the model declarative, keep reporting subordinate to canonical owner surfaces, and avoid speculative workflow generation.
- Agent may decide locally: the exact decision-test wording, which current repo promotions are concrete enough to count as examples, and how much of the lane to retire from the roadmap once the slice lands.
- Escalate when: finishing the lane would require new config fields, auto-generated checks, or another standing-intent source of truth.

## Active Milestone

- Status: completed
- Scope: add the stronger-home decision test and repo examples to the standing-intent contract/report, refresh the installed planning payload, retire the completed roadmap lane, and close the standing-intent issues.
- Ready: ready
- Blocked: none
- optional_deps: GitHub issue `#145`

## Immediate Next Action

- Close the standing-intent GitHub issues and continue from the next roadmap lane.

## Blockers

- None.

## Touched Paths

- `ROADMAP.md`
- `.agentic-workspace/docs/reporting-contract.md`
- `.agentic-workspace/docs/standing-intent-contract.md`
- `.agentic-workspace/planning/execplans/archive/standing-intent-stronger-home-promotion-2026-04-17.md`
- `packages/planning/bootstrap/.agentic-workspace/docs/standing-intent-contract.md`
- `src/agentic_workspace/reporting_support.py`
- `src/agentic_workspace/workspace_output.py`
- `tests/test_workspace_cli.py`

## Invariants

- Stronger-home promotion remains guidance-first and reportable before any automation-first follow-through.
- Config is for machine-readable stable policy; checks and validation are for detectable drift and enforceable workflow.
- Doctrine may remain as explanation even after a stronger home becomes authoritative.

## Contract Decisions To Freeze

- The first stronger-home decision test is: promote to config when the concern is a stable machine-readable default, promote to enforceable workflow when drift should be detectable, and keep doctrine when explanation remains the strongest fit.
- The first examples should come from real repo promotions already present in config and checks.
- The lane is complete once the promotion model is visible in reporting and the roadmap no longer treats standing intent as an open candidate lane.

## Open Questions To Close

- None for the standing-intent lane.

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

- The standing-intent contract defines when to keep doctrine as prose and when to promote it into config or enforceable workflow.
- The report exposes the stronger-home model and at least two real repo examples.
- The standing-intent roadmap lane can be retired and the associated GitHub issues can be closed.

## Execution Summary

- Outcome delivered: added the stronger-home decision test and real repo promotion examples to the standing-intent report, retired the completed standing-intent lane from `ROADMAP.md`, and finished the lane’s checked-in planning/reporting story.
- Validation confirmed: `uv run pytest tests/test_workspace_cli.py -q`; `uv run agentic-planning-bootstrap upgrade --target .`; `uv run agentic-memory-bootstrap upgrade --target .`; `uv run agentic-workspace report --target . --format json`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run python scripts/check/check_source_payload_operational_install.py`.
- Follow-on routed to: `ROADMAP.md` next lane `workspace-optimization-bias-findings`
- Resume from: promote the next roadmap lane rather than reopening standing intent.

## Drift Log

- 2026-04-17: Promoted after the precedence slice because the remaining lane gap was no longer classification or reporting, but the path from prose into stronger enforcement.
- 2026-04-17: Landed the stronger-home model, retired the lane from the roadmap, and prepared the standing-intent issues for closure.
