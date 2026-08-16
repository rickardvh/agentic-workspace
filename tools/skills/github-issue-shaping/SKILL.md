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
3. Choose the issue shape:
   - `bug` for correctness, reliability, regression, or broken behavior;
   - `direction` for product direction, architecture, lanes, or bounded planning slices;
   - `review` for dogfooding friction, trust gaps, continuation gaps, and review findings.
4. Decide hierarchy:
   - parent direction / lane;
   - child slice / bounded follow-on;
   - cross-cutting proposal;
   - no new issue, only a comment or direct fix.
5. Preserve closure boundaries:
   - intended final outcome;
   - observable acceptance criteria;
   - non-solutions;
   - evidence required for final completion;
   - completion rule for whether a PR may close the issue.
6. If the issue depends on future or repeated evidence, shape the proof/evaluation split explicitly:
   - present-tense implementation proof remains required for deterministic behavior that should work now;
   - a longitudinal evaluation must name owner, criteria, evidence sources, report sinks, collection policy, and conclusion policy;
   - known defects, vague "collect more evidence" text, missing present proof, or unimplemented behavior are non-solutions and must not authorize closure;
   - the completion rule may reference a longitudinal evaluation only when the ordinary closure authority has a valid active evaluation owner and fresh/current result, or when the issue is explicitly only about creating that evaluation definition.
7. Keep useful slices honest:
   - name a useful first slice only if it does not imply final closure;
   - route residual intent to a clear owner;
   - avoid creating follow-up issues as a substitute for completing the stated outcome.
8. If creating the issue, hand off to `github-issue-creation` so the template, labels, and refresh/reconcile steps are preserved.
9. If updating an issue, preserve the existing template headings unless a human asks to reshape the issue format.

## Assumption Audit Examples

- Over-assumed issue: a one-off static comparison reveals missing relevant guidance. Keep the comparison as evidence and require the material effect to reach the existing canonical decision; do not require a permanent comparison manifest or new instruction registry.
- Owner-boundary issue: Memory describes a repeatable Planning trap. Require Planning to fix its deterministic relation resolver; let Memory warn while that defect exists, then re-evaluate the note instead of making Memory the resolver.

## Output

Report the shaped issue in this form:

- `recommended_action`: create issue / update issue / comment only / direct fix / dismiss
- `issue_kind`: bug / direction / review
- `hierarchy`: parent / child / cross-cutting / none
- `parent_or_refs`: issue, PR, lane, file, or evidence refs
- `problem_intent`: concise statement of the actual problem
- `intended_outcome`: final state that must become true
- `scope`: in scope and out of scope
- `acceptance`: observable final-state criteria
- `non_solutions`: what does not close the issue
- `evidence_required`: proof or review evidence for final completion
- `completion_rule`: when a PR may close it
- `evaluation_boundary`: not-needed / definition-only / fresh-current-result-required, plus owner/criteria/source/sink/policy refs when applicable
- `remaining_gap_owner`: where any residual intent lives

## Rules

- Do not create a new issue when a direct fix, PR comment, or existing issue update is the smaller durable owner.
- Do not make a parent direction issue closable by a single useful slice unless final satisfaction is truly delivered.
- Do not use longitudinal evaluation language to relabel unfinished implementation, known defects, missing present-tense proof, or vague future evidence as closure-ready.
- Do not preserve history for its own sake; preserve only future-useful intent, proof, and continuation context.
- Do not generalize repo/provider/dogfooding evidence into package policy without an explicit portability argument.
- Keep repo-specific maintainer expectations here, not in shipped installed AW skills.
