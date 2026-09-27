# Prepare, publish and verify an issue

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

## Recover an unknown issue number

Use the actor's retained response or activity evidence first. If it contains no
identity, inspect a bounded set of issues created in the target repository around
the attempted write, including closed issues. Compare author, creation time and
exact title/body/labels with the prepared packet; a title match alone is not enough.
Pass a supported candidate identity to the helper for verification. If no unique
identity can be established, report the creation as uncertain and retain the packet
and actor evidence. An empty search or ambiguous match does not authorize replay.
