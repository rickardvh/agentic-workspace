# Ownership Boundary And Low-Residue Installs

## Goal

- Separate package-owned state cleanly from repo-owned surfaces so install and uninstall become low-residue operations even for local-only mode.

## Non-Goals

- Delete all repo-facing surfaces.
- Pretend every current repo surface is a package mistake.
- Commit to remote or shared storage as near-term roadmap work.
- Rewrite the installer architecture in one pass.

## Intent Continuity

- Larger intended outcome: Cleaner package/repo separation with lower install and uninstall residue.
- This slice completes the larger intended outcome: yes
- Continuation surface: none
- Parent lane: ownership-boundary-and-local-only-mode

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Iterative Follow-Through

- What this slice enabled: a concrete ownership review surface plus a local-only uninstall path that removes the `.gemini/agentic-workspace/` install tree and its ignore residue.
- Intentionally deferred: broader installer architecture changes and any storage-backend redesign.
- Discovered implications: the boundary review needs to stay explicit enough that future storage backends can move without changing ownership semantics.
- Proof achieved now: the ownership command returns a current surface inventory and points to the smallest explicit repo hook.
- Validation still needed: none for this lane.
- Next likely slice: none.

## Delegated Judgment

- Requested outcome: issue `#231` and the ownership-boundary lane it represents.
- Hard constraints: preserve repo-owned contracts, keep local-only compatible, and avoid broad installer rewrites.
- Agent may decide locally: the initial surface taxonomy, the smallest stable repo hook, and the exact presentation order for the boundary review.
- Escalate when: the boundary cannot be expressed without breaking current repo-owned contracts.

## Active Milestone

- Status: completed
- Scope: Classify package-owned, repo-owned, and ambiguous middle-ground surfaces; clean up local-only residue.
- Ready: no
- Blocked: no
- optional_deps: none

## Immediate Next Action

- No further action required for this execplan slice.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- docs/execplans/archive/ownership-boundary-and-low-residue-installs-2026-04-20.md

## Invariants

- Local-only install and uninstall must remain compatible with repo-owned startup surfaces.
- Package-owned state should be identified before any implementation changes widen the boundary.
- The first slice must stay bounded to classification and repo-hook review.
- Local-only uninstall must remove the whole `.gemini/agentic-workspace/` install tree when the repo owns no additional local-only residue.

## Validation Commands

- uv run python scripts/check/check_planning_surfaces.py
- uv run pytest tests/test_workspace_cli.py -q -k "local_only or ownership_command_reports_authority_map"
- uv run agentic-planning-bootstrap upgrade --target .
- uv run agentic-memory-bootstrap upgrade --target .

## Completion Criteria

- The current surface set is classified into package-owned, repo-owned, and ambiguous middle-ground groups.
- The minimum explicit repo hook is identified and justified.
- The boundary review and local-only uninstall cleanup are ready for implementation follow-through without widening the lane.

## Execution Summary

- Outcome delivered: added a queryable ownership boundary review to `agentic-workspace ownership` and a local-only uninstall path that removes the `.gemini/agentic-workspace/` tree plus local-only ignore residue.
- Validation confirmed: `uv run pytest tests/test_workspace_cli.py -q`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-planning-bootstrap upgrade --target .`; `uv run agentic-memory-bootstrap upgrade --target .`.
- Follow-on routed to: none.
- Knowledge promoted (Memory/Docs/Config): docs/ownership-authority-contract.md, docs/agent-installation.md, docs/memory-metadata-contract.md, docs/installer-behavior.md, docs/routing-contract.md
- Resume from: none.

## Drift Log

- 2026-04-20: Promoted issue `#231` into active planning as the ownership-boundary and low-residue installs lane.
