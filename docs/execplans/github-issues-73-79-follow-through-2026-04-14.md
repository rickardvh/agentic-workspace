# GitHub Issues 73-79 Follow-Through

## Goal

- Ingest the remaining open GitHub issues into one current checked-in owner and implement them in bounded priority order until the live open queue is exhausted or explicitly rerouted.

## Non-Goals

- Do not keep stale completed issue tranches active in `TODO.md` or `ROADMAP.md`.
- Do not widen bounded issue slices into a generic planning-system rewrite unless the promoted issue explicitly requires it.
- Do not treat issue closure as sufficient without matching checked-in planning cleanup, validation, and dogfooding when the feature affects normal repo work.

## Intent Continuity

- Larger intended outcome: finish the remaining open GitHub issue queue while keeping the checked-in planning system authoritative and continuation-safe for smaller models.
- This slice completes the larger intended outcome: no
- Continuation surface: TODO.md

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: TODO.md
- Activation trigger: when the current issue tranche or current milestone completes and the next remaining open issue is ready to implement

## Delegated Judgment

- Requested outcome: ingest and prioritize the remaining open GitHub issues, implement them in bounded tranches with commits, dogfood improvements in normal repo work, and route follow-on signals back into checked-in planning.
- Hard constraints: keep issue execution aligned with live `gh` state, preserve one current owner in checked-in planning, keep repo/package boundaries explicit, and prefer the narrowest proving lane that closes each touched contract.
- Agent may decide locally: issue grouping, milestone boundaries, validation scope, whether an issue is already effectively implemented and only needs closure/planning cleanup, and whether multiple small contract/reporting slices belong in one commit.
- Escalate when: the smallest safe implementation would silently change the requested outcome, collapse planning/package ownership boundaries, or force a much broader workflow redesign than the promoted issue actually asks for.

## Active Milestone

- Status: in-progress
- Scope: reconcile the live `#73`-`#79` queue into checked-in planning, close already-landed `#76`, then implement the remaining bounded contract and reliability slices before the larger planning-state work.
- Ready: ready
- Blocked: none
- optional_deps: explorer read-only analysis may run in parallel

## Immediate Next Action

- Tighten the machine-readable state-retrieval contract so agents can query planning state through explicit schemas instead of broad Markdown parsing.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- docs/execplans/
- src/agentic_workspace/
- tests/test_workspace_cli.py
- packages/planning/
- packages/memory/

## Invariants

- Live GitHub issue state stays upstream-authoritative; checked-in planning must be reconciled against `gh` before implementation claims or closure claims.
- `TODO.md` stays a thin active queue, and `ROADMAP.md` stays a thin inactive candidate queue.
- Completed issue detail belongs in archived execplans and issue comments, not in forward-looking planning surfaces.
- Smaller-model continuation safety should improve, not regress, as a result of any planning-state change.

## Contract Decisions To Freeze

- The current active issue tranche should live behind one checked-in execplan owner rather than several stale top-level plan files.
- Already-landed contract slices should be closed or archived promptly instead of lingering as active queue state.
- The planning rewrite work from `#78` and `#79` should follow the smaller contract/reliability slices, not preempt them.

## Open Questions To Close

- Which open issues are already effectively implemented and only need closure plus planning cleanup?
- What is the smallest canonical compact planning record that can make `TODO.md` and `ROADMAP.md` thin views without widening the planning package too far?
- Which completion-discipline checks are cheap enough to run on every bounded slice without turning routine work into ceremony?

## Validation Commands

- `uv run pytest tests/test_workspace_cli.py -q`
- `cd packages/planning && uv run pytest tests/test_installer.py -q`
- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run python scripts/check/check_source_payload_operational_install.py`
- `uv run agentic-planning-bootstrap summary --format json`
- `uv run agentic-workspace config --target . --format json`

## Completion Criteria

- The live open GitHub issue set has been re-ingested into checked-in planning.
- Each completed bounded slice has its own commit and matching issue-state update.
- Any remaining unfinished work is explicitly owned by `TODO.md`, `ROADMAP.md`, or a narrower promoted execplan rather than left in stale issue or plan residue.

## Execution Summary

- Outcome delivered: pending
- Validation confirmed: pending
- Follow-on routed to: TODO.md
- Resume from: validate issue `#76`, then continue through the remaining live issue queue

## Drift Log

- 2026-04-14: Replaced the stale `#69`-`#72` active issue tranche with the live `#73`-`#79` queue after confirming upstream closure drift.
- 2026-04-14: Closed `#76` after validating the shipped safety contract and cleaned up stale active-plan residue; closed `#75` after adding the explicit `--non-interactive` lifecycle posture and prompt-safe handoff guidance.
- 2026-04-14: Closed `#77` after adding advisory `Required Tools` support to the compact planning contract and refreshing the installed planning payload in this repo.
