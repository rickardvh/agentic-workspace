# Decision-reuse audit

## Decision

The repository already has substantial generic projection/currentness
machinery and does not need a shared reasoning cache, decision registry, or
new persistence layer. This PR repairs one demonstrated gap: reuse of the
Verification semantic contribution across execution-attempt retries. Its
currentness check is a thin domain wrapper over `ProjectionConstituentSpec`
identity and comparison semantics.

This audit is evidence for #2981, not a complete v1 owner-boundary
disposition. The source-first semantic contraction in #2989 can still remap or
remove composite alpha boundaries before v1.

## Owner and disposition inventory

| Candidate conclusion | Current owner and identity | Disposition |
| --- | --- | --- |
| Route / operating decision | Workspace operating decision plus the current `route` `ProjectionConstituentSpec`; task, selected owner, Planning, changed paths, and route inputs invalidate it | Existing whole-projection reuse exists; v1 owner-boundary disposition remains under #2981/#2989 |
| Verification operating projection | Verification constituent; task, changed paths, and Verification inputs invalidate it | Existing whole-projection reuse exists; v1 owner-boundary disposition remains under #2981/#2989 |
| Verification semantic-slice contribution | Verification partition keyed by normalized Planning slice revision and proof-policy identity | Owner-specific repair in this PR; target, transport, assignment, and run retries reuse it |
| Selected proof | Current `selected_proof` constituent keyed by task, changed paths, proof subject, and proof inputs | Existing whole-projection reuse exists; proof strategy/evidence lifetime remains under #2981/#2989 |
| Closeout trust | Current `closeout_trust` constituent keyed by task, owner, Planning, changed paths, proof subject, and closeout inputs | Existing whole-projection reuse exists; v1 owner-boundary disposition remains under #2981/#2989 |
| Planning normalized slice / frontier | Planning semantic revision and the derived frontier tracked by #2970 | Route to #2970; do not copy it into another reuse store |
| Parent/sibling ready-work conclusions | Derived Planning frontier tracked by #2970 | Route to #2970; no peer queue or cache |
| Context/read-first selection | Query-shaped operating projection; selected Memory enrichment adds only its declared index and manifest dependencies | Existing whole-projection reuse exists; ordinary partial re-resolution remains under #2981/#2989 |
| Assignment target eligibility and ranking | #2210 assignment policy over current target evidence and runtime facts | Existing separation exists, but stable eligibility versus volatile ranking/economics still requires the #2981/#2989 disposition |
| Reused-versus-reresolved attribution | #2967/#2969 evaluation and attribution owners | This PR exposes `reused` versus `resolution-required`; downstream interpretation remains with those issues |
| Direct/simple decisions | Acting agent | Deliberately ephemeral; no mandatory lookup or retained artifact |

## Measured cases

The maintained fixtures distinguish reuse from coincidentally repeated
computation:

- `test_query_shaped_public_selectors_measure_cold_and_warm_reuse_cost`
  records state reads and dependencies for cold and warm consumers. Adding the
  Memory decision packet adds exactly two reads—the Memory index and manifest—
  rather than invalidating unrelated constituents.
- `test_doctor_reuses_unchanged_projection_before_full_builder_and_invalidates_on_dependency_change`
  proves the warm path skips the full projection builder and emits less than
  half the cold output bytes. Local logs and scratch do not invalidate it;
  external-intent or config changes do.
- `test_report_reuses_source_owned_projection_in_a_fresh_process` runs two
  independent CLI processes and proves that the second consumes the same
  source-owned decision identity from bounded local projection state.
- `test_verification_partition_reuses_semantic_contribution_across_attempt_retry`
  proves cross-consumer integration: a new target/run attempt reuses the prior
  semantic contribution, while a Planning semantic revision reroutes exact
  Verification resolution.
- `test_unversioned_proof_policy_uses_content_digest_for_currentness` proves
  reconstructible fresh-session identity when the proof owner lacks an
  explicit revision.

These fixtures measure avoided builder work, output bytes, state reads, and
semantic-resolution calls/paths. They do not claim to preserve model
reasoning, prompts, transcripts, or token traces. The token-saving boundary is
compact source-owned semantic output plus exact dependency identity.

## Selective invalidation and authority

Branch, HEAD, and base remain observational unless a constituent explicitly
declares them. Unrelated worktree, Memory, module, target, transport, or run
changes therefore cannot invalidate the Verification semantic conclusion.
A changed Planning semantic revision or proof-policy revision suppresses the
old semantic payload and returns an exact Verification re-resolution action.
Uncertainty and target-selection judgment are never promoted into hard
authority by reuse.

## Final architecture disposition

This PR repairs the Verification semantic-versus-attempt gap without adding a
central cache, registry, event ledger, transcript archive, or universal
dependency service. It does not prove that current composite packet and
constituent boundaries are the right v1 reuse boundaries. Names such as
`route`, `selected_proof`, and `closeout_trust` remain alpha implementation
shapes rather than permanent architecture commitments.

#2981 therefore remains open to remap reuse after #2989, including proof
strategy versus evidence, assignment eligibility versus ranking, exact
Planning subject identity, owner revisions versus filesystem reconstruction,
ordinary partial re-resolution, and convergence or removal of this PR's thin
Verification wrapper where the contracted currentness machinery makes it
unnecessary.
