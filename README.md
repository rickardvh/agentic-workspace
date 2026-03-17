# agentic-memory-bootstrap

Small CLI for installing the repository memory bootstrap into an existing repo.

This repository is both the installer implementation and the reference copy of the bootstrap payload it distributes.

## Local usage

Run the command from this workspace with `uv`.

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
uv run agentic-memory-bootstrap install

# Install into a specific repository
uv run agentic-memory-bootstrap install --target /path/to/repo

# Preview or force an install
uv run agentic-memory-bootstrap install --dry-run
uv run agentic-memory-bootstrap install --force

# Clean bootstrap alias
uv run agentic-memory-bootstrap init --target /path/to/repo

# Adopt or inspect an existing repository
uv run agentic-memory-bootstrap adopt --target /path/to/repo
uv run agentic-memory-bootstrap doctor --target /path/to/repo

# Preview or apply an upgrade
uv run agentic-memory-bootstrap upgrade --dry-run --target /path/to/repo
uv run agentic-memory-bootstrap upgrade --target /path/to/repo --apply-local-entrypoint

# Inspect the packaged payload
uv run agentic-memory-bootstrap status
uv run agentic-memory-bootstrap list-files
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
