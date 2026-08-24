#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path
from typing import NamedTuple, TypedDict

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPACT_RUNNER = REPO_ROOT / "scripts" / "check" / "run_compact_command.py"
GENERATED_PACKAGE_CHECK = REPO_ROOT / "scripts" / "check" / "check_generated_command_packages.py"
COMMAND_PACKAGE_IR = REPO_ROOT / "src" / "agentic_workspace" / "contracts" / "command_package_ir.json"
CONFORMANCE_REGISTRY = REPO_ROOT / "src" / "agentic_workspace" / "contracts" / "conformance_contracts.json"


class ProofStep(NamedTuple):
    label: str
    args: list[str]


class TypescriptPackage(TypedDict):
    id: str
    generated_root: str
    name: str
    runnable: bool


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _registry_fingerprint() -> str:
    registry = json.loads(CONFORMANCE_REGISTRY.read_text(encoding="utf-8"))
    paths = [COMMAND_PACKAGE_IR, CONFORMANCE_REGISTRY]
    contract_roots = [
        REPO_ROOT / "src" / "agentic_workspace" / "contracts",
        REPO_ROOT / "packages" / "planning" / "src" / "repo_planning_bootstrap" / "contracts",
        REPO_ROOT / "packages" / "memory" / "src" / "repo_memory_bootstrap" / "contracts",
        REPO_ROOT / "packages" / "verification" / "src" / "repo_verification_bootstrap" / "contracts",
    ]
    for item in registry["contracts"]:
        relative = Path(str(item["path"]))
        matches = [root / relative for root in contract_roots if (root / relative).is_file()]
        if not matches:
            raise RuntimeError(f"registered conformance contract is missing: {relative.as_posix()}")
        paths.extend(matches)
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.relative_to(REPO_ROOT).as_posix().encode())
        digest.update(path.read_bytes())
    return f"sha256:{digest.hexdigest()}"


def _typescript_packages() -> list[TypescriptPackage]:
    ir = json.loads(COMMAND_PACKAGE_IR.read_text(encoding="utf-8"))
    packages: list[dict[str, str]] = []
    for package in ir["packages"]:
        for target in package.get("targets", []):
            if target.get("kind") != "typescript":
                continue
            root = REPO_ROOT / str(target["generated_root"])
            metadata = json.loads((root / "package.json").read_text(encoding="utf-8"))
            packages.append(
                {
                    "id": str(package["id"]),
                    "generated_root": str(target["generated_root"]),
                    "name": str(metadata["name"]),
                    "runnable": target.get("maturity_level_ref")
                    in {"runnable-read-only-adapter", "weak-agent-safe-adapter", "mutation-capable-adapter"},
                }
            )
    return packages


def _pack_packages(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    npm = shutil.which("npm")
    if npm is None:
        raise RuntimeError("npm is required to pack generated TypeScript artifacts")
    for package in _typescript_packages():
        prefix = package["name"].split("/")[-1].replace("_", "-")
        matches = sorted(destination.glob(f"*{prefix}-*.tgz"))
        if len(matches) == 1:
            continue
        if len(matches) > 1:
            raise RuntimeError(f"expected at most one packed artifact for {package['name']}, found {len(matches)} in {destination}")
        subprocess.run(
            [npm, "pack", "--pack-destination", str(destination.resolve())],
            cwd=REPO_ROOT / package["generated_root"],
            check=True,
            text=True,
            capture_output=True,
        )


def _tarball_for_package(artifact_dir: Path, package_name: str) -> Path:
    prefix = package_name.split("/")[-1].replace("_", "-")
    matches = sorted(artifact_dir.glob(f"*{prefix}-*.tgz"))
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one packed artifact for {package_name}, found {len(matches)} in {artifact_dir}")
    return matches[0]


def _extract_tarball(tarball: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tarball, "r:gz") as archive:
        for member in archive.getmembers():
            parts = Path(member.name).parts
            if not parts or parts[0] != "package" or len(parts) == 1:
                continue
            relative = Path(*parts[1:])
            target = (destination / relative).resolve()
            if destination.resolve() not in target.parents:
                raise RuntimeError(f"unsafe tar member in {tarball.name}: {member.name}")
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                raise RuntimeError(f"unsupported non-file tar member in {tarball.name}: {member.name}")
            source = archive.extractfile(member)
            if source is None:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read())


