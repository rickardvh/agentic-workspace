# Planning Friction Signal Review

Date: 2026-04-18

## Question

Does planning friction deserve to be an explicit repo-friction signal rather than staying implicit?

## Operational Definition

Treat planning friction as repo-friction evidence only when the normal compact planning and recovery path still leaves one of these unclear:

- the smallest safe slice
- the narrowest proof boundary
- the owning surface or concern boundary
- the minimum useful read set

Do not treat ordinary hard work or one-off weak-model confusion as planning friction by default.

## Bounded Subtypes

- `unclear_seam`
- `unclear_proof_boundary`
- `ownership_ambiguity`
- `chunking_instability`
- `reread_pressure`

## Recent Repo Cases

### Planning Hierarchy And Queue Routing

- signal: `chunking_instability`
- why it counts: the repo needed a clearer active-chunk versus queue contract before later planning work became cheaper again

### Planning Surface Clarity

- signal: `reread_pressure`
- why it counts: routine recovery needed stronger compact answers so normal work would stop falling back to broader prose

### Workspace Optimization Bias And Setup Findings

- signal: `unclear_seam`
- why it counts: output posture, findings promotion, and planning-friction evidence all belonged in the same workspace/reporting seam, but that seam was not explicit enough in normal operation

## Decision

Yes. Planning friction should be an explicit repo-friction evidence class.

It is useful because it points at structural cost in the repo and the shipped contracts, not merely at local inconvenience during one task.

## Reporting Rule

Expose planning friction through the existing `repo_friction` reporting path.

Do not create a separate planning dashboard or generic productivity score.
