from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
import tomllib
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = Path("src/tooling/contracts/security_supply_chain_policy.json")
REPOSITORY_PERMISSION_POLICY_PATH = Path(".github/workflow-write-permissions.json")
ACTION_REF = re.compile(r"^\s*uses:\s*(?P<action>[^\s#]+)(?:\s+#.*)?$", re.MULTILINE)
PINNED_ACTION = re.compile(r"^(?:\./\.github/workflows/[A-Za-z0-9_-]+\.ya?ml|docker://|[^@]+@[0-9a-f]{40})$")


def _sha256_json(value: Any) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _source_identity(root: Path) -> str:
    completed = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False)
    return completed.stdout.strip() if completed.returncode == 0 else "unversioned:" + _sha256_file(root / "uv.lock")


def evaluate_security_supply_chain(
    root: Path = REPO_ROOT, *, source_identity: str | None = None, artifact_dir: Path | None = None
) -> dict[str, Any]:
    policy_path = root / POLICY_PATH
    failures: list[dict[str, str]] = []
    if not policy_path.is_file():
        return {
            "kind": "agentic-workspace/security-supply-chain-readiness/v1",
            "status": "blocked",
            "failures": [{"control": "policy", "detail": f"missing {POLICY_PATH.as_posix()}"}],
            "controls": [],
        }
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    repository_permission_policy_path = root / REPOSITORY_PERMISSION_POLICY_PATH
    repository_permission_policy: dict[str, Any] = {}
    if repository_permission_policy_path.is_file():
        repository_permission_policy = json.loads(repository_permission_policy_path.read_text(encoding="utf-8"))
        if repository_permission_policy.get("kind") != "agentic-workspace/repository-workflow-write-permissions/v1":
            failures.append(
                {
                    "control": "repository-workflow-permissions",
                    "detail": f"invalid kind in {REPOSITORY_PERMISSION_POLICY_PATH.as_posix()}",
                }
            )
    controls: list[dict[str, Any]] = []

    missing_documents = [path for path in policy["required_documents"] if not (root / path).is_file()]
    controls.append({"id": "public-security-boundary", "status": "pass" if not missing_documents else "fail", "missing": missing_documents})
    if missing_documents:
        failures.append({"control": "public-security-boundary", "detail": f"missing documents: {', '.join(missing_documents)}"})

    workflow_paths = [root / path for path in policy["required_workflows"]]
    missing_workflows = [path.relative_to(root).as_posix() for path in workflow_paths if not path.is_file()]
    all_workflows = sorted((root / ".github/workflows").glob("*.y*ml")) if (root / ".github/workflows").exists() else []
    unpinned: list[str] = []
    missing_permissions: list[str] = []
    workflow_text: dict[str, str] = {}
    for workflow in all_workflows:
        relative = workflow.relative_to(root).as_posix()
        text = workflow.read_text(encoding="utf-8")
        workflow_text[relative] = text
        if re.search(r"(?m)^permissions:\s*$", text) is None:
            missing_permissions.append(relative)
        if "pull_request_target:" in text:
            failures.append({"control": "workflow-trigger", "detail": f"{relative} uses pull_request_target"})
        for match in ACTION_REF.finditer(text):
            action = match.group("action")
            if not PINNED_ACTION.fullmatch(action):
                unpinned.append(f"{relative}: {action}")
    overbroad_permissions: list[str] = []
    admitted_writes = dict(policy.get("allowed_write_permissions", {}))
    for relative, permissions in repository_permission_policy.get("allowed_write_permissions", {}).items():
        admitted_writes[relative] = sorted(set(admitted_writes.get(relative, [])) | set(permissions))
    for relative, text in workflow_text.items():
        observed_writes = set(re.findall(r"(?m)^\s*([a-z-]+):\s*write(?:\s+#.*)?$", text))
        allowed_writes = set(admitted_writes.get(relative, []))
        unexpected = sorted(observed_writes - allowed_writes)
        if unexpected:
            overbroad_permissions.append(f"{relative}: {','.join(unexpected)}")
    action_ok = not missing_workflows and not unpinned and not missing_permissions and not overbroad_permissions
    controls.append(
        {
            "id": "immutable-least-privilege-actions",
            "status": "pass" if action_ok else "fail",
            "missing_workflows": missing_workflows,
            "unpinned": unpinned,
            "missing_permissions": missing_permissions,
            "overbroad_permissions": sorted(set(overbroad_permissions)),
        }
    )
    if not action_ok:
        failures.append(
            {
                "control": "immutable-least-privilege-actions",
                "detail": f"missing={missing_workflows}; unpinned={unpinned}; missing_permissions={missing_permissions}; overbroad={sorted(set(overbroad_permissions))}",
            }
        )

    security_text = workflow_text.get(".github/workflows/security.yml", "")
    scanner_actions = {
        "dependency-review": "actions/dependency-review-action@",
        "codeql": "github/codeql-action/analyze@",
        "secret-scan": "gitleaks/gitleaks-action@",
    }
    missing_jobs = [job for job in policy["required_security_jobs"] if re.search(rf"(?m)^  {re.escape(job)}:\s*$", security_text) is None]
    missing_scanners = [job for job, action in scanner_actions.items() if action not in security_text]
    non_blocking = bool(re.search(r"(?m)^\s*continue-on-error:\s*true\s*$", security_text))
    scans_ok = not missing_jobs and not missing_scanners and not non_blocking
    controls.append(
        {
            "id": "blocking-security-scans",
            "status": "pass" if scans_ok else "fail",
            "missing_jobs": missing_jobs,
            "missing_scanners": missing_scanners,
            "non_blocking": non_blocking,
        }
    )
    if not scans_ok:
        failures.append(
            {
                "control": "blocking-security-scans",
                "detail": f"missing jobs={missing_jobs}; missing scanners={missing_scanners}; non_blocking={non_blocking}",
            }
        )

    rust_policy = policy["rust_dependencies"]
    rust_paths = [
        Path(rust_policy["config"]),
        Path(rust_policy["runner"]),
        Path("Cargo.lock"),
        Path("Cargo.toml"),
        Path("rust-toolchain.toml"),
    ]
    rust_paths.extend([Path("src/core/Cargo.toml"), Path("src/cli/rust/Cargo.toml")])
    missing_rust = [path.as_posix() for path in rust_paths if not (root / path).is_file()]
    rust_command = f"python {rust_policy['runner']} --install"
    missing_rust_gates = [
        path
        for path in (".github/workflows/security.yml", ".github/workflows/release.yml", ".github/workflows/preview-release.yml")
        if rust_command not in workflow_text.get(path, "")
    ]
    rust_ok = not missing_rust and not missing_rust_gates and re.fullmatch(r"\d+\.\d+\.\d+", rust_policy["version"]) is not None
    controls.append(
        {
            "id": "rust-dependency-policy-wiring",
            "status": "pass" if rust_ok else "fail",
            "missing": missing_rust,
            "missing_gates": missing_rust_gates,
        }
    )
    if not rust_ok:
        failures.append(
            {
                "control": "rust-dependency-policy-wiring",
                "detail": f"missing={missing_rust}; missing gates={missing_rust_gates}; exact tool version required",
            }
        )

    trusted_path = root / policy["trusted_shell_implementation"]
    source_files = list((root / "src").rglob("*.py")) if (root / "src").exists() else []
    shell_true_paths = []
    for source in source_files:
        tree = ast.parse(source.read_text(encoding="utf-8"))
        if any(
            isinstance(node, ast.Call)
            and any(keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True
                    for keyword in node.keywords)
            for node in ast.walk(tree)
        ):
            shell_true_paths.append(source.relative_to(root).as_posix())
    trusted_text = trusted_path.read_text(encoding="utf-8") if trusted_path.is_file() else ""
    missing_sources = []
    declared_boundary_present = all(
        marker in trusted_text
        for marker in (
            "proof selection is not a current source-declared command",
            "crate::attempt_store::admit(",
            "revalidate()?;",
            "Command::new(executable)",
        )
    )
    shell_ok = not shell_true_paths and not missing_sources and declared_boundary_present
    controls.append(
        {
            "id": "trusted-shell-admission",
            "status": "pass" if shell_ok else "fail",
            "shell_true_paths": shell_true_paths,
            "missing_trust_sources": missing_sources,
            "declared_boundary_present": declared_boundary_present,
        }
    )
    if not shell_ok:
        failures.append(
            {
                "control": "trusted-shell-admission",
                "detail": (
                    f"implicit shell paths={shell_true_paths}; missing sources={missing_sources}; "
                    f"declared boundary={declared_boundary_present}"
                ),
            }
        )

    release_text = workflow_text.get(".github/workflows/release.yml", "")
    release_tokens = {
        "locked-dependency-resolution": "uv sync --locked",
        "security-readiness-receipt": "security-supply-chain-readiness.json",
        "sbom": "anchore/sbom-action@",
        "checksums": "SHA256SUMS",
        "exact-source-manifest": "agentic-workspace-release-manifest.json",
        "artifact-attestation": "actions/attest-build-provenance@",
    }
    missing_release = [requirement for requirement in policy["release_requirements"] if release_tokens[requirement] not in release_text]
    controls.append({"id": "release-provenance", "status": "pass" if not missing_release else "fail", "missing": missing_release})
    if missing_release:
        failures.append({"control": "release-provenance", "detail": f"missing release controls: {', '.join(missing_release)}"})

    lock_path = root / "uv.lock"
    project_path = root / "pyproject.toml"
    project = tomllib.loads(project_path.read_text(encoding="utf-8")) if project_path.is_file() else {}
    members = project.get("tool", {}).get("uv", {}).get("workspace", {}).get("members", [])
    shadow_locks = sorted(
        (member / "uv.lock").relative_to(root).as_posix()
        for pattern in members
        for member in root.glob(pattern)
        if (member / "uv.lock").is_file()
    )
    unlocked_syncs = [relative for relative, text in workflow_text.items() if re.search(r"(?m)^\s*uv sync(?![^\n]*--locked)", text)]
    lock_ok = lock_path.is_file() and project_path.is_file() and not unlocked_syncs and not shadow_locks
    controls.append(
        {
            "id": "locked-generator-and-runtime-dependencies",
            "status": "pass" if lock_ok else "fail",
            "lock": "uv.lock",
            "unlocked_workflows": unlocked_syncs,
            "shadow_workspace_locks": shadow_locks,
        }
    )
    if not lock_ok:
        failures.append(
            {
                "control": "locked-generator-and-runtime-dependencies",
                "detail": f"Missing workspace lock/project, unlocked syncs: {unlocked_syncs}, or shadow member locks: {shadow_locks}",
            }
        )

    security_paths = [
        POLICY_PATH,
        *([REPOSITORY_PERMISSION_POLICY_PATH] if repository_permission_policy_path.is_file() else []),
        Path("src/tooling/check/check_security_supply_chain.py"),
        Path("uv.lock"),
        Path("pyproject.toml"),
        *rust_paths,
        Path(".github/workflows/preview-release.yml"),
        *[Path(path) for path in policy["required_workflows"]],
    ]
    artifacts: dict[str, str] = {}
    if artifact_dir is not None:
        artifacts = {
            path.relative_to(artifact_dir).as_posix(): _sha256_file(path)
            for path in sorted(artifact_dir.rglob("*"))
            if path.is_file() and path.name != "security-supply-chain-readiness.json"
        }
    subject = {
        "source_identity": source_identity or _source_identity(root),
        "policy": policy,
        "security_surface_hashes": {path.as_posix(): _sha256_file(root / path) for path in security_paths if (root / path).is_file()},
        "workflow_action_refs": sorted(match.group("action") for text in workflow_text.values() for match in ACTION_REF.finditer(text)),
        "trusted_shell_paths": shell_true_paths,
        "release_subject": {
            "manifest": "agentic-workspace-release-manifest.json",
            "checksums": "SHA256SUMS",
            "sbom": "agentic-workspace.spdx.json",
            "attestation": "build-provenance",
            "artifacts": artifacts,
        },
    }
    return {
        "kind": "agentic-workspace/security-supply-chain-readiness/v1",
        "status": "ready" if not failures else "blocked",
        "policy": policy["kind"],
        "subject_fingerprint": _sha256_json(subject),
        "subject": subject,
        "controls": controls,
        "failures": failures,
        "release_promotion_allowed": not failures,
        "branch_enforcement_owner": policy["branch_enforcement_owner"],
        "trust_boundary": "trusted-repository-required; lifecycle dry-run is not a sandbox",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=("json", "text"), default="text")
    parser.add_argument("--output")
    parser.add_argument("--source-identity")
    parser.add_argument("--artifact-dir", type=Path)
    args = parser.parse_args(argv)
    receipt = evaluate_security_supply_chain(source_identity=args.source_identity, artifact_dir=args.artifact_dir)
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    if args.format == "json":
        print(rendered, end="")
    else:
        print(f"security supply-chain readiness: {receipt['status']}")
        for failure in receipt["failures"]:
            print(f"- {failure['control']}: {failure['detail']}")
    return 0 if receipt["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
