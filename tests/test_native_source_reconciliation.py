"""Current source judgments use Verification, without a documentation workflow."""

from __future__ import annotations

import copy
import os
import subprocess
from pathlib import Path

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli


def repository(root: Path) -> dict:
    instruction = root / ".agentic-workspace/instructions/feature.md"
    instruction.parent.mkdir(parents=True)
    instruction.write_text("---\npaths: [src/**]\nread: [docs/context.md]\nreconcile: [docs/guide.md]\n---\nKeep the guide consistent.\n")
    (root / "docs").mkdir()
    (root / "docs/guide.md").write_text("The existing feature behavior.\n")
    (root / "docs/context.md").write_text("Context is not a reconciliation obligation.\n")
    (root / "src").mkdir()
    (root / "src/feature.txt").write_text("feature behavior\n")
    for args in (
        ["init", "-q"],
        ["add", "."],
        ["-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "source authority"],
    ):
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
    pin = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    (root / ".agentic-workspace/config.toml").write_text(f'schema_version=1\n[assurance]\ninstruction_revision="{pin}"\n')
    return {"target": str(root), "task": "Complete the feature change", "changed": ["src/feature.txt"]}


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
@pytest.mark.parametrize("disposition", ["updated", "reviewed-current"])
def test_exact_source_judgment_is_retained_and_selectively_stales(tmp_path, shared_core_binary, native_cli, surface, disposition):
    context = repository(tmp_path)

    def call(extra=None):
        return consume(surface, shared_core_binary, native_cli, {**context, **(extra or {})}, host_path=os.environ["PATH"])

    initial = call()
    reconciliation = initial["verification"]["source_reconciliation"]
    assert reconciliation["status"] == "judgment-material-required"
    assert reconciliation["obligations"] == ["docs/guide.md"]
    assert initial["instructions"]["sources"][0]["read"] == ["docs/context.md"]
    request = reconciliation["requests"][0]
    request["arguments"]["judgments"] = {
        "docs/guide.md": {"disposition": disposition, "reason": "Checked the guide against the exact feature behavior."}
    }
    proposed = call({"request": request})
    request = proposed["decision_packet"]["pending_consequences"]["decisions"][0]["response_request"]
    request["arguments"]["answer"] = "confirm"
    ready = call({"request": request})
    action = ready["decision_packet"]["primary_action"]
    assert action["operation_id"] == "verification.record-source-reconciliation"
    before = (tmp_path / "docs/guide.md").read_bytes()
    result = call({"invocation": action})
    assert result["status"] == "applied", result
    current = call()["verification"]["source_reconciliation"]
    assert current["status"] == "current", current
    assert current["evidence"]["authority_basis"]["kind"] == "exact-bounded-human-answer"
    assert current["evidence"]["authority_basis"]["identity_authentication"] == "not-claimed"
    assert (tmp_path / "docs/guide.md").read_bytes() == before
    assert not (tmp_path / ".agentic-workspace/planning").exists()
    (tmp_path / "docs/unrelated.md").write_text("unrelated")
    assert call()["verification"]["source_reconciliation"]["status"] == "current"
    # New relevant work during an opaque interval is absent from `changed`.
    (tmp_path / "src/new.txt").write_text("new behavior")
    assert call()["verification"]["source_reconciliation"]["status"] == "judgment-material-required"
    with pytest.raises(AssertionError, match="stale or differs"):
        call({"request": request})


def test_source_judgment_rejects_forged_labels_and_missing_sources(tmp_path, shared_core_binary, native_cli):
    context = repository(tmp_path)

    def call(extra=None):
        return consume("json", shared_core_binary, native_cli, {**context, **(extra or {})}, host_path=os.environ["PATH"])

    issued = call()["verification"]["source_reconciliation"]["requests"][0]
    answered = copy.deepcopy(issued)
    answered["arguments"]["judgments"] = {"docs/guide.md": {"disposition": "reviewed-current", "reason": "Checked."}}
    for field in ("actor", "authority", "provenance"):
        forged = copy.deepcopy(answered)
        forged["arguments"][field] = "trusted-human"
        with pytest.raises(AssertionError):
            call({"request": forged})
    (tmp_path / "docs/guide.md").unlink()
    assert call()["verification"]["source_reconciliation"]["status"] == "source-admission-required"


def test_new_instruction_source_invalidates_absent_obligation(tmp_path, shared_core_binary, native_cli):
    context = repository(tmp_path)
    context["changed"] = ["other/file.txt"]
    quiet = consume("json", shared_core_binary, native_cli, context)
    assert quiet["verification"]["source_reconciliation"]["status"] == "not-required"
    new = tmp_path / ".agentic-workspace/instructions/new.md"
    new.write_text("---\npaths: [other/**]\nreconcile: [docs/guide.md]\n---\nNew source requirement.\n")
    fresh = consume("json", shared_core_binary, native_cli, context)
    assert fresh["verification"]["source_reconciliation"]["status"] == "source-admission-required"
    assert fresh["verification"]["source_reconciliation"]["obligations"] == ["docs/guide.md"]


def answer_for(call):
    request = call()["verification"]["source_reconciliation"]["requests"][0]
    request["arguments"]["judgments"] = {
        source: {"disposition": "reviewed-current", "reason": "Checked exact resulting work and canonical source."}
        for source in call()["verification"]["source_reconciliation"]["obligations"]
    }
    proposed = call({"request": request})
    assert proposed["decision_packet"]["primary_action"] is None
    question = next(q for q in proposed["decision_packet"]["pending_consequences"]["decisions"] if q["id"] == "source-reconciliation")
    request = question["response_request"]
    request["arguments"]["answer"] = "confirm"
    return request


@pytest.mark.parametrize("drift", ["source", "dependency", "policy", "work", "instruction"])
def test_exact_answer_stales_before_publication(tmp_path, shared_core_binary, native_cli, drift):
    context = repository(tmp_path)

    def call(extra=None):
        return consume("json", shared_core_binary, native_cli, {**context, **(extra or {})})

    answer = answer_for(call)
    paths = {
        "source": "docs/guide.md",
        "dependency": "docs/context.md",
        "policy": ".agentic-workspace/config.toml",
        "work": "src/feature.txt",
        "instruction": ".agentic-workspace/instructions/feature.md",
    }
    path = tmp_path / paths[drift]
    path.write_text(path.read_text() + "\n# changed\n")
    if drift == "instruction":
        assert call()["verification"]["source_reconciliation"]["status"] == "source-admission-required"
    else:
        with pytest.raises(AssertionError):
            call({"request": answer})
    assert not (tmp_path / ".agentic-workspace/proof/receipts").exists()


@pytest.mark.parametrize("stage", ["receipt", "temporary"])
def test_interrupted_publication_recovers_exact_owner_answer(tmp_path, shared_core_binary, native_cli, stage):
    import json

    context = repository(tmp_path)

    def call(extra=None):
        return consume("json", shared_core_binary, native_cli, {**context, **(extra or {})})

    answer = answer_for(call)
    action = call({"request": answer})["decision_packet"]["primary_action"]
    done = call({"invocation": action})
    receipt = tmp_path / action["arguments"]["receipt_ref"]
    before = receipt.read_bytes()
    (tmp_path / done["custody"]["committed"]["path"]).unlink()
    if stage == "temporary":
        receipt.rename(str(receipt) + ".tmp")
    recovered = call()
    assert recovered["verification"]["source_reconciliation"]["status"] == "publication-required"
    retry = recovered["decision_packet"]["primary_action"]
    assert retry == action
    call({"invocation": retry})
    assert receipt.read_bytes() == before
    assert call()["verification"]["source_reconciliation"]["status"] == "current"
    assert json.loads(before)["value"]["authority_basis"]["kind"] == "exact-bounded-human-answer"


def test_defer_and_changed_proposal_do_not_publish(tmp_path, shared_core_binary, native_cli):
    context = repository(tmp_path)

    def call(extra=None):
        return consume("json", shared_core_binary, native_cli, {**context, **(extra or {})})

    answer = answer_for(call)
    forged = copy.deepcopy(answer)
    forged["arguments"]["judgments"]["docs/guide.md"]["reason"] = "Different decision"
    with pytest.raises(AssertionError):
        call({"request": forged})
    answer["arguments"]["answer"] = "defer"
    result = call({"request": answer})
    assert result["verification"]["source_reconciliation"]["status"] == "deferred"
    assert result["decision_packet"]["primary_action"] is None
    assert not (tmp_path / ".agentic-workspace/proof/receipts").exists()


def test_non_document_source_and_duplicate_instruction(tmp_path, shared_core_binary, native_cli):
    context = repository(tmp_path)
    instruction = tmp_path / ".agentic-workspace/instructions/feature.md"
    instruction.write_text(instruction.read_text().replace("docs/guide.md", "contracts/format.json"))
    (instruction.parent / "duplicate.md").write_bytes(instruction.read_bytes())
    (tmp_path / "contracts").mkdir()
    (tmp_path / "contracts/format.json").write_text('{"format":1}')
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "contract"],
        check=True,
    )
    pin = subprocess.check_output(["git", "-C", str(tmp_path), "rev-parse", "HEAD"], text=True).strip()
    (tmp_path / ".agentic-workspace/config.toml").write_text(f'schema_version=1\n[assurance]\ninstruction_revision="{pin}"\n')

    def call(extra=None):
        return consume("json", shared_core_binary, native_cli, {**context, **(extra or {})})

    assert call()["verification"]["source_reconciliation"]["obligations"] == ["contracts/format.json"]
    answer = answer_for(call)
    call({"invocation": call({"request": answer})["decision_packet"]["primary_action"]})
    assert call()["verification"]["source_reconciliation"]["status"] == "current"
    assert (tmp_path / "contracts/format.json").read_text() == '{"format":1}'


