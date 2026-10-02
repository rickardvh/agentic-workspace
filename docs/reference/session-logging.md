# Session logging

Use this reference when interpreting or exporting AW session diagnostics.

Agentic Workspace records each logical session in one append-only `events.jsonl` file under the local session-logging registry namespace. That shared stream owns the monotonic sequence across physical rotations. Each event retains its physical session id, while the adjacent physical-session `session.md` and `index.json` files remain human-readable and query-friendly compatibility projections.

## Coverage and evidence limits

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

## Recorded events

Every event follows `session_log_event.schema.json` and carries a stable event id, timestamp, monotonic sequence, event type, logical and physical session ids, optional parent/correlation ids, and a typed payload. `command.started` and `command.completed` share an entry id, making interrupted commands visible. Historical source-maintenance captures may also contain `workflow.transition` events; current native capture is described below. Identifiers derived from host-provided correlation values are salted hashes, so raw host identities are not written to disk.

Physical rotations append through the same logical-stream lock and never restart its sequence. A host can link delegated or resumed work by passing the parent raw logical identity in `AW_SESSION_LOG_PARENT_LOGICAL_IDENTITY` and an optional correlation value in `AW_SESSION_LOG_CORRELATION_ID`. AW stores only private derived ids. If the logical identity is missing but either explicit parent or correlation continuity resolves an existing owner, AW records a metadata-only `logging.gap` in that owner's stream without creating identityless state. If no owner can be resolved, the host must retain `AW_SESSION_LOG_GAP_REASON` until the next identified write, which consumes it into the resolvable stream. Temporarily disabling capture uses the same continuity rules.

## Export for inspection

Review an export before sharing it. Path normalisation is not secret scanning or
transfer approval; exports can include command output.

`uv run --frozen python src/tooling/maintainer/session_diagnostics.py export --target .` produces one share-review candidate ending in `.jsonl.gz`. Without an explicit `--id` or `--path`, it includes the current logical session, its physical rotations, and linked delegated descendants. The first record is an `export.manifest`; later records are one normalised event per line in global sequence order. Large text output remains in per-command blob files referenced by path, byte count, and SHA-256 from completion events. Default export verifies each blob's bytes and digest, then emits bounded `output.chunk` events for recorded request, stdout, stderr and configuration content. Chunks retain stream order, source and exported byte counts/digests. Missing, damaged or excluded artifacts have explicit coverage statuses. `--no-artifacts` explicitly omits bodies while retaining references and coverage metadata.

Exports preserve the raw local logs, normalise known machine-local paths, and disclose time, gap, child-session, and artefact coverage. Event ordering is deterministic for unchanged source streams; deliberately variable manifest creation metadata gives each export its own hash.

Raw sessions, derived views, blobs, and exports are ignored local diagnostics. AW does not automatically promote, upload, or delete them; they remain under `.agentic-workspace/local/` until the workspace's local retention or cleanup process removes them.

Older Markdown/index-only sessions remain readable. Existing physical JSONL streams are deterministically migrated into the logical stream on the next identified session resolution; export synthesises migration events and explicit gap records when it must recover chronology from derived views alone. A malformed or partial JSONL tail does not hide later valid events; readers report the damaged record and continue from subsequent complete lines.

## Native transport capture

Native `start` and `invoke` automatically retain diagnostic I/O when the current local `[session_logging]` source enables it and `AW_SESSION_LOGICAL_IDENTITY` supplies a stable explicit identity. Configure it once in `.agentic-workspace/config.local.toml` (or the selected shared-local source):

```toml
[session_logging]
enabled = true
detail = "full"
path_mode = "absolute"
```

Capture is disabled by default. When enabled, `detail` defaults to `full`; explicitly select `metadata` to retain only timings, identities, sizes, digests and status tags. `AW_SESSION_LOGGING_DISABLE=1` wins. Disabled capture produces no diagnostic files or status field. Missing identity creates no diagnostic files. Malformed configuration or diagnostic state cannot change the operation result.

Full capture saves the exact native request envelope text, including task/context, request answers and invocation arguments, and the JSON stdout/stderr delivered by that transport, including its capture advisory and error envelopes. It retains full, compact and carried responses without changing what the caller consumes; the advisory remains outside immutable carriage. CLI argument parsing is upstream of this boundary: the resulting native envelope is retained, rather than host argv. Arbitrary host terminal activity, provider conversations and private model reasoning are outside capture.

