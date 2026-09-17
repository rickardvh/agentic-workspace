# Candidate lanes

Planning owns bounded lane, decomposition and execplan records. Candidate work preserves a broader intended outcome, related issue references, dependencies, a promotion trigger and a suggested next bounded slice. Candidate status does not authorize implementation.

Use current Planning detail returned by `agentic-workspace start --target . --task "<task>" --format json` when this work needs durable execution custody. Follow its exact owner requests to select, create or transition a record. Do not recreate the former aggregate state file or a second backlog.

For ordered multi-lane work, preserve each lane's intent and dependencies. Select the next ready slice, implement and validate it, then reconcile its owner and required continuation before selecting the next. One completed execplan does not prove the parent lane is satisfied.

Keep active sequencing with Planning and durable technical knowledge with its canonical source or Memory. Do not create Planning records for direct work without a real continuity need.
