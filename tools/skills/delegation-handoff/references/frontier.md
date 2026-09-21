# Carry the current frontier

Give the receiving worker enough to perform its bounded outcome without parent
chat. Reuse current owner material before writing a summary. Where an additional
semantic summary is necessary, keep it in one task-owned temporary source using
the repository's resource lifecycle, or in the current Planning frontier when
durable execution custody is warranted. Do not add a per-handoff registry.

The supplied material should answer:

- What outcome and scope is assigned, and what stays with the parent?
- Which current procedure fragment is relevant, and why? Include its exact source
  and dependency references, not all unselected branches.
- Which useful judgments and progress remain supported by current sources? Carry
  their rationale, scope and source revisions; advisory answers are not evidence
  or policy. Missing or stale judgments remain unresolved.
- Which constraints, uncertainties and stop conditions can change the action?
- What proof and independent review does the current owner require, and what
  result format, changed paths and effect disposition must return?

Supply the exact source references through the returned handoff-input request.
Include the relied-upon procedure and evidence sources as captured inputs as well
as the semantic summary. Judge completeness only after inspecting what the owner
actually captured; an old summary alone cannot bind changed upstream material.

Use the sealed Assignment packet. For manual transport, the existing `worker`
primitive presents `{action: "entry", packet}` and expands required captured
inputs with `{action: "expand", packet, reference}`. These bytes are a bounded
snapshot, not live authority or permission to widen scope. Give the worker its
view and required expansions, never parent chat or unrelated owner state.

The worker returns new summary, changed paths, patch and stop conditions through
`{action: "return", packet, material}`. It cannot admit its own result, integrate
it, or close parent work. Continue with [current return custody](resume.md).
