---
name: workspace-setup-jumpstart
description: Help configure Agentic Workspace through current source-owned decisions, using ordinary start/invoke and preserving human policy.
---

# Configure Agentic Workspace

Use this procedure when the user asks for configuration help or the current
operating decision routes a configuration concern here. It is a judgment aid;
the responsible owner supplies current questions, operations and authority.

Start with the user's outcome, not a list of configuration fields. For example,
"use this checkout's build" concerns invocation; "use our existing instructions"
concerns the instruction source; "remember this repository's decisions" concerns
Memory's current admission and source choices. Discover only that owner's current
capability and requests. A high-level request is not permission to enable every
module, choose a provider, or replace repository policy.

Before an irreducible question, compare the existing value with the requested
outcome and inspect the named repository/runtime facts. Apply an inferable value
only when the current owner admits the existing human authorization or explicit
agent grant. A missing value alone is not a required configuration decision.
If no applicable concern remains, finish without creating configuration or state.

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
8. For package-managed payload refresh, submit the Configuration owner's
   `payload_discovery_request`. Its `payload_choices` name only files declared
   by the current artifact. Inspect each `refresh-available` row's exact proposal;
   an authorized answer permits that file's refresh through the existing writer.
   It does not authorize replacing unrelated repository, human or local state.
   Re-resolve after each write and follow an offered `recovery_request` after
   interrupted publication. A second pass with every row `current` needs no writes.
   Byte convergence does not settle unresolved semantic source dispositions or
   establish proof, review acceptance or completion of broader adoption intent.

## Current authoring and former sources

New sources use `schema_version = 2`. Version 1 is bounded source recognition,
not an alternative current authoring mode. The exact writer checks the selected
new value against the current schema while preserving unrelated former material,
comments and the existing version. Do not upgrade or retire a whole source as a
side effect of one setting change. Deprecated/read-only fields are not current
choices. A read-choice result without an edit request names the responsible
repository/local source authoring route; it grants no edit or trust approval.

Local enabled/cli_invoke override shared availability/invocation defaults, including
shared-local then checkout-local precedence. Independent proof, source admission,
module grants and local safety remain binding. Shared-local sources are read
inputs; the canonical writer does not acquire user-file write authority. Use
session_logging.enabled/path_mode for diagnostics and clarification.mode only
as an advisory preference. Use existing defer/recovery for continuation, not setup
fields. Never derive instruction or decision trust pins from HEAD or source hashes.

## Source and capability convergence

In a source checkout, run the documented `cargo build --locked --workspace --bins`
preparation. `scripts/run_agentic_workspace.py` selects that checkout's paired
`target/debug` binaries by default. A custom build directory uses an explicit
`AGENTIC_WORKSPACE_CORE_BINARY`; missing either binary requires rebuilding the
pair. An unavailable runtime supplies no Assignment or configuration permission.
Installed bindings continue to use their artifact-verified native distribution.

When a smaller canonical local source coexists with `agentic-workspace.local.toml`,
explicit canonical fields take precedence, while omitted choices remain derived
from the former source and visible as current dependencies. Preserve that source.
Do not claim retirement from a new filename or successful startup. Once its
meaning is represented in the current source, fresh resolution must work without
the former representation. Deprecated fields do not acquire new semantics from
this derivation; unresolved meaning remains with its current owner.

For a relevant independent module, use its returned `configuration_request` and
`configuration_schema`. Supply only the missing owner-specific settings through
the resulting Configuration edit; retain unrelated module admissions. Do not add
module-name branches or a fixed module questionnaire to this procedure.

Read Assignment's execution configurations for actual constructibility and its
named gaps. Configured internal-delegation support is a preference/declaration,
not evidence that the host session permits dispatch. Report visibility,
persistence, resumability and cleanup as unknown unless the current adapter
guarantees them. Discovery must not create provider work. Any real probe uses
the existing bounded Assignment/transport operation and its cleanup owner.

After a capability or source change, revisit the affected current request; never
replay a stale answer or rewrite settled unrelated choices. A second resolution
should need no writes for settled choices. Deferred optional choices stay with
their existing owner and do not force unrelated direct work through this skill.

Shared policy stays stronger than local preference. Preserve unrelated keys,
comments and files. Former source intent must be represented, explicitly
resolved, or remain an affected-behavior blocker before its source is retired.

Keep task answers with Assignment, learned outcomes with target evidence, and
proof strategy/evidence with Verification. Shared/local config holds durable
human choices and necessary environment declarations. Do not seed generic
obligations, copy package-repository policy, or tune human priors from outcomes.

Report the exact configuration effect and remaining concern. A successful edit
is not evidence that broader configure-once, proof or completion intent is met.
