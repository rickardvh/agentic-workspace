"""One native lifecycle proves standing assessments, custody and currentness."""

from __future__ import annotations

import json
import time

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli


@pytest.mark.parametrize("detail_route", ["measurement:latency", "uv run pytest tests/test_latency.py -q"])
def test_standing_assessment_publication_recovery_and_retirement(tmp_path, shared_core_binary, native_cli, detail_route):
    manifest = tmp_path / ".agentic-workspace/verification/manifest.toml"
    manifest.parent.mkdir(parents=True)
    header = 'schema_version = "agentic-workspace/verification-manifest/v1"\n'
    manifest.write_text(
        header + "[assurance.requirements.example]\n"
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
    context = {"target": str(tmp_path), "task": "Assess the declared example obligation"}

    def call(extra=None):
        return consume("native", shared_core_binary, native_cli, {**context, **(extra or {})})

    initial = call()["verification"]["current_evidence"]
    assert initial["entries"][0]["status"] == "due"
    assert initial["entries"][0]["declaration"]["detail_route"] == detail_route
    request = initial["requests"][0]
    request["arguments"].update(
        observed_at=int(time.time()), outcome="satisfied", reason="Compared the current sources.", evidence_refs=["evidence.md"]
    )
    proposed = call({"request": request})
    decision = next(q for q in proposed["decision_packet"]["pending_consequences"]["decisions"] if q["id"] == "current-evidence-assessment")
    answer = decision["response_request"]
    answer["arguments"]["answer"] = "confirm"
    ready = call({"request": answer})
    action = next(a for a in ready["decision_packet"]["ready_actions"] if a["operation_id"] == "verification.record-current-evidence")
    done = call({"invocation": action})
    assert done["status"] == "applied", done
    state = tmp_path / ".agentic-workspace/proof/current/current-evidence.json"
    published = state.read_bytes()
    observed = call()
    assert observed["verification"]["current_evidence"]["entries"][0]["status"] == "satisfied"
    requirement = next(r for r in observed["verification"]["assurance_applicability"]["requirements"] if r["id"] == "example")
    assert requirement["status"] == "applicable"
    assert requirement["current_evidence"]["status"] == "satisfied"
    assert not any(b["code"].startswith("assurance:example:") for b in observed["decision_packet"]["blockers"])
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
    assert (tmp_path / "evidence.md").read_text() == "A new comparison is needed."
    assert not (tmp_path / ".agentic-workspace/planning").exists()
