---
name: github-issue-creation
description: Create GitHub issues for this repository from the current issue forms after issue shaping has established the problem, owner, scope, and closure boundary.
---

# GitHub Issue Creation

Use this repo-owned skill only when a new GitHub issue has already been selected as
the right durable action. Use `github-issue-shaping` first for nontrivial findings;
this skill owns creation mechanics, not product diagnosis or issue hierarchy.

## Procedure

1. Preserve the issue kind, owner, scope, acceptance criteria, non-solutions, and
   closure boundary produced by shaping. Do not reclassify the problem here.
2. Inspect the current `.github/ISSUE_TEMPLATE/*.yml` form for that issue kind.
   The checked-in form is the authority for required fields and headings.
3. Build a template-shaped body. The repo helper
   `.agentic-workspace/agent-aids/scripts/github-issue-body/new_github_issue_body.py`
   may be used when it is current and cheaper than constructing the form directly;
   it is a maintainer aid, not an independent source of issue semantics.
4. Create the issue through the authorized GitHub transport using the shaped title,
   body, and labels. Fill required fields with concrete information; do not create
   an issue containing `TODO` placeholders merely to reserve a number.
5. Inspect the returned issue once to confirm the intended title, labels, and body
   landed. Do not add a second issue, comment, or Planning record just to prove the
   creation step happened.
6. Refresh external intent or reconcile Planning only when the current AW route or
   owning Planning continuation says subsequent work depends on that refreshed
   state. Issue creation does **not** require an unconditional
   `external-intent refresh-github` + `reconcile` loop.

## Rules

- Preserve the current template headings.
- Use the issue kind selected by shaping; this skill does not turn all dogfooding
  findings into `review` issues or all architecture findings into `direction`.
- Apply labels required by the current form/shaping result. If the helper and form
  disagree, the form wins and the helper should be repaired separately.
- Preserve completion-boundary fields such as `final_satisfaction`,
  `bounded_slice_success`, `partial_pr_may_close`, residual-intent ownership, and
  evidence required for final completion when the selected template defines them.
- Do not create a new issue when shaping concluded that a direct fix, existing issue
  update, or PR comment is the smaller durable owner.
