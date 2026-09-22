# Getting started

Install AW, add it to a Git repository, then give your coding agent ordinary work.
Use an agent that can read repository instructions and run commands.

**Release boundary:** `setup` is in the development version and awaits stable
publication. The [current stable reference](reference/support-bearing-install.md)
identifies the published package; check that its help includes `setup` before
following this journey. Do not substitute internal JSON instructions for a missing
command.

## 1. Install AW

Choose one route. The npm and Python packages include native executables; Cargo
builds them. Your project's language does not restrict the choice.

| Installation scope | Install | Invoke |
| --- | --- | --- |
| npm, user-wide | `npm install --global @agentic-workspace/workspace-cli` | `agentic-workspace` |
| npm, this repository | `npm install --save-dev @agentic-workspace/workspace-cli` | `npm exec --no -- agentic-workspace` |
| Python tool | `uv tool install agentic-workspace` | `agentic-workspace` |
| Cargo | Two exact-version installs below, core first | `agentic-workspace` |

For Cargo, replace `<stable-version>` with the version in the
[stable reference](reference/support-bearing-install.md), then run these commands
in order so both binaries use that exact version:

```sh
cargo install --locked agentic-workspace-core --version '=<stable-version>'
cargo install --locked agentic-workspace-cli --version '=<stable-version>'
```

For a standalone archive or exact reproducible install, use that
reference's platform-specific assets and checksums. [Compatibility and support](evidence-and-support.md)
describes supported environments.

Run your chosen invocation with `--help` in the environment your agent will use.
For a repository-local npm install, use the npm invocation throughout; a global
executable is not required.

## 2. Add AW to the repository

From the Git working-tree root:

```sh
agentic-workspace setup
```

For a repository-local npm installation:

```sh
npm exec --no -- agentic-workspace setup
```

Review the proposal and authorise it. Installation alone does not change the
repository. Setup adds the AW enclave under `.agentic-workspace/` and a small
`AGENTS.md` pointer to its startup skill. Existing instructions outside that
section and independently owned data remain preserved. A conflict stops setup.
Review and commit the shared integration files; leave ignored local state alone.

**AW is not a sandbox:** configured commands run with your access and credentials.
Review the repository before allowing execution. See [security](security/threat-model.md).

## 3. Give your agent a task

> Correct one documentation error. Follow the repository instructions and explain
> what you changed and checked.

A fresh session follows the installed `AGENTS.md` pointer without needing the
setup conversation. Continue with [Everyday use](everyday-use.md). For updates,
removal or saved data, see [Your repository and data](package/installed-surfaces.md);
for an unsuccessful setup, see [Troubleshooting](troubleshooting.md).
