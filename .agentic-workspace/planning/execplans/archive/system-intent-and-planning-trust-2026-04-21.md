# System Intent And Planning Trust

## Goal

- Implement the `system-intent-and-planning-trust` lane end-to-end so the repo preserves higher-level intent, records honest closure decisions, and exposes continuation gaps through ordinary planning/reporting paths.

## Non-Goals

- Reopening the earlier product-compression tranche except where its surfaces need alignment with the new trust contract.
- Turning planning into a second knowledge base or a heavyweight workflow engine.
- Adding a second durable planning state store outside `.agentic-workspace/planning/state.toml` plus execplans.

## Machine-Readable Contract

```yaml
intent:
  outcome: "Make higher-level system intent and closure trust recoverable without rereading raw plan prose."
  constraints: "Keep one planning authority, prefer compact query surfaces, and preserve honest partial completion."
  latitude: "May add compact docs, defaults/report selectors, and archive/check semantics if they stay derivable from existing planning surfaces."
  escalation: "Escalate if the lane would require a second durable state store or ambiguous split between workspace and planning ownership."
execution:
  milestone: "Define and ship the minimum durable system-intent and closure-check contract."
  status: "completed"
  next_step: "None. The lane is complete and ready to archive."
  proof: "Targeted planning installer tests, checker tests, workspace CLI selector tests, package upgrades, and compact summary/report surfaces all show honest archive semantics and system-intent visibility."
scope:
  touched:
    - ".agentic-workspace/planning/state.toml"
    - ".agentic-workspace/planning/execplans/system-intent-and-planning-trust-2026-04-21.md"
    - ".agentic-workspace/docs/"
    - "packages/planning/src/repo_planning_bootstrap/"
    - "packages/planning/bootstrap/"
    - "scripts/check/check_planning_surfaces.py"
    - "src/agentic_workspace/cli.py"
    - "tests/"
  invariants:
    - "Slice completion must stay distinct from larger-intent completion."
    - "Archive may be honest for partial intent only when continuation and evidence are explicit."
    - "Ordinary planning/report surfaces should expose closure blockers before archive."
```

## Intent Continuity

- Larger intended outcome: Make durable planning and closure semantics trustworthy across tasks, issues, and fragmented sessions.
- This slice completes the larger intended outcome: yes
- Continuation surface: none
- Parent lane: system-intent-and-planning-trust

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Iterative Follow-Through

- What this slice enabled: the repo now has one durable system-intent contract, one explicit closure-check section in execplans, evidence-based archive semantics for partial-intent slices, and earlier closure-trust visibility through summary/report/check surfaces.
- Intentionally deferred: no further follow-on inside this lane; later context-budget and delegation-review work stays in separate roadmap lanes.
- Discovered implications: the machine-readable contract fence in execplans needed to be treated as a legitimate planning surface instead of a false memory-blur signal.
- Proof achieved now: the shipped planning/workspace surfaces now distinguish slice completion from larger-intent closure and route continuation explicitly.
- Validation still needed: none.
- Next likely slice: promote `context-budget-and-cheap-context-switching` when the next bounded lane is activated.

## Delegated Judgment

- Requested outcome: Implement the live issue cluster behind `#236`, `#237`, `#238`, `#232`, `#229`, `#220`, `#222`, and `#221` as one coherent planning-trust change.
- Hard constraints: keep one durable planning authority; do not invent hidden state; preserve honest partial completion; keep ordinary recovery compact.
- Agent may decide locally: exact field names, selector names, and whether the compact trust surface lives in defaults, summary/report, or both.
- Escalate when: satisfying the lane would require contradictory closure rules, duplicate intent owners, or a broader redesign of planning beyond this trust contract.

## Active Milestone

- ID: system-intent-and-planning-trust-2026-04-21
- Status: completed
- Scope: add the minimum durable system-intent contract, explicit closure-check semantics, evidence-based archive behavior, and earlier report/check surfacing for continuation gaps.
- Ready: completed
- Blocked: none
- optional_deps: none

## Immediate Next Action

- None. Archive this completed lane and activate the next roadmap lane when ready.

## Blockers

- None.

## Touched Paths

- `.agentic-workspace/planning/state.toml`
- `.agentic-workspace/planning/execplans/system-intent-and-planning-trust-2026-04-21.md`
- `.agentic-workspace/docs/execution-flow-contract.md`
- `.agentic-workspace/planning/execplans/README.md`
- `.agentic-workspace/planning/execplans/TEMPLATE.md`
- `packages/planning/src/repo_planning_bootstrap/installer.py`
- `packages/planning/bootstrap/.agentic-workspace/docs/`
- `packages/planning/bootstrap/.agentic-workspace/planning/`
- `packages/planning/README.md`
- `scripts/check/check_planning_surfaces.py`
- `packages/planning/tests/`
- `src/agentic_workspace/cli.py`
- `tests/test_workspace_cli.py`

## Invariants

