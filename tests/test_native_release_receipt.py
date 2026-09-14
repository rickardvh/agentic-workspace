"""Receipt admission rejects stale bytes and unproved host context."""

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("native_release_checker", ROOT / "scripts/check/check_native_release_topology.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


@pytest.mark.parametrize("change", [None, "artifact", "proof", "context", "extra-package"])
def test_receipt_admits_only_unchanged_root_subject(tmp_path, monkeypatch, change):
    for name in (
        "agentic_workspace-1.0-py3-none-any.whl",
        "agentic_workspace-1.0.tar.gz",
        "agentic-workspace-workspace-cli-1.0.tgz",
        "agentic-workspace-native-test.zip",
        "agentic_workspace_memory-1.0-py3-none-any.whl",
        "agentic_workspace_memory-1.0.tar.gz",
    ):
        (tmp_path / name).write_bytes(name.encode())
    assert len(checker.inventory(tmp_path)) == 4
    receipt = {
        "kind": checker.KIND,
        "status": "passed",
        "execution_context": "local",
        "subject": {
            "release_artifacts": checker.inventory(tmp_path),
            "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "source_diff_sha256": hashlib.sha256(subprocess.check_output(["git", "diff", "HEAD", "--binary"], cwd=ROOT)).hexdigest(),
            "proof_fingerprint": checker.proof_identity(),
            "node_version": "v24.0.0",
        },
    }
    if change == "proof":
        receipt["subject"]["proof_fingerprint"] = "old"
    receipt["receipt_id"] = hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest()
    path = tmp_path / "fixture-receipt.json"
    path.write_text(json.dumps(receipt))
    if change == "artifact":
        (tmp_path / "agentic_workspace-1.0-py3-none-any.whl").write_bytes(b"changed")
    if change == "extra-package":
        (tmp_path / "agentic_workspace-2.0-py3-none-any.whl").write_bytes(b"extra")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "checker",
            "--artifact-dir",
            str(tmp_path),
            "--verify-receipt",
            str(path),
            "--expected-execution-context",
            "hosted-ci" if change == "context" else "local",
        ],
    )
    if change is None:
        assert checker.main() == 0
    else:
        with pytest.raises(ValueError):
            checker.main()
