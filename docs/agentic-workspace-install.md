# Getting started

Install AW, add it to a Git repository, then give your coding agent ordinary work.
Use an agent that can read repository instructions and run commands.

## 1. Install AW

Choose the installation scope first:

- **Repository-scoped and pinned:** keep this repository's AW version independent
  of other repositories. Record the chosen version and installation command with
  the project; keep local environments and extracted binaries out of Git.
- **Intentionally shared:** reuse one tool installation across repositories.
  Updating it changes the runtime used by every repository that invokes it.

Then choose a distribution route. npm, Python/uv, Cargo and standalone archives
provide the same AW product; your project's language does not restrict the choice.
The npm and Python packages include native executables, while Cargo builds them.

Replace `<stable-version>` below with the exact version from the
[current stable reference](reference/support-bearing-install.md). That reference
owns release identities, supported platforms, assets, checksums and receipts.

| Route | Repository-scoped and pinned | Intentionally shared | Invocation |
| --- | --- | --- | --- |
| npm | `npm install --save-dev --save-exact @agentic-workspace/workspace-cli@<stable-version>` | `npm install --global @agentic-workspace/workspace-cli@<stable-version>` | Local: `npm exec --no -- agentic-workspace`; shared: `agentic-workspace` |
| Python/uv | Create `.aw-venv` and install the exact version as below | `uv tool install 'agentic-workspace==<stable-version>'` | Local: `.aw-venv/bin/agentic-workspace`; shared: `agentic-workspace` |
| Cargo | Use both installs below with `--root .aw-tools` | Use both installs below with the default Cargo root | Local: `.aw-tools/bin/agentic-workspace`; shared: `agentic-workspace` on Cargo's PATH |
| Standalone archive | Extract the exact platform archive into a repository-local directory | Extract it into a deliberately shared tools directory | Use that directory's `agentic-workspace` executable, keeping its paired core beside it |

For a repository-local Python environment:

```sh
uv venv .aw-venv
uv pip install --python .aw-venv/bin/python 'agentic-workspace==<stable-version>'
```

On Windows, use `.aw-venv\Scripts\python.exe` for installation and
`.aw-venv\Scripts\agentic-workspace.exe` for invocation. Cargo and standalone
executables also use the `.exe` suffix on Windows.

For Cargo, install core first, then CLI at the same exact version. Add
`--root .aw-tools` to **both** commands for repository scope:

```sh
cargo install --locked agentic-workspace-core --version '=<stable-version>'
cargo install --locked agentic-workspace-cli --version '=<stable-version>'
```

For a standalone archive or an install pinned to artifact bytes, use the
reference's platform-specific assets and checksums. [Compatibility and support](evidence-and-support.md)
describes supported environments.

Run your chosen invocation with `--help` in the environment your agent will use.
For a repository-local npm install, use the npm invocation throughout; a global
executable is not required.

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
