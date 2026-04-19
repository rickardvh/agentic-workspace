# Roadmap

Last reviewed: 2026-04-19

## Purpose

Inactive long-horizon candidate work.

## Scope

This file is a concise sequencing queue, not the canonical home for product doctrine or long-form maturity framing.

Keep long-horizon narrative in `docs/ecosystem-roadmap.md` and design constraints in `docs/design-principles.md`.
Keep the broader long-horizon capability map in `docs/agent-os-capabilities.md`.

## Active Handoff

- No active handoff right now.

## GitHub Issue Intake

- Latest open planning tranche: GitHub issues `#161`-`#217`, grouped below into ordered inactive candidate lanes.
- Keep issue bodies as compact intake sources only; execute from checked-in planning after promotion.
- Keep detailed closure history in archived execplans and issue comments, not here.
- The simplification, improvement-latitude, iterative follow-through, optimization-bias, setup-findings, standing-intent, planning-surface-clarity, planner-worker orchestrator workflow, declarative contract-tooling, canonical module-reporting, bounded workspace CLI hotspot, native candidate-lane, workspace-self-adaptation/friction-order, repo-directed improvement evidence-threshold, validation-friction repo-friction, config-driven execution posture, config-driven autonomy and agnostic improvements, startup front door clarity and agent-agnostic first contact, Memory trust/usefulness/routing/capture, Memory trust/habitual-pull, routine recovery compression/convergence, compression-and-convergence-of-operating-model, rotating-agent-economics, portable-declarative-contracts-beyond-python-cli, and signal-hygiene-and-evidence-based-improvement tranches are complete.

## Candidate Lanes


- Lane: Intent-satisfaction validation
  ID: intent-satisfaction-validation
  Priority: first
  Issues: #216, #217
  Outcome: Add intent-satisfaction validation and review reports so archived plans and closed issues distinguish local slice completion from actual achievement of the original goal.
  Why now: Essential to ensure that "completed" work actually solved the underlying problem, reducing false completion states.
  Promotion signal: Promote immediately as top priority.
  Suggested first slice: Add intent-satisfaction validation to archived plans and closed issues.

- Lane: Payload drift and installer knowledge
  ID: payload-drift-and-installer-knowledge
  Priority: second
  Issues: #214, #215
  Outcome: Add early payload-drift detection to reports and promote installer behavior into durable operator guidance.
  Why now: Reduces manual payload mirroring friction and prevents agents from rediscovering installer logic.
  Promotion signal: Promote when friction with payload syncing occurs again.
  Suggested first slice: Add payload-drift detection to agentic-workspace report.

- Lane: Local-only adoption and external-agent ergonomics
  ID: local-only-adoption-and-external-agent-ergonomics
  Priority: third
  Issues: #206
  Outcome: Enable agents to use Agentic Workspace in repositories they do not own (or where checked-in adoption is not desired) through a local-only installation mode.
  Why now: This is a common "read-only" or "guest" agent use case that currently lacks a first-class supported path.
  Promotion signal: Promote when a guest-agent workflow needs to persist local planning/memory without polluting the target repository's tracked files.
  Suggested first slice: Define the local-only storage and configuration shim for unowned repositories.

- Lane: Agent-native memory and habitual-pull ergonomics
  ID: agent-native-memory-habitual-pull
  Priority: fourth
  Issues: #218
  Outcome: Add an agent-native memory retrieval surface so agents can pull relevant knowledge tranches for a task without manual exploratory scans.
  Why now: Reduces token cost and reasoning depth by narrowing the context-discovery window.
  Promotion signal: Promote when task context discovery becomes a significant part of the startup cost.
  Suggested first slice: Define the metadata/search contract for task-specific knowledge retrieval.

- Lane: Signal hygiene and validation hardening
  ID: signal-hygiene-validation-hardening
  Priority: fifth
  Issues: #219
  Outcome: Fix persistent type-check and validation noise in the root workspace to restore high trust in the primary check lanes.
  Why now: Noise in 'make check' leads to missed real regressions and increases developer cognitive load.
  Promotion signal: Promote immediately to clear the master branch.
  Suggested first slice: Fix the type diagnostics in _schema.py.

## Reopen Conditions

- Reopen roadmap planning when the active queue completes or a new bounded candidate is ready to promote.

## Promotion Rules

- Promote candidate items only when dependencies are clear and the scope fits a short execplan.
- For new contract surfaces, require the promotion note to name the older path it replaces, merges, or materially simplifies.
- For review-derived candidates, prefer promotion only after the same product-level deficiency appears in at least two independent captures, or one review artifact plus one repeated maintenance or dogfooding pass, unless explicit maintainer direction justifies immediate activation.
- Prefer measured friction, repeated failure, repeated dogfooding pain, or explicit maintainer override over concept opportunity when deciding whether new work belongs in planning at all.
- Keep detailed execution in `docs/execplans/` once promoted.
- Prefer collaboration-safe installed-contract work over new top-level concepts when dogfooding shows concurrent-edit ambiguity or merge pressure.
- Prefer friction-confirmed or repeated review findings over one-off static-analysis neatness.
