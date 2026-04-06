# Init Lifecycle and Adoption Modes

## Goal

- Create a dedicated durable doc for the root `init` lifecycle so clean install, conservative adopt, and high-ambiguity adopt behavior are easy to understand without forcing readers to reconstruct them from the README and report payloads.

## Non-Goals

- Redefine the root lifecycle commands.
- Replace package-local installer documentation.
- Duplicate the README in full.

## Deliverables

- A compact lifecycle doc covering install, adopt, and high-ambiguity adopt behavior.
- Clear guidance for machine-readable report expectations and handoff prompt generation.
- Explicit prompt requirement semantics: none, recommended, and required.
- A concise explanation of how the root lifecycle relates to direct package CLIs.

## Canonical Inputs

- README.md
- docs/design-principles.md
- docs/maturity-model.md
- docs/contributor-playbook.md
- docs/maintainer-commands.md
- docs/boundary-and-extraction.md
- current root CLI report shapes

## Active Milestone

- Status: planned
- Scope: define a dedicated `init` lifecycle/adoption doc that can be referenced from the README and maintainer surfaces without becoming redundant.
- Ready: not-started
- Blocked: none
- optional_deps: none

Keep one active milestone by default.

## Immediate Next Action

- Keep this parked until the module-registry tranche finishes, then promote it as the documentation-first lifecycle thread.

## Blockers

- None.

## Invariants

- The dedicated doc must stay shorter than the README and explain `init` modes without becoming a second root manual.
- Prompt semantics must remain aligned with the machine-readable lifecycle reports.
- Direct package CLIs stay documented as maintainable entrypoints, not replaced by the root flow.

## Validation Commands

- uv run python scripts/check/check_planning_surfaces.py

## Drift Log

- 2026-04-06: Parked from the planning-spec intake so the `init` lifecycle doc can be promoted after the active registry tranche.

## Touched Paths

- README.md
- docs/
- AGENTS.md
- docs/contributor-playbook.md
- docs/maintainer-commands.md
- tests/

Keep this as a scope guard, not a broad file inventory.

## Validation

- Verify the doc explains the three adopt/install modes and prompt requirements cleanly.
- Check the README can defer to the dedicated doc instead of repeating lifecycle detail.
- Ensure package CLIs are still described as direct, maintainable entrypoints.

## Completion Criteria

- Readers can understand root `init` behavior without inferring it from implementation details.
- The README stays compact while lifecycle behavior has one canonical reference.
- The prompt-generation rules are explicit and stable.

## Follow-On Work Not Pulled In

- New lifecycle commands.
- Additional machine-readable schemas.
- Any package installer refactor beyond documentation references.
