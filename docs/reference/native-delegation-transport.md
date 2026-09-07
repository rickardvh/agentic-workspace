# Native delegation transport

The Python repository host can construct `codex-app-server/v1` as a peer of a
configured process, API, or manual transport. The generic argv adapter retains
its existing behavior. Neither transport has a fixed priority over the other;
selection compares eligible execution configurations and keeps configured order
as the existing tie breaker when contextual evidence is absent.

```toml
[[delegation_targets.worker.transports]]
kind = "native"
adapter = "codex-app-server/v1"
parameters = { model = "<current-model-id>" }
timeout_seconds = 1800
```

Where discovered, `parameters.ephemeral = true` requests non-persisted fresh or
fork execution. The adapter checks the provider's ephemeral result flag and does
not retain a reusable reference for it. Resume/restart cannot silently use this
setting. Configured persisted execution remains available for continuity.

The adapter discovers the installed protocol schema and current account model
catalog. Supported reasoning settings come from that catalog and are accepted
only when the installed turn protocol can enforce them. Unknown adapter knobs
fail closed. Native execution requires automatic transport authority and the
separate command-safety permission. Changing the source configuration invalidates
the sealed native execution configuration before another provider effect.

Discovery uses the adapter implementation, installed executable version and
protocol fingerprint. A fifteen-minute bound forces rediscovery even when the
local version is unchanged; callers may request an earlier explicit refresh.
Failure to discover this adapter removes its offers without replaying setup or
preventing a constructible process/manual peer from being considered.

Fresh starts an independent provider thread. Resume and restart preserve its
opaque identity; fork must return a different identity. The adapter requests
metadata-only continuation responses and never reads provider transcripts.
Provider method names and settings remain inside the Python adapter. Its
read-only sandbox returns an unapplied patch or read-only result for ordinary AW
admission, integration, proof and closeout. Successful transport is not proof.

Each dispatch owns one control-plane process. The provider owns conversation
persistence after it exits. Live steer, attach and interrupt are unavailable in
this adapter: it has no retained live worker attachment. The generated
TypeScript host also fails closed for native execution rather than substituting
its process adapter. The process adapter remains independently available there.

Local residue contains one current opaque continuation reference per target and
parameter combination, capability/target revisions, exact semantic scope,
originating AW run and known liveness/exclusivity. The checked-in assignment
carries only a digest binding to that local residue. Reuse offers become visible
after the originating attempt is terminal, and only for the same semantic scope
and revision. Cross-scope lineage admission and a public actor choice among
these offers remain assignment-owner work. There is no transcript store,
provider database replica, session ledger or portable session taxonomy.

An OS lock excludes another AW adapter writer of the same provider lineage
across worktrees and releases on process death. This does not claim to exclude
uncoordinated external provider clients. A missing provider thread revokes only
the local reference and blocks that dispatch. Planning survives; the acting
orchestrator must resolve another eligible configuration, commonly a fresh
bounded handoff. The adapter never silently converts resume into fresh.

## Supported-host evidence

On 2026-09-06, the opt-in `test_installed_native_host_continuity` test passed on
Windows with installed `codex-cli 0.153.4`, selecting a model and reasoning effort
from its current catalog. Each mode used a separate app-server process. Resume
and restart preserved the original identity; fork returned a distinct identity.
A well-formed nonexistent thread was rejected before a turn started. Live steer
remained unavailable. No opaque provider IDs are retained in this report.

| Mode | Effective input | Cached input | Output | Elapsed ms |
| --- | ---: | ---: | ---: | ---: |
| Fresh | 13775 | 12544 | 39 | 5805 |
| Resume | 13804 | 13568 | 15 | 4802 |
| Fork | 13833 | 1792 | 27 | 5685 |
| Restart | 13833 | 13568 | 26 | 3998 |

These tiny JSON-return probes establish transport identity and counter contracts.
They do not establish task economics, independent Verification, or #2817's
unrelated substantive-task dogfood. Economic cost, orientation, repair, review
and integration burden remain unknown unless separately observed. Claude was
not installed on this host; no Claude behavior is claimed.

After the user observed test conversations accumulating in the app, cleanup was
added to the opt-in test's `finally` path. A focused fresh-worker run passed with
one owned thread automatically archived and zero active-list residue: 13775 input
tokens (12544 cached), 28 output tokens and 4993 ms. Earlier continuity evidence
was reused. Metadata-only checks separately verified ephemeral-list omission,
that archived threads require explicit unarchive before resume, and that an
external active writer can block archive. No model turns were used for those
metadata checks. The adapter does not claim post-archive resume or forced cleanup
of a live externally owned thread.

The persisted live test requires discovered archive support, captures owned
references before a turn can fail, and attempts exact owned cleanup on success
or exception. Cleanup failure remains a test failure with minimal local pending
references. It never deletes provider history. Ordinary assignment-terminal
cleanup and binding a hard user visibility requirement remain lifecycle/selection
owner work; advertising archive support alone does not satisfy those outcomes.

Run deterministic coverage with `uv run --active pytest tests/test_native_transport.py -q`.
The live test is skipped unless `AW_NATIVE_TRANSPORT_HOST_MODEL` is explicitly
set to a currently discovered model. `AW_NATIVE_TRANSPORT_HOST_EFFORT` optionally
selects a discovered effort. Running with `-s` emits a compact counter report,
not provider references or transcript content.

`AW_NATIVE_TRANSPORT_HOST_MODES=fresh` runs only the unresolved fresh/cleanup
boundary when previously collected resume/fork/restart proof remains applicable.
Deterministic tests do not start provider processes or conversations.
