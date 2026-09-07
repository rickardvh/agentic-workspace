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
