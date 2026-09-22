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


def test_current_source_maintenance_has_enclave_owners_without_host_leakage(tmp_path, shared_core_binary, native_cli):
    source = json.loads((ROOT / "src/tooling/contracts/source_maintenance_surfaces.json").read_text())
    host = json.loads((ROOT / "src/core/contracts/workspace_surfaces.json").read_text())
    required = set(source["payload_files"] + source["necessary_surface_files"])
    required.update(path for paths in source["module_surface_files"].values() for path in paths)

    def inventory(target):
        context = {"target": str(target), "task": "Check current source-maintenance classification"}
        current = consume("native", shared_core_binary, native_cli, context, host_path=os.environ["PATH"])
        request = current["configuration_write"]["repository_adoption_request"]
        return consume("native", shared_core_binary, native_cli, {**context, "request": request}, host_path=os.environ["PATH"])[
            "configuration_write"
        ]["repository_adoption"]["enclave"]

    # Read the actual source checkout through the same public owner used by updates.
    current = inventory(ROOT)
    assert not required.intersection(current["removals"])
    assert all(path in current["entries"] for path in source["payload_files"])

    # The same source-only support on an ordinary host is still cleanup residue.
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    source_only = {
        row["path"]
        for row in tomllib.loads((ROOT / ".agentic-workspace/OWNERSHIP.toml").read_text())["enclave"]
        if row["owner"] == "source-maintenance"
    }
    assert source_only.isdisjoint(host["payload_files"])
    assert source_only
    for path in source_only:
        destination = tmp_path / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT / path).read_bytes())
    ledger = tmp_path / ".agentic-workspace/OWNERSHIP.toml"
    ledger.write_bytes((ROOT / "src/core/payload/.agentic-workspace/OWNERSHIP.toml").read_bytes())
    ordinary = inventory(tmp_path)
    assert source_only <= ordinary["removals"].keys()


