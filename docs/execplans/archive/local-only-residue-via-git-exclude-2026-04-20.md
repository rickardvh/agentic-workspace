# Local-Only Residue Via Git Exclude

## Goal

- Consolidate local-only package-owned state into one explicit package-owned file inside the package install tree, while keeping repo-side residue unobtrusive.

## Encoded Intent

- Issue intent: consolidate this package's data into one clear, unobtrusive package-owned home, leaving repo-owned surfaces only where they are genuinely repo-owned.
- Implementation intent: make local-only state explicit inside the package-owned home and treat residue cleanup as a downstream proof of that boundary.

## Non-Goals

- Change the broader package/repo ownership model.
- Remove the root startup hook or the ownership boundary review.
- Introduce a new storage backend.
- Rewrite installer architecture outside the residue path.
- Declare the lane complete before the package-owned home is unambiguous.

## Intent Continuity

- Larger intended outcome: Cleaner package/repo separation with one unambiguous package-owned home and lower install/uninstall residue.
- This slice completes the larger intended outcome: yes
- Continuation surface: none
- Parent lane: ownership-boundary-and-local-only-mode

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: n/a

## Iterative Follow-Through

- What this slice should enable: local-only install and uninstall should leave no tracked repo-root residue, using git-local metadata and an explicit package-owned state file inside the package install tree.
- Intentionally deferred: any broader repo-root startup simplification beyond the package-owned boundary.
- Discovered implications: the repo-owned startup hook should remain small while the package-owned home carries the local-only state explicitly.
- Proof needed now: package-owned data can be consolidated without forcing the repo to absorb it into tracked root surfaces.
- Validation still needed: dogfood the boundary on a real repo clone with existing legacy residue and confirm the repo-owned surfaces stay minimal.
- Next likely slice: inspect whether any remaining package-owned state still leaks into repo-root surfaces and move it into the package-owned home.

## Delegated Judgment

- Requested outcome: issue `#231` and the ownership-boundary lane it represents.
- Hard constraints: preserve repo-owned contracts, keep local-only compatible, and avoid broad installer rewrites.
- Agent may decide locally: the exact git-local metadata path, the minimal block format, and the cleanup order.
- Escalate when: the ignore residue cannot be moved without breaking local-only install or uninstall symmetry.

## Active Milestone

- Status: complete
- Scope: Move package-owned state into one clear package-owned home and keep only a minimal repo-owned hook.
- Ready: ready
- Blocked: no
- optional_deps: none

## Immediate Next Action

- None.

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
- Package-owned state should consolidate into one unambiguous package-owned home before the lane can be called complete.
- The local-only state file should remain inside the package-owned install tree, not in repo-root metadata.

## Validation Commands

- uv run pytest tests/test_workspace_cli.py -q -k "local_only or selection_commands_accept_non_interactive_flag"
- uv run python scripts/check/check_planning_surfaces.py
- uv run agentic-planning-bootstrap upgrade --target .
- uv run agentic-memory-bootstrap upgrade --target .

## Completion Criteria

- Package-owned state has a single clear home inside the package-owned domain.
- Repo-owned surfaces remain only where they are genuinely repo-owned and the repo hook is minimal.
- Local-only install/uninstall continue to work as consequences of that boundary, not as the only proof of completion.

## Execution Summary

- Outcome delivered: local-only install now records explicit package-owned state in `.gemini/agentic-workspace/LOCAL-ONLY.toml`, uses `.git/info/exclude` instead of tracked repo-root `.gitignore`, and uninstall removes the package-owned marker plus git-local residue while cleaning up legacy `.gitignore` blocks if they exist.
- Validation confirmed: `uv run pytest tests/test_workspace_cli.py -q -k "local_only or selection_commands_accept_non_interactive_flag or ownership_command_reports_authority_map"`; `uv run pytest tests/test_workspace_cli.py -q`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-planning-bootstrap upgrade --target .`; `uv run agentic-memory-bootstrap upgrade --target .`.
- Follow-on routed to: none.
- Knowledge promoted (Memory/Docs/Config): docs/installer-behavior.md, packages/planning/bootstrap/docs/installer-behavior.md
- Resume from: archived.

## Drift Log

- 2026-04-20: Reopened issue `#231` after the lane was only partially completed and restored the active planning surfaces.
