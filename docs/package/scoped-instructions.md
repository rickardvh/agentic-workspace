# Scoped repository instructions

Use an instruction for a repository rule. Use a skill for a reusable method.

Shared instructions live under `.agentic-workspace/instructions/`. Machine-local
instructions live under `.agentic-workspace/local/instructions/` and should stay
out of version control.

## Choose where the rule applies

A plain Markdown file applies repository-wide. Front matter can limit it to
matching repository-relative paths:

```markdown
---
paths: [src/api/**]
read: [docs/api-contract.md]
---

Preserve existing public response fields unless the accepted API change says
otherwise.
```

The common fields are:

| Field | Meaning |
| --- | --- |
| `paths` | Apply the instruction only to matching repository paths |
| `read` | Supply named files as context |
| `governed_by` | Say that another source defines the rule this instruction implements |
| `reconcile` | Require the named files to be checked for consistency |
| `use` | Prefer an existing skill when the task matches |
| `checks` | Require evidence through Verification; `- run: ...` names a command |
| `protect` | Restrict writes to matching paths |

The [generated instruction reference](../reference/instruction-clause-program.md)
defines exact field formats and limits.

A local instruction has local lifetime only. It does not override a shared rule or
grant extra permission.

## Create or change an instruction

Ask the agent for the rule you want and the scope where it should apply. The agent
should show the proposed Markdown before writing it.

When driving the native API directly:

1. call `start` for the real repository, task and changed paths;
2. use the exact returned `instructions/edit-source/v1` request;
3. set only the source path and complete Markdown content the request asks for;
4. submit the returned request through `start`;
5. if AW returns an allowed action, pass that exact action to `invoke`;
6. call `start` again if the next step depends on the changed instruction.

Do not invent write-capable request fields from examples. A returned request or
successful read does not itself permit a write.

If an interrupted write may already have happened, use AW's returned recovery
information before trying it again.

## Require a check only when the repository really uses it

Example:

```markdown
---
paths: [src/receipt.py]
checks:
  - run: python -B -m unittest discover -s tests -p test_receipt.py
---

Verify the public receipt format.
```

Do not copy this command into a repository with a different test setup.

A successful process exit is evidence only for the check that actually ran.
Verification records whether that evidence satisfies the repository requirement.

## Protect files deliberately

A rule such as:

```markdown
---
protect: [generated/**]
---

Do not edit generated files directly.
```

restricts writes to those paths. It does not grant permission elsewhere.

If a requested check cannot run without violating an active protection, keep the
conflict visible and use the repository's supported check or update path. Do not
weaken the rule merely to make an example pass.

## Keep consumers consistent with a source document

Use `governed_by` when a named document defines behaviour that other files must
follow:

```markdown
---
paths: [src/adapters/**]
governed_by: [spec/wire-format.md]
---

Keep adapters consistent with the wire format.
```

When the specification changes, Verification can identify the affected adapter
group and ask for a judgement such as `updated` or `reviewed-current`.

A file that is still correct needs no artificial edit. If the specification
really changes behaviour, update the affected consumers through their normal
project workflow and then record the new result.

Large consumer sets may be checked in groups. Completion requires every current
consumer to be accounted for, not a sample.

## Keep instructions simple

Do not turn instruction front matter into a second programming language. Use only
the supported fields, keep paths repository-relative, and prefer a short rule plus
a link to the real source over copied policy.

For reusable methods, see [Author a repository skill](skill-authoring.md).
