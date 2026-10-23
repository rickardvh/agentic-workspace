---
name: planning-reporting
description: Report selected Planning progress, next steps and restrictions from current sources.
---

# Report current Planning work

Use when asked for the status of a selected plan or unfinished task. Reuse the
current `planning_context` and already-delivered Planning detail when they cover
the question and their sources remain current. Do not start another AW operation
merely to produce a report.

When the needed owner identity or progress is missing or stale, use the
[configured invocation](../../../skills/workspace-startup/references/ordinary.md)
with `start --target <repo> --task "<actual task>"` and any known relevant
changed paths. Follow only the returned Planning detail references needed
for this question, using the same work context. Do not scan all plans or
reconstruct retired summary fields.

Report the selected work, accepted progress, next action, real restrictions and
source references. Distinguish an empty current selection from missing or
ambiguous custody. Read exact source records only to resolve a material gap;
recorded status alone does not prove live currentness or completion.

Use `planning-closeout-trust` for intent/closure judgment and `planning-work`
for structure or continuation. Use current Verification evidence or
`workspace-proof-selection` for proof. Reporting grants no write, proof,
independent-review or completion authority.
