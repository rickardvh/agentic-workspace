# Review: General Agent Workflow

## Goal

- Review the general quality of this repo's agent workflow loop across planning, memory, and installed-contract maintenance.

## Scope

- Root planning surfaces
- Root memory audit surfaces
- Maintainer workflow guidance
- Current review artifacts under `docs/reviews/`

## Non-Goals

- Do not promote any findings into active work.
- Do not implement new fixes from this review.
- Do not review unrelated product areas outside repo workflow and feedback handling.

## Review Method

- Commands used: `uv run python scripts/check/check_planning_surfaces.py`, `uv run python scripts/check/check_memory_freshness.py`, `uv run agentic-memory-bootstrap doctor --target .`
- Evidence sources: current repo contract in `AGENTS.md`, current planning and memory health outputs, `ROADMAP.md`, and recent review artifacts

## Findings

### Finding: The repo now has a viable closed-loop dogfooding workflow

- Summary: The repo has the core pieces needed for agent-driven feedback to survive and be handled cleanly: checked-in planning, checked-in memory, review artifacts, package-local validation, and explicit repo guidance about routing dogfooding signals into tracked surfaces.
- Evidence: `check_planning_surfaces.py` reports no planning drift; `check_memory_freshness.py` reports no structural freshness failures; review artifacts now exist under `docs/reviews/`; and `AGENTS.md` explicitly routes dogfooding findings into planning or memory rather than chat-only residue.
- Risk if unchanged: Low. The current risk is mostly behavioral drift rather than missing workflow structure.
- Suggested action: Keep using `docs/reviews/` for bounded review passes and preserve the rule that findings enter planning or memory before they become product work.
- Confidence: high
- Source: friction-confirmed
- Promotion target: none
- Promotion trigger:

### Finding: The promotion threshold from captured signal to planned work is still underspecified

- Summary: The repo now captures findings better than before, but it still does not make it clear enough when repeated dogfooding or repeated review findings should graduate into `ROADMAP.md` candidate work.
- Evidence: Recent work surfaced real product issues and prompted mid-stream clarification of the dogfooding rule in `AGENTS.md`. The new review artifacts capture follow-up candidates, but both remain intentionally deferred because the repo still lacks a crisp promotion threshold beyond maintainer judgment and repetition.
- Risk if unchanged: Agents may either over-promote noisy findings into planning or keep deferring legitimate product gaps because no explicit activation rule tells them when capture has become enough evidence.
- Suggested action: Add a small canonical promotion rule for repeated dogfooding findings, likely in planning or maintainer guidance, stating when recurring review findings or repeated repo-local friction should be considered a roadmap candidate.
- Confidence: medium
- Source: mixed
- Promotion target: `ROADMAP.md`
- Promotion trigger: Promote when the same product-level deficiency is captured more than once across review artifacts or repeated repo maintenance without a clear activation rule.

### Finding: Memory overlap audit remains the loudest unresolved maintenance signal

- Summary: Across the current workflow surfaces, the memory overlap audit is still the noisiest unresolved source of maintainer friction.
- Evidence: `doctor --target .` still emits a reduced but persistent cluster of overlap findings around installed-system and package-context notes, while planning and freshness checks are otherwise clean. A narrower review already captured this under `docs/reviews/memory-audit-signal-quality-2026-04-07.md`, and the general workflow pass confirms it is the main remaining workflow-quality hotspot.
- Risk if unchanged: This one audit can dominate maintainer attention and weaken trust in the feedback loop if it keeps surfacing more noise than useful prioritization.
- Suggested action: Keep this as the main candidate for future product follow-up if repeated maintenance continues to hit the same warnings.
- Confidence: high
- Source: mixed
- Promotion target: `ROADMAP.md`
- Promotion trigger: Promote when another ordinary maintenance cycle still ends with the overlap audit as the dominant unresolved workflow signal.

## Recommendation

- Promote: None yet.
- Defer: The promotion-threshold rule and the memory overlap-audit follow-up.
- Dismiss: None.

## Validation / Inspection Commands

- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run python scripts/check/check_memory_freshness.py`
- `uv run agentic-memory-bootstrap doctor --target .`

## Drift Log

- 2026-04-07: Review created after repo-level dogfooding of planning, memory, and review capture workflows.

## Status Footer

- Finding 1 (Repo now has viable closed-loop dogfooding workflow): no promotion needed; documents existing good state.
- Finding 2 (Promotion threshold from captured signal to planned work): implemented via the canonical threshold rule in `docs/reviews/README.md` and matching roadmap wording.
- Finding 3 (Memory overlap audit remains the loudest unresolved signal): deferred pending next maintenance cycle that confirms whether overlap audit remains noisy.

Review ready for deletion once Finding 3 result is known.
