---
name: workspace-setup-jumpstart
description: Resolve setup or configuration, preserve evidenced repository working rules, and verify the intended consumer.
---

# Resolve the setup concern

Use this method when the user asks to configure AW or `start` reports setup or
refresh needing attention. Select a due job through the request in current
`setup_context`. For explicit setup when ordinary entry is quiet, resolve this
request in the same work context:

```agentic-owner-reference
{"kind":"request","owner":"configuration","id":"configuration/setup-job/v1"}
```

Answer its returned exact reference with the requested `job` and, when required,
`concern`. This reads the selected setup choices; it does not execute a change.
Infer choices from repository policy; ask only for a decision the user still
needs to make. Apply the exact supported change and check
whether the intended consumer now works. Saved configuration bytes alone do not
prove that result. Preserve explicit exclusions and unrelated settings, then
return to the original task.

During requested customisation, a relevant setup assessment or an explicit
enduring correction, also consider repository working rules evidenced by current
instructions, scripts and user intent. Use [working rules](references/working-rules.md)
to connect a necessary prerequisite to the action that needs it. Reuse adequate
existing guidance; do not survey prerequisites on every entry or package refresh.
Repository preparation does not belong in Configuration readiness records.

Load only needed detail: [behaviour](references/selection.md),
[authorisation and verification](references/consequences.md),
[package refresh and assessment](references/package.md), or
[unavailability and recovery](references/boundaries.md).
