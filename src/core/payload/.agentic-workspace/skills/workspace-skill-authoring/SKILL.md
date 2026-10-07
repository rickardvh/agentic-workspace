---
name: workspace-skill-authoring
description: Create, change, replace or remove the smallest useful repository-owned skill; add AW routing or helpers only when needed.
---

# Author a repository method

Use this method when asked to preserve or maintain a reusable repository method.
Inspect the accepted task and existing skills first. Improve the existing method
when it already covers the job; a repeated action alone does not justify another
skill. Repository instructions set policy; a skill explains how to do the work.

Start with [a plain skill](references/plain.md). It needs no AW registry, semantic
question or helper. Keep repository-owned files in the repository's normal skill
tree, such as `tools/skills/`, outside package-managed `.agentic-workspace/skills/`.

For a known need, read only its reference, or select [the question](procedure.md):

- [Add substantial branches and current source checks](references/structured.md).
- [Declare an optional deterministic helper](references/helpers.md).
- [Maintain, qualify, replace, remove or expose the method](references/maintain.md).

Apply the [canonical agent-facing writing guide](references/writing.md) to the
text you change: a fresh reader needs the job, observable facts, action and stop
condition. Verify the result from files available to its intended consumer.
Stop when that consumer can select and use the requested method and any replaced
method no longer competes with it. Report an unavailable host capability or
missing fact beside the affected step; discovery grants no execution permission.
