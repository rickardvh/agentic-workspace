# Planning Runtime Boundary Disposition

Date: 2026-06-27
Issues: #1657, parent #1649
Lane: P2 runtime boundary decomposition audits

## Summary

#1657 audited the Planning package runtime boundaries that remain accepted in
`python_runtime_projection_inventory.json`. The baseline remains 36 accepted
Planning package runtime boundaries:

- 11 `operation-function-call` boundaries into `repo_planning_bootstrap.installer`
- 25 `runtime-facade-call` boundaries, including 14 into
  `repo_planning_bootstrap.runtime_projection` and 11 installer mirrors

This slice implements the safe local decomposition available now: Planning
runtime projection wrappers now declare repeated operation-call value mapping,
defaults, and coercions through `_call_planning_operation` and
`_planning_operation_value`, with focused regression tests. It does not claim a
generated minimization count reduction. The remaining count is still 36 because
command-generation cannot yet render and prove the generic operation-call
adapter or the conditional dispatch adapter without hiding package-owned
mutation semantics.

## Grouping

Pure value-map wrappers:

- None were pure enough to move directly. Each Planning mutation wrapper also
  carries defaults, boolean coercion, inverted boolean coercion, or package
  mutation/provenance semantics.

Value-map plus defaults/coercions:

- `apply_planning_new_plan_operation`
- `apply_planning_intake_artifact_operation`
- `apply_planning_promote_to_plan_operation`
- `apply_planning_lane_create_operation`
- `apply_planning_lane_promote_operation`
- `apply_planning_lane_activate_operation`
- `apply_planning_lane_close_operation`
- `apply_planning_lane_archive_operation`
- `apply_planning_closeout_operation`
- `apply_planning_delegation_decision_operation`

These wrappers now share the declared local call adapter. The portable part is
the value/default/coercion map; the callee still owns Planning mutation,
validation, safety, and provenance.

Conditional dispatch:

- `apply_planning_archive_plan_operation`

This wrapper chooses `archive_parent_lane_closeout` when
`parent_lane_closeout` is present, otherwise `archive_execplan`. Branch value
maps now use the shared local call adapter, but the branch selection remains
hand-owned until command-generation can render declared conditional operation
dispatch.

Mutation transaction/safety owner:

- `adopt_bootstrap`
- `install_bootstrap`
- `uninstall_bootstrap`
- `upgrade_bootstrap`
- `load_planning_reconcile_operation`
- Planning lifecycle and lane/archive/closeout callees reached by the wrappers

These retain package ownership because they mutate managed planning surfaces,
install or upgrade payloads, reconcile live planning state, or write provenance
under Planning safety rules.

View/output formatting:

- `load_planning_report_operation`
- `load_planning_summary_operation`
- `render_planning_prompt_operation`
- `emit_planning_operation_output`
- `_print_report`
- `_print_summary`
- `_print_reconcile`
- `_print_handoff`

These remain Planning view policy and compatibility formatting. They should be
split only after a declared view-render policy exists with equivalent proof.

Irreducible planning judgment:

- `close_planning_item`
- `create_review_record`
- `doctor_bootstrap`
- `planning_handoff`
- `collect_status`
- `verify_payload`

These own Planning-specific inspection, payload, handoff, review, close-item,
or status judgment rather than portable deterministic generated behavior.

## Implemented Safe Decomposition

Implemented now:

- introduced `_planning_operation_value` for raw, string default, boolean, and
  inverted-boolean coercions
- introduced `_call_planning_operation` for declared positional and keyword
  operation-call mapping
- refactored Planning runtime projection mutation wrappers through that adapter
- added regression tests for lane creation mapping, archive conditional branch
  mapping, archive execplan mapping, and closeout inverted retain-archive
  behavior
- updated `python_runtime_projection_inventory.json` and
  `python_operation_execution_inventory.json` with the #1657 grouping and
  minimization disposition

Runtime source edit classification:

- changed path:
  `packages/planning/src/repo_planning_bootstrap/runtime_projection.py`
- edit reason: `new-primitive-implementation`
- owner: Planning package runtime boundary owner
- source symbols:
  `_planning_operation_value`, `_call_planning_operation`,
  `apply_planning_new_plan_operation`,
  `apply_planning_intake_artifact_operation`,
  `apply_planning_promote_to_plan_operation`,
  `apply_planning_lane_create_operation`,
  `apply_planning_lane_promote_operation`,
  `apply_planning_lane_activate_operation`,
  `apply_planning_lane_close_operation`,
  `apply_planning_lane_archive_operation`,
  `apply_planning_archive_plan_operation`,
  `apply_planning_closeout_operation`,
  `apply_planning_delegation_decision_operation`
- focused proof:
  `uv run pytest packages/planning/tests/test_runtime_projection.py -q`
- residual owner: command-generation owns the next adapter movement through
  command-generation#72 and command-generation#73; Planning keeps semantic
  mutation and safety primitives explicit

Command-generation blockers opened:

- rickardvh/command-generation#72: generic operation-call value/default/coercion
  adapters
- rickardvh/command-generation#73: declared conditional operation-call dispatch

## Remaining Boundary Count

Remaining accepted Planning package runtime boundaries: 36.

Why retained:

- value-map/default/coercion wrappers need command-generation#72 before the
  portable adapter can be generated and proven
- archive conditional dispatch needs command-generation#73
- lifecycle, reconcile, lane/archive/closeout, payload, handoff, review, and
  status functions still own Planning mutation safety, provenance, or judgment
- view/report/prompt output functions still own Planning compatibility policy

This slice advances #1649 but does not satisfy the whole parent issue.
