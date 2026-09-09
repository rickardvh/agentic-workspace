# Scoped repository instructions

Put Markdown in `.agentic-workspace/instructions/`. A plain Markdown file applies
globally. Add `paths` when scoped; optionally add `read`, `reconcile`, `use`,
`checks`, or `protect`.

```markdown
---
paths:
  - src/auth/**
read:
  - docs/security/authentication.md
reconcile:
  - docs/reference/authentication.md
  - contracts/token-format.json
use:
  - security-review
checks:
  - run: pytest tests/auth -q
protect:
  - generated/**
---

Preserve compatibility with existing tokens. Never log raw credentials.
```

`paths` contains repository-relative globs; multiple entries are alternatives.
`read` names context relevant during reasoning. `reconcile` names exact canonical
files whose consistency with the resulting work must be judged before completion.
It can name documentation, configuration, a data contract, or another canonical
source. It does not require editing that source.

`use` prefers an existing procedure and preserves its authority. `checks` requires
current evidence through Verification. `protect` restricts writes. The instruction
source cannot grant execution or deciding authority. Hard obligations require the
current repository instruction admission; a changed or unadmitted declaration
cannot silently inherit the former admission.

Use the configured native AW invocation with `start --target . --task "..."
--changed src/auth/token.py --format json`. The public result distinguishes context,
pending source reconciliation, proof obligations, and protections. Supply only
the bounded material or answer requested by the owner, resolve again, and execute
only the exact returned action with `invoke` and the same context.

## Source reconciliation

Verification returns an exact material request for applicable `reconcile` sources.
Propose `updated` or `reviewed-current`, with a reason, for each named source:

- `updated`: the work invalidated the source and its normal owner changed it.
- `reviewed-current`: the source was checked against the resulting work and needs
  no change.

Material alone does not admit a judgment. Verification constructs the complete
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

Currentness binds the current work, selected Planning subject when present,
canonical sources, declared context dependencies, applicable instruction
admission, relevant work files, policy and capability revisions. Every entry
reobserves the declared file set, including additions made outside AW. An incomplete
caller change list or a quiet event stream cannot prove freshness. Discovery is
bounded; a scope too large or unsafe to observe remains unresolved for completion.

Unresolved obligations are reobserved on Planning-owned continuation. Direct work
does not acquire Planning. Unrelated scoped work has no reconciliation obligation;
`reviewed-current` causes no source edit. Legacy route metadata and maintainer
instruction commands remain migration compatibility, not additional public v1
authoring fields or a second executable authority.
