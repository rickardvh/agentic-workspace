# Memory Metadata & Search Contract

Memory is a checked-in repository contract for anti-rediscovery knowledge. This document defines the metadata schema and the search/retrieval patterns for agents.

## Metadata Schema (manifest.toml)

Every memory note MUST be declared in `.agentic-workspace/memory/repo/manifest.toml`.

### Note Fields

| Field | Type | Purpose |
| --- | --- | --- |
| `note_type` | string | Required non-empty note type such as `domain`, `invariant`, `runbook`, `recurring-failures`, `decision`, `workflow-policy`, `version-marker`, `routing`, or `routing-feedback`. |
| `canonical_home` | string | Required path to the note's canonical home. Use the note path unless the manifest explicitly routes to a canonical non-memory document. |
| `authority` | string | `canonical` (source of truth), `advisory` (helpful guidance), `supporting` (context). |
| `audience` | string | `human`, `agent`, or `human+agent`. |
| `summary` | string | Optional compact routing or durable-fact summary. |
| `canonicality` | string | `agent_only`, `candidate_for_promotion`, `canonical_elsewhere`, or `deprecated`. |
| `task_relevance` | string | `required` (always read for related tasks) or `optional` (load on demand). |
| `subsystems` | list[string] | Package, subsystem, or domain labels for routing. |
| `surfaces` | list[string] | Key terms or subsystems that trigger routing to this note. |
| `applies_to` | list[string] | Paths, subsystems, commands, or surfaces this note covers. |
| `use_when` | list[string] | Conditions under which an agent should load or apply this note. |
| `routes_from` | list[string] | Glob patterns (files/dirs) that trigger routing. |
| `stale_when` | list[string] | Glob patterns that indicate the note might need review if changed. |
| `evidence` | list[string] | Source files, checks, commits, or docs that ground the note. |
| `related_validations` | list[string] | Commands or checks that support the note's trust boundary. |
| `memory_role` | string | `durable_truth` or `improvement_signal`. |

### Improvement Signal Fields

Used when a note exists because the repo is missing something better than memory (docs, skill, script, test, validation, refactor, or code).

| Field | Type | Purpose |
| --- | --- | --- |
| `symptom_of` | string | One of `workflow_friction`, `guidance_drift`, `missing_guardrail`, `architecture_friction`, or `operator_complexity`. |
| `preferred_remediation` | string | How to eliminate the need for this note: `docs`, `skill`, `script`, `test`, `validation`, `refactor`, or `code`. |
| `improvement_candidate` | boolean | Marks the note as a candidate for future promotion, automation, or deletion. |
| `improvement_note` | string | Concrete action needed in the codebase. |
| `elimination_target` | string | The goal: `shrink`, `promote`, `automate`, or `refactor_away`. |
| `promotion_target` | string | Stronger canonical owner, if known. |
| `promotion_trigger` | string | Concrete signal that should move the note to the stronger owner. |
| `retention_after_promotion` | string | Intended post-promotion memory shape: `retain`, `shrink`, `stub`, or `delete`. |
| `retention_justification` | string | Required alternative when the note is an improvement signal but no remediation metadata is available yet. |
| `config_treatment` | string | One of `promote`, `cleanup`, `retain`, or `no_action`. |
| `config_note` | string | Short explanation of the config or posture cue behind `config_treatment`. |

### Durable Fact Fields

Compact durable facts live under `[durable_facts."<id>"]`. Use them only when a small structured record saves repeated note reads.

| Field | Type | Purpose |
| --- | --- | --- |
| `summary` | string | Required compact fact. |
| `owner` | string | Required owning module, subsystem, or surface. |
| `authority_class` | string | `canonical`, `advisory`, or `supporting`. |
| `route_keys` | list[string] | Query/surface terms that should pull this fact. |
| `touched_surfaces` | list[string] | File patterns that should pull this fact. |
| `evidence` | list[string] | Required anchors proving the fact. |
| `affected_decisions` | list[string] | Decision dimensions this fact can inform. |
| `note_ref` | string | Optional larger note or section for bounded drill-down. |
| `promotion` | string | Required rule for promoting the fact to stronger authority. |
| `demotion_or_expiry` | string | Required rule for retiring or demoting the fact. |
| `promotion_target` | string | Existing stronger owner for deterministic recurrence. |
| `promotion_trigger` | string | Evidence threshold that activates promotion review. |
| `preferred_remediation` | string | Smallest correct-by-design remediation. |
| `elimination_target` | string | Condition the stronger owner should eliminate. |
| `retention_after_promotion` | string | Post-proof shape: `retain`, `shrink`, `stub`, or `delete`. |
| `status` | string | `active`, `candidate`, or `deprecated`. |

Post-promotion shape is not selected from a caller-supplied pass flag. A non-`retain` disposition requires a typed stronger-owner resolution that binds the exact fact and revision to the current owner decision plus an admitted, passing `agentic-workspace/proof-receipt/v1`. `retention_after_promotion = "retain"` remains meaningful after remediation: use it when the implementation fix does not make the durable rationale cheap or mechanically equivalent to rediscover.

## Current validation and retrieval

Use current Memory detail returned by `agentic-workspace start --target <repo> --task "<task>" --format json`, with known changed paths. Follow exact route, declaration or disposition requests rather than guessing a module CLI command.

Malformed or stale metadata remains an owner-reported gap. The current owner validates declaration and mutation requests; prose metadata examples do not authorize direct writes to managed state. Consult the workspace startup and correction skills when capturing or promoting durable knowledge.

Read only relevant routed notes. After changes, reconcile affected declarations and disposition through their current owner. A keyword match aids discovery but cannot decide semantic relevance, retention or proof.

## Note Hygiene

- **No Overlap**: One fact has one primary home.
- **Residue Only**: Memory stores what is expensive to rediscover. If it's in the code or canonical docs, don't duplicate it in memory.
- **Weak Authority for Current**: Notes in `.agentic-workspace/memory/repo/current/` are for orientation and continuation, not durable facts.
