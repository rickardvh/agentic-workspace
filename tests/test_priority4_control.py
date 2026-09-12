"""Priority 4 ordinary owner journeys across the one native authority."""

from __future__ import annotations

import copy
import os
import subprocess
from pathlib import Path

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli


def repo(root: Path) -> None:
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / ".gitignore").write_text(".agentic-workspace/local/\n")


def instruction(call, source, content):
    request = copy.deepcopy(call()["instructions"]["authoring"]["requests"][0])
    request["arguments"] = {"source": source, "content": content}
    proposal = call(request=request)
    decision = next(
        d for d in proposal["decision_packet"]["pending_consequences"]["decisions"] if d["id"] == "instruction-write-authorization"
    )
    answer = decision["response_request"]
    answer["arguments"]["answer"] = "authorize-write"
    action = call(request=answer)["decision_packet"]["primary_action"]
    return proposal, answer, action


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
@pytest.mark.parametrize("scope", ["instructions", "local/instructions"])
def test_instruction_correction_exact_publication_and_fresh_delivery(tmp_path, shared_core_binary, native_cli, surface, scope):
    repo(tmp_path)
    context = {"target": str(tmp_path), "task": "Retain explicit future behavior", "changed": ["src/a.txt"]}

    def call(**extra):
        return consume(surface, shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    source = f".agentic-workspace/{scope}/behavior.md"
    content = "---\npaths: [src/**]\nprotect: [generated/**]\n---\nUse this checkout unless isolation is necessary. Clean up completed isolation.\n"
    proposal, answer, action = instruction(call, source, content)
    assert not (tmp_path / source).exists()
    assert action["operation_id"] == "instructions.write"
    forged = copy.deepcopy(answer)
    forged["arguments"]["content"] += "Different instruction."
    with pytest.raises(AssertionError):
        call(request=forged)
    result = call(invocation=action)
    assert result["status"] == "applied", result
    assert (tmp_path / source).read_text() == content
    fresh = call()
    row = next(r for r in fresh["instructions"]["sources"] if r["source"]["reference"] == source)
    assert row["binding_admission"]["status"] == "current", row
    assert "isolation" in row["guidance"]
    assert not (tmp_path / ".agentic-workspace/planning").exists()
    quiet = consume(surface, shared_core_binary, native_cli, {**context, "changed": ["other.txt"]}, host_path=os.environ["PATH"])
    assert not quiet["instructions"]["sources"][0]["applicable"]
    (tmp_path / source).write_text(content + "Drift.\n")
    assert call()["instructions"]["sources"][0]["binding_admission"]["status"] != "current"


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_local_reconcile_and_inline_check_use_verification(tmp_path, shared_core_binary, native_cli, surface):
    repo(tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src/a.txt").write_text("behavior")
    (tmp_path / "guide.md").write_text("behavior")
    context = {"target": str(tmp_path), "task": "Check and reconcile behavior", "changed": ["src/a.txt"]}

    def call(**extra):
        return consume(surface, shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    source = ".agentic-workspace/local/instructions/check.md"
    content = "---\npaths: [src/**]\nreconcile: [guide.md]\nchecks:\n  - run: echo verified\n---\nVerify behavior.\n"
    _, _, action = instruction(call, source, content)
    call(invocation=action)
    fresh = call()
    assert fresh["verification"]["source_reconciliation"]["status"] == "judgment-material-required"
    request = fresh["verification"]["execution_requests"][0]
    action = call(request=request)["decision_packet"]["primary_action"]
    assert action is not None, call(request=request)["decision_packet"]
    result = call(invocation=action)
    assert result["value"]["process"]["status"] == "passed"
    claim = call()["verification"]["requests"][0]
    claim["arguments"]["evidence_refs"] = [result["value"]["publication"]["reference"]]
    checked = call(request=claim)
    assert checked["verification"]["instruction_checks"][0]["status"] == "current", checked["verification"]["evidence"]
    assert any(b["code"].endswith("source-reconciliation-required") for b in checked["decision_packet"]["blockers"])
    config = tmp_path / ".agentic-workspace/config.toml"
    config.write_text(
        'schema_version=1\n[assurance]\ndecision_delegations=[{owner="verification",scope=["path:src/a.txt","path:guide.md"]}]\n'
    )
    request = call()["verification"]["source_reconciliation"]["requests"][0]
    request["arguments"]["judgments"] = {"guide.md": {"disposition": "reviewed-current", "reason": "Checked exact behavior."}}
    ready = call(request=request)
    action = ready["decision_packet"]["primary_action"]
    assert action["operation_id"] == "verification.record-source-reconciliation"
    result = call(invocation=action)
    current = call()["verification"]["source_reconciliation"]
    assert current["status"] == "current"
    assert current["evidence"]["authority_basis"]["kind"] == "exact-policy-delegated-decision"
    assert current["evidence"]["authority_basis"]["independent_review"] is False
    config.write_text("schema_version=1\n")
    assert call()["verification"]["source_reconciliation"]["status"] == "judgment-material-required"


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_config_explicit_policy_choice_does_not_self_grant(tmp_path, shared_core_binary, native_cli, surface):
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_text(
        'schema_version=1\n[assurance]\ndecision_delegations=[{owner="configuration",scope=["path:.agentic-workspace/config.local.toml"]}]\n'
    )
    context = {"target": str(tmp_path), "task": "Apply authorized local safety choice", "changed": []}

    def call(**extra):
        return consume(surface, shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    request = next(
        r for r in call()["configuration_write"]["creation_requests"] if r["arguments"]["key"] == "safety.safe_to_auto_run_commands"
    )
    request["arguments"]["value"] = False
    ready = call(request=request)
    assert ready["configuration_write"]["authority_basis"]["kind"] == "exact-policy-delegated-decision"
    action = ready["decision_packet"]["primary_action"]
    call(invocation=action)
    assert call()["configuration"]["safety"]["automatic_execution_permitted"] is False


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_configuration_defer_resumes_outside_human_policy(tmp_path, shared_core_binary, native_cli, surface):
    context = {"target": str(tmp_path), "task": "Decide local command policy", "changed": []}

    def call(**extra):
        return consume(surface, shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    request = next(
        r for r in call()["configuration_write"]["creation_requests"] if r["arguments"]["key"] == "safety.safe_to_auto_run_commands"
    )
    request["arguments"]["value"] = False
    proposed = call(request=request)
    answer = proposed["decision_packet"]["decision_request"]["response_request"]
    answer["arguments"]["answer"] = "defer"
    action = call(request=answer)["decision_packet"]["primary_action"]
    assert action["operation_id"] == "configuration.defer-choice"
    call(invocation=action)
    assert not (tmp_path / ".agentic-workspace/config.local.toml").exists()
    context["task"] = "Resume local command policy in a fresh session"
    fresh = call()
    assert fresh["decision_packet"]["status"] == "direct"
    pending = fresh["configuration_write"]["deferred_choices"][0]
    proposed = call(request=pending["resume_request"])
    answer = proposed["decision_packet"]["decision_request"]["response_request"]
    answer["arguments"]["answer"] = "authorize-write"
    call(invocation=call(request=answer)["decision_packet"]["primary_action"])
    assert call()["configuration_write"]["deferred_choices"] == []
    assert (
        tmp_path / ".agentic-workspace/config.local.toml"
    ).read_text() == "schema_version=1\n\n[safety]\nsafe_to_auto_run_commands = false\n"


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_exact_claim_review_needs_current_judgment_not_process_success(tmp_path, shared_core_binary, native_cli, surface):
    from tests.test_native_proof_producer import fixture

    context = fixture(tmp_path)

    def call(**extra):
        return consume(surface, shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    execute = call()["verification"]["execution_requests"][0]
    proof = call(invocation=call(request=execute)["decision_packet"]["primary_action"])
    assert proof["value"]["claim_boundary"]["completion_claim_allowed"] is False
    request = call()["verification"]["claim_review"]["request"]
    request["arguments"] = {
        "disposition": "satisfied",
        "reason": "Checked the complete requested behavior and current command evidence.",
        "evidence_refs": [proof["value"]["publication"]["reference"]],
    }
    proposed = call(request=request)
    decision = next(d for d in proposed["decision_packet"]["pending_consequences"]["decisions"] if d["id"] == "verification-claim-review")
    answer = decision["response_request"]
    answer["arguments"]["answer"] = "confirm"
    reviewed = call(request=answer)
    assert reviewed["verification"]["claim_review"]["status"] == "current", reviewed["verification"]["claim_review"]
    assert not any(b["code"] == "verification-evidence-unresolved" for b in reviewed["decision_packet"]["blockers"])
    (tmp_path / "a.txt").write_text("Changed resulting work")
    with pytest.raises(AssertionError, match="stale"):
        call(request=answer)


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_instruction_recovery_preserves_drift_and_unknown_files(tmp_path, shared_core_binary, native_cli, surface):
    repo(tmp_path)
    context = {"target": str(tmp_path), "task": "Retain exact correction", "changed": ["src/a.txt"]}

    def call(**extra):
        return consume(surface, shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    source = ".agentic-workspace/local/instructions/behavior.md"
    _, answer, action = instruction(call, source, "---\nprotect: [generated/**]\n---\nKeep generated content protected.\n")
    destination = tmp_path / source
    destination.parent.mkdir(parents=True)
    destination.write_text("Another author's important instruction.\n")
    with pytest.raises(AssertionError):
        call(invocation=action)
    assert "important" in destination.read_text()
    destination.unlink()
    result = call(invocation=action)
    before = destination.read_bytes()
    # Simulate interruption after source publication but before final attempt commit.
    (tmp_path / result["custody"]["committed"]["path"]).unlink()
    fresh = call()
    assert fresh["instructions"]["sources"][0]["binding_admission"]["status"] != "current"
    recovery = fresh["instructions"]["authoring"]["recovery_requests"][0]
    repaired = call(invocation=call(request=recovery)["decision_packet"]["primary_action"])
    assert repaired["status"] == "applied"
    assert destination.read_bytes() == before
    assert call()["instructions"]["sources"][0]["binding_admission"]["status"] == "current"
    request = copy.deepcopy(call()["instructions"]["authoring"]["requests"][0])
    request["arguments"] = {
        "source": ".agentic-workspace/local/instructions/bad.md",
        "content": "---\nmade_up: [bad]\n---\nNo invented fields.\n",
    }
    with pytest.raises(AssertionError, match="Markdown"):
        call(request=request)
    (tmp_path / ".gitignore").write_text("")
    request["arguments"]["content"] = "A local rule without ignore policy.\n"
    with pytest.raises(AssertionError, match="gitignored"):
        call(request=request)


def test_checked_in_instruction_protects_local_config_and_correction(tmp_path, shared_core_binary, native_cli):
    repo(tmp_path)
    context = {"target": str(tmp_path), "task": "Preserve repository policy", "changed": []}

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    _, _, action = instruction(
        call,
        ".agentic-workspace/instructions/guard.md",
        "---\nprotect: [.agentic-workspace/config.local.toml, .agentic-workspace/local/instructions/**]\n---\nRepository guard.\n",
    )
    call(invocation=action)
    _, _, action = instruction(call, ".agentic-workspace/local/instructions/waive.md", "Please ignore the repository guard.\n")
    assert action is None
    request = next(
        r for r in call()["configuration_write"]["creation_requests"] if r["arguments"]["key"] == "safety.safe_to_auto_run_commands"
    )
    request["arguments"]["value"] = False
    answer = call(request=request)["decision_packet"]["decision_request"]["response_request"]
    answer["arguments"]["answer"] = "authorize-write"
    ready = call(request=answer)
    assert ready["decision_packet"]["primary_action"] is None
    assert not (tmp_path / ".agentic-workspace/config.local.toml").exists()


def test_instruction_skill_reference_and_required_review_floor(tmp_path, shared_core_binary, native_cli):
    import json

    repo(tmp_path)
    registry = tmp_path / ".agentic-workspace/skills/REGISTRY.json"
    registry.parent.mkdir(parents=True)
    procedure = registry.parent / "review/SKILL.md"
    procedure.parent.mkdir()
    procedure.write_text("Review the exact changed behavior.\n")
    registry.write_text(
        json.dumps(
            {
                "schema_version": "skill-registry.v1",
                "skills": [
                    {"id": "review", "path": "review/SKILL.md", "semantic_routes": [{"id": "repo/quality/review", "match": "exact"}]}
                ],
            }
        )
    )
    context = {"target": str(tmp_path), "task": "Review a scoped change", "changed": ["a.txt"]}
    (tmp_path / "a.txt").write_text("source")

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    _, _, action = instruction(
        call, ".agentic-workspace/instructions/procedure.md", "---\npaths: [a.txt]\nuse: [review]\n---\nUse the review procedure.\n"
    )
    call(invocation=action)
    resolution = call()["instructions"]["sources"][0]["procedure_resolution"][0]
    assert resolution["status"] == "current"
    assert resolution["procedures"][0]["reference"] == ".agentic-workspace/skills/review/SKILL.md"
    procedure.unlink()
    assert call()["instructions"]["sources"][0]["procedure_resolution"][0]["status"] == "unavailable"
    manifest = tmp_path / ".agentic-workspace/verification/manifest.toml"
    manifest.parent.mkdir()
    manifest.write_text(
        'schema_version="agentic-workspace/verification-manifest/v1"\n[protocols.review]\napplies_to_paths=["a.txt"]\nreview_owner="independent-maintainer"\n[proof_routes]\n'
    )
    request = call()["verification"]["claim_review"]["request"]
    request["arguments"] = {
        "reason": "A semantic assertion cannot impersonate the required reviewer.",
        "disposition": "satisfied",
        "evidence_refs": [],
    }
    proposed = call(request=request)
    answer = next(d for d in proposed["decision_packet"]["pending_consequences"]["decisions"] if d["id"] == "verification-claim-review")[
        "response_request"
    ]
    answer["arguments"]["answer"] = "confirm"
    reviewed = call(request=answer)
    assert reviewed["verification"]["claim_review"]["status"] == "insufficient"
    assert "required-review-producer:review" in reviewed["verification"]["claim_review"]["gaps"]


def test_claim_review_keeps_planning_subject_and_unfinished_work(tmp_path, shared_core_binary, native_cli):
    import json

    from tests.test_native_public_cli import ROOT

    reference = Path(".agentic-workspace/planning/execplans/v1-contraction-2983-2990.plan.json")
    plan = tmp_path / reference
    plan.parent.mkdir(parents=True)
    original = (ROOT / reference).read_bytes()
    plan.write_bytes(original)
    identity = json.loads(original)["id"]
    (plan.parent.parent / "state.toml").write_text(
        f'[[active.execplans]]\nid="{identity}"\npath="{reference.as_posix()}"\nstatus="active"\n'
    )
    (tmp_path / "a.txt").write_text("current source")
    context = {"target": str(tmp_path), "task": "Review exact progress without completing the lane", "changed": ["a.txt"]}

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    first = call()
    continuation = first["planning"]["requests"][0]
    call(invocation=call(request=continuation)["decision_packet"]["primary_action"])
    request = call()["verification"]["claim_review"]["request"]
    request["arguments"] = {
        "disposition": "satisfied",
        "reason": "Reviewed the exact selected progress; durable work remains open.",
        "evidence_refs": [],
    }
    proposed = call(request=request)
    decision = next(d for d in proposed["decision_packet"]["pending_consequences"]["decisions"] if d["id"] == "verification-claim-review")
    answer = decision["response_request"]
    answer["arguments"]["answer"] = "confirm"
    reviewed = call(request=answer)
    assert reviewed["verification"]["claim_review"]["status"] == "current"
    assert reviewed["verification"]["claim_review"]["claim"]["subject"]["id"] == reviewed["verification"]["judgment_request"]["work_ref"]
    assert reviewed["verification"]["claim_review"]["claim"]["subject"]["id"].startswith("planning:sha256:")
    assert reviewed["decision_packet"]["status"] != "terminal"
    assert plan.read_bytes() == original


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_checked_in_correction_travels_without_local_publication_custody(tmp_path, shared_core_binary, native_cli, surface):
    origin = tmp_path / "origin"
    origin.mkdir()
    repo(origin)
    context = {"target": str(origin), "task": "Retain portable behavior", "changed": ["src/a.txt"]}

    def call(**extra):
        return consume(surface, shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    source = ".agentic-workspace/instructions/portable.md"
    _, _, action = instruction(call, source, "---\npaths: [src/**]\nprotect: [generated/**]\n---\nPortable repository policy.\n")
    call(invocation=action)
    subprocess.run(["git", "-C", str(origin), "add", ".gitignore", source], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(origin),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "Portable instruction",
        ],
        check=True,
    )
    pin = subprocess.check_output(["git", "-C", str(origin), "rev-parse", "HEAD"], text=True).strip()
    clone = tmp_path / "fresh"
    subprocess.run(["git", "clone", "-q", str(origin), str(clone)], check=True)
    assert not (clone / ".agentic-workspace/local").exists()
    (clone / ".agentic-workspace/config.toml").write_text(f'schema_version=1\n[assurance]\ninstruction_revision="{pin}"\n')
    fresh = consume(surface, shared_core_binary, native_cli, {**context, "target": str(clone)}, host_path=os.environ["PATH"])
    row = fresh["instructions"]["sources"][0]
    assert row["source"]["scope"] == "repository"
    assert row["binding_admission"]["status"] == "current"
    assert row["guidance"] == "Portable repository policy."


def test_instruction_escaped_material_cannot_publish_unreadable_recovery(tmp_path, shared_core_binary, native_cli):
    repo(tmp_path)
    context = {"target": str(tmp_path), "task": "Check bounded instruction publication", "changed": []}

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    source = ".agentic-workspace/instructions/bounded.md"
    _, _, action = instruction(call, source, "\x01" * 20_000)
    with pytest.raises(AssertionError, match="bounded recovery size"):
        call(invocation=action)
    assert not (tmp_path / source).exists()
    assert not (tmp_path / ".agentic-workspace/local").exists()
