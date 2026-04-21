# Memory Metadata & Search Contract

Memory is a checked-in repository contract for anti-rediscovery knowledge. This document defines the metadata schema and the search/retrieval patterns for agents.

## Metadata Schema (manifest.toml)

Every memory note MUST be declared in `.agentic-workspace/memory/repo/manifest.toml`.

### Note Fields

| Field | Type | Purpose |
| --- | --- | --- |
| `note_type` | string | One of: `domain`, `invariant`, `runbook`, `recurring-failures`, `decision`, `current-overview`, `current-context`, `routing`, `routing-feedback`. |
| `authority` | string | `canonical` (source of truth), `advisory` (helpful guidance), `supporting` (context). |
| `audience` | string | `human`, `agent`, or `human+agent`. |
| `task_relevance` | string | `required` (always read for related tasks) or `optional` (load on demand). |
| `surfaces` | list[string] | Key terms or subsystems that trigger routing to this note. |
| `routes_from` | list[string] | Glob patterns (files/dirs) that trigger routing. |
| `stale_when` | list[string] | Glob patterns that indicate the note might need review if changed. |
| `memory_role` | string | `durable_truth` or `improvement_signal`. |

### Improvement Signal Fields

Used when a note exists because the repo is missing something (docs, tests, refactor).

| Field | Purpose |
| --- | --- |
| `preferred_remediation` | How to eliminate the need for this note (e.g., `test`, `refactor`). |
| `elimination_target` | The goal: `shrink`, `promote`, `automate`, `refactor_away`. |
| `improvement_note` | Concrete action needed in the codebase. |

## Search & Retrieval Contract

Agents should follow these patterns for "Habitual Pull":

### 1. Automatic Routing (Preferred)

Use `agentic-memory-bootstrap route --files <paths>` or `agentic-memory-bootstrap route --surface <terms>`.
This uses the manifest and `.agentic-workspace/memory/repo/index.md` to find the smallest set of relevant notes.

### 2. Keyword Search (Fallback)

Use `agentic-memory-bootstrap search "<query>"` to find notes containing specific keywords or patterns.

### 3. Sync Check

Use `agentic-memory-bootstrap sync-memory --files <paths>` to see which notes might be stale after your changes.

## Note Hygiene

- **No Overlap**: One fact has one primary home.
- **Residue Only**: Memory stores what is expensive to rediscover. If it's in the code or canonical docs, don't duplicate it in memory.
- **Weak Authority for Current**: Notes in `.agentic-workspace/memory/repo/current/` are for orientation and continuation, not durable facts.
