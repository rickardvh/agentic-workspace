## Issue 1

**Title**  
`[Planning]: Add a hard surface-growth rule so each new contract surface must replace, merge, or materially simplify an older path`

**What kind of planning signal is this?**  
Product guardrail

**Problem**  
The product now has many strong, narrowly scoped contract surfaces. That precision is useful, but it also creates a long-term risk: concept count can keep growing even when individual additions are reasonable.

The repo is already at the point where the main risk is not lack of ideas. It is accumulating enough surfaces that:
- routing becomes harder
- conceptual load rises
- agents need more product literacy before first safe action
- the cost of understanding the system may start to compete with the value it provides

The product currently needs a stronger explicit rule that new contract surfaces must not merely be good in isolation. They must also reduce or absorb existing complexity.

**Expected behavior or better outcome**  
The product should adopt a maintenance rule such as:

- every new contract surface must either replace, merge, or materially simplify an older path
- if a new surface does not reduce ambiguity, rereading, or repeated correction, it should probably not survive
- every review of a new surface should include “what can now be deleted, collapsed, or demoted?”

The result should be:
- slower concept creep
- better product compression over time
- more confidence that each surface earns its place
- lower cognitive setup cost for new agents and maintainers

**Should this be addressed in the shipped product first?**  
`Yes: this looks like a package or contract improvement`

**Product-first reasoning**  
Yes. At the current maturity level, preventing avoidable concept growth is part of product quality, not just maintenance style.

**Likely affected surfaces**  
- design principles  
- roadmap and issue triage  
- review workflow  
- docs or contract surfaces

**Best next planning destination**  
`ROADMAP.md candidate`

**Urgency**  
`Should be scheduled soon`

**Bounded scope**  
Add one compact product rule for contract-surface growth and apply it to the next promotion/review tranche.

A good first slice would:
- define the rule in one design-principle surface
- add a short checklist for new contract proposals
- require one explicit deletion/merge/compression review in the next surface-focused tranche
- test whether the rule changes the outcome of one pending design decision

**Non-goals**
- Do not freeze all new capability work.
- Do not create a heavy approval process.
- Do not confuse bounded contract growth with anti-innovation doctrine.


## Issue 2

**Title**  
`[Planning]: Run a one-time contract consolidation pass to merge or retire surfaces that no longer need to stand alone`

**What kind of planning signal is this?**  
Product refinement

**Problem**  
The repo has accumulated a rich set of contract surfaces around:
- delegated judgment
- delegation posture
- capability-aware execution
- proof selection
- jumpstart
- compact answer profiles
- reporting and summaries
- handoff artifacts
- compact planning state

Many of these are individually good, but the product may now be carrying more named surfaces than normal operation actually needs.

Incremental cleanup helps, but the repo likely needs one deliberate consolidation pass that asks:
- which surfaces are truly user-facing
- which are maintainer-only doctrine
- which can be folded into a smaller operating model
- which should remain explicit because they earn their keep

**Expected behavior or better outcome**  
The product should run one bounded consolidation pass focused on:
- merging nearby concepts where separation is not paying off
- demoting maintainer-only doctrine out of the normal operational path
- retiring any standalone surfaces that no longer need separate existence
- reducing the number of things a normal agent must understand before safe action

The result should be:
- a smaller concept map
- clearer product shape
- lower onboarding cost
- better alignment between surface count and real usage

**Should this be addressed in the shipped product first?**  
`Yes: this looks like a package or contract improvement`

**Product-first reasoning**  
Yes. The product is now mature enough that reduction is as important as invention.

**Likely affected surfaces**  
- default-path contract  
- reporting/routing surfaces  
- planning and workspace docs  
- design-principle surfaces  
- possible contract docs that can be merged or demoted

**Best next planning destination**  
`ROADMAP.md candidate`

**Urgency**  
`Should be scheduled soon`

**Bounded scope**  
Run one one-time consolidation review over the current contract ecosystem.

A good first slice would:
- classify current surfaces as user-facing, maintainer-facing, or support-only
- identify one or two concrete merge/remove/demote actions
- update the routing story afterward
- keep the pass bounded enough to finish in one short tranche

**Non-goals**
- Do not rewrite the whole product architecture.
- Do not collapse distinctions that still have strong operational value.
- Do not turn this into a broad documentation rewrite without actual surface reduction.


## Issue 3

**Title**  
`[Workspace]: Review and reduce orchestration-layer code concentration so the product contract is easier to evolve safely`

