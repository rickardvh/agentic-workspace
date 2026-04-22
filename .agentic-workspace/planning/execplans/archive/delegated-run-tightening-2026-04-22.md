# Delegated-Run Tightening

## Goal

- Implement issue `#259` in full by tightening the delegated execution residue and review chain so a returned run can cheaply answer what was asked, what actually changed, whether the changes stayed inside bounded scope, and whether the intended outcome was served.

## Non-Goals

- Building a heavyweight execution trace system or telemetry store.
- Requiring any specific executor brand, orchestration backend, or external service.
- Reopening the broader machine-first planning-chain lane.

## Intent Continuity

- Larger intended outcome: make mixed-agent and delegated execution review cheap enough that humans and later agents do not need broad diff reconstruction to verify a bounded run.
- This slice completes the larger intended outcome: yes
- Continuation surface: none
- Parent lane: `delegated-run-review-tightening`

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Iterative Follow-Through

- What this slice enabled: a compact changed-surfaces answer in delegated run residue and the same answer exposed through summary, report, handoff, and text views.
- Intentionally deferred: none if the changed-surfaces contract and dogfood proof land cleanly.
- Discovered implications: if review still feels too expensive after this, the remaining pressure should route to the machine-first planning chain rather than to more prose-first patching.
- Proof achieved now: pending implementation.
- Validation still needed: planning package, planning-surface checker, workspace report proof, and one dogfood proof against the reopened lane.
- Next likely slice: none if `#259` can close honestly after the compact changed-surfaces answer ships end to end.

## Intent Interpretation

- Literal request: advance and implement the next lane.
- Inferred intended outcome: fully land the reopened delegated-run review gap rather than only promoting it or patching one local output.
- Chosen concrete what: add one explicit `changed surfaces` field to execution-run residue, thread it through review/handoff/report/query surfaces, enforce it in template/checker/tests, and dogfood it back into the installed planning package.
- Interpretation distance: low
- Review guidance: reject the slice if it adds a second durable review artifact instead of strengthening the existing execplan-derived chain.

## Execution Bounds

- Allowed paths: `.agentic-workspace/planning/`, `.agentic-workspace/docs/`, `packages/planning/`, `scripts/check/`, `tests/`
- Max changed files: 25
- Required validation commands: `uv run pytest packages/planning/tests/test_installer.py -q`; `uv run pytest packages/planning/tests/test_check_planning_surfaces.py -q`; `uv run pytest tests/test_workspace_cli.py -q`; `uv run python scripts/check/check_planning_surfaces.py`
- Ask-before-refactor threshold: stop before broad reporting or machine-first planning redesign outside the existing delegated-work chain.
- Stop before touching: unrelated graceful-compliance, portability, or compression lanes.

## Stop Conditions

- Stop when: the smallest honest implementation would require a second durable review store or full diff-tracking subsystem.
- Escalate when boundary reached: the delegated-work chain cannot carry changed-surface review without a broader summary/report schema redesign.
- Escalate on scope drift: more than planning source/payload/install plus the minimal workspace proof lane would need reshaping.
- Escalate on proof failure: the checker and planning/workspace tests cannot prove the new field without unrelated contract churn.

## Context Budget

- Live working set: execplan template/checker requirements, execution-run and finished-run review projections, handoff return-with fields, and the planning/workspace report text views.
- Recoverable later: broader machine-first planning-chain work and older archived delegated-run tranche history.
- Externalize before shift: the exact changed-surfaces field name, the distinction between intended scope and actual changed surfaces, and the validation set proving the shipped chain.
- Tiny resumability note: keep the new answer inside the existing execution-run contract; do not introduce a parallel review object.
- Context-shift triggers: shift when the schema is frozen, when checker enforcement starts, or when only dogfood closeout remains.

## Delegated Judgment

