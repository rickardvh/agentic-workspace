"""Independent Rust crate participation through the ordinary public product."""

from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess

import pytest
from tests.test_native_public_cli import ROOT, consume
from tests.test_native_public_cli import native_cli as native_cli
from tests.test_shared_core import _commit_native


@pytest.fixture(scope="module")
def independent_binary(shared_core_binary):
    manifest = ROOT / "tests/fixtures/native-independent-owner/Cargo.toml"
    target = ROOT / "target/independent-owner-fixture"
    subprocess.run(
        ["cargo", "build", "--locked", "--manifest-path", str(manifest), "--target-dir", str(target)],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return target / "debug" / ("aw-independent-owner-fixture.exe" if os.name == "nt" else "aw-independent-owner-fixture")


def setup(tmp_path, binary, owner):
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_bytes(subprocess.check_output([str(binary), owner]))
    (tmp_path / "fixture-input.txt").write_text("Current bounded input.")
    return {"target": str(tmp_path), "task": "Use the independent owner", "changed": ["fixture-input.txt"]}


@pytest.fixture(scope="module")
def independent_cli(independent_binary, native_cli, tmp_path_factory):
    installation = tmp_path_factory.mktemp("independent-native-install")
    cli = installation / native_cli.name
    shutil.copy2(native_cli, cli)
    shutil.copy2(independent_binary, installation / ("agentic-workspace-core.exe" if os.name == "nt" else "agentic-workspace-core"))
    return cli


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
@pytest.mark.parametrize("projection", ["full", "compact", "carried"])
def test_multiple_ready_actions_need_no_detail_fetch(tmp_path, independent_binary, independent_cli, surface, projection, monkeypatch):
    monkeypatch.setenv("AGENTIC_WORKSPACE_CORE_BINARY", str(independent_binary))
    context = setup(tmp_path, independent_binary, "fixture-lens")
    config = tmp_path / ".agentic-workspace/config.toml"
    other = subprocess.check_output([str(independent_binary), "fixture-notebook"]).decode()
    config.write_text(config.read_text() + other[other.index("[modules.independent.") :])

    def call(**extra):
        return consume(surface, independent_binary, independent_cli, {**context, **extra}, host_path=os.environ["PATH"])

    first = call()
    requests = [first["independent_owners"][owner]["requests"][0] for owner in ("fixture-lens", "fixture-notebook")]
    for request in requests:
        request["arguments"]["text"] = "Exact independent material"
    full = call(request=requests)
    selected = call(request=requests, projection=projection)
    packet = selected["view"]["decision_packet"] if projection == "carried" else selected["decision_packet"]
    assert packet["primary_action"] is None
    assert len(packet["ready_actions"]) == 2
    assert packet["claim_boundary"] == full["decision_packet"]["claim_boundary"]
    assert packet["blockers"] == full["decision_packet"]["blockers"]
    for index, action in enumerate(packet["ready_actions"]):
        exact = full["decision_packet"]["ready_actions"][index]
        if projection == "carried":
            envelope = next(e["envelope"] for e in selected["carriage"]["envelopes"] if e["reference"] == action["reference"])
            assert envelope == exact
            result = call(invocation=selected["carriage"], reference=action["reference"])
        else:
            assert action == exact
            result = call(invocation=action)
        assert result["effects"] == exact["effects"]
        assert result["value"]["text"] == "Exact independent material"
    # Same returned envelopes are currentness-bound, including each ready ref.
    (tmp_path / "fixture-input.txt").write_text("Changed source")
    with pytest.raises(AssertionError):
        if projection == "carried":
            call(invocation=selected["carriage"], reference=packet["ready_actions"][0]["reference"])
        else:
            call(invocation=packet["ready_actions"][0])


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
@pytest.mark.parametrize("owner", ["fixture-lens", "fixture-notebook"])
def test_independent_native_owner_discovery_request_action_result(
    tmp_path, independent_binary, independent_cli, surface, owner, monkeypatch
):
    monkeypatch.setenv("AGENTIC_WORKSPACE_CORE_BINARY", str(independent_binary))
    context = setup(tmp_path, independent_binary, owner)

    def call(**extra):
        return consume(surface, independent_binary, independent_cli, {**context, **extra}, host_path=os.environ["PATH"])

    first = call()
    assert set(first["independent_owners"]) == {owner}
    request = first["independent_owners"][owner]["requests"][0]
    request["arguments"]["text"] = "Bounded owner material"
    ready = call(request=request)
    action = ready["decision_packet"]["primary_action"]
    assert action["source_owner"] == owner
    result = call(invocation=action)
    assert result["value"]["text"] == "Bounded owner material"
    assert result["value"]["source"]["text"] == "Current bounded input."
    assert call(invocation=action)["value"] == result["value"]
    if owner == "fixture-notebook":
        publication = tmp_path / action["arguments"]["publication"]["path"]
        body = json.loads(publication.read_text())
        assert body["publication"]["value"] == result["value"]
        assert result["custody"]["committed"]
        assert not (tmp_path / ".agentic-workspace/planning").exists()
        assert not (tmp_path / ".agentic-workspace/proof").exists()
    else:
        assert not (tmp_path / ".agentic-workspace/local").exists()
        assert not (tmp_path / ".agentic-workspace/modules").exists()
    quiet = call(changed=["unrelated.txt"])
    assert "independent_owners" not in quiet
    assert "fixture-lens" not in json.dumps(quiet)
    assert "fixture-notebook" not in json.dumps(quiet)


@pytest.mark.parametrize(
    "fault", ["source", "absence", "request-kind", "request-id", "actor", "destination", "removed", "revoked", "version"]
)
def test_independent_owner_reobserves_and_rejects_changed_authority(tmp_path, independent_binary, shared_core_binary, native_cli, fault):
    owner = "fixture-notebook"
    context = setup(tmp_path, independent_binary, owner)

    def call(**extra):
        return consume("json", independent_binary, native_cli, {**context, **extra})

    request = call()["independent_owners"][owner]["requests"][0]
    request["arguments"]["text"] = "Exact material"
    action = call(request=request)["decision_packet"]["primary_action"]
    extra = {"invocation": action}
    if fault == "source":
        (tmp_path / "fixture-input.txt").write_text("Opaque interval changed the source")
    elif fault == "absence":
        (tmp_path / "fixture-input.txt").unlink()
    elif fault in {"request-kind", "request-id", "actor"}:
        bad = copy.deepcopy(request)
        if fault == "request-kind":
            bad["request_kind"] = "unknown/v1"
        elif fault == "request-id":
            bad["id"] += "-caller"
        else:
            bad["arguments"]["actor"] = "trusted-human"
        extra = {"request": bad}
    elif fault == "destination":
        action["arguments"]["publication"]["path"] = ".agentic-workspace/planning/foreign.json"
    elif fault == "removed":

        def call(**extra):
            return consume("json", shared_core_binary, native_cli, {**context, **extra})
    else:
        config = tmp_path / ".agentic-workspace/config.toml"
        raw = config.read_text()
        config.write_text(
            raw.replace('revision = "fixture-v1"', 'revision = "different"')
            if fault == "version"
            else "schema_version=1\n[modules]\nenabled=[]\n"
        )
    with pytest.raises(AssertionError):
        call(**extra)
    assert not (tmp_path / ".agentic-workspace/modules").exists()
    assert not (tmp_path / ".agentic-workspace/local/effects").exists()


def test_independent_configuration_requirement_uses_current_configuration_owner(tmp_path, independent_binary, native_cli):
    from tests.test_native_planning_create import material

    context = setup(tmp_path, independent_binary, "fixture-notebook")
    config = tmp_path / ".agentic-workspace/config.toml"
    config.write_text(config.read_text().replace('label = "admitted fixture"', "").replace("enabled = []", 'enabled = ["planning"]'))

    def call(**extra):
        return consume("json", independent_binary, native_cli, {**context, **extra})

    initial = call()
    required = initial["independent_owners"]["fixture-notebook"]
    assert required["status"] == "configuration-required"
    assert initial["decision_packet"]["status"] == "blocked"
    planning = initial["planning"]["creation_requests"][0]
    planning["arguments"]["material"] = material()
    read = call(request=[required["configuration_request"], planning])
    assert read["decision_packet"]["status"] == "blocked"
    assert read["decision_packet"]["primary_action"] is None
    selected = read["configuration_write"]["selected_choice"]
    edit = selected["edit_request"]
    edit["arguments"]["value"]["fixture-notebook"]["settings"]["label"] = "Repaired by the source owner"
    proposed = call(request=edit)
    answer = proposed["decision_packet"]["decision_request"]["response_request"]
    answer["arguments"]["answer"] = "authorize-write"
    ready = call(request=[answer, planning])
    action = ready["decision_packet"]["primary_action"]
    assert action["source_owner"] == "configuration"
    assert any("effect:planning-state" in b["affects"] for b in ready["decision_packet"]["blockers"])
    call(invocation=action)
    assert call()["independent_owners"]["fixture-notebook"]["status"] == "current"
    assert not (tmp_path / ".agentic-workspace/modules").exists()


@pytest.mark.parametrize("stage", ["prepared", "published", "committed-missing"])
def test_independent_exact_carrier_recovery_preserves_original_attempt(tmp_path, independent_binary, native_cli, stage):
    context = setup(tmp_path, independent_binary, "fixture-notebook")

    def call(**extra):
        return consume("json", independent_binary, native_cli, {**context, **extra})

    request = call()["independent_owners"]["fixture-notebook"]["requests"][0]
    action = call(request=request)["decision_packet"]["primary_action"]
    result = call(invocation=action)
    destination = tmp_path / action["arguments"]["publication"]["path"]
    before = destination.read_bytes()
    if stage != "committed-missing":
        (tmp_path / result["custody"]["committed"]["path"]).unlink()
    if stage != "published":
        destination.unlink()
    if stage == "committed-missing":
        with pytest.raises(AssertionError, match="publication disappeared"):
            call(invocation=action)
        assert not destination.exists()
    else:
        replay = call(invocation=action)
        assert replay["custody"] == result["custody"]
        assert destination.read_bytes() == before


@pytest.mark.parametrize("applicable", [True, False])
def test_independent_effect_respects_exact_instruction_protection(tmp_path, independent_binary, native_cli, applicable):
    context = setup(tmp_path, independent_binary, "fixture-notebook")
    instruction = tmp_path / ".agentic-workspace/instructions/protect.md"
    instruction.parent.mkdir()
    scope = ".agentic-workspace/modules/fixture-notebook/**" if applicable else "unrelated/**"
    instruction.write_text(
        f"---\npaths: [{scope}]\nprotect: [.agentic-workspace/modules/fixture-notebook/**]\n---\nPreserve the scoped owner source.\n"
    )
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    revision = _commit_native(tmp_path)
    config = tmp_path / ".agentic-workspace/config.toml"
    config.write_text(config.read_text() + f'\n[assurance]\ninstruction_revision="{revision}"\n')

    def call(**extra):
        return consume("json", independent_binary, native_cli, {**context, **extra})

    request = call()["independent_owners"]["fixture-notebook"]["requests"][0]
    ready = call(request=request)
    if applicable:
        assert ready["decision_packet"]["primary_action"] is None
        assert any("protected-independent-write" in blocker["code"] for blocker in ready["decision_packet"]["blockers"])
    else:
        call(invocation=ready["decision_packet"]["primary_action"])


@pytest.mark.parametrize(
    "owner,reason",
    [
        ("fixture-foreign-domain", "owned domain"),
        ("fixture-claim", "without authority"),
        ("fixture-restriction", "restriction authority"),
        ("fixture-self-source", "declared input source"),
        pytest.param(
            "fixture-case-source", "declared input source", marks=pytest.mark.skipif(os.name != "nt", reason="Windows case alias")
        ),
        ("fixture-dot-source", "platform path aliases"),
        ("fixture-escape", "confined identifier"),
    ],
)
def test_independent_module_cannot_self_declare_foreign_authority_or_state(tmp_path, independent_binary, native_cli, owner, reason):
    context = setup(tmp_path, independent_binary, owner)

    def call(**extra):
        return consume("json", independent_binary, native_cli, {**context, **extra})

    with pytest.raises(AssertionError, match=reason):
        initial = call()
        call(request=initial["independent_owners"][owner]["requests"][0])
    assert not (tmp_path / ".agentic-workspace/modules").exists()
    assert not (tmp_path / ".agentic-workspace/local").exists()


def test_independent_result_enters_planning_only_through_responsible_owner(tmp_path, independent_binary, native_cli):
    from tests.test_native_planning_create import material

    context = setup(tmp_path, independent_binary, "fixture-lens")
    config = tmp_path / ".agentic-workspace/config.toml"
    config.write_text(config.read_text().replace("enabled = []", 'enabled = ["planning"]'))
    (tmp_path / "fixture-input.txt").write_text(json.dumps(material()))

    def call(**extra):
        return consume("json", independent_binary, native_cli, {**context, **extra})

    offered = call()
    module_request = offered["independent_owners"]["fixture-lens"]["requests"][0]
    module_action = call(request=module_request)["decision_packet"]["primary_action"]
    returned = call(invocation=module_action)
    assert not (tmp_path / ".agentic-workspace/planning").exists()
    owner_request = call()["planning"]["creation_requests"][0]
    owner_request["arguments"]["material"] = json.loads(returned["value"]["source"]["text"])
    owner_action = call(request=owner_request)["decision_packet"]["primary_action"]
    assert owner_action["source_owner"] == "planning"
    admitted = call(invocation=owner_action)
    assert (tmp_path / admitted["value"]["owner_path"]).exists()
    assert admitted["custody"]["attempt"]["owner"] == "planning"


def test_many_irrelevant_admissions_do_not_load_owner_detail(tmp_path, independent_binary, independent_cli):
    context = setup(tmp_path, independent_binary, "fixture-lens")
    context.update(changed=["unrelated.txt"], projection="compact")
    quiet = consume("json", independent_binary, independent_cli, context)
    config = tmp_path / ".agentic-workspace/config.toml"
    extra = "".join(
        f'\n[modules.independent.unused-{i}]\nrevision="absent"\ncontract_revision="sha256:{"0" * 64}"\nsettings={{}}\nscope=["irrelevant-{i}"]\nreads=["missing-{i}.txt"]\neffects=[]\nclaims=[]\nrestrictions=[]\n'
        for i in range(80)
    )
    config.write_text(config.read_text() + extra)
    many = consume("json", independent_binary, independent_cli, context)
    assert "unused-" not in json.dumps(many)
    assert "fixture-lens" not in json.dumps(many)
    assert len(json.dumps(many)) <= len(json.dumps(quiet)) + 256
    assert many["decision_packet"]["claim_boundary"] == quiet["decision_packet"]["claim_boundary"]
    # A previously irrelevant, uninstalled owner must become an explicit gap when selected.
    with pytest.raises(AssertionError, match="unavailable"):
        consume("json", independent_binary, independent_cli, {**context, "changed": ["irrelevant-31"]})