**What kind of planning signal is this?**  
Internal architecture gap

**Problem**  
The external product shape is increasingly coherent, but the implementation may still be too concentrated in the orchestration layer.

That creates risks such as:
- contract logic, routing, reporting, parsing, and output formatting being too entangled
- policy growth making the implementation harder to reason about
- future reductions or schema extraction becoming harder than they should be
- confidence in the product shape exceeding confidence in the implementation shape

This is not primarily a docs problem. It is an internal architecture problem.

**Expected behavior or better outcome**  
The repo should run a focused architecture review of the orchestration layer and then reduce concentration where needed.

The review should assess separation between:
- parser setup and command routing
- contract loading and schema-backed surfaces
- lifecycle execution
- reporting/projection logic
- formatting/output concerns
- policy decisions that should be pulled into clearer modules

The result should be:
- safer future refactors
- easier contract extraction
- clearer ownership boundaries in code
- lower maintenance risk

**Should this be addressed in the shipped product first?**  
`Yes: this looks like a package or contract improvement`

**Product-first reasoning**  
Yes. The product is now serious enough that implementation concentration is a real risk to evolution, even if the user-facing design remains sound.

**Likely affected surfaces**  
- workspace CLI implementation  
- contract-loading code  
- report/projection logic  
- lifecycle execution code  
- internal tests and architecture docs

**Best next planning destination**  
`package backlog item`

**Urgency**  
`Useful follow-up, not urgent`

**Bounded scope**  
Run one focused architecture review and choose one high-value separation improvement.

A good first slice would:
- review code concentration by responsibility
- identify one or two especially overloaded seams
- pick one bounded extraction or separation
- confirm that behavior stays unchanged at the product surface

**Non-goals**
- Do not rewrite the CLI from scratch.
- Do not refactor code structure without a clear boundary gain.
- Do not broaden this into a general style cleanup.


## Issue 4

**Title**  
`[Workspace]: Define a deliberately lightweight operational profile so smaller repos can adopt a useful core without the full framework burden`

**What kind of planning signal is this?**  
Product strategy gap

**Problem**  
Agentic Workspace is currently much closer to a serious framework than to a lightweight utility.

That is acceptable for its core audience, but it creates an adoption problem:
- smaller teams may want a useful subset
- repos may want lighter structure before adopting the full operating system
- selective adoption by module is not always the same thing as lightweight operational profile

The missing piece is a more intentionally minimal operating profile.

**Expected behavior or better outcome**  
The product should define one lightweight operational profile that keeps the highest-value core while reducing framework burden.

Possible shapes could include:
- reporting/query-first core without broader workflow richness
- planning-core-only with a reduced operational surface
- memory-core-only focused on the highest-value durable note classes
- a compact “just enough” profile for repos that want guidance without the full surface map

The result should be:
- clearer adoption spectrum
- lower barrier for cautious adopters
- better product segmentation
- stronger story for who should adopt which depth of the system

**Should this be addressed in the shipped product first?**  
`Yes: this looks like a package or contract improvement`

**Product-first reasoning**  
Yes. If broader practical adoption matters, the product needs more than “full framework” versus “different module combination.”

**Likely affected surfaces**  
- README and product messaging  
- preset or profile design  
- reporting/routing surfaces  
- package adoption guidance  
- docs or contract surfaces

**Best next planning destination**  
`ROADMAP.md candidate`

**Urgency**  
`Useful follow-up, not urgent`

**Bounded scope**  
Define one first lightweight operational profile and explain who it is for.

A good first slice would:
- identify the smallest high-value surface set
- distinguish it from full selective adoption
- update adoption guidance accordingly
- test the profile on one smaller or less framework-tolerant repo

**Non-goals**
- Do not fork the whole product into separate editions.
- Do not weaken the full framework path.
- Do not promise broad simplicity if the chosen profile still carries full conceptual weight.


## Issue 5

**Title**  
`[Review]: Add outsider-legibility as a standing review dimension so new external agents are measured by how quickly they reach first safe action`

**What kind of planning signal is this?**  
Product refinement

**Problem**  
The repo is self-hosting and increasingly rich in contracts, which makes it easy to normalize complexity that long-time users and maintainers can navigate but fresh external agents may not.

Current review modes cover many important things, but outsider legibility is not yet explicit enough as its own recurring review concern.

That leaves a risk that:
- terminology is internally consistent but still dense
- the product is easy for insiders and harder for outsiders
- complexity feels reasonable only because the team already knows the system

