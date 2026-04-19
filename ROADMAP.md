# Roadmap

Last reviewed: 2026-04-18

## Purpose

Inactive long-horizon candidate work.

## Scope

This file is a concise sequencing queue, not the canonical home for product doctrine or long-form maturity framing.

Keep long-horizon narrative in `docs/ecosystem-roadmap.md` and design constraints in `docs/design-principles.md`.
Keep the broader long-horizon capability map in `docs/agent-os-capabilities.md`.

## Active Handoff

- No active handoff right now.

## GitHub Issue Intake

- Latest open planning tranche: GitHub issues `#161`-`#211`, grouped below into ordered inactive candidate lanes.
- Keep issue bodies as compact intake sources only; execute from checked-in planning after promotion.
- Keep detailed closure history in archived execplans and issue comments, not here.
- The simplification, improvement-latitude, iterative follow-through, optimization-bias, setup-findings, standing-intent, planning-surface-clarity, planner-worker orchestrator workflow, declarative contract-tooling, canonical module-reporting, bounded workspace CLI hotspot, native candidate-lane, workspace-self-adaptation/friction-order, repo-directed improvement evidence-threshold, validation-friction repo-friction, config-driven execution posture, config-driven autonomy and agnostic improvements, startup front door clarity and agent-agnostic first contact, Memory trust/usefulness/routing/capture, Memory trust/habitual-pull, routine recovery compression/convergence, compression-and-convergence-of-operating-model, and rotating-agent-economics tranches are complete.

## Candidate Lanes


- Lane: Portable declarative contracts and agent-native alignment
  ID: portable-declarative-contracts-beyond-python-cli
  Priority: first
  Issues: #161, #166, #167, #168, #169, #170, #194, #207, #208, #211
  Outcome: move stable lifecycle and runtime truth toward declarative portable contract sources and align repo planning schemas with agent-native structures (cold-start protocols, escalation boundaries).
  Why now: The operating model is compressed; the next level of efficiency comes from matching repo surfaces to the internal reasoning structures of strong agents.
  Promotion signal: promote when the repo can name one stable next extraction target or a clear portable architecture/tool-selection rule without inventing a bespoke workflow language.
  Suggested first slice: Define a machine-readable 'Cold-Start' Protocol or align the `execplan` schema with agent-native planning structure.

- Lane: Signal hygiene and evidence-based improvement
  ID: signal-hygiene-and-evidence-based-improvement
  Priority: second
  Issues: #188, #190, #192, #193, #195, #209, #210
  Outcome: Formalise the “workspace adapts first, repo changes later” rule. Use planning/validation friction as structural signals and make 'Proof Reports' and 'Knowledge Promotion' standard repo practices.
  Why now: As the core feature set stabilizes, preventing speculative sprawl and ensuring improvement is driven by evidence becomes the primary maintenance challenge.
  Promotion signal: Promote when a recurring friction pattern is identified that requires a structural instead of purely doc-based remediation.
  Suggested first slice: Define the evidence thresholds and anti-concealment guardrails for repo-directed improvement.

- Lane: Local-only adoption and external-agent ergonomics
  ID: local-only-adoption-and-external-agent-ergonomics
  Priority: third
  Issues: #206
  Outcome: Enable agents to use Agentic Workspace in repositories they do not own (or where checked-in adoption is not desired) through a local-only installation mode.
  Why now: This is a common "read-only" or "guest" agent use case that currently lacks a first-class supported path.
  Promotion signal: Promote when a guest-agent workflow needs to persist local planning/memory without polluting the target repository's tracked files.
  Suggested first slice: Define the local-only storage and configuration shim for unowned repositories.

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
