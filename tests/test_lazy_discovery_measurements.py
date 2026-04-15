from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check" / "measure_lazy_discovery.py"
SPEC = importlib.util.spec_from_file_location("measure_lazy_discovery", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
measure_lazy_discovery = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = measure_lazy_discovery
SPEC.loader.exec_module(measure_lazy_discovery)


def test_capture_artifact_supports_file_bundles(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text("# Root\n", encoding="utf-8")
    (tmp_path / "docs" / "guide.md").write_text("# Guide\n", encoding="utf-8")

    artifact = measure_lazy_discovery._capture_artifact(
        measure_lazy_discovery.ArtifactSpec(
            kind="file_bundle",
            label="bundle",
            detail="docs",
            paths=("README.md", "docs/guide.md"),
        ),
        target_root=tmp_path,
    )

    assert artifact["artifact_count"] == 2
    assert artifact["file_reads"] == 2
    assert artifact["query_count"] == 0
    assert artifact["paths"] == ["README.md", "docs/guide.md"]
    assert "## README.md" in artifact["rendered"]
    assert "## docs/guide.md" in artifact["rendered"]


def test_measure_case_tracks_query_and_file_savings(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "AGENTS.md").write_text("# Agent Instructions\n", encoding="utf-8")
    (tmp_path / "TODO.md").write_text("# TODO\n\n- No active work right now.\n", encoding="utf-8")

    def _fake_capture_json_command(args: list[str], *, runner) -> dict[str, object]:
        return {"command": " ".join(args), "answer": "compact"}

    monkeypatch.setattr(measure_lazy_discovery, "_capture_json_command", _fake_capture_json_command)

    case = measure_lazy_discovery.MeasurementCase(
        label="demo",
        workflow_class="startup",
        question="What should I read?",
        preferred=measure_lazy_discovery.ArtifactSpec(
            kind="workspace_command_json",
            label="compact",
            detail="query",
            args=("report", "--target", tmp_path.as_posix(), "--format", "json"),
        ),
        baseline=measure_lazy_discovery.ArtifactSpec(
            kind="file_bundle",
            label="broad",
            detail="files",
            paths=("AGENTS.md", "TODO.md"),
        ),
    )

    result = measure_lazy_discovery._measure_case(case, target_root=tmp_path)

    assert result["preferred"]["query_count"] == 1
    assert result["preferred"]["file_reads"] == 0
    assert result["baseline"]["artifact_count"] == 2
    assert result["baseline"]["file_reads"] == 2
    assert result["savings"]["artifacts_saved"] == 1
    assert result["savings"]["file_reads_saved"] == 2


def test_measure_lazy_discovery_reports_totals(tmp_path: Path, monkeypatch) -> None:
    measurements = [
        {
            "label": "one",
            "preferred": {"artifact_count": 1, "file_reads": 0, "query_count": 1, "bytes": 100, "approx_tokens": 25},
            "baseline": {"artifact_count": 3, "file_reads": 3, "query_count": 0, "bytes": 400, "approx_tokens": 100},
            "savings": {"artifacts_saved": 2, "file_reads_saved": 3, "bytes_saved": 300, "approx_tokens_saved": 75},
        },
        {
            "label": "two",
            "preferred": {"artifact_count": 1, "file_reads": 0, "query_count": 1, "bytes": 50, "approx_tokens": 13},
            "baseline": {"artifact_count": 2, "file_reads": 2, "query_count": 0, "bytes": 250, "approx_tokens": 63},
            "savings": {"artifacts_saved": 1, "file_reads_saved": 2, "bytes_saved": 200, "approx_tokens_saved": 50},
        },
    ]

    monkeypatch.setattr(measure_lazy_discovery, "_build_cases", lambda target_root: ["ignored-a", "ignored-b"])
    monkeypatch.setattr(
        measure_lazy_discovery,
        "_measure_case",
        lambda case, *, target_root: measurements[0] if case == "ignored-a" else measurements[1],
    )

    payload = measure_lazy_discovery.measure_lazy_discovery(target_root=tmp_path)

    assert payload["schema_version"] == "lazy-discovery-measurements/v2"
    assert payload["totals"]["preferred_artifact_count"] == 2
    assert payload["totals"]["baseline_artifact_count"] == 5
    assert payload["totals"]["artifacts_saved"] == 3
    assert payload["totals"]["file_reads_saved"] == 5
    assert payload["totals"]["bytes_saved"] == 500
    assert payload["totals"]["approx_tokens_saved"] == 125
    assert payload["totals"]["artifact_reduction_percent"] == 60.0
    assert payload["totals"]["byte_reduction_percent"] == 76.9
    assert payload["totals"]["approx_token_reduction_percent"] == 76.7
