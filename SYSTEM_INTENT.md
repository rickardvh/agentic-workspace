# System Intent

This file states Agentic Workspace's durable product intent. It is a shaping and validation compass, not active task state or execution authority.

## Purpose

Agentic Workspace is the next developmental stage of repository agent instructions: a quiet, repo-native system for **operating context** and **dynamic control**.

A repository may preserve a small amount of context because its availability materially changes how an agent should operate: intent, authority, ownership, current state, procedures, constraints, proof expectations, learned lessons, or other capability-owned facts. AW selects the relevant part of that context for the current task, agent, environment, and decision, then compiles it into the smallest trustworthy operating contract.

AW should not try to model everything the repository knows. Ordinary source, documentation, tests, history, and other canonical repository contents remain where they belong. A knowledge graph, RAG/indexing system, semantic repository model, or richer knowledge service may be a useful module, but it is not the core product.

The product should make the correct operating path cheaper than broad repository scavenging, preserve human intent across time, and reduce total successful-completion cost without becoming a visible workflow framework or a second source of truth.

## Core operating model

The ordinary conceptual loop is:

1. **Resolve** — derive the smallest relevant operating contract from current task facts, source-owned repository context, runtime/environment facts, admitted capability contributions, and applicable repo-owned instruction policy.
2. **Act** — let the agent perform the bounded action through the supported operation, skill, owner, or explicit human decision, loading deeper detail only when the contract routes there.
3. **Reconcile** — admit the result back to the correct owners, determine what changed, what may now be claimed, what must survive, and whether another resolve step is required.

The existing compiled operating-decision and typed-action boundary is the implementation center of this loop. `resolve -> act -> reconcile` is a conceptual projection of that authority, not a second compiler or another user-facing workflow.

Closeout is the terminal case of reconciliation: no further action remains, required evidence and authority are sufficient for the intended claim, and any future-relevant residue has an explicit owner or is deliberately absent. An individual source owner being settled or having nothing to require is only owner-local quiescence; it does not establish that the user's outcome is terminal or that a broader claim is supportable.

## Authority model

The human or domain expert owns **why**. The system-shaping layer reasons about **what** best serves that why. The implementation layer owns **how**.

AW must preserve that ladder across decomposition, interruption, delegation, review, and reconciliation. It must not silently narrow the intended outcome because a smaller local interpretation is easier to implement or prove.

Repository context remains source-owned. Canonical docs, config, ownership declarations, module state, Planning state, proof evidence, Memory findings, and other authorities keep their own semantics and lifecycle. AW composes their current effect; its generated instruction or operating contract does not become a new source of truth merely because it is convenient to consume.

Still-current recognized authority survives a change of representation. Obsolete representations may be removed only after their current meaning has been transferred, explicitly dispositioned by its owner, or made to block only the behavior that depends on it. This is a bounded transition rule, not a promise of indefinite compatibility.

Persisted caches, receipts, journals, and prior decisions are projections or results, not independent current authority. Reuse or replay requires their producer, contract, source dependencies, and subject to remain current and compatible.

External trackers and services normally provide evidence rather than repo intent or completion authority unless a repository explicitly assigns them a stronger role.

This file does not own the current execution queue or roadmap. Those belong to their configured owner and compact query path.

## Governing intents

### 1. Preserve only operating context with future decision value

Keep context when its durable or current availability materially changes safe agent behavior and its future value exceeds its reread and maintenance cost.

Do not preserve chat, logs, plans, reviews, histories, or arbitrary repository facts merely because they exist. Do not duplicate canonical repository truth into AW just to make it searchable.

`Operating context` is an ownership and routing category, not a central database.

A durable plan or prior work binding does not implicitly become the current task. Selection and resume are explicit, current dependencies remain actionable, and Planning custody does not manufacture completion authority.

### 2. Surface only what matters now

First contact should contain only information that can change the current decision. Deeper context, procedures, evidence, diagnostics, and module detail should remain behind exact selectors, skills, operations, or owners until relevant.

The right information at the wrong time is still a product failure. Installing another capability should not proportionally enlarge ordinary startup or the agent's mental model.

### 3. Make control programmable and actionable

When AW says what should happen next, that route should normally be constructible: a typed operation, derived command, exact selector, routed skill, named owner, bounded recovery, or explicit human decision with the required facts.

Prose that says to “reconcile,” “inspect,” “close,” or “handle appropriately” without a supported route is not sufficient dynamic control.

Programmability should go further than choosing among hard-coded modes. A host repository should be able to declare new **bounded conditional control relationships** over stable facts and capabilities without requiring a new Workspace runtime branch merely because that relationship is new.

The architectural normal form is intentionally small:

- **facts** remain source-owned typed context from repo, runtime, module, or admitted external owners;
- **instruction clauses** state bounded applicability and a supported control effect;
- **skills** provide lazily discovered multi-step procedure;
- **typed operations** provide effectful action under explicit authority;
- the existing **operating-decision compiler** resolves applicable clauses and capabilities into one current contract.

