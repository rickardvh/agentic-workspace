# Native system-intent sources

The native owner consumes configured `system_intent.sources` and
`preferred_source`, plus an existing `.agentic-workspace/system-intent/intent.toml`.
Read-only resolution never refreshes an intent mirror. A compact view lists
exact source identities and retained interpretation currentness; source bodies and
interpreted fields are returned only through the owner-provided
`system-intent/read-current-source/v1` request. The shared public request envelope
binds each read to the current task, source and capability revisions.

The original governing source remains authoritative for acting-agent judgment.
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
proposed TOML, a `faithful` or `revised` semantic judgment, and the reason for that
judgment through `system-intent/edit-source/v1`. `unresolved` preserves the gap.
The proposed `source_records` must match the declared sources (historical
universal-newline SHA-256 format); constructing these records is bookkeeping
**after** semantic review, never the judgment itself. Preserve useful human-owned
why, unresolved questions and extension fields when revising the interpretation.

The returned proposal exposes before/after material and binds raw governing
bytes, the old interpretation, configuration and capability identities. Its
exact response request accepts `authorize-write` or `defer`; without acceptance
there is no effect. Invoke the returned action to publish only
`.agentic-workspace/system-intent/intent.toml`. Scoped protection still applies.
Source, policy or proposed-content changes invalidate the dependent answer/action.
No Git HEAD, timestamp, source-read success or digest comparison supplies semantic
acceptance. The owner validates structural currentness, not the truth of an
agent's judgment or authority beyond the accepted exact owner answer.

Publication uses shared authenticated attempt custody, a bounded preparation
marker and atomic source replacement. An interrupted final outcome exposes an
exact recovery request; recovery confirms existing bytes and cannot republish or
accept changed governing sources. A fresh read clears only source-currentness and
recorded-review gaps. Planning alignment and task completion remain separate.
Unchanged sources are quiet, including across unrelated Git commits. No new intent
store, workflow ledger or automatic mirror refresh is introduced. Without runtime,
readers can inspect checked-in sources but cannot establish live acceptance,
currentness or mutation authority.
