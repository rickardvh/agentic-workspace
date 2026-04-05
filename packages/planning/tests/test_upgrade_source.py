from __future__ import annotations

from pathlib import Path

from repo_planning_bootstrap._source import UPGRADE_SOURCE_PATH, default_upgrade_source, resolve_upgrade_source
from repo_planning_bootstrap.installer import doctor_bootstrap


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def test_default_upgrade_source_uses_master_branch() -> None:
    source = default_upgrade_source()
    assert source.source_type == "git"
    assert source.source_ref == "git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/planning"
    assert source.source_label == "agentic-planning-bootstrap monorepo master"


def test_resolve_upgrade_source_reads_checked_in_file(tmp_path: Path) -> None:
    _write(
        tmp_path / UPGRADE_SOURCE_PATH,
        """
source_type = "git"
source_ref = "git+https://example.com/org/repo@v1.2.3"
source_label = "example release"
recorded_at = "2026-03-01"
recommended_upgrade_after_days = 45
""",
    )
    source = resolve_upgrade_source(tmp_path)
    assert source.source_ref == "git+https://example.com/org/repo@v1.2.3"
    assert source.source_label == "example release"
    assert source.recorded_at == "2026-03-01"
    assert source.recommended_upgrade_after_days == 45


def test_doctor_reports_stale_upgrade_source(tmp_path: Path) -> None:
    _write(
        tmp_path / UPGRADE_SOURCE_PATH,
        """
source_type = "git"
source_ref = "git+https://example.com/org/repo@master"
source_label = "example master"
recorded_at = "2025-01-01"
recommended_upgrade_after_days = 30
""",
    )
    result = doctor_bootstrap(target=tmp_path)
    assert any(action.kind == "source" and action.path == tmp_path / UPGRADE_SOURCE_PATH for action in result.actions)
    assert any(warning["warning_class"] == "upgrade_source_stale" for warning in result.warnings)
