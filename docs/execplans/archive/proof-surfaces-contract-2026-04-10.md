# Proof Surfaces Contract

## Goal

- Make the repo's proof and trust-calibration surfaces queryable enough that agents do not have to infer the right check lane from scattered docs.

## Non-Goals

- Build a monitoring system.
- Replace existing package-local checks.
- Widen this slice into ownership mapping.

## Intent Continuity

- Larger intended outcome: Strengthen checks / proof surfaces so repo contract health is easier to prove than to guess.
- This slice completes the larger intended outcome: no
- Continuation surface: `TODO.md` follow-on slice `ownership-authority-mapping-contract`

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: `TODO.md`
- Activation trigger: The proof-surfaces contract lands and the next bounded slice can focus on ownership and authority mapping without reworking the proof surface again.

## Delegated Judgment

- Requested outcome: Add one compact proof-surfaces contract plus a machine-readable workspace proof command that exposes the normal proof routes and current health summary.
- Hard constraints: Keep the workspace layer thin; report existing proof surfaces rather than inventing new module logic or broad monitoring state.
- Agent may decide locally: Add the canonical doc, workspace command, defaults references, and narrow tests needed to make the proof surface queryable and trustworthy.
- Escalate when: The cleaner fix would require redesigning package-local check ownership or collapsing proof and ownership into one oversized contract.

## Active Milestone

- Status: completed
- Scope: define the proof-surfaces contract, add `agentic-workspace proof`, update front-door guidance, and validate the workspace CLI plus maintainer lanes.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Implement the canonical proof doc and the workspace CLI proof command, then lock the output shape with workspace CLI tests.

## Blockers

- None.

## Touched Paths

- `TODO.md`
- `docs/`
- `src/agentic_workspace/cli.py`
- `tests/test_workspace_cli.py`

## Invariants

- Keep proof surfaces queryable and compact.
- Reuse existing check and doctor lanes instead of inventing shadow proof state.
- Preserve package-local ownership of package-local validation.

## Contract Decisions To Freeze

- `agentic-workspace proof` should answer “what proves the contract here?” in one place.
- The proof surface should expose both proof routes and the current workspace health summary.
- Proof surfaces stay advisory and queryable; they do not become a new source of truth over the underlying checks.

## Open Questions To Close

- No blocking open questions remain for this slice.

## Validation Commands

- `uv run pytest tests/test_workspace_cli.py`
- `uv run python scripts/check/check_planning_surfaces.py`
- `make maintainer-surfaces`
- `uv run agentic-planning-bootstrap upgrade --target .`

## Completion Criteria

- One canonical doc defines the proof-surfaces contract.
- `agentic-workspace proof --target ./repo --format json` returns the proof routes and current health summary.
- Front-door docs reference the proof surface instead of only implying it.

## Execution Summary

- Outcome delivered: Added the canonical proof-surfaces contract, shipped `agentic-workspace proof`, and aligned front-door routing docs around the same proof surface.
- Validation confirmed: `uv run pytest tests/test_workspace_cli.py`; `uv run python scripts/check/check_planning_surfaces.py`; `make maintainer-surfaces`
- Follow-on routed to: `TODO.md` follow-on slice `ownership-authority-mapping-contract`
- Resume from: promote the ownership and authority mapping slice

## Drift Log

- 2026-04-10: Promoted from explicit maintainer direction after the capability ranking put checks / proof surfaces next.
