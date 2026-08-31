# Repo-owned evidence-backed requirements

Repo-owned evidence-backed requirements preserve a small observable consequence of durable intent after the issue that exposed it is closed. They extend the existing assurance, Verification, proof, scoped-instruction, and operating-decision path; they are not a second acceptance or policy engine.

The authority path is:

`intent or explicit repo policy -> assurance.requirements.<id> -> assurance/Verification evidence -> instruction require/prefer effect -> operating decision`

The source intent still owns why the requirement exists and the semantic outcome it serves. A passing requirement supplies evidence for its named target; it never proves the larger intent or replaces task acceptance, requirement grounding, intent feedback, or human judgment.

## Classes and effects

| Class | Existing effect | Missing or stale evidence |
| --- | --- | --- |
| `invariant` | `require` current deterministic evidence before the named claim | blocks only the matching claim and exposes the configured detail route |
| `current-evidence` | `require` current admitted evidence before the named claim | preserves failed, stale, unknown, unavailable, and invalid states |
| `guideline` | `prefer` an existing surface, skill, or operation | remains non-blocking when absent or incomparable |

Hard requirements must name their evidence owner and bounded detail/recovery route. Guidelines cannot carry enforcing force or blocked claims. All three classes bind the strongest current source-intent reference and revision. Marking that source revision non-current forces a relevant hard requirement back through review rather than leaving an immortal gate.

## Authoring

Use the existing assurance configuration. The ordinary scoped Markdown surface may reference the requirement from `checks` without duplicating its evidence or claim semantics.

```toml
[assurance.requirements.typed_exit]
level = "high"
applies_to_paths = ["src/agentic_workspace/**"]
required_evidence = ["typed_exit_fixture"]
force = "required-before-closeout"
blocking_claims = ["claim-work-complete"]
requirement_class = "invariant"
source_intent_ref = "SYSTEM_INTENT.md#trust"
source_intent_revision = "<current revision>"
source_intent_current = true
evidence_owner = "verification:typed-exit"
detail_route = "agentic-workspace proof --target . --select <route> --format json"
```

```markdown
---
paths:
  - src/agentic_workspace/**
checks:
  - requirement:typed_exit
---
```

The Markdown reference surfaces the named requirement. It does not manufacture a second check capability or hard gate; the assurance/Verification owner remains authoritative.

## Current-surface disposition

| Existing surface | Disposition |
| --- | --- |
| scoped Markdown `checks` | retained as the readable reference surface; named requirement refs now surface the assurance-owned requirement instead of creating a duplicate inline gate |
| assurance requirements | retained as repo authoring, applicability, evidence, review, and claim-pressure owner |
| Verification protocols/scenarios | retained as specialized evidence producers and review routes |
| proof profiles and evidence admission | retained as execution/admission/currentness owners |
| instruction clause IR | extended only with compact source/evidence metadata; remains the sole bounded effect compiler |
| workflow obligations | unchanged compatibility metadata; not used as the standing requirement registry |
| operating decision | unchanged as the sole action/claim/preference decision authority |

## Intent boundary

A repeated deterministic drift such as a typed validation error exiting successfully may be promoted from issue evidence into an invariant tied to the current trust intent. If that intent is re-scoped or superseded, the requirement revision must be refreshed, retired, or marked non-current.

A qualitative requirement such as “make the workflow understandable to a first-time maintainer” is not converted into a boolean gate merely for uniformity. Mechanical checks may support its evidence, while applicability, interpretation, residual risk, and final satisfaction remain agent- or human-owned.
