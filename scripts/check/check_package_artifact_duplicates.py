from __future__ import annotations

import argparse
import json
import sys
import tarfile
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PATTERNS = (
    "dist/*.whl",
    "dist/*.zip",
    "dist/*.tar.gz",
    "packages/*/dist/*.whl",
    "packages/*/dist/*.zip",
    "packages/*/dist/*.tar.gz",
)


def _artifact_members(path: Path) -> list[str]:
    suffixes = "".join(path.suffixes).lower()
    if path.suffix.lower() in {".whl", ".zip"}:
        with ZipFile(path) as archive:
            return archive.namelist()
    if suffixes.endswith(".tar.gz"):
        with tarfile.open(path, "r:gz") as archive:
            return archive.getnames()
    return []


def duplicate_members(path: Path) -> list[str]:
    counts = Counter(_artifact_members(path))
    return sorted(member for member, count in counts.items() if count > 1)


def discover_artifacts(root: Path, patterns: list[str]) -> list[Path]:
    artifacts: list[Path] = []
    for pattern in patterns:
        artifacts.extend(path for path in root.glob(pattern) if path.is_file())
    return sorted(set(artifacts))


def check_artifacts(root: Path, artifacts: list[Path]) -> dict[str, object]:
    findings = []
    for artifact in artifacts:
        duplicates = duplicate_members(artifact)
        if duplicates:
            findings.append(
                {
                    "path": artifact.relative_to(root).as_posix() if artifact.is_relative_to(root) else artifact.as_posix(),
                    "duplicate_members": duplicates,
                    "duplicate_member_count": len(duplicates),
                }
            )
    return {
        "kind": "package-artifact-duplicate-member-check/v1",
        "artifact_count": len(artifacts),
        "finding_count": len(findings),
        "findings": findings,
        "status": "fail" if findings else "pass",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check built package artifacts for duplicate archive members.")
    parser.add_argument("artifacts", nargs="*", type=Path, help="Optional artifact paths to check directly.")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="Repository root for default artifact discovery.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    artifacts = [path.resolve() for path in args.artifacts] if args.artifacts else discover_artifacts(root, list(DEFAULT_PATTERNS))
    result = check_artifacts(root, artifacts)
    if args.format == "json":
        print(json.dumps(result, indent=2))
    elif result["status"] == "pass":
        print(f"package artifact duplicate-member check passed ({result['artifact_count']} artifacts)")
    else:
        for finding in result["findings"]:
            print(f"{finding['path']}: duplicate members: {', '.join(finding['duplicate_members'])}", file=sys.stderr)
    return 1 if result["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
