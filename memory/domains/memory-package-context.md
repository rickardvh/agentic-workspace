# Memory Package Context
## Status
Active
## Purpose
Durable context for `packages/memory/`.
## Durable boundaries
- The package stays planning-system agnostic and owns durable-memory bootstrap behavior rather than active execution state.
- Package authority lives in `packages/memory/src/`, `packages/memory/bootstrap/`, and `packages/memory/tests/`; the root `memory/` tree is only the dogfooded install.
- Memory-specific proof surfaces are `memory/manifest.toml`, the packaged memory skills, note templates, and the installer/freshness validation lanes.
## Companion skill
Use `memory/skills/package-context-inspection/SKILL.md` for the repeatable inspection checklist. Keep this note limited to durable package boundaries.
## Load when
- Editing files under `packages/memory/`.
## Review when
- The memory package source, payload, or test layout changes materially.
## Failure signals
- The note starts carrying workflow steps or generic monorepo rationale that belongs elsewhere.
## Verify
- `packages/memory/README.md`
- `packages/memory/src/`
- `packages/memory/tests/`
## Last confirmed
2026-04-08 after extracting the repeatable checklist into a checked-in skill and narrowing this note to memory-specific package boundaries
