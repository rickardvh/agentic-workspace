# Reconciliation Contract

Reconciliation is the post-action part of the ordinary `resolve -> act -> reconcile` loop. It is not a separate workflow or a second closeout authority.

`agentic_workspace.reconciliation.compile_reconciliation` admits owner-supplied facts into the existing operating decision and answers four questions:

1. What happened to the bounded action?
2. What owner level may now be claimed?
3. Does durable residue need exactly one owner?
4. Is the result terminal, or what constructible action happens next?

The contract keeps action result, semantic intent, parent intent, proof, external evidence, residue, and continuation distinct. Passing proof can support a bounded claim, but it cannot satisfy semantic intent, close a parent, or grant a module global completion authority.

Direct work can terminate with no Planning, Memory, Verification, or closeout artifact when its intent is satisfied and no residue remains. Non-terminal results name a recovery owner and supply an operation, command, or explicit human decision. Existing Planning archive/closeout, proof, and reporting surfaces remain domain operations or derived detail; `operating_decision.reconciliation` is the cross-cutting claim/action composition owner.

External state is evidence rather than Planning authority. A changed or closed external item therefore produces one of these explicit choices:

- `local-intent-satisfied`: admit local proof and archive or close through Planning;
- `local-intent-remains`: retain or rebind a current local owner and reason;
- `external-evidence-stale/unavailable`: refresh evidence before relying on it;
- `human-intent-decision`: record the local semantic disposition when it cannot be inferred.

Until that mismatch is disposed, work selection and completion claims are limited.
