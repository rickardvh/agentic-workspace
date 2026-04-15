# GitHub Issues 89-91 Discoverability

## Goal

- Ingest GitHub issues `#89` through `#91`, evaluate which reported gaps are real, and land the smallest product-facing docs/install-surface fixes that improve package architecture context and memory guidance discoverability.

## Non-Goals

- Do not broaden into the larger measurement tranche from GitHub issue `#87`.
- Do not redesign memory doctor or the planning/memory ownership contract.
- Do not introduce new lifecycle behavior or schema beyond guidance/discoverability tightening.

## Intent Continuity

- Larger intended outcome: keep third-party agent feedback flowing into bounded product improvements instead of letting valid friction sit as unstructured intake.
- This slice completes the larger intended outcome: no
- Continuation surface: `ROADMAP.md`

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: `ROADMAP.md`
- Activation trigger: after this tranche lands, the next promoted follow-through is GitHub issue `#87`

## Delegated Judgment

- Requested outcome: fix the concrete issue subset that is already supported by repo evidence and can be resolved with small docs/payload changes.
- Hard constraints: keep source, payload, and root install boundaries explicit; prefer discoverability fixes over new concepts; leave strategic backlog items in `ROADMAP.md`.
- Agent may decide locally: exact wording, which guidance surfaces need the clarification, and whether focused regression assertions should tighten the changed contract.
- Escalate when: an issue turns out to require new lifecycle behavior, invasive payload mutation, or conflict with current package ownership boundaries.

## Active Milestone

- Status: completed
- Scope: updated issue intake, clarified package-local architecture context, exposed memory starter templates in installed guidance, and made improvement-pressure metadata easier to discover from memory package docs and payload workflow surfaces
- Ready: complete
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Promote GitHub issue `#87` when the next measurement tranche is ready to run.

## Blockers

- None.

## Touched Paths

- `ROADMAP.md`
- `TODO.md`
- `docs/execplans/`
- `packages/planning/AGENTS.md`
- `packages/memory/AGENTS.md`
- `packages/memory/README.md`
- `packages/memory/bootstrap/README.md`
- `packages/memory/bootstrap/memory/index.md`
- `packages/memory/bootstrap/memory/system/WORKFLOW.md`
- `packages/memory/tests/test_installer.py`

## Invariants

- Package-local `AGENTS.md` must keep the workspace layer thin and package/root-install ownership explicit.
- Memory starter guidance must stay repo-agnostic and advisory rather than turning templates into required process.
- Improvement-pressure fields remain optional metadata; discoverability should improve without making those fields mandatory.

## Contract Decisions To Freeze

- GitHub issue `#87` stays roadmap-level strategic work; it is not silently folded into this smaller tranche.
- GitHub issues `#89` through `#91` are treated as one docs/discoverability slice because the reported friction converges on guidance visibility rather than distinct runtime defects.

## Open Questions To Close

- Which installed surfaces should carry the starter-template and improvement-metadata pointers so fresh adopters see them without broad rereading?

## Validation Commands

- `uv run pytest packages/memory/tests/test_installer.py -q -k "bootstrap_workflow_doc_includes_note_maintenance_and_skill_precedence_guidance or bootstrap_index_includes_token_efficiency_and_small_routing_examples or bootstrap_readme_includes_optional_patterns_and_project_state_shape or memory_note_template_includes_improvement_signal_metadata"`
- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run agentic-memory-bootstrap upgrade --target .`
- `uv run python scripts/check/check_source_payload_operational_install.py`

## Required Tools

- None.

## Completion Criteria

- `ROADMAP.md` reflects the live GitHub intake tranche and the disposition of issues `#87` through `#91`.
- Package-local `AGENTS.md` files explain the three-layer workspace/package/install architecture more explicitly.
- Installed memory guidance points new adopters to starter note templates and exposes improvement-pressure fields in a compact discoverable way.
- Focused tests and maintainer checks pass.

## Execution Summary

- Outcome delivered: ingested GitHub issues `#87` through `#91`, kept `#87` as the next strategic roadmap candidate, clarified the three-layer workspace/package/install context in both package-local `AGENTS.md` files, and exposed starter templates plus improvement-pressure metadata more directly in the memory package README and installed payload guidance.
- Validation confirmed: `uv run pytest packages/memory/tests/test_installer.py -q -k "bootstrap_workflow_doc_includes_note_maintenance_and_skill_precedence_guidance or bootstrap_index_includes_token_efficiency_and_small_routing_examples or bootstrap_readme_includes_optional_patterns_and_project_state_shape or memory_note_template_includes_improvement_signal_metadata"`, `uv run agentic-memory-bootstrap upgrade --target .`, `uv run python scripts/check/check_source_payload_operational_install.py`
- Follow-on routed to: `ROADMAP.md`
- Resume from: promote GitHub issue `#87` when the lazy-discovery measurement tranche is the highest-value active work.

## Drift Log

- 2026-04-15: Plan created for the docs/discoverability tranche promoted from GitHub issues `#89` through `#91` while leaving `#87` queued in `ROADMAP.md`.
- 2026-04-15: Closed the tranche by tightening package-local architecture context and memory discoverability surfaces, then reran the focused package and boundary validation lanes.
