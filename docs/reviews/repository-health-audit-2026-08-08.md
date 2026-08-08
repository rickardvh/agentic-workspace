# Agentic Workspace Repository Health Audit

**Audit date:** 2026-08-08  
**Audited revision:** [642ec80946fdb8aaf3bac1b527385a130a194df4](https://github.com/rickardvh/agentic-workspace/commit/642ec80946fdb8aaf3bac1b527385a130a194df4) on remote master  
**Latest published release at audit time:** [v0.36.2](https://github.com/rickardvh/agentic-workspace/releases/tag/v0.36.2), published 2026-07-30  
**Audit mode:** Source read-only; the report itself is the only intended repository artifact  
**Primary lens:** Improve the Agentic Workspace package so the same failure classes are prevented in generic host repositories

> **Overall assessment: at risk.** Agentic Workspace has an unusually clear product thesis, strong type coverage, a substantial test and contract corpus, and thoughtful lifecycle safety concepts. It is not yet operating like a dependable beta distribution. The most important gaps are release-gate composition, clean-host install closure, package identity and licensing, runtime ownership, operational-health gating, and proof that the product reduces more work than it creates.

The right next direction is a stabilization tranche, not another broad capability tranche. The package should make invalid states hard to produce and impossible to ship before asking host repositories or agents to compensate for them.

---

## 1. Executive decision

Agentic Workspace is technically ambitious and locally well tested, but several green checks prove less than their names or product claims imply:

- The complete default bounded validation passed in 260.8 seconds, yet the explicitly documented TypeScript semantic-conformance lane failed with 165 adapter-failure records on both Node 24 and Node 25.
- Both full Docker conformance lanes fail before semantic execution because the checked-in source fingerprint cannot be reproduced outside a Git checkout.
- A released clean-host memory install succeeded and produced a pleasantly small 30-file footprint, but that footprint contains seven references to files it did not install.
- The source checkout reports 211 findings, including two broken live planning lanes and five Memory dogfood warnings, while the target named “memory-freshness-strict” still exits successfully.
- The package says ordinary output should be small, but an idempotent init dry run returned 201,519 bytes and a supposedly selected Verification section returned 65,994 bytes.
- The package says it should lower total agent cost, but its own successful-completion-cost report has no recent run evidence, and its Verification manifest has zero evidence bundles.

These are not independent defects. They are symptoms of one systemic gap: **AW has many declarative contracts, but the final promotion gates do not consistently compose those contracts into a release decision.**

### Recommended decision

Treat the current line as an actively dogfooded alpha/beta candidate, pause new public command and contract growth, and do not publish another “supported” multi-target release until the Phase 0 gates in this report pass.

### Highest-leverage actions

| Order | Action | Why it comes first |
| --- | --- | --- |
| 1 | Make semantic conformance mandatory for every shipped target and artifact | A package that declares native mutation-capable adapters must not ship known contract divergence |
| 2 | Make freshness proof reproducible in Git, wheel, sdist, npm tarball, and no-Git container contexts | Current container proof is structurally unable to pass |
| 3 | Make every module footprint referentially closed and leave a durable executable invocation | A generic host must still be operable when the one-shot installer is gone |
| 4 | Resolve license and package-name/distribution identity | Missing license and occupied PyPI dependency names block safe adoption |
| 5 | Protect master and make required CI prove the actual supported matrix | Direct pushes currently bypass PR CI and trigger a write-capable release workflow |
| 6 | Collapse the shadow runtime into one canonical implementation | Roughly 37,000 function lines are duplicated between two runtime modules |
| 7 | Introduce live-health, output-size, archive-retention, and diagnostic-signal budgets | The package currently detects cost and residue without making them consequential |

---

## 2. Health scorecard

The labels below are directional engineering judgments, not a certification.

| Area | Status | Evidence-backed judgment |
| --- | --- | --- |
| Product thesis and design doctrine | **Healthy** | [README](../../README.md), [System Intent](../../SYSTEM_INTENT.md), and [design principles](../design-principles.md) define a coherent problem, anti-intents, ownership model, and cost test |
| Python implementation and static quality | **Mixed / generally strong** | Lint, formatting, type checking, full bounded validation, Python adapter conformance, and primitive conformance passed; annotation coverage is above 98% |
| Runtime architecture | **Critical debt** | Two 50,000-line runtime modules share 1,038 top-level function names; 961 bodies are AST-identical |
| Test and proof design | **Mixed** | Broad local proof exists, but CI omits most root test files and release gates omit the failing semantic lanes |
| Generated Python target | **Healthy with distribution caveats** | Local generated-Python conformance passed; Python Docker conformance is blocked by the fingerprint design |
| Generated TypeScript target | **Critical** | Package self-tests pass, but complete semantic conformance emits 165 failures |
| Clean-host install and fallback | **Critical** | Install succeeds, but the necessary footprint has seven dangling references and no durable configured invocation |
| Documentation and authority consistency | **At risk** | Public documentation is thoughtful, but installed-surface, migration, ownership, maturity, and actual-footprint claims diverge |
| Output economy and agent usability | **At risk** | Key lifecycle and selected report payloads are tens to hundreds of kilobytes |
| Planning and Memory lifecycle hygiene | **At risk** | 1,011 checked-in AW files, 636 archived plans, 211 findings, and live-lane warnings conflict with the low-residue goal |
| Security and supply chain | **Critical baseline gap** | No security policy, branch protection, scanning, SBOM, signature, or attestation; two intentional shell-execution boundaries lack a published threat model |
| Release and adoption readiness | **Critical** | No root PyPI package, no npm packages, two Python dependency names owned by unrelated projects, no license, and 86 releases in 42 days |
| Direction and lifecycle sustainability | **At risk** | Seven concurrent draft feature PRs and 44 open issues expand the surface while foundation gaps remain |
| Maintainer sustainability | **At risk** | Effective human bus factor is one amid 3,241 commits and very high recent churn |

---

## 3. What is already strong

The report should not obscure the foundation worth preserving.

1. **The product has a real thesis.** The README clearly says what AW is and is not, identifies when it should pay back, and names coordination cost as a reason not to use it. That is unusually healthy framing for an agent-infrastructure project.

2. **The authority model is thoughtful.** Repo-owned, module-managed, generated, historical, and local-only concepts are present throughout the design. Dry runs, receipts, claim boundaries, and “agent judgment remains with the agent” are good primitives.

3. **Static quality is strong.** The production tree has 4,286 Python functions. Return annotations cover 99.3%, parameters are annotated or are self/cls in 99.4%, and 98.5% of functions are fully annotated by that measure. Ruff, Ty, and format checks passed.

4. **There is meaningful behavioral proof.** The bounded validation suite passed; generated Python adapter conformance passed; command-generation primitive conformance passed locally and in Docker; the four npm package self-test suites passed in Docker.

5. **Release artifacts have useful integrity metadata.** The release workflow builds all package artifacts together, writes SHA-256 checksums, records a coordinated manifest, verifies source commit and asset hashes, and publishes all-or-nothing. Preserve this design and add identity/signing rather than replacing it.

6. **The necessary-surface install is materially smaller than the source dogfood tree.** The released memory-only install used 30 total files, 28 below .agentic-workspace, and roughly 74 KB under that directory. The footprint direction is right; its reference closure is not yet complete.

7. **Runtime dependencies are comparatively lean.** The three module packages have few or no third-party runtime dependencies. TypeScript packages have no npm dependencies. This is a valuable supply-chain and portability property.

8. **The project actively captures dogfood friction.** Many current issues came from real operational use. The improvement is to make evidence deduplicated, prioritized, and gate-changing rather than to stop dogfooding.

---

## 4. Critical findings

### F01 — Semantic TypeScript conformance is failing but is not a release gate

**Priority:** P0  
**Failure class:** A shallow package self-test is treated as proof of contract equivalence.

#### Evidence

- The default full command, make check-bounded-parallel, passed in 260.8 seconds.
- The documented cross-target command in [config.toml](../../.agentic-workspace/config.toml) and [the contributor playbook](../maintainer/contributor-playbook.md) failed:

~~~text
uv run --active python scripts/check/check_generated_command_packages.py --conformance --require-node
exit 1
165 adapter failure records
~~~

- The result was the same with Node 24.19.0, matching the release workflow’s major version, and Node 25.2.1.
- Failure classes included 54 invalid-option parser failures, 59 unsupported-command refusal mismatches, 22 missing/invalid stdout-field failures, 28 output-shape mismatches, and two exit-code mismatches. These categories overlap because some cases are checked in more than one execution mode.
- The workspace npm package declares itself “mutation-capable-adapter,” “runnable,” and “Node/TypeScript only” in [package.json](../../generated/workspace/typescript/package.json).
- The npm self-tests in [command-package.test.mjs](../../generated/workspace/typescript/test/command-package.test.mjs) passed. Those tests sample parser shape and a few native operations; they do not prove the full conformance registry.
- [CI](../../.github/workflows/ci.yml) runs the static generated-package checker without the conformance flag and only two selected generated-process cases.
- [Release](../../.github/workflows/release.yml) runs npm test and packs the tarballs, but does not run the failing semantic-conformance command.

#### Generic host impact

A host can receive a package whose declared command, option, error, exit, and result-shape contracts disagree with the executable adapter. The risk is larger than a cosmetic API mismatch because AW labels these adapters safe for mutation-capable weak-agent routing.

#### Preventive AW package change

- Add a release-owned target matrix in which every artifact marked runnable must pass its complete semantic conformance registry.
- Make maturity and publishability derived from the proof result. A failing target should be excluded or labeled non-runnable; handwritten metadata must not overrule proof.
- Run a fast representative semantic shard on every relevant PR and the complete registry on release candidates.
- Run against the minimum and current supported Node majors, not only the newest release image.
- Generate a compact machine-readable failure summary and preserve full logs as build artifacts.
- Make the release manifest include the conformance subject fingerprint and proof receipt for each package.

#### Exit criteria

- Zero adapter failures on all supported Node versions.
- Negative parser, unsupported-command, dry-run, mutation-refusal, and result-shape cases are included.
- The exact packed npm tarballs, not only source directories, pass.
- The release job cannot upload assets if any runnable target lacks a current receipt.

---

### F02 — Docker conformance proof is structurally unreproducible

**Priority:** P0  
**Failure class:** Freshness proof depends on source-checkout state that the proof environment intentionally omits.

#### Evidence

Both of these commands failed before adapter execution:

~~~text
scripts/check/check_generated_command_packages.py --python-docker-conformance --require-docker
scripts/check/check_generated_command_packages.py --docker-conformance --require-docker
~~~

Both reported:

~~~text
generated/.agentic-workspace-cli-fingerprint.json is stale; regenerate command packages.
~~~

The checked-in manifest records:

- 1,031 source files;
- a Git index identity;
- uv.lock as an input.

The built conformance image computes:

- 1,030 files;
- no Git index identity;
- otherwise equal content hashes for the files it has.

[Dockerfile.conformance](../../generated/python/Dockerfile.conformance) and [typescript.conformance.Dockerfile](../../generated/typescript.conformance.Dockerfile) omit both .git and uv.lock, so the current equality check cannot succeed by construction. In the TypeScript Docker failure path, the Windows/Python 3.14 caller also emitted a CP1252 UnicodeDecodeError from a subprocess reader thread.

By contrast:

- npm package self-tests in the lightweight TypeScript Docker image passed;
- primitive conformance passed locally and in Docker.

This isolates the failure to the source-fingerprint/proof boundary, not Docker availability.

#### Generic host impact

Any proof tied to a Git index identity becomes unusable for installed wheels, sdists, npm tarballs, source archives, vendored tools, or build containers. The package can then either reject healthy artifacts as stale or skip the proof that would have caught real drift.

#### Preventive AW package change

- Define a transportable content manifest whose identity is independent of .git.
- Separate “source checkout acceleration identity” from “artifact semantic identity.” Git metadata may optimize a local scan, but it must not be a required cross-environment field.
- Include every declared input in container contexts, or explicitly define context-specific manifests whose equivalence is contract-backed.
- Test freshness from five environments: Git checkout, no-Git source tree, sdist, wheel installation, and packed npm tarball.
- Decode subprocess output explicitly as UTF-8 with a bounded replacement/error policy on Windows.
- Make container proof use locked or hashed dependencies rather than unconstrained transitive resolution.

#### Exit criteria

- Both Docker conformance commands pass from a clean clone.
- The same artifact identity is observed in source, wheel/sdist, and npm-tarball tests.
- Missing Git metadata never changes semantic freshness.
- Failure reporting remains valid UTF-8 on supported Windows/Python combinations.

---

### F03 — The distribution identity is not viable as documented

**Priority:** P0  
**Failure class:** Project-local installation works, but no stable public locator exists for the coordinated product.

#### Evidence

- [agentic-workspace on PyPI](https://pypi.org/project/agentic-workspace/) returns 404.
- agentic-verification is also absent from PyPI.
- [agentic-memory](https://pypi.org/project/agentic-memory/) and [agentic-planning](https://pypi.org/project/agentic-planning/) are already owned by unrelated projects.
- All four declared npm package names returned 404 from the npm registry at audit time:
  - @agentic-workspace/workspace-cli
  - @agentic-workspace/memory-cli
  - @agentic-workspace/planning-cli
  - @agentic-workspace/verification-cli
- A clean isolated uvx agentic-workspace invocation fails because there is no registry package.
- A direct GitHub v0.36.2 root-wheel URL works and correctly streams the coordinated module wheels.
- [The root installation guide](../agentic-workspace-install.md) tells the reader to install a stable CLI into the target environment but does not provide a concrete root package locator or durable command.
- Memory and Planning READMEs provide Git-based examples pinned to mutable master, not a version tag or commit.
- The unpatched root [pyproject](../../pyproject.toml) declares ordinary dependencies named agentic-memory, agentic-planning, and agentic-verification. The release workflow has to rewrite the wheel metadata to direct GitHub asset URLs in [patch_workspace_release_wheel.py](../../scripts/release/patch_workspace_release_wheel.py).

#### Generic host impact

A host following normal Python packaging conventions can resolve unrelated packages, fail halfway through dependency resolution, or depend on mutable master. A one-shot URL invocation may install files successfully but disappear before the next agent follows the generated AGENTS instructions.

#### Preventive AW package change

- Make an explicit ecosystem identity decision before public registry publication:
  - rename Python distributions to globally unique names; or
  - publish only a uniquely named root distribution and vendor/internalize module wheels; or
  - use a documented private/index or direct-URL channel with exact hashes.
- Publish one canonical, versioned, copyable installation command in the root README and install guide.
- Have init record a verified durable invocation in config or return a blocking handoff until the host adds the dependency.
- Validate the installed console script in a new process after the temporary installer exits.
- Add clean-environment resolution tests that forbid unexpected project URLs or maintainers for every dependency.
- Keep source-install, release-asset, and eventual registry wheel metadata semantically equivalent.

#### Exit criteria

- A clean host can run one documented command, exit that process, and successfully run agentic-workspace start in a second process.
- Dependency resolution cannot install the unrelated PyPI projects.
- Every public package locator is version-pinned and hash-verified where the ecosystem supports it.
- Root and module package identities are owned by this project before documentation calls them publishable.

**Related existing work:** [#2263](https://github.com/rickardvh/agentic-workspace/issues/2263) addresses reproducible pairing of installed contracts and invocation; [#2365](https://github.com/rickardvh/agentic-workspace/issues/2365) addresses uv invocation posture.

---

### F04 — The public project and all Python distributions lack a license

**Priority:** P0  
**Failure class:** Technically downloadable artifacts are not legally adoptable artifacts.

#### Evidence

- The repository has no LICENSE or COPYING file.
- GitHub reports no detected repository license.
- Root and all three module pyprojects have no project.license metadata.
- The root pyproject also omits authors, project URLs, keywords, and classifiers.

#### Generic host impact

Without an explicit license, downstream users do not have a clear grant to use, modify, redistribute, or package the code. This blocks serious adoption regardless of technical quality and makes registry publication and third-party contribution risky.

#### Preventive AW package change

This is primarily a repository decision, but AW should also prevent recurrence in package projects:

- Select and add an SPDX-recognized license after owner review.
- Add license metadata to every coordinated Python and npm distribution.
- Include the license in wheels, sdists, npm tarballs, and release manifests.
- Add a packaging policy check that fails release when license, source URL, issue URL, author/maintainer, and supported-runtime metadata are absent or inconsistent.
- Add a generic AW release-readiness protocol that distinguishes “buildable” from “redistributable.”

#### Exit criteria

- GitHub detects the intended license.
- Built artifacts contain the license and consistent SPDX metadata.
- Release readiness fails on a fixture with missing or conflicting license data.

---

### F05 — The necessary install footprint is not referentially closed

**Priority:** P0  
**Failure class:** Footprint reduction removes surfaces that surviving instructions still require.

#### Evidence

A fresh v0.36.2 memory install succeeded and wrote 30 non-Git files. A reference scan found seven distinct missing targets:

| Missing target | Referenced by |
| --- | --- |
| .agentic-workspace/docs/module-map.md | workspace-startup and workspace-operating-loop skills |
| .agentic-workspace/docs/workspace-config-contract.md | generated config header |
| docs/module-map.md | startup and operating-loop alternate reference |
| docs/jumpstart-contract.md | setup-jumpstart skill |
| docs/setup-findings-contract.md | setup-jumpstart skill |
| docs/workspace-config-contract.md | generated config header alternate |
| src/agentic_workspace/contracts/skill_specs.json | startup skill |

The most serious is not a decorative link: [workspace-startup/SKILL.md](../../.agentic-workspace/skills/workspace-startup/SKILL.md) says the no-CLI fallback should use the missing module map.

Authority and lifecycle documentation also disagree:

- [installed-surfaces.md](../package/installed-surfaces.md) says .agentic-workspace/OWNERSHIP.toml is repo-owned and lists WORKFLOW.md and docs/module-map.md as installed surfaces.
- The live ownership command reports OWNERSHIP.toml as module-managed.
- The necessary-surface migration plans to remove WORKFLOW.md and the entire .agentic-workspace/docs directory.
- The released minimal install already omits those files.

A broader local Markdown link scan found 28 missing rendered link occurrences, primarily source payload defects repeated in generated Planning/Memory payload mirrors plus a smaller number of checked-in AW-state links. No missing local Markdown links were found in the main public docs tree outside payload/internal-state surfaces.

#### Generic host impact

The exact moment when the CLI is missing or broken is when fallback instructions matter. A reduced footprint that routes to absent files converts an intended safe degraded mode into guesswork. Agents may then broadly reread the repo, use stale global installations, or mutate state without the intended boundaries.

#### Preventive AW package change

- Build an install-closure graph from every installed text/config reference.
- For every module subset and footprint profile, fail packaging when a surviving required reference is neither:
  - installed locally;
  - available through a stable package-resource URI/API; nor
  - explicitly marked optional with a valid degraded behavior.
- Generate installed skills, config comments, docs, and the lifecycle removal manifest from one canonical surface manifest.
- Add a “CLI unavailable” black-box fixture for every module combination.
- Make ownership class machine-owned and generate public documentation from the same source.
- Distinguish human links from package-resource identifiers so Markdown renderability and runtime resolvability are both tested.

#### Exit criteria

- Zero required dangling references across memory, planning, verification, pairwise, and all-module installs.
- The no-CLI fixture can recover the same forbidden actions and next safe action without package import or network access.
- Ownership and installed-surface documentation exactly match command output and migration behavior.

---

### F06 — Master can bypass validation and directly activate release automation

**Priority:** P0  
**Failure class:** Strong workflow code is undermined by an unguarded promotion boundary.

#### Evidence

- GitHub reports “Branch not protected” for master.
- Repository rulesets are empty.
- CI runs only for non-draft pull requests.
- There is no CI push trigger for master.
- A push to master starts [Prepare Coordinated Release](../../.github/workflows/release-from-semver-label.yml), which has contents:write, pull-requests:write, and actions:write.

#### Generic host impact

A direct push, compromised maintainer session, or automation mistake can bypass PR validation and enter a write-capable release path. AW’s local receipts and proof selection cannot compensate for an unprotected server-side promotion boundary.

#### Preventive AW package change

The repository must enable branch protection; the reusable AW improvement is to make promotion trust observable:

- Require PRs, required status checks, conversation resolution, and non-force-push protection for master.
- Require the semantic, packaging, and clean-host gates from this report.
- Give ordinary CI explicit contents:read permissions.
- Make release jobs verify a server-observed required-check set for the exact commit before tagging or publishing.
- Add an optional provider adapter that reports branch/ruleset posture and downgrades release readiness when it cannot verify protection.
- Never auto-enable host settings without explicit authority; detection and lower-trust reporting are the generic package role.

#### Exit criteria

- A direct push cannot update master.
- A commit without every required check cannot be tagged or published.
- Release preparation does not run with write permissions for an unverified commit.

---

## 5. High-priority structural findings

### F07 — Required CI does not test the declared support surface

**Priority:** P1  
**Failure class:** Local comprehensive proof exists, but the merge gate samples a narrower product.

#### Evidence

- The root tests directory has 67 tracked test files.
- Root CI runs:
  - two selected generated-tool cases;
  - all of test_workspace_cli.py;
  - all of test_workspace_proof_generated_packages_cli.py;
  - three packaging smoke tests in a separate job.
- The three module package suites run fully, which is positive.
- CI uses only Ubuntu and Python 3.13.
- The package declares Python >=3.11 with no upper bound; module classifiers name 3.11, 3.12, and 3.13.
- There is no required Windows, macOS, Python 3.11, 3.12, or 3.14 lane.
- The audit reproduced a Python 3.14/Windows subprocess decoding failure.
- TypeScript requires Node >=20, while PR CI does not explicitly install Node or require the semantic Node lane.
- make sync-all uses uv sync without --frozen; CI does not separately run uv lock --check.
- Jobs have no explicit timeout.
- Root and Verification tests do not enforce coverage. Memory measured 83% and Planning 76% in this run, but neither has a fail-under threshold.

#### Preventive AW package change

- Split CI into a fast required matrix and a full release matrix:
  - Python minimum, primary, and newest supported;
  - Windows plus Linux for path/subprocess behavior;
  - Node minimum and release major;
  - exact built artifacts.
- Shard the complete root test set instead of selecting files by hand.
- Run uv lock --check and sync with --frozen.
- Set explicit job timeouts and read-only default permissions.
- Add coverage ratchets per package, focusing first on safety/lifecycle modules rather than chasing a vanity global percentage.
- If Python 3.14 is not supported, declare an upper bound and test the error; otherwise add it to the matrix.
- Let AW’s proof selector emit a warning when declared runtime support exceeds observed CI coverage.

#### Exit criteria

- Every declared runtime family has a required check.
- The full root test inventory is either executed or explicitly classified with an owner and replacement proof.
- Lock drift makes CI fail without rewriting uv.lock.
- The reproduced Windows decoding case is covered.

---

### F08 — “Strict” freshness proves command execution, not healthy state

**Priority:** P1  
**Failure class:** Exit status is treated as operational health.

#### Evidence

The clean master report contains 211 findings:

| Class | Count | Severity |
| --- | ---: | --- |
| Archived closeout residue | 136 | info |
| Legacy roadmap field drift | 44 | warning |
| Projection divergence | 20 | warning |
| Memory dogfood warnings | 5 | warning |
| Legacy payload warnings | 3 | warning |
| Broken live lanes | 2 | warning |
| Unregistered live execplan | 1 | warning |

The live warnings include missing/current-slice relationships for two Planning lanes and failing Memory fixtures. Nevertheless:

- make check-bounded-parallel passes;
- its “memory-freshness-strict” target only invokes report and accepts exit zero;
- historical archive noise and current executable-state defects share one findings list.

#### Generic host impact

A host may believe a “strict” check protects current work while it only proves that diagnostics rendered. Conversely, making every warning fatal would drown hosts in historical residue. The missing abstraction is a policy-aware live-health result.

#### Preventive AW package change

- Add explicit health classes:
  - current executable state;
  - current installed/config state;
  - actionable maintenance debt;
  - historical information.
- Add --fail-on or a dedicated assert-health command with configurable thresholds.
- Make live broken relations, invalid required fixtures, and unregistered active plans fail strict mode.
- Aggregate historical/archive findings outside current health.
- Rename existing Make targets so “strict” always has a failing policy, not merely detailed output.
- Include the health-policy fingerprint in proof receipts.

#### Exit criteria

- A fixture with a broken live lane fails the strict command.
- Archived informational residue does not fail ordinary host health.
- The command returns a compact summary of exactly which policy caused failure.

---

### F09 — The shadow runtime has become a second implementation

**Priority:** P1  
**Failure class:** Compatibility mirroring duplicates behavior without semantic equivalence proof.

#### Evidence

[workspace_runtime_core.py](../../src/agentic_workspace/workspace_runtime_core.py) is 54,723 lines and [workspace_runtime_primitives.py](../../src/agentic_workspace/workspace_runtime_primitives.py) is 51,750 lines.

AST comparison of top-level functions found:

| Metric | Count |
| --- | ---: |
| Core top-level functions | 1,191 |
| Primitives top-level functions | 1,076 |
| Shared names | 1,038 |
| AST-identical bodies | 961 |
| Text-identical bodies | 959 |
| Shared names with different AST | 77 |
| Identical function lines in each file | about 37,120 |

The built-in runtime_mirror_consistency report says:

- status: shape_in_sync;
- proof strength: return-key-shape-plus-selector-ownership;
- semantic_equivalence_checked: false.

Its own rule correctly says the check is not semantic equivalence proof.

#### Generic host impact

Every behavior fix has multiple potential owners. A change may land in the active owner but not the mirror, or vice versa. Shape checks can stay green while defaults, refusal behavior, side effects, or semantics diverge. The code is also costly for agents to inspect and expensive to review.

#### Preventive AW package change

- Declare one canonical runtime implementation.
- Turn the compatibility surface into imports, generated facades, or small explicitly reviewed adapters.
- Add a build-time ban on duplicate function definitions across the compatibility boundary, with a short expiration-based allowlist.
- Replace broad private-symbol compatibility with a documented public/internal API.
- Ratchet duplicate line/function counts downward on every relevant PR.
- Give every remaining divergent symbol a migration owner, reason, proof, and removal milestone.

#### Exit criteria

- No behavior body is hand-maintained in both modules.
- The compatibility module contains only imports/adapters whose equivalence is directly testable.
- The active owner is discoverable without reading historical migration contracts.

---

### F10 — Runtime and installer complexity exceeds safe review scale

**Priority:** P1  
**Failure class:** Large decision procedures absorb unrelated responsibilities until tests are the only practical specification.

#### Evidence

Production Python across root and modules:

| Metric | Value |
| --- | ---: |
| Files | 62 |
| Lines | 183,867 |
| Functions | 4,286 |
| Files above 1,000 lines | 17 |
| Functions above 100 lines | 387 |
| Functions above 250 lines | 69 |
| Functions above 500 lines | 15 |
| Functions above the audit’s branch/decision proxy of 25 | 317 |
| Functions above that proxy of 50 | 84 |

Notable examples:

- _proof_selection_for_changed_paths: 1,431 lines, complexity proxy 281;
- _report_closeout_trust_payload: 1,002 lines in core and a separate 811-line primitives version;
- archive_execplan: 840 lines;
- _start_payload: 779 lines;
- Planning installer.py: 23,897 lines.

There are no action TODO/FIXME/HACK comments in production, which is positive, but absence of comments does not reduce structural coupling.

#### Generic host impact

Proof routing, safety policy, rendering, filesystem mutation, state migration, and compatibility behavior become hard to change independently. Agents must read enormous regions, increasing token cost and the chance of locally correct but globally inconsistent edits.

#### Preventive AW package change

- Introduce ratcheting file/function budgets for touched code; do not require a risky big-bang rewrite.
- Extract domain services around:
  - lifecycle planning/application;
  - health classification;
  - report projection;
  - proof selection;
  - planning relation reconciliation;
  - external command execution.
- Require an explicit decision table or schema for large branching policies.
- Keep parsing, policy, effects, and rendering in separate layers.
- Track review working-set size and changed-symbol fan-out as repository-friction signals.

#### Exit criteria

- New or materially changed functions remain below agreed thresholds unless an exception includes proof and an expiry.
- The five largest procedures shrink through behavior-preserving slices.
- Safety-critical policy is testable without invoking full CLI/report construction.

---

### F11 — Output profiles are not enforcing the product’s own cost doctrine

**Priority:** P1  
**Failure class:** “Compact” is a convention, not a measurable contract.

#### Evidence

On an already-initialized fresh memory host:

| Command | Bytes | Lines | Notes |
| --- | ---: | ---: | --- |
| init --dry-run --format json | 201,519 | 4,667 | Idempotent dry run |
| start --format json | 9,413 | 1 | One very long JSON line |
| report --section verification | 65,994 | 1,654 | Explicitly selected section |
| report --section findings | 80,324 | n/a | 211 records |
| repeated cached report/doctor | about 1,500 | about 45 | Demonstrates that much smaller output is possible |

The init payload’s largest fields were:

| Field | Approximate bytes |
| --- | ---: |
| config | 114,354 |
| lifecycle_plan | 23,016 |
| module_reports | 6,500 |

Within config, mixed_agent, configuration_projection, and config_effect_audit account for roughly 94 KB. This contradicts [output-profiles.md](../package/output-profiles.md), which says ordinary output should hide inventories and provenance unless they change the action.

#### Generic host impact

Agents pay token and attention cost on every lifecycle call. Large JSON also makes field discovery harder, encourages brittle ad hoc parsing, and can bury the one blocking action. A single-line 9 KB payload is machine-valid but poor for human inspection and tool truncation.

#### Preventive AW package change

- Add byte, line, field-count, and estimated-token budgets to every named output profile.
- Make default lifecycle output a stable decision envelope:
  - outcome;
  - mutation status;
  - review requirement;
  - next safe command;
  - warnings that change action;
  - detail selectors/receipts.
- Put config projections, action ledgers, and effect audits behind selectors, verbose mode, or an explicitly named local receipt.
- Test cold and warm output separately while preserving one stable schema.
- Fail generated-surface checks when a default profile exceeds its budget.
- Track output size in successful-completion-cost evidence.

#### Exit criteria

- Idempotent init default JSON is bounded to a small agreed budget, suggested under 10 KB.
- Startup’s ordinary action is visible without parsing dozens of unrelated fields.
- Detail remains accessible by selector and is not lost.

---

### F12 — Diagnostics are noisy where they should aggregate and shallow where they should investigate

**Priority:** P1  
**Failure class:** Diagnostic volume and diagnostic relevance are not separately budgeted.

#### Evidence

- Findings returns 211 individual records, 136 of which repeat an archived-closeout-residue message.
- repo_friction reports its largest and concept-surface hotspots as three local projection-cache JSON files of about 1,900–2,200 lines.
- It labels regenerable cache hotspots unavailable.
- It does not surface the 54,723-line and 51,750-line tracked Python runtime files, the 23,897-line Planning installer, their duplication, or their churn.
- improvement_intake returns candidate_count: 0 despite current warnings and obvious audit signals.
- Verification jumpstart suggests a “full” proof profile whose sampled evidence contains only typecheck targets, reflecting token-based Makefile discovery rather than target dependency semantics.

#### Generic host impact

Agents can spend time triaging repeated history while missing current code concentration. Improvement signals are detected but do not become bounded candidates. Weak discovery may confidently suggest incomplete proof.

#### Preventive AW package change

- Aggregate repeated findings by fingerprint, owner, severity, and lifecycle class.
- Default to counts plus a few exemplars; keep full records behind a selector.
- Scan Git-tracked source first and classify local cache, generated output, archived evidence, vendored code, and source separately.
- Add line count, symbol size, duplication, and churn as optional tracked-code signals.
- Feed current actionable findings into improvement intake with dedupe and candidacy reasons.
- Parse Makefile/CI target relationships or use declared proof manifests rather than keyword-only command discovery.
- Report why a finding is not promotable when candidate_count is zero.

#### Exit criteria

- The source checkout’s default findings view is action-first and bounded.
- repo_friction surfaces the known runtime hotspots and ignores local cache by default.
- Duplicate evidence produces one candidate identity.
- A “full” proof candidate proves the actual full target or is labeled incomplete.

**Related existing work:** [#2176](https://github.com/rickardvh/agentic-workspace/issues/2176) covers projection reuse; [#2310](https://github.com/rickardvh/agentic-workspace/issues/2310) covers consequential AW-context findings.

---

### F13 — Planning history dominates the working tree

**Priority:** P1  
**Failure class:** Durable evidence retention has no ordinary working-tree budget.

#### Evidence

.agentic-workspace contains:

| Surface | Files | Bytes | Lines |
| --- | ---: | ---: | ---: |
| Entire .agentic-workspace | 1,011 | 11,498,125 | 197,925 |
| Planning execplan archive | 636 | 9,255,636 | 158,909 |
| Planning reviews | 131 | 839,614 | 13,746 |
| Planning closeout evidence | 48 | 311,148 | 4,760 |
| Memory repo state | 38 | 84,703 | 2,101 |

The necessary-surface migration says it can safely:

- preserve 702 entries;
- remove 26;
- write/update five.

The archive is therefore mostly classified as durable adopted state, not removable payload. Findings then emits 136 informational residue records about archived closeouts.

#### Generic host impact

A mature host accumulates thousands of repo-visible planning artifacts, increases clone/search/review cost, and exposes future agents to historical intent that may no longer be authoritative. The package’s “small repo-native layer” becomes a second repository inside the repository.

#### Preventive AW package change

- Define a retention lifecycle rather than a delete command:
  - closeout distillation into canonical docs/Memory/issues;
  - compact immutable receipt retained in Git;
  - optional full evidence bundle stored as CI/release artifact or compressed pack;
  - retention/age/value policy for full plans.
- Add per-host file/byte/record budgets and trend them.
- Make archive lookup explicit; exclude archives from ordinary routing and findings unless current intent references them.
- Require a continuation owner before archiving an “open larger intent” plan.
- Provide a dry-run compactor with loss accounting and reversible export.

#### Exit criteria

- Ordinary startup/report cost does not grow linearly with archived plans.
- A long-lived fixture can close hundreds of plans while staying within a bounded checked-in footprint.
- Every removed full record remains retrievable or is intentionally distilled with proof.

---

### F14 — Documentation, runtime ownership, and maturity metadata have diverged

**Priority:** P1  
**Failure class:** Multiple hand-maintained descriptions compete with executable state.

#### Evidence

- Installed-surface ownership and actual ownership output disagree for OWNERSHIP.toml.
- Installed-surface docs list WORKFLOW.md and module-map.md, while migration removes them and necessary install omits them.
- [maturity-model.md](../maturity-model.md) labels Agentic Planning beta, but [Planning pyproject](../../packages/planning/pyproject.toml) declares Development Status :: 3 - Alpha.
- Root docs label the root and Memory beta; the root pyproject has no maturity classifier.
- Documentation status was last reviewed 2026-06-18. Between that date and the latest release, the project published dozens of releases; master was ten commits ahead of v0.36.2 at audit time.
- Internal payload/mirror Markdown contains missing relative links even though the main public docs tree is comparatively healthy.

#### Generic host impact

Agents make authority and lifecycle decisions from whichever surface they encounter first. Contradictory ownership can lead to unsafe manual edits or accidental upgrade replacement. Maturity drift makes support expectations unreliable.

#### Preventive AW package change

- Generate ownership, install inventory, lifecycle removal inventory, package metadata, and maturity tables from canonical manifests.
- Add payload-composition link checks for every module subset.
- Add a freshness rule that becomes failing when a supported-surface or lifecycle contract changes without refreshing its public owner page.
- Separate source-checkout historical reviews from current installed-package guidance.
- Make package version/maturity metadata coordinated but capable of per-surface maturity where intentionally different.

#### Exit criteria

- One machine source answers who owns every installed surface.
- All rendered docs and package metadata agree with it.
- A change to installed footprint or maturity cannot merge without updating generated documentation.

---

### F15 — Security and supply-chain controls are below the risk of a mutation-capable agent tool

**Priority:** P1  
**Failure class:** Safety behavior is modeled inside the product, but repository and artifact security are largely implicit.

#### Evidence

Repository controls:

- no SECURITY.md;
- Dependabot security updates disabled;
- Dependabot alerts disabled;
- no code-scanning analysis;
- secret scanning and push protection disabled;
- no dependency-update configuration;
- no branch protection or rulesets.

Build/release controls:

- GitHub Actions use version tags rather than commit SHAs;
- release assets have checksums and a manifest, but no signature, provenance attestation, or SBOM;
- command-generation is installed from a pinned Git commit in source and Docker proof, with transitive packages resolved at build time;
- CI has no explicit least-privilege permissions in ci.yml.

Code scan:

- pip-audit found no known vulnerabilities among auditable installed third-party packages.
- Local editable AW packages were skipped, and command-generation could not be matched to PyPI, so this is not a complete dependency attestation.
- Bandit reported 147 findings: 145 low and two high-confidence shell=True execution sites in workspace_runtime_primitives.py and workspace_runtime_proof.py.
- Both high findings appear to be intentional user/configured command execution, not proven injection vulnerabilities. They still define a critical trust boundary that is not documented in a security policy.

#### Generic host impact

AW reads host-controlled config and can execute proof or executor commands. In an untrusted checkout, this is equivalent to running repository code. Without a clear threat model and admission boundary, users may mistake lifecycle dry-run safety for sandboxing.

#### Preventive AW package change

- Publish a threat model covering:
  - untrusted host repositories;
  - config and proof-command provenance;
  - shell execution;
  - symlinks/reparse points;
  - release and generator compromise;
  - local caches and sensitive transcripts.
- Prefer argv execution; require explicit trusted-shell admission where shell syntax is necessary.
- Add SECURITY.md and a private reporting route.
- Enable dependency, code, and secret scanning.
- Pin third-party actions by SHA and set least-privilege permissions.
- Generate an SBOM and signed/attested build provenance for every coordinated release.
- Verify the exact generator wheel/commit and transitive lock in every proof environment.
- Add an AW host posture that says “configured command execution requires repository trust” instead of implying that dry run makes an untrusted repo safe.

#### Exit criteria

- Security policy and threat model are public.
- Release artifacts have verifiable provenance and dependency inventory.
- Shell boundaries have focused adversarial tests and explicit admission semantics.
- Security scanning is required and current.

---

## 6. Direction, lifecycle, and sustainability findings

### F16 — Release cadence is much higher than the evidence and adoption loop can support

**Priority:** P2  
**Failure class:** Version production is faster than compatibility learning.

#### Evidence

From 2026-06-18 through 2026-07-30:

| Metric | Value |
| --- | ---: |
| GitHub releases | 86 |
| Custom release assets | 1,204 |
| Custom asset storage | 427,987,433 bytes, about 408 MiB |
| Median interval between releases | 2.84 hours |
| Minimum interval | 0.06 hours |
| Maximum interval | 179.79 hours |
| Latest release custom assets | 14, plus GitHub source archives |
| Commits from v0.36.2 to audited master | 10 |

There was also one chronological semantic-version regression: v0.34.0 was followed minutes later by v0.33.2.

GitHub custom-asset download counters totaled 41 before this audit. The audit’s clean root-wheel probe downloaded four coordinated Python wheels, increasing the counter to 45 and the latest release from zero to four. These counters are not unique-user analytics and omit source archive access, but they do not show an external adoption loop commensurate with 86 releases.

#### Generic host impact

Hosts cannot form stable compatibility expectations. Release notes, docs, support matrices, and upgrade paths are constantly invalidated, while low adoption means regressions are mostly discovered by the same source checkout.

#### Preventive AW package change

- Batch compatible changes into a predictable release cadence.
- Separate canary/nightly artifacts from support-bearing releases.
- Require an evidence window for beta releases:
  - clean install;
  - upgrade from supported prior versions;
  - all-target conformance;
  - a small external-host fixture matrix;
  - no unresolved P0/P1 release findings.
- Define a compatibility window and deprecation policy.
- Measure adoption through opt-in feedback or reproducible external fixtures, not raw download counters.
- Retain fewer redundant historical assets once a documented retention policy exists.

#### Exit criteria

- Support-bearing releases are paced by evidence rather than merge count.
- Version ordering and domain ownership are monotonic.
- Upgrade proof covers the declared compatibility window.

---

### F17 — The package cannot currently prove its central economic claim

**Priority:** P2  
**Failure class:** Cost instrumentation exists as schema and report shape but has no current evidence.

#### Evidence

The successful_completion_cost section reports:

- status: no-evidence;
- recent run count: 0;
- token/request, package-read, proof/rework totals: no-evidence;
- one active high-priority weakness signal.

Verification reports:

- four protocols;
- five scenarios;
- four proof routes;
- zero evidence bundles;
- zero known gaps.

The audit’s full validation run did not create a Verification evidence bundle. The product therefore has rich proof vocabulary without a routine bridge from proof execution to retained evidence.

#### Generic host impact

Hosts bear coordination and repository residue without a way to see whether AW reduced rereads, corrections, failed claims, or time-to-completion. Maturity decisions become feature-count decisions.

#### Preventive AW package change

- Record privacy-safe local metrics by default only when the host opts in:
  - command output bytes;
  - startup/implementation read set;
  - proof duration and reruns;
  - correction/rework count;
  - completion/continuation outcome.
- Make the model harness produce a versioned local evidence summary that report consumes automatically.
- Convert validation manifests into Verification evidence bundles or explicitly explain why they are not admissible.
- Maintain paired AW/no-AW fixtures for representative host tasks.
- Make promotion from alpha to beta require current evidence, not only implemented surfaces.

#### Exit criteria

- The source checkout has recent reproducible completion-cost evidence.
- A release can state which scenarios improved, regressed, or remain unknown.
- Evidence collection stays local/opt-in and does not become surveillance.

---

### F18 — Direction is coherent but work in progress is too broad

**Priority:** P2  
**Failure class:** Capability expansion outpaces consolidation of the operating kernel.

#### Evidence

At audit time:

- 44 open issues;
- eight open PRs;
- seven draft feature PRs covering context authority, Planning route authority, correction guidance, evaluation, targeted execplan writing, delegated-run safety, and external conformance;
- one release PR for v0.36.3;
- 34 root command families in the generated workspace CLI;
- 336 files and 334 JSON files under src/agentic_workspace/contracts, about 4.3 MB;
- 671 tracked generated files.

The open roadmap is not random: it aims at external adapters, evidence-backed orchestration, correction learning, evaluation, delegation, route authority, and context authority. The problem is sequencing. These features add contract, output, generated-target, proof, and lifecycle burden while basic release and install invariants are failing.

#### Preventive AW package change

- Declare a stabilization milestone with a work-in-progress cap.
- Freeze new public command families and schema families until Phase 0 exits.
- Add a capability-cost gate: every new operation must name:
  - user/agent value;
  - canonical owner;
  - installed footprint effect;
  - default output cost;
  - Python and TypeScript proof;
  - upgrade/deprecation path;
  - what older surface it replaces or why net growth is justified.
- Prefer composition of existing operations over new front doors.
- Apply the product’s own “cost more than it removes” test to its roadmap.

#### Exit criteria

- Foundation metrics trend down while public capabilities remain stable.
- New capability proposals include measured cost and retirement impact.
- At most a small number of cross-cutting feature stacks are active simultaneously.

---

### F19 — Effective bus factor is one and contributor entry surfaces are incomplete

**Priority:** P2  
**Failure class:** High-velocity architecture is encoded in one maintainer’s working context.

#### Evidence

Git history at the audited commit:

| Metric | Value |
| --- | ---: |
| Total commits | 3,241 |
| Merge commits | 623 |
| Commits in last 30 days | 705 |
| Commits in last 60 days | 1,503 |
| Commits in last 90 days | 2,162 |
| Human commits across one person’s aliases | 3,164 |
| github-actions bot commits | 77 |

The repository has a single-owner CODEOWNERS file and no CONTRIBUTING.md, CODE_OF_CONDUCT.md, or SECURITY.md.

The highest-churn files in 90 days include runtime primitives (405 commits), Planning state (207), command-package IR (203), workspace CLI tests (194), runtime core (194), generated checker (176), and implement tests (172).

#### Generic host impact

This is primarily a project sustainability risk, but it also weakens dogfood validity: assumptions obvious to the author may not be recoverable by a new maintainer or external host.

#### Preventive AW package change

- Add a contributor path that starts from one small change and explains generated/managed boundaries.
- Add ownership depth and review-rotation metrics to source-checkout health, without pretending AW can create maintainers.
- Use architecture decision records for the runtime and packaging identities that currently live in code/history.
- Reduce hot-file concentration so review can be delegated safely.
- Create maintainer/runbook tests that a new checkout can execute without private context.

#### Exit criteria

- A new contributor can build, test, change, and release a bounded surface from public docs.
- Critical subsystems have at least one review path beyond implicit author knowledge.

---

### F20 — Development invocation and pre-commit behavior can mutate the wrong context

**Priority:** P2  
**Failure class:** A convenience invocation inherits ambient environment identity across worktrees.

#### Evidence

The configured invocation is:

~~~text
uv run --active python scripts/run_agentic_workspace.py
~~~

During this audit, invoking it in the isolated sibling while the original repository’s VIRTUAL_ENV was active caused uv to retarget editable package entries to the sibling checkout. The original environment was immediately restored with uv sync --active --frozen and verified, but a read-only startup should not have changed another worktree’s executable identity.

Other related friction:

- make sync-all is not frozen.
- Pre-commit runs repository-wide format, lint, and typecheck hooks; lint and typecheck are always_run.
- Open issues [#2443](https://github.com/rickardvh/agentic-workspace/issues/2443) and [#2444](https://github.com/rickardvh/agentic-workspace/issues/2444) are duplicate reports of validation run-ID collision.
- [#2445](https://github.com/rickardvh/agentic-workspace/issues/2445) reports generated freshness versus no-semver conflict.

#### Generic host impact

Parallel agents, worktrees, and sibling clones are ordinary agent workflows. Ambient environment reuse can silently point commands at a different checkout, invalidate proof provenance, or modify a shared environment during read-only routing.

#### Preventive AW package change

- Bind configured invocation to an explicit project root and executable identity.
- Before running, compare editable-package origins with the target checkout; refuse or use an isolated environment on mismatch.
- Guarantee that start, summary, report, and doctor do not sync or rewrite environments.
- Preserve active uv posture only when its project identity matches.
- Give every validation run a collision-resistant identity and atomic lifecycle.
- Make pre-commit checks staged/narrow where possible; reserve full validation for pre-push/CI.
- Deduplicate improvement issues by normalized evidence fingerprint before creating a second ticket.

#### Exit criteria

- A two-worktree fixture cannot retarget either environment during read-only commands.
- Proof receipts include executable and project identity.
- Concurrent validation runs never share mutable run state.

---

## 7. Preventive control map for generic host repositories

This is the central package-first interpretation of the findings.

| Repeating failure class | One-off host fix to avoid | AW-owned preventive control |
| --- | --- | --- |
| Installed instruction points to absent file | Add the missing file manually in each host | Compile and validate reference closure for every footprint/module combination |
| Temporary installer disappears | Tell each host to remember a custom command | Record and verify a durable invocation or block completion with an explicit handoff |
| Generated adapter drifts from contract | Patch one generated package | Require artifact-level semantic conformance before maturity/publishability |
| Freshness differs outside Git | Special-case each Dockerfile | Define a transportable artifact fingerprint independent of source-control metadata |
| Diagnostics are green despite broken live state | Manually inspect warnings after every run | Policy-aware strict health that fails only current actionable classes |
| Historical planning state floods reports | Delete archives ad hoc | Retention/distillation policy plus bounded compact receipts and optional external evidence |
| Agent output becomes too large | Ask each agent to use selectors better | Enforced byte/token budgets and decision-first default schemas |
| Runtime fix must be applied twice | Remember both mirror files | One canonical implementation with generated/imported compatibility |
| Shared environment targets wrong checkout | Re-sync the environment after damage | Target/executable identity guard and read-only no-sync commands |
| Duplicate dogfood issue | Close duplicates later | Evidence fingerprints and pre-creation dedupe |
| Host release branch is unsafe | Document “enable protection” | Provider posture detection that lowers release trust; explicit repo setting remains human-owned |
| Proof discovery finds a plausible but incomplete command | Review every heuristic suggestion manually | Parse declared target dependencies and classify confidence/completeness |
| Package is downloadable but not adoptable | Explain licensing in chat | Release-readiness policy for license, identity, metadata, SBOM, and provenance |

---

## 8. Recommended stabilization roadmap

### Phase 0 — Stop invalid artifacts from shipping

**Target:** Before the next support-bearing release.

1. Resolve license and Python/npm package identity.
2. Fix the transportable fingerprint and both Docker conformance lanes.
3. Make complete TypeScript semantic conformance mandatory in PR/release promotion.
4. Add clean-host module-matrix install/fallback tests and durable invocation verification.
5. Protect master and require the exact release gates for the tagged commit.
6. Either fix Python 3.14/Windows behavior or constrain declared support.

**Exit gate:** A clean, protected commit produces artifacts that install and pass Python, TypeScript, and container conformance from a second process with zero dangling required references.

### Phase 1 — Make the operating kernel maintainable and honest

**Target:** Next two to four weeks of focused engineering.

1. Declare and begin enforcing a single runtime owner.
2. Add live-health classification and a truly failing strict command.
3. Run the full root suite in CI with minimum/current Python and Windows coverage.
4. Freeze lock resolution in CI and proof containers.
5. Enforce output-size budgets for start, init, report, and selectors.
6. Add the security policy, threat model, scanning, least privilege, and action pinning.

**Exit gate:** Required CI is a faithful subset of the declared support contract, and default diagnostic/lifecycle output is bounded.

### Phase 2 — Reduce residue and prove value

**Target:** Four to eight weeks.

1. Introduce Planning archive distillation/retention.
2. Aggregate historical findings and make repo_friction scan tracked source.
3. Connect validation results to Verification evidence bundles.
4. Produce current successful-completion-cost evidence from repeatable fixtures.
5. Batch releases and define compatibility/deprecation windows.
6. Refresh generated ownership, maturity, install, and package metadata documentation.

**Exit gate:** The source dogfood repo demonstrates bounded state growth and measurable value over repeated tasks.

### Phase 3 — Resume capability expansion

Resume broad external-adapter, delegation, correction-guidance, and evaluation work only when:

- Phase 0 and Phase 1 gates remain green for at least one release cycle;
- no new public operation lacks both Python and TypeScript proof;
- output and residue budgets do not regress;
- each capability proposal shows which existing surface it composes or replaces.

---

## 9. Issue-ready improvement backlog

No issues were created because the audit was explicitly read-only. These are intentionally narrow candidates.

| Suggested issue | Smallest useful intended outcome | Proof |
| --- | --- | --- |
| Release gate: require semantic conformance for every runnable adapter | Add full Node conformance to required PR/release promotion and derive publishability from its receipt | Known failing fixtures block release; exact tarballs pass |
| Make generated source identity transportable outside Git | Split local Git acceleration from artifact content identity and fix both Docker conformance lanes | Git, no-Git, wheel, sdist, and npm identities agree |
| Enforce necessary-footprint reference closure | Compile installed references across every module/footprint matrix | Zero required missing references, including CLI-unavailable fallback |
| Resolve coordinated package names and durable install channel | Choose unique Python identities and publish one versioned, verified root install path | Clean second-process start succeeds without unrelated PyPI packages |
| Add license and release metadata completeness gate | Add owner-selected license and coordinated package metadata | Wheels/sdists/tarballs contain license; release fails fixture omission |
| Collapse workspace runtime mirror to one owner | Replace duplicated bodies with imports/generated facades and a shrinking allowlist | Duplicate body count ratchets to zero |
| Make strict health current-state aware | Add health classes and a failing live-state policy | Broken lane fails; archive history does not |
| Add output-profile budgets | Put config/effect inventories behind selectors and enforce byte/token limits | Idempotent init and ordinary start stay below budgets |
| Add Planning archive retention and distillation | Keep compact Git receipts, route durable intent, externalize optional full evidence | Long-lived fixture stays within state budget |
| Make repo-friction tracked-source aware | Ignore local caches by default and surface line/symbol/duplication/churn hotspots | Current runtime files appear as top hotspots |
| Integrate validation with Verification evidence | Turn successful proof manifests into admissible evidence bundles | Source checkout shows current evidence_bundle_count above zero |
| Add release/security readiness profile | Detect license, protected promotion, scanning, SBOM, attestation, and package identity | Release readiness becomes lower-trust/failing when absent |
| Deduplicate improvement intake | Fingerprint evidence before issue shaping | #2443/#2444-style duplicate yields one candidate |

Existing issues that appear adjacent rather than complete substitutes:

- [#2176](https://github.com/rickardvh/agentic-workspace/issues/2176): reuse unchanged projections.
- [#2198](https://github.com/rickardvh/agentic-workspace/issues/2198): extend operation conformance to external clients.
- [#2263](https://github.com/rickardvh/agentic-workspace/issues/2263): reproducible installed contract/invocation pair.
- [#2306](https://github.com/rickardvh/agentic-workspace/issues/2306): context consistency and freshness.
- [#2310](https://github.com/rickardvh/agentic-workspace/issues/2310): consequential AW-context findings.
- [#2365](https://github.com/rickardvh/agentic-workspace/issues/2365): active uv posture.
- [#2443](https://github.com/rickardvh/agentic-workspace/issues/2443) and [#2444](https://github.com/rickardvh/agentic-workspace/issues/2444): duplicate validation run-ID collision reports.
- [#2445](https://github.com/rickardvh/agentic-workspace/issues/2445): generated freshness and semver conflict.

---

## 10. Validation and audit evidence

### Repository isolation

The original checkout was on an agent branch and changed branches during the audit. All source analysis and test execution used a fresh sibling clone pinned to remote master. The original worktree was not reset, checked out, staged, or edited.

The isolated clone remained clean after validation. Generated checks rendered current content without tracked diffs.

### Executed checks

| Check | Result | Interpretation |
| --- | --- | --- |
| make check-bounded-parallel | **Pass**, 260.8 s | Strong local baseline; not sufficient as release proof |
| Ruff lint, format checks, Ty type checks | **Pass** | Static quality is healthy |
| Full root/module bounded test composition | **Pass** | Broad source behavior passes on local Windows/Python 3.14 environment |
| Generated Python adapter conformance | **Pass**, 48.3 s | Python semantic adapter path is currently healthy locally |
| TypeScript/npm package self-tests in Docker | **Pass** | Package-local samples and parser basics pass |
| Full TypeScript adapter conformance, Node 24 | **Fail**, 165 records | Release-major semantic behavior diverges |
| Full TypeScript adapter conformance, Node 25 | **Fail**, 165 records | Failure is not specific to Node 24 |
| Python Docker conformance | **Fail before semantics** | Non-transportable fingerprint |
| TypeScript Docker conformance | **Fail before semantics** | Same fingerprint defect; Windows decode traceback also observed |
| Primitive conformance, local | **Pass** | Generic primitive layer healthy in tested cases |
| Primitive conformance, Docker | **Pass** | Primitive portability healthy in tested case |
| Fresh v0.36.2 memory install via GitHub release wheels | **Pass** | Coordinated direct-URL wheel installation works |
| Fresh-footprint reference closure | **Fail**, seven targets | Necessary install is not self-contained |
| Local Markdown link scan | **28 missing occurrences** | Concentrated in installed payload/mirror and AW-state surfaces |
| pip-audit on installed environment | **No known vulnerable auditable dependencies** | Local packages and non-PyPI command-generation were not auditable |
| Bandit production scan | **147 findings: 145 low, 2 high** | High findings are intentional shell execution boundaries requiring threat-model review |
| uv lock --check | **Pass** | Current lock is internally current |

### Important interpretation

A passing broad suite and failing explicit conformance lane are not contradictory. They show that the project has substantial proof machinery but does not make the strongest relevant proof mandatory at promotion.

---

## 11. Quantitative repository profile

### Tracked surface

| Metric | Value |
| --- | ---: |
| Tracked files | 2,740 |
| JSON files | 1,702 |
| Markdown files | 537 |
| Python files | 375 |
| .agentic-workspace files | 1,011 |
| Generated files | 671 |
| Root src files | 389 |
| Package files | 247 |
| Docs files | 192 |
| Root test files | 67 |

Tracked line/size concentrations:

| Area | Bytes | Text lines |
| --- | ---: | ---: |
| .agentic-workspace | 11.50 MB | 197,925 |
| src | 11.46 MB | 262,257 |
| generated | 7.81 MB | 220,239 |
| packages | 3.74 MB | 82,717 |
| tests | 2.64 MB | 61,119 |
| scripts | 1.37 MB | 29,000 |
| docs | 1.24 MB | 17,469 |

### Tests and coverage

- Test trees contain about 2,208 statically named test functions and 82,202 Python lines.
- Memory coverage from its configured suite: 83%.
- Planning coverage from its configured suite: 76%.
- Root and Verification have no enforced coverage result.
- Coverage percentage alone is not the main concern; un-gated semantic and installed-artifact paths are.

### Churn

Most frequently touched paths in the last 90 days:

| Path | Commits touching path |
| --- | ---: |
| workspace_runtime_primitives.py | 405 |
| Planning state.toml | 207 |
| command_package_ir.json | 203 |
| test_workspace_cli.py | 194 |
| workspace_runtime_core.py | 194 |
| check_generated_command_packages.py | 176 |
| test_workspace_implement_cli.py | 172 |
| Planning mutation-provenance.json | 171 |
| root pyproject.toml | 147 |
| uv.lock | 139 |

High churn is understandable in a young project. Combined with beta labels, mirrored runtime code, and rapid releases, it becomes a compatibility and maintainer-risk signal.

---

## 12. Documentation and product assessment

### Public documentation

The main public documentation is one of the healthier parts of the repository:

- [README](../../README.md) is concise and honest about fit.
- [docs/index.md](../index.md) gives a useful owner map.
- [package overview](../package/overview.md), [modules](../package/modules.md), and [lifecycle](../package/lifecycle.md) provide a coherent conceptual route.
- [System Intent](../../SYSTEM_INTENT.md) and [design principles](../design-principles.md) make tradeoffs reviewable.
- Historical reviews are visibly dated rather than silently presented as current authority.

The main weakness is not prose quality; it is executable drift between public descriptions and installed/generated state. The best fix is generation and invariant checks, not another manual rewrite.

### Shipped product

The shipped product currently has three distinct realities:

1. **Source-checkout AW:** rich, heavily dogfooded, 1,011 checked-in AW files, many diagnostics and contracts.
2. **GitHub release wheels:** coordinated and hash-linked, workable when invoked through exact release URLs.
3. **Necessary host footprint:** small, but not referentially closed and not paired with a durable installer invocation.

The product should define which reality is normative for beta support and make the others mechanically equivalent at their shared boundaries.

### Direction

The intended direction—repo-native continuity, proof, authority, and adapter-neutral operations—is coherent. The immediate direction should be **fewer representations with stronger promotion gates**:

- one runtime owner;
- one installed-surface manifest;
- one artifact identity;
- one strict live-health policy;
- one durable install story;
- one proof receipt per shipped target.

That consolidation directly supports later external adapters, delegated work, evaluation, and correction learning.

---

## 13. Limitations and claim boundary

- The audit examined remote master at the pinned commit, not the other agent’s active branch or unmerged draft PR implementations.
- The audit used automated inventories, AST analysis, targeted source review, black-box lifecycle tests, full project validation, container checks, and live repository/release metadata. It did not manually read all 2,740 files line by line.
- No destructive lifecycle operation was run.
- No GitHub issues, comments, branches, settings, or releases were changed because the request was read-only.
- Registry and GitHub state is time-sensitive and reflects 2026-08-08.
- GitHub download counters are not unique-user analytics; the audit itself incremented four latest-release wheel counters and disclosed that effect.
- pip-audit could not attest unpublished local packages or command-generation. Bandit is a heuristic scanner, not a penetration test.
- macOS and the full declared Python-version matrix were not executed. Their absence from CI is itself a finding.
- Docker proof created local build cache/images but did not change tracked source.
- Product-value conclusions are limited by the repository’s own no-evidence completion-cost result and lack of external user studies.

---

## 14. Bottom line

Agentic Workspace has enough real engineering and product thought to justify continued investment. Its present risk is not lack of features or lack of tests. It is **failure to make the strongest existing contracts control what gets installed, called healthy, and shipped**.

The package-first improvement strategy is therefore:

1. turn contracts into mandatory promotion gates;
2. make identities and references portable across source and artifact contexts;
3. make live health, output cost, and residue budgets consequential;
4. consolidate duplicated owners;
5. publish a legally and technically durable install identity;
6. resume feature growth only after those invariants hold.

If those changes land, the same classes of broken fallback, stale proof, noisy health, duplicated runtime, and environment mismatch will be prevented for every future host instead of repaired one repository at a time.
