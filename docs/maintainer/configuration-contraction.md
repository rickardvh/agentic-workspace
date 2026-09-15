# Configuration authoring contraction

Implementation lane: #3297 under #3277. Independent acceptance and parent closure
remain separate from implementation and focused validation.

## Contracts and source/key inventory

Version 2 is the current shared/local authoring contract. Version 1 is bounded
former recognition. The build-time projection generates strict current schemas
from single-owned source definitions; invalid v2 never retries the v1 reader.
Removed/deprecated/read-only values cannot be created through the native writer,
even in a v1 file. Exact edits preserve unrelated former fields, comments, and
version bytes. A version transition is a separately scoped source-owner edit.

| Family | Current authoring / consumer | Exact editing and transition |
| --- | --- | --- |
| workspace.enabled, cli_invoke | Shared default, effective shared-local then checkout-local preference | Native writer; local true may override shared false availability, but never source trust, proof, module grants, or safety |
| workspace.agent_instructions_file, improvement_latitude | Repository selection/initiative policy | Native writer; no implicit instruction approval |
| workspace.workflow_artifact_profile | Repository artifact-source selection | Repository source authoring; native reader preserves unsupported-profile uncertainty |
| workspace.optimization_bias, advanced_features, maintainer_mode | Former recognition only | Preserve source; no current write/choice |
| modules.enabled | Real owner availability | Native writer; disabling never deletes state |
| system_intent.sources, preferred_source | Ordered repository source/preference | Native writer; explicit non-default ordering remains |
| assurance.instruction_revision, decision_record_revision/fallback/target | Exact repository trust and source selection | Existing source-owner admission; never derived from HEAD or routine edits |
| assurance.decision_delegations | Standing repository grant | Existing progressive native choice; never synthesized by setup |
| workspace.shared_config_path (local) | One existing shared-local source, then checkout-local precedence | Read dependency only; canonical writer cannot edit user-file paths or create include graphs |
| safety.* | Local command/review ceilings | Native writer; false/absence stay distinct |
| session_logging.enabled, path_mode | Opt-in local capture and path privacy | Native writer; deprecated redact_local_paths is former transition input only |
| clarification.mode | Advisory procedure preference | Native writer/read result; no waiver of required judgments |
| setup.* | Former continuation, not policy | Existing configuration defer/recovery owner; no current authoring |
| Verification domain families | #3301 | Domain schema/consumer contraction |
| modules.independent.* | #3302 | Exact descriptor preparation with separately approved grants |
| execution_posture.*, delegation*, runtime/handoff | #3303 | Provider-neutral requirement/transport/prior contraction |
| workflow_obligations, local_overlay.* | #3304 | Scoped instruction/Verification sources and lifetime disposition |
| local_memory.* | #3305 | Supported source selection or explicit preserved unavailability |
| update.*, payload.*, cli_compatibility.* | #3306 | Deliberate floors and artifact-derived facts |

The matrix separates recognized input, current authoring and native writability.
For a current field outside the exact writer, read-choice returns its schema and
source-owner route without an edit request. Former-only fields return a preserved
source-disposition route, not a supported current setting. No universal editor is
introduced. Shared/local TOML remain the only general authoring files.

The first boundary reduces inline fixed-property occurrences (excluding reusable
`$defs`) from 179 to 84 in shared authoring and 110 to 68 in local authoring.
This is a reproducible structural count, not a count of independent human choices:
dynamic keys and owner-validated extension schemas still require their assigned
child dispositions. Recognized former input remains broader by design. Native
editing covers 16 source/key pairs plus artifact-owned payload refresh; additional
current fields expose a read-only source route.

## Evidence and limits

Extend existing source-policy, exact-write and recovery cases. Retain one owner
case for the new current/former validation boundary; extend existing adapter
choreography for mixed-source byte preservation and current creation. Reuse
existing trust, diagnostic, source-drift and interrupted-publication evidence.
Generated schema/reference checks prove projection parity, not human approval.
Stop each PR at its assigned owner boundaries and leave aggregate acceptance to
independent review. Configuration byte reduction does not measure total operating
cost or satisfy the release lane.

## Verification ownership (#3301)

The four supported `manifest.toml#assurance` families (`proof_profiles`,
`domain_proof_lanes`, `requirements`, `subsystem_profiles`) are defined by
`packages/verification/src/repo_verification_bootstrap/contracts/assurance.schema.json`.
The native owner validates this table directly. The generator bundles these same
owner definitions into former recognition for offline reads; they do not reappear
in current shared authoring. Equal competing source values are still a conflict.
Transfer one family only after its destination is validated and its former source
is explicitly retired. Reading or generating schemas never changes source bytes.

