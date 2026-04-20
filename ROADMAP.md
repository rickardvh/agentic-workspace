# Roadmap

Last reviewed: 2026-04-20

## Purpose

Inactive long-horizon candidate work.

## Scope

This file is a concise sequencing queue, not the canonical home for product doctrine or long-form maturity framing.

Keep long-horizon narrative in `docs/ecosystem-roadmap.md` and design constraints in `docs/design-principles.md`.
Keep the broader long-horizon capability map in `docs/agent-os-capabilities.md`.

## GitHub Issue Intake

- Latest open planning tranche: GitHub issues `#206` and `#220`-`#232`.
- The active TODO/execplan already owns `#206` and `#231`; the remaining open issues are grouped below as inactive candidate lanes.
- Keep issue bodies as compact intake sources only; execute from checked-in planning after promotion.
- Keep detailed closure history in archived execplans and issue comments, not here.

## Active Handoff

- Lane: Ownership boundary and low-residue installs
  ID: ownership-boundary-and-local-only-mode
  Surface: docs/execplans/local-only-residue-via-git-exclude.md
  Why now: The lane is really about consolidating package-owned state into one unambiguous home inside the package install tree; residue cleanup is the downstream consequence that makes the boundary feel unobtrusive.
- The simplification, improvement-latitude, iterative follow-through, optimization-bias, setup-findings, standing-intent, planning-surface-clarity, planner-worker orchestrator workflow, declarative contract-tooling, canonical module-reporting, bounded workspace CLI hotspot, native candidate-lane, workspace-self-adaptation/friction-order, repo-directed improvement evidence-threshold, validation-friction repo-friction, config-driven execution posture, config-driven autonomy and agnostic improvements, startup front door clarity and agent-agnostic first contact, Memory trust/usefulness/routing/capture, Memory trust/habitual-pull, routine recovery compression/convergence, compression-and-convergence-of-operating-model, rotating-agent-economics, portable-declarative-contracts-beyond-python-cli, signal-hygiene-and-evidence-based-improvement, intent-satisfaction-validation, the earlier `#220`-`#231` tranche, and the ownership-boundary-and-local-only-mode lane are complete.
- The simplification, improvement-latitude, iterative follow-through, optimization-bias, setup-findings, standing-intent, planning-surface-clarity, planner-worker orchestrator workflow, declarative contract-tooling, canonical module-reporting, bounded workspace CLI hotspot, native candidate-lane, workspace-self-adaptation/friction-order, repo-directed improvement evidence-threshold, validation-friction repo-friction, config-driven execution posture, config-driven autonomy and agnostic improvements, startup front door clarity and agent-agnostic first contact, Memory trust/usefulness/routing/capture, Memory trust/habitual-pull, routine recovery compression/convergence, compression-and-convergence-of-operating-model, rotating-agent-economics, portable-declarative-contracts-beyond-python-cli, signal-hygiene-and-evidence-based-improvement, intent-satisfaction-validation, and the earlier `#220`-`#231` tranche are complete.

## Candidate Lanes

- Lane: Product compression and gradual discovery
  ID: product-compression-and-gradual-discovery
  Priority: second
  Issues: #230, #227, #228, #223, #224, #225, #226
  Outcome: Make the visible product shape smaller and more progressively discoverable while preserving real leverage.
  Why now: Onboarding and restart cost are now dominated by visible product shape rather than missing capability.
  Promotion signal: Promote when a visible surface no longer earns its cognitive cost or a deeper concept can stay hidden until a task boundary actually needs it.
  Suggested first slice: Define the tiny safe startup model, the boundary-triggered escalation cues, and the compact module-capability advertisement pattern.

- Lane: System intent and planning trust
  ID: system-intent-and-planning-trust
  Priority: third
  Issues: #236, #237, #238, #232, #229, #220, #222, #221
  Outcome: Preserve higher-level product intent and make durable planning/closure semantics more trustworthy across tasks, issues, and sessions.
  Why now: The repo already validates local slices well; the remaining gap is durable intent and honest follow-through.
  Promotion signal: Promote when local success is not enough to preserve later proof, closure truthfulness, or cross-session alignment.
  Suggested first slice: Define the minimum durable system-intent layer and the honest closure/reopen semantics for slice-complete but intent-partial work.

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
