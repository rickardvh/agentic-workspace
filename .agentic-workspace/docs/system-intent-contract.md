# System Intent Contract

This contract keeps the larger intended outcome visible even when work is executed in smaller bounded slices.
Repo-owned prose such as `SYSTEM_INTENT.md`, `README.md`, `AGENTS.md`, `llms.txt`, design docs, or issue context may provide evidence for that direction; checked-in planning still owns active execution state, bounded slices, and continuation routing.

## Workspace-Owned Declaration

The host repo does not need to author system intent in a package-owned schema, and the workspace does not assume one authoritative source file format.
Instead:

- repo-owned intent sources are declared in `.agentic-workspace/config.toml [system_intent]`
- workspace stores the consumed compiled declaration in `.agentic-workspace/system-intent/intent.toml`
- `.agentic-workspace/system-intent/WORKFLOW.md` tells agents how to refresh source metadata and refine that declaration

This keeps the consumed declaration inside the workspace home while leaving host-repo source authoring unconstrained.
`agentic-workspace system-intent --target ./repo --sync --format json` refreshes source discovery and metadata only. It does not mechanically rewrite interpreted fields from repo prose.

## Interpretation Boundary

- repo-owned prose remains unconstrained evidence
- `.agentic-workspace/system-intent/intent.toml` remains a normalized, reviewable, human-correctable declaration
- agents perform conservative interpretation
- humans retain easy inspection and correction authority

Low-confidence interpretation should remain visible through `confidence`, `needs_review`, and `open_questions`.

## Core Rule

- Confirmed higher-level intent must stay recoverable separately from the currently active slice.
- Bounded slicing may narrow means, decomposition, and immediate proof, but it must not silently replace the larger requested outcome.
- Active execplans should use `system_intent_alignment` to name the materially relevant system intent, the slice-shaping bias it creates, and the broader-lane validation question that remains after local task proof.

## Authority Ladder

1. Confirmed request or live issue cluster: what the repo is actually trying to satisfy.
2. Active execplan delegated judgment and intent continuity: the bounded slice and its mapping back to the larger outcome.
3. Closure check and required continuation: whether the slice can archive, whether the larger outcome is still open, and where follow-through now lives.

## Reinterpretation Boundary

Allowed:
- choose a smaller first slice
- tighten validation
- route required continuation into one checked-in owner

Not allowed:
- claim the larger outcome is closed without explicit evidence
- leave required continuation only in drift prose or chat
- silently substitute a cheaper but different end state

## Recoverability Rule

Ordinary compact inspection should answer:
- what larger outcome this slice serves
- whether that larger outcome is actually closed
- where required continuation now lives
- what evidence justified the closure decision

Use:
- `agentic-workspace defaults --section system_intent --format json`
- `agentic-workspace summary --format json`
- `agentic-planning-bootstrap report --format json`
- `agentic-workspace system-intent --target ./repo --sync --format json`

## Checked-In Residue Rule

Keep a checked-in execplan whenever later proof, intent validation, or required continuation would be expensive or ambiguous to reconstruct from chat alone.
