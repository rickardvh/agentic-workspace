# Native route discovery in the workspace npm artefact

Compiler selection and source-build compatibility follow the shared
[Rust toolchain contract](rust-toolchain.md). Native manifests carry that exact
compiler identity alongside the existing host and executable digests.

The workspace npm release asset includes the same Rust core used by the Python binding. `instructions routes` reads canonical skill registries through that core; root and branch results contain identities, and exact discovery expands only the selected leaf metadata. The `./native` export exposes the existing thin start/invoke binding.

Stage the current build host artefact with `python src/tooling/release/stage_native_npm.py --output <absent staging directory>`, then run `npm test` and `npm pack` in that directory. Cargo receives its explicit Rust host target. Staging rejects Rust/Node host mismatch and unequal product/package versions. The staged package declares its actual OS and architecture; its binding checks the package version, platform and executable digest before use. The manifest records build context and artefact integrity, not signed or independent provenance. Source archives retain the inputs; they do not embed build output. Unstaged generated development consumers may explicitly set `AGENTIC_WORKSPACE_CORE_BINARY`; this does not claim package provenance or self-sufficient installation. Staged artefacts require their manifest even when that development override is present.

This slice proves one actual build host. The current release workflow stages its own host artefact; it does not create an artefact set for every OS or libc class. Existing wider release-platform claims need corresponding artefact builds and isolated proof before promotion.

The legacy TypeScript `instructions select-route` operation now reports an explicit unavailable mutation and preserves existing selection bytes. Its result points to the installed `@agentic-workspace/workspace-cli/native` start API: supply the exact current task, inspect the returned `semantic-routes/select/v1` request, and submit the current request with agent-selected posture/routes. This resolves current applicability only; it does not pretend to complete the old persistent write. Former selection reconciliation remains with the native source owner. Other retained target-language instruction behaviour and package-topology work remain open under #2930, #2985 and #2987.
