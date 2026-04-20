# Agentic Workspace Design Principles

## Purpose

Agentic Workspace exists to make repositories easier to understand, easier to resume, and easier to operate for both coding agents and humans.

It is intended to provide quiet repository infrastructure: durable guidance, explicit working state, and lightweight operational support that improve day-to-day work without demanding constant attention.

The system should help a repository feel orderly, legible, and ready for work, while staying modest in surface area and strict about what it owns.

## Product Intent

Agentic Workspace should:

- move repo-specific operational knowledge into the repository where it belongs
- make repositories easier to understand for both agents and humans
- reduce the startup threshold for a new agent or human entering the repo
- improve agent ergonomics
- reduce required context size and reasoning depth
- enable smaller, cheaper models to work effectively
- reduce unnecessary token use by cutting rediscovery and over-reading
- improve the codebase, documentation, and tooling over time by steering work toward better repository practice

It should also make agent switching economically sane:

- changing subscriptions, tools, or model tiers should not force broad rediscovery
- shared persisted knowledge should be cheaper than repeated re-explanation
- cross-agent continuation should preserve quality while minimizing long-run token spend

It should remain:

- unobtrusive
- clean
- clear
- repo-agnostic
- agent-agnostic
- easy to install, manage, and uninstall
- modular and extendable

A successful Agentic Workspace should provide leverage without noise. It should be visible when help is needed and otherwise stay mostly in the background.

## Core Principles

### 1. Repository-native state beats chat residue

Important operational knowledge should live in checked-in repository surfaces rather than in transient chat history, tool-local memory, or one contributor's working context.

If a fact materially affects future work, restart cost, or safe execution, the repository should be able to carry it.

If the same context is likely to matter across agents, sessions, or contributors, durable checked-in state should beat repeated chat summaries and re-explanation.

### 2. Reduce reading, not increase it

The system should help agents and humans read less, not more.

Good structure narrows the working set:

- load the smallest useful guidance bundle
- route to the right files quickly
- avoid broad exploratory scans when the repo can already point the way

The test is not whether the system adds documentation. The test is whether it reduces unnecessary rediscovery.

### 3. Preserve one home per concern

Each kind of information should have one primary owner.

Examples:

- durable technical residue belongs in memory
- active execution state belongs in planning
- routing belongs in routing surfaces
- validation belongs in checks
- orchestration belongs in the workspace layer
- stable broad explanation belongs in canonical docs

When the same concern is owned in several places, drift becomes normal.

### 4. Make the repo easier to enter

A new agent or human should be able to orient quickly:

- what matters now
- what rules govern this repo
- what is durable context
- what to read first
- what to run
- what not to touch

Lowering that threshold is one of the main product goals.

### 5. Structure should lower reasoning cost

The system should reduce the amount of inference required to do useful work.

That means:

- clearer ownership
- narrower startup paths
- explicit routing
- bounded validation
- predictable lifecycle surfaces
- fewer hidden conventions

A well-structured repo lets smaller models do more useful work and lets stronger models spend effort on the hard parts instead of on orientation.

### 6. Simplicity should remain viable

Simple work should stay simple.

The system should not force heavy process onto small, local, well-bounded tasks. It should add structure when complexity, ambiguity, collaboration risk, or handoff cost justify it.

Good infrastructure makes complex work safer without making simple work ceremonial.

### 7. Be quiet by default

Agentic Workspace should not try to become the star of the repo.

It should:

- support work
- reduce friction
- preserve continuity
- surface help when needed

It should not:

- demand constant interaction
- scatter high-churn workflow residue everywhere
- create unnecessary visible ceremony
- encourage people to maintain the system for its own sake

Visible machinery should justify its visibility. If a surface can move into reporting, routing, or background structure without losing safety or clarity, prefer the quieter shape.

### 8. Improve the repository, not just the agent experience

If the system repeatedly captures the same workaround, warning, or procedural note, that should be pressure to improve the repo itself.

The right long-term answer is often:

- better docs
- stronger tests
- clearer boundaries
- simpler structure
- better scripts
- stronger validation

Leave the repository cleaner than you found it within the touched scope.

If cleanup would expand beyond the touched scope, record the broader improvement as follow-up instead of silently absorbing it.

New contract surfaces should also earn their place by compressing older paths. A new surface should replace, merge, or materially simplify something that already exists; if it only adds precision, ask what can be deleted, collapsed, or demoted.

