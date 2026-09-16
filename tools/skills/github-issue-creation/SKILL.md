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

   When native route/procedure detail is available, consume the selected
   `github/issues/create` executable material identities from the existing route
   result. Missing material blocks the executable path. External Python/runtime
   availability remains explicitly unknown to passive discovery; establish it
   through the existing invocation environment or use the Markdown fallback.
   Reobserve changed material before preparing; the helper's exact-input check
   additionally binds the particular form and supplied shaped sources.

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
4. For the compound path, add `--repository <owner/repo> --task "<current work>"`
   to preparation. The resulting `issue-creation-request/v1` carries one exact
   `material.write` (title/body/labels), preparation identities and request ID.
   Before a deferred effect, pass that packet as `--creation-request`: only a
   still-current `prepared` result may proceed. Changed task/form/helper/shaped
   material requires new preparation and renewed authorization. Discovery and
   preparation grant no GitHub write authority.
5. The already-authorized host/actor sends `material.write` through its GitHub
   transport. Preserve the packet and return an external report with its
   `request_id`, `outcome` (`confirmed`, `rejected-before-effect`, or `uncertain`)
   and exact issue `number` when known. Rejection requires `effect_attempted:
   false` and a reason from the actor; a timeout or unsuccessful process is not
   evidence that GitHub rejected before effect.
6. Resubmit with `--creation-request <packet.json> --external-result <report.json>`.
   The helper performs one read of the exact issue through the existing `gh`
   transport, validates identity/title/body/labels against the request, and returns
   the observed issue or bounded recovery. It never creates an issue on resume.
   Missing identity, lost response, or mismatch requires transport reobservation;
   never replay creation merely because continuation failed. Preserve actor
   evidence outside disposable carriage when recovery needs it; no local digest
   supplies GitHub exactly-once semantics or external authentication.
7. Default continuation is none. Only when an existing current owner actually
   depends on this result, supply its separately authorized exact request through
   `--continuation-input` and the current `--native-cli`. The agent supplies any
   semantic external reference the owner requests; the helper does not synthesize
   Planning ingestion or create a plan. The native owner revalidates the request.
   Confirmed creation remains committed if material drift or owner continuation
   fails. Return the created identity and remaining owner gap, not a retry-create
   instruction. No unconditional external-intent/Planning refresh is required.

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

- A broad delegation parent outcome permits administrative closure from accepted
  children and aggregate proof, while worker-entry and one supported
  launch/return path are separate PR-closeable implementation leaves; real-provider
  economic burden can remain a later-evidence issue requiring no product-code PR.
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
