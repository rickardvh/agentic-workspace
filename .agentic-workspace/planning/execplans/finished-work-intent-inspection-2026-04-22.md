# Finished Work Intent Inspection

## Goal

- Implement issue `#260` in full by shipping a compact finished-work inspection path that can verify previously closed lanes without bespoke checklist files or broad manual reconstruction.

## Non-Goals

- Re-auditing every historical closed issue in one pass.
- Making GitHub or any external tracker authoritative over closeout truth.
- Building a heavyweight archive database or second planning store.

## Intent Continuity

- Larger intended outcome: make closure truthfulness inspectable not only at archive time, but also later when a human or agent needs to verify whether previously closed work really landed.
- This slice completes the larger intended outcome: yes
- Continuation surface: none
- Parent lane: `finished-work-intent-inspection`

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Iterative Follow-Through

- What this slice enabled: one compact finished-work inspection path for archived closeouts that can classify older lanes without bespoke audit checklists.
- Intentionally deferred: none if the new inspection surface and one dogfood proof lane land cleanly.
- Discovered implications: the delegated-run review and machine-first planning lanes remain live follow-ons but should no longer need a bespoke inspection process to justify reopening.
- Proof achieved now: pending implementation.
- Validation still needed: package/report/query proof and one dogfood inspection pass over at least one previously closed lane.
- Next likely slice: none if `#260` closes honestly after the shipped inspection path and one dogfood proof pass land together.

## Intent Interpretation

- Literal request: ingest the new reopening issues, prioritize them, and start with intent/closure so the repo does not need to repeat the manual verification process.
- Inferred intended outcome: make verification of previously closed lanes a product-native capability rather than a bespoke one-off audit ritual.
- Chosen concrete what: add a compact finished-work inspection contract derived from archived planning residue plus optional external evidence, expose it through report/summary surfaces, and dogfood it against at least one closed lane.
- Interpretation distance: low
- Review guidance: reject the slice if it still depends on a hand-authored checklist file or assumes GitHub is always present.

## Execution Bounds

- Allowed paths: `packages/planning/src/`, `packages/planning/bootstrap/.agentic-workspace/`, `src/agentic_workspace/`, `tests/`, `.agentic-workspace/`
- Max changed files: 30
- Required validation commands: `uv run pytest packages/planning/tests/test_installer.py -q`; `uv run pytest tests/test_workspace_cli.py -q`; `uv run python scripts/check/check_planning_surfaces.py`
- Ask-before-refactor threshold: stop before broad archive or issue-ingestion redesign outside planning/reporting surfaces
- Stop before touching: unrelated memory package semantics or already-open graceful-compliance work

## Stop Conditions

- Stop when: the design would require a second durable archive store rather than deriving from checked-in residue.
- Escalate when boundary reached: the current summary/report path cannot carry a compact finished-work inspection view without a broader reporting-contract redesign.
- Escalate on scope drift: the work turns into a mass historical audit instead of shipping the reusable inspection surface.
- Escalate on proof failure: the new surface cannot classify at least one previously closed lane from checked-in residue plus optional evidence.

## Context Budget

- Live working set: archived execplan residue shape, intent-validation logic, planning report surfaces, and the closed-lane proof cases behind `#260`.
- Recoverable later: broader product-compression and portability follow-on lanes.
- Externalize before shift: the finished-work inspection contract shape, classification vocabulary, and the proof-case lane used to validate it.
- Tiny resumability note: the surface must work from archived residue first; external issue state is only optional corroborating evidence.
- Context-shift triggers: shift when the contract shape is frozen, when report integration starts, or when only dogfood validation and closeout remain.

## Delegated Judgment

- Requested outcome: ship a compact finished-work inspection path and dogfood it immediately on one previously closed lane.
- Hard constraints: keep checked-in archive residue primary, keep external evidence optional, and avoid creating a second archival state system.
- Agent may decide locally: the exact classification names, where the compact inspection view lives, and which archived lane is the best proof case.
- Escalate when: the smallest honest implementation still needs a heavyweight historical audit store or mandatory network access.

## Active Milestone

- Status: in-progress
- Scope: add finished-work inspection contracts to planning report surfaces, support compact classification of archived closeouts, dogfood one closed lane, then archive and close `#260`.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Define the compact finished-work inspection contract from archived execplan residue and wire it into planning report output before choosing the first dogfood proof case.

## Blockers

- None.

## Touched Paths

- `packages/planning/src/repo_planning_bootstrap/`
- `packages/planning/bootstrap/.agentic-workspace/docs/`
- `packages/planning/bootstrap/.agentic-workspace/planning/`
- `src/agentic_workspace/`
- `tests/`
- `.agentic-workspace/planning/state.toml`
- `.agentic-workspace/planning/execplans/archive/`

## Invariants

- Archived execplan residue remains the primary source for finished-work inspection.
- External issue or tracker state remains optional corroborating evidence only.
- The inspection path must stay compact and queryable rather than becoming a prose audit template.
- The new surface must help future reopen decisions, not require a bespoke checklist file to justify them.

## Contract Decisions To Freeze

- Finished-work verification should be a product surface, not a one-off audit ritual.
- The inspection path should classify archived closeouts from checked-in residue first and optional external evidence second.
- Reopen routing should remain explicit and checked-in when the inspection surface finds a likely premature closeout.

## Open Questions To Close

- Which archived lane provides the clearest first dogfood proof case without overlapping an already-open follow-on issue?

## Validation Commands

- `uv run pytest packages/planning/tests/test_installer.py -q`
- `uv run pytest tests/test_workspace_cli.py -q`
- `uv run pytest tests/test_maintainer_surfaces.py -q`
- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run agentic-workspace summary --format json`
- `uv run agentic-planning-bootstrap report --format json`
- `uv run agentic-workspace report --target . --format json`

## Required Tools

- `uv`
- `gh`

## Completion Criteria

- planning ships a compact finished-work inspection surface for archived closeouts
- the surface can classify previously closed work without broad manual reconstruction
- external tracker state stays optional and advisory
- one previously closed lane is re-checked through the new product path as proof
- future reopen decisions no longer depend on a bespoke checklist file
- `#260` can close with honest proof and no chat-only follow-through

## Execution Run

- Run status:
- Executor:
- Handoff source:
- What happened:
- Scope touched:
- Validations run:
- Result for continuation:
- Next step:

## Finished-Run Review

- Review status:
- Scope respected:
- Proof status:
- Intent served:
- Misinterpretation risk:
- Follow-on decision:

## Proof Report

- Validation proof:
- Proof achieved now:
- Evidence for "Proof achieved" state:

## Intent Satisfaction

- Original intent:
- Was original intent fully satisfied?:
- Evidence of intent satisfaction:
- Unsolved intent passed to:

## Closure Check

- Slice status:
- Larger-intent status:
- Closure decision:
- Why this decision is honest:
- Evidence carried forward:
- Reopen trigger:

## Execution Summary

- Outcome delivered:
- Validation confirmed:
- Follow-on routed to:
- Knowledge promoted (Memory/Docs/Config):
- Resume from:

## Drift Log

- 2026-04-22: Ingested reopening issue `#260` as the active top-priority lane so finished-work verification can become product-native before more historical closeout audits are attempted.
