# Native command boundary

The source-built `agentic-workspace` binary is an adapter over the shared Rust
authority. Build it with `cargo build --locked -p agentic-workspace-cli`.
The CLI crate owns argument parsing, JSON transport, rendering and exit codes.
Public commands and argument declarations come from `source_decision_contract.json`.

`agentic-workspace start --target <repository> --task "<task>" --format json`
reads current owner sources and returns a decision. Repeated `--changed` arguments
declare the changed paths. Supply a returned public request through `--input <file>`
or JSON stdin with `--input -`; a bounded array can preserve distinct owner answers.
`invoke` accepts the exact returned operation invocation through the same input.
Clients cannot supply source admission, custody, capability contracts or debug facts.

Python `agentic_workspace.decision.start`/`invoke`, the corresponding exports in
`bindings/node/semantic-decision.mjs`, and JSON `start`/`invoke` independently consume
the same Rust ingress. The native executable does not launch Python or Node.

Current native source ingress covers semantic route discovery, configured decision
provenance, shared/local configuration visibility and restrictions, the selected
Planning owner, Planning reconciliation custody and conservative Verification
evidence visibility. Planning writes retain the existing owner selection, preserve
former source bytes, acquire custody before writing, revalidate before commit, and
replay only an admitted current result. Direct-task identity has one Rust owner
shared with the existing Python consumer.

This is not the ordinary repository CLI cutover. Unsupported configuration controls
remain explicit owner gaps. Full Verification strategy/evidence and returned judgment
admission, delegation, other owner operations, packaging and platform admission remain
incomplete. The trusted development core executable is not a public substitute for
these missing operations. The repository adapter retains its configured invocation
until the representative stateful gate and ordinary operation coverage are complete.

Proof lives in `tests/test_native_public_cli.py`, the CLI transport tests and the
native owner tests. Fresh processes exercise all four consumers, including the native
binary with an empty executable search path, a real former Planning source, exact
replay and unrelated claim-sensitive work. Passing these checks does not grant
independent review, supported-provider success or first-stable admission.

Native scoped instructions use the same Rust applicability owner as Python:
path scope and current semantic route scope are both required. Current guidance,
read references and preferred procedures grant no execution or proof authority.
Hard checks/protection retain immutable source admission. Planning reconciliation
also checks its actual bounded write set (including custody and temporary files),
so omitted task paths cannot bypass protection. Character classes share the same
path matcher with native Verification. Discovery creates no state.

A shared-source Planning continuation acquires absent local selection and retains
attempt custody inside the same `planning.reconcile` operation. A pre-existing
source-only local selector remains readable but cannot be overwritten merely
because its shape is valid. Its current owner must admit transfer; that native
transfer route remains unresolved. Current producer custody supports exact replay
and fresh-process continuation. No caller-authored local selector is needed for
the shared-source journey.

For semantic lifetime, source applicability is recomputed from bounded current
inputs; retaining its result would add custody and invalidation work to a cheap
calculation. Planning derives current subject meaning from its stronger source
owner and reuses only exactly admitted effect/attempt custody. A historical next
decision is never retained as current authority. These choices do not complete
#2981's remaining measured expensive-proof and negative-result reuse evidence.

Memory discovery reads the existing manifest only for current path/semantic-route
signals and returns bounded advisory source references. A returned
`memory/read-current-note/v1` request retrieves one selected exact revision in a
fresh process. Neither the manifest's canonical label nor a matching content hash
proves factual freshness; unadmitted freshness and promotion stay explicit. Note
bodies are omitted from initial discovery. Malformed advisory sources produce
Memory diagnostics while direct work remains available; explicit stale or
out-of-scope read requests fail closed.
