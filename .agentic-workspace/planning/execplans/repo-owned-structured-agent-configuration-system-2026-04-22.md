# Repo-Owned Structured Agent Configuration System

## Goal

- Close the first roadmap lane through bounded milestones that make the workspace-owned agent-configuration substrate explicit, queryable, and adapter-shaped.

## Non-Goals

- Turning the workspace layer into a scheduler or workflow engine.
- Moving planning or memory domain ownership into workspace.
- Replacing every prose startup surface in one pass.

## Intent Continuity

- Larger intended outcome: build a repo-owned, vendor-independent structured agent configuration system that planning, memory, and future repo-custom workflow extensions can attach to without relying on prose as primary authority.
- This slice completes the larger intended outcome: no
- Continuation surface: .agentic-workspace/planning/execplans/repo-owned-structured-agent-configuration-system-2026-04-22.md
- Parent lane: repo-owned-structured-agent-configuration-system

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: .agentic-workspace/planning/execplans/repo-owned-structured-agent-configuration-system-2026-04-22.md
- Activation trigger: continue through milestone 2 and milestone 3 until issues `#269` through `#274` can close honestly and the roadmap lane can archive.

## Iterative Follow-Through

- What this slice enabled: milestone 1 now has an explicit canonical contract and compact workspace query surfaces for the substrate.
- Intentionally deferred: milestone 2 selective-loading work plus milestone 3 adapter, module-extension, and system-intent integration remain open.
- Discovered implications: the repo already had most primitives; the missing move was to bind them into one named substrate and expose that substrate compactly.
- Proof achieved now: pending milestone-1 closure checks.
- Validation still needed: planning-surface checks, workspace CLI tests, package boundary checks, and root upgrades for the milestone-1 contract.
- Next likely slice: commit milestone 1, then add selective-loading and compact query refinements for milestone 2.

## Intent Interpretation

- Literal request: implement the next lane end-to-end, committing after each milestone
- Inferred intended outcome: close the first roadmap lane through real shipped milestones rather than leaving it as a parent-issue cluster only.
- Chosen concrete what: use one active execplan with three milestones: `#271` model/authority, `#272` selective loading, then `#269` plus `#273` plus `#274` integration and closeout.
- Interpretation distance: medium
- Review guidance: reject work that invents a second config system beside the workspace CLI or that makes planning or memory subordinate to workspace-owned behavior scripting.

## Execution Bounds

- Allowed paths: `.agentic-workspace/docs/`, `.agentic-workspace/planning/`, `src/agentic_workspace/`, `tests/`, `packages/planning/`, `README.md`, `AGENTS.md`, `llms.txt`, `SYSTEM_INTENT.md`
- Max changed files: 45
- Required validation commands: `uv run pytest tests/test_workspace_cli.py -q`; `uv run pytest packages/planning/tests/test_check_planning_surfaces.py -q`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run python scripts/check/check_source_payload_operational_install.py`; `uv run agentic-planning-bootstrap upgrade --target .`; `uv run agentic-memory-bootstrap upgrade --target .`; `uv run agentic-workspace summary --format json`
- Ask-before-refactor threshold: stop before introducing a new top-level package, a new persistent runtime artifact family, or cross-module mutation machinery.
- Stop before touching: unrelated recurring-friction work, machine-first planning-chain internals beyond adapter/query integration, or graceful-compliance work outside this lane.

## Stop Conditions

- Stop when: the next improvement would require turning workspace defaults/config into a scheduler-like workflow engine.
- Escalate when boundary reached: closing the lane would require moving planning or memory domain ownership into workspace.
- Escalate on scope drift: the work spreads into unrelated roadmap lanes or needs a new module family.
- Escalate on proof failure: the substrate cannot be made cheaper to query than the surrounding prose surfaces.

## Context Budget

- Live working set: issues `#269` through `#274`, workspace defaults/config/report outputs, the canonical substrate doc, adapter surfaces, and module attachment points.
- Recoverable later: older ownership/module archives and broader doctrine can be reloaded from summary plus canonical docs.
- Externalize before shift: milestone boundary, proof state, compact query surfaces added, and which surfaces remain adapters.
- Pre-work config pull: use `agentic-workspace config --target . --format json` for startup filename, workflow artifact profile, and mixed-agent posture while keeping the substrate contract authoritative for class and owner boundaries.
- Pre-work memory pull: use only existing durable boundary notes if a planning-memory ownership question reappears; otherwise keep this lane workspace-first.
- Tiny resumability note: this lane is about explicit substrate authority and cheap queries, not execution scripting.
- Context-shift triggers: shift after each committed milestone or if a later slice needs a new owner surface beyond workspace defaults/config/report plus canonical docs.

## Delegated Judgment

- Requested outcome: close the structured agent configuration lane through compact, reviewable milestones that make the workspace substrate explicit and operational.
- Hard constraints: preserve selective adoption, keep prose as adapters, keep system intent directional rather than scheduler-like, and commit after each milestone.
- Agent may decide locally: exact doc names, compact query section names, descriptor metadata shape, and the smallest adapter wording that makes the authority shift explicit.
- Escalate when: a milestone can no longer stay bounded without reopening package boundaries or building generic workflow automation.

## Active Milestone

