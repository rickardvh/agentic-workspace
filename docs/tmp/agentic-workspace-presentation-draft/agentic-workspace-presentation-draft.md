# Agentic Workspace Presentation Draft

This document is working material for structuring a developer-facing presentation. It is not the presentation itself. Its job is to hold the mental model: what problem AI-assisted software engineering creates, which part Agentic Workspace addresses, and how to explain the product without overclaiming.

## 1. Core Thesis

AI coding tools are fast but weak at continuity.

They can produce plausible software-shaped output, but they do not naturally preserve:

- product intent
- project-specific context
- architectural invariants
- proof obligations
- ownership boundaries
- handoff state
- accountability

Agentic Workspace is an attempt to move those things out of chat/runtime state and into small, checked-in, queryable repository surfaces.

The important nuance:

```text
Without a durable operating substrate:
AI should be treated as a fast, unreliable implementation and analysis instrument.

With a durable operating substrate:
agents can be trusted with more software-engineer-like responsibility,
because intent, context, proof, boundaries, and handoff are explicit.
```

Agentic Workspace is therefore not just a guardrail system. It is a trust-building layer. The goal is to let the human step back from micromanaging every prompt and instead guide, review, and steer work through repo-visible contracts.

```text
AI coding failure:
context and intent live outside the repo

Agentic Workspace response:
make agent operating context repo-native
```

One-sentence product frame:

> Agentic Workspace gives a repository a small checked-in operating layer for agents: startup routing, repo-owned configuration, durable Memory, active Planning, proof guidance, lifecycle safety, ownership boundaries, and contract-backed interfaces.

## 1.1 Presentation Spine: Why, What, How

Use a top-down structure:

```text
Why does this package exist?
└─ AI-assisted development loses intent, context, proof, and ownership across time.

What does it do?
└─ It makes agent operating context repo-native, checked-in, queryable, and reusable across agents, so agents can take more responsibility without becoming unaccountable.

How does it do it?
└─ Through a small workspace layer plus optional Memory and Planning modules, backed by config, proof routing, ownership ledgers, lifecycle commands, and contracts.
```

This is the main narrative. The feature hierarchy should support this story, not replace it.

### Why

Agentic Workspace exists because AI-assisted software engineering creates a continuity problem.

Models can produce code quickly, but real development depends on state that must survive beyond one prompt:

- intent
- context
- invariants
- ownership
- proof
- handoff
- durable learning

When those live in chat, every new session or new agent starts with partial memory and weak accountability.

### What

Agentic Workspace gives the repository a small operating layer for agent work.

It turns agent-relevant context into repo-native surfaces:

- startup routes
- resolved configuration
- durable Memory
- active Planning
- proof guidance
- ownership boundaries
- lifecycle safety
- generated/reference contracts

The goal is not blind autonomy. The goal is trustworthy delegation: agents can own more of the implementation loop because the repo records intent, boundaries, proof, and continuation state.

### How

It works by making the correct operating path cheaper than guessing.

```text
Thin startup adapters
-> compact CLI context
-> repo-owned config
-> Memory for durable knowledge
-> Planning for active work
-> proof routing for validation
-> ownership ledgers for boundaries
-> closeout and residue routing
```

The implementation principle is:

```text
Do not rely on chat as the durable coordination layer.
Put durable coordination state in checked-in repo surfaces.
Expose compact commands so agents do not have to read everything.
```

## 2. The Problem Frame

The main weakness of AI-assisted software engineering is not that models cannot write code. They can often write code quickly.

The weakness is that real software engineering depends on continuity across time:

- why the work exists
- what success actually means
- which constraints are hidden but important
- which files own which concerns
- which tests or checks prove the change
- what the next person needs to know
- what should be remembered after the task ends

AI systems are good at producing a plausible next artifact. They are weaker at preserving the durable operating context around that artifact.

## 2.1 Mental Model: AI Coding Agents As Consultants

AI coding agents are consultants. This is not just a metaphor.

They:

