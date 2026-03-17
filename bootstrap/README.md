# Bootstrap Package

This package is a repo-agnostic bootstrap for agent memory, planning, and local working context.

It is intended to be copied into an existing repository to provide:

- `AGENTS.md` as the slim local bootstrap entrypoint
- `TODO.md` as the execution-focused planning surface
- `memory/` as durable checked-in technical memory
- `memory/system/WORKFLOW.md` as the shared reusable workflow rules
- `memory/system/VERSION.md` as the installed bootstrap version marker
- `memory/system/UPGRADE.md` as the upgrade playbook for older installs
- `.agent-work/` as local scratch working context
- an advisory memory freshness audit
- optional workflow fragments for common contribution flows

Optional extension mechanisms such as skills should stay outside the mandatory payload unless a repository explicitly chooses to add them.

Treat the packaged memory notes as a starting cache of reusable operating knowledge, not an archive to expand without limit.

When maintaining this repository, treat `bootstrap/` as the source of truth for installed files. The packaged wheel payload is built from this directory.

## Copy targets

Copy as-is:

- `AGENTS.md`
- `TODO.md`
- `memory/`
- `scripts/check/check_memory_freshness.py`

Merge or append:

- `.gitignore.append`
- `optional/pull_request_template.fragment.md`
- `optional/CONTRIBUTING.fragment.md`
- `optional/Makefile.fragment.mk`

Do not install maintainer-only repo docs or implementation notes by default.

Local-only templates:

- `.agent-work/README.md`
- `.agent-work/current-task.md`
- `.agent-work/findings.md`
- `.agent-work/handoff.md`

In many repositories, `.agent-work/` should be created locally rather than committed. The templates live here so a later automation script can materialise them consistently.

## Git-ignore guidance

`.agent-work/` should be git-ignored in the target repository.

Use `bootstrap/.gitignore.append` to append:

```gitignore
# Local agent working context
.agent-work/
```

## Recommended installation order

1. Copy `AGENTS.md`.
2. Copy `TODO.md`.
3. Copy `memory/`, including `memory/system/WORKFLOW.md`.
4. Copy `.agent-work/` templates or create them locally from the templates here.
5. Append `.gitignore.append` to the target repo `.gitignore`.
6. Optionally merge the workflow fragments.
7. Run `scripts/check/check_memory_freshness.py`.

## Placeholder replacement

Replace placeholders such as:

- `<PROJECT_NAME>`
- `<PROJECT_PURPOSE>`
- `<KEY_REPO_DOCS>`
- `<KEY_SUBSYSTEMS>`
- `<PRIMARY_BUILD_COMMAND>`
- `<PRIMARY_TEST_COMMAND>`

Delete unused routing examples once the target repository has concrete notes.

`AGENTS.md` should stay short and point to `memory/system/WORKFLOW.md` for the shared operating model.

Skills are an optional extension layer for specialised repeatable procedures. They are not part of the mandatory bootstrap payload.

`memory/system/VERSION.md` is the machine-readable version marker used for deterministic upgrades.

## Upgrade model

Prefer this flow for existing or older installs:

1. Run `agentic-memory-bootstrap doctor --target <repo>`.
2. Run `agentic-memory-bootstrap upgrade --dry-run --target <repo>`.
3. Apply the minimal-safe upgrade plan.
4. Use `--apply-local-entrypoint` only when you want the installer to patch `AGENTS.md`.

Use `agentic-memory-bootstrap list-files` to preview the packaged files and local templates that the installer exposes.

## Automation notes

A later automation script should:

- copy stable files as-is
- merge append-only fragments into existing files
- create `.agent-work/` locally if the target repo should not commit it
- replace placeholders or leave them for a human to fill in
- avoid overwriting existing repo-specific memory notes blindly
- treat `memory/system/VERSION.md` as the installed system version marker
- run the freshness audit after installation
