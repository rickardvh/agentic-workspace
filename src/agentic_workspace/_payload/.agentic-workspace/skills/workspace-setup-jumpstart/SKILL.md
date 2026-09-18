---
name: workspace-setup-jumpstart
description: Help configure Agentic Workspace through current source-owned decisions, using ordinary start/invoke and preserving human policy.
---

# Configure Agentic Workspace

Use this skill when the user asks for configuration help or a current owner
routes a configuration concern here. Start with the desired behavior. Select
only the relevant concern; a setup request does not authorize enabling every
module, choosing providers, changing proof floors or replacing repository policy.

## Current native method

Use the configured AW invocation with `start --target . --task "<task>"
--projection full --format json` and repeated `--changed` paths. Select
`configuration_write.behavior_request` and supply its `concern`:
`instructions`, `diagnostics`, `assignment`, `modules`, `invocation`, or
`preferences`. Resolve that exact request through `start --input <request.json>`.
Select by the human outcome, not task-word matching. Carry required affected-owner
judgments as an exact current request set; never manufacture absent edit requests.

For an already-authorized Configuration action, use native `invoke --input
<action.json>` with the same target/task/changed context. Native admission checks
source, policy and work currentness. The writer attaches current selected behavior
observations after a supported write. A known failure to launch the native
process means no owner/effect entry; once it may have started, preserve uncertainty
and use current owner recovery. No Python subprocess wrapper is involved.

When the concern is already settled or has no durable value, do no work and
retain nothing. A configured command prefix such as `uv run agentic-workspace`
is an agent-facing invocation; do not pass it as one executable filename.

## Questions, writes and consequences

Discover the relevant current Configuration choice through `start`; use its exact
returned read/edit/creation request and schema. Compare the existing value with
the outcome and establish cheap current facts before asking an irreducible
question. Supply an existing human answer only when it authorizes this exact
current proposal. Explicit source delegations may admit ordinary agent choices;
capability enablement and delegation-policy changes keep their own authority.

Pass the returned exact action to native `invoke`. It returns
`effect_outcome`, `configuration_behavior`, actual `session_capture`
when available, and continuation/reentry. Interpret the **affected owner's**
observation: exact instruction delivery or read requirement, effective diagnostic
privacy and capture outcome, eligible Assignment configurations or missing
capabilities, or the selected module's admission/policy gap. Saved bytes alone do
not establish the human outcome. A configured invocation string is not an
executable-launch test; enabled logging is not successful capture.

Preserve confirmed source effects when continuation fails. Use fresh owner
observation or the exact recovery request, never replay the write to obtain a
post-write answer. A current observation can still leave semantic judgment or
proof unresolved. Unknown, disabled and unavailable are not successful adoption.
Do not broaden the writer into Assignment declarations, module manifests,
operational state, learned outcomes or trust pins just to remove a gap.

A deferred optional choice uses the existing `configuration.defer-choice` action
and `deferred_choices.resume_request`. It changes no human config and keeps only
one current source/key continuation. Changed context needs fresh judgment; an
old answer is not standing authorization. Settled or unrelated work needs no
configuration write or retained lesson.

## Package and host exposure

For artifact refresh, use `payload_discovery_request` and each current
`payload_choices` proposal. Only the exact authorized artifact-owned file is
written. Reobserve after interruption; byte convergence does not settle source
admissions, review or broader adoption intent.

For host discovery, use `skill_exposure_request` and its exact expose/remove or
recovery request. `.agents/skills` links point to canonical bundles: relative
symlinks on Unix, NTFS junctions on Windows. Canonical updates need no body copy.
Collisions and unsupported filesystems remain explicit gaps. Preserve the small
mixed-reader pointer. Reconcile moved Windows checkout junctions explicitly;
remove only authenticated matching exposure, preferably before payload teardown.
Retired owned links remain removable. Discovery/selection grants no authority.

## Source boundaries

Use the repository's configured invocation. Source checkouts build the native
pair with `cargo build --locked --workspace --bins`; installed clients use the
artifact-verified distribution. An unavailable runtime supplies no configuration
or Assignment permission. Follow the main skill's read-only fallback.

Repository policy remains stronger than local preferences. Preserve unrelated
keys, comments, files and owner state. Keep task judgments with Assignment,
learned evidence with its owner, and proof/claim judgments with Verification.
Module installation and descriptor changes grant nothing by themselves. Report
the established effect, actual consumer behavior, remaining judgment and exact
gaps separately. The method never claims independent review or task completion.
