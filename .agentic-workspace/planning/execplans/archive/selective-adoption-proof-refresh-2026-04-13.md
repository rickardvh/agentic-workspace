# Selective-Adoption Proof Refresh

## Goal

- Refresh the proof that memory-only, planning-only, and combined installs still feel clean, cheap, and coherent in practice.
- Fix any concrete product or contract gap found through the narrowest canonical path.

## Non-Goals

- Reopen the extension boundary.
- Build a permanent CI matrix for every selective-adoption shape in one pass.
- Redesign the workspace lifecycle around one-off proof friction.

## Intent Continuity

- Larger intended outcome: selective adoption should remain a first-class product truth, not a doctrinal claim.
- This slice completes the larger intended outcome: yes
- Continuation surface: none

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Delegated Judgment

- Requested outcome: run fresh clean-room proof passes for `memory`, `planning`, and `full`, then tighten the smallest canonical product or docs surface needed to keep selective adoption trustworthy.
- Hard constraints: prefer the workspace lifecycle front door; keep validation narrow and representative; do not widen into portability or bootstrap-policy redesign unless the same evidence genuinely requires it.
- Agent may decide locally: which temporary repo shapes to use, which proof commands are enough for each install shape, and whether the outcome is proof-only or requires a small fix.
- Escalate when: a selective-adoption gap cannot be corrected without broader lifecycle or module-boundary redesign.

## Active Milestone

- Status: completed
- Scope: run clean-room `memory`, `planning`, and `full` installs through `agentic-workspace init`, audit the resulting startup and lifecycle surfaces, and fix the smallest real gap if one appears.
- Ready: completed
- Blocked: none
- optional_deps: GitHub issue `#25`

## Immediate Next Action

- Promote `Portability evidence review` from the highest-priority queue.

## Blockers

- None.

## Touched Paths

- `TODO.md`
- `ROADMAP.md`
- `packages/memory/src/repo_memory_bootstrap/_installer_payload.py`
- `packages/memory/tests/test_installer.py`
- `packages/planning/bootstrap/.agentic-workspace/planning/scripts/check/check_planning_surfaces.py`
- `packages/planning/tests/test_installer.py`
- `.agentic-workspace/planning/execplans/archive/selective-adoption-proof-refresh-2026-04-13.md`

## Invariants

- `memory`, `planning`, and `full` remain first-class supported intents.
- Selective-adoption proof should use the same public lifecycle path that adopters are expected to use.
- Any fix should preserve one-home ownership between planning, memory, and workspace orchestration.

## Validation Commands

- `cd packages/memory && uv run pytest tests/test_installer.py -k "optional_append or absent_optional_append_targets or current_memory_synergy or install_does_not_duplicate_existing_optional_fragment"`
- `cd packages/planning && uv run pytest tests/test_installer.py -k "generic_repo_readme_without_startup_claims or partial_readme_startup_guidance or starter_todo_for_milestone_word_in_hygiene_rules"`
- `uv run ruff check packages/memory packages/planning`
- clean-room `agentic-workspace init/status/doctor` passes for `memory`, `planning`, and `full`

## Completion Criteria

- Fresh clean-room installs provide clear evidence for all three supported adoption shapes.
- Any concrete trust or friction gap found is fixed or rerouted into a narrower backlog lane.
- The resulting proof is archived so later work can build on evidence instead of restating doctrine.

## Execution Summary

- Outcome delivered: yes. Fresh `memory`, `planning`, and `full` installs were re-run through the workspace lifecycle front door and used as the proof surface for selective adoption.
- Validation confirmed: yes. Focused package tests, Ruff, and repeated clean-room lifecycle passes confirmed the proof and the fixes.
- Follow-on routed to: `ROADMAP.md` remains open only for `Portability evidence review` in the highest-priority queue.
- Resume from: promote the portability evidence review milestone.

## Proof Outcome

- `memory` now installs cleanly in a blank repo without surfacing missing optional append targets as warnings; absent `Makefile`, `CONTRIBUTING.md`, and PR-template files now report as optional absence rather than trust failures.
- `planning` now installs cleanly in a blank repo without falsely warning that a generic README is missing maintainer-startup guidance or that the shipped starter `TODO.md` violates its own checker.
- `full` now preserves the same clean split: the remaining doctor follow-up is expected starter customization (`TODO.md` and `ROADMAP.md` placeholders, plus the existing advisory pressure on `.agentic-workspace/memory/repo/index.md`) rather than lifecycle inconsistency.

## Drift Log

- 2026-04-13: Promoted from the highest-priority queue after the cross-agent handoff audit completed and the next unresolved proof question narrowed to selective adoption.
- 2026-04-13: Completed after clean-room installs surfaced two real false-positive checks, both were fixed in-package, and the refreshed proof showed only expected starter follow-up.
