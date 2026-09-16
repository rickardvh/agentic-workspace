# Returned Result Admission

Use this only after a delegated run returns, fails, blocks, or becomes stale. Do not use it for direct local implementation.

1. Read the current delegated-run lifecycle and returned-result packet.
2. Treat worker claims as untrusted until `assignment admit` resolves current assignment, scope, transport, proof, and baseline authority.
3. Route malformed, stale, duplicate, blocked, or scope-widened returns to the exact reject, repair, reassign, supersede, or abandon operation; do not hand-edit lifecycle state.
4. Integrate only an admitted return through the normal repository ownership path.
5. After admitted integration, consume the directly offered Planning adoption
   action when present. No separate request is needed to unlock its mechanically
   determined postimage. This does not answer plan relation, edit semantic intent,
   authorize selector custody, or repeat an uncertain write.
6. After integration, run AW-owned proof and reconcile intent and closeout separately. A worker result never authorizes either claim by itself.

Workers, explorers, and reviewers must return at their declared boundary:
workers cannot widen scope or close parent work; explorers cannot write or
claim implementation; reviewers cannot turn findings into implementation
without a new assignment.

Keep the compact path for a current, bounded, schema-valid return. Expand only for conflicts, high risk, uncertainty, human override, or changed scope.
