# Assignment and delegation

Optional local policy at `.agentic-workspace/local/delegation.json` answers four
independent questions: current target/runtime facts, assignment policy,
transport authority, and override owner. An `applies` selector keeps unrelated
work quiet. Provider identities, credentials, prices, and outcome evidence stay
local.

Assignment first excludes unavailable, under-capable, proof-incompatible,
scope/constraint/stop-incompatible, insufficiently trusted, human-restricted,
or non-constructible targets. Cost cannot rescue an ineligible target. It then
compares declared total cost plus current, sufficiently confident,
context-matched evidence from maintainer, repository, or Verification
authority. Stale, disputed, superseded, and worker-self-reported evidence does
not rank. A tie becomes a revision-bound owner decision.

Advisory or retained-local answers do not dispatch. A binding non-local answer
yields one typed handoff with the Planning semantic subject, scope, stops,
transport topology, attempt identity, and mutation baseline. An authorized,
ready process transport with a concrete command executes immediately and
records only bounded result digests; failure remains bound to the same attempt
and never falls back locally. Other transports produce a complete
`prepared-manual` handoff.

Host-native, process/external unapplied-delta, and shared-worktree
already-materialized delivery use the same assignment identity. Returned shared
work must exactly match the declared changed paths against the captured baseline
and remain within scope. Unapplied delivery carries bounded UTF-8 artifacts with
before/after identities; the guarded integration operation checks currentness,
scope, content identity, and applies each artifact exactly once, including
recovery after a partial interruption. Integrated results enter Planning as a
revision-bound returned attempt, then Planning reconciliation and Verification
remain separately source-owned. A worker result never grants the parent claim.