- charge per unit of work
- enter and leave projects frequently
- vary in skill, tooling, and working style
- need onboarding into local context
- may not know why existing decisions were made
- produce work that must be reviewed by permanent maintainers
- require handover when the session, model, tool, or agent changes

Developers already understand the risks of bringing consultants into a mature codebase:

- onboarding cost
- knowledge transfer gaps
- local conventions missed
- hidden invariants violated
- work delivered without enough context
- documentation not updated
- handoff quality varying by person
- permanent staff absorbing review and cleanup burden
- accountability becoming blurry if ownership is not explicit

AI agents have the same class of problem, accelerated and repeated more often.

```text
Human consultant problem:
How do we onboard, bound, review, and retain knowledge from temporary contributors?

AI consultant problem:
How do we onboard, bound, review, and retain knowledge from temporary agents?
```

This framing is useful because it avoids both hype and dismissal. The agent can do real work, but the organization must supply the operating structure that makes temporary work safe and cumulative.

Agentic Workspace can be explained as a lightweight consultant operating system for repositories:

```text
Consultant need                  Agentic Workspace response
───────────────────────────────  ─────────────────────────────────────
Onboarding                       startup routing, preflight, compact reports
Knowledge transfer               Memory
Current task handoff             Planning
Scope boundaries                 execplans, ownership ledgers
Review expectations              proof routing, closeout trust
Local policy                     repo-owned config
Safe lifecycle changes           dry-run, ownership-aware install/upgrade
Long-term learning               durable residue routing
```

## 2.2 Distinctive Idea: Friction As Signal

One of Agentic Workspace's more important ideas is that agent friction is not just something to work around.

It is evidence.

```text
If a memory had to be created,
maybe the repo was too hard to understand.

If a task was hard to plan,
maybe the work or architecture was poorly structured.

If proof was hard to select,
maybe validation boundaries are unclear.

If agents repeatedly edit the wrong surface,
maybe ownership is not visible enough.
```

The package treats recurring friction as a signal that the system may need improvement, not merely that the agent needed more instructions.

This is a stronger idea than "store more knowledge." It creates pressure to remove the need for compensating knowledge when possible.

```text
Bad loop:
agent struggles -> add another note -> future agents read more notes

Better loop:
agent struggles -> capture the lesson -> ask whether the repo should be improved
```

Examples:

- A Memory note exists because an invariant is hidden. Maybe the invariant belongs in docs, tests, schema, or code structure.
- A runbook exists because an operation is too manual. Maybe it should become a script or command.
- A Planning execplan is hard to write because ownership is unclear. Maybe subsystem boundaries need to be declared.
- Proof is hard to choose because tests are poorly mapped to surfaces. Maybe proof routing or test organization needs improvement.
- Agents repeatedly make the same mistake. Maybe startup routing, config, warnings, or ownership headers need to change.

This gives Agentic Workspace a feedback loop:

```text
temporary compensation
-> structured signal
-> promotion lane
-> underlying system improvement
-> less compensation needed next time
```

This can be framed as "improvement pressure":

- Memory pressure: durable knowledge should prevent rediscovery, but its existence may reveal missing docs, tests, scripts, schemas, or clearer architecture.
- Planning pressure: difficulty decomposing, executing, or closing work may reveal poor boundaries, missing proof, unclear ownership, or inadequate workflow affordances.
- Proof pressure: validation friction may reveal that test surfaces or contracts are not aligned with actual risk.
- Ownership pressure: repeated wrong-surface edits may reveal missing owner markers or command routes.

This is one of the strongest product differentiators because it turns agent failures into structured improvement signals rather than accumulating a larger pile of instructions.

## 2.3 Distinctive Idea: Intent At Multiple Levels

Another distinctive idea is that intent is not treated as a single prompt.

Agentic Workspace separates and preserves intent at different levels:

```text
System / product intent
└─ What kind of product or operating model are we trying to preserve?

Repo policy intent
└─ What does this repository want agents to optimize for?

Work / lane intent
└─ Why does this slice of work exist, and what larger outcome does it serve?

Execution intent
└─ What exactly is in scope, out of scope, blocked, and ready to prove?

Closeout intent
└─ Did the work satisfy the original intent, or only complete local tasks?
```

