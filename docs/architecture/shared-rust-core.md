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

Typed public requests are likewise selected outside the deterministic core. A request names one declared owner operation and request kind, carries only arguments admitted by that declaration, and is bound to the current-work, capability-contract, capability-owner, and source-contribution revisions. The Rust core requires exactly one response from that owner and projects whether it returned an exact action, a bounded decision, a blocker, or a settled result. An unknown request field or variant fails closed; arbitrary owner dictionaries and generic caller-selected operation names are not a public language.

The capability contract is separate from a module contribution so a contribution cannot manufacture its own authority. It assigns every declared domain and effect to one owner, assigns every authority-bearing operation to that owner, and records one exclusive owner for each grantable claim. Rust rejects conflicting domains/effects/claims, undeclared response operations, cross-owner effects, self-widened action authority, and claims or outcomes granted by a non-owner. Blocking a known claim remains a constraint, not a grant. Cross-owner evidence must become a new typed request admitted by the responsible owner; this slice does not add a central choreography registry.

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
| Baseline source-first module/request seam | ADAPT | Public constructibility and capability ownership move into the declarative contract plus Rust validation; arbitrary raw-intent and self-declared authority behavior is not ported. |
| Historical operation IR plans and target executors | EVIDENCE / DROP later | Existing contracts inform request/effect inventories, but executable steps do not become a second runtime or public request DSL. |

This slice advances #3020, #2987, and #2989. It does not close them or claim that built-in state owners have migrated.

The stacked #2930 slice adapts the pre-contraction route identity/currentness contract but drops its local selection file and handwritten Python/TypeScript route runtimes. Progressive vocabulary discovery remains a host/declarative concern; repository-control, Memory, Verification, and other owner consumption remains with their owning issues.
