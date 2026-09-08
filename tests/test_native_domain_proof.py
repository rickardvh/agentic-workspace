"""Current config command candidates use the existing native Verification owner."""

from __future__ import annotations

import json
import os
import tomllib
from pathlib import Path

import pytest
from tests.test_native_public_cli import ROOT, consume
from tests.test_native_public_cli import native_cli as native_cli


def config(root: Path, command: str, extra: str = "") -> Path:
    source = root / ".agentic-workspace/config.toml"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(
        'schema_version=1\n[assurance.domain_proof_lanes.current]\npurpose="Current bounded check"\napplies_to_paths=["a.txt"]\ncommands=['
        + json.dumps(command)
        + ']\nmanual_evidence=["domain-review"]\nclaim_boundary="Command success is not domain acceptance"\n'
        + extra
    )
    (root / "a.txt").write_text("current")
    return source


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_domain_source_executes_without_claim_and_rejects_drift(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    command = "Add-Content count.txt executed" if os.name == "nt" else "echo executed >> count.txt"
    source = config(tmp_path, command, 'authority_refs=["rules.md"]\n')
    (tmp_path / "rules.md").write_text("current rule")
    context = {"target": str(tmp_path), "task": "Check the current source", "changed": ["a.txt"]}

    def call(value):
        return consume(surface, shared_core_binary, native_cli, value, host_path=os.environ["PATH"])

    first = call(context)
    verification = first["verification"]
    assert verification["domain_proof_candidates"]["lanes"][0]["applicability"] == "path-matched"
    assert "domain:current" not in verification["strategy"]["proof_routes"]
    request = verification["execution_requests"][0]
    assert request["arguments"] == {"route_id": "domain:current", "command": command}
    chosen = call({**context, "request": request})
    assert chosen["verification"]["strategy"]["proof_routes"]["domain:current"]["manual_evidence"] == ["domain-review"]
    invocation = chosen["decision_packet"]["primary_action"]
    assert invocation["operation_id"] == "proof.report"
    result = call({**context, "invocation": invocation})
    assert result["value"]["process"]["status"] == "passed"
    assert result["value"]["claim_boundary"]["completion_claim_allowed"] is False
    assert call({**context, "invocation": invocation})["value"] == result["value"]
    assert (tmp_path / "count.txt").read_text().splitlines() == ["executed"]
    unrelated = call({**context, "changed": ["other.txt"], "task": "Different work"})
    assert unrelated["verification"]["execution_requests"] == []
    assert unrelated["verification"]["domain_proof_candidates"]["lanes"] == []
    stale = call({**context, "task": "Another requested outcome", "request": request})
    assert "verification-request-stale" in stale["verification"]["evidence_gaps"]
    assert stale["verification"]["contribution"]["actions"] == []
    (tmp_path / "rules.md").write_text("changed rule")
    with pytest.raises(AssertionError, match="stale"):
        call({**context, "invocation": invocation})
    source.write_text(source.read_text().replace("domain-review", "stronger-domain-review"))
    with pytest.raises(AssertionError, match="stale"):
        call({**context, "request": request})
    with pytest.raises(AssertionError, match="stale"):
        call({**context, "invocation": invocation})
    assert (tmp_path / "count.txt").read_text().splitlines() == ["executed"]
    (tmp_path / ".agentic-workspace/config.local.toml").write_text("schema_version=1\n[safety]\nsafe_to_auto_run_commands=false\n")
    current_request = call(context)["verification"]["execution_requests"][0]
    blocked = call({**context, "request": current_request})
    assert blocked["decision_packet"]["status"] != "ready"
    assert (tmp_path / "count.txt").read_text().splitlines() == ["executed"]


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_real_domain_lane_and_semantic_only_scope_stay_source_owned(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    source = tmp_path / ".agentic-workspace/config.toml"
    source.parent.mkdir()
    # Preserve the exact real lane declaration without unrelated repo-local ADR pins.
    text = (ROOT / ".agentic-workspace/config.toml").read_text()
    start = text.index("[assurance.domain_proof_lanes.proof_subject_owner]")
    end = text.index("\n[", start + 1)
    source.write_text("schema_version=1\n" + text[start:end])
    current = tomllib.loads(source.read_text())["assurance"]["domain_proof_lanes"]["proof_subject_owner"]
    result = consume(
        surface,
        shared_core_binary,
        native_cli,
        {"target": str(tmp_path), "task": "Inspect proof owner", "changed": ["crates/agentic-workspace-core/src/proof_publication.rs"]},
        host_path=os.environ["PATH"],
    )
    candidates = result["verification"]["domain_proof_candidates"]["lanes"]
    assert any(row["route_id"] == "domain:proof_subject_owner" and row["command_count"] == len(current["commands"]) for row in candidates)
    assert not (tmp_path / ".agentic-workspace/local").exists()
    source.write_text(
        'schema_version=1\n[assurance.domain_proof_lanes.semantic]\npurpose="Semantic scope"\napplies_to_task_markers=["proof"]\ncommands=["echo candidate"]\n'
    )
    unrelated = consume(surface, shared_core_binary, native_cli, {"target": str(tmp_path), "task": "proof", "changed": ["other.txt"]})
    assert unrelated["verification"]["execution_requests"] == []
    assert unrelated["verification"]["domain_proof_candidates"]["lanes"][0]["applicability"] == "current-task-judgment-unresolved"


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_domain_discovery_packet_is_bounded(tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str) -> None:
    source = config(tmp_path, "echo current")
    with source.open("a") as stream:
        for index in range(40):
            stream.write(
                f'\n[assurance.domain_proof_lanes.lane{index:02d}]\npurpose="bounded discovery"\napplies_to_paths=["a.txt"]\ncommands=["echo one","echo two"]\nreview_aids=['
                + json.dumps("retained detail " * 200)
                + "]\n"
            )
    before = source.read_bytes()
    result = consume(surface, shared_core_binary, native_cli, {"target": str(tmp_path), "task": "Check source", "changed": ["a.txt"]})
    view = result["verification"]
    assert len(view["domain_proof_candidates"]["lanes"]) == 32
    assert view["domain_proof_candidates"]["omitted_descriptor_count"] == 9
    assert len(view["execution_requests"]) == 16
    assert view["execution"]["omitted_domain_command_count"] == 65
    assert view["strategy"]["proof_routes"] == {}
    assert "retained detail" not in json.dumps(result)
    assert len(json.dumps(result)) < 100_000
    assert result["capability_contract"]["owners"]
    for value in result.values():
        if isinstance(value, dict):
            assert "capability_contract" not in value
    assert source.read_bytes() == before


def test_oversized_selected_domain_detail_is_explicitly_blocked(tmp_path: Path, shared_core_binary: Path, native_cli: Path) -> None:
    source = config(tmp_path, "echo bounded", "review_aids=[" + json.dumps("large detail" * 4000) + "]\n")
    context = {"target": str(tmp_path), "task": "Check source", "changed": ["a.txt"]}
    first = consume("json", shared_core_binary, native_cli, context)
    request = first["verification"]["execution_requests"][0]
    result = consume("json", shared_core_binary, native_cli, {**context, "request": request}, host_path=os.environ["PATH"])
    assert result["verification"]["execution"]["reason"] == "domain-lane-selected-detail-exceeds-native-bound"
    assert result["verification"]["contribution"]["actions"] == []
    assert "large detail" not in json.dumps(result)
    assert source.exists()