**Expected behavior or better outcome**  
The review system should explicitly ask:
- how many concepts must a fresh capable external agent internalize before first safe action?
- which terms or surfaces are likely to confuse outsiders?
- which things should be skippable but do not look skippable?
- where does self-hosting familiarity hide product friction?

The result should be:
- better outsider onboarding
- lower concept and vocabulary load
- stronger external-agent compatibility
- earlier detection of self-hosting bias

**Should this be addressed in the shipped product first?**  
`Yes: this looks like a package or contract improvement`

**Product-first reasoning**  
Yes. A product for agents should not rely too heavily on insider literacy to feel well designed.

**Likely affected surfaces**  
- review portfolio  
- contributor/default-path guidance  
- reporting/routing surfaces  
- docs and vocabulary shaping

**Best next planning destination**  
`package backlog item`

**Urgency**  
`Useful follow-up, not urgent`

**Bounded scope**  
Add outsider-legibility as one explicit review dimension and run one bounded pass with it.

A good first slice would:
- define the review question set
- apply it to startup and first-safe-action paths
- identify one or two concrete friction points
- route the result into contract reduction or routing cleanup

**Non-goals**
- Do not optimize for completely unskilled readers.
- Do not reduce useful precision just to flatten all terminology.
- Do not turn outsider-legibility into a vague general UX category.


## Issue 6

**Title**  
`[Review]: Add self-hosting-bias countermeasures so friction seen mainly by fresh external or cheap agents receives extra weight`

**What kind of planning signal is this?**  
Product guardrail

**Problem**  
Because the repo is built and dogfooded by agents working inside its own system, there is a risk of self-hosting bias:
- insiders may underweight friction that only appears to fresh agents
- stronger models may compensate for product weaknesses that cheaper agents expose quickly
- complexity that feels normal internally may still be too high externally

The product already values dogfooding and mixed-agent testing, but it needs a more explicit rule for weighting this kind of signal.

**Expected behavior or better outcome**  
The product should explicitly give extra attention to failures that appear mainly in:
- fresh external agents
- cheaper/weaker models
- agents without strong internal delegation
when those failures concern:
- ambiguity
- routing
- proof choice
- handoff
- restart
- planning curation

The result should be:
- less self-hosting blindness
- better alignment with the product’s stated agent-agnostic and efficiency goals
- stronger pressure to fix ambiguity and overhead rather than relying on strong-model compensation

**Should this be addressed in the shipped product first?**  
`Yes: this looks like a package or contract improvement`

**Product-first reasoning**  
Yes. If the product is meant to help many different agents, then insider and strong-model bias should be treated as a product risk.

**Likely affected surfaces**  
- review and benchmark interpretation rules  
- dogfooding guidance  
- issue-triage guidance  
- model-zoo evaluation workflow

**Best next planning destination**  
`package backlog item`

**Urgency**  
`Useful follow-up, not urgent`

**Bounded scope**  
Define one compact interpretation rule for fresh-agent and cheap-agent failures and apply it in the next review/benchmark pass.

A good first slice would:
- define when this weighting applies
- distinguish product-friction failures from raw capability failures
- apply the rule to one benchmark or feedback tranche
- route one repeated external-only failure into a bounded fix

**Non-goals**
- Do not treat every weak-model failure as equally important.
- Do not overrule maintainers automatically based on model feedback.
- Do not replace real dogfooding with benchmark interpretation alone.


## Issue 7

**Title**  
`[Workspace]: Clarify whether the product is primarily a serious framework or also a broadly adoptable utility, and align messaging and profiles accordingly`

**What kind of planning signal is this?**  
Product strategy decision

**Problem**  
The product currently reads more like a serious framework than a simple utility:
- it has a rich contract ecosystem
- it assumes meaningful agent-centric workflow discipline
- it introduces several managed surfaces and explicit operating concepts

That may be the right choice, but it leaves a strategic ambiguity:
- is the product mainly for repos that want a durable agent operating system?
- or should it also present a compact path for broader practical adoption?

Without a clearer answer, the repo risks:
- promising broader usability than it currently supports
- under-explaining why the framework cost is justified
- or failing to segment its audience and adoption paths clearly enough

**Expected behavior or better outcome**  
The product should make a deliberate positioning decision and align messaging with it.

That might mean:
- explicitly embracing “serious framework” as the primary posture
- or defining a smaller practical utility path alongside the framework core
- or clearly stating which audiences should not adopt the full system

