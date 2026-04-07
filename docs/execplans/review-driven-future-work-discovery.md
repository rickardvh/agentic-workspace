# Execplan: Review-Driven Future Work Discovery

## Goal

Add a deliberate planning workflow for agent-generated future-work discovery so the repo can support true agent-driven development over time without relying only on incidental improvement signals.

The workflow should let agents perform bounded review passes, capture concrete findings, and promote selected findings into roadmap or active planning while keeping friction-derived signals as the higher-trust lane.

## Non-Goals

- Do not collapse review findings into ordinary implementation behavior.
- Do not treat static-analysis findings as equivalent to friction-derived improvement signals.
- Do not send all findings directly into `TODO.md` or create broad speculative cleanup work.
- Do not make review artifacts a substitute for durable memory or canonical docs.

## Active Milestone

### Milestone
Define the planning contract for review-driven future-work discovery and decide how it should integrate with the existing planning and memory model.

### Status
active

### Ready
ready

### Blocked
none

### optional_deps
none

## Immediate Next Action

Draft the canonical workflow contract for review passes, promotion rules, artifact shape, and candidate planning skills, then decide whether to land it first as a temporary execplan-only contract or promote it into package docs and shipped planning helpers.

## Touched Paths

- `docs/execplans/review-driven-future-work-discovery.md`
- `packages/planning/`
- `packages/memory/`
- `docs/design-principles.md`
- `ROADMAP.md`
- `TODO.md`

## Invariants

- Friction-derived improvement signals remain the higher-trust planning input.
- Review findings must be explicitly labeled as analysis-derived until confirmed.
- Capture and promotion remain separate steps.
- Review output must stay compact, evidence-based, and bounded.
- Planning remains the home for candidate future work; memory only receives durable knowledge that outlives immediate planning.
- The workflow must reduce agent supervision burden without creating self-generated maintenance churn.

## Proposed Shape

### Review lane

Introduce a bounded review-driven planning lane for deliberate analysis of repo weaknesses, future opportunities, and structural risks.

### Artifact type

Use scoped review artifacts, likely under `docs/reviews/`, to capture:

- review type
- scope
- findings
- evidence
- risk if unchanged
- suggested action
- confidence
- source (`static-analysis`, `friction-confirmed`, or `mixed`)
- promotion target
- promotion trigger

### Promotion model

Use staged promotion:

1. captured in review artifact only
2. promoted candidate for roadmap or TODO
3. confirmed by friction, repetition, or explicit maintainer choice
4. active planned work

### Candidate skills

- `planning-review-pass`
- `planning-promote-review-findings`

## Validation Commands

- `make planning-surfaces`
- `make maintainer-surfaces`

## Completion Criteria

- The repo has a clear planning contract for review-driven future-work discovery.
- Review findings and improvement signals are explicitly separated.
- Promotion rules are concrete enough to prevent speculative queue churn.
- The intended artifact shape and candidate skills are clear enough for implementation planning.
- Follow-up package and doc changes are identified.

## Drift Log

- 2026-04-07: Created as a temporary execplan to capture the proposed review-driven planning lane before deciding how much should become shipped planning behavior.
