# Validation Friction As Repo-Friction Evidence

## Goal

- Close roadmap lane `validation-friction-repo-friction` by defining validation friction as explicit repo-friction evidence, distinguishing it from ordinary debugging, and exposing it through the existing workspace reporting contract without creating a telemetry subsystem.

## Non-Goals

- Treat every failing test as validation friction.
- Create a productivity score, generalized telemetry layer, or broad analyzer.
- Use validation friction as blanket permission for broad refactoring.
- Reopen the workspace-self-adaptation policy lane except where its result is an input here.

## Intent Continuity

- Larger intended outcome: the repo-friction model should reflect not only when safe slice planning is hard, but also when proving an otherwise straightforward slice is repeatedly expensive because seams, tranche boundaries, or proof contracts are weak.
- This slice completes the larger intended outcome: yes
- Continuation surface: none
- Parent lane: validation-friction-repo-friction

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Iterative Follow-Through

- What this slice should enable: the workspace report can distinguish planning friction from validation friction and treat both as repo-friction evidence classes without inventing a second diagnostic framework.
- Intentionally deferred: any deeper memory or portability follow-on that may later consume this signal.
- Discovered implications: validation-friction should stay evidence, not policy; the useful question is whether proof remained cheap for the right reasons, not whether tests ever failed.
- Proof still needed: docs, defaults, report payloads, tests, and a small review of recent repo examples all agree on the signal shape.
- Validation still needed: workspace CLI tests, planning-surface checks, and one live defaults/report pass on this repo.
- Next likely slice: return to `ROADMAP.md` and promote the next remaining lane after `#175` is archived.

## Delegated Judgment

- Requested outcome: implement issue `#175` as one bounded lane, using the orchestrator/worker workflow for the implementation slice.
- Hard constraints: keep validation-friction as repo-friction evidence rather than a new analyzer; keep the subtype set compact and operational; distinguish validation friction from ordinary bug-fixing and genuinely difficult domains; keep report output derived.
- Agent may decide locally: exact field names, the minimum subtype set, which recent repo examples to use in the review note, and whether the new evidence should live only in report output or also in defaults.
- Escalate when: the lane would require a persistent evidence store, hidden heuristics that amount to telemetry, or a broad redefinition of proof or planning ownership.

## Active Milestone

- ID: validation-friction-contract-shaping
- Status: completed
- Scope: define the compact signal, subtype set, and report/default footprint for `#175`, then hand the bounded implementation slice to a worker.
- Ready: ready
- Blocked: none
- optional_deps: none

## Upcoming Milestones

- None.

## Immediate Next Action

- Archive this completed lane, close `#175`, and return to `ROADMAP.md` for the next candidate.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- .agentic-workspace/planning/execplans/validation-friction-repo-friction-2026-04-18.md
- docs/workspace-config-contract.md
- .agentic-workspace/docs/reporting-contract.md
- docs/default-path-contract.md
- src/agentic_workspace/cli.py
- src/agentic_workspace/reporting_support.py
- tests/test_workspace_cli.py
- .agentic-workspace/planning/reviews/

## Invariants

- Validation friction remains evidence, not a scheduler or cleanup permission.
- The signal must distinguish weak seams, bad tranche boundaries, and unclear proof contracts from ordinary debugging noise.
- Repo-friction reporting stays derived and queryable.
- The existing workspace/report contract remains the owner; do not create a new module.

## Contract Decisions To Freeze

- Validation friction is explicit repo-friction evidence.
- The subtype set should stay compact and operational.
- The signal should appear through the existing report/default surfaces, not through a new telemetry system.

## Open Questions To Close

- What is the smallest subtype set that still separates weak seams, bad tranche boundaries, and unclear proof contracts?
- Should the default surface carry only the contract and subtype set, with the report carrying the live evidence class?
- Which recent repo examples best show validation friction versus ordinary debugging?

## Validation Commands

- uv run pytest tests/test_workspace_cli.py -q
- uv run python scripts/check/check_planning_surfaces.py
- uv run agentic-workspace defaults --section improvement_latitude --format json
- uv run agentic-workspace report --target . --format json

## Required Tools

- uv
- gh

## Completion Criteria

- The workspace config/default/report docs and payloads define validation friction in operational terms.
- The report exposes validation friction as explicit repo-friction evidence with a compact subtype set.
- A checked-in review applies the signal to recent repo examples.
- Tests and planning checks pass, the lane is archived, and `#175` is closed.

## Worker Handoff Template

- Read only: `AGENTS.md`, `TODO.md`, this execplan, issue `#175`, the touched docs/code/tests, and the current compact defaults/report outputs.
- Stay inside the owned write scope.
- Implement only the bounded validation-friction contract; do not widen into memory or portability lanes.
- Run only the named narrow validation commands.
- Do not archive the lane, reroute the roadmap, or close the issue unless explicitly asked.

## Execution Summary

- Outcome delivered: added `validation_friction` as explicit repo-friction evidence in both defaults and report output, defined a compact subtype set, and anchored it in a checked-in review of recent repo examples.
- Validation confirmed: `uv run pytest tests/test_workspace_cli.py -q`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-workspace defaults --section improvement_latitude --format json`; `uv run agentic-workspace report --target . --format json`.
- Follow-on routed to: `.agentic-workspace/planning/reviews/validation-friction-signal-review-2026-04-18.md` and `ROADMAP.md` next lane `memory-trust-habitual-pull`.
- Resume from: `ROADMAP.md` once the next lane is promoted.

## Drift Log

- 2026-04-18: Promoted `validation-friction-repo-friction` into active planning after the workspace-self-adaptation lane completed and left validation difficulty as the next repo-friction gap.
- 2026-04-18: Shaped the contract locally, delegated the bounded docs/code/tests slice to a worker, then tightened the defaults surface so validation friction is defined machine-readably rather than only named as another evidence class.
- 2026-04-18: Archived the lane after the docs, defaults, report payloads, review note, and tests all agreed on the compact validation-friction contract.
