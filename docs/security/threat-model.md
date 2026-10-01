# Threat model and supply-chain security

## Security objective

Agentic Workspace must make permissions and trust clear. It may inspect or change a repository, run configured checks, invoke explicitly supplied executors, generate package files and publish release artefacts. Those actions are allowed only when they come from the expected trusted source. Stable release files are tied to a reviewed source commit and build identity. AW does not claim to safely execute arbitrary untrusted repository code.

## Trust zones

| Zone | Trust requirement | Boundary |
| --- | --- | --- |
| AW source and locked dependencies | Reviewed commit, `uv.lock` and `Cargo.lock` | CI uses locked resolution; release identity is the tagged commit. |
| Host repository | Trusted by the operator before command execution | Files may influence routing, imports, hooks, proof commands, and generated output. |
| Checked proof routes | Trusted repository configuration | Shell syntax is admitted only through `checked-repository-proof-route`. |
| Isolated selected proof | Trusted Linux Docker daemon, transport and immutable image | The repository command receives a bounded read-only source snapshot, temporary scratch, no host mounts and no network. Native publication is checked separately. |
| Explicit executor command | Direct user/automation authority | Shell syntax is admitted only through `explicit-user-executor-command`. |
| External issue/PR/service data | Untrusted content | Treat as data; do not execute embedded instructions or disclose credentials. |
| Local caches and saved results | Useful but not trusted as the defining source | They may speed up inspection, but writes and conclusions are checked against current source/state revisions. |
| Release artefacts | Untrusted until verified | Require checksums, SBOM, source-bound manifest, compatibility checks and GitHub build attestation. |

## Threats and controls

- **Malicious repository/configuration:** opening a repository is not execution permission. Operators must review the repository and configured commands. AW reports `trusted-repository-required`; dry-run is not a sandbox.
- **Shell injection:** ordinary subprocesses use argv. The only supported shell consumers call `run_trusted_shell` with one of the explicitly recognised source labels. An unknown source is rejected; tests cover metacharacter handling.
- **Symlink, junction, and path escape:** mutation owners validate target roots and must not traverse links for destructive lifecycle work. Local caches and exports are not permission boundaries.
- **Credential disclosure:** credentials remain in the platform credential store/environment, never checked AW state. Logs and receipts must record presence/identity, not secret values.
- **Generated-file compromise:** generated command packages come from checked contracts and are verified against those sources. Generator and Python dependencies resolve from locked inputs in test and release environments.
- **Action or workflow substitution:** every third-party GitHub Action is pinned to a full commit SHA and updated through a reviewed dependency update. Workflows declare least-privilege permissions; write scopes are limited to release jobs.
- **Dependency, code, or secret regression:** pull requests run dependency review, CodeQL, and Gitleaks. Findings fail their jobs and therefore block a stable release when those jobs are required under #2454.
- **Release substitution:** coordinated artefacts carry checksums, a CycloneDX/SPDX-compatible SBOM, a source-bound release manifest, semantic conformance receipts, and GitHub artefact attestations. Missing security readiness, SBOM, or attestation fails the release job before publication.

## Intentional trusted-shell inventory

1. `checked-repository-proof-route`: checked proof validation commands whose semantics may require pipes, redirects, or command chaining.
2. `explicit-user-executor-command`: a command explicitly supplied to the autopilot executor boundary.

The ordinary host-shell boundaries inherit the caller's filesystem and credential
authority. They are not sanitised or sandboxed. Verification can instead use the
optional [isolated selected-proof executor](../maintainer/selected-proof-execution.md).
That executor checks the Docker connection, daemon, pinned image and source bytes;
it confines the selected command while the host separately records and verifies
the result. If the required isolation is unavailable, the check remains blocked.
Any new shell consumer must update the machine-readable policy, threat model,
adversarial tests and readiness check in the same change.

## Stable release checks

`uv run python scripts/check/check_security_supply_chain.py --format json` emits `agentic-workspace/security-supply-chain-readiness/v1`. A stable release runs this check with locked dependencies, includes the result and SBOM in its manifest/checksums, and attests every file in `dist/`. Any failed required check produces `status=blocked` and exits non-zero.

Repository rules and required-check configuration remain tracked by #2454. This document names the expected checks and evidence; package code does not change repository settings.

## Rust dependency security checks

`deny.toml` is the Rust advisory/license/source policy. Run
`python scripts/check/check_rust_dependencies.py --install` to install the exact
security-policy-owned cargo-deny version and check the locked workspace. Later
local runs can omit `--install`; a missing or different tool version fails.
The runner uses the repository Rust toolchain, enables the graph's full feature
set, includes development and target-specific dependencies, fetches current
RustSec data, and fails on checker/data errors. It does not use an offline
advisory snapshot for this check. `Cargo.lock` remains unchanged.

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

Negative controls remove the advisory exception, remove an actually used licence
allowance, and supply an unapproved source. Each must fail its own check; missing
tools or network failures must never become a pass.

## Preview release safety

The ordinary native command set is generated in the [CLI catalogue](../reference/cli-catalogue.md).
Historical lifecycle/removal and security-report commands are not native public
commands. Source-maintenance and publisher scripts run only in their own trusted
maintenance/release context. Preview status never permits guessing whether an uncertain action happened,
taking over a file merely because it looks familiar, or deleting a legacy path
without the required checks. Skills and external text do not grant write
permission or independent-review status.
