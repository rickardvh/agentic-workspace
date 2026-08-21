from __future__ import annotations

from typing import Any

_CURRENT_FACTS: dict[str, list[dict[str, Any]]] = {}


def _default_facts(name: str) -> list[dict[str, Any]]:
    return [
        {
            "id": "external-signals.build-risk",
            "type": "string",
            "value": "elevated",
            "subject": "external-build",
            "source": {"owner": name, "revision": "signal-r1", "current": True},
        }
    ]


def _current_facts(name: str) -> list[dict[str, Any]]:
    return [dict(item) for item in _CURRENT_FACTS.get(name, _default_facts(name))]


def _contract(*, name: str, reader_epoch: int = 1, roots: list[str] | None = None) -> dict[str, Any]:
    return {
        "schema_version": "agentic-workspace/module-capability/v2",
        "name": name,
        "description": "Read and refresh external build signals.",
        "compatibility": {
            "reader_epoch": reader_epoch,
            "required_capabilities": ["module-facts-v1", "module-resources-v1", "module-operations-v1", "module-results-v1"],
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
        "facts": _current_facts(name),
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


def _refresh(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    revision = str(arguments.get("revision") or "latest")
    result: dict[str, Any] = {
        "status": "refreshed",
        "effects": ["external-signals-cache"],
        "requested_revision": revision,
    }
    if arguments.get("omit_facts"):
        return result
    facts = (
        []
        if arguments.get("remove")
        else [
            {
                "id": "external-signals.build-risk",
                "type": "string",
                "value": str(arguments.get("value") or "clear"),
                "subject": "external-build",
                "source": {"owner": name, "revision": revision, "current": bool(arguments.get("current", True))},
            }
        ]
    )
    _CURRENT_FACTS[name] = facts
    result["facts"] = facts
    return result


def provider() -> dict[str, Any]:
    return {
        "contract": _contract(name="external-signals"),
        "operations": {"external-signals.refresh": lambda arguments: _refresh("external-signals", arguments)},
    }


def conflicting_provider() -> dict[str, Any]:
    return {
        "contract": _contract(name="external-signals-conflict", roots=["external-signals/cache"]),
        "operations": {"external-signals.refresh": lambda arguments: _refresh("external-signals-conflict", arguments)},
    }


def future_provider() -> dict[str, Any]:
    return {
        "contract": _contract(name="external-signals-future", reader_epoch=99, roots=["external-signals/future"]),
        "operations": {"external-signals.refresh": lambda arguments: _refresh("external-signals-future", arguments)},
    }
