# System Intent Embodiment Review — 2026-04-26

## Purpose

This review assesses how well Agentic Workspace currently embodies its stated system intent.

It is a review artifact, not an operating contract. It should help future planning and review distinguish:

- what has landed
- what intent it serves
- what remains unresolved
- whether closure would be honest

## Executive assessment

Agentic Workspace now embodies its stated intent moderately well in direction and increasingly well in substrate, but unevenly in lived operation.

The core intent is clear: Agentic Workspace should be a quiet, repo-native continuity and execution layer that preserves human intent, reduces restart/handoff/review cost, keeps bounded work cheap to verify, and avoids becoming a visible workflow framework or second source of truth.

The system is visibly moving in that direction. Recent work has made startup, planning, command metadata, policies, issue lanes, and extraction work more explicit and machine-readable. However, the implementation still depends heavily on large Python-owned behavior, prose-heavy Memory and planning surfaces, and human/agent discipline to promote durable learning rather than letting it remain in archived or conversational residue.

Current rough assessment:

```text
Intent clarity:             high
Repo-native posture:        high
Continuity support:         medium-high
Machine-readable substrate: medium, improving quickly
Low-residue posture:        medium
Human intent preservation:  medium-high
Generic-agent usability:    medium
Implementation independence: early but credible
Closure honesty:            improving, still manual
```

## 1. What the system intent asks the package to be

The repository describes Agentic Workspace as a durable operating layer for agents that should not make the repository feel like a workflow product first.

The compiled system-intent declaration sharpens that into recurring obligations:

```text
preserve expensive context
keep human-owned why distinct from system-shaped what and implementation how
prefer compact queryable state over prose-first operation
reduce total successful-completion cost across restart, handoff, review, and proof
stay quiet, repo-native, low-residue, and sharply bounded
```

It also identifies anti-intents:

- do not become a visible workflow framework
- do not grow a surface maze
- do not optimize a local step while making the total loop heavier
- do not blur package-owned and repo-owned authority

The system-intent contract adds a second important principle: bounded slices may narrow means and proof, but must not silently replace the larger intended outcome. Ordinary compact inspection should answer what larger outcome a slice serves, whether it is actually closed, where continuation lives, and what evidence justified closure.

## 2. Where the system already embodies the intent well

### 2.1 It has a clear compact operating path

The ordinary startup path is explicit enough to reduce broad rereading:

1. read the repo entrypoint instructions
2. use system intent as a compass when shaping broader work
3. ask compact workspace/planning queries before opening deeper planning details
4. open the active execplan only when compact state points there

This is one of the strongest parts of the system. It does not ask agents to understand the whole repo first. It gives them a route.

### 2.2 Planning has become a real continuity substrate

Planning has moved toward checked-in active state rather than chat-only continuation. `.agentic-workspace/planning/state.toml` and `.agentic-workspace/planning/execplans/` are recognizable continuity surfaces.

That matches the intended shape: active execution state belongs in planning, not in scattered chat or generic memory. It also supports mixed-agent workflows because active work can be resumed from repo-owned residue.

### 2.3 System intent has a normalized workspace-owned declaration

The current system-intent workflow distinguishes source material from the compiled declaration. Repo-owned sources are directional input; `.agentic-workspace/system-intent/intent.toml` is the normalized workspace-owned view.

This is strongly aligned with the repo's intent. It keeps host-repo authoring unconstrained while still giving Agentic Workspace a compact operational compass.

### 2.4 Standing intent has a useful routing model

The standing-intent contract already classifies durable guidance into owner-shaped classes:

- config policy
- repo doctrine
- durable understanding
- active directional intent
- enforceable workflow
- temporary local guidance

This is the right conceptual shape for preserving the right context without making Memory or planning into a dump.

### 2.5 The package is now seriously moving away from Python as hidden authority

PR #304 completed a major first extraction slice. It moved command/option metadata, module registry metadata, policy payloads, setup findings policy, preflight policy, workflow artifact profiles, repo-friction policy, and workspace surface/path manifests into checked-in contract JSON with schemas and checks.

