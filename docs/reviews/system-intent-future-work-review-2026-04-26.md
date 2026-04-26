# System Intent Future Work Review - 2026-04-26

## Purpose

This is an independent review after reading `docs/reviews/system-intent-embodiment-review-2026-04-26.md`.

It is not an operating contract. It is meant to guide future work by naming the next leverage points, the traps most likely to undermine the package intent, and the standards future slices should meet before claiming closure.

Evidence read for this review:

- `docs/reviews/system-intent-embodiment-review-2026-04-26.md`
- `SYSTEM_INTENT.md`
- `.agentic-workspace/system-intent/intent.toml`
- `.agentic-workspace/WORKFLOW.md`
- `.agentic-workspace/planning/execplans/system-intent-operating-reality.plan.json`
- `README.md`
- `docs/architecture.md`
- `docs/design-principles.md`
- compact outputs from `agentic-workspace preflight`, `summary`, `defaults --section surface_value_guardrail`, `report`, and `ownership`

## Executive View

The earlier embodiment review is directionally right: Agentic Workspace has moved from aspirational doctrine toward real operational substrate. My stronger conclusion is that the next bottleneck is no longer "does the system have the right concepts?" It mostly does. The bottleneck is whether those concepts make ordinary work cheaper without teaching agents and maintainers a growing private operating culture.

The system is at an inflection point. It has enough structure to preserve intent, route work, inspect ownership, expose surface-value pressure, and keep active planning out of chat. That is substantial progress. But the same success creates a new risk: every fix now has an obvious place to become another contract, report field, memory note, adapter, schema, or review artifact.

Future work should therefore optimize for operational compression:

```text
make the existing compact surfaces more decisive
retire or demote surfaces when stronger ones land
turn closeout into durable learning only when the learning will recur
prove that added structure reduces the total loop, not just local ambiguity
```

If the next phase mostly adds sharper names for things the system already knows, it will drift toward the framework-shaped product it is trying not to become.

## What Is Working

### 1. The repo now has a credible first-contact route

The startup path is no longer "read everything and infer the current state." `AGENTS.md`, `preflight`, `summary`, `defaults`, `ownership`, and the active execplan give a bounded route from repo entry to current work.

This is one of the strongest signs of intent embodiment. The product says it should reduce rereads and preserve expensive context; the current install actually does that for a compliant agent.

Future implication: protect this route aggressively. Do not add more first-line surfaces unless an older first-line surface is removed, merged, or backgrounded.

### 2. Planning has become the current-work authority

The active plan for `system-intent-operating-reality` is a real continuation object. It names larger intent, non-goals, bounds, proof, current milestone, closure honesty, drift, and stop conditions. That is much better than relying on issue text or chat residue.

The machine-readable sidecar posture is also correct. Markdown can remain a human view, but active execution truth should be structured enough to inspect.

Future implication: keep planning authoritative for active work, but keep it small after work completes. Archived execplans should be evidence, not the normal place future agents go to learn.

### 3. Surface-value pressure has landed in the right shape

The `surface_value_guardrail` default is a good example of quiet leverage. It did not create a new top-level command. It asks practical questions:

- what repeated cost does this remove?
- which existing surface does it replace, compress, merge, or make cheaper?
- who owns it and what authority class is it?
- how is it discovered without broad rereading?
- how does it stay removable or low-residue?
- what drift or review check keeps it trustworthy?

That is the right review pressure. It does not ban new surfaces, but it makes surface growth pay rent.

Future implication: treat this as a pre-merge and closeout standard for durable surfaces, not merely a helpful defaults payload.

### 4. Ownership is clearer than the implementation history

The ownership view now gives agents a compact answer for repo-owned, managed, module-owned, fenced, and authority surfaces. That matters because the package intent depends on sharp boundaries. Without this, every generated adapter or module-managed file would slowly become ambiguous authority.

Future implication: any new review, memory, planning, or contract surface should name its authority class and owner in the same vocabulary. New vocabulary should be resisted unless the current authority classes fail a concrete case.

## What Is Not Yet Working Enough