This matters because a common AI failure is collapsing all intent into the latest instruction. The model may satisfy the immediate prompt while drifting from the product, architecture, repo policy, or larger lane.

Agentic Workspace tries to keep these levels visible:

- system intent gives directional product constraints
- repo config records shared operating policy
- planning records preserve requested outcome, non-goals, execution bounds, and continuation
- proof and closeout ask whether the intended outcome was actually served
- durable residue records whether anything should carry forward after the task

The useful presentation point:

```text
The prompt is not the whole intent.
```

Real engineering work often has nested intent:

- literal request
- inferred intended outcome
- larger product direction
- constraints and non-goals
- proof expectations
- follow-on responsibility

AW's job is to keep those layers from being lost between sessions and agents.

## 3. Failure Modes of AI-Assisted Software Engineering

These are useful as the opening diagnosis. They can be compressed heavily for slides.

```text
AI coding failure modes
├─ 1. Intent loss
├─ 2. Context loss
├─ 3. Trust gap
├─ 4. Boundary failures
└─ 5. External risk
```

### 1. Intent Loss

The model implements the literal prompt rather than the real product intent.

Common symptoms:

- specification drift
- unstated assumptions filled in confidently
- locally correct work that misses the larger goal
- tests that confirm the model's assumptions instead of the intended behavior
- closeout that says "done" without proving intent satisfaction

Relevant original failure modes:

- specification and intent drift
- testing that confirms the implementation, not the intent
- accountability ambiguity

Agentic Workspace response:

- Planning records intent, non-goals, execution bounds, proof expectations, closeout, and required continuation.
- Execplans preserve why the work exists, what is in scope, and what must be true before claiming completion.
- Closeout separates validation success from intent satisfaction and durable residue.

### 2. Context Loss

The model lacks the repo-specific knowledge that experienced maintainers carry around.

Common symptoms:

- missing internal API conventions
- violating hidden invariants
- rediscovering known traps
- ignoring architectural history
- opening broad files because the narrow context route is not obvious
- losing previous decisions when chat context is compacted or a new agent takes over

Relevant original failure modes:

- weak project-specific context
- plausible but wrong code
- skill and judgment degradation

Agentic Workspace response:

- Startup commands route agents to compact context before broad reading.
- Memory stores durable repo knowledge that is expensive to rediscover.
- Summary/preflight commands provide takeover context without relying on chat history.

### 3. Trust Gap

AI can produce output that looks right before it is right.

Common symptoms:

- code compiles but violates business rules
- tests pass but do not cover the real risk
- more code and commits create a false productivity signal
- review effort moves from writing to validating
- agents run convenient tests instead of the proof that matches the changed surface

Relevant original failure modes:

- plausible but wrong code
- review burden displacement
- false productivity signals
- testing that confirms implementation, not intent

Agentic Workspace response:

- Changed-path proof routing tells agents which checks are relevant.
- Proof surfaces distinguish selected proof from generic "run tests" advice.
- Closeout trust asks whether proof, intent, and continuation are actually satisfied.
- Higher-assurance fields make gates, blockers, traceability, and proof profiles explicit when needed.

### 4. Boundary Failures

AI often edits the wrong surface or crosses ownership boundaries because everything looks like text.

Common symptoms:

- config used as active task state
- planning used as canonical documentation
- startup files growing into huge manuals
- generated files edited by hand
- local-only state treated as shared truth
- package-managed files and repo-owned files blurred together
- responsibility unclear after the model, developer, CI, and reviewer all touched the change

Relevant original failure modes:

- maintainability debt
- unsafe agency
- accountability ambiguity
- review burden displacement

Agentic Workspace response:

- Ownership ledgers classify repo-owned, module-managed, local-only, generated, and fenced surfaces.
- Managed fences make package-owned blocks visible inside repo-owned files.
- Lifecycle commands preserve local and repo-owned content instead of blindly overwriting.
- Config, Memory, Planning, docs, tests, and generated surfaces each get a clearer owner.

