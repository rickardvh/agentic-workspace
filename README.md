# agentic-memory-bootstrap

Small CLI for adding durable repository memory to an existing repo.

Requires Python 3.11 or newer.

## What It Is

`agentic-memory-bootstrap` installs a small checked-in memory system for agent-assisted work.

It gives a repo:

- local repo-specific agent instructions in `AGENTS.md`
- shared workflow rules in `memory/system/WORKFLOW.md`
- durable technical notes in `memory/`
- a lightweight human-readable overview in `memory/current/project-state.md`
- an optional checked-in current-task compression note in `memory/current/task-context.md`

The goal is to make work easier to continue across sessions and contributors without turning the repo into a heavy process system.

## Core Model

Use the layers like this:

- checked-in files = durable shared knowledge and lightweight shared context
- skills = repeatable operations on that knowledge
- built-in agent planning = short-horizon execution
- external task system = task tracking

This tool is memory-only and task-system agnostic.

If something is a durable fact about the repo, store it in files.  
If something is a repeatable workflow over those files, make it a skill.

## What It Is Not

This tool does not try to be:

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

From the Git repository URL:

```bash
# uv users
uv tool install --from git+https://github.com/Tenfifty/agentic-memory agentic-memory-bootstrap

# pipx users
pipx install git+https://github.com/Tenfifty/agentic-memory

# pip users
python -m pip install git+https://github.com/Tenfifty/agentic-memory
```

## First Use

After installation:

```bash
agentic-memory-bootstrap --help
```

Typical first commands:

```bash
# install into a repo
agentic-memory-bootstrap install --target /path/to/repo

# inspect an existing install
agentic-memory-bootstrap doctor --target /path/to/repo

# inspect current-memory notes
agentic-memory-bootstrap current show --target /path/to/repo
```

## Using With An Agent

In a fresh repo, the simplest path is usually to tell the agent to use the bundled bootstrap skill directly.

For first-time adoption, paste:

```text
Run `agentic-memory-bootstrap list-skills` if you do not already see the bundled skills in this session. Then use the `bootstrap-adoption` skill from the installed `agentic-memory-bootstrap` product to adopt this repository conservatively and report any manual-review items. After adoption, offer to use `bootstrap-populate` if new current-memory files were created.
```

For upgrading an existing install, paste:

```text
Run `agentic-memory-bootstrap list-skills` if you do not already see the bundled skills in this session. Then use the `bootstrap-upgrade` skill from the installed `agentic-memory-bootstrap` product to upgrade this repository conservatively and report any manual-review items.
```

Or have the tool print the prompt for you:

```bash
agentic-memory-bootstrap prompt adopt
agentic-memory-bootstrap prompt populate
agentic-memory-bootstrap prompt upgrade
```

## Bundled Skills

The shipped skills are:

- `memory-hygiene`
- `memory-capture`
- `memory-refresh`
- `memory-router`
- `bootstrap-adoption`
- `bootstrap-populate`
- `bootstrap-upgrade`

If your runtime supports packaged skill discovery, these skills should be available from the installed product.

To inspect the bundled catalogue:

```bash
agentic-memory-bootstrap list-skills
```

See [skills/README.md](C:/Users/ricka/src/agentic-memory/skills/README.md) for the skill catalogue and fallback installation methods.

## Command reference

Main commands:

- `install` installs the bootstrap into the target repository.
- `init` is an alias for `install`, intended for clean bootstrap cases.
- `adopt` adds missing bootstrap pieces to an existing repository conservatively.
- `doctor` reports bootstrap state and recommends remediation.
- `upgrade` applies the deterministic upgrade flow for an existing install.
- `status` reports whether bootstrap files are present.
- `list-files` shows the packaged payload files.
- `list-skills` shows the bundled product skills.
- `prompt adopt|populate|upgrade` prints canonical agent prompts for the bundled bootstrap skills.
- `current show|check` inspects or validates the current-memory surface.
- `route` suggests likely relevant memory notes for touched files or explicit surfaces.
- `sync-memory` suggests which memory notes to review after code changes.
- `verify-payload` validates the packaged bootstrap contract.

Common arguments:

- `--target <path>` selects the repository to inspect or modify. It defaults to the current directory.
- `--format text|json` chooses human-readable or structured output. JSON is useful for agent-driven workflows.
- `--project-name <name>` fills the `<PROJECT_NAME>` placeholder for commands that write or analyse starter files.
- `--project-purpose <text>` fills `<PROJECT_PURPOSE>` when explicitly provided.
- `--key-repo-docs <text>` fills `<KEY_REPO_DOCS>` when explicitly provided.
- `--key-subsystems <text>` fills `<KEY_SUBSYSTEMS>` when explicitly provided.
- `--primary-build-command <text>` fills `<PRIMARY_BUILD_COMMAND>` when explicitly provided.
- `--primary-test-command <text>` fills `<PRIMARY_TEST_COMMAND>` when explicitly provided.
- `--other-key-commands <text>` fills `<OTHER_KEY_COMMANDS>` when explicitly provided.

Examples:

```bash
# preview an install
agentic-memory-bootstrap install --dry-run --target /path/to/repo

# apply an upgrade
agentic-memory-bootstrap upgrade --target /path/to/repo

# route likely relevant memory for changed files
agentic-memory-bootstrap route --files src/app.py tests/test_app.py --target /path/to/repo
```

## How `install` behaves

`install` detects whether the target is in clean bootstrap mode or augment mode, copies the base bootstrap files, fills `<PROJECT_NAME>`, applies any explicitly supplied placeholder flags, and leaves other repo-specific placeholders for manual review.

Default behaviour is conservative:

- missing files are copied
- existing `AGENTS.md` and files under `memory/` are left untouched
- optional fragments are appended only when the target file already exists and does not already contain the fragment

If adoption creates new current-memory notes, the intended follow-up is to use `bootstrap-populate` so those notes are filled conservatively from existing repo evidence instead of remaining as generic starters.

If root detection from the current working directory is ambiguous, the installer stops and asks for `--target` instead of guessing.

When `--target` points inside another repository or contains nested repositories, the installer warns and treats the explicit target as authoritative instead of guessing or walking upward.

## Developing This Repository

This repository is both the installer implementation and the reference copy of the bootstrap payload it distributes.

Useful maintainer commands:

```bash
uv sync --group dev
uv run --group dev pytest
uv run python scripts/check/check_memory_freshness.py
```

When changing the installed payload contract or installer behaviour, verify it by running the bootstrap tool against this repo itself, not only by editing source files in place.
