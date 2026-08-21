from __future__ import annotations

from typing import Any


def _contract(*, name: str, reader_epoch: int = 1, roots: list[str] | None = None) -> dict[str, Any]:
    return {
        "schema_version": "agentic-workspace/module-capability/v2",
        "name": name,
        "description": "Read and refresh external build signals.",
        "compatibility": {
            "reader_epoch": reader_epoch,
            "required_capabilities": ["module-resources-v1", "module-operations-v1", "module-results-v1"],
        },
        "ownership": {
            "roots": roots or ["external-signals/cache"],
            "effect_classes": ["external-signals-cache"],
            "authority_exclusions": ["cannot grant mutation, proof, parent-intent, or completion authority"],
        },
        "relevance": {
            "task_terms": ["external build signal"],
            "path_prefixes": ["external-signals/"],
        },
        "capabilities": {
            "resources": [{"id": "external-signals.latest", "ref": "signals://latest", "read_only": True}],
            "skills": [],
            "operations": [{"id": "external-signals.refresh", "result_schema": "external-signals/result/v1"}],
        },
        "result_semantics": {
            "schema_version": "external-signals/result/v1",
            "guaranteed_fields": ["status", "effects"],
            "effect_fields": ["effects"],
            "warning_fields": ["warnings"],
        },
        "dependencies": [],
        "conflicts": [],
    }


def _refresh(arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "refreshed",
        "effects": ["external-signals-cache"],
        "requested_revision": str(arguments.get("revision") or "latest"),
    }


def provider() -> dict[str, Any]:
    return {
        "contract": _contract(name="external-signals"),
        "operations": {"external-signals.refresh": _refresh},
    }


def conflicting_provider() -> dict[str, Any]:
    return {
        "contract": _contract(name="external-signals-conflict", roots=["external-signals/cache"]),
        "operations": {"external-signals.refresh": _refresh},
    }


def future_provider() -> dict[str, Any]:
    return {
        "contract": _contract(name="external-signals-future", reader_epoch=99, roots=["external-signals/future"]),
        "operations": {"external-signals.refresh": _refresh},
    }
