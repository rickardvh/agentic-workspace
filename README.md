# agentic-memory-bootstrap

Small CLI for installing the repository memory bootstrap into an existing repo.

## Local usage

Run it from this workspace with `uv`:

```bash
uv run agentic-memory-bootstrap install
uv run agentic-memory-bootstrap install --target /path/to/repo
uv run agentic-memory-bootstrap install --dry-run
uv run agentic-memory-bootstrap install --force
uv run agentic-memory-bootstrap init --target /path/to/repo
uv run agentic-memory-bootstrap status
uv run agentic-memory-bootstrap list-files
```

The installed model is:

- `AGENTS.md` = slim local entrypoint
- `memory/system/WORKFLOW.md` = shared reusable workflow rules
- `memory/index.md` = routing layer for task-relevant durable knowledge
- `TODO.md` = execution and planning surface

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

Mode summary:

- empty repo or repo without agent files: bootstrap everything
- partial agent setup: install missing pieces and skip existing ones
- full agent setup: do nothing unless new append-only fragments are needed, or `--force` is used

If root detection from the current working directory is ambiguous, the installer stops and asks for `--target` instead of guessing. The installer does not create a committed `.agent-work/` working directory. It only ensures `.agent-work/` is ignored and reports that local templates are available from the packaged bootstrap payload.

When `--target` points inside another repository or contains nested repositories, the installer warns and treats the explicit target as authoritative instead of guessing or walking upward.
