# Bootstrap Package

This package is a repo-agnostic bootstrap for agent memory, planning, and local working context.

It is intended to be copied into an existing repository to provide:

- `AGENTS.md` bootstrap instructions
- `TODO.md` as the execution-focused planning surface
- `memory/` as durable checked-in technical memory
- `.agent-work/` as local scratch working context
- an advisory memory freshness audit
- optional workflow fragments for common contribution flows

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
3. Copy `memory/`.
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

## Automation notes

A later automation script should:

- copy stable files as-is
- merge append-only fragments into existing files
- create `.agent-work/` locally if the target repo should not commit it
- replace placeholders or leave them for a human to fill in
- avoid overwriting existing repo-specific memory notes blindly
- run the freshness audit after installation