def _run_packed_conformance(*, artifact_dir: Path, receipt_out: Path | None) -> int:
    packages = _typescript_packages()
    _pack_packages(artifact_dir)
    with tempfile.TemporaryDirectory(prefix="aw-packed-typescript-conformance-") as tmp:
        extracted = Path(tmp)
        artifact_records = []
        for package in packages:
            tarball = _tarball_for_package(artifact_dir, package["name"])
            _extract_tarball(tarball, extracted / package["generated_root"])
            artifact_records.append(
                {
                    "package_id": package["id"],
                    "package_name": package["name"],
                    "asset": tarball.name,
                    "sha256": _sha256(tarball),
                    "runnable": package["runnable"],
                    "conformance_status": "passed" if package["runnable"] else "not-required-not-runnable",
                }
            )
        command = [
            sys.executable,
            str(GENERATED_PACKAGE_CHECK),
            "--conformance",
            "--require-node",
            "--typescript-artifact-root",
            str(extracted),
        ]
        completed = subprocess.run(command, cwd=REPO_ROOT, check=False)
        if completed.returncode:
            return completed.returncode
    node_version = subprocess.run(["node", "--version"], check=True, text=True, capture_output=True).stdout.strip()
    registry_fingerprint = _registry_fingerprint()
    subject = {"artifacts": artifact_records, "registry_fingerprint": registry_fingerprint, "node_version": node_version}
    receipt_id = f"sha256:{hashlib.sha256(json.dumps(subject, sort_keys=True, separators=(',', ':')).encode()).hexdigest()}"
    receipt = {
        "kind": "agentic-workspace/generated-command-semantic-conformance-receipt/v1",
        "status": "passed",
        "receipt_id": receipt_id,
        "subject": subject,
        "proof": {
            "command": "scripts/check/run_generated_command_package_proof.py --packed-conformance",
            "exact_packed_artifacts": True,
            "complete_registry": True,
        },
    }
    if receipt_out is not None:
        receipt_out.parent.mkdir(parents=True, exist_ok=True)
        receipt_out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0


def _node_major(version: object) -> int | None:
    match = re.fullmatch(r"v(?P<major>[1-9][0-9]*)\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?", str(version or "").strip())
    return int(match.group("major")) if match else None


def _verify_receipt(path: Path, *, artifact_dir: Path, expected_node_major: int) -> int:
    if not path.is_file():
        print(f"missing semantic-conformance receipt: {path}", file=sys.stderr)
        return 1
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if receipt.get("kind") != "agentic-workspace/generated-command-semantic-conformance-receipt/v1" or receipt.get("status") != "passed":
        print(f"failed or unsupported semantic-conformance receipt: {path}", file=sys.stderr)
        return 1
    subject = receipt.get("subject", {})
    expected_receipt_id = f"sha256:{hashlib.sha256(json.dumps(subject, sort_keys=True, separators=(',', ':')).encode()).hexdigest()}"
    if receipt.get("receipt_id") != expected_receipt_id:
        print(f"semantic-conformance receipt identity mismatch: {path}", file=sys.stderr)
        return 1
    if subject.get("registry_fingerprint") != _registry_fingerprint():
        print(f"stale semantic-conformance registry fingerprint: {path}", file=sys.stderr)
        return 1
    actual_node_major = _node_major(subject.get("node_version"))
    if actual_node_major != expected_node_major:
        print(
            f"semantic-conformance runtime mismatch: {path} proves Node {actual_node_major!r}, expected Node {expected_node_major}",
            file=sys.stderr,
        )
        return 1
    artifacts = subject.get("artifacts", [])
    if not isinstance(artifacts, list):
        print(f"semantic-conformance receipt artifact inventory is invalid: {path}", file=sys.stderr)
        return 1
    expected_packages = {package["name"]: package for package in _typescript_packages()}
    actual_packages = {str(artifact.get("package_name", "")): artifact for artifact in artifacts}
    if actual_packages.keys() != expected_packages.keys():
        print(f"semantic-conformance receipt package inventory mismatch: {path}", file=sys.stderr)
        return 1
    for package_name, artifact in actual_packages.items():
        package = expected_packages[package_name]
        expected_status = "passed" if package["runnable"] else "not-required-not-runnable"
        if artifact.get("runnable") is not package["runnable"] or artifact.get("conformance_status") != expected_status:
            print(f"semantic-conformance support status mismatch for {package_name}: {path}", file=sys.stderr)
            return 1
        tarball = artifact_dir / str(artifact.get("asset", ""))
        if not tarball.is_file() or _sha256(tarball) != artifact.get("sha256"):
            print(f"semantic-conformance artifact mismatch: {tarball}", file=sys.stderr)
            return 1
    print(f"[ok] semantic-conformance receipt {receipt['receipt_id']}")
    return 0


def _format_duration(duration_seconds: float) -> str:
    if duration_seconds < 1:
        return f"{duration_seconds * 1000:.0f}ms"
    return f"{duration_seconds:.2f}s"


