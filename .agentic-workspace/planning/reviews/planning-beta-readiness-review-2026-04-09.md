# Planning Beta-Readiness Review

## Review Metadata

- Review mode: `planning-surface`
- Review question: Does the current Agentic Planning contract now justify a `beta` label, or do remaining contract gaps still make `alpha` the correct maturity claim?
- Main inputs inspected first:
  - `docs/maturity-model.md`
  - `packages/planning/README.md`
  - `.agentic-workspace/planning/execplans/README.md`
  - recent planning-focused archived execplans from `.agentic-workspace/planning/execplans/archive/`
- Default finding cap: 3

## Scope

- Judge whether the current planning maturity label still matches current package reality.
- Identify only the remaining maturity blockers that are still real enough to deserve queued follow-through.

## Non-Goals

- Re-review every planning feature in depth.
- Promote work directly into active execution from this review.
- Treat historical churn as a blocker unless it still affects the current contract.

## Findings

### 1. Planning should remain `alpha`, but for current contract-shape reasons rather than historical uncertainty

- Source class: `mixed`
- Confidence: high
- Risk if unchanged: The label itself is still directionally correct, but the repo understates why; that makes the maturity page weaker as a decision surface for adopters and maintainers.
- Evidence:
  - The package now has a real and useful contract with explicit horizons, archive discipline, review lanes, capability-aware execution, delegated judgment, and intent-continuity follow-through.
  - But the contract shape has still changed materially in the current dogfooding tranche: recent slices added or tightened delegated judgment, intent continuity, and required follow-on as first-class planning rules.
  - That means the package is no longer “vague,” but it is still actively stabilizing what the planning contract must carry to prevent partial delivery and lost follow-through.
- Suggested action: Keep the maturity label at `alpha`, but rewrite the explanation in `docs/maturity-model.md` so it reflects current stabilization work instead of older generic wording.
- Promotion target and trigger: Canonical docs now; no roadmap promotion needed.

### 2. The strongest remaining beta blockers are missing explicit contracts for recovery guidance and execution summaries

- Source class: `mixed`
- Confidence: medium-high
- Risk if unchanged: Planning can preserve direction and required continuation better than before, but restart and recovery behavior still depend too much on scattered prose and ad hoc summaries.
- Evidence:
  - `docs/agent-os-capabilities.md` still treats `Environment / recovery guidance` and `Handoff / execution summaries` as important internal capabilities rather than explicit shipped planning contracts.
  - Recent planning hardening focused on intent continuity and required follow-on routing, which reduced one major partial-delivery failure mode, but did not yet define one canonical recovery or summary shape that later sessions can rely on.
  - `packages/planning/README.md` now promises better continuation behavior than before, so the absence of those more explicit follow-through surfaces is the clearest remaining gap between “useful alpha” and “boring beta”.
- Suggested action: Keep both gaps in `ROADMAP.md` as the next bounded planning-adjacent candidates, with `Handoff and execution summary contract` ahead of `Environment and recovery guidance contract`.
- Promotion target and trigger: `ROADMAP.md`; promote when the next planning-facing tranche is selected.

## Dismissed Or Deferred

- No evidence that planning should move to `beta` immediately.
- No new blocker was strong enough to justify reopening already-resolved archive-cleanup or intent-continuity work.
- No new candidate was justified beyond the already-captured handoff/summary and environment/recovery gaps.

## Recommended Outcome

- Keep Agentic Planning at `alpha`.
- Make the maturity explanation more explicit about why the package is still stabilizing.
- Use the next planning-facing tranche to land a handoff/execution-summary contract, then revisit the maturity label.

## Validation / Inspection Commands Used

- `rg -n "alpha|beta|maturity|stabil" packages/planning docs README.md llms.txt`
- `Get-Content docs/maturity-model.md`
- `Get-Content packages/planning/README.md`
- `Get-ChildItem .agentic-workspace/planning/execplans/archive -File | Select-Object -ExpandProperty Name`
