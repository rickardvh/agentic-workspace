# Shared Rust core boundary

This reconstruction slice uses one executable authority for deterministic operating-decision semantics:

| Concern | Authority | Boundary |
| --- | --- | --- |
| Public contribution, action, outcome, blocker, decision, claim, and consequence shapes | `src/agentic_workspace/contracts/source_decision_contract.json` and its schema | Declarative JSON/JSON Schema only; it is not executable policy. |
| Public request, capability, domain, effect, operation, and exclusive claim-authority shapes | The same declarative contract and schema | Describe constructible data and ownership only; they contain no operation algorithm or choreography. |
| Normalization, exact identity, composition, terminality, and fail-closed ambiguity | `crates/agentic-workspace-core` | Implemented once in Rust. |
| Python access | `src/agentic_workspace/decision.py` | JSON process binding only. |
| Node access | `bindings/node/semantic-decision.mjs` | JSON process binding only. |
| JSON access | `agentic-workspace-core` stdin/stdout | Transport projection of the same Rust call. |
| Semantic applicability and acting-agent/human judgment | current typed context and the acting agent/human | Not inferred by the deterministic core. |

Semantic route selection is ephemeral input, not a task classifier or history. The acting agent chooses a declared route; the Rust core only verifies that the fact is bound to the supplied current-work identity and current route-source revision, rejects removed/unknown routes, canonicalizes route order, and projects the fact with an `applicability-only` authority ceiling. Task prose alone never creates a route fact, and route selection cannot add actions, effects, or claims.

Typed public requests are selected outside the deterministic core. A request identifies an owner and intention kind, carries arguments validated against that owner's declared JSON Schema, and binds to the current-work, capability-contract, capability-owner, and source-contribution revisions. Requests are declared independently of operations. The responsible owner derives the exact operation and effect-bearing arguments, or returns a bounded decision, blocker, or settled response. Rust requires exactly one response from that owner and validates the derived action against its separately declared operation schema and effect authority. For example, an intention with `subject: {name: "case-17", mode: "finish"}` may resolve to `example.finish` with `subject: "case-17"`; the caller supplies neither the operation ID nor its exact arguments.

Request and operation `input_schema` values are self-contained JSON Schema Draft 2020-12 documents carried in the revision-bound capability contract. The Rust `jsonschema` validator checks schema validity and instances, including nested properties, enums, composition, and local `$defs`/`$ref`. External HTTP/file retrieval is disabled. Schema authors close bounded request objects with `additionalProperties: false` or `unevaluatedProperties: false`; no parallel AW type vocabulary exists. The existing input revision digest includes these schemas. Unknown public request fields (including a caller-supplied `operation_id`) and undeclared request kinds fail closed.

The capability contract is trusted admission input, separate from implementation descriptors and source contributions. It assigns every declared domain and effect to one owner, assigns every authority-bearing operation to that owner, and records one exclusive owner for each grantable claim. Rust rejects conflicting domains/effects/claims, undeclared response operations, cross-owner effects, self-widened action authority, and claims or outcomes granted by a non-owner. Cross-owner evidence must become a new typed request admitted by the responsible owner; this slice does not add a central choreography registry.

Pure current-work facts and direct/no-signal decisions need neither a capability contract nor semantic-route classification. Progressive contract discovery and real first-party owner consumption remain later #2930/#2986/#2606 work. The existing Python module runtime and historical operation IR are transition evidence, not new authority; they are not deleted until their owners migrate through #2984/#3000/#3001.

The candidate initial matrix is the repository's support-bearing hosted Linux x86-64 lanes (Python 3.11/3.13 and Node 20/24) and Windows x86-64 lane (Python 3.14 and Node 24), all on Rust stable. A cell is admitted only after its support-bearing core and binding checks pass; toolchain availability alone does not admit another platform. Native artifact bundling and final release support remain owned by #2985/#2987.

## #3018/#3019 disposition

