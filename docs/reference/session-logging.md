# Session logging

Analysis and export describe the **known recorded stream**. An internally complete
stream is compatible with unknown whole-task coverage: no gap event does not prove
that no host work went uncaptured. `coverage.subject` identifies index agreement;
`recorded_stream_integrity` identifies canonical-stream integrity. Export profiles
are `recorded-stream-summary` or `recorded-stream-with-output-chunks` and explicitly
retain `whole_task_coverage: unknown`.

Maintainer analysis/export functions accept bounded `capture_observations` status
values (`identity-unavailable`, `capture-failed`, `disabled`) as caller-supplied
context. They do not fabricate events or ingest transcripts. Source/export command
counts refer to recorded completions, including native-only streams. Metadata-only
repetition with omitted arguments cannot establish redundant routing.

Agentic Workspace records each logical session in one append-only `events.jsonl` file under the local session-logging registry namespace. That shared stream owns the monotonic sequence across physical rotations. Each event retains its physical session id, while the adjacent physical-session `session.md` and `index.json` files remain human-readable and query-friendly compatibility projections.

Every event follows `session_log_event.schema.json` and carries a stable event id, timestamp, monotonic sequence, event type, logical and physical session ids, optional parent/correlation ids, and a typed payload. `command.started` and `command.completed` share an entry id, making interrupted commands visible. Routed `start`, `implement`, `proof`, and `closeout` commands also emit compact `workflow.transition` events. Identifiers derived from host-provided correlation values are salted hashes, so raw host identities are not written to disk.

Physical rotations append through the same logical-stream lock and never restart its sequence. A host can link delegated or resumed work by passing the parent raw logical identity in `AW_SESSION_LOG_PARENT_LOGICAL_IDENTITY` and an optional correlation value in `AW_SESSION_LOG_CORRELATION_ID`. AW stores only private derived ids. If the logical identity is missing but either explicit parent or correlation continuity resolves an existing owner, AW records a metadata-only `logging.gap` in that owner's stream without creating identityless state. If no owner can be resolved, the host must retain `AW_SESSION_LOG_GAP_REASON` until the next identified write, which consumes it into the resolvable stream. Temporarily disabling capture uses the same continuity rules.

`session-log export` produces one share-review candidate ending in `.jsonl.gz`. Without an explicit `--id` or `--path`, it includes the current logical session, its physical rotations, and linked delegated descendants. The first record is an `export.manifest`; later records are one normalized event per line in global sequence order. Large text output remains in per-command blob files referenced by path, byte count, and SHA-256 from completion events; export converts available stdout and stderr into bounded `output.chunk` events so no line grows without limit. Binary or unavailable blobs remain digest references. `--no-artifacts` retains hashes and coverage metadata without output bytes.

Exports preserve the raw local logs, normalize known machine-local paths, and disclose time, gap, child-session, and artifact coverage. Event ordering is deterministic for unchanged source streams; deliberately variable manifest creation metadata gives each export its own hash. Normalization is not secret scanning or transfer approval: review the generated stream before sharing it.

Raw sessions, derived views, blobs, and exports are ignored local diagnostics. AW does not automatically promote, upload, or delete them; they remain under `.agentic-workspace/local/` until the workspace's local retention or cleanup process removes them.

Older Markdown/index-only sessions remain readable. Existing physical JSONL streams are deterministically migrated into the logical stream on the next identified session resolution; export synthesizes migration events and explicit gap records when it must recover chronology from derived views alone. A malformed or partial JSONL tail does not hide later valid events; readers report the damaged record and continue from subsequent complete lines.

## Native transport capture

Native `start` and `invoke` capture completion metadata when the current local `[session_logging]` source enables it and `AW_SESSION_LOGICAL_IDENTITY` supplies a stable explicit identity. `AW_SESSION_LOGGING_DISABLE=1` wins. Disabled capture produces no diagnostic files or status field. Opted-in capture returns a compact `session_capture` transport advisory; missing identity creates no diagnostic files. Native capture uses the shared Rust policy for `enabled`, `path_mode`, and the `redact_local_paths` compatibility alias; malformed configuration or diagnostic state cannot change the command result.

Native events contain timing, command identity, transport outcome, request/result byte counts and hashes, and explicit omissions. They omit raw tasks, arguments, result bodies and stdout/stderr. Paths follow the configured mode. Parent/correlation identities use the existing salted identity format at initial registration. Capture is limited to 8 KiB per event and a 1 MiB existing stream/registry read; reaching a bound, lock contention or interruption omits diagnostics. No rotation or interrupted-command recovery is claimed. Transport success is not task success or proof.

An absent registry is created exclusively with exact common attempt/commit custody. A later native command verifies that custody before appending or registering a new logical identity. The existing registry retains only its latest publication provenance; immutable attempt/commit evidence uses the common effect store. Historical registries, including native registries created before this provenance existed, remain readable but unavailable for native mutation. Unknown or torn state is preserved.

A stable OS owner lock serializes admitted native registration writers, and the retained Python writer refuses native publication carriers. Exact source bytes are rechecked before replacement; this is cooperating-owner serialization, not filesystem compare-and-swap against arbitrary external writers. Process interruption after exact registry publication can finish its planned immutable commit. Interruption before publication leaves the attempt censored and does not blindly retry registration. Capture stays failure-isolated in both cases. Common custody references retain confined machine-local target/path identity outside exported diagnostic events; path-mode redaction applies to captured event paths, not proof of local file custody.

This closes the bounded new-identity registration gap for newly custody-created native registries. Historical transfer, interrupted-command capture/rotation, and separate release-artifact acceptance under #2990 remain unresolved; #2995 is not declared complete.

The existing public `session-log analyze --origin all --format json` and `session-log export --no-artifacts --format json` discover registered native streams through the current logical identity. Native caller origin is explicitly unknown. Native capture does not introduce a separate analysis command or log store.

### Ordinary capture posture

The native transport attaches `session_capture` after resolution and capture,
including compact results, the model-facing view of carried results, and error envelopes. Python, TypeScript and
JSON clients receive the same native result field; they do not implement logging
policy. The advisory has `authoritative: false` and one status:

- `capturing`: this invocation was appended to its identified event stream.
- `identity-unavailable`: capture was requested but portable identity is missing,
  blank or oversized. `requirement: AW_SESSION_LOGICAL_IDENTITY` names the host's
  recovery boundary. Provider-specific identity discovery stays in host adapters.
- `capture-failed`: capture was requested with identity but the diagnostic path
  could not record the invocation. Existing files are preserved; the underlying
  operation's result and exit status are unchanged.

This is a replaceable per-invocation observation, not an accumulating warning or
an episode registry. Repeated degradation has the same bounded field (under 160
bytes), no repeated prose and no status-history writes. A fresh successful
observation clears degradation immediately. Supplying identity later records only
subsequent invocations; it does not backfill earlier work. Capture failure details
and raw identities are excluded from the advisory. Disabled/default results stay
quiet. The field is outside decision carriage and all semantic owner inputs;
it grants no task, mutation, proof, claim or completion authority.
