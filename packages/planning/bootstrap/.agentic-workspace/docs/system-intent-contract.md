# System Intent Contract

This contract keeps the larger intended outcome visible even when work is executed in smaller bounded slices.
`SYSTEM_INTENT.md` is the repo's directional compass for that larger outcome; checked-in planning still owns active execution state, bounded slices, and continuation routing.

## Core Rule

- Confirmed higher-level intent must stay recoverable separately from the currently active slice.
- Bounded slicing may narrow means, decomposition, and immediate proof, but it must not silently replace the larger requested outcome.

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

## Checked-In Residue Rule

Keep a checked-in execplan whenever later proof, intent validation, or required continuation would be expensive or ambiguous to reconstruct from chat alone.
