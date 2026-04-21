# Memory Collaboration Safety

## Goal

- Strengthen the installed Agentic Memory contract for larger git-heavy teams by making `.agentic-workspace/memory/repo/current/` explicitly weak-authority, easier to compress or replace, and less likely to duplicate durable memory notes under concurrent edits.

## Non-Goals

- Redesign the planning package in this tranche.
- Add a new memory taxonomy or new top-level memory directories.
- Make memory depend on the planning package for safety checks.

## Active Milestone

- Status: completed
- Scope: tightened current-note manifest metadata, docs, templates, and freshness audits around weak-authority current-state notes, one-fact-one-home discipline, and duplication pressure against durable memory notes.
- Ready: ready
- Blocked: none
- optional_deps: none

Keep one active milestone by default.

## Immediate Next Action

- Promote the cross-module collaboration contract tranche once package-facing write-authority rules are bounded.

Keep exactly one immediate action by default; avoid multi-step mini-plans here.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- .agentic-workspace/planning/execplans/
- memory/
- scripts/check/
- packages/memory/

Keep this as a scope guard, not a broad file inventory.

## Invariants

- Memory must remain planning-agnostic and selectively adoptable.
- Durable facts should stay in canonical memory notes or checked-in docs rather than migrating into `.agentic-workspace/memory/repo/current/`.
- Current-context notes must stay compact, optional, and safe to compress or remove.
- The package payload, checker, and doctor guidance must stay aligned.

Keep invariants contract-shaped and brief.

## Validation Commands

- uv run pytest packages/memory/tests/test_installer.py
- make check-memory

## Completion Criteria

- The shipped memory manifest no longer presents `.agentic-workspace/memory/repo/current/` notes as canonical durable authority.
- Memory docs and starter notes explain weak-authority current-state handling and one-fact-one-home expectations more explicitly.
- The freshness audit warns about current-note authority drift and duplicate durable-note pressure.
- Package tests and root checks stay green after the tightened contract.

## Drift Log

- 2026-04-06: Activated the memory collaboration-safety tranche from the collaboration-safe roadmap candidate set.
- 2026-04-06: Completed the tranche after aligning manifests, docs, templates, doctor guidance, and the strict freshness audit.