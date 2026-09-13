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
   If the canonical source is absent, first submit the returned
   `configuration_write.creation_discovery_request` through `start` with the same
   context. Select the matching `configuration_write.creation_requests` entry
   from that response. This read-only discovery creates no source and does not
   recommend enabling a capability; source or policy drift requires a fresh request.
   Run `start --input <request.json>` with the same context and `--format json`.
   The current writer supports canonical shared/local invocation, shared module
   selection, instruction and intent source choices, and local command/review
   safety ceilings. The returned schema binds each field to its source and type.
   Existing bytes are preserved; absent sources require exact creation authority.
   An unavailable control remains an owner gap; this procedure supplies no
   blanket edit or capability-enablement authority.
4. Present only the returned irreducible decision, including the exact source,
   affected key, intended value and complete proposed source. A previously explicit human answer may be
   supplied only if it authorizes that exact current proposal. Keep all binding
   fields; drift requires a fresh request. Guided use follows the same decisions.
5. Invoke only the returned `primary_action` through
   `invoke --input <action.json>` with the same context and `--format json`.
   Resolve again to verify the result. Use a returned recovery request if a write
   was interrupted. A successful write grants no continuing source custody.
6. A returned `defer` answer changes no human configuration. Invoke its exact
   `configuration.defer-choice` action when the unresolved choice needs to survive
   this interaction. The configuration owner stores only that current choice and
   its binding under `.agentic-workspace/local/configuration/`, using existing
   attempt custody. Fresh resolution exposes `configuration_write.deferred_choices`.
   Use the returned `resume_request` to obtain a current postimage and decision;
   `changed-context` requires fresh judgment. No old answer is standing authority.
   A successful corresponding edit consumes the owner continuation. One current
   continuation per source/key replaces questionnaire history.
7. Current shared policy can delegate an exact configuration source to the acting
   agent for ordinary durable choices. Apply already-authorized choices first;
   capability enablement and delegation-policy editing still require the exact
   human answer. Never create a grant just to automate setup.

Shared policy stays stronger than local preference. Preserve unrelated keys,
comments and files. Former source intent must be represented, explicitly
resolved, or remain an affected-behavior blocker before its source is retired.

Keep task answers with Assignment, learned outcomes with target evidence, and
proof strategy/evidence with Verification. Shared/local config holds durable
human choices and necessary environment declarations. Do not seed generic
obligations, copy package-repository policy, or tune human priors from outcomes.

Report the exact configuration effect and remaining concern. A successful edit
is not evidence that broader configure-once, proof or completion intent is met.