### 1. The compact report risks becoming too large to be compact

The report is valuable, but the full JSON output is already large enough that "ask report first" can become a broad reread in machine-readable clothing. The report contains the right material, but the first-contact report needs a sharper top-level answer and stronger selector discipline.

The risk is subtle: a machine-readable dump can still violate the intent to reduce reading if agents have to scan thousands of lines to find the next action.

Future work should make the report behave more like a router than an encyclopedia:

- default output should privilege health, current work, next action, warnings, and selector hints
- deep detail should sit behind sections or profile selectors
- every high-volume module contribution should justify why it belongs in the default profile
- warnings should be summarized into decision-grade groups before the raw list appears

### 2. Open external work is not yet quiet

The summary says the active lane is clear, but the intent validation contract still reports many open external planning items that are not represented in active or candidate checked-in planning state. That means the repo is not quiet yet; it is just bounded around the current lane.

This distinction matters. A system can be usable for current work while still failing roadmap integrity.

Future work should separate:

- current execution readiness
- broader roadmap reconciliation
- external tracker hygiene
- closure trust

The current lane should not be blocked by every open issue, but the package should not call itself quiet while external work remains materially unrouted.

### 3. Closeout learning is still the highest-leverage missing loop

The previous review correctly identifies closeout distillation as a major gap. I would rank it above broad Memory restructuring.

Memory structure will only be useful if the input quality is good. The current system can produce rich active-plan residue, but it still needs a disciplined closeout pass that decides:

- what dies with the plan
- what becomes issue or roadmap continuation
- what becomes durable memory
- what becomes a contract, check, or config default
- what was merely local execution detail

Without that loop, the system will continue to preserve too much narrative and too little reusable understanding.

### 4. Memory should shrink before it becomes more powerful

The report already shows memory elimination candidates and promotion candidates. That is a useful signal. It also suggests the next Memory phase should not start with "make Memory more expressive." It should start with "make Memory less necessary to read."

A structured Memory record slice is worthwhile only if it reduces ordinary pull size and clarifies authority. A schema that makes it easier to add notes would be counterproductive.

Future Memory work should begin with a small record type for durable facts that have:

- owner and authority class
- reason the fact is expensive to rediscover
- route key or touched-surface trigger
- evidence or provenance
- promotion, demotion, or expiry expectation

The acceptance test should be smaller routed working sets, not a nicer memory taxonomy.

### 5. Effective authority needs a view, not a judge

The planned #339 work is important, but it should stay descriptive. The package should help an agent answer "what authority applies here?" and "what system intent pressure matters?" It should not pretend to automatically decide alignment.

A good effective-authority view would name:

- startup authority
- active planning authority
- system-intent compass
- ownership authority
- proof or workflow obligations
- advisory posture such as local memory or branch warnings
- unresolved external-work pressure

It should also say what it cannot decide. This matters because an automatic "alignment score" would be both brittle and too framework-like.

## Main Future-Work Rule

For the next phase, do not ask "what surface would make this clearer?"

Ask:

```text
what repeated future cost are we removing,
and which existing surface becomes smaller, less visible, or unnecessary because of this change?
```

If there is no answer, the work may still be intellectually tidy, but it is probably not intent-faithful.

## Recommended Work Order

### 1. Finish #339 as a compact effective-authority view

Do this before broad Memory or contract expansion. Agents need one cheap place to inspect which surfaces govern the current decision.

Acceptance standard:

- available through an existing compact query or report path
- descriptive, not a scoring system
- separates authoritative, derived, adapter, procedural-owned, and advisory inputs
- names the current active planning owner when present
- includes system-intent pressure without turning intent into task state
- points to deeper surfaces only when needed

### 2. Turn #338 into an actual review gate

The surface-value guardrail should be used whenever a durable surface is added or preserved.

Acceptance standard:

- every new durable surface names repeated cost removed
- every new durable surface names owner and authority class
- every new durable surface names discovery route and validation or drift check
- every new durable surface states whether it replaces, merges, compresses, backgrounds, or merely adds
- additive-only surfaces are rejected unless the repeated cost is explicit and recurring

