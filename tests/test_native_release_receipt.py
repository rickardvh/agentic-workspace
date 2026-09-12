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


@pytest.mark.parametrize("change", ["artifact", "proof", "context", "extra-package"])
def test_receipt_rejects_changed_subject(tmp_path, monkeypatch, change):
    for name in ("root.whl", "root.tar.gz", "root.tgz", "agentic-workspace-native-test.zip"):
        (tmp_path / name).write_bytes(name.encode())
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
        (tmp_path / "root.whl").write_bytes(b"changed")
    if change == "extra-package":
        (tmp_path / "legacy-module.whl").write_bytes(b"extra")
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
    with pytest.raises(ValueError):
        checker.main()
