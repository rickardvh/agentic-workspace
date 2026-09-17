# Native command boundary

`agentic-workspace` is the ordinary Rust CLI over one shared Rust authority.
Build both source-checkout binaries with `cargo build --locked --workspace --bins`.
Installed wheel, npm and host-labelled native archives carry the paired CLI/core;
see [release topology](../maintainer/native-release-topology.md) for provenance
and the supported artifact boundary.

The CLI owns argument parsing, JSON transport, rendering and exit codes. Its
public command and option declarations come from `source_decision_contract.json`:

| Command | Current purpose |
| --- | --- |
| `start` | Resolve current owner information, requests and available effects. |
| `invoke` | Execute an exact action returned by its current owner. |
| `worker` | Project sealed Assignment input or assemble unproven return re-entry. |
| `resources` | Inspect hygiene and propose or execute an admitted resource operation. |
| `proof-procedure` | Prepare selected proof context or execute and admit one exact native check. |

`start --target <repository> --task "<task>" --format json` reads current owner
sources. Repeated `--changed` arguments declare changed paths. Supply a returned
request through `--input <file>` or JSON stdin with `--input -`; a bounded array
can preserve distinct owner answers. `invoke` accepts the exact returned action.
Clients cannot invent source admission, custody, capability contracts or proof.

Python `agentic_workspace` and the installed npm root/`./operating` exports
project `start`, `invoke` and the reference/carriage helpers. The npm `./native`
export provides low-level JSON transport. JSON and native entry independently
consume the same Rust authority; no binding supplies a parallel domain runtime.
The native executable does not launch Python or Node to decide semantics.
Missing or incompatible paired cores fail explicitly, without source-build or
alternate-runtime fallback.

Compact, full and carried views preserve current requests, restrictions and
available effects. Owner details omit internal contribution objects; composed
blockers and actions identify their owner. Exact references and disposable
carriage avoid reconstructing hidden fields. Delivery suppresses unchanged
source prose only; it grants no compliance, mutation, proof or completion claim.

Current native owners cover configuration, instruction/source reconciliation,
Planning, Memory and repository decisions, Verification, Assignment and bounded
delegation. Read current capability dispositions rather than treating discovery,
owner quiescence or process success as completion. See
[execution configurations](../maintainer/native-execution-configurations.md),
[proof execution](../maintainer/native-proof-execution.md), and the canonical
[workspace procedure](../../.agentic-workspace/skills/workspace-startup/SKILL.md).
Unsupported transport/result classes remain explicit gaps. Semantic judgment,
independent review and human approval retain their own authority.

`tests/test_native_public_cli.py` and existing native owner scenarios exercise
fresh native/JSON/Python/TypeScript consumers, real former/current sources,
currentness, exact replay and claim-sensitive negatives. Exhaustive artifact mode
runs those consumers outside the checkout against one packaged set. Command proof
reuse additionally binds the actual core location: byte-identical installations
at different locations cannot silently inherit each other's receipts.
These checks do not grant independent acceptance, live-provider success or
first-stable admission.