### 5. External Risk

Some AI software engineering risks are real but mostly outside Agentic Workspace's scope.

Examples:

- security vulnerabilities
- prompt injection
- unsafe shell/API actions
- dependency, licensing, and supply-chain risk
- excessive permissions
- organizational accountability
- developer judgment degradation

Agentic Workspace can reduce some workflow mistakes around these risks, but it does not replace security review, dependency tooling, CI, code review, production controls, or human accountability.

This distinction is important in the presentation: the product should not be framed as solving all AI coding risk.

## 4. The Missing Layer

Traditional development already has durable repo surfaces:

- source code
- tests
- docs
- CI config
- issue trackers
- CODEOWNERS
- architecture decision records

AI agents add a new operational need:

```text
What should an agent know, do, prove, preserve, and hand off?
```

That information often lives in chat. Chat is the wrong durability layer for serious repo work.

Agentic Workspace adds a small repo-native layer for agent operating context:

```text
Repo
├─ source code
├─ tests
├─ docs
├─ existing team workflow
└─ Agentic Workspace
   ├─ startup routing
   ├─ repo-owned config
   ├─ Memory
   ├─ Planning
   ├─ proof routing
   └─ ownership boundaries
```

## 5. Product Mental Model

Agentic Workspace is not "an AI developer." It is closer to operating infrastructure for AI-assisted development.

```text
Agentic Workspace
├─ tells agents where to start
├─ tells agents what context matters
├─ tells agents what owns what
├─ tells agents how active work continues
├─ tells agents what proof is expected
└─ tells agents where durable residue belongs
```

It is intentionally repo-native:

- checked in
- inspectable
- versioned with the code
- independent of a single chat session
- usable by different agents and tools
- small enough to adopt selectively

## 5.1 What Agentic Workspace Adds Beyond Agent Platforms

Modern agent platforms mostly optimize the agent's current working context.

Agentic Workspace optimizes the repository's durable operating context.

```text
Agent platforms help an agent work.
Agentic Workspace helps the repo remember, route, bound, prove, and continue that work.
```

The package should not compete with native agent functionality such as chat context, model memory, task plans, IDE integration, shell execution, file editing, session summaries, or background runs. Those are useful execution aids.

Agentic Workspace complements them by making the important repo-specific context shared, durable, and reviewable.

### What AW Adds

1. Repo-native shared memory

Platform memory is usually personal, local, model-specific, or account-specific. AW puts durable repo knowledge in checked-in files so every agent and human can inherit it.

2. Cross-agent continuity

Agents come and go: Codex, Copilot, Claude, Gemini, new session, compacted context, new branch. AW gives them a common restart surface independent of the platform.

3. Explicit ownership and authority

Agent platforms can edit files, but they rarely know which file is the authority for policy, active work, durable knowledge, generated output, or local-only state. AW makes those boundaries inspectable.

4. Proof routing

Platforms can run tests, but they do not naturally know which proof is appropriate for a given changed path or work shape. AW makes proof selection part of the repo contract.

5. Durable handoff

Platform summaries are useful, but often private or ephemeral. AW makes handoff state repo-visible through Planning, execplans, closeout, and continuation fields.

6. Promotion of learning

A platform may remember something for one user. AW asks whether the learning should become Memory, docs, tests, config, an issue, or be discarded.

More importantly, AW asks whether the need for that learning reveals an underlying repo problem. A Memory note or Planning difficulty is not only a patch; it can become an improvement signal.

7. Tool-independent operating contract

Built-in agent features are valuable, but each platform has its own conventions. AW gives them a common substrate to consume.

### Synergy Model

```text
Agent platform owns:
execution, interaction, local reasoning, local plans, tool operation

Agentic Workspace owns:
repo-visible operating context, continuity, proof, ownership, and handoff
```

