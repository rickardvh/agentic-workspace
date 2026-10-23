# Work shape vocabulary

## Vocabulary

- `direct`: target and proof are obvious; answer or edit with the narrowest proof and no durable artifact unless routed.
- `bounded`: finite implementation with meaningful proof, continuation, or issue-linkage risk; use compact implement/proof routing.
- `lane`: multi-slice or issue-lane work; reuse a suitable issue or Planning owner
  for sequencing and dependencies before work that depends on them. Do not create
  a duplicate plan when current repository records are sufficient.
- `epic`: multiple lanes, high assurance, or unclear decomposition; shape before implementation.

## External Reporting Targets

Use this as an agent checklist, not as runtime keyword policy. Issue or
PR references used only for comments, reports, replies or follow-ups are
destinations for the current communication task. They do not by themselves
make those issues implementation targets or establish a multi-issue lane.

When a task mixes an implementation issue with a reporting target, separate them before judging shape:

- implementation refs may carry issue scope and proof obligations;
- reporting target refs identify where to post, edit, or read a comment;
- the agent still owns the final direct/bounded/lane judgment from action safety, source impact, proof burden, and closure claims.

Do not implement this distinction with prompt-keyword matching in AW runtime.
The runtime may expose references, changed paths, active Planning state and
proof facts; deciding which reference governs work remains agent judgment.

## Reference Output

When this reference is explicitly requested, report the inferred outcome,
work shape and rationale, first repository source to inspect or change,
satisfaction evidence, next required route, and whether Planning is optional,
recommended or required.
