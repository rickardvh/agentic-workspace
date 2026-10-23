---
name: memory-refresh
description: Reassess selected Memory when relevant sources change; preserve useful lessons while currentness is unresolved.
---

# Reassess advice affected by a change

Use this method when changed repository sources could invalidate advice selected
for the current task. Reuse current `advisory_context` and the source facts already
available. If nothing relevant changed or no advice was selected, stop; neither a
code edit nor a new session requires a Memory refresh or a corpus sweep.

When the changed paths or current Memory disposition are not yet known, resolve
them with the repository's [configured AW invocation](../../../skills/workspace-startup/references/ordinary.md):
`start --target . --task "<actual task>"`, adding `--changed <path>` for each
relevant path. Use the compact result unless missing detail is needed. Inspect
the selected advisory context and any exact returned disposition request.

For a selected lesson whose dependencies changed, follow
[Memory Hygiene](../memory-hygiene/SKILL.md) to assess its evidence and the
supported retain, retire or promotion action. A source hash change alone does
not establish that a lesson is false or that a stronger source accepted it.
Preserve the uncertain lesson until a supported disposition is justified.

If the needed correction is a prose rewrite, routing change or new capture
that the current native owner cannot perform, preserve the smallest useful
finding through its existing owner and state the missing operation. Keep active
work and continuation with Planning, not Memory. Only use
`.agentic-workspace/local/` for scratch when scratch is actually needed.

Stop when selected advice is still justified, its authorised disposition is
confirmed, or the precise unresolved dependency and next action are recorded.
