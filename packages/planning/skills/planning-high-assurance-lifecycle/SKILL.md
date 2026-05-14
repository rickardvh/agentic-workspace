---
name: planning-high-assurance-lifecycle
description: Preserve intent, decomposition, assurance, delegation, proof, and closeout for broad or high-assurance planning work.
---

# Planning High-Assurance Lifecycle

Use this skill when work is broad, multi-lane, high-assurance, cross-boundary, or likely to grow beyond an initially bounded slice.

## Route

1. Classify the work shape before editing: direct task, bounded execplan, decomposition lane, epic, review, or recovery.
2. If the work is broad or cross-boundary, run the planning CLI to create or promote a checked-in planning artifact before implementation.
3. Tighten intent, non-goals, touched paths, proof, delegation posture, and closeout expectations until a weaker worker could implement a bounded slice mechanically.
4. Record the assurance and delegation decision before implementation continues.
5. Execute one bounded slice at a time; update the active execplan or decomposition when scope, proof, or residue changes.
6. Promote dogfooding findings or review findings to planning records before implementing them.
7. Close out with proof, intent satisfaction, durable residue routing, and `planning close-item` or `archive-plan` as appropriate.

## Required Surfaces

- `agentic-workspace start --target . --task "<task>" --format json`
- `agentic-workspace summary --target . --format json`
- `agentic-workspace planning new-plan|promote-to-plan|delegation-decision|close-item|archive-plan --target . --format json`
- `agentic-workspace proof --target . --changed <paths> --format json`

## Stop Conditions

Stop and tighten planning instead of coding when:

- intent satisfaction cannot be checked from the current artifact
- the task spans multiple modules, targets, or issue lanes without decomposition
- validation proof is unclear or too broad for the claimed slice
- delegation would be cheap and safe but no handoff packet exists
- implementation exposes new durable residue without a routed owner

## Output Contract

End with:

- active planning artifact
- slice completed or blocker
- intent satisfaction status
- proof run
- delegation decision or reason skipped
- planning mutations performed through CLI
- follow-up issues or planning items created