Agents can still use their built-in plans and memory privately. The important output of that work should land in checked-in Planning, Memory, config, docs, tests, issues, or generated contracts when it matters beyond one session.

Good phrasing:

> Agent platforms make agents more capable in the moment. Agentic Workspace makes their work cumulative across time, tools, and contributors.

## 5.2 Weak Agents More Reliable, Strong Agents Cheaper

Another practical way to explain the package:

```text
Weak agents fail because too much repo context is implicit.
Strong agents are expensive because they can reconstruct what is implicit.

Agentic Workspace makes important implicit context explicit,
checked-in, and queryable.
```

This means the package helps at both ends of the capability spectrum.

### Weak Agents Become More Reliable

Weak agents often fail because they must infer too much:

- where to start
- what state matters
- what the repo is trying to preserve
- what owns which surface
- what is in scope
- what proof is expected
- what should happen at handoff
- what should be remembered after the task

Agentic Workspace turns those into explicit surfaces:

```text
implicit startup conventions       -> startup routing / preflight
hidden repo knowledge              -> Memory
ambiguous current work             -> Planning / summary
unclear edit ownership             -> ownership ledgers
unclear repo policy                -> config
unclear validation                 -> proof routing
unclear completion                 -> closeout structure
```

The goal is to make the right path cheaper than guessing.

### Strong Agents Become Cheaper

Strong agents can often recover missing context, but they pay for it in tokens, tool calls, time, and human review.

Agentic Workspace reduces that cost:

- less broad repo reading
- less rediscovery of known invariants
- less inference from stale chat context
- faster proof selection
- cleaner handoff and restart
- fewer repeated explanations from humans
- less need for the model to reconstruct architectural intent
- more durable reuse of prior lessons

Strong agents can still use their reasoning, but they spend it on the actual engineering problem instead of reconstructing the operating context.

### Human Role Moves Up A Level

The human should not need to micromanage every prompt.

With better repo-native context, the human can guide at a higher level:

- clarify intent
- approve boundaries
- inspect proof
- review tradeoffs
- decide follow-on ownership
- steer product direction

This is a trust-building argument:

```text
AW does not ask humans to trust agents more blindly.
It makes the conditions for trust more explicit.
```

## 6. Core Product Loop

This is probably the clearest central slide.

```text
start
  -> route
  -> recover context
  -> work inside bounds
  -> prove the right scope
  -> close out honestly
  -> preserve durable residue
```

Expanded:

```text
1. Start
   Agent reads thin startup adapter and runs compact startup command.

2. Route
   Workspace output points to config, Memory, Planning, proof, or docs.

3. Recover context
   Agent gets current active state and durable repo knowledge.

4. Work inside bounds
   Planning/ownership define scope, non-goals, and escalation triggers.

5. Prove
   Changed-path proof routing selects relevant validation.

6. Close out
   Agent separates proof, intent satisfaction, remaining risk, and continuation.

7. Preserve residue
   Durable learning is routed to Memory, docs, tests, config, issues, or discarded.
```

## 6.1 Cost Model: Avoiding Rework

Agentic Workspace invests overhead on the assumption that it prevents larger downstream costs.

The highest-level cost is not that an agent makes a small mistake.

The expensive failure is rework:

```text
wrong context
-> wrong implementation
-> weak proof
-> false confidence
-> later rediscovery
-> redo the work properly
```

This is where AI-assisted engineering can become deceptively expensive. A task may look fast at the local level because code was produced quickly, while the system-level cost appears later:

- reviewers must reconstruct missing intent
- maintainers must unwind wrong assumptions
- bugs appear after apparently successful validation
- follow-on work starts from a distorted understanding
- architectural coherence is harder to recover
- the same context must be rediscovered in a later session

The package is trying to reduce the probability of expensive redo loops.

```text
AW overhead:
write down intent, context, proof, ownership, and handoff

Avoided cost:
redoing work because intent, context, proof, ownership, or handoff was wrong
```

This is the big-picture argument. The lower-level failure modes matter because they are mechanisms that create rework.

