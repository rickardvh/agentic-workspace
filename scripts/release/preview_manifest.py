from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tomllib
from pathlib import Path
from typing import Any

import coordinated_release

ROOT = Path(__file__).resolve().parents[2]
OWNERSHIP_PATH = ROOT / ".github" / "release-ownership.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def _unique_artifact(dist: Path, pattern: str) -> Path:
    matches = sorted(dist.glob(pattern))
    if len(matches) != 1:
        raise SystemExit(f"Expected exactly one preview artifact matching {pattern!r}, got {[path.name for path in matches]}")
    return matches[0]


def _require_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"Missing required preview artifact {path.name}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"Preview artifact {path.name} must contain a JSON object")
    return value


def build_preview_manifest(*, tag: str, artifact_dir: Path) -> dict[str, Any]:
    ownership = json.loads(OWNERSHIP_PATH.read_text(encoding="utf-8"))
    verified = coordinated_release.verify_preview_release(ownership, tag=tag)
    version = verified["version"]
    artifact_commit = verified["artifact_commit"]
    reconstruction_source_commit = verified["reconstruction_source_commit"]
    dist = artifact_dir.resolve()
    dist.mkdir(parents=True, exist_ok=True)

    package_entries: list[dict[str, Any]] = []
    expected_assets: set[str] = set()

    for package in ownership["packages"]:
        pyproject = ROOT / package["pyproject"]
        declared = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]
        if declared != version:
            raise SystemExit(f"{package['pyproject']} has version {declared}, expected preview version {version}")
        wheel = _unique_artifact(dist, f"{package['wheel_prefix']}-{version}-*.whl")
        sdist = _unique_artifact(dist, f"{package['sdist_prefix']}-{version}.tar.gz")
        expected_assets.update({wheel.name, sdist.name})
        package_entries.append(
            {
                "name": package["name"],
                "ecosystem": "python",
                "version": version,
                "pyproject": package["pyproject"],
                "wheel": {"asset": wheel.name, "sha256": _sha256(wheel)},
                "sdist": {"asset": sdist.name, "sha256": _sha256(sdist)},
                "payload_schema": package["payload_schema"],
                "payload_provenance": package["payload_provenance"],
                "generated_command_contract": package["generated_command_contract"],
                "license_spdx": ownership["project_identity"]["license_spdx"],
            }
        )

    for package in ownership["typescript_packages"]:
        package_json = json.loads((ROOT / package["package_json"]).read_text(encoding="utf-8"))
        if package_json.get("version") != version:
            raise SystemExit(f"{package['package_json']} has version {package_json.get('version')}, expected {version}")
        if package_json.get("private") is not True or package.get("release_policy") != "release-asset-only":
            raise SystemExit(f"{package['package_json']} must remain private release-asset-only for preview publication")
        tarball = _unique_artifact(dist, f"{package['tarball_prefix']}-{version}.tgz")
        expected_assets.add(tarball.name)
        package_entries.append(
            {
                "name": package["name"],
                "ecosystem": "npm",
                "version": version,
                "package_json": package["package_json"],
                "package_root": package["package_root"],
                "tarball": {"asset": tarball.name, "sha256": _sha256(tarball)},
                "entrypoints": package["entrypoints"],
                "python_package": package["python_package"],
                "runtime": package["runtime"],
                "runtime_requirement": package["runtime_requirement"],
                "release_policy": package["release_policy"],
                "registry_status": package["registry_status"],
                "generated_command_contract": package["generated_command_contract"],
                "license_spdx": ownership["project_identity"]["license_spdx"],
            }
        )

    semantic_receipts: list[dict[str, Any]] = []
    for runtime_major in ownership["semantic_conformance"]["runtime_majors"]:
        receipt_path = dist / f"generated-command-conformance-node{runtime_major}.json"
        receipt = _require_json(receipt_path)
        if receipt.get("kind") != ownership["semantic_conformance"]["receipt_kind"] or receipt.get("status") != "passed":
            raise SystemExit(f"Failed or unsupported semantic-conformance receipt: {receipt_path.name}")
        expected_assets.add(receipt_path.name)
        semantic_receipts.append(
            {
                "asset": receipt_path.name,
                "receipt_id": receipt.get("receipt_id"),
                "node_version": receipt.get("subject", {}).get("node_version"),
                "registry_fingerprint": receipt.get("subject", {}).get("registry_fingerprint"),
                "artifacts": receipt.get("subject", {}).get("artifacts", []),
            }
        )

    distribution_receipt = str(ownership["distribution_identity"]["canonical_install_receipt"])
    redistributable_receipt = str(ownership["distribution_identity"]["redistributable_receipt"])
    security_receipt = "security-supply-chain-readiness.json"
    sbom = "agentic-workspace.spdx.json"
    for asset in (distribution_receipt, redistributable_receipt, security_receipt, sbom):
        path = dist / asset
        if not path.is_file():
            raise SystemExit(f"Missing required preview readiness artifact {asset}")
        expected_assets.add(asset)

    for readiness_asset in (distribution_receipt, redistributable_receipt):
        receipt = _require_json(dist / readiness_asset)
        if receipt.get("status") != "passed" or receipt.get("version") != version:
            raise SystemExit(f"Preview readiness receipt {readiness_asset} does not prove version {version}")

    manifest = {
        "kind": "agentic-workspace/coordinated-preview-release-manifest/v1",
        "release_model": ownership["release_model"],
        "release_class": "preview",
        "support_bearing": False,
        "version": version,
        "tag": tag,
        "artifact_commit": artifact_commit,
        "reconstruction_source_commit": reconstruction_source_commit,
        "all_or_nothing": True,
        "project_identity": ownership["project_identity"],
        "distribution_identity": {
            **ownership["distribution_identity"],
            "release_base_url": f"https://github.com/rickardvh/agentic-workspace/releases/download/{tag}",
        },
        "packages": package_entries,
        "preview_subject": {
            "metadata": verified["preview_metadata"],
            "release_note": verified["release_note"],
            "single_parent_source": reconstruction_source_commit,
        },
        "distribution_install_readiness": distribution_receipt,
        "redistributable_package_readiness": redistributable_receipt,
        "semantic_conformance": {
            "required": True,
            "receipt_kind": ownership["semantic_conformance"]["receipt_kind"],
            "receipts": semantic_receipts,
        },
        "security_supply_chain": {
            "required": True,
            "readiness_receipt": security_receipt,
            "sbom": sbom,
            "provenance": "GitHub artifact attestation over published preview dist/*",
        },
        "support_bearing_promotion": {
            "required": False,
            "receipt": None,
            "reason": "preview releases are external-testing artifacts and do not claim stable/support-bearing admission",
        },
    }

    manifest_path = dist / "agentic-workspace-preview-release-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    expected_assets.add(manifest_path.name)

    checksum_lines = []
    for asset in sorted(expected_assets):
        path = dist / asset
        checksum_lines.append(f"{_sha256(path)}  {asset}")
    (dist / "SHA256SUMS").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compose the exact non-support-bearing preview release manifest and checksums.")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--artifact-dir", type=Path, default=Path("dist"))
    args = parser.parse_args(argv)
    manifest = build_preview_manifest(tag=args.tag, artifact_dir=args.artifact_dir)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
