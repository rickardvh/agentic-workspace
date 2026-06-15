from __future__ import annotations

import json
from datetime import date, timedelta
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
    assert payload["evidence_strategy"]["proof_governance"]["kind"] == "agentic-workspace/verification-proof-governance/v1"
    assert payload["evidence_strategy"]["proof_governance"]["status"] == "unavailable"
    assert payload["evidence_strategy"]["proof_governance"]["decision_authority"] == "agent"
    assert payload["evidence_strategy"]["proof_decision"]["kind"] == "agentic-workspace/verification-proof-decision/v1"
    assert payload["evidence_strategy"]["proof_decision"]["status"] == "missing"
    assert payload["evidence_strategy"]["proof_decision"]["decision_authority"] == "agent"


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


def test_verification_evidence_strategy_reports_candidate_strategy_sources_without_interpreting_prose(tmp_path: Path) -> None:
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
    assert strategy["status"] == "attention"
    basis = strategy["strategy_basis"]
    assert basis["declared_strategy_state"] == "partially-declared"
    assert basis["strategy_confidence"] == "low"
    assert basis["declared_strategy_sources"] == []
    assert basis["matched_strategy_signals"] == []
    assert basis["candidate_strategy_sources"] == [
        {
            "path": "docs/maintainer/testing-strategy.md",
            "source_role": "candidate-host-strategy-source",
            "authority": "uninterpreted-source",
        }
    ]
    assert "did not interpret their prose" in basis["strategy_summary"]
    assert basis["decision_questions"] == [
        "Which host-owned strategy source, if any, should govern this evidence?",
        "Do grouped tests represent one behavior class or separate regression records?",
        "What replacement evidence would be required before merging, moving, converting, or pruning evidence?",
    ]
    assert "No universal testing strategy inferred." in strategy["limits"]


def test_verification_evidence_strategy_reports_structured_strategy_hints(tmp_path: Path) -> None:
    strategy_path = tmp_path / ".agentic-workspace" / "verification" / "proof-strategy.toml"
    strategy_path.parent.mkdir(parents=True)
    strategy_path.write_text(
        """
[proof_strategy]
strategy_source = "docs/maintainer/testing-strategy.md"
ordinary_test_growth = "requires-proof-decision"
preferred_owner_vocab = ["root-orchestration", "verification-evidence"]
proof_intent_vocab = ["workflow-routing", "behavior-unchanged"]
""".strip(),
        encoding="utf-8",
    )
    test_file = tmp_path / "tests" / "test_widget.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text(
        """
def test_widget_case_regression_posix():
    assert True


def test_widget_case_regression_windows():
    assert True
""".strip(),
        encoding="utf-8",
    )

    payload = verification_report_payload(target_root=tmp_path, changed_paths=["tests/test_widget.py"], task_text="")

    strategy = payload["evidence_strategy"]
    basis = strategy["strategy_basis"]
    assert basis["declared_strategy_state"] == "declared"
    assert basis["strategy_confidence"] == "medium"
    assert basis["declared_strategy_sources"] == []
    assert basis["matched_strategy_signals"] == []
    assert basis["structured_strategy_hints"] == {
        "path": ".agentic-workspace/verification/proof-strategy.toml",
        "authority": "host-structured-config",
        "limits": [
            "Only structured enum fields are interpreted.",
            "Free-text host strategy prose remains uninterpreted.",
        ],
        "status": "present",
        "hints": {
            "strategy_source": "docs/maintainer/testing-strategy.md",
            "ordinary_test_growth": "requires-proof-decision",
            "preferred_owner_vocab": ["root-orchestration", "verification-evidence"],
            "proof_intent_vocab": ["workflow-routing", "behavior-unchanged"],
        },
        "invalid_fields": [],
    }
    assert {group["recommended_disposition"] for group in strategy["groups"]} == {"needs-human-strategy-choice"}
    assert {item["proof_owner"] for item in strategy["evidence_items"]} == {"unknown"}


