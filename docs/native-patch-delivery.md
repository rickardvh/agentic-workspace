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

Process output is an unproven observation. Assignment's current `use-result`
judgment admits that exact returned result. Integration then constructs a new
proposal against current file contents, retaining disjoint concurrent edits and
uniform current line endings. Divergent overlap requires repair. An identical
already-present delta requires no repeated file write.

Only the captured mutation baseline is historical during return admission.
Independent input dependencies, work, policy, capability and other owner sources
are re-observed. Changed authority stales the return or integration before effect.
Root `.agentic-workspace` sources/custody and Git metadata cannot be mutated by
this operation; their dedicated owners retain authority.

A checkout-wide native patch lock serializes integrations. Exact retained
producer custody and before/postimages allow interrupted publication to resume
without running the worker again. Unknown temporaries, changed postimages and
unrecognized lock contents are preserved. The result's public re-entry exposes
typed integration evidence to Assignment and Planning; Planning adoption of a
patch result waits for current integration. Verification remains responsible for
proof and its current concrete subject. Neither worker success, result judgment,
publication custody nor integration grants proof or parent completion.

## Remaining transport boundaries

This process adapter gives the worker nonmutation instructions; it does not
provide OS isolation or prove who physically wrote existing checkout bytes.
Acceptance of an identical existing delta establishes its presence, not authorship
of the dirty state. Declared `already-materialized` delivery is not supported.

This slice covers modifications to existing UTF-8 files. File creation/deletion,
renames, binary changes, native-host launch/return, worker visibility/retention
guarantees and real supported-host dogfood remain separate unfinished portions of
#2947/#2817/#2210. This path does not establish their completion.
