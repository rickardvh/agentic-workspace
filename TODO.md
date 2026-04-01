# TODO

## Goal

Evolve `agentic-memory-bootstrap` from a durable-memory package into a durable-memory plus improvement-pressure package.

The package should stay unobtrusive inside third-party repos:

- no direct edits to repo code, tests, docs, or tooling outside package-managed surfaces
- no planner-specific coupling
- no required new manifest schema
- no hard enforcement of repo redesign choices

The package should instead help agents:

- notice when memory is compensating for weak code, weak docs, weak tooling, or poor structure
- suggest upstream repo improvements to the user
- choose better design responses themselves instead of writing more memory by default

## Phase 1: Shared Principle

### Issue: Make improvement pressure a first-class design principle

Problem:
The package currently treats memory mainly as durable context. It should also treat some memory as a signal that the repo itself may need improvement.

Acceptance criteria:
- shared docs say memory succeeds when it either preserves irreducible durable truth or creates pressure to shrink, move, or remove the note
- docs state that memory should not become a permanent substitute for clear code, stable docs, safe tooling, or good repo structure
- principle appears near the top of the shared package docs

### Issue: Distinguish durable truth from improvement signals

Problem:
Agents need a clear split between notes that should stay and notes that should create pressure toward repo improvement.

Acceptance criteria:
- docs distinguish `durable truth` from `improvement signal`
- docs give examples of each
- docs say to preserve the first kind and try to eliminate the second kind at the source

## Phase 2: Note Maintenance and Promotion Paths

### Issue: Add an explicit “what would eliminate this note?” rule

Problem:
The maintenance model currently asks whether a note should exist, but not what repo change would make it unnecessary.

Acceptance criteria:
- note-maintenance guidance asks what would shrink, move, automate, promote, or remove the note
- docs encourage promotion to docs, move to skills, scripting, testing, validation, or refactoring where appropriate
- guidance remains compact and repo-agnostic

### Issue: Document canonical remediation paths

Problem:
Agents need a default mapping from memory symptom to likely upstream repo improvement.

Acceptance criteria:
- docs map recurring mistakes to tests/validation/lint
- docs map prose-heavy procedures to skills first, then scripts/tooling if still mechanical
- docs map stable human-facing guidance to canonical docs
- docs map high-discovery-cost explanatory notes to refactor review or clearer boundaries

### Issue: Strengthen the “skills are a bridge, not the endpoint” model

Problem:
Workflow prose often stops at “make a skill”, when the real target may be a repo-owned script or clearer implementation.

Acceptance criteria:
- docs describe the path: prose note -> skill -> script/tooling if stable and mechanical
- docs say memory should shrink after the workflow is encoded elsewhere
- no implication that the package itself should install or edit repo scripts automatically

## Phase 3: Optional Metadata

### Issue: Add optional manifest fields for improvement pressure

Problem:
The manifest can already express routing and freshness, but not why a note exists or what it may want to become.

Acceptance criteria:
- manifest docs support optional fields such as:
  - `memory_role`
  - `symptom_of`
  - `preferred_remediation`
  - `improvement_candidate`
  - `improvement_note`
  - `elimination_target`
- existing manifests remain valid without these fields
- docs frame them as advisory only

### Issue: Add note-class and audience guidance without forcing schema adoption

Problem:
The package should help agents reason about ownership and audience without requiring repos to adopt a rigid taxonomy.

Acceptance criteria:
- docs show how optional metadata can distinguish durable truth, operator guidance, and improvement signals
- docs make clear that repos may omit the fields entirely
- examples remain lightweight

## Phase 4: Soft Tooling

### Issue: Teach `doctor` to emit improvement suggestions

Problem:
`doctor` currently reports state and memory hygiene issues, but it should also suggest upstream repo improvements when memory looks symptomatic.

Acceptance criteria:
- `doctor` can emit soft “consider” suggestions
- suggestions may point to docs promotion, skills, scripting, testing, validation, or refactor review
- output remains advisory and non-blocking

### Issue: Teach `sync-memory` to surface upstream-fix candidates

Problem:
When work changes related memory, the command should also suggest whether the note indicates a repo improvement opportunity.

Acceptance criteria:
- `sync-memory` can append compact improvement suggestions to review/update items
- suggestions remain tied to the touched note or manifest metadata
- command still focuses on memory maintenance first

### Issue: Broaden `promotion-report` into promotion-or-elimination guidance

Problem:
Some notes should be promoted into canonical docs, but others should become skills, tests, scripts, or refactor candidates.

Acceptance criteria:
- `promotion-report` can report notes as promotion or elimination candidates
- docs and output still preserve the existing command name for compatibility
- command can use manifest hints when present and heuristics otherwise

## Phase 5: Heuristics

### Issue: Add lightweight memory-debt heuristics

Problem:
Some notes are signals of repo friction even without explicit manifest metadata.

Acceptance criteria:
- heuristics stay simple and soft
- examples include:
  - recurring-failure notes suggesting tests/validation
  - prose-heavy runbooks suggesting skills/scripts
  - very large domain/orientation notes suggesting refactor review or docs promotion
  - repeated current-note growth suggesting planning bleed or unresolved structure problems
- no hard scoring system is introduced

## Phase 6: Examples and Skills

### Issue: Add examples that show memory shrinking or moving

Problem:
The docs need concrete examples of memory leading to repo improvements rather than only note maintenance.

Acceptance criteria:
- examples cover docs promotion, skill extraction, script/tooling suggestion, regression-test suggestion, and refactor suggestion
- examples remain concise
- examples are package-scoped and planner-agnostic

### Issue: Nudge shipped skills toward improvement thinking

Problem:
Skills such as memory hygiene should push agents to notice when memory is compensating for repo friction.

Acceptance criteria:
- shipped memory skills reinforce shrink/promote/automate/refactor review paths where relevant
- skills do not become repo-specific or prescriptive outside package-owned surfaces

## Phase 7: Guardrails and Verification

### Issue: Add regression coverage

Problem:
The new direction should be kept stable without overfitting tests to prose.

Acceptance criteria:
- tests cover the new shared principle
- tests cover optional manifest compatibility
- tests cover soft improvement suggestions in doctor/sync/promotion-report
- tests continue to accept old manifests that omit the new fields

### Issue: Verify against this repo

Problem:
Changes to docs, payload, and tooling need self-hosted verification.

Acceptance criteria:
- run `uv run pytest`
- run `uv run python -m repo_memory_bootstrap.cli verify-payload`
- run `uv run python -m repo_memory_bootstrap.cli doctor --target .`
- run `uv run python -m repo_memory_bootstrap.cli upgrade --dry-run --target .`
