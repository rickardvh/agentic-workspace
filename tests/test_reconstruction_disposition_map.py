from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = ROOT / ".agentic-workspace" / "reconstruction" / "authority-and-salvage.toml"

BASELINE_DISPOSITIONS = {"retain", "derive", "transfer", "ask", "retire"}
SOURCE_CLASSES = {
    "shared_repo_authority",
    "ignored_local_authority",
    "package_state",
    "durable_domain_state",
    "derived_projection",
    "historical_residue",
    "maintainer_local",
}
SALVAGE_DISPOSITIONS = {"PORT", "ADAPT", "EVIDENCE", "DROP"}


def load_map() -> dict[str, object]:
    return tomllib.loads(MAP_PATH.read_text(encoding="utf-8"))


def test_reconstruction_map_is_temporary_and_fail_closed() -> None:
    document = load_map()
    meta = document["meta"]
    gate = document["gate"]

    assert meta["kind"] == "agentic-workspace/reconstruction-disposition/v1"
    assert meta["temporary"] is True
    assert meta["authority"] == "disposition-only"
    assert meta["baseline"] == "82e1e79c32e6edfa02824d87845c5480ed8928bb"
    assert meta["salvage_snapshot"] == "4973f26d31951a002607455578412ad176415995"
    assert meta["salvage_commit_count"] == 36
    assert meta["retire_when"]

    assert gate["policy"] == "fail-closed"
    assert gate["destructive_ready"] is False
    assert gate["current_checkout_required"] is False
    assert "destination owners" in gate["reason"]
    assert "redacted semantic inspection" in gate["current_checkout_evidence"]
    assert "never persist" in gate["privacy_boundary"]
    assert "destructive" in gate["rule"].lower()


def test_baseline_authority_has_complete_owner_and_disposition_coverage() -> None:
    document = load_map()
    coverage = document["coverage"]
    entries = document["baseline"]
    ids = [entry["id"] for entry in entries]

    assert len(ids) == len(set(ids))
    assert set(coverage["required_areas"]) <= {entry["area"] for entry in entries}

    for entry in entries:
        assert entry["paths"]
        assert entry["source_class"] in SOURCE_CLASSES
        assert entry["authority"]
        assert entry["semantic_owner"]
        assert entry["disposition"] in BASELINE_DISPOSITIONS
        assert entry["destination"]
        assert entry["owner_issues"]
        assert all(issue.startswith("#") for issue in entry["owner_issues"])
        assert entry["evidence"]
        assert isinstance(entry["current_checkout_required"], bool)
        assert isinstance(entry["destructive_ready"], bool)
        assert entry["rationale"]

        if entry["current_checkout_required"]:
            assert "current-checkout" in entry["evidence"]
            assert entry["destructive_ready"] is False

        if entry["disposition"] == "ask":
            assert entry["current_checkout_required"] is True
            assert entry["destructive_ready"] is False

    assert any(entry["source_class"] == "shared_repo_authority" and entry["authority"] == "primary" for entry in entries)
    assert any(entry["source_class"] == "ignored_local_authority" for entry in entries)
    assert any(entry["source_class"] == "package_state" for entry in entries)
    assert any(entry["source_class"] == "durable_domain_state" for entry in entries)
    assert any(entry["source_class"] == "derived_projection" for entry in entries)
    assert any(entry["source_class"] == "historical_residue" for entry in entries)

    assert document["gate"]["destructive_ready"] is False
    unresolved = [entry["id"] for entry in entries if entry["current_checkout_required"]]
    assert unresolved == []
    assert all(entry["disposition"] != "ask" for entry in entries)