That directly advances the stated intent: stable truths become inspectable and portable, while Python becomes more of an adapter/implementation layer.

## 3. Where the system only partially embodies the intent

### 3.1 Continuity exists, but durable learning is still not reliably promoted

The system supports active continuation, but completed work can still lose reusable understanding when execplans are archived. Active lane intent and implementation rationale often remain trapped in execplans. Archiving preserves history, but it does not reliably promote reusable understanding into Memory, doctrine, config, checks, or system intent.

This is one of the clearest places where the system is conceptually ahead of its implementation. It wants to learn from work, but the learning loop is still manual and incomplete.

Related follow-up: #307.

### 3.2 Memory is still too prose-first for the stated ambition

The standing-intent model says durable understanding belongs in Memory when it reduces rediscovery cost. But Memory and possibly other module-owned surfaces may still rely too heavily on prose, making them harder for agents to query reliably, validate, route from, or distinguish authority.

This matters because the stated system intent prefers compact queryable state over prose-first operation. Memory is central to that promise, yet it appears not to have received the same structural treatment as planning.

Related follow-up: #331.

### 3.3 Local-only knowledge is not yet handled

Checked-in Memory is not the right home for everything; chat-only memory is too fragile. The system needs an opt-in local-only memory surface for machine-local, user-local, environment-specific, low-confidence, or private knowledge that should survive agent switches on the same machine without becoming checked-in repo authority.

Related follow-up: #328.

### 3.4 Contract extraction is promising but incomplete

PR #304 completed an important declarative extraction slice, but the first practical milestone is broader: current Python scripts should consume contract-backed sources for interface metadata, policy data, schemas, static/default data, output templates, operation contracts, and validation/parity expectations.

Related parent lane: #309.

### 3.5 Procedural behavior is still mostly implementation-owned

The procedural operation-contract work begins a contract-first path, but the whole CLI behavior is not yet inspectable through implementation-independent contracts. Every CLI command and subcommand should eventually have an operation contract, and CI should validate command-to-operation parity.

Related follow-up: #313.

## 4. Main strengths by intent dimension

### Preserve human intent across time

Status: medium-high.

Strengths:

- System intent is explicit and normalized.
- Planning carries active intent and current continuation.
- Standing intent has a classification and owner-routing model.
- Recent issue work carefully distinguishes landed slices from unresolved underlying intent.

Weaknesses:

- Lane-local learning can still be buried in archives.
- Promotion from active work into durable understanding is not yet systematic.
- Intent validation remains more discipline-based than mechanically supported.

### Make bounded work cheaper to continue and verify

Status: medium-high.

Strengths:

- Compact startup path.
- Planning summary/state machinery.
- Preflight/startup/proof-selection work.
- Contract extraction and parity checks reduce reverse-engineering cost.

Weaknesses:

- Some continuation still requires reading prose execplans or large Python branches.
- Memory is not yet sufficiently queryable.
- Full conformance for generated tools does not exist.

### Stay quiet, repo-native, and low-residue

Status: medium.

Strengths:

- Package-owned artifacts are mostly under `.agentic-workspace/`.
- The system consistently prefers compact query surfaces over broad reading.
- Recent proposals emphasize local-only state, removability, and not making local memory authoritative.

Weaknesses:

- Surface count is growing: planning, memory, system intent, configs, reports, contracts, schemas, operation specs, issues.
- Without compact routing/reporting, the extraction work could become framework-feeling.
- The product needs more surface-compression pressure to keep its own complexity from violating the anti-intent.

Related follow-up: #338.

### Preserve sharp ownership boundaries

Status: medium-high.

Strengths:

- Ownership distinctions are explicit: planning owns active state, Memory owns durable understanding, config owns policy, checks own enforceable workflow, system intent owns higher-level direction.
- Contract extraction separates declarative data from procedural Python.
- Local-only memory is being framed as advisory machine-local context rather than shared repo authority.

Weaknesses:

