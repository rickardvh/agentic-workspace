"""Repository plugin projections preserve fragment custody and independent hosts."""

import copy
import json
import os
import subprocess
import tomllib

import pytest
from tests.test_native_public_cli import ROOT, consume
from tests.test_native_public_cli import native_cli as native_cli


def plugin_host(target, core, cli):
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    context = {"target": str(target), "task": "Adopt repository entry plugins"}

    def call(**extra):
        return consume("native", core, cli, {**context, **extra}, host_path=os.environ["PATH"])

    def apply(request):
        request = copy.deepcopy(request)
        request["arguments"]["answer"] = "authorize-write"
        if request["arguments"].get("mode") == "remove" and request["request_kind"].endswith("repository-adoption/v1"):
            request["arguments"]["disposition"] = "preserve"
        ready = call(request=request)
        action = ready["decision_packet"]["primary_action"]
        assert action, ready
        return call(invocation=action)

    def adoption(mode):
        view = call(request=call()["configuration_write"]["repository_adoption_request"])["configuration_write"]
        return next(r for r in view["adoption_requests"] if r["arguments"]["mode"] == mode)

    def row(host):
        return next(
            r
            for r in call(request=call()["configuration_write"]["plugin_exposure_request"])["configuration_write"]["plugin_exposure"]
            if r["state"]["host"] == host
        )

    apply(adoption("adopt"))
    return call, apply, adoption, row


@pytest.mark.parametrize("host", ["codex", "claude-project", "claude-local"])
def test_repository_lifecycle_fragment_custody_and_fallback(tmp_path, shared_core_binary, native_cli, host):
    call, apply, adoption, row = plugin_host(tmp_path, shared_core_binary, native_cli)
    bundle = tmp_path / ".agentic-workspace/plugins/agentic-workspace-entry"
    assert (bundle / "skills/agentic-workspace-entry/SKILL.md").read_bytes() == (
        ROOT / "src/adapters/skill-entry/SKILL.md"
    ).read_bytes().replace(b"\r\n", b"\n")
    if host == "codex":
        catalogue = tmp_path / ".agents/plugins/marketplace.json"
        catalogue.parent.mkdir(parents=True)
        catalogue.write_text(
            json.dumps(
                {
                    "name": "team",
                    "plugins": [{"name": "unrelated", "source": {"source": "local", "path": "./other"}}],
                    "description": "Keep me",
                }
            )
        )
        settings = tmp_path / ".codex/config.toml"
        settings.parent.mkdir()
        settings.write_text('# Keep this comment\nmodel = "existing"\n')
    else:
        settings = tmp_path / (".claude/settings.local.json" if host == "claude-local" else ".claude/settings.json")
        settings.parent.mkdir()
        if host == "claude-local":
            (tmp_path / ".git/info/exclude").write_text(".claude/settings.local.json\n")
        settings.write_text(json.dumps({"permissions": {"allow": ["Read"]}, "enabledPlugins": {"other@team": True}}))
    state = row(host)
    stale = state["expose_request"]
    apply(stale)
    state = row(host)
    assert state["state"]["status"] == "owned", state
    assert state["state"]["updates"] == {}, state
    assert call(request=adoption("remove"))["configuration_write"]["status"] == "remove-owned-plugin-exposures-first"
    # An unrelated edit is preserved by fragment-level refresh/removal.
    if host == "codex":
        settings.write_text(settings.read_text() + "\n[features]\nweb_search = false\n")
        assert "# Keep this comment" in settings.read_text()
    else:
        data = json.loads(settings.read_text())
        data["newUserSetting"] = "preserved"
        settings.write_text(json.dumps(data))
        assert not (tmp_path / (".claude/settings.json" if host == "claude-local" else ".claude/settings.local.json")).exists()
    with pytest.raises(AssertionError, match="changed"):
        call(request=stale)
    apply(row(host)["expose_request"])
    assert call(request=row(host)["expose_request"])["configuration_write"]["status"] == "unchanged"
    apply(row(host)["remove_request"])
    assert (tmp_path / "AGENTS.md").read_text().find("workspace-startup/SKILL.md") >= 0
    assert (tmp_path / ".agentic-workspace/skills/workspace-startup/SKILL.md").is_file()
    if host == "codex":
        data = tomllib.loads(settings.read_text())
        assert data["model"] == "existing" and not data.get("plugins")
        assert data["features"]["web_search"] is False
        assert json.loads(catalogue.read_text())["plugins"] == [{"name": "unrelated", "source": {"source": "local", "path": "./other"}}]
    else:
        data = json.loads(settings.read_text())
        assert data["enabledPlugins"] == {"other@team": True}
        assert data["newUserSetting"] == "preserved"
        assert not data.get("extraKnownMarketplaces")
        assert not (tmp_path / ".agentic-workspace/plugins/.claude-plugin/marketplace.json").exists()
    apply(adoption("remove"))
    assert not bundle.joinpath("plugin.json").exists()


