"""Governed promotion contract for AW-owned local diagnostic artifacts."""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Callable

FIELD_CLASSES = {
    "local-only": ["absolute paths", "usernames", "home and checkout roots", "host process context"],
    "repo-relative-evidence": ["repo-relative paths", "command chronology", "changed-path relationships"],
    "potentially-sensitive": ["command output", "environment-derived values", "free-form notes"],
    "integrity-critical": ["timestamps", "entry ids", "origin", "work-context ids", "hashes", "parent/artifact relationships"],
}

FIELD_RULES = {
    "integrity-critical": {
        "kind",
        "id",
        "entry_id",
        "created_at",
        "recorded_at",
        "timestamp",
        "origin",
        "work_context_id",
        "output_digest",
        "artifact",
        "relationships",
    },
    "repo-relative-evidence": {
        "changed_paths",
        "path",
        "root",
        "source_log_path",
        "failed_command",
        "command_count",
        "occurrences",
        "exit_status",
        "exit_class",
        "packet_kinds",
    },
    "opaque": {"stdout", "stderr", "output", "body", "message", "note", "notes", "command", "argv"},
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
    substitutions: set[str] = set()

    def field_class(key: str) -> str:
        for class_name, keys in FIELD_RULES.items():
            if key in keys:
                return class_name
        return "unknown"

    def transform(value: Any, path: str = "$") -> Any:
        nonlocal normalized_count
        if isinstance(value, str):
            if profile == "external-minimal" and path == "$":
                omitted.append(path)
                return f"[opaque content omitted; sha256:{hashlib.sha256(value.encode()).hexdigest()[:12]}]"
            normalized = normalize_text(value)
            if normalized != value:
                normalized_count += 1
                substitutions.update(token for token in ("<target>", "<home>", "<python>") if token in normalized and token not in value)
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
                classification = field_class(str(key))
                if profile == "external-minimal" and classification in {"opaque", "unknown"} and isinstance(child, str):
                    omitted.append(child_path)
                    result[key] = f"[opaque field omitted; sha256:{hashlib.sha256(child.encode()).hexdigest()[:12]}]"
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
        "field_rules": {key: sorted(value) for key, value in FIELD_RULES.items()},
        "transformations": {
            "normalized_string_count": normalized_count,
            "omitted_fields": omitted,
            "pseudonymous_substitutions": sorted(substitutions),
        },
        "preserved_integrity": specification["retain"],
        "residual_risks": ["The promoted artifact is analytically useful but is not proof of complete source capture."],
        "omission_notes": omitted or ["No profile-defined structured fields omitted."],
        "originals_mutated": False,
        "authoritative": False,
        "rule": "Promotion is an explicit target-aware transformation; raw local diagnostics remain unchanged and locally authoritative only for debugging.",
    }
    return promoted, manifest
