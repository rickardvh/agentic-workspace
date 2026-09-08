# Native system-intent sources

The native owner consumes configured `system_intent.sources` and
`preferred_source`, plus an existing `.agentic-workspace/system-intent/intent.toml`.
It never creates, refreshes or replaces an intent mirror. A compact view lists
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
