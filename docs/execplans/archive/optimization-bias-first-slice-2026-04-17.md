# Optimization Bias First Slice

## Goal

- Add one narrow repo-owned `optimization_bias` policy that shapes durable output/residue preference without changing execution method or canonical state.

## Non-Goals

- Turn output bias into a scheduler, reasoning-style, or delegation policy.
- Add multiple canonical state formats for different bias modes.
- Expand beyond one report surface and one rendered human-facing view in this slice.

## Intent Continuity

- Larger intended outcome: Agentic Workspace exposes a safe repo-owned output/residue preference that keeps canonical state stable while letting repos lean toward agent efficiency, balance, or human legibility.
- This slice completes the larger intended outcome: yes
- Continuation surface: none

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Iterative Follow-Through

- What this slice enabled: Workspace-level output/residue preference is now a shipped checked-in policy with explicit semantic guardrails.
- Intentionally deferred: none
- Discovered implications: The safest initial scope is shared workspace reporting and rendered human-facing views; that proves the contract without forcing planning or memory package divergence.
- Proof achieved now: The repo dogfoods `optimization_bias = "agent-efficiency"` through config/defaults/reporting, and the rendered report text reflects the bias while JSON truth stays unchanged.
- Validation still needed: none beyond future ordinary-work dogfooding on additional rendered or residue surfaces.
- Next likely slice: Move to the setup/jumpstart findings-promotion lane unless repeated work exposes another output-bias gap.

## Delegated Judgment

- Requested outcome: Ship one narrow repo-owned `optimization_bias` policy and apply it to one report surface plus one rendered human-facing view.
- Hard constraints: Keep canonical state stable, keep the setting presentation-only, and do not let it prescribe execution method.
- Agent may decide locally: Exact field names, the smallest supported bias set, which rendered human view to make bias-aware first, and the narrowest proof that the first slice is safe.
- Escalate when: The best-looking change would create semantic drift across bias modes, alter delegated-judgment/proof/ownership behavior, or widen into generic UI preference sprawl.

## Active Milestone

- ID: optimization-bias-first-slice
- Status: completed
- Scope: add the policy, expose it through config/defaults/reporting, and dogfood `agent-efficiency` in this repo.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this completed slice, close issues `#131` through `#133`, and advance the roadmap to setup/jumpstart findings promotion.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- agentic-workspace.toml
- docs/execplans/optimization-bias-first-slice-2026-04-17.md
- docs/design-principles.md
- docs/reporting-contract.md
- docs/workspace-config-contract.md
- src/agentic_workspace/cli.py
- src/agentic_workspace/workspace_output.py
- tests/test_workspace_cli.py

## Invariants

- `optimization_bias` must stay an output/residue preference, not an execution-method prescription.
- Different bias modes may change rendering density, but they must not change canonical truth.
- Repo-owned checked-in policy is the right place for this preference; extra runtime choreography is out of scope.

## Contract Decisions To Freeze

- The first supported bias set should stay narrow.
- Machine-readable output remains canonical; rendered human views may vary in density.
- Bias-aware rendering should default to `balanced` unless the repo sets otherwise.

## Open Questions To Close

- Which single rendered human-facing view is the safest first place to reflect the bias?
- What is the smallest machine-readable report contract that makes the effective bias visible without inventing another state store?

## Validation Commands

- uv run pytest tests/test_workspace_cli.py -q
- uv run python scripts/check/check_planning_surfaces.py
- uv run agentic-workspace defaults --section optimization_bias --format json
- uv run agentic-workspace config --target . --format json
- uv run agentic-workspace report --target . --format json

## Required Tools

- uv
- gh

## Completion Criteria

- `workspace.optimization_bias` is supported in repo config and effective config reporting.
- `agentic-workspace defaults --section optimization_bias --format json` exposes the safe contract and guardrails.
- `agentic-workspace report --format json` exposes the effective bias without changing report semantics.
- One rendered human-facing view applies the bias through output density rather than execution or truth changes.

## Execution Summary

- Outcome delivered: Added repo-owned `workspace.optimization_bias`, exposed it through `agentic-workspace config` and `defaults`, added `output_contract` to `agentic-workspace report`, and made the rendered report text bias-aware without changing canonical JSON semantics.
- Validation confirmed: `uv run pytest tests/test_workspace_cli.py -q`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-workspace defaults --section optimization_bias --format json`; `uv run agentic-workspace config --target . --format json`; `uv run agentic-workspace report --target . --format json`; `uv run agentic-workspace report --target .`
- Follow-on routed to: `ROADMAP.md` next candidate `Agent-produced setup and jumpstart findings promotion`
- Resume from: No further action in this plan; start from the next roadmap lane when a new bounded slice is promoted.

## Drift Log

- 2026-04-17: Promoted issues #131 through #133 from the roadmap into an active first-slice execplan.
- 2026-04-17: Landed the first optimization-bias policy slice, dogfooded `agent-efficiency` in this repo, and prepared the plan for archive.
