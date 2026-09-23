# Author a repository skill

Use a skill for a reusable method. Start with a short Markdown entry; add optional
branch delivery only when it saves reading. Skills do not grant permission,
admit proof or replace required review. Binding rules belong in
[scoped instructions](scoped-instructions.md).

## Write and try the method

Create `tools/skills/change-note/SKILL.md`:

```markdown
---
name: change-note
description: Draft a change note from an observed patch; never publish it.
---

Compare the patch with its accepted intent. Describe observable changes to
public results, inputs or errors. For an internal refactor, explain the evidence
that public behaviour is preserved. Ask for missing evidence. Return a draft;
do not publish or modify repository state.
```

Ask your agent to read that file and draft a note for a real patch. A known file
needs no registry, route, helper or module. Inspect the draft against the patch;
a skilful-sounding answer is not evidence that the method was followed.

Keep repository bundles separate from package-managed
`.agentic-workspace/skills/`. For host discovery, use that host's supported skill
exposure; a directory alone does not activate a skill. Keep `name` aligned with
the directory and describe when the method applies. Bundle-relative links can
reach references and scripts. The [skill specification](../reference/skill-spec.md)
owns exact metadata. A host may load the entire entry, so keep large alternatives
out of it.

## Add branch delivery only when useful

For a method with substantial alternatives:

1. Put its question in a linked `procedure.md`, with one `agentic-procedure` fence.
   Write natural-language criteria and name each branch's resource.
2. Keep question/context/branch paths relative to and confined inside the bundle.
   Do not use absolute paths, `..` or executable expressions.
3. Add the skill's path, semantic route and procedure resource to the repository
   registry. Remove the row when removing the bundle.
4. Ask the agent to select that route, inspect the question, answer from current
   evidence and request only the selected resource. The same Markdown must work
   when read directly.

The complete [change-note fixture](../../tests/fixtures/change-note/SKILL.md)
demonstrates visible/internal branches without a second tutorial to maintain.
The [semantic route reference](../reference/semantic-task-routes.md) and
[source decision contract](../../src/core/contracts/source_decision_contract.json)
own exact selection/answer fields, limits and currentness. Use returned identities
instead of reconstructing them from an example. Unknown evidence means an unknown
answer, not a default branch. Lost or stale answers require fresh selection or
judgement; a current hash is not semantic truth.

## Keep effects with their owners

An optional helper may calculate facts, but it runs with ordinary host permissions
and cannot decide acceptance or manufacture owner actions. Its declared entrypoint
and dependencies are repository-relative, unlike branch links. Verify runtime
availability before execution; discovery neither executes nor sandboxes it.

For effects, use the current domain owner's exact supported request/action. See
the existing [delegation method](../../tools/skills/delegation-handoff/SKILL.md)
and [review method](../../tools/skills/pr-review-recheck/SKILL.md) for bounded
compositions. Their policy, independence and proof requirements survive skill
replacement or removal. A method's answer cannot approve its own implementation.

## Repair the source and retry

Correct malformed declarations, missing files or unsafe paths in the named bundle,
then repeat the selected read. If route names collide, choose the returned
qualified source or clarify the intended meaning; registry order is not authority.
When evidence changes, reconsider the dependent answer. When the runtime is
unavailable, read the same Markdown and leave owner effects or proof unresolved.

Replace a package method with a distinct repository-owned skill and deliberately
update the preference through its source owner. Do not edit installed package
bodies or treat local exposure as an override of shared policy. Durable unfinished
work stays with its existing continuation owner, not a new state file in the skill.

## Publish situation-driven activation

Keep optional activation declarations in the existing `agentic-procedure` source.
After adding, removing or changing a declaration, derive the registry projection
with the installed executable (no source checkout or maintainer Python required):

```sh
agentic-workspace activation-index --target . --input index-request.json
```

Use this JSON input, changing the repository-relative registry path as needed:

```json
{"registry":"tools/skills/REGISTRY.json","mode":"write"}
```

Commit the generated registry with the procedure source. In authoring checks, use
`"mode":"check"`; stale membership or declarations exit nonzero without mutation.
This explicit pass inspects every declared procedure, including those absent from
the previous index. Run it before exercising or publishing edited skills. Ordinary
operating lookup remains lazy and cannot detect newly relevant unindexed sources;
it validates only entries selected by the compact index. Never duplicate activation
metadata by hand. The command changes only the named registry's derived index,
retaining its other fields; it grants no procedure, policy or outcome authority.
