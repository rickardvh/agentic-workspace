# Native delegation transport

The Python repository host can discover `codex-app-server/v1` for configured
OpenAI target/model identities as a peer of a process, API, or manual transport.
The retained current-host route remains distinct from launching that same target
through another adapter; only retained execution avoids launch safety checks.
Discovery offers persisted and disposable fresh alternatives where supported,
without changing the human policy. Explicit native transports remain supported.
The generic argv adapter retains
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
separate command-safety permission. Changing relevant source authority invalidates
the sealed native configuration before another provider effect; unrelated local
editor preferences do not invalidate it.

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
and revision. The public actor choice below selects among these offers;
cross-scope lineage admission remains assignment-owner work. There is no transcript store,
provider database replica, session ledger or portable session taxonomy.

An OS lock excludes another AW adapter writer of the same provider lineage
across worktrees and releases on process death. This does not claim to exclude
uncoordinated external provider clients. A missing provider thread revokes only
the local reference and blocks that dispatch. Planning survives; the acting
orchestrator must resolve another eligible configuration, commonly a fresh
bounded handoff. The adapter never silently converts resume into fresh.

Before launch, the assignment owner persists the exact bounded packet and run
state. The native process receives that assignment identity and a current AW core
binary through its local environment. Worker startup resolves the named assignment,
not whichever sibling was most recently written. An invalid identity fails closed.
End-to-end inheritance by the provider's worker shell still needs ordinary host
dogfood; deterministic environment fixtures alone do not prove that boundary.

Minimal per-run custody reserves one native attempt before launch and records the
opaque reference as soon as the provider returns it. Process release is recorded
only after close succeeds. Failed dispatch observations survive, including available
counters and total dispatch elapsed time; they are not successful task evidence.
Repeated dispatch cannot overwrite the existing attempt or launch another worker.
Dry-run and export do not launch work.

`assignment cleanup` can reversibly archive a native worker after an exact terminal
run and confirmed process release. It protects released siblings still awaiting
admission/review, preserves AW assignments and proof, and revokes archived local
continuation offers. Cleanup is idempotent. Unknown custody, process loss without
confirmed release, external writer conflicts or the bounded custody-scan limit
defer cleanup explicitly. It does not force another client's worker to stop.

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
references. It never deletes provider history. Ordinary exact terminal cleanup is
now implemented with deterministic custody coverage. Automatic terminal cleanup
policy, binding a hard user visibility requirement, and ordinary supported-host
custody/worker-entry evidence remain unresolved; advertising archive support alone
does not satisfy those outcomes.

Run deterministic coverage with `uv run --active pytest tests/test_native_transport.py -q`.
The live test is skipped unless `AW_NATIVE_TRANSPORT_HOST_MODEL` is explicitly
set to a currently discovered model. `AW_NATIVE_TRANSPORT_HOST_EFFORT` optionally
selects a discovered effort. Running with `-s` emits a compact counter report,
not provider references or transcript content.

`AW_NATIVE_TRANSPORT_HOST_MODES=fresh` runs only the unresolved fresh/cleanup
boundary when previously collected resume/fork/restart proof remains applicable.
Deterministic tests do not start provider processes or conversations.

The ordinary assignment decision exposes `execution_configurations`, including
the current offer revision and eligible configuration IDs. The acting orchestrator
can acquire these through `implement --changed <paths> --task <task> --select
context.delegation_decision --format json`, without expanding full context. It
can pair `--configuration-revision` and `--configuration-id` on `assignment export`
or `assignment dispatch` when materializing a bounded assignment. The supplied
transport must agree with that configuration. The choice selects within human
policy and owner eligibility; it cannot waive proof, change an existing assignment,
or turn advisory policy into execution authority. It is retained on the existing
Planning assignment, scoped to the same human intent and paths.
The offer revision includes the current contextual decision evidence as well as
transport feasibility. A unique current assignment owned by the selected Planning
revision can resume using its canonical intent and paths when task text is absent;
ambiguous sibling assignments require explicit subject selection.

New source-resolved configurations bind relevant local delegation, safety and
selected-target facts. Admission rechecks those facts; process adapters also
recheck executable identity. Stale choices block instead of selecting a different
route. Unrelated workspace launcher settings do not change this source binding.
The Python and generated TypeScript public clients accept the paired fields;
TypeScript requires the repository source host for source-owned admission and
fails closed when that host is unavailable. A dry-run does not materialize a
Planning assignment. Its `selection-preview` result explicitly leaves the run
identity empty and construction unperformed. Hard-ineligible native routes skip
provider discovery.

## Ordinary-work counterevidence

On 2026-09-07 the unchanged human local policy was copied into the stack worktree.
The public route retained the current target by default and exposed an eligible
disposable Sol configuration for a two-file cleanup inspection. Public export
created a canonical assignment and a bounded handoff without provider execution;
public dispatch then launched that selected configuration without another permission.

The inspection was interrupted by the orchestrator after 719347 ms to bound further
cost. No structured task result was returned. The preserved adapter observation was
56512 effective input tokens, 54784 cached input tokens and 1913 output tokens;
the rendered input measured 4274 bytes and the semantic packet 11327 bytes. These
observations are not a monetary total, a successful review, or target-failure
evidence. Orientation, retries, repair and the cause of the long run remain unknown.
Reasoning effort was left at the provider default; no claim is made about its value.

