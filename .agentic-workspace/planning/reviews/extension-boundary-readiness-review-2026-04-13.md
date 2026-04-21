# Extension Boundary Readiness Review

## Goal

- Check whether the current extension-boundary doc still reflects the real first-party module contract and whether any readiness gate is ready to move.

## Scope

- `docs/extension-boundary.md`
- `docs/module-capability-contract.md`
- `docs/ecosystem-roadmap.md`
- related archived extension-boundary and module-contract execplans

## Non-Goals

- Design a third-party plugin API.
- Open the extension boundary.
- Add new module capabilities or lifecycle behavior.

## Review Mode

- Mode: `contract-integrity`
- Review question: Does the current extension-boundary statement still match the real first-party contract and current evidence, or is it now either stale optimism or stale blockage?
- Default finding cap: 3 findings
- Inputs inspected first: `docs/extension-boundary.md`, `docs/module-capability-contract.md`, `docs/ecosystem-roadmap.md`, archived extension-boundary/module-contract execplans

## Review Method

- Commands used:
  - `rg -n "extension boundary|plugin|first-party|module contract" docs packages src -g "*.md" -g "*.py"`
- Evidence sources:
  - canonical docs
  - archived execplans for the original boundary-design and module-contract tranches

## Findings

### Finding: Readiness gates lacked a current evidence snapshot

- Summary: The extension-boundary doc named the right gates, but it did not say which gates were currently blocked versus merely unproven, so the page risked becoming a static caution statement instead of a maintained boundary.
- Evidence: `docs/extension-boundary.md` listed five readiness gates but no current-status read for any gate, while the surrounding contract docs already show materially different evidence strength across those gates.
- Risk if unchanged: Contributors would have to reconstruct whether the boundary is closed because of one missing use-case, several still-unproven lifecycle assumptions, or simple documentation staleness.
- Suggested action: Add a current readiness snapshot to `docs/extension-boundary.md` that records each gate's present status and what evidence would move it.
- Confidence: high
- Source: static-analysis
- Promotion target: canonical docs
- Promotion trigger: immediate; the gap is documentation integrity, not future feature work
- Post-remediation note shape: retain

### Finding: The boundary is still correctly closed, but only gate 1 shows partial progress

- Summary: The first-party module contract has become substantially more explicit, but the repo still lacks proof for public-contract wording, broader selective-adoption evidence, non-core lifecycle expectations, and a compelling external-use case.
- Evidence: `docs/module-capability-contract.md` still describes the contract as first-party-only internal structure, and `docs/ecosystem-roadmap.md` still treats external extension as unsupported. No inspected surface provides repeated real external-use pressure or non-core lifecycle proof.
- Risk if unchanged: Maintainers could misread improved first-party metadata as a reason to start plugin work early, or wrongly assume the boundary doc is conservative only by inertia.
- Suggested action: Keep the boundary closed and state that current evidence explicitly in the canonical boundary doc rather than promoting more extension work now.
- Confidence: high
- Source: mixed
- Promotion target: canonical docs
- Promotion trigger: immediate; the doc should state the current read instead of leaving it implicit
- Post-remediation note shape: retain

## Recommendation

- Promote: no new roadmap candidate; apply the documentation clarification directly
- Defer: reopen extension-boundary review only when a gate materially moves or real external-use pressure appears
- Dismiss: any pressure to infer a public extension contract purely from the stronger first-party module metadata

## Validation / Inspection Commands

- `rg -n "extension boundary|plugin|first-party|module contract" docs packages src -g "*.md" -g "*.py"`

## Drift Log

- 2026-04-13: Review created to decide whether the extension-boundary candidate should become new work or collapse into a documentation-integrity refresh.
