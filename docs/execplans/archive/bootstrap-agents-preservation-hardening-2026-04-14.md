# Bootstrap AGENTS Preservation Hardening

## Goal

- Fix the workspace upgrade path so it keeps repo-owned `AGENTS.md` content outside the managed workspace fence instead of rewriting the whole file.
- Re-prove the remaining bootstrap-hardening contract after that fix and close the bootstrap issue if no narrower remainder survives.

## Non-Goals

- Redesign the whole bootstrap classifier.
- Replace the current external-agent handoff surface.
- Introduce broader startup-filename configurability in this slice.

## Intent Continuity

- Larger intended outcome: finish the remaining bootstrap-hardening follow-through around external-agent trust, conservative policy, and repo-owned surface preservation.
- This slice completes the larger intended outcome: yes
- Continuation surface: `none`

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: `none`
- Activation trigger: `none`

## Delegated Judgment

- Requested outcome: correct the upgrade behavior so repo-owned `AGENTS.md` content survives outside the managed workspace fence, add focused regression coverage, and reassess whether issue `#27` can close.
- Hard constraints: preserve the managed workspace pointer block; do not normalize the whole file on upgrade; keep install behavior for blank repos intact; keep the slice bounded to bootstrap hardening rather than startup-filename expansion.
- Agent may decide locally: the smallest upgrade-path rule change, the exact regression tests, and the minimum docs/planning updates needed if the bootstrap issue closes.
- Escalate when: fixing the preservation bug would require a broader ownership redesign, breaks install/adopt semantics, or exposes another bootstrap-hardening remainder that needs separate promotion.

## Active Milestone

- ID: bootstrap-agents-preservation-hardening
- Status: completed
- Scope: fix upgrade-time `AGENTS.md` preservation, prove the current bootstrap contract with focused tests and live dogfooding, and close issue `#27` if the remaining scope is satisfied.
- Ready: ready
- Blocked: none
- optional_deps: GitHub issue `#27`

## Immediate Next Action

- None. Slice completed; promote the next remaining open issue.

## Blockers

- None.

## Touched Paths

- `TODO.md`
- `ROADMAP.md`
- `docs/execplans/bootstrap-agents-preservation-hardening-2026-04-14.md`
- `src/agentic_workspace/cli.py`
- `tests/test_workspace_cli.py`

## Invariants

- `AGENTS.md` remains repo-owned outside the managed workspace fence.
- The workspace pointer block stays current.
- Upgrade should still keep `llms.txt` current.
- Blank-repo install behavior should remain unchanged.

## Contract Decisions To Freeze

- Upgrade should preserve repo-owned startup instructions outside the managed workspace fence when `AGENTS.md` already exists.
- The workspace layer owns the fenced pointer block, not the whole root startup file.

## Open Questions To Close

- Is there any remaining bootstrap-hardening gap after the AGENTS preservation fix and the recent structured handoff work?

## Validation Commands

- `uv run pytest tests/test_workspace_cli.py -q`
- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run ruff check src tests`

## Completion Criteria

- Workspace upgrade no longer rewrites repo-owned `AGENTS.md` content outside the managed fence.
- Focused regression coverage proves the preserved-content behavior.
- Live bootstrap/handoff dogfooding shows no narrower remainder in issue `#27`, or routes one explicitly if it remains.

## Execution Summary

- Outcome delivered: workspace upgrade now preserves repo-owned `AGENTS.md` content outside the managed workspace fence instead of rewriting the whole file, while still keeping the workspace pointer current; focused regression coverage proves the preserved-content behavior, and live dry-run bootstrap/upgrade dogfooding shows the external-agent and policy-selection surfaces remain consistent.
- Validation confirmed: `uv run pytest tests/test_workspace_cli.py -q`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run ruff check src tests`; `uv run agentic-workspace upgrade --target . --dry-run --format json`.
- Follow-on routed to: `ROADMAP.md`.
- Resume from: promote the next remaining issue, likely lazy-discovery measurement or configurable canonical startup filename support.

## Drift Log

- 2026-04-14: Promoted after identifying a concrete remaining bootstrap-hardening bug: `upgrade` still rewrote the whole root `AGENTS.md` instead of preserving repo-owned content outside the managed workspace fence.
- 2026-04-14: Completed by changing upgrade to patch the managed workspace fence inside `AGENTS.md`, proving repo-owned content survives through regression coverage, and confirming the live bootstrap/handoff reports stay conservative and target-repo-specific.
