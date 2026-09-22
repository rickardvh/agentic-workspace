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
    # Bind the complete native product set, including each declared host variant.
    for pattern in (
        "agentic_workspace-*.whl",
        "agentic_workspace-*.tar.gz",
        "agentic-workspace-workspace-cli-*.tgz",
        "agentic-workspace-native-*.zip",
    ):
        paths = list(directory.glob(pattern))
        if not paths or (len(paths) != 1 and not (directory / "platform-release-manifest.json").exists()):
            raise ValueError(f"Expected exactly one {pattern} in {directory}")
        entries.extend({"asset": path.name, "sha256": digest(path)} for path in paths)
    return sorted(entries, key=lambda entry: entry["asset"])


def proof_identity() -> str:
    paths = [Path(__file__), ROOT / "tests/test_native_release_topology.py",
             ROOT / "tests/test_language_facade.py", ROOT / "scripts/check/check_language_facade.py",
             ROOT / "src/agentic_workspace/contracts/source_decision_contract.json"]
    return hashlib.sha256(b"".join(path.read_bytes() for path in paths)).hexdigest()


def verify_receipt(
    receipt: dict,
    *,
    artifact_dir: Path,
    source_commit: str,
    source_diff_sha256: str,
    expected_node_major: int | None = None,
    expected_execution_context: str | None = None,
) -> None:
    """Validate the same exact-subject receipt for standalone and composed admission."""
    if receipt.get("kind") != KIND or receipt.get("status") != "passed":
        raise ValueError("Unsupported or failed native release receipt")
    subject = receipt.get("subject")
    if not isinstance(subject, dict):
        raise ValueError("Missing native release receipt subject")
    if subject.get("release_artifacts") != inventory(artifact_dir) or subject.get("source_commit") != source_commit:
        raise ValueError("Stale artifact bytes or source commit")
    if subject.get("source_diff_sha256") != source_diff_sha256:
        raise ValueError("Tracked source changed since proof")
    if subject.get("proof_fingerprint") != proof_identity():
        raise ValueError("Stale native release proof implementation")
    if expected_node_major and int(str(subject.get("node_version", "")).lstrip("v").split(".")[0]) != expected_node_major:
        raise ValueError("Node runtime mismatch")
    if expected_execution_context and receipt.get("execution_context") != expected_execution_context:
        raise ValueError("Execution context mismatch")
    unsigned = {key: value for key, value in receipt.items() if key != "receipt_id"}
    if receipt.get("receipt_id") != hashlib.sha256(json.dumps(unsigned, sort_keys=True).encode()).hexdigest():
        raise ValueError("Receipt digest mismatch")


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
        verify_receipt(
            receipt,
            artifact_dir=args.artifact_dir,
            source_commit=source,
            source_diff_sha256=source_diff_digest,
            expected_node_major=args.expected_node_major,
            expected_execution_context=args.expected_execution_context,
        )
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
