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

`default_level`, `agent_may_escalate` and `agent_may_deescalate` remain deliberate
repository proof floors. Binding requirements survive an attempted de-escalation.
Proof results, currentness, review and waivers remain separate owner judgments.

`closeout_postures` has no supported native destination: keep existing entries and
their unresolved claim boundary until a source owner judges each actual outcome.
The manifest rejects these entries rather than pretending a schema annotation
implements them. `strict_closeout`, `classification_owner` and
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
