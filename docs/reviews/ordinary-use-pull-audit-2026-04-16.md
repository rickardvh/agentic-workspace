# Ordinary-Use Pull Audit

## Goal

- Check which Memory and Planning surfaces are actually used in ordinary work.
- Identify low-pull surfaces that should be merged, demoted, or retired.
- Make outsider-legibility and self-hosting bias explicit review dimensions for everyday surface choice.

## Scope

- `docs/contributor-playbook.md`
- `docs/lazy-discovery-measurements.md`
- `docs/reviews/README.md`
- `memory/runbooks/dogfooding-feedback-routing.md`
- `memory/runbooks/dogfooding-usage-ledger.md`

## Non-Goals

- Ship telemetry.
- Build a generic analytics system.
- Re-open broader planning or architecture work beyond the pull audit.

## Review Mode

- Mode: `ordinary-use-pull`
- Review question: Which Memory and Planning surfaces are actually used in ordinary work, which are skipped, and which low-pull surfaces should be merged, demoted, or retired?
- Default finding cap: 3 findings
- Inputs inspected first: `docs/contributor-playbook.md`, `docs/lazy-discovery-measurements.md`, `memory/runbooks/dogfooding-feedback-routing.md`, `memory/runbooks/dogfooding-usage-ledger.md`

## Review Method

- Commands used:
  - `rg -n "dogfooding-feedback|dogfooding-usage-ledger|ordinary-use-pull|outsider-legibility|self-hosting" docs memory tests`
- Evidence sources:
  - canonical docs
  - memory runbooks
  - review portfolio guidance

## Findings

### Finding: Feedback routing is support-only and fits memory better than a docs-level canonical page

- Summary: The feedback-routing convention is a repeatable dogfooding procedure, not broad product doctrine. It belongs in memory/runbooks, where the repo keeps other local operator procedures with durable but narrow value.
- Evidence: `docs/contributor-playbook.md` used the page as a capture convention; `docs/lazy-discovery-measurements.md` already treats the usage ledger as the durable ordinary-use record; the file itself was a narrow routing rubric rather than a user-facing contract.
- Risk if unchanged: `docs/` keeps accumulating low-pull operational notes that are better owned as repo-local runbooks.
- Suggested action: Move the capture convention into `memory/runbooks/`, delete the docs copy, and keep `docs/` focused on broader contracts and review artifacts.
- Confidence: high
- Source: mixed
- Promotion target: memory
- Promotion trigger: immediate; the surface is low-pull and already has a better owner
- Post-remediation note shape: shrink

### Finding: Ordinary-use pull needs explicit legibility and familiarity-bias questions

- Summary: The usage ledger can already record which surface was chosen and why, but that is not enough to tell whether the choice was product-shaped or just insider-shaped.
- Evidence: the ledger contract tracked goal, used surface, skipped surface, and follow-up, but it did not require a fresh-agent legibility note or a self-hosting-bias note.
- Risk if unchanged: repeated skip patterns will remain difficult to interpret, and friction seen mainly by fresh or cheaper agents may stay underweighted.
- Suggested action: Add legibility and bias prompts to the usage ledger and review mode so future entries can separate product fit from repository familiarity.
- Confidence: medium-high
- Source: static-analysis
- Promotion target: memory
- Promotion trigger: immediate; the audit lane should preserve those questions in the checked-in contract
- Post-remediation note shape: retain

### Finding: Review guidance needed a dedicated ordinary-use pull mode

- Summary: The review portfolio covered context cost and generated-surface trust, but it did not have a dedicated lane for ordinary-use pull across Memory and Planning.
- Evidence: the review catalog had no mode that explicitly asked which surfaces are used, skipped, or low-pull in day-to-day work.
- Risk if unchanged: the same question could keep reappearing as ad hoc cleanup instead of a stable review lane.
- Suggested action: Add an `ordinary-use-pull` review mode that names low-pull scaffolding, outsider legibility, and self-hosting bias as explicit findings.
- Confidence: high
- Source: static-analysis
- Promotion target: canonical docs
- Promotion trigger: immediate; review modes should match recurring review questions
- Post-remediation note shape: retain

## Recommendation

- Promote: the memory move and the new ordinary-use pull review lane.
- Defer: broader surface consolidation until the next repeated pull signal appears.
- Dismiss: any pressure to turn this into telemetry or a general analytics system.

## Validation / Inspection Commands

- `rg -n "dogfooding-feedback|dogfooding-usage-ledger|ordinary-use-pull|outsider-legibility|self-hosting" docs memory tests`

## Drift Log

- 2026-04-16: Review created during the simplification tranche for issues `#120`, `#115`, `#116`, and `#114`.
