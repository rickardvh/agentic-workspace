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
