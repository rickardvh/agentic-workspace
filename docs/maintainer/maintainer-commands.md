# Maintainer commands

Run these in an AW source checkout, not in a project that merely uses AW.
Start with [Contribute to AW](contributor-playbook.md) for setup and change boundaries.

## Prepare and build

| Command | Result |
| --- | --- |
| `make setup` | Synchronise the shared environment and install this clone's Git hooks. |
| `make install-hooks` | Restore the repository-managed hooks without requesting a different workflow. |
| `make sync-all` | Synchronise the shared workspace environment. |
| `cargo build --locked --workspace --bins` | Build the paired native CLI and core with the pinned toolchain. |

Build both binaries before using source-checkout AW and after changes to Rust or
bundled resources. The [Makefile](../../Makefile) and
[toolchain guide](rust-toolchain.md) define the exact setup behaviour.

## Check a change

Choose evidence for the changed behaviour using the [testing strategy](testing-strategy.md).
These are available commands, not a checklist to run in full on every patch.

| Command | Purpose |
| --- | --- |
| `cargo fmt --all -- --check` | Check Rust formatting. |
| `cargo test --locked -p agentic-workspace-core <test-filter>` | Run selected Rust core tests; replace the filter with the relevant test name. |
| `uv run --frozen pytest <test-path> -q` | Run a focused Python or public-consumer test file. |
| `make lint` | Run workspace lint. |
| `make typecheck` | Run workspace type checks. |
| `make check` | Run the broader root validation composition when the claim warrants it. |

For a caller that has already synchronised dependencies, use the corresponding
available `*-nosync` target rather than repeating setup. Test execution is serial
by default; parallel execution needs a deliberate local capacity choice.

The Git hook runs its own bounded formatting/lint/type checks. Passing it does not
replace focused proof for the changed behaviour. Hosted **Merge sufficiency** and
explicit exhaustive admission are separate evidence levels; see the testing
strategy for their current scope.

## Refresh generated material

Read a generated file's source notice before choosing a command.

| Command | Purpose |
| --- | --- |
| `make render-schema-reference` | Regenerate schema and contract reference pages. |
| `make schema-reference-docs` | Check the generated reference pages against their sources. |
| `make render-agent-docs` | Regenerate the maintained agent-routing projections. |
| `make maintainer-surfaces` | Check the relevant maintained source/payload/routing surfaces. |

These commands maintain source-derived output; they do not adopt another
repository or authorise edits to retained owner state. Package-specific refresh
and release artefact checks belong to the [source/payload boundary](source-payload-operational-install.md)
and [native distribution reference](native-release-topology.md).

## Specialised maintenance

Use the dedicated procedure rather than copying a long command from a historical
report: [release and versioning](../release-and-versioning.md),
[review workflow](../../tools/skills/pr-review-recheck/SKILL.md), or
[local review continuation tooling](chatgpt-review-continuation.md).
Review polling is opt-in local tooling, not part of ordinary contribution setup.
