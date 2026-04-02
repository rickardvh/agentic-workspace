# agentic-memory-bootstrap

Small CLI for adding durable repository memory to an existing repo.

Requires Python 3.11 or newer.

## Quick Start

Use `install` (or `prompt install`) when adding the bootstrap to a repo for the first time. Use `adopt` (or `prompt adopt`) when the repo already has local files such as `AGENTS.md` or `memory/` that should be preserved conservatively.

Agent workflow:

```bash
# First-time install
uvx --from git+https://github.com/Tenfifty/agentic-memory agentic-memory-bootstrap prompt install --target /path/to/repo

# Conservative adoption into an existing repo
uvx --from git+https://github.com/Tenfifty/agentic-memory agentic-memory-bootstrap prompt adopt --target /path/to/repo
```

Manual workflow:

```bash
uv tool install --from git+https://github.com/Tenfifty/agentic-memory agentic-memory-bootstrap
agentic-memory-bootstrap doctor --target /path/to/repo
agentic-memory-bootstrap adopt --target /path/to/repo
```

## Table Of Contents

- [agentic-memory-bootstrap](#agentic-memory-bootstrap)
  - [Quick Start](#quick-start)
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
  - [Optional Repo Patterns](#optional-repo-patterns)
  - [Current Decisions](#current-decisions)
  - [Improvement Questions](#improvement-questions)
  - [Anti-patterns](#anti-patterns)
  - [Minimal Adoption Checklist](#minimal-adoption-checklist)
  - [Future Direction](#future-direction)
  - [Command Summary](#command-summary)
  - [Developing This Repository](#developing-this-repository)

## What It Does

`agentic-memory-bootstrap` adds a small checked-in memory system for agent-assisted work:

- `AGENTS.md` for the repo-local agent contract
- `memory/` for durable notes
- `memory/current/` for lightweight overview and optional current-work context
- `memory/skills/` for checked-in core memory skills

Install and adopt flows may create a temporary `memory/bootstrap/` workspace so the agent can finish lifecycle work from local skills and then remove that workspace. Upgrade should normally route through the checked-in `memory-upgrade` skill and no longer depends on that workspace as part of the primary model.

Memory owns durable repo knowledge. The repository's active planning/status surface owns active intent and sequencing. Memory complements planning by preserving durable lessons and reducing re-orientation cost, but it must never compete with the planning surface for ownership of active work.
Good memory systems should help an agent read less, not more.
Memory is also a pressure layer: if a note exists because the repo is awkward to understand or operate, the note should help the agent suggest the code, docs, tests, tooling, or refactor that would let the note shrink, move, or disappear.

## Install

### Agent workflow

Print a ready-to-paste prompt:

```bash
uvx --from git+https://github.com/Tenfifty/agentic-memory agentic-memory-bootstrap prompt install --target /path/to/repo
uvx --from git+https://github.com/Tenfifty/agentic-memory agentic-memory-bootstrap prompt adopt --target /path/to/repo
```

Use `prompt install` for clean bootstrap cases and `prompt adopt` for conservative existing-repo adoption. Prompt output prefers `uvx` when it is available and otherwise falls back to `pipx run`. Install and adopt may still use the temporary bootstrap path for lifecycle completion, but normal upgrades should route through the checked-in `memory-upgrade` skill under `memory/skills/`, which runs the packaged upgrade flow using `memory/system/UPGRADE-SOURCE.toml`.

After the agent finishes install or adopt lifecycle work, run `agentic-memory-bootstrap bootstrap-cleanup --target /path/to/repo` (or let the agent run it) to remove the temporary `memory/bootstrap/` workspace.

If you omit the placeholder flags (`--project-name`, `--project-purpose`, etc.), your `AGENTS.md` will contain unfilled placeholders. Run `doctor` after install to identify them.

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

That prompt prefers `uvx` when it is available and otherwise falls back to `pipx run`. It tells the agent to use the checked-in `memory-upgrade` skill as the single repo-local upgrade entrypoint; the skill then runs the packaged upgrade flow using `memory/system/UPGRADE-SOURCE.toml`.

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

Use checked-in memory when it saves repeated rediscovery cost:

- good fits: boundaries, invariants, operator procedures, recurring failures, routing hints
- poor fits: one-off task chatter or code that is easier to inspect directly

Treat canonical repo docs and memory as separate lanes:

- keep stable human-facing engineering guidance in `README.md`, `docs/`, or equivalent checked-in docs
- use memory as assistive residue by default
- if a note stabilises into canonical guidance, promote it into docs and leave memory as a stub, backlink, or short fallback note

Keep the default working set small. Memory is a token saver only when the notes you load are cheaper than rediscovering the same facts from code and docs.
Optimise for deletion and consolidation, not just capture.
Memory is a reasoning aid and constraint layer; it does not replace checking the codebase when the codebase is the source of truth.

Use memory in two modes:

- durable truth: invariants, authority boundaries, recurring traps, operator constraints, and other hard-to-rediscover facts that should stay visible
- improvement signal: notes that exist because the repo still needs clearer docs, stronger tests, better tooling, better automation, or simpler structure

Preserve the first kind. Use the second kind to suggest upstream repo improvements instead of growing memory indefinitely.

When to write to memory:

- invariants and authority boundaries
- recurring failure modes
- routing hints
- operator runbooks
- durable consequences and still-relevant rejected-path boundaries
- facts that are hard to recover quickly from code, tests, tooling, or the repository's active planning/status surface

When not to write to memory:

- milestone status
- next-step checklists
- backlog state
- execution logs
- plan content that already belongs to the repository's active planning/status surface
- user-specific preferences, collaboration habits, or stylistic defaults unless they are shared technical policy

Ask one more question before expanding a note: what repo change would let this note shrink, move, or disappear?

`memory/manifest.toml` can now mark:

- `canonicality` as `agent_only`, `candidate_for_promotion`, `canonical_elsewhere`, or `deprecated`
- `task_relevance` as `required` or `optional`
- `forbid_core_docs_depend_on_memory = true` to make `doctor` flag core docs that depend on memory

Recommended audience conventions for planner-agnostic routing:

- `agent_bootstrap` for bootstrap-only agent guidance
- `human_operator` for operator-facing procedures
- `shared_invariant` for shared technical constraints

These are recommended conventions only in this pass. Existing manifests remain valid.

Compact memory notes work better than quasi-doc pages:

- good residue: pitfalls, routing hints, boundary clarifications, operator gotchas, short fallback context
- promote instead: stable onboarding guidance, normal engineering policy, human-facing procedures, broad architecture docs

Use note types deliberately:

- `domains/` for subsystem orientation
- `decisions/` for lasting rationale and trade-offs
- `runbooks/` for repeatable procedures and verification sequences
- `current/project-state.md` for a short overview, not a changelog
- `current/task-context.md` for optional continuation compression: active goal, touched surfaces, blocking assumptions, and next validation only

Small routing layers work better than summary-heavy indexes. A good routing slice is often only 2-3 note links for the current task surface.
If the same note keeps being routed for safe work on one subsystem, that is often a cue to suggest clearer docs, stronger validation, or refactor review.

Common task bundles:

- current-state refresh: `memory/current/project-state.md` plus `memory/current/task-context.md` when needed
- live decision review: optional repo-owned `memory/current/active-decisions.md` when the repo keeps one, plus `memory/decisions/README.md`
- API contract change: `memory/domains/api.md` plus `memory/invariants/response-contracts.md`
- deployment recovery: `memory/runbooks/deploy-recovery.md` plus `memory/domains/runtime.md`
- architecture trade-off review: `memory/decisions/README.md` plus the relevant domain note

Routing is the primary integration point with planning: the planning/status surface identifies touched paths or surfaces, and `route` or `sync-memory` returns the smallest relevant durable note set.
Those commands should also help the agent notice when a note looks like a candidate for docs promotion, skill extraction, scripting, testing, or refactor review.

Compact `project-state.md` shape:

- current focus
- recent meaningful progress
- blockers
- a few high-value notes

If it starts reading like a ledger, backlog, tranche history, or changelog, compress it.

## Optional Repo Patterns

These are recommended patterns, not part of the mandatory bootstrap contract.

Interoperability pattern catalogue:

- loose coupling: planner first, memory routed on demand
- handoff compression: planner primary, memory holds only minimal cross-session continuation context
- durable capture on close: planner closes work, memory updates only if durable knowledge changed

Short-horizon task tracking versus long-horizon planning:

- keep the active task board in the repo's chosen planning/status surface
- keep roadmap or epic planning separate so `task-context.md` does not become a backlog
- promote a roadmap item into active execution only when it has a clear next owner and next action

Operational verification:

- keep the operational procedure in a runbook
- add a short verification checklist or expected-state section near the procedure when deploy-state confirmation matters
- keep environment-specific deploy status outside the generic bootstrap payload unless the repo intentionally owns that note

Improvement paths:

- recurring mistake -> consider a regression test, validation, or lint rule
- prose-heavy runbook -> consider a checked-in skill first, then a repo-owned script or command if the workflow stays mechanical
- stable human-facing guidance -> consider promoting it into canonical docs and leaving memory as a stub or backlink
- note that repeatedly explains one hard subsystem -> consider refactor review or clearer module boundaries
- routing crutch used for one awkward area -> consider naming, structure, or ownership cleanup in the repo

## Current Decisions

- if the repo keeps `memory/current/active-decisions.md`, use it for live architectural or cross-cutting decisions only
- move a decision into `memory/decisions/` once it no longer changes implementation choices and is only worth keeping as durable rationale
- preserve decisions at the level of consequence or still-relevant rejected-path boundaries, not meeting history
- do not keep completed transitions or operational residue in the current decision note

## Improvement Questions

- Is this note preserving durable truth or compensating for repo friction?
- Why is this not encoded in code, tests, tooling, or canonical docs?
- What repo change would let this note shrink by half?
- Should this become canonical docs, a skill, a script, a test, a validation, or a refactor candidate instead?

## Anti-patterns

- turning memory into a task tracker
- copying plan content into durable notes
- storing rediscoverable facts that are easier to inspect directly
- coupling freshness checks to a specific planner or planning file
- forcing repositories to adopt the memory taxonomy in their planning system
- mixing user-specific memory with repo-specific technical truth
- treating memory as the endpoint when it is really signalling missing docs, missing tests, weak tooling, or awkward architecture

## Minimal Adoption Checklist

- choose the repository's active planning/status surface
- decide whether `memory/current/task-context.md` will be used for optional continuation compression
- decide how memory freshness is checked
- decide who updates memory when durable knowledge changes
- decide which routing metadata fields the repo will maintain

## Future Direction

Skill manifests should only exist for concrete tool consumers such as routing, verification, or freshness checks. A new machine-readable surface without an immediate consumer would add contract weight without enough payoff.

## Command Summary

Main commands:

- `install` or `init` for clean bootstrap application
- `adopt` for conservative adoption into an existing repo
- `doctor` to inspect state and recommended remediation
- `upgrade` for deterministic upgrades
- `uninstall` for conservative bootstrap removal
- `prompt <subcommand>` to print canonical agent prompts (subcommands: `install`, `adopt`, `populate`, `upgrade`)
- `prompt uninstall` to print the canonical uninstall prompt
- `bootstrap-cleanup` to remove the temporary bootstrap workspace when install or adopt created it
- `current show|check` to inspect current-memory notes
- `route` and `sync-memory` to review likely relevant memory notes
- `promotion-report` to suggest notes that should graduate into canonical checked-in docs or become elimination candidates for skills, scripts, tests, or refactors
- `verify-payload` to validate the packaged bootstrap contract

Common arguments:

- `--target <path>` selects the repo
- `--format text|json` selects output format
- `--project-name`, `--project-purpose`, `--key-repo-docs`, `--key-subsystems`, `--primary-build-command`, `--primary-test-command`, `--other-key-commands` fill starter placeholders explicitly

`install` and `adopt` are conservative by default: missing files are copied, existing `AGENTS.md` and `memory/` files are left alone, and optional fragments are appended only when the fragment is not already present.

`doctor --strict-doc-ownership` forces the doc-ownership and shadow-doc audits even if the repository manifest has not opted in yet.

## Developing This Repository

Useful maintainer commands:

```bash
uv sync --group dev
uv run --group dev pytest
uv run python scripts/check/check_memory_freshness.py
```

When installer behaviour or the payload changes, verify against this repo itself. When the packaged tool changes, bump the package version in `pyproject.toml`.
