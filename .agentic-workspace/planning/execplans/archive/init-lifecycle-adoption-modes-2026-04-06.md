# Init Lifecycle and Adoption Modes

## Goal

- Create a dedicated durable doc for the root `init` lifecycle so clean install, conservative adopt, and high-ambiguity adopt behavior are easy to understand without forcing readers to reconstruct them from the README and report payloads.

## Non-Goals

- Redefine the root lifecycle commands.
- Replace package-local installer documentation.
- Duplicate the README in full.

## Active Milestone

- Status: completed
- Scope: define a dedicated `init` lifecycle/adoption doc that can be referenced from the README and maintainer surfaces without becoming redundant.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this completed plan and move the selective-adoption proof milestone into active execution.

## Blockers

- None.

## Touched Paths

- README.md
- docs/
- AGENTS.md
- docs/contributor-playbook.md
- docs/maintainer-commands.md
- tests/

Keep this as a scope guard, not a broad file inventory.

## Invariants

- The dedicated doc must stay shorter than the README and explain `init` modes without becoming a second root manual.
- Prompt semantics must remain aligned with the machine-readable lifecycle reports.
- Direct package CLIs stay documented as maintainable entrypoints, not replaced by the root flow.

## Validation Commands

- uv run python scripts/check/check_planning_surfaces.py

## Drift Log

- 2026-04-06: Parked from the planning-spec intake so the `init` lifecycle doc could be promoted after the active registry tranche.
- 2026-04-06: Milestone complete: the root README now points to a dedicated `init` lifecycle doc that explains the mode matrix and prompt requirements.

## Completion Criteria

- Readers can understand root `init` behavior without inferring it from implementation details.
- The README stays compact while lifecycle behavior has one canonical reference.
- The prompt-generation rules are explicit and stable.

## Follow-On Work Not Pulled In

- New lifecycle commands.
- Additional machine-readable schemas.
- Any package installer refactor beyond documentation references.