# Local-Only Residue Via Git Exclude

## Goal

- Consolidate this package's planning state into one explicit package-owned file inside the package install tree, while keeping repo-side residue unobtrusive.

## Encoded Intent

- Issue intent: consolidate this package's data into one clear, unobtrusive package-owned home, leaving repo-owned surfaces only where they are genuinely repo-owned.
- Implementation intent: make local-only state explicit inside the package-owned home and treat residue cleanup as a downstream proof of that boundary.

## Non-Goals

- Change the broader package/repo ownership model.
- Remove the root startup hook or the ownership boundary review.
- Introduce a new storage backend.
- Rewrite installer architecture outside the residue path.
- Declare the lane complete before the package-owned home is unambiguous.

## Machine-Readable Contract

```yaml
slice:
 id: OWNERSHIP-BOUNDARY-AND-LOCAL-ONLY-MODE
 status: in-progress
 state_source: .agentic-workspace/planning/state.toml
 compatibility_views: []
```

## Intent Continuity

- Larger intended outcome: Cleaner package/repo separation with one unambiguous package-owned home for planning state and lower install/uninstall residue.
- This slice completes the larger intended outcome: no
- Continuation surface: docs/execplans/local-only-residue-via-git-exclude.md
- Parent lane: ownership-boundary-and-local-only-mode

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: docs/execplans/local-only-residue-via-git-exclude.md
- Activation trigger: validation that no installed compatibility queue views remain necessary and the remaining repo-facing surfaces are genuinely repo-owned

## Iterative Follow-Through

- What this slice should enable: the active queue and roadmap should live in `.agentic-workspace/planning/state.toml` without any installed compatibility queue views.
- Intentionally deferred: any broader repo-root startup simplification beyond the package-owned planning boundary.
- Discovered implications: the repo-owned startup hook should remain small while the package-owned home carries the active planning state explicitly.
- Navigation difficulty discovered during interruption recovery: package source, package payload, and operational install are still too easy to confuse during active maintainer work, especially when an interrupted session left only a partial migration in place.
- Orientation difficulty discovered during interruption recovery: re-establishing which open issues were follow-on product gaps versus direct blockers for this lane took extra issue and planning-surface rereading, which is a sign the current product shape still exposes too much planner-internal structure up front.
- Deferred planning-trust follow-ons surfaced from the premature closeout: #236 separate slice completion from lane completion, #237 require an explicit gap check before archive or close, and #238 make closure depend on evidence, not confidence.
- Proof needed now: package-owned planning state can be consolidated without forcing the repo to keep active authority in tracked root surfaces.
- Validation still needed: verify which remaining repo-facing surfaces are genuinely repo-owned versus package residue, and confirm uninstall/local-only behavior stays low-residue under that stricter boundary.
- Next likely slice: review the remaining repo-facing ownership set after the planning-view move, then either tighten the boundary further or explicitly narrow the lane.

## Delegated Judgment

- Requested outcome: issue `#231` and the ownership-boundary lane it represents.
- Hard constraints: preserve repo-owned contracts, keep local-only compatible, and avoid broad installer rewrites.
- Agent may decide locally: the exact git-local metadata path, the minimal block format, and the cleanup order.
- Escalate when: the remaining boundary question now requires a broader repo-owned versus package-owned review across Memory, startup hooks, or uninstall semantics rather than another bounded planning-only move.

## Active Milestone

- Status: in-progress
- Scope: Verify whether the ownership-boundary lane is actually complete after the planning-view move, and either tighten the remaining repo-facing surfaces or narrow the lane honestly.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Compare the live issue intent for `#231` against the current ownership report and surface set, then reopen any still-ambiguous repo-facing product surfaces as explicit remaining scope.

## Blockers

- None.

## Touched Paths

- .agentic-workspace/planning/state.toml
- docs/execplans/local-only-residue-via-git-exclude.md
- README.md
- packages/planning/AGENTS.md
- packages/planning/README.md
- packages/planning/src/repo_planning_bootstrap/installer.py
- scripts/check/check_planning_surfaces.py
- AGENTS.md

## Invariants

- Local-only install and uninstall must remain symmetric.
- The repo-root should not accumulate tracked residue purely for package-owned planning storage.
- The ownership boundary review remains available and unchanged unless the next slice explicitly needs it.
- Package-owned planning state should consolidate into one unambiguous package-owned home before the lane can be called complete.
- The state file should remain inside the package-owned install tree, not in repo-root metadata.

