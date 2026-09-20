# Priority 5: portable continuation and bounded worker context

This lane under #3207 implements the bounded #3195 / #2818 continuation surface
and supplies current evidence for #2970 / #3059. The parent outcomes still require
accepted child dispositions and #2909 exact-candidate aggregation. This is not
provider-switching economics (#3192), automatic host-native dispatch, independent
review acceptance, or preview publication.

## Portable Planning

Current Planning detail exposes `portable_continuation`: a repository source
identity and semantic revision, an exact pointer to the existing reconciled
material, and the separate target-bound local custody status. The material retains
outcome, scope, constraints, dependency/parent boundaries, frontier, declared
progress and proof, handoff/returned/integration-pending work, and residual intent.
No parent chat or new session/handoff database is needed. Task wording, provider
and execution attempts do not define this semantic identity; material and owner
identity do. Existing source admission and containing-outcome limits still apply.

New native creation records use `creation-provenance/v2`, with repo-relative
immutable effect references and a material digest. Their complete source bytes
can move with the repository, like the existing update-provenance/v2. Original
local custody is never copied into executable authority. A fresh consumer selects
the current repo owner and uses its exact `planning.reconcile` action to acquire
local custody; the plan bytes remain unchanged. The full material lives once at
`/planning/current_owner/reconciliation/subject/state`; compact consumers expand
the exact current Planning detail when needed.

Both absent local effect records permit source observation with the local outcome
unknown. They never acknowledge or replay the old effect. One missing, malformed,
or mismatched record remains an uncertain-effect error. Complete local carrier
loss also preserves source discovery at the original target. Legacy v1 creation
records still require their original custody; absence is an explicit gap, not an
implicit migration or imported authority. A current supported update observation
must bind changed portable material. Declared local evidence refs are surfaced as
present-unvalidated or unavailable, never as portable proof. Direct/no-Planning
work receives no portable context and creates no Planning artefacts.

## Worker entry and return

The existing canonical packet API adds `entry`, `expand` and `return`. Native CLI
uses `worker --input <json> --format json`; JSON uses `assignment_packet`, and
existing Python `assignment_packet` / Node `assignmentPacket` expose the same Rust
owner. Input objects contain `action` and the original machine-carried `packet`.

`entry` returns an `assignment-worker-entry/v1` view containing the selected
outcome, role, scope/effects, required/read-first inputs, proof requirements, stop
conditions and authority ceilings. Small captured bodies are inline (2 KiB each,
8 KiB total); larger required bodies have exact packet-bound `detail_ref` values.
Use `expand` with `reference` to retrieve those captured bytes before working.
They are not live source admission. Unrelated parent history and duplicate owner
re-entry envelopes are not worker context.

`return` accepts only new result material: summary, changed paths, patch, stop
conditions hit and optional delivery mode. It assembles immutable identity and
one exact owner return request from the packet. The host submits returned
`reentry` to current `start` at the receiving repository target. Assignment still
rejects stale sources, forged identity, malformed results and wider effects.
Neither a checksum nor successful assembly authenticates a reviewer or proves a
claim. Losing carriage requires current owner re-export; it never authorises a
repeat launch. Existing retained-local and process launch owners remain intact.

## Evidence design and retention

The decisive failure classes are: semantic work lost or rebound across targets;
local effects imported/replayed as authority; portable observation tampering;
worker restrictions lost by presentation; packet/detail substitution; model
identity replacement; and hidden operating burden treated as zero.

Reuse the stable Planning creation/update and Assignment capsule/typed-return
journeys. Extend their native cases for fresh consumer, complete/partial local
loss and worker CLI assembly. Existing adapter parameterisation is unchanged;
new lifecycle semantics are not multiplied across adapters. One small Rust
worker projection contract covers eager/lazy bytes, exact reference substitution,
malformed capsules, seal alteration and identity material rejection. No new
Priority-named test suite or ordinary CI tranche is added. This retains one
previously uncovered disposable-worker presentation contract and extends existing
owner evidence rather than mirroring each acceptance row.

Validation results and measured fixture burden are recorded below after the
current checks. The fixture counts serialised bytes, selected procedure sources,
public/detail calls, bounded semantic judgements and material return size. Runtime
burden fields explicitly distinguish known serialised sizes/helper writes from
unknown host skills, model turns, user steering, repair and elapsed time. Fixture
observations do not turn those production unknowns into zero. No telemetry is
persisted and no tokenisation or provider-cost claim is made.

Stop when these bounded owner contracts, native journeys and required hooks pass
with no unresolved implementation risk. Escalate if fresh source meaning cannot
be recovered, uncertain effects become executable, current owner return admission
is weakened, or source floors fail. #2909 aggregate proof and independent review
remain later owner obligations; no arbitrary broader suite is implied by their
absence from this implementation check.

## Current measurements and checks

The native capsule/return fixture reads exactly the startup, manual-delegation
and returned-result procedures (14,026 UTF-8 bytes). In the current Windows
sample, compact worker context is 2,826 bytes versus 6,866 legacy bytes, and new
return material is 106 bytes versus a 589-byte identity-bearing return. Skills
plus worker entry/return are 16,958 versus 21,481 bytes.

The complete fixture exposes the less flattering aggregate: six parent owner
calls return 663,594 bytes; return admission adds 131,653. Including these owner
responses and selected skills, total fixture context delivery is 812,205 versus
816,728 bytes, only about **0.55% lower**. Parent request envelopes add 11,814 bytes
and return admission adds 4,639 bytes, unchanged between presentations. These
counts describe an explicitly full-detail parent consumer; they are not hidden
host context or a claim that every ordinary client pays this cost.

Three helper calls (entry, optional exact expansion, return) add 56,170 bytes of
machine transport in this sample. The optional expansion is a fidelity check;
the small required source needs zero detail fetches in the ordinary path. Helper
elapsed times were 47.6 / 45.0 / 46.9 ms in one local sample, not a performance
threshold. Reducing worker model context increases transport; the result is not
an overall runtime-efficiency claim. The fixture supplies four bounded parent
answers and one worker material submission, with zero user steering, protocol
repair or worker file writes. Actual model turns, token counts, provider economics
and hidden host-injected context remain unknown. Negative probes are outside the
happy-path counts. No telemetry or new session registry is retained.

Existing operating-carriage measurement also remains green: direct full/compact
responses are 86,508 / 2,837 bytes; one carried answer is 114 bytes versus 4,241
bytes of copied answer/action protocol. Its carried answer performs two internal
resolutions versus one for full input (173.0 / 101.1 ms in that single sample).
That tradeoff is preserved explicitly, not advertised as fewer runtime calls.

Validation: 70 existing/extended Planning, capsule-return and operating-measurement
cases passed. After the final recovery and presentation changes, the affected
native creation/clone, former-owner continuation, worker CLI and operating
measurement cases passed again. Rust Planning/currentness selection passed
30 tests (two subprocess-only entrypoints ignored by design and exercised by
their parent fixtures); worker projection passed one contract; native CLI passed
six parser/real-transport tests. Both native binaries build together with the
locked workspace. Required formatting, lint/type and source checks run as normal
commit hooks. Ordinary CI gets no new test tranche.
