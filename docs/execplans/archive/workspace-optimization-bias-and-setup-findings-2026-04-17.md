# Workspace Optimization Bias And Setup Findings

## Goal

- Close the full first roadmap lane by integrating `optimization_bias` into the normal operating path, completing the setup/jumpstart findings contract, and adding planning-friction as explicit repo-friction evidence.

## Non-Goals

- Build a new analysis framework or telemetry subsystem.
- Turn `optimization_bias` into execution routing or scheduler policy.
- Let setup findings auto-write broad planning or Memory state.
- Treat all hard tasks as planning-friction or repo-failure evidence.

## Intent Continuity

- Larger intended outcome: the workspace layer should make repo-owned output posture, quiet findings promotion, and repo-friction evidence visible and useful in ordinary operation without adding a second analysis framework.
- This slice completes the larger intended outcome: yes
- Continuation surface: none
- Parent lane: workspace-optimization-bias-findings

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Iterative Follow-Through

- What this slice should enable: ordinary recovery should expose the effective output posture cheaply, setup findings should have a stable quiet contract, and planning-friction should appear as bounded repo-friction evidence.
- Intentionally deferred: any broader setup finding ontology, new optimization-bias modes, or heavy planning telemetry.
- Discovered implications: if planning-friction is real in current dogfood, it should feed the same repo-friction/reporting path instead of creating a new dashboard.
- Proof still needed: shipped docs, config/defaults/report/setup surfaces, and tests all agree on the compact contract and dogfood it on this repo.
- Validation still needed: narrow workspace CLI/report/setup tests plus planning-surface checks and one live report/setup dogfood pass.
- Next likely slice: return to the roadmap and promote either the Memory habitual-pull lane or any repeated follow-on surfaced by dogfooding this integrated lane.

## Delegated Judgment

- Requested outcome: implement issues `#148`, `#149`, `#151`, `#152`, `#153`, `#154`, `#155`, `#156`, and `#174` as one coherent lane with issue-sized commits.
- Hard constraints: keep repo-owned planning and config semantics canonical; keep setup findings bounded and advisory; keep optimization bias as output/residue preference only; keep planning-friction as explicit repo-friction evidence rather than a separate planning system.
- Agent may decide locally: exact field names and compact report wording, the smallest stable findings schema that still carries current classes, which normal recovery surface should expose effective optimization bias, and how to classify planning-friction evidence subtypes.
- Escalate when: a proposed change would turn output bias into execution policy, require hidden runtime-specific routing, widen setup into a general analyzer, or make planning-friction rely on vague subjective telemetry rather than bounded operational evidence.

## Active Milestone

- ID: optimization-bias-footprint-and-recovery
- Status: in-progress
- Scope: close `#148`, `#151`, `#152`, and `#153` by auditing visibility, surfacing effective bias in compact recovery, and freezing allowed/invariant surfaces.
- Ready: ready
- Blocked: none
- optional_deps: none

## Upcoming Milestones

- ID: setup-findings-contract-completion
- Status: pending
- Scope: close `#149`, `#154`, `#155`, and `#156` by settling the quiet default artifact path, tightening the minimal schema, and deciding whether any additional finding class is justified.
- Ready: ready
- Blocked: depends on the optimization-bias/recovery milestone only for shared front-door wording
- optional_deps: none

- ID: planning-friction-repo-friction
- Status: pending
- Scope: close `#174` by defining bounded planning-friction evidence and folding it into the existing repo-friction/reporting path.
- Ready: ready
- Blocked: depends on the setup-findings milestone only if setup findings become a source of planning-friction evidence
- optional_deps: none

## Immediate Next Action

- Audit the shipped optimization-bias and setup-findings surfaces, then land the first optimization-bias visibility and boundary commit for issues `#151` and `#152`.

## Blockers

- None.

## Touched Paths

