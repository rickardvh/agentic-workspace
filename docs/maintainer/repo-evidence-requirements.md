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

## Measurable evidence

A `current-evidence` requirement may own a deliberately small measurable condition. The condition fixes the metric, unit, comparator, threshold, aggregation, minimum samples, subject/fixture revision, environment, and evidence-source revision. The compact evidence record supplies observations; it cannot change the condition.

```toml
[assurance.requirements.selected_latency.measurement]
kind = "agentic-workspace/measurement-requirement/v1"
evidence_label = "cold_median"
metric = "selected-read-latency"
unit = "seconds"
comparator = "lte"
threshold = 2.0
tolerance = 0.1
aggregation = "median"
minimum_samples = 5
subject = "planning-record-selected-read"
subject_revision = "fixture-r1"
environment = "windows-ci-python-3.13"
source_revision = "benchmark-r1"
producer_command = "python scripts/measure_selected_latency.py --compact"
excluded_costs = ["environment bootstrap"]
```

The corresponding `.agentic-workspace/verification/assurance-evidence-records.json` item uses `agentic-workspace/measurement-evidence/v1`. It repeats the comparison and freshness identities, binds `requirement_revision` to the source-intent revision, and records `observed_value`, `sample_count`, `status`, and an exact `detail_ref`. Ratio evidence additionally names a control subject/revision and `baseline_value`; deterministic zero-residue evidence uses `aggregation = "count"`, `comparator = "eq"`, `threshold = 0`, and `environment = "none"`.

AW evaluates the observation against the requirement-owned threshold. Identity changes produce stale evidence; malformed values produce invalid evidence; failed, unknown, and unavailable results remain distinct. Current matching evidence is reused with no measurement action. Only a relevant requirement with missing or non-current evidence selects its source-owned `producer_command` through the ordinary proof executor. Raw samples and verbose environment output stay behind the evidence owner’s detail reference.

Measurement remains evidence, not semantic intent authority. The current source intent or grounded requirement owns why the threshold applies; superseding that source makes the derived measurement requirement non-current. A passing observation satisfies only its named evidence contract. Intent feedback such as #2569 may promote repeated deterministic drift into a new source-bound measurable requirement, but the producer cannot create or rewrite that threshold. See #1556, #2569, and `.agentic-workspace/system-intent/intent.toml` for the adjacent intent-grounding and feedback boundaries.

## Current-surface disposition

| Existing surface | Disposition |
| --- | --- |
| scoped Markdown `checks` | retained as the readable reference surface; named requirement refs now surface the assurance-owned requirement instead of creating a duplicate inline gate |
| assurance requirements | retained as repo authoring, applicability, measurable-condition, evidence, review, and claim-pressure owner |
| Verification protocols/scenarios | retained as specialized evidence producers and review routes |
| proof profiles and evidence admission | retained as execution/admission/currentness owners |
| instruction clause IR | extended only with compact source/evidence metadata; remains the sole bounded effect compiler |
| workflow obligations | unchanged compatibility metadata; not used as the standing requirement registry |
| operating decision | unchanged as the sole action/claim/preference decision authority |

## Intent boundary

A repeated deterministic drift such as a typed validation error exiting successfully may be promoted from issue evidence into an invariant tied to the current trust intent. If that intent is re-scoped or superseded, the requirement revision must be refreshed, retired, or marked non-current.

A qualitative requirement such as “make the workflow understandable to a first-time maintainer” is not converted into a boolean gate merely for uniformity. Mechanical checks may support its evidence, while applicability, interpretation, residual risk, and final satisfaction remain agent- or human-owned.

## Initial dogfood policy

The first repo-owned catalogue is intentionally smaller than the issue history that motivated it. It promotes observable outcomes with current owners and maintained fixtures; historical issue numbers are provenance, never runtime authority.

### Typed CLI and selector contract

