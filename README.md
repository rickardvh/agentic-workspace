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
```

Use `prompt install` for clean bootstrap cases and `prompt adopt` for conservative existing-repo adoption. Prompt output prefers `uvx` when it is available and otherwise falls back to `pipx run`. It runs the CLI, then hands off to the local skills under `/path/to/repo/memory/bootstrap/skills`, and finishes with `bootstrap-cleanup`.

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
```

That prompt prefers `uvx` when it is available and otherwise falls back to `pipx run`. It runs the CLI, then hands off to the local skills under `/path/to/repo/memory/bootstrap/skills`, and finishes with `bootstrap-cleanup`.

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
```

That prompt prefers `uvx` when it is available and otherwise falls back to `pipx run`. It runs the CLI uninstall conservatively and points to the bundled `bootstrap-uninstall` skill when manual-review items remain.

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
Do not put general non-memory skills there.

## Memory Guidance

Use checked-in memory when it saves repeated rediscovery cost:

- good fits: boundaries, invariants, operator procedures, recurring failures, routing hints
- poor fits: one-off task chatter or code that is easier to inspect directly

Keep the default working set small. Memory is a token saver only when the notes you load are cheaper than rediscovering the same facts from code and docs.

Use note types deliberately:

- `domains/` for subsystem orientation
- `decisions/` for lasting rationale and trade-offs
- `runbooks/` for repeatable procedures and verification sequences
- `current/project-state.md` for a short overview, not a changelog
- `current/task-context.md` for short active-work compression, not a backlog

Small routing layers work better than summary-heavy indexes. A good routing slice is often only 2-3 note links for the current task surface.

Example routing slices:

- API contract change: `memory/domains/api.md` plus `memory/invariants/response-contracts.md`
- deployment recovery: `memory/runbooks/deploy-recovery.md` plus `memory/domains/runtime.md`
- architecture trade-off review: `memory/decisions/README.md` plus the relevant domain note

Compact `project-state.md` shape:

- current focus
- recent meaningful progress
- blockers
- a few high-level notes

If it starts reading like a dated changelog, compress it.

## Optional Repo Patterns

These are recommended patterns, not part of the mandatory bootstrap contract.

Short-horizon task tracking versus long-horizon planning:

- keep the active task board in the repo's chosen task system or TODO surface
- keep roadmap or epic planning separate so `task-context.md` does not become a backlog
- promote a roadmap item into active execution only when it has a clear next owner and next action

Operational verification:

- keep the operational procedure in a runbook
- add a short verification checklist or expected-state section near the procedure when deploy-state confirmation matters
- keep environment-specific deploy status outside the generic bootstrap payload unless the repo intentionally owns that note

## Future Direction

If skill manifests are added in future, they should only be introduced for concrete tool consumers such as routing, verification, or freshness checks. A new machine-readable surface without an immediate consumer would add contract weight without enough payoff.

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
