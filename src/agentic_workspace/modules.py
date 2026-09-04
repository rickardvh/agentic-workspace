from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from importlib import metadata
from typing import Any

from .generated_semantics import IR
from .operations import Operation, OperationDispatcher

MODULE_ENTRY_POINT_GROUP = "agentic_workspace.modules"


@dataclass(frozen=True)
class Module:
    name: str
    contribute: Callable[[Mapping[str, Any]], Mapping[str, Any] | None]
    operations: tuple[Operation, ...] = ()
    api_version: str = "1.0"
    required_capabilities: tuple[str, ...] = ()
    owns: tuple[str, ...] = ()
    claims: tuple[str, ...] = ()
    resources: tuple[Mapping[str, Any], ...] = ()
    procedures: tuple[Mapping[str, Any], ...] = ()


def admit_modules(modules: Iterable[Module]) -> list[Module]:
    admitted = sorted(modules, key=lambda module: module.name)
    names = [module.name for module in admitted]
    if any(not name for name in names) or len(names) != len(set(names)):
        raise ValueError("module names must be non-empty and unique")
    incompatible = [module.name for module in admitted if module.api_version.split(".", 1)[0] != "1"]
    if incompatible:
        raise ValueError(
            f"incompatible module API: {', '.join(incompatible)}; "
            "upgrade agentic-workspace or use a compatible 1.x module"
        )
    supported = set(IR["module"]["capabilities"])
    unsupported = {
        capability for module in admitted for capability in module.required_capabilities if capability not in supported
    }
    if unsupported:
        raise ValueError(
            "unsupported required module semantics: "
            + ", ".join(sorted(unsupported))
            + "; upgrade agentic-workspace or remove the required capability"
        )
    owners: dict[str, str] = {}
    for module in admitted:
        for domain in module.owns:
            if not domain:
                raise ValueError(f"module {module.name} declared an empty owned domain")
            previous = owners.get(domain)
            if previous is not None:
                raise ValueError(f"owned domain conflict: {domain} ({previous}, {module.name})")
            owners[domain] = module.name
    return admitted


def discover_modules(*, entry_points: Iterable[Any] | None = None) -> list[Module]:
    """Load first- and third-party modules through the same entry-point seam."""

    candidates = entry_points
    if candidates is None:
        discovered = metadata.entry_points()
        candidates = (
            discovered.select(group=MODULE_ENTRY_POINT_GROUP)
            if hasattr(discovered, "select")
            else discovered.get(MODULE_ENTRY_POINT_GROUP, [])
        )
    modules: list[Module] = []
    for entry_point in candidates:
        value = entry_point.load()
        module = value() if callable(value) and not isinstance(value, Module) else value
        if not isinstance(module, Module):
            raise TypeError(f"module entry point {getattr(entry_point, 'name', '<unknown>')} did not return Module")
        modules.append(module)
    return admit_modules(modules)


def module_contributions(modules: Iterable[Module], *, context: Mapping[str, Any]) -> list[dict[str, Any]]:
    contributions: list[dict[str, Any]] = []
    for module in modules:
        contribution = module.contribute(context)
        if contribution is None:
            continue
        payload = dict(contribution)
        if payload.get("owner") not in {None, module.name}:
            raise ValueError(f"module {module.name} attempted to contribute for another owner")
        payload["owner"] = module.name
        contribution_resources = payload.get("resources", [])
        contribution_procedures = payload.get("procedures", [])
        if not isinstance(contribution_resources, list) or not isinstance(contribution_procedures, list):
            raise ValueError(f"module {module.name} resources and procedures must be lists")
        payload["resources"] = [*module.resources, *contribution_resources]
        payload["procedures"] = [*module.procedures, *contribution_procedures]
        contracts = {operation.operation_id: operation for operation in module.operations}
        actions = payload.get("actions", [])
        if not isinstance(actions, list) or any(not isinstance(action, Mapping) for action in actions):
            raise ValueError(f"module {module.name} actions must be a list of objects")
        for action in actions:
            operation_id = str(action.get("operation_id") or "")
            operation = contracts.get(operation_id)
            if operation is None:
                raise ValueError(f"module {module.name} proposed an operation it does not own: {operation_id}")
            if tuple(action.get("effects", [])) != operation.effects:
                raise ValueError(f"module {module.name} action effects differ from its operation contract")
        decisions = payload.get("decisions", [])
        if not isinstance(decisions, list) or any(not isinstance(item, Mapping) for item in decisions):
            raise ValueError(f"module {module.name} decisions must be a list of objects")
        for decision in decisions:
            operation_id = str(decision.get("response_operation_id") or "")
            operation = contracts.get(operation_id)
            if operation is None:
                raise ValueError(
                    f"module {module.name} decision response is not admitted by an owned operation: {operation_id}"
                )
            if tuple(decision.get("effects", [])) != operation.effects:
                raise ValueError(f"module {module.name} decision effects differ from its response operation contract")
        claims = payload.get("claims", {})
        if not isinstance(claims, Mapping):
            raise ValueError(f"module {module.name} claims must be an object")
        allowed = claims.get("allowed", [])
        if not isinstance(allowed, list) or any(claim not in module.claims for claim in allowed):
            raise ValueError(f"module {module.name} attempted to allow an unowned claim")
        contributions.append(payload)
    return contributions


def register_module_operations(dispatcher: OperationDispatcher, modules: Iterable[Module]) -> None:
    for module in modules:
        for operation in module.operations:
            dispatcher.register(operation)
