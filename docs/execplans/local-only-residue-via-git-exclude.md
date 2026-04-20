# Local-Only Residue Via Git Exclude

## Goal

- Reduce local-only install residue further by moving ignore management out of the tracked repo root and into git-local metadata.

## Non-Goals

- Change the broader package/repo ownership model.
- Remove the root startup hook or the ownership boundary review.
- Introduce a new storage backend.
- Rewrite installer architecture outside the residue path.

## Intent Continuity

- Larger intended outcome: Cleaner package/repo separation with lower install and uninstall residue.
- This slice completes the larger intended outcome: no
- Continuation surface: docs/execplans/local-only-residue-via-git-exclude.md
- Parent lane: ownership-boundary-and-local-only-mode

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: docs/execplans/local-only-residue-via-git-exclude.md
- Activation trigger: completion of the local-only uninstall cleanup slice and validation that the repo-root `.gitignore` residue can be eliminated

## Iterative Follow-Through

- What this slice should enable: local-only install and uninstall should leave no tracked repo-root residue, using `.git/info/exclude` instead of `.gitignore`.
- Intentionally deferred: any broader repo-root startup simplification beyond local-only residue.
- Discovered implications: this next slice should preserve the repo-owned startup hook while removing an avoidable tracked-side effect.
- Proof needed now: the local-only path remains symmetric and the repo root stays clean after install/uninstall.
- Validation still needed: dogfood the exclude path on a real repo clone with existing legacy `.gitignore` residue.
- Next likely slice: once the untracked-exclude path works, inspect whether any remaining repo hook can be narrowed further without changing startup semantics.

## Delegated Judgment

- Requested outcome: issue `#231` and the ownership-boundary lane it represents.
- Hard constraints: preserve repo-owned contracts, keep local-only compatible, and avoid broad installer rewrites.
- Agent may decide locally: the exact git-local metadata path, the minimal block format, and the cleanup order.
- Escalate when: the ignore residue cannot be moved without breaking local-only install or uninstall symmetry.

## Active Milestone

- Status: in-progress
- Scope: Move local-only residue management from tracked repo-root `.gitignore` into git-local exclude metadata.
- Ready: ready
- Blocked: no
- optional_deps: none

## Immediate Next Action

- Implement the git-exclude-based local-only residue path and keep uninstall symmetric.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- docs/execplans/local-only-residue-via-git-exclude.md

## Invariants

- Local-only install and uninstall must remain symmetric.
- The repo-root should not accumulate tracked residue purely for local-only workspace storage.
- The ownership boundary review remains available and unchanged unless the next slice explicitly needs it.

## Validation Commands

- uv run pytest tests/test_workspace_cli.py -q -k "local_only or selection_commands_accept_non_interactive_flag"
- uv run python scripts/check/check_planning_surfaces.py
- uv run agentic-planning-bootstrap upgrade --target .
- uv run agentic-memory-bootstrap upgrade --target .

## Completion Criteria

- Local-only install uses git-local exclude metadata instead of tracked repo-root ignore edits.
- Local-only uninstall removes the git-local residue it created.
- The repo root stays clean after the local-only install/uninstall cycle.

## Execution Summary

- Outcome delivered: local-only install now uses `.git/info/exclude` instead of tracked repo-root `.gitignore`, and uninstall removes that git-local residue while cleaning up legacy `.gitignore` blocks if they exist.
- Validation confirmed: `uv run pytest tests/test_workspace_cli.py -q -k "local_only or selection_commands_accept_non_interactive_flag or ownership_command_reports_authority_map"`; `uv run pytest tests/test_workspace_cli.py -q`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-planning-bootstrap upgrade --target .`; `uv run agentic-memory-bootstrap upgrade --target .`.
- Follow-on routed to: continue the ownership-boundary lane from the git-local residue path.
- Knowledge promoted (Memory/Docs/Config): docs/installer-behavior.md, packages/planning/bootstrap/docs/installer-behavior.md
- Resume from: the git-local residue path.

## Drift Log

- 2026-04-20: Reopened issue `#231` after the lane was only partially completed and restored the active planning surfaces.
