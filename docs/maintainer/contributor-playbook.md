# Contribute to AW

Use this guide to change Agentic Workspace itself. To configure AW in another
project, use the [user guide](../index.md). Agents contributing here must also read
[AGENTS.md](../../AGENTS.md) and any repository instructions that apply to the
files they change.

## Prepare a checkout

You need Git, the Rust toolchain pinned by `rust-toolchain.toml`, Python and
`uv`. Node is needed for TypeScript and cross-language checks.

```bash
git clone https://github.com/rickardvh/agentic-workspace.git
cd agentic-workspace/
make setup
cargo build --locked --workspace --bins
```

`make setup` prepares the shared development environment and installs this
checkout's Git hooks. The Cargo command builds both native executables; keep them
together.

Rebuild after changing Rust code or bundled contracts/resources. Imports must not
silently build Cargo or fall back to an older implementation.

Use [Maintainer commands](maintainer-commands.md) for focused setup and checking
commands.

## Find the implementation responsible for the behaviour

Start from what the user or agent observes, then locate the code or document that
actually defines it.

| Change | Start here |
| --- | --- |
| Shared runtime behaviour, permissions, saved component state or controlled changes | `src/core/` |
| CLI options or forwarding | `src/cli/rust/` and the native CLI contract |
| Python / TypeScript API transport | `src/cli/python/` / `src/cli/typescript/` |
| Human documentation and examples | The relevant user, reference or maintainer page |
| Generated schemas or catalogues | Their source contract or generator, not the generated file |
| Repository-maintainer procedure | `tools/skills/` and its current procedure |

Read [Architecture](../architecture.md) when a change crosses those areas.

Planning, Memory and Verification implementations live under
`src/core/src/modules/`. Shared Rust contracts live in `src/core/contracts/`.
The core embeds its generated package files from `src/core/payload/`.

Maintainer tooling lives under `src/tooling/`:

- `check/` validates source and package properties;
- `generate/` produces derived files;
- `release/` builds and publishes releases;
- `model-cli-harness/` contains evaluation runners;
- `github/` contains GitHub workflow helpers;
- `python/aw_maintainer/` contains shared development-only Python helpers;
- `contracts/` contains maintainer-tool schemas and data.

Do not treat `.agentic-workspace/` as scratch space. Use the supported AW
operation for package-managed records and change generated/package files at their
source.

## Keep the change focused

Describe the problem and expected result before choosing an implementation.
A PR should be understandable on its own: code, documentation and current evidence
should agree on what changed.

For documentation, follow the
[documentation style guide](../documentation-style-guide.md).

Do not create Planning or Memory records merely to demonstrate AW. Save unfinished
work before stopping only when another session would otherwise have to reconstruct
important context.

## Choose evidence

Read the [testing strategy](testing-strategy.md) before changing behaviour, tests
or CI.

Name the failure the patch could introduce, reuse existing evidence where it
already catches that failure, and test at the lowest useful level.

Typical starting points:

- focused Cargo tests for shared Rust behaviour;
- focused Python or Node tests for language/API transport;
- link, generation and example checks for documentation;
- package tests when package contents or installation behaviour changed.

Use [Maintainer commands](maintainer-commands.md) for exact commands.

The ordinary hosted requirement is **Merge sufficiency**. Broader package,
runtime-matrix or release qualification should run only when the change creates a
specific risk those checks can expose.

Report which commands actually ran, what they tested and any remaining gap. Do not
describe skipped checks as passing.

## Open the PR

Use the [PR template](../../.github/PULL_REQUEST_TEMPLATE.md). State:

- what changed;
- why it satisfies the issue;
- what was checked;
- what remains unresolved.

Package-affecting changes need the appropriate semver label and release fragment.
A documentation-only change is not itself a release or a maturity change.

An agent that implemented or materially changed the patch must not independently
approve it or direct a child agent to provide that approval. Mark completed work
ready for independent review and leave approval to a separately initiated
reviewer using the [review skill](../../tools/skills/pr-review-recheck/SKILL.md).

Use the [issue-shaping skill](../../tools/skills/github-issue-shaping/SKILL.md)
before creating follow-up issues and the
[issue-creation skill](../../tools/skills/github-issue-creation/SKILL.md) when
publishing them.
