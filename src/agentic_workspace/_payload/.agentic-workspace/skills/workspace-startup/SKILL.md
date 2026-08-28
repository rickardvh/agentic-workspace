---
name: workspace-startup
description: Use the canonical Agentic Workspace operating loop. Resolve one compact current contract, act through its routed operation or skill, reconcile the result, and load deeper capability detail only when routed.
---

# Workspace Startup / Operating Loop

Use this skill for ordinary first contact, resume, changed-path work, routed proof, continuation, or fallback in an installed Agentic Workspace repository.

The ordinary mental model is **resolve -> act -> reconcile**. Do not learn module topology or reconstruct a command sequence before work can begin.

## Configured Invocation

Use the configured AW invocation exposed by the repo adapter, config, or compact output. In an installed repo this may be `agentic-workspace ...`; in a source checkout or dev-dependency install it may be a repo-local command.

Do not replace a configured invocation with a guessed bare command.

## Resolve

1. Run the configured invocation with `start --target . --task "<task>" --format json` for ordinary first contact.
2. If changed paths are already known, use `implement --target . --changed <paths> --task "<task>" --format json` when that is the routed/current affordance.
3. Consume the compact current decision before raw `.agentic-workspace/` files. Preserve the fields that materially constrain the decision, including when present:
   - decision/action identity and input revision;
   - `next_safe_action` or `immediate_next_allowed_action`;
   - allowed and forbidden actions/effects;
   - proof or claim boundaries;
   - routed owner, skill, operation, selector, or preferred invocation;
   - compatibility projections such as `planning_route_decision` or `planning_safety_gate` when the current runtime emits them.
   - receipt-bound `configuration_readiness` when fresh or stale bootstrap authority requires repository setup reconciliation.
4. Treat module- or phase-specific fields as projections of the current operating decision, not as a fixed architecture to generalize from. Follow the route they name. **Do not reclassify the task** from prose, legacy task-switch fields, or another capability after a current authoritative route decision exists.
5. If the compact result is insufficient, use only the smallest selector, skill, operation, or safe probe it routes to before broadening context.

## Act

1. Follow the supported next action before inventing a different command path.
2. Prefer a typed/routed operation, generated command, specialized skill, exact owner/selector, or explicit human decision over hand-editing managed state.
3. Load a specialized capability procedure only when the current decision routes there.
   A `reconcile-repository-configuration` action routes exactly to `workspace-setup-jumpstart` and its configured `setup --target . --format json` command; do not substitute task-keyword inference or broad repo discovery.
4. Keep direct work direct when the contract permits it. Do not create Planning, Memory, review, proof, handoff, or other artifacts merely to demonstrate AW use.
5. Do not infer permission from advisory prose when a current hard gate or forbidden action says otherwise.

## Reconcile

After the bounded action:

1. Admit or refresh the result through the owner/operation named by the current route when required.
2. Reconcile only concerns relevant to this work: changed state, proof/evidence, claim permission, future-relevant residue, continuation, or an explicit human decision.
3. Preserve the difference between successful local action and permission to make a broader completion claim.
4. If the user, review, orchestrator, or host explicitly corrects the acting agent's behavior, treat that correction as reconciliation input and submit it through `correction-event submit` (or a newer routed equivalent) when available. Do not substitute an apology, chat promise, or Memory note for correction admission.
5. If the result names another supported action or unresolved owner, resolve again from that current state.
6. Stop when no further action is required and the intended claim is permitted. Terminal reconciliation is closeout; no separate closeout framework is assumed.

## Progressive Disclosure

First contact should stay small.

- Do not open a module map, module state, broad generated references, or raw Planning/Memory/Verification files merely because they exist.
- Do not load specialized skills merely because they are installed.
- Use exact selectors and routed procedures before broad reads.
- An irrelevant installed capability should remain irrelevant.

## Specialized Routes

Use specialized skills only when routed or when the request directly maps to their narrow job:

- `workspace-intent-discovery` — ambiguous human intent or work-shape decision.
- `workspace-proof-selection` — proof selection/interpretation when the current claim needs it.
- `workspace-setup-jumpstart` — bounded post-bootstrap seeding in a lived-in repo.
- `workspace-operating-loop` — interpret compact decision/state-delta behavior when a visible update or reconciliation needs deeper guidance.
- `workspace-transition-gates` — interpret explicit allowed/forbidden actions, preferred invocation, or degraded fallback when the compact route is not self-explanatory.

A module or future capability may route its own specialized skill or operation through the same mechanism without becoming part of this fixed list.

## No-CLI / Degraded Fallback

If the configured invocation is unavailable, use the installed no-CLI startup fallback when present:

```bash
python .agentic-workspace/fallback/no_cli_startup.py
```

Follow its forbidden actions and next safe action. A degraded route should stay bounded to the named repair or owner; do not compensate by reading the entire workspace tree.

## Compatibility Note

Current runtime packets may still expose first-party or historical projection names such as `planning_safety_gate`, `planning_route_decision`, or closeout-specific fields.

Use them when present because they carry current authority, but interpret them through the generic rule: **which owner/capability is relevant now, what action is allowed, and what claim/reconciliation effect follows?** Do not teach those projection names as permanent core concepts.

## Red Flags

Red flag:
  I can inspect raw Planning, Memory, Verification, or module files first because the task seems related to that capability.

Use instead:
  Resolve the compact current contract, then follow the routed owner/skill/operation if that capability is actually relevant.

Red flag:
  Validation succeeded, so I can call the whole task complete.

Use instead:
  Reconcile the actual result with the current claim boundary and containing intent before making a broader claim.

## Guardrails

- Repository sources keep their own authority; a generated operating contract is a projection, not a new source of truth.
- Do not replace structured decision/action fields with prompt-keyword inference.
- Do not bypass forbidden actions because a different capability appears permissive.
- Do not make installed modules or specialized procedures visible when irrelevant.
- Do not persist residue unless it has future decision value and a clear owner.
- Prefer the smallest safe next action and the smallest sufficient context.
