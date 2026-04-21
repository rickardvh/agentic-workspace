# Local-Only Residue Via Git Exclude

## Goal

- Re-establish issue `#231` as a broader ownership-boundary lane: keep package-owned state inside `.agentic-workspace/`, justify every remaining repo-facing surface as genuinely repo-owned, and keep local-only or uninstall residue low as a consequence of that boundary.

## Intake Source

- System: GitHub Issues
- ID: `#231`
- URL: <https://github.com/rickardvh/agentic-workspace/issues/231>
- Title: `[Workspace]: Separate package-owned state cleanly from repo-owned surfaces so install and uninstall become low-residue operations even for local-only mode`
- Last verified: 2026-04-21
- Captured reason: the issue was updated to make the remaining scope explicit across memory, `docs/`, config, startup hooks, and uninstallability, so the active plan needs to reflect the broader lane rather than the already-completed planning-state move alone.

## Encoded Intent

- Issue intent: ownership should determine location more than subject matter; package-created and package-maintained artifacts belong under `.agentic-workspace/` unless ownership genuinely changes and the surface is deliberately promoted into a repo-owned contract.
- Implementation intent: treat the planning-state move as already-achieved evidence, then review the remaining repo-facing memory, docs, config, and startup surfaces under the stricter ownership rule instead of using local-only residue as the only proxy proof.

## Non-Goals

- Treat the planning-state move as sufficient closure for the whole lane.
- Delete every repo-facing surface by default.
- Remove the root startup hook or the ownership boundary review without first proving they are not genuine repo contracts.
- Introduce a new storage backend.
- Rewrite installer architecture outside the residue path.
- Commit the product to remote or shared storage.
- Declare the lane complete before the remaining repo-facing surfaces are either justified or tightened.

## Machine-Readable Contract

- Slice ID: OWNERSHIP-BOUNDARY-AND-LOCAL-ONLY-MODE
- Slice state: in-progress
- State source: `.agentic-workspace/planning/state.toml`
- Compatibility views: none

## Intent Continuity

- Larger intended outcome: Cleaner package/repo separation with one unambiguous package-owned home for package-maintained state, a minimal repo hook, and repo-root surfaces that remain only when they are durable repo contracts.
- This slice completes the larger intended outcome: yes
- Continuation surface: none
- Parent lane: ownership-boundary-and-local-only-mode

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Iterative Follow-Through

- What this slice enabled: the ownership ledger, docs, payload mirrors, and live memory contract now agree on the package-owned versus repo-owned boundary that issue `#231` asked to make explicit.
- Intentionally deferred: any broad installer redesign or backend/storage work beyond what the ownership review proves necessary.
- Discovered implications: the root `memory/` tree is a deliberate repo-owned durable-knowledge contract, while `.agentic-workspace/memory/` is the package-owned support home; the previous `memory/current/active-decisions.md` note was boundary debt rather than a justified contract.
- Navigation difficulty discovered during interruption recovery: package source, package payload, and operational install are still too easy to confuse during active maintainer work, especially when an interrupted session left only a partial migration in place.
- Orientation difficulty discovered during interruption recovery: re-establishing which open issues were follow-on product gaps versus direct blockers for this lane took extra issue and planning-surface rereading, which is a sign the current product shape still exposes too much planner-internal structure up front.
- Deferred planning-trust follow-ons surfaced from the premature closeout: #236 separate slice completion from lane completion, #237 require an explicit gap check before archive or close, and #238 make closure depend on evidence, not confidence.
- Proof achieved now: `agentic-workspace report` no longer crashes on empty findings, fresh `init` installs inherit the corrected ownership ledger, and the checked-in boundary explicitly classifies repo-owned `memory/` separately from package-managed `.agentic-workspace/memory/`.
- Validation still needed: none for `#231`; broader product-shape follow-ons remain tracked separately in `#236`, `#237`, and `#238`.
- Next likely slice: none for this lane.

## Contract Decisions To Freeze

- Ownership, not subject matter, is the default placement rule: package-created or package-maintained artifacts stay under `.agentic-workspace/` unless ownership genuinely changes.
- The planning-state move is evidence for this lane, not closure for the whole lane.
- Local-only residue and uninstall cleanliness are proof signals for the ownership boundary, not a separate product goal with different routing.
- Future storage flexibility remains a design constraint only; this lane must not turn it into a near-term backend feature.

## Open Questions To Close

