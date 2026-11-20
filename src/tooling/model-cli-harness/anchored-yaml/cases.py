from __future__ import annotations

import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def aw(command, payload):
    binary = ROOT / "target/debug/agentic-workspace"
    if binary.with_suffix(".exe").is_file():
        binary = binary.with_suffix(".exe")
    result = subprocess.run(
        [str(binary), command, "--input", "-"], input=json.dumps(payload), capture_output=True, encoding="utf-8", timeout=90
    )
    if result.returncode and not result.stdout.strip():
        raise RuntimeError(result.stderr[:500])
    value = json.loads(result.stdout)
    if result.returncode and "effect_outcome" not in value:
        raise RuntimeError(str(value.get("error", {}))[:500])
    return value


def config_case(target):
    context = {"target": str(target), "task": "Set the workspace CLI invocation to aw-local"}
    first = aw("start", {**context, "projection": "full"})
    discovery = first["configuration_write"]["creation_discovery_request"]
    menu = aw("start", {**context, "request": discovery, "projection": "full"})
    request = next(r for r in menu["configuration_write"]["creation_requests"] if r["arguments"]["key"] == "workspace.cli_invoke")
    request["arguments"].update(source=".agentic-workspace/config.toml", key="workspace.cli_invoke", value="aw-local")
    return aw("start", {**context, "request": request, "projection": "compact"})


def configuration_detail(view, reference):
    result = aw("start", {**view["reentry"], "reference": reference})
    assert result["selector"] == "/configuration"
    return result["value"]


def checkout_route(view):
    (blocker,) = [row for row in view["decision_packet"]["blockers"] if row["code"] == "current-binding-assignment-required"]
    expected = {"code": blocker["code"], "affects": blocker["affects"], "reference": view["detail_refs"]["/configuration"]}
    answer = yield (
        "Identify the Assignment restriction on starting implementation, return its complete "
        "affected scope, and select the exact detail reference to inspect Configuration.",
        view,
        expected,
    )
    details = configuration_detail(view, answer["reference"])
    assert details["assignment_policy"]["assignment_policy"] == "required-best-fit"
    return "Read current Configuration under the binding assignment policy"


def approved_action(proposal, answer):
    result = aw("start", {**proposal["reentry"], **answer})
    action = result["decision_packet"]["primary_action"]
    args = action["arguments"]["request"]["arguments"]
    assert (action["operation_id"], args["key"], args["value"], args["source"]) == (
        "configuration.write",
        "workspace.cli_invoke",
        "aw-local",
        ".agentic-workspace/config.toml",
    )
    return result


def invoke_selected(ready):
    context = {k: ready["reentry"][k] for k in ("target", "task", "changed")}
    return aw("invoke", {**context, "invocation": ready["decision_packet"]["primary_action"]})


def authorization(proposal):
    question = proposal["decision_packet"]["decision_request"]
    assert question["id"] == "configuration-write-authorization"
    assert "authorize-write" in {choice["id"] for choice in question["choices"]}
    return {"reference": question["reference"], "answer": "authorize-write"}


def write_config(target):
    import tomllib

    proposal = config_case(target)
    answer = yield (
        "You have authorization to set workspace.cli_invoke to aw-local in the shared repository "
        "configuration. Submit the exact current question reference and its semantic answer.",
        proposal,
        authorization(proposal),
    )
    ready = approved_action(proposal, answer)
    action = ready["decision_packet"]["primary_action"]
    yield (
        "Select the prepared write for the authorized change by its operation_id and idempotency_key. "
        "The host will submit the exact selected envelope.",
        ready,
        {key: action[key] for key in ("operation_id", "idempotency_key")},
    )
    result = invoke_selected(ready)
    assert result["effect_outcome"]["status"] == "committed"
    source = target / ".agentic-workspace/config.toml"
    assert tomllib.loads(source.read_text(encoding="utf-8"))["workspace"]["cli_invoke"] == "aw-local"
    return "Configuration write committed and TOML value read back"


def stale_config(target):
    proposal = config_case(target)
    ready = approved_action(proposal, authorization(proposal))
    source = target / ".agentic-workspace/config.toml"
    source.parent.mkdir(exist_ok=True)
    concurrent = b'[workspace]\ncli_invoke = "maintainer-aw"\n'
    source.write_bytes(concurrent)
    rejection = invoke_selected(ready)
    assert rejection["effect_outcome"]["status"] == "rejected-before-effect" and not rejection["effects"]
    answer = yield (
        "A maintainer changed the shared configuration during a write. Inspect the native "
        "outcome. Report the effect status, whether to retry this effect, and which operation "
        "to use for fresh context. The goal is to inspect the current configuration value.",
        rejection,
        {"status": "rejected-before-effect", "retry_effect": False, "operation": "start"},
    )
    context = rejection["continuation"]["reentry"]["context"]
    view = aw(answer["operation"], {**context, "projection": "compact"})
    selected = yield (
        "Select the exact detail reference that will read the effective Configuration.",
        view,
        {"reference": view["detail_refs"]["/configuration"]},
    )
    details = configuration_detail(view, selected["reference"])
    assert details["cli_invoke"] == "maintainer-aw" and source.read_bytes() == concurrent
    return "Stale effect rejected, fresh value read, concurrent bytes preserved"


def defer_config(target):
    proposal = config_case(target)
    expected = authorization(proposal) | {"answer": "defer"}
    assert "defer" in {choice["id"] for choice in proposal["decision_packet"]["decision_request"]["choices"]}
    answer = yield (
        "Postpone the proposed configuration change. Select the question reference and the answer that prepares "
        "a deferral. Stop before invoking any operation.",
        proposal,
        expected,
    )
    ready = aw("start", {**proposal["reentry"], **answer})
    action = ready["decision_packet"]["primary_action"]
    assert action["operation_id"] == "configuration.defer-choice"
    yield (
        "Report the prepared operation_id and whether to invoke it under the original instruction.",
        ready,
        {"operation_id": action["operation_id"], "invoke": False},
    )
    assert not (target / ".agentic-workspace/config.toml").exists()
    return "Deferral selected, no operation invoked, configuration absent"
