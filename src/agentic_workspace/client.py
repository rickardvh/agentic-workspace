from __future__ import annotations

import hashlib
import json
import shlex
import subprocess
import tomllib
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any, Mapping, Sequence, cast

from jsonschema import Draft202012Validator

FAILURE_KINDS = {"absent", "disabled", "incompatible", "unsupported", "rejected", "failed", "malformed", "invocation-unavailable"}


@dataclass
class AWClientError(RuntimeError):
    kind: str
    message: str
    details: Mapping[str, Any]

    def __str__(self) -> str:
        return f"{self.kind}: {self.message}"


def _resource(path: str, package_name: str = "agentic-workspace"):
    package_modules = {
        "agentic-workspace": "agentic_workspace._generated_cli_package_impl",
        "agentic-memory": "repo_memory_bootstrap._generated_cli_package_impl",
        "agentic-planning": "repo_planning_bootstrap._generated_cli_package_impl",
        "agentic-verification": "repo_verification_bootstrap._generated_cli_package_impl",
    }
    try:
        resource = files(package_modules[package_name]).joinpath(path)
        if resource.is_file():
            return resource
    except ModuleNotFoundError:
        pass
    target = package_name.removeprefix("agentic-")
    return Path(__file__).resolve().parents[2] / f"generated/{target}/python" / path


def external_consumer_profile() -> dict[str, Any]:
    resource = _resource("external_consumer_profile.json")
    return json.loads(resource.read_text(encoding="utf-8"))


def external_contract_bundle() -> dict[str, Any]:
    return json.loads(_resource("external_contract_bundle.json").read_text(encoding="utf-8"))


def operation_compatibility_fingerprint(contract: Mapping[str, Any]) -> str:
    def normalize(value: Any) -> Any:
        if isinstance(value, list):
            return [normalize(item) for item in value]
        if not isinstance(value, dict):
            return value
        return {
            key: normalize(item)
            for key, item in value.items()
            if key not in {"description", "title", "$id", "$comment", "examples", "default"}
        }

    normalized = {key: contract.get(key) for key in ("schema_version", "id", "classification", "inputs", "output", "effects", "guards")}
    bundle = external_contract_bundle()
    operation = bundle["operations"].get(str(contract.get("id")), {})
    schemas = operation.get("compatibility_surface", {}).get("schemas", {})
    encoded = json.dumps({"contract": normalized, "schemas": normalize(schemas)}, sort_keys=True, separators=(",", ":")).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _surface_compatible(required: Any, available: Any, *, role: str = "contract", keyword: str = "") -> bool:
    if isinstance(required, dict):
        return isinstance(available, dict) and all(
            key in available and _surface_compatible(value, available[key], role=role, keyword=key) for key, value in required.items()
        )
    if isinstance(required, list):
        if not isinstance(available, list):
            return False
        if keyword == "required":
            return all(item in required for item in available) if role == "input" else all(item in available for item in required)
        if keyword in {"enum", "type"}:
            return all(item in available for item in required) if role == "input" else all(item in required for item in available)
        return required == available
    return required == available


def compatibility_surface_satisfied(required: Mapping[str, Any], available: Mapping[str, Any]) -> bool:
    old_contract = required.get("contract", {})
    new_contract = available.get("contract", {})
    if not isinstance(old_contract, Mapping) or not isinstance(new_contract, Mapping):
        return False
    old_inputs = {str(item.get("name")): item for item in old_contract.get("inputs", []) if isinstance(item, Mapping)}
    new_inputs = {str(item.get("name")): item for item in new_contract.get("inputs", []) if isinstance(item, Mapping)}
    if any(name not in new_inputs for name in old_inputs):
        return False
    for name, old_input in old_inputs.items():
        new_input = new_inputs[name]
        if not old_input.get("required", False) and new_input.get("required", False):
            return False
        if not _surface_compatible(
            {key: value for key, value in old_input.items() if key != "required"},
            {key: value for key, value in new_input.items() if key != "required"},
            role="input",
        ):
            return False
    if any(item.get("required", False) for name, item in new_inputs.items() if name not in old_inputs):
        return False
    old_contract_without_inputs = {key: value for key, value in old_contract.items() if key != "inputs"}
    new_contract_without_inputs = {key: value for key, value in new_contract.items() if key != "inputs"}
    return _surface_compatible(old_contract_without_inputs, new_contract_without_inputs) and all(
        _surface_compatible(schemas, available.get("schemas", {}).get(role), role=role)
        for role, schemas in required.get("schemas", {}).items()
    )


