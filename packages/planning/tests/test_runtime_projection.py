from __future__ import annotations

from repo_planning_bootstrap import runtime_projection


def test_lane_create_operation_declares_value_defaults_and_coercions(monkeypatch) -> None:
    captured = {}

    def fake_create_lane_record(**kwargs):
        captured.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(runtime_projection, "create_lane_record", fake_create_lane_record)

    result = runtime_projection.apply_planning_lane_create_operation(
        {
            "id": "lane-alpha",
            "title": None,
            "target": "repo",
            "outcome": "Done",
            "dry_run": "yes",
        },
        {},
        None,
    )

    assert result == {"ok": True}
    assert captured == {
        "lane_id": "lane-alpha",
        "title": "",
        "target": "repo",
        "parent_decomposition": "",
        "outcome": "Done",
        "purpose": "",
        "proof_strategy": "",
        "expected_planning_revision": "",
        "dry_run": True,
    }


def test_archive_plan_operation_declares_parent_lane_conditional_dispatch(monkeypatch) -> None:
    calls = []

    def fake_archive_parent_lane_closeout(*args, **kwargs):
        calls.append(("parent", args, kwargs))
        return "parent-result"

    def fake_archive_execplan(*args, **kwargs):
        calls.append(("plan", args, kwargs))
        return "plan-result"

    monkeypatch.setattr(runtime_projection, "archive_parent_lane_closeout", fake_archive_parent_lane_closeout)
    monkeypatch.setattr(runtime_projection, "archive_execplan", fake_archive_execplan)

    result = runtime_projection.apply_planning_archive_plan_operation(
        {
            "parent_lane_closeout": "lane-alpha",
            "target": "repo",
            "dry_run": 1,
            "expect_planning_revision": "rev-1",
            "intent_satisfied": "yes",
            "continuation_summary": "Continue",
        },
        {},
        None,
    )

    assert result == "parent-result"
    assert calls == [
        (
            "parent",
            ("lane-alpha",),
            {
                "target": "repo",
                "dry_run": True,
                "expected_planning_revision": "rev-1",
                "intent_satisfied": "yes",
                "intent_evidence": None,
                "closure_reason": None,
                "closure_evidence": None,
                "reopen_trigger": None,
                "discard_summary": None,
                "continuation_summary": "Continue",
            },
        )
    ]


def test_archive_plan_operation_declares_execplan_mapping_when_no_parent_lane(monkeypatch) -> None:
    captured = {}

    def fake_archive_execplan(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return "plan-result"

    monkeypatch.setattr(runtime_projection, "archive_execplan", fake_archive_execplan)

    result = runtime_projection.apply_planning_archive_plan_operation(
        {
            "plan": "plan-alpha",
            "apply_cleanup": "1",
            "prepare_closeout": "",
            "retain_archive": True,
            "closure_decision": "closed",
        },
        {},
        None,
    )

    assert result == "plan-result"
    assert captured == {
        "args": ("plan-alpha",),
        "kwargs": {
            "target": None,
            "dry_run": False,
            "apply_cleanup": True,
            "prepare_closeout": False,
            "closure_decision": "closed",
            "intent_satisfied": None,
            "unsolved_intent": None,
            "intent_evidence": None,
            "closure_reason": None,
            "closure_evidence": None,
            "reopen_trigger": None,
            "discard_summary": None,
            "continuation_summary": None,
            "retain_archive": True,
            "expected_planning_revision": "",
            "decision_point_carry_key": "",
            "prune_decision_point_carry_key": "",
        },
    }


def test_closeout_operation_declares_inverted_retain_archive_flag(monkeypatch) -> None:
    captured = {}

    def fake_closeout_execplan(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return "closed"

    monkeypatch.setattr(runtime_projection, "closeout_execplan", fake_closeout_execplan)

    result = runtime_projection.apply_planning_closeout_operation(
        {"plan": "plan-alpha", "discard_archive": True},
        {},
        None,
    )

    assert result == "closed"
    assert captured["args"] == ("plan-alpha",)
    assert captured["kwargs"]["claim_level"] == "slice"
    assert captured["kwargs"]["intent_status"] == "satisfied"
    assert captured["kwargs"]["residue"] == "none"
    assert captured["kwargs"]["proof_from"] == "last"
    assert captured["kwargs"]["retain_archive"] is False
