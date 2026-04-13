# Validation Defaults Refinement

## Goal

- Strengthen the machine-readable validation contract so lower-capability agents can tell what proof is enough, when broader checks are required, and when they should escalate without mining maintainer prose first.
- Keep the first refinement inside existing default-route surfaces rather than introducing a new command or workflow layer.

## Non-Goals

- Replace the contributor playbook or maintainer commands as the canonical prose guidance for humans.
- Build a fully automatic touched-path-to-validation router in this slice.
- Add repo-wide mandatory validation that broadens simple work.
- Reopen package-specific validation semantics that still belong to the packages.

## Intent Continuity

- Larger intended outcome: make validation choice as queryable and cheap as startup, module discovery, and skill discovery so weaker agents can prove bounded work safely with less interpretation burden.
- This slice completes the larger intended outcome: no
- Continuation surface: `TODO.md`

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: `TODO.md`
- Activation trigger: the structured default-route validation lane lands and later work is ready to add more granular recommendation or behavior if needed.

## Delegated Judgment

- Requested outcome: add a stronger machine-readable validation lane contract to the existing workspace defaults surface and align the docs/tests around it.
- Hard constraints: keep the first pass narrow; preserve package-local ownership of package-local validation; do not create a broader required lane for simple work; keep the output clear enough for weaker agents to use directly.
- Agent may decide locally: the exact JSON shape, the smallest set of lane categories, and the minimum doc updates that make the surface trustworthy.
- Escalate when: the slice would require a new command, path-sensitive inference engine, or broader workflow redesign instead of a bounded default-route refinement.

## Active Milestone

- ID: validation-defaults-refinement
- Status: completed
- Scope: enrich `agentic-workspace defaults` with structured validation lane guidance and update the front-door docs/tests to match.
- Ready: ready
- Blocked: none
- optional_deps: GitHub issue `#26`

## Immediate Next Action

- None. Slice completed; reopen validation follow-through only if the richer defaults surface still leaves repeated proof-lane ambiguity in ordinary use.

## Blockers

- None.

## Touched Paths

- `TODO.md`
- `ROADMAP.md`
- `docs/execplans/validation-defaults-refinement-2026-04-13.md`
- `docs/default-path-contract.md`
- `docs/contributor-playbook.md`
- `src/agentic_workspace/cli.py`
- `tests/test_workspace_cli.py`

## Invariants

- The narrowest proving lane remains the default.
- Package-local validation stays package-owned.
- Simple work must stay cheaper than broader checks.
- Machine-readable guidance should reduce prose dependence.
- Escalation criteria must stay explicit.

## Contract Decisions To Freeze

- The first machine-readable refinement should live in `agentic-workspace defaults --format json`, not a separate command.
- Validation reporting should answer three questions explicitly: what lane fits, what proof is enough, and when broader checks or escalation are required.
- Lane definitions should stay category-shaped and stable instead of overfitting to one repo path heuristic.
- Package-local tests remain package-owned even when the workspace defaults surface reports the route.

## Open Questions To Close

- What is the smallest lane schema that still answers "enough proof", "broaden when", and "escalate when" directly?
- Which current prose guidance should remain prose-only, and which parts now belong in the machine-readable defaults surface?
- How much of the contributor playbook should be tightened once the defaults surface becomes clearer?

## Validation Commands

- `uv run pytest tests/test_workspace_cli.py -q`
- `uv run python scripts/check/check_planning_surfaces.py`

## Completion Criteria

- `agentic-workspace defaults --format json` exposes richer structured validation guidance than the current flat route map.
- The default-path or contributor docs point to the stronger machine-readable validation surface without drift.
- The focused workspace CLI tests prove the new shape.

## Execution Summary

- Outcome delivered: `agentic-workspace defaults` now exposes structured validation lanes with enough-proof, broaden-when, and escalate-when guidance; the default-path and contributor docs now point to that machine-readable surface explicitly.
- Validation confirmed: `uv run pytest tests/test_workspace_cli.py -q`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run ruff check src tests`.
- Follow-on routed to: `ROADMAP.md`.
- Resume from: dogfood the richer validation defaults in ordinary work and reopen only if agents still have to infer the proof lane mainly from prose.

## Drift Log

- 2026-04-13: Promoted from the highest-priority roadmap queue after the mixed-agent reporting/local-override slices completed cleanly and the validation-default gap remained the clearest next efficiency refinement.
- 2026-04-13: Completed by shipping richer validation lane metadata in the defaults payload, aligning the front-door docs, and proving the new shape with focused workspace CLI coverage.
