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
both binaries and set `AGENTIC_WORKSPACE_CORE_BINARY` explicitly. Importing a
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

Host-labelled artifacts establish support only for the host exercised. Linux
wheels retain `linux_*` tags; they do not claim manylinux compatibility. The
release matrix runs the same isolated native proof per host/runtime, and final
release/preview checks prove the bytes actually published. Local Windows results
are not Linux/macOS proof. Preview assets remain non-support-bearing; stable
promotion still requires the separate exact-subject server, runtime, install,
redistribution and security receipts. Implementation completion does not grant
independent review acceptance, merge readiness or parent-issue closure.