def negotiate_requirements(
    requirements: Mapping[str, str | Mapping[str, Any] | None], *, allow_runtime_backed: bool = False
) -> dict[str, Any]:
    bundle = external_contract_bundle()
    results = []
    for operation_id, requirement in requirements.items():
        operation = bundle["operations"].get(operation_id)
        if operation is None:
            results.append({"operation": operation_id, "status": "missing", "reason": "operation is not packaged"})
            continue
        support = operation["external_consumption"]["status"]
        if support == "runtime-backed" and not allow_runtime_backed:
            results.append({"operation": operation_id, "status": "runtime-backed", "reason": "explicit runtime-backed opt-in required"})
        elif support not in {"supported", "runtime-backed"}:
            results.append({"operation": operation_id, "status": "unsupported", "reason": f"support status is {support}"})
        elif isinstance(requirement, Mapping):
            required_surface = requirement.get("compatibility_surface")
            available_surface = operation.get("compatibility_surface")
            if (
                not isinstance(required_surface, Mapping)
                or not isinstance(available_surface, Mapping)
                or not compatibility_surface_satisfied(
                    cast(Mapping[str, Any], required_surface), cast(Mapping[str, Any], available_surface)
                )
            ):
                results.append(
                    {"operation": operation_id, "status": "incompatible", "reason": "operation compatibility surface is breaking"}
                )
                continue
            results.append({"operation": operation_id, "status": "compatible", "reason": "requirement satisfied"})
        elif isinstance(requirement, str) and requirement != operation["compatibility_fingerprint"]:
            results.append({"operation": operation_id, "status": "incompatible", "reason": "operation fingerprint mismatch"})
        else:
            results.append({"operation": operation_id, "status": "compatible", "reason": "requirement satisfied"})
    return {"compatible": all(item["status"] == "compatible" for item in results), "requirements": results}


def detect_workspace(target: str | Path) -> dict[str, Any]:
    root = Path(target).resolve()
    config = root / ".agentic-workspace/config.toml"
    if not config.is_file():
        return {"status": "absent", "target": root.as_posix()}
    payload = tomllib.loads(config.read_text(encoding="utf-8"))
    workspace = payload.get("workspace", {})
    if workspace.get("enabled") is False:
        return {"status": "disabled", "target": root.as_posix()}
    return {"status": "enabled", "target": root.as_posix()}


def resolve_invocation(target: str | Path, override: Sequence[str] | None = None) -> list[str]:
    if override:
        return list(override)
    root = Path(target).resolve()
    for name in ("config.local.toml", "config.toml"):
        path = root / ".agentic-workspace" / name
        if not path.is_file():
            continue
        workspace = tomllib.loads(path.read_text(encoding="utf-8")).get("workspace", {})
        command = workspace.get("cli_invoke")
        if isinstance(command, str) and command.strip():
            return shlex.split(command, posix=False)
    return ["agentic-workspace"]


def require_operations(operation_ids: Sequence[str], *, allow_runtime_backed: bool = False) -> None:
    entries = {entry["id"]: entry for entry in external_consumer_profile()["operations"]}
    allowed = {"supported"} | ({"runtime-backed"} if allow_runtime_backed else set())
    failures = []
    for operation_id in operation_ids:
        status = entries.get(operation_id, {}).get("external_consumption", {}).get("status", "unknown")
        if status not in allowed:
            failures.append({"operation": operation_id, "status": status})
    if failures:
        raise AWClientError("incompatible", "operation requirements are not satisfied", {"requirements": failures})


def _operation_contract(entry: Mapping[str, Any]) -> dict[str, Any]:
    resource_ref = entry["operation_resources"]["python"]
    resource = _resource(resource_ref["path"], resource_ref["package"])
    return json.loads(resource.read_text(encoding="utf-8"))


def _validate_schema(entry: Mapping[str, Any], schema_name: str, value: Any, *, phase: str) -> None:
    resource_ref = entry["operation_resources"]["python"]
    schema_path = f"_contracts/{schema_name}"
    schema = json.loads(_resource(schema_path, resource_ref["package"]).read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda error: list(error.path))
    if errors:
        raise AWClientError(
            "malformed",
            f"operation {phase} failed schema validation",
            {"schema": schema_name, "errors": [error.message for error in errors]},
        )


def _validate_failure(entry: Mapping[str, Any], value: Any) -> None:
    resource_ref = entry["operation_resources"]["python"]
    schema = json.loads(_resource("_contracts/operation_failure.schema.json", resource_ref["package"]).read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda error: list(error.path))
    if errors:
        raise AWClientError("malformed", "operation failure failed schema validation", {"errors": [error.message for error in errors]})