def test_verification_evidence_strategy_reports_absent_structured_strategy_hints(tmp_path: Path) -> None:
    payload = verification_report_payload(target_root=tmp_path, changed_paths=[], task_text="")

    hints = payload["evidence_strategy"]["strategy_basis"]["structured_strategy_hints"]
    assert hints == {
        "path": ".agentic-workspace/verification/proof-strategy.toml",
        "authority": "host-structured-config",
        "limits": [
            "Only structured enum fields are interpreted.",
            "Free-text host strategy prose remains uninterpreted.",
        ],
        "status": "absent",
        "hints": {},
        "invalid_fields": [],
    }


def test_verification_evidence_strategy_reports_partial_structured_strategy_hints(tmp_path: Path) -> None:
    strategy_path = tmp_path / ".agentic-workspace" / "verification" / "proof-strategy.toml"
    strategy_path.parent.mkdir(parents=True)
    strategy_path.write_text(
        """
[proof_strategy]
ordinary_test_growth = "discouraged"
preferred_owner_vocab = ["verification-evidence"]
""".strip(),
        encoding="utf-8",
    )

    payload = verification_report_payload(target_root=tmp_path, changed_paths=[], task_text="")

    basis = payload["evidence_strategy"]["strategy_basis"]
    assert basis["declared_strategy_state"] == "partially-declared"
    assert basis["strategy_confidence"] == "low"
    assert basis["structured_strategy_hints"]["status"] == "present"
    assert basis["structured_strategy_hints"]["hints"]["strategy_source"] == ""


def test_verification_evidence_strategy_reports_source_only_strategy_hints_as_partial(tmp_path: Path) -> None:
    strategy_path = tmp_path / ".agentic-workspace" / "verification" / "proof-strategy.toml"
    strategy_path.parent.mkdir(parents=True)
    strategy_path.write_text(
        """
[proof_strategy]
strategy_source = "docs/maintainer/testing-strategy.md"
""".strip(),
        encoding="utf-8",
    )

    payload = verification_report_payload(target_root=tmp_path, changed_paths=[], task_text="")

    basis = payload["evidence_strategy"]["strategy_basis"]
    assert basis["declared_strategy_state"] == "partially-declared"
    assert basis["strategy_confidence"] == "low"
    assert basis["structured_strategy_hints"]["hints"]["ordinary_test_growth"] == "unknown"


