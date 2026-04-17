# Declarative Contract Tooling First Tranche

## Goal

- Land the first bounded declarative contract tooling tranche for workspace proof, report, and selector surfaces.

## Non-Goals

- Extract all workspace defaults or lifecycle behavior into manifests in one pass.
- Turn procedural lifecycle or reconciliation logic into declarative files prematurely.
- Add runtime requirements that adopters need in order to use the workspace package normally.
- Expand into memory or planning package schema extraction in this slice.

## Intent Continuity

- Larger intended outcome: Stable workspace contract metadata becomes more inspectable, portable, and drift-resistant by moving declarative proof/report/selector definitions into checked-in manifests and schemas while leaving procedural logic in Python.
- This slice completes the larger intended outcome: yes
- Continuation surface: none

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Iterative Follow-Through

- What this slice enabled: Workspace proof, report, and selector metadata can now be inspected and validated as checked-in declarative contract files instead of only as Python branches.
- Intentionally deferred: broader defaults extraction and lifecycle/reconciliation manifesting.
- Discovered implications: The declarative boundary stays trustworthy only if the repo keeps explicit ownership notes for what remains procedural and keeps validation close to the manifests that ship.
- Proof achieved now: A checked-in boundary note and inventory exist, manifests and schemas back the first contract surfaces, CLI output reads from those manifests, and a drift check validates both the manifests and emitted payload shapes.
- Validation still needed: none beyond future ordinary-work dogfooding on additional declarative extraction candidates.
- Next likely slice: Return to the roadmap queue after archiving this tranche; do not widen extraction beyond the first stable contract surfaces without new repeated evidence.

## Delegated Judgment

- Requested outcome: Implement the full first declarative contract tooling lane covering issues `#92` through `#95`.
- Hard constraints: Keep the extraction narrow, preserve current user-visible behavior, and leave procedural lifecycle/reconciliation logic in Python unless a stable declarative boundary is already obvious.
- Agent may decide locally: Exact manifest and schema file layout, the smallest useful schema set, how much helper loading code is justified, and the narrowest validation/drift checks that prove parity.
- Escalate when: The best-looking change would widen into a generic workflow engine, require runtime schema tooling for adopters, or extract unstable procedural behavior into manifests just to satisfy the concept.

## Active Milestone

- Status: active
- Scope: add the boundary note/inventory, shared schemas, manifest-backed proof/report/selector metadata, and validation/drift checks.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Add the boundary note and inventory first, then extract one stable manifest set for proof, report, and selector metadata before adding validation.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- docs/execplans/declarative-contract-tooling-first-tranche-2026-04-17.md
- docs/compact-contract-profile.md
- docs/proof-surfaces-contract.md
- docs/reporting-contract.md
- docs/contributor-playbook.md
- src/agentic_workspace/cli.py
- src/agentic_workspace/contracts/
- tests/test_workspace_cli.py
- tests/test_contract_tooling.py
- scripts/check/

## Invariants

- Declarative contract files must stay subordinate to canonical docs and emitted CLI behavior.
- Procedural lifecycle and reconciliation logic remain Python-owned unless a stable declarative boundary is explicit.
- Runtime behavior and user-visible outputs must stay materially unchanged in this tranche.

## Contract Decisions To Freeze

- The first declarative boundary covers proof routes, report schema metadata, selector metadata, and compact answer envelopes.
- Lifecycle execution, reconciliation, and mixed dynamic payload shaping remain procedural in Python for now.
- Validation for the new contract files should stay development-time and repo-local, not an adopter runtime requirement.

## Open Questions To Close

- Which minimal schema set is enough to validate the first declarative surfaces without inventing a broad new contract language?
- Which metadata is genuinely stable enough to extract now, and which should stay Python-owned in the first slice?

## Validation Commands

- uv run pytest tests/test_workspace_cli.py -q
- uv run pytest tests/test_contract_tooling.py -q
- uv run python scripts/check/check_contract_tooling_surfaces.py
- uv run python scripts/check/check_planning_surfaces.py

## Required Tools

- uv
- gh

## Completion Criteria

- A checked-in boundary note classifies current proof/report/selector/lifecycle/reconciliation behavior as declarative, procedural, or derived.
- Shared schemas exist for the compact answer envelope plus the first proof/report/selector manifests.
- The workspace CLI reads the extracted proof/report/selector metadata from checked-in manifests without user-visible contract drift.
- A repo-local validation/drift check proves manifest/schema validity and emitted-surface parity.

## Execution Summary

- Outcome delivered: pending
- Validation confirmed: pending
- Follow-on routed to: pending
- Resume from: pending

## Drift Log

- 2026-04-17: Promoted roadmap issues `#92` through `#95` into one active declarative-contract-tooling tranche.
