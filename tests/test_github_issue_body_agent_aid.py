import copy
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest
import yaml

_MODULE_PATH = (
    Path(__file__).resolve().parents[1] / ".agentic-workspace" / "agent-aids" / "scripts" / "github-issue-body" / "new_github_issue_body.py"
)
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("new_github_issue_body", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
issue_body = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = issue_body
_SPEC.loader.exec_module(issue_body)


def test_issue_templates_include_completion_boundary_fields() -> None:
    required_fields = {
        "intended_outcome",
        "acceptance",
        "non_solutions",
        "final_satisfaction",
        "evidence_required_for_final_completion",
        "completion_rule",
    }

    for template_path in sorted((_REPO_ROOT / ".github" / "ISSUE_TEMPLATE").glob("*.yml")):
        if template_path.name == "config.yml":
            continue
        payload = yaml.safe_load(template_path.read_text(encoding="utf-8"))
        field_ids = {
            str(item.get("id", "")) for item in payload.get("body", []) if isinstance(item, dict) and item.get("type") != "markdown"
        }
        assert required_fields.issubset(field_ids), template_path


def test_pull_request_template_prompts_completion_audit() -> None:
    template = (_REPO_ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md").read_text(encoding="utf-8")

    assert "## Completion audit" in template
    assert "This PR makes the issue's intended outcome true in the ordinary path." in template
    assert "Any remaining old behavior is explicitly allowed by the issue acceptance criteria." in template
    assert "documentation, inventory, reclassification, or a follow-up plan" in template


def test_issue_creation_semantic_route_resolves_canonical_skills_and_current_template() -> None:
    registry = json.loads((_REPO_ROOT / "tools/skills/REGISTRY.json").read_text(encoding="utf-8"))
    routed = []
    for skill in registry["skills"]:
        for declaration in skill.get("semantic_routes", []):
            if declaration.get("id") == "github/issues/create":
                routed.append((declaration["priority"], skill["id"]))
    assert sorted(routed) == [(10, "github-issue-shaping"), (20, "github-issue-creation")]

    instruction = (_REPO_ROOT / ".agentic-workspace/instructions/github-issue-creation.md").read_text(encoding="utf-8")
    assert "routes:\n  - github/issues/create" in instruction
    assert "github-issue-shaping" in instruction
    assert "github-issue-creation" in instruction


def _request(kind="direction"):
    template = yaml.safe_load((_REPO_ROOT / ".github/ISSUE_TEMPLATE" / issue_body.TEMPLATE_BY_KIND[kind]).read_text(encoding="utf-8"))
    fields = {}
    for item in template["body"]:
        if item.get("type") == "markdown":
            continue
        attributes = item["attributes"]
        value = attributes["options"][0] if item["type"] == "dropdown" else f"Explicit shaped {item['id']}."
        if item["type"] == "checkboxes":
            value = "\n".join(f"- [x] {option['label']}" for option in attributes["options"])
        fields[item["id"]] = {"kind": "markdown", "value": value}
    return {"kind": "agentic-workspace/issue-body-request/v1", "template": kind, "title": "Prepared issue", "fields": fields}


@pytest.mark.parametrize(
    "kind,prefix,labels", [("direction", "[Workspace]:", ["planning"]), ("bug", "[Bug]:", ["bug"]), ("review", "[Review]:", ["review"])]
)
def test_preparation_preserves_current_form_and_supplied_semantics(kind, prefix, labels):
    request = _request(kind)
    request["title"] = prefix + " Prepared issue"
    request["fields"]["intended_outcome"]["value"] = "  Preserve Unicode ÃƒÂ¥ and Markdown.\n\n- [ ] Concrete outcome\n"
    rendered = issue_body.render_issue_request(request)
    form = yaml.safe_load((_REPO_ROOT / ".github/ISSUE_TEMPLATE" / rendered["template"]).read_text(encoding="utf-8"))
    expected = [
        f"## {item['attributes']['label']}\n{request['fields'][item['id']]['value']}" for item in form["body"] if item["type"] != "markdown"
    ]
    if kind == "bug":
        expected[expected.index("## Steps to reproduce\nExplicit shaped reproduction.")] = (
            "## Steps to reproduce\n```shell\nExplicit shaped reproduction.\n```"
        )
    assert rendered["status"] == "prepared"
    assert rendered["body"] == "\n\n".join(expected) + "\n"
    assert rendered["title"] == prefix + " Prepared issue"
    assert rendered["duplicate_prefix_normalized"]
    assert rendered["labels"] == labels
    assert rendered["identities"]["template"]["revision"].startswith("sha256:")


def test_textarea_render_preserves_code_and_follows_current_form(tmp_path):
    shutil.copytree(_REPO_ROOT / ".github/ISSUE_TEMPLATE", tmp_path / ".github/ISSUE_TEMPLATE")
    request = _request("bug")
    request["fields"]["reproduction"]["value"] = "echo example\n```\n## This remains code\n"
    result = issue_body.render_issue_request(request, target_root=tmp_path)
    assert "## Steps to reproduce\n````shell\necho example\n```\n## This remains code\n````\n" in result["body"]
    path = tmp_path / ".github/ISSUE_TEMPLATE" / issue_body.TEMPLATE_BY_KIND["bug"]
    form = yaml.safe_load(path.read_text(encoding="utf-8"))
    reproduction = next(item for item in form["body"] if item.get("id") == "reproduction")
    reproduction["attributes"]["render"] = "python"
    path.write_text(yaml.safe_dump(form), encoding="utf-8")
    changed = issue_body.render_issue_request(request, target_root=tmp_path, previous=result)
    assert changed["comparison"]["changed"] == ["template"]
    assert "## Steps to reproduce\n````python\necho example\n```\n## This remains code\n````\n" in changed["body"]
    reproduction["attributes"]["render"] = "shell\n```"
    path.write_text(yaml.safe_dump(form), encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported render attribute"):
        issue_body.render_issue_request(request, target_root=tmp_path)


@pytest.mark.parametrize(
    "rule",
    [
        "Parent closes administratively after accepted bounded children/dispositions and aggregate proof.",
        "One bounded PR and immediate integration proof establish this leaf's whole outcome.",
        "Later evidence closes without product-code PRs; implementation findings route to bounded owners.",
    ],
)
def test_preparation_does_not_rewrite_closure_shape(rule):
    request = _request()
    request["fields"]["completion_rule"]["value"] = rule
    request["fields"]["parent_issue"]["value"] = "#3276"
    rendered = issue_body.render_issue_request(request)
    assert rule in rendered["body"]
    assert "#3276" in rendered["body"]


def test_missing_ambiguous_and_placeholder_input_produces_no_publishable_body():
    request = _request("review")
    for key in ["issue_kind", "final_satisfaction", "completion_rule", "non_solutions"]:
        del request["fields"][key]
    request["fields"]["product_should_absorb"]["value"] = "Undecided"
    request["fields"]["acceptance"]["value"] = "TODO: decide acceptance"
    request["fields"]["invented"] = {"kind": "text", "value": "Do not silently drop this."}
    rendered = issue_body.render_issue_request(request)
    assert rendered["status"] == "needs-input"
    assert rendered["body"] is None
    assert {p["field"] for p in rendered["problems"]} == {
        "issue_kind",
        "final_satisfaction",
        "completion_rule",
        "non_solutions",
        "product_should_absorb",
        "acceptance",
        "invented",
    }
    assert next(f for f in rendered["form_fields"] if f["id"] == "product_should_absorb")["attributes"]["options"] == [
        "Yes",
        "Maybe",
        "No",
    ]
    assert issue_body.render_issue(kind="direction", title="", fields={})["body"] is None


def test_exact_preparation_inputs_invalidate_without_unrelated_source_churn(tmp_path, monkeypatch):
    forms = tmp_path / ".github/ISSUE_TEMPLATE"
    shutil.copytree(_REPO_ROOT / ".github/ISSUE_TEMPLATE", forms)
    helper = tmp_path / "helper.py"
    helper.write_bytes(_MODULE_PATH.read_bytes())
    source = tmp_path / "shaped-source.md"
    source.write_text("Current shaped source.")
    monkeypatch.setattr(issue_body, "__file__", str(helper))
    monkeypatch.setattr(issue_body, "REPO_ROOT", tmp_path)
    request = _request()
    request["source_refs"] = [{"kind": "shaped-source", "path": source.name}, {"kind": "issue", "url": "https://example.test/1"}]
    before = issue_body.render_issue_request(request, target_root=tmp_path)
    assert before["identities"]["sources"][1]["status"] == "external-currentness-unobserved"
    (tmp_path / "unrelated.md").write_text("unrelated")
    assert issue_body.render_issue_request(request, target_root=tmp_path, previous=before)["comparison"]["status"] == "current"
    for path, content, expected in [
        (forms / before["template"], "\n# changed form", "template"),
        (helper, "\n# changed helper", "helper"),
        (source, "\nChanged source", "sources"),
    ]:
        prior = issue_body.render_issue_request(request, target_root=tmp_path)
        with path.open("a") as stream:
            stream.write(content)
        result = issue_body.render_issue_request(request, target_root=tmp_path, previous=prior)
        assert result["comparison"]["status"] == "stale"
        assert result["comparison"]["changed"] == [expected]
    prior = issue_body.render_issue_request(request, target_root=tmp_path)
    request["fields"]["completion_rule"]["value"] = "Changed explicit closure."
    result = issue_body.render_issue_request(request, target_root=tmp_path, previous=prior)
    assert result["comparison"]["changed"] == ["shaped_input"]
    assert "Changed explicit closure." in result["body"]
    assert issue_body.render_issue_request(request, target_root=tmp_path, previous={})["comparison"]["status"] == "unavailable"


def test_current_form_changes_are_used_and_missing_sources_are_unavailable(tmp_path):
    shutil.copytree(_REPO_ROOT / ".github/ISSUE_TEMPLATE", tmp_path / ".github/ISSUE_TEMPLATE")
    request = _request()
    path = tmp_path / ".github/ISSUE_TEMPLATE" / issue_body.TEMPLATE_BY_KIND["direction"]
    form = yaml.safe_load(path.read_text(encoding="utf-8"))
    form["title"] = "[Current]:"
    form["labels"] = ["new-label"]
    form["body"].append({"type": "input", "id": "new_required", "attributes": {"label": "New required"}, "validations": {"required": True}})
    path.write_text(yaml.safe_dump(form))
    result = issue_body.render_issue_request(request, target_root=tmp_path)
    assert result["title"] == "[Current]: Prepared issue"
    assert result["labels"] == ["new-label"]
    assert result["problems"] == [{"field": "new_required", "reason": "required shaped value missing"}]
    request["fields"]["new_required"] = {"kind": "text", "value": "Supplied"}
    assert "## New required\nSupplied" in issue_body.render_issue_request(request, target_root=tmp_path)["body"]
    request["source_refs"] = [{"kind": "source", "path": "missing.md"}]
    with pytest.raises(OSError):
        issue_body.render_issue_request(request, target_root=tmp_path)
    request["source_refs"][0]["path"] = "../outside.md"
    with pytest.raises(ValueError, match="inside the repository"):
        issue_body.render_issue_request(request, target_root=tmp_path)


def test_cli_reports_incomplete_and_unavailable_without_writing(tmp_path, capsys):
    request = _request()
    path = tmp_path / "request.json"
    path.write_text(json.dumps(request))
    assert issue_body.main(["--input-json", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "prepared"
    assert issue_body.main(["--kind", "review", "--format", "body"]) == 2
    result = capsys.readouterr()
    assert result.out == ""
    assert json.loads(result.err)["status"] == "needs-input"
    assert issue_body.main(["--input-json", str(path), "--kind", "direction"]) == 2
    assert "--input-json" in capsys.readouterr().err
    assert issue_body.main(["--kind", "direction", "--field", "x=one", "--field", "x=two"]) == 2
    assert "ambiguous" in capsys.readouterr().err
    assert issue_body.main(["--input-json", str(tmp_path / "absent")]) == 2
    assert json.loads(capsys.readouterr().err)["status"] == "unavailable"
    assert list(tmp_path.iterdir()) == [path]
    for flag in ["--from-lane", "--from-decomposition"]:
        with pytest.raises(SystemExit):
            issue_body.main([flag, "example"])
    invalid = copy.deepcopy(request)
    invalid["fields"]["acceptance"] = "untyped"
    with pytest.raises(ValueError, match="schema error"):
        issue_body.render_issue_request(invalid)


def test_checkbox_assertions_are_supplied_not_inferred():
    request = _request("bug")
    del request["fields"]["existing_issue"]
    result = issue_body.render_issue_request(request)
    assert {"field": "existing_issue", "reason": "required shaped value missing"} in result["problems"]
    request["fields"]["existing_issue"] = {"kind": "markdown", "value": "- [ ] I searched the existing issues first"}
    assert issue_body.render_issue_request(request)["status"] == "needs-input"
    request["fields"]["existing_issue"]["value"] = "- [x] I searched the existing issues first"
    assert issue_body.render_issue_request(request)["status"] == "prepared"


def test_compound_request_binds_work_material_and_external_result(tmp_path):
    request = issue_body.prepare_creation(_request(), repository="owner/repo", task="Bounded creation")
    assert request["status"] == "prepared"
    assert issue_body.prepare_creation(_request(), repository="owner/repo", task="Changed work")["request_id"] != request["request_id"]
    changed = copy.deepcopy(request)
    changed["material"]["write"]["body"] += "changed"
    with pytest.raises(ValueError, match="changed"):
        issue_body.validate_creation_request(changed)
    with pytest.raises(ValueError, match="different"):
        issue_body.continue_creation(request, {"request_id": "different", "outcome": "confirmed"})


def test_external_creation_reobserves_without_replay_and_preserves_committed_effect():
    request = issue_body.prepare_creation(_request(), repository="owner/repo", task="Bounded creation")
    calls = []

    def observe(repo, number):
        calls.append((repo, number))
        return {
            "number": number,
            "html_url": f"https://github.com/{repo}/issues/{number}",
            **request["material"]["write"],
            "labels": [{"name": value} for value in request["material"]["write"]["labels"]],
        }

    report = {"request_id": request["request_id"], "outcome": "uncertain"}
    unknown = issue_body.continue_creation(request, report, observer=observe)
    assert unknown["effect_outcome"] == "unknown" and not unknown["retry_creation"] and not calls
    # The authorized transport recovers its exact external identity, then a fresh
    # consumer can confirm it with a GET. No create callback exists on resumption.
    report["number"] = 42
    recovered = issue_body.continue_creation(json.loads(json.dumps(request)), report, current=request, observer=observe)
    assert recovered["effect_outcome"] == "committed"
    assert recovered["continuation"]["status"] == "not-requested"
    assert calls == [("owner/repo", 42)]

    def failed_continuation(issue):
        assert issue["number"] == 42
        raise OSError("owner unavailable after confirmed external effect")

    continued = issue_body.continue_creation(request, report, current=request, observer=observe, continuation=failed_continuation)
    assert continued["effect_outcome"] == "committed" and not continued["retry_creation"]
    assert continued["continuation"]["status"] == "unavailable"
    stale = issue_body.continue_creation(request, report, observer=observe, continuation=lambda _: pytest.fail("stale continuation"))
    assert stale["effect_outcome"] == "committed"
    assert stale["currentness"] == "stale-or-unavailable"


def test_rejection_observation_failure_and_mismatch_do_not_authorize_creation():
    request = issue_body.prepare_creation(_request(), repository="owner/repo", task="Bounded creation")
    rejected = {
        "request_id": request["request_id"],
        "outcome": "rejected-before-effect",
        "effect_attempted": False,
        "reason": "Host denied authorization",
    }
    assert issue_body.continue_creation(request, rejected)["effect_outcome"] == "not-committed"
    rejected["effect_attempted"] = True
    with pytest.raises(ValueError, match="no-effect"):
        issue_body.continue_creation(request, rejected)
    report = {"request_id": request["request_id"], "outcome": "confirmed", "number": 7}

    def unavailable(*_):
        raise OSError("lost response")

    assert issue_body.continue_creation(request, report, observer=unavailable)["effect_outcome"] == "unknown"
    mismatch = issue_body.continue_creation(
        request,
        report,
        observer=lambda *_: {"number": 7, "html_url": "https://github.com/owner/repo/issues/7", "title": "Different", "labels": []},
    )
    assert mismatch["status"] == "external-result-mismatch" and not mismatch["retry_creation"]


def test_compound_cli_resumes_after_missing_input_and_owner_failure(tmp_path, monkeypatch, capsys):
    shaped = tmp_path / "shaped.json"
    shaped.write_text(json.dumps(_request()))
    base = ["--input-json", str(shaped), "--repository", "owner/repo", "--task", "Create bounded issue"]
    assert issue_body.main(base) == 0
    packet = json.loads(capsys.readouterr().out)
    prior = tmp_path / "prepared.json"
    prior.write_text(json.dumps(packet))
    report = tmp_path / "result.json"
    report.write_text(json.dumps({"request_id": packet["request_id"], "outcome": "confirmed", "number": 11}))
    monkeypatch.setattr(
        issue_body,
        "observe_created_issue",
        lambda *_: {
            "number": 11,
            "html_url": "https://github.com/owner/repo/issues/11",
            **packet["material"]["write"],
            "labels": [{"name": label} for label in packet["material"]["write"]["labels"]],
        },
    )
    resume = [
        *base,
        "--creation-request",
        str(prior),
        "--external-result",
        str(report),
        "--continuation-input",
        str(tmp_path / "missing-owner-request.json"),
        "--native-cli",
        str(tmp_path / "missing-native"),
    ]
    assert issue_body.main(resume) == 0
    observed = json.loads(capsys.readouterr().out)
    assert observed["effect_outcome"] == "committed" and observed["continuation"]["status"] == "unavailable"
    shaped.unlink()
    assert issue_body.main(resume) == 0
    observed = json.loads(capsys.readouterr().out)
    assert observed["effect_outcome"] == "committed" and observed["currentness"] == "stale-or-unavailable"