def test_verification_evidence_strategy_reports_invalid_structured_strategy_hints(tmp_path: Path) -> None:
    strategy_path = tmp_path / ".agentic-workspace" / "verification" / "proof-strategy.toml"
    strategy_path.parent.mkdir(parents=True)
    strategy_path.write_text(
        """
[proof_strategy]
ordinary_test_growth = "always-add"
preferred_owner_vocab = ["invented-owner"]
proof_intent_vocab = ["coverage-quota"]
""".strip(),
        encoding="utf-8",
    )

    payload = verification_report_payload(target_root=tmp_path, changed_paths=[], task_text="")

    basis = payload["evidence_strategy"]["strategy_basis"]
    assert basis["declared_strategy_state"] == "not-declared"
    assert basis["strategy_confidence"] == "unclear"
    assert basis["structured_strategy_hints"]["status"] == "invalid"
    assert set(basis["structured_strategy_hints"]["invalid_fields"]) == {
        "ordinary_test_growth",
        "preferred_owner_vocab",
        "proof_intent_vocab",
    }


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
    assert strategy["status"] == "attention"
    assert strategy["summary"]["ordinary_tests_touched"] == 2
    assert strategy["summary"]["hotspot_files_touched"] == []
    assert strategy["groups"] == [
        {
            "id": "model-cli-harness-scores-raw-read",
            "paths": ["tests/test_model_cli_harness.py"],
            "members": [
                "test_model_cli_harness_scores_raw_read_posix",
                "test_model_cli_harness_scores_raw_read_windows",
            ],
            "group_role": "fixture-variant",
            "recommended_disposition": "needs-human-strategy-choice",
            "confidence": "low",
            "explanation": (
                "Tests share a path and name prefix. Verification surfaces this as a review question; "
                "the agent must decide whether the host strategy supports merging."
            ),
            "decision_questions": [
                "Does this group represent one behavior class or separate regression records?",
                "Which member labels or historical facts must remain visible if this evidence is rewritten?",
                "What replacement evidence would make it safe to merge, move, convert, or prune this group?",
                "Which host-owned source should the agent read before deciding?",
            ],
        }
    ]
    assert strategy["summary"]["high_confidence_merge_count"] == 0
    assert "does not assign high-confidence merge" in strategy["summary"]["candidate_threshold_note"]
    assert {item["recommended_disposition"] for item in strategy["evidence_items"]} == {"needs-human-strategy-choice"}
    assert {item["evidence_role"] for item in strategy["evidence_items"]} == {"fixture-variant"}
    assert {item["proof_owner"] for item in strategy["evidence_items"]} == {"unknown"}
    assert {tuple(item["decision_questions"]) for item in strategy["evidence_items"]} == {
        (
            "What behavior claim does this evidence item currently preserve?",
            "Is this executable proof, historical regression knowledge, or both?",
            "Which owner should carry this evidence if the test is moved or retired?",
            "What replacement evidence must exist before changing this item?",
        )
    }
    assert strategy["inventory_review"]["test_file_summaries"] == [
        {
            "path": "tests/test_model_cli_harness.py",
            "test_function_count": 2,
            "grouped_test_function_count": 2,
            "helper_call_count": 2,
            "assertion_count": 2,
            "review_questions": [
                "Which inventory row or host-owned source should the agent read for this file?",
                "Which behavior classes in this file are worth preserving as executable proof?",
                "Which historical regression facts should move to a non-executable record?",
                "What smaller proof surface should own stable behavior after migration?",
            ],
        }
    ]
    governance = strategy["proof_governance"]
    assert governance["status"] == "attention"
    assert governance["decision_authority"] == "agent"
    assert governance["available_decisions"] == [
        "add",
        "merge",
        "convert-to-conformance",
        "record-manual-evidence",
        "prune",
        "no-new-proof-needed",
        "needs-human-strategy-choice",
    ]
    assert governance["candidate_context"] == {
        "changed_path_count": 1,
        "ordinary_test_function_count": 2,
        "group_count": 1,
        "candidate_strategy_source_count": 1,
        "verification_manifest_configured": False,
        "task_text_present": True,
    }
    assert governance["pre_test_decision_questions"] == [
        "What host-repo testing or proof strategy applies to this surface?",
        "What trust question is being answered?",
        "What is the narrowest evidence that answers it under that strategy?",
        "Which owner should hold the evidence?",
        "Is this proof permanent, temporary, or replaceable by a host-preferred proof surface?",
        "What would make it safe to prune later?",
    ]
    assert governance["agent_decision_template"] == {
        "selected_decision": "unset-agent-owned",
        "trust_question": "unset-agent-owned",
        "proof_intent": "unset-agent-owned",
        "narrowest_evidence": "unset-agent-owned",
        "evidence_owner": "unset-agent-owned",
        "durability": "unset-agent-owned",
        "safe_to_prune_when": "unset-agent-owned",
    }
    assert "No decision is assigned by Verification." in governance["limits"]


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
    assert strategy["status"] == "attention"
    assert strategy["strategy_basis"]["declared_strategy_state"] == "not-declared"
    assert strategy["strategy_basis"]["strategy_confidence"] == "low"
    assert strategy["evidence_items"][0]["recommended_disposition"] == "needs-human-strategy-choice"
    assert strategy["evidence_items"][0]["confidence"] == "low"
    assert "No universal testing strategy inferred." in strategy["limits"]
    governance = strategy["proof_governance"]
    assert governance["status"] == "attention"
    assert governance["candidate_context"]["candidate_strategy_source_count"] == 0
    assert governance["agent_decision_template"]["selected_decision"] == "unset-agent-owned"
    assert "No host strategy is inferred from prose." in governance["limits"]


