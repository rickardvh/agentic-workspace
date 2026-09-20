# C53 architecture, conformance and public truth

## Exact source and review boundary

Priority 6 under #3207 rechecks integrated source
`4d3a21caded4bce3967eaf4a49f0929185422d58`, tree
`2231dc2c2f91735012e0a2e05642f899a92e0d66`. This is the merge of independently
accepted #3233 head `15bd9d8e96b0fc7db2f92231f0cb9a8dc3c56000` into
`reconstruct/first-stable`. Its accepted CI/security/semver runs are recorded in
#3233. Runtime sources, native declarations, package payloads and bindings are
unchanged by this Priority 6 PR. The documentation generator and two existing
proof guards are corrected here; their evidence is patch evidence, not a claim
that the unchanged baseline already passed those stale guards.

This report is implementation-owned preflight, not independent review. After this
PR is reviewed and merged, the release owner must select/rebind the final exact
C53 source including these public docs. A runtime-equivalent base is not a receipt
for a different complete tree. P53 normalisation, publication and public-byte
install proof remain Priority 7. Do not check candidate rows or close #3207 from
this report alone. No support-bearing admission is claimed.

## Architecture disposition (#3020)

The [authority graph](../architecture/shared-rust-core.md) separates declarative
contracts, one Rust executable owner implementation, domain/source authority,
transport and agent/human judgement. Current native `start`/`invoke` use that core;
`resources` and `worker` are bounded tools over its existing owners. Skills are
procedure and selective disclosure, never a second runtime or mandatory phase
model. No runtime code or capability branch is added here.

The existing anti-wrapper guard now admits only the bounded transport added by
accepted carriage/artifact work: a Python unknown-key rejection before forwarding,
its Node equivalent, and paired-binary validation/argv forwarding. All other
exported domain functions still forward to the core, forbidden semantic vocabulary
remains rejected, and the CLI cannot link or call a second domain runtime.
Shared Rust/Python/Node/JSON vectors cover currentness, request constructibility,
error equivalence and selected-outcome authority. Independently linked-owner
recovery and responsible Planning consumption exercise capability-first ingress.
Historical Python lifecycle/generated command machinery has no native fallback
authority. The public catalogue now derives from `source_decision_contract.json`,
the same native declaration used by the executable, rather than its historical
128-command predecessor. No general executable DSL or lifecycle engine is added.

## Selected aggregate journeys (#2909)

These existing owners supply shared evidence across the checklist; this is not a
new test suite, execution engine or ordinary-CI tranche.

| C53 claim | Current owner evidence | Downstream consequence and limit |
| --- | --- | --- |
| Fresh tiny bootstrap/main skill, selective known leaf | `test_skills_first_interface.py` | Fresh native/JSON/Python/Node consumers reach a bounded Configuration write; stale work/procedure invalidates reuse. Skills alone grant no claim. |
| Local/shared correction, policy and fresh delivery | `test_native_instruction_write.py` | Exact publication, protected source, interruption, changed-byte preservation and shared-source portability. |
| Current config, source/proof/claim distinction | `test_native_claim_review.py`, core Configuration/Verification contracts | Process success is insufficient; current judgement, source obligations, Planning residuals and independent-review ceilings survive. |
| Quiet direct/no-signal work and burden | `test_operating_journey_measurement`, fresh native source observation | Empty target is direct and leaves zero files. Full/compact costs and internal call tradeoffs remain visible. |
| Opaque entry and global currentness | `test_global_reconciliation_observes_opaque_new_work` | Newly observed work requires current source reconciliation rather than history-based permission. |
| Portable Planning and worker context | Native creation/clone and capsule/typed-return journeys | Fresh process/environment recovers meaning with new local custody; worker returns remain unproven until current owner admission. |
| Returned work and local quiescence versus whole outcome | Planning-owned patch integration, independent-result consumption, claim-review tests, shared outcome vectors | A finished process/owner/patch is not completion of selected work; pending integration, proof and parent residuals remain. |
| Structured local resources/isolation | Scratch ownership/cleanup and worktree policy/teardown journeys | Owned scratch can be cleaned; unknown ignored or unleased/tracked content remains. Required policy and teardown are exercised. |
| No-runtime behaviour | Canonical main skill static fallback and interface conformance | Selective read-only source orientation only. Executable authority, retained corrections, proof and provider state remain unknown. |

The shared outcome vectors include `owner-settled-is-not-terminal`,
`request-settled-is-not-owner-quiescence`, `explicit-current-outcome-is-terminal`,
`stale-outcome-evidence-is-not-terminal`, required-claim/residual/task-blocker
negatives and unrelated/optional-consequence controls. Native material owners add
Planning residuals, Verification insufficiency, Assignment return/integration and
independent-owner consumption. This factors shared terminality semantics instead
of repeating every permutation across every adapter. Memory's advisory and exact
publication/disposition contracts remain separate from proof/completion authority.

The complete selected skill/worker/parent burden in [Priority 5 evidence](../priority5-validation.md)
remains the measured reference: only 0.55% lower full-fixture context despite much
smaller worker presentation, with extra machine transport. This recheck reruns the
operating measurement but does not manufacture hidden-host token/semantic-turn
measurements, real-provider economics or a universal agent-efficiency claim.

