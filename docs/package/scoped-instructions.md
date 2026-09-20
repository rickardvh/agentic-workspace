# Scoped repository instructions

Use an instruction for a repository rule, context requirement, evidence obligation
or write protection. Use a skill for a reusable method. A short rule needs no
skill, and an ordinary skill needs no instruction. Optional branch judgements never
change repository policy or satisfy required proof.

This page describes the current native source contract. Check the selected
[release and installation evidence](../agentic-workspace-install.md) before
assuming an older installed artefact supports it. Use your configured AW invocation
in place of `agentic-workspace` below; no historical instruction CLI is required.

For reusable methods, see [skill authoring](skill-authoring.md). Follow the
[customisation walkthrough](../customization.md) to combine them in one task.

## Choose scope and lifetime

Checked-in shared sources live under `.agentic-workspace/instructions/`.
Machine-local sources live under `.agentic-workspace/local/instructions/` and stay
out of version control. Local means local lifetime, not higher authority: it cannot
waive shared protection or substitute for a current shared source admission.

A plain Markdown file has global applicability. A front matter block with `paths`
limits it to matching repository-relative paths. Entries within the list are
alternatives; use forward slashes, without absolute paths or `..`. References are
relative to the repository root, not the instruction directory. The supported
small metadata vocabulary is:

| Field | Observable consequence |
| --- | --- |
| `paths` | Limit applicability by repository-relative glob; omit for global scope. |
| `read` | Supply named context for reasoning; availability does not prove it correct. |
| `governed_by` | Supply exact governing sources and require consistency of the declared consumer scope when either side changes. |
| `reconcile` | Require current consistency judgement for exact canonical files, without compulsory editing. |
| `use` | Prefer an existing replaceable procedure; no guaranteed host activation, effect permission or proof. |
| `checks` | Require current evidence through Verification; `- run: ...` declares a concrete command. |
| `protect` | Restrict writes to matching paths; cannot grant permission elsewhere. |

Use simple inline lists or indented list entries, not general YAML expressions,
nested conditions or powerskill predicates. Unknown keys, malformed lists,
unterminated front matter and unsafe paths remain explicit source problems.
The reader still recognises historical `routes` metadata for compatibility; it
is not an additional preferred public authoring field. Meaning-based skill
selection belongs to procedure, separately from instruction policy.

## Write and inspect a small rule

For a receipt-formatting repository, first create the ordinary context file
`docs/receipt-format.md` with its current public format, for example:

```markdown
# Receipt format

A total is a decimal amount without a currency symbol. Preserve the existing
public representation unless the accepted change explicitly alters it.
```

Then ask the agent:

> Add a shared instruction at `.agentic-workspace/instructions/receipts.md`
> applying to `src/receipt.py`. Read `docs/receipt-format.md` before changing
> public formatting. Prefer the installed `workspace-proof-selection` method
> when choosing evidence. Preserve the accepted formatting intent.

The complete proposed source is:

```markdown
---
paths: [src/receipt.py]
read: [docs/receipt-format.md]
use: [workspace-proof-selection]
---

Preserve the accepted public receipt format. Explain any intended change to it.
```

`workspace-proof-selection` is an existing Workspace bundle after adoption. If it
is absent, report that method gap; the instruction does not manufacture it or
waive any independent obligation. The context file above exists in this setup.

Inspect with the same task and actual changed path:

```sh
agentic-workspace start --target . --task "Change receipt formatting" --changed src/receipt.py --projection full --format json
```

Under `instructions.sources`, the row names its source, `applicable`, guidance,
context and `preferred_procedures` / `procedure_resolution`. Expect this source to
apply and the named procedure to resolve when installed. A context-only source
has `binding_admission.status: not-required`; that does not mean it grants effects.
With `--changed docs/unrelated.md` instead, expect this source's `applicable` to be
false. Do not invent a changed path to obtain a preferred policy result.

For a global version omit `paths`; for a local version choose the local directory.
These are deliberate scope/lifetime choices, not a priority mechanism.

## Publish hard requirements through the owner

Editing a source and admitting its hard consequences are separate. `governed_by`, `reconcile`,
concrete `checks` and `protect` require current instruction admission. A changed
or unadmitted source stays unresolved; copying a hash or advancing a trust revision
by hand is not admission. A current protection is not permission to run a command.

The native authoring path can create or replace one exact shared/local Markdown
source. Ask the agent to present the entire proposed file and the current bounded
instruction-write authorisation question. To drive it directly:

1. Run the `start` command above. Copy its exact
   `instructions.authoring.requests` entry for `instructions/edit-source/v1`.
2. Set only `arguments.source` to the chosen instruction path and
   `arguments.content` to the complete Markdown. Save that returned request as
   `request.json`, then run the same `start` command with `--input request.json`.
3. Inspect the source/postimage and pending `instruction-write-authorization`
   decision. The responsible human supplies `authorize-write` or `defer` in its
   returned response request; return that request through `start --input`.
   An agent must not invent an actor label or answer for the human.
4. If authorised, invoke only the exact returned action with `invoke --target .`
   and the same task/changed context plus `--input action.json`. Re-run `start`.
   Expect a committed effect and current source admission, or retain the owner's
   explicit failure/recovery state. A receipt is not task completion.

