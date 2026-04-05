# Project State

## Status

Active

## Scope

- Lightweight current overview only.

## Applies to

- The repository's current shared orientation and memory entrypoints.

## Load when

- Starting work and needing a short current overview.
- Returning to the repository after a break.

## Review when

- The repo's current focus changes materially.
- Recent meaningful progress or blockers change.
- Main orientation docs move or change role.

## Current focus

- Stabilise `agentic-planning-bootstrap` as a reusable package and self-hosted reference repo.
- Keep the planning bootstrap explicitly interoperable with `agentic-memory` so the two systems have a clean ownership split.

## Recent meaningful progress

- Initial package skeleton landed with packaged payload, installer CLI, baseline tests, and self-hosted planning surfaces.
- Memory bootstrap was adopted conservatively into this repo, including the shared `.agentic-memory/` workflow surface and routed `memory/` tree.
- The planning bootstrap contract now treats memory as an optional routed companion rather than a competing startup surface.

## Blockers

- None currently noted.

## High-level notes

- Planning remains the owner of `TODO.md`, active execplans, and `ROADMAP.md`.
- Memory should only hold durable routed knowledge and compact current-state orientation for this repo.
- The package currently covers install, adopt, doctor, status, verification, and prompt flows; upgrade and uninstall parity with `agentic-memory-bootstrap` is still future work.

## Failure signals

- The overview becomes a task list instead of a short current-state note.
- The note drifts away from the current repository reality.

## Verify

- Read `memory/index.md` and confirm the routing still matches the memory structure.
- Confirm the current focus, recent progress, and blockers still reflect the repo.
- Confirm `AGENTS.md`, `tools/agent-manifest.json`, and `tools/AGENT_QUICKSTART.md` still preserve the planning-versus-memory ownership boundary.

## Verified against

- `memory/index.md`
- `.agentic-memory/WORKFLOW.md`
- `README.md`
- `AGENTS.md`
- `docs/execplans/planning-bootstrap-initialisation-2026-04-05.md`

## Last confirmed

2026-04-05 after memory bootstrap adoption and planning-memory boundary review
