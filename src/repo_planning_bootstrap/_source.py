from __future__ import annotations

import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

DEFAULT_SOURCE_TYPE = "git"
DEFAULT_SOURCE_REF = "git+https://github.com/rickardvh/agentic-planning@master"
DEFAULT_SOURCE_LABEL = "agentic-planning-bootstrap master"
DEFAULT_RECORDED_AT = "2026-04-05"
DEFAULT_RECOMMENDED_UPGRADE_AFTER_DAYS = 30
UPGRADE_SOURCE_PATH = Path(".agentic-planning/UPGRADE-SOURCE.toml")


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


def default_upgrade_source() -> UpgradeSource:
    return UpgradeSource(
        source_type=DEFAULT_SOURCE_TYPE,
        source_ref=DEFAULT_SOURCE_REF,
        source_label=DEFAULT_SOURCE_LABEL,
        recorded_at=DEFAULT_RECORDED_AT,
        recommended_upgrade_after_days=DEFAULT_RECOMMENDED_UPGRADE_AFTER_DAYS,
        path=None,
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
