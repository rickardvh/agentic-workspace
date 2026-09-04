# System intent

This document preserves Agentic Workspace's durable human-owned product intent.
It shapes implementation and release decisions; it is not current task state,
an execution queue, or authority to mutate a repository.

## Purpose

Agentic Workspace is a quiet, repo-native operating-context and execution layer.
It helps an agent determine what is true, what may happen next, and what can be
claimed afterward. It is not the agent's brain and does not replace source,
documentation, tests, history, or domain judgment.

The ordinary semantic loop is:

```text
relevant source owners -> one operating decision -> one exact typed operation
or bounded judgment/blocker/direct outcome -> typed result or owner-admitted answer
-> source-owner reconciliation -> next operating decision
```

The human or domain expert owns why, the shaping layer determines what best
serves that intent, and implementation owns how. Local implementation
convenience must not silently narrow a still-intended outcome.

## Operating principles

1. **One answer from current authority.** Facts, actions, effects, currentness,
   blockers, and claims retain their source owners. Views, transports, generated
   clients, and host integrations project the answer but cannot independently
   change it.
   A current answer has exactly one consequence: one typed operation, one
   bounded human/domain decision request, one exact blocker with recovery, or a
   terminal/direct outcome. Judgment requests name their owner, source revision,
   answer authority, and bounded response route; stale answers cannot mutate
   current state.
2. **Direct work stays direct.** No applicable signal means no mandatory plan,
   Memory, proof, delegation, configuration, diagnostics, learning ceremony, or
   durable residue. Detail is progressively and query-shapedly disclosed only
   when it can change the current decision.
3. **Optimize total successful-completion cost.** Reduce rediscovery, broad
   reads, clarification, retries, repair, proof reruns, handoff reconstruction,
   and future recurrence. File count, prompt size, latency, and command count are
   subordinate measurements, not goals by themselves.
4. **Act through bounded authority.** Mutation, process execution, external
   effects, proof, and claim changes use exact typed owner operations or an
   explicit human/domain judgment. Guidance and procedure selection never
   manufacture authority.
   Effect admission, currentness validation, execution, and durable result form
   one owner-serialized commit boundary. Concurrent or restarted invocation
   cannot blindly repeat a non-idempotent effect, and interrupted multi-write
   state is reconstructible or blocks with exact owner recovery.
5. **Memory prevents expensive rediscovery.** It preserves bounded durable
   advisory knowledge with provenance, applicability, and currentness, surfaces
   only relevant knowledge, and yields to a stronger deterministic owner when
   one can absorb the lesson.
6. **Planning provides proportional execution custody.** It exists only when
   interruption, dependency, delegation, review, or fresh-session continuation
   justifies durable intent/scope/stops. Ready work is derived; Planning is not a
   task manager or completion-claim authority.
7. **Verification owns proof meaning.** Repository proof strategy, admissible
   current evidence, sufficiency, and claim effects remain distinct from
   Planning status, command exit, worker success, or model assertion.
8. **Repositories remain programmable.** Scoped instructions and shared config
   express repo-owned constraints and choices; local config expresses weaker
   machine/runtime facts and preferences; specialized domain state stays with
   its owner. Reusable procedures are source-owned references loaded only when
   relevant, not a second policy or skill-routing framework.
9. **Modules are capability-first peers.** A module describes its compatible
   identity, owned domain, bounded facts/resources/procedures/operations, and
   result semantics. Workspace owns the loop. First-party batteries have no
   architectural privilege, and adding an independent module requires no
   module-name branch or phase choreography in core.
   Compatible additive semantics remain usable across 1.x; an unknown required
   capability or incompatible semantic variant fails closed with an exact
   upgrade route.
10. **Mixed agents share one authority.** Strong agents may exercise judgment
    without weaker-agent scaffolding becoming mandatory. Partial compliance and
    ignored guidance fail closed at effect/claim boundaries; trusted human
    corrections can reach their proper owner without relying on the corrected
    agent to cooperate.
11. **Reuse safe conclusions.** Expensive unchanged source-owner conclusions
    may survive transitions and fresh sessions when their exact dependencies
    remain current. Reuse is invisible, dependency-narrow, and never a reasoning
    transcript or parallel authority.
12. **Delegation is configure-once ordinary behavior when relevant.** Current
    task requirements and target facts yield one conservative best-fit answer.
    Eligibility precedes cost. Binding assignment constrains execution; transport
    failure cannot silently become local work; worker return remains subject to
    parent integration, Verification, and claim authority. Retained-local work
    remains direct.
13. **External integration is inverted.** Independent adapters consume the
    generated package and JSON operation boundary. AW owns no provider registry,
    credential host, adapter lifecycle, marketplace, or adoption telemetry.
    External observations enter through the source owner that understands and
    validates their semantics, not a generic ingress database.
14. **Experience converges existing owners.** Consequential corrections,
    outcomes, repeated friction, and reusable successes may produce a bounded
    future-value disposition. They refine, promote into, or retire from the
    smallest canonical owner; they do not accumulate in a universal learning,
    telemetry, warning, or improvement store. Repo-directed action requires
    explicit latitude and remains constrained by human intent, safety, public
    contracts, and proof.
15. **Ownership is acquired, never inferred.** A state path becomes managed only
    through atomic creation, confirmation by its current owner, or explicit
    transfer. Repo-authored config/instructions and unknown content cannot be
    overwritten and then claimed. Package state, durable module state, ignored
    local diagnostics, and promoted repo output remain distinguishable. Removal
    proves current ownership and canonical root confinement before deleting
    legitimate package residue; malformed records, traversal, absolute paths,
    and link escapes fail closed without a central ownership database.
16. **Support claims are evidence-bound.** Supported environments, trust and
    side effects, artifact provenance, deterministic conformance, host dogfood,
    and provider limitations are stated honestly. Package support is proven by
    isolated black-box use, never inferred from downloads, telemetry, or named
    adopters.

## Product and extension shape

The first-party release contains exactly one generated Python package and one
generated TypeScript package. Both, plus the JSON `start`/`invoke` transport,
project one implementation-independent semantic authority to the practical
limit. Handwritten target code is restricted to explicit bootstrap, discovery,
and platform primitives; ordinary operation and domain semantics are generated.
Canonical serialization, revision/decision/idempotency identity, required
capability handling, and compatible 1.x evolution are defined by that shared
authority rather than by either runtime.

Configuration enters through ordinary resolution: infer safe implementation
facts, ask only irreducible human/domain questions, nominate exact owner
operations, support deferral, and disappear when current. Optional diagnostics,
maintainer procedures, research harnesses, and conformance tooling remain
available outside ordinary first contact and shipped host payloads.

## Anti-intents

AW must resist becoming a workflow engine, project manager, scheduler, event
bus, transcript archive, central reasoning/context/evidence database, general
knowledge graph or RAG service, mandatory Planning system, policy DSL, visible
surface maze, adapter marketplace, credential host, provider authority, or
scripted replacement for model judgment. It must not preserve alpha mechanisms
merely because they existed, nor delete still-intended capabilities merely
because their former implementation was too large.

## Compact rule

Preserve only context with future decision value. Surface only what matters
now. Act through the exact supported route. Reconcile into the owning source.
Improve the owner when material friction repeats. Stay quiet otherwise.
