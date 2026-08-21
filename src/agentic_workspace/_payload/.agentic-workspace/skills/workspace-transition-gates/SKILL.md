---
name: workspace-transition-gates
description: Interpret explicit AW transition gates only when the compact current contract needs deeper allowed-action, forbidden-action, owner, proof, reconciliation, or degraded-fallback guidance.
---

# Workspace Transition Gates Reference

This is a routed reference skill. Do not use it as an ordinary startup, module map, proof manual, or closeout workflow.

Start with `workspace-startup`. Use this reference only when the current operating contract exposes a gate that needs interpretation.

## Gate Contract

A gate should be understood through the smallest set of fields that change the next decision:

- trigger/reason;
- current decision/action identity or revision when relevant;
- owning authority/capability;
- preferred operation, skill, selector, or invocation;
- allowed actions/effects;
- forbidden actions/effects;
- proof/claim requirement when relevant;
- expected transition/reconciliation effect;
- bounded no-CLI or human-decision fallback.

Treat those facts as a projection of current source-owned authority. Do not infer a permanent workflow phase from the gate name.

## Resolve Gate

Use when first contact, takeover, stale state, ambiguous ownership, or insufficient current context prevents a safe action.

- Preferred route: configured AW `start` or the exact selector/owner query named by the packet.
- Allowed: obtain the smallest missing authoritative fact, route to the named owner, or continue direct work when explicitly permitted.
- Forbidden: broad raw-state inspection when a compact route exists; treating advisory prose as stronger than a current hard gate.
- Expected result: one current operating contract with a constructible action or explicit human decision.

## Owner / Capability Gate

Use when the current decision routes work to a specialized owner, module, repo operation, or skill.

- Follow the named route without assuming the capability applies globally.
- Let the owner interpret its domain state; return only the bounded result needed by the current operating decision.
- Preserve mutation, proof, and claim boundaries from the parent decision.
- If the capability is unavailable/incompatible, use the bounded recovery named by the current packet rather than raw file guessing.

Current runtimes may name first-party owners such as Planning, Memory, Verification/proof, or another specialized subsystem. Those names are examples of routed owners, not fixed gate classes.

## Action / Effect Gate

Use when an operation is blocked or constrained by authority, changed scope, mutation baseline, runtime capability, or another effect boundary.

- Preferred action: the typed operation or exact recovery route supplied by the current decision.
- Allowed: only effects within the admitted boundary.
- Forbidden: broadening mutation because the user or another module permitted a different concern.
- A blocked result must name a constructible next action, exact owner/selector, or explicit human decision. A conceptual transition label alone is insufficient.

## Proof / Claim Gate

Use only when evidence materially affects the intended claim.

- Run or admit the narrow proof route selected for the current subject/requirement.
- Preserve the distinction between evidence success, semantic intent satisfaction, and broader parent completion.
- A module-local or proof-local success cannot widen the claim beyond the current compiled boundary.
- When proof is not relevant, do not introduce proof ceremony merely because proof capability exists.

## Reconciliation Gate

Use after a bounded action when the result does not automatically determine what happens next.

Reconcile only relevant facts:

- expected transition/result status;
- changed source-owned state/evidence;
- current claim permission;
- future-relevant residue and its owner, if any;
- continuation owner or next supported action;
- explicit human decision when semantics cannot be inferred safely.

If another action remains, return to resolve. If no action remains and the intended claim is permitted, reconciliation is terminal.

Do not preserve a separate mandatory closeout phase merely because current compatibility packets use closeout-specific names.

## Correction, Learning, and Other Specialized Results

When a user correction, durable learned lesson, evaluation result, delegation outcome, setup finding, or future module result needs admission, follow the exact operation/owner routed by the current contract.

This reference does not define those domain procedures. Do not substitute one owner for another—for example, do not turn an agent-specific correction into shared repository knowledge merely because Memory is installed.

## Degraded / No-CLI Gate

When the configured runtime is unavailable:

- preserve the current forbidden actions;
- use the installed fallback or exact named file/selector only;
- repair or escalate the specific missing capability rather than reconstructing broad state manually;
- keep module-specific state opaque unless the fallback explicitly routes there.

## Compatibility Note

Current packets may still expose names such as `planning_safety_gate`, `module_slot`, `planning.closeout`, `workspace.proof`, or phase-specific transition fields.

Honor them when they carry current authority, but interpret them through generic owner/action/reconciliation semantics. Do not teach those names as the permanent architecture.

## Guardrails

- Treat `forbidden_actions` as binding until superseded by a newer admitted decision.
- Prefer exact selectors and owner routes before broad raw reads.
- Keep the transition reference smaller than the domain procedure it routes to.
- Do not let transport, evidence, or module-local state silently widen unrelated authority.
- Do not create another gate category when an existing owner/action/reconcile fact can express the decision.