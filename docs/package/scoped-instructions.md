# Scoped repository instructions

Ask the agent to save a repository rule and show where it applies. The installed,
on-demand [instruction-authoring method](../../.agentic-workspace/skills/workspace-instruction-authoring/SKILL.md)
helps it choose the smallest suitable rule, preview the Markdown, publish through
AW's current write checks and inspect the result. An explicit authoring request
needs no correction event.

Use an instruction for a persistent rule and a [skill](skill-authoring.md) for a
reusable method. A one-off request needs no saved instruction. Revise an adequate
existing rule in place instead of adding a competing copy.

## Choose scope and lifetime separately

Plain Markdown applies repository-wide: use it only for deliberately global
guidance. Front matter can limit a rule to matching repository-relative `paths`,
optionally combined with currently selected semantic `routes`. Both conditions
must hold when both are present. Unresolved route selection is not a proven
non-match.

Shared rules are direct `.md` files under `.agentic-workspace/instructions/`.
Machine-local rules are direct `.md` files under
`.agentic-workspace/local/instructions/`, untracked and ignored by Git. Local
lifetime does not override a shared rule or grant extra permission.

## Source reconciliation

For example, ask:

> For API adapter work, treat our existing API contract as the governing
> specification; leave unrelated work alone. Save this as a shared rule.

Assuming these paths exist in your repository, the instruction can be small:

```markdown
---
paths: [src/adapters/**]
governed_by: [docs/api-contract.md]
---

Keep API adapters consistent with the existing API contract.
```

`governed_by` supplies the contract and requires a current Verification judgement
of the affected adapters. When the contract changes, inspect the returned groups
until every current consumer is covered. An adapter that is still correct needs
no artificial edit. `read` alone supplies context without that obligation.

Inspect matching and unrelated work after publication. The matching work should
receive the rule and its applicable requirements; unrelated work should not.
A successful write does not prove consistency, run a declared check or show that
an agent followed the rule.

## Look up syntax and maintain the rule

The installed [Markdown reference](../../.agentic-workspace/skills/workspace-instruction-authoring/references/format.md)
defines all eight supported fields: `paths`, `routes`, `read`, `governed_by`,
`reconcile`, `use`, `checks` and `protect`. It explains their combinations, exact
list/check forms and limits. This is constrained front matter, not arbitrary YAML.
Add only the consequences the requested rule needs; name the repository's actual
checks and governing sources.

Follow the installed [publication procedure](../../.agentic-workspace/skills/workspace-instruction-authoring/references/publish.md)
for exact authorisation, revision and interrupted-write recovery. Publication is
not a Git commit. Shared rules can travel through normal version control; local
publication records do not transfer trust to another checkout.

The current operation supports creation and revision, not general deletion or
renaming. An unadmitted removal does not erase admitted governance. Removing or
refreshing AW's package support preserves custom instruction files.