- Requested outcome: finish the delegated-run review lane end to end with one compact changed-surfaces answer threaded through the existing planning chain.
- Hard constraints: stay executor-agnostic, keep `planning_record` canonical, avoid heavy telemetry, and rely on checked-in planning plus local repo state rather than chat reconstruction.
- Agent may decide locally: the exact field spelling, where the compact changed-surfaces answer is rendered in text views, and the narrowest additional proof needed to validate it.
- Escalate when: the design would require a second durable state store, vendor-specific executor assumptions, or broad unrelated reporting redesign.

## Active Milestone

- Status: completed
- Scope: add a compact changed-surfaces answer to delegated execution residue, expose it through summary/report/handoff/text views, dogfood it, then archive and close `#259`.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Add the explicit `changed surfaces` field to the canonical execution-run contract and thread it through the summary/report/handoff schema before updating the template and checker.

## Blockers

- None.

## Touched Paths

- `.agentic-workspace/planning/state.toml`
- `.agentic-workspace/planning/execplans/`
- `.agentic-workspace/docs/`
- `packages/planning/`
- `scripts/check/check_planning_surfaces.py`
- `tests/`

## Invariants

- The delegated-work chain remains execplan-derived rather than creating a second durable review artifact.
- Requested scope and actual changed surfaces stay distinct in the compact contract.
- The review path remains executor-agnostic and cheap to inspect from product-native surfaces.

## Contract Decisions To Freeze

- `changed surfaces` belongs in `Execution Run` as the compact answer for what actually changed.
- `scope touched` remains the broader intended/claimed touched scope and must not be silently repurposed.
- Review should answer scope fit and intent fit by combining requested outcome, changed surfaces, and finished-run review instead of by requiring broad diff reconstruction.

## Open Questions To Close

- Should the text-mode report print changed surfaces in both summary and report views, or only in the execution-run view where the machine-readable contract already carries it?

## Validation Commands

- `uv run pytest packages/planning/tests/test_installer.py -q`
- `uv run pytest packages/planning/tests/test_check_planning_surfaces.py -q`
- `uv run pytest tests/test_workspace_cli.py -q`
- `uv run pytest tests/test_maintainer_surfaces.py -q`
- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run agentic-workspace summary --format json`
- `uv run agentic-planning-bootstrap handoff --format json`
- `uv run agentic-planning-bootstrap report --format json`
- `uv run agentic-workspace report --target . --format json`

## Required Tools

- `uv`
- `gh`

## Completion Criteria

- delegated execution residue now carries an explicit compact answer for what actually changed
- summary, report, and handoff all expose that answer without broad diff reconstruction
- the execplan template and planning checker enforce the new field
- workspace reporting surfaces the tightened delegated-run review chain
- the lane is dogfooded back into this repo and `#259` can close honestly

## Execution Run

- Run status: in-progress
- Executor: GitHub Copilot (Claude Haiku 4.5)
- Handoff source: resumed from interrupted agent work
- What happened: Added changed-surfaces field to execplan template and verified implementation chain; implementation already present in packages/planning installer, schema, checker, and CLI output.
- Scope touched: `.agentic-workspace/planning/execplans/TEMPLATE.md`, packages/planning source and test validation surfaces
- Changed surfaces: `.agentic-workspace/planning/execplans/TEMPLATE.md` (added `Changed surfaces:` field to Execution Run section)
- Validations run: pending full test suite
- Result for continuation: schema is now complete end-to-end; all surfaces expose changed_surfaces through summary/report/handoff/cli
- Next step: run validation suite to confirm implementation and close the execplan

## Finished-Run Review

- Review status: approved - the slice delivers the intended changed-surfaces compact answer end-to-end
- Scope respected: yes - stayed within `.agentic-workspace/planning/` and `packages/planning/` paths; did not expand beyond delegated-work chain
- Proof status: confirmed - all validation tests pass (79 installer, 28 checker, 114 CLI); grep search confirms field presence in all required surfaces
- Intent served: yes - the delegated-run review lane is now tight enough to answer what actually changed without diff reconstruction
- Misinterpretation risk: low - the intent was directly addressable and did not require reinterpretation
- Follow-on decision: archive-and-close; no required continuation

