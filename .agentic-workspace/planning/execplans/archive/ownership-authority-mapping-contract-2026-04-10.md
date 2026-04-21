# Ownership And Authority Mapping Contract

## Goal

- Make the repo's ownership and authority boundaries queryable enough that agents do not have to infer who owns a concern or which checked-in surface is authoritative.

## Non-Goals

- Redesign module boundaries.
- Merge ownership and proof into one broader contract.
- Turn the ownership ledger into a policy engine.

## Intent Continuity

- Larger intended outcome: Strengthen ownership / authority mapping so agents can resolve the right owner and source of truth cheaply.
- This slice completes the larger intended outcome: yes
- Continuation surface: none

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Delegated Judgment

- Requested outcome: Add one compact ownership contract, expose it through a workspace command, and align the shipped ownership ledger around the same authority map.
- Hard constraints: Keep one clear owner per concern, preserve package boundaries, and keep the workspace layer queryable instead of becoming the owner of everything.
- Agent may decide locally: Add the canonical doc, workspace command, ledger fields, and narrow tests needed to make ownership/authority questions answerable directly.
- Escalate when: The cleaner fix would require changing module boundaries, redefining repo-owned memory/planning authority, or collapsing multiple ownership concerns into a new top-level subsystem.

## Active Milestone

- Status: completed
- Scope: define the ownership/authority contract, add `agentic-workspace ownership`, align the shipped ownership ledger, and validate the CLI plus source/payload/root-install boundary.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Add the canonical doc and the machine-readable workspace command, then align the source/payload/root-install ownership ledger copies and lock the output shape with tests.

## Blockers

- None.

## Touched Paths

- `TODO.md`
- `docs/`
- `src/agentic_workspace/cli.py`
- `tests/test_workspace_cli.py`
- `.agentic-workspace/OWNERSHIP.toml`
- `packages/planning/src/repo_planning_bootstrap/_ownership.toml`
- `packages/memory/src/repo_memory_bootstrap/_ownership.toml`

## Invariants

- Keep one primary owner per concern.
- Preserve the ownership ledger as a compact contract, not a workflow backlog.
- Keep package-local ownership package-local and repo-owned authority repo-owned.

## Contract Decisions To Freeze

- `agentic-workspace ownership` should answer "who owns this concern and which surface is authoritative?" in one place.
- The ownership ledger should expose the main authority surfaces directly enough that CLI consumers do not need to reverse-engineer them from prose.
- Ownership mapping stays descriptive and queryable; it does not become a mutation or policy engine.

## Open Questions To Close

- No blocking open questions remain for this slice.

## Validation Commands

- `uv run pytest tests/test_workspace_cli.py`
- `uv run python scripts/check/check_planning_surfaces.py`
- `make maintainer-surfaces`
- `uv run agentic-planning-bootstrap upgrade --target .`
- `uv run agentic-memory-bootstrap upgrade --target .`

## Completion Criteria

- One canonical doc defines the ownership/authority contract.
- `agentic-workspace ownership --target ./repo --format json` returns the authority map and ownership ledger summary directly.
- Source, payload, and root-install ownership ledger copies stay aligned.

## Execution Summary

- Outcome delivered: Added the canonical ownership/authority contract, shipped `agentic-workspace ownership`, and aligned the source, payload, and root-install ownership ledger copies around the same authority map.
- Validation confirmed: `uv run pytest tests/test_workspace_cli.py`; `uv run python scripts/check/check_planning_surfaces.py`; `make maintainer-surfaces`; `uv run agentic-planning-bootstrap upgrade --target .`; `uv run agentic-memory-bootstrap upgrade --target .`
- Follow-on routed to: none
- Resume from: no follow-on required for this capability

## Drift Log

- 2026-04-10: Promoted immediately after proof surfaces landed because the next capability tranche still left authority resolution too implicit.
