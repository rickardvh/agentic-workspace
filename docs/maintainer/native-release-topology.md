# Native release topology

The shipped set is one `agentic-workspace` Python distribution (wheel and
source archive), one `@agentic-workspace/workspace-cli` npm distribution, and
one host-labelled archive containing `agentic-workspace` and
`agentic-workspace-core`, plus the coordinated Cargo source pair described below.
Both language packages carry the identical executable pair. The Rust core owns
decisions, answer admission, effects and continuations.

Canonical language source lives under `src/cli/python` and `src/cli/typescript`.
Codex protocol I/O lives under `src/adapters/codex`. Wheel source mappings join
the Python facade and provider portions into the existing `agentic_workspace`
package; editable development uses the same portions through its package path.
The six installed modules and `agentic_workspace.sealed_codex_transport` command
remain unchanged. No duplicate source implementation is retained.

The installed Python API exports `start`, `invoke`, `resources`, `select_reference`,
`answer_carried` and `invoke_carried`; npm exports their camel-case equivalents
from the package root and `./operating`, with TypeScript declarations. `./native`
retains the low-level JSON transport projection. The command launchers forward
to the paired Rust CLI. Packaged manifests bind version and binary digests;
missing or altered executables fail explicitly. Source developers must build
both binaries with `cargo build --locked --workspace --bins`. The source Python
binding and repository launcher resolve that checkout's prepared pair. Custom
build directories and standalone Node development use an explicit
`AGENTIC_WORKSPACE_CORE_BINARY` override. Importing a
binding never starts Cargo or falls back to a Python/generated command host.

The installed consumer contract is the capability contract returned by native
`start`. The prerelease `external_operation_conformance_receipts` Python export
and private `_generated_cli_package_impl` resources are retired installed APIs;
source-only conformance fixtures do not make them wheel compatibility promises.
The isolated wheel consumer test checks the current API with development core
overrides removed and checks that those retired surfaces remain absent.

Repository-only Python helpers live in `src/tooling/python/aw_maintainer`.
`native_conformance` exposes internal Rust vector/contract operations for tests;
public consumers import `agentic_workspace` directly. `contracts`,
`ownership_profile` and `review_topology` serve source generation and GitHub
maintainer workflows. `session_diagnostics` reads and exports existing native
logs; it does not implement capture or workflow authority. Editable development includes this tooling path; wheels
exclude it. Former helper imports under `agentic_workspace` have no aliases.

The former Python clients, domain host, compatibility aliases and generated
Python/TypeScript execution trees are removed. Planning, Memory and Verification
execute in `src/core/src/modules/`; their native schemas live beside their owner.
The former `packages/` installer trees and generated operation catalogues are
removed. Shared contracts live in `src/core/contracts/`, embedded operating
resources in `src/core/payload/`, and the native CLI in `src/cli/rust/`.
The source archive contains binding sources and exact Rust compile inputs,
including canonical contracts and bundled operating resources.

Build the wheel/source archive with `uv build --wheel --sdist`. Stage npm and
the native archive with `src/tooling/release/stage_native_npm.py --output <new-dir>
--native-archive-dir <artifact-dir>`, then `npm pack` that staging directory.
The staging directory and native archive must be absent before creation.

The npm manifest is authored in `src/cli/typescript/package.json`; staging supplies
the version and description from `pyproject.toml`, the host constraints and paired
native artefacts. The source manifest is private until staging installs those
artefacts. Staging reads the binding files directly and does not consume
`generated/workspace/`. The source archive includes these canonical inputs and
the release helpers needed to rebuild them.

`src/tooling/check/check_native_release_topology.py` consumes exactly one wheel,
source archive, npm archive and native archive from `--artifact-dir`. It installs
the packages in isolated consumers, clears tool lookup and source overrides,
performs a carried owner-authorised write through each binding, checks binary
tampering rejection, and compares both packaged executables byte-for-byte with
the standalone pair. It does not rebuild artefacts. Its receipt binds exact
asset hashes, source commit, proof implementation, Node version and execution
context; verification rejects stale inputs. Historical receipt filenames remain
for release manifest compatibility, with the new `native-release-conformance/v1`
kind. Current native owner tests, public binding conformance and isolated artifact
consumers replace the retired generated-command runners.