- ID: repo-owned-structured-agent-configuration-system-2026-04-22
- Status: in-progress
- Scope: milestone 1 (`#271`) define the structured configuration model, authority map, and module attachment points through a canonical workspace contract plus compact defaults/report/config exposure.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Rerun planning-surface checks, then stage and commit the milestone-1 contract and workspace query changes.

## Blockers

- None.

## Touched Paths

- `.agentic-workspace/docs/`
- `.agentic-workspace/planning/`
- `src/agentic_workspace/`
- `tests/`
- `packages/planning/`

## Invariants

- The workspace layer exposes substrate truth and composition boundaries; it does not own planning or memory domain state.
- Selective loading must become clearer and cheaper, not broader.
- Prose startup files remain compatibility adapters once the substrate exists.
- System intent stays distinct from task intent and proof.

## Contract Decisions To Freeze

- The structured agent-configuration substrate lives at the workspace layer and remains queryable through compact workspace surfaces.
- Planning and memory attach to that substrate as modules with their own owned state rather than as prose-only branches.
- Repo-owned prose startup and handoff files are adapters over structured configuration authority, not the primary authority themselves.

## Open Questions To Close

- Milestone 2: which selective-loading answers should become the canonical compact queries for substrate discovery?
- Milestone 3: which minimum module and adapter fields are enough to support repo-custom workflow extensions without inventing a workflow engine?

## Validation Commands

- `uv run pytest tests/test_workspace_cli.py -q`
- `uv run pytest packages/planning/tests/test_check_planning_surfaces.py -q`
- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run python scripts/check/check_source_payload_operational_install.py`
- `uv run agentic-planning-bootstrap upgrade --target .`
- `uv run agentic-memory-bootstrap upgrade --target .`
- `uv run agentic-workspace summary --format json`

## Required Tools

- `gh` for live issue verification and closeout.

## Completion Criteria

- The lane has one explicit workspace-owned substrate contract tying together config, ownership, module attachment, selective loading, prose adapters, and system-intent usage.
- Compact workspace query surfaces answer the high-value substrate questions directly.
- Prose startup and handoff surfaces become explicitly adapter-shaped.
- Repo-custom workflow extension points are explicit enough to live in the substrate without making planning the extension host.
- System intent shapes slice means, review, and follow-on in a compact operational way.
- Issues `#269` through `#274` can close honestly and the roadmap lane can archive with clear continuation residue.

## Execution Run

- Run status: in-progress
- Executor: Codex
- Handoff source: roadmap lane plus live GitHub issue cluster
- What happened: implemented milestone-1 code for the canonical substrate contract, compact defaults/report/config exposure, and planning payload wiring; planning-surface cleanup is the remaining pre-commit step.
- Scope touched: workspace contract docs, workspace CLI/report surfaces, planning payload inventory, contract inventory, tests, and active planning residue.
- Changed surfaces: `.agentic-workspace/docs/workspace-config-contract.md`, `packages/planning/bootstrap/.agentic-workspace/docs/workspace-config-contract.md`, `packages/planning/src/repo_planning_bootstrap/installer.py`, `src/agentic_workspace/cli.py`, `src/agentic_workspace/workspace_output.py`, `src/agentic_workspace/contracts/contract_inventory.json`, `tests/test_workspace_cli.py`, and planning state/execplan surfaces.
- Validations run: `uv run pytest tests/test_workspace_cli.py -q`; `uv run pytest packages/planning/tests/test_packaging.py -q`; `uv run pytest packages/planning/tests/test_check_planning_surfaces.py -q`; `uv run python scripts/check/check_source_payload_operational_install.py`; `uv run agentic-planning-bootstrap upgrade --target .`; `uv run agentic-memory-bootstrap upgrade --target .`; `uv run agentic-workspace summary --format json`
- Result for continuation: milestone-1 implementation is ready once planning-surface warnings are cleared and the commit is cut.
- Next step: make the execplan checker-clean, rerun summary, then commit milestone 1.

## Finished-Run Review

- Review status: pending
- Scope respected: pending
- Proof status: pending
- Intent served: pending
- Config compliance: pending
- Misinterpretation risk: medium
- Follow-on decision: pending

## Execution Summary

- Outcome delivered: milestone 1 implementation is in place but not yet committed.
- Validation confirmed: targeted tests and boundary checks passed; planning-surface cleanup remains before milestone-1 closeout.
- Follow-on routed to: .agentic-workspace/planning/execplans/repo-owned-structured-agent-configuration-system-2026-04-22.md
- Post-work posterity capture: preserve the canonical substrate contract and compact query surfaces in workspace-owned docs and CLI/report outputs.
- Knowledge promoted (Memory/Docs/Config): workspace docs plus defaults/config/report exposure for the agent-configuration substrate.
- Resume from: planning-surface cleanup, then milestone-1 commit.

## Closure Check

- Slice status: in progress
- Larger-intent status: open
- Closure decision: keep-active
- Why this decision is honest: milestone 1 is not committed yet and milestone 2 plus milestone 3 remain open.
- Evidence carried forward: the active execplan, the live issue cluster, and the milestone-1 implementation already in the worktree.
- Reopen trigger: finish the current milestone and reassess closure after each committed slice.

## Drift Log

- 2026-04-22: Promoted the first roadmap lane into one active execplan after verifying issues `#269` through `#274` are still open with `gh`.
- 2026-04-22: Implemented the milestone-1 canonical contract and compact query surfaces; planning cleanup remains before commit.