After confirmed process release, ordinary exact cleanup completed with
`already-absent`, preserving AW semantic state and deleting no provider history.
This proves interrupted-dispatch observation and terminal cleanup behavior, not
successful worker-shell entry or the full return/admission/proof lineage. No second
inference run repeated this inspection. The adapter now retains a reported ephemeral
guarantee before turn failure, so deterministic failed-ephemeral coverage requires
no archive request; that refinement has no additional live-host claim.

The ordinary selector initially omitted current offers and then exceeded its byte
budget when full legacy detail was included. Both gaps were corrected, with public
Python/TypeScript choice coverage and more than eight candidates. The verbose
fallback was 2046293 bytes; complete selected output was 21584 bytes. These are AW
serialization measurements, not token-price or credit-saving estimates.

## Adapter parameter choices and usage scope

The ordinary configuration selector carries adapter-owned `parameter_options`.
Assignment export/dispatch accept `configuration_parameters_json` alongside the
current `configuration_revision` and `configuration_id`. For example,
`{"reasoning_effort":"low","timeout_seconds":90}` is constructible only when that
exact adapter offer permits it. The source host validates the base revision and
adapter parameters, then re-enters shared eligibility and configuration fingerprinting.
The choice is local to the semantic assignment; it neither edits standing policy nor
changes the selected target, history guarantee, or continuity topology. Generic
process/manual routes do not pretend to support native parameterization.

Codex discovers supported efforts and suggested defaults from its installed model
catalog, and resolves effective provider settings for the target working directory.
The selected effort is explicit in the sealed configuration and provider turn.
Unknown effective settings require an explicit configured effort or exclude that
implicit native route. Parameter choices do not produce a Cartesian offer list.
The timeout bounds the model turn, with separately bounded setup and process cleanup;
it cannot exceed the configured adapter timeout or this adapter's 1800-second ceiling.

Codex `last` usage describes the latest model response; `total` accumulates responses
([matching provider source](https://github.com/openai/codex/blob/rust-v0.153.4/codex-rs/protocol/src/protocol.rs)).
Fresh native dispatch records cumulative counters for its exact turn. Resume, fork
and restart lack a proven pre-turn baseline here, so their whole-worker token counts
remain unknown. Duplicate updates do not add cumulative counters again. Neither
scope is a monetary estimate. A metadata-only query of the installed account usage
endpoint for the exact interrupted worker returned no thread usage; that does not
mean zero cost and does not justify reading unrelated account activity.

The parameterized ordinary host check on Codex 0.153.4 selected Sol, explicit low
effort, ephemeral execution and a 90-second turn deadline through public export.
It timed out without a structured return after 91347 ms. The fresh cumulative
observations were 103262 input, 73088 cached input and 1522 output tokens. This is
censored counterevidence, not successful delegation, target failure evidence or a
savings comparison against the earlier last-response counters. Monetary cost and
orientation/repair burden remain unknown. Exact cleanup reported `not-stored`,
retained semantic assignment state, and deleted no provider state. No further
provider inference was used to guess the cause.

Active-turn expiry is now distinguished from initial control-plane response timeout.
After a graceful close deadline, the native adapter terminates the owned Windows
launcher tree or POSIX process group; it does not treat killing only a launcher as
proof of worker release. An unconfirmed forced release leaves custody pending.
The Windows launcher/child termination fixture uses owned non-provider processes.
It is not a live-provider interrupt/steer proof.

## Completed native attempt admission

Native return admission uses the exact completed attempt's consumed lineage view. A successful persisted dispatch publishes its new continuation, but that publication cannot by itself invalidate the configuration which produced the return. The existing local run custody retains the bounded input-lineage metadata and resulting publication digest; no prompt, transcript or provider database is copied. Only the owner-held sealed packet, matching local run state, confirmed process release and unchanged publication admit that view. Current policy, safety, capability and evidence checks still apply. New selections do not get this admission view and cannot reuse a lineage whose producing return is awaiting admission. Missing custody, another run, changed publication or an unconfirmed live process fails closed.

## Hard execution guarantees

The human/repository configuration owner can require provider-neutral execution facts before best-fit comparison:

```toml
[delegation]
required_execution_guarantees = ["history.non-persisted"]
```

This optional list is a hard constraint, not a provider preference or an execution-authority grant. Shared Rust checks that every required name is present in the current adapter facts, alongside safety, independence, result/proof constructibility and exclusivity. Unknown facts do not satisfy a requirement. Names are extensible; accepting a name in configuration does not establish its availability. The public policy projection carries source provenance. Configuration choice and parameterized variants use the same requirements, and changing policy invalidates incompatible sealed packets.

The current Codex adapter establishes `history.non-persisted` for its supported ephemeral route and `history.provider-persisted` when it can explicitly request persistence. It requires the provider to confirm the selected guarantee before starting a turn; missing confirmation fails closed. These describe provider conversation history. They do not erase AW semantic assignment/proof state, establish general service retention, promise an unexpired conversation, or prove that a live worker is never visible. A required `history.never-visible` guarantee currently leaves these routes ineligible. Archive capability remains a separate fact; archive-after-completion cannot satisfy never-stored or never-visible intent. Resume/fork/recovery still require their independently discovered and current continuation capabilities.

The generic process, retained host and manual transports do not invent history guarantees. With no required guarantees their established portability behavior is unchanged. A hard requirement can therefore leave no eligible route; economics cannot override it. For a softer quiet-list preference, the acting orchestrator can compare the disclosed current facts without converting that preference into a universal transport ordering.
