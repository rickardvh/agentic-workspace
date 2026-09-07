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