The final promotion composer uses this same receipt validator for the exact
source and artefact set. Only intact hosted proofs from clean source may satisfy
its semantic runtime lanes; a passed status or recognised Node version alone
cannot admit a receipt.

Host-labelled artefacts establish support only for the host exercised. Before
hosted proof and registry publication, Linux wheels are audited against
`manylinux_2_39_x86_64`; only compatible wheels are relabelled, with their native
executable bytes unchanged. Source builds alone do not establish that ABI. The
release matrix runs the same isolated native proof per host/runtime, and final
release/preview checks prove the bytes actually published. The required publication set is Windows, macOS and Linux on x64 and ARM64, declared in `.github/release-platforms.json`. Each platform builds natively and installs the assembled Python, npm and standalone artefacts with Rust absent from the consumer PATH. Previously published Linux-only artefacts retain their original boundary. Preview assets remain non-support-bearing; stable
promotion still requires the separate exact-subject server, runtime, install,
redistribution and security receipts. Implementation completion does not grant
independent review acceptance, merge readiness or parent-issue closure.

The published macOS minimum is **macOS 15.0 on Intel x64** and **macOS 14.0 on Apple Silicon ARM64**, as declared in `.github/release-platforms.json`. Both Rust executables are built with that explicit `MACOSX_DEPLOYMENT_TARGET`; Python wheel tags and the platform inventory bound by installation receipts carry the same minimum. Compiler-free macOS coverage is limited to these versions and newer. Older macOS versions are not covered by release installation proof.

## Exact installed owner conformance

Explicit exhaustive CI builds one coordinated artefact set before Workspace,
Planning handoff and declared-runtime proof. Those jobs download the same assets
and select `AW_NATIVE_ARTIFACT_DIR`; existing shared fixtures then install the
wheel/npm packages outside the checkout and extract the native pair. Source
commit, manifest identities and actual executable bytes must agree. Missing or
mismatched artefacts fail before owner execution, without a Cargo fallback.
Public consumers clear development binary/module overrides and use the installed
bindings, retaining the original owner assertions rather than duplicating semantics.
Scenarios preserve required host tools such as Git for pinned-source admission;
explicit empty-PATH and missing-core cases still prove unavailable-runtime rejection.

Command evidence binds the actual producer executable location. A Python/npm
proof-reuse case therefore produces through that installation's paired native
CLI. Cross-location and changed-binary rejection remain separate negatives.
The sealed provider handoff fixture uses the installed wheel's transport primitive;
its simulated provider response does not establish live-provider availability.

The existing topology checker retains receipts on each declared runtime and Node
semantic major. Those receipts prove installed topology and exact asset identity;
owner, Planning and custody behaviour is evidenced by the corresponding CI job
results. Neither the receipt alone nor the workflow prerequisite aggregate supplies
independent admission or a publication decision. Ordinary PR checks remain bounded.

## Candidate A publication handoff (#3275)

