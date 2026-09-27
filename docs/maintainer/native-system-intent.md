# Native system-intent sources

The native owner consumes configured `system_intent.sources` and
`preferred_source`, plus an existing `.agentic-workspace/system-intent/intent.toml`.
Read-only resolution never refreshes an intent mirror. A compact view lists
exact source identities and retained interpretation currentness; source bodies and
interpreted fields are returned only through the owner-provided
`system-intent/read-current-source/v1` request. The shared public request envelope
binds each read to the current task, source and capability revisions.

The original governing source remains authoritative for acting-agent judgement.
Its summary, governing/anti-intents, decision tests and recorded review fields are
not promoted into machine proof or human acceptance. Current source hashes do not
prove the interpretation correct. Missing or unreadable governing sources and
invalid, stale or unreviewed retained interpretation remain explicit owner gaps.
Read requests can still expose preserved content for diagnosis; reading cannot
clear these gaps. References outside the current source set and stale requests
are rejected, including changes observed during the bounded read.

Planning retains active work and existing `intent_continuity`; a typed native
update for newly judged larger-outcome alignment is still missing. This source
reader does not close that gap or infer alignment from task words. Generic README
presence in an unconfigured repository does not activate this owner. No new
source taxonomy, intent store, acceptance flag or arbitrary-file reader exists.

## Retained interpretation reconciliation

A stale, invalid or unreviewed interpretation exposes
`system_intent.reconciliation.requests`. Read every governing source and the
retained interpretation using their exact read requests. Supply the complete
proposed TOML, a `faithful` or `revised` semantic judgement, and the reason for that
judgement through `system-intent/edit-source/v1`. `unresolved` preserves the gap.
The proposed `source_records` must match the declared sources (historical
universal-newline SHA-256 format). Each governing entry in `system_intent.sources`
exposes a `source_record` containing its current `path`, `present` and `sha256`.
Use that record after review. `source_record_scheme` is `universal-newline-utf8`:
decode UTF-8, replace CRLF and lone CR with LF, then hash the UTF-8 bytes. The
record's hex digest has no `sha256:` prefix. Its identity is equal for otherwise
identical LF and CRLF text, including on Windows.

The entry's separate `revision` uses `revision_scheme = "raw-bytes"` and includes
the `sha256:` prefix. Read requests and effect bindings use this raw identity,
so a line-ending change still invalidates a previously issued request or action.
Do not copy its digest into a source record. Mismatch diagnostics identify the
source-record path and field without printing source contents. An unavailable
UTF-8 identity cannot supply a current record.

Constructing these records is bookkeeping
**after** semantic review, never the judgement itself. Preserve useful human-owned
why, unresolved questions and extension fields when revising the interpretation.

The returned proposal exposes before/after material and binds raw governing
bytes, the old interpretation, configuration and capability identities. Its
exact response request accepts `authorize-write` or `defer`; without acceptance
there is no effect. Invoke the returned action to publish only
`.agentic-workspace/system-intent/intent.toml`. Scoped protection still applies.
Source, policy or proposed-content changes invalidate the dependent answer/action.
No Git HEAD, timestamp, source-read success or digest comparison supplies semantic
acceptance. The owner validates structural currentness, not the truth of an
agent's judgement or authority beyond the accepted exact owner answer.

Publication uses shared authenticated attempt custody, a bounded preparation
marker and atomic source replacement. An interrupted final outcome exposes an
exact recovery request; recovery confirms existing bytes and cannot republish or
accept changed governing sources. A fresh read clears only source-currentness and
recorded-review gaps. Planning alignment and task completion remain separate.
Unchanged sources are quiet, including across unrelated Git commits. No new intent
store, workflow ledger or automatic mirror refresh is introduced. Without runtime,
readers can inspect checked-in sources but cannot establish live acceptance,
currentness or mutation authority.


System Intent and Verification share native dependency observations and exact
basis comparison. Interpretation records retain their historical newline-normalised
text scheme; current read and effect bindings use raw bytes. A source change
requires reconsidering the interpretation, while a changed governing guide requires
reassessing its declared consumers. Neither comparison supplies semantic acceptance
or write authority. See [governing sources](../package/scoped-instructions.md#source-reconciliation)
for the grouped consumer path; interpretation judgement and recovery remain with
System Intent.
