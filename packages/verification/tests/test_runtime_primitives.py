from __future__ import annotations

from pathlib import Path

import pytest

from repo_verification_bootstrap.runtime_primitives import VerificationUsageError, verification_report_payload


def test_verification_report_absent_manifest(tmp_path: Path) -> None:
    payload = verification_report_payload(target_root=tmp_path, changed_paths=[], task_text="")

    assert payload["status"] == "absent"
    assert payload["configured"] is False
    assert payload["protocol_count"] == 0
    assert payload["active_count"] == 0
    assert payload["evidence_strategy"]["kind"] == "agentic-workspace/verification-evidence-strategy/v1"
    assert payload["evidence_strategy"]["status"] == "unavailable"
    assert payload["evidence_strategy"]["strategy_basis"]["declared_strategy_state"] == "not-declared"


def test_verification_report_matches_path_protocol_and_evidence(tmp_path: Path) -> None:
    manifest = tmp_path / ".agentic-workspace" / "verification" / "manifest.toml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        """
schema_version = "agentic-workspace/verification-manifest/v1"

[protocols.ui_review]
title = "UI review"
purpose = "Check user-visible behavior."
applies_to_paths = ["web/**"]
expected_evidence = ["ui_review_passed"]
review_owner = "frontend"

[evidence_bundles.ui_pass]
protocol_id = "ui_review"
evidence_items = ["ui_review_passed"]
changed_paths = ["web/app.py"]
""".strip(),
        encoding="utf-8",
    )

    payload = verification_report_payload(target_root=tmp_path, changed_paths=["web/app.py"], task_text="")

    assert payload["status"] == "matched"
    assert payload["configured"] is True
    assert payload["active_count"] == 1
    assert payload["active_protocols"][0]["id"] == "ui_review"
    assert payload["evidence_status"][0]["state"] == "satisfied"


def test_verification_report_task_marker_match_reports_configured_protocol_authority(tmp_path: Path) -> None:
    manifest = tmp_path / ".agentic-workspace" / "verification" / "manifest.toml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        """
schema_version = "agentic-workspace/verification-manifest/v1"

[protocols.privacy_review]
title = "Privacy review"
purpose = "Check privacy-sensitive behavior."
applies_to_task_markers = ["privacy"]
expected_evidence = ["privacy_reviewed"]
review_owner = "privacy-owner"
""".strip(),
        encoding="utf-8",
    )

    payload = verification_report_payload(
        target_root=tmp_path,
        changed_paths=["README.md"],
        task_text="Update privacy wording",
    )

    assert payload["status"] == "attention"
    assert payload["active_protocols"][0]["id"] == "privacy_review"
    assert payload["active_protocols"][0]["applies_because"] == ["task marker matched privacy"]
    protocol_boundary = payload["active_protocols"][0]["authority_boundary"]
    assert "configured verification protocol privacy_review" in protocol_boundary["observed_by_aw"]
    assert "task marker matched privacy" in protocol_boundary["observed_by_aw"]
    assert "whether the configured protocol is semantically relevant to the current work" in protocol_boundary["agent_owned_decisions"]
    assert "does not classify user intent" in protocol_boundary["reporting_rule"]
    assert "does not decide the user's semantic intent" in payload["authority_boundary"]["reporting_rule"]


def test_verification_report_rejects_protocol_without_activation(tmp_path: Path) -> None:
    manifest = tmp_path / ".agentic-workspace" / "verification" / "manifest.toml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        """
schema_version = "agentic-workspace/verification-manifest/v1"

[protocols.unrouted]
title = "Unrouted"
purpose = "No activation signal."
review_owner = "owner"
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(VerificationUsageError, match="requires at least one activation signal"):
        verification_report_payload(target_root=tmp_path, changed_paths=[], task_text="")


def test_verification_report_rejects_unbounded_transcript_refs(tmp_path: Path) -> None:
    manifest = tmp_path / ".agentic-workspace" / "verification" / "manifest.toml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        """
schema_version = "agentic-workspace/verification-manifest/v1"

[protocols.model_eval]
title = "Model eval"
purpose = "Check model-run evidence."
applies_to_task_markers = ["eval"]
expected_evidence = ["eval_passed"]
review_owner = "eval-owner"

[evidence_bundles.eval_run]
protocol_id = "model_eval"
evidence_items = ["eval_passed"]
transcript_refs = [".agentic-workspace/local/scratch/evals/run/transcript.jsonl"]
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(VerificationUsageError, match="transcript_refs requires bounded transcript metadata"):
        verification_report_payload(target_root=tmp_path, changed_paths=[], task_text="eval")


def test_verification_report_marks_stale_evidence_attention(tmp_path: Path) -> None:
    manifest = tmp_path / ".agentic-workspace" / "verification" / "manifest.toml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        """
schema_version = "agentic-workspace/verification-manifest/v1"

[protocols.ui_review]
title = "UI review"
purpose = "Check user-visible behavior."
applies_to_paths = ["web/**"]
expected_evidence = ["ui_review_passed"]
review_owner = "frontend"

