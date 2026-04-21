# GitHub Issues 80-82 Follow-Through

## Goal

- Close the current bounded GitHub issue tranche by tightening the external-agent front door and by making fresh memory installs more immediately useful without widening either module into heavier documentation or repo-specific bootstrap guidance.

## Non-Goals

- Do not promote the newer planning-refinement issues `#84` through `#88` into active implementation prematurely.
- Do not turn `llms.txt` into a second README or a broad maintainer reference.
- Do not turn memory bootstrap examples into bulky pseudo-documentation or repo-specific truth.

## Intent Continuity

- Larger intended outcome: keep the live GitHub issue queue reconciled into checked-in planning while closing the highest-value bounded slices first.
- This slice completes the larger intended outcome: no
- Continuation surface: ROADMAP.md

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: ROADMAP.md
- Activation trigger: when the active `#80`-`#82` tranche completes and the next highest-priority planning-refinement candidate is ready to promote

## Delegated Judgment

- Requested outcome: ingest and prioritize the new GitHub issues, close the current bounded front-door and memory-bootstrap tranche with commits and dogfooding, and route the broader planning-refinement follow-on back into roadmap order instead of mixing them into this execution slice.
- Hard constraints: keep live `gh` state upstream-authoritative, keep startup and handoff entrypoints compact, preserve `AGENTS.md` as the startup entrypoint, and keep bootstrap examples clearly weak-authority and easy to replace.
- Agent may decide locally: issue grouping inside the tranche, exact doc and payload wording, validation scope, and whether one or two commits best preserve clean module boundaries.
- Escalate when: the smallest safe implementation would require a broader redesign of external-agent bootstrap, memory note taxonomy, or the planning-state hierarchy that belongs in the roadmap candidates instead.

## Active Milestone

- Status: completed
- Scope: closed `#80`, `#81`, and `#82` through one bounded front-door plus memory-bootstrap tranche while leaving `#84`-`#88` inactive in roadmap order.
- Ready: complete
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Promote the next planning-state/reporting tranche from `ROADMAP.md`.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- README.md
- llms.txt
- memory/
- src/agentic_workspace/
- tests/test_workspace_cli.py
- packages/memory/

## Invariants

- `AGENTS.md` remains the root startup entrypoint.
- `llms.txt` stays compact and front-door shaped rather than turning into a second maintainer handbook.
- Generated routing docs remain mirrors of canonical sources, not hand-edited authorities.
- Memory starter examples stay obviously replaceable and weak-authority.
- The new planning-refinement issues remain inactive candidates until this bounded tranche closes.

## Contract Decisions To Freeze

- Front-door discoverability and compact external-agent state queries belong in the existing startup surfaces, not in a new parallel handoff document family.
- Memory bootstrap should prove its value faster through tiny concrete examples, not by bloating the README-style category notes.
- Broader planning-surface compression work belongs in roadmap follow-through after this tranche, not hidden inside it.

## Open Questions To Close

- Which front-door surface should carry the compact query-first state checks: `llms.txt`, `README.md`, or both?
- What is the smallest concrete starter example set that proves each primary memory note class without pretending to be repo-specific truth?

## Validation Commands

- `uv run pytest tests/test_workspace_cli.py -q`
- `cd packages/memory && uv run pytest tests/test_installer.py -q`
- `uv run agentic-planning-bootstrap upgrade --target .`
- `uv run agentic-memory-bootstrap upgrade --target .`
- `uv run python scripts/check/check_source_payload_operational_install.py`
- `uv run python scripts/check/check_planning_surfaces.py`

## Completion Criteria

- `#80` and `#82` are closed with compact, aligned front-door routing that exposes the smallest useful query-first state surfaces.
- `#81` is closed with weak-authority starter examples for the primary memory note classes.
- Any remaining broader planning-refinement work is explicitly left in `ROADMAP.md` rather than leaked into the active tranche.

## Execution Summary

- Outcome delivered: compact external-agent handoff now exposes query-first state checks and generated routing docs from the public front door, and fresh memory installs now seed one weak-authority example for each primary note class.
- Validation confirmed: `uv run pytest tests/test_workspace_cli.py -q -k "external_agent_handoff_text or test_report_real_init_summarizes_combined_workspace_state or test_setup_command_reports_no_new_seed_surfaces_for_mature_repo"`, `uv run pytest packages/memory/tests/test_installer.py -q -k "memory_freshness_strict_default_does_not_fail_on_bootstrap_placeholders or memory_freshness_strict_can_fail_on_bootstrap_placeholders_when_requested or starter_examples or bootstrap_index_includes_token_efficiency_and_small_routing_examples or bootstrap_readme_includes_optional_patterns_and_project_state_shape"`, `uv run pytest packages/memory/tests/test_packaging.py -q`, `uv run agentic-memory-bootstrap upgrade --target .`, `uv run agentic-workspace upgrade --target .`, `uv run agentic-workspace doctor --target .`, `uv run python scripts/check/check_memory_freshness.py --strict`, `uv run python scripts/check/check_source_payload_operational_install.py`, `uv run python scripts/check/check_planning_surfaces.py`
- Follow-on routed to: ROADMAP.md
- Resume from: promote the planning-state/reporting tranche (`#86` + `#85`) and keep the operating-map plus maintenance/measurement work inactive until that hierarchy settles.

## Drift Log

- 2026-04-15: Promoted the live `#80`-`#82` issue tranche into active planning and routed the newer planning-refinement issues `#84`-`#88` into a quiet roadmap queue instead of widening the active owner.
- 2026-04-15: Closed `#80` and `#82` by tightening `llms.txt` around compact state-query commands and by exposing `tools/AGENT_QUICKSTART.md` plus `tools/AGENT_ROUTING.md` from the public front door without changing `AGENTS.md` startup precedence.
- 2026-04-15: Closed `#81` by shipping starter example notes for domains, invariants, runbooks, and decisions, teaching the packaged freshness checker to stay quiet when placeholder findings are absent, and dogfooding the starter-note manifest entries plus strict freshness pass in the repo root.