A clause should express only control effects the kernel already knows how to compose safely, such as surfacing a context/skill reference, nominating or requiring a typed operation, requiring evidence or an explicit human decision, restricting an effect, or limiting a claim. The clause itself must not mutate repository state; mutation remains behind an admitted typed operation and its owner.

Composition must preserve authority and be deterministic. Lower-authority guidance cannot widen a higher-authority permission or claim. Restrictions and requirements compose conservatively, conflicts become visible facts rather than hidden precedence, and decisions remain revision/provenance bound.

A blocker or unresolved decision constrains only the action, effect, or claim that depends on it unless explicit authority makes it task-global. Selecting one visible consequence may compress presentation, but it must retain exact, queryable identities and recovery routes for unresolved peer consequences.

An exact typed operation means the complete current action selected by its owner: operation and source identity, arguments, target, effects, handoff, currentness, and idempotency. A caller cannot retain the operation name while substituting other schema-valid effect-bearing values.

A bounded human or domain judgment must be constructible from the public request. The owner supplies currentness, authority, and every effect-bearing field; the human supplies only the bounded answer.

Do not create a second instruction compiler or a general-purpose policy/rule language. Existing specialized mechanisms—workflow obligations, assurance/proof declarations, scoped instructions, skill routing, target/correction guidance, and module relevance—should converge on or compile through a shared internal control normal form where their semantics overlap. They may retain domain-specific authoring surfaces when those surfaces carry genuine domain meaning.

Natural-language or keyword matching may help discovery, but it cannot decide genuine semantic applicability. That classification remains acting-agent judgment admitted as current structured context; deterministic path, operation, source, and authority facts remain owner-derived rather than matters of prose interpretation.

### 4. Optimize total successful-completion cost

Reduce rereads, rediscovery, clarification loops, route reversals, retries, proof reruns, repair cycles, handoff reconstruction, and unnecessary user roundtrips.

Prompt size, token count, latency, command count, and file count are useful only when they improve the total path to a correct result. A local optimization that makes another stage heavier is not a product improvement.

Delegation follows the same measure: bounded self-sufficient worker context and observable expected total successful-completion burden, not declared price alone. A host or shared-worktree transport must carry a complete public assignment and return contract; hidden orchestrator relay is not semantic completion.

### 5. Keep modules as practical peer extensions of the loop

Workspace is the small cross-cutting control kernel, not the union of today's domain capabilities.

The practical rule is: **a module describes its domain; Workspace owns the loop.** `resolve -> act -> reconcile` must not become three mandatory module hooks or another framework that extension authors have to learn.

An ordinary module should declare only the domain facts needed for safe composition: what capability it is and is compatible with, what it owns, when it is relevant, what resources/procedures/typed operations it can provide, and what its results/effects mean. Contribution dimensions are optional when they do not apply. A read-only capability should not invent action or reconciliation hooks; an operation-oriented capability should not invent startup posture or a closeout phase.

Workspace derives how those declarations affect resolution, action, and reconciliation through the existing operating decision. Planning, Memory, and Verification are first-party batteries and proving grounds for that model, not privileged architectural slots.

Useful genericity must reduce extension cost as well as conceptual duplication. Adding a later independent module should normally be module-package work plus its public descriptor/contracts and tests—not semantic Workspace edits, module-name switches, fixed slot/phase registration, canonical-skill changes, or another core-owned per-module list merely to recognize the capability.

Modules contribute facts, capabilities, procedures, operations, and result semantics. They should not define new global instruction operators merely because their domain is new; repo-owned instruction policy and Workspace composition remain the control layer.

Peer owners compose through typed public facts, results, evidence, and operations. One owner does not inspect another's private storage or run arbitrary callbacks after another owner's effect; the responsible owner admits cross-owner results before mutating its own state or claims.

Keep three mechanisms distinct:

- **modules** add independently owned reusable capabilities;
- **repo customization** supplies host-owned control inputs and bounded instruction policy through config, obligations, skills, canonical guidance, ownership, and repository operations;
- **external adapters** project or transport stable AW operations into other hosts while remaining outside AW's semantic authority.

A new capability should normally enrich the existing resolve/act/reconcile loop instead of adding a mandatory new phase, first-contact command, or mental model.

### 6. Keep configuration proportional to control value

Shared config should express real repository policy, authority, ownership, capability selection, or durable operating choices. Local config should express machine/runtime capability or preference with appropriately weaker authority. Module-specific controls should stay with the module.

Do not preserve a growing public `posture` model merely because many independent knobs can be represented. Retain a field when it materially changes the current operating contract or has demonstrated completion-cost value; otherwise merge, derive, demote, or remove it.

Repo customization should become more programmable by composing a small set of typed instruction effects, not by accumulating more peer knobs, stages, forces, callbacks, or prose fragments.

