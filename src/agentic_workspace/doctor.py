from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from agentic_workspace import cli, config
from agentic_workspace.contract_tooling import (
    compact_contract_manifest,
    contract_schema,
    proof_routes_manifest,
    report_contract_manifest,
)

# Absolute Path Check Constants
_POSIX_ROOT_NAMES = ("Users", "home", "tmp", "var", "etc", "opt", "srv", "mnt", "media", "root", "workspace", "workspaces")
_POSIX_PLACEHOLDER_ROOTS = (("absolute", "path"), ("path", "to"))
_TOKEN_TRAILING_PUNCTUATION = ".,:;!?)]}>\"'"

WINDOWS_ABSOLUTE_PATH = re.compile(r"(?<![A-Za-z0-9_./-])[A-Za-z]:[\\/]\S+")
POSIX_ABSOLUTE_PATH = re.compile(
    r"(?<![A-Za-z0-9_./-])(?:"
    + "|".join(
        [rf"/(?:{'|'.join(_POSIX_ROOT_NAMES)})\S*"] + [re.escape("/" + "/".join(parts)) + r"\S*" for parts in _POSIX_PLACEHOLDER_ROOTS]
    )
    + r")"
)

ALLOWED_LITERAL_EXCEPTIONS = frozenset[str]()
ALLOWED_FILE_LITERAL_EXCEPTIONS: dict[Path, frozenset[str]] = {}


@dataclass(frozen=True, slots=True)
class AbsolutePathFinding:
    path: Path
    line: int
    column: int
    value: str


def check_absolute_paths(target_root: Path) -> list[AbsolutePathFinding]:
    """Scan tracked files for absolute filesystem paths."""
    findings: list[AbsolutePathFinding] = []
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=target_root,
            capture_output=True,
            check=True,
        )
        tracked_files = [target_root / Path(raw.decode("utf-8")) for raw in result.stdout.split(b"\0") if raw]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []

    for path in tracked_files:
        if not path.is_file():
            continue
        try:
            raw = path.read_bytes()
            if b"\0" in raw:
                continue
            text = raw.decode("utf-8", errors="ignore")

            for pattern in (WINDOWS_ABSOLUTE_PATH, POSIX_ABSOLUTE_PATH):
                for match in pattern.finditer(text):
                    value = match.group(0).rstrip(_TOKEN_TRAILING_PUNCTUATION)
                    if not value:
                        continue

                    repo_relative_path = path.relative_to(target_root)
                    if value in ALLOWED_LITERAL_EXCEPTIONS or value in ALLOWED_FILE_LITERAL_EXCEPTIONS.get(repo_relative_path, frozenset()):
                        continue

                    line = text.count("\n", 0, match.start()) + 1
                    last_newline = text.rfind("\n", 0, match.start())
                    column = match.start() + 1 if last_newline == -1 else match.start() - last_newline
                    findings.append(AbsolutePathFinding(path=repo_relative_path, line=line, column=column, value=value))
        except Exception:
            continue

    return findings


def check_contract_integrity() -> list[str]:
    """Check for drift between code constants and JSON contract schemas."""
    errors: list[str] = []

    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return ["jsonschema not installed; skipping contract integrity check"]

    def _validate(instance: object, schema_name: str) -> list[str]:
        schema = contract_schema(schema_name)
        validator = Draft202012Validator(schema)
        return [error.message for error in validator.iter_errors(instance)]

    # Parity checks
    defaults_payload = cli._defaults_payload()  # type: ignore[attr-defined]
    if defaults_payload["compact_contract_profile"]["answer_shape"] != compact_contract_manifest()["answer_shape"]:
        errors.append("defaults payload answer_shape drifted from compact_contract_profile.json")
    if defaults_payload["proof_surfaces"]["default_routes"] != proof_routes_manifest()["default_routes"]:
        errors.append("defaults payload proof routes drifted from proof_routes.json")
    if cli._reporting_schema_payload() != report_contract_manifest():  # type: ignore[attr-defined]
        errors.append("reporting schema payload drifted from report_contract.json")

    workspace_config_schema = contract_schema("workspace_config.schema.json")
    if workspace_config_schema["properties"]["workspace"]["properties"]["agent_instructions_file"]["enum"] != list(
        config.SUPPORTED_AGENT_INSTRUCTIONS_FILES
    ):
        errors.append("workspace_config schema agent_instructions_file enum drifted from config constants")
    if workspace_config_schema["properties"]["workspace"]["properties"]["workflow_artifact_profile"]["enum"] != list(
        config.SUPPORTED_WORKFLOW_ARTIFACT_PROFILES
    ):
        errors.append("workspace_config schema workflow_artifact_profile enum drifted from config constants")
    if workspace_config_schema["properties"]["workspace"]["properties"]["improvement_latitude"]["enum"] != list(
        config.SUPPORTED_IMPROVEMENT_LATITUDES
    ):
        errors.append("workspace_config schema improvement_latitude enum drifted from config constants")
    if workspace_config_schema["properties"]["workspace"]["properties"]["optimization_bias"]["enum"] != list(
        config.SUPPORTED_OPTIMIZATION_BIASES
    ):
        errors.append("workspace_config schema optimization_bias enum drifted from config constants")

    local_override_schema = contract_schema("workspace_local_override.schema.json")
    delegation_target_schema = local_override_schema["properties"]["delegation_targets"]["patternProperties"]["^.+$"]
    if delegation_target_schema["properties"]["strength"]["enum"] != list(config.SUPPORTED_DELEGATION_TARGET_STRENGTHS):
        errors.append("workspace_local_override schema delegation target strengths drifted from config constants")
    if delegation_target_schema["properties"]["execution_methods"]["items"]["enum"] != list(
        config.SUPPORTED_DELEGATION_TARGET_EXECUTION_METHODS
    ):
        errors.append("workspace_local_override schema delegation target execution methods drifted from config constants")

    delegation_outcome_schema = contract_schema("delegation_outcomes.schema.json")
    record_schema = delegation_outcome_schema["properties"]["records"]["items"]
    if record_schema["properties"]["outcome"]["enum"] != list(config.SUPPORTED_DELEGATION_OUTCOMES):
        errors.append("delegation_outcomes schema outcome enums drifted from config constants")
    if record_schema["properties"]["handoff_sufficiency"]["enum"] != list(config.SUPPORTED_HANDOFF_SUFFICIENCY):
        errors.append("delegation_outcomes schema handoff_sufficiency enums drifted from config constants")
    if record_schema["properties"]["review_burden"]["enum"] != list(config.SUPPORTED_REVIEW_BURDENS):
        errors.append("delegation_outcomes schema review_burden enums drifted from config constants")

    setup_findings_schema = contract_schema("setup_findings.schema.json")
    if setup_findings_schema["properties"]["kind"]["const"] != cli.SETUP_FINDINGS_KIND:  # type: ignore[attr-defined]
        errors.append("setup_findings schema kind drifted from cli constants")
    finding_schema = setup_findings_schema["properties"]["findings"]["items"]
    if finding_schema["properties"]["class"]["enum"] != list(cli.SUPPORTED_SETUP_FINDING_CLASSES):  # type: ignore[attr-defined]
        errors.append("setup_findings schema classes drifted from cli constants")

    return errors
