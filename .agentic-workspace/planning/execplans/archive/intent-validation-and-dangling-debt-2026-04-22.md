# Intent Validation And Dangling Debt

Compact inactive-plan residue generated at archive time.
Use git history for superseded active-step detail; keep only the closure, continuation, proof, and cheap-resume residue here.

## Origin

- Archived from: .agentic-workspace/planning/execplans/intent-validation-and-dangling-debt-2026-04-22.md

## Intent Continuity

- Larger Intended Outcome: make closure, follow-through, and quiet-state inspection trustworthy even when work spans checked-in planning plus optional external planning evidence.
- This Slice Completes The Larger Intended Outcome: yes
- Continuation Surface: none
- Parent Lane: `intent-validation-and-dangling-debt`

## Required Continuation

- Required Follow-On For The Larger Intended Outcome: no
- Owner Surface: none
- Activation Trigger: none

## Delegated Judgment

- Requested Outcome: ship the inspection surface first, then dogfood it immediately in the installed repo.
- Hard Constraints: keep checked-in planning primary, treat external systems as optional evidence only, and leave lower-trust signals compact and informative.
- Agent May Decide Locally: exact field names, evidence artifact schema, warning wording, and how to represent dangling-debt status in summary/report.
- Escalate When: the smallest honest implementation would still need a new heavyweight planning runtime or mandatory network dependency.

## Intent Interpretation

- Literal Request: create a new issue for the intent-validation gap, ingest it, and implement it in the shipped product first without assuming GitHub or any external planning system.
- Inferred Intended Outcome: make dangling ends, incomplete larger intent, and low-trust closeout inspectable even in local-only or non-GitHub environments while still accommodating optional external evidence when available.
- Chosen Concrete What: add a compact intent-validation / closeout-debt surface to planning summary and report, define an optional external evidence artifact, surface lower-trust findings in workspace reporting, and dogfood the current repo's hidden `#251` cluster through that mechanism.
- Interpretation Distance: low
- Review Guidance: reject the change if the new surface requires GitHub to exist or if it leaves the current hidden open-lane debt unrepresented after the pass.

## Execution Bounds

- Allowed Paths: `packages/planning/src/`, `packages/planning/bootstrap/.agentic-workspace/`, `src/agentic_workspace/`, `tests/`, `.agentic-workspace/`
- Max Changed Files: 30
- Required Validation Commands: `uv run pytest packages/planning/tests/test_installer.py -q`; `uv run pytest tests/test_workspace_cli.py -q`; `uv run python scripts/check/check_planning_surfaces.py`
- Ask-Before-Refactor Threshold: stop before broad CLI or installer redesign outside planning/reporting surfaces
- Stop Before Touching: unrelated memory payload semantics or non-planning product lanes

## Stop Conditions

- Stop When: the implementation would require making an external tracker authoritative instead of optional evidence.
- Escalate When Boundary Reached: the current summary/report schema cannot carry the new inspection surface without a broader contract redesign.
- Escalate On Scope Drift: the work starts turning into broad workflow redesign instead of inspection, validation, and dangling-end detection.
- Escalate On Proof Failure: summary/report cannot surface the current repo's hidden `#251` cluster after dogfood sync.

## Context Budget

- Live Working Set: planning summary/report schema, workspace report integration, optional evidence artifact shape, and the current repo's hidden `#251` cluster.
- Recoverable Later: older archived closure-trust tranches and the broader product-compression history.
- Externalize Before Shift: the optional evidence contract, the exact dangling-debt fields, and the dogfood proof path for `#251`.
- Tiny Resumability Note: the shipped product must work with no external tracker at all; GitHub is only one dogfood evidence source.
- Context-Shift Triggers: shift when source/payload/install sync lands, when workspace report integration starts, or when issue closeout is the only work left.

## Execution Run

