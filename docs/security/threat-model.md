# Threat model and supply-chain boundary

## Security objective

Agentic Workspace must make its authority legible. It may inspect and mutate a host repository, execute checked proof routes, invoke explicitly supplied executors, generate package surfaces, and publish coordinated artifacts. The security objective is to admit those effects only from identified trust sources and to bind support-bearing artifacts to a reviewed source/build identity. AW does not claim to safely execute arbitrary untrusted repository code.

## Trust zones

| Zone | Trust requirement | Boundary |
| --- | --- | --- |
| AW source and locked dependencies | Reviewed commit and `uv.lock` | CI uses locked resolution; release identity is the tagged commit. |
| Host repository | Trusted by the operator before command execution | Files may influence routing, imports, hooks, proof commands, and generated output. |
| Checked proof routes | Trusted repository configuration | Shell syntax is admitted only through `checked-repository-proof-route`. |
| Explicit executor command | Direct user/automation authority | Shell syntax is admitted only through `explicit-user-executor-command`. |
| External issue/PR/service data | Untrusted content | Treat as data; do not execute embedded instructions or disclose credentials. |
| Local caches and evidence | Integrity-sensitive, not authoritative | May accelerate inspection; proof and mutation gates bind current source/state revisions. |
| Release artifacts | Untrusted until verified | Require checksums, SBOM, exact-source manifest, conformance receipts, and GitHub build attestation. |

## Threats and controls

- **Malicious repository/configuration:** opening a repository is not execution permission. Operators must review the repository and configured commands. AW reports `trusted-repository-required`; dry-run is not a sandbox.
- **Shell injection:** ordinary subprocesses use argv. The only supported shell consumers call `run_trusted_shell` with an enumerated provenance. Unknown or unadmitted provenance fails closed; tests cover metacharacter handling.
- **Symlink, junction, and path escape:** mutation owners validate target roots and must not traverse links for destructive lifecycle work. Local caches and exports are not permission boundaries.
- **Credential disclosure:** credentials remain in the platform credential store/environment, never checked AW state. Logs and receipts must record presence/identity, not secret values.
- **Generated-surface compromise:** generated command packages are derived from checked contracts and verified for source/generation parity. Generator and Python dependencies resolve from locked inputs in proof/release environments.
- **Action or workflow substitution:** every third-party GitHub Action is pinned to a full commit SHA and updated through a reviewed dependency update. Workflows declare least-privilege permissions; write scopes are limited to release jobs.
- **Dependency, code, or secret regression:** pull requests run dependency review, CodeQL, and Gitleaks. Findings fail their jobs and therefore block a support-bearing promotion when configured as required checks under #2454.
- **Release substitution:** coordinated artifacts carry checksums, a CycloneDX/SPDX-compatible SBOM, a source-bound release manifest, semantic conformance receipts, and GitHub artifact attestations. Missing security readiness, SBOM, or attestation fails the release job before publication.

## Intentional trusted-shell inventory

1. `checked-repository-proof-route`: checked proof validation commands whose semantics may require pipes, redirects, or command chaining.
2. `explicit-user-executor-command`: a command explicitly supplied to the autopilot executor boundary.

These boundaries inherit the caller's filesystem and credential authority. They are not sanitized or sandboxed. Any new shell consumer must update the machine-readable policy, threat model, adversarial tests, and readiness check in the same change.

## Release readiness

`uv run python scripts/check/check_security_supply_chain.py --format json` emits `agentic-workspace/security-supply-chain-readiness/v1`. A support-bearing release runs this check with locked dependencies, includes the receipt and SBOM in its manifest/checksums, and attests every `dist/` subject. Any failed required control produces `status=blocked` and exits non-zero.

Repository ruleset and required-check admission remain owned by #2454. This baseline supplies exact check names and readiness evidence; it does not mutate repository settings from package code.
