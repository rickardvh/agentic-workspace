"""Stable manifest and inventory admission, shared by local and hosted release stages."""


def generate():
    import hashlib
    import json
    import os
    import re
    import subprocess
    import tarfile
    import tomllib
    from pathlib import Path

    ownership = json.loads(Path(".github/release-ownership.json").read_text(encoding="utf-8"))
    version = os.environ["RELEASE_TAG"].removeprefix("v")

    def sha256(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    dist = Path("dist")
    checksum_lines = []
    package_entries = []
    for package in ownership["packages"]:
        declared = tomllib.loads(Path(package["pyproject"]).read_text(encoding="utf-8"))["project"]["version"]
        if declared != version:
            raise SystemExit(f"{package['pyproject']} has version {declared}, expected {version}")
        wheel = next(dist.glob(f"{package['wheel_prefix']}-{version}-*-manylinux_2_39_x86_64.whl"), None)
        sdist = next(dist.glob(f"{package['sdist_prefix']}-{version}.tar.gz"), None)
        if wheel is None or sdist is None:
            raise SystemExit(f"Missing wheel or sdist for {package['name']} {version}")
        for artifact in (wheel, sdist):
            checksum_lines.append(f"{sha256(artifact)}  {artifact.name}")
        package_entries.append(
            {
                "name": package["name"],
                "ecosystem": "python",
                "version": version,
                "pyproject": package["pyproject"],
                "wheel": {"asset": wheel.name, "sha256": sha256(wheel)},
                "sdist": {"asset": sdist.name, "sha256": sha256(sdist)},
                "payload_schema": package["payload_schema"],
                "payload_provenance": package["payload_provenance"],
                "license_spdx": ownership["project_identity"]["license_spdx"],
            }
        )
    for package in ownership["typescript_packages"]:
        tarball = next(dist.glob(f"{package['tarball_prefix']}-{version}.tgz"), None)
        if tarball is None:
            raise SystemExit(f"Missing npm tarball for {package['name']} {version}")
        with tarfile.open(tarball, "r:gz") as archive:
            package_json = json.load(archive.extractfile("package/package.json"))
        declared = package_json["version"]
        if declared != version:
            raise SystemExit(f"{package['package_json']} has version {declared}, expected {version}")
        if package_json.get("private") is not False or package.get("release_policy") != "coordinated-public-registry":
            raise SystemExit(f"{package['package_json']} must declare coordinated public registry publication")
        tarball = next(dist.glob(f"{package['tarball_prefix']}-{version}.tgz"), None)
        if tarball is None:
            raise SystemExit(f"Missing npm tarball for {package['name']} {version}")
        checksum_lines.append(f"{sha256(tarball)}  {tarball.name}")
        package_entries.append(
            {
                "name": package["name"],
                "ecosystem": "npm",
                "version": version,
                "package_json": package["package_json"],
                "package_root": package["package_root"],
                "tarball": {"asset": tarball.name, "sha256": sha256(tarball)},
                "entrypoints": package["entrypoints"],
                "python_package": package["python_package"],
                "runtime": package["runtime"],
                "runtime_requirement": package["runtime_requirement"],
                "release_policy": package["release_policy"],
                "registry_status": package["registry_status"],
                "license_spdx": ownership["project_identity"]["license_spdx"],
            }
        )

    native_paths = list(dist.glob(f"agentic-workspace-native-{version}-x86_64-unknown-linux-gnu.zip"))
    if len(native_paths) != 1:
        raise SystemExit("Expected exactly one paired native archive")
    native_archive = {"asset": native_paths[0].name, "sha256": sha256(native_paths[0])}
    checksum_lines.append(f"{sha256(native_paths[0])}  {native_paths[0].name}")
    conformance_receipts = []
    expected_runtime_majors = ownership["semantic_conformance"]["runtime_majors"]
    for runtime_major in expected_runtime_majors:
        receipt_path = dist / f"generated-command-conformance-node{runtime_major}.json"
        if not receipt_path.is_file():
            raise SystemExit(f"Missing semantic-conformance receipt for Node {runtime_major}")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("kind") != ownership["semantic_conformance"]["receipt_kind"] or receipt.get("status") != "passed":
            raise SystemExit(f"Failed or unsupported semantic-conformance receipt: {receipt_path}")
        node_version = str(receipt.get("subject", {}).get("node_version", ""))
        runtime_match = re.fullmatch(r"v(?P<major>[1-9][0-9]*)\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?", node_version)
        if runtime_match is None or int(runtime_match.group("major")) != runtime_major:
            raise SystemExit(
                f"Semantic-conformance receipt runtime mismatch: {receipt_path} proves {node_version!r}, expected Node {runtime_major}"
            )
        receipt_assets = {item["asset"] for item in receipt["subject"]["artifacts"]}
        expected_assets = {entry["tarball"]["asset"] for entry in package_entries if entry["ecosystem"] == "npm"}
        if receipt_assets != expected_assets:
            raise SystemExit(f"Semantic-conformance receipt artifact set mismatch: {receipt_path}")
        checksum_lines.append(f"{sha256(receipt_path)}  {receipt_path.name}")
        conformance_receipts.append(
            {
                "asset": receipt_path.name,
                "receipt_id": receipt["receipt_id"],
                "registry_fingerprint": receipt["subject"]["registry_fingerprint"],
                "node_version": receipt["subject"]["node_version"],
                "artifacts": receipt["subject"]["artifacts"],
            }
        )

    manifest = {
        "publisher_workflow": "release.yml",
        "kind": "agentic-workspace/coordinated-release-manifest/v1",
        "release_model": ownership["release_model"],
        "version": version,
        "tag": os.environ["RELEASE_TAG"],
        "source_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
        "all_or_nothing": True,
        "project_identity": ownership["project_identity"],
        "distribution_identity": ownership["distribution_identity"],
        "packages": package_entries,
        "native_archive": native_archive,
        "release_ownership": {
            "path": ".github/release-ownership.json",
            "schema_version": ownership["schema_version"],
        },
        "distribution_install_readiness": ownership["distribution_identity"]["canonical_install_receipt"],
        "redistributable_package_readiness": ownership["distribution_identity"]["redistributable_receipt"],
        "semantic_conformance": {
            "required": True,
            "receipt_kind": ownership["semantic_conformance"]["receipt_kind"],
            "receipts": conformance_receipts,
        },
        "security_supply_chain": {
            "required": True,
            "readiness_receipt": "security-supply-chain-readiness.json",
            "sbom": "agentic-workspace.spdx.json",
            "provenance": "GitHub artifact attestation over dist/*",
        },
        "support_bearing_promotion": {
            "required": True,
            "receipt": "support-bearing-promotion.json",
            "source_commit": subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip(),
        },
    }
    if os.environ["RELEASE_TAG"] == "v1.0.0":
        manifest["release_candidate_promotion"] = json.loads(
            subprocess.check_output(["python", "src/tooling/release/coordinated_release.py", "verify-rc-promotion"], text=True)
        )
    import sys

    sys.path.insert(0, "src/tooling/release")
    import cargo_release

    manifest["cargo"] = cargo_release.admitted_manifest(dist, ownership, manifest["source_commit"], manifest["version"])
    for item in [manifest["cargo"]["manifest"], *manifest["cargo"]["packages"]]:
        checksum_lines.append(f"{item['sha256']}  {item['asset']}")
    manifest_path = dist / "agentic-workspace-release-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for required_security_asset in ("security-supply-chain-readiness.json", "agentic-workspace.spdx.json"):
        security_path = dist / required_security_asset
        if not security_path.is_file():
            raise SystemExit(f"Missing required security supply-chain asset: {required_security_asset}")
        checksum_lines.append(f"{sha256(security_path)}  {security_path.name}")
    for readiness_asset in (
        ownership["distribution_identity"]["canonical_install_receipt"],
        ownership["distribution_identity"]["redistributable_receipt"],
    ):
        readiness_path = dist / readiness_asset
        if not readiness_path.is_file():
            raise SystemExit(f"Missing package readiness asset: {readiness_asset}")
        checksum_lines.append(f"{sha256(readiness_path)}  {readiness_path.name}")
    promotion_path = dist / "support-bearing-promotion.json"
    promotion = json.loads(promotion_path.read_text(encoding="utf-8")) if promotion_path.is_file() else {}
    if promotion.get("status") != "passed" or promotion.get("source_commit") != manifest["source_commit"]:
        raise SystemExit("Missing or invalid exact-subject support-bearing promotion result")
    checksum_lines.append(f"{sha256(promotion_path)}  {promotion_path.name}")
    checksum_lines.append(f"{sha256(manifest_path)}  {manifest_path.name}")
    (dist / "SHA256SUMS").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")


def verify(directory="dist"):
    import hashlib
    import json
    import os
    import subprocess
    from pathlib import Path

    dist = Path(directory)
    manifest = json.loads((dist / "agentic-workspace-release-manifest.json").read_text(encoding="utf-8"))
    if manifest["tag"] != os.environ["RELEASE_TAG"]:
        raise SystemExit("Release manifest tag mismatch")
    source_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if manifest.get("source_commit") != source_commit:
        raise SystemExit("Release manifest source_commit mismatch")
    ownership = json.loads(Path(".github/release-ownership.json").read_text(encoding="utf-8"))
    expected_package_count = len(ownership["packages"]) + len(ownership["typescript_packages"])
    if len(manifest["packages"]) != expected_package_count:
        raise SystemExit("Release manifest must list every shipped package")
    checksums = {}
    for line in (dist / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, asset = line.split("  ", 1)
        checksums[asset] = digest
    required_assets = {
        "agentic-workspace-release-manifest.json",
        "security-supply-chain-readiness.json",
        "agentic-workspace.spdx.json",
        ownership["distribution_identity"]["canonical_install_receipt"],
        ownership["distribution_identity"]["redistributable_receipt"],
        "support-bearing-promotion.json",
    }
    security = manifest.get("security_supply_chain", {})
    if security.get("required") is not True:
        raise SystemExit("Release manifest is missing required security supply-chain readiness")
    for readiness_key in ("distribution_install_readiness", "redistributable_package_readiness"):
        readiness_asset = manifest.get(readiness_key, "")
        readiness_path = dist / readiness_asset
        readiness = json.loads(readiness_path.read_text(encoding="utf-8")) if readiness_path.is_file() else {}
        if readiness.get("status") != "passed" or readiness.get("version") != manifest["version"]:
            raise SystemExit(f"Release manifest has invalid {readiness_key}: {readiness_asset}")
    semantic = manifest.get("semantic_conformance", {})
    if semantic.get("required") is not True or len(semantic.get("receipts", [])) != len(
        ownership["semantic_conformance"]["runtime_majors"]
    ):
        raise SystemExit("Release manifest is missing required semantic-conformance receipts")
    required_assets.update(receipt["asset"] for receipt in semantic["receipts"])
    native = manifest["native_archive"]
    required_assets.add(native["asset"])
    if checksums.get(native["asset"]) != native["sha256"]:
        raise SystemExit("Native archive manifest/checksum mismatch")
    for item in [manifest["cargo"]["manifest"], *manifest["cargo"]["packages"]]:
        required_assets.add(item["asset"])
        if checksums.get(item["asset"]) != item["sha256"]:
            raise SystemExit("Cargo manifest/checksum mismatch")
    for package in manifest["packages"]:
        if package.get("ecosystem") == "npm":
            required_assets.add(package["tarball"]["asset"])
        else:
            required_assets.add(package["wheel"]["asset"])
            required_assets.add(package["sdist"]["asset"])
    required_assets.add(manifest["platform_release"]["asset"])
    required_assets.update(item["asset"] for item in manifest["platform_consumers"])
    required_assets.update(item["asset"] for item in manifest["native_archives"])
    for package in manifest["packages"]:
        required_assets.update(item["asset"] for item in package.get("wheels", []))
    missing = sorted(required_assets - set(checksums))
    if missing:
        raise SystemExit(f"Missing checksums for release assets: {missing}")
    for asset in required_assets:
        digest = hashlib.sha256((dist / asset).read_bytes()).hexdigest()
        if checksums[asset] != digest:
            raise SystemExit(f"Checksum mismatch for {asset}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("generate", "verify"))
    args = parser.parse_args()
    {"generate": generate, "verify": verify}[args.stage]()
