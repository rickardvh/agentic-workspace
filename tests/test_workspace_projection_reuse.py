from __future__ import annotations

import json
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from tests.workspace_cli_support import cli


def _allow_contended_git_authority(monkeypatch: Any) -> None:
    """Keep real Git authoritative when xdist briefly delays Windows probes."""

    from agentic_workspace import projection_reuse

    monkeypatch.setattr(projection_reuse, "_GIT_TIMEOUT_SECONDS", 5.0)


def _target(tmp_path: Path) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    return tmp_path


def test_doctor_reuses_unchanged_projection_before_full_builder_and_invalidates_on_dependency_change(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    target = _target(tmp_path)
    capsys.readouterr()

    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0
    first_text = capsys.readouterr().out
    first = json.loads(first_text)
    assert first.get("kind") != "agentic-workspace/unchanged-projection/v1"

    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0
    second_text = capsys.readouterr().out
    second = json.loads(second_text)
    assert second["kind"] == "agentic-workspace/unchanged-projection/v1"
    assert second["work_avoided"]["full_projection_builder_skipped"] is True
    assert second["actionability_delta"] == "unchanged"
    assert second["proof_delta"] == "unchanged"
    assert second["residue_delta"] == "unchanged"
    assert second["next_action_delta"] == "unchanged"
    assert len(second_text) < len(first_text) / 2

    log = target / ".agentic-workspace" / "local" / "logs" / "session" / "command.jsonl"
    log.parent.mkdir(parents=True)
    log.write_text("observational log output\n", encoding="utf-8")
    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0
    after_log = json.loads(capsys.readouterr().out)
    assert after_log["kind"] == "agentic-workspace/unchanged-projection/v1"

    scratch = target / ".agentic-workspace" / "local" / "scratch" / "diagnostic.txt"
    scratch.parent.mkdir(parents=True, exist_ok=True)
    scratch.write_text("runtime-only scratch artifact\n", encoding="utf-8")
    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0
    after_scratch = json.loads(capsys.readouterr().out)
    assert after_scratch["kind"] == "agentic-workspace/unchanged-projection/v1"

    external_evidence = target / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json"
    external_evidence.parent.mkdir(parents=True, exist_ok=True)
    external_evidence.write_text('{"kind": "planning-external-intent-evidence/v1", "items": []}\n', encoding="utf-8")
    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0
    after_evidence = json.loads(capsys.readouterr().out)
    assert after_evidence.get("kind") != "agentic-workspace/unchanged-projection/v1"

    config = target / ".agentic-workspace" / "config.toml"
    config.write_text(config.read_text(encoding="utf-8") + "\n# dependency changed\n", encoding="utf-8")
    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0
    changed = json.loads(capsys.readouterr().out)
    assert changed.get("kind") != "agentic-workspace/unchanged-projection/v1"

    monkeypatch.setenv("AW_PROJECTION_FORCE_REFRESH", "1")
    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0
    forced = json.loads(capsys.readouterr().out)
    assert forced.get("kind") != "agentic-workspace/unchanged-projection/v1"


def test_report_reuses_equivalent_router_projection_and_verbose_forces_full_detail(tmp_path: Path, capsys) -> None:
    target = _target(tmp_path)
    capsys.readouterr()

    assert cli.main(["report", "--target", str(target), "--format", "json"]) == 0
    first_text = capsys.readouterr().out
    assert cli.main(["report", "--target", str(target), "--format", "json"]) == 0
    reused_text = capsys.readouterr().out
    reused = json.loads(reused_text)

    assert reused["kind"] == "workspace-report-router/v1"
    assert reused["projection_reuse"]["status"] == "decision+enrichment-reused"
    assert reused["projection_reuse"]["decision_id"]
    assert len(reused_text) <= len(first_text) + 64

    assert cli.main(["report", "--target", str(target), "--verbose", "--format", "json"]) == 0
    verbose = json.loads(capsys.readouterr().out)
    assert verbose["kind"] != "agentic-workspace/unchanged-projection/v1"


def test_start_implement_and_proof_reuse_each_surface_admitted_decision(tmp_path: Path, capsys) -> None:
    target = _target(tmp_path)
    changed = ".agentic-workspace/config.toml"
    capsys.readouterr()

    commands = [
        ["start", "--target", str(target), "--changed", changed, "--task", "Keep the route narrow.", "--format", "json"],
        [
            "start",
            "--target",
            str(target),
            "--changed",
            changed,
            "--task",
            "Keep the route narrow.",
            "--select",
            "planning_safety_gate",
            "--format",
            "json",
        ],
        ["implement", "--target", str(target), "--changed", changed, "--task", "Keep the route narrow.", "--format", "json"],
        [
            "implement",
            "--target",
            str(target),
            "--changed",
            changed,
            "--task",
            "Keep the route narrow.",
            "--select",
            "verification",
            "--format",
            "json",
        ],
        ["proof", "--target", str(target), "--changed", changed, "--task", "Keep the route narrow.", "--format", "json"],
        ["summary", "--target", str(target), "--select", "planning_revision", "--format", "json"],
        ["report", "--target", str(target), "--section", "closeout_trust", "--format", "json"],
    ]
    for command in commands:
        assert cli.main(command) == 0
        cold = json.loads(capsys.readouterr().out)
        assert cold.get("kind") != "agentic-workspace/unchanged-projection/v1"
        assert len(json.dumps(cold, indent=2).encode()) <= 65536

        assert cli.main(command) == 0
        warm = json.loads(capsys.readouterr().out)
        assert warm["kind"] == cold["kind"]
        exposes_decision_receipt = "--select" in command or command[0] not in {"start", "implement"}
        if not exposes_decision_receipt:
            if command[0] == "implement":
                assert "projection_reuse" not in cold
                assert "projection_reuse" not in warm
            else:
                assert not str(cold.get("projection_reuse", {}).get("status", "")).startswith("decision+")
                assert not str(warm.get("projection_reuse", {}).get("status", "")).startswith("decision+")
            continue
        compact_receipt = cold["projection_reuse"]
        assert compact_receipt == {
            "decision_id": compact_receipt["decision_id"],
            "status": "decision+enrichment-rebuilt",
            "freshness": "current",
            "authority": "agentic_workspace.operating_decision.compile_operating_decision",
            "projection_input_revision": compact_receipt["projection_input_revision"],
        }
        assert compact_receipt["decision_id"]
        assert compact_receipt["projection_input_revision"].startswith("sha256:")
        assert not any(field.startswith("projection_decision_") for field in cold.get("context", {}))
        assert warm["projection_reuse"] == {
            "decision_id": compact_receipt["decision_id"],
            "status": "decision+enrichment-reused",
            "freshness": "current",
            "authority": "agentic_workspace.operating_decision.compile_operating_decision",
            "projection_input_revision": compact_receipt["projection_input_revision"],
        }


def test_selected_closeout_and_planning_projections_are_bounded_and_warm_reused(tmp_path: Path, capsys, monkeypatch) -> None:
    _allow_contended_git_authority(monkeypatch)
    target = _target(tmp_path)
    capsys.readouterr()
    commands = [
        ["report", "--target", str(target), "--section", "closeout_trust", "--format", "json"],
        ["summary", "--target", str(target), "--select", "planning_revision", "--format", "json"],
    ]
    for command in commands:
        started = time.perf_counter()
        assert cli.main(command) == 0
        cold_text = capsys.readouterr().out
        cold_elapsed = time.perf_counter() - started
        assert len(cold_text.encode()) <= 65536

        started = time.perf_counter()
        assert cli.main(command) == 0
        warm_text = capsys.readouterr().out
        warm_elapsed = time.perf_counter() - started
        warm = json.loads(warm_text)
        assert warm["projection_reuse"]["status"] == "decision+enrichment-reused"
        assert len(warm_text.encode()) <= 65536
        assert cold_elapsed < 2.0
        assert warm_elapsed < 2.0


def test_query_shaped_public_selectors_measure_cold_and_warm_reuse_cost(tmp_path: Path, capsys, monkeypatch) -> None:
    from agentic_workspace import projection_reuse

    _allow_contended_git_authority(monkeypatch)
    target = _target(tmp_path)
    memory_root = target / ".agentic-workspace" / "memory" / "repo"
    memory_root.mkdir(parents=True, exist_ok=True)
    (memory_root / "manifest.toml").write_text("schema_version = 1\n", encoding="utf-8")
    (memory_root / "index.md").write_text("# Memory\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=target, check=True)
    subprocess.run(
        ["git", "-c", "user.name=AW Tests", "-c", "user.email=aw-tests@example.invalid", "commit", "-qm", "fixture"],
        cwd=target,
        check=True,
    )
    capsys.readouterr()
    measured: list[dict[str, Any]] = []
    real_digest = projection_reuse.dependency_digest

    def measured_digest(**kwargs: Any):
        result = real_digest(**kwargs)
        measured.append(
            {
                "operation": kwargs["operation"],
                "query": dict(kwargs["query"]),
                "state_read_count": result.state_read_count,
                "dependencies": list(result.dependencies),
            }
        )
        return result

    monkeypatch.setattr(projection_reuse, "dependency_digest", measured_digest)
    commands = [
        ["summary", "--target", str(target), "--select", "planning_record", "--format", "json"],
        ["summary", "--target", str(target), "--select", "planning_record,memory_decision_packet", "--format", "json"],
    ]
    observations: list[dict[str, Any]] = []
    for command in commands:
        started = time.perf_counter()
        assert cli.main(command) == 0
        cold_text = capsys.readouterr().out
        cold_elapsed_ms = (time.perf_counter() - started) * 1000
        cold = json.loads(cold_text)

        started = time.perf_counter()
        assert cli.main(command) == 0
        warm_text = capsys.readouterr().out
        warm_elapsed_ms = (time.perf_counter() - started) * 1000
        warm = json.loads(warm_text)
        observations.append(
            {
                "cold_elapsed_ms": cold_elapsed_ms,
                "warm_elapsed_ms": warm_elapsed_ms,
                "cold_bytes": len(cold_text.encode()),
                "warm_bytes": len(warm_text.encode()),
            }
        )

        assert cold["projection_reuse"]["status"] == "decision+enrichment-rebuilt"
        assert warm["projection_reuse"] == {
            **cold["projection_reuse"],
            "status": "decision+enrichment-reused",
        }
        assert list(cold["values"]) == command[command.index("--select") + 1].split(",")

    assert len(measured) >= len(commands) * 2
    assert all(item["state_read_count"] == len(item["dependencies"]) + 3 for item in measured)
    assert len({json.dumps(item["query"], sort_keys=True) for item in measured}) == len(commands)
    by_selector = {item["query"]["select"]: item for item in measured}
    baseline = by_selector["planning_record"]
    enriched = by_selector["planning_record,memory_decision_packet"]
    enrichment_delta = set(enriched["dependencies"]) - set(baseline["dependencies"])
    assert enrichment_delta == {
        ".agentic-workspace/memory/repo/index.md",
        ".agentic-workspace/memory/repo/manifest.toml",
    }
    assert enriched["state_read_count"] - baseline["state_read_count"] == len(enrichment_delta)
    assert all(item["cold_elapsed_ms"] < 2_000 and item["warm_elapsed_ms"] < 2_000 for item in observations)
    assert all(item["cold_bytes"] <= 65_536 and item["warm_bytes"] <= 65_536 for item in observations)


def test_invalidation_reasons_cover_each_admitted_authority_input_exactly() -> None:
    from agentic_workspace.projection_reuse import _invalidation_reasons

    previous = {
        "branch": "main",
        "head": "a",
        "task": "a",
        "selected_owner": "a",
        "planning": "a",
        "changed_paths": "a",
        "proof_subject": "a",
        "runtime_compatibility": "a",
        "external_freshness": "a",
        "worktree": "a",
    }
    expected = {
        "branch": "branch-changed",
        "head": "head-changed",
        "task": "task-changed",
        "selected_owner": "selected-owner-changed",
        "planning": "planning-revision-changed",
        "changed_paths": "changed-paths-changed",
        "proof_subject": "proof-subject-changed",
        "runtime_compatibility": "runtime-compatibility-changed",
        "external_freshness": "external-freshness-changed",
        "worktree": "admitted-worktree-changed",
    }
    for field, reason in expected.items():
        current = dict(previous)
        current[field] = "b"
        assert _invalidation_reasons(previous, current) == [reason]


def _standard_constituent_revisions() -> dict[str, str]:
    return {
        "branch": "codex/stack-child",
        "head": "head-a",
        "base": "base-a",
        "task": "task-a",
        "selected_owner": "owner-a",
        "planning": "planning-a",
        "changed_paths": "paths-a",
        "proof_subject": "proof-a",
        "runtime_compatibility": "runtime-a",
        "route_inputs": "route-a",
        "verification_inputs": "verification-a",
        "proof_inputs": "proof-inputs-a",
        "closeout_inputs": "closeout-a",
        "runtime_mirror_inputs": "mirror-a",
    }


def test_constituent_identity_keeps_stack_position_observational_by_default() -> None:
    from agentic_workspace.projection_reuse import (
        ProjectionConstituentSpec,
        build_projection_constituent_identity,
        compare_projection_constituent_identity,
    )

    spec = ProjectionConstituentSpec("runtime_mirror", ("runtime_mirror_inputs",))
    previous = build_projection_constituent_identity(
        spec=spec,
        input_revisions={
            "branch": "codex/parent",
            "head": "head-a",
            "base": "base-a",
            "runtime_mirror_inputs": "mirror-a",
        },
    )
    current = build_projection_constituent_identity(
        spec=spec,
        input_revisions={
            "branch": "codex/child",
            "head": "head-b",
            "base": "base-b",
            "runtime_mirror_inputs": "mirror-a",
        },
    )

    assert previous["input_revision"] == current["input_revision"]
    assert previous["observed_context_revision"] != current["observed_context_revision"]
    comparison = compare_projection_constituent_identity(previous=previous, current=current)
    assert comparison["status"] == "reused"
    assert comparison["freshness"] == "current"
    assert [item["reason"] for item in comparison["context_delta"]] == ["base-changed", "branch-changed", "head-changed"]
    assert all(item["invalidates_constituent"] is False for item in comparison["context_delta"])


def test_constituent_must_explicitly_declare_head_before_stack_movement_invalidates_it() -> None:
    from agentic_workspace.projection_reuse import (
        ProjectionConstituentSpec,
        build_projection_constituent_identity,
        compare_projection_constituent_identity,
    )

    spec = ProjectionConstituentSpec("exact_head_owner", ("head", "owner_inputs"))
    previous = build_projection_constituent_identity(
        spec=spec,
        input_revisions={"head": "head-a", "owner_inputs": "inputs-a"},
    )
    current = build_projection_constituent_identity(
        spec=spec,
        input_revisions={"head": "head-b", "owner_inputs": "inputs-a"},
    )

    comparison = compare_projection_constituent_identity(previous=previous, current=current)
    assert comparison["status"] == "invalidated"
    assert comparison["changed_dependency_fields"] == ["head"]
    assert comparison["invalidation_reasons"] == ["head-changed"]
    assert comparison["context_delta"] == [{"field": "head", "reason": "head-changed", "invalidates_constituent": True}]


def test_standard_constituents_invalidate_only_declared_semantic_dependents() -> None:
    from agentic_workspace.projection_reuse import (
        build_standard_projection_constituent_identities,
        compare_projection_constituent_sets,
    )

    previous_revisions = _standard_constituent_revisions()
    previous = build_standard_projection_constituent_identities(input_revisions=previous_revisions)
    expected_by_change = {
        "planning": ["closeout_trust", "route"],
        "proof_subject": ["closeout_trust", "selected_proof"],
        "runtime_mirror_inputs": ["runtime_mirror"],
        "changed_paths": ["closeout_trust", "route", "selected_proof", "verification"],
    }
    for field, expected_invalidated in expected_by_change.items():
        current_revisions = {**previous_revisions, field: f"{field}-b", "head": f"head-for-{field}"}
        current = build_standard_projection_constituent_identities(input_revisions=current_revisions)
        delta = compare_projection_constituent_sets(previous=previous, current=current)

        assert delta["status"] == "partially-invalidated"
        assert delta["invalidated_constituents"] == expected_invalidated
        assert delta["focused_rebuild_constituents"] == expected_invalidated
        assert delta["broad_rebuild_required"] is False
        for constituent_id, comparison in delta["constituents"].items():
            if constituent_id in expected_invalidated:
                assert comparison["status"] == "invalidated"
                assert comparison["required_action"] == "build-constituent"
            else:
                assert comparison["status"] == "reused"
                assert comparison["required_action"] == "reuse-owner-result"
                assert comparison["context_delta"] == [{"field": "head", "reason": "head-changed", "invalidates_constituent": False}]


def test_constituent_identity_degrades_conservatively_when_required_evidence_is_ambiguous() -> None:
    from agentic_workspace.projection_reuse import (
        ProjectionConstituentSpec,
        build_projection_constituent_identity,
        compare_projection_constituent_sets,
    )

    spec = ProjectionConstituentSpec("verification", ("changed_paths", "verification_inputs"))
    previous = build_projection_constituent_identity(
        spec=spec,
        input_revisions={"changed_paths": "paths-a", "verification_inputs": "verification-a"},
    )
    current = build_projection_constituent_identity(
        spec=spec,
        input_revisions={"changed_paths": "paths-a", "verification_inputs": "unavailable"},
    )
    delta = compare_projection_constituent_sets(
        previous={"verification": previous},
        current={"verification": current},
    )

    assert current["status"] == "unavailable"
    assert current["identity_id"] == ""
    assert current["unavailable_dependency_fields"] == ["verification_inputs"]
    assert delta["status"] == "unknown"
    assert delta["unknown_constituents"] == ["verification"]
    assert delta["focused_rebuild_constituents"] == ["verification"]
    assert delta["broad_rebuild_required"] is False
    assert delta["constituents"]["verification"]["invalidation_reasons"] == ["unavailable:verification_inputs"]


def test_constituent_set_marks_only_unrecorded_owner_for_initial_build() -> None:
    from agentic_workspace.projection_reuse import (
        build_standard_projection_constituent_identities,
        compare_projection_constituent_sets,
    )

    current = build_standard_projection_constituent_identities(input_revisions=_standard_constituent_revisions())
    previous = {key: value for key, value in current.items() if key != "runtime_mirror"}
    delta = compare_projection_constituent_sets(previous=previous, current=current)

    assert delta["status"] == "partially-invalidated"
    assert delta["invalidated_constituents"] == ["runtime_mirror"]
    assert delta["focused_rebuild_constituents"] == ["runtime_mirror"]
    assert delta["constituents"]["runtime_mirror"]["status"] == "not-recorded"
    assert delta["constituents"]["runtime_mirror"]["invalidation_reasons"] == ["prior-identity-missing"]


def test_cache_record_consumes_surface_decision_without_a_compiler_dependency(tmp_path: Path) -> None:
    from agentic_workspace import projection_reuse
    from agentic_workspace.operating_decision import (
        admit_projection_surface_decision_input,
        consume_projection_surface_decision_input,
        finalize_projection_surface_operating_decision,
        materialize_projection_under_decision_input,
    )

    target = _target(tmp_path)
    query = {"changed": [".agentic-workspace/config.toml"]}
    context = projection_reuse.prepare_projection_reuse(
        root=target,
        operation="report",
        query=query,
    )
    admitted_input = admit_projection_surface_decision_input(input_revisions=context["decision_input_revisions"], consumer="report")
    _cached, context = projection_reuse.lookup_projection_reuse(
        root=target,
        operation="report",
        query=query,
        full_detail_command="report --verbose",
        context=context,
        admitted_input=admitted_input,
    )
    builder_decisions: list[dict[str, Any]] = []

    def build_payload(decision_input: dict[str, Any]) -> dict[str, Any]:
        builder_decisions.append(decision_input)
        return consume_projection_surface_decision_input(
            payload={"status": "CONTINUE", "next_action": {"action": "inspect"}},
            admitted_input=decision_input,
            consumer="report",
        )

    payload = materialize_projection_under_decision_input(
        builder=build_payload,
        admitted_input=admitted_input,
        consumer="report",
    )
    payload, operating_decision = finalize_projection_surface_operating_decision(
        payload=payload, admitted_input=admitted_input, consumer="report"
    )
    assert builder_decisions == [admitted_input]
    assert not hasattr(projection_reuse, "compile_operating_decision")
    reuse = projection_reuse.record_projection_reuse(
        root=target,
        operation="report",
        query=query,
        context=context,
        payload=payload,
        operating_decision=operating_decision,
    )

    assert reuse["operating_decision"]["decision_id"] == operating_decision["decision_id"]


def test_builder_must_consume_input_and_mismatched_posture_cannot_be_stamped() -> None:
    from agentic_workspace.operating_decision import (
        admit_projection_surface_decision_input,
        bind_projection_surface_operating_decision,
        compile_projection_surface_operating_decision,
        finalize_projection_surface_operating_decision,
        materialize_projection_under_decision_input,
    )

    admitted_input = admit_projection_surface_decision_input(input_revisions={"head": "a", "selected_owner": "owner-a"}, consumer="proof")
    ignored = materialize_projection_under_decision_input(
        builder=lambda _decision_input: {"status": "BLOCKED", "next_action": {"action": "repair"}},
        admitted_input=admitted_input,
        consumer="proof",
    )
    ignored, ignored_decision = finalize_projection_surface_operating_decision(
        payload=ignored, admitted_input=admitted_input, consumer="proof"
    )
    assert ignored_decision == {}
    assert "projection_decision_authority" not in ignored.get("context", {})

    blocked_payload = {
        "status": "BLOCKED",
        "next_action": {"action": "repair"},
        "context": {
            "projection_decision_input_consumption": {
                "status": "consumed",
                "consumer": "proof",
                "input_id": admitted_input["input_id"],
                "admitted_input_revision": admitted_input["admitted_input_revision"],
                "material_input_revision": admitted_input["material_input_revision"],
                "used_material_input_revision": admitted_input["material_input_revision"],
            }
        },
    }
    blocked_decision = compile_projection_surface_operating_decision(
        payload=blocked_payload, admitted_input=admitted_input, consumer="proof"
    )
    mismatched = {
        **blocked_payload,
        "status": "CONTINUE",
        "next_action": {"action": "implement"},
        "context": dict(blocked_payload["context"]),
    }
    mismatched = bind_projection_surface_operating_decision(
        payload=mismatched,
        admitted_input=admitted_input,
        operating_decision=blocked_decision,
        consumer="proof",
    )
    assert mismatched["context"]["projection_decision_authority"]["status"] == "rejected"
    assert mismatched["context"]["projection_decision_authority"]["decision_id"] == blocked_decision["decision_id"]


def test_builder_material_input_mismatch_rejects_consumption_and_authority() -> None:
    from agentic_workspace.operating_decision import (
        admit_projection_surface_decision_input,
        attach_projection_surface_decision_input_consumption,
        finalize_projection_surface_operating_decision,
        projection_surface_builder_inputs,
    )

    admitted_input = admit_projection_surface_decision_input(
        input_revisions={"head": "a", "selected_owner": "owner-a"},
        consumer="start",
        material_inputs={"task": "admitted task", "changed": ["a.py"]},
    )
    builder_inputs, consumption = projection_surface_builder_inputs(
        admitted_input=admitted_input,
        consumer="start",
        required_fields=("task", "changed"),
    )
    assert builder_inputs == {"changed": ["a.py"], "task": "admitted task"}

    altered = attach_projection_surface_decision_input_consumption(
        payload={"status": "CONTINUE", "next_action": {"action": "inspect"}},
        consumption=consumption,
        used_material_inputs={"task": "different task", "changed": ["a.py"]},
    )
    altered, altered_decision = finalize_projection_surface_operating_decision(
        payload=altered,
        admitted_input=admitted_input,
        consumer="start",
    )

    assert altered_decision == {}
    assert altered["context"]["projection_decision_input_consumption"]["status"] == "rejected"
    assert "projection_decision_authority" not in altered["context"]


def test_each_ordinary_surface_rejects_selected_owner_race_after_builder(tmp_path: Path, capsys, monkeypatch) -> None:
    from agentic_workspace import workspace_runtime_core, workspace_runtime_implement, workspace_runtime_startup

    target = _target(tmp_path)
    capsys.readouterr()
    changed = ".agentic-workspace/config.toml"
    cases = [
        (
            "start",
            workspace_runtime_startup,
            ["start", "--target", str(target), "--changed", changed, "--task", "Race proof.", "--format", "json"],
        ),
        (
            "implement",
            workspace_runtime_implement,
            ["implement", "--target", str(target), "--changed", changed, "--task", "Race proof.", "--format", "json"],
        ),
        (
            "proof",
            workspace_runtime_core,
            ["proof", "--target", str(target), "--changed", changed, "--task", "Race proof.", "--format", "json"],
        ),
        (
            "summary",
            workspace_runtime_core,
            ["summary", "--target", str(target), "--select", "planning_revision", "--format", "json"],
        ),
        (
            "report",
            workspace_runtime_core,
            ["report", "--target", str(target), "--section", "closeout_trust", "--format", "json"],
        ),
    ]

    for operation, runtime_module, command in cases:
        real_prepare = runtime_module.prepare_projection_reuse
        matching_calls = 0

        def racing_prepare(*args: Any, **kwargs: Any) -> dict[str, Any]:
            nonlocal matching_calls
            context = real_prepare(*args, **kwargs)
            if kwargs.get("operation") != operation:
                return context
            matching_calls += 1
            revisions = dict(context.get("decision_input_revisions", {}))
            revisions["selected_owner"] = "owner-before" if matching_calls == 1 else "owner-after"
            return {**context, "decision_input_revisions": revisions}

        with monkeypatch.context() as scoped:
            scoped.setattr(runtime_module, "prepare_projection_reuse", racing_prepare)
            assert cli.main(command) == 0
        payload = json.loads(capsys.readouterr().out)
        assert "context" in payload, operation
        context = payload["context"]
        assert context["projection_decision_input_revalidation"]["status"] == "stale"
        assert context["projection_decision_input_revalidation"]["changed_fields"] == ["selected_owner"]
        assert context["projection_decision_input_consumption"]["status"] == "rejected"
        assert "projection_decision_authority" not in context


def test_all_admitted_authority_classes_fail_closed_when_they_change_during_materialization() -> None:
    from agentic_workspace.operating_decision import (
        admit_projection_surface_decision_input,
        consume_projection_surface_decision_input,
        finalize_projection_surface_operating_decision,
        materialize_projection_under_decision_input,
    )

    base_revisions = {
        "branch": "branch-a",
        "head": "head-a",
        "task": "task-a",
        "selected_owner": "owner-a",
        "planning": "planning-a",
        "changed_paths": "changed-a",
        "proof_subject": "proof-a",
        "runtime_compatibility": "runtime-a",
    }
    for consumer in ("start", "summary", "implement", "proof", "report"):
        for field in base_revisions:
            admitted_input = admit_projection_surface_decision_input(
                input_revisions=base_revisions,
                consumer=consumer,
            )
            current_revisions = {**base_revisions, field: f"{field}-b"}
            payload = materialize_projection_under_decision_input(
                builder=lambda decision_input: consume_projection_surface_decision_input(
                    payload={"status": "CONTINUE", "next_action": {"action": "inspect"}},
                    admitted_input=decision_input,
                    consumer=consumer,
                ),
                admitted_input=admitted_input,
                consumer=consumer,
                revalidate_input_revisions=lambda: current_revisions,
            )
            payload, operating_decision = finalize_projection_surface_operating_decision(
                payload=payload,
                admitted_input=admitted_input,
                consumer=consumer,
            )
            assert operating_decision == {}
            revalidation = payload["context"]["projection_decision_input_revalidation"]
            assert revalidation["status"] == "stale"
            assert revalidation["changed_fields"] == [field]


def test_progress_heartbeat_and_cooperative_cancellation_are_bounded(tmp_path: Path, capsys) -> None:
    from agentic_workspace.projection_reuse import ProjectionBudget, ProjectionProgress

    target = _target(tmp_path)
    capsys.readouterr()
    cancel = target / ".agentic-workspace/local/cancellation/proof.cancel"
    cancel.parent.mkdir(parents=True, exist_ok=True)
    cancel.write_text("cancel\n", encoding="utf-8")
    budget = ProjectionBudget(long_command_threshold_seconds=0.0, progress_interval_seconds=0.01)
    with ProjectionProgress(root=target, operation="proof", budget=budget) as progress:
        time.sleep(0.03)
        contract = progress.contract()
    heartbeats = [json.loads(line) for line in capsys.readouterr().err.splitlines()]
    assert 1 <= len(heartbeats) <= 5
    assert heartbeats[0]["status"] == "cancel-requested"
    assert contract["status"] == "cancel-requested"
    assert contract["cancel"]["path"] == ".agentic-workspace/local/cancellation/proof.cancel"


def test_start_stops_active_builder_after_cancellation_and_skips_later_stages(tmp_path: Path, capsys, monkeypatch) -> None:
    import agentic_workspace.workspace_runtime_startup as startup_runtime

    target = _target(tmp_path)
    capsys.readouterr()
    started = threading.Event()
    stopped = threading.Event()
    side_effect_ran = threading.Event()

    def slow_start_payload(**_kwargs):
        from agentic_workspace.projection_reuse import projection_cancellation_checkpoint

        started.set()
        try:
            while True:
                projection_cancellation_checkpoint()
        finally:
            stopped.set()
        side_effect_ran.set()  # pragma: no cover - cancellation must unwind first
        return {"kind": "late-start-projection/v1", "status": "complete"}  # pragma: no cover

    monkeypatch.setattr(startup_runtime, "_start_payload", slow_start_payload)
    cancel = target / ".agentic-workspace/local/cancellation/start.cancel"

    def request_cancel() -> None:
        assert started.wait(timeout=1)
        cancel.parent.mkdir(parents=True, exist_ok=True)
        cancel.write_text("cancel\n", encoding="utf-8")

    requester = threading.Thread(target=request_cancel)
    requester.start()
    before = time.perf_counter()
    assert cli.main(["start", "--target", str(target), "--format", "json"]) == 0
    elapsed = time.perf_counter() - before
    payload = json.loads(capsys.readouterr().out)
    requester.join(timeout=1)

    assert elapsed < 1
    assert stopped.wait(timeout=0.2)
    assert side_effect_ran.is_set() is False
    assert not any(thread.name == "aw-start-build-start-projection" for thread in threading.enumerate())
    assert payload["kind"] == "agentic-workspace/projection-cancelled/v1"
    assert payload["cancelled_stage"] == "build-start-projection"
    assert payload["cancellation_observed_during_work"] is True
    assert payload["later_stages_skipped"] is True
    assert payload["active_stage_stopped"] is True


def test_selected_summary_and_report_cancellation_return_bounded_envelopes(tmp_path: Path, capsys) -> None:
    target = _target(tmp_path)
    capsys.readouterr()
    commands = [
        ("summary", ["summary", "--target", str(target), "--select", "planning_revision", "--format", "json"]),
        ("report", ["report", "--target", str(target), "--format", "json"]),
        ("report", ["report", "--target", str(target), "--section", "closeout_trust", "--format", "json"]),
    ]
    for operation, command in commands:
        cancel = target / ".agentic-workspace" / "local" / "cancellation" / f"{operation}.cancel"
        cancel.parent.mkdir(parents=True, exist_ok=True)
        cancel.write_text("cancel\n", encoding="utf-8")
        assert cli.main(command) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["kind"] == "agentic-workspace/projection-cancelled/v1"
        assert payload["status"] == "cancelled"
        cancel.unlink()


def test_serialization_budget_preserves_semantic_answer_shape_and_bounds_inventories() -> None:
    from agentic_workspace.projection_reuse import enforce_projection_serialization_budget

    payload = {
        "kind": "workspace-report-answer/v1",
        "answer": {
            "installed_state_residue": {"status": "separate_maintenance_residue"},
            "inventory": ["x" * 500 for _ in range(1000)],
        },
    }
    reuse_result = {
        "status": "rebuilt",
        "decision_id": "operating-decision:test",
        "observed_cost": {"serialized_bytes": 500000},
        "budgets": {"serialization_status": "exceeded", "serialization_budget_bytes": 65536},
    }

    bounded = enforce_projection_serialization_budget(
        payload=payload,
        operation="report",
        reuse_result=reuse_result,
        full_detail_command="agentic-workspace report --target . --verbose --format json",
    )

    assert bounded["kind"] == payload["kind"]
    assert bounded["answer"]["installed_state_residue"] == payload["answer"]["installed_state_residue"]
    assert bounded["serialization_budget"]["inventories_materialized_in_response"] is False
    assert len(json.dumps(bounded, indent=2).encode()) <= 65536


def test_serialization_budget_preserves_selected_report_values() -> None:
    from agentic_workspace.projection_reuse import enforce_projection_serialization_budget

    payload = {
        "kind": "agentic-workspace/selected-output/v1",
        "values": {
            "answer": {
                "trust": "verified",
                "inventory": ["x" * 500 for _ in range(1000)],
            }
        },
    }
    reuse_result = {
        "status": "rebuilt",
        "decision_id": "operating-decision:test",
        "observed_cost": {"serialized_bytes": 500000},
        "budgets": {"serialization_status": "exceeded", "serialization_budget_bytes": 65536},
    }

    bounded = enforce_projection_serialization_budget(
        payload=payload,
        operation="report",
        reuse_result=reuse_result,
        full_detail_command="agentic-workspace report --target . --verbose --format json",
    )

    assert bounded["values"]["answer"]["trust"] == "verified"
    assert len(json.dumps(bounded, indent=2).encode()) <= 65536


def test_summary_reuses_unchanged_projection_and_preserves_decision_deltas(tmp_path: Path, capsys, monkeypatch) -> None:
    target = _target(tmp_path)
    capsys.readouterr()

    assert cli.main(["summary", "--target", str(target), "--format", "json"]) == 0
    first_text = capsys.readouterr().out
    assert cli.main(["summary", "--target", str(target), "--format", "json"]) == 0
    reused_text = capsys.readouterr().out
    reused = json.loads(reused_text)

    assert reused["kind"] == "planning-summary/v1"
    assert reused["projection_reuse"]["status"] == "decision+enrichment-reused"
    assert reused["projection_reuse"]["decision_id"]
    assert len(reused_text) <= len(first_text) + 64

    planning_state = target / ".agentic-workspace" / "planning" / "state.toml"
    planning_state.write_text(
        "[todo]\nactive_items = []\nqueued_items = []\n\n[roadmap]\nlanes = []\ncandidates = []\n# decision relevant planning change\n",
        encoding="utf-8",
    )
    assert cli.main(["summary", "--target", str(target), "--format", "json"]) == 0
    changed = json.loads(capsys.readouterr().out)
    assert changed.get("kind") != "agentic-workspace/unchanged-projection/v1"

    assert cli.main(["summary", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()
    monkeypatch.setenv("AW_PROJECTION_FORCE_REFRESH", "1")
    assert cli.main(["summary", "--target", str(target), "--format", "json"]) == 0
    forced = json.loads(capsys.readouterr().out)
    assert forced.get("kind") != "agentic-workspace/unchanged-projection/v1"


def test_dependency_digest_tracks_commit_relevant_worktree_and_contract_but_ignores_irrelevant_file(tmp_path: Path, monkeypatch) -> None:
    from agentic_workspace import projection_reuse

    target = _target(tmp_path)
    first, _ = projection_reuse.dependency_digest(root=target, operation="doctor", query={})
    (target / "notes.txt").write_text("irrelevant\n", encoding="utf-8")
    irrelevant, _ = projection_reuse.dependency_digest(root=target, operation="doctor", query={})
    assert irrelevant == first
    (target / "src/agentic_workspace/new_runtime.py").parent.mkdir(parents=True, exist_ok=True)
    (target / "src/agentic_workspace/new_runtime.py").write_text("VALUE = 1\n", encoding="utf-8")
    relevant, _ = projection_reuse.dependency_digest(root=target, operation="doctor", query={})
    assert relevant != first
    monkeypatch.setattr(projection_reuse, "_CACHE_CONTRACT_VERSION", 99)
    contract, _ = projection_reuse.dependency_digest(root=target, operation="doctor", query={})
    assert contract != relevant


def test_dependency_digest_invalidates_when_branch_revision_changes(tmp_path: Path) -> None:
    from agentic_workspace import projection_reuse

    target = _target(tmp_path)
    first, _ = projection_reuse.dependency_digest(root=target, operation="summary", query={})
    (target / ".git" / "HEAD").write_text("ref: refs/heads/feature\n", encoding="utf-8")
    (target / "notes.txt").write_text("not summary relevant\n", encoding="utf-8")
    changed, _ = projection_reuse.dependency_digest(root=target, operation="summary", query={})

    assert changed != first


def test_dependency_digest_excludes_crash_recovery_worktrees_and_virtualenvs(tmp_path: Path) -> None:
    from agentic_workspace import projection_reuse

    target = _target(tmp_path)
    first, first_dependencies = projection_reuse.dependency_digest(root=target, operation="report", query={})
    runtime_file = (
        target
        / ".agentic-workspace"
        / "local"
        / "chatgpt-review-worktrees"
        / "pr-9999"
        / ".venv"
        / "Lib"
        / "site-packages"
        / "dependency.py"
    )
    runtime_file.parent.mkdir(parents=True)
    runtime_file.write_text("VALUE = 1\n", encoding="utf-8")

    unchanged, dependencies = projection_reuse.dependency_digest(root=target, operation="report", query={})

    assert unchanged == first
    assert dependencies == first_dependencies
    assert not any("chatgpt-review-worktrees" in path or "/.venv/" in path for path in dependencies)


def test_dependency_digest_fails_open_when_git_probe_times_out(tmp_path: Path, monkeypatch) -> None:
    from agentic_workspace import projection_reuse

    target = _target(tmp_path)

    def _timeout(*_args, **_kwargs):
        return projection_reuse.GitProbeResult("unavailable", reason="Git revision probe timed out")

    monkeypatch.setattr(projection_reuse, "_git", _timeout)

    result = projection_reuse.dependency_digest(root=target, operation="report", query={})
    digest, dependencies = result

    assert digest
    assert ".agentic-workspace/config.toml" in dependencies
    assert result.status == "unavailable"
    assert result.findings[0]["section"] == "projection_branch_revision"


def test_admitted_revision_computation_fails_open_above_content_read_budget(tmp_path: Path) -> None:
    from agentic_workspace import projection_reuse

    target = _target(tmp_path)
    changed = [f"src/agentic_workspace/generated_{index}.py" for index in range(100)]
    cached, context = projection_reuse.lookup_projection_reuse(
        root=target,
        operation="report",
        query={"changed": changed},
        full_detail_command="agentic-workspace report --target . --verbose --format json",
    )

    assert cached is None
    assert len(context["dependencies"]) <= 64 + 32
    assert context["dependency_status"] == "unavailable"
    assert context["degraded_findings"][-1]["section"] == "projection_changed_path_revision"
    result = projection_reuse.record_projection_reuse(
        root=target,
        operation="report",
        query={"changed": changed},
        context=context,
        payload={"status": "ok"},
        operating_decision={},
    )
    assert result == {}


def test_report_git_timeout_disables_reuse_and_names_failed_probe(tmp_path: Path, capsys, monkeypatch) -> None:
    from agentic_workspace import projection_reuse

    target = _target(tmp_path)
    capsys.readouterr()
    assert cli.main(["report", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()

    def _timeout(*_args, **_kwargs):
        return projection_reuse.GitProbeResult("unavailable", reason="Git revision probe timed out")

    monkeypatch.setattr(projection_reuse, "_git", _timeout)

    assert cli.main(["report", "--target", str(target), "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload.get("kind") != "agentic-workspace/unchanged-projection/v1"
    finding = payload["projection_reuse"]["findings"][0]
    assert finding["section"] == "projection_branch_revision"
    assert finding["status"] == "unavailable"


def test_volatile_projection_fails_open_and_cache_is_bounded(tmp_path: Path) -> None:
    from agentic_workspace.operating_decision import (
        admit_projection_surface_decision_input,
        consume_projection_surface_decision_input,
        finalize_projection_surface_operating_decision,
    )
    from agentic_workspace.projection_reuse import lookup_projection_reuse, prepare_projection_reuse, record_projection_reuse

    target = _target(tmp_path)
    cached, context = lookup_projection_reuse(
        root=target, operation="report", query={"external_freshness_required": True}, full_detail_command="report"
    )
    assert cached is None and context["volatile"] is True
    for index in range(40):
        query = {"index": index}
        context = prepare_projection_reuse(root=target, operation="doctor", query=query)
        admitted_input = admit_projection_surface_decision_input(input_revisions=context["decision_input_revisions"], consumer="doctor")
        cached, context = lookup_projection_reuse(
            root=target,
            operation="doctor",
            query=query,
            full_detail_command="doctor",
            context=context,
            admitted_input=admitted_input,
        )
        payload = consume_projection_surface_decision_input(payload={"status": "ok"}, admitted_input=admitted_input, consumer="doctor")
        payload, operating_decision = finalize_projection_surface_operating_decision(
            payload=payload, admitted_input=admitted_input, consumer="doctor"
        )
        record_projection_reuse(
            root=target,
            operation="doctor",
            query={"index": index},
            context=context,
            payload=payload,
            operating_decision=operating_decision,
        )
    assert len(list((target / ".agentic-workspace/local/projection-cache").glob("*.json"))) <= 32


def test_absent_surface_admission_disables_reuse_without_synthesizing_a_decision(tmp_path: Path) -> None:
    from agentic_workspace.operating_decision import (
        admit_projection_surface_decision_input,
        attach_projection_surface_decision_input_consumption,
        projection_surface_builder_inputs,
    )
    from agentic_workspace.projection_reuse import lookup_projection_reuse, prepare_projection_reuse, record_projection_reuse

    target = _target(tmp_path)
    query = {"profile": "router"}
    context = prepare_projection_reuse(root=target, operation="report", query=query)
    admitted_input = admit_projection_surface_decision_input(input_revisions={}, consumer="report")
    material_inputs, consumption = projection_surface_builder_inputs(
        admitted_input=admitted_input,
        consumer="report",
        required_fields=("task", "changed"),
    )
    rendered = attach_projection_surface_decision_input_consumption(
        payload={"status": "detail-only"},
        consumption=consumption,
        used_material_inputs=material_inputs,
    )

    assert consumption["status"] == "unavailable"
    assert "context" not in rendered

    cached, context = lookup_projection_reuse(
        root=target,
        operation="report",
        query=query,
        full_detail_command="report --verbose",
        context=context,
        admitted_input=admitted_input,
    )
    assert cached is None
    assert context["invalidation_reasons"] == ["surface-decision-input-unavailable"]
    assert (
        record_projection_reuse(
            root=target,
            operation="report",
            query=query,
            context=context,
            payload={"status": "CONTINUE"},
            operating_decision={},
        )
        == {}
    )
    assert not context["path"].exists()


def test_projection_cache_does_not_bootstrap_workspace_state(tmp_path: Path) -> None:
    from agentic_workspace.projection_reuse import lookup_projection_reuse, record_projection_reuse

    cached, context = lookup_projection_reuse(root=tmp_path, operation="report", query={}, full_detail_command="report")
    assert cached is None
    record_projection_reuse(
        root=tmp_path,
        operation="report",
        query={},
        context=context,
        payload={"status": "ok"},
        operating_decision={},
    )

    assert not (tmp_path / ".agentic-workspace").exists()


def test_doctor_declares_package_inputs_and_caller_external_freshness_recomputes(tmp_path: Path, capsys, monkeypatch) -> None:
    target = _target(tmp_path)
    capsys.readouterr()
    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()
    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["kind"] == "agentic-workspace/unchanged-projection/v1"

    package_file = target / "packages/example/src/example.py"
    package_file.parent.mkdir(parents=True)
    package_file.write_text("VALUE = 1\n", encoding="utf-8")
    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out).get("kind") != "agentic-workspace/unchanged-projection/v1"

    monkeypatch.setenv("AW_PROJECTION_EXTERNAL_STATE", "1")
    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out).get("kind") != "agentic-workspace/unchanged-projection/v1"
