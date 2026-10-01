# Author a repository skill

Use a skill for a reusable method. Start with a short `SKILL.md`; add optional
branching or helper scripts only when they reduce repeated work.

A skill teaches procedure. It does not grant write permission, prove that a check
passed, or replace required review. Binding repository rules belong in
[scoped instructions](scoped-instructions.md).

Follow the
[agent-facing writing guide](../../.agentic-workspace/instructions/agent-facing-style.md):
a fresh reader should know when the method applies, what to inspect, what to do
and when to stop.

## Start with a plain skill

Create `tools/skills/change-note/SKILL.md`:

```markdown
---
name: change-note
description: Draft a change note from an observed patch; never publish it.
---

Compare the patch with the accepted intent. Describe observable changes to public
results, inputs or errors. For an internal refactor, explain the evidence that
public behaviour is preserved. Ask for missing evidence. Return a draft; do not
publish or modify repository state.
```

Ask an agent to read that file and use it on a real patch. A known skill file
needs no extra registry or helper merely to be useful.

Keep repository-owned skills separate from package-managed
`.agentic-workspace/skills/`. Do not edit installed package skills in place.

The [skill specification](../reference/skill-spec.md) defines exact metadata.
Keep `name` aligned with the directory and make the description clear enough for
a host or agent to decide when the skill is relevant.

## Add branches only when the method is genuinely branch-heavy

When a method has substantial alternatives, put the question in a linked
`procedure.md` and keep branch resources inside the skill directory.

Use the existing procedure/registry format rather than inventing executable
conditions. The
[semantic task-route reference](../reference/semantic-task-routes.md) defines the
exact stored fields.

If evidence is insufficient to choose a branch, return an unknown/needs-input
result rather than selecting a convenient default.

## Helpers compute facts; they do not make policy decisions

A skill may include a deterministic helper script. The host still executes it
with ordinary host permissions.

Check that the required runtime is available before execution. Discovering a
helper does not execute it, sandbox it or grant permission to change the
repository.

If the skill needs Planning, Memory, Verification or another AW component to make
a change, use that component's exact returned operation. The skill should not
manufacture another component's write request or approval.

## Repair the skill at its source

Fix malformed metadata, missing resources or unsafe paths in the repository-owned
skill itself, then try it again.

If names collide, use the source-qualified skill returned by the host/AW rather
than relying on registry order.

When evidence changes, reconsider any branch choice that depended on it.

## Regenerate the activation index when using optional activation rules

If the skill uses the existing `agentic-procedure` activation declarations,
regenerate the repository registry after changing them:

```sh
agentic-workspace activation-index --target . --input index-request.json
```

Example input:

```json
{"registry":"tools/skills/REGISTRY.json","mode":"write"}
```

Use `"mode":"check"` in validation and `"mode":"render"` to inspect the proposed
generated registry without writing it. The returned JSON field named
`projection` is an exact API identifier for that generated result.

Commit the generated registry with the procedure source. Do not duplicate the
activation metadata by hand.

The activation index only helps discovery. It does not grant permission, prove
the skill was followed or decide that the user's task is complete.
