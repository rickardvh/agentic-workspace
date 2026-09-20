# Native semantic scope and measurement admission

Verification uses its existing `verification/assurance-applicability/v1` request
for owner-issued `protocol:<id>` and `domain:<id>` identities as well as assurance
requirements. The answer is `applicable`, `not-applicable`, or `unresolved` for
that exact source, task, and current work. Source path matches cannot be weakened
by an answer. Task words never classify scope. Unknown identities, extra scope
fields, conflicting answers, and stale requests cannot select a new command.
No semantic declaration means no classification request.

An applicable protocol or domain lane supplies its source commands and retained
review context through the existing strategy owner. Execution requests carry
the applicability answer for fresh-process re-entry. Changing scope invalidates
the strategy; an answer is not execution, evidence, review, or claim authority.

## Measurement producer boundary

An applicable measurement requirement offers its exact `producer_command` as
`measurement:<requirement-id>`. Nothing runs during discovery. The selected
producer prints one JSON `agentic-workspace/assurance-evidence-records/v1`
object to stdout, containing at most 64 records. Each record names its exact
`requirement_id`, `evidence_label`, and an existing
`agentic-workspace/measurement-evidence/v1` compact `measurement` object.

The compact observation repeats metric, unit, comparator, threshold, aggregation,
subject/revision, environment, method `source_revision`, and the source-intent
`requirement_revision`. It supplies numeric `observed_value`, integer
`sample_count`, and `status="passed"`. Relative comparisons additionally bind
`control_subject`, `control_revision`, and a finite nonzero `baseline_value`.
Verification evaluates the value against the **source** threshold and tolerance;
the producer's status never substitutes for that comparison. The producer owns
the declared aggregation and environment observation, just as it owns the raw
samples; native custody does not establish an unobserved nested tool environment.

Only complete stdout in the current native execution's hashed private artefact
is eligible. Manual receipts, historical assurance files, labels, unbound JSON,
truncated output, and command success without the observation cannot satisfy it.
No new evidence store is introduced. Reuse the current receipt reference with
the existing claim request. Declared source, task, method or subject changes
require fresh evidence; do not relabel an old receipt. Raw records stay private;
the public requirement gap includes a compact measurement admission and an exact
repair reason for failed conditions.

`current-measurement-satisfied` removes only that measurement's missing evidence
condition. Other evidence labels, independent reviewer custody, source-intent
reconciliation and task claim judgement remain separate requirements. This does
not assert that the repository's historical performance thresholds are met or
that old pytest producers already emit this compact format.

## Evidence and cost

The native public scope journey tests a selected command, replay without repeat
execution, negative and stale judgements, path precedence, unknown scope, and a
quiet unrelated control. The measurement journey executes a maintained fixture
which measures five real file reads, then uses controlled threshold, sample,
identity and output negatives. It checks manual-result rejection, stale source
re-entry, private output, and the independent reviewer restriction. Numeric
comparison edge classes live at the Rust owner level. Existing strategy and
receipt tests cover retained command/recovery contracts.

These are two native public journeys, without repeating shared semantics across
four adapters. The bounded claim is scope-to-command and receipt-to-measurement
admission, not benchmark performance or independent acceptance. No new ordinary
CI constituent or recurring measurement collection is added. Stop after these
owner boundaries and existing native tests pass; independent acceptance remains
external to the implementation.
