# System Intent

This file states Agentic Workspace's durable product intent. It is a compass for shaping and validation, not active task state or execution authority.

## Purpose

Agentic Workspace should be a quiet, repo-native operating substrate for agents. It should preserve human intent across time, keep bounded work cheap to start and continue, make proof and ownership legible, and reduce total successful-completion cost without becoming a visible workflow framework or a second source of truth.

The package should help an agent answer the current operating question from the smallest trustworthy state, then get out of the way.

## Authority model

The human or domain expert owns **why**. The system-shaping layer reasons about **what** best serves that why. The implementation layer owns **how**.

AW must preserve that ladder across decomposition, interruption, delegation, review, and closeout. It must not silently narrow the intended outcome merely because a smaller local interpretation is easier to implement or prove.

Active execution state belongs to Planning or another explicit owner. Durable repository truth belongs in its canonical repo surface or Memory when it is genuinely anti-rediscovery knowledge. Proof evidence does not by itself own semantic completion. External trackers and services provide evidence unless the repository explicitly gives them stronger authority.

This file does not own the current execution queue or medium-term roadmap. In this source repository those belong to Planning and its compact summary/routing surfaces; use the configured Planning/Workspace query path before treating raw Planning files as the current work answer.

## Governing intents

### 1. Preserve the right intent and context

Keep what is expensive to rediscover and necessary for safe continuation: current bounded intent, durable repo understanding, proof and ownership boundaries, higher-level convergence context, and compact handoff residue.

Do not preserve narrative history merely because it exists. Chat, logs, plans, reviews, and archives should survive only when their future value exceeds their reread and maintenance cost.

### 2. Make bounded work cheap to start, continue, hand off, review, and finish

The ordinary product should be organized around phase questions rather than command inventory: smallest safe startup context, work shape, governing knowledge, implementation boundary, proof, closeout, and continuation.

Commands, skills, state files, modules, and diagnostics are useful when they answer one of those questions or expose the next safe action. They should not become concepts an agent must learn before repository work can begin.

### 3. Optimize total successful-completion cost

Reduce rereads, rediscovery, clarification loops, retries, proof reruns, repair cycles, handoff reconstruction, and unnecessary user roundtrips. Prompt size, token count, latency, and file count are useful proxies only when they improve the total path to a correct result.

A local optimization that makes another stage heavier is not a product improvement.

### 4. Prefer compact, queryable operational state

Prefer machine-readable current state, narrow selectors, compact reports, lazy discovery, typed next actions, and thin human-readable explanations over prose-first operation.

Prose should explain stable concepts and maintenance decisions. It should not remain the primary operating substrate when a small contract can answer the question more reliably.

### 5. Treat safe composable extensibility as a core product property

Workspace is the small operating kernel, not the fixed union of today's first-party modules.

Domain capabilities should compose through stable declared contracts. Planning, Memory, and Verification are first-party batteries and proving grounds for that capability model, not privileged architectural slots.

Keep three extension mechanisms distinct:

- **modules** provide independently owned domain capabilities, state/resources, operations, and bounded effects on the ordinary operating decision;
- **repo customization** uses repository-owned config, obligations, skills, and canonical guidance to adapt the operating contract to the host;
- **external adapters** consume stable AW operations from outside the core package and own vendor/tool transport, credentials, and integration lifecycle.

AW should remain adapter-unaware: external integrations know about AW; AW does not need an adapter registry, marketplace, credential store, or reverse dependency on them.

Extensibility does not mean every internal hook is a public API. The public module boundary should be deliberately smaller than the implementation vocabulary and should expose only the stable semantics needed for safe composition, compatibility, ownership, lifecycle, and conformance.

New capabilities should normally enrich the existing startup/work/proof/closeout/continuation questions rather than multiply first-contact commands or concepts.

### 6. Keep ownership sharp and residue low

Package-owned machinery, module-owned state, repo-owned policy, local-only runtime state, and promoted normal repo output must remain distinguishable.

Keep package-owned artifacts under `.agentic-workspace/` as far as reasonably possible. Promoted output should become ordinary repo output. Local caches, diagnostics, and integration residue must not become shared authority merely because they exist.