No special request schema needs to be authored; preserve all owner-issued fields.
For a crash, use the exact recovery action at the current frontier. Do not repeat
a consumed authorisation, edit managed custody or overwrite a collision.

## Add evidence or protection deliberately

To require consistency with the context file, add
`reconcile: [docs/receipt-format.md]`. A reviewed and still-correct file needs no
edit; the following section explains admission of that judgement.

A separate command example assumes Python is installed. Create `src/receipt.py`:

```python
def format_total(value):
    return str(value)
```

Create `tests/test_receipt.py`:

```python
import unittest
from src.receipt import format_total

class ReceiptTest(unittest.TestCase):
    def test_public_format(self):
        self.assertEqual(format_total(12), "12")
```

For this fixture, the concrete evidence declaration is:

```markdown
---
paths: [src/receipt.py]
checks:
  - run: python -B -m unittest discover -s tests -p test_receipt.py
---

Verify the public receipt format.
```

Publish it through the same instruction owner, then inspect the current
Verification request/action before running and admitting the result. A shell exit
code alone is not admitted proof. Do not add this fixture check to a repository
whose actual test command differs.

A protection-only alternative can declare `protect: [generated/**]`. Do not infer
that combining it with the shell check above is supported just because both parse:
the native owner blocks shell proof when it cannot establish a bounded write scope
preserving current protection. `-B`, an agent's read-only assertion or selecting a
skill does not supply that proof. Keep the contradiction visible and use the
responsible owner's supported evidence/authorization path; do not weaken policy
merely to make the example run.

## Source reconciliation

To make a source govern consumers, name it once in `governed_by`:

```markdown
---
paths: [src/adapters/**]
governed_by: [spec/wire-format.md]
---

Keep adapters consistent with the wire format.
```

Publish this declaration through the instruction owner described above. Adapter
work receives the specification as context; no duplicate `read` entry is needed.
A change to `spec/wire-format.md` discovers the current adapter scope even though
the specification is outside `paths`. Plain `read` never creates this reverse
obligation. Existing `reconcile` continues to check named canonical files against
resulting work.

Inspect `verification.source_reconciliation`: `relation_id` identifies the
declaration, `proposal.work_postimages` names the current group, and `coverage`
shows what remains. Its `material_request` reads at most 16 exact references;
select fewer if the existing byte budget is exceeded. Submit the issued judgement
request after assessing the source and group, then publish with current authority.
A justified no-impact assessment requires no consumer edits. For substantive
impact, edit consumers through their normal owners and obtain a fresh request.

Each declared relationship retains its own authority and coverage. Overlapping
scopes and sources inside their own scope are direct relationships, not recursive
expansion. Unrelated work does not acquire a corpus review. An unadmitted scope
withdrawal remains unresolved until its instruction owner admits the change.

Verification returns an exact material request for applicable `reconcile` sources.
Propose `updated` or `reviewed-current`, with a reason, for each named source:

- `updated`: the work invalidated the source and its normal owner changed it.
- `reviewed-current`: the source was checked against the resulting work and needs
  no change.

Material alone does not admit a judgement. Verification constructs the complete
proposal and a bounded confirm/defer request in the decision packet's pending
decisions. With no current admitted delegated authority for this scope, obtain
the human answer to that exact request. Neither a model assertion nor an actor
label supplies authority. The confirmed basis records the exact request/proposal
and answer, without claiming cryptographically authenticated human identity.
Independent review retains its separate identity and separation-of-duty rules.

Publication uses existing Verification proof/effect custody. Its receipt is
evidence of the bounded answer, not deciding authority or a semantic truth oracle.
It satisfies only the source-reconciliation obligation; other completion checks
remain pending. No source body is copied into a documentation store.

Currentness binds the selected Planning subject when present,
canonical sources, declared context dependencies, admitted instruction content,
relevant work files, the matching decision delegation and producer semantics.
Admission is checked afresh; changing its Git pointer to identical instruction
content preserves accepted coverage. Unrelated configuration and other owners'
capability changes also preserve coverage. Fresh publication requests and actions
still require their current capability envelope and exact authority. Every entry
reobserves the declared file set, including additions made outside AW. An incomplete
caller change list or a quiet event stream cannot prove freshness. Discovery is
bounded; an unsafe or incompletely observed scope remains unresolved for completion.

Large scopes are assessed in groups of at most 64 consumers. The proposal names
the exact group; `coverage` reports total, accepted and pending consumers. Publish
the group, then request the next one. A fresh process can recover accepted groups
from Verification receipts without the original task or conversation. New tasks
still need their own current publication authority. Completion requires coverage
of the entire current set, not a sample or the sum of overlapping groups.

A consumer change invalidates its group; a canonical source or governing policy
change invalidates dependent groups. New consumers require additional coverage.
These observations mean reconsideration, not that every consumer needs editing.

Unresolved obligations are reobserved on Planning-owned continuation. Direct work
does not acquire Planning. Unrelated scoped work has no reconciliation obligation;
`reviewed-current` causes no source edit. Legacy route metadata and maintainer
instruction commands remain migration compatibility, not additional public v1
authoring fields or a second executable authority.