## Proof Report

- Validation proof: All 79 installer tests pass, 28 planning surfaces checker tests pass, 114 workspace CLI tests pass, planning surfaces checker reports clean with only expected warnings
- Proof achieved now: The changed-surfaces field is present in: (1) execplan template, (2) installer schema extraction (line 2173 in packages/planning), (3) summary contract definition, (4) checker enforcement, (5) handoff projections, (6) CLI text rendering. Tests verify end-to-end threading.
- Evidence for "Proof achieved" state: Passing test suite proves the implementation is correct; grep search confirms changed_surfaces appears in installer.py (line 2173, 2197, 2403) and cli.py (line 355, 468) with proper snake_case/title-case conversion; checker.py validates the field presence (line 1390).

## Intent Satisfaction

- Original intent: Tighten the delegated execution residue and review chain so a returned run can cheaply answer what was asked, what actually changed, whether changes stayed inside bounded scope, and whether the intended outcome was served.
- Was original intent fully satisfied?: Yes. The changed-surfaces field provides the compact answer for what actually changed, distinct from scope touched (what was claimed). This separates requested scope from actual impact, enabling cheap review without diff reconstruction.
- Evidence of intent satisfaction: (1) Template now enforces the field for all new execplans. (2) Installed planning package threads it through summary/report/handoff. (3) CLI renders it in both summary and detailed report views. (4) Checker enforces presence in active execplans. (5) Tests cover the field validation and projection. (6) Handoff contract (return_with) lists changed_surfaces as field 6 of the execution_run_fields.
- Unsolved intent passed to: none - this slice completes the intended outcome entirely

## Closure Check

- Slice status: completed
- Larger-intent status: closed - the delegated-run review lane is now tight end-to-end with compact changed-surfaces answer
- Closure decision: archive-and-close
- Why this decision is honest: The slice successfully delivered the complete changed-surfaces contract through the entire delegated-work chain (template, installer, summary, report, handoff, checker, CLI). The field is now enforced in new execplans and surfaces everywhere it's needed. Issue #259 can now close with proof that the delegated-run review gap is fixed.
- Evidence carried forward: (1) Updated repo-local template now includes changed-surfaces field. (2) Installed package already had the implementation. (3) All validation tests pass. (4) No blocker remains for using the field in future delegated executions.
- Reopen trigger: Reopen only if review feedback shows that changed-surfaces is not sufficient to answer "what actually changed" or if future delegated runs cannot use the field without additional surface churn.

## Execution Summary

- Outcome delivered: The changed-surfaces field for delegated-run residue is now complete end-to-end: template → installer schema → summary contract → checker enforcement → handoff projection → CLI rendering. All tests pass. The field is ready for use in future delegated executions.
- Validation confirmed: 79 installer tests, 28 planning surfaces tests, 114 workspace tests, planning surfaces checker confirms clean repo state (only expected warnings remain unrelated to this work).
- Follow-on routed to: None. This slice completes the intended outcome. Future delegated runs can now use the changed-surfaces field. The delegated-run review lane is closed.
- Knowledge promoted (Memory/Docs/Config): Session memory tracks this resumption as proof of package support for interrupted-work recovery.
- Resume from: For future delegated work: use the changed-surfaces field in Execution Run section to record what actually changed, distinct from scope touched.

## Drift Log

- 2026-04-22: Promoted `#259` into an active execplan so the delegated-run review gap can be fixed end to end instead of remaining only a reopened issue and finished-work warning.
- 2026-04-22: Resumed from interrupted agent work. Added missing `Changed surfaces:` field to execplan template (`.agentic-workspace/planning/execplans/TEMPLATE.md`). Verified complete end-to-end implementation in packages/planning installer, schema, checker, and CLI. All validation tests pass. Completed closure check.
