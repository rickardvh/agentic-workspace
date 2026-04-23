# Product Feature Self-Hosting Review

## Goal

- Review how well this repo is actually using Agentic Workspace's shipped and important internal capabilities itself.
- Distinguish features that are strongly dogfooded from features that are still more doctrinal than routine in ordinary work.

## Scope

- `README.md`
- `docs/agent-os-capabilities.md`
- `docs/maturity-model.md`
- `docs/ecosystem-roadmap.md`
- `.agentic-workspace/WORKFLOW.md`
- `.agentic-workspace/planning/reviews/`
- `.agentic-workspace/planning/execplans/archive/`
- `.agentic-workspace/memory/repo/runbooks/dogfooding-usage-ledger.md`
- `.agentic-workspace/memory/repo/runbooks/dogfooding-feedback-routing.md`
- `.agentic-workspace/delegation-outcomes.json`
- live `agentic-workspace summary --format json`
- live `agentic-workspace config --target . --format json`

## Non-Goals

- Re-open planning automatically from this review.
- Re-rate package maturity labels.
- Re-audit every individual command or doc surface in depth.

## Review Mode

- Mode: `doctrine-refresh`
- Review question: Which product capabilities are genuinely exercised in ordinary self-hosting here, and which ones still have thinner real-use evidence than their doctrinal weight suggests?
- Default finding cap: 2 findings
- Inputs inspected first: `docs/agent-os-capabilities.md`, `README.md`, `agentic-workspace summary --format json`, `agentic-workspace config --target . --format json`

## Review Method

- Commands used:
  - `uv run agentic-workspace summary --format json`
  - `uv run agentic-workspace config --target . --format json`
  - `rg -n "feature|capability|product|dogfood|dogfooding|review" README.md docs .agentic-workspace packages -g "*.md"`
  - `rg -n "module registry|capability registry|modules output|result_contract|workflow_obligations|optimization_bias|summary --format json|config --target \\. --format json|planning-review|upstream-task-intake|OWNERSHIP|render_agent_docs|check_planning_surfaces|delegation-outcomes|handoff" docs .agentic-workspace packages README.md -g "*.md"`
- Evidence sources:
  - canonical docs
  - live workspace query surfaces
  - review portfolio
  - archived execplans
  - local dogfooding evidence artifacts

## Feature Usage Matrix

| Capability | Current self-use read | Evidence |
| --- | --- | --- |
| Agentic Memory | strong | Repo-local memory runbooks, recurring-friction tracking, and memory-owned dogfooding routing are live checked-in surfaces under `.agentic-workspace/memory/repo/`. |
| Agentic Planning | strong | `README.md` and `AGENTS.md` route startup through `agentic-workspace summary --format json`; the repo currently carries 158 archived execplans and planning remains the canonical active-state owner. |
| Workspace composition layer | strong | The repo uses the workspace CLI as the front door for startup, config, summary, report, defaults, and lifecycle composition rather than treating memory and planning as disconnected tools. |
| Checks / proof surfaces | strong | Commit hooks rerun repo, planning, and memory suites; `summary` currently reports clean planning-surface health; review and execplan residue repeatedly cite `check_planning_surfaces.py` and package tests as the proof lane. |
| Ownership / authority mapping | strong | `.agentic-workspace/WORKFLOW.md`, `.agentic-workspace/OWNERSHIP.toml`, repo-owned `AGENTS.md`, and contributor docs are all actively used to separate repo-owned from product-managed surfaces. |
| Bounded delegated judgment | moderate | The contract is deeply encoded in planning and docs, but the live dogfood evidence for actual delegated execution remains narrower than the surface area of the doctrine. |
| Capability / module registry | light | The registry and capability contract are documented and queryable, but the repo's own ordinary work still rarely seems to depend on module-registry lookup as a first-line operating move. |
| Collaboration / concurrency safety | moderate | Feature-scoped execplans/reviews and explicit boundary rules are routine, but the evidence is mostly indirect discipline rather than repeated live multi-agent/concurrent proof. |
| Intake / triage | strong | `.agentic-workspace/planning/upstream-task-intake.md`, external-intent evidence, candidate lanes, and review-to-roadmap separation are all active repo behavior. |
| Review / audit lane | strong | The repo currently has 31 checked-in review artifacts, and review mode selection is a normal part of bounded analysis work. |
| Generated-surface trust | moderate | Generated helper docs, manifest-backed rendering, and trust checks exist and have prior review coverage, but they remain support surfaces rather than clearly high-pull daily operating surfaces. |
| Environment / recovery guidance | strong | The default path in `README.md` and contributor docs is query-first recovery through `summary`, `defaults`, and `config`, not broad rereading of raw prose. |
| Handoff / execution summaries | moderate | Structured handoff and execution-summary contracts exist and are used in archived execplans, but finished-work inspection still reports four likely premature closeouts, so closeout trust is not yet as boring as the contract aspires to be. |

