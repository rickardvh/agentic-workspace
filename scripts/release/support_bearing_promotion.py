from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
import tomllib
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / ".github/support-bearing-promotion.json"


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def python_support_policy_failures(policy: dict[str, Any], root: Path = ROOT) -> list[str]:
    support = policy.get("python_support", {})
    declared = [str(item) for item in support.get("declared", [])]
    roles = {role: str(support.get(role) or "") for role in ("minimum", "primary", "newest")}
    failures: list[str] = []
    if not declared or any(not version for version in roles.values()):
        return ["python support policy must declare minimum, primary, newest, and the supported versions"]
    matrix_roles = {str(item.get("role")): str(item.get("python")) for item in policy.get("runtime_matrix", [])}
    if matrix_roles != roles:
        failures.append(f"runtime matrix roles {matrix_roles} do not match declared Python support roles {roles}")
    intermediate = set(declared) - set(roles.values())
    disposition = support.get("intermediate_disposition", {})
    if (
        not isinstance(disposition, dict)
        or set(disposition) != intermediate
        or any(not str(value).strip() for value in disposition.values())
    ):
        failures.append(f"intermediate Python versions {sorted(intermediate)} require an explicit disposition")

    ownership = _load(root / ".github/release-ownership.json")
    expected_classifier_versions = set(declared)
    for package in ownership.get("packages", []):
        relative = Path(str(package["pyproject"]))
        project = tomllib.loads((root / relative).read_text(encoding="utf-8")).get("project", {})
        requirement = str(project.get("requires-python") or "")
        match = re.fullmatch(r">=(\d+\.\d+)", requirement)
        if match is None or match.group(1) != roles["minimum"]:
            failures.append(f"{relative.as_posix()} requires-python {requirement!r} does not match policy minimum {roles['minimum']}")
        classifiers = {
            str(item).removeprefix("Programming Language :: Python :: ")
            for item in project.get("classifiers", [])
            if str(item).startswith("Programming Language :: Python :: 3.")
        }
        if classifiers != expected_classifier_versions:
            failures.append(f"{relative.as_posix()} Python classifiers {sorted(classifiers)} do not match declared support {declared}")
    return failures


def _github_check_runs(repository: str, commit: str, token: str) -> dict[str, Any]:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/commits/{commit}/check-runs?per_page=100",
        headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}", "X-GitHub-Api-Version": "2022-11-28"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - fixed GitHub API origin
        return json.load(response)


def server_check_receipt(*, repository: str, commit: str, required: list[str], check_runs: dict[str, Any]) -> dict[str, Any]:
    observed = [item for item in check_runs.get("check_runs", []) if isinstance(item, dict)]
    by_name = {str(item.get("name")): item for item in observed}
    checks = []
    failures = []
    for name in required:
        item = by_name.get(name, {})
        conclusion = str(item.get("conclusion") or "")
        status = "passed" if conclusion == "success" and str(item.get("head_sha") or commit) == commit else "blocked"
        checks.append(
            {
                "name": name,
                "status": status,
                "conclusion": conclusion or "missing",
                "head_sha": str(item.get("head_sha") or ""),
                "url": str(item.get("html_url") or ""),
            }
        )
        if status != "passed":
            failures.append(f"required check {name!r} is {conclusion or 'missing'} for {commit}")
    return {
        "kind": "agentic-workspace/server-promotion-receipt/v1",
        "status": "passed" if not failures else "blocked",
        "repository": repository,
        "source_commit": commit,
        "required_checks": checks,
        "failures": failures,
    }


def _github_checks(args: argparse.Namespace) -> int:
    policy = _load(args.policy)
    required = [str(item) for item in (args.required_check or [policy["required_check"]])]
    deadline = time.monotonic() + args.wait_seconds
    while True:
        check_runs = _load(args.check_runs_file) if args.check_runs_file else _github_check_runs(args.repository, args.commit, args.token)
        receipt = server_check_receipt(repository=args.repository, commit=args.commit, required=required, check_runs=check_runs)
        if receipt["status"] == "passed" or args.check_runs_file or time.monotonic() >= deadline:
            _write(args.output, receipt)
            print(json.dumps(receipt, sort_keys=True))
            return 0 if receipt["status"] == "passed" else 1
        time.sleep(min(15, max(1, args.wait_seconds)))


def _runtime_receipt(args: argparse.Namespace) -> int:
    receipt = {
        "kind": "agentic-workspace/runtime-support-receipt/v1",
        "status": "passed",
        "source_commit": args.commit,
        "os": args.os,
        "python": args.python,
        "node": args.node,
        "proof": args.proof,
    }
    _write(args.output, receipt)
    return 0


