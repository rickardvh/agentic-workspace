# agentic-memory-bootstrap

A small CLI that adds a checked-in, route-indexed memory layer to any Git repository so AI coding agents retain durable context across sessions without rediscovering the codebase from scratch each time.

## Why

Some AI agents, such as GitHub Copilot, have their own built-in memory, but that memory is typically per-user, per-machine, and invisible to the rest of the team. Checked-in repository memory complements those systems by providing a shared, version-controlled knowledge layer that:

- **Survives agent and tool switches.** Developers move between Copilot, Cursor, Claude Code, custom agents, and others. Checked-in memory travels with the repo, not the tool.
- **Works across machines and developers.** Built-in agent memory is local to one user's profile. Repository memory is shared through Git, so every contributor and every agent session starts from the same durable knowledge base.
- **Captures knowledge that no single session owns.** Invariants, authority boundaries, recurring failure modes, and operator procedures accumulate across many sessions and many contributors. No individual agent memory is the right home for team-wide lessons.
- **Stays auditable and reviewable.** Checked-in notes go through normal code review and version history, making it visible when knowledge changes and why.

`agentic-memory-bootstrap` installs a lightweight `memory/` tree that agents load selectively on each task start, giving them the smallest useful slice of durable context without bulk-reading the codebase.

## How it works

- **Structured taxonomy.** Notes are split into `domains/` for subsystem orientation, `invariants/` for contracts and authority boundaries, `runbooks/` for operator procedures, `mistakes/` for recurring failure modes, `decisions/` for longer-lived rationale, and `current/` for lightweight project overview plus optional task-continuation compression.
- **Route-indexed, not bulk-loaded.** `memory/index.md` maps task types to minimal note bundles, and a machine-readable `manifest.toml` annotates every note with audience, authority, routing triggers (`routes_from`, `stale_when`), and task relevance so agents read only what matters for the current change. Good memory helps an agent read *less*, not more.
- **Clear ownership boundary.** Memory owns durable repo knowledge that is expensive to reconstruct from code alone: invariants, authority boundaries, recurring failure modes, operator sequences, and routing hints. The repository's active planning surface (`TODO.md`, issue trackers, and similar systems) keeps ownership of active intent and sequencing. Memory complements planning; it never competes with it.
- **Improvement pressure without memory dependence.** Each note can declare whether it is *durable truth* or an *improvement signal* - something that exists because the repo still needs better tests, docs, validation, or design. Manifest fields like `preferred_remediation` and `elimination_target` let the `doctor` command, the freshness audit, and the sync workflow surface actionable suggestions that drive improvements into the codebase without assuming memory volume should follow one universal trend.
- **Freshness and hygiene tooling.** A bundled audit script checks for missing metadata, stale confirmations, oversized notes, and manifest/note mismatches. `stale_when` globs catch semantic drift from code changes, not just calendar age.
- **Skills layer.** Repeatable memory operations such as capture, hygiene, refresh, routing, and upgrade ship as upgrade-replaceable skills under `.agentic-workspace/memory/skills/`. Repos can add their own memory-specific skills under `memory/skills/` without modifying the core set.
- **Language-agnostic.** The installed memory system is plain Markdown and TOML. It works in any repository regardless of language or framework. Only the bootstrap CLI itself requires Python; once installed, the memory layer has no runtime dependencies.

### Bootstrap CLI requirements

Python 3.11 or newer, only needed to run the installer, not at runtime in the target repo.

## Ownership Boundary

Put information in memory when it preserves durable knowledge that outlives the current task and is expensive to reconstruct quickly.

Memory owns:

- durable subsystem orientation
- invariants and authority boundaries
- recurring failure modes
- operator runbooks
- compact continuation context
- memory routing metadata and note hygiene rules

Memory does not own:

- active task state
- next actions or milestone sequencing
- backlog state
- execution logs
- broad canonical documentation

## Anti-Blur Rules

- Memory must not become a task tracker or backlog mirror.
- Memory should complement planning surfaces, not replace them.
- Routing hints inside memory should stay subordinate to the repo's canonical startup and planning contract.
- Selective adoption must remain valid: memory should still make sense in repos that do not install planning.

## Table Of Contents