`typed_cli_selector_contract` merges typed result/process/session agreement with selector authority and fail-fast behavior. A typed usage, validation, or failed direct-action result declares and returns the same nonzero status. Pre-execution rejection remains mutation-free and happens before expensive payload construction; an effectful failure additionally reports retry and mutation posture. The shared selector authority must advertise only executable fields and expose one bounded inventory/correction route. `invalid_selector_rejection_budget` adds the repo-local two-second cold-process median; the deterministic invariant separately caps the structured envelope through the shared selector contract.

### Proof execution integrity

`proof_execution_integrity` merges affected-owner claim completeness, the ordinary one-operation execute/reconcile path, subject-stable publication, current-evidence reuse, and honest failed/blocked process status. `selected_proof_residue_budget` gives its deterministic persistence dimension a count measurement: ordinary successful selected proof creates zero tracked receipt residue.

### Selected Planning read budget

`selected_planning_read_budget` retains the two-second cold-process median for maintained exact-selector fixtures. `selected_planning_scaling_budget` retains the 1,000-history ratio at no more than 1.20 of the empty-history control, with a small timing tolerance for sub-clock-resolution fixtures. Both remain Planning/Verification-owned and exclude provider refresh or environment installation.

### Direct work and optimization guidance

`direct_no_signal` preserves the system-intent rule that irrelevant installed capabilities do not create first-line context, commands, network work, durable artifacts, or claim pressure. `total_completion_cost`, `query_shaped_operation`, and `stronger_owner_correction` merge the advisory list into three non-blocking preferences: optimize the whole successful path among safe/capable peers, prefer exact owner queries and progressive disclosure, and repair the strongest deterministic owner instead of accumulating compensating guidance. Reusing current evidence and enforcing outcomes rather than historical choreography are part of those three preferences, not separate gates.

### Initial-policy disposition

| Proposed policy | Disposition | Current owner and rationale |
| --- | --- | --- |
| typed result/process/session agreement | retained, merged | `typed_cli_selector_contract`; root CLI/runtime plus session logging |
| selector authority and fail-fast | retained, merged | `typed_cli_selector_contract`; shared selector authority and lifecycle regression fixture |
| proof claim completeness/execution integrity | retained, merged | `proof_execution_integrity`; existing proof admission and execution owners |
| binding automatic assignment without second permission | deferred | remains owned by open #2817 until an explicitly authorized substantive non-local dispatch proves its acceptance boundary; no passing policy is fabricated here |
| direct/no-signal stays direct | retained | `direct_no_signal`; system intent plus startup/implement proportionality fixtures |
| selected Planning read latency/scaling | retained as two measurements | `selected_planning_read_budget` and `selected_planning_scaling_budget` |
| invalid-selector latency/envelope | retained, split by semantics | latency is `invalid_selector_rejection_budget`; bounded recovery/envelope is deterministic selector-contract evidence |
| narrow proof projection latency/size | adjusted | size stays under existing proof/output profile authority; latency is deferred until a stable maintained cold-process proof fixture exists rather than inventing evidence |
| selected-proof persistence/reuse | retained, merged | zero tracked residue is measured; exact-revision reuse remains part of `proof_execution_integrity` |
| startup/lifecycle/proof/report output | adjusted | existing versioned output-profile budgets remain authoritative (startup is currently 6 KiB, not the stale proposed 4 KiB); no duplicate threshold is added |
| total successful-completion cost and capability-first selection | retained, merged guideline | `total_completion_cost`; safety and required capability remain preconditions |
| query-shaped/progressive disclosure | retained guideline | `query_shaped_operation` |
| stronger-owner repair | retained guideline | `stronger_owner_correction` |
| reuse current evidence / outcomes over choreography | retained, merged guidelines | expressed through total-cost and stronger-owner preferences plus evidence identity semantics |

This catalogue deliberately does not add a policy engine, benchmark daemon, provider-specific portable threshold, or global acceptance packet. The config remains the named requirement owner, Verification/proof remain evidence owners, scoped Markdown supplies readable references, and the existing instruction/operating-decision compiler supplies the only action, claim, or preference effect.