def test_verification_evidence_strategy_does_not_force_merge_for_different_host_strategy_prose(tmp_path: Path) -> None:
    strategy_doc = tmp_path / "docs" / "maintainer" / "testing-strategy.md"
    strategy_doc.parent.mkdir(parents=True)
    strategy_doc.write_text(
        """
# Testing Strategy

This repository keeps one test per regression record so incident history stays
auditable. Do not merge unrelated regression records just because they share
fixtures or assertion shape.
""".strip(),
        encoding="utf-8",
    )
    test_file = tmp_path / "tests" / "test_widget.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text(
        """
def test_widget_case_regression_posix():
    assert True


def test_widget_case_regression_windows():
    assert True
""".strip(),
        encoding="utf-8",
    )

    payload = verification_report_payload(target_root=tmp_path, changed_paths=["tests/test_widget.py"], task_text="")

    strategy = payload["evidence_strategy"]
    assert strategy["strategy_basis"]["declared_strategy_sources"] == []
    assert strategy["strategy_basis"]["matched_strategy_signals"] == []
    assert strategy["strategy_basis"]["candidate_strategy_sources"] == [
        {
            "path": "docs/maintainer/testing-strategy.md",
            "source_role": "candidate-host-strategy-source",
            "authority": "uninterpreted-source",
        }
    ]
    assert {group["recommended_disposition"] for group in strategy["groups"]} == {"needs-human-strategy-choice"}
    assert {item["recommended_disposition"] for item in strategy["evidence_items"]} == {"needs-human-strategy-choice"}
    assert strategy["summary"]["high_confidence_merge_count"] == 0


def test_verification_evidence_strategy_surfaces_test_knowledge_inventory_without_interpreting_it(
    tmp_path: Path,
) -> None:
    inventory_doc = tmp_path / "docs" / "maintainer" / "test-knowledge-inventory.md"
    inventory_doc.parent.mkdir(parents=True)
    inventory_doc.write_text(
        """
# Test Knowledge Inventory

This host keeps one executable test for every incident record until a human
maintainer explicitly migrates that knowledge elsewhere.
""".strip(),
        encoding="utf-8",
    )
    test_file = tmp_path / "tests" / "test_widget.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text(
        """
def test_widget_case_regression_posix():
    assert True


def test_widget_case_regression_windows():
    assert True
""".strip(),
        encoding="utf-8",
    )

    payload = verification_report_payload(target_root=tmp_path, changed_paths=["tests/test_widget.py"], task_text="")

    strategy = payload["evidence_strategy"]
    assert strategy["strategy_basis"]["candidate_strategy_sources"] == [
        {
            "path": "docs/maintainer/test-knowledge-inventory.md",
            "source_role": "candidate-test-knowledge-inventory",
            "authority": "uninterpreted-source",
        }
    ]
    assert strategy["strategy_basis"]["declared_strategy_sources"] == []
    assert strategy["strategy_basis"]["matched_strategy_signals"] == []
    assert strategy["inventory_review"]["candidate_inventory_sources"] == [
        {
            "path": "docs/maintainer/test-knowledge-inventory.md",
            "source_role": "candidate-test-knowledge-inventory",
            "authority": "uninterpreted-source",
        }
    ]
    assert {group["recommended_disposition"] for group in strategy["groups"]} == {"needs-human-strategy-choice"}
    assert {item["proof_owner"] for item in strategy["evidence_items"]} == {"unknown"}


