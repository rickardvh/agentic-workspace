# 1. Planning-only development

This track assumes the planning system should become a strong standalone package or framework, independent of memory.

## Goal

Make the planning system robust, low-drift, and independently useful for agent-centric execution without depending on the memory package.

## Product boundary

Planning owns:

* activation
* sequencing
* execution contracts
* candidate queue
* promotion/readiness rules
* archive discipline

Planning does **not** own:

* durable technical residue
* invariants as a knowledge system
* recurring failures as long-lived memory
* runbooks as durable technical context

## Phase A — Harden the current planning model

Focus on the current repo as the proving ground.

### A1. Tighten `TODO.md`

Implement:

* max 3 `Now` items warning
* line-count warning
* shape enforcement for `ID / Status / Surface / Why now`
* warning when `Why now` becomes overloaded
* warning when non-trivial in-progress work lacks an execplan
* warning when completed detail remains inline

### A2. Harden execplans

Implement:

* required-section checks
* exactly one active milestone warning
* exactly one immediate next action warning
* drift-log compaction warnings
* touched-path scope-guard warnings
* invariant-section prose-bloat warnings
* blocker-section narrative drift warnings
* archive-over-accumulation warnings

### A3. Harden `ROADMAP.md`

Implement:

* candidate-shape checks
* warning when entries become execution-shaped
* warning when promoted work still retains too much detail
* warning when promotion/reopen signal is missing
* pruning pressure for stale candidate residue

### A4. Add planning health checks

Add:

* `plan-check`
* possibly later `plan-report`

This should warn on:

* activation overload
* missing execplan linkage
* multi-active-milestone execplans
* roadmap execution drift
* archive-over-accumulation
* cross-surface duplication inside planning

## Phase B — Improve planning semantics

Borrow good ideas from systems like Beads, without runtime dependencies.

### B1. Readiness model

Add lightweight fields such as:

* `Ready`
* `Blocked`
* optional dependency references

### B2. Promotion discipline

Make activation more explicitly signal-driven:

* clear promotion triggers
* clear reopen conditions
* no editorial drift

### B3. Startup discipline

Define minimal execution startup:

1. read `TODO.md`
2. read one referenced execplan
3. do not read `ROADMAP.md` unless reprioritising/planning

## Phase C — Extract into a standalone planning package

Only do this once the model is stable in one repo.

The package should ship:

* templates
* checks
* archive discipline
* readiness/promotion rules
* minimal workflow docs

It should not ship:

* memory assumptions
* memory taxonomy
* hardcoded memory hooks

## Main risks to watch

* execplans becoming notebooks
* roadmap becoming a strategic junk drawer
* `TODO.md` becoming a compressed planner
* too much startup overhead
* coupling to one repo’s conventions too early

---

# 2. Memory-only development

This track assumes the memory system remains a standalone package and continues to evolve independently.

## Goal

Make the memory package sharper, more measurable, and harder to degrade, while preserving:

* no runtime dependency
* no hidden state
* small default read surface
* file-first inspectability

## Product boundary

Memory owns:

* durable technical residue
* invariants
* authority boundaries
* recurring failures
* operator runbooks
* routing hints
* current technical context
* memory skills

Memory does **not** own:

* tasks
* backlog
* milestone status
* sequencing
* next-step plans

## Phase A — Continue hardening note quality

### A1. Maintain note-shape discipline

Continue strengthening:

* note-type-specific size pressure
* current-context constraints
* canonical-doc promotion pressure
* improvement-signal lifecycle
* one-home rule enforcement
* overlap detection

### A2. Keep current-context files compressed

Protect:

* `memory/current/project-state.md`
* `memory/current/task-context.md`

These should remain:

* overview-only
* continuation-only
* non-planner
* non-journal

### A3. Tighten always-read surface discipline

Ensure the default read path stays minimal:

* `AGENTS.md`
* `memory/index.md`
* routed notes only as needed

Keep `.agentic-memory/WORKFLOW.md` and similar files out of the normal always-read path unless the task is about the memory system itself.

## Phase B — Improve routing quality

### B1. Working-set pressure

Keep:

* `<=3` default routed notes unless justified
* warning bands above 3 and 5
* required-vs-optional suppression
* per-note route explanations

### B2. Calibration

Continue:

* `routing-feedback.md`
* `route-review`
* fixtures under `tests/fixtures/routing/`

### B3. Aggregate visibility

