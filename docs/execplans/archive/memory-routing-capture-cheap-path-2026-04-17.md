# Memory Routing Capture Cheap Path

## Goal

- Make Agentic Memory cheaper to consult and cheaper to update during ordinary work by tightening one real routing gap, surfacing the cheapest useful note-update path, and proving the result through compact routing fixtures and repo dogfooding.

## Non-Goals

- Do not turn Memory into the owner of general skill routing or replace `agentic-workspace skills`.
- Do not broaden this slice into a new memory store, telemetry system, or active-task tracker.
- Do not create a second authority surface parallel to the manifest.

## Intent Continuity

- Larger intended outcome: make Memory a cheap habitual path instead of a conceptually correct but easier-to-bypass optional layer.
- This slice completes the larger intended outcome: yes
- Continuation surface: none

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Iterative Follow-Through

- What this slice should enable: route-report and sync-memory should point at concrete cheap-path proof instead of carrying stale non-memory misses or forcing broad note inspection.
- Intentionally deferred: any broader redesign of task-to-skill recommendation outside Memory.
- Proof to achieve now: one live repo can see a compact cheap update path from changed files, and route-report shows real Memory fixtures rather than only stale or externalized feedback residue.

## Delegated Judgment

- Requested outcome: land the smallest product-level routing/capture slice that closes the final roadmap lane honestly.
- Hard constraints: keep package boundaries explicit, prefer fixture-backed proof, and do not solve non-memory routing gaps by teaching Memory to own unrelated surfaces.
- Agent may decide locally: the exact compact summary shape for sync output, how to classify externalized routing-feedback cases, and which one or two work shapes should become fixtures.
- Escalate when: closing the lane would require a new module, broad natural-language intent routing inside Memory, or repo-local-only workarounds with no reusable package value.

## Active Milestone

- Status: completed
- Scope: add a cheap capture/update summary to sync-memory, keep route-report honest about non-memory/externalized misses, add fixture-backed proof for one or two real Memory work shapes, dogfood the result, and close the final roadmap lane.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this completed slice, close `#98`, and leave the roadmap empty until a genuinely new candidate appears.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- docs/execplans/memory-routing-capture-cheap-path-2026-04-17.md
- packages/memory/README.md
- packages/memory/src/repo_memory_bootstrap/cli.py
- packages/memory/src/repo_memory_bootstrap/installer.py
- packages/memory/tests/test_installer.py
- memory/current/routing-feedback.md

## Invariants

- Memory remains optional and selectively adoptable.
- `agentic-workspace skills` remains the owner of generic skill discovery and recommendation.
- Memory routing/capture outputs remain derived and advisory, not a second editable task system.

## Contract Decisions To Freeze

- Route-report should distinguish live memory misses from non-memory or already-externalized misses so usefulness proof stays honest.
- `sync-memory` should expose the cheapest useful note-update path directly instead of forcing broad action-list inspection.
- Fixture-backed routing proof should be preferred over prose-only confidence claims.

## Open Questions To Close

- None for this slice.

## Validation Commands

- uv run pytest packages/memory/tests/test_installer.py -q
- uv run agentic-memory-bootstrap route-report --target . --format json
- uv run agentic-memory-bootstrap sync-memory --target . --files packages/memory/src/repo_memory_bootstrap/installer.py packages/memory/tests/test_installer.py --format json
- uv run python scripts/check/check_memory_freshness.py
- uv run agentic-planning-bootstrap upgrade --target .
- uv run agentic-memory-bootstrap upgrade --target .
- uv run python scripts/check/check_source_payload_operational_install.py

## Required Tools

- uv
- gh

## Completion Criteria

- `sync-memory` exposes a compact cheapest-useful-update summary for changed files.
- `route-report` can keep externalized/non-memory misses from distorting the remaining Memory cheap-path proof.
- Fixture-backed routing proof exists for at least one or two common Memory work shapes.
- Repo dogfooding shows the final roadmap lane is honestly complete, or the leftover gap is narrowed into a distinct new candidate.

## Execution Summary

- Outcome delivered: `sync-memory` now emits a compact `sync_summary` with the cheapest useful note-update path, `route-report` now separates externalized non-memory misses from live Memory misses, directory-style `/**` manifest patterns now match nested files as intended, and route trimming now prefers the smallest real working set over starter examples, version markers, and broad historical decisions.
- Validation confirmed: `uv run pytest packages/memory/tests/test_installer.py -q`; `uv run agentic-memory-bootstrap route-report --target . --format json`; `uv run agentic-memory-bootstrap sync-memory --target . --files packages/memory/src/repo_memory_bootstrap/installer.py packages/memory/tests/test_installer.py --format json`; `uv run python scripts/check/check_memory_freshness.py`; `uv run agentic-planning-bootstrap upgrade --target .`; `uv run agentic-memory-bootstrap upgrade --target .`; `uv run python scripts/check/check_source_payload_operational_install.py`.
- Dogfooding result: this repo now carries two passing live routing fixtures, zero live Memory missed-note cases, and a compact package-context sync summary that points directly at `memory/domains/memory-package-context.md`.
- Follow-on routed to: none.
- Resume from: no further action in this plan; reopen planning only if new dogfooding shows a distinct fresh Memory cheap-path gap.

## Drift Log

- 2026-04-17: Promoted from the final remaining roadmap lane after the Memory trust/usefulness/reporting tranche closed.
- 2026-04-17: Fixed `/**` manifest matching for nested files, added compact sync summaries, externalized non-memory skill-routing residue, checked in two live repo routing fixtures, and reduced the routed working set to the intended three-note default for the main dogfood cases.