Each operation references a recoverable JSON artifact in the existing physical session's `artifacts/` directory. The canonical event stays below 8 KiB; request/output bodies have no inline truncation threshold. The artifact also records effective operating configuration (workspace, modules, assurance, payload, logging, clarification and delegation policy), local/repository source revisions and bundled runtime identity. It excludes arbitrary environment values and worker transport declarations. This prelude is retained with every full operation so changed configuration remains interpretable.

`absolute` preserves native I/O bytes. `repo-relative` replaces known target paths with `.`, while `redacted` replaces them with `<target>`; both also replace known home paths and explicitly supplied `AW_SESSION_LOG_REDACT_PATHS`. The artifact declares this transformation and events retain original transport digests. These choices apply to recorded bodies as well as event targets. Default export normalises known local paths in either mode and reports source and exported stream digests; normalisation is not secret scanning or approval to transfer. Full local logging can contain sensitive request/output content supplied to AW.

Parent/correlation identities use the existing salted identity format at initial registration. The 1 MiB existing stream/registry read bound, lock contention or interruption can prevent capture; bodies are never silently replaced with hashes to fit those bounds. The operation returns `capture-failed` when retention fails. No native rotation or interrupted-command recovery is claimed. `diagnostic_content` in the export manifest separately reports capture levels, intentionally omitted body ids, and completeness for recorded commands; an intact metadata stream does not imply full-body capture. Transport success is not task success or proof.

An absent registry is created exclusively with exact common attempt/commit custody. A later native command verifies that custody before appending or registering a new logical identity. The existing registry retains only its latest publication provenance; immutable attempt/commit evidence uses the common effect store. Historical registries, including native registries created before this provenance existed, remain readable but unavailable for native mutation. Unknown or torn state is preserved.

A stable OS owner lock serialises admitted native registration writers, and the retained Python writer refuses native publication carriers. Exact source bytes are rechecked before replacement; this is cooperating-owner serialisation, not filesystem compare-and-swap against arbitrary external writers. Process interruption after exact registry publication can finish its planned immutable commit. Interruption before publication leaves the attempt censored and does not blindly retry registration. Capture stays failure-isolated in both cases. Common custody references retain confined machine-local target/path identity outside exported diagnostic events; path-mode redaction applies to captured event paths, not proof of local file custody.

This closes the bounded new-identity registration gap for newly custody-created native registries. Historical transfer, interrupted-command capture/rotation, and separate release-artefact acceptance under #2990 remain unresolved; #2995 is not declared complete.

Source-checkout maintainers can use `uv run --frozen python src/tooling/maintainer/session_diagnostics.py analyze --target .` or the same script with `export --no-artifacts` to read registered native streams through the current logical identity. This is maintained diagnostic tooling, not an installed/public command. The former command-generation session-log model is source-maintenance-only. Native caller origin is explicitly unknown. Native capture does not introduce a separate analysis command or log store.

### Ordinary capture posture

The native transport attaches `session_capture` after resolution and capture,
including compact results, the model-facing view of carried results, and error envelopes. Python, TypeScript and
JSON clients receive the same native result field; they do not implement logging
policy. The advisory has `authoritative: false` and one status:

- `capturing`: this invocation was appended to its identified event stream.
  `detail` declares `full` or `metadata`; only full means its I/O artifact was retained.
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

### Restoration parity

| Accepted diagnostic outcome | Current native capture/export |
| --- | --- |
| #2122 automatic AW input/output and effective configuration | Full level records native envelopes, delivered responses/errors and an operating configuration prelude automatically. Disabled/default capture remains quiet. |
| #2130 recoverable large raw output beside a bounded index | Canonical completion events reference hashed local I/O artifacts. Default export verifies and carries their content in bounded chunks. Native output deduplication and richer Markdown/index projections remain unavailable. |
| #2707 one ordered logical chronology and ordinary export | Existing logical/physical ids, monotonic ordering and supported child/rotation reader selection remain in use. Default export includes recorded I/O and declares real missing/damaged/omitted content. |

This restores diagnostic content for newly recorded native operations. It does not
backfill historical metadata-only bytes. Native optional note writing, automatic
rotation and interruption/disabled-gap events remain unavailable; historical
reader support does not establish those native capabilities or whole-task coverage.
