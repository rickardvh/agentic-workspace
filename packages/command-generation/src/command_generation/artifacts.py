from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CanonicalCommandArtifact:
    package_id: str
    program: str
    adapter_id: str
    command_name: str
    interface: dict[str, Any]
    operation_ref: dict[str, Any]
    runtime_binding: dict[str, Any]
    schemas: dict[str, Any]
    effect_hints: dict[str, Any]
    conformance_refs: tuple[str, ...]
    projection_boundary: dict[str, tuple[str, ...]]


def _string_tuple(values: object) -> tuple[str, ...]:
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        return ()
    return tuple(values)


def _projection_boundary(value: object) -> dict[str, tuple[str, ...]]:
    if not isinstance(value, dict):
        return {"universal": (), "target_specific": (), "runtime_owned": ()}
    return {
        "universal": _string_tuple(value.get("universal")),
        "target_specific": _string_tuple(value.get("target_specific")),
        "runtime_owned": _string_tuple(value.get("runtime_owned")),
    }


def canonical_command_artifacts(ir: dict[str, Any]) -> tuple[CanonicalCommandArtifact, ...]:
    artifacts: list[CanonicalCommandArtifact] = []
    for package in ir.get("packages", []):
        if not isinstance(package, dict):
            continue
        package_id = str(package.get("id", ""))
        program = str(package.get("program", ""))
        for command in package.get("commands", []):
            if not isinstance(command, dict) or command.get("status") != "generated":
                continue
            command_payload = command.get("command", {})
            command_name = str(command_payload.get("name", "")) if isinstance(command_payload, dict) else ""
            conformance_refs = command.get("conformance_refs", [])
            artifacts.append(
                CanonicalCommandArtifact(
                    package_id=package_id,
                    program=program,
                    adapter_id=str(command.get("adapter_id", "")),
                    command_name=command_name,
                    interface=dict(command.get("interface", {})) if isinstance(command.get("interface"), dict) else {},
                    operation_ref=dict(command.get("operation_ref", {})) if isinstance(command.get("operation_ref"), dict) else {},
                    runtime_binding=dict(command.get("runtime_binding", {})) if isinstance(command.get("runtime_binding"), dict) else {},
                    schemas=dict(command.get("schemas", {})) if isinstance(command.get("schemas"), dict) else {},
                    effect_hints=dict(command.get("effect_hints", {})) if isinstance(command.get("effect_hints"), dict) else {},
                    conformance_refs=_string_tuple(conformance_refs),
                    projection_boundary=_projection_boundary(command.get("projection_boundary")),
                )
            )
    return tuple(artifacts)
