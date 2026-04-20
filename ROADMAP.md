# ROADMAP

<!-- GENERATED COMPATIBILITY VIEW: authoritative source is .agentic-workspace/planning/state.toml -->

This file is a compatibility projection of `.agentic-workspace/planning/state.toml`.

## Candidate Lanes

- Lane: Product compression and gradual discovery
  ID: product-compression-and-gradual-discovery
  Priority: second
  Issues: #230, #227, #228, #223, #224, #225, #226
  Outcome: Make the visible product shape smaller and more progressively discoverable while preserving real leverage.
  Why now: Onboarding, crash recovery, and restart cost are now dominated by visible product shape and issue-orientation overhead rather than missing capability.
  Promotion signal: Promote when a visible surface no longer earns its cognitive cost or a deeper concept can stay hidden until a task boundary actually needs it.
  Suggested first slice: Define the tiny safe startup model, the boundary-triggered escalation cues, and the compact module-capability advertisement pattern, with special attention to cheaper package-layer navigation and faster issue orientation after interruption.

- Lane: System intent and planning trust
  ID: system-intent-and-planning-trust
  Priority: third
  Issues: #236, #237, #238, #232, #229, #220, #222, #221
  Outcome: Preserve higher-level product intent and make durable planning/closure semantics more trustworthy across tasks, issues, and sessions.
  Why now: The repo already validates local slices well; the remaining gap is durable intent and honest follow-through.
  Promotion signal: Promote when local success is not enough to preserve later proof, closure truthfulness, or cross-session alignment.
  Suggested first slice: Define the minimum durable system-intent layer and the honest closure/reopen semantics for slice-complete but intent-partial work.

## Reopen Conditions

- Reopen when a queue or report signals new work.
