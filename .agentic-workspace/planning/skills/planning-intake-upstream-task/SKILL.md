---
name: planning-intake-upstream-task
description: Turn an externally tracked task into checked-in planning without making the upstream tracker the execution authority.
---

# Planning Intake Upstream Task

Planning Intake Upstream Task converts an upstream issue, ticket, or task into the repo's checked-in planning surfaces.

It exists to keep external trackers as intent authorities while preserving execution custody in bounded execplan, lane, decomposition, and issue-relation records.

## Use When

- a GitHub issue, Linear ticket, Jira task, Notion task, or internal task note should become checked-in planning
- the repo needs a tracker-agnostic intake path
- an agent should preserve source metadata without copying the whole upstream thread into planning

## Do Not Use When

- the task already has a selected, live execplan owner
- the work is a bounded review pass rather than an accepted planning item
- the real need is durable subsystem knowledge rather than active or candidate planning

## Workflow

1. Read the startup skill and use current native `start` for the task. Inspect its
   applicable instructions and Planning relation/posture before deciding whether
   durable continuity is useful. When available, the shared executable
   `.agentic-workspace/skills/workspace-intent-discovery/prepare.py` with
   `--procedure planning --judgment clear` prepares those current inputs. It creates
   nothing. No runtime means source-reading only; use `READING.json` and the named
   owner record without inferring custody.
2. Read the upstream task or issue that is being ingested.
3. Normalize it into a compact summary:
   - source system
   - source identifier or URL
   - title
   - problem summary
   - product-first reasoning when relevant
4. Decide the smallest correct routing target:
   - dismiss
   - `.agentic-workspace/planning/reviews/`
   - external intent evidence only
   - a bounded lane or decomposition record
   - an execplan plus an issue-relation record when execution custody is accepted
5. Preserve the upstream source reference in the chosen planning surface.
6. If Planning is warranted, submit the current `planning.creation_requests` or
   selected-owner update request through native `start`/`invoke`. Keep milestone,
   continuation, dependencies, proof and risk/invariant facts with that owner.
   An incumbent selection alone does not establish the current task relation.
   Direct work needs no plan. Never infer a numeric threshold or automatic
   creation rule from the task title.

## Output Expectations

Report:

- upstream source used
- chosen planning destination
- files updated
- whether the work stayed inactive or became active

If the task becomes active planned work, ensure the execplan includes an `## Intake Source` section with compact source metadata.

## Guardrails

- Keep the contract tracker-agnostic even when the current intake source is GitHub.
- Do not treat the upstream tracker as the source of truth after promotion.
- Do not paste full issue bodies into bounded planning records.
- Prefer one-paragraph normalized summaries over copied tracker prose.