### 3. Implement closeout distillation before large Memory changes

This should be the next major continuity improvement after #339.

Acceptance standard:

- active plan closeout has a small structured distillation target
- closeout separates death, continuation, memory, config/check, and documentation outcomes
- archived execplans are no longer the normal durable-learning carrier
- proof includes at least one example where plan residue is intentionally not promoted

### 4. Shrink Memory through structured routing, not broad taxonomy

Memory should become more queryable only to reduce rediscovery and pull size.

Acceptance standard:

- first structured record slice covers a small durable-fact class
- ordinary routed Memory pull gets smaller or more precise
- elimination candidates have a path to promotion, shrinkage, or removal
- Memory does not own active sequencing or workflow policy

### 5. Continue contract extraction only where it removes implementation archaeology

Not every Python-owned behavior needs immediate extraction. The priority should be high-trust, repeated, inspectable behavior that agents or checks must reason about.

Acceptance standard:

- extracted contract is consumed by runtime or checks
- extracted contract replaces a hard-coded truth or repeated reverse-engineering path
- parity failure is detectable
- the extraction does not add a new first-contact concept

### 6. Keep local-only memory small and explicitly non-authoritative

Local-only memory is useful, but it can easily become hidden authority. Keep it opt-in, advisory, safe to delete, and promotion-oriented.

Acceptance standard:

- disabled by default or explicitly configured
- never overrides checked-in Memory, planning, config, or docs
- carries confidence and promotion candidacy
- excludes secrets and environment-specific credential material

### 7. Reconcile external-work pressure into candidate state

The repo should not need every external item active, but open work should have a visible routing state.

Acceptance standard:

- tracked and untracked open external items are summarized by decision state
- current-lane readiness stays separate from roadmap quietness
- unresolved external pressure appears as guidance, not noisy raw backlog

## Rejection Tests For Future PRs

Future work should be challenged when any of these are true:

- it adds a new durable surface without retiring, merging, compressing, or backgrounding another path
- it makes the default report larger without a selector or profile boundary
- it preserves old and new models because choosing feels uncomfortable
- it turns advisory posture into authority without an owner change
- it stores active planning or sequencing in Memory
- it leaves reusable learning trapped only in archived plans
- it introduces an alignment score or workflow engine where a descriptive view would do
- it optimizes prompt size while increasing human review or maintenance burden
- it hardens this monorepo's tooling or agent preferences into a portable product contract

## Suggested Measures

The system should start measuring whether future structure actually helps. Useful measures do not need to be elaborate:

- number of first-line startup/read surfaces
- default report size and top-level warning count
- average routed Memory note count and line count
- count of durable surfaces with owner, authority class, discovery route, and drift check
- count of additive surfaces that did not replace, merge, compress, or background anything
- count of archived plans with explicit distillation outcome
- count of external open items without active, candidate, deferred, or rejected routing state
- count of generated or adapter surfaces with named consumer and removal or demotion path

The point is not dashboards. The point is to make "quiet and lower cost" falsifiable.

## Definition Of Done For The Next Phase

The next phase should not be considered done merely because #338 and #339 land.

It should be considered done when a future agent can cheaply answer:

- what is the current active work?
- which surfaces are authoritative for this decision?
- what system intent pressure matters here?
- what should not be read unless needed?
- what external work is unresolved but not current?
- what completed-work learning was promoted, routed, or discarded?
- what surface was removed, merged, compressed, or backgrounded by the new work?

If the answer requires broad scanning, the system has not yet embodied its intent in ordinary operation.

## Bottom Line

Agentic Workspace has crossed an important threshold: it now has enough structured machinery to make intent preservation and continuation real.

The next risk is not lack of structure. The next risk is structure that grows faster than it removes cost.

Future work should be judged by compression, decisiveness, and closeout learning. Finish the effective-authority view, make surface-value review unavoidable, distill completed work into the right owner surface, and shrink the ordinary reading path. That is the route most consistent with the stated system intent.