- TODO.md
- docs/execplans/workspace-optimization-bias-and-setup-findings-2026-04-17.md
- docs/default-path-contract.md
- docs/reporting-contract.md
- docs/workspace-config-contract.md
- docs/setup-findings-contract.md
- docs/jumpstart-contract.md
- src/agentic_workspace/cli.py
- src/agentic_workspace/reporting_support.py
- src/agentic_workspace/workspace_output.py
- src/agentic_workspace/contracts/
- tests/test_workspace_cli.py
- tests/test_contract_tooling.py

## Invariants

- `optimization_bias` may change rendering density or residue style only; canonical truth and execution posture stay invariant.
- Setup findings remain optional external input; the workspace layer standardizes promotion only.
- Repo-friction evidence remains derived, queryable, and bounded rather than becoming a second editable state store.
- Planning-friction must reflect operational seam/proof/ownership difficulty, not generic model weakness.

## Contract Decisions To Freeze

- One compact normal recovery path should expose the effective optimization bias.
- Setup findings should keep one quiet default artifact path unless later exceptions are explicitly justified.
- The minimal findings schema should stay routing-oriented and agent-agnostic.
- Planning-friction should join `repo_friction` as another evidence class, not as a separate dashboard or scoring system.

## Open Questions To Close

- Which single ordinary recovery surface is the right compact place to expose effective optimization bias?
- Which rendered or residue surfaces should honor optimization bias, and which must stay invariant?
- Is the current `tools/setup-findings.json` path already the quiet default, or does the contract still leave ambiguity?
- Are repo-friction evidence and planning candidates enough durable setup classes, or is one more class justified by repeated value?
- What bounded planning-friction subtypes are specific enough to be useful without turning into generic telemetry?

## Validation Commands

- uv run pytest tests/test_workspace_cli.py -q
- uv run pytest tests/test_contract_tooling.py -q
- uv run python scripts/check/check_contract_tooling_surfaces.py
- uv run python scripts/check/check_planning_surfaces.py
- uv run agentic-workspace defaults --section optimization_bias --format json
- uv run agentic-workspace setup --target . --format json
- uv run agentic-workspace report --target . --format json

## Required Tools

- uv
- gh

## Completion Criteria

- The effective optimization bias is visible in one compact ordinary recovery path and its boundary is explicit.
- Setup findings have one quiet default artifact path, a compact stable schema, and an explicit keep-or-expand decision on finding classes.
- Planning-friction is queryable as repo-friction evidence with bounded operational subtypes.
- The lane is dogfooded on this repo and archived cleanly with issue closure history.

## Execution Summary

- Outcome delivered: integrated optimization bias into ordinary recovery and workspace posture, completed the quiet setup-findings promotion bridge with a formal schema and class-scope review, and added planning-friction as explicit repo-friction evidence.
- Validation confirmed: `uv run pytest tests/test_workspace_cli.py -q`; `uv run pytest tests/test_contract_tooling.py -q`; `uv run python scripts/check/check_contract_tooling_surfaces.py`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-workspace report --target . --format json`.
- Follow-on routed to: `docs/reviews/optimization-bias-visibility-audit-2026-04-17.md`, `docs/reviews/setup-findings-classes-review-2026-04-18.md`, `docs/reviews/planning-friction-signal-review-2026-04-18.md`, and `ROADMAP.md` next candidate `validation-friction-repo-friction`.
- Resume from: `ROADMAP.md` once the next bounded repo-friction lane is promoted.

## Drift Log

- 2026-04-17: Promoted roadmap lane `workspace-optimization-bias-findings` into active planning with issue-sized milestones for optimization-bias integration, setup-findings completion, and planning-friction evidence.
- 2026-04-17: Captured the bounded optimization-bias visibility audit in checked-in review form to anchor the remaining integration work.
- 2026-04-18: Recorded the setup-findings class-scope review and kept the contract at the first two durable classes only.
- 2026-04-18: Closed the lane after shipping the optimization-bias integration, setup-findings completion, and planning-friction repo-friction slices.
