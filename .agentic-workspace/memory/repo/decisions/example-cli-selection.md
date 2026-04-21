# Starter Example: CLI Selection

This is a starter example for a decision note.
Replace or delete it once the repository has a real lasting trade-off worth keeping.

## Decision

- Prefer one shared lifecycle entrypoint for normal work, while keeping lower-level package commands available for maintainer or debugging paths.

## Consequence

- Normal use gets cheaper and easier to teach, but package-local escape hatches still need to stay documented.

## Load when

- A maintainer is deciding whether a workflow should stay on the shared lifecycle path or drop to a package-local command.

## Review when

- The shared entrypoint no longer covers the common lifecycle safely, or lower-level commands become the routine path again.

## Failure signals

- Maintainers bypass the shared entrypoint for ordinary work because the supposed default path is no longer sufficient.

## Verify

- Check that the documented default path still covers the common lifecycle without forcing routine fallback to package-local commands.

## Last confirmed

2026-04-15
