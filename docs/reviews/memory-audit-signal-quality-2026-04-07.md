# Review: Memory Audit Signal Quality

## Goal

- Review whether the current memory audit lane is producing compact, high-signal maintenance guidance after recent repo dogfooding.

## Scope

- `uv run agentic-memory-bootstrap doctor --target .`
- `uv run python scripts/check/check_memory_freshness.py`
- `memory/` note set involved in current overlap findings
- `packages/memory/src/repo_memory_bootstrap/_installer_memory.py`

## Non-Goals

- Do not activate new work in `TODO.md` or create an execplan.
- Do not perform broad memory-note consolidation in this review artifact.
- Do not review the planning package or unrelated repo surfaces.

## Review Method

- Commands used: `uv run agentic-memory-bootstrap doctor --target .`, `uv run python scripts/check/check_memory_freshness.py`
- Evidence sources: current doctor output, current memory notes under `memory/`, and the overlap-audit implementation in `packages/memory/src/repo_memory_bootstrap/_installer_memory.py`

## Findings

### Finding: Overlap audit still over-reports adjacent durable notes

- Summary: The overlap audit is improved, but it still flags several adjacent durable notes that appear to have distinct primary homes and explicit separation, especially around root-owned installed-system history and planning/memory package context.
- Evidence: Current `doctor` output still emits overlap warnings across `memory/decisions/installed-system-consolidation-2026-04-05.md`, `memory/decisions/path-consolidation-agentic-workspace-2026-04-05.md`, `memory/decisions/foundation-stability-2026-04-05.md`, and `memory/decisions/workspace-orchestrator-ownership-ledger-2026-04-05.md`, plus the package-context domain notes. Recent fixes already reduced clear false positives by reclassifying customised seed notes and teaching the audit to honor explicit note-to-note references, which suggests the remaining warnings are coming from the heuristic still relying heavily on shared terminology within one subsystem.
- Risk if unchanged: Maintainers may start ignoring overlap findings entirely, which weakens the audit's value when a real multi-home drift problem appears.
- Suggested action: Revisit the overlap heuristic as planned work, likely by adding stronger structural signals such as section-shape weighting, note-family exclusions for accepted sibling decision notes, or a way for manifest metadata to declare intentional adjacent homes.
- Confidence: high
- Source: mixed
- Promotion target: `ROADMAP.md`
- Promotion trigger: Promote when the overlap audit keeps producing repeated low-signal warnings during normal repo maintenance after the current heuristic fixes.

### Finding: Installed-system history is still fragmented across too many durable notes

- Summary: The repo still carries closely related durable history across several decision notes and two package-context notes, which makes the note set harder to maintain even when the audit is behaving correctly.
- Evidence: The remaining warnings cluster around one story: root-owned installed systems, `.agentic-workspace/` path consolidation, foundation stability, and workspace ownership. Those are adjacent but not identical decisions, and the repo now also has repo-owned skills for the repeatable checks. That leaves the durable note set looking denser than it likely needs to be for restart efficiency.
- Risk if unchanged: Contributors will spend time re-reading or maintaining multiple near-neighbor notes to recover one operational story, raising restart cost and making future note consolidation harder.
- Suggested action: Run a targeted follow-up consolidation pass over the installed-system decision family and the two package-context notes, deciding whether some of that material should collapse into fewer durable notes with narrower package-context stubs.
- Confidence: medium
- Source: friction-confirmed
- Promotion target: `ROADMAP.md`
- Promotion trigger: Promote when maintainers repeatedly touch or cross-reference the same installed-system decision family during ordinary memory/planning package work.

## Recommendation

- Promote: Neither finding yet. Keep this review as capture only until repeated maintenance confirms which follow-up is worth queueing.
- Defer: Both findings, pending another normal maintenance cycle that confirms whether the remaining overlap warnings are still noisy or whether the note family keeps imposing restart cost.
- Dismiss: None.

## Validation / Inspection Commands

- `uv run agentic-memory-bootstrap doctor --target .`
- `uv run python scripts/check/check_memory_freshness.py`

## Drift Log

- 2026-04-07: Review created after dogfooding the memory audit lane through repo-local maintenance and package fixes.
