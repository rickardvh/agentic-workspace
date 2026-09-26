# Hosted automation

Implementation lane: #3654, with non-release contraction in #3655 and release
contraction in #3656. Green-first release semantics belong to #3652.

## CI and maintenance

CI owns merge proof, PR semver admission, and required security checks. The stable
`Merge sufficiency` result requires all three, including the current public-install
check. Individual steps and security jobs retain specific failure messages.
Explicit exhaustive dispatch still requires an exact head and a nonempty reason;
ordinary PRs do not acquire release-grade package/runtime proof.

Semver admission is implemented in `src/tooling/release/pr_semver_admission.py`.
Its input is the PR event, Git history and run identity. Immutable historical
admissions from `pr-semver-label.yml` remain acceptable only when their artifact
producer matches the observed successful run. New admissions name `ci.yml`.
The retired workflow is deleted, not forwarded.

Maintenance freezes public consumer subjects once for each daily run and retains
the existing consumer reports and cleanup. Weekly security work uses the same
security implementation as CI. `security.yml` is a callable provider wrapper:
CodeQL needs a language matrix and `security-events: write`; the other blocking
scans share one runner. It has no independent triggers or admission policy.

`consumer-validation.yml` is replaced by `maintenance.yml`; its deterministic
selection, exact public subjects, seven-day artifacts and report owner are kept.

## Required checks and provider boundaries

The checked-in master ruleset requires `Merge sufficiency`, which is preserved.
The live ruleset audit on 2026-09-26 found ruleset 20615912 disabled. This is an
existing enforcement gap, not evidence that protection is active. Contraction
does not enable or weaken remote branch policy.

CI and Maintenance grant the callable security job `security-events: write`.
The CodeQL job uses it; other security steps keep read-only permissions. The
repository write-permission admission records these two caller grants explicitly.

## Release

`release_lifecycle.py` owns release class, exact subject admission, source proof
reuse, composition and recovery. The shared publisher uses existing platform and
support declarations for its matrices. Stable composition still requires the
server, runtime, semantic, security, install and redistribution receipts. Preview
and RC composition cannot carry stable promotion evidence.

The release preparer first qualifies its exact source. Candidate dispatch names
that source run, verifies a normalisation-only delta and retains artifact/runtime
checks. Without that admitted source evidence, CI runs exhaustive source proof.
The preparer remains separate because it writes branches, PRs and tags; the
publisher consumes an existing immutable tag and holds publication credentials.

Complete admitted GitHub assets are reused without rebuilding. Partial recovery
compares existing assets and refuses changed bytes. Registry projection verifies
the original attestation identity, stages only absent versions and observes
propagation for a bounded interval. Historical RC manifests without the new
publisher field still bind to their original `preview-release.yml` attestations.

PyPI/npm publication stays in top-level `release.yml` with `package-registries`.
The Cargo callable wrapper retains `cargo-registry` and its OIDC identity. These
are provider boundaries, not separate release policy. The repository declarations
preserve the existing stable publisher identity; live PyPI/npm/crates.io account
configuration and a consolidated RC publication still require provider evidence.

## Surface audit

| Measure | Before | After |
| --- | ---: | ---: |
| Workflow files | 9 | 6 |
| Declared jobs, before matrix expansion | 40 | 29 |
| YAML lines, approximately | 2,307 | 1,390 |

| Retired entrypoint | Surviving responsibility |
| --- | --- |
| `pr-semver-label.yml` | CI invokes repository semver admission |
| `consumer-validation.yml` | Maintenance freezes, executes and reports consumer observations |
| `preview-release.yml` | Release takes an explicit class and shares package/runtime stages |
| `platform-release.yml` | Release uses the existing platform owner and hosted runner matrix |

The six remaining files have specific roles: CI admission, Maintenance recurrence,
CodeQL/security permissions, release preparation writes, publication identity, and
Cargo OIDC credentials. There is no generated workflow graph or new scheduler.

The immediate local evidence includes source/candidate failure controls, preview,
RC and stable composition, bounded registry absence/conflict/timeout controls,
immutable recovery, historical semver provenance and maintenance trigger checks.
Actionlint checks the surviving Actions graph. These controlled tests use fakes
for provider effects; they are not live publication or six-platform execution.

## Completion boundary

Local policy/static tests establish deterministic behavior and hosted wiring.
They do not establish hosted execution, independent review, provider trust
configuration, issue closure or satisfaction of the full parent lane. The parent
requires the ordinary PR, exhaustive escalation, maintenance and release journeys
and a final inventory of files, jobs and YAML volume.
New trusted dispatch and `workflow_run` routes require reviewed default-branch
code. No implementation-agent merge, independent approval or issue closure is
implied by the local results.
