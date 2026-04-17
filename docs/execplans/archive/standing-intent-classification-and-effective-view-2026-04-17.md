# Standing Intent Classification And Effective View

## Goal

- Add the first standing-intent classification and promotion contract so durable repo-wide guidance no longer depends on chat memory alone.
- Expose a compact effective standing-intent view through workspace reporting so the current durable guidance is inspectable without broad rereads.

## Non-Goals

- Do not solve full precedence and supersession handling in this slice.
- Do not turn standing intent into a unified source of truth spanning policy, doctrine, Memory, Planning, and checks.
- Do not auto-promote every chat instruction into repo state.
- Do not broaden the slice into full enforcement generation.

## Intent Continuity

- Larger intended outcome: make durable repo intent classifiable, recoverable, evolvable, and promotable into stronger enforcement and reporting instead of leaving it trapped in chat.
- This slice completes the larger intended outcome: no
- Continuation surface: `ROADMAP.md` candidate lane `standing-intent-durability`
- Parent lane: `standing-intent-durability`

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: `ROADMAP.md`
- Activation trigger: standing guidance now has class and visibility, but precedence/supersession and stronger-home promotion are still unresolved.

## Iterative Follow-Through

- What this slice enabled: durable chat-borne guidance now has a compact class model, default owner mapping, and one effective report view grounded in current repo surfaces.
- Intentionally deferred: precedence/supersession rules and stronger enforcement promotion remain separate follow-on slices.
- Discovered implications: effective reporting is cheap enough when it reports owner surfaces and active direction, but it should stay source-attributed and not become a second editable state store.
- Proof achieved now: the repo can classify standing intent into policy, doctrine, durable understanding, active direction, enforceable workflow, and temporary local guidance, and the workspace report shows which durable classes are currently in force.
- Validation still needed: dogfood contradiction handling and stronger-home promotion in ordinary work before widening the contract.
- Next likely slice: define standing-intent precedence and supersession rules, then tighten the promotion path from doctrine or policy into stronger enforcement.

## Delegated Judgment

- Requested outcome: land one compact standing-intent classification and promotion contract plus one effective report view.
- Hard constraints: keep one primary owner per concern, keep the first slice routing-oriented rather than fully automated, and preserve the boundary between reporting and canonical owner surfaces.
- Agent may decide locally: the exact class names, the minimum effective-view shape, and which current repo surfaces should participate in the first report.
- Escalate when: the best remaining change would require a new durable state store, automatic policy generation, or a broad rule engine for precedence and enforcement.

## Active Milestone

- Status: completed
- Scope: define the standing-intent classes and owner mapping, surface them through `agentic-workspace report`, update canonical docs, refresh the installed planning payload, and route the next follow-on in the roadmap.
- Ready: ready
- Blocked: none
- optional_deps: GitHub issues `#143` and `#147`

## Immediate Next Action

- Promote the precedence and supersession slice for standing intent when the next bounded roadmap promotion is ready.

## Blockers

- None.

## Touched Paths

- `ROADMAP.md`
- `docs/reporting-contract.md`
- `docs/execplans/archive/standing-intent-classification-and-effective-view-2026-04-17.md`
- `packages/planning/README.md`
- `packages/planning/src/repo_planning_bootstrap/installer.py`
- `packages/planning/bootstrap/docs/standing-intent-contract.md`
- `src/agentic_workspace/cli.py`
- `src/agentic_workspace/reporting_support.py`
- `src/agentic_workspace/contracts/report_contract.json`
- `src/agentic_workspace/contracts/schemas/workspace_report.schema.json`
- `src/agentic_workspace/workspace_output.py`
- `tests/test_workspace_cli.py`

## Invariants

- Standing intent stays subordinate to the canonical owner surfaces that actually carry policy, doctrine, Memory, Planning, or checks.
- The first slice remains compact and routing-oriented rather than a broad automation or memory system.
- Effective reporting must preserve source provenance and authority shape instead of flattening everything into one blob.

## Contract Decisions To Freeze

- The first standing-intent class set is `config_policy`, `repo_doctrine`, `durable_understanding`, `active_directional_intent`, `enforceable_workflow`, and `temporary_local_guidance`.
- `agentic-workspace report --target ./repo --format json` is the first effective standing-intent inspection surface.
- The first effective view should report current owner surfaces and authority kinds rather than pretending precedence or supersession is already solved.

## Open Questions To Close

- How should newer durable standing guidance supersede older guidance across doctrine, config, planning, Memory, and checks?
- What decision test should move standing intent from prose into stronger enforcement once prose is no longer the strongest home?

## Validation Commands

- `uv run pytest tests/test_workspace_cli.py -q`
- `uv run agentic-workspace report --target . --format json`
- `uv run agentic-planning-bootstrap upgrade --target .`
- `uv run agentic-memory-bootstrap upgrade --target .`
- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run python scripts/check/check_source_payload_operational_install.py`

## Required Tools

- `uv`
- `gh`

## Completion Criteria

- A canonical standing-intent contract defines the minimum durable classes and default owner mapping.
- Workspace reporting exposes a compact effective standing-intent view with source provenance.
- The repo can dogfood the new contract against its current config, doctrine, Memory, Planning, and check surfaces.
- Follow-on work remains routed through the standing-intent roadmap lane rather than chat residue.

## Execution Summary

- Outcome delivered: added the standing-intent classification and promotion contract, exposed a first effective standing-intent view in `agentic-workspace report`, and routed the remaining lane forward to precedence/supersession plus stronger-home promotion.
- Validation confirmed: `uv run pytest tests/test_workspace_cli.py -q`; `uv run agentic-workspace report --target . --format json`; `uv run agentic-planning-bootstrap upgrade --target .`; `uv run agentic-memory-bootstrap upgrade --target .`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run python scripts/check/check_source_payload_operational_install.py`.
- Follow-on routed to: `ROADMAP.md` candidate lane `standing-intent-durability`
- Resume from: promote the precedence and supersession slice, then tighten stronger-home promotion into checks or config where prose is too weak.

## Drift Log

- 2026-04-17: Promoted from the top roadmap lane after the planning hierarchy tranche completed and standing repo guidance remained the next clear continuity gap.
- 2026-04-17: Landed the first standing-intent class model, effective reporting view, payload/install refresh, and roadmap follow-through routing.