The package should remain plausibly removable.

### 7. Work under partial compliance and mixed agents

AW cannot depend on perfect obedience, hidden reasoning, one vendor, or a universal integration standard.

Correct use should be easy to discover and cheaper than ad hoc repo scavenging. When an agent bypasses a routed contract, trust should degrade visibly rather than causing silent corruption. Strong agents should spend reasoning on judgment; weaker agents should receive enough structure to avoid common ownership, proof, and continuation failures.

### 8. Stay portable across repositories, languages, agents, and vendors

Assume as little as possible about a host repository beyond its ability to host declared AW surfaces and an agent capable of operating them.

Dogfooding must not turn this repository's language, structure, environment manager, provider, workflow, or current first-party modules into hidden universal requirements. Repo- or provider-specific choices should remain visibly outside the durable product contract unless repeated evidence justifies promotion.

### 9. Convert repeated friction into product improvement

Repeated human steering, context overload, proof confusion, wrong-owner work, stale state, failed handoff, late closeout repair, and recurring workarounds should become pressure to improve the product or the repository's canonical surfaces.

Prefer fixing the deterministic owner over preserving permanent compensating guidance in another domain.

### 10. Keep planning, Memory, config, and evaluation proportional

Planning should preserve live intent and cheap continuation, not become a prose archive or second backlog. Memory should preserve expensive-to-forget durable understanding, not active state or broad documentation. Config should express real authority or durable operating choices, not every possible agent preference. Evaluation should preserve decision-useful evidence and named ownership, not raw history by default.

When declared config or a normalized machine-readable mirror materially affects routing, mutation, proof, review, or closeout, treat it as explicit operational authority rather than ambient advice. Prefer one authoritative definition projected consistently across CLI, skills, generated targets, modules, and adapters.

## Product-shape rules

The kernel owns cross-cutting composition: compatibility admission, current authority, task-shaped routing, conflict visibility, effect/mutation boundaries, proof/claim boundaries, lifecycle coordination, and stable operations.

Modules own domain semantics. Repo customization owns host policy. External adapters own transport and vendor integration. None should silently absorb another owner's meaning.

Conflicts must be surfaced rather than resolved by hidden precedence when they change accepted workflow or authority. Blocking results should name a constructible next action: an operation, selector, owner, recovery route, or explicit human decision with the facts needed to make it.

Closeout should distinguish useful slice completion from the larger intended outcome. Passing tests or a successful module-local operation must never automatically authorize a broader claim.

## Anti-intents

AW should resist becoming:

- a project-management or ticketing system;
- a visible workflow framework the user must consciously operate;
- a repo-side script that micromanages ordinary local judgment;
- a surface-growing contract maze where every good idea becomes a new command, file, posture field, or lifecycle concept;
- an arbitrary plugin runtime, adapter marketplace, or vendor credential host;
- a historical archive preserved mainly because it already exists;
- a blurry ownership model where package, module, repo, local, and promoted artifacts compete;
- a local optimization machine that reduces one metric while increasing total completion cost;
- a repo-, language-, module-, agent-, or vendor-specific product accidentally generalized from dogfooding.

## Validation implications

A change is not validated merely because the requested slice landed. Validation should ask whether it:

- preserved the intended why rather than only the literal local request;
- reduced or at least did not worsen total successful-completion cost;
- respected ownership and compatibility boundaries;
- made continuation, review, proof, and closeout cheaper and more trustworthy;
- made the correct action easy to construct by design rather than teaching it through repeated validation failures;
- avoided unnecessary visible residue or new framework feel;
- kept relevant config and declared posture explicit when they materially mattered;
- improved portability and composability rather than hardening current dogfooding assumptions;
- used extensibility to background capability behind existing ordinary questions rather than expanding first-contact complexity.

New work should be questioned when it mainly adds another visible concept, preserves history without future value, scripts agent judgment, duplicates an existing owner, or exposes an internal mechanism as public API without a demonstrated external need.

## Compact operating rule

Keep the right context.
Shape the right bounded work.
Preserve the right intent.
Make continuation cheap.
Stay quiet.
