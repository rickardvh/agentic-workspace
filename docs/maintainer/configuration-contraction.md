# Configuration baseline

Shared and local configuration each use one closed schema. Neither accepts a
version selector or unknown fields. Native admission validates these sources
before interpreting managed state; the Python maintenance reader uses the same
schemas. Missing configuration remains quiet and uses existing owner defaults.

## Source disposition audit for #3312

The baseline was ec242fc71666bded79837217710d6957a755f0e7. This is a
one-time implementation audit, not a product migration procedure or registry.
Private target identities and values are deliberately omitted.

| Populated source / removed field | Disposition | Destination and verification |
| --- | --- | --- |
| Verification manifest: workflow_obligation_refs=commit_after_proof / adapter_surface_refresh | already represented | Both requirements already live in AGENTS.md. Existing Verification requirements now cite AGENTS.md through authority_refs; evidence labels, force and claim boundaries are unchanged. |
| Repository config: schema_version | obsolete | Single closed grammar; actual source validated without a marker. |
| Present machine-local config: schema_version | obsolete | Local source validated against the same current local grammar. |
| Machine-local runtime.supports_internal_delegation, runtime.strong_planner_available | already represented | Existing canonical transports retain declared constructibility; native Assignment observes actual host availability. Old observations grant no availability. |
| Machine-local targets: strength, task_fit, capability_classes, context_capacity | migrate | Ignored local scoped target-selection instruction. Fresh instruction-owner resolution observed the source before the config fields were removed. These are human preferences, not execution guarantees. |
| Machine-local targets: model_family, provider | migrate | Identity metadata in the same ignored local instruction; canonical target IDs and revisions remain unchanged. |
| Machine-local target current_economic_evidence | obsolete | Its recorded observation was expired and explicitly unknown. No current economic evidence was established; guidance preserves that boundary without an evidence claim. |
| Harness shared config: schema_version | obsolete | Validated current shared fixture. |
| Harness workspace.optimization_bias | migrate | Scoped configuration-behavior instruction requests concise agent-readable output. |
| Harness workflow_obligations.config_closeout: summary, stage, scope_tags, commands, review_hint | migrate | Scoped instruction requires effective-config inspection and reporting before completion when relevant. Current owner inspection replaces the unavailable command recipe. |
| Harness local config: schema_version | obsolete | Validated current local fixture. |
| Harness runtime capability booleans | obsolete | Synthetic observations are not runtime facts. Scoped guidance requires current observation. |
| Harness handoff.prefer_internal_delegation_when_available=false | already represented | Both targets use explicit handoff transports; no internal dispatch preference is inferred. |
| Harness delegation.mode=auto | migrate | delegation.transport_authority=automatic; independent safety=false still prevents automatic execution. |
| Harness targets: strength, task_fit, capability_classes | migrate | Scoped target-selection preferences; hard prohibitions remain in config. |
| Harness targets: execution_methods | migrate | Canonical manual transports. The docs worker had no executable command, so no executable was invented; the instruction records manual handoff. |
| Harness escalation_target, human_control_modes | obsolete | Current Assignment judgment selects targets; canonical transport authority and independent human review remain. |
| Test-only recommended-control source excerpt | obsolete | Deleted acceptance/preservation fixture. Current repository commit-after-proof guidance already lives in AGENTS.md and scoped instructions. |
| Native independent-owner fixture: schema_version, revision, contract_revision | migrate | No config marker; one exact implementation/contract binding with identical grants, scope, reads and settings. |
| Embedded operation-conformance config: version markers | obsolete | The same generated operations use unversioned sources. |
| Selected-output conformance: workspace.optimization_bias | obsolete | The case tests field selection, now with the current improvement_latitude field. It establishes no repository style policy. |
| Guidance conformance: target revision_policy, strength, model_family, provider | obsolete | Synthetic identity/lifecycle cases retain stable IDs, revisions and aliases; no target-quality or model claim is needed. |
| Guidance conformance: execution_methods=internal | migrate | Canonical internal transport; peer process/provider and identity tests retain their own current declarations. |
| Guidance conformance: local_memory flags/root/path | obsolete / already represented | Synthetic enablement and external-root hints are retired. The current repository-local correction store already supplies the named path. Owner-internal cross-store transaction tests inject storage observations directly; they do not accept old human config. |
| Inline configuration test sources | migrate / obsolete | Current safety, proof, trust, invocation and transport tests use current syntax. Verification definitions live in its manifest. Acceptance/preservation-only journeys are deleted. |