The implementation stack is configuration convergence (#3280), required Assignment
admission (#3281), then Candidate A release preparation. Each dependent change needs
independent review and acceptance before publication from `master`. The publisher
dispatch and source-ancestry check both trust `master`; the historical
`reconstruction_source_commit` manifest key and `--reconstruction-ref` option remain
compatible. A non-master override is limited to local preparation and cannot push.

Candidate A remains [Alpha](../maturity-model.md#alpha).
The intended version is `preview-v0.55.0`, subject to a fresh unused-version check.
The implementation stack does not create or reserve that tag. After the stack is
accepted and merged, record the exact accepted `master` SHA and run the existing
preview preparation flow with `--version 0.55.0 --source-commit <accepted-sha>`.
Supply `--isolation-policy-revision` only after reading the resource owner's current
policy and judging that it permits the concrete normalisation isolation. Add
`--push` only for the accepted publication run. The resource owner manages the
temporary release checkout and cleanup; a dirty failure must retain its evidence.

Require successful exact-source CI/security, installed native runtime proof,
provenance, manifest and checksum checks from the existing preview workflow. Then
run `src/tooling/release/preview_release.py --check-published preview-v0.55.0 --repo
rickardvh/agentic-workspace` from the exact artefact checkout, and the existing
public install smoke on its supported host against the published assets. The
source checkout can instead use `--admit-tag` with the exact `--artifact-commit`
to verify Git objects without substituting its development version. Local tests
cannot substitute for those exact published bytes.
Do not overwrite a tag or asset to recover a failed publication; reuse the existing
immutable-subject recovery. Keep #3275 and #2985 open until their respective
independent acceptance and intent conditions are actually satisfied.

The root `uv.lock` is the single dependency lock for the source workspace, including
its retained module fixtures. Obsolete module-local locks are removed, and the
existing security readiness control rejects their reintroduction. Dependency alert
closure must be checked after the accepted default branch is scanned; removal in
an unmerged PR does not establish closure of a hosted alert.

## Candidate A publication record

[preview-v0.55.0](https://github.com/rickardvh/agentic-workspace/releases/tag/preview-v0.55.0)
was published on 2026-09-15 as an immutable, non-support-bearing Alpha preview.

| Identity | Exact value |
| --- | --- |
| Accepted master source | `b5a7748a493a6ea257ec4ad5a9696336a66bfdf2` |
| Release-only artefact commit | `ce0eef8cc89bbecdbda39fbe0051118dd9492eae` |
| Manifest SHA-256 | `bf04966bff10f1fb16889d52098b8f5f5acef5a74126c1f581fdefa395f5930d` |
| Root Linux x64 wheel SHA-256 | `4d26fa2057bdaa36469093333e1d9bc4d6c80099ab53a3dfbecc9c232d7a8474` |

The [publication run](https://github.com/rickardvh/agentic-workspace/actions/runs/34946934597)
passed exact source/tag/parent admission, all three hosted runtime jobs, native
artefact conformance, install/redistribution/security readiness, provenance,
manifest/checksums and public-byte installation/start. The public smoke reports
runtime `0.55.0`. A separate downloaded-asset verification returned `complete: true`
for all 13 release assets. `gh attestation verify` on the downloaded manifest
succeeded for this repository and identified the master preview workflow and that
publication run. These checks do not extend the Linux x64 support boundary.

#3274 closed after the corrected-head independent acceptance in #3281 and its
accepted-base merge. #2767 closed by reconciling #3280's final source-runtime and
former-local-intent correction with accepted #3178 source writes, #3185 independent
settings ingress, #3230 configuration decisions/progressive discovery, #3241 lazy
owner schemas, and #3252/#3254 lived-in and composed-upgrade convergence. Their
existing owner evidence is reused; closure does not assert new provider guarantees.
#3275 was administratively closed before publication; the run and byte evidence
above establish the subsequent publication outcome. #2985 remains open for final
support-bearing admission, and the maturity promotion reason remains explicit.

The release helper preserved its temporary checkout when commit hooks created
unleased Ruff/uv caches and validation output. Only these known new outputs were
relocated to task scratch; uv cleaned its cache, then native resource removal
succeeded. Do not broaden cleanup to unrelated ignored files or worktrees. Hosted
Dependabot alerts 1–3 still reported open for removed member locks when checked;
the active workspace lock and exact preview security checks passed. No hosted
alert dismissal or closure is inferred from source removal.

## Candidate B publication record

The accepted executable-skill stack is published as non-support-bearing
[`preview-v0.56.0`](https://github.com/rickardvh/agentic-workspace/releases/tag/preview-v0.56.0).
Source `3fd508feba856354e30fd4afc82930f2e6012c87` is the single parent of release-only
artefact `87cf9ea4b2b0e1d6d59152ef707c3900b5b90595`.
[Run 34962615722](https://github.com/rickardvh/agentic-workspace/actions/runs/34962615722)
passed runtime/package/security/provenance and public-byte installation/start proof.
The [Candidate B reconciliation](../reviews/candidate-b-publication.md) records
independent leaf acceptance, downloaded-asset verification, real issue-creation
dogfood, exact cleanup recovery and residual ownership. Public maturity remains
Alpha; Candidate C and support-bearing v1 admission remain separate.

## Candidate C prepublication reconciliation

The [integrated acceptance input](../reviews/candidate-c-integrated-acceptance.md)
records the accepted #3359 aggregate and the post-implementation reconciliation
through #3389. RC identity (#3360), public facade/subtraction (#3365), registry
projection and Cargo packaging (#3366/#3367), later owner/host corrections, and
the final command-authority cleanup (#3389) are merged. The reconciliation is
ready for independent review; merged implementation does not prove publication.

Candidate C has no publication record here. Reopened #3361 owns the remaining
PyPI/npm bootstrap, trusted-publisher and public-byte/install outcome; reopened
#3362 owns the corresponding paired Cargo outcome. Their merged repository
implementations do not close those external requirements. Release-owner
environment setup and exact hosted artefacts also remain required.
Follow the existing first-stable RC preparation path
from the fresh accepted master after reconciliation, then publish/exercise
`v1.0.0-rc.1`. Only an independently accepted RC may feed fresh stable
preparation/admission/publication under #2985. Closed pre-C #3283 is superseded.

## Coordinated Cargo distribution

The public Cargo surface is the existing `agentic-workspace-core` and
`agentic-workspace-cli` crates, in that publication order. Both versions come from
the release owner's `package_versions.cargo` mapping; the source manifests and
their two local Cargo.lock entries are normalised together. Third-party lock
resolution is not a release-only normalisation.

After the corresponding registry publication receipt passes, install both exact
versions into the same Cargo root, core first. For the first candidate:

```sh
cargo +1.98.1 install --locked agentic-workspace-core --version '=1.0.0-rc.1'
cargo +1.98.1 install --locked agentic-workspace-cli --version '=1.0.0-rc.1'
agentic-workspace start --target . --task 'Inspect this repository' --format json
```

Use the stable mapped version only after its independent support admission.
Installing the CLI alone is not the supported paired installation. Registry
availability does not widen the release's admitted platform/toolchain classes.

`src/tooling/release/cargo_release.py` stages the existing sources, relocates literal
compile-time resource references into `_inputs`, and retains the original bytes
of included Rust source used for owner identities. The Cargo payload inventory
explicitly includes hidden `.agentic-workspace` resources. The standalone lock is
pruned by Cargo and checked to contain only the original locked third-party
identities. No executable domain implementation is generated or forked.

The existing publisher builds and verifies each `.crate`, installs from the actual
archives in a clean Cargo home, and includes the crates and
`cargo-release-manifest.json` in checksums, SBOM inputs and attestations. Registry
publication reconstructs packaging and compares the bytes before uploading;
matching versions are reused, conflicting/yanked versions fail, and an uncertain
upload is reobserved on the next invocation. The CLI upload requires its exact
core predecessor to be public. Public verification checks the archive downloaded
by the clean Cargo consumer, not only registry metadata.

crates.io requires the first version of each crate to exist before configuring a
trusted publisher. The package owner performs that one-time bootstrap only from
an independently admitted release: download its admitted assets, run the same
staging/byte comparison, publish core before CLI using a short-lived manually
authorised credential, and verify the public bytes. Record the receipt and revoke
the bootstrap credential. Configure the calling workflows `preview-release.yml`
and `release.yml` for `rickardvh/agentic-workspace`, environment `cargo-registry`,
before ordinary OIDC publication. The registry workflow contains no persistent
Cargo token secret; its token comes from the Rust team's authentication action.
See the [Rust trusted-publishing announcement](https://blog.rust-lang.org/2025/07/11/crates-io-development-update-2025-07/)
and [authentication action](https://github.com/rust-lang/crates-io-auth-action).

Account bootstrap, trusted-publisher configuration and live registry receipts are
external acceptance steps. Local staging/build/install proof does not establish
their completion or authorise the final RC/stable release.

The sandbox model harness captures one Codex execution and its output artifact.
It does not invoke the retired Python final-response admission/auto-resume route.
Evaluation and native owner evidence remain separate from transport exit status.
