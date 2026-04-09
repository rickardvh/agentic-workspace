# Decision: Repository Foundation Stability

## Status

Decided

## Date

2026-04-05

## Load when

Read this note when deciding whether the repo is still in structural cleanup mode or whether new work should start from product priorities and bounded planning promotion.

## Review when

Review this note if root-owned planning or memory stops being the operational authority, if package fixtures start acting like live state again, or if a new active tranche appears without bounded planning surfaces.

## Failure signals

Failure looks like the monorepo no longer operating from one root-owned planning and memory install, or contributors reintroducing historical cleanup behavior as if the foundation were still unsettled.

## Decision

Treat the repository foundation as stable. Root-owned planning and memory are the operational authority, both bootstraps use the unified `.agentic-workspace/` namespace, package boundaries remain independent, and future work should start from roadmap promotion rather than more cleanup tranches.

## Why

The root orchestration contract, ownership ledger, and validation lanes were already in place, and day-to-day dogfooding had moved the repo from structural cleanup into additive product work.

## Consequences

The monorepo host is the normal source of truth for ongoing work, package maintainers can release independently with confidence in root orchestration, and archived cleanup plans should stay historical rather than return as active operating guidance.

## Ongoing stance

Keep archived execplans lightweight, keep new TODO entries bounded and roadmap-driven, and treat future work as product evolution rather than repository stabilization. Use [foundation-stability-check](../../tools/skills/foundation-stability-check/SKILL.md) for the repeatable recheck workflow.

## Verify

Confirm that `TODO.md` and `ROADMAP.md` remain bounded, the relevant root validation lanes still pass, and package docs still describe the current `.agentic-workspace/`-based operating model.

## Last confirmed

2026-04-05 after repository cleanup guidance was simplified
