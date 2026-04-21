# Local-Only Residue Via Git Exclude

## Goal

- Re-establish issue `#231` as a broader ownership-boundary lane: root-level artefacts are the smell, package-owned state should collapse inward under `.agentic-workspace/`, and outward promotion should happen only when ownership genuinely changes.

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
- Interrupt the current migration tranche or use this lane as permission to derail already-active migration work.
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
- This slice completes the larger intended outcome: no
- Continuation surface: `.agentic-workspace/planning/state.toml` (`roadmap` lane `ownership-boundary-and-root-footprint-reduction`)
- Parent lane: ownership-boundary-and-local-only-mode

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: `.agentic-workspace/planning/state.toml` (`roadmap` lane `ownership-boundary-and-root-footprint-reduction`)
- Activation trigger: current migration work reaches the next boundary-cleanup tranche, at which point root `memory/`, leaked config, and hybrid package-owned `docs/` material should be collapsed back into package-owned homes unless they are strongly justified as true repo contracts.

## Iterative Follow-Through

- What this slice enabled: the incorrect closeout exposed exactly where the product and planning still default to justifying root-visible surfaces instead of treating them as boundary debt.
- Intentionally deferred: any broad installer redesign or backend/storage work beyond what the ownership review proves necessary.
- Discovered implications: repo-specific does not equal repo-owned; root `memory/`, root config, and hybrid `docs/` surfaces remain suspicious until the migration tranche explicitly proves otherwise or moves them inward.
- Navigation difficulty discovered during interruption recovery: package source, package payload, and operational install are still too easy to confuse during active maintainer work, especially when an interrupted session left only a partial migration in place.
- Orientation difficulty discovered during interruption recovery: re-establishing which open issues were follow-on product gaps versus direct blockers for this lane took extra issue and planning-surface rereading, which is a sign the current product shape still exposes too much planner-internal structure up front.
- Deferred planning-trust follow-ons surfaced from the premature closeout: #236 separate slice completion from lane completion, #237 require an explicit gap check before archive or close, and #238 make closure depend on evidence, not confidence.
- Proof achieved now: `agentic-workspace report` no longer crashes on empty findings, and the previous `memory/current/active-decisions.md` note was removed from the live memory contract.
- Validation still needed: the next boundary tranche still needs to minimize repo-root footprint, move package-owned state under `.agentic-workspace/`, and split package/system-owned versus repo-specific-but-still-package-owned artefacts inside that domain.
- Next likely slice: reopen `#231` as inward boundary cleanup after the current migration tranche finishes, starting with explicit relocation targets for root `memory/`, leaked config, and package-owned planning/memory/install/routing material in `docs/`.

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
- Scope: Reingest the updated `#231` framing, then make a first pass at ownership classification and supporting fixes. This archived slice is a premature closeout record, not evidence that the larger lane is done.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Keep this as an archived premature-closeout record and carry the remaining lane forward in roadmap planning instead of treating `#231` as satisfied.

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

- uv run pytest tests/test_workspace_cli.py -q -k "ownership_command_reports_authority_map or ownership_real_init_does_not_settle_repo_root_memory_as_repo_owned_contract or report_real_init_summarizes_combined_workspace_state or report_handles_modules_with_empty_findings_lists"
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

- Outcome delivered: fixed the empty-findings crash in `agentic-workspace report`, removed `memory/current/active-decisions.md` from the live memory contract, and exposed that the broader `#231` lane was closed on the wrong default.
- Validation confirmed: `uv run pytest tests/test_workspace_cli.py -q -k "ownership_command_reports_authority_map or ownership_real_init_does_not_settle_repo_root_memory_as_repo_owned_contract or report_real_init_summarizes_combined_workspace_state or report_handles_modules_with_empty_findings_lists"`; `uv run pytest packages/memory/tests/test_installer.py -q`; `uv run pytest packages/memory/tests/test_check_memory_freshness.py -q`; `uv run python scripts/check/check_source_payload_operational_install.py`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-workspace ownership --target . --format json`; `uv run agentic-workspace report --target . --format json`; `uv run agentic-planning-bootstrap upgrade --target .`; `uv run agentic-memory-bootstrap upgrade --target .`.
- Follow-on routed to: `.agentic-workspace/planning/state.toml` roadmap lane `ownership-boundary-and-root-footprint-reduction`; related planning-trust follow-ons remain on issues `#236`, `#237`, and `#238`.
- Knowledge promoted (Memory/Docs/Config): `memory/index.md`, `memory/manifest.toml`, `memory/decisions/README.md`, `src/agentic_workspace/cli.py`
- Resume from: the next migration-backed boundary cleanup tranche should start from the corrected default that root artefacts are presumptively boundary debt, not presumptively justified contracts.

## Proof Report

- Validation proof: `uv run pytest tests/test_workspace_cli.py -q -k "ownership_command_reports_authority_map or ownership_real_init_does_not_settle_repo_root_memory_as_repo_owned_contract or report_real_init_summarizes_combined_workspace_state or report_handles_modules_with_empty_findings_lists"`; `uv run pytest packages/memory/tests/test_installer.py -q`; `uv run pytest packages/memory/tests/test_check_memory_freshness.py -q`; `uv run python scripts/check/check_source_payload_operational_install.py`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-workspace ownership --target . --format json`; `uv run agentic-workspace report --target . --format json`; `uv run agentic-planning-bootstrap upgrade --target .`; `uv run agentic-memory-bootstrap upgrade --target .`
- Proof achieved now: the bounded fixes in this slice are real, but they do not prove that root `memory/`, leaked config, or hybrid package-owned `docs/` material are justified repo-owned contracts.
- Evidence for "Proof achieved" state: the validation above proves the report fix and the memory-contract cleanup; it does not prove the larger boundary-cleanup intent, which remains open and was prematurely declared complete.

## Intent Satisfaction

- Original intent: separate package-owned state cleanly from repo-owned surfaces so install and uninstall become low-residue operations even for local-only mode.
- Was original intent fully satisfied?: no
- Evidence of intent satisfaction: this slice improved part of the contract surface, but it used the wrong default by treating some root-visible artefacts as justified once they were classifiable; the corrected interpretation is that root artefacts are the smell and should move inward unless ownership has truly changed.
- Unsolved intent passed to: `.agentic-workspace/planning/state.toml` roadmap lane `ownership-boundary-and-root-footprint-reduction` and issue `#231`

## Drift Log

- 2026-04-21: Reingested the updated issue `#231` and widened the active lane from the planning-state move to the broader ownership review across memory, docs, config, startup hooks, and uninstall residue.
- 2026-04-21: Preserved the earlier planning-state proof as already-achieved evidence instead of letting it masquerade as full lane closure.
- 2026-04-21: Prematurely closed the broader lane by treating root `memory/` and root config as justified repo-owned contracts; this archive now records that mistake and routes the larger intent back into roadmap planning with the corrected inward-default interpretation.
- 2026-04-20: The prior slice finished the state-first planning migration and removed installed compatibility queue views, which now serves as input proof for the broader boundary review.
