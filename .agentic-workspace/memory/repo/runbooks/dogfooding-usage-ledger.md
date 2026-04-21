# Dogfooding Usage Ledger

## Status

Stable

## Scope

Local dogfooding evaluation procedure for recording which surfaces are actually used in ordinary repo work and why they were chosen or skipped.

## Applies to

- `.agentic-workspace/memory/repo/runbooks/dogfooding-feedback-routing.md`
- `docs/lazy-discovery-measurements.md`
- repo-local dogfooding notes captured during normal work

## Load when

- You are recording ordinary daily-use surface pull, feature-choice reasons, or skip reasons during a repo task.

## Review when

- The daily-use capture contract changes.
- The feedback routing path changes.
- The measurement lane starts trying to answer usage questions instead of retrieval-cost questions.
- Ordinary-use pull audits start surfacing repeated outsider-legibility or self-hosting-bias findings.

## Failure signals

- The same skipped surface keeps showing up without being recorded.
- Choice reasons are disappearing into chat instead of the repo.
- A usage entry starts replacing a plan, review finding, or durable doc.

## When to use this

- A task is small enough that the useful signal is which surfaces were actually chosen.
- You want to track why a feature was used or skipped without shipping telemetry.

## Symptoms

- A surface is available but rarely chosen.
- A feature works, but only after explanation.
- The same fallback path keeps getting used in ordinary work.

## Checks

- Record one entry per meaningful task or decision point.
- Capture the goal, surfaces used, surfaces skipped, selection reason, skip reason, friction, cost note, and follow-up.
- Add a short legibility note when a fresh external agent would likely have chosen differently.
- Keep the entry short enough that it survives ordinary maintenance.

## Steps

1. Record the task class and goal while the work is happening.
2. Note which surface you used first.
3. Note which surface you skipped and why.
4. Add a short friction or cost note.
5. Route any repeated pattern into planning, a review artifact, or canonical docs.
6. If the same choice keeps showing up, note whether the pull came from repository familiarity, model capability, or genuine product fit.

## Entry Template

- Task class:
- Goal:
- Surface used first:
- Surface skipped:
- Choice reason:
- Skip reason:
- Friction or cost note:
- Follow-up:
- Outsider-legibility note:
- Self-hosting-bias note:

## Verification

- The ledger shows repeated choice patterns that can be reviewed later.
- A repeated pattern can be routed to planning state candidate lanes, active execplans, or canonical docs without reconstructing the reasoning from chat.

## Boundary reminder

- Keep this note focused on daily-use pull and feature-choice reasons.
- Do not turn it into product telemetry, a generic analytics system, or a second planning backlog.

## Verified against

- `.agentic-workspace/memory/repo/runbooks/dogfooding-feedback-routing.md`
- `docs/lazy-discovery-measurements.md`
- `.agentic-workspace/memory/repo/runbooks/README.md`
- `.agentic-workspace/memory/repo/manifest.toml`

## Pitfalls

- Logging every interaction instead of only meaningful task or decision points.
- Recording a future candidate here instead of promoting it into planning.
- Letting the ledger become a narrative history instead of a compact decision aid.

## Last confirmed

2026-04-16 during the simplification pass for issues `#120`, `#115`, `#116`, and `#114`
