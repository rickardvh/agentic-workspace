"""Native selected-command evidence, never independent acceptance."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli


def fixture(root: Path) -> dict:
    (root / "a.txt").write_text("current source")
    command = (
        "Add-Content -Path count.txt -Value executed; Write-Output verified"
        if os.name == "nt"
        else "echo executed >> count.txt; echo verified"
    )
    manifest = root / ".agentic-workspace/verification/manifest.toml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        'schema_version="agentic-workspace/verification-manifest/v1"\n'
        '[protocols.check]\napplies_to_paths=["a.txt"]\n'
        '[proof_routes.check]\nprotocol_refs=["check"]\ncommands=[' + json.dumps(command) + "]\n"
    )
    return {"target": str(root), "task": "Check the current source", "changed": ["a.txt"]}


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_native_selected_command_publishes_and_replays_without_task_claim(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    context = fixture(tmp_path)

    def call(value: dict) -> dict:
        return consume(surface, shared_core_binary, native_cli, value, host_path=os.environ["PATH"])

    initial = call(context)
    assert not (tmp_path / ".agentic-workspace/local").exists()
    request = initial["verification"]["execution_requests"][0]
    selected = call({**context, "request": request})
    invocation = selected["decision_packet"]["primary_action"]
    assert invocation["operation_id"] == "proof.report"
    assert invocation["effects"] == ["proof-execution"]
    forged_invocation = json.loads(json.dumps(invocation))
    forged_invocation["arguments"]["selection"]["proof_subject"]["runtime"]["shell"]["path"] = "untrusted-executable"
    with pytest.raises(AssertionError, match="stale"):
        call({**context, "invocation": forged_invocation})
    assert not (tmp_path / "count.txt").exists()
    applied = call({**context, "invocation": invocation})
    assert applied["status"] == "applied"
    value = applied["value"]
    assert value["process"]["status"] == "passed"
    assert value["publication"]["status"] == "published"
    assert value["claim_boundary"]["completion_claim_allowed"] is False
    replay = call({**context, "invocation": invocation})
    assert replay["value"] == value
    assert (tmp_path / "count.txt").read_text().splitlines() == ["executed"]
    claim = call(context)["verification"]["requests"][0]
    claim["arguments"]["evidence_refs"] = [value["publication"]["reference"]]
    evidence = call({**context, "request": claim})["verification"]["evidence"][0]
    assert evidence["publication_admission"]["status"] == "admitted"
    assert evidence["evidence_freshness"] == "reusable"
    assert evidence["strategy_coverage"] == "selected-command-covered"
    assert evidence["task_judgment"]["current_judgment_count"] == 0
    (tmp_path / "unrelated-attempt.txt").write_text("unrelated orchestration observation")
    assert call({**context, "request": claim})["verification"]["evidence"][0]["evidence_freshness"] == "reusable"
    (tmp_path / "a.txt").write_text("material change")
    stale = call({**context, "request": claim})["verification"]["evidence"][0]
    assert stale["evidence_freshness"] != "reusable"
    with pytest.raises(AssertionError, match="stale"):
        call({**context, "invocation": invocation})
    assert len((tmp_path / "count.txt").read_text().splitlines()) == 1


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_native_proof_preserves_existing_index_and_rejects_command_injection(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    context = fixture(tmp_path)

    def call(value: dict) -> dict:
        return consume(surface, shared_core_binary, native_cli, value, host_path=os.environ["PATH"])

    request = call(context)["verification"]["execution_requests"][0]
    forged = json.loads(json.dumps(request))
    forged["arguments"]["command"] += "; echo different"
    with pytest.raises(AssertionError, match="current source-declared command"):
        call({**context, "request": forged})
    action = call({**context, "request": request})["decision_packet"]["primary_action"]
    index = tmp_path / ".agentic-workspace/proof/receipts/index.json"
    index.parent.mkdir(parents=True)
    index.write_text('{"kind":"agentic-workspace/trusted-producer-receipt-index/v1","receipts":{}}')
    before = index.read_bytes()
    with pytest.raises(AssertionError, match="publication-index-custody-required"):
        call({**context, "invocation": action})
    assert index.read_bytes() == before
    assert not (tmp_path / "count.txt").exists()
    assert not (tmp_path / ".agentic-workspace/local").exists()


def test_native_proof_actual_interruption_cannot_reexecute(tmp_path: Path, shared_core_binary: Path, native_cli: Path) -> None:
    import subprocess
    import time

    context = fixture(tmp_path)
    manifest = tmp_path / ".agentic-workspace/verification/manifest.toml"
    text = manifest.read_text()
    command = "Add-Content count.txt executed; Start-Sleep -Seconds 30" if os.name == "nt" else "echo executed >> count.txt; sleep 30"
    text = text[: text.index("commands=")] + "commands=[" + json.dumps(command) + "]\n"
    manifest.write_text(text)
    request = consume("native", shared_core_binary, native_cli, context, host_path=os.environ["PATH"])["verification"][
        "execution_requests"
    ][0]
    selected = consume("native", shared_core_binary, native_cli, {**context, "request": request}, host_path=os.environ["PATH"])
    invocation = selected["decision_packet"]["primary_action"]
    process = subprocess.Popen(
        [
            str(native_cli),
            "invoke",
            "--target",
            str(tmp_path),
            "--task",
            context["task"],
            "--changed",
            "a.txt",
            "--input",
            "-",
            "--format",
            "json",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        process.stdin.write(json.dumps(invocation))
        process.stdin.close()
        deadline = time.monotonic() + 10
        while not (tmp_path / "count.txt").exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert (tmp_path / "count.txt").exists(), "real worker must start before interruption"
        process.kill()
        process.wait(timeout=5)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
    with pytest.raises(AssertionError, match="proof-execution-uncertain"):
        consume("native", shared_core_binary, native_cli, {**context, "invocation": invocation}, host_path=os.environ["PATH"])
    assert (tmp_path / "count.txt").read_text().splitlines() == ["executed"]
    assert not (tmp_path / ".agentic-workspace/proof/receipts/index.json").exists()


@pytest.mark.parametrize("failure", ["exit", "timeout"])
def test_native_failed_or_timed_out_command_is_retained_without_retry(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, failure: str
) -> None:
    context = fixture(tmp_path)
    manifest = tmp_path / ".agentic-workspace/verification/manifest.toml"
    command = "Add-Content count.txt executed; " if os.name == "nt" else "echo executed >> count.txt; "
    command += ("Start-Sleep -Seconds 30" if os.name == "nt" else "sleep 30") if failure == "timeout" else "exit 7"
    text = manifest.read_text()
    manifest.write_text(text[: text.index("commands=")] + "commands=[" + json.dumps(command) + "]\ntimeout_seconds=1\n")

    def call(value: dict) -> dict:
        return consume("native", shared_core_binary, native_cli, value, host_path=os.environ["PATH"])

    request = call(context)["verification"]["execution_requests"][0]
    action = call({**context, "request": request})["decision_packet"]["primary_action"]
    result = call({**context, "invocation": action})
    assert result["value"]["process"]["status"] == ("timeout" if failure == "timeout" else "failed")
    assert call({**context, "invocation": action})["value"] == result["value"]
    assert (tmp_path / "count.txt").read_text().splitlines() == ["executed"]
    request = call(context)["verification"]["requests"][0]
    request["arguments"]["evidence_refs"] = [result["value"]["publication"]["reference"]]
    evidence = call({**context, "request": request})["verification"]["evidence"][0]
    assert evidence["receipt_admission"]["proof_sufficient"] is False


def test_native_proof_cannot_bypass_current_source_protection(tmp_path: Path, shared_core_binary: Path, native_cli: Path) -> None:
    from tests.test_native_public_cli import pin_instructions

    context = fixture(tmp_path)
    instruction = tmp_path / ".agentic-workspace/instructions/preserve.md"
    instruction.parent.mkdir(parents=True)
    instruction.write_text("---\npaths: [count.txt]\nprotect: [count.txt]\n---\nPreserve this source.\n")
    pin_instructions(tmp_path)

    def call(value: dict) -> dict:
        return consume("native", shared_core_binary, native_cli, value, host_path=os.environ["PATH"])

    request = call(context)["verification"]["execution_requests"][0]
    blocked = call({**context, "request": request})
    assert any(item["code"].endswith(":proof-execution-scope-unresolved") for item in blocked["decision_packet"]["blockers"])
    assert not (tmp_path / "count.txt").exists()
    assert not (tmp_path / ".agentic-workspace/local/effects").exists()


@pytest.mark.parametrize("consumer", ["json", "python", "typescript"])
def test_native_producer_reused_by_fresh_adapters_through_same_core(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, consumer: str
) -> None:
    context = fixture(tmp_path)

    def call(surface: str, value: dict) -> dict:
        return consume(surface, shared_core_binary, native_cli, value, host_path=os.environ["PATH"])

    request = call("native", context)["verification"]["execution_requests"][0]
    action = call("native", {**context, "request": request})["decision_packet"]["primary_action"]
    result = call("native", {**context, "invocation": action})
    request = call(consumer, context)["verification"]["requests"][0]
    request["arguments"]["evidence_refs"] = [result["value"]["publication"]["reference"]]
    evidence = call(consumer, {**context, "request": request})["verification"]["evidence"][0]
    assert evidence["publication_admission"]["status"] == "admitted"
    assert evidence["evidence_freshness"] == "reusable"
    assert evidence["task_judgment"]["current_judgment_count"] == 0
    replay = call(consumer, {**context, "invocation": action})
    assert replay["value"] == result["value"]
    assert (tmp_path / "count.txt").read_text().splitlines() == ["executed"]


def test_native_large_output_has_compact_sealed_detail_and_tamper_gap(tmp_path: Path, shared_core_binary: Path, native_cli: Path) -> None:
    context = fixture(tmp_path)
    manifest = tmp_path / ".agentic-workspace/verification/manifest.toml"
    command = "Write-Output ('x' * 200000)" if os.name == "nt" else "printf '%0200000d' 0"
    text = manifest.read_text()
    manifest.write_text(text[: text.index("commands=")] + "commands=[" + json.dumps(command) + "]\n")

    def call(value: dict) -> dict:
        return consume("native", shared_core_binary, native_cli, value, host_path=os.environ["PATH"])

    request = call(context)["verification"]["execution_requests"][0]
    action = call({**context, "request": request})["decision_packet"]["primary_action"]
    result = call({**context, "invocation": action})
    value = result["value"]
    assert len(json.dumps(value)) < 10000
    artifact = value["process"]["artifact"]
    assert artifact["streams"]["stdout"]["bytes"] >= 200000
    assert artifact["streams"]["stdout"]["truncated"] is True
    detail = tmp_path / artifact["path"]
    assert "x" * 1000 in detail.read_text() if os.name == "nt" else detail.exists()
    request = call(context)["verification"]["requests"][0]
    request["arguments"]["evidence_refs"] = [value["publication"]["reference"]]
    assert call({**context, "request": request})["verification"]["evidence"][0]["detail"]["status"] == "current"
    receipt_id = value["publication"]["reference"].rsplit("/", 1)[-1]
    receipt_path = tmp_path / f".agentic-workspace/proof/receipts/{receipt_id}.json"
    original = receipt_path.read_bytes()
    receipt = json.loads(original)
    receipt["execution_artifact"]["path"] = "../../unrelated-detail"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    rejected = call({**context, "request": request})["verification"]["evidence"][0]
    assert rejected["publication_admission"]["reason"] == "publication-content-identity-mismatch"
    assert rejected["detail"]["status"] == "unavailable-or-stale"
    receipt_path.write_bytes(original)
    detail.write_text("altered detail")
    evidence = call({**context, "request": request})["verification"]["evidence"][0]
    assert evidence["publication_admission"]["status"] == "admitted"
    assert evidence["evidence_freshness"] == "unproven"
    assert "native-proof-detail-unavailable-or-stale" in evidence["gaps"]


def test_native_proof_source_change_during_execution_cannot_publish_current_evidence(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path
) -> None:
    context = fixture(tmp_path)
    manifest = tmp_path / ".agentic-workspace/verification/manifest.toml"
    command = (
        "Set-Content a.txt changed; Add-Content count.txt executed"
        if os.name == "nt"
        else "echo changed > a.txt; echo executed >> count.txt"
    )
    text = manifest.read_text()
    manifest.write_text(text[: text.index("commands=")] + "commands=[" + json.dumps(command) + "]\n")

    def call(value: dict) -> dict:
        return consume("native", shared_core_binary, native_cli, value, host_path=os.environ["PATH"])

    request = call(context)["verification"]["execution_requests"][0]
    action = call({**context, "request": request})["decision_packet"]["primary_action"]
    result = call({**context, "invocation": action})
    assert result["value"]["process"]["status"] == "passed"
    assert result["value"]["source_current"] is False
    assert result["value"]["publication"]["status"] == "unpublished"
    assert not (tmp_path / ".agentic-workspace/proof/receipts/index.json").exists()
    with pytest.raises(AssertionError, match="stale"):
        call({**context, "invocation": action})
    assert (tmp_path / "count.txt").read_text().splitlines() == ["executed"]


def test_native_concurrent_same_effect_launches_once(tmp_path: Path, shared_core_binary: Path, native_cli: Path) -> None:
    import subprocess

    context = fixture(tmp_path)
    request = consume("native", shared_core_binary, native_cli, context, host_path=os.environ["PATH"])["verification"][
        "execution_requests"
    ][0]
    action = consume("native", shared_core_binary, native_cli, {**context, "request": request}, host_path=os.environ["PATH"])[
        "decision_packet"
    ]["primary_action"]
    command = [
        str(native_cli),
        "invoke",
        "--target",
        str(tmp_path),
        "--task",
        context["task"],
        "--changed",
        "a.txt",
        "--input",
        "-",
        "--format",
        "json",
    ]
    children = [
        subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)
    ]
    for child in children:
        child.stdin.write(json.dumps(action))
        child.stdin.close()
        child.stdin = None
    results = [child.communicate(timeout=15) for child in children]
    assert any(child.returncode == 0 for child in children), results
    assert all(child.returncode in {0, 2} for child in children), results
    assert (tmp_path / "count.txt").read_text().splitlines() == ["executed"]


def test_native_proof_builtin_command_does_not_require_python(tmp_path: Path, shared_core_binary: Path, native_cli: Path) -> None:
    import shutil

    context = fixture(tmp_path)
    shell = (shutil.which("pwsh") or shutil.which("powershell")) if os.name == "nt" else shutil.which("sh")
    assert shell is not None
    host_path = str(Path(shell).parent)

    def call(value: dict) -> dict:
        return consume("native", shared_core_binary, native_cli, value, host_path=host_path)

    request = call(context)["verification"]["execution_requests"][0]
    action = call({**context, "request": request})["decision_packet"]["primary_action"]
    result = call({**context, "invocation": action})
    assert result["value"]["process"]["status"] == "passed"
    assert result["value"]["proof_subject"]["runtime"]["implementation"] == "native-aw-proof"


def test_shared_publication_identity_preserves_legacy_unicode_and_defaults(shared_core_binary: Path) -> None:
    from agentic_workspace.workspace_runtime_core import _proof_publication_identity

    receipt = {
        "command": "check",
        "result": "passed",
        "changed_paths": ["a.txt"],
        "proof_subject": {"kind": "fixture"},
        "target_context": {"unicode": "\u00c5\U0001f642", "integer": 7, "decimal": 1.25, "boolean": True, "unknown": None},
    }
    expected = {**receipt, "proof_commands": []}
    assert _proof_publication_identity(receipt) == expected
    assert _proof_publication_identity({}) == {
        "command": None,
        "result": None,
        "changed_paths": None,
        "proof_subject": None,
        "target_context": {},
        "proof_commands": [],
    }
    sealed = {**receipt, "execution_artifact": {"path": "source-owned-detail", "sha256": "digest"}}
    assert _proof_publication_identity(sealed) == {**expected, "execution_artifact": sealed["execution_artifact"]}


def test_native_proof_uses_actual_reconciled_planning_subject(tmp_path: Path, shared_core_binary: Path, native_cli: Path) -> None:
    from tests.test_native_public_cli import ROOT

    context = fixture(tmp_path)
    reference = Path(".agentic-workspace/planning/execplans/delegation-lane-sweep.plan.json")
    plan = tmp_path / reference
    plan.parent.mkdir(parents=True)
    plan.write_bytes((ROOT / reference).read_bytes())
    (tmp_path / ".agentic-workspace/planning/state.toml").write_text(
        f'[[active.execplans]]\nid="delegation-lane-sweep"\npath="{reference.as_posix()}"\nstatus="active"\n'
    )

    def call(value: dict) -> dict:
        return consume("native", shared_core_binary, native_cli, value, host_path=os.environ["PATH"])

    initial = call(context)
    request = initial["decision_packet"]["decision_request"]["response_request"]
    request["arguments"]["answer"] = "continue-selected"
    continued = call({**context, "request": request})
    call({**context, "invocation": continued["decision_packet"]["primary_action"]})
    current = call(context)
    subject = current["planning"]["current_owner"]["reconciliation"]["subject"]
    request = current["verification"]["execution_requests"][0]
    selected = call({**context, "request": request})
    action = selected["decision_packet"]["primary_action"]
    assert action["arguments"]["selection"]["work"] == {"id": subject["id"], "revision": subject["revision"]}
    result = call({**context, "invocation": action})

    def evidence_for(consumer: str):
        current = consume(consumer, shared_core_binary, native_cli, context, host_path=os.environ["PATH"])
        claim = current["verification"]["requests"][0]
        claim["arguments"]["evidence_refs"] = [result["value"]["publication"]["reference"]]
        checked = consume(consumer, shared_core_binary, native_cli, {**context, "request": claim}, host_path=os.environ["PATH"])
        assert checked["verification"]["judgment_request"]["work_ref"] == subject["id"]
        assert checked["decision_packet"]["status"] != "terminal"
        evidence = checked["verification"]["evidence"][0]
        assert evidence["publication_admission"]["status"] == "admitted"
        assert evidence["task_judgment"]["current_judgment_count"] == 0
        return evidence

    for consumer in ["native", "json", "python", "typescript"]:
        assert evidence_for(consumer)["evidence_freshness"] == "reusable"
    original = (tmp_path / "a.txt").read_bytes()
    (tmp_path / "a.txt").write_text("changed proof input")
    for consumer in ["native", "json", "python", "typescript"]:
        assert evidence_for(consumer)["evidence_freshness"] == "stale"
    (tmp_path / "a.txt").write_bytes(original)
    body = json.loads(plan.read_bytes())
    body["canonical_core"]["hard_constraints"] = "New material Planning boundary"
    plan.write_text(json.dumps(body))
    request = call(context)["decision_packet"]["decision_request"]["response_request"]
    request["arguments"]["answer"] = "continue-selected"
    action = call({**context, "request": request})["decision_packet"]["primary_action"]
    call({**context, "invocation": action})
    assert call(context)["planning"]["current_owner"]["reconciliation"]["subject"]["revision"] != subject["revision"]
    for consumer in ["native", "json", "python", "typescript"]:
        assert evidence_for(consumer)["evidence_freshness"] == "stale"
    assert (tmp_path / "count.txt").read_text().splitlines() == ["executed"]


def test_native_cli_colocated_core_is_required_without_path_or_env_fallback(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path
) -> None:
    import shutil
    import subprocess

    installed = tmp_path / "installed"
    installed.mkdir()
    launcher = installed / native_cli.name
    shutil.copy2(native_cli, launcher)
    target = tmp_path / "target"
    target.mkdir()
    command = [str(launcher), "start", "--target", str(target), "--task", "Explain this source"]
    environment = {**os.environ, "PATH": "", "AGENTIC_WORKSPACE_CORE_BINARY": str(shared_core_binary)}
    absent = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=15)
    assert absent.returncode == 2
    assert json.loads(absent.stderr)["error"]["code"] == "core-unavailable"
    assert list(target.iterdir()) == []
    shutil.copy2(shared_core_binary, installed / shared_core_binary.name)
    admitted = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=15)
    assert admitted.returncode == 0, admitted.stderr
    assert json.loads(admitted.stdout)["decision_packet"]
    assert list(target.iterdir()) == []


def test_native_core_byte_drift_and_other_location_do_not_reuse_proof(tmp_path: Path, shared_core_binary: Path, native_cli: Path) -> None:
    import shutil

    installed = tmp_path / "installed"
    installed.mkdir()
    launcher = installed / native_cli.name
    core = installed / shared_core_binary.name
    shutil.copy2(native_cli, launcher)
    shutil.copy2(shared_core_binary, core)
    target = tmp_path / "target"
    target.mkdir()
    context = fixture(target)

    def call(binary: Path, value: dict) -> dict:
        return consume("native", core, binary, value, host_path=os.environ["PATH"])

    request = call(launcher, context)["verification"]["execution_requests"][0]
    action = call(launcher, {**context, "request": request})["decision_packet"]["primary_action"]
    result = call(launcher, {**context, "invocation": action})
    claim = call(launcher, context)["verification"]["requests"][0]
    claim["arguments"]["evidence_refs"] = [result["value"]["publication"]["reference"]]
    assert call(launcher, {**context, "request": claim})["verification"]["evidence"][0]["evidence_freshness"] == "reusable"
    relocated = call(native_cli, {**context, "request": claim})["verification"]["evidence"][0]
    assert relocated["evidence_freshness"] != "reusable"
    # A valid executable with appended diagnostic bytes still executes, but its
    # actual full-binary identity changed at the SAME path.
    with core.open("ab") as output:
        output.write(b"\nAW proof runtime drift fixture\n")
    drifted = call(launcher, {**context, "request": claim})["verification"]["evidence"][0]
    assert drifted["runtime_admission"]["reason"] == "native-producer-binary-compatibility-unproven"
    assert drifted["evidence_freshness"] != "reusable"
    with pytest.raises(AssertionError, match="stale"):
        call(launcher, {**context, "invocation": action})
    assert (target / "count.txt").read_text().splitlines() == ["executed"]
