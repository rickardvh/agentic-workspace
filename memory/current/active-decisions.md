# Active Decisions

## Status

Active

## Scope

Current high-impact decisions that still affect active implementation choices.

## Load when

- Updating root orchestration, CI routing, or ownership contracts.
- Deciding whether package-level changes should run through root-owned systems.

## Review when

- Root check entrypoints or CI routing behavior changes.
- Ownership boundaries between root and package systems are updated.

## Failure signals

- Root and package workflows disagree on operational ownership.
- CI or local checks run against the wrong sync lane.

## Current decisions

- Root owns the operational memory and planning installs for this repo; package-local copies are fixtures or payload sources.
- The root `agentic-workspace` CLI is the shared lifecycle entrypoint for common workspace verbs, while package CLIs remain authoritative for module-specific behavior.
- Keep collaboration-safe installed-contract hardening ahead of new top-level concepts when dogfooding exposes merge or ownership ambiguity.
- Use ownership tests and explicit manifests before introducing new shared managed surfaces.
- Keep `ROADMAP.md` as a concise sequencing queue; move long-horizon product framing into `docs/ecosystem-roadmap.md` and `docs/design-principles.md`.

## Verify

- TODO.md
- ROADMAP.md
- README.md
- docs/ecosystem-roadmap.md
- docs/design-principles.md

## Last confirmed

2026-04-06 after trimming the roadmap to queue-only scope
