"""Public clients consume the established Verification owner, never empty stubs."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TS_PACKAGE = ROOT / "generated/verification/typescript"


def _report(root: Path, runtime: str, *arguments: str) -> dict:
    command = (
        [sys.executable, "-c", "import sys; from repo_verification_bootstrap.cli import main; raise SystemExit(main(sys.argv[1:]))"]
        if runtime == "python"
        else ["node", str(TS_PACKAGE / "src/cli.mjs")]
    )
    completed = subprocess.run(
        [*command, "report", "--target", str(root), *arguments, "--format", "json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


@pytest.mark.parametrize("runtime", ["python", "typescript"])
def test_public_report_preserves_established_manifest_protocol_and_gap(tmp_path: Path, runtime: str) -> None:
    relative = Path(".agentic-workspace/verification/manifest.toml")
    manifest = tmp_path / relative
    manifest.parent.mkdir(parents=True)
    # The real current/former source is authoritative; no synthetic replacement
    # state or Python-produced expected answer is used by this public test.
    manifest.write_bytes((ROOT / relative).read_bytes())
    before = {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    report = _report(tmp_path, runtime, "--changed", "scripts/check/run_compact_command.py", "--verbose")
    assert report["kind"] == "agentic-workspace/verification/v1"
    assert report["configured"] is True
    assert report["status"] == "attention"
    assert [item["id"] for item in report["active_protocols"]] == ["authoritative_validation"]
    assert report["active_protocols"][0]["expected_evidence"] == ["authoritative_validation_pass"]
    assert [item["id"] for item in report["active_proof_routes"]] == ["authoritative_validation"]
    assert report["validation_evidence_admission_summary"]["admitted_count"] == 0
    unrelated = _report(tmp_path, runtime, "--changed", "unrelated.txt", "--verbose")
    assert unrelated["active_protocols"] == []
    assert {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()} == before


def test_typescript_report_missing_owner_is_explicitly_unavailable(tmp_path: Path) -> None:
    isolated = tmp_path / "isolated-package"
    shutil.copytree(TS_PACKAGE, isolated)
    target = tmp_path / "target"
    target.mkdir()
    environment = {key: value for key, value in os.environ.items() if key not in {"VIRTUAL_ENV", "PYTHONPATH"}}
    environment["PATH"] = ""
    completed = subprocess.run(
        [str(shutil.which("node")), str(isolated / "src/cli.mjs"), "report", "--target", str(target), "--format", "json"],
        cwd=target,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["status"] == "unavailable"
    assert report["reason_code"] == "verification-owner-unavailable"
    assert report["completion_claim_allowed"] is False
    assert "checks" not in report


def _workspace(root: Path, runtime: str, *arguments: str, allow_publication_gap: bool = False) -> dict:
    command = (
        [sys.executable, str(ROOT / "scripts/run_agentic_workspace.py")]
        if runtime == "python"
        else ["node", str(ROOT / "generated/workspace/typescript/src/cli.mjs")]
    )
    index = root / ".agentic-workspace/proof/receipts/index.json"
    before = index.read_bytes() if index.exists() else None
    completed = subprocess.run(
        [*command, *arguments, "--target", str(root), "--format", "json"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    if allow_publication_gap and completed.returncode != 0:
        diagnostic = completed.stderr if runtime == "python" else json.loads(completed.stdout)["diagnostic"]
        assert "proof-publication-current-owner-decision-required" in diagnostic, (completed.stdout, completed.stderr)
        assert (index.read_bytes() if index.exists() else None) == before
        return {"status": "publication-unavailable", "owner_blocker": "current-owner-decision-required"}
    assert completed.returncode == 0, (completed.stdout, completed.stderr)
    return json.loads(completed.stdout)


@pytest.mark.parametrize("runtime", ["python", "typescript"])
def test_public_workspace_manual_pass_cannot_manufacture_exact_task_admission(tmp_path: Path, runtime: str) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    _workspace(tmp_path, "python", "init", "--modules", "planning,memory", "--mirror-payload")
    (tmp_path / "docs").mkdir(exist_ok=True)
    (tmp_path / "tests").mkdir(exist_ok=True)
    (tmp_path / "docs/upgrade.md").write_text("# Upgrade replay\n")
    (tmp_path / "tests/test_upgrade_replay.py").write_text("def test_upgrade_replay():\n    assert True\n")
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "upgrade-replay"\nversion = "0.0.0"\n')
    (tmp_path / "Makefile").write_text(
        "test:\n\tpython -m pytest tests/test_upgrade_replay.py -q\n"
        + "".join(
            f"{name}:\n\tpython -m py_compile tests/test_upgrade_replay.py\n"
            for name in ["maintainer-surfaces", "lint-workspace", "typecheck"]
        )
    )
    manifest = Path(".agentic-workspace/verification/manifest.toml")
    (tmp_path / manifest).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / manifest).write_bytes((ROOT / manifest).read_bytes())
    task = "Upgrade the installed workspace without losing the active task"
    scope = ["--changed", "docs/upgrade.md"]
    selection = _workspace(tmp_path, runtime, "proof", *scope, "--task", task)
    commands = selection.get("required_commands") or [selection["next"]["command"]]
    assert commands
    for command in commands:
        recorded = _workspace(
            tmp_path,
            runtime,
            "proof",
            *scope,
            "--task",
            task,
            "--record-receipt",
            "--receipt-command",
            command,
            "--receipt-result",
            "passed",
            "--receipt-claim-sufficiency",
            "sufficient",
            allow_publication_gap=True,
        )
        if recorded["status"] != "publication-unavailable":
            assert recorded["receipt"]["result"] == "passed"
            assert recorded["receipt"]["task_claim_judgment"]["status"] == "sufficient"
            assert recorded["receipt"]["native_publication_boundary"]["native_execution_admission"] == "unproven"
    report = _workspace(tmp_path, runtime, "report", "--section", "closeout_trust", *scope, "--task", task)
    assert report["answer"]["current_task_closeout"]["proof_state"]["status"] != "recorded-and-accepted"
    admission = [
        "final-response",
        "admit",
        "--attempt",
        "The bounded slice is complete.",
        "--claim-class",
        "slice-complete",
        "--claim-scope-id",
        "direct_task_closeout:slice_complete",
        "--residue",
        "issue",
        "--residue-owner",
        "GitHub issue #2334",
        *scope,
    ]
    current = _workspace(tmp_path, runtime, *admission, "--task", task)
    assert current["status"] != "accepted_bounded_report"
    assert not (tmp_path / "tests/__pycache__").exists()
    unrelated = _workspace(tmp_path, runtime, *admission, "--task", "Implement payment validation")
    assert unrelated["status"] != "accepted_bounded_report"
    (tmp_path / "docs/upgrade.md").write_text("# A materially different source\n")
    stale = _workspace(tmp_path, runtime, *admission, "--task", task)
    assert stale["status"] != "accepted_bounded_report"
    # Re-enter the real established Planning owner, not a delegation-local plan.
    (tmp_path / "docs/upgrade.md").write_text("# Upgrade replay\n")
    plan_ref = Path(".agentic-workspace/planning/execplans/delegation-lane-sweep.plan.json")
    plan = json.loads((ROOT / plan_ref).read_text())
    (tmp_path / plan_ref).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / plan_ref).write_text(json.dumps(plan))
    (tmp_path / ".agentic-workspace/planning/state.toml").write_text(
        'kind = "agentic-planning-state"\nschema_version = "planning-state/v1"\n[todo]\n'
        'active_items = [{id = "delegation-lane-sweep", title = "Reconstruct delegation", status = "active", '
        'surface = ".agentic-workspace/planning/execplans/delegation-lane-sweep.plan.json"}]\n'
        "queued_items = []\n[roadmap]\nlanes = []\ncandidates = []\n"
    )
    planned = _workspace(
        tmp_path,
        runtime,
        "proof",
        *scope,
        "--task",
        plan["title"],
        "--record-receipt",
        "--receipt-command",
        commands[0],
        "--receipt-result",
        "passed",
        "--receipt-claim-sufficiency",
        "sufficient",
        allow_publication_gap=True,
    )
    judgment = planned.get("receipt", {}).get("task_claim_judgment")
    if judgment:
        assert "delegation-lane-sweep" in judgment["work_ref"]
        assert not judgment["work_revision"].startswith("direct-task:")
    plan["goal"] = ["A different semantic outcome requires new acceptance."]
    plan["intent"]["outcome"] = plan["goal"][0]
    (tmp_path / plan_ref).write_text(json.dumps(plan))
    revised = _workspace(
        tmp_path,
        runtime,
        "proof",
        *scope,
        "--task",
        plan["title"],
        "--record-receipt",
        "--receipt-command",
        commands[0],
        "--receipt-result",
        "passed",
        "--receipt-claim-sufficiency",
        "sufficient",
        allow_publication_gap=True,
    )
    if judgment and revised["status"] != "publication-unavailable":
        assert revised["receipt"]["task_claim_judgment"]["work_revision"] != judgment["work_revision"]


@pytest.mark.parametrize("operation", [["proof"], ["report"], ["final-response", "admit", "--attempt", "Complete"]])
def test_workspace_typescript_missing_proof_owner_fails_closed(tmp_path: Path, operation: list[str]) -> None:
    isolated = tmp_path / "package"
    shutil.copytree(ROOT / "generated/workspace/typescript", isolated)
    environment = {key: value for key, value in os.environ.items() if key not in {"VIRTUAL_ENV", "PYTHONPATH"}}
    environment["PATH"] = ""
    completed = subprocess.run(
        [str(shutil.which("node")), str(isolated / "src/cli.mjs"), *operation, "--target", str(tmp_path), "--format", "json"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 2, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["reason_code"] == "proof-owner-unavailable"
    assert payload["completion_claim_allowed"] is False
    assert payload["mutation_applied"] is False
    assert not (tmp_path / ".agentic-workspace").exists()