Implement and refine:

* `route-report`
* fixture-backed working-set pressure summaries
* separate missed-note vs over-routing summaries

## Phase C — Improve the control plane

### C1. Make `manifest.toml` increasingly operational

Use it more actively for:

* routing
* staleness pressure
* high-level/routing-only compactness
* lifecycle warnings
* note-role enforcement

### C2. Keep docs minimal, move procedure into skills

Continue shifting repeatable workflows into:

* `memory-router`
* `memory-refresh`
* `memory-hygiene`
* `memory-capture`
* `memory-upgrade`

Core docs should remain:

* short
* architectural
* non-procedural

## Phase D — Empirical validation

Do this carefully, without runtime telemetry if possible.

### D1. Routing-quality measurement

Continue improving:

* missed-note capture
* over-routing examples
* fixture coverage
* aggregate summaries

### D2. Token-efficiency benchmarks

Build offline/repeatable evaluation:

* resumed-task startup cost
* notes loaded per task
* working-set size
* missed-note frequency in benchmark scenarios

## Main risks to watch

* routing drift
* note overlap
* current-context drift
* too many “helpful” docs
* metadata becoming richer than the control logic actually uses
* false confidence from limited calibration coverage

---

# 3. Integration development touching both

This track is about making planning and memory work well together without tightly coupling them.

## Goal

Define and strengthen the interface between the planning package and the memory package, while keeping each independently useful.

## Guiding principle

Use **loose coupling with explicit contracts**.

Planning and memory should:

* reference each other where useful
* validate boundary blur
* exchange small hints

They should **not**:

* duplicate ownership
* require each other to function
* mirror each other’s state

## Integration boundary

### Planning exports

Potentially:

* touched surfaces
* touched paths
* active subsystem hints
* current execution focus

### Memory consumes

Potentially:

* those hints for routing
* promotion triggers for durable residue
* boundary checks

### Shared checks

Warn when:

* plans absorb durable technical knowledge
* memory absorbs active task/sequence state

## Phase A — Define interoperability contract

Create a small, explicit contract covering:

### A1. Planning → memory routing hook

An active task or execplan may provide:

* touched paths
* surfaces
* subsystem hints

The memory system may use those to route notes.

Important:

* planning emits hints
* memory decides routing

### A2. Execution → durable-memory promotion

When active work discovers:

* invariants
* recurring traps
* operator sequences
* durable architectural boundaries

those should be promotable into memory.

Important:

* planning does not own the durable fact
* memory does not own active execution state

### A3. Boundary linting

Add cross-system warnings for:

* durable technical facts inside plans
* active sequencing inside memory
* duplicated guidance across planning and memory

## Phase B — Keep startup path efficient

Define the integrated startup flow for a repo that uses both:

1. read the planning activation surface
2. read one execution contract if needed
3. route into memory from touched surfaces/paths
4. read only the smallest useful memory bundle

Avoid:

* bulk-reading planning
* bulk-reading memory
* always reading roadmap + workflow + project-state + task-context by default

## Phase C — Shared UX conventions

Define consistent conventions for:

* referencing memory notes from plans
* referencing active work from memory only when truly needed
* surfacing promotion opportunities
* distinguishing active work from durable residue

These should be:

* links or references
* not duplicated prose

## Phase D — Integration checks

Add optional checks or reports for:

* active item without durable context where one seems needed
* repeated promotion-worthy facts stuck in execplans
* repeated memory notes pointing to the same active planning confusion
* boundary blur between execution contract and durable knowledge

These should stay advisory.

## What not to do

Do not:

* make planning require memory
* make memory require planning
* force every plan item to map to memory
* force every memory update to update planning
* create a shared hidden state layer
* unify both into one giant system

## Main risks to watch

* coupling by convenience
* duplicated state
* startup overhead
* leaking planning semantics into the memory package
* leaking memory taxonomy into the planning package

---

# Recommended execution order across all three tracks

## First

* finish stabilizing the memory package’s routing/hardening/calibration path
* stabilize the planning model in the current repo

## Second

* define the interoperability contract between them
* add boundary warnings and startup discipline

## Third

* extract planning into its own package if it proves stable
* keep integration thin and explicit

---

# One-sentence summary

* **Planning-only development** should make planning independently strong.
* **Memory-only development** should keep memory independently sharp and lightweight.
* **Integration development** should define a thin, explicit interface so the two systems cooperate without becoming one system.
