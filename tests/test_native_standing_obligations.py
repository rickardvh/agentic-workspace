"""One native lifecycle proves standing assessments, custody and currentness."""

from __future__ import annotations

import json
import shutil
import time
import tomllib
from pathlib import Path

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli


def test_repository_coherence_declaration_reaches_native_entry(tmp_path, shared_core_binary, native_cli):
    root = Path(__file__).resolve().parents[1]
    manifest_path = ".agentic-workspace/verification/manifest.toml"
    manifest = tomllib.loads((root / manifest_path).read_text(encoding="utf-8"))
    requirement_id = "aw_repository_state_coherence"
    declaration = manifest["assurance"]["requirements"][requirement_id]
    assert declaration["requirement_class"] == "current-evidence"
    freshness = declaration["freshness"]
    for path in {manifest_path, freshness["procedure"], *freshness["dependencies"]}:
        source = root / path
        assert source.is_file(), path
        destination = tmp_path / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    context = {"target": str(tmp_path), "task": "Inspect the repository coherence condition"}
    result = consume("native", shared_core_binary, native_cli, context)
    entry = next(e for e in result["verification"]["current_evidence"]["entries"] if e["id"] == requirement_id)
    assert entry["status"] == "due"
    assert entry["reason"] == "no-current-assessment"
    assert entry["declaration"]["freshness"] == freshness
    candidate = next(
        c
        for c in result["activation"]["candidates"]
        if c["entry"].get("owner_reference", {}).get("id") == f"current-evidence:{requirement_id}"
    )
    assert candidate["entry"]["resource"] == freshness["procedure"]
    assert candidate["disposition"] == "route"


