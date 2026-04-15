# Roadmap: Declarative Contract Layer And Multi-Runtime Tooling

## Goal

Make Agentic Workspace safer and faster to develop by using stronger schema, validation, and generation tooling during development, while keeping shipped operational requirements narrow and intentional.

## Guiding rule

- Use rich tooling in development.
- Keep runtime/adopter requirements minimal.
- Treat checked-in contracts as the durable source of truth.
- Treat CLIs as implementations and accelerators, not the only place behavior lives.

## Success criteria

- More product behavior is declared in checked-in schemas/manifests instead of hidden in Python branching.
- Python remains the reference implementation, but key surfaces are no longer Python-defined in spirit.
- A second runtime can implement at least a narrow subset of the contract with parity.
- Development becomes faster and safer through schema validation, generation, and parity tooling.
- Target repos remain operable without requiring the full development toolchain.

---

## Stage 1: Inventory and boundary setting

### Objective

Identify what should become declarative and what should remain procedural.

### Deliverables

- A checked-in architecture note defining:
  - declarative contract
  - procedural runtime logic
  - derived projections/views
- An inventory of current Python-owned behavior grouped into:
  - proof/validation metadata
  - reporting metadata
  - selector/routing metadata
  - lifecycle metadata
  - procedural reconciliation logic
- A short non-goals list:
  - no mini language
  - no generic query language
  - no declarative merge engine in the first slice
  - no runtime requirement for the development toolchain

### Exit criteria

- Every major behavior can be classified as declarative, procedural, or derived.
- The team agrees on the boundary.

---

## Stage 2: Schema foundation

### Objective

Create stable schemas for the most obviously declarative surfaces.

### Deliverables

- Versioned schemas for:
  - compact answer envelopes
  - report envelopes
  - proof route definitions
  - selector definitions
  - reporting surface definitions
  - module metadata
  - managed-surface inventory
  - startup/handoff metadata
- A schema index doc that explains:
  - which schemas exist
  - what owns them
  - what consumes them
  - what remains procedural

### Recommended tooling

- JSON Schema as the base validation layer
- Optional stronger authoring/constraint tooling later if needed

### Exit criteria

- Schemas validate current checked-in examples.
- Python can begin consuming schema-backed data without changing product behavior.

---

## Stage 3: Extract proof and reporting metadata from Python

### Objective

Move stable metadata out of Python code and into checked-in manifests.

### Deliverables

- Manifest-backed proof route definitions
- Manifest-backed reporting surface definitions
- Manifest-backed selector definitions for:
  - defaults
  - proof
  - ownership
  - report
- Manifest-backed module metadata where still implicit in code

### Keep procedural in Python

- install/adopt reconciliation
- repo-state classification
- ambiguity detection
- content-aware merge/preservation logic
- proof execution
- drift/content checks

### Exit criteria

- Python reads proof/report/selector metadata from checked-in manifests.
- Behavior remains unchanged from the user’s perspective.
- Docs can point to checked-in metadata for these surfaces.

---

## Stage 4: Refactor Python into a clearer reference implementation

### Objective

Make Python obviously an implementation of checked-in contracts, not the only place they live.

### Deliverables

- Python command routing driven by manifest-backed metadata where feasible
- Python output envelopes validated against shared schemas
- Explicit separation in code between:
  - contract loading
  - projection/rendering
  - procedural execution
- Contract-parity tests between manifests and emitted CLI outputs

### Exit criteria

- A reviewer can tell whether a behavior comes from manifest contract or procedural code.
- Broad read/report/query behavior is no longer hidden in ad hoc Python branching.

---

## Stage 5: Add development-time generation and validation tooling

### Objective

Use tools aggressively in development to improve safety and speed.

### Deliverables

- Schema validation in CI
- Manifest linting in CI
- Generated docs/tables/help text from manifests where useful
- Output-shape tests against checked-in fixtures
- Drift tests between schema, manifests, and rendered docs
- Optional codegen for:
  - help text
  - command metadata
  - route tables
  - projection templates

### Important constraint

- These tools are for development and CI.
- They must not silently become required in adopting repos.

### Exit criteria

- Contract edits fail fast when schemas/manifests drift.
- Repetitive boilerplate in Python and docs is reduced.

---

## Stage 6: Narrow second implementation prototype

### Objective

Prove that the contract is portable across runtimes.