def test_payload_inventory_reconciliation_preserves_content_and_custody(tmp_path, shared_core_binary, native_cli):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    context = {"target": str(tmp_path), "task": "Reconcile package inventory"}

    def call(**extra):
        return consume("native", shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    def propose(mode):
        read = call(request=call()["configuration_write"]["repository_adoption_request"])["configuration_write"]
        request = next(r for r in read["adoption_requests"] if r["arguments"]["mode"] == mode)
        return call(request=request)

    def action(proposal):
        answer = next(
            d for d in proposal["decision_packet"]["pending_consequences"]["decisions"] if d["id"] == "repository-adoption-authorization"
        )["response_request"]
        answer["arguments"]["answer"] = "authorize-write"
        return call(request=answer)["decision_packet"]["primary_action"]

    assert call(invocation=action(propose("adopt")))["effect_outcome"]["status"] == "committed"
    record = tmp_path / ".agentic-workspace/local/effects/adoption.prepared.json"
    previous = json.loads(record.read_text())["invocation"]["arguments"]["binding"]["state"]
    provenance = tmp_path / ".agentic-workspace/payload-provenance.json"
    expected = provenance.read_bytes()
    old = json.loads(expected)
    old["payload_files"] = []
    provenance.write_text(json.dumps(old))
    (tmp_path / ".agentic-workspace/config.toml").write_text('[payload]\ntarget_release="source-current"\npolicy="required-before-work"\n')
    skill = tmp_path / ".agentic-workspace/skills/workspace-startup/SKILL.md"
    source = skill.read_bytes()
    skill.write_bytes(source + b"\nHost customization\n")
    assert propose("reconcile-payload")["configuration_write"]["status"] == "preserved-blocked"
    skill.write_bytes(source)
    planning_skill = tmp_path / ".agentic-workspace/planning/skills/planning-assignment/SKILL.md"
    planning_source = planning_skill.read_bytes()
    planning_skill.write_bytes(planning_source + b"\nHost Planning customization\n")
    assert propose("reconcile-payload")["configuration_write"]["status"] == "preserved-blocked"
    assert planning_skill.read_bytes() == planning_source + b"\nHost Planning customization\n"
    planning_skill.write_bytes(planning_source)
    old["host_notes"] = "Preserve me"
    provenance.write_text(json.dumps(old))
    assert propose("reconcile-payload")["configuration_write"]["status"] == "preserved-blocked"
    del old["host_notes"]
    provenance.write_text(json.dumps(old))
    exact = action(propose("reconcile-payload"))
    state = exact["arguments"]["binding"]["state"]
    assert set(state["updates"]) == {".agentic-workspace/payload-provenance.json"}
    assert state["installed"] == previous["installed"]
    assert state["ownership_baseline"] == previous["ownership_baseline"]
    result = call(invocation=exact)
    assert result["effect_outcome"]["status"] == "committed"
    assert provenance.read_bytes() == expected
    assert skill.read_bytes() == source
    assert propose("reconcile-payload")["configuration_write"]["status"] == "already-current"
    assert propose("adopt")["configuration_write"]["status"] == "already-current"
    (tmp_path / result["custody"]["committed"]["path"]).unlink()
    read = call(request=call()["configuration_write"]["repository_adoption_request"])["configuration_write"]
    recovered = call(invocation=action(call(request=read["recovery_requests"][0])))
    assert recovered["effect_outcome"]["status"] == "committed"
    assert provenance.read_bytes() == expected
    assert skill.read_bytes() == source


def test_fresh_source_current_checkout_without_adoption_custody(tmp_path, shared_core_binary, native_cli):
    """Committed source projections work on a new machine, without writer custody."""

    from aw_maintainer.ownership_profile import LEDGER, PROFILE, render

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    host = json.loads((ROOT / "src/core/contracts/workspace_surfaces.json").read_text())
    for ref in [*host["payload_files"], ".agentic-workspace/payload-provenance.json"]:
        destination = tmp_path / ref
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text((ROOT / ref).read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    (tmp_path / ".agentic-workspace/config.toml").write_text('[payload]\ntarget_release="source-current"\npolicy="required-before-work"\n')
    context = {"target": str(tmp_path), "task": "Work in the fresh source checkout"}

    def call(**extra):
        return consume("native", shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    ledger = tmp_path / LEDGER
    before = ledger.read_bytes()
    reading = json.loads((tmp_path / PROFILE).read_text())
    assert (tmp_path / PROFILE).read_text() == render(ledger.read_bytes().decode(), target=tmp_path)
    assert "tools/skills/REGISTRY.json" in [ref for row in reading["entries"] for ref in row["refs"]]
    portable = json.loads((ROOT / "src/core/payload" / PROFILE).read_text())
    assert "tools/skills/REGISTRY.json" not in [ref for row in portable["entries"] for ref in row["refs"]]
    provenance = json.loads((tmp_path / ".agentic-workspace/payload-provenance.json").read_text())
    assert provenance["payload_files"] == host["payload_files"]
    for _ in range(2):
        current = call()
        assert current["configuration"]["payload"]["status"] == "satisfied"
        assert current["configuration"]["payload"]["gaps"] == []
        assert ledger.read_bytes() == before
        assert not (tmp_path / ".agentic-workspace/adoption.json").exists()
        assert not (tmp_path / ".agentic-workspace/local/effects").exists()
    # A real package-fact change still fails closed, and discovery identifies
    # its exact source rather than manufacturing a migration baseline.
    ledger.write_text(ledger.read_text().replace('path = ".agentic-workspace/memory/"', 'path = "unexpected/"'))
    invalid = call()
    assert invalid["configuration"]["payload"]["status"] == "unresolved"
    discovery = call(request=invalid["configuration_write"]["payload_discovery_request"])
    choice = next(row for row in discovery["configuration_write"]["payload_choices"] if row["source"] == LEDGER)
    assert choice["status"] == "preserved-blocked"
    assert "conflicting package ownership fact" in choice["reason"]


@pytest.mark.parametrize("change", ["unchanged", "customized", "conflict", "unknown-history"])
def test_legacy_adoption_reconciles_authenticated_history(tmp_path, shared_core_binary, native_cli, change):
    """A legacy producer held installed hashes, not a structured baseline."""
    from aw_maintainer.native_conformance import admit_stored_attempt, commit_stored_attempt
    from aw_maintainer.ownership_profile import LEDGER, PROFILE, render

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
    # Retain the legacy package-owned collision explicitly: the current source
    # ledger is now intentionally composition-compatible without prior custody.
    old_ledger = old_ledger.replace(
        'refs = [".agentic-workspace/skills/REGISTRY.json"]',
        'refs = [".agentic-workspace/skills/REGISTRY.json", "tools/skills/REGISTRY.json"]',
    )
    state["updates"][LEDGER]["after"] = old_ledger
    state["updates"][PROFILE]["after"] = render(old_ledger, target=tmp_path)
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
    portable = tomllib.loads((ROOT / "src/core/contracts/portable_ownership.toml").read_text())
    expected = copy.deepcopy(portable)
    if host_subsystems:
        expected["subsystems"] = host_subsystems
        expected["authority_surfaces"] += host_authorities
    assert tomllib.loads(ledger.read_text()) == expected
    reading = json.loads(profile.read_text())
    route = next(row for row in reading["entries"] if row["concern"] == "canonical-agent-procedure")
    assert route["refs"] == [".agentic-workspace/skills/REGISTRY.json"]
    raw = ledger.read_bytes()
    assert (
        reading["source"]["git_blob_sha1"]
        == subprocess.check_output(["git", "hash-object", f"--path={LEDGER}", "--stdin"], cwd=tmp_path, input=raw).decode().strip()
    )
    migrated = json.loads(record.read_text())["invocation"]["arguments"]["binding"]["state"]
    assert migrated["ownership_baseline"] == portable
    before = ledger.read_bytes(), profile.read_bytes()
    assert propose()["configuration_write"]["status"] == "already-current"
    assert (ledger.read_bytes(), profile.read_bytes()) == before


@pytest.mark.parametrize("customized", [False, True])
def test_host_ownership_composition_and_profile_converge(tmp_path, shared_core_binary, native_cli, customized):
    """One native journey also runs unchanged against installed release artifacts."""
    from aw_maintainer.ownership_profile import LEDGER, PROFILE, render

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    root = tmp_path / ".agentic-workspace"
    root.mkdir()
    ledger, profile = tmp_path / LEDGER, tmp_path / PROFILE
    config = root / "config.toml"
    config.write_text('[payload]\ntarget_release="source-current"\npolicy="advisory"\n')
    context = {"target": str(tmp_path), "task": "Refresh repository ownership", "changed": ["backend/service.py"]}
    (tmp_path / ".gitattributes").write_text(f"{LEDGER} text eol=lf\n", encoding="utf-8", newline="\n")
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
        ledger.write_bytes(ledger.read_text().replace("\n", "\r\n").encode())
        # Previous distributed projection is valid generated material, but bound
        # to AW's source ledger instead of this host. It must be recomputed.
        profile.write_text(render((ROOT / LEDGER).read_bytes().decode(), target=ROOT))
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
    assert (
        reading["source"]["git_blob_sha1"]
        == subprocess.check_output(["git", "hash-object", f"--path={LEDGER}", "--stdin"], cwd=tmp_path, input=raw).decode().strip()
    )
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
            == subprocess.check_output(["git", "hash-object", f"--path={LEDGER}", "--stdin"], cwd=tmp_path, input=raw).decode().strip()
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


@pytest.mark.parametrize("host_declarations", [False, True])
def test_repository_foothold_currentness_removal_and_reentry(tmp_path, shared_core_binary, native_cli, host_declarations):
    initial = consume("native", shared_core_binary, native_cli, {"target": str(tmp_path), "task": "Configure repository integration"})
    assert "repository_adoption_request" not in initial["configuration_write"]
    assert not (tmp_path / ".agentic-workspace").exists()
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    instructions = tmp_path / "AGENTS.md"
    instructions.write_text("# Repository policy\nPreserve this text.\n", encoding="utf-8")
    original_instructions = instructions.read_bytes()
    # Convergence uses current ownership, never a historical package digest.
    retired = ".agentic-workspace/obsolete-support/old.bin"
    old = tmp_path / retired
    old.parent.mkdir(parents=True, exist_ok=True)
    old.write_bytes(b"\xff\x00unknown historic support")
    unknown = tmp_path / ".agentic-workspace/unknown.txt"
    unknown.write_text("Unknown material is residue")
    preserved_state = {
        ".agentic-workspace/config.toml": b"# repository policy\n",
        ".agentic-workspace/planning/execplans/archive/history.json": b"{}",
        ".agentic-workspace/planning/assignments/current.assignment.json": b"{}",
        ".agentic-workspace/proof/receipts/source-reconciliation.json": b"{}",
        ".agentic-workspace/proof/manifests/current.json": b"{}",
        ".agentic-workspace/proof/current/source-reconciliation-current.json": b"[]",
        ".agentic-workspace/proof/current/source-reconciliation-current.json.tmp": b"[]",
        ".agentic-workspace/evaluations.json": b'{"kind":"agentic-workspace/evaluations/v1","evaluations":[]}',
        ".agentic-workspace/evaluations/history.json": b"{}",
        ".agentic-workspace/agent-aids/candidate.md": b"repo-owned candidate",
        ".agentic-workspace/example/state/current.json": b"independent state",
        ".agentic-workspace/example/support.md": b"independent support",
        ".agentic-workspace/memory/repo/domains/lesson.md": b"durable lesson",
        ".agentic-workspace/verification/evidence/proof.json": b"{}",
        ".agentic-workspace/custom/plugin/config.txt": b"custom extension",
        ".agentic-workspace/local/scratch/retained.bin": b"\xfflocal custody",
    }
    if not host_declarations:
        for ref in (
            ".agentic-workspace/agent-aids/candidate.md",
            ".agentic-workspace/example/state/current.json",
            ".agentic-workspace/example/support.md",
        ):
            del preserved_state[ref]
    for ref, content in preserved_state.items():
        path = tmp_path / ref
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    if host_declarations:
        (tmp_path / ".agentic-workspace/OWNERSHIP.toml").write_text(
            'schema_version=1\n[[authority_surfaces]]\nconcern="agent-aids"\n'
            'surface=".agentic-workspace/agent-aids/"\nowner="repo"\nownership="repo_owned"\nauthority="primary"\n'
            '[[enclave]]\npath=".agentic-workspace/example/state"\nowner="example"\n'
            'scope="subtree"\nclass="mutable-state"\nlifetime="durable"\n'
            '[[enclave]]\npath=".agentic-workspace/example/support.md"\nowner="example"\n'
            'scope="exact"\nclass="managed-support"\nlifetime="current-version"\n'
        )
    module_skill = ".agentic-workspace/memory/skills/memory-hygiene/SKILL.md"
    module_path = tmp_path / module_skill
    module_path.parent.mkdir(parents=True, exist_ok=True)
    module_path.write_bytes(b"Existing module-owned support, customized before Workspace adoption")
    stale = [
        ".agentic-workspace/proof/unowned/current.json",
        ".agentic-workspace/planning/schemas/obsolete.json",
        ".agentic-workspace/memory/skills/obsolete/prepare.py",
        ".agentic-workspace/example/obsolete.md",
        ".agentic-workspace/skills/workspace-intent-discovery/prepare.py",
        ".agentic-workspace/skills/workspace-setup-jumpstart/prepare.py",
        ".agentic-workspace/memory/skills/memory-hygiene/prepare.py",
    ]
    for ref in stale:
        path = tmp_path / ref
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("unknown support")
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel.txt"
    sentinel.write_text("untouched")
    link = tmp_path / ".agentic-workspace/unknown-link"
    if os.name == "nt":
        subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(outside)], check=True, capture_output=True)
    else:
        link.symlink_to(outside, target_is_directory=True)
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
    removals = prepared["arguments"]["binding"]["state"]["enclave"]["removals"]
    assert set([retired, ".agentic-workspace/unknown.txt", ".agentic-workspace/unknown-link", *stale]) <= set(removals)
    forged = copy.deepcopy(prepared)
    forged["arguments"]["binding"]["state"]["updates"]["AGENTS.md"]["after"] = "Forged"
    with pytest.raises(AssertionError):
        call(invocation=forged)
    result = call(invocation=prepared)
    assert result["effect_outcome"]["status"] == "committed"
    assert instructions.read_text().startswith("# Repository policy\nPreserve this text.\n")
    assert instructions.read_bytes() == original_instructions + (
        b"<!-- agentic-workspace:workflow:start -->\n"
        b"Use `.agentic-workspace/skills/workspace-startup/SKILL.md` for repository procedure; "
        b"if native skill discovery is unavailable, read it directly.\n"
        b"<!-- agentic-workspace:workflow:end -->\n"
    )
    assert instructions.read_text().count("<!-- agentic-workspace:workflow:start -->") == 1
    assert "update-observation" not in instructions.read_text()
    identity = tmp_path / ".agentic-workspace/adoption.json"
    assert identity.is_file()
    ignored = subprocess.run(
        ["git", "-C", str(tmp_path), "check-ignore", ".agentic-workspace/local/effects/adoption.prepared.json"],
        capture_output=True,
        text=True,
    )
    assert ignored.returncode == 0
    assert not old.exists()
    assert not unknown.exists() and not link.exists()
    assert sentinel.read_text() == "untouched"
    assert all((tmp_path / ref).read_bytes() == content for ref, content in preserved_state.items())
    assert all(not (tmp_path / ref).exists() for ref in stale)
    assert read()["repository_adoption"]["enclave"]["status"] == "current"
    assert module_skill not in read()["repository_adoption"]["installed"]
    assert module_path.read_bytes() == b"Existing module-owned support, customized before Workspace adoption"
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
    preserved = tmp_path / ".agentic-workspace/planning/execplans/retained.md"
    preserved.parent.mkdir(parents=True, exist_ok=True)
    preserved.write_text("Independent durable work")
    if host_declarations:
        request = next(r for r in read()["adoption_requests"] if r["arguments"]["mode"] == "remove")
        assert call(request=request)["configuration_write"]["status"] == "preserved-blocked"
        assert all((tmp_path / ref).read_bytes() == content for ref, content in preserved_state.items())
        return
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


def test_managed_fence_boundary_refresh_and_removal(tmp_path, shared_core_binary, native_cli):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    context = {"target": str(tmp_path), "task": "Refresh the managed skill pointer"}
    instructions = tmp_path / "AGENTS.md"
    start = b"<!-- agentic-workspace:workflow:start -->"
    end = b"<!-- agentic-workspace:workflow:end -->"
    prefix = "# Repository café\r\nKeep whitespace.  \n".encode()
    suffix = b"\r\n\r\nKeep this suffix without a final newline."
    canonical = (
        start + b"\nUse `.agentic-workspace/skills/workspace-startup/SKILL.md` for repository procedure; "
        b"if native skill discovery is unavailable, read it directly.\n" + end
    )

    def call(**extra):
        return consume("native", shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    def apply(mode):
        discovery = call(request=call()["configuration_write"]["repository_adoption_request"])["configuration_write"]
        request = next(r for r in discovery["adoption_requests"] if r["arguments"]["mode"] == mode)
        proposed = call(request=request)
        answer = next(
            d for d in proposed["decision_packet"]["pending_consequences"]["decisions"] if d["id"] == "repository-adoption-authorization"
        )["response_request"]
        answer["arguments"]["answer"] = "authorize-write"
        assert call(invocation=call(request=answer)["decision_packet"]["primary_action"])["effect_outcome"]["status"] == "committed"

    # Marker custody works both before adoption and on later refreshes. Interior
    # content is deliberately unrelated to any current or historical producer.
    for interior in (b"", b"arbitrary package-owned text", "\r\n# Unknown procedure\r\n秘密\n".encode()):
        instructions.write_bytes(prefix + start + interior + end + suffix)
        apply("adopt")
        assert instructions.read_bytes() == prefix + canonical + suffix
    skill_path = ".agentic-workspace/skills/workspace-startup/SKILL.md"
    skill = (tmp_path / skill_path).read_bytes()
    assert skill == (ROOT / skill_path).read_bytes()
    assert b"At runtime-capable session entry or a possible dependency change, obtain one" in skill
    assert b"ordinary `start` observation unless a sufficient current observation is held." in skill

    malformed = (start, end, end + start, start + start + end, start + end + end, start + end + start + end)
    for block in malformed:
        before = prefix + block + suffix
        instructions.write_bytes(before)
        with pytest.raises(AssertionError, match="conflicting managed fence"):
            call(request=call()["configuration_write"]["repository_adoption_request"])
        assert instructions.read_bytes() == before

    # Removal uses the same ownership boundary, without an interior preimage.
    instructions.write_bytes(prefix + start + b"\nAnother unknown interior\n" + end + suffix)
    apply("remove")
    assert instructions.read_bytes() == prefix + suffix