def test_verification_regression_sprawl_reports_changed_test_facts(tmp_path: Path) -> None:
    test_file = tmp_path / "tests" / "test_command_output.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text(
        """
def test_command_output_payload_case_posix():
    result = {"stdout": "ok"}
    assert result["stdout"] == "ok"


def test_command_output_payload_case_windows():
    result = {"stdout": "warn"}
    assert "warn" in result["stdout"]
""".strip(),
        encoding="utf-8",
    )

    payload = verification_report_payload(
        target_root=tmp_path,
        changed_paths=["tests/test_command_output.py"],
        task_text="reduce regression sprawl",
    )

    sprawl = payload["evidence_strategy"]["regression_sprawl"]
    assert sprawl["kind"] == "agentic-workspace/verification-regression-sprawl/v1"
    assert sprawl["status"] == "attention"
    assert sprawl["authority"] == "diagnostic-facts"
    assert sprawl["test_files_touched"] == ["tests/test_command_output.py"]
    assert sprawl["deleted_or_missing_test_files"] == []
    assert sprawl["ordinary_test_function_count"] == 2
    assert sprawl["likely_fixture_variant_group_count"] == 1
    assert sprawl["generated_output_assertion_count"] == 2
    assert sprawl["proof_decision_status"] == "missing"
    assert sprawl["missing_or_incomplete_proof_decision"] is True
    assert "No deletion, merge, or conformance conversion is recommended by this diagnostic." in sprawl["limits"]


def test_verification_regression_sprawl_reports_deleted_or_missing_test_paths(tmp_path: Path) -> None:
    payload = verification_report_payload(
        target_root=tmp_path,
        changed_paths=["tests/test_removed_regression.py"],
        task_text="remove legacy regression",
    )

    sprawl = payload["evidence_strategy"]["regression_sprawl"]
    assert sprawl["test_files_touched"] == ["tests/test_removed_regression.py"]
    assert sprawl["deleted_or_missing_test_files"] == ["tests/test_removed_regression.py"]
    assert sprawl["ordinary_test_function_count"] == 0


def test_verification_regression_sprawl_reports_present_proof_decision(tmp_path: Path) -> None:
    decision_path = tmp_path / ".agentic-workspace" / "verification" / "proof-decision.json"
    decision_path.parent.mkdir(parents=True)
    decision_path.write_text(
        json.dumps(
            {
                "selected_decision": "prune",
                "trust_question": "Is the removed legacy regression covered elsewhere?",
                "host_strategy_source": "docs/verification.md",
                "proof_owner": "verification-evidence",
                "proof_intent": "migration-residue",
                "evidence_durability": "permanent",
                "narrowest_evidence": "A retained conformance-owned scenario.",
                "prune_or_replacement_condition": "Equivalent coverage is recorded.",
                "confidence": "medium",
                "residual_risk": "Replacement evidence may still need human review.",
            }
        ),
        encoding="utf-8",
    )

    payload = verification_report_payload(
        target_root=tmp_path,
        changed_paths=["tests/test_removed_regression.py"],
        task_text="remove legacy regression",
    )

    sprawl = payload["evidence_strategy"]["regression_sprawl"]
    assert sprawl["proof_decision_status"] == "present"
    assert sprawl["missing_or_incomplete_proof_decision"] is False


def test_verification_proof_decision_reports_complete_agent_authored_record(tmp_path: Path) -> None:
    decision_path = tmp_path / ".agentic-workspace" / "verification" / "proof-decision.json"
    decision_path.parent.mkdir(parents=True)
    decision_path.write_text(
        json.dumps(
            {
                "proof_decision": {
                    "selected_decision": "add",
                    "trust_question": "Does the new report field preserve host-neutral proof governance?",
                    "host_strategy_source": "docs/verification.md",
                    "proof_owner": "verification-evidence",
                    "proof_intent": "workflow-routing",
                    "evidence_durability": "permanent",
                    "narrowest_evidence": "Verification runtime primitive tests.",
                    "prune_or_replacement_condition": "A schema-owned conformance case replaces the runtime test.",
                    "confidence": "medium",
                    "residual_risk": "Closeout surfaces do not consume the decision yet.",
                }
            }
        ),
        encoding="utf-8",
    )

    payload = verification_report_payload(target_root=tmp_path, changed_paths=[], task_text="")

    decision = payload["evidence_strategy"]["proof_decision"]
    assert decision["status"] == "present"
    assert decision["authority"] == "agent-authored"
    assert decision["missing_fields"] == []
    assert decision["invalid_fields"] == []
    assert decision["decision"]["selected_decision"] == "add"
    assert decision["lifecycle"]["state"] == "permanent"
    assert decision["lifecycle"]["review_needed"] is False


