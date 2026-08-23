# Future-decision context closure

This review records the current architecture and proof for #2680 and #2690. It is evidence, not a parallel operating workflow.

## Current architecture map

| Flow | Source owner | Canonical seam | Material effect | Durable mutation owner |
| --- | --- | --- | --- | --- |
| Relevant Memory before action | Memory route/manifest | startup or implement projection → `compile_operating_decision` | `memory_effectiveness.projected_contributions` changes the canonical decision | Memory lifecycle operations |
| Other durable guidance before action | context-authority registry owner | `context_authority_projection` → `source_guidance` | compact decision-dimension reference | registered source-owner operation |
| Signed human correction after action | independent host adapter | `correction-event.submit --trusted-host-event-json …` → trusted-authority custody | pending normalization or admitted correction signal | correction-event lifecycle, then selected route owner |
| Evaluation or other known result after action | producing owner | `future_context_signals` → existing context consequences and reconciliation | claim bound plus one typed owner action | the signal's registered owner operation |

The operating decision composes effects; it does not copy source semantics or manufacture authority. Reconciliation checks whether a known signal has an owner/disposition and never writes Memory, guidance, Planning, or policy directly.

## Correction ingress and partial compliance

An independent host can now pass its signed event envelope to the generated `correction-event.submit` operation. Signature, producer custody, channel, workspace binding, expiry, and source identity are checked before local custody. Caller-supplied `authority=explicit-user-correction` or `producer_class=human` remains non-authoritative.

The first host call may contain only compact evidence identity and applicability hints. It returns `pending-normalization`, writes the signed observation to the existing trusted-authority event store, and does not create a correction event or choose a durable route. Replays are no-ops. A later submit names the opaque `host_event_ref` and supplies semantic identity; it enters the existing correction store as `accepted-unrouted`. A final update can route or dismiss it. No transcript, vendor adapter registry, or second correction store was added.

The regression fixture deliberately gives the corrected implementation agent zero correction actions: the test host calls the generated Python operation directly with a signed, minimally classified observation. The observation survives, appears as a relevant normalization action, normalizes into the existing owner, and remains visible until routed. Vendor conversation APIs that do not expose feedback must report `future_context_capture.status = unavailable`; the repository does not simulate host authority.

## Replacement and demotion map

| Legacy or voluntary surface | Current disposition |
| --- | --- |
| Agent remembers to run `memory route` before ordinary work | Replaced by route-selected Memory contribution composed into the canonical operating decision |
| `memory_decision_packet` as a peer first-line decision | Selector-only diagnostic/input compatibility; material use is `operating_decision.memory_effectiveness.projected_contributions` |
| Memory capture questionnaire or closeout ritual | Demoted; known producer-owned signals enter existing context consequences/reconciliation |
| Agent-prompted “host recovery” that tells the corrected model to submit | Rejected as independent-host proof; the host invokes the generated operation itself |
| Raw trusted-event inbox writes/private `agent_guidance.py` imports | Replaced for supported consumers by signed JSON through `correction-event.submit` |
| Deterministic Memory workaround after a stronger owner absorbs it | Existing Memory effectiveness lifecycle re-evaluates retain/shrink/stub/delete |

Start, implement, proof, summary, and reconciliation retain their phase-owned compact outputs. No universal envelope or mandatory Memory/correction phase was introduced.

## Cost and counterexamples

- No applicable context: zero additional agent commands, zero local artifacts, no `future_context_signals` field, and quiet context effects. The only runtime check is the existing local-custody lookup when a target root is available.
- Relevant Memory: zero Memory-specific agent commands; the already-selected compact contribution reaches the canonical decision. Candidate-only contributions remain distinguishable and cannot claim projected use.
- Host correction: one idempotent host operation preserves evidence while the corrected agent performs zero correction actions. Normalization and disposition occur only when needed.
- Agent-proposed learning: remains an `agent-proposed` candidate. It may be routed for owner review but creates no human, policy, proof, or stronger-owner authority and blocks no claim by itself.
- Stronger-owner counterexample: existing Memory effectiveness tests retain genuinely advisory facts while recommending shrink/stub/delete only when a deterministic owner absorbs the lesson.

This reduces the historical failure cost—rediscovery and repeated human steering—without adding commands or artifacts to the no-context path.

## Proof boundary

Focused tests cover signed-host import, forged-authority rejection, replay deduplication, incomplete normalization, admitted-but-unrouted state, separate disposition, relevant/unrelated selection, generated Python invocation, generic non-correction evaluation residue, low-authority agent candidates, unavailable host capture, and quiet no-context behavior. Generated Python and TypeScript packages carry the new public inputs; external-consumer and operation contracts remain the shared interface authority.
