from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check" / "run_compact_command.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("run_compact_command", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_compact_runner_timeout_writes_tailed_log(tmp_path, capsys) -> None:
    runner = _load_runner()
    runner.REPO_ROOT = tmp_path
    runner.LOG_ROOT = tmp_path / "scratch" / "command-logs"
    runner.RESULT_ROOT = tmp_path / "scratch" / "validation-results"

    returncode = runner.main(
        [
            "--label",
            "timeout test",
            "--run-id",
            "local",
            "--timeout-seconds",
            "0.1",
            "--failure-tail-lines",
            "20",
            "--",
            sys.executable,
            "-c",
            "import time; print('started', flush=True); time.sleep(30)",
        ]
    )

    captured = capsys.readouterr()
    logs = list(runner.LOG_ROOT.glob("*-timeout-test.log"))
    assert returncode == runner.TIMEOUT_EXIT_CODE
    assert len(logs) == 1
    assert "[timeout] timeout test" in captured.err
    assert "Command timed out after 0.1 seconds." in captured.err
    assert "Full log: scratch/command-logs/" in captured.err
    assert "Result: scratch/validation-results/local/timeout-test.json" in captured.err
    assert "started" in logs[0].read_text(encoding="utf-8")
    result = json.loads((tmp_path / "scratch" / "validation-results" / "local" / "timeout-test.json").read_text(encoding="utf-8"))
    assert result["kind"] == "agentic-workspace/validation-constituent-result/v1"
    assert result["constituent_id"] == "timeout-test"
    assert result["outcome"] == "timeout"
    assert result["timed_out"] is True
    assert result["log_path"].startswith("scratch/command-logs/")


def test_compact_runner_records_cancellation_separately_from_timeout_and_failure(tmp_path, capsys) -> None:
    runner = _load_runner()
    runner.REPO_ROOT = tmp_path
    runner.LOG_ROOT = tmp_path / "scratch" / "command-logs"
    runner.RESULT_ROOT = tmp_path / "scratch" / "validation-results"
    cancel_file = tmp_path / "scratch" / "cancel" / "proof.cancel"
    cancel_file.parent.mkdir(parents=True)
    cancel_file.write_text("cancel\n", encoding="utf-8")

    returncode = runner.main(
        [
            "--label",
            "cancel test",
            "--run-id",
            "cancel-run",
            "--cancel-file",
            "scratch/cancel/proof.cancel",
            "--",
            sys.executable,
            "-c",
            "import time; time.sleep(30)",
        ]
    )

    captured = capsys.readouterr()
    result = json.loads((runner.RESULT_ROOT / "cancel-run" / "cancel-test.json").read_text(encoding="utf-8"))
    assert returncode == runner.CANCELLED_EXIT_CODE
    assert "[cancelled] cancel test" in captured.err
    assert result["outcome"] == "cancelled"
    assert result["timed_out"] is False
    assert result["heartbeat"]["cancelled"] is True


def test_compact_runner_success_writes_machine_readable_result(tmp_path, capsys) -> None:
    runner = _load_runner()
    runner.REPO_ROOT = tmp_path
    runner.LOG_ROOT = tmp_path / "scratch" / "command-logs"
    runner.RESULT_ROOT = tmp_path / "scratch" / "validation-results"

    returncode = runner.main(
        [
            "--label",
            "workspace lint",
            "--id",
            "lint.workspace",
            "--run-id",
            "run-1",
            "--depends-on",
            "sync.root",
            "--proof-purpose",
            "workspace lint proof",
            "--",
            sys.executable,
            "-c",
            "print('ok')",
        ]
    )

    captured = capsys.readouterr()
    result = json.loads((tmp_path / "scratch" / "validation-results" / "run-1" / "lint.workspace.json").read_text(encoding="utf-8"))
    assert returncode == 0
    assert "[run] workspace lint (lint.workspace)" in captured.out
    assert "[ok] workspace lint" in captured.out
    assert result["outcome"] == "passed"
    assert result["dependencies"] == ["sync.root"]
    assert result["proof_purpose"] == "workspace lint proof"
    assert result["log_path"] is None
    assert "runtime" in result["repository"]
    manifest = json.loads((tmp_path / "scratch" / "validation-results" / "run-1" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["kind"] == "agentic-workspace/validation-run-manifest/v1"
    assert manifest["result_count"] == 1
    assert manifest["outcomes"] == {"passed": 1}
    assert manifest["results"][0]["constituent_id"] == "lint.workspace"
    assert manifest["critical_path_seconds"] >= 0
    assert abs(manifest["summed_work_seconds"] - manifest["critical_path_seconds"]) < 0.01


def test_manifest_reconcile_repairs_interrupted_publish_without_rerunning_result(tmp_path) -> None:
    runner = _load_runner()
    runner.REPO_ROOT = tmp_path
    runner.LOG_ROOT = tmp_path / "scratch" / "command-logs"
    runner.RESULT_ROOT = tmp_path / "scratch" / "validation-results"

    assert runner.main(["--label", "proof", "--run-id", "repair", "--", sys.executable, "-c", "print('ok')"]) == 0
    run_root = runner.RESULT_ROOT / "repair"
    manifest_path = run_root / "manifest.json"
    original = json.loads(manifest_path.read_text(encoding="utf-8"))
    (run_root / "proof-two.json").write_text(
        json.dumps({**original["results"][0], "constituent_id": "proof-two", "duration_seconds": 2.5}),
        encoding="utf-8",
    )

    def interrupt(_temp_path: Path, _manifest_path: Path) -> None:
        raise RuntimeError("fault after durable temp write")

    try:
        runner._update_manifest(result_root=runner.RESULT_ROOT, run_id="repair", before_replace=interrupt)
    except RuntimeError as exc:
        assert "fault after durable temp write" in str(exc)
    else:
        raise AssertionError("fault injection did not interrupt manifest publication")

    assert json.loads(manifest_path.read_text(encoding="utf-8"))["result_count"] == 1
    residue = list(run_root.glob(".manifest.json.*.tmp"))
    assert len(residue) == 1
    result_mtimes = {path: path.stat().st_mtime_ns for path in runner._record_paths_for_run(run_root)}

    healed = runner._update_manifest(result_root=runner.RESULT_ROOT, run_id="repair")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert healed["status"] == "rebuilt"
    assert healed["orphan_temp_residue"] == [runner._repo_relative(residue[0])]
    assert manifest["result_count"] == 2
    assert manifest["outcomes"] == {"passed": 2}
    assert manifest["summed_work_seconds"] == round(float(original["results"][0]["duration_seconds"]) + 2.5, 6)
    assert manifest["result_set_identity"] == healed["result_set_identity"]
    assert manifest["completion_admissible"] is True
    assert not list(run_root.glob(".manifest.json.*.tmp"))
    assert result_mtimes == {path: path.stat().st_mtime_ns for path in runner._record_paths_for_run(run_root)}


def test_manifest_reconcile_excludes_malformed_records_and_fails_closed(tmp_path, capsys) -> None:
    runner = _load_runner()
    runner.REPO_ROOT = tmp_path
    runner.RESULT_ROOT = tmp_path / "scratch" / "validation-results"
    run_root = runner.RESULT_ROOT / "malformed"
    run_root.mkdir(parents=True)
    (run_root / "broken.json").write_text("{not-json", encoding="utf-8")

    assert runner.main(["--reconcile-manifest", "malformed"]) == 1
    response = json.loads(capsys.readouterr().out)
    manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
    assert response["completion_admissible"] is False
    assert response["excluded_results"][0]["reason"] == "unreadable-or-malformed-json"
    assert manifest["status"] == "incomplete"
    assert manifest["result_count"] == 0


def test_manifest_reconcile_is_idempotent_when_result_identity_is_current(tmp_path) -> None:
    runner = _load_runner()
    runner.REPO_ROOT = tmp_path
    runner.LOG_ROOT = tmp_path / "scratch" / "command-logs"
    runner.RESULT_ROOT = tmp_path / "scratch" / "validation-results"

    assert runner.main(["--label", "proof", "--run-id", "stable", "--", sys.executable, "-c", "print('ok')"]) == 0
    manifest_path = runner.RESULT_ROOT / "stable" / "manifest.json"
    before = manifest_path.read_bytes()
    before_mtime = manifest_path.stat().st_mtime_ns
    reconciliation = runner._update_manifest(result_root=runner.RESULT_ROOT, run_id="stable")

    assert reconciliation["status"] == "current"
    assert manifest_path.read_bytes() == before
    assert manifest_path.stat().st_mtime_ns == before_mtime

    corrupted = json.loads(before)
    corrupted["outcomes"] = {"passed": 999}
    manifest_path.write_text(json.dumps(corrupted), encoding="utf-8")
    repaired = runner._update_manifest(result_root=runner.RESULT_ROOT, run_id="stable")
    assert repaired["status"] == "rebuilt"
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["outcomes"] == {"passed": 1}


def test_compact_runner_records_no_heartbeat_for_short_success(tmp_path, capsys) -> None:
    runner = _load_runner()
    runner.REPO_ROOT = tmp_path
    runner.LOG_ROOT = tmp_path / "scratch" / "command-logs"
    runner.RESULT_ROOT = tmp_path / "scratch" / "validation-results"

    returncode = runner.main(
        [
            "--label",
            "short proof",
            "--run-id",
            "local",
            "--",
            sys.executable,
            "-c",
            "print('captured detail', flush=True)",
        ]
    )

    captured = capsys.readouterr()
    assert returncode == 0
    assert "[heartbeat]" not in captured.err
    assert "captured detail" not in captured.out
    assert "captured detail" not in captured.err
    assert "[ok] short proof" in captured.out
    result = json.loads((runner.RESULT_ROOT / "local" / "short-proof.json").read_text(encoding="utf-8"))
    assert result["heartbeat"]["count"] == 0
    assert result["heartbeat"]["claim"] == "process-liveness-only"


def test_run_command_emits_rate_limited_heartbeats_with_fake_clock_and_process(tmp_path) -> None:
    runner = _load_runner()
    clock = type("Clock", (), {"now": 0.0})()

    class FakeProcess:
        returncode = 0

        def __init__(self) -> None:
            self.waits = 0

        def communicate(self, timeout=None):
            self.waits += 1
            clock.now += float(timeout)
            if self.waits <= 3:
                raise subprocess.TimeoutExpired(["fake"], timeout)
            return "buffered child output", ""

        def poll(self):
            return None

    messages: list[str] = []
    returncode, stdout, stderr, timed_out, heartbeat = runner._run_command(
        ["fake"],
        cwd=tmp_path,
        timeout_seconds=None,
        progress_interval_seconds=10.0,
        progress_threshold_seconds=20.0,
        progress_label="long proof",
        constituent_id="proof.long",
        durable_result_path="scratch/validation-results/run/proof.long.json",
        monotonic=lambda: clock.now,
        process_factory=lambda *_args, **_kwargs: FakeProcess(),
        emit_heartbeat=messages.append,
    )

    assert returncode == 0
    assert stdout == "buffered child output"
    assert stderr == ""
    assert timed_out is False
    assert heartbeat["count"] == 3
    assert heartbeat["elapsed_seconds"] == [20.0, 30.0, 40.0]
    assert all("long proof (proof.long)" in message for message in messages)
    assert all("process liveness only" in message for message in messages)
    assert all("scratch/validation-results/run/proof.long.json" in message for message in messages)


def test_compact_runner_rejects_duplicate_constituent_in_same_run(tmp_path, capsys) -> None:
    runner = _load_runner()
    runner.REPO_ROOT = tmp_path
    runner.LOG_ROOT = tmp_path / "scratch" / "command-logs"
    runner.RESULT_ROOT = tmp_path / "scratch" / "validation-results"

    args = [
        "--label",
        "workspace lint",
        "--id",
        "lint.workspace",
        "--run-id",
        "same-run",
        "--",
        sys.executable,
        "-c",
        "print('ok')",
    ]

    assert runner.main(args) == 0
    assert runner.main(args) == runner.DUPLICATE_EXIT_CODE
    captured = capsys.readouterr()
    assert "[duplicate] workspace lint (lint.workspace)" in captured.err
    assert "scratch/validation-results/same-run/lint.workspace.json" in captured.err
    conflict = json.loads(captured.err.splitlines()[0])
    assert conflict["status"] == "already-completed"
    assert "--retry-reason" in conflict["next_action"]


def test_compact_runner_rejects_concurrent_writer_for_same_attempt(tmp_path, capsys) -> None:
    runner = _load_runner()
    runner.REPO_ROOT = tmp_path
    runner.LOG_ROOT = tmp_path / "scratch" / "command-logs"
    runner.RESULT_ROOT = tmp_path / "scratch" / "validation-results"
    lock = runner.RESULT_ROOT / "same-run" / "lint.workspace.lock"
    lock.parent.mkdir(parents=True)
    lock.write_text("owned\n", encoding="utf-8")

    returncode = runner.main(
        [
            "--label",
            "workspace lint",
            "--id",
            "lint.workspace",
            "--run-id",
            "same-run",
            "--",
            sys.executable,
            "-c",
            "print('should not run')",
        ]
    )

    conflict = json.loads(capsys.readouterr().err.splitlines()[0])
    assert returncode == runner.DUPLICATE_EXIT_CODE
    assert conflict["status"] == "running-conflict"
    assert conflict["next_action"] == "wait for the running attempt or allocate a new top-level run"


def test_compact_runner_uses_plan_metadata_and_keeps_repeat_attempts(tmp_path, capsys) -> None:
    runner = _load_runner()
    runner.REPO_ROOT = tmp_path
    runner.LOG_ROOT = tmp_path / "scratch" / "command-logs"
    runner.RESULT_ROOT = tmp_path / "scratch" / "validation-results"
    runner.PLAN_PATH = tmp_path / "docs" / "maintainer" / "validation-runtime-2435" / "validation-plan.json"
    runner.PLAN_PATH.parent.mkdir(parents=True)
    runner.PLAN_PATH.write_text(
        json.dumps(
            {
                "compact_label_map": {
                    "workspace lint": {
                        "id": "lint.workspace",
                        "dependencies": ["sync.all"],
                        "proof_purpose": "workspace lint proof from plan",
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    first_args = [
        "--label",
        "workspace lint",
        "--run-id",
        "same-run",
        "--",
        sys.executable,
        "-c",
        "print('ok')",
    ]
    retry_args = [
        "--label",
        "workspace lint",
        "--join-run-id",
        "same-run",
        "--retry",
        "--retry-reason",
        "rerun after relevant input change",
        "--",
        sys.executable,
        "-c",
        "print('ok')",
    ]

    assert runner.main(first_args) == 0
    assert runner.main(retry_args) == 0
    captured = capsys.readouterr()
    assert "[run] workspace lint (lint.workspace)" in captured.out
    first = json.loads((tmp_path / "scratch" / "validation-results" / "same-run" / "lint.workspace.json").read_text(encoding="utf-8"))
    second = json.loads(
        (tmp_path / "scratch" / "validation-results" / "same-run" / "attempts" / "lint.workspace.attempt-2.json").read_text(
            encoding="utf-8"
        )
    )
    manifest = json.loads((tmp_path / "scratch" / "validation-results" / "same-run" / "manifest.json").read_text(encoding="utf-8"))
    assert first["dependencies"] == ["sync.all"]
    assert second["proof_purpose"] == "workspace lint proof from plan"
    assert first["run_identity"]["provenance"] == "allocated-here"
    assert second["attempt_identity"]["attempt_index"] == 2
    assert second["attempt_identity"]["retry_reason"] == "rerun after relevant input change"
    assert second["run_identity"]["provenance"] == "explicitly-joined"
    assert second["proof_operation"]["execution_class"] == "focused-local"
    assert manifest["result_count"] == 2


def test_compact_runner_ignores_unadmitted_ambient_transport(tmp_path, capsys, monkeypatch) -> None:
    runner = _load_runner()
    runner.REPO_ROOT = tmp_path
    runner.LOG_ROOT = tmp_path / "scratch" / "command-logs"
    runner.RESULT_ROOT = tmp_path / "scratch" / "validation-results"
    monkeypatch.setenv("VALIDATION_RUN_ID", "stale-run")
    monkeypatch.delenv("VALIDATION_JOIN_TOKEN", raising=False)

    assert runner.main(["--label", "fresh proof", "--", sys.executable, "-c", "print('ok')"]) == 0

    run_dirs = [path for path in runner.RESULT_ROOT.iterdir() if path.is_dir()]
    assert len(run_dirs) == 1
    assert run_dirs[0].name != "stale-run"
    record = json.loads((run_dirs[0] / "fresh-proof.json").read_text(encoding="utf-8"))
    assert record["run_identity"] == {
        "join_authority": "local-allocation",
        "provenance": "allocated-here",
        "run_id": record["run_id"],
        "transport_run_id_ignored": True,
    }
    assert "[ok] fresh proof" in capsys.readouterr().out


def test_compact_runner_distinguishes_explicit_join_and_transported_child(tmp_path, monkeypatch) -> None:
    runner = _load_runner()
    runner.REPO_ROOT = tmp_path
    runner.LOG_ROOT = tmp_path / "scratch" / "command-logs"
    runner.RESULT_ROOT = tmp_path / "scratch" / "validation-results"

    assert runner.main(["--label", "explicit join", "--join-run-id", "shared", "--", sys.executable, "-c", "print('ok')"]) == 0
    monkeypatch.setenv("VALIDATION_RUN_ID", "transported")
    monkeypatch.setenv("VALIDATION_JOIN_TOKEN", "join:transported")
    assert runner.main(["--label", "child", "--", sys.executable, "-c", "print('ok')"]) == 0

    explicit = json.loads((runner.RESULT_ROOT / "shared" / "explicit-join.json").read_text(encoding="utf-8"))
    child = json.loads((runner.RESULT_ROOT / "transported" / "child.json").read_text(encoding="utf-8"))
    assert explicit["run_identity"]["provenance"] == "explicitly-joined"
    assert child["run_identity"]["provenance"] == "transported-child"


def test_compact_runner_captures_bounded_dirty_subject_at_launch(tmp_path) -> None:
    runner = _load_runner()
    runner.REPO_ROOT = tmp_path
    runner.LOG_ROOT = tmp_path / "scratch" / "command-logs"
    runner.RESULT_ROOT = tmp_path / "scratch" / "validation-results"
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Fixture"], cwd=tmp_path, check=True)
    source = tmp_path / "src" / "example.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "src/example.py"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "fixture"], cwd=tmp_path, check=True, capture_output=True)
    source.write_text("VALUE = 2\n", encoding="utf-8")

    assert runner.main(["--label", "dirty proof", "--run-id", "dirty-run", "--", sys.executable, "-c", "print('ok')"]) == 0

    record = json.loads((runner.RESULT_ROOT / "dirty-run" / "dirty-proof.json").read_text(encoding="utf-8"))
    assert record["proof_operation"]["subject_paths"] == ["src/example.py"]
    assert record["proof_operation"]["subject_declaration"] == "captured-tracked-working-set-at-launch"
    assert record["repository"]["tracked_diff_sha256"] == record["repository_post"]["tracked_diff_sha256"]
