# Lazy Discovery Workflow Measurements

## Goal

- Expand the existing lazy-discovery measurement framework so the repo has workflow-class evidence that compact/query-first surfaces reduce reading cost in more than the original three selector cases.

## Non-Goals

- Do not add telemetry, runtime logging, or provider-specific token accounting.
- Do not redesign the compact-contract profile or reporting hierarchy in the same slice.
- Do not turn the measurement lane into generic product analytics.

## Intent Continuity

- Larger intended outcome: close GitHub issue `#87` with a broader but still cheap proof bar for query-first and report-first workflow claims.
- This slice completes the larger intended outcome: yes
- Continuation surface: none

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Delegated Judgment

- Requested outcome: extend the current measurement script and audit so startup, planning inspection, jumpstart/setup, proof selection, ownership lookup, and restart/handoff questions are all measured with the same cheap framework.
- Hard constraints: keep the method reproducible and cheap; prefer explicit proxies over fake exactness; keep the workflow set bounded.
- Agent may decide locally: exact workflow questions, the baseline read bundles, the compact/query-first command set, and whether the final evidence lives in one review artifact or a paired doc plus review.
- Escalate when: the tranche would require live telemetry, scenario harnesses, or a new benchmark system instead of an extension of the checked-in measurement contract.

## Active Milestone

- ID: lazy-discovery-workflow-measurements
- Status: completed
- Scope: extended the measurement script and docs, ran one broader audit over a small workflow set, and prepared GitHub issue `#87` for closure.
- Ready: complete
- Blocked: none
- optional_deps: GitHub issue `#87`

## Immediate Next Action

- None. Slice completed; clear the final GitHub issue and leave the roadmap empty.

## Blockers

- None.

## Touched Paths

- `ROADMAP.md`
- `TODO.md`
- `.agentic-workspace/planning/execplans/lazy-discovery-workflow-measurements-2026-04-15.md`
- `docs/lazy-discovery-measurements.md`
- `.agentic-workspace/planning/reviews/`
- `scripts/check/measure_lazy_discovery.py`
- `tests/`

## Invariants

- The framework stays cheap enough to run as a normal checked-in proof lane.
- Measurements stay explicit about what is proxy versus qualitative interpretation.
- Workflow-class measurement should compare the preferred compact/query-first route against the plausible broader route a contributor would otherwise use.

## Contract Decisions To Freeze

- The expanded tranche should keep one small reusable script rather than adding a second measurement tool.
- File-bundle baselines are acceptable when the real fallback path is prose-first or file-first rather than a broader machine-readable command.

## Open Questions To Close

- Which workflow classes are broad enough to matter for `#87` but still bounded enough to keep the audit cheap?
- Which manual/qualitative notes belong beside the numeric proxies so the audit says something about restart and curation cost rather than only byte counts?

## Validation Commands

- `uv run pytest tests/test_lazy_discovery_measurements.py -q`
- `uv run python scripts/check/measure_lazy_discovery.py --target .`
- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run ruff check scripts/check/measure_lazy_discovery.py tests/test_lazy_discovery_measurements.py`

## Required Tools

- None.

## Completion Criteria

- The measurement script covers a broader workflow set than the original three selector cases.
- The canonical measurement doc explains the expanded method and its limits.
- A new audit artifact records the measured savings and qualitative workflow takeaways for the broader tranche.
- GitHub issue `#87` can close on the resulting evidence.

## Execution Summary

- Outcome delivered: expanded `scripts/check/measure_lazy_discovery.py` from three selector-only questions to five workflow classes, added focused regression coverage, updated the canonical measurement doc, and recorded the broader audit in `.agentic-workspace/planning/reviews/lazy-discovery-workflow-measurements-2026-04-15.md`; the resulting steady-state audit shows five compact routes replacing sixteen fallback file reads while cutting retrieval payload by about 86% overall.
- Validation confirmed: `uv run pytest tests/test_lazy_discovery_measurements.py -q`; `uv run ruff check scripts/check/measure_lazy_discovery.py tests/test_lazy_discovery_measurements.py`; `uv run python scripts/check/measure_lazy_discovery.py --target .`; `uv run python scripts/check/check_planning_surfaces.py`
- Follow-on routed to: none
- Resume from: no remaining roadmap candidate; next work starts from new GitHub intake or new dogfooding friction.

## Drift Log

- 2026-04-15: Promoted GitHub issue `#87` into the final active measurement tranche after the smaller discoverability fixes landed and the roadmap narrowed to this one evidence pass.
- 2026-04-15: Completed the broader workflow-class audit and confirmed the compact/query-first route replaces 16 fallback file reads and reduces retrieval payload by about 86% across the measured tranche.
