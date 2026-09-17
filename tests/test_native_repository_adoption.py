"""Configuration's public foothold lifecycle preserves repository ownership."""

import copy
import hashlib
import json
import os
import subprocess
import tomllib

import pytest
from tests.test_native_public_cli import ROOT, consume
from tests.test_native_public_cli import native_cli as native_cli


@pytest.mark.parametrize("change", ["unchanged", "customized", "conflict", "unknown-history"])
def test_legacy_adoption_reconciles_authenticated_history(tmp_path, shared_core_binary, native_cli, change):
    """A legacy producer held installed hashes, not a structured baseline."""
    from agentic_workspace.decision import admit_stored_attempt, commit_stored_attempt
    from agentic_workspace.static_read_profile import LEDGER, PROFILE, render

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    context = {"target": str(tmp_path), "task": "Refresh legacy repository ownership"}

    def call(**extra):
        return consume("native", shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    def propose():
        discovery = call(request=call()["configuration_write"]["repository_adoption_request"])["configuration_write"]
        request = next(r for r in discovery["adoption_requests"] if r["arguments"]["mode"] == "adopt")
        return call(request=request)

    def authorize(proposed):
        answer = next(
            d for d in proposed["decision_packet"]["pending_consequences"]["decisions"] if d["id"] == "repository-adoption-authorization"
        )["response_request"]
        answer["arguments"]["answer"] = "authorize-write"
        return call(request=answer)["decision_packet"]["primary_action"]

    # Model the old producer through the real immutable attempt store. This is
    # fixture construction, not an edit of already-authenticated custody files.
    legacy = authorize(propose())
    state = legacy["arguments"]["binding"]["state"]
    del state["ownership_baseline"]
    old_ledger = (ROOT / LEDGER).read_text(encoding="utf-8")
    state["updates"][LEDGER]["after"] = old_ledger
    state["updates"][PROFILE]["after"] = render(old_ledger)
    for path, update in state["updates"].items():
        if update["after"] is not None:
            output = tmp_path / path
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(update["after"].encode())
            if path in state["installed"]:
                state["installed"][path] = "sha256:" + hashlib.sha256(output.read_bytes()).hexdigest()
    if change == "unknown-history":
        # No trusted postimage matching the installed identity is available.
        state["updates"][LEDGER]["after"] = "schema_version=1\n"
    admission = admit_stored_attempt(str(tmp_path), {"ready_actions": [legacy]}, legacy)
    committed = commit_stored_attempt(
        str(tmp_path),
        admission["custody"],
        {
            "status": "applied",
            "effects": ["configuration-source"],
            "value": {"kind": "agentic-workspace/repository-adoption-result/v1", "mode": "adopt", "completion_authority": False},
        },
    )
    record = tmp_path / ".agentic-workspace/local/effects/adoption.prepared.json"
    record.write_text(json.dumps({"invocation": legacy, "custody": committed["custody"]}))
    ledger, profile = tmp_path / LEDGER, tmp_path / PROFILE
    host_subsystems = []
    host_authorities = []
    if change == "customized":
        customized = old_ledger.replace("proof = [", 'proof = ["host-test", ', 1)
        customized += (
            '\n[[subsystems]]\nid="backend"\npaths=["backend/**"]\nowns=["host API"]\n'
            'does_not_own=["frontend"]\nproof=["host-test backend"]\nescalate_when=["API changes"]\n'
            '[[authority_surfaces]]\nconcern="host-api"\nsurface="docs/api.md"\n'
            'owner="repo"\nownership="repo_owned"\nauthority="primary"\n'
            'read={refs=["docs/api.md"],select="Read the host API",unknown=["runtime"]}\n'
        )
        ledger.write_bytes(customized.encode())
        host = tomllib.loads(customized)
        host_subsystems = [host["subsystems"][0], host["subsystems"][-1]]
        host_authorities = [host["authority_surfaces"][-1]]
    elif change == "conflict":
        ledger.write_text(old_ledger.replace('path = ".agentic-workspace/memory/"', 'path = "unexpected/"'))
    elif change == "unknown-history":
        ledger.write_bytes(ledger.read_bytes() + b"\n# Host customization after RC3 adoption\n")
    if change in ("conflict", "unknown-history"):
        before = ledger.read_bytes()
        assert propose()["configuration_write"]["status"] == "preserved-blocked"
        assert ledger.read_bytes() == before
        return
    assert call(invocation=authorize(propose()))["effect_outcome"]["status"] == "committed"
    portable = tomllib.loads((ROOT / "src/agentic_workspace/contracts/portable_ownership.toml").read_text())
    expected = copy.deepcopy(portable)
    if host_subsystems:
        expected["subsystems"] = host_subsystems
        expected["authority_surfaces"] += host_authorities
    assert tomllib.loads(ledger.read_text()) == expected
    reading = json.loads(profile.read_text())
    route = next(row for row in reading["entries"] if row["concern"] == "canonical-agent-procedure")
    assert route["refs"] == [".agentic-workspace/skills/REGISTRY.json"]
    raw = ledger.read_bytes()
    assert reading["source"]["git_blob_sha1"] == hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    migrated = json.loads(record.read_text())["invocation"]["arguments"]["binding"]["state"]
    assert migrated["ownership_baseline"] == portable
    before = ledger.read_bytes(), profile.read_bytes()
    assert propose()["configuration_write"]["status"] == "already-current"
    assert (ledger.read_bytes(), profile.read_bytes()) == before


@pytest.mark.parametrize("customized", [False, True])
def test_host_ownership_composition_and_profile_converge(tmp_path, shared_core_binary, native_cli, customized):
    """One native journey also runs unchanged against installed release artifacts."""
    from agentic_workspace.static_read_profile import LEDGER, PROFILE, render

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    root = tmp_path / ".agentic-workspace"
    root.mkdir()
    ledger, profile = tmp_path / LEDGER, tmp_path / PROFILE
    config = root / "config.toml"
    config.write_text('[payload]\ntarget_release="source-current"\npolicy="advisory"\n')
    context = {"target": str(tmp_path), "task": "Refresh repository ownership", "changed": ["backend/service.py"]}
    preserved = {}
    if customized:
        ledger.write_text(
            'schema_version=1\n[[subsystems]]\nid="backend"\npaths=["backend/**"]\n'
            'owns=["host API"]\ndoes_not_own=["user interface"]\nproof=["host-test backend"]\n'
            'escalate_when=["API changes"]\n[[authority_surfaces]]\nconcern="host-api"\n'
            'surface="docs/api.md"\nowner="repo"\nownership="repo_owned"\nauthority="primary"\n'
            'read={refs=["docs/api.md"],select="Read the host API contract",unknown=["runtime compatibility"]}\n'
        )
        host = tomllib.loads(ledger.read_text())
        # Previous distributed projection is valid generated material, but bound
        # to AW's source ledger instead of this host. It must be recomputed.
        profile.write_text(render((ROOT / LEDGER).read_text()))
        verification = root / "verification/manifest.toml"
        verification.parent.mkdir()
        verification.write_text(
            'schema_version="agentic-workspace/verification-manifest/v1"\n'
            '[assurance.proof_profiles.host]\nrequired_commands=["host-test backend"]\n'
            '[assurance.subsystem_profiles.backend]\nassurance_level="high"\n'
            'force="required-before-closeout"\nscope_refs=["ownership.subsystems.backend"]\nproof_profile="host"\n'
        )
        intent = root / "system-intent/subsystems.toml"
        intent.parent.mkdir()
        intent.write_text(
            'schema_version=1\nkind="agentic-workspace/subsystem-intent-set/v1"\n'
            '[[subsystems]]\nid="backend"\nscope="backend/**"\nstatus="active"\nsummary="Preserve the host API"\n'
            'governing_intents=["Preserve API compatibility"]\nneeds_review=false\n'
        )
        preserved = {p: p.read_bytes() for p in [verification, intent]}

    def call(**extra):
        return consume("native", shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    def payload():
        return call(request=call()["configuration_write"]["payload_discovery_request"])["configuration_write"]["payload_choices"]

    if customized:
        for path in [LEDGER, PROFILE]:
            choice = next(row for row in payload() if row["source"] == path)
            proposed = call(request=choice["request"])
            post = proposed["configuration_write"]["proposal"]["postimage"]
            if path == LEDGER:
                assert tomllib.loads(post)["subsystems"] == host["subsystems"]
            answer = next(d for d in proposed["decision_packet"]["pending_consequences"]["decisions"] if d["owner"] == "configuration")[
                "response_request"
            ]
            answer["arguments"]["answer"] = "authorize-write"
            result = call(invocation=call(request=answer)["decision_packet"]["primary_action"])
            assert result["effect_outcome"]["status"] == "committed"

    def adopt():
        read = call(request=call()["configuration_write"]["repository_adoption_request"])["configuration_write"]
        request = next(r for r in read["adoption_requests"] if r["arguments"]["mode"] == "adopt")
        return call(request=request)

    proposed = adopt()
    answer = next(
        d for d in proposed["decision_packet"]["pending_consequences"]["decisions"] if d["id"] == "repository-adoption-authorization"
    )["response_request"]
    answer["arguments"]["answer"] = "authorize-write"
    assert call(invocation=call(request=answer)["decision_packet"]["primary_action"])["effect_outcome"]["status"] == "committed"
    actual = tomllib.loads(ledger.read_text())
    reading = json.loads(profile.read_text())
    raw = ledger.read_bytes()
    assert reading["source"]["git_blob_sha1"] == hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if customized:
        assert actual["subsystems"] == host["subsystems"]
        assert next(row for row in actual["authority_surfaces"] if row["concern"] == "host-api") == host["authority_surfaces"][0]
        assert next(row for row in reading["entries"] if row["concern"] == "host-api")["refs"] == ["docs/api.md"]
        assert all(path.read_bytes() == before for path, before in preserved.items())
        assert {row["id"] for row in tomllib.loads(intent.read_text())["subsystems"]} <= {row["id"] for row in actual["subsystems"]}
        assert call()["verification"]["assurance_applicability"]["requirements"][0]["id"] == "subsystem:backend"
    else:
        assert not actual.get("subsystems")
    before = {path: path.read_bytes() for path in [ledger, profile, root / "adoption.json"]}
    assert adopt()["configuration_write"]["status"] == "already-current"
    assert all(row["status"] == "current" for row in payload())
    assert all(path.read_bytes() == raw for path, raw in before.items())
    if customized:
        stale_profile = next(row["request"] for row in payload() if row["source"] == PROFILE)
        ledger.write_bytes(ledger.read_bytes() + "\r\n# Host note: café\r\n".encode())
        with pytest.raises(AssertionError, match="stale|changed"):
            call(request=stale_profile)
        # Customization after adoption remains legitimate; old whole-file custody
        # is not required to update the derived profile and integration identity.
        changed = adopt()
        answer = next(
            d for d in changed["decision_packet"]["pending_consequences"]["decisions"] if d["id"] == "repository-adoption-authorization"
        )["response_request"]
        answer["arguments"]["answer"] = "authorize-write"
        assert call(invocation=call(request=answer)["decision_packet"]["primary_action"])["effect_outcome"]["status"] == "committed"
        assert ledger.read_bytes().endswith("# Host note: café\r\n".encode())
        raw = ledger.read_bytes()
        assert (
            json.loads(profile.read_text())["source"]["git_blob_sha1"]
            == hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        )
        assert adopt()["configuration_write"]["status"] == "already-current"
        current_profile = profile.read_bytes()
        edited = json.loads(current_profile)
        edited["authority"] = "User-owned instructions"
        profile.write_text(json.dumps(edited))
        assert next(row for row in payload() if row["source"] == PROFILE)["status"] == "preserved-blocked"
        assert adopt()["configuration_write"]["status"] == "preserved-blocked"
        profile.write_bytes(current_profile)
    # Even an authenticated adoption never grants blanket replacement authority.
    ledger.write_text(ledger.read_text().replace('path = ".agentic-workspace/memory/"', 'path = "unexpected/"'))
    blocked = next(row for row in payload() if row["source"] == LEDGER)
    assert blocked["status"] == "preserved-blocked" and "request" not in blocked
    assert adopt()["configuration_write"]["status"] == "preserved-blocked"


def test_repository_foothold_currentness_removal_and_reentry(tmp_path, shared_core_binary, native_cli):
    initial = consume("native", shared_core_binary, native_cli, {"target": str(tmp_path), "task": "Configure repository integration"})
    assert "repository_adoption_request" not in initial["configuration_write"]
    assert not (tmp_path / ".agentic-workspace").exists()
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    instructions = tmp_path / "AGENTS.md"
    instructions.write_text("# Repository policy\nPreserve this text.\n", encoding="utf-8")
    # A former mirror converges only exact known package bytes.
    contract = json.loads((ROOT / "src/agentic_workspace/contracts/workspace_surfaces.json").read_text())
    retired = contract["retired_package_surfaces"][0]["path"]
    old = tmp_path / retired
    old.parent.mkdir(parents=True, exist_ok=True)
    old.write_bytes((ROOT / "src/agentic_workspace/_payload" / retired).read_bytes())
    unknown = tmp_path / ".agentic-workspace/unknown.txt"
    unknown.write_text("Preserve unknown material")
    context = {"target": str(tmp_path), "task": "Configure repository integration"}

    def call(**extra):
        return consume("native", shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    def read():
        request = call()["configuration_write"]["repository_adoption_request"]
        return call(request=request)["configuration_write"]

    def action(mode):
        discovery = read()
        request = next(r for r in discovery["adoption_requests"] if r["arguments"]["mode"] == mode)
        proposed = call(request=request)
        decisions = proposed["decision_packet"]["pending_consequences"]["decisions"]
        answer = next(d for d in decisions if d["id"] == "repository-adoption-authorization")["response_request"]
        answer["arguments"]["answer"] = "authorize-write"
        return call(request=answer)["decision_packet"]["primary_action"]

    assert read()["status"] == "unadopted"
    prepared = action("adopt")
    forged = copy.deepcopy(prepared)
    forged["arguments"]["binding"]["state"]["updates"]["AGENTS.md"]["after"] = "Forged"
    with pytest.raises(AssertionError):
        call(invocation=forged)
    result = call(invocation=prepared)
    assert result["effect_outcome"]["status"] == "committed"
    assert instructions.read_text().startswith("# Repository policy\nPreserve this text.\n")
    identity = tmp_path / ".agentic-workspace/adoption.json"
    assert identity.is_file()
    ignored = subprocess.run(
        ["git", "-C", str(tmp_path), "check-ignore", ".agentic-workspace/local/effects/adoption.prepared.json"],
        capture_output=True,
        text=True,
    )
    assert ignored.returncode == 0
    assert not old.exists()
    assert unknown.read_text() == "Preserve unknown material"
    assert not (tmp_path / ".agentic-workspace/config.toml").exists()
    assert not (tmp_path / ".agentic-workspace/planning").exists()
    request = next(r for r in read()["adoption_requests"] if r["arguments"]["mode"] == "adopt")
    assert call(request=request)["configuration_write"]["status"] == "already-current"
    # Lost outcome evidence recovers without replaying published files.
    (tmp_path / result["custody"]["committed"]["path"]).unlink()
    partial = tmp_path / ".agentic-workspace/skills/workspace-startup/SKILL.md"
    expected = partial.read_bytes()
    partial.unlink()
    recovery = read()["recovery_requests"][0]
    proposed = call(request=recovery)
    answer = next(
        d for d in proposed["decision_packet"]["pending_consequences"]["decisions"] if d["id"] == "repository-adoption-authorization"
    )["response_request"]
    answer["arguments"]["answer"] = "authorize-write"
    recovered = call(invocation=call(request=answer)["decision_packet"]["primary_action"])
    assert recovered["effect_outcome"]["status"] == "committed"
    assert partial.read_bytes() == expected

    def exposure(mode):
        request = call()["configuration_write"]["skill_exposure_request"]
        row = next(
            row for row in call(request=request)["configuration_write"]["skill_exposure"] if row["state"]["name"] == "workspace-startup"
        )
        proposed = call(request=row[mode + "_request"])
        answer = proposed["configuration_write"]["authorization_request"]
        answer["arguments"]["answer"] = "authorize-write"
        return call(invocation=call(request=answer)["decision_packet"]["primary_action"])

    assert exposure("expose")["effect_outcome"]["status"] == "committed"
    request = next(r for r in read()["adoption_requests"] if r["arguments"]["mode"] == "remove")
    assert call(request=request)["configuration_write"]["status"] == "remove-owned-skill-exposures-first"
    assert exposure("remove")["effect_outcome"]["status"] == "committed"
    preserved = tmp_path / ".agentic-workspace/planning/retained.md"
    preserved.parent.mkdir()
    preserved.write_text("Independent durable work")
    removed = call(invocation=action("remove"))
    assert removed["effect_outcome"]["status"] == "committed"
    assert not identity.exists()
    assert preserved.read_text() == "Independent durable work"
    assert "Preserve this text." in instructions.read_text()
    assert "agentic-workspace:workflow" not in instructions.read_text()
    # Deliberate re-adoption needs no removal tombstone or registry reset.
    assert call(invocation=action("adopt"))["effect_outcome"]["status"] == "committed"
    skill = tmp_path / ".agentic-workspace/skills/workspace-startup/SKILL.md"
    skill.write_text(skill.read_text() + "\nUser edits\n")
    removal = next(r for r in read()["adoption_requests"] if r["arguments"]["mode"] == "remove")
    blocked = call(request=removal)["configuration_write"]
    assert blocked["status"] == "preserved-blocked"
    assert any("edited or unowned" in b for b in blocked["repository_adoption"]["blockers"])
    assert skill.read_text().endswith("User edits\n")
