from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from .decision import compile_source_decision
from .modules import Module, discover_modules, module_contributions, register_module_operations
from .operations import OperationDispatcher


class Workspace:
    def __init__(self, target: str | Path, *, modules: Iterable[Module] | None = None) -> None:
        self.target = Path(target).resolve()
        self._modules = list(modules) if modules is not None else discover_modules()

    def start(
        self,
        *,
        intent: Mapping[str, Any] | None = None,
        task: str = "",
        changed_paths: Iterable[str] = (),
        claims: Iterable[str] = (),
    ) -> dict[str, Any]:
        request = dict(intent or {})
        request.setdefault("task", task)
        request.setdefault("changed_paths", sorted(set(changed_paths)))
        request.setdefault("claims", sorted(set(claims)))
        context = {**request, "target": str(self.target)}
        return compile_source_decision(module_contributions(self._modules, context=context), intent=request)

    def _receipt_path(self, key: str) -> Path:
        safe_key = key.removeprefix("sha256:")
        return self.target / ".agentic-workspace" / "receipts" / f"{safe_key}.json"

    def _load_receipt(self, key: str) -> tuple[dict[str, Any], dict[str, Any]] | None:
        path = self._receipt_path(key)
        if not path.is_file():
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        if (
            not isinstance(value, dict)
            or not isinstance(value.get("request"), dict)
            or not isinstance(value.get("result"), dict)
        ):
            return None
        return (dict(value["request"]), dict(value["result"]))

    def _write_receipt(self, key: str, request: dict[str, Any], result: dict[str, Any]) -> None:
        path = self._receipt_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"request": request, "result": result}, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def invoke(self, invocation: Mapping[str, Any]) -> dict[str, Any]:
        intent = invocation.get("intent", {})
        if not isinstance(intent, Mapping):
            raise ValueError("invocation intent must be an object")
        operation_id = str(invocation.get("operation_id") or "")
        persist_receipt = operation_id not in {"workspace.remove", "workspace.remove-legacy"}
        dispatcher = OperationDispatcher(
            receipt_loader=self._load_receipt if persist_receipt else None,
            receipt_writer=self._write_receipt if persist_receipt else None,
        )
        register_module_operations(dispatcher, self._modules)
        return dispatcher.invoke(
            invocation,
            resolve_decision=lambda: self.start(
                intent=intent,
            ),
        )
