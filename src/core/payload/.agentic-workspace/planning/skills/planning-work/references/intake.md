# Relate the current request to existing work

Read the upstream task or issue and the current Planning question about whether
this task continues the selected record. Preserve
source system, identifier/URL, title, problem and relevant product reasoning in a
compact summary. External trackers supply intent evidence; they do not become
execution custody or replace the user's current instructions.

Use the existing active record for the same work. Otherwise judge the smallest useful
destination: no retention, review finding, external intent evidence, a bounded
decomposition, or accepted execution custody. Do not paste whole threads, invent
a numeric creation threshold or turn knowledge into an active plan. Keep source
references in the owner-returned fields, not an invented Markdown record shape.
An incumbent selection alone does not establish the current task relation.

```agentic-owner-reference
{"kind":"request","owner":"planning","id":"planning/continuation/v1"}
```

## Upgrade legacy aggregate input

`state.toml` supplies legacy owner relations, never current status, revision or
continuation. Read the canonical owner body and use the exact Planning selection
request to establish the task relation, then invoke `planning.reconcile`. With
several owner candidates, choose one of `legacy_aggregate.selection_requests`;
absence or ambiguity does not authorise deletion.

Preserve useful aggregate-only intent in the appropriate canonical owner through
Planning's update operation. Unfamiliar aggregate material stays preserved until
its owner relations can be represented safely. Once current selection custody
is committed, use the exact terminal retention request for `state.toml`, judging
that no unresolved intent or continuing value remains in the aggregate itself.
The operation guards source and consumers and provides interruption recovery.
After retirement, native and repository reads use the same owner body; fresh
setup does not recreate an aggregate.
