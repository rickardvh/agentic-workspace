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

## Optional installed entry skill

`agentic-workspace-entry` follows the startup skill in the repository being worked
on. It can serve repositories with different AW versions, including subdirectory
and linked-worktree tasks. Runtime installation through npm, pip, uv or Cargo and
repository setup remain separate. Keep the `AGENTS.md` pointer: passive discovery
does not guarantee automatic activation. Select the entry skill when needed.

The shared plugin exposes one skill and has no hooks, MCP server or runtime.
Use the native host lifecycle with the Git marketplace:

```sh
codex plugin marketplace add rickardvh/agentic-workspace
codex plugin add agentic-workspace-entry@agentic-workspace
```

```sh
claude plugin marketplace add rickardvh/agentic-workspace
claude plugin install agentic-workspace-entry@agentic-workspace --scope user
```

Alternatively, extract `agentic-workspace-entry-<version>.zip` from the ordinary
release and pass the extracted directory to `plugin marketplace add`. Both
catalogues refer to the same self-contained bundle. Select
`$agentic-workspace-entry` in Codex or
`/agentic-workspace-entry:agentic-workspace-entry` in Claude Code.

For Codex Git updates, run `codex plugin marketplace upgrade agentic-workspace`,
then `codex plugin add agentic-workspace-entry@agentic-workspace`. Disable it in
the host's plugin settings or remove it with
`codex plugin remove agentic-workspace-entry@agentic-workspace`. For Claude Git
updates, run `claude plugin marketplace update agentic-workspace`, then
`claude plugin update agentic-workspace-entry@agentic-workspace --scope user`.
The Git projection omits Claude's explicit version so its cache identity follows
the source commit; release ZIPs use the coordinated explicit release version.
Claude Code also provides `plugin disable`, `plugin enable` and `plugin uninstall`
with that selector and `--scope user`. Restart the host after lifecycle changes.
For an extracted release, replace the marketplace directory with the chosen
release before updating. These operations affect host storage, not repository
integration or retained state. The generic repository pointer remains usable
after removal.

The npm package also ships `skills/agentic-workspace-entry/SKILL.md`. npm and pnpm
install package bytes; [skills-npm](https://github.com/antfu/skills-npm) is a
separate, opt-in skill installer. In an explicit consumer package, install AW
normally, then declare the external source:

```json
{
  "skills": ["npm:@agentic-workspace/workspace-cli"]
}
```

Run `npx skills-npm@4.0.0 --agents codex --yes --no-remote` or
`pnpm dlx skills-npm@4.0.0 --agents codex --yes --no-remote` from that consumer.
The installer requires Node 22.20 or later. Its default package source resolves
the declaration from the consumer, including pnpm's layout; `--source
node_modules` also discovers bundled skills directly. No AW install hook runs
this step. Keep an integration-only consumer package under `.agentic-workspace/`
if it is not already part of the repository's package setup. Installer-created
host exposure is an explicit external boundary.

Update the dependency and rerun the installer. To remove this exposure, remove
the dependency and declaration, run the package manager, then rerun skills-npm
with cleanup enabled. Clearing the declaration alone can retain cached bundled
skills while the package is installed. Cleanup preserves unrelated skills.

See the [current local evidence and support boundary](maintainer/skill-entry-evidence.md)
before advertising these optional paths as tested host entry. Plugin recognition
and artifact correctness alone do not establish selected handoff or automatic
activation.