def _adapter_commands(package_name: str) -> list[dict[str, Any]]:
    try:
        payload = json.loads(_resource("adapter_commands.json", package_name).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    return [item for item in payload if isinstance(item, dict)] if isinstance(payload, list) else []


def _command_interface(contract: Mapping[str, Any], *, package_name: str) -> Mapping[str, Any]:
    surface = contract.get("command_surface", {})
    if not isinstance(surface, Mapping):
        return {}
    command_tokens = str(surface.get("command", "")).split()
    subcommand = str(surface.get("subcommand", "")).strip()
    if subcommand and (not command_tokens or command_tokens[-1] != subcommand):
        command_tokens.append(subcommand)
    if not command_tokens:
        return {}
    current: Mapping[str, Any] | None = None
    choices = [item.get("interface", {}) for item in _adapter_commands(package_name)]
    for token in command_tokens:
        current = next(
            (item for item in choices if isinstance(item, Mapping) and str(item.get("name", "")) == token),
            None,
        )
        if current is None:
            return {}
        choices = [item for item in current.get("subcommands", []) if isinstance(item, Mapping)]
    return cast(Mapping[str, Any], current)


def _command_options_by_input_name(contract: Mapping[str, Any], *, package_name: str) -> dict[str, Mapping[str, Any]]:
    interface = _command_interface(contract, package_name=package_name)
    options = interface.get("options", []) if isinstance(interface, Mapping) else []
    return {str(option.get("name")): option for option in options if isinstance(option, Mapping) and str(option.get("name", "")).strip()}


def _option_flag(name: str, option_spec: Mapping[str, Any] | None) -> str:
    flags = option_spec.get("flags", []) if isinstance(option_spec, Mapping) else []
    if isinstance(flags, list):
        long_flags = [str(flag) for flag in flags if isinstance(flag, str) and flag.startswith("--")]
        if long_flags:
            return long_flags[0]
    return f"--{name.replace('_', '-')}"


def _argv(contract: Mapping[str, Any], values: Mapping[str, Any], target: Path, *, package_name: str = "agentic-workspace") -> list[str]:
    surface = contract.get("command_surface", {})
    command = str(surface.get("command", "")).split()
    subcommand = str(surface.get("subcommand", "")).strip()
    if subcommand and (not command or command[-1] != subcommand):
        command.append(subcommand)
    program = str(surface.get("program", "agentic-workspace"))
    if program.startswith("agentic-") and program != "agentic-workspace":
        command.insert(0, program.removeprefix("agentic-"))
    if not command:
        raise AWClientError("malformed", "operation contract has no command surface", {"operation": contract.get("id")})
    declared = {str(item.get("name")): item for item in contract.get("inputs", []) if isinstance(item, dict)}
    unknown = sorted(set(values) - set(declared))
    if unknown:
        raise AWClientError("malformed", "operation input contains unknown fields", {"fields": unknown})
    missing = sorted(name for name, item in declared.items() if item.get("required") and name not in values)
    if missing:
        raise AWClientError("malformed", "operation input is missing required fields", {"fields": missing})
    options_by_name = _command_options_by_input_name(contract, package_name=package_name)
    argv = list(command)
    for name, value in values.items():
        if name == "target":
            continue
        option_spec = options_by_name.get(name)
        flag = _option_flag(name, option_spec)
        if isinstance(value, bool):
            if value:
                argv.append(flag)
        elif isinstance(value, list):
            if isinstance(option_spec, Mapping) and option_spec.get("action") == "append":
                for item in value:
                    argv.extend([flag, str(item)])
            else:
                argv.extend([flag, ",".join(str(item) for item in value)])
        else:
            argv.extend([flag, str(value)])
    if "target" in declared:
        target_spec = options_by_name.get("target")
        argv.extend([_option_flag("target", target_spec), str(target)])
    if "format" in declared:
        format_spec = options_by_name.get("format")
        argv.extend([_option_flag("format", format_spec), "json"])
    return argv


def invoke_operation(
    operation_id: str,
    values: Mapping[str, Any],
    *,
    target: str | Path,
    invocation: Sequence[str] | None = None,
    allow_runtime_backed: bool = False,
) -> dict[str, Any]:
    state = detect_workspace(target)
    if state["status"] != "enabled":
        raise AWClientError(state["status"], "workspace is not available", state)
    require_operations([operation_id], allow_runtime_backed=allow_runtime_backed)
    entry = next(item for item in external_consumer_profile()["operations"] if item["id"] == operation_id)
    for schema_name in entry["schemas"]["input"]:
        _validate_schema(entry, schema_name, dict(values), phase="input")
    resource_ref = entry["operation_resources"]["python"]
    argv = _argv(_operation_contract(entry), values, Path(target).resolve(), package_name=str(resource_ref["package"]))
    command = [*resolve_invocation(target, invocation), *argv]
    try:
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
    except OSError as exc:
        raise AWClientError("invocation-unavailable", str(exc), {"command": command}) from exc
    stream = completed.stdout or completed.stderr
    try:
        payload = json.loads(stream)
    except json.JSONDecodeError as exc:
        raise AWClientError("malformed", "AW returned non-JSON output", {"exit_code": completed.returncode}) from exc
    if completed.returncode:
        _validate_failure(entry, payload)
        kind = str(payload.get("status", "failed")) if isinstance(payload, dict) else "failed"
        if kind not in FAILURE_KINDS:
            kind = "rejected" if completed.returncode == 2 else "failed"
        raise AWClientError(kind, "AW operation failed", {"exit_code": completed.returncode, "error": payload})
    if not isinstance(payload, dict):
        raise AWClientError("malformed", "AW result envelope must be an object", {"result": payload})
    for schema_name in entry["schemas"]["output"]:
        _validate_schema(entry, schema_name, payload, phase="result")
    return payload
