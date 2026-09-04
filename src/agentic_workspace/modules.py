from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from importlib import metadata
from typing import Any

from .operations import Operation, OperationDispatcher

MODULE_ENTRY_POINT_GROUP = "agentic_workspace.modules"


@dataclass(frozen=True)
class Module:
    name: str
    contribute: Callable[[Mapping[str, Any]], Mapping[str, Any] | None]
    operations: tuple[Operation, ...] = ()


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
    names = [module.name for module in modules]
    if len(names) != len(set(names)):
        raise ValueError("module names must be unique")
    return sorted(modules, key=lambda module: module.name)


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
        contributions.append(payload)
    return contributions


def register_module_operations(dispatcher: OperationDispatcher, modules: Iterable[Module]) -> None:
    for module in modules:
        for operation in module.operations:
            dispatcher.register(operation)