def test_verification_proof_decision_reports_current_temporary_lifecycle(tmp_path: Path) -> None:
    decision_path = tmp_path / ".agentic-workspace" / "verification" / "proof-decision.json"
    decision_path.parent.mkdir(parents=True)
    decision_path.write_text(
        json.dumps(
            {
                "selected_decision": "record-manual-evidence",
                "trust_question": "Does the temporary evidence cover the migration window?",
                "host_strategy_source": "docs/verification.md",
                "proof_owner": "verification-evidence",
                "proof_intent": "temporary-characterization",
                "evidence_durability": "temporary",
                "narrowest_evidence": "Short-lived manual record.",
                "prune_or_replacement_condition": "Replace when the contract proof lands.",
                "confidence": "low",
                "residual_risk": "Temporary evidence may go stale.",
                "retention_until": (date.today() + timedelta(days=7)).isoformat(),
                "stale_when": ["src/**"],
                "replacement_owner": "conformance-contract",
                "review_trigger": "Before retiring the temporary proof.",
            }
        ),
        encoding="utf-8",
    )

    payload = verification_report_payload(target_root=tmp_path, changed_paths=["docs/verification.md"], task_text="")

    lifecycle = payload["evidence_strategy"]["proof_decision"]["lifecycle"]
    assert lifecycle["state"] == "current"
    assert lifecycle["review_needed"] is False
    assert lifecycle["replacement_owner"] == "conformance-contract"
    assert lifecycle["review_trigger"] == "Before retiring the temporary proof."


def test_verification_proof_decision_reports_stale_replaceable_lifecycle(tmp_path: Path) -> None:
    decision_path = tmp_path / ".agentic-workspace" / "verification" / "proof-decision.json"
    decision_path.parent.mkdir(parents=True)
    decision_path.write_text(
        json.dumps(
            {
                "selected_decision": "add",
                "trust_question": "Does replaceable evidence cover the current adapter shape?",
                "host_strategy_source": "docs/verification.md",
                "proof_owner": "verification-evidence",
                "proof_intent": "temporary-characterization",
                "evidence_durability": "replaceable",
                "narrowest_evidence": "Focused runtime primitive test.",
                "prune_or_replacement_condition": "Replace with protocol conformance.",
                "confidence": "medium",
                "residual_risk": "Adapter changes can stale it.",
                "stale_when": ["packages/verification/src/**"],
            }
        ),
        encoding="utf-8",
    )

    payload = verification_report_payload(
        target_root=tmp_path,
        changed_paths=["packages/verification/src/repo_verification_bootstrap/runtime_primitives.py"],
        task_text="",
    )

    lifecycle = payload["evidence_strategy"]["proof_decision"]["lifecycle"]
    assert lifecycle["state"] == "stale"
    assert lifecycle["review_needed"] is True
    assert lifecycle["stale_because"] == ["changed path matched packages/verification/src/**"]


