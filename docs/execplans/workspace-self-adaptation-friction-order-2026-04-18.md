# Workspace Self-Adaptation And Friction-Response Order

## Goal

- Close roadmap lane `workspace-self-adaptation-friction-order` by clarifying that workspace-self-adaptation is distinct from repo-directed improvement, making the default friction-response order explicit, and adding one compact guardrail test so internal adaptation stays bounded instead of becoming a hidden workaround layer.

## Non-Goals

- Create a new workspace module or a second policy language.
- Turn workspace-self-adaptation into blanket permission for broad repo changes.
- Hide real repo seams by silently absorbing every friction signal into workspace behavior.
- Add scheduler logic or vendor-specific delegation rules.

## Intent Continuity

- Larger intended outcome: the workspace layer should reduce its own fit friction first when that is the cheapest honest fix, while still surfacing real repo problems instead of concealing them behind accumulated workaround logic.
- This slice completes the larger intended outcome: yes
- Continuation surface: none
- Parent lane: workspace-self-adaptation-friction-order

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Iterative Follow-Through

- What this slice should enable: `improvement_latitude` can stay about repo-directed initiative, while workspace-self-adaptation remains available under every mode and follows one explicit response order plus guardrail test.
- Intentionally deferred: any deeper repo-friction lane such as validation friction, memory follow-through, or broader portability work.
- Discovered implications: repo-friction reporting should stay visible even when the workspace adapts itself first, because self-adaptation is not proof that the repo has no structural problem.
- Proof still needed: shipped docs, defaults, reporting payloads, and tests all agree on the split, response order, and guardrail wording.
- Validation still needed: workspace CLI tests, planning-surface checks, and one live defaults/report dogfood pass on this repo.
- Next likely slice: return to `ROADMAP.md` and promote `validation-friction-repo-friction`.

## Delegated Judgment

- Requested outcome: implement issues `#176`, `#177`, and `#178` as one coherent workspace-policy lane with issue-sized commits.
- Hard constraints: keep policy workspace-level; keep repo-friction evidence derived and visible; keep `improvement_latitude` about repo-directed initiative rather than runtime orchestration; do not create a second decision engine.
- Agent may decide locally: exact field names, the smallest stable additions to defaults/report payloads, which examples best show self-adaptation first versus repo-directed improvement, and whether the guardrail test lives in docs only or also in report/default surfaces.
- Escalate when: the lane would require new editable state, hidden repo-specific workaround rules, or a change that makes self-adaptation mask external repo problems by default.

## Active Milestone

- ID: self-adaptation-guardrails
- Status: in-progress
- Scope: close `#178` by freezing one compact guardrail test and anchoring it in docs/report guidance with examples from this repo.
- Ready: ready
- Blocked: none
- optional_deps: none

## Upcoming Milestones

- None.

## Immediate Next Action

- Implement the `#178` guardrail test in the config contract, reporting contract, design principles, defaults payload, report payload, and CLI tests so workspace self-adaptation stays general, bounded, and cheaper than repeated repo or user burden.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- docs/execplans/workspace-self-adaptation-friction-order-2026-04-18.md
- docs/workspace-config-contract.md
- docs/design-principles.md
- docs/reporting-contract.md
- docs/default-path-contract.md
- src/agentic_workspace/cli.py
- src/agentic_workspace/reporting_support.py
- tests/test_workspace_cli.py

## Invariants

- Workspace-self-adaptation must stay bounded by correctness, ownership, proof, and portability rules.
- Repo-directed improvement remains controlled by `workspace.improvement_latitude`.
- Repo-friction evidence stays visible and derived even when the workspace adapts itself first.
- The workspace may improve its own fit, but must not normalize poor repo structure indefinitely through narrow hidden compensation paths.

## Contract Decisions To Freeze

- Workspace-self-adaptation and repo-directed improvement are separate policy targets.
- `improvement_latitude` governs repo-directed initiative only.
- The default friction-response order should prefer honest workspace adaptation first, then repo-directed improvement when the root problem is genuinely external.
- One compact guardrail test should decide when self-adaptation is healthy fit improvement versus hidden workaround accretion.

## Open Questions To Close

- Which compact defaults/report fields are enough to make the policy split queryable without inventing a second policy surface?
- Which examples best show honest workspace adaptation first versus repo-directed improvement?
- What is the smallest guardrail wording that still stops concealment drift?

## Validation Commands

- uv run pytest tests/test_workspace_cli.py -q
- uv run python scripts/check/check_planning_surfaces.py
- uv run agentic-workspace defaults --section improvement_latitude --format json
- uv run agentic-workspace report --target . --format json

## Required Tools

- uv
- gh

## Completion Criteria

- The config contract, default-path contract, reporting contract, and design principles all distinguish workspace-self-adaptation from repo-directed improvement.
- `agentic-workspace defaults --section improvement_latitude --format json` exposes the split, the default response order, and the compact guardrail test.
- `agentic-workspace report --target . --format json` keeps repo-friction visible while reflecting the updated policy semantics.
- Tests and planning checks pass, the lane is archived, and issues `#176`-`#178` are closed.

## Execution Summary

- Outcome delivered: pending.
- Validation confirmed: pending.
- Follow-on routed to: pending.
- Resume from: the active milestone in this execplan.

## Drift Log

- 2026-04-18: Promoted roadmap lane `workspace-self-adaptation-friction-order` into active planning after issue intake clarified that `improvement_latitude` semantics were still ambiguous.
- 2026-04-18: Landed the `#176` policy split so `improvement_latitude` now governs repo-directed initiative only while bounded workspace-self-adaptation remains allowed under every mode.
- 2026-04-18: Landed the `#177` response-order contract so the workspace now adapts itself first when that is the honest cheap fix and only then promotes repo-directed improvement.
