# Native Candidate Lanes First Slice

## Goal

- Add one thin native candidate-lane shape to `ROADMAP.md` so grouped, ordered, promotable future work no longer has to live as ad hoc queue prose.

## Non-Goals

- Do not turn Planning into a backlog system or external tracker clone.
- Do not replace `ROADMAP.md`, `TODO.md`, or execplans with one unified artifact.
- Do not widen this slice into the broader Memory trust/usefulness lane.
- Do not require GitHub issues for the native shape.

## Intent Continuity

- Larger intended outcome: deferred grouped work should stay repo-native, ordered, and promotable without forcing agents to invent new roadmap structures each time.
- This slice completes the larger intended outcome: yes
- Continuation surface: none

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Iterative Follow-Through

- What this slice enabled: a thin native candidate-lane shape can carry grouped deferred work in `ROADMAP.md` and expose it through planning summary/reporting instead of ad hoc queue prose.
- Intentionally deferred: the Memory lane itself, plus any broader roadmap or review-system redesign.
- Discovered implications: archive cleanup and planning checks have to understand the lane shape immediately or the new contract would just create a second stale queue path.
- Proof achieved now: this repo's remaining Memory lane is expressed as a native candidate lane rather than ad hoc queue prose.
- Validation still needed: dogfood the lane shape through ordinary roadmap promotion and future archive cleanup.
- Next likely slice: return to the remaining Memory lane once the native lane shape is installed and the roadmap is quiet again.

## Delegated Judgment

- Requested outcome: land the smallest native candidate-lane contract that replaces the current ad hoc roadmap queue structure.
- Hard constraints: keep the shape file-native, compact, tool-agnostic, and subordinate to `TODO.md` and execplans for active work.
- Agent may decide locally: the exact lane fields, how summary/report surfaces project them, and the minimum docs/checker coverage needed.
- Escalate when: the smallest implementation would require a new planning file, a heavyweight tracker abstraction, or a broad redesign of the planning hierarchy.

## Active Milestone

- Status: completed
- Scope: define the lane shape, parse it in planning summary/reporting, update roadmap/checker/docs, translate the remaining Memory lane into the native form, and archive the slice.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this completed slice, close issue `#135`, and leave the remaining Memory lane as the only roadmap candidate.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- docs/execplans/native-candidate-lanes-first-slice-2026-04-17.md
- packages/planning/README.md
- packages/planning/src/repo_planning_bootstrap/cli.py
- packages/planning/src/repo_planning_bootstrap/installer.py
- packages/planning/tests/test_installer.py
- packages/planning/bootstrap/ROADMAP.md
- packages/planning/bootstrap/docs/execplans/README.md
- packages/planning/bootstrap/docs/candidate-lanes-contract.md
- packages/planning/bootstrap/.agentic-workspace/planning/scripts/check/check_planning_surfaces.py
- docs/candidate-lanes-contract.md

## Invariants

- `ROADMAP.md` remains the single inactive future-candidate surface.
- The lane shape stays lighter than `TODO.md` plus execplans and does not carry active execution state.
- The planning summary remains the preferred compact inspection surface over raw roadmap prose.

## Contract Decisions To Freeze

- Native candidate lanes belong inside `ROADMAP.md`, not in a new planning file.
- A lane needs only compact identity, grouped intent, ordering, promotion, and first-slice fields.
- The planning package should keep a flattened candidate view for compatibility while exposing the richer lane view directly.

## Open Questions To Close

- None for this first slice.

## Validation Commands

- uv run pytest packages/planning/tests/test_installer.py -q
- uv run python scripts/check/check_planning_surfaces.py
- uv run agentic-planning-bootstrap summary --format json
- uv run agentic-planning-bootstrap report --format json
- uv run agentic-planning-bootstrap upgrade --target .
- uv run agentic-memory-bootstrap upgrade --target .
- uv run python scripts/check/check_source_payload_operational_install.py

## Required Tools

- uv
- gh

## Completion Criteria

- Planning defines one native `Candidate Lanes` shape inside `ROADMAP.md`.
- Planning summary/reporting expose that lane shape in machine-readable form.
- The checker accepts and validates the lane shape.
- This repo's remaining Memory lane is translated into the native shape.

## Execution Summary

- Outcome delivered: added a native `Candidate Lanes` shape inside `ROADMAP.md`, exposed it through planning summary/reporting, taught archive cleanup and planning checks to understand it, and translated the remaining Memory roadmap work into that lane format.
- Validation confirmed: `uv run pytest packages/planning/tests/test_installer.py -q`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-planning-bootstrap summary --format json`; `uv run agentic-planning-bootstrap report --format json`; `uv run agentic-planning-bootstrap upgrade --target .`; `uv run agentic-memory-bootstrap upgrade --target .`; `uv run python scripts/check/check_source_payload_operational_install.py`.
- Follow-on routed to: `ROADMAP.md` candidate lane `Memory trust, usefulness, and cleanup ergonomics`.
- Resume from: no further action in this plan; promote the remaining Memory lane when ready.

## Drift Log

- 2026-04-17: Promoted from roadmap issue `#135` after the workspace CLI hotspot slice left the roadmap itself as the next repeated planning friction.
- 2026-04-17: Added the native lane shape, updated planning summary/reporting plus archive cleanup to understand it, refreshed the root install, and translated the live roadmap to the new contract.
