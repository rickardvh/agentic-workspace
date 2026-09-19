# Native module capability contract

An independent module supplies deterministic domain semantics through the Rust
`agentic_workspace_core::independent_owner` API. Link its crate into a native core
assembly; Python, TypeScript, JSON and CLI clients all project that authority.
Python entry points and the former `module-capability/v2` schema are historical
source-maintenance fixtures, not installed extension or fallback execution paths.

## Small authoring boundary

| Declaration | Domain meaning |
| --- | --- |
| Registration owner/revision/api_version | Implementation identity and compatibility. |
| Registration describe | Lazily returns the domain descriptor, settings schema and required exact source paths. |
| Registration resolve | Deterministically observes bounded Context and returns current domain facts, blockers, request templates and an optional prepared operation. It is not an agent workflow callback. |
| Description capability | One capability-contract/v1 owner: domains, effect classes, typed requests and operations. Unknown owner fields fail closed. |
| Description configuration_schema | Durable module settings; no task answer or workflow cursor. |
| Description sources | Exact bounded repository sources, separately admitted for reading and freshly observed including absence. |
| Context | Current work, settings, observed sources and an optional typed owner request. |
| Resolution | Facts, blockers, requests and optional prepared operation; all may be empty. |
| PreparedOperation / Publication | Exact owner result and optional immutable owner-namespaced publication, admitted by core before effect. |

A facts-only owner returns `Resolution { facts, ..Default::default() }` and declares
no operation or publication. A read-only operation may return a bounded computed
result without state. An effectful operation additionally declares its own effect
class and prepares publication. Neither needs act/reconcile hooks, posture fields,
startup phases, report slots or mandatory skills.

The repository admits implementation/descriptor revisions, scope, exact reads,
effects, claims, restrictions and settings separately in `modules.independent`.
Linking and descriptor claims do not grant any authority. Configuration owns the
bounded authorization to change those grants. Missing, changed or revoked owner
admission cannot be replaced by a skill or client-built invocation.

## Optional procedure

A module may distribute ordinary SKILL.md plus relative resources. Register its
passive registry path using the repository's existing skill discovery contract;
no native owner-name switch or phase hook is needed. An optional procedure can
nominate a current request/action by generic exact identity. The owner validates
all submitted material. Removing the skill cannot remove domain restrictions.
A module need not ship any skill. A skill need not belong to a module.

## Currentness, effects and removal

Core binds requests and prepared operations to work, observed source revisions,
settings and repository admission. Direct callers use current start/invoke without
selecting a skill. Facts-only results create no custody. Immutable publication
uses existing attempts and recovery; unknown effects cannot be retried as new work.
Foreign-owner material remains evidence for that owner's separate admission.
Disabling/removing a module removes its contribution, not repository-owned outputs.

See [native owner authoring and recovery](maintainer/independent-native-owners.md)
and the separate [neutral fixture](../tests/fixtures/native-independent-owner/src/lib.rs).
Its assembly links the crate without adding either fixture identity to core.
Planning, Memory and Verification retain their current domain semantics; first-party
packaging does not confer independent authority or define a required module slot.
