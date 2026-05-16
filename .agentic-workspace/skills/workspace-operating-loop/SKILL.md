---
name: workspace-operating-loop
description: Use the core Agentic Workspace operating loop and module slot contract. Use when deciding which module owns startup, planning, implementation, proof, closeout, memory consultation, residue routing, or no-artifact direct answers.
---

# Workspace Operating Loop

This is a package-managed workspace skill installed under `.agentic-workspace/skills/`.

Use it to keep module ownership visible while preserving compact CLI-first operation.

## Module Slot Contract

`workspace`

- Owns startup, config, ownership, lifecycle, module map, skill routing, proof routing, and package composition.
- Preferred CLI: `agentic-workspace start`, `implement`, `proof`, `skills`, `report`, `doctor`, `status`.
- No-CLI fallback: `.agentic-workspace/WORKFLOW.md`, `.agentic-workspace/docs/module-map.md`, then only the named surface.

`planning`

- Owns active execution state, todo promotion, execplans, decomposition, closeout, issue linkage, and continuation.
- Preferred CLI: `agentic-workspace summary`, `agentic-workspace planning ...`.
- No-CLI fallback: read the compact summary first when possible; open the active execplan only when routed there.

`planning.closeout`

- Owns intent satisfaction, proof-to-claim reconciliation, archive/close decisions, continuation owner, and completion honesty.
- Preferred CLI: Planning archive/closeout commands.
- No-CLI fallback: do not mutate managed state by hand; state proof, intent, gaps, and owner.

`workspace.proof`

- Owns proof selection and proof result interpretation, not broader intent by itself.
- Preferred CLI: `agentic-workspace proof --changed <paths> --format json`.
- No-CLI fallback: select the narrowest existing test, lint, contract, or inspection route.

`memory`

- Owns durable anti-rediscovery knowledge, consultation status, durable residue, and improvement-signal routing.
- Preferred CLI: `agentic-workspace memory route`, `capture-note`, `promotion-report`.
- No-CLI fallback: read the Memory index and already-routed notes only.

## Loop

1. Start with the compact router.
2. Preserve the returned `module_slot`, `preferred_cli`, `forbidden_actions`, `proof_required`, and `completion_claim_allowed`.
3. Move to the owning module slot only when the current packet routes there.
4. Use the module's preferred CLI before raw files.
5. If the CLI is unavailable, use the no-CLI fallback for the same slot and keep the same forbidden actions.
6. Before completion, reconcile proof, intent, residue, and issue/PR closure separately.

## Direct Answer Rule

When the router or task shape supports an answer-directly/no-artifact outcome, do not create planning, Memory, review, or docs artifacts just to show work. State the answer and the proof or limitation.

## Guardrails

- Do not let one module absorb another module's ownership.
- Do not put active sequencing in Memory.
- Do not put durable repo facts only in a plan closeout.
- Do not treat proof selection as completion permission.
- Do not continue after `completion_claim_allowed=false` without naming the unresolved owner.