- Is repo-root `memory/` still a deliberate repo-owned contract, or has enough of it become package-managed that it should collapse back into `.agentic-workspace/`?
- Which parts of repo-root `docs/` are durable repo documentation versus package-maintained routing, planning, or install material?
- Are the current startup hook and config surfaces already minimal repo-owned contracts, or do they still leak package concerns outward by default?

## Delegated Judgment

- Requested outcome: issue `#231` and the ownership-boundary lane it represents.
- Hard constraints: preserve genuine repo-owned contracts, keep local-only and checked-in modes compatible, avoid broad installer rewrites, and do not turn future storage flexibility into an immediate feature commitment.
- Agent may decide locally: the exact classification method for ambiguous surfaces, the minimum repo hook that should remain, and the cleanup order if a surface clearly belongs back under `.agentic-workspace/`.
- Escalate when: resolving the remaining ambiguity now requires a product-level decision about whether `memory/`, `docs/`, or config are repo contracts by doctrine rather than by current implementation convenience.

## Active Milestone

- Status: completed
- Scope: Reingest the updated `#231` framing, classify the remaining repo-facing ownership boundary, and implement the boundary corrections needed to make that classification hold in live installs and reports.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this completed plan and remove the matched active-item residue from `.agentic-workspace/planning/state.toml`.

## Blockers

- None.

## Touched Paths

- Core boundary docs: `docs/ownership-authority-contract.md`, `docs/compatibility-policy.md`, `docs/collaboration-safety.md`, `docs/integration-contract.md`, `docs/contributor-playbook.md`, `docs/architecture.md`
- Repo startup and config surfaces: `AGENTS.md`, `agentic-workspace.toml`, `.agentic-workspace/WORKFLOW.md`, `.agentic-workspace/OWNERSHIP.toml`
- Repo docs and intake policy: `docs/upstream-task-intake.md`, `docs/installer-behavior.md`, `docs/extraction-and-discovery-contract.md`
- Memory decision surfaces: `memory/decisions/installed-system-consolidation-2026-04-05.md`, `memory/decisions/workspace-orchestrator-ownership-ledger-2026-04-05.md`
- Memory package contract: `packages/memory/AGENTS.md`, `packages/memory/README.md`, `packages/memory/bootstrap/README.md`, `packages/memory/bootstrap/AGENTS.template.md`, `packages/memory/src/repo_memory_bootstrap/cli.py`, `packages/memory/tests/test_installer.py`
- Memory payload surfaces: `packages/memory/bootstrap/memory/index.md`, `packages/memory/bootstrap/memory/system/WORKFLOW.md`, `packages/memory/bootstrap/memory/system/SKILLS.md`, `packages/memory/bootstrap/memory/bootstrap/README.md`, `packages/memory/bootstrap/memory/bootstrap/skills/install/SKILL.md`, `packages/memory/bootstrap/memory/skills/REGISTRY.json`, `packages/memory/memory/index.md`, `packages/memory/tests/fixtures/routing/memory-index-template.md`
- Planning mirrors: `packages/planning/bootstrap/docs/upstream-task-intake.md`, `packages/planning/bootstrap/docs/candidate-lanes-contract.md`

## Invariants

- Local-only install and uninstall must remain symmetric.
- The repo-root should not accumulate tracked residue purely for package-owned planning, memory, docs, or config storage.
- The ownership boundary review remains available and unchanged unless the next slice explicitly needs it.
- Package-owned state should default to `.agentic-workspace/` unless ownership genuinely changes.
- Storage location and ownership classification must stay conceptually separate.

## Validation Commands

- uv run pytest tests/test_workspace_cli.py -q -k "ownership_command_reports_authority_map or ownership_real_init_classifies_repo_memory_separately_from_managed_support or report_real_init_summarizes_combined_workspace_state or report_handles_modules_with_empty_findings_lists"
- uv run pytest packages/memory/tests/test_installer.py -q
- uv run pytest packages/memory/tests/test_check_memory_freshness.py -q
- uv run python scripts/check/check_source_payload_operational_install.py
- uv run python scripts/check/check_planning_surfaces.py
- uv run agentic-workspace ownership --target . --format json
- uv run agentic-workspace report --target . --format json
- uv run agentic-planning-bootstrap upgrade --target .
- uv run agentic-memory-bootstrap upgrade --target .

## Completion Criteria

- Package-owned state has a clear and more complete home inside the package-owned domain.
- Repo-owned versus package-owned surfaces are easier to distinguish and reason about across planning, memory, docs, config, and startup hooks.
- Local-only install/uninstall continue to work as consequences of that boundary, not as the only proof of completion.
- The remaining repo-facing surfaces look like deliberate repo-owned contracts rather than leftover package interweaving, or they are routed as explicit follow-on tightening work before closeout.

