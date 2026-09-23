# Getting started

Install AW, add it to a Git repository, then give your coding agent ordinary work.
Use an agent that can read repository instructions and run commands.

## 1. Install AW

Pin AW per repository when repositories need independent versions; otherwise a
shared installation is fine. Choose npm, Python/uv, Cargo or a standalone archive
according to your tooling. Keep using that installation when running AW.

Replace `<stable-version>` below with the exact version from the
[current stable reference](reference/support-bearing-install.md). That reference
also provides platform-specific assets, checksums and installation details.

| Distribution | Install |
| --- | --- |
| npm | `npm install --save-dev --save-exact @agentic-workspace/workspace-cli@<stable-version>` in the repository; use `--global` instead of `--save-dev --save-exact` for a shared tool |
| Python/uv | `uv pip install 'agentic-workspace==<stable-version>'` in your repository's virtual environment, or `uv tool install 'agentic-workspace==<stable-version>'` for a shared tool |
| Cargo | `cargo install --locked agentic-workspace-core --version '=<stable-version>'`, then `cargo install --locked agentic-workspace-cli --version '=<stable-version>'`; use the same `--root` for both if choosing a repository-specific location |
| Standalone | Extract the exact platform archive from the stable reference into your chosen location, keeping both executables together |

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
