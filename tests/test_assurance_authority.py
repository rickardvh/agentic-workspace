from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from repo_verification_bootstrap.runtime_primitives import verification_report_payload

from agentic_workspace.assurance_authority import (
    APPLICATION_KIND,
    AUTHORITY_KIND,
    DECISION_KIND,
    EVIDENCE_KIND,
    admit_external_evidence,
    admit_repository_assurance_decision,
    build_assurance_application,
    evaluate_assurance_disposition,
)
from agentic_workspace.config import WorkspaceUsageError, load_workspace_config
from agentic_workspace.operating_decision import compile_operating_decision
from agentic_workspace.proof_subject import PROOF_SUBJECT_KIND


def _subject(*, fingerprint: str = "a" * 64, paths: tuple[str, ...] = ("src/a.py",)) -> dict[str, object]:
    return {
        "kind": PROOF_SUBJECT_KIND,
        "fingerprint": fingerprint,
        "identity_complete": True,
        "claim_classes": ["executable-validation"],
        "source_inputs": [{"path": path, "sha256": "b" * 64} for path in paths],
    }


def _candidate(subject: dict[str, object]) -> dict[str, object]:
    return {
        "kind": EVIDENCE_KIND,
        "producer_id": "ci/acme",
        "transport_id": "github-api",
        "proof_route": "unit",
        "evidence_class": "test-result",
        "result_contract": "pytest/v1",
        "result": "passed",
        "evidence_ref": "https://ci.example/runs/42",
        "proof_subject": subject,
    }


def _authority(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "kind": AUTHORITY_KIND,
        "id": "acme-unit",
        "producer_id": "ci/acme",
        "proof_route": "unit",
        "evidence_class": "test-result",
        "result_contract": "pytest/v1",
        "allowed_results": ["passed", "failed"],
    }
    value.update(overrides)
    return value


def test_application_identity_is_stable_for_irrelevant_context() -> None:
    first = build_assurance_application(
        requirement_id="safety", classification_owner="repo", source_revision="sha256:1", applicability_input={"path": "src/a.py"}
    )
    second = build_assurance_application(
        requirement_id="safety", classification_owner="repo", source_revision="sha256:1", applicability_input={"path": "src/a.py"}
    )
    assert first["kind"] == APPLICATION_KIND
    assert first["application_id"] == second["application_id"]
    assert first["status"] == "current"


def test_application_identity_changes_with_source_or_scope() -> None:
    base = build_assurance_application(
        requirement_id="safety", classification_owner="repo", source_revision="sha256:1", applicability_input={"path": "src/a.py"}
    )
    changed = build_assurance_application(
        requirement_id="safety", classification_owner="repo", source_revision="sha256:2", applicability_input={"path": "src/a.py"}
    )
    assert base["application_id"] != changed["application_id"]


def test_repository_decision_is_revision_bound_and_cannot_widen_authority() -> None:
    candidate = {
        "kind": DECISION_KIND,
        "classification_owner": "repo",
        "source_revision": "sha256:source",
        "input_revision": "sha256:input",
        "complete": True,
        "requirements": [{"id": "safety", "applicability_input": {"path": "src/a.py"}}],
    }
    admitted = admit_repository_assurance_decision(
        candidate=candidate,
        configured_owner="repo",
        expected_source_revision="sha256:source",
        expected_input_revision="sha256:input",
    )
    assert admitted["status"] == "admitted"
    assert admitted["applications"][0]["application_id"]
    denied = admit_repository_assurance_decision(
        candidate={**candidate, "authority_effects": ["waive-proof"]},
        configured_owner="repo",
        expected_source_revision="sha256:source",
        expected_input_revision="sha256:input",
    )
    assert denied["status"] == "blocked"
    assert "authority-widening-denied" in denied["reason_codes"]


def test_repository_decision_distinguishes_owner_conflict_and_staleness() -> None:
    result = admit_repository_assurance_decision(
        candidate={
            "kind": DECISION_KIND,
            "classification_owner": "other",
            "source_revision": "old",
            "input_revision": "old",
            "complete": True,
            "requirements": [],
        },
        configured_owner="repo",
        expected_source_revision="new",
        expected_input_revision="new",
    )
    assert result["reason_codes"] == ["classification-owner-conflict", "decision-input-stale", "decision-source-stale"]


def test_operating_decision_projects_admitted_assurance_and_blocks_stale_input() -> None:
    candidate = {
        "kind": DECISION_KIND,
        "classification_owner": "repo",
        "source_revision": "source-current",
        "input_revision": "input-current",
        "complete": True,
        "requirements": [{"id": "safety", "applicability_input": {"path": "src/a.py"}}],
    }
    admitted = compile_operating_decision(
        inputs={
            "assurance_decision": candidate,
            "assurance_classification_owner": "repo",
            "assurance_source_revision": "source-current",
            "assurance_input_revision": "input-current",
        }
    )
    assert admitted["assurance"]["status"] == "admitted"
    assert admitted["status"] == "terminal"
    stale = compile_operating_decision(
        inputs={
            "assurance_decision": candidate,
            "assurance_classification_owner": "repo",
            "assurance_source_revision": "source-current",
            "assurance_input_revision": "input-new",
        }
    )
    assert stale["assurance"]["status"] == "blocked"
    assert stale["external_blocker"]["owner"] == "repo"


