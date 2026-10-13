# Advisory knowledge

## Status

Active advisory recurrence cues. Current instructions and owner requests control actions.

## Scope

Planning continuity, early decomposition judgment and independent PR review.

## Load when

- Work may benefit from decomposition or must continue an existing Planning owner.
- An implementation actor reports fixes or readiness for PR review.

## Review when

- Startup, planning-work intake, native Planning or PR-custody instructions change.

## Failure signals

- A broad task is treated as automatically requiring a plan, or existing issues automatically waive the need to judge decomposition.
- An owned next task is classified as unrelated because older closeout residue remains.
- An implementation actor exercises or directs independent reviewer authority.

## Rule or lesson

### Failure: broad planned work bypasses active planning

Judge decomposition and continuity before implementation when they would materially help. Reuse an adequate existing issue or related owner; otherwise follow workspace-startup and planning-work intake to create/select native Planning custody. A broad task or absent plan alone does not mandate a plan, summary command or todo promotion. Direct work remains available under current policy.

### Failure: selected plan blocks its next owned task

Explicitly relate the current task to its existing Planning owner through the returned selection/relation request. Compare its actual intended outcome and declared issue references with current work. Preserve pending closeout obligations separately; do not invent another plan or worktree to escape them. Use current native Planning requests, never retired route-decision or summary fields.

### Failure: implementation agent occupies the review decision namespace

An implementation actor reports fixes and readiness for independent review. It does not review or approve its own PR, post reviewer decision markers, or spawn/direct its reviewer. Follow the repository PR-custody instruction; only an externally initiated eligible reviewer owns independent review. This boundary also applies while fixing a stack.

## Verify

- Read `.agentic-workspace/skills/workspace-startup/SKILL.md` and `.agentic-workspace/planning/skills/planning-work/references/intake.md`.
- Compare selected task/owner relations with `src/core/src/modules/planning/native_planning.rs`.
- Read `.agentic-workspace/instructions/github-pr-review.md` before any reviewer action.

## Provenance

The dated lessons confirmed on 2026-04-26 (#322), 2026-08-11 (#2277) and 2026-08-13 remain [verbatim in source history](https://github.com/rickardvh/agentic-workspace/blob/78e5ef6ba92e434ea144d9d508e25e7f898249f7/.agentic-workspace/memory/repo/mistakes/recurring-failures.md). They record former interfaces and rationale; their commands and the bootstrap template are historical evidence. This revision preserves all three lessons' useful intent without projecting those interfaces as current advice.

## Last confirmed

2026-10-13: compared all three current lessons against the startup, Planning intake/native owner and independent PR-custody sources; no stronger-owner promotion or factual admission is claimed.


## Future value

Replace retired interfaces with current owner guidance, preserve the ordinary recurring-failures identity, and keep verbatim dated provenance in existing Git history and retained evidence rather than enlarging active advice.

Material authorship is unattributed. Retention was admitted through the current owner request; this note grants no decision, policy, proof or completion authority.
