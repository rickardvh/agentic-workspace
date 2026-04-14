# Structured Bootstrap Handoff Artifact

## Goal

- Add a compact structured sibling artifact for bootstrap handoff so cheaper or weaker follow-on agents can recover intent, proof, and escalation boundaries without mining prose first.
- Use the same artifact to carry delegated-judgment boundaries in checked-in form during bootstrap follow-through.

## Non-Goals

- Replace `llms.txt` or `.agentic-workspace/bootstrap-handoff.md`.
- Build a generic task handoff system for all lifecycle commands.
- Turn the artifact into a second execplan or a long narrative log.

## Intent Continuity

- Larger intended outcome: complete the remaining compact-handoff and delegated-judgment practical-follow-through work with a bounded bootstrap-focused contract improvement.
- This slice completes the larger intended outcome: yes
- Continuation surface: `none`

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: `none`
- Activation trigger: `none`

## Delegated Judgment

- Requested outcome: ship one structured bootstrap handoff sibling artifact with explicit intent, scope, next step, proof, must-not-change boundaries, escalation triggers, and refs; align docs/tests and dogfood it.
- Hard constraints: keep `llms.txt` and the prose bootstrap brief canonical for human-readable startup; keep the new artifact small; avoid a generic query language or a second planning system; keep repo semantics authoritative.
- Agent may decide locally: the exact JSON shape, the canonical artifact path, and the smallest doc/reporting updates needed to keep the artifact trustworthy.
- Escalate when: the slice would require a general handoff framework, broader lifecycle redesign, or replacement of the prose surfaces instead of a bounded bootstrap sibling artifact.

## Active Milestone

- ID: structured-bootstrap-handoff-artifact
- Status: completed
- Scope: add a structured bootstrap handoff artifact, expose it through the existing bootstrap/reporting contract, and validate it through focused CLI tests plus live repo dogfooding.
- Ready: ready
- Blocked: none
- optional_deps: GitHub issues `#31` and `#25`

## Immediate Next Action

- None. Slice completed; promote the next remaining GitHub issue tranche.

## Blockers

- None.

## Touched Paths

- `TODO.md`
- `ROADMAP.md`
- `docs/execplans/structured-bootstrap-handoff-artifact-2026-04-14.md`
- `docs/init-lifecycle.md`
- `docs/environment-recovery-contract.md`
- `docs/default-path-contract.md`
- `src/agentic_workspace/cli.py`
- `tests/test_workspace_cli.py`

## Invariants

- The structured artifact must stay smaller than the prose brief.
- Human-readable startup and bootstrap guidance remains available.
- The artifact must preserve delegated-judgment boundaries instead of hiding them in prose.
- The new surface should reduce rereading, not create another mandatory dashboard.

## Contract Decisions To Freeze

- The first structured handoff artifact belongs to bootstrap state, not every lifecycle command.
- The artifact should be a sibling to the prose bootstrap brief, not a replacement for it.
- Required fields should match the bounded strong-planner / cheap-implementer handoff contract: intent, scope, next, proof, must_not_change, escalate_when, refs.

## Open Questions To Close

- What is the smallest bootstrap-focused record shape that still preserves delegated-judgment boundaries cheaply?
- Should the artifact be written only when bootstrap already writes the prose handoff brief, or also be exposed during dry-run prompt generation?
- Which existing machine-readable defaults or recovery surfaces should name the new artifact explicitly?

## Validation Commands

- `uv run pytest tests/test_workspace_cli.py -q`
- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run ruff check src tests`

## Completion Criteria

- Bootstrap writes a compact structured sibling artifact when a checked-in finishing handoff is required or recommended.
- The artifact carries the bounded delegated-judgment fields needed by a follow-on implementer.
- Docs and focused CLI tests align to the same path and field vocabulary.
- The new artifact is dogfooded in this repo through the existing bootstrap/reporting surfaces.

## Execution Summary

- Outcome delivered: bootstrap now emits a compact structured sibling handoff artifact at `.agentic-workspace/bootstrap-handoff.json` whenever bootstrap already carries a checked-in finishing brief; the record preserves intent, scope, next steps, proof, must-not-change boundaries, escalation triggers, and refs, and the lifecycle/default-path docs and CLI tests now point to the same contract.
- Validation confirmed: `uv run pytest tests/test_workspace_cli.py -q`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run ruff check src tests`; `uv run agentic-workspace prompt init --target . --format json`; `uv run agentic-workspace defaults --section recovery --format json`.
- Follow-on routed to: `ROADMAP.md`.
- Resume from: promote the next open issue, most likely external-agent handoff polish or conservative automatic policy selection follow-through.

## Drift Log

- 2026-04-14: Promoted after the lazy-discovery selector tranche landed cleanly and the next clearest product gap remained compact structured bootstrap handoff with explicit delegated-judgment boundaries.
- 2026-04-14: Completed by shipping the structured bootstrap handoff sibling artifact, aligning the docs/tests around the new path, and dogfooding the new record against this repo's live high-ambiguity bootstrap state.
