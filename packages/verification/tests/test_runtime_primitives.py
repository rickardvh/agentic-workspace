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
