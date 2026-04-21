# Cross-Agent Workflow Robustness Hardening

## Goal

- Make the cheapest machine-readable workflow surfaces easier for weaker or less repo-native agents to follow without repeated user steering.

## Non-Goals

- Prove every agent family now follows the contract equally well.
- Reopen the broader mixed-agent posture or delegation boundary.
- Add repo-local-only workaround guidance as the primary fix.

## Intent Continuity

- Larger intended outcome: Agentic Workspace should improve cross-agent execution quality, not only work well for the strongest agents or the repo's most workflow-native models.
- This slice completes the larger intended outcome: no
- Continuation surface: `ROADMAP.md` candidate `Cross-agent workflow robustness hardening`

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: `ROADMAP.md` candidate `Cross-agent workflow robustness hardening`
- Activation trigger: another mixed-agent pass still misses startup routing, package-managed paths, or same-pass planning cleanup after this machine-readable hardening slice lands

## Delegated Judgment

- Requested outcome: strengthen the shipped machine-readable startup and completion contract so weaker agents can recover the intended workflow more reliably than they can today.
- Hard constraints: keep the slice bounded to workflow-routing and closeout guidance; prefer shipped package and workspace surfaces over repo-local instruction patches; preserve current public entrypoints.
- Agent may decide locally: which machine-readable surfaces to tighten first, how to phrase the new startup and completion cues, and which narrow validation lanes prove the change.
- Escalate when: the smaller fix would not help without reopening mixed-agent policy boundaries, adding a new planning schema, or changing lifecycle ownership.

## Active Milestone

- Status: completed
- Scope: promoted the roadmap item, tightened startup and completion cues in the planning manifest and workspace defaults, refreshed generated/root installs, and validated the relevant package and root lanes.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this completed slice and leave broader mixed-agent follow-on in `ROADMAP.md` only if future dogfooding shows the remaining trigger.

## Blockers

- None.

## Touched Paths

- `TODO.md`
- `ROADMAP.md`
- `.agentic-workspace/planning/execplans/cross-agent-workflow-robustness-hardening-2026-04-13.md`
- `src/agentic_workspace/cli.py`
- `tests/test_workspace_cli.py`
- `packages/planning/bootstrap/.agentic-workspace/planning/agent-manifest.json`
- `packages/planning/tests/test_installer.py`
- `tools/AGENT_QUICKSTART.md`
- `tools/AGENT_ROUTING.md`

## Invariants

- Keep the workspace and planning machine-readable surfaces as the preferred remediation target for cross-agent workflow misses.
- Preserve repo-owned planning state in `TODO.md`, `ROADMAP.md`, and execplans.
- Keep lifecycle entrypoints and package boundaries unchanged.

## Contract Decisions To Freeze

- Cross-agent workflow robustness should improve first through machine-readable routing and completion cues, not through repo-local instruction patches.
- Same-pass cleanup of matched `TODO.md` or `ROADMAP.md` residue should remain an explicit completion reminder in shipped planning surfaces.
- When workflow routing is unclear, agents should prefer machine-readable defaults and manifest surfaces before repo-local workaround prose.

## Open Questions To Close

- None.

## Validation Commands

- `cd packages/planning && uv run pytest tests/test_installer.py -q`
- `uv run pytest tests/test_workspace_cli.py -q`
- `uv run python packages/planning/bootstrap/.agentic-workspace/planning/scripts/render_agent_docs.py`
- `uv run agentic-planning-bootstrap upgrade --target .`
- `uv run python scripts/check/check_planning_surfaces.py`

## Completion Criteria

- Planning's shipped manifest and generated quickstart make package-managed workflow fallback and same-pass queue cleanup explicit.
- Workspace defaults expose the same workflow-recovery and completion cue in machine-readable form.
- Root installed planning surfaces are refreshed from the updated package contract.
- The active queue and roadmap no longer carry duplicate state for this promoted slice.

## Execution Summary

- Outcome delivered: added package-managed workflow-recovery and same-pass completion cues to the shipped planning manifest and to `agentic-workspace defaults`, then refreshed both the planning payload and the root installed surfaces.
- Validation confirmed: `uv run pytest tests/test_workspace_cli.py -q`; `cd packages/planning && uv run pytest tests/test_installer.py -q`; `uv run python packages/planning/bootstrap/.agentic-workspace/planning/scripts/render_agent_docs.py`; `uv run agentic-planning-bootstrap upgrade --target .`; `uv run python scripts/check/check_planning_surfaces.py`
- Follow-on routed to: `ROADMAP.md` only if another mixed-agent pass still misses startup routing, package-managed paths, or same-pass planning cleanup.
- Resume from: no further action in this execplan; reopen from `ROADMAP.md` only on the stated trigger.

## Drift Log

- 2026-04-13: Promoted from the roadmap after repeated mixed-agent dogfooding showed weaker agents still missed startup routing, package-managed paths, and same-pass planning cleanup.