- Actual surfaces still blur in places: Memory, prose, archived execplans, and system intent can all carry why.
- The system needs stronger closeout and promotion rules to prevent accidental authority through residue.

### Reduce total successful-completion cost

Status: medium.

Strengths:

- Startup and summary paths reduce first-contact cost.
- Contract manifests reduce implementation archaeology.
- Planning state reduces restart cost.
- New issue lanes are more structured and easier to route.

Weaknesses:

- Current system still requires substantial human/agent judgement to decide which surface owns a fact.
- Large Python implementations still exist.
- Agents still need discipline to avoid broad rereading and to promote durable learning correctly.

## 5. Key gaps that most affect embodiment

### Gap 1: Learning from completed work is still weak

The system needs closeout distillation. Archived execplans should be evidence, not the ordinary carrier of durable understanding.

Follow-up: #307.

### Gap 2: Memory needs structured records

Planning has moved toward compact state; Memory likely needs a comparable structured substrate.

Follow-up: #331.

### Gap 3: Local-only continuity is missing

Checked-in Memory is not the right home for everything; chat-only memory is too fragile.

Follow-up: #328.

### Gap 4: Implementation-independent behavior is not complete

Declarative extraction landed, but operation contracts, input/output schemas, Python loader boundaries, and parity/conformance checks remain ongoing.

Follow-ups: #309, #313, #315.

### Gap 5: Surface count may become its own cost

The system is adding useful structure, but every new surface must justify itself by reducing total cost.

Follow-up: #338.

### Gap 6: Agents need a compact effective authority view

The system has the ingredients for intent/authority review, but agents still need to synthesize multiple surfaces to judge whether current work aligns with system intent.

Follow-up: #339.

## 6. Honest closure view

### What has landed

- Stronger startup and compact routing path.
- Planning as checked-in active continuity.
- Compiled system intent.
- Standing-intent routing doctrine.
- Major first declarative contract extraction via #304.
- A clearer issue hierarchy for Python-consumable extraction, procedural contracts, local-only memory, structured Memory, and next-stage system-intent embodiment.

### What intent it serves

- Lower restart and handoff cost.
- More faithful preservation of human intent.
- Less Python-as-hidden-authority.
- More compact, queryable operating state.
- Better mixed-agent continuation.

### What remains unresolved

- Durable learning promotion from completed lanes.
- Machine-readable Memory.
- Local-only memory.
- Full procedural operation-contract coverage.
- Input/output schema coverage and schema-derived models.
- Black-box conformance for generated tools.
- Classification of remaining Python-owned procedural logic.
- Ongoing surface compression.

### Whether closure seems honest

For the first declarative extraction slice: yes, a meaningful slice landed.

For the full system intent: no, not yet closed.

For the package's broader ambition: the system is directionally coherent but still mid-migration.

## 7. Recommended next moves

The most intent-faithful next order is:

1. Complete #310, the audit of remaining Python-owned extractable content, before more opportunistic extraction.
2. Advance #307, closeout distillation, because durable learning is central to the system's promise.
3. Design the first structured Memory record slice from #331, not a full Memory rewrite.
4. Keep #328 local-only memory small and opt-in as advisory machine-local context.
5. Finish #313 operation-contract coverage only after #308's operation shape is accepted.
6. Maintain surface-compression pressure via #338 as contracts and memory surfaces grow.
7. Add a compact effective authority/system-intent view through #339 to support closure review.

## Bottom line

Agentic Workspace is no longer merely describing its intended shape; it is beginning to implement it. The strongest evidence is the merged declarative-contract extraction, compact planning/startup surfaces, and explicit standing-intent/system-intent contracts.

But the deepest promise is not yet fully real: the package does not yet reliably turn work into durable, queryable system understanding. Memory remains too prose-first, closeout learning is not consistently promoted, and procedural behavior is still mostly Python-owned.

The system currently embodies its intent best as a careful, repo-native operating substrate in transition. Its next challenge is to make the transition real without becoming the heavy framework it explicitly does not want to be.