def test_verification_proof_decision_reports_expired_temporary_lifecycle(tmp_path: Path) -> None:
    decision_path = tmp_path / ".agentic-workspace" / "verification" / "proof-decision.json"
    decision_path.parent.mkdir(parents=True)
    decision_path.write_text(
        json.dumps(
            {
                "selected_decision": "record-manual-evidence",
                "trust_question": "Was the temporary proof still inside its retention window?",
                "host_strategy_source": "docs/verification.md",
                "proof_owner": "verification-evidence",
                "proof_intent": "temporary-characterization",
                "evidence_durability": "temporary",
                "narrowest_evidence": "Temporary review note.",
                "prune_or_replacement_condition": "Expires after migration.",
                "confidence": "low",
                "residual_risk": "Expired evidence cannot support closeout alone.",
                "retention_until": (date.today() - timedelta(days=1)).isoformat(),
            }
        ),
        encoding="utf-8",
    )

    payload = verification_report_payload(target_root=tmp_path, changed_paths=[], task_text="")

    lifecycle = payload["evidence_strategy"]["proof_decision"]["lifecycle"]
    assert lifecycle["state"] == "expired"
    assert lifecycle["review_needed"] is True


def test_verification_proof_decision_reports_invalid_lifecycle_date(tmp_path: Path) -> None:
    decision_path = tmp_path / ".agentic-workspace" / "verification" / "proof-decision.json"
    decision_path.parent.mkdir(parents=True)
    decision_path.write_text(
        json.dumps(
            {
                "selected_decision": "record-manual-evidence",
                "trust_question": "Was the temporary proof date valid?",
                "host_strategy_source": "docs/verification.md",
                "proof_owner": "verification-evidence",
                "proof_intent": "temporary-characterization",
                "evidence_durability": "temporary",
                "narrowest_evidence": "Temporary review note.",
                "prune_or_replacement_condition": "Expires after migration.",
                "confidence": "low",
                "residual_risk": "Bad dates hide lifecycle state.",
                "retention_until": "soon",
            }
        ),
        encoding="utf-8",
    )

    payload = verification_report_payload(target_root=tmp_path, changed_paths=[], task_text="")

    decision = payload["evidence_strategy"]["proof_decision"]
    assert decision["status"] == "invalid"
    assert decision["lifecycle"]["state"] == "invalid"
    assert decision["lifecycle"]["invalid_fields"] == ["retention_until"]


def test_verification_proof_decision_reports_incomplete_record_without_inference(tmp_path: Path) -> None:
    decision_path = tmp_path / ".agentic-workspace" / "verification" / "proof-decision.json"
    decision_path.parent.mkdir(parents=True)
    decision_path.write_text(
        json.dumps(
            {
                "selected_decision": "merge",
                "trust_question": "Can two regression rows become one scenario matrix?",
            }
        ),
        encoding="utf-8",
    )

    payload = verification_report_payload(target_root=tmp_path, changed_paths=[], task_text="")

    decision = payload["evidence_strategy"]["proof_decision"]
    assert decision["status"] == "incomplete"
    assert "proof_owner" in decision["missing_fields"]
    assert decision["invalid_fields"] == []
    assert "No missing field is inferred" in decision["limits"][1]


def test_verification_proof_decision_reports_invalid_enums(tmp_path: Path) -> None:
    decision_path = tmp_path / ".agentic-workspace" / "verification" / "proof-decision.json"
    decision_path.parent.mkdir(parents=True)
    decision_path.write_text(
        json.dumps(
            {
                "selected_decision": "auto-delete",
                "trust_question": "Question",
                "host_strategy_source": "docs/strategy.md",
                "proof_owner": "magic-owner",
                "proof_intent": "unknown",
                "evidence_durability": "forever",
                "narrowest_evidence": "Evidence",
                "prune_or_replacement_condition": "Condition",
                "confidence": "certain",
                "residual_risk": "Risk",
            }
        ),
        encoding="utf-8",
    )

    payload = verification_report_payload(target_root=tmp_path, changed_paths=[], task_text="")

    decision = payload["evidence_strategy"]["proof_decision"]
    assert decision["status"] == "invalid"
    assert set(decision["invalid_fields"]) == {
        "selected_decision",
        "proof_owner",
        "evidence_durability",
        "confidence",
    }