def test_unowned_matching_and_modified_plugin_fields_fail_closed(tmp_path, shared_core_binary, native_cli):
    call, apply, adoption, row = plugin_host(tmp_path, shared_core_binary, native_cli)
    planned = row("codex")
    catalogue = tmp_path / ".agents/plugins/marketplace.json"
    catalogue.parent.mkdir(parents=True)
    # Matching bytes do not transfer custody.
    catalogue.write_text(planned["state"]["updates"][".agents/plugins/marketplace.json"]["after"])
    assert row("codex")["state"]["status"] == "preserved-blocked"
    catalogue.unlink()
    apply(row("codex")["expose_request"])
    settings = tmp_path / ".codex/config.toml"
    settings.write_text(settings.read_text().replace("enabled = true", "enabled = false"))
    assert row("codex")["state"]["status"] == "preserved-blocked"
    assert call(request=adoption("remove"))["configuration_write"]["status"] == "remove-owned-plugin-exposures-first"
    assert bundle_exists(tmp_path)


def bundle_exists(root):
    return (root / ".agentic-workspace/plugins/agentic-workspace-entry/plugin.json").is_file()


def test_local_scope_requires_checkout_ignore_and_never_promotes(tmp_path, shared_core_binary, native_cli):
    call, apply, _, row = plugin_host(tmp_path, shared_core_binary, native_cli)
    subprocess.run(["git", "-C", str(tmp_path), "config", "core.excludesFile", str(tmp_path / "empty-global-ignore")], check=True)
    (tmp_path / ".git/info/exclude").write_text("")
    request = row("claude-local")["expose_request"]
    assert call(request=request)["configuration_write"]["status"] == "local-settings-ignore-required"
    assert not (tmp_path / ".claude").exists()
    (tmp_path / ".git/info/exclude").write_text(".claude/settings.local.json\n")
    settings = tmp_path / ".claude/settings.local.json"
    settings.parent.mkdir()
    settings.write_text("{}\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-f", ".claude/settings.local.json"], check=True)
    assert call(request=row("claude-local")["expose_request"])["configuration_write"]["status"] == "local-settings-ignore-required"
    assert json.loads(settings.read_text()) == {}
    subprocess.run(["git", "-C", str(tmp_path), "rm", "--cached", "-f", ".claude/settings.local.json"], check=True)
    apply(row("claude-local")["expose_request"])
    assert row("claude-project")["state"]["status"] == "preserved-blocked"
    assert not (tmp_path / ".claude/settings.json").exists()


@pytest.mark.parametrize("published", [0, 1, 2])
def test_interrupted_projection_recovers_exact_remaining_files(tmp_path, shared_core_binary, native_cli, published):
    from aw_maintainer.native_conformance import admit_stored_attempt

    call, apply, _, row = plugin_host(tmp_path, shared_core_binary, native_cli)
    request = row("codex")["expose_request"]
    request["arguments"]["answer"] = "authorize-write"
    ready = call(request=request)
    action = ready["decision_packet"]["primary_action"]
    admission = admit_stored_attempt(str(tmp_path), ready["decision_packet"], action)
    record = tmp_path / ".agentic-workspace/local/effects/plugin-exposure-codex.json"
    record.write_text(json.dumps({"invocation": action, "custody": admission["custody"]}))
    updates = action["arguments"]["binding"]["state"]["updates"]
    for path, update in list(updates.items())[:published]:
        destination = tmp_path / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(update["after"], newline="\n")
    observed = row("codex")
    assert observed["state"]["status"] == "recovery-required"
    assert call(request=observed["expose_request"])["configuration_write"]["status"] == "recovery-required"
    assert apply(observed["recovery_request"])["effect_outcome"]["status"] == "committed"
    for path, update in updates.items():
        assert (tmp_path / path).read_text() == update["after"]
    assert row("codex")["state"]["status"] == "owned"