The system should help the repo mature, not simply accumulate operational residue forever.

### 9. Favor explicit seams over hidden coupling

Modules should cooperate through clear contracts, not implicit dependence.

Use:

- explicit ownership rules
- manifests and schemas
- generated artifacts derived from canonical sources
- narrow lifecycle hooks
- stable adapters

Avoid:

- hidden cross-module assumptions
- duplicated ownership
- private coupling disguised as convenience

Clear seams keep the ecosystem modular and make selective adoption real.

### 10. Selective adoption must remain valid

The ecosystem should work in parts, not only as a full stack.

A repository should be able to adopt:

- memory only
- planning only
- a composed first-party set
- future modules later

The platform should get stronger when modules are combined, but each module should still make sense alone.

### 11. Lifecycle should be centralized, domain logic should not

The workspace layer should make installation and management easy, but it must not quietly absorb the internal logic of the modules it coordinates.

The platform should centralize:

- lifecycle entrypoints
- preset and module selection
- shared reporting
- orchestration
- shared workspace policy and evidence surfaces that do not justify an independent lifecycle

It should not erase:

- memory ownership
- planning ownership
- future module ownership
- the distinction between workspace-level shared policy/reporting and module-owned domain logic

Convenience must not blur responsibility.

Workspace-self-adaptation should also remain distinct from repo-directed improvement.
The workspace may improve its own fit to a repo through clearer reporting, routing, recovery, or contract surfaces even when repo-directed initiative is tightly constrained.
That distinction should stay explicit so `improvement_latitude = "none"` does not accidentally freeze legitimate workspace self-improvement.
The matching guardrail is that workspace-self-adaptation should stay general, bounded, and cheaper than repeated repo or user burden; it should not accrete into a concealment layer for real repo problems.
Repo-directed improvement should therefore clear a higher bar: repeated shared evidence that the repo is the real friction source, not one-off agent taste, single-run discomfort, or a workspace friction that the product can still honestly absorb inside its own surfaces.

### 12. Generated surfaces must stay trustworthy

Generated docs and routing artifacts are useful only when they remain reliable.

They must:

- derive from canonical sources
- be easy to regenerate
- be clearly marked when generated
- be validated for freshness and consistency

High-confidence stale guidance is worse than missing guidance.

### 13. Collaboration safety matters

The system must work under real git-based collaboration.

That means:

- keep high-churn shared files small
- archive completed active surfaces promptly
- prefer feature-scoped files over giant mutable dashboards
- preserve clear authority rules
- make conflicts recoverable
- keep generated surfaces reproducible

A good repository system should degrade gracefully under normal collaborative pressure.

Shared continuity should also survive tool diversity:

- one contributor's agent choice should not become another contributor's restart tax
- persisted repository state should let different subscriptions, vendors, or local models continue work without broad rediscovery

### 14. Dogfooding is a proving ground, not a special exception

This repository should validate the product through real use.

That means:

- major capabilities should be exercised here before being treated as mature
- friction discovered here should feed back into the product
- repo-specific hacks should not be normalized as product behavior
- internal use should strengthen portability rather than weaken it

Dogfooding is valuable only if it produces better general systems.

### 15. Help the agent do the job, do not script the job

The product should make bounded work easier, not turn the repository into a workflow script that dictates every local decision.
It should stay opinionated about what must remain true, not about the exact local choreography used to get there.

Prefer:

- thin guidance that helps the agent proceed safely
- capability-shaped contracts that leave room for local judgment
- explicit escalation boundaries when the task shape changes

Avoid:

- over-prescriptive execution choreography
- scheduler-like repo policy
- broad local workflows that only work when the agent follows a long script

If a proposed surface mostly tells the agent exactly how to work rather than helping it work better, ask whether it is actually reducing repository operating cost.
Prefer boundaries over procedures: if a surface mostly tells the agent how to work instead of what boundary to preserve, look for a thinner contract or a clearer handoff instead.
Repo-owned output preferences should follow the same rule: a surface such as `optimization_bias` may change rendering density or residue style, but it should not prescribe the agent's internal execution method.

### 15. Portability matters more than local cleverness

A feature is stronger when it works in many repos, with different codebases, different contributors, and different agent tools.

Prefer:

- plain checked-in surfaces
- narrow assumptions
- conservative adoption
- clear lifecycle behavior
- modular design

Avoid solutions that only feel elegant inside one particularly well-understood monorepo.

