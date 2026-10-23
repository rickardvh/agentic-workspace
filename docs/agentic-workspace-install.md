# Getting started

Install AW, add it to a Git repository, then give your coding agent ordinary work.
Use an agent that can read repository instructions and run commands.

## 1. Install AW

Pin AW per repository when repositories need independent versions; otherwise a
shared installation is fine. Choose npm, Python/uv, Cargo or a standalone archive
according to your tooling. Keep using that installation when running AW.

Minor upgrades preserve supported configuration and durable work, with normal
managed-file refresh when needed. See the
[compatibility policy](release-and-versioning.md#package-compatibility-boundary).
Cargo provides the paired executables. For embedding, the supported core Rust
API is [`operating::{start, invoke}`](architecture/shared-rust-core.md).

Package registries resolve the current stable release. A repository-local npm
install can record the resolved version exactly; for other package managers, add
an explicit version when your repository needs the same version on every machine.
Standalone downloads are available from the
[latest stable GitHub release](https://github.com/rickardvh/agentic-workspace/releases/latest),
whose attached receipts and checksums describe the exact release files.

| Distribution | Install |
| --- | --- |
| npm | `npm install --save-dev --save-exact @agentic-workspace/workspace-cli` in the repository; use `--global` instead of `--save-dev --save-exact` for a shared tool |
| Python/uv | `uv pip install agentic-workspace` in your repository's virtual environment, or `uv tool install agentic-workspace` for a shared tool; use `agentic-workspace==<version>` when pinning |
| Cargo | `cargo install --locked agentic-workspace-core`, then `cargo install --locked agentic-workspace-cli`; when pinning, pass the same `--version` to both crates and use the same `--root` for a repository-specific location |
| Standalone | Open the latest stable GitHub release, choose the archive for your platform and keep both executables together |

Run `--help` using that installation: `npm exec --no -- agentic-workspace` for
repository-local npm, `agentic-workspace` in the selected environment or on PATH,
or the executable's path for a custom location.

## 2. Add AW to the repository

From the Git working-tree root, append `setup` to your chosen invocation. For a
shared tool on PATH:

```sh
agentic-workspace setup
```

For a repository-local npm installation:

```sh
npm exec --no -- agentic-workspace setup
```

Review the proposal and authorise it. Installation alone does not change the
repository. Setup adds the `.agentic-workspace/` directory and a small `AGENTS.md` pointer
to its startup skill. Existing instructions outside that section and unrelated
project data remain preserved. A conflict stops setup.
Review and commit the shared integration files; leave ignored local state alone.

**AW is not a sandbox:** configured commands run with your access and credentials.
Review the repository before allowing execution. See [security](security/threat-model.md).

## 3. Give your agent a task

> Correct one documentation error. Follow the repository instructions and explain
> what you changed and checked. Identify the AW startup guidance you consulted.

The agent should identify `.agentic-workspace/skills/workspace-startup/SKILL.md`
and report the change and its checks. If it missed the startup guidance, use
[The agent does not use AW](troubleshooting.md#the-agent-does-not-use-aw). A small
correction need not create a plan, lesson or verification record.

A fresh session follows the installed `AGENTS.md` pointer without needing the
setup conversation. Planning, Memory and Verification are available when needed
without selecting modules during installation. Availability does not establish
their useful configuration; see the [default policy](package/modules.md#default-availability).
Continue with [Everyday use](everyday-use.md). For updates,
removal or saved data, see [Your repository and data](package/installed-surfaces.md);
for an unsuccessful setup, see [Troubleshooting](troubleshooting.md).

## Optional installed entry skill

The `AGENTS.md` entry is enough to start work. For host-specific discovery and
selection, see [Optional entry plugin and skill](entry-plugin.md), including
repository, global and npm-based installation options.