def test_two_repositories_refresh_only_the_selected_bundle(tmp_path, shared_core_binary, native_cli):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    _, apply_a, _, row_a = plugin_host(a, shared_core_binary, native_cli)
    _, apply_b, _, row_b = plugin_host(b, shared_core_binary, native_cli)
    for host in ["codex", "claude-project"]:
        apply_a(row_a(host)["expose_request"])
        apply_b(row_b(host)["expose_request"])
        assert row_a(host)["state"]["selector"] != row_b(host)["state"]["selector"]
    before_b = {p.relative_to(b): p.read_bytes() for p in b.rglob("*") if p.is_file() and ".git" not in p.parts}
    path = a / ".agentic-workspace/plugins/agentic-workspace-entry/skills/agentic-workspace-entry/SKILL.md"
    path.write_text(path.read_text() + "\nA distinct installed revision.\n")
    assert row_a("codex")["state"]["bundle_revision"] != row_b("codex")["state"]["bundle_revision"]
    assert row_a("codex")["state"]["refresh_needed"] is True
    assert row_b("codex")["state"]["host_actions"] == []
    apply_a(row_a("codex")["expose_request"])
    after_b = {p.relative_to(b): p.read_bytes() for p in b.rglob("*") if p.is_file() and ".git" not in p.parts}
    assert before_b == after_b


@pytest.mark.parametrize("scope", ["repository", "machine-local"])
def test_source_checkout_reassessment_unlocks_only_exact_provenance_repair(tmp_path, shared_core_binary, native_cli, scope):
    call, apply, adoption, _ = plugin_host(tmp_path, shared_core_binary, native_cli)
    workspace = tmp_path / ".agentic-workspace"
    (workspace / "config.toml").write_text('[payload]\ntarget_release="source-current"\npolicy="required-before-work"\n')
    declaration = tmp_path / "src/core/contracts/workspace_surfaces.json"
    declaration.parent.mkdir(parents=True)
    declaration.write_bytes((ROOT / "src/core/contracts/workspace_surfaces.json").read_bytes())

    def assessment():
        request = call()["configuration_write"]["setup_assessment"]["request"]
        request["arguments"]["scope"] = scope
        return call(request=request)["configuration_write"]["setup_assessment"]

    old = assessment()["record_request"]["arguments"]["value"]
    old.update(
        runtime_version="1.3.2",
        coverage="Preceding maintainer setup assessment",
        dispositions=[{"subject": "Optional setup", "status": "excluded", "reason": "Fixture has no optional capabilities."}],
    )
    path = workspace / ("local/configuration-assessment.json" if scope == "machine-local" else "configuration-assessment.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(old))
    before = path.read_bytes()
    provenance = workspace / "payload-provenance.json"
    original = json.loads(provenance.read_text())
    stale = copy.deepcopy(original)
    stale["payload_files"] = []
    provenance.write_text(json.dumps(stale))
    assert call(request=adoption("reconcile-payload"))["configuration_write"]["status"] == "preserved-blocked"
    offered = assessment()
    assert offered["status"] == "source-reassessment-required"
    request = offered["record_request"]
    with pytest.raises(AssertionError, match="reassessment reason"):
        call(request=request)
    assert path.read_bytes() == before

    # A source-current label alone cannot admit an edited source, newer installed
    # package or unknown assessment format/fields.
    startup = workspace / "skills/workspace-startup/SKILL.md"
    body = startup.read_bytes()
    startup.write_bytes(body + b"\nUnowned edit\n")
    assert "record_request" not in assessment()
    startup.write_bytes(body)
    newer = copy.deepcopy(stale)
    newer["release_identity"]["version"] = "99.0.0"
    provenance.write_text(json.dumps(newer))
    assert "record_request" not in assessment()
    provenance.write_text(json.dumps(stale))
    path.write_text(json.dumps({**old, "future_field": "preserve"}))
    assert "record_request" not in assessment()
    path.write_bytes(before)

    request = assessment()["record_request"]
    request["arguments"]["value"]["coverage"] = "Reassessed the delivered source checkout material; no new optional setup is required."
    request["arguments"]["value"]["source_reassessment"]["reason"] = (
        "The package is already the current development artifact; only its earlier released-build assessment needs renewal."
    )
    result = call(invocation=call(request=request)["decision_packet"]["primary_action"])
    assert result["effect_outcome"]["status"] == "committed"
    saved = json.loads(path.read_text())
    assert saved["runtime_version"] == "0.0.0-dev.0"
    assert "source_reassessment" not in saved
    # Reassessment itself does not publish provenance or lift the package gate.
    assert json.loads(provenance.read_text()) == stale
    assert call()["configuration"]["payload"]["status"] == "unresolved"
    assert apply(adoption("reconcile-payload"))["effect_outcome"]["status"] == "committed"
    assert call()["configuration"]["payload"]["status"] == "satisfied"
