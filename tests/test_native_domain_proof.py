"""Current config command candidates use the existing native Verification owner."""

from __future__ import annotations

import json
import os
import subprocess
import tomllib
from pathlib import Path

import pytest
from tests.test_native_public_cli import ROOT, consume
from tests.test_native_public_cli import native_cli as native_cli


def config(root: Path, command: str, extra: str = "") -> Path:
    source = root / ".agentic-workspace/verification/manifest.toml"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(
        'schema_version="agentic-workspace/verification-manifest/v1"\n[assurance.domain_proof_lanes.current]\npurpose="Current bounded check"\napplies_to_paths=["a.txt"]\ncommands=['
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
    if surface == "native":
        encoded = json.dumps(invocation)
        rejected = subprocess.run([str(native_cli), "invoke", "--input", "-"], input=encoded, text=True, capture_output=True, check=False)
        assert rejected.returncode == 2
        assert rejected.stdout == ""
        assert json.loads(rejected.stderr)["error"]["code"] == "invalid-cli-input"
        assert not (tmp_path / "count.txt").exists()
        explicit = subprocess.run(
            [
                str(native_cli),
                "invoke",
                "--target",
                context["target"],
                "--task",
                context["task"],
                "--changed",
                *context["changed"],
                "--input",
                "-",
            ],
            input=encoded,
            text=True,
            capture_output=True,
            env={**os.environ, "PATH": os.environ["PATH"]},
            check=True,
        )
        assert json.loads(explicit.stdout)["value"]["process"]["status"] == "passed"
    # Native uses the complete envelope here; the explicit raw invocation above
    # and this envelope must share the existing exactly-once execution result.
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
    assert not any(row["owner"] == "verification" for row in stale["decision_packet"]["pending_consequences"]["actions"])
    (tmp_path / "rules.md").write_text("changed rule")
    with pytest.raises(AssertionError, match="stale"):
        call({**context, "invocation": invocation})
    source.write_text(source.read_text().replace("domain-review", "stronger-domain-review"))
    stale = call({**context, "request": request})
    assert "verification-request-stale" in stale["verification"]["evidence_gaps"]
    assert not any(row["owner"] == "verification" for row in stale["decision_packet"]["pending_consequences"]["actions"])
    with pytest.raises(AssertionError, match="stale"):
        call({**context, "invocation": invocation})
    assert (tmp_path / "count.txt").read_text().splitlines() == ["executed"]
    (tmp_path / ".agentic-workspace/config.local.toml").write_text("[safety]\nsafe_to_auto_run_commands=false\n")
    current_request = call(context)["verification"]["execution_requests"][0]
    blocked = call({**context, "request": current_request})
    assert blocked["decision_packet"]["status"] != "ready"
    assert (tmp_path / "count.txt").read_text().splitlines() == ["executed"]


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_real_domain_lane_and_semantic_only_scope_stay_source_owned(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    source = tmp_path / ".agentic-workspace/verification/manifest.toml"
    source.parent.mkdir(parents=True)
    # Preserve the exact real lane declaration without unrelated repo-local ADR pins.
    text = (ROOT / ".agentic-workspace/verification/manifest.toml").read_text()
    start = text.index("[assurance.domain_proof_lanes.proof_subject_owner]")
    end = text.index("\n[", start + 1)
    profile_start = text.index("[assurance.proof_profiles.workspace_behavior]")
    profile_end = text.index("\n[", profile_start + 1)
    source.write_text(
        'schema_version="agentic-workspace/verification-manifest/v1"\n' + text[start:end] + "\n" + text[profile_start:profile_end]
    )
    current = tomllib.loads(source.read_text())["assurance"]["domain_proof_lanes"]["proof_subject_owner"]
    result = consume(
        surface,
        shared_core_binary,
        native_cli,
        {"target": str(tmp_path), "task": "Inspect proof owner", "changed": ["src/core/src/modules/verification/proof_publication.rs"]},
        host_path=os.environ["PATH"],
    )
    candidates = result["verification"]["domain_proof_candidates"]["lanes"]
    assert any(row["route_id"] == "domain:proof_subject_owner" and row["command_count"] == len(current["commands"]) for row in candidates)
    assert not (tmp_path / ".agentic-workspace/local").exists()
    source.write_text(
        'schema_version="agentic-workspace/verification-manifest/v1"\n[assurance.domain_proof_lanes.semantic]\npurpose="Semantic scope"\napplies_to_task_markers=["proof"]\ncommands=["echo candidate"]\n'
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
    assert not any(row["owner"] == "verification" for row in result["decision_packet"]["pending_consequences"]["actions"])
    assert "large detail" not in json.dumps(result)
    assert source.exists()


def test_repo_test_evidence_review_keeps_mechanical_proof_with_current_owner(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path
) -> None:
    # Use the real source declarations, including their reference closure. This
    # checks policy selection once, not transport parity or a new path registry.
    text = (ROOT / ".agentic-workspace/verification/manifest.toml").read_text()
    sections = [
        "scenarios.test_evidence_decision_review",
        "protocols.test_evidence_decision",
        "proof_routes.test_evidence_decision",
        "assurance.proof_profiles.workspace_behavior",
        "assurance.proof_profiles.verification_behavior",
        "assurance.proof_profiles.test_evidence_change",
        "assurance.requirements.test_evidence_change_decision",
        "assurance.domain_proof_lanes.native_public_owners",
        "assurance.domain_proof_lanes.verification_package_behavior",
        "assurance.domain_proof_lanes.compact_output_contract",
        "assurance.domain_proof_lanes.test_evidence_decision",
    ]
    declarations = []
    for section in sections:
        start = text.index(f"[{section}]")
        end = text.find("\n[", start + 1)
        declarations.append(text[start : end if end >= 0 else None])
    source = tmp_path / ".agentic-workspace/verification/manifest.toml"
    source.parent.mkdir(parents=True)
    source.write_text('schema_version="agentic-workspace/verification-manifest/v1"\n' + "\n".join(declarations))
    (source.parent.parent / "config.toml").write_text("[assurance]\nstrict_closeout=true\n")
    actual = tomllib.loads(source.read_text())
    lanes = actual["assurance"]["domain_proof_lanes"]
    fixed_suite = "uv run --frozen --active --no-sync python -m pytest tests/test_native_verification_strategy.py -q"

    def observe(paths):
        return consume(
            "native",
            shared_core_binary,
            native_cli,
            {"target": str(tmp_path), "task": "Inspect this bounded change", "changed": paths},
        )["verification"]

    def check(paths, mechanical_owner, *, review=True):
        view = observe(paths)
        routes = view["strategy"]["proof_routes"]
        selected = {row["arguments"]["route_id"]: [] for row in view["execution_requests"]}
        for row in view["execution_requests"]:
            selected[row["arguments"]["route_id"]].append(row["arguments"]["command"])
        assert fixed_suite not in [command for commands in selected.values() for command in commands]
        assert "test_evidence_decision" not in selected and "domain:test_evidence_decision" not in selected
        requirements = view["assurance_applicability"]["requirements"]
        evidence_review = next(row for row in requirements if row["id"] == "test_evidence_change_decision")
        assert (evidence_review["status"] == "applicable") == review
        if review:
            assert "test_evidence_decision" in view["strategy"]["protocols"]
            assert routes["test_evidence_decision"]["commands"] == []
            profile = next(row for row in view["strategy_control"]["selected_profiles"] if row["id"] == "test_evidence_change")
            assert profile["selected_by"] == "binding-requirement" and profile["required_count"] == 0
            assert view["strategy_control"]["obligations"] == []
            assert evidence_review["source_requirement"]["required_evidence"] == ["verification_proof_decision_review"]
        else:
            assert "test_evidence_decision" not in view["strategy"]["protocols"]
        if mechanical_owner:
            assert selected[f"domain:{mechanical_owner}"] == lanes[mechanical_owner]["commands"]
        else:
            assert selected == {}
        return view

    check(["tests/test_native_verification_strategy.py"], "native_public_owners")
    check(["tests/test_review_preparation.py"], None)
    check(["src/core/src/operating.rs", "tests/test_native_operating_carriage.py"], "compact_output_contract")
    cleanup = check(["tests/test_review_preparation.py"], None)
    # Existing evidence can support a semantic test-only cleanup review without
    # manufacturing a command. This is not independent review or whole-work
    # completion; the remaining assurance/reviewer owner remains separate.
    context = {"target": str(tmp_path), "task": "Inspect this bounded change", "changed": ["tests/test_review_preparation.py"]}
    request = cleanup["claim_review"]["request"]
    request["arguments"] = {
        "disposition": "satisfied",
        "reason": "The cleanup retains the existing maintainer-review behavior evidence; no distinct mechanical risk needs a new run.",
        "evidence_refs": [],
    }
    proposed = consume("native", shared_core_binary, native_cli, {**context, "request": request})
    decision = next(
        row for row in proposed["decision_packet"]["pending_consequences"]["decisions"] if row["id"] == "verification-claim-review"
    )
    answer = decision["response_request"]
    answer["arguments"]["answer"] = "confirm"
    reviewed = consume("native", shared_core_binary, native_cli, {**context, "request": answer})
    assert reviewed["verification"]["claim_review"]["status"] == "current"
    assert reviewed["verification"]["execution_requests"] == []
    assert reviewed["decision_packet"]["claim_boundary"]["allowed"] == []
    check(["src/core/src/operating.rs"], "compact_output_contract", review=False)

    # Representative layer paths from the merged #3774–#3776 implementation PRs
    # #3777–#3779. The native owner may offer its declared conformance command;
    # test-evidence review itself never selects the old standalone strategy run.
    check(
        [
            ".agentic-workspace/skills/workspace-intent-discovery/references/intent.md",
            "src/core/payload/.agentic-workspace/skills/workspace-intent-discovery/references/intent.md",
            "docs/maintainer/compact-intent-3774.md",
        ],
        None,
        review=False,
    )
    check(
        [
            "src/core/src/modules/verification/native_proof.rs",
            "src/core/src/modules/verification/proof_executor.rs",
            "tests/test_native_proof_producer.py",
        ],
        "native_public_owners",
    )
    check(["tools/skills/pr-review-recheck/prepare.py", "tests/test_review_preparation.py"], None)
    assert not (tmp_path / ".agentic-workspace/local").exists()
