# Dynamic-instruction lane closure review

Date: 2026-08-17

Issues reviewed: #2556, #2558, #2562, #2565, #2566, #2570, #2571, #2597, and #2598.

## Decision

The reopened operating-decision lane is satisfied by the merged domain implementations plus this bounded composition slice. The new slice does not add an instruction inventory or second authority system. It lets the existing context-authority registry declare when a source-owned procedure changes a canonical decision dimension, projects only the admitted source reference and revision, and adds a seven-case adversarial integration matrix.

## Acceptance mapping

| Concern | Evidence | Result |
| --- | --- | --- |
| Canonical decision and coherence (#2562) | `src/agentic_workspace/operating_decision.py`, `tests/test_operating_decision.py`, `tests/test_composed_operation_scenarios.py`, `tests/test_dynamic_instruction_projection.py` | One revision-bound compiler owns action, blocker, owner, terminal, claim, and continuation semantics. The generic composed loop covers compatibility, related Planning work, changed surfaces, focused proof, handoff, terminal closeout, and same-revision resume. |
| Query-shaped reuse (#2556) | `src/agentic_workspace/projection_reuse.py`, `tests/test_workspace_projection_reuse.py`, selected-summary tests in `tests/test_workspace_cli.py` and `tests/test_workspace_summary_cli.py` | Existing decision/enrichment reuse remains keyed by the canonical decision identity. The new matrix records bounded first-line bytes and one invocation per scenario; domain tests retain cold/warm read and invalidation coverage. |
| Compatibility admission (#2558) | `src/agentic_workspace/runtime_compatibility.py`, `tests/test_runtime_compatibility.py`, freshness scenario in `tests/test_dynamic_instruction_projection.py` | Compatibility-aware readers fail before managed semantic interpretation and expose no implementation permission. The boundary remains capability-based and does not claim control over pre-contract binaries. |
| Symmetric relevance (#2565) | context-authority registry/projection tests, planned-child and unrelated-direct-work scenarios | The planned child remains a continuation; unrelated direct work has neither Memory nor source-guidance contributions. Unknown semantic applicability remains with the source owner or agent resolver. |
| Planning relation and child continuity (#2566) | Planning route decision tests in `tests/test_workspace_cli.py`, `packages/planning/tests/test_branch_safe_planning.py`, planned-child scenario | Structured relation identity, not active-owner presence or prose markers, distinguishes continuation from bounded independent work. Planning remains the stronger relation owner. |
| Truthful Memory contribution and lifecycle (#2570, #2571) | `src/agentic_workspace/memory_effectiveness.py`, `tests/test_memory_effectiveness.py`, Memory/Planning boundary scenario | Candidate discovery and projected use remain distinct. One advisory contribution enters the decision without overriding Planning; stronger-owner resolution reuses the existing retain/shrink/stub/delete lifecycle. |
| Source-owned guidance composition (#2597) | registry `decision_dimension`, `source_guidance`, positive/negative skill tests | A selected skill contributes only owner, source ref/revision, decision dimension, proof route, and authority boundary. Its body is not copied. Unselected skill classes are absent. Memory remains the second representative typed guidance path through its existing owner contract. |
| Adversarial conformance (#2598) | `tests/fixtures/dynamic_instruction_scenarios.json`, `tests/test_dynamic_instruction_projection.py` | Seven small behavior-level scenarios cover recall, precision, freshness, causal effect, coherence, Memory/Planning authority, and a focused procedure route. Expectations are hand-maintained effects, not snapshots generated from runtime mappings. |

## Cost and authority boundary

The matrix measures deterministic first-line bytes and AW invocation count only. Existing domain tests own deeper read-count, cache, invalidation, lifecycle, and generated-adapter proof. Human repair-loop and total-successful-completion measurements remain dogfooding/evaluation evidence; this suite does not pretend to observe them.

The source-guidance seam is intentionally narrow. Applicability and the affected dimension come from the existing source-owner registry; the decision compiler only carries an admitted reference. It cannot turn guidance into Planning, proof, mutation, or claim authority.

## Residue

No new ledger, universal relevance engine, instruction superset, or live-agent evaluation database was added. Additional source classes remain domain-owned and should use existing typed outputs unless a concrete missing composition route is proven. Provider-specific PR, review, and session-export flows remain supplemental dogfooding rather than generic operating-loop requirements.