[evidence_bundles.ui_pass]
protocol_id = "ui_review"
evidence_items = ["ui_review_passed"]
changed_paths = ["web/app.py"]
stale_when = ["web/**"]
""".strip(),
        encoding="utf-8",
    )

    payload = verification_report_payload(target_root=tmp_path, changed_paths=["web/app.py"], task_text="")

    assert payload["status"] == "attention"
    assert payload["evidence_status"][0]["state"] == "stale-evidence"
    assert payload["evidence_status"][0]["stale_expected_evidence"] == ["ui_review_passed"]
    assert payload["evidence_status"][0]["missing_evidence"] == ["ui_review_passed"]


def test_verification_evidence_strategy_reports_declared_host_strategy(tmp_path: Path) -> None:
    strategy_doc = tmp_path / "docs" / "maintainer" / "testing-strategy.md"
    strategy_doc.parent.mkdir(parents=True)
    strategy_doc.write_text(
        """
# Testing Strategy

Prefer behavior contracts over one-off regressions. Merge repeated mode, section,
or branch-shape checks when the same behavior is covered. Contract-Owned Cases
use conformance when suitable. Prune only when equivalent coverage remains.
Root workspace tests prove product orchestration. Package-local tests prove
module-owned behavior.
""".strip(),
        encoding="utf-8",
    )

    payload = verification_report_payload(target_root=tmp_path, changed_paths=[], task_text="")

    strategy = payload["evidence_strategy"]
    assert strategy["status"] == "ready"
    basis = strategy["strategy_basis"]
    assert basis["declared_strategy_state"] == "declared"
    assert basis["strategy_confidence"] == "high"
    assert basis["declared_strategy_sources"] == [
        {
            "path": "docs/maintainer/testing-strategy.md",
            "signals": [
                "prefer behavior contracts over one-off regressions",
                "merge repeated mode/section/branch-shape checks",
                "convert stable generated command output only with named conformance owner",
                "prune only with equivalent coverage recorded",
                "root tests prove product orchestration",
                "package-local tests prove module-owned behavior",
            ],
        }
    ]
    assert "No universal testing strategy inferred." in strategy["limits"]


def test_verification_evidence_strategy_classifies_changed_test_fixture_variants(tmp_path: Path) -> None:
    strategy_doc = tmp_path / "docs" / "maintainer" / "testing-strategy.md"
    strategy_doc.parent.mkdir(parents=True)
    strategy_doc.write_text(
        """
# Testing Strategy

Prefer behavior contracts over one-off regressions. Merge repeated mode, section,
or branch-shape checks when the same behavior is covered.
""".strip(),
        encoding="utf-8",
    )
    test_file = tmp_path / "tests" / "test_model_cli_harness.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text(
        """
def _warning_case(value):
    return value


def test_model_cli_harness_scores_raw_read_posix():
    warnings = _warning_case("posix")
    assert "raw workspace files" in warnings


def test_model_cli_harness_scores_raw_read_windows():
    warnings = _warning_case("windows")
    assert "raw workspace files" in warnings
""".strip(),
        encoding="utf-8",
    )

    payload = verification_report_payload(
        target_root=tmp_path,
        changed_paths=["tests/test_model_cli_harness.py"],
        task_text="reduce regression sprawl",
    )

    strategy = payload["evidence_strategy"]
    assert strategy["status"] == "ready"
    assert strategy["summary"]["ordinary_tests_touched"] == 2
    assert strategy["summary"]["hotspot_files_touched"] == ["tests/test_model_cli_harness.py"]
    assert strategy["groups"] == [
        {
            "id": "model-cli-harness-scores-raw-read",
            "paths": ["tests/test_model_cli_harness.py"],
            "members": [
                "test_model_cli_harness_scores_raw_read_posix",
                "test_model_cli_harness_scores_raw_read_windows",
            ],
            "group_role": "fixture-variant",
            "recommended_disposition": "merge",
            "confidence": "high",
            "explanation": (
                "Tests share a path and name prefix, and the declared strategy supports merging repeated checks; "
                "inspect setup/assertion shape before merging."
            ),
        }
    ]
    assert strategy["summary"]["high_confidence_merge_count"] == 1
    assert "Fewer than 10 high-confidence merge candidates" in strategy["summary"]["candidate_threshold_note"]
    assert {item["recommended_disposition"] for item in strategy["evidence_items"]} == {"merge"}
    assert {item["evidence_role"] for item in strategy["evidence_items"]} == {"fixture-variant"}
    assert {item["proof_owner"] for item in strategy["evidence_items"]} == {"root-orchestration"}


def test_verification_evidence_strategy_keeps_unclear_strategy_host_neutral(tmp_path: Path) -> None:
    test_file = tmp_path / "tests" / "test_widget.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text(
        """
def test_widget_handles_error():
    assert True
""".strip(),
        encoding="utf-8",
    )

    payload = verification_report_payload(target_root=tmp_path, changed_paths=["tests/test_widget.py"], task_text="")

    strategy = payload["evidence_strategy"]
    assert strategy["status"] == "unclear"
    assert strategy["strategy_basis"]["declared_strategy_state"] == "not-declared"
    assert strategy["strategy_basis"]["strategy_confidence"] == "low"
    assert strategy["evidence_items"][0]["recommended_disposition"] == "needs-human-strategy-choice"
    assert strategy["evidence_items"][0]["confidence"] == "low"
    assert "No universal testing strategy inferred." in strategy["limits"]
