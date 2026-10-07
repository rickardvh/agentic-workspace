# Author a repository skill

Use a skill for a reusable method. AW ships the on-demand
[skill-authoring procedure](../../.agentic-workspace/skills/workspace-skill-authoring/SKILL.md)
with installed repositories. That bundle is the maintained authoring method;
this page is its human-facing entry. It follows the canonical
[agent-facing writing guide](../../.agentic-workspace/instructions/agent-facing-style.md).

Start with [one plain `SKILL.md`](../../.agentic-workspace/skills/workspace-skill-authoring/references/plain.md)
in the repository's normal skill tree, such as `tools/skills/`. An ordinary skill
needs no AW registry, semantic question or helper. Ask its intended consumer to
read the exact file and use it. Host-native discovery is optional and depends on
the host.

Add only the help the method needs:

- [Structured branches and current source checks](../../.agentic-workspace/skills/workspace-skill-authoring/references/structured.md)
  use the existing `agentic-workspace/procedure/v1` contract. Native `start` with
  its returned discovery request resolves a bundle and its selected resources outside
  `.agentic-workspace/`, without a per-skill core change.
- [Deterministic helpers](../../.agentic-workspace/skills/workspace-skill-authoring/references/helpers.md)
  use the existing executable-affordance declaration. Discovery identifies
  entrypoints and dependencies; ordinary host execution establishes runtime
  availability and permission.
- [Maintenance and exposure](../../.agentic-workspace/skills/workspace-skill-authoring/references/maintain.md)
  cover qualification, merging, replacement and removal. Configuration owns
  package adoption/exposure; repository-owned custom skills stay distinct.

The public [procedure schema reference](../reference/procedure-resource.md) and
[executable declaration reference](../reference/executable-affordance.md) describe
the exact contracts. Identical schemas ship in the authoring bundle, so an
installed consumer can author and validate without this source checkout.
Native resolution adds source identity, resource diagnostics and confinement
checks; the procedure explains its supported commands and inputs.

A skill teaches procedure. It grants no write permission, proof success or review
approval. Binding repository rules belong in [scoped instructions](scoped-instructions.md);
domain changes still use the responsible component's exact current operation.
