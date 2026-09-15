# Native release topology

The shipped set is one `agentic-workspace` Python distribution (wheel and
source archive), one `@agentic-workspace/workspace-cli` npm distribution, and
one host-labelled archive containing `agentic-workspace` and
`agentic-workspace-core`. Both language packages carry the identical executable
pair. The Rust core owns decisions, answer admission, effects and continuations.

The installed Python API exports `start`, `invoke`, `select_reference`,
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

Legacy Python clients, operations, generated command trees, and the three module
distributions remain source development and migration fixtures. They are not
wheel contents, installed dependencies, npm contents, or release assets. The
source archive contains binding sources and exact Rust compile inputs, including
canonical contracts and bundled operating resources; those resources are not a
second language runtime. Release ownership records this disposition explicitly.

Build the wheel/source archive with `uv build --wheel --sdist`. Stage npm and
the native archive with `scripts/release/stage_native_npm.py --output <new-dir>
--native-archive-dir <artifact-dir>`, then `npm pack` that staging directory.
The staging directory and native archive must be absent before creation.

`scripts/check/check_native_release_topology.py` consumes exactly one wheel,
source archive, npm archive and native archive from `--artifact-dir`. It installs
the packages in isolated consumers, clears tool lookup and source overrides,
performs a carried owner-authorized write through each binding, checks binary
tampering rejection, and compares both packaged executables byte-for-byte with
the standalone pair. It does not rebuild artifacts. Its receipt binds exact
asset hashes, source commit, proof implementation, Node version and execution
context; verification rejects stale inputs. Historical receipt filenames remain
for release manifest compatibility, with the new `native-release-conformance/v1`
kind. Historical generated-command proofs remain source-only checks.

The final promotion composer uses this same receipt validator for the exact
source and artifact set. Only intact hosted proofs from clean source may satisfy
its semantic runtime lanes; a passed status or recognized Node version alone
cannot admit a receipt.

Host-labelled artifacts establish support only for the host exercised. Linux
wheels retain `linux_*` tags; they do not claim manylinux compatibility. The
release matrix runs the same isolated native proof per host/runtime, and final
release/preview checks prove the bytes actually published. The admitted published class is Linux x64 only. Windows and macOS are not
supported release classes; local Windows validation is development evidence. Preview assets remain non-support-bearing; stable
promotion still requires the separate exact-subject server, runtime, install,
redistribution and security receipts. Implementation completion does not grant
independent review acceptance, merge readiness or parent-issue closure.

## Exact installed owner conformance

Explicit exhaustive CI builds one coordinated artifact set before Workspace,
Planning handoff and declared-runtime proof. Those jobs download the same assets
and select `AW_NATIVE_ARTIFACT_DIR`; existing shared fixtures then install the
wheel/npm packages outside the checkout and extract the native pair. Source
commit, manifest identities and actual executable bytes must agree. Missing or
mismatched artifacts fail before owner execution, without a Cargo fallback.
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
owner, Planning and custody behavior is evidenced by the corresponding CI job
results. Neither the receipt alone nor the workflow prerequisite aggregate supplies
independent admission or a publication decision. Ordinary PR checks remain bounded.

## Candidate A publication handoff (#3275)

The implementation stack is configuration convergence (#3280), required Assignment
admission (#3281), then Candidate A release preparation. Each dependent change needs
independent review and acceptance before publication from `master`. The publisher
dispatch and source-ancestry check both trust `master`; the historical
`reconstruction_source_commit` manifest key and `--reconstruction-ref` option remain
compatible. A non-master override is limited to local preparation and cannot push.

Candidate A remains [Alpha](../maturity-model.md#candidate-a-disposition-3275).
The intended version is `preview-v0.55.0`, subject to a fresh unused-version check.
The implementation stack does not create or reserve that tag. After the stack is
accepted and merged, record the exact accepted `master` SHA and run the existing
preview preparation flow with `--version 0.55.0 --source-commit <accepted-sha>`.
Supply `--isolation-policy-revision` only after reading the resource owner's current
policy and judging that it permits the concrete normalization isolation. Add
`--push` only for the accepted publication run. The resource owner manages the
temporary release checkout and cleanup; a dirty failure must retain its evidence.

Require successful exact-source CI/security, installed native runtime proof,
provenance, manifest and checksum checks from the existing preview workflow. Then
run `scripts/release/preview_release.py --check-published preview-v0.55.0 --repo
rickardvh/agentic-workspace` and the existing public install smoke against the
published assets. Local tests cannot substitute for those exact published bytes.
Do not overwrite a tag or asset to recover a failed publication; reuse the existing
immutable-subject recovery. Keep #3275 and #2985 open until their respective
independent acceptance and intent conditions are actually satisfied.

The root `uv.lock` is the single dependency lock for the source workspace, including
its retained module fixtures. Obsolete module-local locks are removed, and the
existing security readiness control rejects their reintroduction. Dependency alert
closure must be checked after the accepted default branch is scanned; removal in
an unmerged PR does not establish closure of a hosted alert.
