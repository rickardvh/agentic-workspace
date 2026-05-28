# Pre-Ingestion Refinement

Use this before a coding agent starts implementation when an upstream issue, candidate lane, or broad request still needs stronger reasoning to clarify scope.

This surface is preparatory guidance only. It can produce issue comments, review notes, or planning-friendly clarification, but it does not become active planning state until a maintainer promotes the result into `.agentic-workspace/planning/state.toml` or an execplan.

## When To Use

- The request is ambiguous enough that implementation would require guessing.
- The likely boundary crosses packages, generated surfaces, config, or runtime policy.
- Proof expectations are unclear or too broad.
- The task needs architecture/domain framing before a bounded code slice exists.
- A candidate lane needs sharper first-slice wording before promotion.

## Non-Goals

- Do not require this before every task.
- Do not turn issue comments into canonical planning truth automatically.
- Do not preserve long analysis when a compact clarification is enough.
- Do not use this as a second workflow system beside checked-in planning.

## Refinement Output Contract

Keep the output short enough to paste into an issue comment or review note:

```text
Refinement type:
Source:
Restated outcome:
Key ambiguity:
Boundary decision:
Suggested first slice:
Proof expectation:
Planning destination:
Open question:
```

## Template: Ambiguity Reduction

```text
Refinement type: ambiguity-reduction
Source: <issue/url/title>
Restated outcome: <one sentence>
Key ambiguity: <the decision blocking implementation>
Likely interpretation: <the safest interpretation and why>
Rejected interpretation: <what should not be assumed>
Suggested first slice: <smallest implementation-ready slice>
Proof expectation: <narrowest command or inspection that would prove it>
Planning destination: <dismiss | bounded review | roadmap candidate | active task | execplan>
Open question: <one question only, or "none">
```

## Template: Boundary And Ownership

```text
Refinement type: boundary-and-ownership
Source: <issue/url/title>
Restated outcome: <one sentence>
Owned surfaces: <paths or modules that should change>
Surfaces to avoid: <paths or modules that should not change>
Authority source: <config/docs/contracts/plan that should govern>
Boundary risk: <what would make the slice too broad>
Suggested first slice: <bounded change>
Proof expectation: <validation command or review target>
Planning destination: <dismiss | bounded review | roadmap candidate | active task | execplan>
Open question: <one question only, or "none">
```

## Template: Proof Shaping

```text
Refinement type: proof-shaping
Source: <issue/url/title>
Restated outcome: <one sentence>
Expected behavior: <observable behavior, not implementation detail>
Minimum proof: <narrowest command or check>
Broaden proof when: <condition that requires a wider lane>
Insufficient proof: <what would not be enough>
Suggested first slice: <bounded change>
Planning destination: <dismiss | bounded review | roadmap candidate | active task | execplan>
Open question: <one question only, or "none">
```

## Promotion Rule

After refinement, promote only the durable result:

- Use `roadmap` in `.agentic-workspace/planning/state.toml` for accepted inactive work.
- Use `todo.active_items` only for tiny direct work.
- Use an execplan when sequencing, proof, ownership, or handoff detail would otherwise remain in the issue comment.
- Use a review artifact when the refinement produces findings that need bounded validation before planning.

If the refined output is only explanatory and does not change planning, leave it in the upstream tracker or review note.