def test_baseline_map_keeps_known_primary_sources_out_of_the_retirement_bucket() -> None:
    document = load_map()
    by_id = {entry["id"]: entry for entry in document["baseline"]}

    assert by_id["system-intent-source"]["disposition"] == "retain"
    assert by_id["shared-config-core"]["disposition"] == "retain"
    assert by_id["verification-protocols"]["disposition"] == "retain"
    assert by_id["ownership-custody-ledger"]["disposition"] == "transfer"
    assert by_id["planning-history"]["disposition"] == "retire"
    assert by_id["proof-receipt-corpus"]["disposition"] == "retire"
    assert by_id["local-config-overrides"]["disposition"] == "retain"
    assert by_id["local-config-assignment-policy"]["disposition"] == "transfer"
    assert by_id["local-config-target-evidence"]["disposition"] == "transfer"
    assert by_id["local-delegation-decision-projection"]["disposition"] == "derive"
    assert by_id["local-assignment-run-history"]["destructive_ready"] is True
    assert by_id["local-assignment-conclusions"]["destructive_ready"] is False
    assert by_id["planning-current-local-state"]["destructive_ready"] is True
    assert by_id["planning-decision-point-intent-carry"]["disposition"] == "transfer"
    assert by_id["planning-decision-point-intent-carry"]["destructive_ready"] is False
    assert by_id["local-improvement-consequence-history"]["disposition"] == "transfer"
    assert by_id["maintainer-local-diagnostics"]["destructive_ready"] is True


def test_current_checkout_disposition_records_semantics_without_local_values() -> None:
    document = load_map()
    serialized = MAP_PATH.read_text(encoding="utf-8")
    current_evidence = [entry for entry in document["baseline"] if "current-checkout" in entry["evidence"]]

    assert current_evidence
    assert all(entry["current_checkout_required"] is False for entry in current_evidence)
    assert "user-local:" not in serialized
    assert ".agentic-workspace/local/logs/aw-session-" not in serialized
    assert "assignment-runs/run-" not in serialized


def test_salvage_map_covers_the_snapshot_by_component_not_by_pr() -> None:
    document = load_map()
    coverage = document["coverage"]
    entries = document["salvage"]
    ids = [entry["id"] for entry in entries]
    origin_prs = {pr for entry in entries for pr in entry["origin_prs"]}

    assert len(ids) == len(set(ids))
    assert set(coverage["snapshot_prs"]) <= origin_prs
    assert set(coverage["required_salvage_prs"]) <= origin_prs
    assert set(coverage["outside_snapshot_followups"]) <= origin_prs
    assert set(entry["disposition"] for entry in entries) == SALVAGE_DISPOSITIONS
    assert any(len(entry["origin_prs"]) > 1 for entry in entries)

    for entry in entries:
        assert entry["origin_prs"]
        assert entry["component_level"] is True
        assert entry["disposition"] in SALVAGE_DISPOSITIONS
        assert entry["current_owner"]
        assert entry["owner_issues"]
        assert all(issue.startswith("#") for issue in entry["owner_issues"])
        assert entry["reuse"]
        assert isinstance(entry["corrected_source_dependency"], bool)

        if entry["disposition"] == "PORT":
            assert entry["corrected_source_dependency"] is False
            assert entry["independent_reason"]
        elif entry["disposition"] == "DROP":
            assert entry["rejected_assumption"]
        else:
            assert entry["independent_reason"]

    outside_snapshot = {pr for entry in entries if entry.get("outside_snapshot") for pr in entry["origin_prs"]}
    assert outside_snapshot == set(coverage["outside_snapshot_followups"])


def test_salvage_false_positives_are_not_direct_ports() -> None:
    document = load_map()
    by_id = {entry["id"]: entry for entry in document["salvage"]}

    assert by_id["repo-maintainer-skills"]["disposition"] == "PORT"
    assert by_id["repo-maintainer-skills"]["corrected_source_dependency"] is False

    assert by_id["assignment-total-cost-and-bounded-return"]["disposition"] == "ADAPT"
    assert by_id["lexical-runtime-task-applicability"]["disposition"] == "DROP"
    assert by_id["wholesale-v1-contraction"]["disposition"] == "DROP"
    assert by_id["windows-lock-test-quarantine"]["disposition"] == "DROP"
    assert by_id["durability-portability-failure"]["disposition"] == "EVIDENCE"
    assert by_id["trusted-human-correction-ingress"]["disposition"] == "ADAPT"

    assert "acting agent" in by_id["lexical-runtime-task-applicability"]["rejected_assumption"]
    assert "Windows" in by_id["durable-operation-primitives"]["independent_reason"]
