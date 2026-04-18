# Memory Habitual Pull Audit

## Goal

- Classify recent ordinary-work evidence for whether Memory is actually being pulled directly, surfaced indirectly, bypassed, or merely hypothetically useful.
- Name one dominant remaining practical-pull gap, if any, before broader follow-through is considered.

## Scope

- `docs/execplans/archive/memory-trust-and-usefulness-first-slice-2026-04-17.md`
- `docs/execplans/archive/memory-routing-capture-cheap-path-2026-04-17.md`
- `docs/execplans/archive/module-reporting-first-slice-2026-04-17.md`
- `docs/reviews/ordinary-use-pull-audit-2026-04-16.md`
- `memory/runbooks/dogfooding-usage-ledger.md`
- `memory/current/routing-feedback.md`
- `ROADMAP.md`

## Non-Goals

- Build telemetry or a broad usage analytics system.
- Reopen Memory routing or trust-state work that already has healthy fixture-backed proof.
- Treat one isolated skip as evidence of a broad Memory redesign need.

## Review Mode

- Mode: `ordinary-use-pull`
- Review question: In recent ordinary repo work, was Memory a cheap habitual pull, a surfaced-but-still-indirect aid, a bypassed layer, or only hypothetically useful?
- Default finding cap: 3 findings
- Inputs inspected first: recent Memory archived execplans, the prior ordinary-use pull review, the usage ledger contract, and current routing-feedback residue

## Review Method

- Commands used:
  - `rg -n "habitual|ordinary work|Memory owns|would have helped|bypass|route-report" docs memory packages/memory tests`
  - `uv run agentic-memory-bootstrap report --target . --format json`
  - `uv run agentic-memory-bootstrap route-report --target . --format json`
- Evidence sources:
  - archived execplans
  - current Memory runbooks and routing evidence
  - active roadmap lane definition

## Findings

### Finding: Recent direct consultation is real, but mostly confined to Memory-focused work

- Summary: Recent slices prove that Memory routing, capture, and trust reporting are being exercised, but the strongest direct pulls are still inside Memory-specific maintenance or package work rather than broad ordinary repo tasks.
- Evidence:
  - `docs/execplans/archive/memory-routing-capture-cheap-path-2026-04-17.md`
  - `uv run agentic-memory-bootstrap route-report --target . --format json` currently shows 2 fixtures, 0 low-confidence fixtures, and 0 unresolved live routing cases.
- Risk if unchanged: Memory remains easy to describe as healthy while still feeling like a specialist tool rather than a habitual first pull during normal work.
- Suggested action: preserve the ordinary-work answer in a compact report view instead of requiring contributors to infer it from separate route, report, and ownership surfaces.
- Confidence: high
- Source: mixed
- Promotion target: `TODO.md` plus active execplan
- Promotion trigger: immediate; this is the current active lane
- Post-remediation note shape: retain as bounded audit evidence

### Finding: Ordinary work usually saw Memory indirectly through reporting and route proof, not as an explicit first-pull answer

- Summary: The recent combined-report and trust-state slices made Memory more visible and more trustworthy, but they still left ordinary work to reconstruct the actual cheap path from several surfaces.
- Evidence:
  - `docs/execplans/archive/memory-trust-and-usefulness-first-slice-2026-04-17.md`
  - `docs/execplans/archive/module-reporting-first-slice-2026-04-17.md`
  - `docs/reviews/ordinary-use-pull-audit-2026-04-16.md`
- Risk if unchanged: agents can keep bypassing Memory out of familiarity or inference cost even when routing and trust-state machinery are already good.
- Suggested action: add one compact Memory report view that states the baseline ordinary-work bundle, the owner boundary, and the current proof signals.
- Confidence: high
- Source: friction-confirmed
- Promotion target: `TODO.md` plus active execplan
- Promotion trigger: immediate; it is one bounded shipped-contract fix
- Post-remediation note shape: shrink

### Finding: The dominant remaining bypass reason is missing first-pull legibility, not raw routing accuracy

- Summary: Current live routing evidence is already healthy; the missing piece is a compact ordinary-work answer that tells an agent what Memory to load first and what Memory does not own.
- Evidence:
  - `uv run agentic-memory-bootstrap route-report --target . --format json`
  - `memory/runbooks/dogfooding-usage-ledger.md`
  - `ROADMAP.md`
- Risk if unchanged: the repo keeps treating practical-pull doubt as an open product concern even though the remaining gap is now narrow and contract-shaped.
- Suggested action: finish the lane by shipping the compact first-pull view and explicit owner boundary, then retire the remaining issue cluster if validation stays healthy.
- Confidence: high
- Source: mixed
- Promotion target: active execplan
- Promotion trigger: immediate; this is the explicit current closure decision
- Post-remediation note shape: archive alongside the completed lane

## Recommendation

- Promote: the compact `habitual_pull` report view and explicit ordinary-work first-pull guidance.
- Defer: any broader Memory redesign unless future ordinary work surfaces a new repeated bypass cause.
- Dismiss: pressure to add telemetry or force Memory usage.

## Validation / Inspection Commands

- `uv run agentic-memory-bootstrap report --target . --format json`
- `uv run agentic-memory-bootstrap route-report --target . --format json`
- `rg -n "habitual|ordinary work|Memory owns|would have helped|bypass|route-report" docs memory packages/memory tests`

## Drift Log

- 2026-04-18: Review created while implementing the `memory-trust-habitual-pull` lane to keep the recent-case audit and dominant remaining gap in checked-in form.