The result should be:
- stronger product honesty
- clearer adoption expectations
- less mismatch between user hopes and actual framework cost
- better coherence between README, presets/profiles, and contract surface design

**Should this be addressed in the shipped product first?**  
`Yes: this looks like a package or contract improvement`

**Product-first reasoning**  
Yes. This is not only messaging. It affects how much surface area the product should carry and how it should present its adoption options.

**Likely affected surfaces**  
- README and front-door messaging  
- adoption guidance  
- presets or profiles  
- design-principle surfaces  
- roadmap prioritization

**Best next planning destination**  
`ROADMAP.md candidate`

**Urgency**  
`Useful follow-up, not urgent`

**Bounded scope**  
Make one explicit positioning decision and align the front door to it.

A good first slice would:
- define the intended primary audience
- define whether a compact adoption path is strategically important
- update the README and adoption guidance accordingly
- make sure the decision matches actual product surface reality

**Non-goals**
- Do not launch a broad rebrand.
- Do not promise simplicity the product does not yet deliver.
- Do not treat this as mere copywriting without product implications.


## Issue 8

**Title**  
`[Review]: Audit ordinary-use surface pull across Memory and Planning and demote, merge, or retire low-pull scaffolding`

**What kind of planning signal is this?**  
Product refinement

**Problem**  
The product clearly solves real problems:
- restart and handoff cost
- active-work drift
- durable repo understanding
- proof/ownership/routing ambiguity
- mixed-agent continuity

But there is a growing risk that some current surfaces are **well designed in theory yet weakly pulled in ordinary work**.

This appears especially plausible for:
- Memory as a whole, which may be conceptually strong but not yet consulted often enough in real repos
- planning surfaces beyond the core trio of `TODO.md`, `ROADMAP.md`, and execplans
- newer reporting/contract/routing surfaces that may exist correctly but still not be the obvious cheap path in day-to-day work

The problem is not only concept count.
It is that the system may now contain some amount of **latent scaffolding**:
- surfaces that are valid
- surfaces that are occasionally useful
- but surfaces that do not yet earn their cost in ordinary operation strongly enough

If so, the product should know that explicitly and act on it.

**Context and evidence**  
Recent review of the repo suggests:
- the core product shape is real and valuable
- the main risk is not fake problems, but over-encoding real ones before enough of the current structure has proved its everyday pull
- Memory in particular appears conceptually strong but not yet convincingly proven as a high-pull everyday surface
- Planning looks healthier, but its strongest practical center of gravity still seems to be the core trio rather than the full surrounding surface ecosystem

The existing issue set already addresses:
- concept reduction
- reporting-first operation
- lazy-discovery measurement
- Memory usefulness
- outsider legibility
- self-hosting bias

What is still missing is one explicit cross-product review asking:
- which surfaces are actually used in ordinary work?
- which ones are merely available but not truly pulled?
- which should be strengthened, merged, demoted, or removed?

**Expected behavior or better outcome**  
The product should run a bounded review of **ordinary-use surface pull** across Memory and Planning.

That review should identify:
- core surfaces that are genuinely used and valuable
- low-pull surfaces that are mostly latent scaffolding
- surfaces that should be strengthened because they are useful but too hidden
- surfaces that should be merged, demoted, or retired because they are not earning their keep

The result should be:
- lower concept overhead
- better alignment between structure and everyday use
- more confidence that remaining surfaces justify themselves operationally
- clearer product focus on what actually reduces cost and ambiguity in normal work

**Should this be addressed in the shipped product first?**  
`Yes: this looks like a package or contract improvement`

**Product-first reasoning**  
Yes. At the current maturity level, the product needs not only richer contracts but evidence that its current surfaces are actually the ones agents and users reach for in ordinary work.

**Likely affected surfaces**  
- memory package  
- planning package  
- report/summary/routing surfaces  
- review workflow  
- docs or contract surfaces

**Best next planning destination**  
`ROADMAP.md candidate`

**Urgency**  
`Should be scheduled soon`

**Bounded scope**  
Run one bounded ordinary-use pull audit across Memory and Planning.

A good first slice would:
- define what counts as ordinary-use pull
- review a small set of normal repo workflows
- identify core, hidden-but-valuable, and low-pull surfaces
- route at least one low-pull result into a merge/demote/remove action
- route at least one hidden-but-valuable result into stronger reporting/routing

**Non-goals**
- Do not build heavy telemetry.
- Do not equate surface existence with usefulness.
- Do not assume low visible activity automatically means success.
- Do not preserve a surface only because it is conceptually elegant.
