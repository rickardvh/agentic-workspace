# Start with one ordinary skill

When a reusable method is needed, inspect the repository's skill tree and any
method already serving the same job. Edit that source, or create one directory
whose `SKILL.md` starts with `name` and `description` in YAML front matter. Keep
the name aligned with its directory and the description useful for selection.

For example, `tools/skills/change-note/SKILL.md` may contain:

```markdown
---
name: change-note
description: Draft a change note from an observed patch; never publish it.
---

Compare the patch with the accepted intent. Describe changes to public results,
inputs or errors. For an internal refactor, explain the evidence that public
behaviour is preserved. Ask for missing evidence. Return a draft.
```

Keep the entry small. Put substantial alternatives or lookup material in files
inside the same bundle and link them relative to `SKILL.md`. Explain when to read
each link; do not make a reader load every reference to find the first step.
State any runtime prerequisite where it becomes necessary. Follow
[the writing guide](writing.md) for applicability, concrete actions and endings.

Ask the intended consumer to read the exact file and use it on one real or neutral
task. Confirm it can identify the next action and stop condition from those files.
Check a relevant missing-evidence case and an unrelated task that should not use
the method. Metadata and link checks establish structure, not comprehension.

Stop here when this shape suffices. A directly read ordinary skill needs no AW
registry, semantic question, helper or package adoption. Host-native discovery is
optional and host-specific; use [maintenance and exposure](maintain.md) only when
the requested consumer needs it.
