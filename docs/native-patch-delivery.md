# Native process patch delivery

Ordinary Assignment can select a configured, currently observed process for an
`unapplied-patch` result. Automatic transport still requires current admitted
policy and executable/safety facts. A configured native-host label does not make
a host adapter constructible.

The owner returns the input-completeness, export, dispatch, result-admission and
integration requests. Consume those exact requests through ordinary `start` and
`invoke`; do not reconstruct their revisions or substitute caller authority.
The sealed packet carries the complete return identity and public re-entry.

## Mutation subject

The acting orchestrator selects at most eight input references, including each
concrete `mutation_paths` entry. The owner captures their existing UTF-8 contents
and revisions before dispatch. Mutation paths must match the allowed scope
patterns. Patterns themselves are never changed-file subjects.

The worker returns `result_delivery: "unapplied-patch"`. Its `patch` string is a
JSON-encoded array of file deltas, for example:

```json
[{"path":"src/example.txt","diff":"--- original\n+++ modified\n@@ -2 +2 @@\n-old\n+new\n"}]
```

Each element contains only `path` and `diff`. Diffs use canonical unified headers
`original` and `modified`, exact old and new hunk positions, and no Git metadata
or trailing material. `changed_paths` must equal the concrete delta paths.
LF and CRLF transport are equivalent. The returned delta applies to the sealed
baseline, including any dirty content captured there, rather than the branch's
cumulative changes. It cannot contain an unrelated pre-existing change merely
because that change lies in the allowed scope.

The current process reader accepts at most 65,536 bytes of complete stdout;
truncated output cannot become an admitted return. The packet states this limit.
Captured inputs and combined baseline/postimage delta text are additionally
bounded to 262,144 bytes. The complete escaped integration recovery carrier must
fit the native source reader before an integration attempt is admitted.

## Admission and integration

The supported enforcement boundary is the shared Rust `start`/`invoke` boundary
used by native, Python, TypeScript and JSON clients. It mechanically gates native
patch integration and preserves required Assignment restrictions during
Verification claim re-entry, including generic `complete` and `pr-complete`
claims. A successful check or exact claim judgement cannot discharge an unresolved
Assignment. Runtime failure, a stale request, or an unavailable required transport
does not supply permission to continue locally.

With binding Assignment, `task_requirements.implementation_admission` projects
the current owner state:

| Status | Meaning |
| --- | --- |
| `assessment-required` | Current comparison/admission is missing or unresolved. Follow the Assignment recovery requests. |
| `admitted-local` | Current retained-local continuation is valid; no worker dispatch is required. |
| `admitted-nonlocal` | Follow only the selected Assignment's exact handoff/transport envelope; this is not local implementation permission. |
| `returned-unadmitted` | A returned result or declared `already-materialized` work has no admitted result use. Assignment restricts implementation and completion claims even after a later local choice. Existing bytes and proof cannot establish admission. |
| `returned-admitted` | The result owner admits the exact observed result. Patch integration and Verification retain their separate requirements. |

This status creates no new session history or Assignment ledger. A current local
choice does not authenticate earlier externally performed implementation:
`historical_compliance` remains `not-established`. A host reporting already-produced
work must preserve that result class through the existing task-requirements
request. Arbitrary editor, shell and Git actions remain outside mechanical
control; callers that conceal those actions cannot claim AW enforced them.
Unsupported materialised returns require current owner re-resolution or a new
supported captured-baseline patch journey; they cannot be relabelled into proof
of prior compliance. No implicit override or retired reassignment command is
provided.

Configured `supports_internal_delegation` alone does not make nonlocal dispatch
constructible. Current execution configuration reports the actual process or
adapter boundary and its gaps. Binding best-fit comparison preserves unbound
internal workers as unresolved alternatives. Configure a concrete supported
transport in the machine-local source; the sealed Codex bridge binds current
installed-protocol/model capability to the candidate and rechecks it at dispatch.
See [consequential delegation](maintainer/consequential-delegation.md).
Unknown visibility, persistence, resume and
cleanup guarantees remain unknown; read-only discovery creates no provider work.
Direct work without an Assignment requirement gains no admission procedure.

Process output is an unproven observation. Assignment's current `use-result`
judgement admits that exact returned result. Integration then constructs a new
proposal against current file contents, retaining disjoint concurrent edits and
uniform current line endings. Divergent overlap requires repair. An identical
already-present delta requires no repeated file write.

Only the captured mutation baseline is historical during return admission.
Independent input dependencies, work, policy, capability and other owner sources
are re-observed. Changed authority stales the return or integration before effect.
Root `.agentic-workspace` sources/custody and Git metadata cannot be mutated by
this operation; their dedicated owners retain authority.

A checkout-wide native patch lock serialises integrations. Exact retained
producer custody and before/postimages allow interrupted publication to resume
without running the worker again. Unknown temporaries, changed postimages and
unrecognised lock contents are preserved. The result's public re-entry exposes
typed integration evidence to Assignment and Planning; Planning adoption of a
patch result waits for current integration. Verification remains responsible for
proof and its current concrete subject. Neither worker success, result judgement,
publication custody nor integration grants proof or parent completion.

After Planning retains the integrated result, a current native Verification check
can nominate one bounded target outcome. Its checked sources must include the
exact retained Planning document and every integrated postimage. Partial checks,
failed/stale receipts and later source changes cannot supply that outcome. The
observation is context for the same role and delivery class among currently
eligible configurations; it neither selects a target nor changes eligibility.
This sparse owner projection adds no outcome store or general target ranking.
Failure/repair history, compaction and broader learning under #2209 remain open.

## Remaining transport boundaries

This process adapter gives the worker nonmutation instructions; it does not
provide OS isolation or prove who physically wrote existing checkout bytes.
Acceptance of an identical existing delta establishes its presence, not authorship
of the dirty state. Declared `already-materialized` delivery is not supported.

This slice covers modifications to existing UTF-8 files. File creation/deletion,
renames, binary changes, native-host launch/return, worker visibility/retention
guarantees and real supported-host dogfood remain separate unfinished portions of
#2947/#2817/#2210. This path does not establish their completion.
