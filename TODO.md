# TODO

Last pruned: 2026-04-05

## Purpose

This file is the active queue and activation surface.
Use it to show what is active now, what owns execution, and which small direct tasks still need doing.
Historical rationale, completed tranche detail, and long-form execution context belong in active execplans, archived execplans, docs, memory, and git history.
Long-horizon planning belongs in `ROADMAP.md`.
When there is no active task, keep this file minimal.

## Hygiene Rules

- Keep this file under ~150 lines.
- Keep only active work and near-term queued work.
- Maximum 3 `Now` items in progress at once.
- Planned work should list only: `ID`, `Status`, `Surface`, and `Why now`.
- Small direct tasks that do not justify an execplan may also include `Next action` and `Done when`.
- Do not restate phase scope, blockers, validation, or completion criteria here when an execplan already owns them.
- Remove completed implementation detail immediately after closure.
- Do not store architecture essays, migration logs, or full retrospectives here.

## Next

- ID: payload-hygiene
  Status: in-progress
  Surface: docs/execplans/payload-hygiene-2026-04-05.md
  Why now: the canonical self-refresh run reported generated `__pycache__` residue in the packaged payload, which should be removed before the next milestone closes.
