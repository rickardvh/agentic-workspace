---
name: workspace-setup-jumpstart
description: Help configure Agentic Workspace through current source-owned decisions, using ordinary start/invoke and preserving human policy.
---

# Configure Agentic Workspace

Use this skill when the user asks for configuration help or a current owner
routes a configuration concern here. Start with the desired behavior. Select
only the relevant concern; a setup request does not authorize enabling every
module, choosing providers, changing proof floors or replacing repository policy.

## Selected executable method

Run this bundle's `prepare.py` with the configured `--native-cli`, repository
`--target`, exact `--task` and any `--changed` paths. It uses the existing native
request/action/result boundary; it does not parse config, edit sources, answer
owner questions or execute a primary-action loop.

- `--concern instructions|diagnostics|assignment|modules|invocation|preferences`
  obtains fresh current behavior and its remaining gaps from the responsible
  native owner. Select by the human outcome, not task-word matching.
- `--input <request.json>` carries an exact Configuration request, a current
  request set containing that concern and supplied affected-owner judgments, or
  one **already-authorized** Configuration action. Native source/work admission
  remains mandatory. It does not manufacture absent edit requests.
- `--no-change` is a successful zero-owner-call, no-retention disposition when
  the concern is already settled or a one-off observation has no durable value.
- `--expected-method-revision <returned revision>` rejects carried preparation
  after this helper or skill changes. Native owners separately revalidate source,
  policy, task and action currentness. A changed method is not a hot-patch permit.

Use `configuration_write.behavior_request` directly through ordinary native
`start` when the host does not run Python. The same current owner observations
and effect restrictions apply. The native writer also attaches selected behavior
observations after a supported write, so bypassing this optional helper does not
bypass the responsible owners.

## Questions, writes and consequences

Discover the relevant current Configuration choice through `start`; use its exact
returned read/edit/creation request and schema. Compare the existing value with
the outcome and establish cheap current facts before asking an irreducible
question. Supply an existing human answer only when it authorizes this exact
current proposal. Explicit source delegations may admit ordinary agent choices;
capability enablement and delegation-policy changes keep their own authority.

Pass the returned exact action to the method. It carries one invocation and
returns native `effect_outcome`, `configuration_behavior`, actual `session_capture`
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
