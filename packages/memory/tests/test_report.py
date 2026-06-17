from __future__ import annotations

import sys as _sys

# ruff: noqa: F403,F405
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parent))
from memory_test_support import *
from repo_memory_bootstrap import runtime_primitives


def test_memory_report_defaults_to_tiny_profile(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    assert cli.main(["report", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "tiny"
    assert set(payload) <= {
        "kind",
        "profile",
        "module",
        "target_root",
        "health",
        "status",
        "active",
        "habitual_pull",
        "promotion_pressure",
        "trust",
        "finding_count",
        "findings",
        "next_action",
        "detail_commands",
    }
    assert "state_model" not in payload
    assert payload["detail_commands"]["full"] == "agentic-memory report --target . --verbose --format json"


def test_memory_report_tiny_does_not_build_full_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    def fail_full_report(*, target=None):
        raise AssertionError("tiny memory report should not build the full report")

    monkeypatch.setattr(runtime_primitives, "memory_report", fail_full_report)

    assert cli.main(["report", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "tiny"
    assert payload["active"]["note_count"] >= 1


def test_memory_report_text_uses_compact_declarative_payload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    def fail_full_report(*, target=None):
        raise AssertionError("non-verbose text memory report should not build the full report")

    monkeypatch.setattr(runtime_primitives, "memory_report", fail_full_report)

    assert cli.main(["report", "--target", str(target)]) == 0

    output = capsys.readouterr().out
    assert "Memory report" in output
    assert "Notes:" in output
    assert "Habitual pull:" in output
    assert "agentic-memory report --target . --verbose --format json" in output


def test_memory_promotion_report_defaults_to_primary_next_action(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    assert cli.main(["promotion-report", "--target", str(target), "--mode", "remediation", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "memory-promotion-report/v1"
    assert set(payload) <= {
        "kind",
        "target_root",
        "dry_run",
        "mode",
        "message",
        "next_action",
        "context",
        "drill_down",
    }
    assert payload["next_action"]["action"] in {"review-promotion-candidates", "no-promotion-action"}
    assert isinstance(payload["context"]["action_count"], int)
    assert payload["drill_down"]["detail_command"] == "agentic-memory promotion-report --target . --mode remediation --format json"


def test_memory_lifecycle_status_defaults_to_tiny_actions(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    assert cli.main(["status", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert "action_count" in payload
    assert any(action["path"] == "AGENTS.md" for action in payload["actions"])


def test_memory_lifecycle_tiny_does_not_collect_full_status(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    def fail_collect_status(*, target=None):
        raise AssertionError("tiny status should not collect full lifecycle status")

    monkeypatch.setattr(runtime_primitives, "collect_status", fail_collect_status)

    assert cli.main(["status", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["health"] == "healthy"
    assert any(action["kind"] == "present" and action["path"] == "AGENTS.md" for action in payload["actions"])


def test_memory_lifecycle_text_status_uses_declarative_payload_policy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    def fail_collect_status(*, target=None):
        raise AssertionError("text status should not collect full lifecycle status")

    monkeypatch.setattr(runtime_primitives, "collect_status", fail_collect_status)

    assert cli.main(["status", "--target", str(target)]) == 0

    output = capsys.readouterr().out
    assert "Status report" in output
    assert "Detected version: 47 (payload version 47)" in output
    assert "- present: AGENTS.md" in output


def test_memory_lifecycle_doctor_uses_declarative_payload_policy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    def fail_doctor(*args, **kwargs):
        raise AssertionError("non-verbose doctor should not call package-domain doctor runtime")

    monkeypatch.setattr(runtime_primitives, "_load_memory_bootstrap_doctor", fail_doctor)

    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["dry_run"] is True
    assert payload["message"] == "Doctor report"
    assert any(action["kind"] == "present" and action["path"] == "AGENTS.md" for action in payload["actions"])


def test_memory_lifecycle_text_doctor_uses_declarative_payload_policy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    def fail_doctor(*args, **kwargs):
        raise AssertionError("non-verbose text doctor should not call package-domain doctor runtime")

    monkeypatch.setattr(runtime_primitives, "_load_memory_bootstrap_doctor", fail_doctor)

    assert cli.main(["doctor", "--target", str(target)]) == 0

    output = capsys.readouterr().out
    assert "Doctor report" in output
    assert "Detected version: 47 (payload version 47)" in output
    assert "- present: AGENTS.md" in output


def test_memory_route_report_tiny_does_not_evaluate_fixtures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    def fail_report_routes(*, target=None):
        raise AssertionError("tiny route-report should not evaluate route fixtures")

    monkeypatch.setattr(runtime_primitives, "report_routes", fail_report_routes)

    assert cli.main(["route-report", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["route_report_summary"]["detail"].startswith("Run full route-report")


def test_memory_route_report_text_uses_compact_declarative_payload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    def fail_report_routes(*, target=None):
        raise AssertionError("non-verbose text route-report should not evaluate route fixtures")

    monkeypatch.setattr(runtime_primitives, "report_routes", fail_report_routes)

    assert cli.main(["route-report", "--target", str(target)]) == 0

    output = capsys.readouterr().out
    assert "Routing report" in output
    assert "Feedback:" in output
    assert "Fixtures:" in output
    assert "Run full route-report" in output


def test_memory_generated_report_uses_compact_target_error_for_ambiguous_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    parent = tmp_path / "parent"
    child = parent / "child"
    (parent / ".git").mkdir(parents=True)
    (child / ".git").mkdir(parents=True)
    monkeypatch.chdir(child)

    with pytest.raises(SystemExit) as excinfo:
        cli.main(["report", "--format", "json"])

    assert excinfo.value.code == 2
    stderr = capsys.readouterr().err
    assert "Ambiguous repository root detected" in stderr
    assert "Retry with --target ." in stderr
    assert "Traceback" not in stderr


def test_memory_freshness_audit_ignores_bootstrap_workspace(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    installer.install_bootstrap(target=target)

    completed = subprocess.run(
        [
            sys.executable,
            str(_memory_freshness_script_path()),
        ],
        cwd=target,
        check=True,
        capture_output=True,
        text=True,
    )

    assert ".agentic-workspace/memory/bootstrap/" not in completed.stdout


def test_memory_freshness_strict_default_does_not_fail_on_bootstrap_placeholders(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    result = subprocess.run(
        [sys.executable, str(_memory_freshness_script_path()), "--strict"],
        cwd=target,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Uncustomised routing placeholders:" not in result.stdout


def test_memory_freshness_strict_can_fail_on_bootstrap_placeholders_when_requested(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)
    (target / ".agentic-workspace" / "memory" / "repo" / "index.md").write_text(
        (target / ".agentic-workspace" / "memory" / "repo" / "index.md")
        .read_text(encoding="utf-8")
        .replace(
            "Treat starter examples as temporary orientation until the repository has real notes to replace them.",
            "Delete unused routing examples once the repository has concrete notes.",
        )
        + "\n- runtime or deployment change: `.agentic-workspace/memory/repo/domains/<runtime-or-deployment-note>.md`\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(_memory_freshness_script_path()),
            "--strict",
            "--strict-categories",
            "uncustomised_index_placeholders",
        ],
        cwd=target,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Uncustomised routing placeholders:" in result.stdout
    assert "starter placeholder route examples" in result.stdout


def test_memory_freshness_reports_current_planning_state_residue(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)
    (target / ".agentic-workspace" / "memory" / "repo" / "current" / "project-state.md").write_text(
        "# Project State\n\n"
        "## Status\n\n"
        "- Active execplan: `.agentic-workspace/planning/execplans/example.md`.\n\n"
        "## Scope\n\n- Shared overview only.\n\n"
        "## Applies to\n\n- Root monorepo operation.\n\n"
        "## Load when\n\n- Starting work.\n\n"
        "## Review when\n\n- Current focus changes.\n\n"
        "## Current focus\n\n- Ordinary work.\n\n"
        "## Recent meaningful progress\n\n- One thing changed.\n\n"
        "## Blockers\n\n- None.\n\n"
        "## High-level notes\n\n- Keep this note short.\n\n"
        "## Failure signals\n\n- It becomes a planner.\n\n"
        "## Verify\n\n- Confirm overview still matches repo reality.\n\n"
        "## Verified against\n\n- `TODO.md`\n\n"
        "## Last confirmed\n\n2026-04-13\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(_memory_freshness_script_path())],
        cwd=target,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Current-context drift signals:" in result.stdout
    assert ".agentic-workspace/memory/repo/current/project-state.md" in result.stdout


def test_memory_report_derives_compact_module_state(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    report = installer.memory_report(target=target)

    assert report["kind"] == "memory-module-report/v1"
    assert report["schema"]["command"] == "agentic-memory report --target ./repo --format json"
    assert report["status"]["note_count"] >= 1
    assert report["status"]["current_note_count"] >= 2
    assert "current_notes" in report["active"]
    assert report["state_model"]["kind"] == "agentic-memory/state-model/v1"
    assert report["state_model"]["owner_surface"] == ".agentic-workspace/memory/repo/manifest.toml"
    assert report["state_model"]["classification_counts"]["structured_state"] >= 1
    assert report["state_model"]["classification_counts"]["prose_explanation"] >= 1
    assert report["state_model"]["record_contract"]["surface_classes"] == [
        "structured_state",
        "prose_explanation",
        "adapter_rendering",
    ]
    assert any(record["path"] == ".agentic-workspace/memory/repo/index.md" for record in report["state_model"]["records"])
    assert report["habitual_pull"]["status"] in {
        "ready-for-ordinary-work",
        "attention-needed",
        "needs-more-proof",
    }
    assert report["habitual_pull"]["ordinary_work_bundle"]["always_load"] == [".agentic-workspace/memory/repo/index.md"]
    assert "manual_review_count" in report["trust"]
    assert "state_counts" in report["trust"]
    assert "usefulness_audit" in report
    assert report["usefulness_audit"]["status"] in {"measured", "needs-more-proof", "attention-needed", "actionable"}
    assert ".agentic-workspace/memory/repo/manifest.toml" in report["state_model"]["common_queries"]["structured_state_owner"]
    helpers = {helper["artifact"]: helper for helper in report["writer_helpers"]["helpers"]}
    assert helpers["memory_capture_recommendation"]["writes"] == []
    assert "capture-note" in helpers["memory_capture_recommendation"]["command"]
    assert "create-note" in helpers["memory_note"]["command"]
    assert report["promotion_pressure"]["status"] in {"clear", "attention"}
    assert report["merge_safety"]["kind"] == "agentic-memory/merge-safety/v1"
    assert report["merge_safety"]["status"] in {"clear", "advisory", "attention"}


def test_memory_report_flags_merge_conflict_markers_in_notes(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)
    note_path = target / ".agentic-workspace/memory/repo/domains/conflicted-note.md"
    installer.create_memory_note(
        target=target,
        slug="conflicted-note",
        summary="Conflicted durable note.",
        applies_to=["src/**"],
    )
    note_path.write_text(
        "# Conflicted Note\n\n<<<<<<< ours\n- Durable fact from this branch.\n=======\n- Durable fact from another branch.\n>>>>>>> theirs\n",
        encoding="utf-8",
    )

    report = installer.memory_report(target=target)

    merge_safety = report["merge_safety"]
    assert merge_safety["status"] == "attention"
    assert merge_safety["findings"][0]["warning_class"] == "memory_merge_conflict_marker"
    assert report["health"] == "attention-needed"
    assert any(finding["source_report"] == "merge-safety" for finding in report["findings"])


def test_memory_report_flags_large_broad_notes_as_merge_hotspots(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)
    installer.create_memory_note(
        target=target,
        slug="broad-note",
        summary="Broad note.",
    )
    note_path = target / ".agentic-workspace/memory/repo/domains/broad-note.md"
    note_path.write_text("# Broad Note\n\n" + "\n".join(f"- fact {idx}" for idx in range(260)) + "\n", encoding="utf-8")

    report = installer.memory_report(target=target)

    classes = {finding["warning_class"] for finding in report["merge_safety"]["findings"]}
    assert "memory_note_merge_hotspot" in classes
    assert "memory_broad_note_hotspot" in classes


def test_create_memory_note_writes_note_and_manifest_entry(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    result = installer.create_memory_note(
        target=target,
        slug="api-routing",
        title="API Routing",
        summary="Route API implementation reminders.",
        applies_to=["src/api/**"],
        use_when=["touching API routing"],
        evidence=["tests/test_api.py"],
        promotion_target="docs/api-routing.md",
        promotion_trigger="guidance stabilises",
        retention_after_promotion="stub",
    )

    note_path = target / ".agentic-workspace/memory/repo/domains/api-routing.md"
    manifest_path = target / ".agentic-workspace/memory/repo/manifest.toml"
    manifest = installer._load_memory_manifest(manifest_path)

    assert result.counts()["created"] == 1
    assert result.counts()["updated"] == 1
    assert note_path.exists()
    assert "Route API implementation reminders." in note_path.read_text(encoding="utf-8")
    assert manifest is not None
    note = next(record for record in manifest.notes if record.path.as_posix().endswith("api-routing.md"))
    assert note.summary == "Route API implementation reminders."
    assert note.applies_to == ("src/api/**",)
    assert note.use_when == ("touching API routing",)
    assert note.routes_from == ("src/api/**",)
    assert note.stale_when == ("src/api/**",)
    assert note.evidence == ("tests/test_api.py",)
    assert note.promotion_target == "docs/api-routing.md"
    assert note.promotion_trigger == "guidance stabilises"
    assert note.retention_after_promotion == "stub"
    assert installer._memory_manifest_typed_validator_findings(manifest_path) == []


def test_memory_create_note_cli_writes_json_result(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    exit_code = cli.main(
        [
            "create-note",
            "cli-routing",
            "--target",
            str(target),
            "--summary",
            "CLI routing memory.",
            "--applies-to",
            "src/cli.py",
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["actions"][0]["kind"] == "created"
    assert (target / ".agentic-workspace/memory/repo/domains/cli-routing.md").exists()


def test_memory_create_note_cli_writes_local_note_without_manifest_update(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)
    manifest_path = target / ".agentic-workspace/memory/repo/manifest.toml"
    before = manifest_path.read_text(encoding="utf-8")

    exit_code = cli.main(
        [
            "create-note",
            "local-python-invocation",
            "--target",
            str(target),
            "--summary",
            "Bare python is unavailable in this local Windows Codex shell.",
            "--local",
            "--local-reason",
            "machine-local shell PATH behavior",
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    note_path = target / ".agentic-workspace/local/memory/local-python-invocation.md"
    assert exit_code == 0
    assert payload["actions"][0]["kind"] == "created"
    assert note_path.exists()
    assert "local_only" in note_path.read_text(encoding="utf-8")
    assert manifest_path.read_text(encoding="utf-8") == before


def test_memory_capture_note_prefers_existing_note(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)
    installer.create_memory_note(
        target=target,
        slug="api-routing",
        summary="API routing conventions.",
        applies_to=["src/api/**"],
        routes_from=["src/api/**"],
    )

    payload = installer.suggest_memory_note_capture(
        target=target,
        slug="api-routing-followup",
        summary="API routing durable learning.",
        files=["src/api/routes.py"],
    )

    assert payload["recommended_action"] == "update-existing-note"
    assert payload["candidates"][0]["path"] == ".agentic-workspace/memory/repo/domains/api-routing.md"

    assert (
        cli.main(
            [
                "capture-note",
                "api-routing-followup",
                "--target",
                str(target),
                "--summary",
                "API routing durable learning.",
                "--files",
                "src/api/routes.py",
                "--format",
                "json",
            ]
        )
        == 0
    )
    cli_payload = json.loads(capsys.readouterr().out)
    assert cli_payload["recommended_action"] == "update-existing-note"


def test_memory_capture_note_does_not_update_unrelated_note_from_weak_tokens(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)
    installer.create_memory_note(
        target=target,
        slug="agent-judgment-over-keyword-matching",
        folder="decisions",
        note_type="decision",
        summary="Agent judgment should not be replaced by keyword matching.",
        applies_to=[".agentic-workspace/**"],
        routes_from=["memory", "verification", "routing"],
    )

    payload = installer.suggest_memory_note_capture(
        target=target,
        slug="local-python-invocation",
        summary="Bare python is unavailable in this local Windows Codex shell; use uv run python.",
        task="Capture local shell execution memory for this Codex environment.",
        surfaces=["python", "shell", "codex"],
    )

    assert payload["recommended_action"] == "create-local-note"
    assert payload["storage_decision"]["recommended_owner"] == "local_memory"
    assert "--local" in payload["commands"][0]
    assert all(candidate["evidence_class"] != "ownership-evidence" for candidate in payload["candidates"])


def test_memory_capture_note_surfaces_improvement_promotion_metadata(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    assert (
        cli.main(
            [
                "capture-note",
                "dogfooding-feedback",
                "--target",
                str(target),
                "--summary",
                "Dogfooding improvement pressure: repeated correction should become routine Memory promotion metadata.",
                "--files",
                ".agentic-workspace/memory/repo/current/routing-feedback.md",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    guidance = payload["promotion_metadata_guidance"]
    assert guidance["status"] == "promotion-metadata-suggested"
    assert guidance["metadata_required"] is True
    assert guidance["suggested_manifest_fields"]["memory_role"] == "improvement_signal"
    assert "promotion-report" in payload["commands"][-1]


def test_promotion_report_surfaces_prose_only_current_improvement_signal(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)
    note_path = target / ".agentic-workspace/memory/repo/current/routing-feedback.md"
    note_path.write_text(
        "# Routing Feedback\n\nDogfooding improvement pressure: repeated correction about Memory promotion should not stay prose-only.\n",
        encoding="utf-8",
    )

    result = installer.promotion_report(target=target, mode="remediation")

    assert any(
        action.kind == "manual review"
        and action.source == ".agentic-workspace/memory/repo/current/routing-feedback.md"
        and action.remediation_kind == "metadata"
        and action.memory_action == "mark_improvement_signal_or_dismiss"
        for action in result.actions
    )


def test_promotion_report_does_not_rescan_metadata_routed_current_signal(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)
    note_path = target / ".agentic-workspace/memory/repo/current/routing-feedback.md"
    note_path.write_text(
        "# Routing Feedback\n\nDogfooding improvement pressure: repeated correction is routed through manifest metadata.\n",
        encoding="utf-8",
    )
    manifest_path = target / ".agentic-workspace/memory/repo/manifest.toml"
    with manifest_path.open("a", encoding="utf-8") as handle:
        handle.write(
            '\n[notes.".agentic-workspace/memory/repo/current/routing-feedback.md"]\n'
            'note_type = "current"\n'
            'canonical_home = ".agentic-workspace/memory/repo/current/routing-feedback.md"\n'
            'authority = "advisory"\n'
            'audience = "agent"\n'
            'memory_role = "improvement_signal"\n'
            'promotion_target = "planning closeout tests"\n'
            'promotion_trigger = "next closeout friction pass"\n'
            'retention_after_promotion = "shrink"\n'
        )

    result = installer.promotion_report(target=target, mode="remediation")

    assert not any(
        action.source == ".agentic-workspace/memory/repo/current/routing-feedback.md"
        and action.memory_action == "mark_improvement_signal_or_dismiss"
        for action in result.actions
    )


def test_memory_report_exposes_habitual_pull_boundary_and_evidence(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    report = installer.memory_report(target=target)

    habitual_pull = report["habitual_pull"]
    assert "repo-specific interpretive norms and recurring distinction hints" in habitual_pull["owner_boundary"]["memory_owns"]
    assert "broad repo doctrine or machine-readable policy" in habitual_pull["owner_boundary"]["memory_does_not_own"]
    assert habitual_pull["evidence"]["routing_fixture_count"] >= 0
    assert habitual_pull["ordinary_work_bundle"]["working_set_target"] == 3


def test_memory_report_routes_structured_durable_facts(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)
    _write_routing_fixture_file(
        target,
        "durable-fact-architecture.json",
        {
            "name": "durable-fact-architecture",
            "case_type": "general",
            "files": ["packages/memory/src/repo_memory_bootstrap/installer.py"],
            "surfaces": ["architecture"],
            "expected_required": [".agentic-workspace/memory/repo/index.md"],
            "expected_optional": [],
            "unexpected_notes": [".agentic-workspace/memory/repo/current/task-context.md"],
            "missing_note_candidates": [],
        },
    )
    manifest_path = target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml"
    manifest_path.write_text(
        manifest_path.read_text(encoding="utf-8")
        + """

[durable_facts."memory-test-boundary"]
summary = "Memory owns durable rediscovery-saving facts, not active sequencing or workflow policy."
owner = "memory"
authority_class = "canonical"
route_keys = ["architecture", "memory"]
touched_surfaces = ["packages/memory/**", ".agentic-workspace/memory/repo/manifest.toml"]
evidence = ["packages/memory/README.md", ".agentic-workspace/memory/repo/manifest.toml"]
promotion = "Promote into canonical docs if humans need it outside Memory routing."
demotion_or_expiry = "Remove or demote if it stops reducing routed prose reads."
status = "active"
""",
        encoding="utf-8",
    )

    route_result = installer.route_memory(target=target, surfaces=["architecture"])
    report = installer.memory_report(target=target)

    assert any(action.role == "memory-durable-fact" and "memory-test-boundary" in action.detail for action in route_result.actions)
    assert report["durable_facts"]["kind"] == "agentic-memory/durable-facts/v1"
    test_record = next(record for record in report["durable_facts"]["records"] if record["id"] == "memory-test-boundary")
    assert test_record["owner"] == "memory"
    assert test_record["authority_class"] == "canonical"
    assert test_record["promotion"]
    assert test_record["demotion_or_expiry"]
    assert report["durable_facts"]["routing_measure"]["matched_case_count"] >= 1
    assert report["durable_facts"]["routing_measure"]["smaller_or_more_precise"] is True
    assert report["usefulness_audit"]["durable_facts_smaller_or_more_precise"] is True
    assert "active task state, next actions, or milestone sequencing" in report["habitual_pull"]["owner_boundary"]["memory_does_not_own"]
    assert report["state_model"]["common_queries"]["durable_fact_count"] >= 1


def test_memory_report_classifies_trust_states_from_manifest_metadata(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    questionable_note = target / ".agentic-workspace" / "memory" / "repo" / "decisions" / "questionable-note.md"
    questionable_note.write_text("# Questionable\n", encoding="utf-8")
    fresh_note = target / ".agentic-workspace" / "memory" / "repo" / "decisions" / "fresh-note.md"
    fresh_note.write_text("# Fresh\n", encoding="utf-8")
    stale_note = target / ".agentic-workspace" / "memory" / "repo" / "decisions" / "stale-note.md"
    stale_note.write_text("# Stale\n", encoding="utf-8")
    superseded_note = target / ".agentic-workspace" / "memory" / "repo" / "decisions" / "superseded-note.md"
    superseded_note.write_text("# Superseded\n", encoding="utf-8")
    replacement_note = target / ".agentic-workspace" / "memory" / "repo" / "decisions" / "replacement-note.md"
    replacement_note.write_text("# Replacement\n", encoding="utf-8")
    contradicted_note = target / ".agentic-workspace" / "memory" / "repo" / "decisions" / "contradicted-note.md"
    contradicted_note.write_text("# Contradicted\n", encoding="utf-8")
    contradicting_note = target / ".agentic-workspace" / "memory" / "repo" / "decisions" / "contradicting-note.md"
    contradicting_note.write_text("# Contradicting\n", encoding="utf-8")
    improvement_note = target / ".agentic-workspace" / "memory" / "repo" / "mistakes" / "improvement-note.md"
    improvement_note.write_text("# Improvement\n", encoding="utf-8")

    manifest_path = target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml"
    manifest_path.write_text(
        manifest_path.read_text(encoding="utf-8")
        + """

[notes.".agentic-workspace/memory/repo/decisions/questionable-note.md"]
note_type = "decision"
canonical_home = ".agentic-workspace/memory/repo/decisions/questionable-note.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
subsystems = ["test"]
surfaces = ["decision"]
memory_role = "durable_truth"

[notes.".agentic-workspace/memory/repo/decisions/fresh-note.md"]
note_type = "decision"
canonical_home = ".agentic-workspace/memory/repo/decisions/fresh-note.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
subsystems = ["test"]
surfaces = ["decision"]
routes_from = ["AGENTS.md"]
stale_when = ["AGENTS.md"]
last_confirmed = "2999-01-01"
valid_until = "2999-12-31"
memory_role = "durable_truth"

[notes.".agentic-workspace/memory/repo/decisions/stale-note.md"]
note_type = "decision"
canonical_home = ".agentic-workspace/memory/repo/decisions/stale-note.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
subsystems = ["test"]
surfaces = ["decision"]
routes_from = ["AGENTS.md"]
stale_when = ["AGENTS.md"]
last_confirmed = "1999-01-01"
valid_until = "2000-01-01"
memory_role = "durable_truth"

[notes.".agentic-workspace/memory/repo/decisions/superseded-note.md"]
note_type = "decision"
canonical_home = ".agentic-workspace/memory/repo/decisions/superseded-note.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
subsystems = ["test"]
surfaces = ["decision"]
routes_from = ["AGENTS.md"]
stale_when = ["AGENTS.md"]
last_confirmed = "2026-01-01"
superseded_by = [".agentic-workspace/memory/repo/decisions/replacement-note.md"]
memory_role = "durable_truth"

[notes.".agentic-workspace/memory/repo/decisions/contradicted-note.md"]
note_type = "decision"
canonical_home = ".agentic-workspace/memory/repo/decisions/contradicted-note.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
subsystems = ["test"]
surfaces = ["decision"]
routes_from = ["AGENTS.md"]
stale_when = ["AGENTS.md"]
last_confirmed = "2026-01-01"
contradicted_by = [".agentic-workspace/memory/repo/decisions/contradicting-note.md"]
memory_role = "durable_truth"

[notes.".agentic-workspace/memory/repo/mistakes/improvement-note.md"]
note_type = "recurring-failures"
canonical_home = ".agentic-workspace/memory/repo/mistakes/improvement-note.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
subsystems = ["test"]
surfaces = ["tests"]
routes_from = ["AGENTS.md"]
stale_when = ["AGENTS.md"]
memory_role = "improvement_signal"
improvement_candidate = true
preferred_remediation = "docs"
improvement_note = "Promote once docs improve."
elimination_target = "promote"
""",
        encoding="utf-8",
    )

    report = installer.memory_report(target=target)

    assert report["trust"]["state_counts"]["questionable"] >= 1
    assert report["trust"]["state_counts"]["supported"] >= 1
    assert report["trust"]["state_counts"]["stale"] >= 1
    assert report["trust"]["state_counts"]["superseded"] >= 1
    assert report["trust"]["state_counts"]["contradicted"] >= 1
    assert report["trust"]["state_counts"]["elimination_candidate"] >= 1
    assert report["trust"]["status"] == "attention"
    assert report["trust"]["attention_count"] >= 3
    assert any(item["freshness"] == "expired" for item in report["trust"]["stale_notes"])
    assert any(
        item["path"] == ".agentic-workspace/memory/repo/decisions/superseded-note.md"
        and item["superseded_by"] == [".agentic-workspace/memory/repo/decisions/replacement-note.md"]
        for item in report["trust"]["superseded_notes"]
    )
    assert any(
        item["path"] == ".agentic-workspace/memory/repo/decisions/contradicted-note.md"
        and item["contradicted_by"] == [".agentic-workspace/memory/repo/decisions/contradicting-note.md"]
        for item in report["trust"]["contradicted_notes"]
    )
    assert any(
        item["path"] == ".agentic-workspace/memory/repo/decisions/questionable-note.md" for item in report["trust"]["questionable_notes"]
    )
    assert any(
        item["path"] == ".agentic-workspace/memory/repo/mistakes/improvement-note.md" for item in report["trust"]["elimination_candidates"]
    )
    assert (
        ".agentic-workspace/memory/repo/mistakes/improvement-note.md" in report["state_model"]["common_queries"]["improvement_candidates"]
    )


def test_memory_report_surfaces_recurring_friction_pressure(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    ledger_path = target / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "recurring-friction-ledger.md"
    ledger_path.write_text(
        """
# Recurring Friction Ledger

## Status

Active

## Scope

- Lightweight recurring friction evidence.

## Load when

- The same friction shows up again.

## Review when

- A friction class is promoted elsewhere.

## Failure signals

- The same friction keeps recurring.

## When to use this

- The signal is real but still below issue threshold.

## Rules

- Keep one entry per friction class.

## Entry format

### Friction: missing-memory-capture

Observed recurrences
- 2026-04-20: Post-task friction was noticed but not captured.
- 2026-04-22: Another task required the same manual rescue.

Keep now
- Two recurrences are enough to preserve, but the exact fix still needs shaping.

Promote when
- The same friction recurs again or a clear package change presents itself.

Most likely remediation
- validation

Config treatment
- promote because current repo posture prefers escalating repeated workflow drift instead of letting it stay note-only evidence.

Last seen
2026-04-22 during issue #263 closeout
""".strip()
        + "\n",
        encoding="utf-8",
    )

    report = installer.memory_report(target=target)

    assert report["recurring_friction"]["status"] == "present"
    assert report["recurring_friction"]["entry_count"] == 1
    assert report["recurring_friction"]["promotion_pressure_count"] == 1
    assert any("has 2 observed recurrences" in message for message in report["recurring_friction"]["promotion_pressure"])
