# Shared Rust core boundary

This reconstruction slice uses one executable authority for deterministic operating-decision semantics:

| Concern | Authority | Boundary |
| --- | --- | --- |
| Public contribution, action, outcome, blocker, decision, claim, and consequence shapes | `src/agentic_workspace/contracts/source_decision_contract.json` and its schema | Declarative JSON/JSON Schema only; it is not executable policy. |
| Normalization, exact identity, composition, terminality, and fail-closed ambiguity | `crates/agentic-workspace-core` | Implemented once in Rust. |
| Python access | `src/agentic_workspace/decision.py` | JSON process binding only. |
| Node access | `bindings/node/semantic-decision.mjs` | JSON process binding only. |
| JSON access | `agentic-workspace-core` stdin/stdout | Transport projection of the same Rust call. |
| Semantic applicability and acting-agent/human judgment | current typed context and the acting agent/human | Not inferred by the deterministic core. |

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

This slice advances #3020, #2987, and #2989. It does not close them or claim that built-in state owners have migrated.