def test_strict_policy_reactivates_legacy_disposition_for_migration() -> None:
    application = build_assurance_application(
        requirement_id="safety", classification_owner="repo", source_revision="r1", applicability_input={"path": "src/a.py"}
    )
    result = evaluate_assurance_disposition(
        disposition={"reason": "accepted", "owner": "security"}, application=application, strict_policy=True
    )
    assert result == {
        "status": "migration-required",
        "requirement_active": True,
        "reason_codes": ["legacy-unbounded-disposition"],
    }


def test_disposition_reactivates_when_application_changes_or_review_is_due() -> None:
    application = build_assurance_application(
        requirement_id="safety", classification_owner="repo", source_revision="r2", applicability_input={"path": "src/a.py"}
    )
    result = evaluate_assurance_disposition(
        disposition={
            "applicability": {
                "application_id": "assurance-application:old",
                "review_after": "2026-01-01T00:00:00Z",
            }
        },
        application=application,
        now=datetime(2026, 8, 20, tzinfo=timezone.utc),
    )
    assert result["status"] == "inactive"
    assert result["requirement_active"] is True
    assert result["reason_codes"] == ["application-changed", "disposition-review-required"]


def test_external_evidence_admission_is_idempotent_and_keeps_result_separate() -> None:
    subject = _subject()
    first = admit_external_evidence(candidate=_candidate(subject), authorities=[_authority()], current_proof_subject=subject)
    second = admit_external_evidence(candidate=_candidate(subject), authorities=[_authority()], current_proof_subject=subject)
    assert first["status"] == "admitted"
    assert first["admission_id"] == second["admission_id"]
    assert first["producer_result"] == "passed"
    assert first["claim_authority"] == "none"


def test_external_evidence_fails_closed_for_unauthorized_or_stale_subject() -> None:
    subject = _subject()
    unauthorized = admit_external_evidence(candidate=_candidate(subject), authorities=[], current_proof_subject=subject)
    assert "producer-unauthorized" in unauthorized["reason_codes"]
    stale = admit_external_evidence(
        candidate=_candidate(subject),
        authorities=[_authority()],
        current_proof_subject=_subject(fingerprint="c" * 64),
    )
    assert "proof-subject-stale" in stale["reason_codes"]


def test_transport_cannot_self_authorize() -> None:
    subject = _subject()
    candidate = {**_candidate(subject), "transport_id": "ci/acme"}
    result = admit_external_evidence(candidate=candidate, authorities=[_authority()], current_proof_subject=subject)
    assert "transport-self-authorization-denied" in result["reason_codes"]


def test_workspace_config_loads_bounded_disposition_applicability(tmp_path: Path) -> None:
    config_dir = tmp_path / ".agentic-workspace"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text(
        """
schema_version = 1
[assurance.requirements.safety]
level = "high"
force = "blocking"
applies_to_paths = ["src/**"]
[assurance.requirements.safety.waiver]
reason = "accepted for this application"
owner = "security"
[assurance.requirements.safety.waiver.applicability]
application_id = "assurance-application:123"
source_revision = "sha256:abc"
review_after = "2027-01-01T00:00:00Z"
""".strip(),
        encoding="utf-8",
    )
    config = load_workspace_config(target_root=tmp_path)
    assert config.assurance.requirements[0].waiver is not None
    assert config.assurance.requirements[0].waiver.applicability["source_revision"] == "sha256:abc"


def test_workspace_config_requires_one_explicit_repository_classifier_source(tmp_path: Path) -> None:
    config_dir = tmp_path / ".agentic-workspace"
    config_dir.mkdir()
    config_path = config_dir / "config.toml"
    config_path.write_text('schema_version = 1\n[assurance]\nclassification_owner = "repository-owned"\n', encoding="utf-8")
    with pytest.raises(WorkspaceUsageError, match="classification_source is required"):
        load_workspace_config(target_root=tmp_path)
    config_path.write_text(
        'schema_version = 1\n[assurance]\nclassification_owner = "repository-owned"\nclassification_source = "tools/classify.py"\n',
        encoding="utf-8",
    )
    config = load_workspace_config(target_root=tmp_path)
    assert config.assurance.classification_owner == "repository-owned"
    assert config.assurance.classification_source == "tools/classify.py"


def test_verification_manifest_projects_queryable_evidence_authority(tmp_path: Path) -> None:
    manifest = tmp_path / ".agentic-workspace" / "verification" / "manifest.toml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        """
schema_version = "agentic-workspace/verification-manifest/v1"
[protocols.unit]
title = "Unit"
purpose = "Run unit proof"
applies_to_paths = ["src/**"]
review_owner = "maintainers"
[proof_routes.unit]
protocol_refs = ["unit"]
commands = ["pytest"]
[evidence_authorities.acme]
producer_id = "ci/acme"
proof_route = "unit"
evidence_class = "test-result"
result_contract = "pytest/v1"
allowed_results = ["passed", "failed"]
""".strip(),
        encoding="utf-8",
    )
    report = verification_report_payload(target_root=tmp_path)
    assert report["evidence_authority_count"] == 1
    assert report["evidence_authorities"][0]["producer_id"] == "ci/acme"