def _proof_steps(args: argparse.Namespace) -> list[ProofStep]:
    requested = {
        "static": bool(args.static),
        "python_conformance": bool(args.python_conformance),
        "python_docker_conformance": bool(args.python_docker_conformance),
        "primitive_conformance": bool(args.primitive_conformance),
        "primitive_docker_conformance": bool(args.primitive_docker_conformance),
        "conformance": bool(args.conformance),
        "docker": bool(args.docker),
        "docker_conformance": bool(args.docker_conformance),
    }
    if args.all:
        requested = dict.fromkeys(requested, True)
    if not any(requested.values()):
        requested["python_docker_conformance"] = True
        requested["primitive_docker_conformance"] = True
        requested["docker"] = True
        requested["docker_conformance"] = True

    steps: list[ProofStep] = []
    if requested["static"]:
        steps.append(ProofStep("generated packages static", []))
        steps.append(ProofStep("ordinary output profile budgets", []))
    if requested["python_conformance"]:
        steps.append(ProofStep("generated packages python conformance", ["--python-conformance"]))
    if requested["python_docker_conformance"]:
        steps.append(ProofStep("generated packages python docker conformance", ["--python-docker-conformance", "--require-docker"]))
    if requested["primitive_conformance"]:
        steps.append(ProofStep("generated packages primitive conformance", ["--primitive-conformance"]))
    if requested["primitive_docker_conformance"]:
        steps.append(ProofStep("generated packages primitive docker conformance", ["--primitive-docker-conformance", "--require-docker"]))
    if requested["conformance"]:
        steps.append(ProofStep("generated packages conformance", ["--conformance", "--require-node"]))
    if requested["docker"]:
        steps.append(ProofStep("generated packages docker", ["--docker", "--require-docker"]))
    if requested["docker_conformance"]:
        steps.append(ProofStep("generated packages docker conformance", ["--docker-conformance", "--require-docker"]))
    return steps


def _run_step(step: ProofStep, *, timeout_seconds: float | None, failure_tail_lines: int) -> int:
    command = [
        sys.executable,
        str(COMPACT_RUNNER),
        "--label",
        step.label,
        "--failure-tail-lines",
        str(failure_tail_lines),
    ]
    if timeout_seconds is not None:
        command.extend(["--timeout-seconds", f"{timeout_seconds:g}"])
    if step.label == "ordinary output profile budgets":
        command.extend(["--", sys.executable, "-m", "pytest", "tests/test_output_profile_budgets.py", "-q"])
    else:
        command.extend(["--", sys.executable, str(GENERATED_PACKAGE_CHECK), *step.args])
    return subprocess.run(command, cwd=REPO_ROOT, check=False).returncode


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than 0")
    return parsed


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run generated command package proof through compact command wrappers.",
    )
    parser.add_argument("--static", action="store_true", help="Run static generated-package proof.")
    parser.add_argument("--python-conformance", action="store_true", help="Run generated Python adapter conformance proof.")
    parser.add_argument("--python-docker-conformance", action="store_true", help="Run generated Python adapter Docker conformance proof.")
    parser.add_argument("--primitive-conformance", action="store_true", help="Run codegen-owned primitive conformance proof.")
    parser.add_argument("--primitive-docker-conformance", action="store_true", help="Run codegen-owned primitive Docker conformance proof.")
    parser.add_argument("--conformance", action="store_true", help="Run local Node adapter conformance proof.")
    parser.add_argument("--docker", action="store_true", help="Run Docker package proof.")
    parser.add_argument("--docker-conformance", action="store_true", help="Run Docker adapter conformance proof.")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run static, Python conformance, Python Docker conformance, primitive conformance, primitive Docker conformance, local Node conformance, Docker, and Docker conformance proof.",
    )
    parser.add_argument(
        "--packed-conformance", action="store_true", help="Run complete conformance against exact npm tarballs and emit a receipt."
    )
    parser.add_argument("--artifact-dir", type=Path, help="Directory containing or receiving exact npm tarballs.")
    parser.add_argument("--receipt-out", type=Path, help="Write the packed-artifact conformance receipt to this path.")
    parser.add_argument(
        "--verify-receipt", type=Path, help="Fail closed unless this receipt matches the current registry and exact artifacts."
    )
    parser.add_argument(
        "--expected-node-major",
        type=_positive_int,
        help="Required Node major that a verified semantic-conformance receipt must prove.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=_positive_float,
        default=300,
        help="Per-step timeout passed to the compact runner. Defaults to 300 seconds.",
    )
    parser.add_argument(
        "--failure-tail-lines",
        type=int,
        default=80,
        help="Per-step failure tail lines passed to the compact runner.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.verify_receipt:
        if args.artifact_dir is None:
            raise SystemExit("--verify-receipt requires --artifact-dir")
        if args.expected_node_major is None:
            raise SystemExit("--verify-receipt requires --expected-node-major")
        return _verify_receipt(
            args.verify_receipt.resolve(),
            artifact_dir=args.artifact_dir.resolve(),
            expected_node_major=args.expected_node_major,
        )
    if args.packed_conformance:
        if args.artifact_dir is not None:
            return _run_packed_conformance(
                artifact_dir=args.artifact_dir.resolve(),
                receipt_out=args.receipt_out.resolve() if args.receipt_out else None,
            )
        with tempfile.TemporaryDirectory(prefix="aw-command-package-artifacts-") as tmp:
            return _run_packed_conformance(
                artifact_dir=Path(tmp),
                receipt_out=args.receipt_out.resolve() if args.receipt_out else None,
            )
    started = time.perf_counter()
    steps = _proof_steps(args)
    for step in steps:
        status = _run_step(
            step,
            timeout_seconds=args.timeout_seconds,
            failure_tail_lines=max(1, int(args.failure_tail_lines)),
        )
        if status:
            return status
    print(f"[ok] generated command package proof ({len(steps)} steps, {_format_duration(time.perf_counter() - started)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
