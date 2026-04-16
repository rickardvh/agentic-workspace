# Intent Interpretation Contract

## Goal

- Add a first-class contract for vague prompt handling so Memory can inform Planning without silently rewriting user ends.
- Distinguish confirmed intent from interpreted intent and keep escalation boundaries explicit.
- Make the cheap clarification path, relay path, and durable Memory capture path cheaper than ad hoc prompt polishing.

## Non-Goals

- Do not build generic natural-language understanding research.
- Do not require long formal prompts from users.
- Do not turn Memory into an active planner.
- Do not add a second full intent system.

## Intent Continuity

- Larger intended outcome: make vague prompts cheap to interpret without losing the human/agent boundary.
- This slice completes the larger intended outcome: yes
- Continuation surface: none

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Delegated Judgment

- Requested outcome: preserve confirmed intent, inferred intent, and escalation boundaries while making vague prompts cheaper to handle.
- Hard constraints: do not silently widen user ends; do not require Memory for every install; keep the contract compact.
- Agent may decide locally: field names, whether the bridge lives in docs, defaults, reporting, or planning summary surfaces first, and the narrowest validation that proves the slice.
- Escalate when: the better-looking answer changes the requested outcome, needs a broader rewrite, or requires turning the work into a generic prompt engine.

## Active Milestone

- Status: completed
- Scope: completed
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Completed.

## Blockers

- None.

## Touched Paths

- `docs/intent-contract.md`
- `docs/proof-surfaces-contract.md`
- `docs/ownership-authority-contract.md`
- `docs/delegated-judgment-contract.md`
- `docs/capability-aware-execution.md`
- `docs/default-path-contract.md`
- `docs/reporting-contract.md`
- `memory/templates/memory-note-template.md`
- `memory/runbooks/README.md`
- `memory/runbooks/`
- `memory/manifest.toml`
- `src/agentic_workspace/cli.py`
- `tests/test_workspace_cli.py`

## Invariants

- Confirmed intent stays human-owned.
- Interpreted intent must remain visibly inferred.
- Escalation boundaries stay compact and explicit.
- Memory remains additive, not required for basic Planning functionality.

## Contract Decisions To Freeze

- `defaults --section intent --format json` owns the front-door confirmed-versus-interpreted split.
- `defaults --section clarification --format json` owns the smallest repo-context follow-up for vague prompts.
- `defaults --section prompt_routing --format json` owns the compact proof-lane and owner inference surface.
- `defaults --section relay --format json` owns the planner-to-implementer handoff and routed-Memory bridge.
- `init` handoff mirrors the same split for bootstrap follow-through.
- `report` stays the combined workspace-state surface rather than becoming a second intent contract.

## Open Questions To Close

- None.

## Validation Commands

- `uv run pytest tests/test_workspace_cli.py -q`
- `uv run ruff check src tests`
- `uv run python scripts/check/check_planning_surfaces.py`
- `git diff --check`

## Required Tools

- `uv`
- `gh`

## Completion Criteria

- The repo can name confirmed intent versus interpreted intent in a compact contract surface.
- The distinction is visible in the checked-in docs or machine-readable defaults.
- At least one real vague-prompt path is documented and validated end to end.
- The next tranche can continue from the checked-in plan without chat reconstruction.

## Execution Summary

- Outcome delivered: confirmed versus interpreted intent, cheap clarification, prompt routing, relay, and durable Memory capture guidance now all appear in checked-in contract surfaces.
- Validation confirmed: `uv run pytest tests/test_workspace_cli.py -q`, `uv run ruff check src tests`, `uv run python scripts/check/check_planning_surfaces.py`, `uv run python scripts/check/check_memory_freshness.py`.
- Follow-on routed to: none.
- Resume from: none.

## Drift Log

- 2026-04-16: Plan created from the vague-prompt / intent-interpretation tranche.
- 2026-04-16: First slice landed the confirmed-versus-interpreted intent split in defaults and bootstrap handoff surfaces.
- 2026-04-16: Second slice landed cheap clarification and prompt routing selectors for vague prompts.
- 2026-04-16: Third slice landed the relay selector and routed-Memory handoff contract.
- 2026-04-16: Final slice landed durable Memory capture guidance for repeated vague-instruction failures.
