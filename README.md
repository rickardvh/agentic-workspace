# agentic-memory-bootstrap

Small CLI for adding durable repository memory to an existing repo.

Requires Python 3.11 or newer.

## What It Does

`agentic-memory-bootstrap` adds a small checked-in memory system for agent-assisted work:

- `AGENTS.md` for the repo-local agent contract
- `memory/` for durable notes
- `memory/current/` for lightweight overview and optional current-work context
- `memory/skills/` for checked-in core memory skills

Install and upgrade flows also create a temporary `memory/bootstrap/` workspace so the agent can finish lifecycle work from local skills and then remove that workspace.

## Install

### Agent workflow

Print a ready-to-paste prompt:

```bash
uvx --from git+https://github.com/Tenfifty/agentic-memory agentic-memory-bootstrap prompt install --target /path/to/repo
uvx --from git+https://github.com/Tenfifty/agentic-memory agentic-memory-bootstrap prompt adopt --target /path/to/repo
pipx run --spec git+https://github.com/Tenfifty/agentic-memory agentic-memory-bootstrap prompt install --target /path/to/repo
pipx run --spec git+https://github.com/Tenfifty/agentic-memory agentic-memory-bootstrap prompt adopt --target /path/to/repo
```

Use `prompt install` for clean bootstrap cases and `prompt adopt` for conservative existing-repo adoption. The prompt runs the CLI, then hands off to the local skills under `/path/to/repo/memory/bootstrap/skills`, and finishes with `bootstrap-cleanup`.

### Manual alternative

Install the tool:

```bash
uv tool install --from git+https://github.com/Tenfifty/agentic-memory agentic-memory-bootstrap
pipx install git+https://github.com/Tenfifty/agentic-memory
python -m pip install git+https://github.com/Tenfifty/agentic-memory
```

Then run:

```bash
agentic-memory-bootstrap doctor --target /path/to/repo
agentic-memory-bootstrap adopt --target /path/to/repo
```

If you are working from a local clone, replace the Git URL with `.`.

## Upgrade

### Agent workflow

Print a ready-to-paste prompt:

```bash
uvx --from git+https://github.com/Tenfifty/agentic-memory agentic-memory-bootstrap prompt upgrade --target /path/to/repo
pipx run --spec git+https://github.com/Tenfifty/agentic-memory agentic-memory-bootstrap prompt upgrade --target /path/to/repo
```

That prompt runs the CLI, then hands off to the local skills under `/path/to/repo/memory/bootstrap/skills`, and finishes with `bootstrap-cleanup`.

### Manual alternative

After installation, run:

```bash
agentic-memory-bootstrap doctor --target /path/to/repo
agentic-memory-bootstrap upgrade --dry-run --target /path/to/repo
agentic-memory-bootstrap upgrade --target /path/to/repo
```

## Uninstall

### Agent workflow

Print a ready-to-paste prompt:

```bash
uvx --from git+https://github.com/Tenfifty/agentic-memory agentic-memory-bootstrap prompt uninstall --target /path/to/repo
pipx run --spec git+https://github.com/Tenfifty/agentic-memory agentic-memory-bootstrap prompt uninstall --target /path/to/repo
```

That prompt runs the CLI uninstall conservatively and points to the bundled `bootstrap-uninstall` skill when manual-review items remain.

### Manual alternative

If the tool is already installed, run:

```bash
agentic-memory-bootstrap uninstall --dry-run --target /path/to/repo
agentic-memory-bootstrap uninstall --target /path/to/repo
```

`uninstall` removes safe bootstrap-managed files and reports remaining repo-local memory files for manual review instead of deleting them blindly.

## Skills

Checked-in core memory skills:

- `memory-hygiene`
- `memory-capture`
- `memory-refresh`
- `memory-router`

Temporary bootstrap lifecycle skills:

- `install`
- `populate`
- `upgrade`
- `cleanup`

Add repo-specific day-to-day memory skills as siblings under `memory/skills/`.

## Command Summary

Main commands:

- `install` or `init` for clean bootstrap application
- `adopt` for conservative adoption into an existing repo
- `doctor` to inspect state and recommended remediation
- `upgrade` for deterministic upgrades
- `uninstall` for conservative bootstrap removal
- `prompt install|adopt|populate|upgrade` to print canonical agent prompts
- `prompt uninstall` to print the canonical uninstall prompt
- `bootstrap-cleanup` to remove the temporary bootstrap workspace
- `current show|check` to inspect current-memory notes
- `route` and `sync-memory` to review likely relevant memory notes
- `verify-payload` to validate the packaged bootstrap contract

Common arguments:

- `--target <path>` selects the repo
- `--format text|json` selects output format
- `--project-name`, `--project-purpose`, `--key-repo-docs`, `--key-subsystems`, `--primary-build-command`, `--primary-test-command`, `--other-key-commands` fill starter placeholders explicitly

`install` and `adopt` are conservative by default: missing files are copied, existing `AGENTS.md` and `memory/` files are left alone, and optional fragments are appended only when appropriate.

## Developing This Repository

Useful maintainer commands:

```bash
uv sync --group dev
uv run --group dev pytest
uv run python scripts/check/check_memory_freshness.py
```

When installer behaviour or the payload changes, verify against this repo itself. When the packaged tool changes, bump the package version in `pyproject.toml`.