def _compose(args: argparse.Namespace) -> int:
    policy = _load(args.policy)
    artifact_dir = args.artifact_dir.resolve()
    failures: list[str] = []
    inputs: list[Path] = []
    failures.extend(python_support_policy_failures(policy))

    def require(path: Path, kind: str, status: str) -> dict[str, Any]:
        if not path.is_file():
            failures.append(f"missing receipt: {path.name}")
            return {}
        inputs.append(path)
        payload = _load(path)
        if payload.get("kind") != kind:
            failures.append(f"{path.name} has kind {payload.get('kind')!r}, expected {kind!r}")
        if payload.get("status") != status:
            failures.append(f"{path.name} has status {payload.get('status')!r}, expected {status!r}")
        return payload

    server = require(args.server_receipt, "agentic-workspace/server-promotion-receipt/v1", "passed")
    if server.get("source_commit") != args.commit:
        failures.append("server promotion receipt source commit mismatch")

    runtime_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    for path in sorted(args.runtime_receipt_dir.glob("*.json")):
        payload = require(path, "agentic-workspace/runtime-support-receipt/v1", "passed")
        runtime_by_key[(str(payload.get("os")), str(payload.get("python")), str(payload.get("node")))] = payload
        if payload.get("source_commit") != args.commit:
            failures.append(f"{path.name} source commit mismatch")
    for item in policy["runtime_matrix"]:
        key = (item["os"], item["python"], item["node"])
        if key not in runtime_by_key:
            failures.append(f"missing runtime support receipt for {key}")

    observed_node_majors = set()
    for path in args.semantic_receipt:
        payload = require(path, "agentic-workspace/generated-command-semantic-conformance-receipt/v1", "passed")
        node_version = str(payload.get("subject", {}).get("node_version") or "")
        if node_version:
            observed_node_majors.add(int(node_version.split(".", 1)[0]))
    missing_nodes = sorted(set(policy["semantic_node_majors"]) - observed_node_majors)
    if missing_nodes:
        failures.append(f"missing semantic conformance for Node majors: {missing_nodes}")

    install = require(artifact_dir / policy["receipts"]["install"], "agentic-workspace/distribution-install-readiness/v1", "passed")
    redistribution = require(
        artifact_dir / policy["receipts"]["redistribution"],
        "agentic-workspace/redistributable-package-readiness/v1",
        "passed",
    )
    security = require(artifact_dir / policy["receipts"]["security"], "agentic-workspace/security-supply-chain-readiness/v1", "ready")
    if security.get("release_promotion_allowed") is not True or security.get("subject", {}).get("source_identity") != args.commit:
        failures.append("security receipt does not admit the exact source commit")
    if redistribution.get("license_spdx") != "MIT":
        failures.append("redistribution receipt does not prove MIT licensing")
    declared_artifacts = redistribution.get("artifacts", [])
    declared_artifact_map = {
        str(item.get("name")): str(item.get("sha256")) for item in declared_artifacts if isinstance(item, dict) and item.get("name")
    }
    distributable_suffixes = (".whl", ".tar.gz", ".tgz")
    actual_artifact_map = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in artifact_dir.iterdir()
        if path.is_file() and path.name.endswith(distributable_suffixes)
    }
    if (
        len(declared_artifact_map) != len(declared_artifacts)
        or redistribution.get("artifact_count") != len(declared_artifact_map)
        or declared_artifact_map != actual_artifact_map
    ):
        failures.append("redistribution receipt does not bind the exact distributable artifact names and sha256 digests")
    artifact = install.get("artifact", {})
    artifact_path = artifact_dir / str(artifact.get("name") or "")
    if not artifact_path.is_file() or artifact.get("sha256") != hashlib.sha256(artifact_path.read_bytes()).hexdigest():
        failures.append("install receipt artifact hash mismatch")

    excluded = {args.output.resolve()}
    artifacts = {
        path.relative_to(artifact_dir).as_posix(): _digest(path)
        for path in sorted(artifact_dir.rglob("*"))
        if path.is_file() and path.resolve() not in excluded
    }
    result = {
        "kind": "agentic-workspace/support-bearing-promotion/v1",
        "status": "passed" if not failures else "blocked",
        "source_commit": args.commit,
        "artifacts": artifacts,
        "inputs": {path.name: _digest(path) for path in inputs},
        "domains": {
            "server_promotion": server.get("status", "missing"),
            "runtime_support": "passed" if not any("runtime" in failure for failure in failures) else "blocked",
            "semantic_conformance": "passed" if not missing_nodes else "blocked",
            "install_identity": install.get("status", "missing"),
            "redistribution": redistribution.get("status", "missing"),
            "security_supply_chain": security.get("status", "missing"),
        },
        "failures": failures,
        "next_action": failures[0] if failures else "publish the exact judged artifacts",
    }
    _write(args.output, result)
    print(json.dumps(result, sort_keys=True))
    return 0 if not failures else 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compose support-bearing release promotion evidence.")
    parser.add_argument("--policy", type=Path, default=POLICY_PATH)
    subparsers = parser.add_subparsers(dest="command", required=True)
    checks = subparsers.add_parser("github-checks")
    checks.add_argument("--repository", required=True)
    checks.add_argument("--commit", required=True)
    checks.add_argument("--required-check", action="append")
    checks.add_argument("--check-runs-file", type=Path)
    checks.add_argument("--token", default=os.environ.get("GH_TOKEN", ""))
    checks.add_argument("--wait-seconds", type=int, default=900)
    checks.add_argument("--output", type=Path, required=True)
    runtime = subparsers.add_parser("runtime-receipt")
    runtime.add_argument("--commit", required=True)
    runtime.add_argument("--os", required=True)
    runtime.add_argument("--python", required=True)
    runtime.add_argument("--node", required=True)
    runtime.add_argument("--proof", required=True)
    runtime.add_argument("--output", type=Path, required=True)
    compose = subparsers.add_parser("compose")
    compose.add_argument("--commit", required=True)
    compose.add_argument("--artifact-dir", type=Path, required=True)
    compose.add_argument("--server-receipt", type=Path, required=True)
    compose.add_argument("--runtime-receipt-dir", type=Path, required=True)
    compose.add_argument("--semantic-receipt", type=Path, action="append", required=True)
    compose.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return {"github-checks": _github_checks, "runtime-receipt": _runtime_receipt, "compose": _compose}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
