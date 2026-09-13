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

For delegation, ask for a bounded result and name its constraints. Repository
policy can attach provider-neutral requirements to a semantic route; local
configuration supplies available targets and transports. Assignment applies
eligibility before preferences or cost. A configured process can return read-only
material or an unapplied patch; the Codex app-server bridge supports read-only
material. The responsible owner
must still admit the return, integrate any patch, and establish the required proof.
Manual export remains a valid outcome when automatic execution is unavailable.
See the [transport boundaries](maintainer/consequential-delegation.md) before
configuring a host; credentials and current provider availability stay local.

## Preserve a useful lesson or decision

Ask to retain an observation only when it will help future work. Memory can store
one advisory lesson with its rationale and dependencies. A relevant later task
can read it; changed dependencies require reconsideration. A note is neither a
governing decision nor proof that its advice is still correct. Choosing no
retention creates no archive record.

A settled material decision belongs in the repository's admitted decision
convention when one exists, with Memory supplying fallback custody otherwise.
The deciding authority is separate from who wrote or published the text.
Corrections should update the strongest appropriate owner: instructions for
future behavior, a decision for settled policy, a fact's source for a factual
error, or code/procedure for a defect. A related file alone does not establish
that a correction is already covered.

## Improve a method within current authority

Material friction can justify one bounded change through the receiving owner.
Repository opportunity proposals also respect `workspace.improvement_latitude`:
`none`/`reporting` allow reporting, `conservative`/`balanced` permit proposals
within current work, and `proactive` permits proactive proposals. These settings
never grant mutation authority. The owner still applies its current write
authorization, protection, validation and recovery rules. Reporting or declining
creates no improvement backlog or mandatory reflection step.

## Read with repository access only

An agent without an executable runtime starts from the same canonical skill and
its `.agentic-workspace/READING.json` profile. It selects the relevant existing
owner refs, reads those sources, and binds observations to repository/blob
identities. This can recover intended work, constraints, recorded progress and
relevant advice without searching all historical state.

The profile cannot establish machine-local selection, provider readiness, fresh
proof or permission to act. An absent or stale profile permits only directly
observed repository facts until the named source is reconciled. It is not a
read-only runtime or a substitute for independent review.

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
[evidence and trust](evidence-and-support.md). This page describes the reconstruction
source capability set. An earlier published preview may not contain these later
additions; use the documentation and receipts for the exact version installed.
No source-checkout result establishes a published preview or stable/support-bearing
release. API/JSON-file transports, autonomous improvement queues and runtime
authority from static reads are not claimed capabilities.