def test_planning_reentry_preserves_pending_obligation(tmp_path, shared_core_binary, native_cli):
    import json

    from tests.test_native_public_cli import ROOT

    context = repository(tmp_path)
    ref = Path(".agentic-workspace/planning/execplans/v1-contraction-2983-2990.plan.json")
    plan = tmp_path / ref
    plan.parent.mkdir(parents=True)
    plan.write_bytes((ROOT / ref).read_bytes())
    original = json.loads(plan.read_bytes())
    (plan.parent.parent / "state.toml").write_text(
        f'[[active.execplans]]\nid="{original["id"]}"\npath="{ref.as_posix()}"\nstatus="active"\n'
    )

    def call(extra=None):
        return consume("json", shared_core_binary, native_cli, {**context, **(extra or {})})

    first = call()
    continuation = first["planning"]["requests"][0]
    selected = call({"request": continuation})
    assert selected["planning"]["source_reconciliation"]["obligations"] == ["docs/guide.md"]
    action = selected["decision_packet"]["primary_action"]
    call({"invocation": action})
    fresh = call()
    assert fresh["planning"]["source_reconciliation"]["obligations"] == ["docs/guide.md"]
    assert fresh["planning"]["source_reconciliation"]["status"] == "judgment-material-required"
    assert plan.read_bytes() == (ROOT / ref).read_bytes()


