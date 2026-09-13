# Everyday use

Start with the repository's tiny bootstrap and canonical `workspace-startup`
skill. It teaches procedure; scoped instructions/config provide policy and domain
owners provide current work and evidence. Ask tools for exact state only when it
matters. An unrelated explanation should need neither a plan nor a proof receipt.

## A scoped repository rule

For example, the following is candidate Markdown for
`.agentic-workspace/instructions/api.md`:

```markdown
---
paths:
  - src/api/**
read:
  - docs/api-contract.md
---
Preserve existing response fields unless the API owner approves a version change.
```

Use the current instruction owner to publish or revise that source; the example
is material, not a forged owner request. `read` names an exact prerequisite.
The other optional fields are `reconcile`, `use`, `checks` and `protect`.
Required checks do not replace semantic review, and a read or skill reference
does not grant permission to modify a protected file.

Say "For this repository everywhere, check the API contract before changing
response fields" to request shared behavior, or "Only in this local repository
environment" for a local instruction. The acting agent routes the correction to
the appropriate owner and verifies publication. A chat promise is not retention.
Local sources must satisfy the owner's local/untracked admission; checked-in
sources carry meaning across checkouts and still require current admission.

## Configuration without protocol copying

Ask the agent to inspect current configuration or change a specific setting.
For example: "Use this repository's supported AW invocation for future tasks."
The agent obtains the current Configuration request, supplies the desired value
and any required bounded human decision, and invokes the exact returned action.
Absent native support is an explicit gap; no historical `config` or `defaults`
command is a fallback. Policy grants, source identity and preserved unknown fields
remain the Configuration owner's responsibility.

## Continue work or receive a worker result

Planning preserves the outcome, constraints, accepted progress, remaining work
and proof obligations. In a fresh checkout, select the current repository owner
and let its returned reconciliation acquire local custody. A copied plan is not
a copied executable action. Missing local evidence and uncertain effects stay
visible; a small finished slice does not finish its parent outcome.

For a selected Assignment, a thin host can hold the exported packet and call
`worker` with `entry`, `expand` or `return` input. The model reads bounded context
and every required lazy input, then supplies only new result material. The host
submits the exact assembled re-entry; Assignment validates current sources and
scope. A worker result never authenticates independent review or grants completion.

## Precise tools

```bash
agentic-workspace --help
agentic-workspace start --target . --task "Inspect the API change constraints" --format json
```

Supply known paths with repeated `--changed`. Fill only the bounded material in
an owner-returned request and pass it through `start --input <request.json>`.
Execute only a returned action with `invoke --input <action.json>`, using the same
current target/task/changed context. Prefer current continuation; after an
uncertain effect, recover through its owner instead of repeating execution.
These are tool affordances for the main skill, not mandatory phases for all work.

See the [generated native tool reference](reference/cli-catalogue.md),
[installation limits](agentic-workspace-install.md), and
[evidence and trust](evidence-and-support.md). Automatic host-native delegation,
provider replacement, general adaptive correction and full Memory/decision
continuity are outside this daily-use preview boundary. No source-checkout result
establishes a published preview or stable/support-bearing release.