- [agentic-memory-bootstrap](#agentic-memory-bootstrap)
  - [Why](#why)
  - [How it works](#how-it-works)
    - [Bootstrap CLI requirements](#bootstrap-cli-requirements)
  - [Table Of Contents](#table-of-contents)
  - [What It Does](#what-it-does)
  - [Install](#install)
    - [Agent workflow](#agent-workflow)
    - [Manual alternative](#manual-alternative)
  - [Upgrade](#upgrade)
    - [Agent workflow](#agent-workflow-1)
    - [Manual alternative](#manual-alternative-1)
  - [Uninstall](#uninstall)
    - [Agent workflow](#agent-workflow-2)
    - [Manual alternative](#manual-alternative-2)
  - [Skills](#skills)
  - [Memory Guidance](#memory-guidance)
  - [Command Summary](#command-summary)
  - [Developing This Repository](#developing-this-repository)

## What It Does

Running `install` or `adopt` adds the following to your repository:

| Path | Purpose |
|------|---------|
| `AGENTS.md` | Repo-local agent contract and bootstrap entry point |
| `memory/index.md` | Route-indexed entry point that maps tasks to minimal note bundles |
| `memory/manifest.toml` | Machine-readable note metadata, routing triggers, and improvement-pressure fields |
| `memory/domains/` | Subsystem orientation notes |
| `memory/invariants/` | Contracts and authority boundaries |
| `memory/runbooks/` | Repeatable operator procedures |
| `memory/mistakes/` | Recurring failure modes |
| `memory/decisions/` | Longer-lived rationale and trade-offs |
| `memory/current/` | Lightweight project overview and optional task-continuation compression |
| `.agentic-workspace/memory/skills/` | Bootstrap-managed shared memory skills, upgrade-replaceable |
| `memory/skills/` | Optional repo-owned memory skills |
| `scripts/check/` | Advisory freshness audit script |

Install and adopt flows may create a temporary `.agentic-workspace/memory/bootstrap/` workspace so the agent can finish lifecycle work from local skills and then remove that workspace. Upgrade should normally route through the checked-in `memory-upgrade` skill and no longer depends on that workspace as part of the primary model.

In this monorepo checkout, the active operational memory install lives at the repository root. This package directory keeps the reusable package source, bootstrap payload, tests, and fixtures; the paths listed above describe the target-repository structure that `install` or `adopt` writes.

## Install

### Agent workflow

If you want an agent to perform the setup and do not want to install the CLI locally, print a ready-to-paste prompt with one of these commands:

```bash
# Preferred when uvx is available
uvx --from git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/memory agentic-memory-bootstrap prompt install --target /path/to/repo

# Fallback when pipx is available instead
pipx run --spec git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/memory agentic-memory-bootstrap prompt install --target /path/to/repo

# Conservative adoption into an existing repo
uvx --from git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/memory agentic-memory-bootstrap prompt adopt --target /path/to/repo

# Fallback when pipx is available instead
pipx run --spec git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/memory agentic-memory-bootstrap prompt adopt --target /path/to/repo
```

Use `prompt install` for clean bootstrap cases and `prompt adopt` for conservative existing-repo adoption. The printed prompt is designed for an agent to execute the bootstrap flow without asking you to install or clone this repo first. Install and adopt may still use the temporary bootstrap path for lifecycle completion, but normal upgrades should route through the checked-in `memory-upgrade` skill under `.agentic-workspace/memory/skills/`, which runs the packaged upgrade flow using `.agentic-workspace/memory/UPGRADE-SOURCE.toml`. Treat that file as the source of truth for remote runner specs instead of scattering raw Git URLs through local workflow docs.

Typical lifecycle for a fresh bootstrap:

1. Run `prompt install` or `install`.
2. If new current-memory files were created, populate them conservatively.
3. Run `bootstrap-cleanup` when bootstrap lifecycle work is complete.

After the agent finishes install or adopt lifecycle work, run `agentic-memory-bootstrap bootstrap-cleanup --target /path/to/repo`, or let the agent run it, to remove the temporary `.agentic-workspace/memory/bootstrap/` workspace.

If you omit the placeholder flags such as `--project-name` or `--project-purpose`, your `AGENTS.md` will contain unfilled placeholders. Run `doctor` after install to identify them.

### Manual alternative

If you want a local CLI installation instead, install the tool with one of these commands:

```bash
# Choose one
uv tool install --from git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/memory agentic-memory-bootstrap

# Or
pipx install git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/memory

# Or
python -m pip install git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/memory
```

Then run:

```bash
# First-time install
agentic-memory-bootstrap doctor --target /path/to/repo
agentic-memory-bootstrap install --target /path/to/repo

# Conservative adoption into an existing repo
agentic-memory-bootstrap doctor --target /path/to/repo
agentic-memory-bootstrap adopt --target /path/to/repo
```

If you are working from a local clone, replace the Git URL with `.`.

## Upgrade

### Agent workflow

If you want an agent to perform the upgrade without a local CLI install, print a ready-to-paste prompt with one of these commands:

```bash
# Preferred when uvx is available
uvx --from git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/memory agentic-memory-bootstrap prompt upgrade --target /path/to/repo

# Fallback when pipx is available instead
pipx run --spec git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/memory agentic-memory-bootstrap prompt upgrade --target /path/to/repo
```

This is the preferred upgrade path for the primary agent-first workflow. The prompt tells the agent to use the checked-in `memory-upgrade` skill as the single repo-local upgrade entrypoint; the skill then runs the packaged upgrade flow using `.agentic-workspace/memory/UPGRADE-SOURCE.toml`.

### Manual alternative

After installation, run:

```bash
agentic-memory-bootstrap doctor --target /path/to/repo
agentic-memory-bootstrap upgrade --dry-run --target /path/to/repo
agentic-memory-bootstrap upgrade --target /path/to/repo
```

## Uninstall

### Agent workflow

If you want an agent to perform the uninstall without a local CLI install, print a ready-to-paste prompt with one of these commands:

```bash
# Preferred when uvx is available
uvx --from git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/memory agentic-memory-bootstrap prompt uninstall --target /path/to/repo

# Fallback when pipx is available instead
pipx run --spec git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/memory agentic-memory-bootstrap prompt uninstall --target /path/to/repo
```

This runs the uninstall flow conservatively and points the agent to the bundled `bootstrap-uninstall` skill when manual-review items remain.

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
- `memory-upgrade`
- `memory-refresh`
- `memory-router`

Temporary bootstrap lifecycle skills:

- `install`
- `populate`
- `cleanup`

Add repo-specific day-to-day memory skills as siblings under `memory/skills/`.
Do not put general non-memory skills there.

## Memory Guidance

The installed `WORKFLOW.md` under `.agentic-workspace/memory/` is the full reference for memory conventions, note types, improvement pressure, anti-patterns, and interoperability with planning surfaces. Key principles:

- **Write to memory** when the fact is expensive to rediscover from code alone: invariants, authority boundaries, recurring failure modes, operator procedures, routing hints.
- **Don't write to memory** for milestone status, backlog state, execution logs, or anything the repo's planning surface already owns.
- **Optimise for justified memory.** Ask what repo change - better docs, a test, a script, a refactor - would let a note shrink, move, or become a short stub when that is genuinely better than keeping the note.
- **Keep the working set small.** Memory saves tokens only when the notes you load are cheaper than rediscovering the same facts from code.
- **Promote when stable.** If a note matures into general guidance, move it into canonical docs and leave memory as a stub.
- **Do not make memory the default answer to repo complexity.** Durable truth may stay or grow when justified, but improvement-signal notes should push agents toward clearer docs, safer tests, stronger tooling, or simpler structure when those fixes are feasible.

## Command Summary

Main commands:

- `install` or `init` for clean bootstrap application
- `adopt` for conservative adoption into an existing repo
- `doctor` to inspect state and recommended remediation
- `upgrade` for deterministic upgrades
- `uninstall` for conservative bootstrap removal
- `prompt <subcommand>` to print ready-to-paste no-install agent prompts, with subcommands `install`, `adopt`, `populate`, `upgrade`, and `uninstall`
- `bootstrap-cleanup` to remove the temporary bootstrap workspace when install or adopt created it
- `current show|check` to inspect current-memory notes
- `route` and `sync-memory` to review likely relevant memory notes
- `route-review` to replay checked-in routing-feedback cases against current routing behaviour
- `route-report` to summarise fixture-backed routing health, missed-note vs over-routing drift, and working-set/startup-cost pressure
- `promotion-report` to suggest notes that should graduate into canonical checked-in docs or become elimination candidates for skills, scripts, tests, or refactors
- `verify-payload` to validate the packaged bootstrap contract
- `scripts/check/check_memory_freshness.py --strict` to fail CI on selected freshness contract violations

Common arguments:

- `--target <path>` selects the repo
- `--format text|json` selects output format
- `--policy-profile default|strict-doc-ownership` applies installer policy presets for install, adopt, and upgrade
- `--project-name`, `--project-purpose`, `--key-repo-docs`, `--key-subsystems`, `--primary-build-command`, `--primary-test-command`, and `--other-key-commands` fill starter placeholders explicitly

`install` and `adopt` are conservative by default: missing files are copied, existing `AGENTS.md` and `memory/` files are left alone, and optional fragments are appended only when the fragment is not already present.

`doctor --strict-doc-ownership` forces the doc-ownership and shadow-doc audits even if the repository manifest has not opted in yet.

## Developing This Repository

Useful maintainer commands:

```bash
uv sync --group dev
uv run --group dev pytest
make check-memory

# Or from the monorepo root
make check-memory
```

When installer behaviour or the payload changes, verify against this repo itself. When the packaged tool changes, bump the package version in `pyproject.toml`.