```text
Lost intent              -> redo the wrong solution
Weak repo context        -> fix hidden invariant violations
Wrong-surface edits      -> unwind ownership damage
Weak proof               -> repair regressions later
Bad handoff              -> restart or duplicate the work
Repeated rediscovery     -> pay onboarding cost again
Instruction debt         -> future agents make slower, noisier decisions
Maintainability erosion  -> every later change costs more
```

The practical claim:

> Agentic Workspace spends a little more effort upfront so teams spend less effort later re-understanding, repairing, and redoing agent-assisted work.

## 6.2 Origin Failure Pattern: Slice Completion Mistaken For Feature Completion

One concrete failure that motivated the package:

```text
Human + agent plan a larger feature.
Human tells agent to implement the plan.
Agent implements the first bounded slice.
Agent marks the plan complete.
The larger feature is not fully integrated.
The incompleteness is discovered much later.
```

This is especially costly in large systems because the missing integration may not be obvious until another feature depends on it.

Common variants:

- The agent implements only the first slice of a larger feature and closes the whole plan.
- The agent follows a repo-saved plan, but deletes it after completing one local part.
- The agent creates a new parallel subsystem instead of integrating with the existing architecture.
- The agent confines itself to a subdirectory and scaffolds a miniature replacement project.
- Cleanup removes only the small visible integration surface while leaving conceptual sprawl behind.
- The feature appears done locally but is not wired into the broader product, lifecycle, tests, or architecture.

This is not just an implementation bug. It is an intent-continuity failure.

```text
The agent completed a task-shaped slice,
but the human asked for a product-shaped outcome.
```

Agentic Workspace tries to prevent this by making several things explicit:

- larger intended outcome
- current slice outcome
- whether this slice completes the larger outcome
- required continuation
- non-goals
- execution bounds
- integration expectations
- closeout decision
- durable residue and next owner

Planning should not let "first slice done" silently become "feature done."

The desired behavior:

```text
If only one slice is complete:
close the slice honestly,
keep the larger intent open,
route required continuation,
and preserve the next integration step.
```

This connects directly to maintainability. Without this discipline, agent work tends to create sprawl:

- duplicate subsystems
- shallow wrappers
- isolated scaffolds
- unintegrated partial features
- abandoned plans
- misleading closeout

The package aims to make agents keep sight of the end goal while still working in bounded, reviewable slices.

## 6.3 Origin Failure Pattern: Steering Debt

Another motivating failure was repeated steering.

At first, the human steers the agent in chat:

```text
Do not create a parallel subsystem.
Use the existing architecture.
Keep the larger feature goal in mind.
Run the right proof.
Do not delete the plan after one slice.
Preserve the handoff.
```

That works briefly, but chat instructions are fragile:

- they disappear between sessions
- they are compacted or summarized badly
- they are private to one tool/runtime
- the next agent does not inherit them reliably
- the human has to repeat them again

The next reaction is to move those instructions into startup files like `AGENTS.md`.

That also fails if it becomes the only mechanism:

- startup files grow into large manuals
- agents stop reading them carefully
- important instructions compete with incidental guidance
- rules become hard to route by task
- startup cost rises
- the file becomes a dumping ground for every previous mistake

This creates steering debt:

```text
agent makes expensive mistake
-> human adds more instructions
-> instructions become larger and noisier
-> future agents miss or misapply them
-> same mistake happens again
```

Agentic Workspace tries to break that loop.

Instead of adding more prose every time, it asks where the guidance belongs:

```text
Repeated repo fact       -> Memory
Active work state        -> Planning
Repo policy              -> config
Proof expectation        -> proof routing / tests
Ownership confusion      -> ownership ledger / managed warning
Canonical explanation    -> docs
Enforceable behavior     -> tests / checks / schemas
One-off context          -> discard after closeout
```

This is closely related to friction-as-signal. If the human keeps repeating the same steering instruction, the system probably needs a better durable surface or a clearer workflow affordance.

The product goal:

> Stop turning every agent mistake into more startup prose. Route durable guidance to the right repo-owned surface, and improve the system when repeated guidance reveals a deeper problem.

