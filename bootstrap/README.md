# Bootstrap Package

This package is a repo-agnostic bootstrap for agent memory and lightweight checked-in coordination notes.

It is intended to be copied into an existing repository to provide:

- `AGENTS.md` as the slim local bootstrap entrypoint
- `memory/` as durable checked-in technical memory
- `memory/manifest.toml` as optional machine-readable memory metadata
- `memory/skills/` as checked-in core memory skills for repo-local workflows
- `memory/system/WORKFLOW.md` as the shared reusable memory workflow rules
- `memory/system/SKILLS.md` as the shared skill-boundary guidance
- `memory/system/VERSION.md` as the installed bootstrap version marker
- `memory/system/UPGRADE.md` as the upgrade playbook for older installs
- `memory/current/project-state.md` as a short human-readable overview
- `memory/current/task-context.md` as optional checked-in current-task compression
- an advisory memory freshness audit
- optional workflow fragments for common contribution flows

The packaged files are the durable state and knowledge layer. Repeatable workflow-like actions should live in optional skills rather than expanding the mandatory payload indefinitely.

Optional extension mechanisms such as skills should stay outside the mandatory payload unless a repository explicitly chooses to add them.

The CLI around this payload can also inspect the current-memory surface, suggest relevant notes for touched files, use manifest-aware routing when `memory/manifest.toml` is present, and verify payload consistency for maintainers and agent workflows.

Treat the packaged memory notes as a starting cache of reusable operating knowledge, not an archive to expand without limit.

When maintaining this repository, treat `bootstrap/` as the source of truth for installed files. The packaged wheel payload is built from this directory.

## Copy targets

Copy as-is:

- `AGENTS.md`
- `memory/`
- `scripts/check/check_memory_freshness.py`

Merge or append:

- `optional/pull_request_template.fragment.md`
- `optional/CONTRIBUTING.fragment.md`
- `optional/Makefile.fragment.mk`

Do not install maintainer-only repo docs or implementation notes by default.

## Recommended installation order

1. Copy `AGENTS.md`.
2. Copy `memory/`, including `memory/system/WORKFLOW.md`, `memory/system/SKILLS.md`, `memory/current/project-state.md`, and `memory/current/task-context.md`.
3. Copy `memory/skills/`.
4. Optionally merge the workflow fragments.
5. Run `scripts/check/check_memory_freshness.py`.

## Placeholder replacement

`<PROJECT_NAME>` is filled by the installer when possible.

Review and replace repo-specific placeholders such as:

- `<PROJECT_PURPOSE>`
- `<KEY_REPO_DOCS>`
- `<KEY_SUBSYSTEMS>`
- `<PRIMARY_BUILD_COMMAND>`
- `<PRIMARY_TEST_COMMAND>`

The installer can also fill these placeholders when you pass the matching explicit CLI flags.

Delete unused routing examples once the target repository has concrete notes.

`AGENTS.md` should stay short and point to `memory/system/WORKFLOW.md` for the shared operating model.

This bootstrap is task-system agnostic. `/memory` owns durable technical knowledge, `memory/current/project-state.md` is the overview note, `memory/current/task-context.md` is optional checked-in current-work compression, and `memory/skills/` holds the checked-in core memory skills that repos can extend with their own sibling skills.

Bundled product skills should stay limited to bootstrap lifecycle operations. Repo-local memory procedures should live in checked-in `memory/skills/`.

`memory/system/VERSION.md` is the machine-readable version marker used for deterministic upgrades.

## Upgrade model

Prefer this flow for existing or older installs:

1. Run `agentic-memory-bootstrap doctor --target <repo>`.
2. Run `agentic-memory-bootstrap upgrade --dry-run --target <repo>`.
3. Apply the minimal-safe upgrade plan.
4. Use `--apply-local-entrypoint` only when you want the installer to patch `AGENTS.md`.

Use `agentic-memory-bootstrap list-files` to preview the packaged files that the installer exposes.

## Automation notes

A later automation script should:

- copy stable files as-is
- merge append-only fragments into existing files
- replace placeholders or leave them for a human to fill in
- avoid overwriting existing repo-specific memory notes blindly
- treat `memory/system/VERSION.md` as the installed system version marker
- run the freshness audit after installation
