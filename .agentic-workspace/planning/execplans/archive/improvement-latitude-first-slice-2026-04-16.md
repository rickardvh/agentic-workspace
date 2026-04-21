# Improvement Latitude First Slice

## Goal

- Define one narrow repo-owned `improvement_latitude` policy that works through the existing workspace config/reporting path instead of a new control surface.
- Add one queryable repo-friction evidence surface so improvement latitude is tied to observable repo cost rather than free-form preference.
- Freeze the minimum boundary rule that keeps bounded friction reduction subordinate to delegated judgment, proof, and ownership.

## Non-Goals

- Do not build a broad analyzer, scorer, or telemetry system.
- Do not add a new core module.
- Do not turn config into a scheduler or override the existing local mixed-agent posture.
- Do not solve setup/jumpstart finding promotion in this slice.

## Intent Continuity

- Larger intended outcome: make bounded repo-friction reduction safe, evidence-backed, and cheap enough that agents can reduce real repo cost without repeated human moderation.
- This slice completes the larger intended outcome: no
- Continuation surface: ROADMAP.md

## Convergence Context

- Larger intended outcome: workspace-level improvement latitude plus repo-friction evidence that guide safe opportunistic simplification without widening requested ends.
- Convergence owner: workspace config/reporting/contracts
- What must remain intact after interruption: config remains the capability/policy home, reporting remains the shared evidence home, and delegated judgment / proof / ownership stay authoritative boundaries.
- Current interruption boundary: this slice only needs one policy field, one evidence class, and one compact boundary rule.

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: ROADMAP.md
- Activation trigger: when the first policy-plus-evidence slice lands and the next bounded follow-on is ready to extend evidence classes or promote setup/jumpstart findings.

## Delegated Judgment

- Requested outcome: ship the smallest useful implementation of improvement latitude and repo-friction evidence without adding a parallel workflow layer.
- Hard constraints: use the existing config/reporting contract, keep the evidence class simple and queryable, and do not let the new policy silently rewrite requested ends or proof scope.
- Agent may decide locally: the exact field names, the first evidence threshold, the narrowest docs to update, and the minimum tests that prove the slice.
- Escalate when: the smallest workable implementation would require a new top-level module, a heavyweight analyzer, or broader scheduling semantics.

## Active Milestone

- Status: completed
- Scope: add repo-owned `improvement_latitude` config/reporting support, derive one repo-friction evidence surface from the current repo tree, and align the boundary docs with the shipped contract.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Decide whether the next bounded follow-on should calibrate evidence-backed defaults from real repo-friction signals or promote one bounded cleanup/dogfood slice from the current hotspot report.

## Blockers

- None.

## Touched Paths

- `TODO.md`
- `ROADMAP.md`
- `docs/workspace-config-contract.md`
- `.agentic-workspace/docs/capability-aware-execution.md`
- `docs/delegated-judgment-contract.md`
- `.agentic-workspace/docs/reporting-contract.md`
- `docs/default-path-contract.md`
- `src/agentic_workspace/cli.py`
- `tests/test_workspace_cli.py`

## Invariants

- Repo-owned config remains the only checked-in policy surface for this lane.
- Local mixed-agent override remains capability/cost posture only.
- Repo-friction evidence stays workspace-level and derived.
- Improvement latitude may widen means only; it must not silently rewrite requested ends.

## Contract Decisions To Freeze

- `workspace.improvement_latitude` is the narrow repo-owned policy field for bounded repo-friction initiative.
- The first evidence class is queryable repo-friction hotspots derived by the workspace report, not a separate state file.
- Improvement latitude is interpreted through delegated judgment, proof, and ownership; it is not a scheduler or blanket refactor permission.

## Open Questions To Close

- Which default mode should the product use when the repo does not set `improvement_latitude`?
- What is the smallest hotspot threshold that is useful in this repo without turning report into noise?

## Validation Commands

- `uv run pytest tests/test_workspace_cli.py -q`
- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run agentic-workspace report --target . --format json`
- `git diff --check`

## Required Tools

- `uv`

## Completion Criteria

- `.agentic-workspace/config.toml` may express one repo-owned `improvement_latitude` value and `agentic-workspace config` reports it.
- `agentic-workspace report --format json` exposes one compact repo-friction evidence object.
- The docs state how improvement latitude stays bounded by delegated judgment, proof, and ownership.
- The first slice can be used in this repo without adding another control layer on top of the configured posture.

## Execution Summary

- Outcome delivered: repo-owned improvement latitude now supports explicit non-acting `none` and `reporting` modes alongside acting modes, and reporting-only destinations are exposed through defaults and workspace report output.
- Validation confirmed: `uv run pytest tests/test_workspace_cli.py -q`; `uv run python scripts/check/check_planning_surfaces.py`; dogfood via `uv run agentic-workspace defaults --section improvement_latitude --format json`; `uv run agentic-workspace config --target . --format json`; `uv run agentic-workspace report --target . --format json`.
- Follow-on routed to: `ROADMAP.md`
- Resume from: calibrate the next improvement-latitude / repo-friction follow-on from real hotspots and moderation burden rather than expanding the policy ladder again.

## Drift Log

- 2026-04-16: Promoted from the highest-priority roadmap lane after live GitHub intake confirmed the improvement-latitude / repo-friction cluster as the clearest next bounded product slice.
- 2026-04-16: Landed repo-owned `workspace.improvement_latitude`, exposed it through `agentic-workspace config` and `defaults`, added `repo_friction.large_file_hotspots` to `agentic-workspace report`, and dogfooded the repo policy with `improvement_latitude = "proactive"`.
- 2026-04-16: Live GitHub intake added `#130`, which sharpens the likely next follow-on for this lane: explicit non-acting `none` and `reporting` modes so repos can surface friction without granting cleanup initiative.
- 2026-04-16: Implemented the `#130` follow-on by extending the policy ladder with `none` and `reporting`, exposing reporting-only destinations through defaults/reporting, and keeping the non-acting modes bounded to report output, review output, or already-owned planning residue.
