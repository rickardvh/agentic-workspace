# Local Delegation Target Profiles And Confidence Hints

## Goal

- Add the smallest local-only delegation target profile contract that helps an orchestrator stop guessing blindly about executor capability while staying advisory, agent-agnostic, and non-scheduler.

## Non-Goals

- Turn repo config into a routing matrix for vendors, models, or APIs.
- Make checked-in planning or workspace policy own local executor choice.
- Require internal delegation, a specific CLI, or a specific external API.
- Infer or auto-learn target confidence in this first slice beyond reading local hints.

## Intent Continuity

- Larger intended outcome: make planner-to-worker delegation cheaper and safer by letting local environments declare available targets and coarse capability confidence without leaking that into checked-in repo semantics.
- This slice completes the larger intended outcome: yes
- Continuation surface: none
- Parent lane: local-delegation-target-profiles

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Iterative Follow-Through

- What this slice enabled: a planner can read one local-only target inventory with coarse strength/confidence/task-fit hints before deciding whether to stay direct, delegate internally, or hand the checked-in worker contract to an external executor.
- Intentionally deferred: automatic confidence updates, per-task telemetry, target invocation adapters, and scheduler-like routing policy.
- Discovered implications: the smallest useful target profile shape is enough to reduce blind guessing, and the main unexpected friction in practice was Windows BOM tolerance for local TOML rather than missing target metadata fields.
- Proof achieved now: the local override parser, formal schema, config reporting surface, and live repo dogfood pass all worked with advisory-only semantics.
- Validation still needed: none for this lane beyond archive and issue closure.
- Next likely slice: none right now.

## Delegated Judgment

- Requested outcome: support local-only target profiles with coarse capability/confidence hints and surface them through effective config reporting without changing repo-owned semantics.
- Hard constraints: local-only; advisory only; capability-shaped rather than vendor-prescriptive where possible; keep the existing mixed-agent posture fields authoritative for base capability/cost posture; do not prescribe internal vs external delegation method.
- Agent may decide locally: the exact table shape, the smallest useful field set, how to summarize task-fit hints, where the effective reporting should live, and which narrow tests prove the contract.
- Escalate when: the profile shape starts dictating runtime executor choice, requires checked-in repo policy changes, or needs a broad plugin-style target registry instead of one narrow local contract.

## Active Milestone

- ID: local-target-profile-contract
- Status: completed
- Scope: added a local-only target profile table to `.agentic-workspace/config.local.toml`, exposed it through `agentic-workspace config`, aligned formal schemas/docs/tests, and dogfooded it on one realistic local profile.
- Ready: done
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this lane, close `#172`, and advance the roadmap to the next candidate lane.

## Blockers

- None.

## Touched Paths

- TODO.md
- .agentic-workspace/planning/execplans/local-delegation-target-profiles-2026-04-17.md
- .agentic-workspace/planning/execplans/archive/local-delegation-target-profiles-2026-04-17.md
- .agentic-workspace/planning/reviews/local-delegation-target-profiles-dogfood-2026-04-17.md
- docs/workspace-config-contract.md
- docs/orchestrator-workflow-contract.md
- .agentic-workspace/docs/delegation-posture-contract.md
- src/agentic_workspace/cli.py
- src/agentic_workspace/contracts/schemas/workspace_local_override.schema.json
- scripts/check/check_contract_tooling_surfaces.py
- tests/test_workspace_cli.py
- tests/test_contract_tooling.py

## Invariants

- Checked-in repo policy must remain separate from local target hints.
- The existing planner/worker handoff remains the canonical task contract.
- Target profiles must help decide delegation depth and review burden, not become a scheduler.
- The contract must stay usable for internal delegation, local models, and external CLI/API executors.

## Contract Decisions To Freeze

- Target profiles belong in `.agentic-workspace/config.local.toml`, not `.agentic-workspace/config.toml`.
- Target labels may name concrete executors locally, but the product contract should describe their meaning in capability terms.
- Confidence and task-fit hints are advisory only and may be revised locally without repo review.
- Effective reporting should distinguish base mixed-agent posture from per-target advisory hints.

## Open Questions To Close

- None. The lane closed cleanly at the bounded first slice.

## Validation Commands

- uv run pytest tests/test_workspace_cli.py tests/test_contract_tooling.py -q
- uv run python scripts/check/check_contract_tooling_surfaces.py
- uv run python scripts/check/check_planning_surfaces.py
- uv run agentic-workspace config --target . --format json

## Required Tools

- uv
- gh

## Completion Criteria

- `.agentic-workspace/config.local.toml` supports a narrow local-only target profile shape.
- Formal config schema artifacts describe the new local-only shape.
- `agentic-workspace config --target . --format json` reports the target profiles and makes their advisory status explicit.
- One dogfood pass proves the profile helps the orchestrator interpret target capability without becoming a scheduler.

## Execution Summary

- Outcome delivered: local-only delegation target profiles now support `strength`, `confidence`, `task_fit`, and `execution_methods`, and the config surface reports derived advisory handoff/review hints without prescribing routing.
- Validation confirmed: `uv run pytest tests/test_workspace_cli.py tests/test_contract_tooling.py -q`; `uv run python scripts/check/check_contract_tooling_surfaces.py`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-workspace config --target . --format json`.
- Follow-on routed to: none; the roadmap advances to the next lane.
- Resume from: not needed unless a new delegation-target follow-on is explicitly promoted.

## Drift Log

- 2026-04-17: Promoted from roadmap issue `#172` after the first orchestrator-workflow dogfood pass showed the remaining uncovered cost class was target capability confidence, not missing planner/worker contract structure.
- 2026-04-17: Implementation landed with a narrow local-only target profile table, config reporting, schema/docs/tests alignment, and a live repo dogfood pass.
- 2026-04-17: Dogfood revealed one in-scope friction point: PowerShell-written UTF-8 BOM local override files needed to parse cleanly on Windows; TOML loading now tolerates that.
