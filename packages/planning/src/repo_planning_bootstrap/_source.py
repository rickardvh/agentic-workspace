from __future__ import annotations

import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

DEFAULT_SOURCE_TYPE = "git"
DEFAULT_SOURCE_REF = "git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/planning"
DEFAULT_SOURCE_LABEL = "agentic-planning monorepo master"
DEFAULT_RECORDED_AT = "2026-05-06"
DEFAULT_RECOMMENDED_UPGRADE_AFTER_DAYS = 30
UPGRADE_SOURCE_PATH = Path(".agentic-workspace/planning/UPGRADE-SOURCE.toml")


@dataclass(frozen=True)
class UpgradeSource:
    source_type: str
    source_ref: str
    source_label: str
    recorded_at: str
    recommended_upgrade_after_days: int
    path: Path | None = None

    def age_days(self, *, today: date | None = None) -> int | None:
        today_value = today or date.today()
        try:
            recorded = date.fromisoformat(self.recorded_at)
        except ValueError:
            return None
        return (today_value - recorded).days


def default_upgrade_source(*, recorded_at: str | None = None) -> UpgradeSource:
    return UpgradeSource(
        source_type=DEFAULT_SOURCE_TYPE,
        source_ref=DEFAULT_SOURCE_REF,
        source_label=DEFAULT_SOURCE_LABEL,
        recorded_at=recorded_at or DEFAULT_RECORDED_AT,
        recommended_upgrade_after_days=DEFAULT_RECOMMENDED_UPGRADE_AFTER_DAYS,
        path=None,
    )


def current_recorded_at(*, today: date | None = None) -> str:
    return (today or date.today()).isoformat()


def is_valid_upgrade_source_text(text: str) -> bool:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return False

    source_type = str(data.get("source_type", "")).strip()
    source_ref = str(data.get("source_ref", "")).strip()
    recorded_at = str(data.get("recorded_at", "")).strip()
    recommended_upgrade_after_days = data.get("recommended_upgrade_after_days", DEFAULT_RECOMMENDED_UPGRADE_AFTER_DAYS)
    if source_type not in {"git", "local"} or not source_ref:
        return False
    if recorded_at:
        try:
            date.fromisoformat(recorded_at)
        except ValueError:
            return False
    return isinstance(recommended_upgrade_after_days, int)


def is_default_upgrade_source_text(text: str) -> bool:
    if not is_valid_upgrade_source_text(text):
        return False
    data = tomllib.loads(text)
    default = default_upgrade_source()
    return (
        str(data.get("source_type", "")).strip() == default.source_type
        and str(data.get("source_ref", "")).strip() == default.source_ref
        and (str(data.get("source_label", "")).strip() or default.source_label) == default.source_label
        and data.get("recommended_upgrade_after_days", default.recommended_upgrade_after_days) == default.recommended_upgrade_after_days
    )


def render_upgrade_source(source: UpgradeSource | None = None, *, recorded_at: str | None = None) -> str:
    source_record = source or default_upgrade_source(recorded_at=recorded_at or current_recorded_at())
    return (
        f'source_type = "{source_record.source_type}"\n'
        f'source_ref = "{source_record.source_ref}"\n'
        f'source_label = "{source_record.source_label}"\n'
        f'recorded_at = "{recorded_at or source_record.recorded_at}"\n'
        f"recommended_upgrade_after_days = {source_record.recommended_upgrade_after_days}\n"
    )


def resolve_upgrade_source(target: str | Path | None = None) -> UpgradeSource:
    target_root = Path(target or Path.cwd()).resolve()
    path = target_root / UPGRADE_SOURCE_PATH
    default = default_upgrade_source()
    if not target_root.exists() or not path.exists():
        return default

    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return default

    source_type = str(data.get("source_type", "")).strip()
    source_ref = str(data.get("source_ref", "")).strip()
    source_label = str(data.get("source_label", "")).strip() or default.source_label
    recorded_at = str(data.get("recorded_at", "")).strip() or default.recorded_at
    recommended_upgrade_after_days = data.get("recommended_upgrade_after_days", default.recommended_upgrade_after_days)
    if source_type not in {"git", "local"}:
        return default
    if not source_ref:
        return default
    if not isinstance(recommended_upgrade_after_days, int):
        recommended_upgrade_after_days = default.recommended_upgrade_after_days
    return UpgradeSource(
        source_type=source_type,
        source_ref=source_ref,
        source_label=source_label,
        recorded_at=recorded_at,
        recommended_upgrade_after_days=recommended_upgrade_after_days,
        path=path,
    )