All other populated repository and machine-local keys retain their current
owners: module enablement, instruction/artifact selection, initiative, invocation,
shared assurance floors, exact instruction/decision admission pins, payload target
and capability floor, system-intent selection, local safety, Assignment policy,
canonical transports, hard prohibitions, confidence provenance and cost/latency
human preferences. No trust revision is advanced to HEAD by this cleanup.

No populated cli_compatibility requirement was found in the actual repository or
machine-local sources. Its human-config negotiation and repair machinery is
removed. Independently current payload target/capability requirements remain with
Payload; configured invocation remains with Workspace. Installed artifact identity
and byte/provenance checks retain their existing owner.

## Deleted machinery

The two source-recognition schemas, their generated reference pages, and the
schema projection generator are deleted. The separate workflow-definition
compatibility schema, manifest, loader and generated reference are also deleted.
Its unused Python report, clause-adapter, closeout, and task-posture consumers are
deleted, together with the module registry model and report/schema fields.
The current schemas are canonical.
Native version dispatch, source residual bookkeeping, Assignment discharge of
residuals, local-source metadata migration views, root-local source derivation,
transport aliases, independent admission pin fallback and payload shorthand are
removed. The writer validates whole current postimages and preserves current
human comments, without a version upgrade path.

Python source readers no longer accept the removed configuration bags, target
aliases/observations, setup state, local overlays, workflow maps or merge-conflict
fallback defaults. Configuration reports and setup guidance describe current
sources and owners. The prerelease config-policy operation and its Python and
TypeScript writers, conformance cases, and generated adapters are deleted.
TypeScript config reads and identity writes use the authoritative host reader. Proof definitions are read from Verification's manifest;
recorded waivers and currentness are not policy input.

## Boundaries and validation

Current proof policy with a disabled Verification owner remains a completion
restriction. Local safety and human-review constraints remain independent.
Configuration grants neither proof nor source trust. Package payload refresh
continues to require exact artifact bytes and an authorized file proposal.

Validation must cover creation/read/edit, old-input rejection before state,
configured proof and safety, exact independent grants, payload currentness,
generated references and package consistency. Independent review is separate
from implementation validation and remains externally initiated.

## Search exceptions

Version fields in Planning, Memory, Verification manifests, operation envelopes,
Ownership and payload provenance identify current non-configuration contracts.
Their identity/admission semantics are unchanged. Semantic-route and Planning
source custody transitions are current non-configuration owners. Historical
release fragments, decision records and review reports retain their provenance.
Runtime admission wire names identify the executing artifact and pre-state
boundary; they no longer negotiate human-config reader requirements. Generic
operation/adapter compatibility fingerprints concern executable contracts, not
prerelease human configuration.

### Retained matches by owner

- `runtime_compatibility.rs`, its input schema, and native ingress retain the
  pre-state wire identity. They validate the current schema and report executing
  artifact facts; no configured epochs, version negotiations, or capability bags
  are read. Installed-state compatibility validates current artifact provenance
  and the Payload-owned floor.
- `native_routes.rs`, `native_planning.rs`, and corresponding `former` tests
  preserve source custody for current route/Planning records. They do not decode
  another human config grammar.
- `assurance_applicability.rs` labels unresolved semantic scope as `legacy_scope`;
  this is current task judgment over Verification-owned declarations, not a
  former configuration reader. Requirement `level` remains canonical;
  subsystem profile's `level` alias is removed in favor of `assurance_level`.
- `config.py`'s legacy delegation-outcome path and `session_logging.py`'s event
  recovery concern recorded evidence/logs. Neither supplies human configuration.
