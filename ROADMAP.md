# Roadmap

Last reviewed: 2026-04-05

## Purpose

Inactive long-horizon candidate work.

## Active Handoff

- Monorepo scaffold is in place.
- No active execution tranche is currently promoted.
- Maintainer feedback favors sharper documentation, liveness checks, and naming consistency over adding new layers.
- New maintainer feedback centers on git-safe installed contracts: merge-friendly file shapes, weak-authority current surfaces, explicit lifecycle markers, and collaboration-oriented checks.
- Promote the next candidate only when the scope is bounded enough for a short execplan and a narrow validation story.

## Next Candidate Queue

- Memory collaboration-safe contract hardening: make installed memory safer for concurrent edits by weakening `memory/current/` authority, tightening one-fact-one-home discipline, defining stale or superseded note expectations more explicitly, and adding checks for oversized current-state notes or durable-note duplication pressure. Promote when memory-current and note-hygiene rules can be delivered as one bounded contract-and-check tranche.

- Cross-module collaboration contract and write-authority rules: make branch-vs-trunk state boundaries, canonical-source precedence, selective write authority, and partial-adoption behavior explicit across memory, planning, and the workspace layer so concurrent contributors can tell which surfaces are safe to edit. Promote when the integration rules can be expressed as one compact package-facing contract without expanding the workspace layer's ownership.

- Installed-contract collaboration design checklist for package authorship: add a package-authoring checklist aimed at templates, generated artifacts, lifecycle markers, collaboration-oriented checks, and merge-safe file shapes so new installed surfaces are evaluated for concurrent git workflows instead of only single-agent restartability. Promote when the checklist can stay short, package-facing, and directly actionable during package evolution.

- Shared tooling extraction: evaluate a common checker core when the first stable monorepo release exposes repeated maintenance friction across duplicated scripts.

- Shared tooling extraction: evaluate a common checker core when the first stable monorepo release exposes repeated maintenance friction across duplicated scripts.

## Reopen Conditions

- Reopen roadmap planning when active queue completes or a new bounded candidate is ready to promote.

## Promotion Rules

- Promote candidate items only when active tranche dependencies are clear and bounded.
- Keep detailed execution in `docs/execplans/` once promoted.
- Prefer collaboration-safe installed-contract work over new top-level concepts when dogfooding shows concurrent-edit ambiguity or merge pressure.
