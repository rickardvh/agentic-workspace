# Setup Findings Classes Review

Date: 2026-04-18

## Question

Beyond `repo_friction_evidence` and `planning_candidate`, does any additional setup or jumpstart finding class currently justify durable promotion?

## Current Durable Classes

- `repo_friction_evidence`
  - durable owner: `agentic-workspace report --target ./repo --format json`
  - preserved as: `repo_friction.external_evidence`
- `planning_candidate`
  - durable owner: `TODO.md` or `.agentic-workspace/planning/execplans/` after bounded planning review
  - preserved as: explicit planning-promotion guidance rather than auto-written active state

## Adjacent Plausible Classes Reviewed

- memory candidate or memory usefulness finding
- ownership ambiguity finding
- validation or proof concern finding
- generic setup warning or diagnosis bucket

## Evaluation

### Memory-Oriented Findings

Not justified as a new setup-finding class right now.
Memory candidates already belong in setup discovery or later Memory-native review and routing surfaces.
Adding a third setup class here would duplicate a better owner.

### Ownership Or Proof Concerns

Not justified as a new setup-finding class right now.
These are better treated as repo-friction evidence, bounded planning promotion, or ordinary review findings depending on whether they reflect shared structural friction or a specific follow-on slice.

### Generic Diagnostics

Not justified.
This would widen setup into a broad analysis interchange bucket and break the product boundary of "accept analysis, standardize promotion."

## Decision

Keep the current two durable classes only.

The current contract is broad enough to preserve the setup findings that already have clear durable owners, and narrow enough to avoid turning setup into a second analysis framework.

## Reopen Signal

Revisit this only when repeated real setup or jumpstart passes produce one additional finding shape that:

- clearly reduces later repo operating cost
- has a stable durable owner outside setup itself
- cannot already be represented as repo-friction evidence, planning promotion, or ordinary review residue
