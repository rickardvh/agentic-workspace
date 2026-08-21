---
name: workspace-operating-loop
description: Interpret AW compact state through the generic resolve-act-reconcile loop and write decision-relevant updates without teaching fixed module slots.
---

# Workspace Operating Loop

This is a routed support skill for interpreting compact AW state after `workspace-startup`.

Use it when `current_decision`, `message_economy`, `continuation_capsule`, `evidence_bundle`, routed owner/capability state, or result reconciliation needs interpretation before the next action or visible update.

Do not use this as a module map or a second startup manual.

## Resolve

Read the smallest current decision frame that is already available, for example:

- `current_decision` / decision identity;
- `next_safe_action` or immediate allowed action;
- allowed/forbidden effects;
- routed owner, operation, skill, selector, or preferred invocation;
- `message_economy` / `communication_contract`;
- `continuation_capsule`;
- `evidence_bundle`;
- proof/claim limits;
- compatibility projections such as `module_slot` when emitted by the current runtime.

If that frame is sufficient, do not broaden into raw state. If it is insufficient, use the smallest routed selector, evidence bundle, owner query, or safe probe that can change the decision.

Treat module-specific fields as routing/projection metadata, not a fixed set of architectural slots.

## Act

Follow the supported action named by the current decision.

Preferred action forms are:

- typed operation invocation;
- generated/concrete command derived from an operation;
- routed specialized skill;
- exact owner/selector query;
- bounded recovery action;
- explicit human decision with the necessary conflict facts.

Do not hand-edit managed state merely because the underlying file is visible. Do not invent a module-specific command path when the current contract already names one.

## Reconcile

After the action, reconcile only the dimensions that became relevant:

- did the expected transition occur;
- what source-owned state or evidence changed;
- what claim is now permitted;
- what blocker or uncertainty remains;
- whether future-relevant residue needs a canonical/module owner;
- who owns continuation;
- what exact action follows.

If another action is required, resolve again from the new current state. If nothing remains and the intended claim is allowed, stop.

A successful module-local action, proof result, or file edit does not by itself authorize a broader completion claim.

## Visible Update Rule

Default visible output is the smallest decision-relevant delta, not a chronology recap.

Useful fields when relevant:

- `Decision:` or `Finding:`
- `Evidence:`
- `Residue:` or `Claim boundary:`
- `Next action:`

Omit fields that are genuinely irrelevant. Do not omit uncertainty, proof, residue, or owner boundaries when they change the safe claim.

Do not repeat context already preserved in AW state unless it changed the current decision.

## Owner and Capability Routing

There is no fixed module-slot contract in this skill.

When the current packet names an owner, capability, module, skill, or preferred CLI:

1. preserve its authority and forbidden-action boundaries;
2. follow the named operation/skill/selector before raw files;
3. let the domain owner interpret its own state;
4. return only the bounded result needed by the current operating decision;
5. do not infer that the capability applies outside the routed scope.

Current runtimes may emit names such as `planning`, `memory`, `workspace.proof`, or `planning.closeout`. Treat those as compatibility projections of specific owners, not as the permanent shape of the loop.

## Progressive Disclosure

- Irrelevant installed modules stay out of first-line context.
- Specialized procedures load only when routed.
- Generated references are for exact details after the relevant owner is known.
- Raw managed files are fallback/detail surfaces, not first-contact discovery.
- A module can add a new routed procedure without requiring this skill to learn the module's identity.

## Direct Answer Rule

When the current contract supports answer-directly/no-artifact behavior, answer directly.

Do not create Planning, Memory, proof, review, handoff, correction, evaluation, or docs artifacts simply because those capabilities exist. Persist only future-relevant context with a clear owner.

## Specialized Procedures

Domain procedures belong behind their routed owners rather than in this main loop.

Examples include intent/work-shape study, proof selection, correction-event capture, learned-knowledge capture, Planning transitions, Verification protocols, delegation, setup, and future module procedures.

Follow the exact routed skill or operation when one of those becomes relevant. If no route exists, report the missing constructible action instead of embedding a new domain procedure here as a workaround.

## Guardrails

- Repository/module sources retain semantic authority; this skill interprets their compiled current effect.
- Do not replace structured packets with prompt-keyword classification.
- Do not let one capability absorb another owner's semantics.
- Do not treat proof success as semantic completion.
- Do not make all visible updates short when proof, safety, or unresolved ownership requires detail.
- Do not continue after a blocking/claim-denied result without naming the unresolved owner or supported recovery.
- Prefer less first-line context, fewer framework concepts, and exact deeper routes.
