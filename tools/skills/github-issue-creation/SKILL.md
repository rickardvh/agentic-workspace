---
name: github-issue-creation
description: Create GitHub issues from this repo while preserving current issue-template fields, labels, and source-owned intent.
---

# GitHub Issue Creation

Use this repo-owned skill before creating GitHub issues for this repository.
For any nontrivial issue or refinement, use `github-issue-shaping` first; this skill owns template mechanics and must not bypass the assumption, ownership, scope, or closure audit.

## Required Shape

1. Inspect or use the current `.github/ISSUE_TEMPLATE/*.yml` forms instead of hand-authoring an ad hoc issue body.
2. Pick the matching template kind:
   - `direction` for product direction, architecture, lanes, and bounded planning slices.
   - `bug` for correctness, reliability, or regression problems.
   - `review` for dogfooding friction, review gaps, trust gaps, and continuation or handoff friction.
3. Construct the body directly from the selected YAML form, preserving its headings and required fields.
4. Create the issue with `gh issue create`, using the template's labels and the shaped title/body.
5. Treat the resulting GitHub issue as current external source intent on the next `start`; do not recreate deleted refresh/reconcile commands.

## Rules

- Preserve the template headings in the body.
- Apply the labels emitted by the helper.
- Fill required fields with concrete evidence; do not leave `TODO` values in a created issue.
- Use `review` for dogfooding findings unless the finding is clearly a product direction or bug.
- Preserve the completion boundary fields:
  - `final_satisfaction`: what must be true before the issue is complete.
  - `bounded_slice_success`: useful partial progress that may land without final closure.
  - `partial_pr_may_close`: default `no` for direction/proposal work unless the issue owner says otherwise.
  - `required_follow_up_owner`, `required_residual_intent`, and `evidence_required_for_final_completion`: where remaining intent lives and what proves final completion.
- If the helper output and the YAML template disagree, trust the YAML template and fix the helper.
