---
name: github-issue-creation
description: Prepare and verify a new GitHub issue from the current repository form after its scope and closure rule have been shaped.
---

# Create a shaped repository issue

Use this procedure only after [issue shaping](../github-issue-shaping/SKILL.md)
has selected a new issue. Keep its kind, hierarchy, scope, acceptance criteria,
evidence and closure rule. Preparation does not authorize a GitHub write.

Check that the supplied closure rule matches the intended work:

- A **parent outcome** allows administrative closure from accepted children and
  aggregate evidence; it need not have one giant closing PR.
- A **bounded implementation leaf** must fit one coherent bounded PR and immediate
  proof. Return to shaping if it needs splitting.
- A **later evidence** issue states its no-code closure rule. No product-code PR is
  required; route concrete defects to bounded implementation owners.

## Prepare the exact body

Follow [preparation and publication](references/prepare-and-publish.md) for the
helper command, request fields, current-form checks and external result protocol.
The helper reads `.github/ISSUE_TEMPLATE/` and prepares exact title, body and labels
from shaped values. Resolve missing fields with shaping; do not invent dropdown
choices or completion text. Preserve template headings and explicit closure fields.

If the helper or runtime is unavailable, that reference's Markdown fallback uses
the current form directly. A missing form or unresolved semantic field blocks
publication. The current form wins if the helper disagrees with it; report the
helper defect for repair.

## Publish and confirm

The authorized actor publishes the prepared title/body/labels and supplies the
external result to the helper. Confirm the exact issue identity and observed body
before claiming creation succeeded. If a response is lost or differs, inspect the
existing result through the recovery path; do not create another issue.

Stop after confirmed creation unless a current component has a separately
authorized continuation request. A continuation failure leaves the issue created;
report its identity and the remaining gap. Do not replay creation or refresh
Planning unconditionally.
