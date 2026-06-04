from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_prompt_semantic_markers.py"
SPEC = importlib.util.spec_from_file_location("check_prompt_semantic_markers", MODULE_PATH)
check_prompt_semantic_markers = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = check_prompt_semantic_markers
SPEC.loader.exec_module(check_prompt_semantic_markers)


def test_prompt_semantic_marker_guardrail_accepts_current_runtime() -> None:
    assert check_prompt_semantic_markers.prompt_semantic_marker_findings() == []


def test_prompt_semantic_marker_guardrail_rejects_guarded_marker_table(tmp_path: Path) -> None:
    source = tmp_path / "runtime.py"
    source.write_text(
        """
def _intent_discovery_dialogue_payload():
    broad_markers = ("improve", "better")
    return broad_markers
""",
        encoding="utf-8",
    )

    findings = check_prompt_semantic_markers.prompt_semantic_marker_findings(source)

    assert len(findings) == 1
    assert "broad_markers" in findings[0]


def test_prompt_semantic_marker_guardrail_rejects_removal_intent_classifier(tmp_path: Path) -> None:
    source = tmp_path / "runtime.py"
    source.write_text(
        """
def _task_has_removal_intent(task_text):
    return "remove" in task_text
""",
        encoding="utf-8",
    )

    findings = check_prompt_semantic_markers.prompt_semantic_marker_findings(source)

    assert len(findings) == 1
    assert "_task_has_removal_intent" in findings[0]


def test_prompt_semantic_marker_guardrail_rejects_objective_drift_marker_table(tmp_path: Path) -> None:
    source = tmp_path / "runtime.py"
    source.write_text(
        """
def _objective_drift_payload():
    removal_markers = ("remove", "delete")
    return removal_markers
""",
        encoding="utf-8",
    )

    findings = check_prompt_semantic_markers.prompt_semantic_marker_findings(source)

    assert len(findings) == 1
    assert "removal_markers" in findings[0]
