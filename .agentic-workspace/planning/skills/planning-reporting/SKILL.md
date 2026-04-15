---
name: planning-reporting
description: Report active planning state, proof expectations, and next-action guidance using the canonical summary JSON before reading raw planning files.
---

# Planning Reporting

Use this skill when you need a compact, comparable picture of what is active and what should happen next, without rereading `TODO.md` or execplan prose first.
Use `agentic-workspace report --target <repo> --format json` first when the question is broader than planning state alone.

## Canonical Reporting Surface

Prefer:

```bash
agentic-planning-bootstrap summary --target <repo> --format json
```

This is the canonical compact inspection surface for active planning state. The `planning_record` payload carries the minimum facts needed for safe continuation, including next action and proof expectations.
Treat `planning_record` as canonical active state when it is available; `active_contract` and `resumable_contract` are thinner projections, and raw planning files are fallback surfaces.

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
