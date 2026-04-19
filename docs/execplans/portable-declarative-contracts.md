# Portable Declarative Contracts and Agent-Native Alignment

Move toward declarative portable contract sources and align repo planning schemas with agent-native structures to reduce startup cost and reasoning depth.

## Goal

- Define a machine-readable "Cold-Start" Protocol for immediate agent orientation.
- Align `execplan` and `summary` schemas with agent-native planning structures.
- Inventory and extract lifecycle truths from Python into declarative manifests.

## Non-Goals

- Inventing a new workflow language or generic automation system.
- Replacing human-legible documentation entirely with JSON.

## User Review Required

> [!IMPORTANT]
> This plan will reshape the structured output of `agentic-workspace summary` and `report`. If external tools rely on the specific existing JSON schema, they may need updates.

## Intent Continuity

- Larger intended outcome: Consolidate agentic-workspace CLI and operating model by aligning repository planning contracts with agent-native reasoning structures.
- This slice completes the larger intended outcome: no
- Continuation surface: docs/execplans/portable-declarative-contracts.md
- Parent lane: Portable declarative contracts and agent-native alignment

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: docs/execplans/portable-declarative-contracts.md
- Activation trigger: Completion of the first implementation slice.

## Iterative Follow-Through

- What this slice enabled: High-signal cold-start orientation and machine-readable startup protocol.
- Intentionally deferred: Extraction of broader lifecycle logic (beyond startup) into the manifest.
- Discovered implications: Need for stricter `TODO.md` and `execplan` parsing to ensure high-quality structured output.
- Proof achieved now: `agentic-workspace report --startup` returns a valid block.
- Validation still needed: Verified integration with a simulated fresh agent.
- Next likely slice: Aligning `summary` fields and extracting more lifecycle truth.

## Delegated Judgment

- Requested outcome: A working "Cold-Start" protocol and aligned summary schemas that reduce agent startup friction.
- Hard constraints: Maintain zero-warning repository health; avoid breaking existing human-legible surfaces.
- Agent may decide locally: Local implementation details of CLI flags and JSON structures.
- Escalate when: Proposed changes would break backward compatibility in a way that blocks other active lanes.

## Active Milestone

- Status: in-progress
- Scope: Define protocol in manifest, implement --startup flag, and update summary fields.
- Ready: ready
- Blocked: no

## Immediate Next Action

- Implement aligned planning fields in `agentic-workspace summary`.

## Blockers

- None.

## Touched Paths

- src/agentic_workspace/cli.py
- .agentic-workspace/planning/agent-manifest.json
- packages/planning/src/repo_planning_bootstrap/installer.py

## Invariants

- `agentic-workspace report --startup` must always return high-signal orientation context.
- Schema changes must be backward-compatible or explicitly noted as breaking.

## Contract Decisions To Freeze

- The `startup-report/v1` schema is now the canonical cold-start entrypoint.

## Open Questions To Close

- Should we also extract `setup` and `init` lifecycle logic into the manifest in this slice? (No, deferred to next slice).

## Validation Commands

- uv run agentic-workspace report --startup --format json
- make maintainer-surfaces

## Completion Criteria

- `agentic-workspace report --startup` returns a valid, high-signal JSON block.
- `agentic-workspace summary` includes Requested Outcome, Hard Constraints, and Escalation Boundaries.
- Zero warnings from `make maintainer-surfaces`.

## Execution Summary

- Outcome delivered: 
- Validation confirmed: 
- Follow-on routed to: 
- Resume from: 

## Drift Log

- 2026-04-19: Initial plan created for portable contracts and agent-native alignment.
- 2026-04-19: Aligned plan with TEMPLATE.md for better tool integration.
- 2026-04-19: Filled out required sections to satisfy planning checker.
