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
| `promotion` | string | Required rule for promoting the fact to stronger authority. |
| `demotion_or_expiry` | string | Required rule for retiring or demoting the fact. |
| `status` | string | `active`, `candidate`, or `deprecated`. |

## Validation Contract

`agentic-memory doctor --target <repo>` validates `manifest.toml` as a typed TOML contract. Invalid TOML, malformed tables, scalar values where arrays are required, non-boolean booleans, invalid enum values, incomplete improvement-signal lifecycle metadata, and incomplete durable facts produce `memory-manifest` diagnostics.

Agents may edit manifest entries, but they should keep values inside this contract and run doctor or the workspace doctor before claiming completion.

## Search & Retrieval Contract

Agents should follow these patterns for "Habitual Pull":

### 1. Automatic Routing (Preferred)

Use `agentic-memory route --files <paths>` or `agentic-memory route --surface <terms>`.
This uses the manifest and `.agentic-workspace/memory/repo/index.md` to find the smallest set of relevant notes.

### 2. Keyword Search (Fallback)

Use `agentic-memory search "<query>"` to find notes containing specific keywords or patterns.

### 3. Sync Check

Use `agentic-memory sync-memory --files <paths>` to see which notes might be stale after your changes.

## Note Hygiene

- **No Overlap**: One fact has one primary home.
- **Residue Only**: Memory stores what is expensive to rediscover. If it's in the code or canonical docs, don't duplicate it in memory.
- **Weak Authority for Current**: Notes in `.agentic-workspace/memory/repo/current/` are for orientation and continuation, not durable facts.

