from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import repo_planning_bootstrap._render as render_module
import repo_planning_bootstrap.cli as planning_cli
import repo_planning_bootstrap.installer as installer_mod
from repo_planning_bootstrap._ownership import module_root as planning_module_root
from repo_planning_bootstrap.installer import (
    PLANNING_COMPATIBILITY_CONTRACT_FILES,
    PLANNING_LOWER_STABILITY_HELPER_FILES,
    REQUIRED_PAYLOAD_FILES,
    adopt_bootstrap,
    archive_execplan,
    collect_status,
    doctor_bootstrap,
    install_bootstrap,
    planning_handoff,
    planning_reconcile,
    planning_report,
    planning_summary,
    promote_todo_item_to_execplan,
    uninstall_bootstrap,
    upgrade_bootstrap,
    verify_payload,
)


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
            "handoff source": "agentic-planning-bootstrap handoff --format json",
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
        "- Handoff source: agentic-planning-bootstrap handoff --format json\n"
        "- What happened: implemented the bounded checker update and returned compact residue.\n"
        "- Scope touched: scripts/check/check_planning_surfaces.py\n"
        "- Changed surfaces: scripts/check/check_planning_surfaces.py\n"
        "- Validations run: uv run pytest tests/test_check_planning_surfaces.py\n"
        "- Result for continuation: no further delegated execution needed for this bounded slice.\n"
        "- Next step: archive the plan.\n"
        if status in {"completed", "done", "closed"}
        else "- Run status: not-run-yet\n"
        "- Executor: pending\n"
        "- Handoff source: agentic-planning-bootstrap handoff --format json\n"
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

## Execution Summary

{execution_summary}

{proof_report}
{intent_satisfaction}
{system_intent_alignment}
{closure_check}

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


