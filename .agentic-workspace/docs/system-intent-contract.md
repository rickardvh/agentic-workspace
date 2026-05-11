# System Intent Contract

This contract keeps the larger intended outcome visible even when work is executed in smaller bounded slices.
Repo-owned prose such as `SYSTEM_INTENT.md`, `README.md`, `AGENTS.md`, design docs, or issue context may provide evidence for that direction; checked-in planning still owns active execution state, bounded slices, and continuation routing.

## Workspace-Owned Declaration

The host repo does not need to author system intent in a package-owned schema, and the workspace does not assume one authoritative source file format.
Instead:

- repo-owned intent sources are declared in `.agentic-workspace/config.toml [system_intent]`
- workspace stores the consumed compiled declaration in `.agentic-workspace/system-intent/intent.toml`
- `.agentic-workspace/OWNERSHIP.toml [[subsystems]]` is authoritative for which subsystems exist
- workspace stores scoped subsystem intent for those ownership subsystem ids in `.agentic-workspace/system-intent/subsystems.toml`
- `.agentic-workspace/system-intent/WORKFLOW.md` tells agents how to refresh source metadata and refine that declaration

This keeps the consumed declaration inside the workspace home while leaving host-repo source authoring unconstrained.
`agentic-workspace system-intent --target ./repo --sync --format json` refreshes source discovery and metadata only. It does not mechanically rewrite interpreted fields from repo prose.

## Interpretation Boundary

- repo-owned prose remains unconstrained evidence
- `.agentic-workspace/system-intent/intent.toml` remains a normalized, reviewable, human-correctable declaration
- agents perform conservative interpretation
- humans retain easy inspection and correction authority

Low-confidence interpretation should remain visible through `confidence`, `needs_review`, and `open_questions`.

## Intent Scopes

Task intent is the bounded goal of current work. It can be implemented, validated, and closed.

System intent is durable repo-wide direction, purpose, constraint, or invariant. It is not active work by default; it is decision pressure that should remain inspectable, editable, provenance-backed, and allowed to change.

Subsystem intent is durable direction for a component, module, concern, or owned surface already declared in `.agentic-workspace/OWNERSHIP.toml [[subsystems]]`. Use it when the direction is narrower than the whole system but broader than one task, such as Planning behavior, Memory hygiene, generated CLI portability, accessibility expectations, memory usage constraints, documentation philosophy, or auditability requirements. Do not invent a separate subsystem taxonomy in `subsystems.toml`; it attaches intent to ownership subsystem ids.

## Durable Intent Lifecycle

Durable intent records may be inferred from docs, code, issues, chat context, review evidence, or repeated task outcomes. Inference can be wrong or become stale, so records should carry:

- source records
- confidence
- `needs_review`
- open questions
- revision or supersession fields when an interpretation changes

Use `agentic-workspace report --target ./repo --section durable_intent --format json` for the compact decision projection.
Use `agentic-workspace defaults --section durable_intent --format json` for the lifecycle contract.

## Promotion From Task Intent

Before closing planned work, classify any durable direction revealed by the task:

- `do-not-promote`
- `memory`
- `subsystem-intent`
- `system-intent`
- `refine-existing-intent`
- `supersede-existing-intent`

Promotion should be evidence-backed and reviewable. Agents should not silently make inferred intent authoritative.

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
- `agentic-workspace defaults --section durable_intent --format json`
- `agentic-workspace report --target ./repo --section durable_intent --format json`
- `agentic-workspace summary --format json`
- `agentic-planning report --format json`
- `agentic-workspace system-intent --target ./repo --sync --format json`

## Checked-In Residue Rule

Keep a checked-in execplan whenever later proof, intent validation, or required continuation would be expensive or ambiguous to reconstruct from chat alone.
