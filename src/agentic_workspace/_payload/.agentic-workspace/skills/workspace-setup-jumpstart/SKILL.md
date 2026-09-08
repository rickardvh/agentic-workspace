---
name: workspace-setup-jumpstart
description: Help configure Agentic Workspace through current source-owned decisions, using ordinary start/invoke and preserving human policy.
---

# Configure Agentic Workspace

Use this procedure when the user asks for configuration help or the current
operating decision routes a configuration concern here. It is a judgment aid;
the responsible owner supplies current questions, operations and authority.

1. Use the invocation already selected by the adapter. Run
   `start --target . --task "<configuration outcome>" --format json` and read its
   `decision_packet`. Preserve any required source-read or Planning request.
2. Inspect only the current concern and its named source. Derive technical facts
   before asking questions; a cheap current fact need not be persisted. If the
   requested outcome is already represented, leave configuration alone.
3. Use an exact owner-returned request. For a configuration edit, select the
   matching `configuration_write.requests` entry and supply the intended value.
   Run `start --input <request.json>` with the same context and `--format json`.
   The current writer supports an existing `workspace.cli_invoke` control in
   canonical shared or local TOML. An unavailable control remains an owner gap;
   this procedure does not authorize a direct edit or capability enablement.
4. Present only the returned irreducible decision, including the exact source,
   affected key and intended value. A previously explicit human answer may be
   supplied only if it authorizes that exact current proposal. Keep all binding
   fields; drift requires a fresh request. Guided use follows the same decisions.
5. Invoke only the returned `primary_action` through
   `invoke --input <action.json>` with the same context and `--format json`.
   Resolve again to verify the result. Use a returned recovery request if a write
   was interrupted. A successful write grants no continuing source custody.
6. A returned `defer` answer changes no configuration and grants no readiness.
   On resume, resolve the concern from current sources; do not replay a stale
   answer or create setup history in local config. Report an unavailable durable
   resume operation honestly rather than fabricating one.

Shared policy stays stronger than local preference. Preserve unrelated keys,
comments and files. Former source intent must be represented, explicitly
resolved, or remain an affected-behavior blocker before its source is retired.

Keep task answers with Assignment, learned outcomes with target evidence, and
proof strategy/evidence with Verification. Shared/local config holds durable
human choices and necessary environment declarations. Do not seed generic
obligations, copy package-repository policy, or tune human priors from outcomes.

Report the exact configuration effect and remaining concern. A successful edit
is not evidence that broader configure-once, proof or completion intent is met.
