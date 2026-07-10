---
name: workspace-operating-loop
description: Use AW compact state to write visible updates as decision, proof, residue, and next-action deltas while preserving module-slot ownership.
---

# Workspace Operating Loop

This is a package-managed workspace skill installed under `.agentic-workspace/skills/`.

Start with `workspace-startup`; use this skill when compact routing, `current_decision`, `message_economy`, `continuation_capsule`, `evidence_bundle`, module ownership, or no-artifact direct-answer behavior needs interpretation before a visible update.

## State-Delta Procedure

1. Read the compact decision frame when present:
   - `current_decision`
   - `message_economy` or `communication_contract`
   - `continuation_capsule`
   - `evidence_bundle`
   - `decision_packet`
   - `proof_narrowness`
   - `reasoning_economy`
2. If the frame is sufficient, answer only the decision-relevant delta:
   - decision or finding;
   - evidence or proof boundary;
   - residue or claim boundary;
   - next safe action or closure status.
3. Do not repeat context already captured in AW state unless it changes the current decision.
4. Do not narrate tool chronology unless the chronology itself is proof-relevant or trust-relevant.
5. If the frame is insufficient, use the smallest `evidence_bundle` or safe probe before making a hard claim.
6. Expand only for proof gaps, safety or ownership ambiguity, unresolved residue, stale evidence, or explicit user request.

## Output Rule

Default visible output is a compact delta, not a recap:

- `Decision:` or `Finding:`
- `Evidence:`
- `Residue:`
- `Next action:`

Omit a field only when it is genuinely irrelevant. Do not omit proof, residue, uncertainty, or owner boundaries when they change the safe claim.

## Module Slot Contract

`workspace`

- Owns startup, config, ownership, lifecycle, module map, skill routing, proof routing, and package composition.
- Preferred route: configured AW invocation with `start`, `implement`, `proof`, `skills`, `report`, `doctor`, or `status`.
- No-CLI fallback: `.agentic-workspace/WORKFLOW.md`, `.agentic-workspace/docs/module-map.md`, then only the named surface.

`planning`

- Owns active execution state, todo promotion, execplans, decomposition, closeout, issue linkage, and continuation.
- Preferred route: configured AW invocation with `summary` or `planning ...`.
- No-CLI fallback: read the compact summary first when possible; open the active execplan only when routed there.

`planning.closeout`

- Owns intent satisfaction, proof-to-claim reconciliation, archive/close decisions, continuation owner, and completion honesty.
- Preferred CLI: Planning archive/closeout commands.
- No-CLI fallback: do not mutate managed state by hand; state proof, intent, gaps, and owner.

`workspace.proof`

- Owns proof selection and proof result interpretation, not broader intent by itself.
- Preferred route: configured AW invocation with `proof --changed <paths> --format json`.
- No-CLI fallback: select the narrowest existing test, lint, contract, or inspection route.

`memory`

- Owns durable anti-rediscovery knowledge, consultation status, durable residue, and improvement-signal routing.
- Preferred route: configured AW invocation with `memory route`, `capture-note`, or `promotion-report`.
- No-CLI fallback: read the Memory index and already-routed notes only.

## Loop

1. Start with the compact router through `workspace-startup`.
2. Preserve the returned `module_slot`, `preferred_cli`, `forbidden_actions`, `proof_required`, and `completion_claim_allowed`.
3. Move to the owning module slot only when the current packet routes there.
4. Use the module's preferred CLI before raw files.
5. If the CLI is unavailable, use the no-CLI fallback for the same slot and keep the same forbidden actions.
6. Before completion, reconcile proof, intent, residue, and issue/PR closure separately.

## Direct Answer Rule

When the router or task shape supports an answer-directly/no-artifact outcome, do not create planning, Memory, review, or docs artifacts just to show work. State the answer and the proof or limitation.

## Optional Work-Shape Pre-Study

Use `work_shape_study` only when a concrete missing evidence class can change the Planning form. Planning custody and known artefact shape are separate decisions: custody may be required while shape-specific creation and product edits remain blocked.

1. Skip study when available evidence already supports one shape without material ambiguity.
2. When referenced intent, parent/child relationships, lane membership, or conflicting Planning is unresolved, run only the named safe probes.
3. Keep the budget to direct references and one-hop shape evidence. Stop when one shape is sufficiently supported.
4. If materially different shapes remain plausible after cheap evidence is exhausted, route `needs-human-decision`; never default to a regular execplan.
5. Preserve observed evidence, inference, missing/unavailable evidence, freshness bindings, selected shape, artefact route, and next action in the compact packet.
6. Compile useful state into the selected Planning owner or `continuation_capsule.work_shape_seed`, then retire the study packet. It is disposable seed state, not proof or parallel authority.

Evaluate activation by total successful-completion cost. Compare clear skip, shape-changing study, and apparent uncertainty that resolves without broadening. Report study cost separately from downstream savings, including rereads, refreshes, artefact conversion/cleanup, proof reruns, clarification loops, AW invocations, and unavailable elapsed evidence. Do not activate from task length, title keywords, branch name, file count, or opaque complexity scores.

## Guardrails

- Do not replace structured packets with prompt-prose keyword matching.
- Do not make all messages short when proof or residue requires detail.
- Do not let one module absorb another module's ownership.
- Do not put active sequencing in Memory.
- Do not put durable repo facts only in a plan closeout.
- Do not treat proof selection as completion permission.
- Do not continue after `completion_claim_allowed=false` without naming the unresolved owner.
