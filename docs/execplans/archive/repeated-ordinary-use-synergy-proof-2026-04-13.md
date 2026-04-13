# Repeated Ordinary-Use Synergy Proof

## Goal

- Prove the combined Memory/Planning install against ordinary repo work rather than contract prose alone.
- Confirm whether current memory and planning surfaces keep restart and re-orientation cheap, and tighten the shipped contract if stale shared context still slips through.

## Non-Goals

- Redesign the planning-memory interaction model.
- Expand mixed-agent config or scheduling behavior.
- Treat a single ordinary-use pass as the final proof for all future synergy claims.

## Intent Continuity

- Larger intended outcome: repeated ordinary work should show that Memory shortens plans, restart uses the smallest useful durable bundle, and completed planning work promotes only the residue worth keeping.
- This slice completes the larger intended outcome: yes
- Continuation surface: none

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Delegated Judgment

- Requested outcome: use ordinary repo work to test whether the combined install is actually keeping current context cheap, fix any small shipped gap that blocks that proof, and leave durable evidence in checked-in planning or memory state.
- Hard constraints: keep the slice bounded; prefer a real friction-confirmed current-context failure over speculative review; do not turn memory into a second planning layer; keep package source, payload, and root install aligned when shipped behavior changes.
- Agent may decide locally: the smallest proof artifact, the exact freshness-tightening needed if current-note drift is missed, and the final shape of current-memory notes after the proof.
- Escalate when: the proof requires reopening the broader planning-memory contract, the required fix would sprawl into unrelated doctor or routing redesign, or the current repo state cannot be made coherent without a larger planning pass first.

## Active Milestone

- Status: completed
- Scope: prove the combined install on one ordinary maintenance cycle, tighten the freshness lane if it misses stale shared current context, and refresh the repo's current-memory notes to match current planning reality.
- Ready: completed
- Blocked: none
- optional_deps: GitHub issue `#25`

## Immediate Next Action

- Promote the next highest-priority roadmap candidate.

## Blockers

- None.

## Touched Paths

- `TODO.md`
- `ROADMAP.md`
- `docs/execplans/archive/repeated-ordinary-use-synergy-proof-2026-04-13.md`
- `packages/memory/src/repo_memory_bootstrap/`
- `packages/memory/bootstrap/`
- `packages/memory/tests/`
- `scripts/check/check_memory_freshness.py`
- `memory/current/`

## Invariants

- Planning remains the owner of active execution state.
- Memory current notes remain weak-authority re-orientation surfaces, not a shadow planner.
- Any shipped behavior change keeps source, payload, and root install aligned.
- The proof leaves only the smallest durable residue that still lowers restart cost.

## Open Questions Closed

- Freshness-gap question: before this slice, the shipped freshness lane missed explicit planning-state residue in `memory/current/project-state.md`; after this slice, both the bundled freshness script and `agentic-memory-bootstrap current check` flag that class of drift.
- Current-memory shape question: the smallest useful current bundle for this repo right now is a compact overview plus optional continuation compression, with no explicit execplan ownership embedded in memory.
- Completion question: yes. The proof found and fixed a real combined-install gap on ordinary work, then refreshed the repo to the corrected contract.

## Validation Commands

- `uv run pytest packages/memory/tests/test_installer.py -k "planning_state_residue or current_check_flags_project_state_planning_state_residue or memory_freshness_reports_current_planning_state_residue or current_check_flags_task_context_structure_drift_and_planner_signals or current_check_flags_stale_project_state or memory_freshness_strict_default_does_not_fail_on_bootstrap_placeholders or memory_freshness_strict_can_fail_on_bootstrap_placeholders_when_requested"`
- `uv run ruff check packages/memory`
- `uv run agentic-memory-bootstrap upgrade --target .`
- `uv run python scripts/check/check_memory_freshness.py`
- `uv run agentic-memory-bootstrap current check --target .`
- `uv run python scripts/check/check_source_payload_operational_install.py`

## Completion Criteria

- Ordinary repo work produces a concrete combined-install proof result.
- The freshness/doctor lane catches the observed stale current-context class if it is a shipped gap.
- Root current-memory notes are refreshed to current reality and stay subordinate to planning.
- The slice records what the proof did and did not establish before archival.

## Execution Summary

- Outcome delivered: yes. Ordinary repo work exposed stale planning-state residue in root current memory, and the shipped freshness/current-check surfaces now catch that class of drift.
- Validation confirmed: yes. Focused memory tests, lint, source/payload/root boundary checks, the installed freshness script, and current-memory checks all passed after the fix.
- Follow-on routed to: none.
- Resume from: promote `Strong-planner / cheap-implementer dogfooding` from the highest-priority queue.

## Proof Outcome

- What worked:
- The combined install produced a real friction-confirmed signal instead of abstract doctrine churn.
- The missing-synergy signal mapped cleanly to a shipped fix: explicit planning-state residue in `memory/current/*` is now treated as drift.
- Refreshing the root current-memory notes back to a smaller shape left the live repo cheaper to trust on restart.

- What this still does not prove:
- It does not by itself prove cross-agent continuity or stronger-planner/cheaper-implementer execution on a nontrivial implementation slice.

## Drift Log

- 2026-04-13: Promoted from the highest-priority roadmap queue after the first mixed-agent dogfood pass shifted the next evidence need from abstract contract writing to ordinary combined-install proof.
- 2026-04-13: Completed after ordinary work exposed stale current-memory planning residue, the shipped freshness/current-check lane was tightened to catch it, and the root current-memory notes were refreshed to the corrected shape.