### Scope

Start with a very small second implementation, likely Node, for:

- `defaults`
- `proof`
- `ownership`
- `report`

Do **not** start with:

- install
- adopt
- upgrade
- uninstall

### Deliverables

- A minimal Node prototype for the selected query/report surfaces
- Cross-runtime parity tests
- A discrepancy log showing which parts of the contract are still too procedural or underspecified

### Exit criteria

- Python and Node produce equivalent structured outputs for the selected surfaces.
- The second implementation feels straightforward, not heroic.

---

## Stage 7: Runtime-critical contract audit

### Objective

Ensure safe normal operation does not depend on one CLI/runtime.

### Deliverables

- An audit of all runtime-critical questions:
  - startup path
  - active state
  - next action
  - ownership
  - proof route
  - escalation boundary
  - handoff/jumpstart state
- For each question:
  - checked-in source of truth
  - CLI projection path
  - whether operation is safe without CLI
- A remediation list for any answer that exists only conveniently through CLI output

### Exit criteria

- Safe normal operation is possible from checked-in state alone.
- CLI remains optional but valuable.

---

## Stage 8: Lifecycle protocol extraction (bounded)

### Objective

Extract only the declarative parts of lifecycle management that are stable enough to share.

### Candidate extractions

- lifecycle mode metadata
- managed file inventories
- policy classes such as:
  - preserve
  - replace
  - require handoff
- postconditions
- verification requirements
- handoff artifact schemas

### Keep procedural unless proven otherwise

- ambiguous adopt behavior
- content-aware reconciliation
- repo-state classification heuristics
- conservative overwrite/merge logic

### Exit criteria

- A meaningful lifecycle subset is shared declaratively.
- Or the team explicitly concludes that lifecycle remains mostly reference-implementation territory.

---

## Stage 9: Benchmarking and parity discipline

### Objective

Ensure the declarative core actually improves safety, portability, and development speed.

### Deliverables

- Cross-runtime parity benchmarks for schema-backed surfaces
- Regression tests for:
  - output parity
  - lazy-discovery/read-cost behavior
  - selector correctness
  - proof-route correctness
  - ownership correctness
- Benchmarks that distinguish:
  - checked-in contract success
  - Python reference implementation success
  - alternate runtime success

### Exit criteria

- Shared-contract surfaces stay behaviorally aligned across implementations.
- Contract extraction is justified by measurable gains in safety and maintainability.

---

## Stage 10: Decide the long-term runtime strategy

### Objective

Choose the long-term product posture based on evidence, not instinct.

### Questions to answer

- Is Python still the best primary implementation language?
- Is a Node implementation worth maintaining beyond narrow query/report surfaces?
- Which surfaces are now truly multi-runtime?
- Which surfaces should remain reference-implementation-specific?
- Does the product need generated CLIs, or only shared schemas plus handwritten thin front ends?

### Exit criteria

- A clear long-term decision:
  - Python-first with shared contract layer
  - Python + Node for selected surfaces
  - broader multi-runtime strategy
  - or explicit containment of multi-runtime ambition to narrow surfaces only

---

## Recommended sequencing

### First tranche

1. Inventory and boundary setting
2. Schema foundation
3. Extract proof/report/selector metadata
4. Refactor Python to consume it

### Second tranche

5. Add development tooling in CI
2. Build narrow Node prototype
3. Run parity tests

### Third tranche

8. Audit runtime-critical non-CLI safety
2. Extract bounded lifecycle protocol pieces
3. Decide long-term runtime posture

---

## Immediate next actions

- Write the declarative-vs-procedural boundary note
- Create versioned schemas for proof routes, selectors, and report envelopes
- Extract current proof/report/selector metadata from Python into manifests
- Add schema validation and manifest linting to CI
- Refactor Python query/report surfaces to consume those manifests
- Prototype Node support for one narrow surface, ideally `proof` or `ownership`

---

## Guardrails

- Do not build a mini programming language.
- Do not overfit schemas to code generation.
- Do not make development convenience tools mandatory for adopters.
- Do not let runtime-critical semantics exist only in Python.
- Do not attempt multi-runtime lifecycle parity too early.
- Do not keep both manifests and code equally authoritative for the same behavior.

## North star

The product contract should live in checked-in, inspectable, versioned data.

Python should be the current best implementation of that contract, not the only place the contract truly exists.
