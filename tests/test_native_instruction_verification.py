"""Instruction checks compose with reconciliation and protected writes."""

from __future__ import annotations

import os

from tests.test_native_instruction_write import instruction, repo
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli


def test_local_reconcile_and_inline_check_use_verification(tmp_path, shared_core_binary, native_cli):
    repo(tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src/a.txt").write_text("behavior")
    (tmp_path / "guide.md").write_text("behavior")
    context = {"target": str(tmp_path), "task": "Check and reconcile behavior", "changed": ["src/a.txt"]}

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

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
    assert not any(b["code"] == f"instruction:{source}:current-binding" for b in checked["decision_packet"]["blockers"])
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


def test_current_check_releases_claim_but_preserves_same_instruction_protection(tmp_path, shared_core_binary, native_cli):
    from tests.test_native_proof_producer import fixture

    repo(tmp_path)
    context = fixture(tmp_path)

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    # Produce evidence for the existing named route before installing the guard:
    # unbounded shell execution under a current protection remains forbidden.
    request = call()["verification"]["execution_requests"][0]
    action = call(request=request)["decision_packet"]["primary_action"]
    result = call(invocation=action)
    assert result["value"]["process"]["status"] == "passed"
    source = ".agentic-workspace/instructions/guard.md"
    _, _, action = instruction(
        call,
        source,
        "---\nchecks: [check]\nprotect: [.agentic-workspace/local/instructions/**]\n---\nCheck behavior and preserve local instructions.\n",
    )
    call(invocation=action)
    code = f"instruction:{source}:current-binding"
    before = next(b for b in call()["decision_packet"]["blockers"] if b["code"] == code)
    assert "claim:complete" in before["affects"]
    claim = call()["verification"]["requests"][0]
    claim["arguments"]["evidence_refs"] = [result["value"]["publication"]["reference"]]
    checked = call(request=claim)
    assert checked["verification"]["instruction_checks"][0]["status"] == "current", checked["verification"]["evidence"]
    remaining = next(b for b in checked["decision_packet"]["blockers"] if b["code"] == code)
    assert remaining["affects"] == ["effect:write:.agentic-workspace/local/instructions/**"]

    def with_evidence(**extra):
        selected = extra.pop("request", None)
        result = call(request=[claim, selected] if selected else claim, **extra)
        assert result["verification"]["instruction_checks"][0]["status"] == "current"
        if selected and selected.get("arguments", {}).get("answer") == "authorize-write":
            assert any(b["code"].endswith("protected-instruction-write") for b in result["decision_packet"]["blockers"])
        return result

    _, _, protected = instruction(with_evidence, ".agentic-workspace/local/instructions/waive.md", "Waive the guard.\n")
    assert protected is None
    assert not (tmp_path / ".agentic-workspace/local/instructions/waive.md").exists()

    (tmp_path / "a.txt").write_text("changed after proof")
    stale = call(request=claim)
    assert stale["verification"]["instruction_checks"][0]["status"] != "current"
    restored = next(b for b in stale["decision_packet"]["blockers"] if b["code"] == code)
    assert "claim:complete" in restored["affects"]
    assert "effect:write:.agentic-workspace/local/instructions/**" in restored["affects"]


def test_former_mixed_guidance_converges_through_scoped_owners(tmp_path, shared_core_binary, native_cli):
    repo(tmp_path)
    workspace = tmp_path / ".agentic-workspace"
    workspace.mkdir()
    shared = workspace / "config.toml"
    local = workspace / "config.local.toml"
    shared.write_text(
        'schema_version=1\n[workflow_obligations.proof]\nsummary="Shared proof before completion"\nstage="closeout"\nforce="required-before-closeout"\ncommands=["echo shared-proof"]\nscope_tags=["workspace"]\n'
    )
    local.write_text(
        'schema_version=1\n[local_overlay.high_risk.guardrails.fixture]\napplies_to_paths=["src/**"]\nimpact="blocking"\nsensitive_data=["private fixtures"]\nsynthetic_fixture_guidance=["Use synthetic examples"]\nrequired_sources=["templates/form.md"]\nheadings=["Evidence"]\nvalidation_state="ci_unavailable"\nlocal_substitute_commands=["echo local-only"]\nlocal_substitute_policy="insufficient"\nquestion="Is old CI still unavailable?"\ncategory="safe-follow-up"\n'
    )
    template = tmp_path / "templates/form.md"
    template.parent.mkdir()
    template.write_text("# Evidence\n")
    context = {"target": str(tmp_path), "task": "Inspect fixture behavior", "changed": ["src/a.txt"]}

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, {**context, **extra})

    old = shared.read_bytes(), local.read_bytes()
    before = call()
    residual = next(row for row in before["configuration"]["residuals"] if row["field"] == "local_overlay.high_risk")
    assert residual["transition"]["authority"].startswith("local;")
    destinations = {
        ".agentic-workspace/instructions/shared-proof.md": "---\npaths: [src/**]\nchecks:\n  - run: echo shared-proof\n---\nRequired shared proof before completion.\n",
        ".agentic-workspace/local/instructions/fixtures.md": "---\npaths: [src/**]\nread: [templates/form.md]\nprotect: [private/**]\n---\nDo not expose private fixture data; use synthetic examples. Consult the original form. Optional local-only validation (`echo local-only`) cannot replace shared proof.\n",
    }
    for source, content in destinations.items():
        _, _, action = instruction(call, source, content)
        assert action is not None
        call(invocation=action)
        assert (shared.read_bytes(), local.read_bytes()) == old
    # The source owner confirms each meaning before retiring the former entries.
    # Template structure stays in its original file. Old CI status is reobserved,
    # and its obsolete safe-follow-up question is deliberately not retained.
    staged = call()
    assert staged["configuration"]["residuals"]
    assert staged["decision_packet"]["claim_boundary"]["allowed"] == []
    shared.write_text("schema_version=2\n")
    local.write_text("schema_version=2\n")
    fresh = call()
    assert fresh["configuration"]["residuals"] == []
    rows = {row["source"]["reference"]: row for row in fresh["instructions"]["sources"]}
    for source in destinations:
        assert rows[source]["applicable"]
        assert rows[source]["binding_admission"]["status"] == "current"
    assert fresh["verification"]["instruction_checks"]
    assert fresh["decision_packet"]["claim_boundary"]["allowed"] == []
    assert "local-only" not in (tmp_path / ".agentic-workspace/instructions/shared-proof.md").read_text()
    assert template.read_text() == "# Evidence\n"
    unrelated = call(changed=["unrelated.txt"], task="src private shared-proof keyword overlap")
    assert not any(row["applicable"] for row in unrelated["instructions"]["sources"])
    assert unrelated["verification"]["instruction_checks"] == []
    assert call()["configuration"]["residuals"] == []
    assert shared.read_text() == local.read_text() == "schema_version=2\n"
