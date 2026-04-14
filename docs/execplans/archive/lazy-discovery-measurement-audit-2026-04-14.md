# Lazy Discovery Measurement Audit

## Goal

- Add the first small measurement framework for lazy-discovery cost so compact contract work can be justified by less reading, not only cleaner structure.
- Use it in one bounded audit of the current defaults/proof/ownership selector path in this repo.

## Non-Goals

- Add telemetry or runtime monitoring.
- Claim exact model-token accounting.
- Broaden the slice into generic analytics.

## Intent Continuity

- Larger intended outcome: close the remaining lazy-discovery measurement issue and leave a reusable proof bar for future compact-contract work.
- This slice completes the larger intended outcome: yes
- Continuation surface: none

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Delegated Judgment

- Requested outcome: add a small checked-in measurement script plus one audit artifact showing how much the current selector path reduces retrieval size for common one-answer questions.
- Hard constraints: keep the framework cheap and reproducible; use explicit approximations rather than pretending to know model-exact tokens; stay focused on defaults/proof/ownership selector work.
- Agent may decide locally: the exact proxy metrics, the audit format, and the smallest reusable script shape that keeps future compactness work measurable.
- Escalate when: the slice would require invasive instrumentation, runtime logging, or provider-specific token accounting.

## Active Milestone

- ID: lazy-discovery-measurement-audit
- Status: completed
- Scope: ship one measurement script and one audit artifact for the current selector path, then close issue `#32`.
- Ready: ready
- Blocked: none
- optional_deps: GitHub issue `#32`

## Immediate Next Action

- None. Slice completed; promote the final remaining open issue.

## Blockers

- None.

## Touched Paths

- `TODO.md`
- `ROADMAP.md`
- `docs/execplans/lazy-discovery-measurement-audit-2026-04-14.md`
- `docs/lazy-discovery-measurements.md`
- `docs/reviews/lazy-discovery-measurement-audit-2026-04-14.md`
- `scripts/check/measure_lazy_discovery.py`

## Invariants

- The framework should stay cheap enough to run routinely.
- Measurements should compare one-answer retrieval against the corresponding full-surface dump.
- Report approximations clearly instead of implying exact token truth.

## Contract Decisions To Freeze

- Byte length and a simple character-based token approximation are acceptable first-pass proxies.
- The first audit should focus on current selector-enabled defaults, proof, and ownership questions.

## Open Questions To Close

- What is the smallest useful proxy set for measuring lazy discovery?
- Which one-answer queries best represent the current compact-contract value?

## Validation Commands

- `uv run python scripts/check/measure_lazy_discovery.py --target .`
- `uv run python scripts/check/check_planning_surfaces.py`

## Completion Criteria

- A checked-in script can measure full-vs-narrow retrieval for at least the current defaults/proof/ownership selector path.
- One audit artifact records the measured reductions in this repo.
- Issue `#32` can close on the resulting proof.

## Execution Summary

- Outcome delivered: added `scripts/check/measure_lazy_discovery.py` plus the canonical measurement doc and a checked-in audit artifact; the first audit shows the current defaults/proof/ownership selector path reduces total retrieval size by 60.8% and the simple token proxy by 60.7% for the three current one-answer questions.
- Validation confirmed: `uv run python scripts/check/measure_lazy_discovery.py --target .`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run ruff check scripts/check/measure_lazy_discovery.py`.
- Follow-on routed to: `ROADMAP.md`.
- Resume from: promote the final remaining issue for configurable canonical startup filename support.

## Drift Log

- 2026-04-14: Promoted after the bootstrap hardening issue closed and the remaining open queue narrowed to measurement proof plus startup-filename configurability.
- 2026-04-14: Completed by shipping the first cheap measurement framework and auditing the current selector path in this repo instead of claiming compactness wins by intuition alone.
