# Planning Recovery Ambiguity Audit

## Goal

- Audit the routine planning recovery questions for ordinary agent work.
- Identify the cheapest current owner surface for each question.
- Call out the main repeated ambiguity or reread pressure that still remains.

## Scope

- `AGENTS.md`
- `TODO.md`
- `docs/default-path-contract.md`
- `docs/execplans/README.md`
- `docs/execplans/planning-surface-clarity-lane-2026-04-17.md`
- `agentic-planning-bootstrap summary --format json`

## Non-Goals

- Change planning ownership.
- Rewrite the compact summary schema.
- Promote follow-on work out of this review.

## Review Mode

- Mode: `routine-planning-recovery-audit`
- Review question: Which current surfaces answer the ordinary planning recovery questions cheapest, and where does prose reread pressure still remain?
- Default finding cap: 1 finding
- Inputs inspected first: `agentic-planning-bootstrap summary --format json`, `docs/default-path-contract.md`, `docs/execplans/README.md`

## Review Method

- Commands used:
  - `Get-Content AGENTS.md`
  - `Get-Content TODO.md`
  - `Get-Content docs/default-path-contract.md`
  - `Get-Content docs/execplans/README.md`
  - `Get-Content docs/execplans/planning-surface-clarity-lane-2026-04-17.md`
  - `uv run agentic-planning-bootstrap summary --format json`
- Evidence sources:
  - repo startup and planning-routing guidance
  - compact planning summary projections
  - active execplan framing for the current lane

## Recovery Map

| Routine question | Cheapest current owner surface | Why this is the cheapest surface now |
| --- | --- | --- |
| What is active right now? | `agentic-planning-bootstrap summary --format json` -> `planning_record` | It is the canonical compact active state and already names the active task, outcome, constraints, and continuation owner. |
| What should I do next? | `agentic-planning-bootstrap summary --format json` -> `resumable_contract.current_next_action` | This is the narrow restart field, so it avoids rereading raw TODO or execplan prose. |
| What larger chunk or queue owns follow-on? | `agentic-planning-bootstrap summary --format json` -> `hierarchy_contract.parent_lane`, `active_chunk`, `near_term_queue`, `next_likely_chunk` | The hierarchy projection is the current thin owner for parent-lane and queue answers. |
| What residue remains if this slice stops? | `agentic-planning-bootstrap summary --format json` -> `follow_through_contract` | The follow-through projection already carries deferred work, proof state, and next-likely-slice residue. |
| When do I fall back to prose? | `docs/default-path-contract.md`, then `docs/execplans/README.md` only if the compact summary is still ambiguous | These docs own the route rule, not the restart-critical facts themselves. |

## Findings

### Finding: The recovery questions are cheap now, but the fallback boundary is still split across two prose owners

- Summary: The compact planning summary already answers the ordinary recovery questions cheaply, but the repo still teaches the fallback path in both `docs/default-path-contract.md` and `docs/execplans/README.md`, and both still refer readers back to raw `TODO.md` or execplan prose as secondary fallback. That split leaves a small but repeated reread pressure: agents still have to compare prose owners before trusting the compact field map.
- Evidence: `docs/default-path-contract.md` lists the four routine recovery questions and says to fall back to prose only when the compact summary is ambiguous; `docs/execplans/README.md` repeats the same meaning boundary and restart guidance; `agentic-planning-bootstrap summary --format json` already exposes the compact fields that answer the questions directly.
- Risk if unchanged: Routine recovery keeps paying a comparison tax, especially for the boundary between follow-on ownership and slice residue, because the answer is spread across two prose docs plus the summary output.
- Suggested action: Add one shared compact question-to-owner table in the default path contract, then trim the duplicate fallback explanation in `docs/execplans/README.md` to a short pointer.
- Confidence: high
- Source: mixed
- Promotion target: canonical docs
- Promotion trigger: the next planning-surface clarity cleanup edit
- Post-remediation note shape: shrink

## Recommendation

- Promote: one compact question-to-surface map that keeps routine recovery on the summary path.
- Defer: broader planning-surface reshaping until another repeated ambiguity appears.
- Dismiss: raw planning prose as the default restart path.

## Validation / Inspection Commands

- `uv run agentic-planning-bootstrap summary --format json`
- `uv run python scripts/check/check_planning_surfaces.py`

## Drift Log

- 2026-04-17: Review created for issue #162.
