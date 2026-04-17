# Module Reporting First Slice

## Goal

- Ship canonical compact module reporting surfaces so planning and memory state can be summarized without reading raw module files first.

## Non-Goals

- Replace canonical planning or memory state with report output.
- Turn reporting into a second editable workflow layer.
- Redesign memory trust/usefulness policy in the same slice just because the new report exposes existing weaknesses.
- Rewrite the shared workspace CLI while landing the reporting contract.

## Intent Continuity

- Larger intended outcome: Each installed module exposes one compact derived state report with shared reporting vocabulary, and the workspace report can consume those module views instead of forcing raw-file inspection.
- This slice completes the larger intended outcome: yes
- Continuation surface: none

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Iterative Follow-Through

- What this slice enabled: Planning and Memory now expose module-owned compact report commands, and the workspace report can surface those module reports directly.
- Intentionally deferred: bounded workspace CLI hotspot reduction and the broader memory trust/usefulness lane that the new memory report makes more visible.
- Discovered implications: Module reporting stays useful only if it remains stricter and quieter than the lower-level doctor/routing/promotion surfaces it derives from.
- Proof achieved now: `agentic-planning-bootstrap report`, `agentic-memory-bootstrap report`, and `agentic-workspace report` all expose compact module-state views with shared field vocabulary and no second state store.
- Validation still needed: ordinary-work dogfooding on the new memory report during the later memory lane.
- Next likely slice: Return to the roadmap queue and take the bounded workspace CLI hotspot lane before widening memory follow-through.

## Delegated Judgment

- Requested outcome: implement the remaining roadmap milestone for canonical module reporting surfaces and keep the follow-on queue bounded.
- Hard constraints: reports must stay derived, compact, machine-readable first, and subordinate to canonical planning/memory state.
- Agent may decide locally: exact report field shape, whether planning needs a thin report wrapper over summary, and how much workspace aggregation is justified.
- Escalate when: the smallest implementation would require a new editable state surface, a broad CLI rewrite, or mixing memory cleanup policy into the reporting tranche.

## Active Milestone

- Status: completed
- Scope: add module report commands for planning and memory, wire them into the workspace report, update the shared reporting contract, and cover the new surfaces with focused tests and contract checks.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this completed slice, close issue `#40`, and advance the roadmap to `#134`.

## Blockers

- None.

## Touched Paths

- ROADMAP.md
- docs/execplans/archive/module-reporting-first-slice-2026-04-17.md
- docs/reporting-contract.md
- packages/planning/README.md
- packages/planning/src/repo_planning_bootstrap/cli.py
- packages/planning/src/repo_planning_bootstrap/installer.py
- packages/planning/tests/test_installer.py
- packages/memory/README.md
- packages/memory/src/repo_memory_bootstrap/cli.py
- packages/memory/src/repo_memory_bootstrap/installer.py
- packages/memory/tests/test_installer.py
- src/agentic_workspace/cli.py
- src/agentic_workspace/contracts/report_contract.json
- src/agentic_workspace/contracts/schemas/workspace_report.schema.json
- src/agentic_workspace/workspace_output.py
- tests/test_workspace_cli.py

## Invariants

- Planning summary and memory doctor/routing/promotion remain the authoritative underlying surfaces.
- Module reports may compress or prioritize derived state, but they must not change canonical truth or execution posture.
- The workspace report remains a combined view, not a second planning or memory schema.

## Contract Decisions To Freeze

- `agentic-planning-bootstrap report --format json` is a compact module report derived from planning summary, not a new planner state file.
- `agentic-memory-bootstrap report --target ./repo --format json` is a compact module report derived from existing doctor/current/routing/promotion surfaces.
- `agentic-workspace report --target ./repo --format json` now carries `module_reports` alongside lifecycle `reports`.

## Open Questions To Close

- How much additional memory trust/usefulness signal should move into the compact memory report versus stay in lower-level audit surfaces?
- Which single workspace CLI concern should be extracted next to reduce reread pressure without widening the workspace layer?

## Validation Commands

- uv run pytest tests/test_workspace_cli.py packages/planning/tests/test_installer.py packages/memory/tests/test_installer.py -q
- uv run python scripts/check/check_planning_surfaces.py
- uv run python scripts/check/check_contract_tooling_surfaces.py
- uv run python scripts/check/check_source_payload_operational_install.py
- uv run agentic-planning-bootstrap report --format json
- uv run agentic-memory-bootstrap report --target . --format json
- uv run agentic-workspace report --target . --format json
- uv run agentic-planning-bootstrap upgrade --target .
- uv run agentic-memory-bootstrap upgrade --target .

## Required Tools

- uv
- gh

## Completion Criteria

- Planning exposes a compact module report derived from summary.
- Memory exposes a compact module report derived from existing canonical surfaces.
- Workspace reporting can surface module reports directly without creating a second state store.
- The reporting contract and schema checks accept the new module report aggregation field.

## Execution Summary

- Outcome delivered: added compact planning and memory module report commands, updated the shared workspace reporting contract and schema to carry `module_reports`, wired the workspace report to consume those module views, and covered the new reporting layer with focused package/workspace tests plus contract drift checks.
- Validation confirmed: `uv run pytest tests/test_workspace_cli.py packages/planning/tests/test_installer.py packages/memory/tests/test_installer.py -q`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run python scripts/check/check_contract_tooling_surfaces.py`; `uv run python scripts/check/check_source_payload_operational_install.py`; live dogfood via `uv run agentic-planning-bootstrap report --format json`, `uv run agentic-memory-bootstrap report --target . --format json`, and `uv run agentic-workspace report --target . --format json`; final root refresh via both package upgrade commands.
- Follow-on routed to: `ROADMAP.md` next candidate `Shared workspace CLI hotspot reduction`, with the memory trust/usefulness lane remaining behind it.
- Resume from: No further action in this plan; promote `#134` when starting the next bounded slice.

## Drift Log

- 2026-04-17: Promoted roadmap issue `#40` into a bounded reporting tranche.
- 2026-04-17: Landed module reports for planning and memory, updated the workspace report contract, and prepared the slice for archive.
