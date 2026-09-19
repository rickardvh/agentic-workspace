# Customize how an agent works in your repository

Suppose your project formats receipts. You want changes to preserve the accepted
public format, and you want a useful change note when the behavior changes.
One repository rule and one small reusable method can express that intent.
Neither requires a new module or a mandatory workflow.

Choose only what the task needs:

| Need | Mechanism |
| --- | --- |
| Preserve the public format, read its contract, require evidence or protect files | A scoped instruction; use config for an existing setting. |
| Reuse a method for drafting a change note | An ordinary skill. |
| Ask a meaning-based question and deliver its relevant branch | Optional AW procedure resources in that same skill. |
| Compute a deterministic comparison | An optional script/helper, with normal execution permissions. |
| Supply a new independently owned domain fact or operation | A module capability, even if entirely read-only. |

The examples describe the current source stack. Use the selected
[release's installation evidence](agentic-workspace-install.md) for artifact
availability; a source example is not a stable-release support claim.

## Preserve the receipt format

Ask the agent:

> Create `docs/receipt-format.md` recording that a total is a decimal amount
> without a currency symbol. Add a shared instruction for `src/receipt.py` to
> read that contract and preserve the accepted public format. Show me the
> proposed source and any current owner decision before publication.

Use the complete setup and inspection command in the
[instruction reference](package/scoped-instructions.md#write-and-inspect-a-small-rule).
It creates both the context and rule, and shows the expected applicable source.
Repeat with an unrelated changed path: the scoped rule should be inapplicable.
Choose `.agentic-workspace/local/instructions/` only for machine-local lifetime;
it does not override shared policy. Add checks, protection or canonical-source
reconciliation only when needed, through their current source owner. A skill
preference does not satisfy any of those requirements.

## Draft the note with a small skill

Create the [ordinary change-note skill](package/skill-authoring.md#start-with-an-ordinary-skill)
under your repository-owned `tools/skills/`. Then ask:

> Read `tools/skills/change-note/SKILL.md`. Compare the patch and accepted intent,
> and draft the appropriate change note. Do not publish it.

For a small task that can be enough. The agent reads the patch with ordinary tools
and returns a draft. A refactor that preserves public output gets an internal
description rather than an invented user-facing change. No AW call is required
solely to write that draft.

For longer alternatives, use the reference's
[same-source question and branches](package/skill-authoring.md#add-a-semantic-question-without-custom-code).
Its small entrypoint links to the visibility question and two leaf resources.
Ordinary readers follow those same links; the AW path adds current qualified
selection and answer carriage. These are composable facilities, not a second
incompatible skill format. A host may load all of the selected entrypoint; keeping
large alternatives outside it permits lazy delivery. Host discovery/exposure
must be checked separately from AW's selected reads.

## Try the question and inspect its consequence

After adding the reference's registry row, ask:

> Select `example/change-note` for “Draft a note for a total-format change”. Show
> its source, current question and alternatives. Explain what each answer changes
> before choosing. Use only the observed patch and accepted intent.

The [concrete command sequence](package/skill-authoring.md#try-inspect-and-answer)
starts with ordinary `start`, returns the exact discovery/selection requests and
shows `procedure` detail. The question is:

> Does the observed change alter behavior visible to a user?

The alternatives are public behavior changes (`visible`, leading to
`user-note.md`) and behavior preserved (`internal`, leading to `internal-note.md`).
The source and revision explain where that question comes from. Its consequence
is which drafting instruction is delivered, not whether the patch is authorized
or correct. This is the answer to “why am I being asked this?”, without requesting
hidden model reasoning or studying internal packets.

With no observed patch, the agent should return `unknown`, identify the missing
evidence and receive no next branch. Now supply an accepted intent to add the
currency symbol and observed before/after output: `format_total(12)` changes from
`"12"` to `"$12"`. The semantic judgment is `visible`; only the user-note resource
is delivered. A resulting draft is:

> Receipt totals now include the dollar symbol: for example, $12 instead of 12.
> No user action is required.

Bind relied-upon evidence as described in
[currentness and handoff](package/skill-authoring.md#keep-meaning-and-currentness-separate).
Unchanged re-entry can reuse a current answer. If the patch instead becomes an
internal refactor preserving `"12"`, a retained evidence-bound answer becomes
stale. Reconsider it, select `internal`, and explain what establishes unchanged
public behavior. Do not re-use a favorable branch across changed evidence or
silently substitute another same-content skill.

The [integration walkthrough](reviews/powerskill-p1-integration.md) exercised
these outcomes and records its costs and limits. It does not claim this tiny
draft task is cheaper with native coordination. Use AW delivery where current
identity and selective navigation earn the extra calls.

## Add computation only when it helps

The optional [comparison helper](package/skill-authoring.md#an-optional-deterministic-helper)
reports before/after strings and equality. It has no role in choosing whether
the change is acceptable. Selected discovery observes its declared material
without executing it; the host must establish Python availability and normal
execution authority. Its JSON result is data, not an action to run.

This receipt method still needs no module. A contrasting capability would be an
independently owned receipt-schema service that reports the current supported
currency formats with its own source revision and availability. Even a facts-only
read-only owner can justify a module. If it also publishes schemas, those effects
need explicit owner operations and admission. Persistence, script size and branch
count are not the deciding boundary. See [modules](package/modules.md) and the
[extension boundary](extension-boundary.md) for that separate authoring task.

## Maintain one method and keep authority intact

Keep your custom skill in repository-owned sources. Update or remove its registry
row and bundle together, and reobserve selected detail after editing. Qualify
colliding sources instead of relying on implicit precedence. Package-managed
skills follow package adoption/update/removal; do not customize them in place.
The [authoring reference](package/skill-authoring.md#customize-and-repair) owns the
exact identity, repair and replacement rules.

Without AW, an ordinary agent can read the same question, inspect the patch and
draft the note with available tools. If a selected fragment requires a current
owner result—for example publishing admitted proof—that step remains unavailable
without its runtime and authority. Never edit managed state as a fallback. Skill
selection, helper output and branch hashes cannot waive policy, independent review,
human decisions or evidence requirements. Direct unrelated work remains direct.