@pytest.mark.parametrize(
    "detail_route,human_required",
    [("measurement:latency", False), ("uv run pytest tests/test_latency.py -q", False), ("measurement:latency", True)],
)
def test_standing_assessment_publication_recovery_and_retirement(tmp_path, shared_core_binary, native_cli, detail_route, human_required):
    manifest = tmp_path / ".agentic-workspace/verification/manifest.toml"
    manifest.parent.mkdir(parents=True)
    header = 'schema_version = "agentic-workspace/verification-manifest/v1"\n'
    manifest.write_text(
        header + "[assurance.requirements.example]\n"
        f"human_judgment_required = {str(human_required).lower()}\n"
        'level = "medium"\nforce = "required-before-closeout"\nrequirement_class = "current-evidence"\n'
        'source_intent_ref = "interface.json"\nsource_intent_revision = "v1"\n'
        'evidence_owner = "verification:example"\nrequired_evidence = ["Recorded comparison"]\n'
        'blocking_claims = ["claim-work-complete"]\nnotes = "Example follows the interface"\n'
        f'detail_route = "{detail_route}"\n[assurance.requirements.example.freshness]\n'
        'procedure = "procedure.md"\n'
        'max_age_seconds = 3600\ndependencies = ["interface.json"]\ndisposition = "route"\n'
    )
    for path, content in {
        "procedure.md": "Compare the example and current interface.",
        "interface.json": "{}",
        "evidence.md": "The comparison found no difference.",
    }.items():
        (tmp_path / path).write_text(content)
    if human_required:
        (tmp_path / ".agentic-workspace/config.toml").write_text(
            '[assurance]\ndecision_delegations=[{owner="verification",scope=['
            '"path:.agentic-workspace/verification/manifest.toml","path:procedure.md",'
            '"path:interface.json","path:evidence.md"]}]\n'
        )
    context = {"target": str(tmp_path), "task": "Assess the declared example obligation"}

    def call(extra=None):
        return consume("native", shared_core_binary, native_cli, {**context, **(extra or {})})

    initial = call()["verification"]["current_evidence"]
    assert initial["entries"][0]["status"] == "due"
    assert initial["entries"][0]["declaration"]["detail_route"] == detail_route
    compact = call({"projection": "compact"})
    assert compact["material"]["items"][0]["gap"] == "no-current-assessment"
    assert compact["activation"]["candidates"][0]["entry"]["resource"] == "procedure.md"
    assert compact["activation"]["candidates"][0]["disposition"] == "route"
    time.sleep(1.05)
    detail = call({"projection": "compact", "reference": compact["detail_refs"]["/verification"]})
    assert detail["value"]["current_evidence"] == initial
    external = consume("json", shared_core_binary, native_cli, {**context, "projection": "compact"})
    assert external["activation"] == compact["activation"]
    request = initial["requests"][0]
    request["arguments"].update(
        observed_at=int(time.time()), outcome="satisfied", reason="Compared the current sources.", evidence_refs=["evidence.md"]
    )
    proposed = call({"request": request})
    decision = next(q for q in proposed["decision_packet"]["pending_consequences"]["decisions"] if q["id"] == "current-evidence-assessment")
    assert decision["resolution"] == ("bounded-human-answer" if human_required else "bounded-domain-answer")
    assert ("human_eligibility" in decision) == human_required
    if human_required:
        assert decision["human_eligibility"]["declaration"]["human_judgment_required"] is True
        assert decision["human_eligibility"]["reference"].endswith("#assurance.requirements.example")
    for projection in ["compact", "carried"]:
        projected = call({"request": request, "projection": projection})
        view = projected.get("view", projected)
        projected_decision = next(
            q for q in view["decision_packet"]["pending_consequences"]["decisions"] if q["id"] == "current-evidence-assessment"
        )
        assert projected_decision.get("human_eligibility") == decision.get("human_eligibility")
        assert projected_decision.get("human_context") == decision.get("human_context")
    answer = decision["response_request"]
    answer["arguments"]["answer"] = "confirm"
    if human_required:
        original_manifest = manifest.read_bytes()
        manifest.write_bytes(original_manifest.replace(b"human_judgment_required = true", b"human_judgment_required = false"))
        with pytest.raises(AssertionError):
            call({"request": answer})
        manifest.write_bytes(original_manifest)
        deferred = json.loads(json.dumps(answer))
        deferred["arguments"]["answer"] = "defer"
        assert call({"request": deferred})["verification"]["current_evidence"]["status"] == "deferred"
        assert not (tmp_path / ".agentic-workspace/proof/current/current-evidence.json").exists()
    ready = call({"request": answer})
    action = next(a for a in ready["decision_packet"]["ready_actions"] if a["operation_id"] == "verification.record-current-evidence")
    done = call({"invocation": action})
    assert done["status"] == "applied", done
    state = tmp_path / ".agentic-workspace/proof/current/current-evidence.json"
    published = state.read_bytes()
    authorization = json.loads(published)["assessments"]["example"]["assessment"]["authorization"]
    assert authorization["kind"] == ("exact-bounded-human-answer" if human_required else "exact-bounded-domain-answer")
    observed = call()
    assert observed["verification"]["current_evidence"]["entries"][0]["status"] == "satisfied"
    requirement = next(r for r in observed["verification"]["assurance_applicability"]["requirements"] if r["id"] == "example")
    assert requirement["status"] == "applicable"
    assert requirement["current_evidence"]["status"] == "satisfied"
    assert not any(b["code"].startswith("assurance:example:") for b in observed["decision_packet"]["blockers"])
    quiet = call({"projection": "compact"})
    assert "material" not in quiet
    assert "activation" not in quiet
    other_checkout = tmp_path / "other-checkout"
    for source in (manifest, state, *(tmp_path / p for p in ("procedure.md", "interface.json", "evidence.md"))):
        destination = other_checkout / source.relative_to(tmp_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    portable = call({"target": str(other_checkout), "projection": "compact"})
    assert "material" not in portable
    (other_checkout / "interface.json").write_text('{"changed": true}')
    opaque = call({"target": str(other_checkout), "projection": "compact"})
    assert opaque["material"]["items"][0]["gap"] == "declaration-procedure-or-dependency-changed"
    context["task"] = "A different task observes the same repository condition"
    (tmp_path / "unrelated.md").write_text("An unrelated edit.")
    observed = call()
    assert observed["verification"]["current_evidence"]["entries"][0]["status"] == "satisfied"
    requirement = next(r for r in observed["verification"]["assurance_applicability"]["requirements"] if r["id"] == "example")
    assert requirement["status"] == "applicable"
    assert requirement["current_evidence"]["status"] == "satisfied"
    assert not any(b["code"].startswith("assurance:example:") for b in observed["decision_packet"]["blockers"])
    # Simulate interruption after publication but before the result was retained.
    (tmp_path / done["custody"]["committed"]["path"]).unlink()
    pending = call()["verification"]["current_evidence"]
    assert pending["status"] == "publication-result-unresolved"
    assert pending["entries"][0]["status"] == "unknown"
    (tmp_path / "evidence.md").write_text("Changed after interrupted publication.")
    with pytest.raises(AssertionError, match="recovery evidence changed"):
        call({"request": pending["requests"][0]})
    (tmp_path / "evidence.md").write_text("The comparison found no difference.")
    recovery = call({"request": pending["requests"][0]})
    action = next(a for a in recovery["decision_packet"]["ready_actions"] if a["operation_id"] == "verification.recover-current-evidence")
    assert call({"invocation": action})["status"] == "applied"
    assert state.read_bytes() == published
    (tmp_path / "evidence.md").write_text("A new comparison is needed.")
    assert call()["verification"]["current_evidence"]["entries"][0]["reason"] == "evidence-changed"
    manifest.write_text(header)
    retired = call()["verification"]["current_evidence"]
    assert retired["retired"] == ["example"]
    ready = call({"request": retired["requests"][0]})
    action = next(a for a in ready["decision_packet"]["ready_actions"] if a["operation_id"] == "verification.record-current-evidence")
    protection = tmp_path / ".agentic-workspace/instructions/protect-assessments.md"
    protection.parent.mkdir()
    protection.write_text(
        "---\nprotect: [.agentic-workspace/proof/current/current-evidence.json]\n---\nPreserve the current assessments.\n"
    )
    fresh_retirement = call()["verification"]["current_evidence"]["requests"][0]
    restricted = call({"request": fresh_retirement})
    assert any("effect:proof-execution" in b["affects"] for b in restricted["decision_packet"]["blockers"])
    assert all(a["operation_id"] != "verification.record-current-evidence" for a in restricted["decision_packet"]["ready_actions"])
    assert state.read_bytes() == published
    protection.unlink()
    assert call({"invocation": action})["status"] == "applied"
    assert json.loads(state.read_text())["assessments"] == {}
    assert "current_evidence" not in call()["verification"]
    assert (tmp_path / "evidence.md").read_text() == "A new comparison is needed."
    assert not (tmp_path / ".agentic-workspace/planning").exists()
    assert "material" not in call({"projection": "compact"})