def test_protected_receipt_destination_never_publishes(tmp_path, shared_core_binary, native_cli):
    context = repository(tmp_path)
    instruction = tmp_path / ".agentic-workspace/instructions/feature.md"
    instruction.write_text(instruction.read_text().replace("read:", "protect: [.agentic-workspace/proof/**]\nread:"))
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "protection"],
        check=True,
    )
    pin = subprocess.check_output(["git", "-C", str(tmp_path), "rev-parse", "HEAD"], text=True).strip()
    (tmp_path / ".agentic-workspace/config.toml").write_text(f'schema_version=1\n[assurance]\ninstruction_revision="{pin}"\n')

    def call(extra=None):
        return consume("json", shared_core_binary, native_cli, {**context, **(extra or {})})

    answer = answer_for(call)
    ready = call({"request": answer})
    assert ready["decision_packet"]["primary_action"] is None
    assert any("protected-proof-write" in b["code"] for b in ready["decision_packet"]["blockers"])
    assert not (tmp_path / ".agentic-workspace/proof/receipts").exists()


def test_global_reconciliation_observes_opaque_new_work(tmp_path, shared_core_binary, native_cli):
    context = repository(tmp_path)
    instruction = tmp_path / ".agentic-workspace/instructions/feature.md"
    instruction.write_text(instruction.read_text().replace("paths: [src/**]\n", ""))
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "global"],
        check=True,
    )
    pin = subprocess.check_output(["git", "-C", str(tmp_path), "rev-parse", "HEAD"], text=True).strip()
    (tmp_path / ".agentic-workspace/config.toml").write_text(f'schema_version=1\n[assurance]\ninstruction_revision="{pin}"\n')

    def call(extra=None):
        return consume("json", shared_core_binary, native_cli, {**context, **(extra or {})})

    answer = answer_for(call)
    call({"invocation": call({"request": answer})["decision_packet"]["primary_action"]})
    assert call()["verification"]["source_reconciliation"]["status"] == "current"
    (tmp_path / "new-behavior.txt").write_text("Not listed by the caller")
    assert call()["verification"]["source_reconciliation"]["status"] == "judgment-material-required"


