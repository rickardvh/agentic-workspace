from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = Path("src/agentic_workspace/contracts/security_supply_chain_policy.json")
ACTION_REF = re.compile(r"^\s*uses:\s*(?P<action>[^\s#]+)(?:\s+#.*)?$", re.MULTILINE)
PINNED_ACTION = re.compile(r"^(?:\./|docker://|[^@]+@[0-9a-f]{40}$)")


def _sha256_json(value: Any) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def evaluate_security_supply_chain(root: Path = REPO_ROOT) -> dict[str, Any]:
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
    action_ok = not missing_workflows and not unpinned and not missing_permissions
    controls.append(
        {
            "id": "immutable-least-privilege-actions",
            "status": "pass" if action_ok else "fail",
            "missing_workflows": missing_workflows,
            "unpinned": unpinned,
            "missing_permissions": missing_permissions,
        }
    )
    if not action_ok:
        failures.append(
            {
                "control": "immutable-least-privilege-actions",
                "detail": f"missing={missing_workflows}; unpinned={unpinned}; missing_permissions={missing_permissions}",
            }
        )

    security_text = workflow_text.get(".github/workflows/security.yml", "")
    missing_jobs = [job for job in policy["required_security_jobs"] if re.search(rf"(?m)^  {re.escape(job)}:\s*$", security_text) is None]
    controls.append({"id": "blocking-security-scans", "status": "pass" if not missing_jobs else "fail", "missing_jobs": missing_jobs})
    if missing_jobs:
        failures.append({"control": "blocking-security-scans", "detail": f"missing jobs: {', '.join(missing_jobs)}"})

    trusted_path = root / policy["trusted_shell_implementation"]
    source_files = list((root / "src").rglob("*.py")) if (root / "src").exists() else []
    shell_true_paths = []
    for source in source_files:
        if "shell=True" in source.read_text(encoding="utf-8"):
            shell_true_paths.append(source.relative_to(root).as_posix())
    trusted_text = trusted_path.read_text(encoding="utf-8") if trusted_path.is_file() else ""
    missing_sources = [source for source in policy["trusted_shell_sources"] if source not in trusted_text]
    shell_ok = shell_true_paths == [policy["trusted_shell_implementation"]] and not missing_sources
    controls.append(
        {
            "id": "trusted-shell-admission",
            "status": "pass" if shell_ok else "fail",
            "shell_true_paths": shell_true_paths,
            "missing_trust_sources": missing_sources,
        }
    )
    if not shell_ok:
        failures.append(
            {"control": "trusted-shell-admission", "detail": f"shell paths={shell_true_paths}; missing sources={missing_sources}"}
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

    lock_ok = (root / "uv.lock").is_file()
    controls.append({"id": "locked-generator-and-runtime-dependencies", "status": "pass" if lock_ok else "fail", "lock": "uv.lock"})
    if not lock_ok:
        failures.append({"control": "locked-generator-and-runtime-dependencies", "detail": "uv.lock is missing"})

    subject = {
        "policy": policy,
        "workflow_action_refs": sorted(match.group("action") for text in workflow_text.values() for match in ACTION_REF.finditer(text)),
        "trusted_shell_paths": shell_true_paths,
    }
    return {
        "kind": "agentic-workspace/security-supply-chain-readiness/v1",
        "status": "ready" if not failures else "blocked",
        "policy": policy["kind"],
        "subject_fingerprint": _sha256_json(subject),
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
    args = parser.parse_args(argv)
    receipt = evaluate_security_supply_chain()
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
