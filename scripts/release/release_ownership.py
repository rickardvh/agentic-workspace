"""Shared changed-path classification from the release ownership authority."""

from __future__ import annotations

from typing import Any, Iterable


def _matches(path: str, pattern: str) -> bool:
    normalized = path.replace("\\", "/")
    candidate = pattern.replace("\\", "/")
    return normalized == candidate or normalized.startswith(candidate)


def classify_changed_paths(changed_paths: Iterable[str], ownership: dict[str, Any]) -> dict[str, Any]:
    """Classify paths by semantic release ownership, preserving strongest-change wins."""

    paths = [path.replace("\\", "/") for path in changed_paths]
    watched = [str(item) for item in ownership.get("package_affecting_paths", [])]
    non_semver_patterns = [str(item) for item in ownership.get("non_semver_paths", [])]
    metadata_entries = ownership.get("non_semver_generated_metadata", [])
    exempt_paths = {
        str(item["path"]).replace("\\", "/")
        for item in metadata_entries
        if isinstance(item, dict) and str(item.get("path", "")).strip()
    }
    non_semver_paths = [
        path for path in paths if any(_matches(path, pattern) for pattern in non_semver_patterns)
    ]
    package_paths = [
        path
        for path in paths
        if path not in exempt_paths
        and path not in non_semver_paths
        and any(_matches(path, pattern) for pattern in watched)
    ]
    integrity_metadata_paths = [path for path in paths if path in exempt_paths]
    return {
        "kind": "agentic-workspace/release-path-classification/v1",
        "package_affecting": bool(package_paths),
        "package_affecting_paths": package_paths,
        "non_semver_paths": non_semver_paths,
        "integrity_metadata_paths": integrity_metadata_paths,
        "unclassified_paths": [
            path
            for path in paths
            if path not in package_paths
            and path not in non_semver_paths
            and path not in integrity_metadata_paths
        ],
    }
