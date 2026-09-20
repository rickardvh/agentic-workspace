# Rust source builds and native artefacts

`rust-toolchain.toml` is the compiler and component authority for this repository.
Use ordinary `cargo` commands from the checkout; rustup selects and installs the
declared release, minimal profile, rustfmt and Clippy. Do not independently select
`+stable` in admission or release commands. Update the declaration deliberately,
then validate the locked workspace and native artefact set before acceptance.

Source-build compatibility is **the pinned toolchain only**. There is no lower
MSRV promise; the workspace metadata points to that same declaration instead of
duplicating a compiler version in both crates. Cargo.lock owns the resolved
dependency graph. Builds, tests and Clippy use `--locked`; formatting and Clippy's
`-D warnings` remain ordinary merge checks.

Both crates inherit `[workspace.lints]`; new members must opt in with
`[lints] workspace = true` as well. The workspace forbids unsafe Rust: current
native operations use safe dependency APIs and require no locally owned unsafe
implementation. `forbid` prevents a crate from silently allowing an exception.
A future unsafe requirement needs a deliberate workspace policy change and review.
Rustc and default Clippy remain the primary source lint stack, with warnings
denied by the ordinary Clippy command. No additional Clippy rules or broad lint
groups are enabled without a concrete uncovered invariant; blanket panic API bans
would conflate production behaviour with test assertions.

Native wheel/npm/archive producers reject a different observed compiler release
or a compiler wrapper/override. They record the declaration digest, observed
compiler version/commit/date/LLVM/host, explicit build target, Git source identity
when available, and existing binary hashes. Source archives carry the declaration
and build helper. Missing Git identity in an unpacked source archive is reported
as unknown, never borrowed from another build. These manifests describe build
observations; signed release attestations remain the provenance owner.

The current public preview artefact class is Linux x86_64 on the exercised Ubuntu
hosts, using the declared Python/Node combinations. Windows local builds exercise
Windows code, but do not establish a published Windows support class. macOS,
other architectures and libc compatibility classes remain unclaimed until
actual-host artifact/install evidence exists. Cross-compilation alone adds no
runtime-support promise. See [installation/support](../agentic-workspace-install.md).

Optional tooling disposition under #3246:

| Tool/change | Disposition and evidence boundary |
| --- | --- |
| Rustdoc strictness | Defer: the Rust crates are implementation substrate, with no supported public Rust API contract requiring exhaustive API documentation. |
| nextest | Defer: the observed long aggregate lane is Python/public handoff integration; no Rust test-runner bottleneck has been measured. |
| Cargo caching | Defer: existing uncached builds pass; no measured total-cost benefit justifies another retained cache/invalidation path. |
| Rust coverage | Defer: no named unprotected semantic class is answered by a percentage threshold. Use existing owner proofs. |
| Release-profile tuning | Defer: no measured artifact-size/latency tradeoff justifies changing the default profile. |
| Miri/fuzzing/vet/semver tooling | Not adopted: no current distinct required threat/failure class was established in this tranche. |

Rust advisory/license/source policy is enforced by `deny.toml` and the pinned
runner under the existing [security owner](../security/threat-model.md#rust-dependency-admission).
Security CI and both publishers execute it over the locked full workspace;
dependency review retains its distinct PR-delta/non-Rust role. #3246 still needs
independent acceptance of the combined substrate result; optional deferred tools
and unclaimed platforms do not become release blockers.
