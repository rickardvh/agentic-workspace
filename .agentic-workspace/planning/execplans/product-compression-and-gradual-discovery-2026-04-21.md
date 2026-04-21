# Product Compression And Gradual Discovery

## Goal

- Promote the next roadmap lane by making the visible product shape smaller and more progressively discoverable without losing real leverage.

## Non-Goals

- Reopening the ownership-boundary lane that just closed under `#231` and `#240`.
- Broad file relocation unrelated to startup/discovery/compression pressure.
- Inventing a new public extension or module system while reducing startup surface cost.

## Intent Continuity

- Larger intended outcome: Make the visible product shape smaller and more progressively discoverable while preserving real leverage.
- This slice completes the larger intended outcome: no
- Continuation surface: `.agentic-workspace/planning/execplans/product-compression-and-gradual-discovery-2026-04-21.md`
- Parent lane: `product-compression-and-gradual-discovery`

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: `.agentic-workspace/planning/execplans/product-compression-and-gradual-discovery-2026-04-21.md`
- Activation trigger: complete the first bounded startup/discovery tranche and reassess the next compression slice from the same lane.

## Iterative Follow-Through

- What this slice enabled: the repo now has one explicit tiny safe startup model, explicit boundary-triggered escalation cues, and one compact top-level capability-advertisement pattern shipped through defaults, routing, generated helpers, and startup reporting.
- Intentionally deferred: README tightening, doctrine compression, and broader query-surface cleanup now that the startup/discovery contract is frozen.
- Discovered implications: the inactive roadmap queue should now begin with system-intent-and-planning-trust once this lane is active.
- Proof achieved now: the first bounded tranche from `#223`, `#227`, and `#228` is now encoded in canonical docs, compact query surfaces, generated helper surfaces, and planning-surface checks.
- Validation still needed: none for the first tranche beyond the targeted proof already captured; broaden only when starting the next compression slice.
- Next likely slice: use the frozen startup/discovery contract to tighten README, doctrine, and query-surface visibility without re-expanding the startup model.

## Delegated Judgment

- Requested outcome: Promote the next roadmap lane and start the product-compression-and-gradual-discovery thread cleanly.
- Hard constraints: keep the lane bounded to startup/discovery/compression pressure; do not reopen closed ownership cleanup unless new evidence demands it.
- Agent may decide locally: exact tranche title, bounded first-slice wording, and compact continuation framing.
- Escalate when: the lane boundary becomes ambiguous, the requested outcome would widen into a different lane, or the first slice cannot be bounded without live issue re-triage.

## Active Milestone

- ID: product-compression-and-gradual-discovery-2026-04-21
- Status: in-progress
- Scope: implement and prove the first bounded tranche around the tiny safe startup model, gradual discovery cues, and compact capability advertisement.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Narrow the next slice against the now-frozen startup/discovery contract: tighten README, doctrine, and broader query surfaces without widening the startup model again.

## Blockers

- None.

## Touched Paths

- `.agentic-workspace/planning/state.toml`
- `.agentic-workspace/planning/execplans/product-compression-and-gradual-discovery-2026-04-21.md`
- `.agentic-workspace/planning/reviews/product-compression-context-cost-review-2026-04-21.md`
- `src/agentic_workspace/cli.py`
- `packages/planning/bootstrap/.agentic-workspace/docs/minimum-operating-model.md`
- `packages/planning/bootstrap/.agentic-workspace/docs/routing-contract.md`
- `packages/planning/bootstrap/.agentic-workspace/planning/agent-manifest.json`
- `packages/planning/bootstrap/.agentic-workspace/planning/scripts/render_agent_docs.py`
- `packages/planning/bootstrap/.agentic-workspace/planning/scripts/check/check_planning_surfaces.py`
- `packages/planning/src/repo_planning_bootstrap/_render.py`
- `packages/planning/src/repo_planning_bootstrap/installer.py`
- `tools/AGENT_QUICKSTART.md`
- `tools/AGENT_ROUTING.md`

## Invariants

- Active lane state must remain recoverable from `todo.active_items` plus one execplan.
- Completed roadmap lanes should leave the inactive queue instead of lingering as stale candidates.
- Promotion should not silently widen the requested outcome beyond the product-compression/discovery lane.

## Contract Decisions To Freeze

- The first slice for this lane is the startup/discovery boundary problem, not a generic “make docs smaller” sweep.
- Gradual discovery should stay capability- and boundary-triggered rather than ontology-first.
- Root-visible product shape should shrink by better routing and quieter defaults before introducing new concepts.

## Open Questions To Close

- Which README and doctrine content should be treated as follow-on compression targets only after the startup/discovery contract is frozen?

## Validation Commands

- `uv run pytest tests/test_workspace_cli.py -k "defaults_command_reports_machine_readable_default_routes_as_json" -q`
- `uv run pytest packages/planning/tests/test_installer.py -k "compatibility_view_categories_are_exhaustive_and_disjoint or planning_readme_and_bootstrap_agents_describe_required_follow_on_routing" -q`
- `uv run pytest packages/planning/tests/test_check_planning_surfaces.py -q`
- `uv run pytest tests/test_maintainer_surfaces.py -q`
- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run agentic-workspace summary --format json`

## Required Tools

- `uv`
- `agentic-workspace`

## Completion Criteria

- `todo.active_items` points at this execplan as the active lane.
- The completed ownership-boundary lane is no longer present in the inactive roadmap queue.
- The remaining inactive queue begins with `system-intent-and-planning-trust`.
- Summary/report surfaces show one active planning thread and the updated roadmap ordering.

## Proof Report

- Validation proof (logs, command output, or screenshots): targeted CLI defaults test, planning installer/checker tests, maintainer-surface tests, planning-surface check, `agentic-workspace defaults --section startup --format json`, `agentic-workspace summary --format json`, and final `agentic-planning-bootstrap` / `agentic-memory-bootstrap` refresh passes all succeeded.
- Proof achieved now: the tiny safe startup model and discovery-boundary contract are now shipped through defaults, routing, startup reporting, generated helpers, and planning-surface enforcement.
- Evidence for "Proof achieved" state: `agentic-workspace defaults --section startup --format json` now exposes `tiny_safe_model`, `escalation_cues`, and `top_level_capabilities`; the planning upgrade renders the new helper sections and installs `.agentic-workspace/docs/minimum-operating-model.md`.

## Intent Satisfaction

- Original intent: Promote the next lane.
- Was original intent fully satisfied?: yes for the first bounded startup/discovery tranche; no for the larger lane
- Evidence of intent satisfaction: `#223`, `#227`, and `#228` now have concrete shipped contract surfaces and enforcement paths instead of remaining review-only direction.
- Unsolved intent passed to: none

## Execution Summary

- Outcome delivered: implemented the first bounded startup/discovery tranche and froze the minimum operating model for later compression work.
- Validation confirmed: targeted defaults, installer, checker, maintainer-surface, planning-surface, startup-selector, summary, and final repo-level package-refresh validation all passed.
- Follow-on routed to: the same active execplan
- Knowledge promoted (Memory/Docs/Config): canonical docs and startup defaults/report contracts
- Resume from: narrow the next README/doctrine/query-surface cleanup slice against the frozen startup/discovery contract

## Drift Log

- 2026-04-21: Promoted the `product-compression-and-gradual-discovery` roadmap lane into active planning after the ownership-boundary lane closed.
- 2026-04-21: Implemented the first bounded tranche from `#223`, `#227`, and `#228` by shipping the tiny safe startup model, boundary-triggered discovery cues, and compact top-level capability advertisement.