- `client.py` operation compatibility fingerprints and TypeScript package payload
  version-path handling concern executable/package contracts and installed
  payload custody. They do not accept prerelease human config.
- Internal Python target descriptors still carry observation/evidence attributes
  used by the current Assignment and guidance algorithms. Removed human knobs
  are never parsed into them; unknown observations remain unknown. They are not
  listed as supported configuration fields.
- `docs/reviews/`, archived Planning material, existing release fragments, and
  the current implementation audit record historical evidence. They are not
  setup or authoring instructions. The active delegation migration guide is
  deleted.

## Implementation validation

### Review correction: active producers

The initial audit overstated the inline-fixture migration. Independent review of
`38b561e0206e2db2316c58aaf7f6b463d8ccb62e` found the shared instruction-admission
helper still writing a config version marker, blocking invoke continuation.
The correction removes remaining current-config markers from that helper,
intent/adaptation/payload/proof fixtures, operation conformance setup, and external
consumer readiness. Non-config owner versions and explicit rejection fixtures
remain. The readiness negative now tests an unknown current-config section.

The model harness no longer branches on a local config version; its source-checkout
and configured-orchestration producers use the current invocation/transport fields.
Scoped named-requirement discovery and its existing test now use the Verification
manifest. Tests asserting removed config-owned overlays and scratch-retention knobs
are retired; current native instruction, Verification and resource guards remain.
The shared fixture correction passes the existing invoke-continuation guard across
all 12 surface/projection combinations, without adding duplicate regressions.
Scoped-instruction and source-checkout checks pass (21 tests); three focused harness
preparation/startup checks also pass. Required hosted merge validation is reported
on the PR for the pushed correction head, separately from this local evidence.

The first correction's hosted run passed the public integration guard and exposed
a later lifecycle serialization failure. The result adapter now converts nested
configuration dataclasses and tuples into JSON values. The existing skills-first
lifecycle suite passes all 18 tests, including initialization and upgrade with and
without a mirrored payload.

- Actual shared and ignored local sources load through the closed Python reader;
  native `start` reports both sources through the current configuration view.
  A parsed comparison against the baseline confirms that removing the shared
  version marker changed no shared policy value.
- Rust core library: 124 passed, 3 existing ignored interruption helpers. Native
  CLI: 6 passed, including direct operation without Python or Node.
- Native admission, startup, logging and assurance applicability: 196 passed.
- Native configuration/write, instruction, transport and handoff group: 150
  passed, 2 platform skips; the one unknown-strength failure was corrected and
  its focused regression passed. Unknown strength does not become a claimed
  capability.
- Final native Verification, Assignment, execution and rejected-input group:
  64 passed, 1 platform skip.
- Native proof producer and independent owner: 71 passed. Current configuration,
  defaults and pre-state reader group: 151 passed. Root guidance proof selection:
  2 passed. Current assurance projection: 11 passed.
- Adapter/module/instruction/decision checks: 177 passed in the bounded run;
  the current-schema rejection assertion was corrected and passed separately.
- Generated command packages, contract tooling, structured inventory, repository
  lint and type checks passed. Generated references and package mirrors were
  refreshed after removing the schemas, operations and report fields.

Broader exploratory checks are not reported as a full-suite pass. Remaining
failures outside this configuration proof include the maintainer skill wording
assertion, older session-log tests invoking retired public commands, the legacy
session-improvement index expectation, and an evaluation-launcher test invoking
retired `evaluation`. These are recorded validation limits, not substitutes for
current owner proof. No release or independent acceptance is claimed here.

Implementation validation, independent acceptance, issue completion and parent
release readiness are separate. This change is ready for independent review;
source-trust pins and unresolved source admissions remain unchanged. The current
Verification source-reconciliation owner returned no reconciliation obligations
for the changed shared config, requirement manifest and configuration document.
That observation does not grant independent review or completion authority.

Operating cost: this is one subtraction PR and adds no runtime migration scan,
registry or setup ceremony. Exploratory runs included retries and an interrupted
broad run; their counts are not additive proof. Total task wall time and token
cost were not instrumented, so test timings are not presented as total operating
cost.
