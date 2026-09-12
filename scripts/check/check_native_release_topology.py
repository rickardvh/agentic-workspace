"""Prove already-built native distributions; never repair or rebuild their bytes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KIND = "agentic-workspace/native-release-conformance/v1"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(directory: Path) -> list[dict[str, str]]:
    entries = []
    for pattern in ("*.whl", "*.tar.gz", "*.tgz", "agentic-workspace-native-*.zip"):
        paths = list(directory.glob(pattern))
        if len(paths) != 1:
            raise ValueError(f"Expected exactly one {pattern} in {directory}")
        entries.append({"asset": paths[0].name, "sha256": digest(paths[0])})
    return sorted(entries, key=lambda entry: entry["asset"])


def proof_identity() -> str:
    paths = [Path(__file__), ROOT / "tests/test_native_release_topology.py"]
    return hashlib.sha256(b"".join(path.read_bytes() for path in paths)).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--receipt-out", type=Path)
    parser.add_argument("--verify-receipt", type=Path)
    parser.add_argument("--execution-context", choices=("local", "hosted-ci"), default="local")
    parser.add_argument("--expected-execution-context", choices=("local", "hosted-ci"))
    parser.add_argument("--expected-node-major", type=int)
    args = parser.parse_args()
    artifacts = inventory(args.artifact_dir)
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    source_diff = subprocess.check_output(["git", "diff", "HEAD", "--binary"], cwd=ROOT)
    source_diff_digest = hashlib.sha256(source_diff).hexdigest()
    if args.verify_receipt:
        receipt = json.loads(args.verify_receipt.read_text(encoding="utf-8"))
        subject = receipt["subject"]
        if receipt.get("kind") != KIND or receipt.get("status") != "passed":
            raise ValueError("Unsupported or failed native release receipt")
        if subject["release_artifacts"] != artifacts or subject["source_commit"] != source:
            raise ValueError("Stale artifact bytes or source commit")
        if subject["source_diff_sha256"] != source_diff_digest:
            raise ValueError("Tracked source changed since proof")
        if subject["proof_fingerprint"] != proof_identity():
            raise ValueError("Stale native release proof implementation")
        if args.expected_node_major and int(subject["node_version"].lstrip("v").split(".")[0]) != args.expected_node_major:
            raise ValueError("Node runtime mismatch")
        if args.expected_execution_context and receipt["execution_context"] != args.expected_execution_context:
            raise ValueError("Execution context mismatch")
        receipt_id = receipt.pop("receipt_id")
        if receipt_id != hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest():
            raise ValueError("Receipt digest mismatch")
    else:
        if not args.receipt_out:
            parser.error("--receipt-out is required when proving artifacts")
        if args.execution_context == "hosted-ci" and os.environ.get("GITHUB_ACTIONS") != "true":
            raise ValueError("hosted-ci proof requires GitHub Actions")
        if args.execution_context == "hosted-ci" and source_diff:
            raise ValueError("hosted-ci proof requires unchanged tracked source")
        environment = dict(os.environ, AW_NATIVE_ARTIFACT_DIR=str(args.artifact_dir.resolve()))
        subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_native_release_topology.py", "-q"], cwd=ROOT, env=environment, check=True
        )
        if inventory(args.artifact_dir) != artifacts:
            raise ValueError("Artifacts changed during proof")
        receipt = {
            "kind": KIND,
            "status": "passed",
            "execution_context": args.execution_context,
            "subject": {
                "source_commit": source,
                "source_diff_sha256": source_diff_digest,
                "proof_fingerprint": proof_identity(),
                "registry_fingerprint": None,
                "node_version": subprocess.check_output([shutil.which("node"), "--version"], text=True).strip(),
                "artifacts": [entry for entry in artifacts if entry["asset"].endswith(".tgz")],
                "release_artifacts": artifacts,
            },
        }
        receipt["receipt_id"] = hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest()
        args.receipt_out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print("Native release topology receipt verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
