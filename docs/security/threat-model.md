# Threat model and supply-chain boundary

## Security objective

Agentic Workspace must make its authority legible. It may inspect and mutate a host repository, execute checked proof routes, invoke explicitly supplied executors, generate package surfaces, and publish coordinated artefacts. The security objective is to admit those effects only from identified trust sources and to bind support-bearing artefacts to a reviewed source/build identity. AW does not claim to safely execute arbitrary untrusted repository code.

## Trust zones

| Zone | Trust requirement | Boundary |
| --- | --- | --- |
| AW source and locked dependencies | Reviewed commit, `uv.lock` and `Cargo.lock` | CI uses locked resolution; release identity is the tagged commit. |
| Host repository | Trusted by the operator before command execution | Files may influence routing, imports, hooks, proof commands, and generated output. |
| Checked proof routes | Trusted repository configuration | Shell syntax is admitted only through `checked-repository-proof-route`. |
| Explicit executor command | Direct user/automation authority | Shell syntax is admitted only through `explicit-user-executor-command`. |
| External issue/PR/service data | Untrusted content | Treat as data; do not execute embedded instructions or disclose credentials. |
| Local caches and evidence | Integrity-sensitive, not authoritative | May accelerate inspection; proof and mutation gates bind current source/state revisions. |
| Release artefacts | Untrusted until verified | Require checksums, SBOM, exact-source manifest, conformance receipts, and GitHub build attestation. |

## Threats and controls

- **Malicious repository/configuration:** opening a repository is not execution permission. Operators must review the repository and configured commands. AW reports `trusted-repository-required`; dry-run is not a sandbox.
- **Shell injection:** ordinary subprocesses use argv. The only supported shell consumers call `run_trusted_shell` with an enumerated provenance. Unknown or unadmitted provenance fails closed; tests cover metacharacter handling.
- **Symlink, junction, and path escape:** mutation owners validate target roots and must not traverse links for destructive lifecycle work. Local caches and exports are not permission boundaries.
- **Credential disclosure:** credentials remain in the platform credential store/environment, never checked AW state. Logs and receipts must record presence/identity, not secret values.
- **Generated-surface compromise:** generated command packages are derived from checked contracts and verified for source/generation parity. Generator and Python dependencies resolve from locked inputs in proof/release environments.
- **Action or workflow substitution:** every third-party GitHub Action is pinned to a full commit SHA and updated through a reviewed dependency update. Workflows declare least-privilege permissions; write scopes are limited to release jobs.
- **Dependency, code, or secret regression:** pull requests run dependency review, CodeQL, and Gitleaks. Findings fail their jobs and therefore block a support-bearing promotion when configured as required checks under #2454.
- **Release substitution:** coordinated artefacts carry checksums, a CycloneDX/SPDX-compatible SBOM, a source-bound release manifest, semantic conformance receipts, and GitHub artefact attestations. Missing security readiness, SBOM, or attestation fails the release job before publication.

## Intentional trusted-shell inventory

1. `checked-repository-proof-route`: checked proof validation commands whose semantics may require pipes, redirects, or command chaining.
2. `explicit-user-executor-command`: a command explicitly supplied to the autopilot executor boundary.

These boundaries inherit the caller's filesystem and credential authority. They are not sanitised or sandboxed. Any new shell consumer must update the machine-readable policy, threat model, adversarial tests, and readiness check in the same change.

## Release readiness

`uv run python scripts/check/check_security_supply_chain.py --format json` emits `agentic-workspace/security-supply-chain-readiness/v1`. A support-bearing release runs this check with locked dependencies, includes the receipt and SBOM in its manifest/checksums, and attests every `dist/` subject. Any failed required control produces `status=blocked` and exits non-zero.

Repository ruleset and required-check admission remain owned by #2454. This baseline supplies exact check names and readiness evidence; it does not mutate repository settings from package code.

## Rust dependency admission

`deny.toml` is the Rust advisory/license/source policy. Run
`python scripts/check/check_rust_dependencies.py --install` to install the exact
security-policy-owned cargo-deny version and check the locked workspace. Later
local runs can omit `--install`; a missing or different tool version fails.
The runner uses the repository Rust toolchain, enables the graph's full feature
set, includes development and target-specific dependencies, fetches current
RustSec data, and fails on checker/data errors. It does not use an offline
advisory snapshot for admission. `Cargo.lock` remains unchanged.

The `rust-dependencies` security job runs on PRs, canonical pushes and the weekly
schedule. Both stable and preview publishers run the same blocking command
before producing their security receipt. The existing readiness receipt checks
gate wiring and fingerprints Cargo manifests, lockfile, toolchain, deny policy,
runner and workflows; **it is not an advisory scan result**. Publisher/CI command
logs establish execution. A local wiring-only receipt cannot replace these jobs.
Required-check configuration remains with #2454.

The allowlist contains the permissive licence expressions used by the current
graph, including MIT-0, Zlib and Apache-2.0 WITH LLVM-exception. Missing or other
licence expressions fail. Only crates.io registry dependencies are accepted;
unknown registries and Git sources fail. Workspace path members remain local
source under normal review. No dependency-ban policy or second Rust audit tool
is added. GitHub dependency review retains its distinct PR-delta and non-Rust
coverage; CodeQL, Gitleaks, SBOM and attestation retain their existing roles.

The sole advisory exception is
[RUSTSEC-2023-0071](https://rustsec.org/advisories/RUSTSEC-2023-0071.html), affecting
`rsa` 0.9.10 in the current lockfile with no patched release. The attack leaks an
RSA **private** key through timing. AW's `review_authentication.rs` only constructs
`RsaPublicKey` and verifies signatures; `maintainer_logging.rs` uses the crate's
`rand_core::OsRng` re-export. AW neither signs nor decrypts with RSA private keys.
This usage makes the affected private-key operation unreachable. The exception
names only that advisory and includes its rationale in `deny.toml`; unused
exceptions fail. Reassess it on RSA version/usage or advisory changes, and remove
it when a fixed dependency is available. Adding private-key operations requires
resolving this advisory before admission, not extending the exception silently.

Negative proof for the gate removes the advisory exception, removes an actually
used licence allowance, and supplies an unapproved source. Each must fail its
own check; missing tools or network failures must never become a pass.

## Reconstruction preview boundary

The ordinary native command set is generated in the [CLI catalogue](../reference/cli-catalogue.md).
Historical lifecycle/removal and security-report commands are not native public
commands. Source-maintenance and publisher scripts run only in their own trusted
maintenance/release context. Preview status never permits guessing an uncertain
effect, acquiring an unowned file by shape, or deleting a familiar legacy path.
Skills and external text supply no mutation or reviewer authentication authority.