## 7. Product Architecture

```text
Agentic Workspace
├─ Workspace layer
│  ├─ startup routing
│  ├─ repo-owned configuration
│  ├─ lifecycle management
│  ├─ ownership boundaries
│  ├─ proof routing
│  └─ combined reports
├─ Memory
│  ├─ durable repo knowledge
│  ├─ anti-rediscovery
│  ├─ route-indexed notes
│  └─ hygiene / promotion pressure
├─ Planning
│  ├─ active execution state
│  ├─ decomposition
│  ├─ execplans
│  ├─ handoff / restart
│  └─ closeout
├─ Contracts and generated surfaces
│  ├─ schemas
│  ├─ command and operation contracts
│  ├─ generated references
│  └─ generated adapters
└─ Maintainer dogfooding
   ├─ model CLI harness
   ├─ weakness ledger
   ├─ workflow scoring
   └─ improvement intake
```

For the presentation, keep Contracts and Dogfooding visibly secondary unless the audience wants implementation details.

## 8. Main Capabilities

### Workspace Layer

The workspace layer is the front door and coordination layer.

It owns:

- startup routing
- resolved configuration
- lifecycle commands
- ownership lookup
- proof routing
- combined reports
- module composition

Important commands:

```text
agentic-workspace start --format json
agentic-workspace preflight --format json
agentic-workspace config --target . --format json
agentic-workspace report --target . --format json
agentic-workspace proof --changed ... --format json
agentic-workspace ownership --target . --format json
```

### Repo-Owned Configuration

Configuration is the repo-owned policy surface.

It answers:

- Which preset is default?
- Which startup file should agents use?
- What workflow artifact profile applies?
- Which advanced features are enabled?
- What local policy is advisory versus shared?
- Which workflow obligations should agents see?

This matters because absent or implicit config causes agents to guess.

### Memory

Memory is durable anti-rediscovery knowledge.

It is for:

- repo invariants
- subsystem orientation
- recurring traps
- non-obvious operator procedures
- durable decisions that are too easy to forget

It is not for:

- active task state
- issue triage
- chat transcripts
- canonical docs replacement
- arbitrary notes

### Planning

Planning is active execution continuity.

It is for:

- current active work
- decomposition into lanes/slices
- bounded execplans
- proof expectations
- handoff/restart state
- closeout and archive

It is not a full project-management system. It is the checked-in continuity layer for agent execution.

### Proof and Trust

Proof routing is one of the strongest developer-facing points.

The product tries to prevent:

```text
"I changed a contract and ran one convenient unit test."
```

It pushes toward:

```text
"These paths changed, so this proof lane is required, and closeout must record whether it passed."
```

### Ownership and Boundaries

Ownership answers:

- Who owns this surface?
- Is it repo-owned, module-managed, local-only, generated, or fenced?
- Is it safe to edit by hand?
- Which command gives the safe view?
- Where should this concern actually live?

This is central to separation of concerns.

## 9. Mapping Failure Modes To Product Features

```text
Failure mode                         Product response
───────────────────────────────────  ─────────────────────────────────────
Intent drift                         Planning intent, non-goals, closeout
Weak repo context                    Memory, startup routing, preflight
Plausible but wrong code             Proof routing, closeout trust
Review burden displacement           Compact summaries, proof expectations
False productivity signals           Intent satisfaction and proof evidence
Maintainability debt                 Ownership boundaries, residue routing
Unsafe agency                        Lifecycle dry-runs, local boundaries
Tests confirm wrong implementation   Independent proof routes and contracts
Handoff discontinuity                Summary, execplans, continuation owner
Wrong edit surface                   Ownership lookup, managed warnings
Context window collapse              Checked-in Memory and Planning
Repeated rediscovery                 Memory capture and hygiene
```

Important caveat:

```text
Security, dependency risk, licensing, CI, and accountability still require normal engineering controls.
```

## 10. Developer Audience Framing

Lead with engineering realism, not AI optimism.