### 7. Keep ownership sharp and residue low

Package-owned machinery, module-owned state, repo-owned policy, local-only runtime state, canonical repository content, and promoted output must remain distinguishable.

Keep package-owned artifacts under `.agentic-workspace/` as far as reasonably possible. Local caches, diagnostics, and integration residue do not become shared authority merely because they exist. Promoted output should become ordinary repo-owned output.

AW should remain plausibly removable. Removing executable integration does not abandon durable state that survives it: custody must remain readable and actionable, or be explicitly transferred or retired by its authority, until deliberate removal is complete.

### 8. Work under partial compliance and mixed agents

AW cannot depend on perfect obedience, hidden reasoning, one vendor, or a universal integration standard.

Correct use should be progressively discoverable and cheaper than bypass. When an agent ignores a routed contract, trust should degrade visibly rather than causing silent authority expansion. Strong agents should spend reasoning on judgment; weaker agents should receive enough structure to avoid common ownership, proof, and continuation failures.

### 9. Stay portable

Assume as little as possible about the host repository, language, environment manager, model, provider, and selected modules.

Dogfooding must not turn this repository's current shape into hidden universal requirements. Repo-, provider-, language-, or module-specific choices remain outside the durable core unless repeated evidence justifies promotion.

Portable deterministic first-party semantics should have one implementation-independent executable authority and generated projections for each supported language. Handwritten target code is limited to a small reviewed set of irreducible platform primitives; neither language implementation becomes the semantic oracle for the other.

### 10. Convert repeated friction into better context or control

Repeated human steering, stale context, wrong-owner work, proof confusion, failed handoff, repeated rediscovery, late reconciliation repair, and recurring workarounds should create pressure to improve the deterministic owner, the routed operating context, or the control contract.

Do not preserve permanent compensating guidance when the underlying owner can be fixed.

## Product-shape rules

Workspace owns only the cross-cutting mechanics needed to resolve and reconcile one trustworthy operating contract: compatibility admission, relevance/routing, source provenance, instruction-effect composition, conflict visibility, effect/mutation boundaries, typed actions, claim boundaries, lifecycle coordination, and safe degraded recovery.

Modules own domain semantics. Repo customization owns host policy and bounded instruction programming. External adapters own transport/vendor integration. Canonical repository contents remain repository-owned. None should silently absorb another owner's meaning.

Conflicts that change accepted workflow or authority must be surfaced rather than resolved through hidden precedence.

Irrelevance and absence are first-class states. Direct work should stay direct. An irrelevant installed module, Memory note, plan, proof protocol, config fragment, instruction clause, or diagnostic should remain absent from the current contract.

## Anti-intents

AW should resist becoming:

- a knowledge graph, vector/RAG database, semantic repository index, ontology, or general repository knowledge API in core;
- a project-management or ticketing system;
- a visible workflow engine the user must consciously operate;
- a repo-side script that micromanages ordinary implementation judgment;
- a general-purpose or Turing-complete policy/rule language, scheduler, event bus, or arbitrary callback runtime;
- a framework where Planning, Memory, Verification, assurance, delegation, closeout, posture, or another current capability becomes a mandatory core concept;
- a surface-growing contract maze where every useful mechanism becomes a new command, phase, file, policy dimension, identity, or lifecycle concept;
- an arbitrary plugin/callback runtime, adapter marketplace, or credential host;
- a module API that makes extension authors describe AW's phase/slot choreography back to AW;
- a historical archive preserved mainly because it already exists;
- a blurry ownership model where generated instructions compete with their source authorities;
- a local optimization machine that reduces one metric while increasing total completion cost.

## Validation implications

A change is not validated merely because its requested slice landed. Ask whether it:

- preserved the intended why;
- improved the repository's ability to preserve useful operating context or apply it to current agent behavior;
- allowed a new bounded repo control relationship to be expressed without an unnecessary new runtime branch or framework concept;
- surfaced less but better context at the right decision point;
- produced an exact supported next action rather than another instruction to infer;
- respected source ownership and provenance;
- preserved recognized current authority before retiring its representation or custody;
- reduced or bounded total successful-completion cost;
- kept direct work cheap and irrelevant capabilities/instruction clauses quiet;
- made modules easier to author as well as more peer-like, with module-specific meaning remaining module-owned;
- avoided requiring a new independent module to modify semantic core code or register itself in fixed AW choreography;
- reconciled results and claims without another parallel authority;
- kept stability, version, and platform support claims behind current final-admission evidence and explicit platform proof;
- removed, derived, backgrounded, or replaced older machinery where a new abstraction was introduced.

Question new work when it does not materially improve operating context, dynamic control, programmable instruction composition, or a module's bounded contribution to that loop.

## Compact operating rule

Preserve the context that governs work.
Program only bounded control that pays back.
Surface only what matters now.
Act through the supported route.
Reconcile what changed.
Stay quiet.
