from __future__ import annotations

import argparse
import hashlib
import json
import re
import tarfile
import tomllib
from pathlib import Path
from typing import Any
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
OWNERSHIP_PATH = Path(".github/release-ownership.json")
FORBIDDEN_DISTRIBUTIONS = {"agentic-memory", "agentic-planning"}
PUBLIC_REHEARSAL_PATH = Path("docs/maintainer/public-install-rehearsal-v0.40.1.json")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain an object")
    return payload


def _load_pyproject(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _dependency_name(requirement: str) -> str:
    return requirement.split("@", 1)[0].split(";", 1)[0].strip().split()[0]


def public_install_rehearsal_errors(root: Path = ROOT) -> list[str]:
    path = root / PUBLIC_REHEARSAL_PATH
    if not path.is_file():
        return []
    receipt = _load_json(path)
    controlled = receipt.get("resolution", {}).get("controlled_distributions", [])
    names = {str(item.get("name")) for item in controlled if isinstance(item, dict)}
    expected = {
        "agentic-workspace",
        "agentic-workspace-memory",
        "agentic-workspace-planning",
        "agentic-workspace-verification",
    }
    second_process = receipt.get("second_process", {})
    errors: list[str] = []
    if receipt.get("kind") != "agentic-workspace/public-install-rehearsal/v1" or receipt.get("status") != "passed":
        errors.append(f"{PUBLIC_REHEARSAL_PATH.as_posix()} has the wrong kind or status")
    if names != expected or any(item.get("version") != "0.40.1" for item in controlled if isinstance(item, dict)):
        errors.append(f"{PUBLIC_REHEARSAL_PATH.as_posix()} does not retain the exact four controlled 0.40.1 distributions")
    if receipt.get("resolution", {}).get("forbidden_identity_match_count") != 0:
        errors.append(f"{PUBLIC_REHEARSAL_PATH.as_posix()} does not prove forbidden distribution identities absent")
    if (
        second_process.get("bootstrap_process_exited_before_invocation") is not True
        or second_process.get("exit_code") != 0
        or second_process.get("result_kind") != "startup-context/v1"
    ):
        errors.append(f"{PUBLIC_REHEARSAL_PATH.as_posix()} does not retain a successful separate-process startup result")
    if second_process.get("durable_machine_local_path_match_count") != 0 or re.search(r"[A-Za-z]:\\\\", json.dumps(receipt)):
        errors.append(f"{PUBLIC_REHEARSAL_PATH.as_posix()} retains a machine-local durable path")
    return errors


def source_identity_errors(root: Path = ROOT) -> list[str]:
    ownership = _load_json(root / OWNERSHIP_PATH)
    identity = ownership.get("project_identity", {})
    distribution = ownership.get("distribution_identity", {})
    errors: list[str] = []
    license_path = root / str(identity.get("license_file", ""))
    if not license_path.is_file():
        errors.append("canonical LICENSE is missing")
        license_text = ""
    else:
        license_text = license_path.read_text(encoding="utf-8")
        if not license_text.startswith("MIT License\n") or "Rickard von Haugwitz" not in license_text:
            errors.append("canonical LICENSE is not the owner-approved MIT grant")

    expected_names = {str(item["name"]) for item in ownership.get("packages", [])}
    for package in ownership.get("packages", []):
        pyproject_path = root / str(package["pyproject"])
        project = _load_pyproject(pyproject_path).get("project", {})
        prefix = pyproject_path.relative_to(root).as_posix()
        expected = {
            "name": package["name"],
            "license": identity.get("license_spdx"),
            "authors": [{"name": identity.get("author")}],
            "maintainers": [{"name": identity.get("maintainer")}],
        }
        for field, value in expected.items():
            if project.get(field) != value:
                errors.append(f"{prefix} project.{field} does not match canonical identity")
        if project.get("license-files") != ["LICENSE"]:
            errors.append(f"{prefix} project.license-files must contain LICENSE")
        urls = project.get("urls", {})
        for field, identity_field in (
            ("Homepage", "homepage"),
            ("Repository", "repository"),
            ("Issues", "issues"),
            ("Support", "support"),
        ):
            if urls.get(field) != identity.get(identity_field):
                errors.append(f"{prefix} project.urls.{field} does not match canonical identity")
        if identity.get("maturity_classifier") not in project.get("classifiers", []):
            errors.append(f"{prefix} has contradictory or missing maturity classifier")
        local_license = pyproject_path.parent / "LICENSE"
        if not local_license.is_file() or local_license.read_text(encoding="utf-8") != license_text:
            errors.append(f"{prefix} does not project the canonical LICENSE")

    root_project = _load_pyproject(root / "pyproject.toml")["project"]
    dependency_names = {_dependency_name(str(item)) for item in root_project.get("dependencies", [])}
    if dependency_names & FORBIDDEN_DISTRIBUTIONS:
        errors.append("root dependencies can resolve unrelated agentic-memory or agentic-planning projects")
    coordinated_modules = expected_names - {str(distribution.get("canonical_root_distribution", ""))}
    if not coordinated_modules.issubset(dependency_names):
        errors.append("root dependencies do not contain every coordinated module identity")
    if distribution.get("strategy") != "exact-github-release-assets" or distribution.get("registry_resolution_supported") is not False:
        errors.append("supported distribution strategy must be exact GitHub release assets, not registry resolution")
    for relative in (
        "README.md",
        "docs/agentic-workspace-install.md",
        "packages/memory/README.md",
        "packages/planning/README.md",
    ):
        documentation = (root / relative).read_text(encoding="utf-8")
        if "git+https://github.com/rickardvh/agentic-workspace@master" in documentation:
            errors.append(f"{relative} recommends mutable master as an install identity")
        if "distribution-install-readiness.json" not in documentation:
            errors.append(f"{relative} does not route support-bearing installs through the canonical receipt")

    for package in ownership.get("typescript_packages", []):
        package_path = root / str(package["package_json"])
        payload = _load_json(package_path)
        prefix = package_path.relative_to(root).as_posix()
        expected = {
            "name": package["name"],
            "private": True,
            "license": identity.get("license_spdx"),
            "author": identity.get("author"),
            "homepage": identity.get("homepage"),
            "repository": {"type": "git", "url": identity.get("repository")},
            "bugs": {"url": identity.get("issues")},
        }
        for field, value in expected.items():
            if payload.get(field) != value:
                errors.append(f"{prefix} {field} does not match canonical identity")
        if (
            "publishConfig" in payload
            or package.get("release_policy") != "release-asset-only"
            or package.get("registry_status") != "unpublished"
        ):
            errors.append(f"{prefix} must be explicitly unpublished and release-asset-only")
        if "LICENSE" not in payload.get("files", []):
            errors.append(f"{prefix} does not package LICENSE")
        generated_license = package_path.parent / "LICENSE"
        if not generated_license.is_file() or generated_license.read_text(encoding="utf-8") != license_text:
            errors.append(f"{prefix} does not carry the canonical LICENSE")
    errors.extend(public_install_rehearsal_errors(root))
    return errors


def _find_one(dist: Path, pattern: str) -> Path:
    matches = sorted(dist.glob(pattern))
    if len(matches) != 1:
        raise ValueError(f"expected one {pattern} artifact, found {len(matches)}")
    return matches[0]


def artifact_identity_errors(root: Path, dist: Path, *, require_exact_urls: bool = False) -> list[str]:
    ownership = _load_json(root / OWNERSHIP_PATH)
    identity = ownership["project_identity"]
    license_text = (root / identity["license_file"]).read_text(encoding="utf-8").encode()
    version = _load_pyproject(root / "pyproject.toml")["project"]["version"]
    errors: list[str] = []
    for package in ownership["packages"]:
        try:
            wheel = _find_one(dist, f"{package['wheel_prefix']}-{version}-*.whl")
            sdist = _find_one(dist, f"{package['sdist_prefix']}-{version}.tar.gz")
        except ValueError as exc:
            errors.append(str(exc))
            continue
        with ZipFile(wheel) as archive:
            names = archive.namelist()
            metadata_name = next((name for name in names if name.endswith(".dist-info/METADATA")), "")
            license_name = next((name for name in names if ".dist-info/licenses/" in name and name.endswith("LICENSE")), "")
            metadata = archive.read(metadata_name).decode() if metadata_name else ""
            if f"Name: {package['name']}" not in metadata or "License-Expression: MIT" not in metadata:
                errors.append(f"{wheel.name} has conflicting name or license metadata")
            for expected_line in (
                f"Author: {identity['author']}",
                f"Maintainer: {identity['maintainer']}",
                f"Project-URL: Homepage, {identity['homepage']}",
                f"Project-URL: Repository, {identity['repository']}",
                f"Project-URL: Issues, {identity['issues']}",
                f"Project-URL: Support, {identity['support']}",
            ):
                if expected_line not in metadata:
                    errors.append(f"{wheel.name} is missing {expected_line}")
            if not license_name or archive.read(license_name) != license_text:
                errors.append(f"{wheel.name} does not contain canonical LICENSE text")
            if package["name"] == ownership["distribution_identity"]["canonical_root_distribution"]:
                if any(f"Requires-Dist: {name}" in metadata for name in FORBIDDEN_DISTRIBUTIONS):
                    errors.append(f"{wheel.name} contains ambiguous module dependencies")
                if require_exact_urls:
                    for dependency in ownership["packages"][1:]:
                        marker = f"Requires-Dist: {dependency['name']} @ https://github.com/"
                        if marker not in metadata or "#sha256=" not in metadata.split(marker, 1)[1].splitlines()[0]:
                            errors.append(f"{wheel.name} lacks an exact hashed URL for {dependency['name']}")
        with tarfile.open(sdist, "r:gz") as archive:
            member = next((item for item in archive.getmembers() if item.name.endswith("/LICENSE")), None)
            data = archive.extractfile(member).read() if member and archive.extractfile(member) else b""
            if data != license_text:
                errors.append(f"{sdist.name} does not contain canonical LICENSE text")

    for package in ownership["typescript_packages"]:
        try:
            tarball = _find_one(dist, f"{package['tarball_prefix']}-{version}.tgz")
        except ValueError as exc:
            errors.append(str(exc))
            continue
        with tarfile.open(tarball, "r:gz") as archive:
            package_json_member = archive.getmember("package/package.json")
            license_member = archive.getmember("package/LICENSE")
            package_json_file = archive.extractfile(package_json_member)
            license_file = archive.extractfile(license_member)
            payload = json.loads(package_json_file.read()) if package_json_file else {}
            data = license_file.read() if license_file else b""
            if (
                payload.get("name") != package["name"]
                or payload.get("license") != identity["license_spdx"]
                or payload.get("private") is not True
            ):
                errors.append(f"{tarball.name} has conflicting package identity")
            if data != license_text:
                errors.append(f"{tarball.name} does not contain canonical LICENSE text")
    return errors


def write_readiness_receipts(root: Path, dist: Path) -> list[Path]:
    ownership = _load_json(root / OWNERSHIP_PATH)
    distribution = ownership["distribution_identity"]
    version = _load_pyproject(root / "pyproject.toml")["project"]["version"]
    root_package = ownership["packages"][0]
    wheel = _find_one(dist, f"{root_package['wheel_prefix']}-{version}-*.whl")
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    identity_digest = hashlib.sha256((root / OWNERSHIP_PATH).read_bytes()).hexdigest()
    base_url = distribution["release_base_url_template"].format(version=version)
    requirement = f"agentic-workspace @ {base_url}/{wheel.name}#sha256={digest}"
    install = {
        "kind": "agentic-workspace/distribution-install-readiness/v1",
        "status": "passed",
        "version": version,
        "artifact": {"name": wheel.name, "sha256": digest, "url": f"{base_url}/{wheel.name}"},
        "install": {"requirement": requirement, "command": f'uv tool install "{requirement}"'},
        "second_process_command": 'agentic-workspace start --target . --task "<task>" --format json',
        "registry_resolution_used": False,
        "identity": {"source": OWNERSHIP_PATH.as_posix(), "sha256": identity_digest},
    }
    release_artifacts: list[Path] = []
    for package in ownership["packages"]:
        release_artifacts.extend(
            (
                _find_one(dist, f"{package['wheel_prefix']}-{version}-*.whl"),
                _find_one(dist, f"{package['sdist_prefix']}-{version}.tar.gz"),
            )
        )
    for package in ownership["typescript_packages"]:
        release_artifacts.append(_find_one(dist, f"{package['tarball_prefix']}-{version}.tgz"))
    artifacts = [
        {"name": artifact.name, "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest()}
        for artifact in sorted(release_artifacts, key=lambda item: item.name)
    ]
    redistributable = {
        "kind": "agentic-workspace/redistributable-package-readiness/v1",
        "status": "passed",
        "version": version,
        "license_spdx": ownership["project_identity"]["license_spdx"],
        "identity_source": OWNERSHIP_PATH.as_posix(),
        "identity_sha256": identity_digest,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }
    paths = [dist / distribution["canonical_install_receipt"], dist / distribution["redistributable_receipt"]]
    for path, payload in zip(paths, (install, redistributable), strict=True):
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return paths


def redistributable_receipt_errors(root: Path, dist: Path) -> list[str]:
    ownership = _load_json(root / OWNERSHIP_PATH)
    receipt_path = dist / ownership["distribution_identity"]["redistributable_receipt"]
    if not receipt_path.is_file():
        return [f"{receipt_path.name} is missing"]
    receipt = _load_json(receipt_path)
    version = _load_pyproject(root / "pyproject.toml")["project"]["version"]
    expected: list[dict[str, str]] = []
    try:
        for package in ownership["packages"]:
            for artifact in (
                _find_one(dist, f"{package['wheel_prefix']}-{version}-*.whl"),
                _find_one(dist, f"{package['sdist_prefix']}-{version}.tar.gz"),
            ):
                expected.append({"name": artifact.name, "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest()})
        for package in ownership["typescript_packages"]:
            artifact = _find_one(dist, f"{package['tarball_prefix']}-{version}.tgz")
            expected.append({"name": artifact.name, "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest()})
    except ValueError as exc:
        return [str(exc)]
    expected.sort(key=lambda item: item["name"])
    errors: list[str] = []
    if receipt.get("artifacts") != expected:
        errors.append(f"{receipt_path.name} does not bind the exact artifact names and sha256 digests")
    if receipt.get("artifact_count") != len(expected):
        errors.append(f"{receipt_path.name} artifact_count does not match its exact artifact set")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check coordinated package and redistribution identity.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument("--require-exact-urls", action="store_true")
    parser.add_argument("--write-receipts", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    errors = source_identity_errors(root)
    receipts: list[Path] = []
    if args.artifact_dir:
        dist = args.artifact_dir.resolve()
        errors.extend(artifact_identity_errors(root, dist, require_exact_urls=args.require_exact_urls))
        if not errors and args.write_receipts:
            receipts = write_readiness_receipts(root, dist)
            errors.extend(redistributable_receipt_errors(root, dist))
    payload = {
        "kind": "agentic-workspace/package-identity-readiness/v1",
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "receipts": [path.name for path in receipts],
    }
    print(json.dumps(payload, indent=2) if args.format == "json" else ("[ok] package identity" if not errors else "\n".join(errors)))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