Good framing:

```text
AI can produce code quickly.
The bottleneck shifts to context, review, proof, and continuity.
Agentic Workspace makes those concerns explicit in the repo.
```

Avoid framing:

```text
This makes agents autonomous developers.
This replaces project management.
This eliminates review burden.
This guarantees correctness.
```

Developers will likely accept:

- agents are useful but unreliable
- repo state beats chat state for durable context
- proof selection matters
- ownership boundaries matter
- handoff quality matters

They may resist:

- extra files without clear ownership
- anything that sounds like Jira replacement
- any claim that AI can own accountability
- overly broad process machinery

So keep the tone pragmatic:

```text
This is not a new management layer.
It is a small operating layer for making agent work recoverable and reviewable.
```

## 11. Suggested Presentation Flow

### Slide 1: The Problem

```text
AI coding tools are fast, but their operating context lives in chat.
Real software engineering depends on context that must survive time.
```

### Slide 2: Failure Modes

Use five buckets:

```text
Intent loss
Context loss
Trust gap
Boundary failures
External risk
```

### Slide 3: The Missing Layer

```text
Code, tests, docs, and CI are durable.
Agent operating state often is not.
```

Introduce the repo-native operating layer.

### Slide 4: Product Concept

```text
Agentic Workspace makes agent continuity checked-in, queryable, and tool-independent.
```

### Slide 5: Core Loop

```text
start -> route -> recover context -> work -> prove -> close out -> preserve residue
```

### Slide 6: Three Main Surfaces

```text
Workspace: routing, config, lifecycle, ownership, proof
Memory: durable repo knowledge
Planning: active execution continuity
```

### Slide 7: Trust and Boundaries

```text
Proof routing tells agents what validates the change.
Ownership tells agents where state belongs.
```

### Slide 8: What It Is Not

```text
Not Jira.
Not CI.
Not RAG memory.
Not autonomous orchestration.
Not a replacement for docs, tests, review, or human accountability.
```

### Slide 9: Example Workflow

```text
A new agent enters the repo:
1. Reads AGENTS.md.
2. Runs start/preflight.
3. Sees active Planning and relevant Memory.
4. Makes bounded changes.
5. Runs selected proof.
6. Records closeout and continuation.
```

### Slide 10: Why This Matters

```text
The goal is not more generated code.
The goal is lower cost to continue, review, and trust agent-assisted work.
```

## 12. Possible Live Explanation

Short version:

> The way I think about this is: AI coding tools are very good at producing a plausible next diff, but real engineering depends on continuity. You need to know why the work exists, what owns what, what proof is required, and what the next person needs to inherit. Today, too much of that lives in chat. Agentic Workspace moves that operating context into the repo.

Slightly longer:

> Agentic Workspace is not trying to replace Jira, CI, docs, tests, or review. It sits between the agent and the repo as a small checked-in operating layer. It gives agents a startup route, durable repo knowledge, active planning state, proof guidance, and ownership boundaries. The point is to make agent-assisted work resumable, reviewable, and cheaper to continue.

## 13. Open Questions To Resolve While Preparing

- How much of the presentation should be problem framing versus product tour?
- Should the live demo show a fresh agent entering a repo?
- Should Memory and Planning be explained as independent modules before showing full install?
- Should maintainer dogfooding be a main slide or appendix?
- How much external AI-productivity evidence should be included?
- Should the presentation use this product as a response to AI risk generally, or specifically to continuity/context/proof failures?

## 14. References To Verify Before Final Slides

These came from the initial ChatGPT-generated failure-mode list and should be verified before using in final slides:

- Dr Kelly Blincoe / future AI-driven software engineering paper
- METR 2025 randomized trial on experienced open-source developers
- DORA 2025 report and relationship between AI adoption and delivery stability
- GitClear 2025 code quality analysis
- OWASP Top 10 for LLM Applications

Use them sparingly. The presentation should not depend on contested productivity numbers. The stronger argument is the engineering shape: agent work needs durable intent, context, proof, and ownership.