- Run Status: completed.
- Executor: single-agent local implementation in this repo.
- Handoff Source: `.agentic-workspace/planning/execplans/intent-validation-and-dangling-debt-2026-04-22.md` plus the issue body for `#257`.
- What Happened: added an `intent_validation_contract` to planning summary/report, introduced an optional `external-intent-evidence.json` artifact and contract doc, promoted planning-side signals into workspace reporting, restored the hidden `#251` cluster to roadmap state, and dogfooded the new surface against live issue evidence.
- Scope Touched: planning source, planning payload docs/readme/checker surfaces, workspace report aggregation, package and workspace tests, installed planning state, and repo-local optional evidence.
- Validations Run: `uv run pytest packages/planning/tests/test_installer.py -q`; `uv run pytest tests/test_workspace_cli.py -q`; `uv run pytest tests/test_maintainer_surfaces.py -q`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-workspace summary --format json`; `uv run agentic-planning-bootstrap report --format json`; `uv run agentic-workspace report --target . --format json`.
- Result For Continuation: no further implementation residue is needed for `#257`; only archive, refresh, and issue closeout remain.
- Next Step: archive-and-close.

## Finished-Run Review

- Review Status: completed.
- Scope Respected: yes; the work stayed inside planning/reporting source, shipped payload, installed planning state, and the minimum workspace integration required for proof.
- Proof Status: satisfied pending final payload refresh and archive cleanup.
- Intent Served: yes; the result is vendor-agnostic and treats external systems as optional evidence rather than required truth.
- Misinterpretation Risk: low; the dogfood proof uses GitHub evidence, but the shipped product path works when the evidence file is absent.
- Follow-On Decision: archive-and-close.

## Proof Report

- Validation proof: `uv run pytest packages/planning/tests/test_installer.py -q`; `uv run pytest tests/test_workspace_cli.py -q`; `uv run pytest tests/test_maintainer_surfaces.py -q`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-workspace summary --format json`; `uv run agentic-planning-bootstrap report --format json`; `uv run agentic-workspace report --target . --format json`; `uv run agentic-planning-bootstrap upgrade --target .`; `uv run agentic-memory-bootstrap upgrade --target .`.
- Proof achieved now: the product can detect dangling-intent and lower-trust closeout signals from checked-in planning plus optional external evidence, and workspace reporting now preserves those planning findings instead of dropping them.
- Evidence for "proof achieved" state: package tests, workspace CLI tests, maintainer-surface tests, planning-surface checks, summary/report outputs, and the refreshed installed payload all agree on the new contract and on the visible `#251` follow-on lane.

## Intent Satisfaction

- Original intent: create the issue, ingest it, and implement a shipped vendor-agnostic intent-validation and dangling-debt inspection layer, then dogfood it back into the installed repo.
- Was original intent fully satisfied?: yes
- Evidence of intent satisfaction: `intent_validation_contract` now ships from the planning package, workspace reporting surfaces its findings, optional external evidence is documented and supported, and the hidden `#251` cluster is visible again in checked-in planning state and dogfood evidence.
- Unsolved intent passed to: none

## Closure Check

- Slice status: bounded slice complete
- Larger-intent status: closed
- Closure decision: archive-and-close
- Why this decision is honest: `#257` asked for an inspection and validation layer, not for the downstream `#251` cluster itself to be implemented; the shipped product and installed repo now both carry that layer, and the follow-on cluster is explicitly preserved in roadmap state rather than left in chat.
- Evidence carried forward: archived execplan residue, planning/source/payload/test changes, `.agentic-workspace/planning/external-intent-evidence.json`, and the visible `graceful-partial-compliance` roadmap lane.
- Reopen trigger: reopen if summary/report stop surfacing intent-validation cleanly, if optional evidence becomes mandatory, or if quiet-state inspection can again hide open larger intent with no checked-in continuation owner.

## Execution Summary

- Outcome delivered: planning now ships a compact intent-validation contract, optional external evidence input, and lower-trust/dangling-intent reporting that also survives workspace aggregation; the installed repo uses that surface to keep the `#251` cluster visible.
- Validation confirmed: package tests, workspace CLI tests, maintainer-surface tests, planning-surface checks, summary/report queries, and final planning/memory upgrades passed.
- Follow-on routed to: `.agentic-workspace/planning/state.toml` roadmap lane `graceful-partial-compliance`.
- Knowledge promoted (memory/docs/config): planning docs and the new external-evidence contract now live in the package-owned planning domain; repo-local optional external evidence lives in `.agentic-workspace/planning/external-intent-evidence.json`.
- Resume from: promote `graceful-partial-compliance` when ready.
