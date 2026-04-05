# Planning Package Context

## Status

Active

## Purpose

Capture durable context imported from the previous package-local planning and memory installs so root planning and memory ownership can replace package-local installs.

## Consolidated from

- Previous package-local planning TODO, ROADMAP, memory current note, and archived execplans under packages/planning/.

## Durable context

- Planning owns active execution state through TODO.md, ROADMAP.md, and docs/execplans.
- Memory remains an optional companion for durable technical context and should not own active queue state.
- Keep planning and memory ownership boundaries explicit in agent startup and routing docs.
- Package planning active queue was empty at consolidation time.
- Package planning roadmap carried one candidate: pin .agentic-planning/UPGRADE-SOURCE.toml to immutable tags/releases when release cadence stabilises.

## Imported history location

- docs/execplans/archive/imported-planning-package/

## Monorepo adaptation note

Root ownership now contains the installed planning and memory systems. Package-local installed systems in packages/planning should be removed after this context is preserved.

## Load when

- Editing files under packages/planning.
- Updating planning bootstrap package ownership or migration consolidation behavior.

## Review when

- Planning package README, bootstrap payload, or archived execplan imports change materially.
- Root planning orchestration changes how imported planning context is routed.

## Failure signals

- Package-planning work misses package-specific execution assumptions after root consolidation.
- Imported archive context under docs/execplans/archive/imported-planning-package becomes stale or inconsistent with package state.

## Verify

- packages/planning/README.md
- packages/planning/bootstrap/
- packages/planning/src/
- packages/planning/tests/
- docs/execplans/archive/imported-planning-package/

## Last confirmed

2026-04-05 during monorepo installed-system consolidation
