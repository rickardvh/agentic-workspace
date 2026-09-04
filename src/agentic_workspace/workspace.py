from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from .decision import compile_source_decision
from .durability import atomic_write_json, owner_process_lock
from .modules import Module, admit_modules, discover_modules, module_contributions, register_module_operations
from .operations import OperationDispatcher


class Workspace:
    def __init__(self, target: str | Path, *, modules: Iterable[Module] | None = None) -> None:
        self.target = Path(target).resolve()
        self._modules = admit_modules(modules) if modules is not None else discover_modules()

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
        safe_key = self._safe_key(key)
        return self.target / ".agentic-workspace" / "receipts" / f"{safe_key}.json"

    @staticmethod
    def _safe_key(key: str) -> str:
        safe_key = key.removeprefix("sha256:")
        if re.fullmatch(r"[0-9a-f]{64}", safe_key) is None:
            raise ValueError("idempotency_key must be a sha256 identity")
        return safe_key

    def _journal_path(self, key: str) -> Path:
        return self.target / ".agentic-workspace" / "local" / "commits" / f"{self._safe_key(key)}.json"

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
        atomic_write_json(path, {"request": request, "result": result})

    def _load_journal(self, key: str) -> dict[str, Any] | None:
        path = self._journal_path(key)
        if not path.is_file():
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        return dict(value) if isinstance(value, dict) else None

    def _write_journal(self, key: str, value: dict[str, Any]) -> None:
        atomic_write_json(self._journal_path(key), value)

    def _clear_journal(self, key: str) -> None:
        path = self._journal_path(key)
        path.unlink(missing_ok=True)
        for directory in (path.parent, path.parent.parent):
            try:
                directory.rmdir()
            except OSError:
                break

    def invoke(self, invocation: Mapping[str, Any]) -> dict[str, Any]:
        intent = invocation.get("intent", {})
        if not isinstance(intent, Mapping):
            raise ValueError("invocation intent must be an object")
        operation_id = str(invocation.get("operation_id") or "")
        persist_receipt = operation_id not in {"workspace.remove", "workspace.remove-legacy"}
        dispatcher = OperationDispatcher(
            receipt_loader=self._load_receipt if persist_receipt else None,
            receipt_writer=self._write_receipt if persist_receipt else None,
            journal_loader=self._load_journal,
            journal_writer=self._write_journal,
            journal_clearer=self._clear_journal,
        )
        register_module_operations(dispatcher, self._modules)
        operation = dispatcher.operation(operation_id)
        # Invocation transport fields are untrusted. Every registered mutation
        # shares the authoritative process lock; effect-free work is isolated by
        # its registered operation identity.
        lock_owner = "mutation" if operation.effects else operation.operation_id
        with owner_process_lock(self.target, lock_owner):
            return dispatcher.invoke(
                invocation,
                resolve_decision=lambda: self.start(
                    intent=intent,
                ),
            )