`strict_closeout`, `default_level`, `agent_may_escalate` and `agent_may_deescalate` remain deliberate
repository proof floors. Binding requirements survive an attempted de-escalation.
`strict_closeout = true` requires a current task-bound Verification claim judgment
before completion, including work with no matching protocol. False does not waive
independently binding requirements. The existing claim-review request and exact
human answer or admitted delegation discharge this floor; config is never proof.
Proof results, currentness, review and waivers remain separate owner judgments.
Current manifest requirements reject `waiver`, `dismissal` and
`source_intent_current`. The former reader preserves these recorded fields without
admitting their claimed outcome; applicability never satisfies evidence or waivers.
Currentness must be established against the actual source and evidence owners.
The repository manifest removes its twelve static `source_intent_current = true`
assertions; source refs/revisions, evidence owners, selectors and blocking claims
remain unchanged. This retires the policy assertions, not the required outcomes
or their unresolved source/evidence admissions.

`closeout_postures` has no supported native destination: keep existing entries and
their unresolved claim boundary until a source owner judges each actual outcome.
The manifest rejects these entries rather than pretending a schema annotation
implements them. `classification_owner` and
`classification_source` likewise remain recognized former inputs, not supported
current knobs. Do not silently replace a repository classifier or required gate
with the native path matcher. Existing native requirements can express explicit
proof/review obligations after an owner validates the intended scope; this is not
an automatic prose or classifier translation.

Decision format/template/status conventions belong to scoped decision-authoring
instructions, not runtime trust. Invariant/risk registry references and test-data
policy belong to their maintained repository sources and applicable instructions
or explicit Verification requirements. Their former settings remain preserved,
with unsupported intent surfaced until an owner confirms a destination or
retirement. This implementation does not bulk-transfer them. Exact instruction
and decision revision consent, fallback selection and standing delegations remain
unchanged. No trust revision is refreshed from HEAD.

Evidence extends the existing transfer/collision test with an unsupported
closeout-posture preservation case; existing strategy tests cover proof floors,
source currentness and scope. This proves the bounded implemented destination,
not completion of all former-source migration or independent acceptance.

## Independent admissions and Assignment targets (#3302, #3303)

Select `modules.independent` through `configuration/read-choice/v1`, then set
`selected_owner` to the known linked owner. Only that descriptor is loaded. The
returned preparation supplies one exact `binding` over implementation and contract,
its requested capability/read footprint, and its settings schema. The proposal
preserves all existing grants, scope and settings, removes former duplicate pins,
and omits empty grant lists. New admissions start with no grants. The existing
explicit authorize-write decision approves the exact postimage; a binding hash
alone never grants an effect, read, claim or restriction. Both former pins remain
recognized until an authorized exact transition. Descriptor expansion or changed
implementation cannot inherit approval. Missing scope means explicit requests
only; missing settings means an empty object validated by the selected owner.

Effects and reads permit specific actions/sources; claims grant claim authority;
restrictions grant the ability to block specified scopes. None is derived from
installation. Scope and settings are repository choices. A refused subset may
make a module incompatible; preparation never fills it in to make execution work.
Unrelated admissions are preserved and their descriptors are not loaded. Invalid
settings or a stale proposed binding fail before source publication.

Current target authoring requires canonical `transports` and removes strength,
task_fit, capability_classes, context_capacity, model/provider labels and target
revision migration policy. The remaining target dimensions each have a purpose:
identity/revision/aliases bind a configured target; identity_status is a human
eligibility prohibition, not an observed availability fact; location is a boundary
hint; execution_guarantees advertise capabilities without proving host readiness;
forbidden_task_classes retain hard prohibitions with current scope judgment.
Confidence and provenance remain a human prior; cost/latency remain rough durable
preferences. No prior becomes admitted evidence. Former economics/evaluation data
is explicitly reported as unadmitted and cannot clear its configuration residual.

The existing transport decoder derives equivalent former methods and exact command
parameters. Missing/ambiguous transport payload remains unavailable; it does not
create a launch method. Former/shared-local/checkout-local omission and precedence
remain unchanged. Required Assignment, transport authority, human override, safety
and guarantee requirements remain separate. Repository requirements/preferences
stay provider-neutral; hard target prohibitions can coexist with them. Removed
ranking prose is not converted into capability guarantees.

Validation extends the selected-module settings journey with exact former-grant
preservation and a new absent-grant/stale-binding control. The existing work-class
journey now authors version 2 sources and continues to prove requirements before
preferences and relational independence. Current-schema projection preserves
conditional predicates instead of incorrectly closing partial `if` shapes.

## Guidance, local sources and package policy (#3304–#3306)

