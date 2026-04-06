from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Protocol


class ActionDictLike(Protocol):
    def to_dict(self, target_root: Path) -> dict[str, object]: ...


@dataclass(frozen=True)
class WorkspaceModuleReport:
    module: str
    message: str
    target_root: Path
    dry_run: bool
    actions: list[dict[str, Any]]
    warnings: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "module": self.module,
            "message": self.message,
            "target_root": self.target_root.as_posix(),
            "dry_run": self.dry_run,
            "actions": [serialise_value(action) for action in self.actions],
            "warnings": [serialise_value(warning) for warning in self.warnings],
        }


def adapt_module_result(*, module: str, result: Any) -> WorkspaceModuleReport:
    target_root = Path(result.target_root)
    actions = [adapt_action(action=action, target_root=target_root) for action in getattr(result, "actions", [])]
    warnings = [serialise_value(warning) for warning in getattr(result, "warnings", [])]
    return WorkspaceModuleReport(
        module=module,
        message=result.message,
        target_root=target_root,
        dry_run=bool(result.dry_run),
        actions=actions,
        warnings=warnings,
    )


def adapt_action(*, action: Any, target_root: Path) -> dict[str, Any]:
    to_dict = getattr(action, "to_dict", None)
    if callable(to_dict):
        return {key: serialise_value(value) for key, value in to_dict(target_root).items()}
    if is_dataclass(action):
        payload = asdict(action)
        path_value = payload.get("path")
        if isinstance(path_value, Path):
            try:
                payload["path"] = path_value.relative_to(target_root)
            except ValueError:
                payload["path"] = path_value
        return {key: serialise_value(value) for key, value in payload.items()}
    return {key: serialise_value(value) for key, value in vars(action).items()}


def serialise_value(value: Any) -> Any:
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        return {key: serialise_value(inner) for key, inner in value.items()}
    if isinstance(value, list):
        return [serialise_value(item) for item in value]
    return value
