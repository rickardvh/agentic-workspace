# Memory Trust And Usefulness First Slice

## Goal

- Turn the existing Memory manifest, routing, freshness, and remediation metadata into a compact trust/usefulness/cleanup contract that makes Memory cheaper to inspect and safer to trust.

## Non-Goals

- Do not invent a new memory store or moderation tree.
- Do not require heavy annotation on every note.
- Do not widen this slice into fully automatic capture/routing ergonomics if reporting alone still leaves that gap open.
- Do not delete notes automatically.

## Intent Continuity

- Larger intended outcome: make Agentic Memory materially trustworthy, cheap to inspect, and visibly useful in ordinary repo work rather than conceptually sound but easy to bypass.
- This slice completes the larger intended outcome: no
- Continuation surface: `ROADMAP.md` candidate lane `Memory trust, usefulness, and cleanup ergonomics`

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: `ROADMAP.md` candidate lane `Memory trust, usefulness, and cleanup ergonomics`
- Activation trigger: promote another bounded slice if ordinary-work dogfooding still shows Memory is not the cheap path after trust/usefulness reporting improves.

## Iterative Follow-Through

- What this slice enabled: Memory report can carry explicit note trust states, cleanup pressure, and a bounded usefulness audit without broad raw-note inspection.
- Intentionally deferred: low-friction capture/routing changes beyond reporting and trust-state surfacing.
- Discovered implications: the current manifest already carries most of the needed evidence and remediation metadata; the product gap is mainly making that metadata operational and easy to inspect.
- Proof achieved now: one live repo can see which notes are supported, questionable, stale, or elimination-biased through the compact memory report.
- Validation still needed: ordinary-work dogfooding to see whether the new trust/usefulness report materially reduces memory bypass.
- Next likely slice: if bypass still dominates, tighten the low-friction routing/capture path rather than widening trust-state rules again.

## Delegated Judgment

- Requested outcome: ship the smallest trust/usefulness reporting tranche that closes the trust/cleanup issues before widening into broader routing ergonomics.
- Hard constraints: reuse existing manifest/routing/remediation metadata where possible, keep the module report compact, and avoid turning reporting into a second editable authority surface.
- Agent may decide locally: the exact trust-state model, the usefulness-audit summary shape, and which existing doctor/route/promotion signals are worth lifting into the compact report.
- Escalate when: the smallest implementation would require a new manifest file, invasive note rewrites across the whole tree, or a broad redesign of memory routing.

## Active Milestone

- Status: completed
- Scope: add note trust-state classification plus usefulness/cleanup summaries to the memory module report, update the package docs/tests, dogfood it on this repo, and then narrow the remaining lane honestly.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this completed slice, close the trust/cleanup issues it resolves, and leave only the low-friction Memory routing/capture follow-on active in the roadmap.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- docs/execplans/memory-trust-and-usefulness-first-slice-2026-04-17.md
- packages/memory/README.md
- packages/memory/bootstrap/memory/manifest.toml
- packages/memory/src/repo_memory_bootstrap/installer.py
- packages/memory/tests/test_installer.py

## Invariants

- Memory manifest metadata remains the canonical source of note role, stale triggers, and remediation hints.
- The compact report remains derived and read-only.
- Planning still owns active task state; memory trust/usefulness reporting must not absorb that role.

## Contract Decisions To Freeze

- The first evidence-backed note model will treat existing manifest anchors as evidence rather than introducing a second parallel evidence field immediately.
- Trust-state reporting should be note-shaped and bounded, not a general telemetry system.
- Usefulness reporting should prefer routing and remediation evidence over raw note-count metrics.

## Open Questions To Close

- None for this slice.

## Validation Commands

- uv run pytest packages/memory/tests/test_installer.py -q
- uv run python scripts/check/check_memory_freshness.py
- uv run agentic-memory-bootstrap report --target . --format json
- uv run agentic-memory-bootstrap route-report --target . --format json
- uv run agentic-memory-bootstrap promotion-report --target . --mode remediation --format json
- uv run agentic-planning-bootstrap upgrade --target .
- uv run agentic-memory-bootstrap upgrade --target .
- uv run python scripts/check/check_source_payload_operational_install.py

## Required Tools

- uv
- gh

## Completion Criteria

- The memory module report exposes explicit note trust states and cleanup pressure.
- The memory module report exposes a bounded usefulness audit based on existing routing/remediation surfaces.
- The package docs explain the trust-state model using existing manifest metadata.
- The roadmap lane is narrowed honestly after dogfooding the new report on this repo.

## Execution Summary

- Outcome delivered: `agentic-memory-bootstrap report` now projects note trust states and a bounded usefulness audit from existing manifest/routing/remediation metadata, with explicit cleanup pressure for questionable, stale, and elimination-biased notes.
- Validation confirmed: `uv run pytest packages/memory/tests/test_installer.py -q`; `uv run python scripts/check/check_memory_freshness.py`; `uv run agentic-memory-bootstrap report --target . --format json`; `uv run agentic-memory-bootstrap route-report --target . --format json`; `uv run agentic-memory-bootstrap promotion-report --target . --mode remediation --format json`; `uv run agentic-planning-bootstrap upgrade --target .`; `uv run agentic-memory-bootstrap upgrade --target .`; `uv run python scripts/check/check_source_payload_operational_install.py`.
- Follow-on routed to: `ROADMAP.md` candidate lane `Low-friction Memory routing and capture`.
- Resume from: no further action in this plan; promote the remaining low-friction Memory routing/capture lane when ready.

## Drift Log

- 2026-04-17: Promoted from the final remaining roadmap lane after the native candidate-lane planning slice closed.
- 2026-04-17: Landed trust-state/usefulness reporting in the memory module report, dogfooded it on this repo, and narrowed the remaining Memory roadmap work to low-friction routing/capture follow-through.
