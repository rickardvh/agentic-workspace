# TODO

## Goal

Tighten the bootstrap package from a "minimise discovery, ambiguity, and validation cost" perspective without expanding the default memory surface.

Improve by pruning, compressing, sharpening routing, and increasing freshness pressure rather than by adding more memory.

## Epic: Keep Current-State Notes Current

### Issue: Tighten current-state guidance so overview notes do not turn into ledgers

Problem:
Repositories can let `memory/current/project-state.md` drift into a long historical ledger, which raises token cost and weakens it as a fast orientation note.

Scope:
- shared workflow guidance
- starter `project-state.md`
- related README guidance

Files:
- `memory/system/WORKFLOW.md`
- `bootstrap/memory/system/WORKFLOW.md`
- `bootstrap/memory/current/project-state.md`
- `README.md`
- `bootstrap/README.md`

Acceptance criteria:
- shared docs explicitly describe aggressive compression of current-state notes
- starter `project-state.md` keeps only current focus, recent meaningful progress, blockers, and a few high-value notes
- docs discourage tranche history and ledger-style chronology in current-state files
- docs make it clear that older closed slices should move to specific notes only when they are still hard to recover elsewhere

### Issue: Tighten active-decisions guidance so it stays limited to live decisions

Problem:
`memory/current/active-decisions.md` is useful only when it stays restricted to true live architectural or cross-cutting decisions.

Scope:
- current-memory guidance
- decisions README

Files:
- `memory/system/WORKFLOW.md`
- `memory/decisions/README.md`
- `bootstrap/memory/decisions/README.md`

Acceptance criteria:
- docs say `active-decisions` should hold only live decisions that still affect implementation choices
- docs discourage operational residue and completed transition history in current decision notes
- docs make clear when mature rationale should move into longer-lived decision notes

## Epic: Sharpen Routing

### Issue: Make the routing layer even more packet-oriented

Problem:
The bootstrap routing model works best when it points to the smallest useful note set for recurring change classes.

Scope:
- memory index guidance
- README examples

Files:
- `memory/index.md`
- `bootstrap/memory/index.md`
- `README.md`
- `bootstrap/README.md`

Acceptance criteria:
- routing guidance emphasises smallest-note bundles over broad lane descriptions
- examples show compact packets for recurring work classes
- `memory/index.md` stays short and task-routed rather than summary-heavy

### Issue: Add a lightweight common-task-bundles pattern

Problem:
Agents should be able to open one compact packet of notes for recurring work types instead of inferring the bundle each time.

Scope:
- routing guidance only
- no new mandatory memory file

Files:
- `memory/index.md`
- `bootstrap/memory/index.md`
- optionally `memory/manifest.toml` guidance if a machine-readable pattern is justified later

Acceptance criteria:
- docs define a small common-task-bundles pattern
- bundles are routing-only and do not duplicate note content
- no new mandatory surface is introduced

## Epic: Reduce Prose-Heavy Procedures

### Issue: Push repeated procedures out of runbooks and into skills more aggressively

Problem:
The package says durable facts belong in memory and repeated procedures belong in skills, but that split should be applied more aggressively.

Scope:
- runbook guidance
- skill guidance
- templates

Files:
- `memory/system/WORKFLOW.md`
- `memory/system/SKILLS.md`
- `memory/runbooks/README.md`
- `bootstrap/memory/runbooks/README.md`
- `bootstrap/memory/templates/runbook-template.md`
- `bootstrap/memory/templates/memory-note-template.md`

Acceptance criteria:
- docs explain when a prose-heavy repeated procedure should move to a skill
- runbooks are described as durable operator facts, symptoms, entry conditions, and verification
- templates reinforce the split between durable fact and repeated procedure

## Epic: Increase Freshness Pressure

### Issue: Strengthen manifest-based freshness pressure for oversized or stale notes

Problem:
Oversized or stale notes should be easier to spot before they become expensive.

Scope:
- manifest guidance
- verification and freshness checks

Files:
- `memory/index.md`
- `memory/system/WORKFLOW.md`
- `src/repo_memory_bootstrap/installer.py`
- related tests

Acceptance criteria:
- package guidance explains stronger freshness pressure for oversized or stale notes
- verification can flag current-state notes that exceed intended size or obvious freshness expectations
- rules avoid noisy churn on nearly every edit

### Issue: Add note-size and stale-surface checks where they pay off

Problem:
The package should surface expensive drift earlier without turning verification into noise.

Scope:
- installer or verification behaviour
- tests

Files:
- `src/repo_memory_bootstrap/installer.py`
- `tests/test_installer.py`

Acceptance criteria:
- oversized current-state notes can be surfaced clearly in package verification or checks
- stale routing surfaces are easier to detect
- checks encourage pruning and compression rather than more memory

## Epic: Validate The Shape

### Issue: Add regression coverage for compact routing and current-state guidance

Problem:
The package contract is easy to erode unless tests defend the high-value boundaries.

Files:
- `tests/test_installer.py`

Acceptance criteria:
- tests cover compact current-state guidance
- tests cover routing-layer guidance and bundle-oriented examples
- tests cover the durable-fact versus repeated-procedure split where practical

## Constraints

- do not add package guidance that depends on a specific external task-planning surface
- do not add new mandatory memory files unless clearly justified
- keep the base bootstrap understandable without skills
- preserve a small default working set
