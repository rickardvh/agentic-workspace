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
2. Prepare the already shaped fields through the repository helper:

   ```text
   uv run --frozen --active --no-sync python .agentic-workspace/agent-aids/scripts/github-issue-body/new_github_issue_body.py --input-json <shaped-request.json>
   ```

   The request uses `agentic-workspace/issue-body-request/v1`, a `template`
   (`direction`, `bug`, or `review`), `title`, and `fields` keyed by current form
   IDs. Each field is `{"kind":"markdown","value":"<supplied text>"}` (also
   `text` or `scalar`). Optional `source_refs` carry shaped source IDs, URLs,
   or repository-relative paths. The helper reads the current form, prepares its
   headings/order/title prefix/default labels, and preserves the supplied values.
   It does not infer issue hierarchy or convert Planning records into semantics.
3. Resolve any `needs-input` diagnostics from shaping. The packet includes current
   field requirements/options; it supplies no missing dropdown choices, completion
   rules, or placeholders. Preserve the shaped parent, bounded-leaf, or later-evidence
   closure text explicitly, including fields whose form has generic default text.
   A missing or unsupported template, helper, dependency, or source is unavailable:
   report that limitation and use the Markdown fallback below.
4. Use only a fresh `prepared` result. It carries exact template/helper/input and
   local source identities. If preparation inputs may have changed, rerun with
   `--previous <prior-packet.json>`: it always prepares fresh and identifies stale
   dependencies; unrelated files do not invalidate the preparation. A comparison
   marked `current` covers local preparation inputs only. Supplied external URLs/IDs
   are explicitly unobserved and must be reobserved when subsequent work depends
   on their current state. Preparation grants no issue-write authority.
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

## Markdown Fallback

If executable preparation is unavailable, read the selected current
`.github/ISSUE_TEMPLATE/*.yml` directly and preserve its field headings/order,
title prefix, required fields, and default labels. Fill semantic fields only from
shaping, including the explicit closure rule. Return missing or ambiguous
information to shaping; do not choose the first dropdown option or generate
completion text. Review the completed body before the separately authorized
transport step. Python and its dependencies are repository-maintainer tooling,
not a shipped product runtime requirement.

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
