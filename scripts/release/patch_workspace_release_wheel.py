from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import shutil
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


DEPENDENCY_PACKAGES = {
    "agentic-memory": "agentic_memory",
    "agentic-planning": "agentic_planning",
    "agentic-verification": "agentic_verification",
}


def sha256_hex(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _record_digest(data: bytes) -> str:
    digest = hashlib.sha256(data).digest()
    return "sha256=" + base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _find_one(root: Path, pattern: str) -> Path:
    matches = sorted(root.glob(pattern))
    if len(matches) != 1:
        raise SystemExit(f"Expected exactly one match for {pattern!r} in {root}, found {len(matches)}")
    return matches[0]


def _wheel_filename_for_package(*, dist_dir: Path, wheel_prefix: str, version: str) -> str:
    return _find_one(dist_dir, f"{wheel_prefix}-{version}-*.whl").name


def _dependency_requirements(*, dist_dir: Path, version: str, release_asset_base_url: str) -> list[str]:
    base_url = release_asset_base_url.rstrip("/")
    requirements: list[str] = []
    for package_name, wheel_prefix in DEPENDENCY_PACKAGES.items():
        wheel_name = _wheel_filename_for_package(dist_dir=dist_dir, wheel_prefix=wheel_prefix, version=version)
        digest = sha256_hex(dist_dir / wheel_name)
        requirements.append(f"Requires-Dist: {package_name} @ {base_url}/{wheel_name}#sha256={digest}")
    return requirements


def _patch_metadata(metadata: str, *, requirements: list[str]) -> str:
    lines = [
        line
        for line in metadata.splitlines()
        if not any(line == f"Requires-Dist: {package_name}" for package_name in DEPENDENCY_PACKAGES)
    ]
    insert_at = 0
    for index, line in enumerate(lines):
        if line.startswith("Requires-"):
            insert_at = index + 1
    lines[insert_at:insert_at] = requirements
    return "\n".join(lines) + "\n"


def patch_workspace_wheel(*, dist_dir: Path, version: str, release_asset_base_url: str) -> Path:
    wheel_path = _find_one(dist_dir, f"agentic_workspace-{version}-*.whl")
    requirements = _dependency_requirements(
        dist_dir=dist_dir,
        version=version,
        release_asset_base_url=release_asset_base_url,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        patched_path = Path(tmpdir) / wheel_path.name
        with ZipFile(wheel_path, "r") as source, ZipFile(patched_path, "w", ZIP_DEFLATED) as target:
            records: list[tuple[str, str, str]] = []
            record_path = ""
            for item in source.infolist():
                data = source.read(item.filename)
                if item.filename.endswith(".dist-info/METADATA"):
                    data = _patch_metadata(data.decode("utf-8"), requirements=requirements).encode("utf-8")
                if item.filename.endswith(".dist-info/RECORD"):
                    record_path = item.filename
                    continue
                info = ZipInfo(item.filename, date_time=item.date_time)
                info.compress_type = item.compress_type
                info.external_attr = item.external_attr
                target.writestr(info, data)
                records.append((item.filename, _record_digest(data), str(len(data))))

            if not record_path:
                raise SystemExit(f"{wheel_path.name} has no RECORD file")
            record_buffer = io.StringIO()
            writer = csv.writer(record_buffer, lineterminator="\n")
            writer.writerows(records)
            writer.writerow((record_path, "", ""))
            target.writestr(record_path, record_buffer.getvalue().encode("utf-8"))
        shutil.move(str(patched_path), wheel_path)
    return wheel_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Patch the root AW wheel to depend on same-release GitHub wheel assets.")
    parser.add_argument("--dist-dir", default="dist")
    parser.add_argument("--version", required=True)
    parser.add_argument("--release-asset-base-url", required=True)
    args = parser.parse_args(argv)

    patched = patch_workspace_wheel(
        dist_dir=Path(args.dist_dir),
        version=args.version,
        release_asset_base_url=args.release_asset_base_url,
    )
    print(f"Patched {patched}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
