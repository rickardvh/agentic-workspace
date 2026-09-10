from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

import coordinated_release

ROOT = Path(__file__).resolve().parents[2]
OWNERSHIP_PATH = ROOT / ".github" / "release-ownership.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def _preview_base_url(ownership: dict[str, Any], version: str) -> str:
    template = str(ownership["distribution_identity"]["preview_release_base_url_template"])
    return template.format(version=version)


def _write_preview_readiness_receipts(
    *,
    ownership: dict[str, Any],
    dist: Path,
    tag: str,
    version: str,
    package_entries: list[dict[str, Any]],
) -> tuple[str, str]:
    distribution = ownership["distribution_identity"]
    root_name = distribution["canonical_root_distribution"]
    root_package = next(package for package in package_entries if package["ecosystem"] == "python" and package["name"] == root_name)
    root_wheel = root_package["wheel"]
    base_url = _preview_base_url(ownership, version)
    identity_digest = _sha256(OWNERSHIP_PATH)

    distribution_receipt = str(distribution["canonical_install_receipt"])
    redistributable_receipt = str(distribution["redistributable_receipt"])
    requirement = f"{root_name} @ {base_url}/{root_wheel['asset']}#sha256={root_wheel['sha256']}"
    install = {
        "kind": "agentic-workspace/distribution-install-readiness/v1",
        "status": "passed",
        "release_class": "preview",
        "support_bearing": False,
        "version": version,
        "tag": tag,
        "artifact": {
            "name": root_wheel["asset"],
            "sha256": root_wheel["sha256"],
            "url": f"{base_url}/{root_wheel['asset']}",
        },
        "install": {
            "requirement": requirement,
            "command": f'uv tool install "{requirement}"',
        },
        "second_process_command": 'agentic-workspace start --target . --task "<task>" --format json',
        "registry_resolution_used": False,
        "identity": {"source": OWNERSHIP_PATH.relative_to(ROOT).as_posix(), "sha256": identity_digest},
    }

    redistributable_artifacts: list[dict[str, str]] = []
    for package in package_entries:
        if package["ecosystem"] == "python":
            redistributable_artifacts.extend([package["wheel"], package["sdist"]])
        else:
            redistributable_artifacts.append(package["tarball"])
    redistributable_artifacts = sorted(
        [{"name": item["asset"], "sha256": item["sha256"]} for item in redistributable_artifacts],
        key=lambda item: item["name"],
    )
    redistributable = {
        "kind": "agentic-workspace/redistributable-package-readiness/v1",
        "status": "passed",
        "release_class": "preview",
        "support_bearing": False,
        "version": version,
        "tag": tag,
        "license_spdx": ownership["project_identity"]["license_spdx"],
        "identity_source": OWNERSHIP_PATH.relative_to(ROOT).as_posix(),
        "identity_sha256": identity_digest,
        "artifact_count": len(redistributable_artifacts),
        "artifacts": redistributable_artifacts,
    }
    (dist / distribution_receipt).write_text(json.dumps(install, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (dist / redistributable_receipt).write_text(json.dumps(redistributable, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return distribution_receipt, redistributable_receipt


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

    # Shared package checks remain authoritative; preview additionally binds
    # every coordinated root dependency to this release and these exact bytes.
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check/check_package_identity.py"),
            "--root",
            str(ROOT),
            "--artifact-dir",
            str(dist),
            "--require-exact-urls",
        ],
        check=True,
        stdout=sys.stderr,
    )
    verify_preview_dependencies(ownership=ownership, dist=dist, version=version)

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

    distribution_receipt, redistributable_receipt = _write_preview_readiness_receipts(
        ownership=ownership,
        dist=dist,
        tag=tag,
        version=version,
        package_entries=package_entries,
    )
    expected_assets.update({distribution_receipt, redistributable_receipt})

    semantic_receipts: list[dict[str, Any]] = []
    for runtime_major in ownership["semantic_conformance"]["runtime_majors"]:
        receipt_path = dist / f"generated-command-conformance-node{runtime_major}.json"
        receipt = _require_json(receipt_path)
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/check/run_generated_command_package_proof.py"),
                "--verify-receipt",
                str(receipt_path),
                "--artifact-dir",
                str(dist),
                "--expected-node-major",
                str(runtime_major),
            ],
            check=True,
            stdout=sys.stderr,
        )
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

    security_receipt = "security-supply-chain-readiness.json"
    sbom = "agentic-workspace.spdx.json"
    for asset in (security_receipt, sbom):
        path = dist / asset
        if not path.is_file():
            raise SystemExit(f"Missing required preview readiness artifact {asset}")
        expected_assets.add(asset)
    security = _require_json(dist / security_receipt)
    if security.get("status") != "ready" or security.get("subject", {}).get("source_identity") != artifact_commit:
        raise SystemExit("Preview security receipt is failed or belongs to another artifact commit")
    security_artifacts = security["subject"]["release_subject"]["artifacts"]
    for entry in package_entries:
        for key in ("wheel", "sdist", "tarball"):
            if key in entry and security_artifacts.get(entry[key]["asset"]) != f"sha256:{entry[key]['sha256']}":
                raise SystemExit("Preview security receipt does not bind exact package bytes")
    sbom_payload = _require_json(dist / sbom)
    if not str(sbom_payload.get("spdxVersion", "")).startswith("SPDX-") or not sbom_payload.get("packages"):
        raise SystemExit("Preview SBOM must contain an SPDX package inventory")

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
            "release_base_url": _preview_base_url(ownership, version),
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


def verify_preview_dependencies(*, ownership: dict[str, Any], dist: Path, version: str) -> list[str]:
    from email.parser import Parser
    from zipfile import ZipFile

    root = _unique_artifact(dist, f"agentic_workspace-{version}-*.whl")
    with ZipFile(root) as wheel:
        metadata = next(name for name in wheel.namelist() if name.endswith(".dist-info/METADATA"))
        requirements = Parser().parsestr(wheel.read(metadata).decode()).get_all("Requires-Dist", [])
    expected = []
    for package in ownership["packages"]:
        if package["name"] == "agentic-workspace":
            continue
        wheel = _unique_artifact(dist, f"{package['wheel_prefix']}-{version}-*.whl")
        requirement = f"{package['name']} @ {_preview_base_url(ownership, version)}/{wheel.name}#sha256={_sha256(wheel)}"
        actual = [item for item in requirements if item.split(" ", 1)[0] == package["name"]]
        if actual != [requirement]:
            raise SystemExit(f"Preview root dependency URL/digest mismatch for {package['name']}")
        expected.append(requirement)
    return expected


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
