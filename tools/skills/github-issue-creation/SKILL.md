---
name: github-issue-creation
description: Create GitHub issues for this repository from the current issue forms after issue shaping has established the problem, owner, scope, and closure boundary.
---

# GitHub Issue Creation

Use this repo-owned skill only when a new GitHub issue has already been selected as
the right durable action. Use `github-issue-shaping` first for nontrivial findings;
this skill owns creation mechanics, not product diagnosis or issue hierarchy.

## Procedure

1. Preserve the issue kind, hierarchy, **closure shape**, owner, scope, acceptance
   criteria, non-solutions, evidence requirements, and closure boundary produced by
   shaping. Do not reclassify the problem or closure shape here.
2. Inspect the current `.github/ISSUE_TEMPLATE/*.yml` form for that issue kind.
   The checked-in form is the authority for required fields and headings.
3. Translate the closure shape into the template without inventing a new lifecycle
   surface:
   - for a **parent outcome / direction**, state that accepted bounded children and
     dispositions plus immediate aggregate proof permit administrative closure;
     do not imply that one giant parent-closing PR is required;
   - for a **bounded implementation leaf**, make the completion rule explicit that
     one coherent bounded PR plus immediate deterministic/integration proof must be
     able to make the whole stated implementation outcome true. If the shaped issue
     cannot honestly satisfy that boundary, return to shaping and split it before
     creation;
   - for a **later evidence / review** issue, state explicitly that no product-code
     PR is required for closure and that concrete implementation findings route to
     the smallest bounded implementation owner rather than accumulating here.
4. Build a template-shaped body. The repo helper
   `.agentic-workspace/agent-aids/scripts/github-issue-body/new_github_issue_body.py`
   may be used when it is current and cheaper than constructing the form directly;
   it is a maintainer aid, not an independent source of issue semantics.
5. Create the issue through the authorized GitHub transport using the shaped title,
   body, and labels. Fill required fields with concrete information; do not create
   an issue containing `TODO` placeholders merely to reserve a number.
6. Inspect the returned issue once to confirm the intended title, labels, body,
   hierarchy, and closure boundary landed. Do not add a second issue, comment, or
   Planning record just to prove the creation step happened.
7. Refresh external intent or reconcile Planning only when the current AW route or
   owning Planning continuation says subsequent work depends on that refreshed
   state. Issue creation does **not** require an unconditional
   `external-intent refresh-github` + `reconcile` loop.

## Closure-Shape Examples

- A broad delegation outcome may be a parent while worker-entry and one supported
  launch/return path are separate PR-closeable implementation leaves; real-provider
  economic burden can remain a no-code later-evidence issue.
- A bounded adaptation implementation issue may close from current authority,
  mutation/no-retention, and fresh-resolution proof even while a separate evidence
  issue continues observing long-run payoff.

## Rules

- Preserve the current template headings.
- Use the issue kind selected by shaping; this skill does not turn all dogfooding
  findings into `review` issues or all architecture findings into `direction`.
- Preserve the closure shape selected by shaping; issue kind and hierarchy do not
  determine whether something is a parent, bounded implementation leaf, or later
  evidence owner.
- Do not create a scheduled implementation leaf whose whole outcome cannot
  credibly fit one coherent bounded PR plus immediate proof; return to shaping and
  split it first.
- Do not encode a parent as requiring one giant closing PR when accepted bounded
  children/dispositions can establish the outcome administratively.
- Do not turn a later-evidence issue into an implementation backlog; record its
  no-code closure rule and route concrete defects to bounded owners.
- Apply labels required by the current form/shaping result. If the helper and form
  disagree, the form wins and the helper should be repaired separately.
- Preserve completion-boundary fields such as `final_satisfaction`,
  `bounded_slice_success`, `partial_pr_may_close`, residual-intent ownership, and
  evidence required for final completion when the selected template defines them.
- Do not create a new issue when shaping concluded that a direct fix, existing issue
  update, or PR comment is the smaller durable owner.