def test_linked_scope_cannot_supply_currentness(tmp_path, shared_core_binary, native_cli):
    context = repository(tmp_path)
    source = tmp_path / "src"
    moved = tmp_path / "real-src"
    source.rename(moved)
    if os.name == "nt":
        subprocess.run(["cmd", "/c", "mklink", "/J", str(source), str(moved)], check=True, capture_output=True)
    else:
        source.symlink_to(moved, target_is_directory=True)
    fresh = consume("json", shared_core_binary, native_cli, context)
    assert fresh["verification"]["source_reconciliation"]["status"] == "scope-observation-required"
    assert fresh["decision_packet"]["primary_action"] is None


def test_unknown_receipt_is_preserved_without_claim_authority(tmp_path, shared_core_binary, native_cli):
    context = repository(tmp_path)

    def call(extra=None):
        return consume("json", shared_core_binary, native_cli, {**context, **(extra or {})})

    answer = answer_for(call)
    action = call({"request": answer})["decision_packet"]["primary_action"]
    receipt = tmp_path / action["arguments"]["receipt_ref"]
    receipt.parent.mkdir(parents=True)
    receipt.write_text('{"value":{"authority_basis":"trusted-human"}}')
    before = receipt.read_bytes()
    fresh = call()
    assert fresh["verification"]["source_reconciliation"]["status"] == "publication-review-required"
    assert fresh["decision_packet"]["primary_action"] is None
    with pytest.raises(AssertionError):
        call({"invocation": action})
    assert receipt.read_bytes() == before


def test_escaped_receipt_budget_rejects_before_admission(tmp_path, shared_core_binary, native_cli):
    context = repository(tmp_path)
    instruction = tmp_path / ".agentic-workspace/instructions/feature.md"
    refs = [f"docs/guide-{i}.md" for i in range(16)]
    for ref in refs:
        (tmp_path / ref).write_text("Canonical source")
    instruction.write_text(instruction.read_text().replace("docs/guide.md", ", ".join(refs)))
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "bounded sources",
        ],
        check=True,
    )
    pin = subprocess.check_output(["git", "-C", str(tmp_path), "rev-parse", "HEAD"], text=True).strip()
    (tmp_path / ".agentic-workspace/config.toml").write_text(f'schema_version=1\n[assurance]\ninstruction_revision="{pin}"\n')

    def call(extra=None):
        return consume("json", shared_core_binary, native_cli, {**context, **(extra or {})})

    request = call()["verification"]["source_reconciliation"]["requests"][0]
    request["arguments"]["judgments"] = {ref: {"disposition": "reviewed-current", "reason": "\u0001" * 4096} for ref in refs}
    proposed = call({"request": request})
    answer = proposed["decision_packet"]["pending_consequences"]["decisions"][0]["response_request"]
    answer["arguments"]["answer"] = "confirm"
    action = call({"request": answer})["decision_packet"]["primary_action"]
    with pytest.raises(AssertionError, match="bounded recovery size"):
        call({"invocation": action})
    assert not (tmp_path / ".agentic-workspace/local/effects").exists()
    assert not (tmp_path / ".agentic-workspace/proof/receipts").exists()
