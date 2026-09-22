# Repository layout

The authored product lives under `src/`. Follow behavior to its owner rather than
choosing a language first.

| Path | Authority and lifetime |
| --- | --- |
| `src/core/` | Rust decisions, state, effects, source admission and continuation. Shared contracts are in `contracts/`; Memory, Planning and Verification code and schemas are in `src/modules/`. |
| `src/cli/rust/` | Native command parsing and transport into the core. |
| `src/cli/python/` | Thin Python API and launchers; no second semantic host. |
| `src/cli/typescript/` | Thin Node API, declarations and launcher; staging supplies the published package identity. |
| `src/adapters/codex/` | Codex protocol input/output packaged with the Python facade. |
| `src/tooling/` | Development-only checks, generators, release tooling, GitHub helpers and model harness. Its Python helpers are not wheel APIs. |
| `tests/` | Native-owner scenarios, transport/artifact checks and stable fixtures. Disposable operating history is not a fixture source. |
| `docs/` | User and contributor guidance, reference projections and explicitly historical design/review records. |
| `tools/skills/` | Human/agent repository procedures; executable helpers live in `src/tooling/`. |
| `.agentic-workspace/` | Repo-local owner sources, current declarations and operating context. It is not product implementation or a general event archive. |
| `.github/`, `.release/` | CI/release policy, compact release changes and published release provenance. |

`target/`, `dist/`, caches, scratch and package staging directories are local build
or task outputs. No tracked `bindings/`, `crates/`, `packages/`, `scripts/` or
`generated/` compatibility implementation remains. Old ignored directories in an
existing developer checkout do not define another source root.

## Generated material

Contract/reference pages are checked in so readers can inspect the public shape
without running the toolchain. Edit their source schema or generator and rerun the
named generation check. The generated read profile and bundled operating payload
remain checked in because the native executable embeds them for standalone use;
they are reproduced from their declared source owners. Wheels, npm packages and
native archives are built on demand, not treated as authored checkout code.

Use `make render-schema-reference` and the agent-interface generator for source
projections. `uv build --wheel --sdist` and the native npm staging tool consume the
canonical sources above. Cargo stages the coordinated core/CLI pair from the same
workspace. [Native release topology](native-release-topology.md) describes exact
artifact contents, provenance and isolated consumer proof.

## Operating state

Planning retains unresolved or currently referenced intent. Its terminal owner can
retire exact closed groups after value judgment; historical location alone grants
no deletion authority. Verification keeps reusable/current evidence and replaces
superseded authenticated projections. Memory separates selection retirement from
terminal source removal and preserves explicit human retention requirements.
See [Planning lifetime](planning-lifetime-boundary.md) and
[Memory lifetime](memory-lifetime-boundary.md).

Evaluation conclusions, reconstruction admissions and older Verification decisions
that have no current append producer remain source-owned records with explicit
continuing consumers or unresolved authority. Their existence does not authorize
new event history. The existing structured inventory requires every wildcard
enclave family to declare its replacement or terminal lifetime before a new family
can be added. Producer changes still need bounded lifecycle proof; a descriptive
inventory entry is not evidence that a producer is bounded.

Contributor orientation should work from a fresh checkout: locate semantic changes
in Rust, public transport changes in `src/cli`, provider changes in `src/adapters`,
and maintainer commands in `src/tooling`. Historical review records and admitted
source snapshots retain their original scope; they do not redirect current edits.