## Findings

### Finding: Registry-shaped features are still more described than exercised

- Summary: The capability and module registry contract looks architecturally real, but the repo's own day-to-day operating path still depends far more on summary/config/planning surfaces than on explicit registry-driven discovery.
- Evidence: `docs/module-capability-contract.md` and `docs/architecture.md` make the registry sound central; `README.md` and `docs/contributor-playbook.md` route ordinary work through `summary`, `config`, and planning surfaces instead; the strongest live proof I found for registry use is doctrinal and review-oriented rather than repeated ordinary-use evidence.
- Risk if unchanged: the repo may overestimate how self-proving the registry is and keep broadening a capability that still has relatively light first-line product pull.
- Suggested action: keep the registry internal and treat it as support infrastructure until repeated ordinary work or extension-boundary pressure clearly depends on it.
- Confidence: medium-high
- Source: mixed
- Promotion target: none
- Promotion trigger: promote only if another doctrine-refresh or extension-boundary review again finds that registry semantics are important but still thinly exercised.
- Post-remediation note shape: retain

### Finding: Delegation and handoff are credible, but still not routine enough to count as fully self-proven

- Summary: The repo has real delegated-execution and handoff contracts, but the actual self-hosting evidence is still thinner than the amount of doctrine and surface area dedicated to them.
- Evidence: `.agentic-workspace/delegation-outcomes.json` contains only one local recorded outcome; the strongest direct evidence lives in bounded review artifacts such as `local-delegation-outcome-evidence-dogfood-2026-04-17.md`, `local-delegation-target-profiles-dogfood-2026-04-17.md`, and `orchestrator-workflow-evidence-2026-04-17.md`; `finished_work_inspection_contract` from the live summary still shows four `likely_premature_closeout` signals, which means execution-summary and closure trust are improved but not yet fully routine.
- Risk if unchanged: the repo may treat delegated handoff quality as more operationally settled than the current evidence really supports, especially for closure and cross-agent continuation.
- Suggested action: keep delegation and handoff in the actively dogfooded set, but judge them by repeated ordinary-use evidence and clean closeout behavior rather than by contract richness alone.
- Confidence: high
- Source: friction-confirmed
- Promotion target: none
- Promotion trigger: promote only if repeated ordinary work keeps surfacing the same thin-evidence pattern after the current `machine-first-planning-chain` and `graceful-partial-compliance` follow-through.
- Post-remediation note shape: retain

## Recommendation

- Promote: none now; the review does not justify a new queue item beyond already-open follow-through.
- Defer: revisit this review after another mixed-agent and closeout-heavy tranche, especially if registry or delegation evidence remains thin.
- Dismiss: any conclusion that the product is only doctrinal. The core loop is already strongly self-hosted; the weaker evidence is concentrated in a smaller set of supporting capabilities.

## Validation / Inspection Commands

- `uv run agentic-workspace summary --format json`
- `uv run agentic-workspace config --target . --format json`
- `rg -n "feature|capability|product|dogfood|dogfooding|review" README.md docs .agentic-workspace packages -g "*.md"`
- `rg -n "module registry|capability registry|modules output|result_contract|workflow_obligations|optimization_bias|summary --format json|config --target \\. --format json|planning-review|upstream-task-intake|OWNERSHIP|render_agent_docs|check_planning_surfaces|delegation-outcomes|handoff" docs .agentic-workspace packages README.md -g "*.md"`

## Drift Log

- 2026-04-23: Review created to assess how fully the repo self-hosts the product's own feature set without activating new work automatically.
