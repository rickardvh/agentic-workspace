from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Any

MODULE_ENTRY_POINT_GROUP = "agentic_workspace.modules"
MODULE_CONTRACT_VERSION = "agentic-workspace/module-capability/v2"
MODULE_READER_EPOCH = 1
SUPPORTED_REQUIRED_CAPABILITIES = frozenset(
    {
        "module-resources-v1",
        "module-skills-v1",
        "module-operations-v1",
        "module-results-v1",
    }
)


@dataclass(frozen=True)
class DiscoveredModule:
    name: str
    entry_point: str
    contract: dict[str, Any]
    operations: Mapping[str, Callable[..., Any]]
    status: str = "available"
    reason: str = ""


class ModuleContractError(ValueError):
    pass


def _string_list(value: Any, *, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ModuleContractError(f"{field} must be a list of non-empty strings")
    return [item.strip() for item in value]


def _mapping(value: Any, *, field: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ModuleContractError(f"{field} must be an object")
    return dict(value)


def validate_module_contract(payload: Mapping[str, Any]) -> dict[str, Any]:
    contract = dict(payload)
    if contract.get("schema_version") != MODULE_CONTRACT_VERSION:
        raise ModuleContractError(f"schema_version must be {MODULE_CONTRACT_VERSION}")
    name = str(contract.get("name", "")).strip()
    description = str(contract.get("description", "")).strip()
    if not name or not description:
        raise ModuleContractError("name and description are required")

    compatibility = _mapping(contract.get("compatibility"), field="compatibility")
    reader_epoch = compatibility.get("reader_epoch")
    if not isinstance(reader_epoch, int) or reader_epoch < 1:
        raise ModuleContractError("compatibility.reader_epoch must be a positive integer")
    required_capabilities = _string_list(compatibility.get("required_capabilities", []), field="compatibility.required_capabilities")

    ownership = _mapping(contract.get("ownership"), field="ownership")
    roots = _string_list(ownership.get("roots", []), field="ownership.roots")
    effect_classes = _string_list(ownership.get("effect_classes", []), field="ownership.effect_classes")
    authority_exclusions = _string_list(ownership.get("authority_exclusions"), field="ownership.authority_exclusions")
    if not authority_exclusions:
        raise ModuleContractError("ownership.authority_exclusions must preserve at least one explicit boundary")

    relevance = _mapping(contract.get("relevance"), field="relevance")
    task_terms = _string_list(relevance.get("task_terms", []), field="relevance.task_terms")
    path_prefixes = _string_list(relevance.get("path_prefixes", []), field="relevance.path_prefixes")
    always = relevance.get("always", False)
    if not isinstance(always, bool):
        raise ModuleContractError("relevance.always must be a boolean")

    capabilities = _mapping(contract.get("capabilities"), field="capabilities")
    normalized_capabilities: dict[str, list[dict[str, Any]]] = {}
    for capability_class in ("resources", "skills", "operations"):
        entries = capabilities.get(capability_class, [])
        if not isinstance(entries, list) or any(not isinstance(item, Mapping) for item in entries):
            raise ModuleContractError(f"capabilities.{capability_class} must be a list of objects")
        normalized_entries = [dict(item) for item in entries]
        for item in normalized_entries:
            if not str(item.get("id", "")).strip():
                raise ModuleContractError(f"capabilities.{capability_class}[].id is required")
        normalized_capabilities[capability_class] = normalized_entries

    result_semantics = _mapping(contract.get("result_semantics"), field="result_semantics")
    result_schema = str(result_semantics.get("schema_version", "")).strip()
    if not result_schema:
        raise ModuleContractError("result_semantics.schema_version is required")
    guaranteed_fields = _string_list(result_semantics.get("guaranteed_fields", []), field="result_semantics.guaranteed_fields")
    effect_fields = _string_list(result_semantics.get("effect_fields", []), field="result_semantics.effect_fields")
    warning_fields = _string_list(result_semantics.get("warning_fields", []), field="result_semantics.warning_fields")

    normalized = {
        **contract,
        "name": name,
        "description": description,
        "compatibility": {
            **compatibility,
            "reader_epoch": reader_epoch,
            "required_capabilities": required_capabilities,
        },
        "ownership": {
            **ownership,
            "roots": roots,
            "effect_classes": effect_classes,
            "authority_exclusions": authority_exclusions,
        },
        "relevance": {
            **relevance,
            "task_terms": task_terms,
            "path_prefixes": path_prefixes,
            "always": always,
        },
        "capabilities": normalized_capabilities,
        "result_semantics": {
            **result_semantics,
            "schema_version": result_schema,
            "guaranteed_fields": guaranteed_fields,
            "effect_fields": effect_fields,
            "warning_fields": warning_fields,
        },
        "dependencies": _string_list(contract.get("dependencies", []), field="dependencies"),
        "conflicts": _string_list(contract.get("conflicts", []), field="conflicts"),
    }
    return normalized


def module_contract_compatibility(contract: Mapping[str, Any]) -> tuple[str, str]:
    compatibility = _mapping(contract.get("compatibility"), field="compatibility")
    reader_epoch = int(compatibility.get("reader_epoch", 0))
    if reader_epoch > MODULE_READER_EPOCH:
        return ("incompatible", f"requires module reader epoch {reader_epoch}; runtime provides {MODULE_READER_EPOCH}")
    required = set(_string_list(compatibility.get("required_capabilities", []), field="compatibility.required_capabilities"))
    unsupported = sorted(required - SUPPORTED_REQUIRED_CAPABILITIES)
    if unsupported:
        return ("unsupported-capability", f"unsupported required capabilities: {', '.join(unsupported)}")
    return ("available", "")


def _entry_points() -> list[Any]:
    discovered = metadata.entry_points()
    if hasattr(discovered, "select"):
        return list(discovered.select(group=MODULE_ENTRY_POINT_GROUP))
    return list(discovered.get(MODULE_ENTRY_POINT_GROUP, []))


def discover_module_contracts(*, entry_points: list[Any] | None = None) -> list[DiscoveredModule]:
    results: list[DiscoveredModule] = []
    seen: set[str] = set()
    for entry_point in entry_points if entry_points is not None else _entry_points():
        entry_name = str(getattr(entry_point, "name", "unknown"))
        entry_identity = f"{getattr(entry_point, 'module', '')}:{getattr(entry_point, 'attr', '')}".strip(":") or entry_name
        try:
            loaded = entry_point.load()
            provided = loaded() if callable(loaded) else loaded
            provider = _mapping(provided, field=f"entry point {entry_name}")
            raw_contract = provider.get("contract", provider)
            contract = validate_module_contract(_mapping(raw_contract, field=f"entry point {entry_name}.contract"))
            operations_value = provider.get("operations", {}) if "contract" in provider else {}
            operations = _mapping(operations_value, field=f"entry point {entry_name}.operations")
            if any(not callable(operation) for operation in operations.values()):
                raise ModuleContractError("entry point operations must be callables")
            name = str(contract["name"])
            if name in seen:
                raise ModuleContractError(f"duplicate module identity: {name}")
            seen.add(name)
            status, reason = module_contract_compatibility(contract)
            results.append(
                DiscoveredModule(
                    name=name,
                    entry_point=entry_identity,
                    contract=contract,
                    operations=operations,
                    status=status,
                    reason=reason,
                )
            )
        except Exception as exc:
            results.append(
                DiscoveredModule(
                    name=entry_name,
                    entry_point=entry_identity,
                    contract={},
                    operations={},
                    status="malformed",
                    reason=str(exc),
                )
            )
    return results


def module_relevance(contract: Mapping[str, Any], *, task: str, changed_paths: list[str]) -> dict[str, Any]:
    relevance = _mapping(contract.get("relevance"), field="relevance")
    task_lower = task.lower()
    terms = _string_list(relevance.get("task_terms", []), field="relevance.task_terms")
    prefixes = _string_list(relevance.get("path_prefixes", []), field="relevance.path_prefixes")
    matched_terms = [term for term in terms if term.lower() in task_lower]
    matched_paths = [path for path in changed_paths if any(path.startswith(prefix) for prefix in prefixes)]
    selected = bool(relevance.get("always", False) or matched_terms or matched_paths)
    return {
        "status": "relevant" if selected else "irrelevant",
        "matched_terms": matched_terms,
        "matched_paths": matched_paths,
        "source": f"{contract.get('name', 'module')}.relevance",
    }


def module_contribution(contract: Mapping[str, Any], *, task: str, changed_paths: list[str]) -> dict[str, Any] | None:
    relevance = module_relevance(contract, task=task, changed_paths=changed_paths)
    if relevance["status"] != "relevant":
        return None
    capabilities = _mapping(contract.get("capabilities"), field="capabilities")
    return {
        "module": str(contract.get("name", "")),
        "contract": MODULE_CONTRACT_VERSION,
        "relevance": relevance,
        "resources": [dict(item) for item in capabilities.get("resources", [])],
        "skills": [dict(item) for item in capabilities.get("skills", [])],
        "operations": [dict(item) for item in capabilities.get("operations", [])],
        "effect_classes": list(_mapping(contract.get("ownership"), field="ownership").get("effect_classes", [])),
        "authority_exclusions": list(_mapping(contract.get("ownership"), field="ownership").get("authority_exclusions", [])),
        "result_semantics": dict(_mapping(contract.get("result_semantics"), field="result_semantics")),
        "source": "module entry-point contract",
    }


def target_has_install_signal(target_root: Path, signals: list[str]) -> bool:
    return True if not signals else any((target_root / signal).exists() for signal in signals)


def invoke_module_operation(discovered: DiscoveredModule, *, operation_id: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
    if discovered.status != "available":
        raise ModuleContractError(f"module {discovered.name} is {discovered.status}: {discovered.reason}")
    declared = {
        str(item.get("id")): dict(item)
        for item in _mapping(discovered.contract.get("capabilities"), field="capabilities").get("operations", [])
    }
    if operation_id not in declared:
        raise ModuleContractError(f"operation {operation_id} is not declared by module {discovered.name}")
    operation = discovered.operations.get(operation_id)
    if operation is None:
        raise ModuleContractError(f"operation {operation_id} is declared but unavailable")
    result = operation(dict(arguments))
    if not isinstance(result, Mapping):
        raise ModuleContractError(f"operation {operation_id} must return an object")
    payload = dict(result)
    semantics = _mapping(discovered.contract.get("result_semantics"), field="result_semantics")
    missing = [field for field in semantics.get("guaranteed_fields", []) if field not in payload]
    if missing:
        raise ModuleContractError(f"operation {operation_id} omitted guaranteed result fields: {', '.join(missing)}")
    allowed_effects = set(_mapping(discovered.contract.get("ownership"), field="ownership").get("effect_classes", []))
    reported_effects = set(payload.get("effects", [])) if isinstance(payload.get("effects", []), list) else set()
    widened = sorted(reported_effects - allowed_effects)
    if widened:
        raise ModuleContractError(f"operation {operation_id} reported undeclared effects: {', '.join(widened)}")
    return {
        "kind": "agentic-workspace/module-operation-result/v1",
        "module": discovered.name,
        "operation": operation_id,
        "result_schema": semantics.get("schema_version"),
        "result": payload,
        "authority_exclusions": list(_mapping(discovered.contract.get("ownership"), field="ownership").get("authority_exclusions", [])),
    }
