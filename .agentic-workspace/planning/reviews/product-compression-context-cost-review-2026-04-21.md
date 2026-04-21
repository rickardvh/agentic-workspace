# Product Compression Startup Review

## Goal

- Identify the first bounded work that should land under the active product-compression lane before broader README, doctrine, or query-surface cleanup starts.

## Scope

- Startup-entry surfaces and the current active issue cluster for product compression and gradual discovery.

## Non-Goals

- Planning every follow-on slice up front.
- Reopening the ownership-boundary cleanup that already closed.
- Converting this review into an active implementation plan.

## Review Mode

- Mode: context-cost
- Review question: What bounded startup/discovery work should come first so the product can move toward a tiny safe operating model without flattening ownership or starting a broad docs rewrite?
- Default finding cap: 2 findings
- Inputs inspected first: `AGENTS.md`, `agentic-workspace defaults --section startup --format json`, `README.md`, `tools/AGENT_QUICKSTART.md`, `docs/design-principles.md`, live issues `#223`, `#224`, `#225`, `#226`, `#227`, `#228`, `#230`

## Review Method

- Commands used:
  - `uv run agentic-workspace defaults --section startup --format json`
  - `uv run agentic-workspace summary --format json`
  - `gh issue view 223 --json number,title,body,state,url`
  - `gh issue view 224 --json number,title,body,state,url`
  - `gh issue view 225 --json number,title,body,state,url`
  - `gh issue view 226 --json number,title,body,state,url`
  - `gh issue view 227 --json number,title,body,state,url`
  - `gh issue view 228 --json number,title,body,state,url`
  - `gh issue view 230 --json number,title,body,state,url`
  - `rg -n "^#|^##|AGENTS.md|llms.txt|design-principles|startup|memory|planning" README.md tools/AGENT_QUICKSTART.md docs/design-principles.md AGENTS.md`
- Evidence sources:
  - Root startup contract in `AGENTS.md`
  - Compact startup answer from `agentic-workspace defaults --section startup --format json`
  - Repo front-door and helper surfaces in `README.md` and `tools/AGENT_QUICKSTART.md`
  - Long-form doctrine in `docs/design-principles.md`
  - Live upstream issue framing for the active lane

## Findings

### Finding: The first slice should freeze the tiny startup model before broader compression work

- Summary: The repo already has a compact startup answer in queryable form, but the visible front-door surfaces have not yet been reduced to match it. The first implementation slice should therefore define and freeze the tiny safe startup model plus the discovery/escalation cues around it, rather than beginning with README or doctrine compression.
- Evidence:
  - `agentic-workspace defaults --section startup --format json` already answers startup compactly: read the configured startup file, then `summary`, then the active execplan only when pointed to.
  - That same defaults surface already classifies `llms.txt` as external handoff only and `tools/AGENT_QUICKSTART.md` / `tools/AGENT_ROUTING.md` as generated helpers.
  - `README.md` still carries product framing, startup path, state locations, command inventory, and further reading in one front-door surface.
  - `tools/AGENT_QUICKSTART.md` still advertises a large helper surface even though it is already correctly marked as generated and secondary.
- Risk if unchanged: Work starts as a diffuse “make docs smaller” pass, which can remove text without actually lowering startup cost or clarifying when deeper concepts should become discoverable.
- Suggested action: Make the first active tranche explicitly cover three outputs together: the minimum startup contract, the escalation/discovery cues that justify deeper reads, and the compact top-level capability advertisement that explains what the main modules are for.
- Confidence: high
- Source: mixed
- Promotion target: `.agentic-workspace/planning/state.toml (todo.active_items)`
- Promotion trigger: immediate, because the active execplan already names this lane and needs a more precise first tranche definition.
- Post-remediation note shape: shrink

### Finding: README and doctrine compression should be sequenced as follow-on work, not the anchor slice

- Summary: The issue cluster is dependency-ordered. `#223`, `#227`, and `#228` define the operating model that later cleanup depends on. `#224`, `#225`, and `#226` look like follow-on compression and routing work that should be driven by that operating model instead of being planned first.
- Evidence:
  - Live issues in the active lane separate the operating-model work (`#223`, `#227`, `#228`) from follow-on front-door and doctrine cleanup (`#224`, `#225`, `#226`).
  - `docs/design-principles.md` is still a long mixed doctrine surface spanning product intent, policy, heuristics, validation standards, and queue-entry rules, which matches the motivation behind `#225`.
  - `README.md` still behaves as a hybrid front door rather than the strict minimal entry surface proposed by `#224`.
  - Without a frozen startup/discovery model, compressing those surfaces first would mostly be stylistic editing.
- Risk if unchanged: The lane expands into a multi-surface documentation sweep before the repo has decided what the stable minimal model actually is, increasing churn and the chance of repeated rewrites.
- Suggested action: Keep the active plan ordered as:
  1. minimum startup model
  2. boundary-triggered escalation cues
  3. compact top-level capability advertisement
  4. then tighten README, doctrine, and queryable-answer surfaces against that frozen model
- Confidence: high
- Source: mixed
- Promotion target: `.agentic-workspace/planning/state.toml (todo.active_items)`
- Promotion trigger: immediate for sequencing in the active execplan; roadmap promotion is not needed because the lane is already active.
- Post-remediation note shape: shrink

## Recommendation

- Promote: refine the active execplan so the first tranche is explicitly `#223` + `#227` + `#228`, with README/doctrine/query-surface cleanup marked as follow-on slices driven by that model.
- Defer: `#224`, `#225`, and `#226` as immediate implementation anchors until the startup/discovery contract is frozen.
- Dismiss: any broader “compress everything visible” framing for this lane.

## Validation / Inspection Commands

- `uv run agentic-workspace defaults --section startup --format json`
- `uv run agentic-workspace summary --format json`
- `uv run python scripts/check/check_planning_surfaces.py`

## Drift Log

- 2026-04-21: Review created to bound the first startup/discovery tranche under the active product-compression lane.