## Execution Summary

- Outcome delivered: the repo now treats `memory/` as a deliberate repo-owned durable-memory contract, `.agentic-workspace/memory/` as package-managed support, removes `memory/current/active-decisions.md` from the live contract, fixes the empty-findings crash in `agentic-workspace report`, and updates fresh-install ownership payloads to match the checked-in ledger.
- Validation confirmed: `uv run pytest tests/test_workspace_cli.py -q -k "ownership_command_reports_authority_map or ownership_real_init_classifies_repo_memory_separately_from_managed_support or report_real_init_summarizes_combined_workspace_state or report_handles_modules_with_empty_findings_lists"`; `uv run pytest packages/memory/tests/test_installer.py -q`; `uv run pytest packages/memory/tests/test_check_memory_freshness.py -q`; `uv run python scripts/check/check_source_payload_operational_install.py`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-workspace ownership --target . --format json`; `uv run agentic-workspace report --target . --format json`; `uv run agentic-planning-bootstrap upgrade --target .`; `uv run agentic-memory-bootstrap upgrade --target .`.
- Follow-on routed to: none for `#231`; broader planning-trust follow-ons remain on issues `#236`, `#237`, and `#238`.
- Knowledge promoted (Memory/Docs/Config): `.agentic-workspace/OWNERSHIP.toml`, `docs/ownership-authority-contract.md`, `docs/architecture.md`, `memory/index.md`, `memory/manifest.toml`, `memory/decisions/README.md`, `packages/memory/bootstrap/README.md`, `packages/memory/memory/index.md`, `src/agentic_workspace/_payload/.agentic-workspace/OWNERSHIP.toml`
- Resume from: none; lane completed.

## Proof Report

- Validation proof: `uv run pytest tests/test_workspace_cli.py -q -k "ownership_command_reports_authority_map or ownership_real_init_classifies_repo_memory_separately_from_managed_support or report_real_init_summarizes_combined_workspace_state or report_handles_modules_with_empty_findings_lists"`; `uv run pytest packages/memory/tests/test_installer.py -q`; `uv run pytest packages/memory/tests/test_check_memory_freshness.py -q`; `uv run python scripts/check/check_source_payload_operational_install.py`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-workspace ownership --target . --format json`; `uv run agentic-workspace report --target . --format json`; `uv run agentic-planning-bootstrap upgrade --target .`; `uv run agentic-memory-bootstrap upgrade --target .`
- Proof achieved now: the broader ownership rule from `#231` now explains the live repo-facing surface set without falling back to historical layout convenience, and both fresh installs and current reports honor that classification.
- Evidence for "Proof achieved" state: ownership output now reports repo-owned `memory/` separately from package-managed `.agentic-workspace/memory/`; fresh `init` installs emit the corrected ownership ledger; the live memory contract no longer routes through `memory/current/active-decisions.md`; `agentic-workspace report` succeeds even when module findings are empty; and source/payload/root-install plus planning-surface checks report no drift.

## Intent Satisfaction

- Original intent: separate package-owned state cleanly from repo-owned surfaces so install and uninstall become low-residue operations even for local-only mode.
- Was original intent fully satisfied?: yes
- Evidence of intent satisfaction: the remaining ambiguous ownership boundary was classified and implemented end-to-end: repo-root `memory/` stays only as durable repo knowledge, package-managed support moved or remained under `.agentic-workspace/`, stale package-owned decision state was removed from the root memory contract, fresh-install ownership payloads now match the checked-in ledger, and the resulting install/report/check flows validate without boundary drift.
- Unsolved intent passed to: none

## Drift Log

- 2026-04-21: Reingested the updated issue `#231` and widened the active lane from the planning-state move to the broader ownership review across memory, docs, config, startup hooks, and uninstall residue.
- 2026-04-21: Preserved the earlier planning-state proof as already-achieved evidence instead of letting it masquerade as full lane closure.
- 2026-04-21: Classified root `memory/` as a deliberate repo-owned durable-memory contract, removed `memory/current/active-decisions.md` from the live contract, fixed `agentic-workspace report` for empty findings, and synchronized the fresh-install ownership payload with the checked-in ownership ledger.
- 2026-04-20: The prior slice finished the state-first planning migration and removed installed compatibility queue views, which now serves as input proof for the broader boundary review.