## Exposed effect and preservation dispositions (#3000/#3001/#2984)

The fresh native capability declaration exposes Configuration write/recover/defer,
Planning reconcile/create/update/recover, Verification report/source reconciliation,
instruction write/recover, Assignment patch integration and Delegation dispatch.
Configured Memory and independent owners add only admitted bounded effects;
Resources has its own dedicated local-resource boundary. Reading this inventory
is not an authorisation to invoke an operation.

| Effect family | Safety disposition | Recheck contribution |
| --- | --- | --- |
| Configuration and instruction publication | Exact source/policy admission, retained pre/postimage and common attempt custody; occupied or changed content is preserved. | Core interruption contracts and native instruction write/recovery/protection. |
| Planning create/reconcile/update | Creation while absent or exact owner/explicit transfer; local execution remains target-bound. Portable observations never import executable custody. | Core selection/update interruption and native fresh-consumer/partial-loss/recovery. |
| Memory publication/disposition | Explicit bounded source authority; unknown source bytes and policy drift fail closed. | Core capture interruption and disposition/policy-drift contracts. |
| Proof process and receipts | Attempt precedes execution; unknown outcome cannot relaunch; exact committed outcomes replay. | Actual process interruption and concurrent same-effect native proof tests; core publication/recovery contracts. |
| Delegation process/patch return | `native_delegation` admits the immutable attempt and creates its carrier before `process_execution::run`; a non-execute/non-replay admission returns uncertain, never another launch. Patch uses exact captured baseline and preserves concurrent work. | Native execute-once/current-result journey and Planning-owned patch replay/integration; source audit of the prelaunch ordering. |
| Independent owner | Common custody/current authority, exact recovery and responsible-owner result consumption. | Native independently linked recovery and Planning integration. |
| Scratch/worktree removal | Current leased resource identity, policy, exact registration and owned content; unknown ignored/tracked/unleased files are preserved. | Native scratch cleanup/preservation and worktree teardown. |
| Legacy/package cleanup | `workspace.remove-legacy` is absent from native commands and operations. Historical path recognition cannot create an action or prefilled destructive confirmation. | Native command declaration, retired-command controls, exact source-lifecycle byte preservation and current owner acquisition tests. |

This dispositions the exposed C53 surface; it does not close broad historical
safety owners or restore retired cleanup mechanisms. A future effect must supply
its own current owner evidence. Preview status waives none of these boundaries.

## Public truth (#2616)

README, installation, overview, everyday examples, evidence/trust and the native
reference now teach one canonical skill plus exact tools. Copyable instruction
material is kept separate from publication authority. The CLI catalogue removes
over 1,900 lines of misleading historical commands and its existing freshness
check remains binding. The installed-surface catalogue is refreshed and explicitly
labels source-maintenance lifecycle profiles, not available native initialisation.
The installation guide reports the missing native adoption command rather than
using an old host. Current source use and future public-byte installation are
separate claims. #2616 final support/platform reconciliation remains with #2990.

## Proof and retention disposition

The runtime recheck uses existing owner/contract tests; no permanent aggregate
suite, matrix generator or recurring CI work is added. The catalogue test changes
its authority from the retired command manifest to the live native declaration.
The existing architecture guard changes only for the accepted bounded transport
forms and keeps its no-domain-semantics checks. These are maintained behavioural
boundaries, not incident-specific regression additions.

Stop after the selected risks and normal commit checks pass. Escalate a concrete
failed safety/currentness/constructibility path to its smallest owner; do not
substitute a generic all-tests run or historical migration failures for current
candidate evidence. Independent final-tree acceptance and Priority 7 artefact
proof are explicit remaining release-owner work, not silently passing results.

## Current run results (2026-09-13, Windows x86-64)

- Locked workspace build of both native binaries passed.
- `cargo test --locked -p agentic-workspace-core --lib`: 118 passed; three
  subprocess entrypoints ignored as designed and exercised by their parent tests.
- `cargo test --locked -p agentic-workspace-core --test vectors`: four passed,
  exercising the shared success/error/currentness corpus.
- 32 selected interface, instruction, claim, scratch, portable-continuation,
  worker and independent-owner public cases passed in 55.04 seconds.
- Six shared-binding/constructibility/process cases passed before catalogue
  freshness exposed stale installed-surface output. Both catalogue authority and
  output were corrected; all four catalogue tests pass.
- The final 12-case group (including those four catalogue cases) passed in
  66.24 seconds: real proof interruption/concurrency, Planning patch integration,
  opaque source reconciliation, worktree policy/teardown and three independent
  recovery boundaries. There are 50 distinct selected Python cases overall.
- `agentic-workspace --help` matches the four-command generated native reference;
  a fresh temporary target returned direct and left zero files.

The wrapper guard initially failed on accepted transport functions; its bounded
exceptions were corrected rather than weakening domain-authority restrictions.
The old generated catalogue initially failed currentness; regenerated source-
maintenance output remains distinct from public native adoption support.
These diagnostic failures are resolved patch findings, not erased historical
successes. Normal commit formatting/lint/type/path checks are also required.
No new ordinary CI constituents or permanent aggregate tests were retained.
