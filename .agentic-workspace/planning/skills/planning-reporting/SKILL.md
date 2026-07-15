---
name: planning-reporting
description: Report active planning state, proof expectations, and next-action guidance using the canonical summary JSON before reading raw planning files.
---

# Planning Reporting

Use this skill when you need a compact, comparable picture of what is active and what should happen next, without rereading `.agentic-workspace/planning/state.toml` or execplan prose first.
Use `agentic-workspace report --target <repo> --format json` first when the question is broader than planning state alone.
This reporting skill is not a bypass around enabled-AW participation: consult it when `start`, `next_safe_action`, `skill_routing`, or active Planning state routes here, and preserve any planning or proof gate before implementation or closeout.

## Primary Ownership

This skill owns compact projection of active planning state. It reports the current state, warnings, next action, and proof posture from canonical JSON; it is not the semantic owner for intent satisfaction, closeout permission, or decomposition structure.

Route intent satisfaction to `planning-intent-verification`, closeout mechanics to `planning-closeout-trust`, broad lifecycle sequencing to `planning-high-assurance-lifecycle`, and parent/lane/slice shaping to `planning-decompose`.

## Canonical Reporting Surface

Prefer:

```bash
agentic-workspace summary --target <repo> --format json
```

This is the canonical compact inspection surface for active planning state. The `planning_record` payload carries the minimum facts needed for safe continuation, including next action and proof expectations.
Treat `planning_record` as canonical active state when it is available; `active_contract` and `resumable_contract` are thinner projections, and raw planning files are fallback surfaces.

When an explicit current task needs a route, select `planning_route_decision` from `summary` or `planning_safety_gate` from `start`. Treat its task relation, owner posture, and required transition as the shared Planning contract; do not rebuild a task-switch classification from prose, status aliases, or a consumer-local heuristic.

When the question is "which proof lane is enough?", also consult:

```bash
agentic-workspace defaults --section proof_selection --format json
```

## Reporting Procedure (Bounded)

1. Run the planning summary JSON.
2. If `planning_record` is present, report from it first:
   - `status`
   - `next_action`
   - `blockers`
   - `completion_criteria`
   - `proof_expectations`
   - `escalate_when`
   - `continuation_owner`
   - `minimal_refs`
3. If `planning_record` is missing or ambiguous, report that explicitly and stop before inventing canonical state.
4. Include any `warnings` from the summary (do not hide drift or missing-contract warnings).
5. Only then open raw planning files if the compact summary is insufficient for the question.

## Output Contract

Return a compact planning report containing:

- active surface refs (active TODO id and/or active execplan path, if present in summary)
- next action
- proof expectations / recommended lane
- blockers (or `none`)
- escalation boundary
- warnings worth acting on
