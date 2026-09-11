---
name: github-issue-shaping
description: Shape or refine Agentic Workspace GitHub issues before creation or update while preserving intent, scope, evidence, and honest closure boundaries.
---

# GitHub Issue Shaping

Use this repo-owned skill when refining an existing issue, turning a finding into a lane or child issue, or deciding whether a new issue should be created for this repository. Use `github-issue-creation` after this skill only when a new issue must actually be created.

## Procedure

1. Identify the real problem before naming a solution:
   - what is missing, mis-shaped, noisy, unsafe, or too costly today;
   - why it matters beyond the local symptom;
   - who owns the final intended outcome.
2. Run a bounded assumption audit before committing the issue shape:
   - separate directly observed evidence from inferred diagnosis, intended invariant, and proposed mechanism;
   - treat an example or reproduction as evidence unless the issue justifies it as a durable contract fixture;
   - name the owning domain, portability boundary (generic package versus repo/provider/dogfooding case), and any intentionally agent- or human-owned judgment;
   - ask whether the mechanism creates avoidable framework, registry, durable-state, or event-ledger growth when an existing owner could satisfy the outcome more cheaply;
   - test whether the invariant is feasible and no stronger or more absolute than the actual need;
   - remove the proposed mechanism from the wording and verify that the problem, owner, and acceptance boundary still make sense.
3. Choose the issue kind:
   - `bug` for correctness, reliability, regression, or broken behavior;
   - `direction` for product direction, architecture, lanes, or bounded planning slices;
   - `review` for dogfooding friction, trust gaps, continuation gaps, and review findings.
4. Decide hierarchy:
   - parent direction / lane;
   - child slice / bounded follow-on;
   - cross-cutting proposal;
   - no new issue, only a comment or direct fix.
5. Classify the closure shape separately from issue kind or hierarchy:
   - **parent outcome / direction** — preserves broad intent and coordinates bounded children or dispositions; it closes administratively when accepted children/dispositions plus immediate aggregate proof make the parent outcome true. Do not require a giant parent-closing PR.
   - **bounded implementation leaf** — one coherent bounded PR plus immediate deterministic/integration proof must be able to make the whole stated implementation outcome true. If that is not credible before implementation starts, split the leaf first.
   - **later evidence / review** — gathers evidence that is inherently unavailable at implementation time, such as ordinary-use burden, provider incidents, heterogeneous-repository convergence, or longitudinal ROI. Product code is not required for this issue to close; concrete defects or improvements discovered here route to the smallest bounded implementation owner.
6. Audit leaf size before scheduling implementation:
   - a scheduled implementation leaf must be honestly closeable by one coherent PR and present-tense proof;
   - if the stated outcome spans multiple independently useful implementation changes, split bounded children before implementation rather than normalizing “first slice landed, leaf remains open”;
   - if new evidence genuinely changes the understood problem mid-stream, reshape transparently and preserve residual intent before continuing;
   - do not retroactively create follow-ups merely to excuse a knowingly partial implementation of the original leaf.
7. Preserve closure boundaries:
   - intended final outcome;
   - observable acceptance criteria;
   - non-solutions;
   - evidence required for final completion;
   - completion rule for whether a PR may close the issue;
   - for a parent, which accepted child/disposition evidence permits administrative closure;
   - for a later-evidence issue, an explicit statement that no product-code PR is required and where concrete findings route.
8. Separate immediate implementation proof from later evidence:
   - fresh-process fixtures, fault injection, exact-head tests, controlled before/after measurements, and currently available integration smoke tests can close a bounded implementation leaf when they prove its present behavior;
   - future ordinary-use observations, future provider incidents, heterogeneous-repository convergence, and broad break-even/ROI claims belong to a later-evidence owner unless they are already available current evidence;
   - present-tense deterministic behavior cannot be deferred into an evaluation;
   - when a longitudinal evaluation is itself part of an issue, name owner, criteria, evidence sources, report sinks, collection policy, and conclusion policy;
   - known defects, vague "collect more evidence" text, missing present proof, or unimplemented behavior are non-solutions and must not authorize closure.
9. Keep useful slices honest:
   - name a useful first slice only if it does not imply final closure;
   - route residual intent to a clear owner;
   - do not use later evidence owned elsewhere to keep an otherwise-complete bounded implementation leaf open;
   - avoid creating follow-up issues as a substitute for completing the stated outcome.
10. If creating the issue, hand off to `github-issue-creation` so the template, labels, closure shape, and refresh/reconcile steps are preserved.
11. If updating an issue, preserve the existing template headings unless a human asks to reshape the issue format.

## Closure-Shape Examples

- **Oversized implementation:** “make delegation work end to end across every provider, replacement mode, worker context, target evidence, and long-run economics” is not one implementation leaf. Keep the broad delegation outcome as a parent; shape PR-closeable worker-entry, supported launch/return, and replacement-effect leaves; put real-provider burden/economic observations in a no-code later-evidence issue.
- **Implementation plus later evidence:** a bounded adaptation mechanism may close when current nomination, authority, application/no-retention, and fresh-resolution fixtures pass. Whether that mechanism repays its cost across months of heterogeneous repository use belongs in a separate later-evidence issue and does not keep the correct implementation leaf open.

## Assumption Audit Examples

- Over-assumed issue: a one-off static comparison reveals missing relevant guidance. Keep the comparison as evidence and require the material effect to reach the existing canonical decision; do not require a permanent comparison manifest or new instruction registry.
- Owner-boundary issue: Memory describes a repeatable Planning trap. Require Planning to fix its deterministic relation resolver; let Memory warn while that defect exists, then re-evaluate the note instead of making Memory the resolver.

## Output

Report the shaped issue in this form:

- `recommended_action`: create issue / update issue / comment only / direct fix / dismiss
- `issue_kind`: bug / direction / review
- `hierarchy`: parent / child / cross-cutting / none
- `closure_shape`: parent outcome / bounded implementation leaf / later evidence / none
- `parent_or_refs`: issue, PR, lane, file, or evidence refs
- `problem_intent`: concise statement of the actual problem
- `intended_outcome`: final state that must become true
- `scope`: in scope and out of scope
- `acceptance`: observable final-state criteria
- `non_solutions`: what does not close the issue
- `evidence_required`: proof or review evidence for final completion
- `completion_rule`: when a PR may close it, or how a parent/evidence issue closes administratively
- `evaluation_boundary`: not-needed / definition-only / fresh-current-result-required, plus owner/criteria/source/sink/policy refs when applicable
- `remaining_gap_owner`: where any residual intent lives

## Rules

- Do not create a new issue when a direct fix, PR comment, or existing issue update is the smaller durable owner.
- Do not make a parent direction issue closable by a single useful slice unless final satisfaction is truly delivered.
- Do not schedule an implementation leaf whose whole stated outcome cannot credibly fit one coherent bounded PR plus immediate proof; split it first.
- Do not create follow-ups after knowingly under-delivering a leaf simply to manufacture closure.
- Do not use longitudinal evaluation language to relabel unfinished implementation, known defects, missing present-tense proof, or vague future evidence as closure-ready.
- Do not hold a complete bounded implementation leaf open for later evidence explicitly owned elsewhere.
- Later-evidence issues do not become implementation backlogs; route concrete findings to bounded implementation owners.
- Do not preserve history for its own sake; preserve only future-useful intent, proof, and continuation context.
- Do not generalize repo/provider/dogfooding evidence into package policy without an explicit portability argument.
- Keep repo-specific maintainer expectations here, not in shipped installed AW skills.
