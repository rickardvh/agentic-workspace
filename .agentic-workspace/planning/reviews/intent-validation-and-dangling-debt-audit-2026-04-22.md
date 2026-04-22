# Intent Validation And Dangling Debt Audit

## Goal

- Identify why unfinished larger intent can still disappear from active inspection and closure flow, even though execplans now carry `Intent Continuity`, `Required Continuation`, `Intent Satisfaction`, and `Closure Check`.

## Scope

- Audit the current planning, archive, and reporting path against the failure mode:
  - a bounded slice closes cleanly
  - the larger issue or lane is still unfinished
  - the unresolved follow-on is not easy to inspect later
- Use live GitHub issue state plus checked-in planning state.

## Findings

### 1. Live issue reality is not reconciled with the checked-in roadmap or summary

The planning summary is still derived only from checked-in planning state, not from the live issue graph.

Current evidence:

- `agentic-workspace summary --format json` reports no active work and only one roadmap lane: `#230`.
- Live GitHub still has open issue `#251` plus child slices `#253`, `#254`, `#255`, and `#256`.
- Those issues are absent from `.agentic-workspace/planning/state.toml`, so the compact inspection path currently hides them entirely.

Why this matters:

- a lane can remain genuinely unfinished in GitHub while the repo's compact planning surfaces present the system as nearly done
- humans cannot cheaply tell whether the quiet state means "nothing remains" or "unfinished intent fell out of the checked-in queue"

Root cause:

- `planning_summary()` reads roadmap lanes only from `.agentic-workspace/planning/state.toml` or legacy roadmap files and never reconciles them with live issue state
- the summary/report path therefore has no way to detect omitted open parent/child issue clusters

Key refs:

- `packages/planning/src/repo_planning_bootstrap/installer.py:527-536`
- `packages/planning/src/repo_planning_bootstrap/installer.py:703-707`
- `.agentic-workspace/planning/state.toml`

### 2. Archive and close trust self-reported closure fields but do not verify unresolved external continuation

The archive gate is internally consistent, but it still trusts the plan's own declared closure state.

Current evidence:

- archive validation requires complete `Intent Satisfaction` and `Closure Check`
- `archive-and-close` is blocked only when those fields contradict each other locally
- there is no check that the corresponding live issue still has open children, open sibling slices, or an unresolved parent lane that should keep the lane visible

Why this matters:

- a plan can honestly say "archive-and-close" according to its own fields while the broader lane is still externally open and not represented elsewhere
- this enables the exact failure mode you called out: chat or local judgment silently decides that a bounded tranche was "enough"

Root cause:

- archive validation checks field completeness and internal consistency, not whether the larger intent remains live in the issue graph or in another surfaced continuation owner

Key refs:

- `packages/planning/src/repo_planning_bootstrap/installer.py:2370-2459`

### 3. Report and summary do not expose a first-class dangling-intent or low-trust closure surface

The combined report can answer many operational questions, but it still has no explicit surface for:

- likely dangling larger intent
- open issue clusters missing from planning state
- closed issues whose larger parent lane still appears open
- lower-trust closure when expected planning residue is missing

Current evidence:

- when there is no active plan, `planning_report()` falls back to "No active planning work right now" or "Promote the highest-priority roadmap candidate"
- there is no dedicated object for dangling intent, unresolved closeout debt, or likely bypassed planning/closure discipline
- the reporting contract mentions warnings and findings generally, but not a compact inspectable debt inventory for intent/closure trust

Why this matters:

- humans currently have no cheap answer to "what claims of completion should I distrust?" or "what larger work probably fell out of the lane map?"
- this makes inspection and intent validation harder exactly when active planning is quiet

Key refs:

- `packages/planning/src/repo_planning_bootstrap/installer.py:729-747`
- `.agentic-workspace/docs/reporting-contract.md`

### 4. The planning checker validates shape drift, not issue-to-intent completeness drift

The checker has become good at enforcing plan structure, archive hygiene, and closure-field completeness.
It still does not warn when:

- open issues exist that are not represented in checked-in candidate lanes
- a closed issue cluster appears replaced by a new open successor cluster that never entered roadmap state
- a plan archived with `archive-and-close` but the related larger lane is still externally active

Why this matters:

- the repo can pass all planning-surface checks while still carrying substantial invisible continuation debt

Key refs:

- `scripts/check/check_planning_surfaces.py:1698-1778`
- `scripts/check/check_planning_surfaces.py:1663-1695`

## Concrete Example

The current repo state demonstrates the failure clearly:

- open: `#251`, `#253`, `#254`, `#255`, `#256`
- roadmap visible in summary/state: only `#230`
- closed recently: `#252`, which is closely related in title and intent to still-open `#254`

That means the system can currently represent itself as quiet and nearly exhausted while a meaningful open lane is still live and not surfaced.

## Required Correction

The next corrective tranche should add all of the following:

1. A live issue reconciliation surface

- compare checked-in active/roadmap issues against live GitHub issue state
- surface open-but-untracked issue clusters
- surface closed issues whose parent lane still appears open
- treat this as inspection data, not a second source of truth

2. A dangling-intent / closeout-debt surface in summary and report

- one compact machine-readable object for unresolved larger intent, likely missing continuation ownership, and suspicious closeouts
- available even when there is no active execplan

3. Archive/close gating that can fail on unresolved external continuation

- `archive-and-close` should require either:
  - reconciled evidence that the larger issue/lane is actually closed, or
  - an explicit reviewed override that remains visible in the archive/report output

4. Lower-trust signals for likely package/planning bypass

- if closure happened without the expected planning residue, report should say so
- this aligns directly with open issue `#256`

## Suggested First Tranche

- create one review/inspection lane for:
  - issue reconciliation
  - dangling-intent detection
  - lower-trust closeout signals
- use `#251` and children `#253`-`#256` as the first proof case for the new detection path
- do not close or promote further lanes until this inspection path exists

## Minimal Proof For The Correction

- `agentic-workspace summary --format json` or `report --format json` can answer:
  - which open issue clusters are not represented in checked-in planning
  - which archived closures are lower-trust because required continuation is unclear
  - what dangling larger intent still exists even with no active plan
- the current `#251` cluster appears in that answer
- closing a lane with unresolved live follow-on produces a visible warning or blocks clean closeout
