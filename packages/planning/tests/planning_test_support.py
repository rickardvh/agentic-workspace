from __future__ import annotations

# ruff: noqa: F401
import importlib.util
import json
import subprocess
import tomllib
from pathlib import Path

import pytest
from command_generation.generated_package_loader import load_generated_cli_module_for_entrypoint

import repo_planning_bootstrap._render as render_module
import repo_planning_bootstrap.installer as installer_mod
from repo_planning_bootstrap._ownership import module_root as planning_module_root
from repo_planning_bootstrap.installer import (
    OPTIONAL_PAYLOAD_FILES,
    PLANNING_COMPATIBILITY_CONTRACT_FILES,
    PLANNING_LOWER_STABILITY_HELPER_FILES,
    REQUIRED_PAYLOAD_FILES,
    adopt_bootstrap,
    archive_execplan,
    close_planning_item,
    collect_status,
    doctor_bootstrap,
    install_bootstrap,
    planning_handoff,
    planning_reconcile,
    planning_report,
    planning_summary,
    promote_todo_item_to_execplan,
    record_delegation_decision,
    uninstall_bootstrap,
    upgrade_bootstrap,
    verify_payload,
)

planning_cli = load_generated_cli_module_for_entrypoint("agentic-planning", "planning_runtime_cli")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def _load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_external_intent_evidence(path: Path, *, items: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "kind": "planning-external-intent-evidence/v1",
                "items": items,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_finished_work_evidence(path: Path, *, items: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "kind": "planning-finished-work-evidence/v1",
                "items": items,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_execplan_record(
    path: Path,
    *,
    item_id: str = "plan-alpha",
    status: str = "in-progress",
    references: list[dict[str, str]] | None = None,
) -> None:
    record = installer_mod._build_execplan_record_from_todo_item(
        title="Plan Alpha",
        item_id=item_id,
        status=status,
        why_now="this item needs a bounded execution contract.",
        next_action="add one checker.",
        done_when="the bounded change is implemented and validated.",
    )
    if references is not None:
        record["references"] = references
    record["system_intent_alignment"] = {
        "relevant system intent": "Preserve larger user or product outcome separately from the bounded slice.",
        "slice shaping bias": "Keep this slice small but route continuation explicitly.",
        "broader-lane validation question": ("Did this slice advance the parent lane rather than only local task completion?"),
        "intent evidence source": ".agentic-workspace/docs/system-intent-contract.md",
    }
    if status in {"completed", "done", "closed"}:
        record["iterative_follow_through"] = {
            "what this slice enabled": "one bounded planning improvement landed",
            "intentionally deferred": "none",
            "discovered implications": "none yet",
            "proof achieved now": "validation and closure checks passed for the bounded slice.",
            "validation still needed": "none",
            "next likely slice": "none",
        }
        record["execution_run"] = {
            "run status": "completed",
            "executor": "bounded external executor",
            "handoff source": "agentic-planning handoff --format json",
            "what happened": "implemented the bounded checker update and returned compact residue.",
            "scope touched": "scripts/check/check_planning_surfaces.py",
            "changed surfaces": "scripts/check/check_planning_surfaces.py",
            "validations run": "uv run pytest tests/test_check_planning_surfaces.py",
            "result for continuation": "no further delegated execution needed for this bounded slice.",
            "next step": "archive the plan.",
        }
        record["finished_run_review"] = {
            "review status": "completed",
            "scope respected": "yes",
            "proof status": "satisfied",
            "intent served": "yes",
            "config compliance": "respected checked-in and local config for the bounded slice.",
            "misinterpretation risk": "low",
            "follow-on decision": "archive-and-close",
        }
        record["execution_summary"] = {
            "outcome delivered": "Added one bounded planning improvement.",
            "validation confirmed": "uv run pytest tests/test_check_planning_surfaces.py",
            "follow-on routed to": "none; slice complete",
            "post-work posterity capture": (
                "preserve the checker-boundary reminder in planning docs and route any durable subsystem learning "
                "to canonical docs or Memory only when that module is installed and is the right owner."
            ),
            "resume from": "no further action in this plan",
        }
        record["proof_report"] = {
            "validation proof": "uv run pytest tests/test_check_planning_surfaces.py",
            "proof achieved now": "validation and closure checks passed for the bounded slice.",
            'evidence for "proof achieved" state': "archive gate and planning checks were satisfied.",
        }
        record["intent_satisfaction"] = {
            "original intent": "Keep scope clear.",
            "was original intent fully satisfied?": "yes",
            "evidence of intent satisfaction": "the bounded slice landed and the lane-level evidence was recorded.",
            "unsolved intent passed to": "none",
        }
        record["closure_check"] = {
            "slice status": "bounded slice complete",
            "larger-intent status": "closed",
            "closure decision": "archive-and-close",
            "why this decision is honest": "the bounded slice and larger intent are both complete.",
            "evidence carried forward": "proof and intent satisfaction both show the lane is closed.",
            "reopen trigger": "none",
        }
    installer_mod._write_execplan_record(record_path=path, record=record)


def _write_review_record(path: Path) -> None:
    installer_mod._write_review_record(
        record_path=path,
        record={
            "kind": "planning-review/v1",
            "title": "Review Alpha",
            "goal": ["Check one narrow planning boundary."],
            "scope": [".agentic-workspace/planning/reviews/"],
            "non_goals": ["No implementation work."],
            "review_mode": {
                "mode": "review-promotion",
                "review question": "should this review stay live?",
                "default finding cap": "2",
                "inputs inspected first": "reviews README",
            },
            "review_method": {
                "commands used": "uv run pytest packages/planning/tests/test_installer.py -q",
                "evidence sources": "local review artifact",
            },
            "references": [],
            "findings": [
                {
                    "title": "stale residue",
                    "summary": "the review should shrink after promotion.",
                    "evidence": "the artifact is no longer the only durable owner.",
                    "risk if unchanged": "review residue grows into a parallel archive.",
                    "suggested action": "move durable residue into a structured record.",
                    "confidence": "high",
                    "source": "static-analysis",
                    "promotion target": ".agentic-workspace/planning/state.toml (roadmap)",
                    "promotion trigger": "when the finding is confirmed",
                    "post-remediation note shape": "shrink",
                }
            ],
            "recommendation": {
                "promote": "yes",
                "defer": "no",
                "dismiss": "no",
            },
            "retention": {
                "closeout shape": "shrink",
                "trigger": "after the finding is promoted into planning state",
                "proof surface": "canonical review record plus promoted planning residue",
            },
            "validation_commands": ["uv run pytest packages/planning/tests/test_installer.py -q"],
            "drift_log": ["2026-04-23: Review created."],
        },
    )


def _minimal_execplan(status: str = "in-progress") -> str:
    execution_run = (
        "- Run status: completed\n"
        "- Executor: bounded external executor\n"
        "- Handoff source: agentic-planning handoff --format json\n"
        "- What happened: implemented the bounded checker update and returned compact residue.\n"
        "- Scope touched: scripts/check/check_planning_surfaces.py\n"
        "- Changed surfaces: scripts/check/check_planning_surfaces.py\n"
        "- Validations run: uv run pytest tests/test_check_planning_surfaces.py\n"
        "- Result for continuation: no further delegated execution needed for this bounded slice.\n"
        "- Next step: archive the plan.\n"
        if status in {"completed", "done", "closed"}
        else "- Run status: not-run-yet\n"
        "- Executor: pending\n"
        "- Handoff source: agentic-planning handoff --format json\n"
        "- What happened: pending delegated execution.\n"
        "- Scope touched: scripts/check/check_planning_surfaces.py\n"
        "- Changed surfaces: none yet; execution has not changed files.\n"
        "- Validations run: pending\n"
        "- Result for continuation: return compact residue after the first bounded run.\n"
        "- Next step: execute the bounded checker update.\n"
    )
    finished_run_review = (
        "- Review status: completed\n"
        "- Scope respected: yes\n"
        "- Proof status: satisfied\n"
        "- Intent served: yes\n"
        "- Config compliance: respected checked-in and local config for the bounded slice.\n"
        "- Misinterpretation risk: low\n"
        "- Follow-on decision: archive-and-close\n"
        if status in {"completed", "done", "closed"}
        else "- Review status: pending\n"
        "- Scope respected: pending\n"
        "- Proof status: pending\n"
        "- Intent served: pending\n"
        "- Config compliance: pending\n"
        "- Misinterpretation risk: pending\n"
        "- Follow-on decision: pending\n"
    )
    execution_summary = (
        "- Outcome delivered: Added one bounded planning improvement.\n"
        "- Validation confirmed: uv run pytest tests/test_check_planning_surfaces.py\n"
        "- Follow-on routed to: none; slice complete\n"
        "- Post-work posterity capture: preserve the checker-boundary reminder in planning docs and route any durable subsystem learning to canonical docs or Memory only when that module is installed and is the right owner.\n"
        "- Resume from: no further action in this plan\n"
        if status in {"completed", "done", "closed"}
        else "- Outcome delivered: not completed yet\n"
        "- Validation confirmed: pending\n"
        "- Follow-on routed to: none yet\n"
        "- Post-work posterity capture: pending\n"
        "- Resume from: current milestone\n"
    )
    proof_report = (
        "\n## Proof Report\n\n"
        "- Validation proof: uv run pytest tests/test_check_planning_surfaces.py\n"
        "- Proof achieved now: validation and closure checks passed for the bounded slice.\n"
        '- Evidence for "Proof achieved" state: archive gate and planning checks were satisfied.\n'
        if status in {"completed", "done", "closed"}
        else ""
    )
    intent_satisfaction = (
        "\n## Intent Satisfaction\n\n"
        "- Original intent: Keep scope clear.\n"
        "- Was original intent fully satisfied?: yes\n"
        "- Evidence of intent satisfaction: the bounded slice landed and the lane-level evidence was recorded.\n"
        "- Unsolved intent passed to: none\n"
        if status in {"completed", "done", "closed"}
        else ""
    )
    system_intent_alignment = (
        "\n## System Intent Alignment\n\n"
        "- Relevant system intent: Preserve larger user or product outcome separately from the bounded slice.\n"
        "- Slice shaping bias: Keep this slice small but route continuation explicitly.\n"
        "- Broader-lane validation question: Did this slice advance the parent lane rather than only local task completion?\n"
        "- Intent evidence source: .agentic-workspace/docs/system-intent-contract.md\n"
    )
    closure_check = (
        "\n## Closure Check\n\n"
        "- Slice status: bounded slice complete\n"
        "- Larger-intent status: closed\n"
        "- Closure decision: archive-and-close\n"
        "- Why this decision is honest: the bounded slice and larger intent are both complete.\n"
        "- Evidence carried forward: proof and intent satisfaction both show the lane is closed.\n"
        "- Reopen trigger: none\n"
        if status in {"completed", "done", "closed"}
        else "\n## Closure Check\n\n"
        "- Slice status: in progress\n"
        "- Larger-intent status: open\n"
        "- Closure decision: keep-active\n"
        "- Why this decision is honest: the active milestone has not closed yet.\n"
        "- Evidence carried forward: validation and completion criteria are still pending.\n"
        "- Reopen trigger: finish the current milestone and reassess closure.\n"
    )
    durable_residue = (
        "\n## Durable Residue\n\n"
        "- Status: evidence_only\n"
        "- Learned constraint: no future-relevant learning beyond the archived proof record.\n"
        "- Motivation worth preserving: none beyond evidence-only archive.\n"
        "- Canonical owner now: archive\n"
        "- Promotion trigger: none\n"
        "- Retention after promotion: retain\n"
    )
    return f"""
# Plan Alpha

## Goal

- Keep scope clear.

## Non-Goals

- No runtime changes.

## Intent Continuity

- Larger intended outcome: Land plan alpha end to end.
- This slice completes the larger intended outcome: yes
- Continuation surface: none
- Parent lane: plan-alpha-lane

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Iterative Follow-Through

- What this slice enabled: Added one bounded planning improvement.
- Intentionally deferred: none
- Discovered implications: none yet
- Proof achieved now: validation remains pending until the current milestone closes.
- Validation still needed: run the bounded planning checker test before archive.
- Next likely slice: finish the current milestone and archive if no larger follow-on remains.

## Intent Interpretation

- Literal request: Keep scope clear.
- Inferred intended outcome: land one bounded planning improvement without widening the lane.
- Chosen concrete what: update the planning checker contract and validate it narrowly.
- Interpretation distance: low
- Review guidance: correct the slice if the implementation expands beyond the named planning checker surface.

## Execution Bounds

- Allowed paths: scripts/check/check_planning_surfaces.py
- Max changed files: 1
- Required validation commands: uv run pytest tests/test_check_planning_surfaces.py
- Ask-before-refactor threshold: stop before broad planning-surface refactors.
- Stop before touching: unrelated workspace or memory surfaces.

## Stop Conditions

- Stop when: the work needs broader planning-surface rereads than the named checker update.
- Escalate when boundary reached: the change no longer fits one bounded checker slice.
- Escalate on scope drift: additional owned surfaces are required.
- Escalate on proof failure: the named planning test stops proving the change.

## Context Budget

- Live working set: the active checker change, proof command, and closure state for this bounded slice.
- Recoverable later: broader planning doctrine and archived lane history can be reloaded from checked-in docs if needed.
- Externalize before shift: the exact next action, proof expectation, blocker state, and one scoped caution if the checker semantics change.
- Pre-work config pull: ask which repo or local config materially constrains this bounded slice and where those limits must show up in execution bounds, stop conditions, or review.
- Pre-work memory pull: ask what durable planning guidance should be recovered before execution and which planning surface it concerns.
- Tiny resumability note: keep the warning-class boundary explicit if this slice is revisited later.
- Context-shift triggers: shift when proof lands, when leaving planning-surface work, or when a handoff/interruption stops the slice.

## Delegated Judgment

- Requested outcome: Keep scope clear.
- Hard constraints: Keep scope bounded to the promoted TODO item and its touched paths.
- Agent may decide locally: Bounded decomposition, validation tightening, and plan-local residue routing.
- Escalate when: The requested outcome, owned surface, time horizon, or meaningful validation story would change.

## Post-Decomposition Delegation

- Status: evaluated
- Decision rule: choose direct, exploration, implementation, validation, stronger review, or no safe route from the bounded slice.
- Route candidates: keep-local|delegate-exploration|delegate-implementation|delegate-validation|escalate-review|no-safe-route
- Required evidence: route, reason, quality risk, token-saving class, read-first refs, write scope, proof burden, stop conditions, and return contract.

## Capability Posture

- Execution class: mechanical-follow-through
- Recommended strength: weak
- Preferred location: either
- Delegation friendly: yes
- Strong external reasoning: avoid
- Why: the slice is bounded enough for cheaper follow-through once the contract is clear.

## Active Milestone

- ID: plan-alpha
- Status: {status}
- Scope: maintain planning discipline.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Add one checker.

## Blockers

- None.

## Touched Paths

- scripts/check/check_planning_surfaces.py

## Invariants

- Planning surfaces remain separate.

## Validation Commands

- uv run pytest tests/test_check_planning_surfaces.py

## Required Tools

- None.

## Completion Criteria

- Warning classes are emitted for known drift.

## Execution Run

{execution_run}

## Finished-Run Review

{finished_run_review}

## Delegation Outcome Feedback

- Route chosen: keep-local
- Route skipped reason: handoff would cost more than this one-file checker slice.
- Expected savings: none
- Actual friction: none
- Proof result: pending
- Quality concern: none
- Decomposition adjustment: none

## Execution Summary

{execution_summary}

{proof_report}
{intent_satisfaction}
{system_intent_alignment}
{closure_check}
{durable_residue}

## Drift Log

- 2026-04-04: Initial plan created.
""".format(
        status=status,
        execution_run=execution_run,
        finished_run_review=finished_run_review,
        execution_summary=execution_summary,
        proof_report=proof_report,
        intent_satisfaction=intent_satisfaction,
        system_intent_alignment=system_intent_alignment,
        closure_check=closure_check,
    )


def _minimal_execplan_with_required_tools(status: str = "in-progress") -> str:
    return _minimal_execplan(status=status).replace("## Required Tools\n\n- None.\n", "## Required Tools\n\n- browser\n- gh\n")


def _rename_like_execplan(*, status: str = "completed", with_reference_sweep: bool = False) -> str:
    plan = _minimal_execplan(status=status).replace("- Keep scope clear.", "- Rename the stale planning surface cleanly.")
    if with_reference_sweep:
        plan = plan.replace(
            "- uv run pytest tests/test_check_planning_surfaces.py",
            "- uv run pytest tests/test_check_planning_surfaces.py\n- rg old-planning-surface docs scripts",
            1,
        )
        plan = plan.replace(
            "- Validation confirmed: uv run pytest tests/test_check_planning_surfaces.py",
            "- Validation confirmed: uv run pytest tests/test_check_planning_surfaces.py; rg old-planning-surface docs scripts",
        )
    return plan


__all__ = [name for name in globals() if not name.startswith("__")]