| Component | Disposition | Result here |
| --- | --- | --- |
| Contribution/outcome/claim/action vocabulary and exact typed shapes | ADAPT | Kept as the smaller declarative contract and schema. |
| Settled-versus-terminal, explicit current outcome authority, hostile-priority rejection | PORT semantics | Implemented once in Rust with shared vectors. |
| Selective consequence scoping, bounded decisions, lossless alternatives and recovery | PORT semantics | Implemented once in Rust; pending actions now remain explicit too. |
| Exact action identity review correction | ADAPT | Revision-bound digest includes owner, operation, arguments/targets, effects, and authority. |
| Python/TypeScript parity tests and installed-surface intent | EVIDENCE | Replaced by black-box Rust/Python/Node/JSON execution of one core. |
| Executable JSON expression program and dual evaluator/templates | DROP | Not carried into this branch. |
| Generated schemas/types/builders and package/conformance machinery | ADAPT later | Retained as downstream #2985/#2987 input; no executable target runtime is added here. |
| Baseline source-first module/request seam | ADAPT | Public constructibility, baseline `Operation.input_schema` Draft 2020-12 validation, and capability ownership move into the declarative contract plus Rust validation; arbitrary raw-intent and self-declared authority behavior is not ported. |
| Historical operation IR plans and target executors | EVIDENCE / DROP later | Existing contracts inform request/effect inventories, but executable steps do not become a second runtime or public request DSL. |

This slice advances #3020, #2987, and #2989. It does not close them or claim that built-in state owners have migrated.

The stacked #2930 slice adapts the pre-contraction route identity/currentness contract but drops its local selection file and handwritten Python/TypeScript route runtimes. Progressive vocabulary discovery remains a host/declarative concern; repository-control, Memory, Verification, and other owner consumption remains with their owning issues.

## Post-#3025 restriction correction (#2606)

Restriction authority is separately admitted in `capability_contract.restriction_authorities`: each entry names an admitted `owner` and an `affects` set using the existing exact consequence vocabulary. Blocker and bounded-decision scopes, plus `claim:<name>` for each blocked claim, must belong to that owner's grant. Claim-grant authority and effect/state ownership imply no veto; restriction implies no grant or mutation authority. `task` explicitly permits a task-wide constraint and is not a wildcard for other scopes. A policy owner can be granted `effect:planning-state` without owning Planning state. Multiple restriction owners may constrain the same consequence. Blockers cannot impersonate another owner. Unknown claim/effect grants, absent owners, and removed grants fail closed; exact action/decision/outcome targets can be admitted before their consequences appear.

This is a deterministic admission check, not authentication of caller-supplied JSON. Hosts must supply the current contract from trusted authority, never assemble grants from arbitrary installed code declarations. The normalized contract, including restrictions, participates in the existing composed input digest. Acquiring trusted authority from real former sources, revocation/disappearance handling, and durable invocation revalidation remain #2606/#2984/#3000 work.

The #2909 ratchet consumes the restriction vectors in `tests/vectors/source_decision.json` through the existing Rust vector suite and `tests/test_shared_core.py` Python/Node/JSON checks in the hosted core lanes. They reject self-granted vetoes, cross-domain and task widening, bounded-question bypass, blocker-owner impersonation, removed grants, and claim/effect acquisition through restriction. Positive proof retains exact selective blocking and demonstrates externally granted cross-owner restriction. These are kernel regressions, not former-source or first-party migration closure evidence.

Remaining correction ownership before broad stateful migration:

| Owner | Confirmed remaining coupling / boundary |
| --- | --- |
| #2987, consumed by #3000/#2981 | Action-local dependency revisions and logical effect generation are separated below. Real source derivation and durable execution-attempt/recovery identity remain unresolved. |
| #2989 | Known independent actions form a ready set as described below; terminality now uses outcome-owned required claims and residual work, as described below. Real owner journeys remain unresolved. Existing explicit outcome authority, settled/direct distinction, and fail-closed conflicting actions are retained and tested. |
| #2986 | Response admission still checks caller request ID and infers response consequences from the whole owner contribution. Complete normalized request binding and request-local consequence selection remain unresolved. The intention-to-owner-derived-operation model and schema validation are retained. |
| #2606 | Trusted source acquisition/currentness, capability disappearance, cross-owner worker evidence admission, state custody, and real first-party consumption remain unresolved. This slice only removes implicit restriction authority in the shared kernel. |