## Validation Commands

- uv run pytest tests/test_workspace_cli.py -q -k "local_only or selection_commands_accept_non_interactive_flag"
- uv run python scripts/check/check_planning_surfaces.py
- uv run agentic-planning-bootstrap upgrade --target .
- uv run agentic-memory-bootstrap upgrade --target .
- rg "state.toml" docs packages/planning/src/repo_planning_bootstrap scripts

## Completion Criteria

- Package-owned state has a single clear home inside the package-owned domain.
- Repo-owned surfaces remain only where they are genuinely repo-owned and the repo hook is minimal.
- Local-only install/uninstall continue to work as consequences of that boundary, not as the only proof of completion.
- The lane can explain why the remaining repo-facing surfaces are justified, or it tightens them further before closeout.

## Execution Summary

- Outcome delivered: planning authority stays in `.agentic-workspace/planning/state.toml`, generated queue/roadmap views are no longer installed under `.agentic-workspace/planning/`, and summary/checker surfaces now derive directly from state when no legacy root views exist.
- Validation confirmed: `uv run pytest packages/planning/tests/test_planning_lifecycle.py -q`; `uv run pytest packages/planning/tests/test_installer.py -q`; `uv run pytest packages/planning/tests/test_check_planning_surfaces.py -q`; `uv run agentic-planning-bootstrap upgrade --target .`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-workspace summary --format json`; `uv run pytest tests/test_source_payload_operational_install.py -q`.
- Follow-on routed to: continue the same ownership-boundary lane until the broader issue `#231` intent is either satisfied or explicitly narrowed.
- Knowledge promoted (Memory/Docs/Config): docs/installer-behavior.md, packages/planning/bootstrap/docs/installer-behavior.md
- Resume from: compare the live `#231` issue intent against the remaining repo-facing surfaces and reclassify the lane honestly before closing it.

## Proof Report

- Validation proof: `uv run pytest packages/planning/tests/test_planning_lifecycle.py -q`; `uv run pytest packages/planning/tests/test_installer.py -q`; `uv run pytest packages/planning/tests/test_check_planning_surfaces.py -q`; `uv run agentic-planning-bootstrap upgrade --target .`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-workspace summary --format json`; `uv run pytest tests/test_source_payload_operational_install.py -q`; `rg "state.toml" docs packages/planning/src/repo_planning_bootstrap scripts`
- Proof achieved now: planning summary/install flows are state-first, installed planning no longer writes compatibility queue views, and legacy root views are treated only as migration or cleanup inputs.
- Evidence for "Proof achieved" state: package lifecycle, installer, and planning-surface checks pass; upgrade leaves `.agentic-workspace/planning/state.toml` as the only planning state file; and the workspace summary/checker still report the active lane correctly without installed TODO/ROADMAP projections.

## Intent Satisfaction

- Original intent: separate package-owned state cleanly from repo-owned surfaces so install and uninstall become low-residue operations even for local-only mode.
- Was original intent fully satisfied?: no
- Evidence of intent satisfaction: the planning-state boundary is materially cleaner, but the broader issue still asks whether the remaining repo-facing surfaces are truly repo-owned and whether uninstall/local-only residue is now low enough across the whole package boundary.
- Unsolved intent passed to: this active lane and issue `#231`

## Drift Log

- 2026-04-20: Reopened issue `#231` after the lane was only partially completed and restored the active planning surfaces.
- 2026-04-20: Interrupted while beginning the package-owned planning-state migration; only the `PLANNING_STATE_PATH` constant had been added when work stopped.
- 2026-04-20: Completed state-first migration in installer/summary flows and added root compatibility view generation from `.agentic-workspace/planning/state.toml`.
- 2026-04-20: Recovery from the interrupted migration exposed two separate usability gaps worth preserving for the next simplification lane: package-layer navigation is still too opaque during maintainer work, and issue-orientation still costs too much after a crash or context reset.
- 2026-04-20: Reopened the lane again after checking the live issue body and finding that the planning-view move satisfied only the narrow planning-state part of `#231`, not the full ownership-boundary intent.
- 2026-04-20: Removed the installed compatibility queue views entirely; summary/checker fall back to `.agentic-workspace/planning/state.toml` directly, while legacy root views remain migration-only inputs for cleanup and archive compatibility.
