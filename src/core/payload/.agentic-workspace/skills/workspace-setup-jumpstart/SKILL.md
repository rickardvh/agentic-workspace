---
name: workspace-setup-jumpstart
description: Resolve an AW setup or refresh request, apply an authorised configuration change, and verify the resulting behaviour.
---

# Resolve the setup concern

Use this method when the user asks to configure AW or `start` reports setup or
refresh needing attention. Inspect the current Configuration request and its
installed guidance. Infer safe choices from repository policy; ask only for a
decision the user still needs to make. Apply the exact supported change and check
whether the intended consumer now works. Saved configuration bytes alone do not
prove that result. Preserve explicit exclusions and unrelated settings, then
return to the original task.

Load only needed detail: [behaviour](references/selection.md),
[authorisation and verification](references/consequences.md),
[package assessment](references/package.md), or
[unavailability and recovery](references/boundaries.md).
