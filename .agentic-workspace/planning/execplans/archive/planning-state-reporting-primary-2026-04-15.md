# Planning State And Reporting Primary

## Goal

- Close GitHub issues `#86` and `#85` by making compact planning state and report/summary-first inspection unmistakably primary, while keeping raw planning files and richer prose explicitly secondary.

## Non-Goals

- Do not remove human-readable planning files.
- Do not invent a second planning schema beyond the existing `planning_record` and reporting surfaces.
- Do not widen this slice into the compact operating-map or measurement follow-ons from `#84`, `#88`, or `#87`.

## Intent Continuity

- Larger intended outcome: close the remaining GitHub planning-refinement queue and empty the roadmap without losing the product's token-efficiency posture.
- This slice completes the larger intended outcome: no
- Continuation surface: ROADMAP.md

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: ROADMAP.md
- Activation trigger: when this hierarchy-and-routing tranche is complete and the compact operating-map follow-on for `#84` is ready to promote

## Delegated Judgment

- Requested outcome: make the planning/reporting hierarchy explicit in canonical docs, skills, and checks so agents start from summary/report surfaces first, use raw planning prose only as fallback, and treat `planning_record` as canonical active state when available.
- Hard constraints: preserve human-readable planning files, keep `planning_record` as the canonical compact planning state rather than adding another schema, and keep report/summary surfaces query-first and cheaper than raw-file rereads.
- Agent may decide locally: exact wording, which docs need the strongest hierarchy language, whether one or two narrow planning-surface checks best enforce the contract, and which dogfood flow best proves the updated route.
- Escalate when: the smallest safe implementation would require changing planning summary schema semantics, removing existing human-readable planning surfaces, or widening into a broader workflow-map redesign that belongs in `#84`.

## Active Milestone

- Status: completed
- Scope: tightened the canonical planning/reporting docs, startup/routing guidance, skills, generated quickstart guidance, and planning checks so the compact-state/report-first hierarchy is explicit and auditable.
- Ready: complete
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Promote the compact operating-map tranche from `ROADMAP.md`.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- docs/default-path-contract.md
- .agentic-workspace/docs/reporting-contract.md
- docs/intent-contract.md
- docs/resumable-execution-contract.md
- .agentic-workspace/planning/execplans/README.md
- docs/contributor-playbook.md
- .agentic-workspace/planning/skills/planning-reporting/SKILL.md
- .agentic-workspace/planning/scripts/check/check_planning_surfaces.py

## Invariants

- `planning_record` stays the canonical compact active planning state when it is available.
- `active_contract` and `resumable_contract` stay thinner projections over `planning_record`.
- Report and summary surfaces remain query-first and cheaper than raw planning-file rereads.
- Human-readable planning files remain available, but operational authority must not read as equal for routine inspection.

## Contract Decisions To Freeze

- `agentic-planning-bootstrap summary --format json` is the primary planning-state inspection path.
- `agentic-workspace report --target ./repo --format json` is the primary combined workspace-state inspection path.
- Raw `TODO.md`, `ROADMAP.md`, and execplan prose are fallback surfaces for richer semantics or maintenance, not the default inspection path.

## Open Questions To Close

- Which docs and generated surfaces still make raw planning-file inspection sound equally primary?
- What is the smallest planning-surface checker rule that catches hierarchy drift without forcing broad prose churn?

## Validation Commands

- `uv run pytest packages/planning/tests/test_check_planning_surfaces.py -q`
- `uv run pytest tests/test_workspace_cli.py -q`
- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run agentic-planning-bootstrap summary --format json`
- `uv run agentic-workspace report --target . --format json`

## Completion Criteria

- GitHub issues `#86` and `#85` are closed.
- Canonical docs and skills clearly say `summary/report first`, `selector second`, `raw files only when needed`.
- Planning checks warn when planning docs or startup guidance drift back toward raw-file-first hierarchy.
- One real dogfood pass confirms the updated route works without broad rereading.

## Execution Summary

- Outcome delivered: canonical docs, generated quickstart guidance, and the planning reporting skill now make `agentic-planning-bootstrap summary --format json` and `agentic-workspace report --target ./repo --format json` the explicit first inspection path, with `planning_record` called out as canonical active state and raw planning/module files kept as fallback maintenance surfaces.
- Validation confirmed: `uv run pytest packages/planning/tests/test_check_planning_surfaces.py -q`, `uv run pytest tests/test_workspace_cli.py -q -k "report or summary"`, `uv run python scripts/check/check_planning_surfaces.py`, `uv run python scripts/check/check_source_payload_operational_install.py`, `uv run agentic-planning-bootstrap summary --format json`, `uv run agentic-workspace report --target . --format json`
- Follow-on routed to: ROADMAP.md
- Resume from: promote the compact operating-map tranche for `#84`, then apply the new maintenance guardrail and measurement follow-ons after the map is stable

## Drift Log

- 2026-04-15: Promoted GitHub issues `#86` and `#85` together because the planning-state hierarchy and report-first routing are the same source-of-truth change and should not drift across separate plans.
- 2026-04-15: Closed `#86` and `#85` after tightening canonical docs, generated quickstart guidance, the planning reporting skill, and the planning checker around one explicit hierarchy: summary/report first, selectors second, raw files only when the compact surface is insufficient.
