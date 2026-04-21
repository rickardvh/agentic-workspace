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
- Intentionally deferred: broader query-surface cleanup now that the startup/discovery contract is frozen and the front-door/doctrine slice has landed.
- Discovered implications: the inactive roadmap queue should now begin with system-intent-and-planning-trust once this lane is active.
- Proof achieved now: the startup/discovery tranche is frozen, and the next compression slice now has a stricter README front door plus a smaller must-internalize doctrine surface with tactical dogfooding policy routed elsewhere.
- Validation still needed: prove the ordinary operating-map lookup can move from prose-first tables into a compact defaults surface without duplicating truth.
- Next likely slice: if the operating-question selector lands cleanly, decide whether any additional routine question still needs promotion under `#226`.

## Delegated Judgment

- Requested outcome: Promote the next roadmap lane and start the product-compression-and-gradual-discovery thread cleanly.
- Hard constraints: keep the lane bounded to startup/discovery/compression pressure; do not reopen closed ownership cleanup unless new evidence demands it.
- Agent may decide locally: exact tranche title, bounded first-slice wording, and compact continuation framing.
- Escalate when: the lane boundary becomes ambiguous, the requested outcome would widen into a different lane, or the first slice cannot be bounded without live issue re-triage.

## Active Milestone

- ID: product-compression-and-gradual-discovery-2026-04-21
- Status: in-progress
- Scope: promote the ordinary operating-question map from prose into a compact defaults surface now that the startup/discovery model, README front door, and doctrine boundary are frozen.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Move the ordinary operating-question map out of `docs/which-package.md` and into a compact defaults surface, then shrink the prose table so it becomes secondary.

## Blockers

- None.

## Touched Paths

- `README.md`
- `docs/design-principles.md`
- `docs/dogfooding-feedback.md`
- `docs/contributor-playbook.md`
- `docs/which-package.md`
- `.agentic-workspace/planning/state.toml`
- `.agentic-workspace/planning/execplans/product-compression-and-gradual-discovery-2026-04-21.md`
- `.agentic-workspace/planning/reviews/product-compression-context-cost-review-2026-04-21.md`
- `packages/planning/src/repo_planning_bootstrap/`
- `packages/planning/bootstrap/.agentic-workspace/docs/`
- `packages/planning/bootstrap/.agentic-workspace/planning/`
- `tools/AGENT_QUICKSTART.md`
- `tools/AGENT_ROUTING.md`

## Invariants

- Active lane state must remain recoverable from `todo.active_items` plus one execplan.
- Completed roadmap lanes should leave the inactive queue instead of lingering as stale candidates.
- Promotion should not silently widen the requested outcome beyond the product-compression/discovery lane.
- README should stay a front door, not a compact handbook.
- `docs/design-principles.md` should stay enduring doctrine, not a mixed doctrine-and-policy bundle.
- routine operating lookup should prefer one compact query surface over prose tables when the answer is already structured.

## Contract Decisions To Freeze

- The first slice for this lane is the startup/discovery boundary problem, not a generic "make docs smaller" sweep.
- Gradual discovery should stay capability- and boundary-triggered rather than ontology-first.
- Root-visible product shape should shrink by better routing and quieter defaults before introducing new concepts.

## Open Questions To Close

- Is the operating-question map sufficient as the first `#226` proof point, or does one more routine lookup still force prose rereads often enough to justify another compact promotion?

## Validation Commands

- `uv run pytest tests/test_workspace_cli.py -k "defaults_command_reports_machine_readable_default_routes_as_json" -q`
- `uv run pytest tests/test_workspace_cli.py -k "operating_questions" -q`
- `uv run pytest tests/test_maintainer_surfaces.py -q`
- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run agentic-workspace summary --format json`

## Required Tools

- `uv`
- `agentic-workspace`

## Completion Criteria

- `todo.active_items` points at this execplan as the active lane.
- `README.md` reads as a stricter front door rather than a compact handbook.
- `docs/design-principles.md` is smaller and more clearly must-internalize doctrine.
- tactical dogfooding and admission policy has a narrower owner surface.
- one routine operating-map lookup is answered by a compact defaults surface instead of a prose table.
- corresponding prose now clearly points back to the queryable surface instead of competing with it.

## Proof Report

- Validation proof (logs, command output, or screenshots): `uv run pytest tests/test_workspace_cli.py -k "defaults_command_reports_machine_readable_default_routes_as_json or operating_questions" -q`; `uv run pytest tests/test_maintainer_surfaces.py -q`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-workspace defaults --section operating_questions --format json`; `uv run agentic-workspace summary --format json`.
- Proof achieved now: the active lane now has a stricter public front door, a smaller must-internalize doctrine surface, and one ordinary operating-map lookup promoted into a compact defaults surface without changing the already-frozen startup/discovery model.
- Evidence for "Proof achieved" state: `README.md` now points ordinary work at the compact startup path and narrower maintainer docs; `docs/design-principles.md` now holds doctrine rather than mixed tactical policy; `docs/dogfooding-feedback.md` owns dogfooding/admission policy explicitly; `docs/which-package.md` now points its routine operating map at the queryable defaults answer.

## Intent Satisfaction

- Original intent: Promote the next lane.
- Was original intent fully satisfied?: yes for the first bounded startup/discovery tranche; no for the larger lane
- Evidence of intent satisfaction: `#223`, `#227`, and `#228` landed first; `#224` and the doctrine half of `#225` now follow from that frozen model instead of widening it; `#226` now starts by moving the operating-question map into a compact defaults surface.
- Unsolved intent passed to: none

## Execution Summary

- Outcome delivered: tightened the README into a stricter front door, compressed `docs/design-principles.md` into enduring doctrine, moved tactical dogfooding/admission policy into `docs/dogfooding-feedback.md`, and promoted the ordinary operating-question map into a compact defaults surface.
- Validation confirmed: workspace CLI defaults tests, maintainer-surface tests, planning-surface checks, the new compact operating-question answer, and the compact planning summary all passed after the compression changes.
- Follow-on routed to: the same active execplan
- Knowledge promoted (Memory/Docs/Config): canonical docs and startup defaults/report contracts
- Resume from: decide whether any routine operational lookup beyond the operating-question map still forces enough prose rereading to justify another compact promotion under `#226`

## Drift Log

- 2026-04-21: Promoted the `product-compression-and-gradual-discovery` roadmap lane into active planning after the ownership-boundary lane closed.
- 2026-04-21: Implemented the first bounded tranche from `#223`, `#227`, and `#228` by shipping the tiny safe startup model, boundary-triggered discovery cues, and compact top-level capability advertisement.
- 2026-04-21: Used the startup review plus live issue bodies for `#224`, `#225`, and `#226` to narrow the second slice: README/front-door compression and doctrine compression now land before any broader query-surface expansion.