- The governing system-intent rule must be queryable without reopening raw issue prose.
- Checked-in execplans remain required when later proof, intent validation, or follow-through depends on durable residue.
- `archive-plan` must allow slice-complete but intent-partial work only when continuation owner, activation trigger, and closure evidence are explicit.
- Stronger proof is required to close a larger intent than to archive a bounded slice.
- Ordinary planning/report/check surfaces should reveal closure blockers before a contributor reaches archive time.

## Contract Decisions To Freeze

- System intent needs its own compact, durable contract surface instead of surviving only in scattered issue prose or plan narratives.
- Closure is not binary: the contract must distinguish slice completion, larger-intent satisfaction, and required continuation.
- Confidence alone is not closure evidence; the repo should record the evidence class and the closure decision explicitly.
- Archive readiness should be validated by the same checked-in contract that later contributors use for restart and review.

## Open Questions To Close

- Should the compact system-intent surface live only in defaults, or also be echoed in summary/report output for active planning?
- Which minimum closure-check fields are required to keep archive truthful without turning execplans into a second issue tracker?

## Validation Commands

- `uv run pytest packages/planning/tests/test_installer.py -k "archive or closure or summary or report" -q`
- `uv run pytest tests/test_workspace_cli.py -k "defaults_command_reports_machine_readable_default_routes_as_json or system_intent" -q`
- `uv run python scripts/check/check_planning_surfaces.py`
- `rg "system-intent-contract|Closure Check|archive-and-close|archive-but-keep-lane-open" .`
- `uv run agentic-workspace defaults --section system_intent --format json`
- `uv run agentic-workspace summary --format json`

## Required Tools

- `uv`
- `agentic-workspace`
- `gh`

## Completion Criteria

- A compact system-intent contract is queryable from the normal workspace front door.
- Active and archived execplans use an explicit closure-check section that distinguishes slice completion from larger-intent closure.
- `archive-plan` accepts honest slice completion with explicit continuation and rejects unsupported closure claims.
- planning summary/report output surfaces the relevant continuation or closure-trust state without reopening raw plan prose first.
- planning-surface checks flag missing or contradictory closure evidence earlier than archive.
- the live issue cluster for this lane can close without pretending the repo now has a second planning authority or a hidden state machine.

## Proof Report

- Validation proof: `uv run pytest packages/planning/tests/test_installer.py -q`; `uv run pytest packages/planning/tests/test_check_planning_surfaces.py -q`; `uv run pytest tests/test_workspace_cli.py -k "defaults and (system_intent or install_profiles or operating_questions)" -q`; `uv run agentic-planning-bootstrap upgrade --target .`; `uv run agentic-memory-bootstrap upgrade --target .`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-workspace defaults --section system_intent --format json`; `uv run agentic-workspace summary --format json`; `uv run agentic-planning-bootstrap report --target . --format json`.
- Proof achieved now: yes.
- Evidence for "Proof achieved" state: the repo now ships `.agentic-workspace/docs/system-intent-contract.md`, execplans now require `Closure Check`, `archive-plan` allows honest partial-intent archive while blocking unsupported close claims, the planning checker catches closure drift earlier, and the compact defaults/summary/report surfaces expose the governing system-intent and closure state directly.

## Intent Satisfaction

- Original intent: Fully implement `system-intent-and-planning-trust`.
- Was original intent fully satisfied?: yes
- Evidence of intent satisfaction: the lane now preserves one durable system-intent layer, one explicit closure/gap contract, evidence-based archive semantics, one checked-in rule for when execplans are mandatory durable residue, and earlier report/check surfacing for closure blockers.
- Unsolved intent passed to: none

## Closure Check

- Slice status: bounded slice complete
- Larger-intent status: closed
- Closure decision: archive-and-close
- Why this decision is honest: the shipped repo surfaces now satisfy the whole lane rather than only one subordinate implementation slice.
- Evidence carried forward: the proof report, compact system-intent selector, summary/report projections, archive semantics, and early checker/report signals all align with the intended outcome.
- Reopen trigger: reopen only if repeated later work shows the system-intent layer or closure-trust contract still fails to preserve larger intent honestly in ordinary use.

## Execution Summary

- Outcome delivered: added a durable system-intent contract, wired `system_intent` into workspace defaults plus planning summary/report, added `Closure Check` to the execplan contract, updated archive behavior so partial-intent slices can archive honestly with explicit continuation, and moved closure-trust warnings into ordinary planning checks.
- Validation confirmed: targeted planning installer tests, planning checker tests, workspace CLI defaults tests, package upgrades, planning-surface checks, and compact defaults/summary/report outputs all passed.
- Follow-on routed to: `.agentic-workspace/planning/state.toml`
- Knowledge promoted (Memory/Docs/Config): planning payload docs, package README, planning summary/report schema, and workspace defaults
- Resume from: activate `context-budget-and-cheap-context-switching` when the next bounded lane is ready

## Drift Log

- 2026-04-21: Promoted `system-intent-and-planning-trust` from the roadmap into an active execplan after verifying the live issue cluster with `gh`.
- 2026-04-21: Shipped the system-intent contract, closure-check execplan contract, evidence-based archive semantics, and earlier closure-trust signals across defaults, summary/report, and planning checks.
