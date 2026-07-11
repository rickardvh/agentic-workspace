"""Governed promotion contract for AW-owned local diagnostic artifacts."""

from __future__ import annotations

import copy
from typing import Any, Callable

FIELD_CLASSES = {
    "local-only": ["absolute paths", "usernames", "home and checkout roots", "host process context"],
    "repo-relative-evidence": ["repo-relative paths", "command chronology", "changed-path relationships"],
    "potentially-sensitive": ["command output", "environment-derived values", "free-form notes"],
    "integrity-critical": ["timestamps", "entry ids", "origin", "work-context ids", "hashes", "parent/artifact relationships"],
}

PROFILES = {
    "reviewer-with-artifacts": {
        "audience": "trusted maintainer or reviewer",
        "omit_fields": [],
        "retain": ["chronology", "origin", "work context", "artifact relationships", "redacted command evidence"],
    },
    "external-minimal": {
        "audience": "issue, external reviewer, or broadly shared artifact",
        "omit_fields": ["python", "python_executable", "argv0_path", "path_executable", "module_path", "package_root", "parent_context"],
        "retain": ["chronology", "origin", "work context", "entry and artifact relationships", "repo-relative evidence"],
    },
}


def promote_diagnostic_payload(
    *, artifact_type: str, payload: Any, profile: str, normalize_text: Callable[[str], str]
) -> tuple[Any, dict[str, Any]]:
    """Transform a local diagnostic value and return an auditable manifest."""

    if profile not in PROFILES:
        raise ValueError(f"unsupported diagnostic disclosure profile: {profile}")
    specification = PROFILES[profile]
    omitted: list[str] = []
    normalized_count = 0

    def transform(value: Any, path: str = "$") -> Any:
        nonlocal normalized_count
        if isinstance(value, str):
            normalized = normalize_text(value)
            if normalized != value:
                normalized_count += 1
            return normalized
        if isinstance(value, list):
            return [transform(child, f"{path}[{index}]") for index, child in enumerate(value)]
        if isinstance(value, dict):
            result: dict[str, Any] = {}
            for key, child in value.items():
                child_path = f"{path}.{key}"
                if key in specification["omit_fields"]:
                    omitted.append(child_path)
                    continue
                result[key] = transform(child, child_path)
            return result
        return copy.deepcopy(value)

    promoted = transform(payload)
    manifest = {
        "kind": "agentic-workspace/diagnostic-promotion-manifest/v1",
        "artifact_type": artifact_type,
        "source_class": "raw-local-diagnostic",
        "output_class": "promoted-shareable-diagnostic",
        "disclosure_profile": profile,
        "audience": specification["audience"],
        "field_classes": FIELD_CLASSES,
        "transformations": {
            "normalized_string_count": normalized_count,
            "omitted_fields": omitted,
            "pseudonymous_substitutions": ["<target>", "<home>", "<python>", "<local-path-N>"],
        },
        "preserved_integrity": specification["retain"],
        "residual_risks": [
            "Free-form command output may contain secrets not recognizable as local paths.",
            "The promoted artifact is analytically useful but is not proof of complete source capture.",
        ],
        "omission_notes": omitted or ["No profile-defined structured fields omitted."],
        "originals_mutated": False,
        "authoritative": False,
        "rule": "Promotion is an explicit target-aware transformation; raw local diagnostics remain unchanged and locally authoritative only for debugging.",
    }
    return promoted, manifest