Current authoring has no workflow-obligation map, local guidance/high-risk maps,
local_memory family, empty handoff bag, runtime capability observations or module
update-source policy. There is no replacement generic policy bag. The existing
native owners remain responsible for applicability, source admission and proof.
A config residual names the required entry-level disposition; writing a candidate
instruction destination does not retire its source or admit completion.

| Former meaning | Destination / disposition |
| --- | --- |
| Shared advisory method | Applicable repository instruction/procedure, retaining advisory strength |
| Binding proof/check or review requirement | Supported Verification requirement or instruction check, retaining scope, force and its separate admission |
| Local guidance/privacy constraint | Existing local scoped instruction; retain protection and local provenance |
| Template fields/headings, source/runbook content | Original repository-owned file; instruction references it instead of copying a second definition |
| Unavailable CI, validation/drift state | Reobserve through current owner; never convert into standing guidance |
| Local substitute command | Local optional method only; cannot discharge stronger shared proof without its owner's authorization |
| Unresolved question | Existing responsible decision/continuation if still useful; explicit no-retention for obsolete observations is valid |

The mixed transition proof creates the candidate shared/local instructions through
the normal exact authorization path while old bytes remain. The source owner then
confirms each meaning and retires the old entries. Fresh relevant work consumes
both destinations, shared proof stays required, private policy stays local, the
original template stays intact and unrelated task words do not activate paths.
A second pass creates no old configuration. Unknown mandatory meaning remains a
blocker until supported and admitted; this is not a general prose translator.

All six local_memory fields are unsupported as native local topology controls:
`enabled`/`path` do not select repository Memory; `target_guidance_enabled` and
`user_guidance_root` concern scoped guidance/target owners;
`target_guidance_overlay_path` and `correction_events_path` concern operational
owner material. Each is former recognition only. Explicit source metadata reports
missing, empty, inaccessible/unconfined or present-unclassified material without
reading content or inferring a home directory. Repository Memory's manifest is a
distinct supported source, never a fallback. Source owner judgment is required for
meaningfulness, transfer, retention or retirement. No local content is copied,
deleted, moved or recreated, and existing uninstall controls are unchanged.

Current package policy has three fields: `payload.target_release` chooses an exact
artifact or source-current, `minimum_capabilities` supplies a floor, and `policy`
chooses advisory/before-work/before-claim enforcement. Former dogfood_latest=true
without an explicit target has the same artifact-following meaning as source-current;
an explicit target and capability floor always survive. Former update.modules
provenance remains unresolved at the package owner; it is not silently switched
to the coordinated artifact. Payload refresh writes only artifact-declared paths.

Current reader policy retains `minimum_reader_epoch` and
`required_reader_capabilities`. Contract identity and available capabilities are
derived from the actual reader. Former contract_schema still checks its explicit
pin, including rejecting an unsupported contract. Former minimum/exact versions,
source classes, target relations, command, capabilities/resources, enforcement and
resolution_policy retain their prior advisory or unresolved binding disposition;
no retired launcher is restored. A mismatch cannot become admitted by hiding the
old source. The invocation preference stays in workspace.cli_invoke.

The actual checkout audit found no workflow_obligations, local_overlay,
local_memory, update or cli_compatibility material to transfer. Its existing
payload target, floor and enforcement remain unchanged. Private target/policy
choices and all source-trust pins remain untouched. Existing unsupported assurance
intent remains visible; no aggregate acceptance or trust refresh is inferred.

## Aggregate implementation evidence and cost

Against baseline 5e35307320ed380b1a0fac093168fc08bfd933a0, fixed-property occurrences
outside reusable definitions contract from 179 to 45 shared and 110 to 41 local.
The metric is structural, not independent human decisions. The meaningful
subtractions are the parallel policy frameworks, stale observations and copied
module metadata; the remaining choices have distinct authority or preference
roles documented above. Ordinary unconfigured work still creates no setup state
or external probe. Detailed module discovery loads only one selected descriptor;
former local-source inspection touches only explicitly configured metadata.
Unconfigured local topology contributes no public Configuration/Memory detail.
Explicit former sources still expose observations and unresolved boundaries;
internal source binding is retained. Memory capture requests/results remain
public, while their internal contributions appear only through the composed
decision. The existing full-projection size bound remains unchanged.

Retain bounded tests with the current configuration, independent-admission,
Assignment, Verification, instruction and payload owners. Do not retain a test per
former field, migration transcript, personal-source inventory or a new CI lane.
Validation proves the implemented contracts and representative convergence; issue
acceptance, parent closure and total operating cost are separate judgments. This
stack includes no release publication and no self-review. Ready for independent
review after its focused checks; source-specific unresolved consent stays visible.