This slice closes none of those issues. It makes #2984/#3000/#3001 safer by requiring explicit restriction admission before migrated owners or persisted decisions can treat contributed vetoes as authority. It does not make broad stateful migration ready by itself, and adds no alternate runtime, scheduler, policy language, registry, or durable state.

## Material action currentness (#2987)

Every owner-derived action supplies `dependency_revision`, the revision of its material subject/source/policy dependencies, independently of the enclosing contribution revision. Owners must derive this from actual current material inputs, including work identity when it changes applicability; omitting a material input is an owner contract violation. Rust binds that revision to the exact declared operation schema/result/effect/claim contract and effect custody. The aggregate decision `input_revision` still identifies the entire composed view, but is absent from the returned invocation.

`expected_dependency_revision` and the exact `consequence_id` bind current action admission. `idempotency_key` identifies the logical owner/operation/arguments/ordered effects/authority plus optional `effect_generation`. A changed material dependency invalidates the invocation without inventing another effect. Repeating the effect requires the owner to return a new generation. Clients cannot choose generation or any other effect-bearing field at invocation time. Empty/absent generation means the initial effect. Distinct attempts do not create distinct logical effects; attempt identity and durable receipts are deliberately left to #3000.

Python `admit_invocation`, Node `admitInvocation`, and JSON `{ "admission": { "decision": <fresh trusted decision>, "invocation": <exact returned action>, "previous_invocation": <trusted receipt invocation or null> } }` execute one Rust admission check. They are host boundaries: the decision must be freshly resolved from current sources, and a previous invocation must come from trusted receipt custody. Callers cannot use a supplied decision as proof of their own authority. Admission returns `execute` or `replay`, never performs an effect, and rejects any changed or unknown invocation field. A trusted exact receipt can replay after the action disappears, without re-execution. A freshly authorized invocation for the same logical effect can likewise reuse the receipt despite changed dependency currentness. The existing Python callback dispatcher consumes this check; its process-local receipt store is not durable #3000 recovery proof.

The #2909 shared vector and Rust/Python/Node tests prove unchanged exact action across unrelated owner/view churn, relevant dependency rejection before callback execution, stable logical identity across dependency changes, tampering rejection, and owner-authorized repetition. No real former-source owner migration or issue closure is claimed.

## Independently ready actions (#2989)

`ready_actions` contains exact invocations available for agent/client choice. `primary_action` remains the single-action projection only. With multiple available actions, Rust checks every pair against the admitted operation contract: optional `reads` declares the complete material read-domain footprint, and the full operation effect ceiling supplies write domains through existing exclusive effect custody. No write may overlap another action's reads or writes. Missing `reads` means unknown; it does not mean read-free. A false or incomplete footprint is an admission/owner contract violation, not a grant the implementation may self-assert. Changed footprints also change material action currentness.

Unknown or conflicting relationships retain a fail-closed composition blocker and lossless alternatives. The core does not rank, schedule, execute concurrently, or truncate alternatives. A client chooses one exact ready action and re-resolves after its result. Rust invocation admission checks membership in that current ready set. #2909 shared cases cover independent actions, unknown footprints, read/write and write/write conflicts, permutation stability, and public Python/Node exact choice. Real owner footprint derivation remains owner migration proof; this slice closes no issue.

## Selected-outcome closure (#2989)

A current authoritative outcome closes when its own status, claim evidence, and residual work establish completion. Optional `required_claims` names additional claims that must be currently allowed by their admitted owners; missing owners, missing evidence, blocked claims, and constraints on these claims cannot waive an obligation. The outcome owner must include every unfinished required task in existing `residual_work`, even when another owner will perform it, and must bind that conclusion to current evidence. Dependency completeness is an owner responsibility, not inferred from module installation or an action census.

Optional or unrelated actions, questions, advice, and claim gaps remain in pending detail. They no longer veto an otherwise complete selected outcome. An admitted task-wide restriction still prevents terminality. A synthetic conflict between optional actions affects those exact alternatives, not the entire completed outcome. Terminal views have no primary action; any independently ready optional invocations remain available by explicit choice. #2909 shared vectors cover pending optional action/conflict, missing and blocked required claims, current required proof, residual required implementation, genuine task blockers, and unrelated claim gaps. Owner-local settled state still grants no task terminality. This is kernel proof, not #2989 or real Planning/Verification journey closure.
