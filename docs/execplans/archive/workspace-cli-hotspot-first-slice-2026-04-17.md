# Workspace CLI Hotspot First Slice

## Goal

- Reduce one repeated shared-workspace CLI hotspot by extracting a coherent report/setup shaping concern from `src/agentic_workspace/cli.py` without widening the workspace layer.

## Non-Goals

- Do not broadly rewrite the workspace CLI.
- Do not create a new module or change workspace/package ownership.
- Do not change the public report or setup contract while reducing the hotspot.
- Do not widen this slice into the Memory follow-through lane.

## Intent Continuity

- Larger intended outcome: repeated repo-friction evidence against the shared workspace CLI should be reduced through bounded ownership tightening rather than tolerated indefinitely.
- This slice completes the larger intended outcome: yes
- Continuation surface: none

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Iterative Follow-Through

- What this slice enabled: the workspace CLI now delegates report/setup discovery, output-contract shaping, and repo-friction payload construction to one dedicated helper surface.
- Intentionally deferred: any broader CLI decomposition beyond this one coherent concern, plus the remaining Memory trust/usefulness lane.
- Discovered implications: hotspot-reduction slices are more reliable when they target one derived shared concern and preserve the root CLI as an orchestrator rather than a second policy surface.
- Proof achieved now: the extracted helper owns the shared report/setup shaping logic and the focused workspace report/setup tests still pass unchanged.
- Validation still needed: ordinary-work dogfooding after later slices to confirm the hotspot actually rereads less often in practice.
- Next likely slice: reprioritize the remaining roadmap between the new native candidate-lane issue and the Memory lane, then promote the next bounded tranche.

## Delegated Judgment

- Requested outcome: close the bounded workspace CLI hotspot lane without turning it into a broad cleanup campaign.
- Hard constraints: preserve current report/setup behavior, keep the workspace layer thin, and avoid introducing a new state owner.
- Agent may decide locally: which coherent concern to extract, whether the extracted helper should stay workspace-local, and the minimum planning updates needed after closure.
- Escalate when: the smallest clean cut would require a public contract change, a new module, or a broad rewrite of unrelated CLI concerns.

## Active Milestone

- Status: completed
- Scope: extract the shared report/setup shaping concern into one helper module, validate the unchanged contract, archive the slice, and close issue `#134`.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this completed slice, close issue `#134`, and reprioritize the remaining roadmap with issue `#135` against the Memory lane.

## Blockers

- None.

## Touched Paths

- ROADMAP.md
- docs/execplans/archive/workspace-cli-hotspot-first-slice-2026-04-17.md
- src/agentic_workspace/cli.py
- src/agentic_workspace/reporting_support.py

## Invariants

- `src/agentic_workspace/cli.py` remains the orchestration entrypoint for workspace commands.
- The extracted helper remains a workspace-local implementation detail, not a new product module.
- Report/setup payloads remain derived from canonical config, lifecycle state, and existing helper inputs.

## Contract Decisions To Freeze

- Shared report/setup shaping logic is a coherent enough concern to extract without changing the public workspace contract.
- Reducing workspace CLI reread pressure should prefer helper-boundary extraction over broad structural churn.

## Open Questions To Close

- Should future hotspot slices continue targeting report/setup shaping, or is another concern now the next reread hotspot?
- Does the new planning issue about native candidate lanes belong ahead of the Memory lane once this hotspot slice is complete?

## Validation Commands

- uv run pytest tests/test_workspace_cli.py -q -k "report_real_init_summarizes_combined_workspace_state or report_surfaces_large_file_hotspots_as_repo_friction_evidence or report_consumes_external_codebase_map_when_present or setup_command_reports_no_new_seed_surfaces_for_mature_repo"
- uv run python scripts/check/check_contract_tooling_surfaces.py

## Required Tools

- uv
- gh

## Completion Criteria

- One coherent workspace CLI concern is extracted to a helper boundary.
- The workspace report/setup behavior remains unchanged under focused tests.
- The roadmap no longer carries `#134` as an open lane after closure.

## Execution Summary

- Outcome delivered: extracted the shared report/setup shaping concern from `src/agentic_workspace/cli.py` into `src/agentic_workspace/reporting_support.py`, leaving the CLI as the caller and preserving the existing workspace report/setup contract.
- Validation confirmed: `uv run pytest tests/test_workspace_cli.py -q -k "report_real_init_summarizes_combined_workspace_state or report_surfaces_large_file_hotspots_as_repo_friction_evidence or report_consumes_external_codebase_map_when_present or setup_command_reports_no_new_seed_surfaces_for_mature_repo"`; `uv run python scripts/check/check_contract_tooling_surfaces.py`.
- Follow-on routed to: `ROADMAP.md`, where the remaining queue must now be reprioritized between planning issue `#135` and the Memory lane.
- Resume from: no further action in this plan; start from the reprioritized roadmap queue.

## Drift Log

- 2026-04-17: Promoted the bounded workspace CLI hotspot lane after module reporting surfaced repeated report/setup reread pressure.
- 2026-04-17: Extracted the report/setup shaping concern into `reporting_support.py` and prepared the lane for closure.