### 16. Repository leverage should complement runtime leverage

Agentic Workspace should assume that a capable coding assistant may already have better internal tools for delegation, model selection, reasoning depth, or execution shaping than the repository can or should prescribe.

The product should therefore focus on checked-in leverage:

- explicit execution contracts
- durable handoff state
- smaller restart surfaces
- machine-readable validation expectations
- clear escalation boundaries
- durable residue promotion

It should help runtimes do better work without trying to replace their native orchestration.

That means:

- prefer inference and checked-in guidance over hard orchestration rules
- use capability language instead of vendor-specific routing
- empower weaker agents by reducing ambiguity and rereading
- keep repo semantics authoritative even when local/runtime preferences differ
- treat smooth switching between agents, subscriptions, and future local models as a first-class continuity goal

The system is succeeding when a strong agent can ignore optional preferences and still benefit from the repo, while a weaker agent can rely on the same checked-in surfaces to perform above its base capability.

### 17. Proof should beat preference

Mixed-agent features should earn their place through repeated ordinary work, not intuition alone.

If a feature claims to save tokens, reduce restart cost, or improve handoff quality, the product should be able to evaluate that claim through real dogfooding, bounded review, or repeated workflow evidence.

Preference without proof is not enough when the product goal is efficiency.

### 18. Continuity quality matters more than artifact count

A handoff artifact is useful only when the next agent or human can continue with minimal rereading and without reconstructing hidden assumptions.

Smooth switching means the next contributor can recover:

- current intent
- hard constraints
- relevant durable context
- proof expectations
- immediate next action

without broad startup rereads.

### 19. Optimize total token cost, not single-run cheapness

The cheapest-looking run is not always the cheapest workflow.

Prefer:

- a stronger agent once when the work still needs interpretation, proof choice, or boundary setting
- a smaller or cheaper agent later when the slice has become bounded and mechanically clear
- checked-in continuity when work may cross sessions, tools, contributors, or subscriptions

Do not prefer:

- a small agent first when it still has to rediscover the contract
- hidden internal delegation as the only continuity mechanism
- saving model tokens mainly by shifting cost into human prompting, cleanup, or repeated restarts

The success test is lower total cost across planning, execution, validation, interruption, handoff, and restart without quality loss.

### 20. Do not save model tokens by creating human bureaucracy

A feature fails if it reduces model-side token use but shifts comparable or greater cost onto humans through extra prompting, triage, cleanup, or hidden configuration burden.

The product should reduce total operating cost, not merely move it between participants.

### 21. New work must earn its way in

At this maturity level, new planning or contract work should enter the queue only when one of these is true:

- measured overhead reduction opportunity
- repeated practical failure class
- repeated dogfooding friction
- explicit maintainer override for strategically important work

Concept opportunity alone is not enough.
The default posture should be subtraction and proof, not idea accumulation.

## Design Tests

A proposed feature is moving in the right direction if it helps answer yes to questions like:

- Does this reduce startup friction?
- Does this reduce rediscovery?
- Does this make the repo easier to understand?
- Does this lower context or reasoning cost?
- Does this lower total restart, handoff, and correction cost over time rather than only in one run?
- Does this preserve or sharpen ownership boundaries?
- Does this improve the repo itself over time?
- Can it remain quiet in normal use?
- Can it be adopted selectively?
- Can it be removed cleanly if needed?
- Would it still make sense outside this monorepo?
- Does this strengthen checked-in leverage without trying to out-orchestrate the runtime?
- Is there measured friction, repeated failure, repeated dogfooding pain, or an explicit maintainer reason for adding it now?

A proposed feature is suspicious if it tends to:

- create new shared hot files
- duplicate source-of-truth surfaces
- require broad reading
- hide ownership
- add ceremony to simple work
- save agent tokens mainly by shifting work onto humans
- depend on special knowledge of this repo
- make the workspace layer absorb module logic
- leave behind high-churn residue that outlives its value
- try to schedule runtime model choice or delegation from checked-in policy
- enter planning mainly because it sounds like a useful idea rather than because the repo has paid a real cost for its absence
- add a new contract surface without naming the older path it replaces, merges, or materially simplifies

## Practical Standard

The standard for success is not novelty.

The standard is that the repository becomes:

- easier to enter
- easier to resume
- easier to trust
- cheaper to operate with agents
- clearer for humans
- better structured over time

Agentic Workspace should provide real operating leverage while staying quiet enough that most of its value is felt more than noticed.

