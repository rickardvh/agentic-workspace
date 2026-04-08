# Review: Repo Workflow Signal Quality

## Goal

- Review whether the repo's current planning, memory, and installed-contract workflow loop is producing high-signal operational feedback during normal dogfooding.

## Scope

- Root planning surfaces
- Root memory hygiene and doctor output
- Installed-contract refresh behavior for planning and memory
- Existing review artifact from `docs/reviews/memory-audit-signal-quality-2026-04-07.md`

## Non-Goals

- Do not activate new work in `TODO.md` or create an execplan.
- Do not perform another implementation pass in this review.
- Do not review product direction outside the current agent-workflow and repo-maintenance loop.

## Review Method

- Commands used: `uv run python scripts/check/check_planning_surfaces.py`, `uv run python scripts/check/check_memory_freshness.py`, `uv run agentic-memory-bootstrap doctor --target .`
- Evidence sources: current root planning surfaces, current memory notes, current doctor output, and recent review artifact(s) under `docs/reviews/`

## Findings

### Finding: The repo-level feedback loop is now structurally present and usable

- Summary: The repo has the right surfaces to turn dogfooding into durable feedback instead of chat residue: planning is clean, review artifacts exist, memory audits are active, and the agent contract now explicitly routes product signals back into checked-in planning or memory.
- Evidence: `check_planning_surfaces.py` reports no drift warnings; review artifacts now exist under `docs/reviews/`; `AGENTS.md` explicitly says dogfooding signals should enter the checked-in planning or memory loop; and the recent memory-package fixes were validated end-to-end through package tests plus repo-level upgrades.
- Risk if unchanged: Low. The main risk here is drift in usage discipline rather than missing infrastructure.
- Suggested action: Keep using review artifacts for bounded future-work discovery and resist falling back to chat-only “remember this next time” behavior.
- Confidence: high
- Source: friction-confirmed
- Promotion target: none
- Promotion trigger:

### Finding: Repo dogfooding still exposes one unresolved product-vs-repo boundary

- Summary: The repo now has a better feedback loop, but there is still ambiguity about when a repeated repo-local maintenance pain should stay as captured feedback versus become active product work. The overlap-audit issue is the clearest live example.
- Evidence: Recent work repeatedly crossed from repo-local maintenance into package changes because the repo exposed real product deficiencies, but the repo contract had to be corrected mid-stream to say those signals should enter planning or memory first. The remaining `doctor` warnings show one unresolved class of problem that is still captured but not yet clearly promoted.
- Risk if unchanged: Agents may oscillate between two bad modes: over-eager direct fixes that bypass the planning loop, or under-reacting to repeated product friction because no promotion threshold is explicit enough.
- Suggested action: Add a small canonical rule, likely in planning or maintainer guidance, for when repeated review findings or repeated dogfooding friction should graduate from review-memory capture into `ROADMAP.md` candidate work.
- Confidence: medium
- Source: mixed
- Promotion target: `ROADMAP.md`
- Promotion trigger: Promote when the same repo-local product deficiency is captured more than once across review artifacts or repeated maintenance sessions without a clear activation rule.

## Recommendation

- Promote: Not yet.
- Defer: The promotion-threshold question, pending one more repeated case or a clearer maintainer pain point.
- Dismiss: None.

## Validation / Inspection Commands

- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run python scripts/check/check_memory_freshness.py`
- `uv run agentic-memory-bootstrap doctor --target .`

## Drift Log

- 2026-04-07: Review created after dogfooding the planning-memory-review loop through repo maintenance and package refinement.

## Status Footer

- Finding 1 (Repo dogfooding still exposes one unresolved product-vs-repo boundary): implemented via the canonical threshold rule in `docs/reviews/README.md` and matching roadmap wording.
