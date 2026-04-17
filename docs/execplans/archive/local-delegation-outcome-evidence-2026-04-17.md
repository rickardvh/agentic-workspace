# Local Delegation Outcome Evidence And Derived Tuning

## Goal

- Add the smallest local-only evidence loop that lets delegation target profiles improve over time from real outcomes without turning the repo into a scheduler.

## Non-Goals

- Auto-route tasks to targets.
- Rewrite `agentic-workspace.local.toml` automatically in this first slice.
- Introduce repo-owned policy for target confidence or task fit.
- Build a heavy telemetry or experiment system.

## Intent Continuity

- Larger intended outcome: make planner-to-worker delegation cheaper over time by turning repeated local experience into better advisory target confidence and task-fit hints.
- This slice completes the larger intended outcome: yes
- Continuation surface: none
- Parent lane: local-delegation-outcome-evidence

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Iterative Follow-Through

- What this slice enabled: the orchestrator can read one local-only outcome artifact, compare repeated target results by task class, and see derived confidence/task-fit suggestions in the config surface.
- Intentionally deferred: automated profile rewrites, target invocation adapters, multi-armed-bandit logic, per-run token accounting, and repo-owned policy changes.
- Discovered implications: a separate sibling evidence artifact is quieter than extending the editable local TOML profile, and confidence tuning already becomes useful before any automatic write-back exists.
- Proof achieved now: the local outcome log command, schema, config reporting surface, and live repo dogfood pass all worked with advisory-only semantics.
- Validation still needed: none for this lane beyond archive and issue closure.
- Next likely slice: none right now.

## Delegated Judgment

- Requested outcome: support local-only delegation outcome evidence and derived tuning suggestions while keeping the target profiles and handoff contract advisory.
- Hard constraints: local-only; no checked-in semantics; no scheduler behavior; no hidden auto-edits; capability- and outcome-shaped rather than vendor-prescriptive.
- Agent may decide locally: the smallest evidence artifact shape, which fields are enough to derive coarse suggestions, how suggestions are surfaced in `config`, and what minimal command records outcomes.
- Escalate when: the slice would require repo-owned orchestration policy, automatic routing decisions, or a broad analytics framework instead of one narrow local evidence loop.

## Active Milestone

- ID: local-delegation-outcome-evidence
- Status: completed
- Scope: added a local-only delegation outcome artifact, ingested it through workspace config reporting, derived coarse confidence/task-fit suggestions, and dogfooded it on this repo.
- Ready: done
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this lane, close `#173`, and advance the roadmap back to the next broader candidate lane.

## Blockers

- None.

## Touched Paths

- .gitignore
- TODO.md
- ROADMAP.md
- docs/execplans/local-delegation-outcome-evidence-2026-04-17.md
- docs/execplans/archive/local-delegation-outcome-evidence-2026-04-17.md
- docs/reviews/local-delegation-outcome-evidence-dogfood-2026-04-17.md
- docs/workspace-config-contract.md
- docs/orchestrator-workflow-contract.md
- docs/delegation-posture-contract.md
- docs/contract-schema-index.md
- src/agentic_workspace/cli.py
- src/agentic_workspace/contracts/contract_inventory.json
- src/agentic_workspace/contracts/schemas/delegation_outcomes.schema.json
- scripts/check/check_contract_tooling_surfaces.py
- tests/test_workspace_cli.py

## Invariants

- Checked-in planning and repo policy remain authoritative for work shape; local evidence only tunes target hints.
- The existing handoff contract remains the canonical worker boundary.
- Outcome evidence must stay local-only and optional.
- Suggestions must stay advisory and auditable.

## Contract Decisions To Freeze

- Outcome evidence belongs next to the local override, not in checked-in state.
- Derived suggestions should appear in `agentic-workspace config --target ./repo --format json`, not in a separate orchestration dashboard.
- The first slice may suggest confidence/task-fit adjustments, but it must not rewrite profiles automatically.
- If a target keeps failing a task class, the product should suggest narrower fit or more review, not silently stop using the target.

## Open Questions To Close

- None. The bounded slice closed cleanly.

## Validation Commands

- uv run pytest tests/test_workspace_cli.py tests/test_contract_tooling.py -q
- uv run python scripts/check/check_contract_tooling_surfaces.py
- uv run python scripts/check/check_planning_surfaces.py
- uv run agentic-workspace note-delegation-outcome --target . --delegation-target gpt_5_4_mini --task-class bounded-docs --outcome success --format json
- uv run agentic-workspace config --target . --format json

## Required Tools

- uv
- gh

## Completion Criteria

- A local-only delegation outcome artifact shape exists and is documented.
- `agentic-workspace config --target ./repo --format json` reports derived advisory tuning suggestions from that evidence.
- The loop is dogfooded on this repo with a realistic local example.
- No scheduler behavior or repo-owned policy change is introduced.

## Execution Summary

- Outcome delivered: local delegation outcomes now record through `agentic-workspace note-delegation-outcome`, accumulate in `agentic-workspace.delegation-outcomes.json`, and surface advisory confidence/task-fit suggestions through `agentic-workspace config --target ./repo --format json`.
- Validation confirmed: `uv run pytest tests/test_workspace_cli.py tests/test_contract_tooling.py -q`; `uv run python scripts/check/check_contract_tooling_surfaces.py`; `uv run python scripts/check/check_planning_surfaces.py`; live repo dogfood via repeated `agentic-workspace note-delegation-outcome` calls followed by `agentic-workspace config --target . --format json`.
- Follow-on routed to: none; the roadmap returns to the next broader candidate lane.
- Resume from: not needed unless a new local-outcome follow-on is explicitly promoted.

## Drift Log

- 2026-04-17: Promoted immediately after real local target profiles were configured and the next obvious cost class became manual confidence/task-fit maintenance over time.
- 2026-04-17: Implemented as a sibling local JSON artifact plus derived config suggestions instead of extending the editable local override TOML.
- 2026-04-17: Dogfooding showed the loop is already useful for advisory confidence tuning without any automatic profile rewrite.