## Short Version

Agentic Workspace should make repositories quietly well-run for agents and humans.

It should move important operational knowledge into the repo, reduce startup cost, cut unnecessary context and reasoning, support smaller and cheaper models, and improve the repository over time through better structure and clearer practice.

It should do this while remaining unobtrusive, clean, modular, portable, and easy to manage.

That is the bar.

## Product Doctrine

This repository exists to build agent-first workspace infrastructure: systems that make coding agents more capable, more reliable, and easier to trust in real repositories.
The one-word summary of the product goal is `efficiency`: maximum quality at minimum token cost over time for a single repository.

Dogfooding is a primary development mode here, not just background context.
When normal work in this repo reveals friction, ambiguity, noisy maintenance, or repeated agent missteps in the shipped planning or memory systems, treat that as a product signal that should enter the checked-in feedback loop.
Route that signal into the active execplan, `.agentic-workspace/planning/state.toml` (`todo.active_items` or `roadmap`), memory, or canonical docs as appropriate instead of treating chat or ad hoc direct package edits as the default feedback path.

Work in this repo should steer toward these goals:

- Build for agents first, while keeping the result legible and useful to humans.
- Treat development work in this repo as live testing of the shipped packages and workflows.
- Dogfood every major capability here before treating it as mature.
- Continuously evaluate friction, reliability gaps, confusing ownership, and handoff failures during normal work.
- Feed meaningful friction and improvement signals back into the active plan, roadmap, or routed memory instead of leaving them in chat-only residue.
- When internal use reveals repeated friction, prefer fixing the shipped package or contract over adding repo-local workaround guidance.
- Prefer repository-native state over chat-only or tool-local state.
- Give agents durable context, explicit execution state, clear routing, narrow validation, and cheap handoff.
- Optimise for continuity across sessions, tools, models, and contributors.
- Prefer work that lowers token spend by shrinking rediscovery, cross-checking, and avoidable rereads.
- Keep systems modular, portable, and selectively adoptable in other repos.
- Preserve strict boundaries between concerns; do not let planning, memory, routing, checks, or workspace orchestration blur together.
- Treat internal use as a proving ground, not a licence for repo-specific hacks.
- Generalise only after a feature works under real autonomous use here.
- Avoid overfitting to this monorepo when shaping package behavior; prefer solutions that remain broadly useful in other repositories.
- Favour mechanisms that reduce rediscovery, drift, and manual supervision.
- Keep the system quiet in normal use: prefer structure that lowers reading and reasoning cost over workflow ceremony.
- Leave the repository cleaner than you found it within the touched scope, and record broader cleanup as follow-up instead of silently expanding the task.
- Preserve one primary owner per concern so planning, memory, routing, checks, and orchestration do not drift into duplicated authority.
- Treat selective adoption as a product requirement, not a nice-to-have: each module should remain useful alone.
- Keep lifecycle centralized and domain logic package-local so workspace convenience does not erase module responsibility.

The standard for success is not novelty. It is giving agents real operating leverage in a repo: faster restart, safer execution, better continuity, and less wasted context.
When several plausible improvements compete, prefer the one that most directly removes an efficiency tax from normal repo work.

### Dogfooding Rule

- Treat this monorepo as the proving ground for shipped agent workflows.
- When normal work exposes a plausible product-level deficiency, explicitly ask whether the repo symptom should be dogfooded into a product improvement even if the user did not request that step.
- Do not wait for an explicit prompt before suggesting the checked-in dogfooding path when the answer is plausibly yes.
- If repo-local work exposes a real product deficiency in planning, memory, routing, checks, or lifecycle behavior, capture it in the checked-in planning or memory system so the signal survives the current session.
- Prefer promoting the signal into planned work instead of making unauthorised direct package changes solely because the repo exposed the issue.
- Make direct package or shipped-contract fixes only when they are already in active scope, explicitly requested, or clearly the smallest approved way to complete the current planned work.
- When a repo-specific symptom does not generalise cleanly, record the signal in memory, docs, roadmap, or an execplan instead of forcing a package change.
- When a finding surfaces about this repo, explicitly ask whether it could or should have been found, prevented, or remediated by the shipped product itself.
- If the answer is plausibly yes, record that as part of the checked-in feedback loop and treat the repo-local symptom as a potential package or contract improvement, with the product surface as the preferred remediation target when planning later promotes the work.
