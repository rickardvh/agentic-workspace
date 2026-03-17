# agentic-memory-bootstrap

Small CLI for installing the repository memory bootstrap into an existing repo.

This repository is both the installer implementation and the reference copy of the bootstrap payload it distributes.

Requires Python 3.11 or newer.

## What This Is

`agentic-memory-bootstrap` is a small installer for adding a lightweight agent-workflow layer to an existing repository.

It gives a repo a predictable structure for:

- local repo-specific agent instructions in `AGENTS.md`
- shared workflow rules in `memory/system/WORKFLOW.md`
- milestone and handoff continuity in `TODO.md`
- durable technical notes in `memory/`
- local disposable scratch notes in `.agent-work/`

The goal is not heavy process. The goal is to make agent-assisted work easier to continue safely across sessions, contributors, and repositories without turning the repo into a documentation system of its own.

## What It Does Not Try To Be

This tool is not:

- a replacement for product docs, architecture docs, or contribution guides
- a project-management system
- a knowledge base that stores every implementation detail forever
- a destructive scaffolder that overwrites heavily customised local files by default
- an agent runtime or orchestration framework

## Install

Pick the install method that matches your toolchain.

From a local clone:

```bash
# uv users
uv tool install --from . agentic-memory-bootstrap

# pipx users
pipx install .

# pip users
python -m pip install .
```

From a Git repository URL:

```bash
# uv users
uv tool install --from <repo-url> agentic-memory-bootstrap

# pipx users
pipx install <repo-url>

# pip users
python -m pip install <repo-url>
```

After installation, use the installed command:

```bash
agentic-memory-bootstrap --help
```

## Command reference

These commands use the installed `agentic-memory-bootstrap` executable.

Common commands:

- `install` installs the bootstrap into the target repository.
- `init` is an alias for `install`, intended for clean bootstrap cases.
- `adopt` adds missing bootstrap pieces to an existing repository conservatively.
- `doctor` reports bootstrap state and recommends remediation.
- `upgrade` applies the deterministic upgrade flow for an existing install.
- `status` reports whether bootstrap files are present.
- `list-files` shows the packaged payload and local template files.

Shared arguments:

- `--target <path>` selects the repository to inspect or modify. It defaults to the current directory.
- `--format text|json` chooses human-readable or structured output. JSON is useful for agent-driven workflows.
- `--project-name <name>` fills the `<PROJECT_NAME>` placeholder for commands that write or analyse starter files.

Command-specific arguments:

- `install --dry-run` previews the planned install without writing files.
- `install --force` overwrites managed files that already exist.
- `adopt --dry-run` previews the adoption plan without writing files.
- `adopt --apply-local-entrypoint` patches `AGENTS.md` with the canonical workflow pointer block when needed.
- `upgrade --dry-run` previews the upgrade plan without writing files.
- `upgrade --force` allows replacement of customised starter files during upgrade.
- `upgrade --apply-local-entrypoint` patches `AGENTS.md` with the canonical workflow pointer block when needed.

Examples:

```bash
# Install into the current repository
agentic-memory-bootstrap install

# Install into a specific repository
agentic-memory-bootstrap install --target /path/to/repo

# Preview or force an install
agentic-memory-bootstrap install --dry-run
agentic-memory-bootstrap install --force

# Clean bootstrap alias
agentic-memory-bootstrap init --target /path/to/repo

# Adopt or inspect an existing repository
agentic-memory-bootstrap adopt --target /path/to/repo
agentic-memory-bootstrap doctor --target /path/to/repo

# Preview or apply an upgrade
agentic-memory-bootstrap upgrade --dry-run --target /path/to/repo
agentic-memory-bootstrap upgrade --target /path/to/repo --apply-local-entrypoint

# Inspect the packaged payload
agentic-memory-bootstrap status
agentic-memory-bootstrap list-files
```

## Maintainer usage in this repository

If you are developing this repository itself, running through `uv` is still the shortest path:

```bash
uv run agentic-memory-bootstrap --help
uv run agentic-memory-bootstrap install --dry-run
```

The installed model is:

- `AGENTS.md` = slim local entrypoint
- `memory/system/WORKFLOW.md` = shared reusable workflow rules
- `memory/system/VERSION.md` = installed bootstrap version marker
- `memory/system/UPGRADE.md` = repo-agnostic upgrade playbook
- `memory/index.md` = routing layer for task-relevant durable knowledge
- `TODO.md` = execution and planning surface

## Repository layout

- `bootstrap/` = source-of-truth files that get installed into target repositories
- `src/repo_memory_bootstrap/` = installer and upgrade logic
- `scripts/check/check_memory_freshness.py` = advisory audit for stale or contradictory memory notes
- `memory/` = this repository's own durable operating notes

When changing installer behaviour, check whether the same change also needs an update under `bootstrap/` or `memory/`.

## What `install` does

`install` detects whether the target is in clean bootstrap mode or augment mode, copies the base bootstrap files, applies simple placeholder substitution, and appends a few small text fragments when they are not already present.

Default behaviour is conservative:

- missing files are copied
- existing `AGENTS.md`, `TODO.md`, and files under `memory/` are left untouched
- `.gitignore` gets `.agent-work/` appended only if needed
- `.gitignore` is created if it does not already exist
- optional fragments are appended only when the target file already exists and does not already contain the fragment
- `.agent-work/` is never installed as committed state

## Overwrite and dry-run

- `--dry-run` reports what would change without writing anything
- `--force` allows overwriting managed files that already exist

## Adoption, diagnosis, and upgrades

- `adopt` adds missing bootstrap capability to an existing repo without replacing local files by default
- `doctor` reports missing files, stale versions, and manual-review items such as older `AGENTS.md` layouts
- `upgrade` applies a deterministic minimal-safe upgrade plan

Upgrade defaults:

- add missing core files
- replace shared repo-agnostic files such as `memory/system/WORKFLOW.md`, templates, and the audit script
- never replace `AGENTS.md` automatically
- never replace `TODO.md` automatically
- only replace starter notes automatically when they still look like untouched bootstrap placeholders

Use `--apply-local-entrypoint` to patch `AGENTS.md` with the canonical workflow pointer block.  
Use `--format json` on `doctor`, `upgrade`, `status`, and `list-files` for structured output that an agent can consume.

Mode summary:

- empty repo or repo without agent files: bootstrap everything
- partial agent setup: install missing pieces and skip existing ones
- full agent setup: do nothing unless new append-only fragments are needed, or `--force` is used

If root detection from the current working directory is ambiguous, the installer stops and asks for `--target` instead of guessing. The installer does not create a committed `.agent-work/` working directory. It only ensures `.agent-work/` is ignored and reports that local templates are available from the packaged bootstrap payload.

When `--target` points inside another repository or contains nested repositories, the installer warns and treats the explicit target as authoritative instead of guessing or walking upward.

## Maintenance checks

Run the freshness audit after changing repository memory, bootstrap docs, or installer behaviour that affects documented commands or file roles:

```bash
uv run python scripts/check/check_memory_freshness.py
```
