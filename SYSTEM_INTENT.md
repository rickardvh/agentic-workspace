# System Intent

This file states the package's durable purpose and the main intents that should guide future work.

It exists to keep the system aligned as issues, slices, and implementation details evolve.
It is not a backlog, a plan, or a full architecture document.
It is the compact answer to:

- what is this system trying to become?
- what must future work preserve?
- what should the system resist becoming?

## Purpose

Agentic Workspace should be a quiet, repo-native continuity and execution layer that preserves human intent, keeps active work cheap to continue and verify, and reduces total operating cost for agents without becoming a visible framework or a second source of truth.

## Governing intents

### 1. Preserve the right things, not more things
The system should keep only information that is expensive to rediscover and necessary for safe continuation.

That includes:
- current bounded execution state
- durable repo understanding
- higher-level convergence context
- proof and ownership boundaries
- compact handoff and review residue

It should resist becoming a prose archive, a second backlog, or a broad framework-shaped knowledge dump.

### 2. Keep agents aligned with human intent across time
The human/domain expert owns **why**.
The system-shaping layer reasons about **what** best serves that why.
The implementation layer owns **how**.

The package should preserve that ladder across bounded slices, interruptions, delegation, and review.
It must not silently rewrite the human's intended outcome just because a narrower local interpretation looks plausible.

### 3. Make active work cheap to start, continue, hand off, review, and finish
The package should act as a low-cost execution substrate for bounded work.

Active work should be:
- easy to start from small checked-in state
- easy to continue after interruption
- easy to hand off between agents
- easy to review against intent and scope
- easy to finish cleanly without dangling ends

### 4. Reduce total interaction cost, not just prompt size
The system should lower the total cost of getting a tranche done correctly.

That means reducing:
- rereads
- rediscovery
- clarification loops
- retries
- review and repair cycles
- unnecessary roundtrips
- repeated reasoning caused by missing residue

Optimize for total successful-completion cost, not one narrow metric.

### 5. Make weaker agents safer and stronger agents more worthwhile
The package should reduce interpretation burden enough that weaker agents can succeed on bounded work more often.
It should also make larger models economically worthwhile by ensuring that expensive reasoning is spent on judgment, shaping, and review rather than orchestration waste.

### 6. Prefer queryable compact state over prose-first operation
The system should prefer:
- machine-readable active state
- narrow selectors
- compact reports
- lazy discovery
- thin human-readable views

Prose should explain the system and support maintenance, but should not remain the main operational substrate when a compact contract would do better.

### 7. Stay quiet, repo-native, and low-residue
The package should help from the background.

It should:
- live primarily in its own domain
- keep ownership unambiguous
- avoid leaking package artifacts into the wider repo
- remain easy to remove cleanly
- justify every visible user-facing surface by clear operating-cost savings

Promoted output should become normal repo output.
Package residue should remain package residue.

### 8. Be useful even when agents only partially comply
The package cannot depend on perfect obedience or a universal plugin standard.

It should therefore be:
- easy to discover
- cheap to follow
- useful with partial adoption
- visibly lower-trust when bypassed
- better than ad hoc repo scavenging

The system should succeed under imperfect agent behavior, not only under ideal integration.

## Supporting intents

### 9. Convert repeated friction into product improvement
Repeated human steering, repeated proof confusion, repeated handoff repair, repeated context overload, and repeated late failure should become signals for product refinement.

The workspace should adapt itself before repeatedly asking the repo or the user to compensate.

### 10. Keep boundaries and ownership sharp
Planning, Memory, package-owned machinery, repo-owned artifacts, local state, and promoted output must not blur.

A cheaper system is usually also a system with sharper boundaries and fewer ambiguous surfaces.

### 11. Preserve durable understanding without turning Memory into a dump
Memory should hold what is expensive to forget and useful to recover:
- invariants
- authority boundaries
- anti-trap knowledge
- durable rationale
- runbooks

It should not become generic documentation mirroring, hidden active planning, or broad workaround accumulation.

### 12. Keep planning residue proportional to its value
Execplans, run artifacts, completion residue, reports, and archives should justify their continued size and visibility.

Finished work can be inspected through git and the resulting repo state.
Whatever survives in planning after work is done should usually be much smaller than the full narrative used during active execution.

## Anti-intents

The system should resist becoming any of the following:

- a visible workflow framework the user must consciously operate
- a repo-side script for micromanaging the agent's local judgment
- a surface-growing contract maze where every good idea becomes a new file or command
- a historical archive preserved mainly because it already exists
- a blurry ownership model where package-owned and repo-owned artifacts are hard to distinguish
- a local optimization machine that makes one step cheaper while increasing total loop cost

## Design tests for future work

New work should be favored when it does one or more of the following:
- preserves human intent more faithfully across time
- makes bounded work cheaper to continue or verify
- reduces total interaction cost
- makes weaker agents safer without adding heavy ceremony
- makes stronger-agent effort more reusable
- removes, merges, compresses, or backgrounds older machinery
- sharpens ownership or reduces package residue

New work should be questioned when it mainly:
- adds a new visible concept or surface without replacing an older one
- preserves narrative history more than future usefulness
- increases framework feel in ordinary use
- scripts local execution judgment instead of supporting it
- improves one narrow loop stage while making the overall system heavier

## Compact operating rule

Keep the right context.
Shape the right bounded work.
Preserve the right intent.
Make continuation cheap.
Stay quiet.