def test_install_bootstrap_copies_required_files(tmp_path: Path) -> None:
    result = install_bootstrap(target=tmp_path)
    capability_fit_doc_path = tmp_path / ".agentic-workspace" / "docs" / "capability-aware-execution.md"
    routing_doc_path = tmp_path / ".agentic-workspace" / "docs" / "routing-contract.md"
    execution_flow_doc_path = tmp_path / ".agentic-workspace" / "docs" / "execution-flow-contract.md"
    lifecycle_doc_path = tmp_path / ".agentic-workspace" / "docs" / "lifecycle-and-config-contract.md"
    extraction_doc_path = tmp_path / ".agentic-workspace" / "docs" / "extraction-and-discovery-contract.md"
    skill_readme_path = tmp_path / ".agentic-workspace" / "planning" / "skills" / "README.md"
    skill_registry_path = tmp_path / ".agentic-workspace" / "planning" / "skills" / "REGISTRY.json"
    skill_path = tmp_path / ".agentic-workspace" / "planning" / "skills" / "planning-autopilot" / "SKILL.md"
    intake_skill_path = tmp_path / ".agentic-workspace" / "planning" / "skills" / "planning-intake-upstream-task" / "SKILL.md"
    review_readme_path = tmp_path / ".agentic-workspace" / "planning" / "reviews" / "README.md"
    review_template_path = tmp_path / ".agentic-workspace" / "planning" / "reviews" / "TEMPLATE.md"
    review_record_template_path = tmp_path / ".agentic-workspace" / "planning" / "reviews" / "TEMPLATE.review.json"
    intake_doc_path = tmp_path / ".agentic-workspace" / "planning" / "upstream-task-intake.md"
    refinement_doc_path = tmp_path / ".agentic-workspace" / "planning" / "pre-ingestion-refinement.md"

    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / ".agentic-workspace/planning/state.toml").exists()
    assert not (tmp_path / ".agentic-workspace/planning/TODO.md").exists()
    assert not (tmp_path / ".agentic-workspace/planning/ROADMAP.md").exists()
    assert not (tmp_path / "TODO.md").exists()
    assert not (tmp_path / "ROADMAP.md").exists()
    assert capability_fit_doc_path.exists()
    assert routing_doc_path.exists()
    assert execution_flow_doc_path.exists()
    assert lifecycle_doc_path.exists()
    assert extraction_doc_path.exists()
    assert review_readme_path.exists()
    assert review_record_template_path.exists()
    assert not review_template_path.exists()
    assert intake_doc_path.exists()
    assert refinement_doc_path.exists()
    assert (tmp_path / ".agentic-workspace" / "planning" / "execplans" / "TEMPLATE.plan.json").exists()
    assert (tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json").exists()
    assert not (tmp_path / ".agentic-workspace" / "planning" / "scripts").exists()
    assert skill_readme_path.exists()
    assert skill_registry_path.exists()
    assert skill_path.exists()
    assert intake_skill_path.exists()
    assert not (tmp_path / "tools").exists()
    assert not (tmp_path / "scripts").exists()
    assert any(action.kind in {"copied", "created", "updated"} for action in result.actions)


def test_ownership_module_root_matches_workspace_ledger() -> None:
    assert planning_module_root("planning") == Path(".agentic-workspace/planning")


def test_planning_contract_file_shortlist_is_explicit() -> None:
    assert Path("AGENTS.template.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES
    assert Path(".agentic-workspace/docs/capability-aware-execution.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES
    assert Path(".agentic-workspace/docs/execution-flow-contract.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES
    assert Path(".agentic-workspace/docs/orchestrator-workflow-contract.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES
    assert Path(".agentic-workspace/docs/minimum-operating-model.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES
    assert Path(".agentic-workspace/planning/execplans/README.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES
    assert Path(".agentic-workspace/planning/reviews/README.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES
    assert Path(".agentic-workspace/planning/reviews/TEMPLATE.review.json") in PLANNING_COMPATIBILITY_CONTRACT_FILES
    assert Path(".agentic-workspace/planning/upstream-task-intake.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES
    assert Path(".agentic-workspace/planning/pre-ingestion-refinement.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES
    assert Path(".agentic-workspace/docs/routing-contract.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES
    assert Path(".agentic-workspace/planning/UPGRADE-SOURCE.toml") in PLANNING_LOWER_STABILITY_HELPER_FILES
    assert Path("tools/AGENT_QUICKSTART.md") not in REQUIRED_PAYLOAD_FILES
    assert Path("scripts/render_agent_docs.py") not in REQUIRED_PAYLOAD_FILES
    assert Path(".agentic-workspace/planning/scripts/render_agent_docs.py") not in REQUIRED_PAYLOAD_FILES
    assert set(PLANNING_COMPATIBILITY_CONTRACT_FILES).isdisjoint(PLANNING_LOWER_STABILITY_HELPER_FILES)
    assert set(PLANNING_COMPATIBILITY_CONTRACT_FILES) | set(PLANNING_LOWER_STABILITY_HELPER_FILES) == set(REQUIRED_PAYLOAD_FILES)


def test_adopt_bootstrap_preserves_existing_agents(tmp_path: Path) -> None:
    agents_path = tmp_path / "AGENTS.md"
    agents_path.write_text("repo-owned agents\n", encoding="utf-8")
    result = adopt_bootstrap(target=tmp_path)
    assert agents_path.read_text(encoding="utf-8") == "repo-owned agents\n"
    assert any(action.kind == "skipped" and action.path == agents_path for action in result.actions)


def test_adopt_bootstrap_docs_heavy_repo_preserves_root_surfaces_and_installs_helpers(tmp_path: Path) -> None:
    agents_path = tmp_path / "AGENTS.md"
    todo_path = tmp_path / ".agentic-workspace/planning/state.toml"
    roadmap_path = tmp_path / "ROADMAP.md"
    execplan_readme_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "README.md"
    contributor_playbook_path = tmp_path / "docs" / "contributor-playbook.md"
    maintainer_commands_path = tmp_path / "docs" / "maintainer-commands.md"

    _write(agents_path, "# Existing agents\n")
    _write(todo_path, "# Existing TODO\n")
    _write(roadmap_path, "# Existing Roadmap\n")
    _write(execplan_readme_path, "# Existing execution docs\n")
    _write(contributor_playbook_path, "# Existing contributor playbook\n")
    _write(maintainer_commands_path, "# Existing commands\n")

    result = adopt_bootstrap(target=tmp_path)

    assert agents_path.read_text(encoding="utf-8") == "# Existing agents\n"
    assert todo_path.read_text(encoding="utf-8") == "# Existing TODO\n"
    assert roadmap_path.read_text(encoding="utf-8") == "# Existing Roadmap\n"
    assert execplan_readme_path.read_text(encoding="utf-8") == "# Existing execution docs\n"
    assert contributor_playbook_path.read_text(encoding="utf-8") == "# Existing contributor playbook\n"
    assert maintainer_commands_path.read_text(encoding="utf-8") == "# Existing commands\n"
    assert (tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json").exists()
    assert (tmp_path / ".agentic-workspace" / "planning" / "skills" / "planning-autopilot" / "SKILL.md").exists()
    assert any(action.kind == "skipped" and action.path == agents_path for action in result.actions)
    assert any(action.kind == "skipped" and action.path == execplan_readme_path for action in result.actions)
    assert any(
        action.kind in {"copied", "created", "updated"}
        and action.path == tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json"
        for action in result.actions
    )
    assert not (tmp_path / "tools").exists()


def test_render_wrapper_install_does_not_ship_root_script_entrypoint(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    assert not (tmp_path / "scripts" / "render_agent_docs.py").exists()


def test_adopt_bootstrap_preserves_existing_manifest_in_partial_managed_state(tmp_path: Path) -> None:
    manifest_path = tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json"
    manifest_text = '{"bootstrap": {"first_reads": ["AGENTS.md", ".agentic-workspace/planning/state.toml"]}}\n'
    _write(manifest_path, manifest_text)

    result = adopt_bootstrap(target=tmp_path)

    assert manifest_path.read_text(encoding="utf-8") == manifest_text
    assert any(action.kind == "skipped" and action.path == manifest_path for action in result.actions)
    assert not (tmp_path / "tools").exists()


def test_adopt_bootstrap_leaves_memory_owned_surfaces_untouched(tmp_path: Path) -> None:
    memory_index_path = tmp_path / "memory" / "index.md"
    _write(memory_index_path, "# Existing memory index\n")

    result = adopt_bootstrap(target=tmp_path)

    assert memory_index_path.read_text(encoding="utf-8") == "# Existing memory index\n"
    assert not any(action.path == memory_index_path for action in result.actions)
    assert (tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json").exists()


def test_status_reports_missing_and_present_files(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    result = collect_status(target=tmp_path)
    assert any(action.kind == "present" for action in result.actions)


def test_status_command_routes_through_generated_adapter(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, str]] = []

    def fake_status_handler(args) -> int:
        calls.append((args.command, args.format, args.target))
        print('{"ok": true}')
        return 0

    monkeypatch.setitem(planning_cli._GENERATED_RUNTIME_HANDLERS, "planning.status.report", fake_status_handler)

    assert planning_cli.main(["status", "--target", str(tmp_path), "--format", "json"]) == 0

    assert json.loads(capsys.readouterr().out) == {"ok": True}
    assert calls == [("status", "json", str(tmp_path))]


def test_payload_filters_generated_artifacts(tmp_path: Path, monkeypatch) -> None:
    payload_root = tmp_path / "payload"
    _write(payload_root / "AGENTS.md", "agents\n")
    _write(
        payload_root / "scripts" / "render_agent_docs.py",
        (
            "import json\n\n"
            "from pathlib import Path\n\n"
            "def load_manifest():\n"
            "    manifest_path = Path(__file__).resolve().parents[1] / '.agentic-workspace' / 'planning' / 'agent-manifest.json'\n"
            "    return json.loads(manifest_path.read_text(encoding='utf-8'))\n\n"
            "def render_quickstart(_manifest):\n"
            "    return 'generated file\\n'\n\n"
            "def render_routing(_manifest):\n"
            "    return 'generated file\\n'\n"
        ),
    )
    _write(payload_root / "scripts" / "__pycache__" / "render_agent_docs.cpython-314.pyc", "junk\n")

    monkeypatch.setattr(installer_mod, "payload_root", lambda: payload_root)

    files = installer_mod.list_payload_files()
    assert "scripts/__pycache__/render_agent_docs.cpython-314.pyc" not in files

    result = install_bootstrap(target=tmp_path / "target")
    assert not (tmp_path / "target" / "scripts" / "__pycache__").exists()
    assert any(action.path == tmp_path / "target" / "AGENTS.md" for action in result.actions)


def test_verify_payload_generated_docs_match_manifest() -> None:
    result = verify_payload()
    manifest_actions = [action for action in result.actions if action.path.name == "agent-manifest.json"]
    assert manifest_actions
    assert any(action.kind == "current" for action in manifest_actions)


def test_verify_payload_reports_contract_surface_shortlists() -> None:
    result = verify_payload()

    assert any(
        action.path.name == "agent-manifest.json"
        and action.kind == "current"
        and "compatibility contract files:" in action.detail
        and "AGENTS.md" in action.detail
        and ".agentic-workspace/planning/agent-manifest.json" in action.detail
        for action in result.actions
    )
    assert any(
        action.path.name == "agent-manifest.json"
        and action.kind == "current"
        and "lower-stability helper files:" in action.detail
        and ".agentic-workspace/planning/UPGRADE-SOURCE.toml" in action.detail
        for action in result.actions
    )


def test_bootstrap_review_readme_includes_canonical_review_portfolio() -> None:
    text = (installer_mod.payload_root() / ".agentic-workspace" / "planning" / "reviews" / "README.md").read_text(encoding="utf-8")

    assert "## Canonical Review Portfolio" in text
    assert "`contract-integrity`" in text
    assert "future contributors would reasonably trust" in text
    assert "promise-vs-enforcement gaps" in text
    assert "`maintainer-workflow`" in text
    assert "`source-payload-install`" in text
    assert "`doctrine-refresh`" in text
    assert "`review-promotion`" in text
    assert "Use one primary review mode per artifact." in text
    assert "default finding cap" in text
    assert "long-horizon doctrine still matches current dogfooding reality" in text
    assert "## Improvement-targeting workflow" in text
    assert "record the intended post-remediation note shape" in text
    assert "Repeated findings that work needed stronger execution capability than expected" in text
    assert "make future work cheaper to execute" in text
    assert "Last doctrinal review" in text


def test_bootstrap_review_template_includes_mode_and_cap_fields() -> None:
    record = json.loads(
        (installer_mod.payload_root() / ".agentic-workspace" / "planning" / "reviews" / "TEMPLATE.review.json").read_text(encoding="utf-8")
    )

    assert record["kind"] == "planning-review/v1"
    assert "review_mode" in record
    assert "findings" in record


def test_bootstrap_capability_aware_execution_doc_defines_categories() -> None:
    text = (installer_mod.payload_root() / ".agentic-workspace" / "docs" / "capability-aware-execution.md").read_text(encoding="utf-8")

    assert "# Capability-Aware Execution" in text
    assert "## Operating Stance" in text
    assert "## Task-Shape Dimensions" in text
    assert "### Cheap Direct Execution" in text
    assert "### Stronger Planning First" in text
    assert "### Autopilot-Suitable" in text
    assert "### Delegation-Friendly" in text
    assert "### Stop And Escalate" in text
    assert "## Silent Shaping And Non-Interference" in text
    assert "## Bounded Initiative And Scope Expansion" in text
    assert "## Complexity-Reduction Feedback" in text
    assert "automatic capability selection" in text
    assert "Prefer changing the work shape over interrupting execution with capability advice." in text
    assert "make more future tasks safe for cheaper execution paths" in text
    assert "task-shape based" in text
    assert "Intent is sticky" in text
    assert "do not silently replace the requested outcome" in text
    assert "improve means locally" in text
    assert "do not rewrite ends locally" in text
    assert "present it as a promotion or escalation decision" in text


def test_bootstrap_delegated_judgment_doc_is_part_of_contract() -> None:
    text = (installer_mod.payload_root() / ".agentic-workspace" / "docs" / "execution-flow-contract.md").read_text(encoding="utf-8")

    assert "# Execution and Milestone Flow Contract" in text
    assert "## Delegated Judgment" in text
    assert "Agents have bounded initiative to" in text
    assert "Escalation is required" in text
    assert "The path is blocked" in text
    assert Path(".agentic-workspace/docs/execution-flow-contract.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES


def test_bootstrap_environment_recovery_contract_is_part_of_payload() -> None:
    text = (installer_mod.payload_root() / ".agentic-workspace" / "docs" / "execution-flow-contract.md").read_text(encoding="utf-8")

    assert "agentic-workspace report" in text
    assert "summary" in text
    assert "recover current context" in text
    assert "### Resumable Execution" in text
    assert "Environment and State Recovery" in text
    assert "agentic-workspace report" in text
    assert "agentic-workspace doctor --target ./repo" in text
    assert Path(".agentic-workspace/docs/execution-flow-contract.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES


def test_planning_readme_and_bootstrap_agents_describe_required_follow_on_routing() -> None:
    readme_text = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
    bootstrap_agents_text = (installer_mod.payload_root() / "AGENTS.template.md").read_text(encoding="utf-8")
    execplans_readme_text = (installer_mod.payload_root() / ".agentic-workspace" / "planning" / "execplans" / "README.md").read_text(
        encoding="utf-8"
    )
    manifest_payload = json.loads(
        (installer_mod.payload_root() / ".agentic-workspace" / "planning" / "agent-manifest.json").read_text(encoding="utf-8")
    )
    quickstart_text = render_module.render_quickstart(manifest_payload)
    routing_text = render_module.render_routing(manifest_payload)

    assert "Execplans now treat four fields as first-class" in readme_text
    assert "clear the matched queue residue in the same pass" in readme_text
    assert "`Required Continuation`" in readme_text
    assert "`Iterative Follow-Through`" in readme_text
    assert "`Execution Summary`" in readme_text
    assert "Required continuation for an unfinished larger intended outcome" in readme_text
    assert "Keep this file thin." in bootstrap_agents_text
    assert "agentic-workspace start --format json" in bootstrap_agents_text
    assert "agentic-workspace preflight --format json" in bootstrap_agents_text
    assert "agentic-workspace summary --format json" in bootstrap_agents_text
    assert "agentic-workspace defaults --section startup --format json" in bootstrap_agents_text
    assert (
        "Use `agentic-workspace config --target . --format json` when the configured entrypoint, posture, or workflow obligations matter."
        in bootstrap_agents_text
    )
    assert "Read package-local `AGENTS.md` only for the package being edited." in bootstrap_agents_text
    assert "## When Needed" not in bootstrap_agents_text
    assert "remove or archive the matched queue residue in the same pass" in execplans_readme_text
    assert "## Authority Table" not in quickstart_text
    assert "## Escalation Table" not in quickstart_text
    assert "Generated, non-authoritative helper" in quickstart_text
    assert "agentic-workspace start --format json" in quickstart_text
    assert "agentic-workspace preflight --format json" in quickstart_text
    assert "## Routing Table" not in routing_text
    assert "## Compact Queries" in routing_text
    assert "agentic-workspace start --format json" in routing_text
    assert "Iterative carry-forward belongs under `## Iterative Follow-Through`" in execplans_readme_text
    assert any(
        "Use `agentic-workspace summary --format json` first when active planning recovery or compact ownership state is the question."
        in item
        for item in manifest_payload["bootstrap"]["first_queries"]
    )
    assert any(
        "Read `agentic-workspace summary --format json` first when planning recovery or ownership boundary review is the question." in item
        for item in manifest_payload["bootstrap"]["conditional_reads"]
    )
    assert any(
        "Read `agentic-workspace summary --format json` first when planning recovery or ownership boundary review is the question." in item
        for item in manifest_payload["bootstrap"]["conditional_reads"]
    )
    assert any(
        "prefer `agentic-workspace defaults --section startup --format json` and `agentic-workspace config --target ./repo --format json` before broader prose"
        in item
        for item in manifest_payload["bootstrap"]["conditional_reads"]
    )
    assert any("Ask compact startup queries first" in item for item in manifest_payload["bootstrap"]["tiny_safe_model"])
    assert manifest_payload["bootstrap"]["boundary_triggered_escalation"][0]["boundary"] == "workspace"
    assert manifest_payload["bootstrap"]["top_level_capabilities"][1]["module"] == "planning"
    assert any("clear the matched queue residue in the same pass" in item for item in manifest_payload["bootstrap"]["completion_reminders"])
    assert "generated static adapter" in quickstart_text
    assert "Do not bulk-read all planning surfaces" in quickstart_text
    assert "clear the matched queue residue in the same pass" not in quickstart_text


def test_bootstrap_execplan_readme_includes_memory_synergy_guidance() -> None:
    text = (installer_mod.payload_root() / ".agentic-workspace" / "planning" / "execplans" / "README.md").read_text(encoding="utf-8")

    assert "prefer borrowing durable context from the smallest relevant memory note or canonical doc" in text
    assert "Repeated background prose in plans is a missing-synergy signal" in text
    assert "promote it into memory or canonical docs" in text
    assert "must not silently widen the requested outcome" in text
    assert "Continuation surface" in text
    assert "larger intended outcome" in text
    assert "Required follow-on for the larger intended outcome" in text
    assert "Activation trigger" in text
    assert "## Iterative Follow-Through" in text
    assert "What this slice enabled" in text
    assert "## Delegated Judgment" in text
    assert "Requested outcome" in text
    assert "Agent may decide locally" in text
    assert "required tools" in text
    assert "Native runtime artifacts such as `implementation_plan.md`" in text
    assert "## Execution Summary" in text
    assert "Outcome delivered" in text


def test_bootstrap_execution_summary_contract_is_part_of_payload() -> None:
    text = (installer_mod.payload_root() / ".agentic-workspace" / "docs" / "execution-flow-contract.md").read_text(encoding="utf-8")
    assert Path(".agentic-workspace/docs/execution-flow-contract.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES
    assert "Execution Summary" in text
    assert "Execution Summary" in text
    assert "Captured Outcome" in text
    assert "Unfinished Detail" in text
    assert "Stable References" in text


def test_bootstrap_iterative_follow_through_contract_is_part_of_payload() -> None:
    text = (installer_mod.payload_root() / ".agentic-workspace" / "docs" / "execution-flow-contract.md").read_text(encoding="utf-8")

    assert "## Iterative Follow-Through" in text
    assert "Follow-Through Section" in text
    assert "residue" in text
    assert Path(".agentic-workspace/docs/execution-flow-contract.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES


def test_bootstrap_intent_contract_is_part_of_payload() -> None:
    text = (installer_mod.payload_root() / ".agentic-workspace" / "docs" / "standing-intent-contract.md").read_text(encoding="utf-8")
    assert Path(".agentic-workspace/docs/standing-intent-contract.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES
    assert "Standing Intent Contract" in text
    assert "active_directional_intent" in text
    assert "repo_doctrine" in text
    assert "config_policy" in text
    assert "agentic-workspace report" in text
    assert Path(".agentic-workspace/docs/standing-intent-contract.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES


def test_bootstrap_resumable_execution_contract_is_part_of_payload() -> None:
    text = (installer_mod.payload_root() / ".agentic-workspace" / "docs" / "execution-flow-contract.md").read_text(encoding="utf-8")
    assert Path(".agentic-workspace/docs/execution-flow-contract.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES
    assert "Resumable Execution" in text
    assert "agentic-workspace report" in text
    assert Path(".agentic-workspace/docs/execution-flow-contract.md") in PLANNING_COMPATIBILITY_CONTRACT_FILES


def test_doctor_reports_contract_surface_shortlists(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)

    result = doctor_bootstrap(target=tmp_path)

    assert any(
        action.path == tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json"
        and action.kind == "current"
        and "compatibility contract files:" in action.detail
        and "AGENTS.md" in action.detail
        and ".agentic-workspace/docs/capability-aware-execution.md" in action.detail
        and ".agentic-workspace/planning/execplans/TEMPLATE.plan.json" in action.detail
        and ".agentic-workspace/planning/upstream-task-intake.md" in action.detail
        for action in result.actions
    )
    assert any(
        action.path == tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json"
        and action.kind == "current"
        and "lower-stability helper files:" in action.detail
        and ".agentic-workspace/planning/UPGRADE-SOURCE.toml" in action.detail
        for action in result.actions
    )


def test_doctor_ignores_generic_repo_readme_without_startup_claims(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("planning proof repo\n", encoding="utf-8")
    install_bootstrap(target=tmp_path)

    result = doctor_bootstrap(target=tmp_path)

    assert not any(action.path == tmp_path / "README.md" and "agent-startup guidance" in action.detail for action in result.actions)


def test_doctor_flags_partial_readme_startup_guidance(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    (tmp_path / "README.md").write_text(
        "# Repo\n\nFor agent maintainers, the primary operating path is `AGENTS.md`.\n",
        encoding="utf-8",
    )

    result = doctor_bootstrap(target=tmp_path)

    assert not any(action.path == tmp_path / "README.md" and "agent-startup guidance" in action.detail for action in result.actions)


def test_doctor_does_not_flag_starter_todo_for_milestone_word_in_hygiene_rules(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)

    result = doctor_bootstrap(target=tmp_path)

    assert not any(
        action.path == tmp_path / ".agentic-workspace/planning/state.toml" and "milestone-level narrative" in action.detail
        for action in result.actions
    )


def test_doctor_guides_older_execplans_toward_current_contract_sections(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: the active plan still needs migration hints for the newer contract shape.
""",
    )
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Next Candidate Queue

- Candidate alpha; promote when maintained report signal appears.

## Reopen Conditions

- Reopen when a queue or report signals new work.
""",
    )
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    _write(
        plan_path,
        """
# Plan Alpha

## Goal

- Keep scope clear.

## Non-Goals

- No runtime changes.

## Intent Continuity

- Larger intended outcome: Land plan alpha end to end.
- This slice completes the larger intended outcome: yes
- Continuation surface: none

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Active Milestone

- Status: in-progress
- Scope: maintain planning discipline.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Add one checker.

## Blockers

Long narrative status update line one.
Long narrative status update line two.
Long narrative status update line three.
Long narrative status update line four.
Long narrative status update line five.
Long narrative status update line six.
Long narrative status update line seven.
Long narrative status update line eight.
Long narrative status update line nine.
Long narrative status update line ten.
Long narrative status update line eleven.

## Touched Paths

## Invariants

## Validation Commands

## Completion Criteria

-

## Drift Log

- 2026-04-01: Decision one.
- 2026-04-02: Decision two.
- 2026-04-03: Decision three.
- 2026-04-04: Decision four.
- 2026-04-05: Decision five.
- 2026-04-06: Decision six.
""",
    )

    result = doctor_bootstrap(target=tmp_path)

    assert any(warning["warning_class"] == "execplan_structure_drift" for warning in result.warnings)
    assert any(
        action.kind == "suggested fix"
        and action.path == plan_path
        and ".agentic-workspace/docs/execution-flow-contract.md" in action.detail
        and ".agentic-workspace/planning/execplans/README.md" in action.detail
        for action in result.actions
    )


def test_verify_payload_flags_missing_collaboration_safe_template_guidance(tmp_path: Path, monkeypatch) -> None:
    payload_root = tmp_path / "payload"
    _write(payload_root / "AGENTS.md", "# Agent Instructions\n")
    _write(payload_root / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(payload_root / "ROADMAP.md", "# Roadmap\n")
    _write(payload_root / ".agentic-workspace" / "planning" / "execplans" / "README.md", "# Execution Plans\n")
    _write(payload_root / ".agentic-workspace" / "planning" / "execplans" / "TEMPLATE.md", "# Plan Title\n")
    _write(payload_root / ".agentic-workspace" / "planning" / "execplans" / "archive" / "README.md", "# Archive\n")
    _write(payload_root / ".agentic-workspace" / "planning" / "UPGRADE-SOURCE.toml", 'source_type = "git"\n')
    _write(payload_root / ".agentic-workspace" / "planning" / "agent-manifest.json", "{}\n")
    _write(
        payload_root / ".agentic-workspace" / "planning" / "scripts" / "render_agent_docs.py",
        (
            "def render_quickstart(_manifest):\n"
            '    return "generated file\\n"\n\n'
            "def render_routing(_manifest):\n"
            '    return "generated file\\n"\n'
        ),
    )
    _write(payload_root / ".agentic-workspace" / "planning" / "scripts" / "check" / "check_planning_surfaces.py", "print('ok')\n")
    _write(payload_root / ".agentic-workspace" / "planning" / "scripts" / "check" / "check_maintainer_surfaces.py", "print('ok')\n")
    _write(
        payload_root / "scripts" / "render_agent_docs.py",
        (
            "import json\n\n"
            "from pathlib import Path\n\n"
            "def load_manifest():\n"
            "    manifest_path = Path(__file__).resolve().parents[1] / '.agentic-workspace' / 'planning' / 'agent-manifest.json'\n"
            "    return json.loads(manifest_path.read_text(encoding='utf-8'))\n\n"
            "def render_quickstart(_manifest):\n"
            "    return 'generated file\\n'\n\n"
            "def render_routing(_manifest):\n"
            "    return 'generated file\\n'\n"
        ),
    )
    _write(payload_root / "scripts" / "check" / "check_planning_surfaces.py", "print('ok')\n")
    _write(payload_root / "scripts" / "check" / "check_maintainer_surfaces.py", "print('ok')\n")
    _write(payload_root / "tools" / "agent-manifest.json", "{}\n")
    _write(payload_root / "tools" / "AGENT_QUICKSTART.md", "generated file\n")
    _write(payload_root / "tools" / "AGENT_ROUTING.md", "generated file\n")

    monkeypatch.setattr(installer_mod, "payload_root", lambda: payload_root)

    result = verify_payload()

    assert any(
        action.path == payload_root / ".agentic-workspace" / "planning" / "execplans" / "TEMPLATE.md"
        and action.kind == "manual review"
        and "collaboration-safe template wording" in action.detail
        for action in result.actions
    )


def test_upgrade_bootstrap_overwrites_managed_files_but_preserves_root_surfaces(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    agents_path = tmp_path / "AGENTS.md"
    checker_path = tmp_path / ".agentic-workspace" / "planning" / "UPGRADE-SOURCE.toml"
    skill_path = tmp_path / ".agentic-workspace" / "planning" / "skills" / "planning-autopilot" / "SKILL.md"

    agents_path.write_text("repo-owned agents\n", encoding="utf-8")
    checker_path.write_text("stale checker\n", encoding="utf-8")
    skill_path.write_text("stale skill\n", encoding="utf-8")

    result = upgrade_bootstrap(target=tmp_path)

    assert agents_path.read_text(encoding="utf-8") == "repo-owned agents\n"
    assert "stale checker" not in checker_path.read_text(encoding="utf-8")
    assert "stale skill" not in skill_path.read_text(encoding="utf-8")
    assert any(action.kind == "skipped" and action.path == agents_path for action in result.actions)
    assert any(action.kind == "overwritten" and action.path == checker_path for action in result.actions)
    assert any(action.kind == "overwritten" and action.path == skill_path for action in result.actions)


def test_upgrade_bootstrap_legacy_standalone_install_adds_managed_helpers_without_overwriting_root_surfaces(tmp_path: Path) -> None:
    _write(tmp_path / "AGENTS.md", "legacy repo-owned agents\n")
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Next Candidate Queue

- Candidate alpha

## Reopen Conditions

- Reopen when a queue or report signals new work.
""",
    )
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "README.md", "# Execution Plans\n")
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "TEMPLATE.md", "# Plan Title\n")
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive" / "README.md", "# Archive\n")
    _write(tmp_path / ".agentic-workspace" / "planning" / "reviews" / "README.md", "# Reviews\n")
    _write(tmp_path / ".agentic-workspace" / "planning" / "reviews" / "TEMPLATE.md", "# Review Template\n")
    _write(tmp_path / ".agentic-workspace" / "planning" / "upstream-task-intake.md", "# Upstream Task Intake\n")

    result = upgrade_bootstrap(target=tmp_path)

    assert (tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json").exists()
    assert not (tmp_path / "tools").exists()
    assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == "legacy repo-owned agents\n"
    assert any(action.kind == "skipped" and action.path == tmp_path / "AGENTS.md" for action in result.actions)
    assert any(
        action.kind == "copied" and action.path == tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json"
        for action in result.actions
    )


def test_upgrade_bootstrap_recovers_partial_managed_state_without_overwriting_root_surfaces(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    agents_path = tmp_path / "AGENTS.md"
    manifest_path = tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json"
    routing_path = tmp_path / ".agentic-workspace" / "planning" / "UPGRADE-SOURCE.toml"

    agents_path.write_text("repo-owned agents\n", encoding="utf-8")
    manifest_path.unlink()
    routing_path.unlink()

    result = upgrade_bootstrap(target=tmp_path)

    assert manifest_path.exists()
    assert routing_path.exists()
    assert agents_path.read_text(encoding="utf-8") == "repo-owned agents\n"
    assert any(action.kind == "copied" and action.path == manifest_path for action in result.actions)
    assert any(action.kind == "copied" and action.path == routing_path for action in result.actions)
    assert any(action.kind == "skipped" and action.path == agents_path for action in result.actions)


def test_upgrade_bootstrap_preserves_unowned_root_todo_and_roadmap_files(tmp_path: Path) -> None:
    todo_path = tmp_path / "TODO.md"
    roadmap_path = tmp_path / "ROADMAP.md"
    todo_text = "# TODO\n\n## Personal Notes\n\n- Keep this user-owned file.\n"
    roadmap_text = "# ROADMAP\n\n## My Product Plan\n\n- Keep this user-owned file.\n"

    _write(todo_path, todo_text)
    _write(roadmap_path, roadmap_text)

    upgrade_bootstrap(target=tmp_path)

    assert todo_path.exists()
    assert roadmap_path.exists()
    assert todo_path.read_text(encoding="utf-8") == todo_text
    assert roadmap_path.read_text(encoding="utf-8") == roadmap_text
    assert (tmp_path / ".agentic-workspace/planning/state.toml").exists()


def test_upgrade_bootstrap_flags_managed_compatibility_views_for_manual_review(tmp_path: Path) -> None:
    todo_path = tmp_path / "TODO.md"
    roadmap_path = tmp_path / "ROADMAP.md"
    compat_notice = installer_mod._COMPATIBILITY_VIEW_NOTICE

    _write(todo_path, f"{compat_notice}\n# TODO\n")
    _write(roadmap_path, f"{compat_notice}\n# ROADMAP\n")

    result = upgrade_bootstrap(target=tmp_path)

    assert todo_path.exists()
    assert roadmap_path.exists()
    assert (tmp_path / ".agentic-workspace/planning/state.toml").exists()
    assert any(
        action.kind == "manual review" and action.path == todo_path and "delete manually if no longer needed" in action.detail
        for action in result.actions
    )
    assert any(
        action.kind == "manual review" and action.path == roadmap_path and "delete manually if no longer needed" in action.detail
        for action in result.actions
    )


def test_doctor_reports_stale_generated_routing_residue_for_partial_managed_state(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    routing_path = tmp_path / "tools" / "AGENT_ROUTING.md"
    routing_path.parent.mkdir(parents=True, exist_ok=True)
    routing_path.write_text("stale generated routing\n", encoding="utf-8")

    result = doctor_bootstrap(target=tmp_path)

    assert not any(action.path == routing_path for action in result.actions)


def test_uninstall_bootstrap_removes_pristine_files_and_keeps_modified_surfaces(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    agents_path = tmp_path / "AGENTS.md"
    checker_path = tmp_path / ".agentic-workspace" / "planning" / "UPGRADE-SOURCE.toml"
    quickstart_path = tmp_path / "tools" / "AGENT_QUICKSTART.md"
    skill_path = tmp_path / ".agentic-workspace" / "planning" / "skills" / "planning-autopilot" / "SKILL.md"

    agents_path.write_text("repo-owned agents\n", encoding="utf-8")

    result = uninstall_bootstrap(target=tmp_path)

    assert agents_path.exists()
    assert not checker_path.exists()
    assert not quickstart_path.exists()
    assert not skill_path.exists()
    assert any(action.kind == "manual review" and action.path == agents_path for action in result.actions)
    assert any(action.kind == "removed" and action.path == checker_path for action in result.actions)
    assert any(action.kind == "removed" and action.path == skill_path for action in result.actions)


def test_promote_todo_item_to_execplan_scaffolds_plan_and_updates_todo(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: direct-item
  Status: in-progress
  Surface: direct
  Why now: this thread needs a bounded execution contract.
  Next Action: sketch the first implementation step.
  Done When: the bounded change is implemented and validated.
""",
    )

    result = promote_todo_item_to_execplan("direct-item", target=tmp_path)
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "direct-item.md"
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "direct-item.plan.json"

    assert not plan_path.exists()
    assert record_path.exists()
    record = json.loads(record_path.read_text(encoding="utf-8"))
    todo_text = (tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8")
    assert record["kind"] == "planning-execplan/v1"
    assert record["active_milestone"]["id"] == "direct-item"
    assert record["intent_continuity"]["this slice completes the larger intended outcome"] == "yes"
    assert record["intent_continuity"]["continuation surface"] == "none"
    assert record["required_continuation"]["required follow-on for the larger intended outcome"] == "no"
    assert record["delegated_judgment"]["requested outcome"] == "this thread needs a bounded execution contract."
    assert "Surface: .agentic-workspace/planning/execplans/direct-item.md" in todo_text
    assert "Next Action:" not in todo_text
    assert "Done When:" not in todo_text
    assert any(action.kind == "created" and action.path == record_path for action in result.actions)


def test_promote_todo_item_to_execplan_supports_compact_toml_active_items(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = [
  { id = "compact-item", status = "in-progress", surface = "direct", why_now = "this thread needs the package command to dogfood compact state.", next_action = "promote the compact item.", done_when = "the command creates a plan." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )

    result = promote_todo_item_to_execplan("compact-item", target=tmp_path)
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "compact-item.plan.json"

    assert record_path.exists()
    record = json.loads(record_path.read_text(encoding="utf-8"))
    state_text = (tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8")
    assert record["kind"] == "planning-execplan/v1"
    assert record["active_milestone"]["id"] == "compact-item"
    assert record["delegated_judgment"]["requested outcome"] == "this thread needs the package command to dogfood compact state."
    assert 'surface = ".agentic-workspace/planning/execplans/compact-item.plan.json"' in state_text
    assert "next_action" not in state_text
    assert "done_when" not in state_text
    assert any(action.kind == "created" and action.path == record_path for action in result.actions)


def test_promote_todo_item_to_execplan_accepts_bom_prefixed_compact_toml(tmp_path: Path) -> None:
    state_path = tmp_path / ".agentic-workspace/planning/state.toml"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_bytes(
        b"\xef\xbb\xbf"
        + b"""
[todo]
active_items = [
  { id = "bom-compact", status = "in-progress", surface = "direct", why_now = "Windows-authored TOML should still be parsed." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
"""
    )

    result = promote_todo_item_to_execplan("bom-compact", target=tmp_path)
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "bom-compact.plan.json"

    assert record_path.exists()
    assert any(action.kind == "created" and action.path == record_path for action in result.actions)


def test_promote_todo_item_to_execplan_refuses_existing_execplan_surface(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: this item is already routed through an execplan.
""",
    )
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md", _minimal_execplan())

    result = promote_todo_item_to_execplan("plan-alpha", target=tmp_path)

    assert any(action.kind == "manual review" and "already points at" in action.detail for action in result.actions)


def test_promote_todo_item_to_execplan_refuses_existing_compact_execplan_surface(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = [
  { id = "plan-alpha", status = "in-progress", surface = ".agentic-workspace/planning/execplans/plan-alpha.plan.json", why_now = "this item is already routed through an execplan." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    _write_execplan_record(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json",
        status="in-progress",
    )

    result = promote_todo_item_to_execplan("plan-alpha", target=tmp_path)

    assert any(action.kind == "manual review" and "already points at" in action.detail for action in result.actions)


def test_planning_cli_dogfoods_compact_state_for_summary_promote_and_archive(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = [
  { id = "compact-cli", status = "in-progress", surface = "direct", why_now = "prove package commands use compact state.", next_action = "promote through the CLI.", done_when = "archive through the CLI." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )

    assert planning_cli.main(["summary", "--target", str(tmp_path), "--format", "json"]) == 0
    summary_payload = json.loads(capsys.readouterr().out)
    assert summary_payload["todo"]["active_items"][0]["id"] == "compact-cli"
    assert summary_payload["execution_readiness"]["status"] == "active-item-without-execplan"

    assert planning_cli.main(["promote-to-plan", "compact-cli", "--target", str(tmp_path), "--format", "json"]) == 0
    promote_payload = json.loads(capsys.readouterr().out)
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "compact-cli.plan.json"
    state_text = (tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8")
    assert promote_payload["actions"][0]["kind"] == "created"
    assert record_path.exists()
    assert 'surface = ".agentic-workspace/planning/execplans/compact-cli.plan.json"' in state_text
    assert "next_action" not in state_text
    assert "done_when" not in state_text

    _write_execplan_record(record_path, item_id="compact-cli", status="completed")
    assert planning_cli.main(["archive-plan", "compact-cli", "--target", str(tmp_path), "--apply-cleanup", "--format", "json"]) == 0
    archive_payload = json.loads(capsys.readouterr().out)
    archived_record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive" / "compact-cli.plan.json"
    state_text = (tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8")
    assert any(action["kind"] == "archived" and action["path"].endswith("compact-cli.plan.json") for action in archive_payload["actions"])
    assert archived_record_path.exists()
    assert not record_path.exists()
    assert "compact-cli" not in state_text


def test_archive_execplan_moves_completed_plan(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Reopen Conditions

- Reopen when a queue or report signals new work.
""",
    )
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json"
    _write_execplan_record(record_path, status="completed")

    result = archive_execplan("plan-alpha", target=tmp_path)
    archived_record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive" / "plan-alpha.plan.json"

    assert archived_record_path.exists()
    assert not plan_path.exists()
    assert not record_path.exists()
    assert any(action.kind == "archived" and action.path == archived_record_path for action in result.actions)
    archived_record = json.loads(archived_record_path.read_text(encoding="utf-8"))
    assert archived_record["kind"] == "planning-execplan/v1"
    assert archived_record["proof_report"]["proof achieved now"] == "validation and closure checks passed for the bounded slice."


def test_planning_summary_prefers_canonical_execplan_record_when_markdown_stales(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: keep the canonical sidecar authoritative.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json"
    _write_execplan_record(record_path, status="in-progress")

    summary = planning_summary(target=tmp_path)

    assert summary["planning_record"]["requested_outcome"] == "this item needs a bounded execution contract."
    assert summary["planning_record"]["next_action"] == "add one checker."
    assert summary["planning_record"]["task"]["surface"] == ".agentic-workspace/planning/execplans/plan-alpha.md"
    assert summary["planning_record"]["system_intent_alignment"]["relevant system intent"] == (
        "Preserve larger user or product outcome separately from the bounded slice."
    )
    assert summary["machine_first_planning"]["status"] == "canonical-active"
    assert summary["machine_first_planning"]["active_canonical_count"] == 1
    assert summary["machine_first_planning"]["active_markdown_fallback_count"] == 0
    assert summary["machine_first_planning"]["canonical_active_execplans"] == [".agentic-workspace/planning/execplans/plan-alpha.plan.json"]


def test_planning_summary_and_handoff_expose_structured_execplan_references(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: keep explicit references queryable for continuation and handoff.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    _write_execplan_record(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json",
        references=[
            {
                "kind": "issue",
                "target": "#280",
                "role": "related-work",
                "label": "Structured references",
            },
            {
                "kind": "file",
                "target": "packages/planning/src/repo_planning_bootstrap/installer.py",
                "role": "implementation-target",
                "locator": "L2000-L2100",
            },
        ],
    )

    summary = planning_summary(target=tmp_path)
    handoff = planning_handoff(target=tmp_path)

    assert summary["planning_record"]["references"] == [
        {
            "kind": "issue",
            "target": "#280",
            "role": "related-work",
            "label": "Structured references",
        },
        {
            "kind": "file",
            "target": "packages/planning/src/repo_planning_bootstrap/installer.py",
            "role": "implementation-target",
            "locator": "L2000-L2100",
        },
    ]
    assert "#280" in summary["active_contract"]["minimal_refs"]
    assert "packages/planning/src/repo_planning_bootstrap/installer.py" in summary["active_contract"]["minimal_refs"]
    assert handoff["handoff_contract"]["references"][0]["target"] == "#280"
    assert handoff["handoff_contract"]["references"][1]["role"] == "implementation-target"


def test_planning_summary_and_handoff_project_review_residue_from_structured_references(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: keep review residue queryable without rereading full review artifacts.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    _write_execplan_record(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json",
        references=[
            {
                "kind": "review",
                "target": ".agentic-workspace/planning/reviews/review-alpha.review.json",
                "role": "review-target",
                "label": "Review Alpha",
            }
        ],
    )
    _write_review_record(tmp_path / ".agentic-workspace" / "planning" / "reviews" / "review-alpha.review.json")

    summary = planning_summary(target=tmp_path, profile="compact")
    handoff = planning_handoff(target=tmp_path)

    assert summary["planning_record"]["review_residue"] == [
        {
            "kind": "review",
            "target": ".agentic-workspace/planning/reviews/review-alpha.review.json",
            "role": "review-target",
            "label": "Review Alpha",
            "title": "Review Alpha",
            "finding_count": 1,
            "finding_titles": ["stale residue"],
            "promotion_targets": [".agentic-workspace/planning/state.toml (roadmap)"],
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
        }
    ]
    assert handoff["handoff_contract"]["review_residue"][0]["target"] == ".agentic-workspace/planning/reviews/review-alpha.review.json"
    assert handoff["handoff_contract"]["review_residue"][0]["finding_titles"] == ["stale residue"]
    assert handoff["handoff_contract"]["review_residue"][0]["retention"]["closeout shape"] == "shrink"


def test_upgrade_backfills_canonical_review_records(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    review_path = tmp_path / ".agentic-workspace" / "planning" / "reviews" / "review-alpha.md"
    review_path.write_text(
        """
# Review Alpha

## Goal

- Check one narrow planning boundary.

## Scope

- `.agentic-workspace/planning/reviews/`

## Non-Goals

- No implementation work.

## Review Mode

- Mode: review-promotion
- Review question: should this review stay live?
- Default finding cap: 2
- Inputs inspected first: reviews README

## Review Method

- Commands used: uv run pytest packages/planning/tests/test_installer.py -q
- Evidence sources: local review artifact

## Findings

### Finding: stale residue

- Summary: the review should shrink after promotion.
- Evidence: the artifact is no longer the only durable owner.
- Risk if unchanged: review residue grows into a parallel archive.
- Suggested action: move durable residue into a structured record.
- Confidence: high
- Source: static-analysis
- Promotion target: `.agentic-workspace/planning/state.toml (roadmap)`
- Promotion trigger: when the finding is confirmed
- Post-remediation note shape: shrink

## Recommendation

- Promote: yes
- Defer: no
- Dismiss: no

## Validation / Inspection Commands

- uv run pytest packages/planning/tests/test_installer.py -q

## Drift Log

- 2026-04-23: Review created.
""".strip()
        + "\n",
        encoding="utf-8",
    )

    upgrade_bootstrap(target=tmp_path)

    record_path = tmp_path / ".agentic-workspace" / "planning" / "reviews" / "review-alpha.review.json"
    assert record_path.exists()
    payload = json.loads(record_path.read_text(encoding="utf-8"))
    assert payload["kind"] == "planning-review/v1"
    assert payload["title"] == "Review Alpha"
    assert payload["review_mode"]["mode"] == "review-promotion"
    assert payload["findings"][0]["title"] == "stale residue"
    assert payload["retention"]["closeout shape"] == "shrink"


def test_archive_execplan_blocks_unfinished_larger_intent_without_continuation_surface(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    _write(
        plan_path,
        _minimal_execplan(status="completed").replace(
            "- This slice completes the larger intended outcome: yes", "- This slice completes the larger intended outcome: no"
        ),
    )

    result = archive_execplan("plan-alpha", target=tmp_path)

    assert plan_path.exists()
    assert any(warning["warning_class"] == "archive_missing_intent_continuity" for warning in result.warnings)
    assert any(
        action.kind == "manual review" and action.path == plan_path and "Continuation surface" in action.detail for action in result.actions
    )


def test_archive_execplan_blocks_missing_required_follow_on_when_parent_intent_is_unfinished(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    _write(
        plan_path,
        _minimal_execplan(status="completed")
        .replace("- This slice completes the larger intended outcome: yes", "- This slice completes the larger intended outcome: no")
        .replace("- Continuation surface: none", "- Continuation surface: `ROADMAP.md` candidate `next-slice`"),
    )

    result = archive_execplan("plan-alpha", target=tmp_path)

    assert plan_path.exists()
    assert any(warning["warning_class"] == "archive_missing_required_follow_on" for warning in result.warnings)
    assert any(
        action.kind == "manual review" and action.path == plan_path and "Required Continuation" in action.detail
        for action in result.actions
    )


def test_archive_execplan_blocks_missing_execution_summary(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    _write(
        plan_path,
        _minimal_execplan(status="completed").replace(
            "- Outcome delivered: Added one bounded planning improvement.",
            "- Outcome delivered: not completed yet",
        ),
    )

    result = archive_execplan("plan-alpha", target=tmp_path)

    assert plan_path.exists()
    assert any(warning["warning_class"] == "archive_missing_execution_summary" for warning in result.warnings)
    assert any(
        action.kind == "manual review" and action.path == plan_path and "Execution Summary" in action.detail for action in result.actions
    )


def test_archive_execplan_requires_post_work_posterity_capture(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    _write(
        plan_path,
        _minimal_execplan(status="completed").replace(
            (
                "- Post-work posterity capture: preserve the checker-boundary reminder in planning docs and route any durable subsystem "
                "learning to canonical docs or Memory only when that module is installed and is the right owner."
            ),
            "- Post-work posterity capture: pending",
        ),
    )

    result = archive_execplan("plan-alpha", target=tmp_path)

    assert plan_path.exists()
    assert any(warning["warning_class"] == "archive_missing_execution_summary" for warning in result.warnings)
    assert any(
        action.kind == "manual review"
        and action.path == plan_path
        and "what should survive this slice and where it belongs" in action.detail
        for action in result.actions
    )


def test_archive_execplan_blocks_missing_proof_report(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    plan = _minimal_execplan(status="completed").split("\n## Proof Report\n\n", 1)[0] + "\n"
    _write(plan_path, plan)

    result = archive_execplan("plan-alpha", target=tmp_path)

    assert plan_path.exists()
    assert any(warning["warning_class"] == "archive_missing_proof_report" for warning in result.warnings)
    assert any(action.kind == "manual review" and action.path == plan_path and "Proof Report" in action.detail for action in result.actions)


def test_archive_execplan_blocks_incomplete_intent_satisfaction(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    completed = _minimal_execplan(status="completed")
    proof_section = completed.split("\n## Proof Report\n\n", 1)[1].split("\n## Intent Satisfaction\n\n", 1)[0]
    plan = (
        completed.split("\n## Proof Report\n\n", 1)[0]
        + "\n## Proof Report\n\n"
        + proof_section
        + "\n## Intent Satisfaction\n\n"
        + "- Original intent: Keep scope clear.\n"
        + "- Was original intent fully satisfied?: no\n"
        + "- Evidence of intent satisfaction: the lane still has open follow-on work.\n"
        + "- Unsolved intent passed to: .agentic-workspace/planning/execplans/local-only-residue-via-git-exclude.md\n"
        + "\n## Closure Check\n\n"
        + "- Slice status: bounded slice complete\n"
        + "- Larger-intent status: closed\n"
        + "- Closure decision: archive-and-close\n"
        + "- Why this decision is honest: placeholder contradiction for test coverage.\n"
        + "- Evidence carried forward: intent and proof sections remain present.\n"
        + "- Reopen trigger: none\n"
        + "\n"
    )
    _write(plan_path, plan)

    result = archive_execplan("plan-alpha", target=tmp_path)

    assert plan_path.exists()
    assert any(
        warning["warning_class"] in {"archive_missing_intent_satisfaction", "archive_intent_not_fully_satisfied"}
        for warning in result.warnings
    )
    assert any(
        action.kind == "manual review"
        and action.path == plan_path
        and ("Intent Satisfaction" in action.detail or "archive-and-close" in action.detail or "larger-intent closure" in action.detail)
        and (
            "intent_satisfaction.was original intent fully satisfied?" in action.detail
            or "closure_check.larger-intent status" in action.detail
        )
        for action in result.actions
    )


def test_archive_execplan_refusal_names_supported_closure_values(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    _write(
        plan_path,
        _minimal_execplan(status="completed")
        .replace("- Slice status: bounded slice complete", "- Slice status: all bounded slices complete")
        .replace("- Closure decision: archive-and-close", "- Closure decision: close-lane"),
    )

    result = archive_execplan("plan-alpha", target=tmp_path)

    assert plan_path.exists()
    assert any(warning["warning_class"] == "archive_missing_closure_check" for warning in result.warnings)
    assert any(
        action.kind == "manual review"
        and action.path == plan_path
        and "closure_check.slice status" in action.detail
        and "complete" in action.detail
        and "completed" in action.detail
        and "bounded slice complete" in action.detail
        for action in result.actions
    )


def test_archive_execplan_refusal_names_supported_closure_decisions(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    _write(
        plan_path,
        _minimal_execplan(status="completed").replace("- Closure decision: archive-and-close", "- Closure decision: close-lane"),
    )

    result = archive_execplan("plan-alpha", target=tmp_path)

    assert plan_path.exists()
    assert any(warning["warning_class"] == "archive_missing_closure_check" for warning in result.warnings)
    assert any(
        action.kind == "manual review"
        and action.path == plan_path
        and "closure_check.closure decision" in action.detail
        and "archive-and-close" in action.detail
        and "archive-but-keep-lane-open" in action.detail
        for action in result.actions
    )


def test_archive_plan_prepare_closeout_dry_run_returns_valid_patch(tmp_path: Path, capsys) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json"
    _write_execplan_record(record_path, status="completed")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record.pop("intent_satisfaction")
    record.pop("closure_check")
    record.pop("closeout_distillation", None)
    installer_mod._write_execplan_record(record_path=record_path, record=record)

    assert (
        planning_cli.main(["archive-plan", "plan-alpha", "--target", str(tmp_path), "--prepare-closeout", "--dry-run", "--format", "json"])
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    text = json.dumps(payload)

    assert payload["warnings"] == []
    assert any(action["kind"] == "would update" and "prepared closeout patch" in action["detail"] for action in payload["actions"])
    assert "archive-and-close" in text
    assert "intent_satisfaction" in text
    assert "closeout_distillation" in text
    assert "next command" in text
    assert record_path.exists()
    assert "intent_satisfaction" not in json.loads(record_path.read_text(encoding="utf-8"))


def test_archive_plan_prepare_closeout_archives_without_manual_json_repair(tmp_path: Path, capsys) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = [
  { id = "plan-alpha", status = "completed", surface = ".agentic-workspace/planning/execplans/plan-alpha.plan.json" },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json"
    _write_execplan_record(record_path, status="completed")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record.pop("intent_satisfaction")
    record.pop("closure_check")
    record.pop("closeout_distillation", None)
    installer_mod._write_execplan_record(record_path=record_path, record=record)

    assert (
        planning_cli.main(
            [
                "archive-plan",
                "plan-alpha",
                "--target",
                str(tmp_path),
                "--prepare-closeout",
                "--apply-cleanup",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    archived_record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive" / "plan-alpha.plan.json"
    archived = json.loads(archived_record_path.read_text(encoding="utf-8"))

    assert payload["warnings"] == []
    assert any(action["kind"] == "updated" and "prepared normalized closeout fields" in action["detail"] for action in payload["actions"])
    assert any(action["kind"] == "archived" for action in payload["actions"])
    assert archived["intent_satisfaction"]["was original intent fully satisfied?"] == "yes"
    assert archived["closure_check"]["closure decision"] == "archive-and-close"
    assert archived["closeout_distillation"]["buckets"]["discard"][0]["owner"] == "discard"
    assert not record_path.exists()


def test_archive_plan_prepare_closeout_handles_open_parent_lane(tmp_path: Path, capsys) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json"
    _write_execplan_record(record_path, status="completed")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["intent_continuity"]["this slice completes the larger intended outcome"] = "no"
    record["intent_continuity"]["continuation surface"] = ".agentic-workspace/planning/state.toml"
    record["required_continuation"] = {
        "required follow-on for the larger intended outcome": "yes",
        "owner surface": ".agentic-workspace/planning/state.toml",
        "activation trigger": "when fresh product-compression pressure appears",
    }
    record.pop("intent_satisfaction")
    record.pop("closure_check")
    record.pop("closeout_distillation", None)
    installer_mod._write_execplan_record(record_path=record_path, record=record)

    assert (
        planning_cli.main(
            [
                "archive-plan",
                "plan-alpha",
                "--target",
                str(tmp_path),
                "--prepare-closeout",
                "--closure-decision",
                "archive-but-keep-lane-open",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    archived_record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive" / "plan-alpha.plan.json"
    archived = json.loads(archived_record_path.read_text(encoding="utf-8"))

    assert payload["warnings"] == []
    assert archived["intent_satisfaction"]["was original intent fully satisfied?"] == "no"
    assert archived["intent_satisfaction"]["unsolved intent passed to"] == ".agentic-workspace/planning/state.toml"
    assert archived["closure_check"]["larger-intent status"] == "open"
    assert archived["closure_check"]["closure decision"] == "archive-but-keep-lane-open"
    assert archived["closeout_distillation"]["buckets"]["continuation"][0]["owner"] == ".agentic-workspace/planning/state.toml"


def test_archive_execplan_allows_partial_intent_when_continuation_is_explicit(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    _write(
        plan_path,
        _minimal_execplan(status="completed")
        .replace("- This slice completes the larger intended outcome: yes", "- This slice completes the larger intended outcome: no")
        .replace("- Continuation surface: none", "- Continuation surface: .agentic-workspace/planning/state.toml")
        .replace("- Required follow-on for the larger intended outcome: no", "- Required follow-on for the larger intended outcome: yes")
        .replace("- Owner surface: none", "- Owner surface: .agentic-workspace/planning/state.toml")
        .replace("- Activation trigger: none", "- Activation trigger: when the next bounded slice for the lane is activated")
        .replace("- Was original intent fully satisfied?: yes", "- Was original intent fully satisfied?: no")
        .replace(
            "- Evidence of intent satisfaction: the bounded slice landed and the lane-level evidence was recorded.",
            "- Evidence of intent satisfaction: the bounded slice landed, but the larger lane still has required continuation.",
        )
        .replace("- Unsolved intent passed to: none", "- Unsolved intent passed to: .agentic-workspace/planning/state.toml")
        .replace("- Larger-intent status: closed", "- Larger-intent status: partial")
        .replace("- Closure decision: archive-and-close", "- Closure decision: archive-but-keep-lane-open")
        .replace(
            "- Why this decision is honest: the bounded slice and larger intent are both complete.",
            "- Why this decision is honest: the bounded slice is complete, but the larger lane remains open in checked-in planning.",
        )
        .replace(
            "- Evidence carried forward: proof and intent satisfaction both show the lane is closed.",
            "- Evidence carried forward: proof shows the slice is complete and the continuation owner is explicit.",
        )
        .replace(
            "- Reopen trigger: none",
            "- Reopen trigger: reopen when the next bounded lane slice is activated from .agentic-workspace/planning/state.toml",
        ),
    )

    result = archive_execplan("plan-alpha", target=tmp_path)
    archived_record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive" / "plan-alpha.plan.json"

    assert archived_record_path.exists()
    assert not plan_path.exists()
    assert not result.warnings


def test_archive_execplan_blocks_missing_delegated_judgment(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    _write(
        plan_path,
        _minimal_execplan(status="completed").replace(
            "## Delegated Judgment\n\n"
            "- Requested outcome: Keep scope clear.\n"
            "- Hard constraints: Keep scope bounded to the promoted TODO item and its touched paths.\n"
            "- Agent may decide locally: Bounded decomposition, validation tightening, and plan-local residue routing.\n"
            "- Escalate when: The requested outcome, owned surface, time horizon, or meaningful validation story would change.\n\n",
            "",
        ),
    )

    result = archive_execplan("plan-alpha", target=tmp_path)

    assert plan_path.exists()
    assert any(warning["warning_class"] == "archive_missing_delegated_judgment" for warning in result.warnings)
    assert any(
        action.kind == "manual review" and action.path == plan_path and "Delegated Judgment" in action.detail for action in result.actions
    )


def test_archive_execplan_blocks_rename_like_work_without_reference_sweep(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    _write(plan_path, _rename_like_execplan())

    result = archive_execplan("plan-alpha", target=tmp_path)

    assert plan_path.exists()
    assert any(warning["warning_class"] == "archive_missing_closure_check" for warning in result.warnings)
    assert any(
        action.kind == "manual review" and action.path == plan_path and "stale-reference sweep" in action.detail
        for action in result.actions
    )


def test_archive_execplan_allows_rename_like_work_with_reference_sweep(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    _write(plan_path, _rename_like_execplan(with_reference_sweep=True))

    result = archive_execplan("plan-alpha", target=tmp_path)
    archived_record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive" / "plan-alpha.plan.json"

    assert archived_record_path.exists()
    assert not plan_path.exists()
    assert any(action.kind == "archived" and action.path == archived_record_path for action in result.actions)


def test_archive_execplan_apply_cleanup_updates_completed_todo_and_roadmap(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: completed
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: already finished.
""",
    )
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Active Handoff

- Plan alpha is the current active package pass.

## Next Candidate Queue

- Candidate beta: promote when a report signals follow-on work.
""",
    )
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    _write(plan_path, _minimal_execplan(status="completed"))

    result = archive_execplan("plan-alpha", target=tmp_path, apply_cleanup=True)

    todo_text = (tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8")
    roadmap_text = (tmp_path / "ROADMAP.md").read_text(encoding="utf-8")
    assert "plan-alpha" not in todo_text
    assert "- No active work right now." in todo_text
    assert "- No active handoff right now." in roadmap_text
    assert any(action.kind == "updated" and action.path == tmp_path / ".agentic-workspace/planning/state.toml" for action in result.actions)
    assert any(action.kind == "updated" and action.path == tmp_path / "ROADMAP.md" for action in result.actions)


def test_archive_execplan_apply_cleanup_removes_active_todo_pointer_to_same_plan(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Now

- ID: bounded-delegated-judgment-contract
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/bounded-delegated-judgment-contract-2026-04-09.md
  Why now: finish the bounded contract update.

## Action

- Complete `bounded-delegated-judgment-contract`, then archive it and return the active queue to empty.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "bounded-delegated-judgment-contract-2026-04-09.md"
    _write(plan_path, _minimal_execplan(status="completed").replace("plan-alpha", "bounded-delegated-judgment-contract"))

    result = archive_execplan("bounded-delegated-judgment-contract-2026-04-09", target=tmp_path, apply_cleanup=True)

    todo_text = (tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8")
    assert "Surface: .agentic-workspace/planning/execplans/bounded-delegated-judgment-contract-2026-04-09.md" not in todo_text
    assert "- No active work right now." in todo_text
    assert (
        "Promote the next bounded candidate only when fresh repeated friction or explicit maintainer choice justifies activation."
        in todo_text
    )
    assert any(
        action.kind == "updated"
        and action.path == tmp_path / ".agentic-workspace/planning/state.toml"
        and "remove TODO item 'bounded-delegated-judgment-contract'" in action.detail
        for action in result.actions
    )
    assert (
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive" / "bounded-delegated-judgment-contract-2026-04-09.plan.json"
    ).exists()


def test_archive_execplan_apply_cleanup_handles_active_todo_without_blank_before_action_heading(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Now

- ID: intent-continuity-across-slices
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/intent-continuity-across-slices-2026-04-09.md
  Why now: keep larger intent alive across bounded slices.
## Action

- Complete `intent-continuity-across-slices`, then archive it and return the active queue to empty.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "intent-continuity-across-slices-2026-04-09.md"
    _write(plan_path, _minimal_execplan(status="completed").replace("plan-alpha", "intent-continuity-across-slices"))

    archive_execplan("intent-continuity-across-slices-2026-04-09", target=tmp_path, apply_cleanup=True)

    todo_text = (tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8")
    assert "## Action" in todo_text
    assert "- No active work right now." in todo_text
    assert "Complete `intent-continuity-across-slices`" not in todo_text


def test_archive_execplan_apply_cleanup_updates_compact_now_todo_shape(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Purpose

Repo-owned active queue for repository work.
Use `agentic-workspace summary --format json` first; keep this file as the repo-owned view of the active queue.

## Now
- front-door-defaults-tranche: Active - compress front-door docs and land the defaults contract.

## Action
- Execute `.agentic-workspace/planning/execplans/front-door-defaults-tranche-2026-04-09.md` and archive it once validation is complete.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "front-door-defaults-tranche-2026-04-09.md"
    _write(plan_path, _minimal_execplan(status="completed").replace("plan-alpha", "front-door-defaults-tranche"))

    result = archive_execplan("front-door-defaults-tranche-2026-04-09", target=tmp_path, apply_cleanup=True)

    todo_text = (tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8")
    assert "front-door-defaults-tranche: Active" not in todo_text
    assert ".agentic-workspace/planning/execplans/front-door-defaults-tranche-2026-04-09.md" not in todo_text
    assert "- No active work right now." in todo_text
    assert (
        "Promote the next bounded candidate only when fresh repeated friction or explicit maintainer choice justifies activation."
        in todo_text
    )
    assert any(action.kind == "updated" and action.path == tmp_path / ".agentic-workspace/planning/state.toml" for action in result.actions)


def test_archive_execplan_apply_cleanup_removes_compact_state_active_item_pointer(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = [
  { id = "#257", surface = ".agentic-workspace/planning/execplans/intent-validation-and-dangling-debt-2026-04-22.md", why_now = "Ship vendor-agnostic intent validation." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "intent-validation-and-dangling-debt-2026-04-22.md"
    _write(plan_path, _minimal_execplan(status="completed").replace("plan-alpha", "intent-validation-and-dangling-debt"))

    result = archive_execplan("intent-validation-and-dangling-debt-2026-04-22", target=tmp_path, apply_cleanup=True)

    state_text = (tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8")
    archived_path = (
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive" / "intent-validation-and-dangling-debt-2026-04-22.plan.json"
    )

    assert archived_path.exists()
    assert not plan_path.exists()
    assert "intent-validation-and-dangling-debt-2026-04-22.md" not in state_text
    assert "active_items = []" in state_text
    assert any(action.kind == "updated" and "remove TODO item '#257'" in action.detail for action in result.actions)


def test_archive_execplan_apply_cleanup_merges_compact_state_todo_and_roadmap_cleanup(tmp_path: Path) -> None:
    plan_ref = ".agentic-workspace/planning/execplans/planning-backed-dogfooding-guardrail.plan.json"
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        f"""
[todo]
active_items = [
  {{ id = "planning-backed-dogfooding-guardrail", status = "active", plan = "{plan_ref}" }},
]
queued_items = []

[roadmap]
lanes = [
  {{ id = "planning-backed-dogfooding-guardrail", title = "Planning backed dogfooding guardrail", priority = "first", issues = ["#322"] }},
  {{ id = "machine-first-planning-state", title = "Machine-first planning state and closeout hygiene", priority = "second", issues = ["#323", "#325"] }},
]
candidates = [
  {{ priority = "first", summary = "Planning backed dogfooding guardrail" }},
  {{ priority = "second", summary = "Machine-first planning state and closeout hygiene" }},
]
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / plan_ref
    _write_execplan_record(plan_path, item_id="planning-backed-dogfooding-guardrail", status="completed")

    result = archive_execplan("planning-backed-dogfooding-guardrail", target=tmp_path, apply_cleanup=True)

    state_text = (tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8")
    archived_path = tmp_path / ".agentic-workspace/planning/execplans/archive/planning-backed-dogfooding-guardrail.plan.json"

    assert archived_path.exists()
    assert not plan_path.exists()
    assert "active_items = []" in state_text
    assert "planning-backed-dogfooding-guardrail" not in state_text
    assert "Machine-first planning state and closeout hygiene" in state_text
    assert "machine-first-planning-state" in state_text
    assert any(action.kind == "updated" and "remove TODO item" in action.detail for action in result.actions)
    assert any(action.kind == "updated" and "roadmap lanes" in action.detail for action in result.actions)


def test_archive_execplan_cleanup_requires_all_stem_tokens_before_removing_state_lane(tmp_path: Path) -> None:
    plan_ref = ".agentic-workspace/planning/execplans/lower-trust-closeout-reconciliation-view.plan.json"
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        f"""
[todo]
active_items = [
  {{ id = "lower-trust-closeout-reconciliation-view", status = "active", plan = "{plan_ref}" }},
]
queued_items = []

[roadmap]
lanes = [
  {{ id = "machine-first-planning-state", title = "Machine-first planning state and closeout hygiene", priority = "first", issues = ["#323", "#325"] }},
  {{ id = "graceful-partial-compliance", title = "Graceful partial compliance and bypass trust", priority = "tenth", issues = ["#292"] }},
]
candidates = [
  {{ priority = "first", summary = "Machine-first planning state and closeout hygiene" }},
  {{ priority = "tenth", summary = "Graceful partial compliance and bypass trust" }},
]
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    plan_path = tmp_path / plan_ref
    _write_execplan_record(plan_path, item_id="lower-trust-closeout-reconciliation-view", status="completed")

    archive_execplan("lower-trust-closeout-reconciliation-view", target=tmp_path, apply_cleanup=True)

    state_text = (tmp_path / ".agentic-workspace/planning/state.toml").read_text(encoding="utf-8")
    assert "active_items = []" in state_text
    assert "machine-first-planning-state" in state_text
    assert "Graceful partial compliance and bypass trust" in state_text


def test_archive_execplan_apply_cleanup_removes_matching_candidate_queue_entry(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: workspace-result-contract
  Status: completed
  Surface: .agentic-workspace/planning/execplans/workspace-result-contract-2026-04-05.md
  Why now: already finished.
""",
    )
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Active Handoff

- Workspace result contract docs are complete.

## Next Candidate Queue

- Workspace result contract: define a shared adapter or result protocol for
    orchestrated module actions and warnings when more module families land.
- Shared tooling extraction: evaluate a common checker core when repeated maintenance friction appears.
""",
    )
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "workspace-result-contract-2026-04-05.md"
    _write(plan_path, _minimal_execplan(status="completed"))

    result = archive_execplan("workspace-result-contract-2026-04-05", target=tmp_path, apply_cleanup=True)

    roadmap_text = (tmp_path / "ROADMAP.md").read_text(encoding="utf-8")
    assert "Workspace result contract:" not in roadmap_text
    assert "Shared tooling extraction:" in roadmap_text
    assert any(
        action.kind == "updated" and action.path == tmp_path / "ROADMAP.md" and "Next Candidate Queue" in action.detail
        for action in result.actions
    )


def test_archive_execplan_apply_cleanup_removes_matching_candidate_lane_entry(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: memory-trust-lane
  Status: completed
  Surface: .agentic-workspace/planning/execplans/memory-trust-lane-2026-04-17.md
  Why now: already finished.
""",
    )
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Candidate Lanes

- Lane: Memory trust, usefulness, and cleanup ergonomics
  ID: memory-trust-usefulness-cleanup
  Priority: second
  Issues: #96, #97, #98, #99, #100
  Outcome: make Memory cheaper to trust, inspect, and clean up.
  Why later: wait until the current planning tranche lands.
  Promotion signal: promote when the current planning tranche completes.
  Suggested first slice: start with evidence-backed note trust states.
- Lane: Separate lane
  ID: separate-lane
  Priority: third
  Issues: #999
  Outcome: keep another candidate lane.
  Why later: later.
  Promotion signal: promote when later.
  Suggested first slice: later slice.
""",
    )
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "memory-trust-lane-2026-04-17.md"
    _write(plan_path, _minimal_execplan(status="completed").replace("plan-alpha", "memory-trust-lane"))

    result = archive_execplan("memory-trust-lane-2026-04-17", target=tmp_path, apply_cleanup=True)

    roadmap_text = (tmp_path / "ROADMAP.md").read_text(encoding="utf-8")
    assert "Memory trust, usefulness, and cleanup ergonomics" not in roadmap_text
    assert "Separate lane" in roadmap_text
    assert any(
        action.kind == "updated" and action.path == tmp_path / "ROADMAP.md" and "Candidate Lanes" in action.detail
        for action in result.actions
    )


def test_archive_execplan_cleanup_does_not_remove_unrelated_candidate_lane_from_generic_plan_stem(tmp_path: Path) -> None:
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: native-candidate-lanes
  Status: completed
  Surface: .agentic-workspace/planning/execplans/native-candidate-lanes-first-slice-2026-04-17.md
  Why now: already finished.
""",
    )
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Candidate Lanes

- Lane: Memory trust, usefulness, and cleanup ergonomics
  ID: memory-trust-usefulness-cleanup
  Priority: first
  Issues: #96, #97, #98, #99, #100
  Outcome: make Memory cheaper to trust, inspect, and clean up.
  Why now: Memory is the main remaining trust bottleneck.
  Promotion signal: promote when the next bounded slice is ready or when the candidate-lane slice lands.
  Suggested first slice: start with evidence-backed note trust states.
""",
    )
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "native-candidate-lanes-first-slice-2026-04-17.md"
    _write(plan_path, _minimal_execplan(status="completed").replace("plan-alpha", "native-candidate-lanes"))

    archive_execplan("native-candidate-lanes-first-slice-2026-04-17", target=tmp_path, apply_cleanup=True)

    roadmap_text = (tmp_path / "ROADMAP.md").read_text(encoding="utf-8")
    assert "Memory trust, usefulness, and cleanup ergonomics" in roadmap_text


def test_archive_execplan_preserves_explicit_roadmap_continuation_candidate(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Next Candidate Queue

- Intent continuity follow-through: promote when another larger user outcome
    needs multiple bounded slices so Planning can preserve unfinished parent
    intent across archival without re-explaining the purpose in chat.
""",
    )
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "intent-continuity-across-slices-2026-04-09.md"
    plan_text = (
        _minimal_execplan(status="completed")
        .replace("plan-alpha", "intent-continuity-across-slices")
        .replace(
            "- Continuation surface: none",
            "- Continuation surface: `ROADMAP.md` candidate `Intent continuity follow-through`",
        )
        .replace(
            "- This slice completes the larger intended outcome: yes",
            "- This slice completes the larger intended outcome: no",
        )
    )
    _write(plan_path, plan_text)

    archive_execplan("intent-continuity-across-slices-2026-04-09", target=tmp_path, apply_cleanup=True)

    roadmap_text = (tmp_path / "ROADMAP.md").read_text(encoding="utf-8")
    assert "Intent continuity follow-through:" in roadmap_text


def test_archive_execplan_without_cleanup_only_suggests_roadmap_followup(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Active Handoff

- Plan alpha is the current active package pass.
""",
    )
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md"
    _write(plan_path, _minimal_execplan(status="completed"))

    result = archive_execplan("plan-alpha", target=tmp_path)

    assert any(action.kind == "suggested fix" and action.path == tmp_path / "ROADMAP.md" for action in result.actions)
    assert any(warning["warning_class"] == "roadmap_archive_followup" for warning in result.warnings)


def test_archive_execplan_ignores_generic_roadmap_language(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Active Handoff

- The initial package pass is complete.

## Promotion Rules

- Promote an epic only when it is ready for active execution.
""",
    )
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "promotion-linkage-tuning-2026-04-05.md"
    _write(plan_path, _minimal_execplan(status="completed"))

    result = archive_execplan("promotion-linkage-tuning-2026-04-05", target=tmp_path)

    assert not any(action.kind == "suggested fix" and action.path == tmp_path / "ROADMAP.md" for action in result.actions)
    assert not any(warning["warning_class"] == "roadmap_archive_followup" for warning in result.warnings)


def test_planning_summary_reports_active_items_and_warnings(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: promote when maintained report signal appears.
""",
    )
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Next Candidate Queue

- Priority 1: Candidate alpha; promote when maintained report signal appears.

## Reopen Conditions

- Reopen when a queue or report signals new work.
""",
    )
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md", _minimal_execplan())

    summary = planning_summary(target=tmp_path)

    assert summary["kind"] == "planning-summary/v1"
    assert summary["schema"]["schema_version"] == "planning-summary-schema/v1"
    assert summary["schema"]["command"] == "agentic-workspace summary --format json --profile full"
    assert "planning_record" in summary["schema"]["shared_fields"]
    assert "machine_first_planning" in summary["schema"]["shared_fields"]
    assert "planning_surface_health" in summary["schema"]["shared_fields"]
    assert summary["todo"]["active_count"] == 1
    assert summary["execplans"]["active_count"] == 1
    assert summary["machine_first_planning"]["status"] == "markdown-fallback-active"
    assert summary["machine_first_planning"]["canonical_record_extension"] == ".plan.json"
    assert summary["machine_first_planning"]["active_canonical_count"] == 0
    assert summary["machine_first_planning"]["active_markdown_fallback_count"] == 1
    assert "sidecar is canonical" in summary["machine_first_planning"]["rule"]
    assert summary["execution_readiness"]["status"] == "planning-backed"
    assert summary["execution_readiness"]["broad_work_allowed"] is True
    assert summary["execution_readiness"]["recommendation"]["id"] == "continue-active-plan"
    assert summary["planning_surface_health"]["status"] == "clean"
    assert summary["planning_surface_health"]["warning_count"] == 0
    assert summary["planning_surface_health"]["recommended_next_action"] == "No planning-surface drift detected."
    assert summary["planning_record"]["status"] == "present"
    assert summary["planning_record"]["task"]["id"] == "plan-alpha"
    assert summary["planning_record"]["task"]["surface"] == ".agentic-workspace/planning/execplans/plan-alpha.md"
    assert summary["planning_record"]["next_action"] == "Add one checker."
    assert summary["planning_record"]["proof_expectations"] == ["uv run pytest tests/test_check_planning_surfaces.py"]
    assert summary["planning_record"]["closure_check"]["closure decision"] == "keep-active"
    assert summary["planning_record"]["system_intent_alignment"]["slice shaping bias"] == (
        "Keep this slice small but route continuation explicitly."
    )
    assert summary["planning_record"]["system_intent_alignment"]["broader-lane validation question"] == (
        "Did this slice advance the parent lane rather than only local task completion?"
    )
    assert summary["planning_record"]["agent_may_decide"] == (
        "Bounded decomposition, validation tightening, and plan-local residue routing."
    )
    assert summary["planning_record"]["escalate_when"] == (
        "The requested outcome, owned surface, time horizon, or meaningful validation story would change."
    )
    assert summary["planning_record"]["continuation_owner"] == ".agentic-workspace/planning/execplans/plan-alpha.md"
    assert summary["active_contract"]["status"] == "present"
    assert summary["active_contract"]["view_of"] == "planning_record"
    assert summary["active_contract"]["todo_item"]["id"] == "plan-alpha"
    assert summary["active_contract"]["intent"]["requested_outcome"] == "Keep scope clear."
    assert summary["active_contract"]["proof_expectations"] == ["uv run pytest tests/test_check_planning_surfaces.py"]
    assert summary["active_contract"]["tool_verification"]["status"] == "unspecified"
    assert summary["active_contract"]["tool_verification"]["required_tools"] == []
    assert summary["active_contract"]["touched_scope"] == ["scripts/check/check_planning_surfaces.py"]
    assert summary["active_contract"]["minimal_refs"] == [
        ".agentic-workspace/planning/state.toml",
        ".agentic-workspace/planning/execplans/plan-alpha.md",
    ]
    assert summary["resumable_contract"]["status"] == "present"
    assert summary["resumable_contract"]["view_of"] == "planning_record"
    assert summary["resumable_contract"]["current_next_action"] == "Add one checker."
    assert summary["resumable_contract"]["active_milestone"]["scope"] == "maintain planning discipline."
    assert summary["resumable_contract"]["completion_criteria"] == ["Warning classes are emitted for known drift."]
    assert summary["resumable_contract"]["tool_verification"]["status"] == "unspecified"
    assert summary["follow_through_contract"]["status"] == "present"
    assert summary["follow_through_contract"]["what_this_slice_enabled"] == "Added one bounded planning improvement."
    assert summary["follow_through_contract"]["validation_still_needed"] == ("run the bounded planning checker test before archive.")
    assert summary["follow_through_contract"]["larger_intended_outcome"] == "Land plan alpha end to end."
    assert summary["intent_interpretation_contract"]["status"] == "present"
    assert summary["intent_interpretation_contract"]["literal_request"] == "Keep scope clear."
    assert summary["intent_interpretation_contract"]["interpretation_distance"] == "low"
    assert summary["context_budget_contract"]["status"] == "present"
    assert summary["context_budget_contract"]["live_working_set"] == (
        "the active checker change, proof command, and closure state for this bounded slice."
    )
    assert summary["context_budget_contract"]["pre_work_config_pull"] == (
        "ask which repo or local config materially constrains this bounded slice and where those limits must show up in execution bounds, stop conditions, or review."
    )
    assert summary["context_budget_contract"]["pre_work_memory_pull"] == (
        "ask what durable planning guidance should be recovered before execution and which planning surface it concerns."
    )
    assert summary["context_budget_contract"]["tiny_resumability_note"] == (
        "keep the warning-class boundary explicit if this slice is revisited later."
    )
    assert summary["execution_run_contract"]["status"] == "present"
    assert summary["execution_run_contract"]["run_status"] == "not-run-yet"
    assert summary["execution_run_contract"]["handoff_source"] == "agentic-planning-bootstrap handoff --format json"
    assert summary["execution_run_contract"]["changed_surfaces"] == "none yet; execution has not changed files."
    assert summary["finished_run_review_contract"]["status"] == "present"
    assert summary["finished_run_review_contract"]["review_status"] == "pending"
    assert summary["finished_run_review_contract"]["config_compliance"] == "pending"
    assert summary["finished_run_review_contract"]["config_trust"] == "pending"
    assert summary["hierarchy_contract"]["status"] == "present"
    assert summary["hierarchy_contract"]["current_layer"] == "execution"
    assert summary["hierarchy_contract"]["parent_lane"]["id"] == "plan-alpha-lane"
    assert summary["hierarchy_contract"]["parent_lane"]["source"] == "execplan"
    assert summary["hierarchy_contract"]["active_chunk"]["milestone_id"] == "plan-alpha"
    assert summary["hierarchy_contract"]["active_chunk"]["next_action"] == "Add one checker."
    assert summary["hierarchy_contract"]["next_likely_chunk"] == (
        "finish the current milestone and archive if no larger follow-on remains."
    )
    assert summary["hierarchy_contract"]["proof_state"]["proof_expectations"] == ["uv run pytest tests/test_check_planning_surfaces.py"]
    assert summary["hierarchy_contract"]["closure_check"]["closure decision"] == "keep-active"
    assert summary["handoff_contract"]["status"] == "present"
    assert summary["handoff_contract"]["task"]["id"] == "plan-alpha"
    assert summary["handoff_contract"]["read_first"] == [
        ".agentic-workspace/planning/state.toml",
        ".agentic-workspace/planning/execplans/plan-alpha.md",
    ]
    assert summary["handoff_contract"]["pre_work_config_pull"] == (
        "ask which repo or local config materially constrains this bounded slice and where those limits must show up in execution bounds, stop conditions, or review."
    )
    assert summary["handoff_contract"]["pre_work_memory_pull"] == (
        "ask what durable planning guidance should be recovered before execution and which planning surface it concerns."
    )
    assert summary["handoff_contract"]["owned_write_scope"] == ["scripts/check/check_planning_surfaces.py"]
    assert summary["handoff_contract"]["context_budget"]["status"] == "present"
    assert summary["handoff_contract"]["execution_bounds"]["allowed paths"] == "scripts/check/check_planning_surfaces.py"
    assert summary["handoff_contract"]["stop_conditions"]["stop when"].startswith("the work needs broader")
    assert summary["handoff_contract"]["intent_interpretation"]["status"] == "present"
    assert summary["handoff_contract"]["system_intent_alignment"]["intent evidence source"] == (
        ".agentic-workspace/docs/system-intent-contract.md"
    )
    assert summary["handoff_contract"]["return_with"]["execution_run_fields"][0] == "run status"
    assert summary["handoff_contract"]["return_with"]["execution_run_fields"][5] == "changed surfaces"
    assert summary["handoff_contract"]["return_with"]["execution_summary_fields"][3] == "post-work posterity capture"
    assert summary["handoff_contract"]["worker_contract"]["allowed_execution_methods"][1] == "external cli or api"
    assert summary["roadmap"]["candidate_count"] == 1
    assert summary["roadmap"]["candidates"] == [
        {
            "priority": "1",
            "summary": "Candidate alpha; promote when maintained report signal appears.",
        }
    ]
    assert summary["system_intent"]["canonical_doc"] == ".agentic-workspace/docs/system-intent-contract.md"
    if summary["warning_count"] != 0:
        print(f"DEBUG: warnings found: {summary['warnings']}")
    assert summary["warning_count"] == 0


def test_planning_summary_compact_profile_trims_heavy_sections(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = [
  { id = "plan-alpha", status = "in-progress", surface = ".agentic-workspace/planning/execplans/plan-alpha.md", why_now = "keep compact startup cheap." }
]
queued_items = []

[roadmap]
lanes = [
  { id = "tracked-lane", title = "Tracked lane", priority = "first", issues = ["EXT-1"], outcome = "Keep tracked.", reason = "Needed.", promotion_signal = "Promote when needed.", suggested_first_slice = "Do the thing." },
]
candidates = [
  { priority = "first", summary = "Tracked lane" },
]
""",
    )
    _write_external_intent_evidence(
        tmp_path / ".agentic-workspace/planning/external-intent-evidence.json",
        items=[
            {
                "system": "manual",
                "id": "EXT-1",
                "title": "Tracked lane",
                "status": "open",
                "kind": "lane",
                "parent_id": "",
                "planning_residue_expected": "required",
            }
        ],
    )
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md", _minimal_execplan())

    summary = planning_summary(target=tmp_path, profile="compact")

    assert summary["profile"] == "compact"
    assert summary["schema"]["schema_version"] == "planning-summary-compact-schema/v1"
    assert summary["schema"]["command"] == "agentic-workspace summary --format json"
    assert summary["schema"]["full_profile_command"] == "agentic-workspace summary --format json --profile full"
    assert summary["machine_first_planning"]["status"] == "markdown-fallback-active"
    assert summary["machine_first_planning"]["active_markdown_fallback_count"] == 1
    assert summary["execution_readiness"]["status"] == "planning-backed"
    assert summary["execution_readiness"]["recommendation"]["id"] == "continue-active-plan"
    assert summary["planning_record"]["system_intent_alignment"]["relevant system intent"] == (
        "Preserve larger user or product outcome separately from the bounded slice."
    )
    assert summary["handoff_contract"]["system_intent_alignment"]["slice shaping bias"] == (
        "Keep this slice small but route continuation explicitly."
    )
    assert "candidate_lanes" not in summary["roadmap"]
    assert summary["roadmap"]["candidates"] == [{"priority": "first", "summary": "Tracked lane"}]
    assert "signals" not in summary["intent_validation_contract"]
    assert "external_evidence" not in summary["intent_validation_contract"]
    assert summary["ownership_review"]["repo_owned_surface_count"] >= 1
    assert "repo_owned_surfaces" not in summary["ownership_review"]
    assert "shared_fields" in summary["schema"]


def test_planning_summary_flags_roadmap_work_without_active_plan(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = []
queued_items = []

[roadmap]
lanes = [
  { id = "dogfooding-guardrail", title = "Dogfooding guardrail", priority = "first", issues = ["#322"], outcome = "Make planned work use planning.", reason = "A broad run bypassed active planning.", promotion_signal = "Promote before broad work.", suggested_first_slice = "Add readiness guardrail." },
]
candidates = [
  { priority = "first", summary = "Dogfooding guardrail" },
]
""",
    )

    summary = planning_summary(target=tmp_path, profile="compact")

    readiness = summary["execution_readiness"]
    assert readiness["status"] == "roadmap-needs-promotion"
    assert readiness["broad_work_allowed"] is False
    assert readiness["direct_work_allowed"] is True
    assert readiness["recommendation"]["id"] == "promote-before-broad-work"
    assert "Roadmap candidates are not execution authority" in readiness["rule"]


def test_planning_summary_reports_candidate_lanes(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Candidate Lanes

- Lane: Native candidate-lane queue for deferred grouped work
  ID: native-candidate-lanes
  Priority: highest
  Issues: #135
  Outcome: keep grouped deferred work repo-native and promotable without ad hoc queue prose.
  Why now: the ad hoc roadmap queue shape itself is the next planning friction.
  Promotion signal: promote when one thin native shape can replace the grouped queue prose.
  Suggested first slice: define the minimum lane fields and translate one real lane into them.
- Lane: Memory trust, usefulness, and cleanup ergonomics
  ID: memory-trust-usefulness-cleanup
  Priority: second
  Issues: #96, #97, #98, #99, #100
  Outcome: make Memory cheaper to trust, inspect, and clean up.
  Why later: wait until the planning slice lands.
  Promotion signal: promote when the candidate-lane slice lands.
  Suggested first slice: start with evidence-backed note trust states.
""",
    )

    summary = planning_summary(target=tmp_path)

    assert summary["roadmap"]["lane_count"] == 2
    assert summary["roadmap"]["candidate_count"] == 2
    assert summary["roadmap"]["candidates"] == [
        {"priority": "highest", "summary": "Native candidate-lane queue for deferred grouped work"},
        {"priority": "second", "summary": "Memory trust, usefulness, and cleanup ergonomics"},
    ]
    assert summary["roadmap"]["candidate_lanes"][0]["id"] == "native-candidate-lanes"
    assert summary["roadmap"]["candidate_lanes"][0]["issues"] == ["#135"]
    assert summary["roadmap"]["candidate_lanes"][0]["references"] == [{"kind": "issue", "target": "#135", "role": "related-work"}]
    assert summary["roadmap"]["candidate_lanes"][1]["issues"] == ["#96", "#97", "#98", "#99", "#100"]
    assert summary["roadmap"]["candidate_lanes"][1]["promotion_signal"] == "promote when the candidate-lane slice lands."


def test_planning_summary_normalizes_structured_lane_references_from_state_toml(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = [
  { id = "plan-alpha", status = "in-progress", surface = ".agentic-workspace/planning/execplans/plan-alpha.md", why_now = "keep lane references queryable above the execplan layer." }
]
queued_items = []

[roadmap]
lanes = [
  { id = "machine-first-planning-chain", title = "Machine-first planning chain", priority = "second", issues = ["#261", "#280"], references = [{ kind = "plan", target = ".agentic-workspace/planning/execplans/archive/machine-first-planning-chain-first-slice-2026-04-23.plan.json", role = "prior-proof", label = "First sidecar proof" }] }
]
candidates = [
  { priority = "second", summary = "Machine-first planning chain" }
]
""",
    )
    _write_execplan_record(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json",
        item_id="plan-alpha",
    )

    summary = planning_summary(target=tmp_path)

    assert summary["roadmap"]["candidate_lanes"][0]["references"] == [
        {
            "kind": "plan",
            "target": ".agentic-workspace/planning/execplans/archive/machine-first-planning-chain-first-slice-2026-04-23.plan.json",
            "role": "prior-proof",
            "label": "First sidecar proof",
        },
        {
            "kind": "issue",
            "target": "#261",
            "role": "related-work",
        },
        {
            "kind": "issue",
            "target": "#280",
            "role": "related-work",
        },
    ]


def test_planning_summary_reports_required_tools_when_execplan_declares_them(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: promote when maintained report signal appears.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md", _minimal_execplan_with_required_tools())

    summary = planning_summary(target=tmp_path)

    assert summary["planning_record"]["tool_verification"]["status"] == "required-tools-declared"
    assert summary["planning_record"]["tool_verification"]["required_tools"] == ["browser", "gh"]
    assert summary["active_contract"]["tool_verification"]["required_tools"] == ["browser", "gh"]
    assert summary["resumable_contract"]["tool_verification"]["required_tools"] == ["browser", "gh"]


def test_planning_report_derives_compact_module_state_from_summary(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: report-lane
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/report-lane.md
  Why now: derive compact module state.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n\n## Next Candidate Queue\n- Later lane.\n")
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "report-lane.md", _minimal_execplan())

    report = planning_report(target=tmp_path)

    assert report["kind"] == "planning-module-report/v1"
    assert report["schema"]["command"] == "agentic-planning-bootstrap report --format json"
    assert report["status"]["active_todo_count"] == 1
    assert report["status"]["active_execplan_count"] == 1
    assert report["status"]["roadmap_lane_count"] == 0
    assert report["next_action"]["summary"] == "Add one checker."
    assert report["system_intent"]["canonical_doc"] == ".agentic-workspace/docs/system-intent-contract.md"


def test_planning_report_flags_lower_trust_config_closeout(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: report-lane
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/report-lane.md
  Why now: derive compact module state.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n\n## Next Candidate Queue\n- Later lane.\n")
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "report-lane.md",
        _minimal_execplan()
        .replace("- Review status: pending\n", "- Review status: completed\n")
        .replace("- Scope respected: pending\n", "- Scope respected: yes\n")
        .replace("- Proof status: pending\n", "- Proof status: satisfied\n")
        .replace("- Intent served: pending\n", "- Intent served: yes\n")
        .replace(
            "- Config compliance: pending\n",
            "- Config compliance: bypassed repo-local config and left the resulting bounds underspecified.\n",
        )
        .replace("- Misinterpretation risk: pending\n", "- Misinterpretation risk: medium\n")
        .replace("- Follow-on decision: pending\n", "- Follow-on decision: repair-before-close\n"),
    )

    summary = planning_summary(target=tmp_path)
    report = planning_report(target=tmp_path)

    assert summary["finished_run_review_contract"]["config_trust"] == "lower-trust"
    assert "bypass" in summary["finished_run_review_contract"]["recommended_next_action"].lower()
    assert report["health"] == "attention-needed"
    assert any(finding["warning_class"] == "config_compliance_lower_trust" for finding in report["findings"])


def test_planning_summary_exposes_compact_planning_surface_health_when_not_clean(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: promote when maintained report signal appears.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md",
        _minimal_execplan().replace("## Delegated Judgment", "## Delegated Notes"),
    )

    summary = planning_summary(target=tmp_path)

    assert summary["planning_surface_health"]["status"] == "not-clean"
    assert summary["planning_surface_health"]["warning_count"] >= 1
    assert summary["planning_surface_health"]["warnings"][0]["warning_class"] == "execplan_structure_drift"
    assert "Restore the current template sections" in summary["planning_surface_health"]["recommended_next_action"]


def test_planning_summary_exposes_intent_validation_contract(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = []
queued_items = []

[roadmap]
lanes = [
  { id = "tracked-lane", title = "Tracked lane", priority = "first", issues = ["EXT-1"], outcome = "Keep tracked.", reason = "Needed.", promotion_signal = "Promote when needed.", suggested_first_slice = "Do the thing." },
]
candidates = [
  { priority = "first", summary = "Tracked lane" },
]
""",
    )
    _write_external_intent_evidence(
        tmp_path / ".agentic-workspace/planning/external-intent-evidence.json",
        items=[
            {
                "system": "manual",
                "id": "EXT-1",
                "title": "Tracked lane",
                "status": "open",
                "kind": "lane",
                "parent_id": "",
                "planning_residue_expected": "required",
            },
            {
                "system": "manual",
                "id": "EXT-2",
                "title": "Untracked lane",
                "status": "open",
                "kind": "lane",
                "parent_id": "",
                "planning_residue_expected": "required",
            },
            {
                "system": "manual",
                "id": "EXT-3",
                "title": "Closed without residue",
                "status": "closed",
                "kind": "slice",
                "parent_id": "",
                "planning_residue_expected": "required",
            },
        ],
    )

    summary = planning_summary(target=tmp_path)

    assert "intent_validation_contract" in summary["schema"]["shared_fields"]
    contract = summary["intent_validation_contract"]
    assert contract["status"] == "present"
    assert contract["external_evidence"]["status"] == "loaded"
    assert contract["external_evidence"]["item_count"] == 3
    assert contract["current_external_work"]["status"] == "loaded"
    assert contract["current_external_work"]["open_count"] == 2
    assert contract["current_external_work"]["closed_count"] == 1
    assert "provider-agnostic" in contract["current_external_work"]["provider_rule"]
    assert contract["historical_audit_references"]["status"] == "needs-audit"
    assert "not current external-work state" in contract["historical_audit_references"]["rule"]
    assert contract["counts"]["tracked_external_open_count"] == 1
    assert contract["counts"]["untracked_external_open_count"] == 1
    assert contract["counts"]["lower_trust_closeout_count"] == 1
    assert contract["counts"]["attention_count"] == 2
    assert contract["signals"][0]["kind"] == "external_open_untracked"
    assert contract["signals"][1]["kind"] == "closed_without_planning_residue"


def test_planning_summary_reconciles_lower_trust_closeouts_from_review_artifact(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        "[todo]\nactive_items = []\nqueued_items = []\n\n[roadmap]\nlanes = []\ncandidates = []\n",
    )
    _write_external_intent_evidence(
        tmp_path / ".agentic-workspace/planning/external-intent-evidence.json",
        items=[
            {
                "system": "manual",
                "id": "EXT-1",
                "title": "Closed with proof",
                "status": "closed",
                "kind": "slice",
                "parent_id": "",
                "planning_residue_expected": "required",
            },
            {
                "system": "manual",
                "id": "EXT-2",
                "title": "Closed with follow-up",
                "status": "closed",
                "kind": "slice",
                "parent_id": "",
                "planning_residue_expected": "required",
            },
            {
                "system": "manual",
                "id": "EXT-3",
                "title": "Closed without audit",
                "status": "closed",
                "kind": "slice",
                "parent_id": "",
                "planning_residue_expected": "required",
            },
        ],
    )
    _write(
        tmp_path / ".agentic-workspace/planning/reviews/lower-trust.review.json",
        json.dumps(
            {
                "kind": "planning-review/v1",
                "title": "Lower Trust",
                "issue_classifications": [
                    {
                        "id": "EXT-1",
                        "title": "Closed with proof",
                        "classification": "fully_satisfied_with_evidence",
                        "live_state": "closed",
                        "evidence": "commit abc123",
                        "follow_up": "none",
                    },
                    {
                        "id": "EXT-2",
                        "title": "Closed with follow-up",
                        "classification": "covered_by_open_followup",
                        "live_state": "closed",
                        "evidence": "bounded slice landed",
                        "follow_up": "EXT-4",
                    },
                ],
            },
            indent=2,
        )
        + "\n",
    )

    summary = planning_summary(target=tmp_path, profile="compact")
    reconciliation = summary["intent_validation_contract"]["closeout_reconciliation"]

    assert reconciliation["status"] == "needs-audit"
    assert reconciliation["counts"]["reconciled_count"] == 2
    assert reconciliation["counts"]["evidence_present_count"] == 1
    assert reconciliation["counts"]["follow_up_open_count"] == 1
    assert reconciliation["counts"]["needs_audit_count"] == 1
    assert reconciliation["items_by_state"] == {
        "needs-audit": ["EXT-3"],
        "evidence-present": ["EXT-1"],
        "follow-up-open": ["EXT-2"],
    }
    assert summary["intent_validation_contract"]["counts"]["closeout_reconciled_count"] == 2
    assert summary["intent_validation_contract"]["counts"]["closeout_needs_audit_count"] == 1


def test_planning_summary_accepts_historical_closeout_baseline(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        "[todo]\nactive_items = []\nqueued_items = []\n\n[roadmap]\nlanes = []\ncandidates = []\n",
    )
    _write_external_intent_evidence(
        tmp_path / ".agentic-workspace/planning/external-intent-evidence.json",
        items=[
            {
                "system": "manual",
                "id": "EXT-1",
                "title": "Historical closeout",
                "status": "closed",
                "kind": "slice",
                "parent_id": "",
                "planning_residue_expected": "required",
            },
        ],
    )
    _write(
        tmp_path / ".agentic-workspace/planning/reviews/historical-baseline.review.json",
        json.dumps(
            {
                "kind": "planning-review/v1",
                "title": "Historical Baseline",
                "issue_classifications": [
                    {
                        "id": "EXT-1",
                        "title": "Historical closeout",
                        "classification": "accepted_historical_baseline",
                        "live_state": "closed",
                        "evidence": "Legacy debt accepted as baseline.",
                        "follow_up": "none",
                    },
                ],
            },
            indent=2,
        )
        + "\n",
    )

    summary = planning_summary(target=tmp_path, profile="compact")
    reconciliation = summary["intent_validation_contract"]["closeout_reconciliation"]

    assert reconciliation["status"] == "present"
    assert reconciliation["counts"]["historical_baseline_count"] == 1
    assert reconciliation["counts"]["needs_audit_count"] == 0
    assert reconciliation["items_by_state"] == {"historical-baseline": ["EXT-1"]}
    assert summary["intent_validation_contract"]["counts"]["closeout_needs_audit_count"] == 0


def test_planning_reconcile_reports_stale_state_from_provider_agnostic_evidence(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = []
queued_items = []

[roadmap]
lanes = [
  { id = "closed-lane", title = "Closed lane", priority = "first", issues = ["EXT-1"], outcome = "Done.", reason = "Done.", promotion_signal = "None.", suggested_first_slice = "None." },
  { id = "mixed-lane", title = "Mixed lane", priority = "second", issues = ["EXT-1", "EXT-2"], outcome = "Mixed.", reason = "Mixed.", promotion_signal = "None.", suggested_first_slice = "None." },
]
candidates = []
""",
    )
    _write_external_intent_evidence(
        tmp_path / ".agentic-workspace/planning/external-intent-evidence.json",
        items=[
            {
                "system": "manual",
                "id": "EXT-1",
                "title": "Closed elsewhere",
                "status": "resolved",
                "kind": "lane",
                "parent_id": "",
                "planning_residue_expected": "optional",
            },
            {
                "system": "manual",
                "id": "EXT-2",
                "title": "Still open elsewhere",
                "status": "in_progress",
                "kind": "lane",
                "parent_id": "",
                "planning_residue_expected": "optional",
            },
        ],
    )

    reconcile = planning_reconcile(target=tmp_path)

    assert reconcile["kind"] == "planning-reconcile/v1"
    assert reconcile["status"] == "attention-needed"
    assert "provider-agnostic" in reconcile["schema"]["provider_rule"]
    assert reconcile["external_work_state"]["open_count"] == 1
    assert reconcile["external_work_state"]["closed_count"] == 1
    closed_lanes = reconcile["stale_forward_state"]["closed_roadmap_lanes"]
    assert [lane["id"] for lane in closed_lanes] == ["closed-lane"]
    assert closed_lanes[0]["refs"] == ["EXT-1"]


def test_planning_cli_reconcile_outputs_provider_agnostic_state(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = []
queued_items = []

[roadmap]
lanes = [
  { id = "closed-lane", title = "Closed lane", priority = "first", issues = ["EXT-1"], outcome = "Done.", reason = "Done.", promotion_signal = "None.", suggested_first_slice = "None." },
]
candidates = []
""",
    )
    _write_external_intent_evidence(
        tmp_path / ".agentic-workspace/planning/external-intent-evidence.json",
        items=[
            {
                "system": "manual",
                "id": "EXT-1",
                "title": "Closed elsewhere",
                "status": "done",
                "kind": "lane",
                "parent_id": "",
                "planning_residue_expected": "optional",
            }
        ],
    )

    assert planning_cli.main(["reconcile", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"]["schema_version"] == "planning-reconcile-schema/v1"
    assert payload["external_work_state"]["closed_count"] == 1
    assert payload["stale_forward_state"]["closed_roadmap_lanes"][0]["id"] == "closed-lane"


def test_planning_report_promotes_intent_validation_signals_to_findings(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        "[todo]\nactive_items = []\nqueued_items = []\n\n[roadmap]\nlanes = []\ncandidates = []\n",
    )
    _write_external_intent_evidence(
        tmp_path / ".agentic-workspace/planning/external-intent-evidence.json",
        items=[
            {
                "system": "manual",
                "id": "EXT-9",
                "title": "Untracked lane",
                "status": "open",
                "kind": "lane",
                "parent_id": "",
                "planning_residue_expected": "required",
            }
        ],
    )

    report = planning_report(target=tmp_path)

    assert report["intent_validation"]["counts"]["untracked_external_open_count"] == 1
    assert report["status"]["intent_validation_attention_count"] == 1
    assert any(finding["warning_class"] == "external_open_untracked" for finding in report["findings"])


def test_planning_summary_exposes_finished_work_inspection_contract(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    archive_dir = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    _write(
        archive_dir / "system-intent-and-planning-trust-2026-04-21.md",
        (
            "# System Intent And Planning Trust\n\n"
            "## Intent Satisfaction\n\n"
            "- Was original intent fully satisfied?: yes\n\n"
            "## Closure Check\n\n"
            "- Closure decision: archive-and-close\n"
            "- Larger-intent status: closed\n\n"
            "Implemented #220, #222, and #229.\n"
        ),
    )
    _write(
        archive_dir / "bounded-delegation-and-run-contracts-2026-04-21.md",
        (
            "# Bounded Delegation And Run Contracts\n\n"
            "## Intent Satisfaction\n\n"
            "- Was original intent fully satisfied?: no\n\n"
            "## Closure Check\n\n"
            "- Closure decision: archive-but-keep-lane-open\n"
            "- Larger-intent status: open\n\n"
            "Implemented #233 and left #241 open.\n"
        ),
    )
    _write_finished_work_evidence(
        tmp_path / ".agentic-workspace/planning/finished-work-evidence.json",
        items=[
            {
                "system": "manual",
                "id": "#260",
                "title": "Finished-work intent inspection",
                "status": "open",
                "kind": "lane",
                "reopens": ["#220", "#222", "#229"],
            }
        ],
    )

    summary = planning_summary(target=tmp_path)

    assert "finished_work_inspection_contract" in summary["schema"]["shared_fields"]
    contract = summary["finished_work_inspection_contract"]
    assert contract["status"] == "present"
    assert contract["counts"]["archived_closeout_count"] == 2
    assert contract["counts"]["likely_premature_closeout_count"] == 1
    assert contract["counts"]["partial_count"] == 1
    assert contract["counts"]["attention_count"] == 1
    assert contract["evidence"]["status"] == "loaded"
    assert contract["evidence"]["item_count"] == 1
    assert contract["inspections"][0]["classification"] == "partial"
    assert contract["inspections"][1]["classification"] == "likely_premature_closeout"
    assert contract["signals"][0]["kind"] == "likely_premature_closeout"


def test_planning_summary_exposes_closeout_distillation_contract(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    plan_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "distill-closeout.plan.json"
    _write_execplan_record(plan_path, item_id="distill-closeout", status="in-progress")
    record = json.loads(plan_path.read_text(encoding="utf-8"))
    record["required_continuation"] = {
        "required follow-on for the larger intended outcome": "yes",
        "owner surface": ".agentic-workspace/planning/state.toml",
        "activation trigger": "continue #344",
    }
    record["execution_summary"] = {
        "outcome delivered": "Added closeout distillation.",
        "validation confirmed": "focused tests",
        "follow-on routed to": "#344 memory routing",
        "post-work posterity capture": "No durable learning beyond continuation; local execution details should die.",
        "knowledge promoted (Memory/Docs/Config)": "none",
        "resume from": "next milestone",
    }
    record["references"] = [{"kind": "external-work", "target": "#344", "label": "Memory routing follow-up", "role": "follow-up"}]
    installer_mod._write_execplan_record(record_path=plan_path, record=record)
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        (
            "[todo]\n"
            "active_items = [\n"
            '  { id = "distill-closeout", status = "in-progress", surface = ".agentic-workspace/planning/execplans/distill-closeout.plan.json", why_now = "prove closeout distillation." },\n'
            "]\n"
            "queued_items = []\n"
        ),
    )

    summary = planning_summary(target=tmp_path)
    contract = summary["closeout_distillation_contract"]

    assert "closeout_distillation_contract" in summary["schema"]["shared_fields"]
    assert contract["status"] == "present"
    assert contract["archive_role"] == "archive is proof and historical recovery, not the ordinary durable-learning carrier"
    assert contract["counts"]["intentionally_discarded_count"] == 1
    assert contract["buckets"]["discard"][0]["owner"] == "discard"
    assert contract["buckets"]["continuation"][0]["summary"] == "#344 memory routing"
    assert contract["buckets"]["issue_follow_up"][0]["source"] == "#344"

    report = planning_report(target=tmp_path)
    assert report["closeout_distillation"]["counts"]["intentionally_discarded_count"] == 1
    assert report["active"]["closeout_distillation_contract"]["buckets"]["discard"][0]["source"] == (
        "execution_summary.knowledge promoted (Memory/Docs/Config)"
    )


def test_planning_report_promotes_finished_work_inspection_signals_to_findings(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    archive_dir = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    _write(
        archive_dir / "system-intent-and-planning-trust-2026-04-21.md",
        (
            "# System Intent And Planning Trust\n\n"
            "## Intent Satisfaction\n\n"
            "- Was original intent fully satisfied?: yes\n\n"
            "## Closure Check\n\n"
            "- Closure decision: archive-and-close\n"
            "- Larger-intent status: closed\n\n"
            "Implemented #220 and #222.\n"
        ),
    )
    _write_finished_work_evidence(
        tmp_path / ".agentic-workspace/planning/finished-work-evidence.json",
        items=[
            {
                "system": "manual",
                "id": "#260",
                "title": "Finished-work intent inspection",
                "status": "open",
                "kind": "lane",
                "reopens": ["#220"],
            }
        ],
    )

    report = planning_report(target=tmp_path)

    assert report["finished_work_inspection"]["counts"]["likely_premature_closeout_count"] == 1
    assert report["status"]["finished_work_inspection_attention_count"] == 1
    assert report["next_action"]["summary"].startswith("Inspect archived closeouts flagged by reopening evidence")
    assert any(finding["warning_class"] == "likely_premature_closeout" for finding in report["findings"])


def test_planning_summary_exposes_closure_evidence(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: expose closure evidence.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md", _minimal_execplan(status="completed"))

    summary = planning_summary(target=tmp_path)

    completed_execplans = summary["execplans"]["completed_execplans"]
    assert summary["planning_record"]["status"] == "unavailable"
    assert len(completed_execplans) == 1
    assert completed_execplans[0]["proof_report"]["proof achieved now"] == "validation and closure checks passed for the bounded slice."
    assert completed_execplans[0]["intent_satisfaction"]["was original intent fully satisfied?"] == "yes"
    assert completed_execplans[0]["closure_check"]["closure decision"] == "archive-and-close"
    assert summary["planning_surface_health"]["status"] == "not-clean"
    assert summary["planning_surface_health"]["warnings"][0]["warning_class"] == "archive_accumulation_drift"
    assert summary["planning_surface_health"]["warnings"][0]["path"].endswith(".agentic-workspace/planning/execplans/plan-alpha.md")
    assert "archive-plan" in summary["planning_surface_health"]["recommended_next_action"]
    assert "intent_interpretation" in summary["schema"]["view_fields"]["planning_record"]
    assert "execution_run" in summary["schema"]["view_fields"]["planning_record"]
    assert "finished_run_review" in summary["schema"]["view_fields"]["planning_record"]
    assert "proof_report" in summary["schema"]["view_fields"]["planning_record"]
    assert "intent_satisfaction" in summary["schema"]["view_fields"]["planning_record"]
    assert "closure_check" in summary["schema"]["view_fields"]["planning_record"]


def test_planning_report_prints_closure_evidence(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: expose closure evidence.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md", _minimal_execplan(status="completed"))

    exit_code = planning_cli.main(["report", "--target", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "Completed execplans awaiting archive: 1" in out
    assert "Proof report: validation and closure checks passed for the bounded slice." in out
    assert "Intent satisfaction: yes" in out
    assert "Closure decision: archive-and-close" in out


def test_planning_summary_can_expose_active_contract_from_execplan_without_todo_row(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        "# TODO\n\n## Now\n\n- Active execplan: .agentic-workspace/planning/execplans/plan-alpha.md\n",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md", _minimal_execplan())

    summary = planning_summary(target=tmp_path)

    assert summary["todo"]["active_count"] == 0
    assert summary["execplans"]["active_count"] == 1
    assert summary["planning_record"]["status"] == "present"
    assert summary["planning_record"]["task"]["id"] == "plan-alpha"
    assert summary["planning_record"]["task"]["surface"] == ".agentic-workspace/planning/execplans/plan-alpha.md"
    assert summary["planning_record"]["continuation_owner"] == ".agentic-workspace/planning/execplans/plan-alpha.md"
    assert summary["active_contract"]["status"] == "present"
    assert summary["resumable_contract"]["status"] == "present"
    assert summary["follow_through_contract"]["status"] == "present"
    assert summary["context_budget_contract"]["status"] == "present"
    assert summary["hierarchy_contract"]["status"] == "present"
    assert summary["active_contract"]["todo_item"]["id"] == ""
    assert summary["active_contract"]["minimal_refs"] == [
        ".agentic-workspace/planning/state.toml",
        ".agentic-workspace/planning/execplans/plan-alpha.md",
    ]


def test_planning_summary_schema_describes_projection_fields(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")

    summary = planning_summary(target=tmp_path)

    assert summary["schema"]["view_fields"]["planning_record"][0] == "task"
    assert "intent_interpretation" in summary["schema"]["view_fields"]["planning_record"]
    assert "execution_run" in summary["schema"]["view_fields"]["planning_record"]
    assert "finished_run_review" in summary["schema"]["view_fields"]["planning_record"]
    assert "tool_verification" in summary["schema"]["view_fields"]["planning_record"]
    assert "system_intent_alignment" in summary["schema"]["view_fields"]["planning_record"]
    assert "tool_verification" in summary["schema"]["view_fields"]["resumable_contract"]
    assert "follow_through_contract" in summary["schema"]["shared_fields"]
    assert "intent_interpretation_contract" in summary["schema"]["shared_fields"]
    assert "context_budget_contract" in summary["schema"]["shared_fields"]
    assert "execution_run_contract" in summary["schema"]["shared_fields"]
    assert "finished_run_review_contract" in summary["schema"]["shared_fields"]
    assert "intent_validation_contract" in summary["schema"]["shared_fields"]
    assert "finished_work_inspection_contract" in summary["schema"]["shared_fields"]
    assert "hierarchy_contract" in summary["schema"]["shared_fields"]
    assert "handoff_contract" in summary["schema"]["shared_fields"]
    assert "planning_surface_health" in summary["schema"]["view_fields"]
    assert "literal_request" in summary["schema"]["view_fields"]["intent_interpretation_contract"]
    assert "live_working_set" in summary["schema"]["view_fields"]["context_budget_contract"]
    assert "pre_work_config_pull" in summary["schema"]["view_fields"]["context_budget_contract"]
    assert "pre_work_memory_pull" in summary["schema"]["view_fields"]["context_budget_contract"]
    assert "run_status" in summary["schema"]["view_fields"]["execution_run_contract"]
    assert "changed_surfaces" in summary["schema"]["view_fields"]["execution_run_contract"]
    assert "review_status" in summary["schema"]["view_fields"]["finished_run_review_contract"]
    assert "config_compliance" in summary["schema"]["view_fields"]["finished_run_review_contract"]
    assert "config_trust" in summary["schema"]["view_fields"]["finished_run_review_contract"]
    assert "counts" in summary["schema"]["view_fields"]["intent_validation_contract"]
    assert "inspections" in summary["schema"]["view_fields"]["finished_work_inspection_contract"]
    assert "parent_lane" in summary["schema"]["view_fields"]["hierarchy_contract"]
    assert "next_likely_slice" in summary["schema"]["view_fields"]["follow_through_contract"]
    assert "read_first" in summary["schema"]["view_fields"]["handoff_contract"]
    assert "pre_work_config_pull" in summary["schema"]["view_fields"]["handoff_contract"]
    assert "pre_work_memory_pull" in summary["schema"]["view_fields"]["handoff_contract"]
    assert "system_intent_alignment" in summary["schema"]["view_fields"]["handoff_contract"]


def test_planning_summary_exposes_ownership_review(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")

    summary = planning_summary(target=tmp_path)
    report = planning_report(target=tmp_path)
    planning_cli._print_summary(summary)
    planning_cli._print_report(report)
    out = capsys.readouterr().out

    ownership_review = summary["ownership_review"]
    assert ownership_review["status"] == "present"
    assert ".agentic-workspace/planning/" in ownership_review["package_owned_roots"]
    assert ".agentic-workspace/planning/state.toml" not in ownership_review["repo_owned_surfaces"]
    assert "AGENTS.md" in ownership_review["repo_owned_surfaces"]
    assert "ROADMAP.md" not in ownership_review["repo_owned_surfaces"]
    assert ownership_review["minimal_repo_hook"] == "AGENTS.md#agentic-workspace:workflow"
    assert "ownership_review" in summary["schema"]["shared_fields"]
    assert "Ownership review:" in out


def test_summary_command_defaults_to_compact_json_and_accepts_full_profile(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = [
  { id = "plan-alpha", status = "in-progress", surface = ".agentic-workspace/planning/execplans/plan-alpha.md", why_now = "keep compact startup cheap." }
]
queued_items = []

[roadmap]
lanes = [
  { id = "tracked-lane", title = "Tracked lane", priority = "first", issues = ["EXT-1"], outcome = "Keep tracked.", reason = "Needed.", promotion_signal = "Promote when needed.", suggested_first_slice = "Do the thing." },
]
candidates = [
  { priority = "first", summary = "Tracked lane" },
]
""",
    )
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md", _minimal_execplan())

    exit_code = planning_cli.main(["summary", "--target", str(tmp_path), "--format", "json"])
    default_payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert default_payload["profile"] == "compact"
    assert default_payload["schema"]["schema_version"] == "planning-summary-compact-schema/v1"

    exit_code = planning_cli.main(["summary", "--target", str(tmp_path), "--format", "json", "--profile", "full"])
    full_payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert full_payload["profile"] == "full"
    assert full_payload["schema"]["schema_version"] == "planning-summary-schema/v1"
    assert full_payload["schema"]["command"] == "agentic-workspace summary --format json --profile full"
    assert "candidate_lanes" in full_payload["roadmap"]


def test_planning_handoff_derives_compact_worker_contract(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: promote when maintained report signal appears.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md", _minimal_execplan())

    handoff = planning_handoff(target=tmp_path)

    assert handoff["kind"] == "planning-handoff/v1"
    assert handoff["schema"]["schema_version"] == "planning-handoff-schema/v1"
    assert handoff["schema"]["canonical_doc"] == ".agentic-workspace/docs/execution-flow-contract.md"
    assert handoff["handoff_contract"]["status"] == "present"
    assert handoff["handoff_contract"]["next_action"] == "Add one checker."
    assert handoff["handoff_contract"]["capability_posture"]["execution class"] == "mechanical-follow-through"
    assert handoff["handoff_contract"]["capability_posture"]["recommended strength"] == "weak"
    assert handoff["handoff_contract"]["context_budget"]["status"] == "present"
    assert handoff["handoff_contract"]["intent_interpretation"]["status"] == "present"
    assert handoff["handoff_contract"]["execution_bounds"]["allowed paths"] == "scripts/check/check_planning_surfaces.py"
    assert handoff["handoff_contract"]["stop_conditions"]["stop when"].startswith("the work needs broader")
    assert handoff["handoff_contract"]["return_with"]["execution_summary_fields"][3] == "post-work posterity capture"
    assert handoff["handoff_contract"]["return_with"]["finished_run_review_fields"][0] == "review status"
    assert handoff["handoff_contract"]["return_with"]["finished_run_review_fields"][4] == "config compliance"
    assert handoff["handoff_contract"]["worker_contract"]["worker_must_not_own_by_default"][0] == "roadmap routing"


def test_planning_handoff_command_emits_json(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: promote when maintained report signal appears.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md", _minimal_execplan())

    exit_code = planning_cli.main(["handoff", "--target", str(tmp_path), "--format", "json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "planning-handoff/v1"
    assert payload["handoff_contract"]["status"] == "present"


def test_planning_summary_human_view_starts_with_planning_record(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: promote when maintained report signal appears.
""",
    )
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Next Candidate Queue

- Candidate alpha; promote when maintained report signal appears.

## Reopen Conditions

- Reopen when a queue or report signals new work.
""",
    )
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md", _minimal_execplan())

    summary = planning_summary(target=tmp_path)
    planning_cli._print_summary(summary)
    out = capsys.readouterr().out

    assert "Planning-surface health:" in out
    assert "- Status: clean" in out
    assert "Planning record:" in out
    assert "Planning hierarchy view:" in out
    assert "Parent lane: plan-alpha-lane" in out
    assert "Requested outcome: Keep scope clear." in out
    assert "Continuation owner: .agentic-workspace/planning/execplans/plan-alpha.md" in out
    assert "Active contract view:" in out
    assert "Resumable contract view:" in out
    assert "Follow-through contract view:" in out
    assert "Context budget contract view:" in out
    assert "Intent-interpretation contract view:" in out
    assert "Execution-run contract view:" in out
    assert "Finished-run review contract view:" in out


def test_summary_text_prints_planning_record_before_contract_views(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: promote when maintained report signal appears.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n\n## Next Candidate Queue\n\n- Candidate alpha\n")
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md", _minimal_execplan())

    exit_code = planning_cli.main(["summary", "--target", str(tmp_path)])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "Planning hierarchy view:" in captured
    assert "Planning record:" in captured
    assert "Active contract view:" in captured
    assert "Resumable contract view:" in captured
    assert captured.index("Planning record:") < captured.index("Active contract view:")
    assert "- Next action: Add one checker." in captured


def test_summary_text_prints_required_tools_when_declared(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: promote when maintained report signal appears.
""",
    )
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md", _minimal_execplan_with_required_tools())

    exit_code = planning_cli.main(["summary", "--target", str(tmp_path)])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "- Required tools: browser, gh" in captured


def test_planning_report_exposes_hierarchy_projection(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: report-lane
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/report-lane.md
  Why now: derive compact module state.
""",
    )
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Candidate Lanes

- Lane: Report lane parent
  ID: plan-alpha-lane
  Priority: first
  Issues: #140
  Outcome: test the hierarchy projection.
  Why now: exercise the derived hierarchy view.
  Promotion signal: promote when report output needs a live parent lane.
  Suggested first slice: use one real plan.
""",
    )
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "report-lane.md", _minimal_execplan())

    report = planning_report(target=tmp_path)

    assert report["active"]["hierarchy_contract"]["status"] == "present"
    assert report["active"]["hierarchy_contract"]["parent_lane"]["id"] == "plan-alpha-lane"
    assert report["active"]["hierarchy_contract"]["parent_lane"]["title"] == "Report lane parent"


def test_planning_summary_tracks_near_term_todo_queue(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
# TODO

## Next

- ID: plan-alpha
  Status: in-progress
  Surface: .agentic-workspace/planning/execplans/plan-alpha.md
  Why now: active slice first.

- ID: plan-beta
  Status: planned
  Surface: direct
  Why now: next same-thread chunk after the active slice lands.
""",
    )
    _write(
        tmp_path / "ROADMAP.md",
        """
# Roadmap

## Candidate Lanes

- Lane: Report lane parent
  ID: plan-alpha-lane
  Priority: first
  Issues: #140
  Outcome: test the hierarchy projection.
  Why now: exercise the derived hierarchy view.
  Promotion signal: promote when report output needs a live parent lane.
  Suggested first slice: use one real plan.
""",
    )
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.md", _minimal_execplan())

    summary = planning_summary(target=tmp_path)
    report = planning_report(target=tmp_path)

    assert summary["todo"]["queued_count"] == 1
    assert summary["todo"]["queued_items"][0]["id"] == "plan-beta"
    assert summary["hierarchy_contract"]["near_term_queue"][0]["id"] == "plan-beta"
    assert report["status"]["queued_todo_count"] == 1


def test_resolve_target_root_keeps_explicit_repo_target_when_local_tree_exists(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)
    (repo_root / ".agentic-workspace" / "local-only").mkdir(parents=True)

    resolved = installer_mod.resolve_target_root(repo_root)

    assert resolved == repo_root


def test_resolve_target_root_local_only_uses_agentic_workspace_local_only_subtree(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)

    resolved = installer_mod.resolve_target_root(repo_root, local_only=True)

    assert resolved == repo_root / ".agentic-workspace" / "local-only"
