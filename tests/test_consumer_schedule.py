"""Finite rotation and negative reporting proof; no fake provider acceptance."""

import datetime as dt
import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/tooling/model-cli-harness"))
sys.path.insert(0, str(ROOT / "src/tooling/release"))
import consumer_environment as environments  # noqa: E402
import consumer_schedule as schedule  # noqa: E402
from consumer_journeys import FAMILIES  # noqa: E402


def plan(day=0):
    return {
        **schedule.selection(day),
        "current": {"version": "1.3.2", "inventory_sha256": "exact"},
        "previous": {"version": "1.2.0"},
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "harness_commit": "a" * 40,
        "harness_sources": schedule.harness_identity(),
        "attempt": "initial",
        "template": "pinned",
        "model": "gpt-5.6-luna",
        "reasoning": "medium",
        "billing": "subscription",
    }


def test_seven_day_rotation_covers_declared_targets_profiles_and_families():
    days = [schedule.selection(day, skip_macos=False) for day in range(7)]
    cases = [case for day in days for case in day["live"]]
    assert {c["target"] for c in cases} == {p["target"] for p in schedule.platform_release.platforms()}
    assert {c["profile"] for c in cases} == set(schedule.PROFILES)
    from consumer_journeys import ON_DEMAND_FAMILIES

    assert {c["family"] for c in cases} == set(FAMILIES) - set(ON_DEMAND_FAMILIES)
    assert all(sum(c["sessions"] for c in day["live"]) <= 3 for day in days)
    assert all(day["seconds_per_session"] == 900 for day in days)


def test_user_skipped_macos_remains_assigned_and_cannot_pass():
    selected = plan(5)
    assert sum(c["disposition"] == "skipped-by-user" for c in selected["live"]) == 2
    result = schedule.summary(selected, [])
    assert result["assigned"] == len(selected["live"]) + len(selected["deterministic"])
    assert result["passed"] == 0 and result["status"] != "passed"


def test_missing_results_and_wrong_subject_are_not_green(tmp_path):
    selected = plan()
    path = tmp_path / "docker.json"
    path.write_text(json.dumps({"status": "passed", "executed": True, "requested": {"version": "older"}}))
    result = schedule.summary(selected, [path])
    assert result["passed"] == 0
    assert result["cases"][0]["failure_class"] == "missing-or-mismatched-subject-witness"


def test_missing_provider_never_launches_or_drops_assigned_cases(tmp_path, monkeypatch):
    selected = plan()
    (tmp_path / "plan.json").write_text(json.dumps(selected))
    monkeypatch.setattr(schedule, "frozen_subject", lambda *args: object())
    monkeypatch.setattr(schedule, "run_case", lambda *args, **kwargs: pytest.fail("Unexpected provider launch"))
    schedule.execute_plan(tmp_path, tmp_path / "results", tmp_path / "scratch", kind="live")
    rows = [json.loads(path.read_text()) for path in (tmp_path / "results").glob("*.json")]
    assert len(rows) == len(selected["live"])
    assert all(row["failure_class"] == "provider-runner-unavailable" and not row["executed"] for row in rows)


def test_budget_exhaustion_prevents_next_provider_session(tmp_path, monkeypatch):
    selected = plan()
    (tmp_path / "plan.json").write_text(json.dumps(selected))
    monkeypatch.setattr(schedule, "frozen_subject", lambda *args: object())
    calls = []

    def transport(args, **kwargs):
        calls.append(args.family)
        args.result.write_text(json.dumps({"status": "failed", "sessions_started": 3}))

    monkeypatch.setattr(schedule, "run_case", transport)
    schedule.execute_plan(tmp_path, tmp_path / "results", tmp_path / "scratch", kind="live", live_ready=True)
    assert len(calls) == 1
    assert json.loads((tmp_path / "results/live-1.json").read_text())["failure_class"] == "session-budget-exhausted"


def test_first_failure_cannot_be_replaced(tmp_path, monkeypatch):
    (tmp_path / "plan.json").write_text(json.dumps(plan()))
    monkeypatch.setattr(schedule, "frozen_subject", lambda *args: object())
    output = tmp_path / "results"
    output.mkdir()
    (output / "live-0.json").write_text('{"status":"failed"}')
    with pytest.raises(ValueError, match="first failure"):
        schedule.execute_plan(tmp_path, output, tmp_path / "scratch", kind="live")


def test_recurring_workflow_has_no_pr_provider_ingress_and_seven_day_retention():
    path = ROOT / ".github/workflows/consumer-validation.yml"
    workflow = yaml.load(path.read_text(), Loader=yaml.BaseLoader)
    assert workflow["on"]["schedule"][0]["cron"] == "23 7 * * *"
    assert "pull_request_target" not in workflow["on"] and "pull_request" not in workflow["on"]
    live = workflow["jobs"]["live"]
    assert "github.ref == 'refs/heads/master'" in live["if"]
    assert live["environment"] == "consumer-live"
    assert "CONSUMER_LIVE_RUNNER_READY" in live["if"]
    for job in workflow["jobs"].values():
        for step in job["steps"]:
            if step.get("uses", "").startswith("actions/upload-artifact@"):
                assert step["with"]["retention-days"] == "7"


def test_release_observation_waits_for_both_registry_attempts_even_on_failure():
    workflow = yaml.load((ROOT / ".github/workflows/release.yml").read_text(), Loader=yaml.BaseLoader)
    job = workflow["jobs"]["public-consumers"]
    assert {"language-packages", "language-registries"} <= set(job["needs"])
    assert "always() && !cancelled() && needs.promotion-admission.result == 'success'" in job["if"]


def test_cancel_cleanup_targets_only_exact_owned_resource(tmp_path, monkeypatch):
    name = "aw-consumer-" + "a" * 32
    path = tmp_path / (name + ".resource.json")
    path.write_text(json.dumps({"kind": "consumer-disposable/v1", "name": name, "backend": "sandbox"}))
    calls = []
    monkeypatch.setattr(environments, "run", lambda command: calls.append(command))
    environments.cleanup_remaining(tmp_path)
    assert calls == [["sbx", "rm", "--force", name]]
    assert not path.exists()


def test_cleanup_rejects_another_sandbox_name(tmp_path, monkeypatch):
    path = tmp_path / ("aw-consumer-" + "a" * 32 + ".resource.json")
    path.write_text(json.dumps({"kind": "consumer-disposable/v1", "name": "user-existing-sandbox", "backend": "sandbox"}))
    monkeypatch.setattr(environments, "run", lambda command: pytest.fail("Unowned resource deletion"))
    with pytest.raises(ValueError, match="ownership"):
        environments.cleanup_remaining(tmp_path)
    assert path.exists()


def test_changed_harness_cannot_execute_a_frozen_plan(tmp_path, monkeypatch):
    selected = plan()
    (tmp_path / "plan.json").write_text(json.dumps(selected))
    monkeypatch.setattr(schedule, "harness_identity", lambda: {"changed": "bytes"})
    monkeypatch.setattr(schedule, "run_case", lambda *a, **kw: pytest.fail("Drifted execution"))
    with pytest.raises(ValueError, match="Harness differs"):
        schedule.execute_plan(tmp_path, tmp_path / "results", tmp_path / "scratch", kind="live")
