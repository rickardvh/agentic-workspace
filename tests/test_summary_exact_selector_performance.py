from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from statistics import median

import pytest
from repo_planning_bootstrap import installer as planning_installer
from repo_planning_bootstrap.installer import install_bootstrap

REPO_ROOT = Path(__file__).resolve().parents[1]
SUMMARY_SCRIPT = REPO_ROOT / "scripts" / "run_agentic_workspace.py"
SELECTOR_FIXTURES = (
    "decomposition,planning_surface_health,planning_revision",
    "planning_record,execplans,continuation_view,planning_revision",
    "planning_record,execution_readiness",
    "execution_readiness,planning_revision",
    "continuation_view,execution_readiness,planning_revision",
    "lanes,roadmap,planning_record",
)
HISTORICAL_BUILDERS = {
    "execplan_archive_builder",
    "finished_work_builder",
    "review_history_builder",
    "unrelated_external_backlog_builder",
}


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def _prepare_summary_target(target: Path, *, closeout_count: int) -> None:
    install_bootstrap(target=target)
    _write(target / ".agentic-workspace/config.toml", "schema_version = 1\n\n[workspace]\nenabled = true")
    _write(
        target / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[active]
execplans = []

[todo]
active_items = [
  { id = "plan-alpha", status = "active", surface = ".agentic-workspace/planning/execplans/plan-alpha.plan.json", next_action = "run bounded proof" },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    _write(
        target / ".agentic-workspace/planning/execplans/plan-alpha.plan.json",
        json.dumps(
            {
                "kind": "planning-execplan/v1",
                "id": "plan-alpha",
                "title": "Exact selector fixture",
                "owner_level": "slice",
                "lifecycle": "live",
                "phase": "implementation",
                "revision": 1,
                "intent": {"outcome": "Prove exact selector isolation.", "non_goals": []},
                "next_action": "run bounded proof",
                "completion_criteria": ["The bounded exact-selector proof passes."],
                "blockers": [],
                "proof": {"claims": [], "requirements": [], "refs": []},
                "continuation": {"owner": "none", "residual_intent": "none"},
                "active_milestone": {"status": "in-progress", "ready": "ready", "blocked": "none"},
                "specialist_contracts": [],
            }
        ),
    )
    _write(
        target / ".agentic-workspace/planning/execplans/plan-beta.plan.json",
        json.dumps(
            {
                "kind": "planning-execplan/v1",
                "id": "plan-beta",
                "title": "Adjacent live owner",
                "owner_level": "slice",
                "lifecycle": "live",
                "phase": "validation",
                "revision": 2,
                "intent": {"outcome": "Remain visible in the current live-owner projection.", "non_goals": []},
                "next_action": "validate adjacent owner",
                "blockers": [],
                "proof": {"claims": [], "requirements": [], "refs": []},
                "continuation": {"owner": "none", "residual_intent": "none"},
                "specialist_contracts": [],
            }
        ),
    )
    _write(
        target / ".agentic-workspace/planning/decompositions/epic-alpha.decomposition.json",
        json.dumps(
            {
                "kind": "planning-decomposition/v1",
                "title": "Nontrivial exact-selector decomposition",
                "larger_intended_outcome": "Deliver two independently promotable lanes.",
                "status": "active",
                "parent_acceptance": {
                    "original_intent": "Deliver the complete epic.",
                    "acceptance_target": "Both lanes are integrated.",
                    "parent_proof_required": "Cross-lane acceptance proof passes.",
                    "residual_intent_rule": "Keep remaining lanes explicit.",
                },
                "non_goals": ["Do not merge the two lane owners."],
                "candidate_lanes": [
                    {
                        "id": "lane-ready",
                        "title": "Ready lane",
                        "readiness": "ready",
                        "outcome": "Deliver the first capability.",
                        "owner_surface": ".agentic-workspace/planning/execplans/plan-alpha.plan.json",
                        "proof": "Prove the first capability independently.",
                        "slice_contribution_to_parent": "Supplies the first capability.",
                        "residual_parent_intent": "The second capability remains.",
                        "parent_proof_boundary": "Prove the first capability independently.",
                        "human_confirmation_needed": [],
                        "depends_on": [],
                        "parallel_with": ["lane-shaped"],
                    },
                    {
                        "id": "lane-shaped",
                        "title": "Shaped lane",
                        "readiness": "needs-shaping",
                        "outcome": "Deliver the second capability.",
                        "owner_surface": "",
                        "proof": "Prove the second capability before promotion.",
                        "slice_contribution_to_parent": "Supplies the second capability.",
                        "residual_parent_intent": "No residual intent after integration.",
                        "parent_proof_boundary": "Prove both capabilities compose.",
                        "human_confirmation_needed": [],
                        "depends_on": ["lane-ready"],
                        "parallel_with": [],
                    },
                ],
                "dependency_assumptions": [],
                "parallelization_assumptions": [],
                "proof_expectations": ["Each lane retains independent acceptance proof."],
                "promotion_rule": "Promote only ready lanes with bounded ownership.",
                "references": [],
                "notes": "Exact-selector semantic fixture.",
            }
        ),
    )
    evidence_root = target / ".agentic-workspace/planning/closeout-evidence"
    for index in range(closeout_count):
        _write(
            evidence_root / f"closed-{index}.closeout.json",
            json.dumps(
                {
                    "kind": "planning-closeout-evidence/v1",
                    "plan_id": f"closed-{index}",
                    "claim_level": "slice",
                }
            ),
        )
    subprocess.run(["git", "init", "--quiet"], cwd=target, check=True)
    subprocess.run(["git", "add", "-A"], cwd=target, check=True)
    subprocess.run(
        ["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "--quiet", "-m", "fixture"],
        cwd=target,
        check=True,
    )


def _run_exact_summary(target: Path, selector: str) -> tuple[float, dict[str, object], int]:
    environment = dict(os.environ)
    environment["AW_PROJECTION_FORCE_REFRESH"] = "1"
    environment["AW_SESSION_LOG_ORIGIN"] = "pytest-exact-selector-fixture"
    started = time.perf_counter()
    completed = subprocess.run(
        [
            sys.executable,
            str(SUMMARY_SCRIPT),
            "summary",
            "--target",
            str(target),
            "--select",
            selector,
            "--format",
            "json",
        ],
        cwd=REPO_ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=True,
        timeout=5,
    )
    elapsed = time.perf_counter() - started
    payload = json.loads(completed.stdout)
    return elapsed, payload, len(completed.stdout.encode("utf-8"))


@pytest.mark.parametrize("selector", SELECTOR_FIXTURES)
def test_exact_summary_selectors_are_clean_process_history_independent(tmp_path: Path, selector: str) -> None:
    empty_target = tmp_path / "empty"
    historical_target = tmp_path / "history-1000"
    _prepare_summary_target(empty_target, closeout_count=0)
    _prepare_summary_target(historical_target, closeout_count=1000)

    empty_samples: list[float] = []
    historical_samples: list[float] = []
    observed_payloads: list[dict[str, object]] = []
    observed_sizes: list[int] = []
    for _ in range(5):
        empty_elapsed, empty_payload, empty_size = _run_exact_summary(empty_target, selector)
        historical_elapsed, historical_payload, historical_size = _run_exact_summary(historical_target, selector)
        empty_samples.append(empty_elapsed)
        historical_samples.append(historical_elapsed)
        observed_payloads.extend((empty_payload, historical_payload))
        observed_sizes.extend((empty_size, historical_size))

    requested_roots = {token.split(".", 1)[0] for token in selector.split(",")}
    for payload in observed_payloads:
        diagnostics = payload["selection_cost"]
        assert diagnostics["fallback_profile_loaded"] is False
        assert diagnostics["historical_sources_loaded"] is False
        assert set(diagnostics["dependency_plan"]) == requested_roots
        assert set(diagnostics["omitted_builders"]) == HISTORICAL_BUILDERS
        assert set(diagnostics["omitted_sources"]) >= {
            "execplan-archive",
            "closeout-evidence",
            "finished-work-evidence",
            "review-history",
            "unrelated-external-backlog",
        }
        values = payload["values"]
        if "decomposition" in requested_roots:
            decomposition = values["decomposition"]
            assert decomposition["status"] == "present"
            assert decomposition["record_count"] == 1
            assert decomposition["ready_lane_count"] == 1
            assert decomposition["records"][0]["lane_count"] == 2
            assert "direct-decomposition" in diagnostics["invoked_resolvers"]
        if "execplans" in requested_roots:
            execplans = values["execplans"]
            assert execplans["active_count"] == 2
            assert {item["path"] for item in execplans["active_execplans"]} == {
                ".agentic-workspace/planning/execplans/plan-alpha.plan.json",
                ".agentic-workspace/planning/execplans/plan-beta.plan.json",
            }
            assert "direct-live-execplans" in diagnostics["invoked_resolvers"]
        if "execution_readiness" in requested_roots:
            readiness = values["execution_readiness"]
            assert readiness["status"] == "scaffold-tightening-required"
            assert readiness["implementation_tightening"]["owner"].endswith("plan-alpha.plan.json")
            assert "tiny-readiness" in diagnostics["invoked_resolvers"]
        if "lanes" in requested_roots:
            assert values["lanes"]["record_count"] == 0
            assert "tiny-lanes" in diagnostics["invoked_resolvers"]
        if "roadmap" in requested_roots:
            assert values["roadmap"] == {
                "lane_count": 0,
                "candidate_lanes": [],
                "candidate_count": 0,
                "candidates": [],
            }
            assert "tiny-roadmap-counts" in diagnostics["invoked_resolvers"]
    assert max(observed_sizes) < 64 * 1024

    empty_median = median(empty_samples)
    historical_median = median(historical_samples)
    assert empty_median <= 2.0
    assert historical_median <= 2.0
    assert historical_median <= max(empty_median * 1.2, empty_median + 0.010), (
        f"exact selector exceeded the 20% history-independence budget: {selector}; "
        f"empty={empty_median:.6f}s history_1000={historical_median:.6f}s"
    )


def test_exact_summary_resolvers_preserve_broad_current_semantics_without_broad_or_historical_builders(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "semantic-equivalence"
    _prepare_summary_target(target, closeout_count=3)
    broad = planning_installer.planning_summary(target=target, profile="full")
    expected_decomposition = broad["decomposition"]
    expected_live_execplans = {
        "active_count": broad["execplans"]["active_count"],
        "active_execplans": broad["execplans"]["active_execplans"],
    }

    planning_installer._PLANNING_SELECTED_OWNER_CACHE.clear()

    def fail_builder(*args: object, **kwargs: object) -> object:
        raise AssertionError("broad or historical builder was invoked by an exact selector")

    monkeypatch.setattr(planning_installer, "planning_summary", fail_builder)
    monkeypatch.setattr(planning_installer, "_archived_execplan_count", fail_builder)
    monkeypatch.setattr(planning_installer, "_finished_work_inspection_contract", fail_builder)
    monkeypatch.setattr(planning_installer, "_ownership_review", fail_builder)

    query = planning_installer.planning_summary_query(
        target=target,
        selectors=["decomposition", "execplans", "planning_revision"],
    )
    assert query["status"] == "present"
    assert query["payload"]["decomposition"] == expected_decomposition
    assert query["payload"]["execplans"] == expected_live_execplans
    assert query["payload"]["decomposition"]["record_count"] == 1
    assert query["payload"]["decomposition"]["ready_lane_count"] == 1
    assert query["payload"]["decomposition"]["records"][0]["lane_count"] == 2
    assert query["payload"]["execplans"]["active_count"] == 2
    assert set(query["query_diagnostics"]["invoked_resolvers"]) >= {
        "direct-decomposition",
        "direct-live-execplans",
        "planning_revision",
    }
