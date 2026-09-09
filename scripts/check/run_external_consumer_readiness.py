from __future__ import annotations

import argparse
import copy
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPO_ROOT / "tests/fixtures/external_consumer"
REQUIRED_OPERATIONS = ("start", "planning.create", "planning.update", "planning.reconcile", "configuration.write", "proof.report")


class ReadinessCheckError(RuntimeError):
    pass


def _run(command: Sequence[str | Path], *, cwd: Path, env: Mapping[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [str(item) for item in command],
        cwd=cwd,
        env=dict(env) if env is not None else None,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        detail = (completed.stderr or completed.stdout).strip()
        raise ReadinessCheckError(f"command failed ({completed.returncode}): {' '.join(map(str, command))}\n{detail}")
    return completed


def _python(env_root: Path) -> Path:
    return env_root / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def _console_script(env_root: Path, name: str) -> Path:
    suffix = ".exe" if sys.platform == "win32" else ""
    return env_root / ("Scripts" if sys.platform == "win32" else "bin") / f"{name}{suffix}"


def _build_python_artifacts(dist: Path) -> list[Path]:
    uv = shutil.which("uv") or "uv"
    _run([uv, "build", "--wheel", "--out-dir", dist], cwd=REPO_ROOT)
    for package in ("agentic-workspace-memory", "agentic-workspace-planning", "agentic-workspace-verification"):
        _run([uv, "build", "--wheel", "--package", package, "--out-dir", dist], cwd=REPO_ROOT)
    wheels = sorted(dist.glob("*.whl"))
    if len(wheels) < 4:
        raise ReadinessCheckError("expected workspace plus three module wheels")
    return wheels


def _pack_typescript_artifact(dist: Path, npm: str) -> Path:
    # This archive is subsequently reused verbatim by packed conformance and
    # release validation. Stage its native payload at the originating producer.
    with tempfile.TemporaryDirectory(prefix="aw-readiness-native-stage-") as temporary:
        package = Path(temporary) / "workspace"
        _run(
            [sys.executable, REPO_ROOT / "scripts/release/stage_native_npm.py", "--output", package],
            cwd=REPO_ROOT,
        )
        completed = _run(
            [npm, "pack", "--json", "--pack-destination", dist.resolve()],
            cwd=package,
        )
    payload = json.loads(completed.stdout)
    archive = dist / str(payload[0]["filename"])
    if not archive.is_file():
        raise ReadinessCheckError("npm pack did not produce the declared archive")
    return archive


def _install_python_stack(env_root: Path, wheels: Sequence[Path]) -> None:
    uv = shutil.which("uv") or "uv"
    _run([uv, "venv", env_root], cwd=env_root.parent)
    python = _python(env_root)
    _run([uv, "pip", "install", "--python", python, "jsonschema>=4.23"], cwd=env_root.parent)
    _run([uv, "pip", "install", "--python", python, "--no-deps", *wheels], cwd=env_root.parent)


def _prepare_python_consumer(root: Path, wheels: Sequence[Path]) -> tuple[Path, Path]:
    root.mkdir(parents=True)
    env_root = root / ".venv"
    _install_python_stack(env_root, wheels)
    script = root / "consumer.py"
    shutil.copy2(FIXTURE_ROOT / "consumer.py", script)
    return _python(env_root), script


def _prepare_typescript_consumer(root: Path, archive: Path, npm: str) -> Path:
    root.mkdir(parents=True)
    _run([npm, "init", "--yes"], cwd=root)
    _run([npm, "install", archive, "--ignore-scripts", "--no-package-lock", "--no-audit", "--no-fund"], cwd=root)
    script = root / "consumer.mjs"
    shutil.copy2(FIXTURE_ROOT / "consumer.mjs", script)
    return script


def _consumer_request(
    *,
    language: str,
    consumer_root: Path,
    executable: Path | str,
    script: Path,
    request: Mapping[str, Any],
) -> dict[str, Any]:
    request_path = consumer_root / "request.json"
    request_path.write_text(json.dumps(request, sort_keys=True), encoding="utf-8", newline="\n")
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"PYTHONPATH", "AGENTIC_WORKSPACE_CORE_BINARY", "AGENTIC_WORKSPACE_CLI_BINARY"}
    }
    completed = _run([executable, script, request_path], cwd=consumer_root, env=env)
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ReadinessCheckError(f"{language} consumer returned malformed JSON: {completed.stdout!r}") from exc
    if not isinstance(payload, dict):
        raise ReadinessCheckError(f"{language} consumer returned a non-object envelope")
    return payload


def _ok(payload: Mapping[str, Any], label: str) -> Any:
    if payload.get("status") != "ok":
        raise ReadinessCheckError(f"{label} failed: {json.dumps(payload, sort_keys=True)}")
    result = payload.get("result")
    if isinstance(result, dict) and result.get("effect_outcome", {}).get("status") in {"uncertain", "rejected-before-effect"}:
        raise ReadinessCheckError(f"{label} did not establish effect success: {json.dumps(result, sort_keys=True)}")
    return result


def _rejected(payload: Mapping[str, Any]) -> bool:
    return payload.get("status") == "ok" and payload.get("result", {}).get("effect_outcome", {}).get("status") == "rejected-before-effect"


def _reverse_dependency_violations() -> list[str]:
    violations: list[str] = []
    allowed = {
        "agentic-workspace",
        "agentic-workspace-memory",
        "agentic-workspace-planning",
        "agentic-workspace-verification",
    }
    for manifest in [REPO_ROOT / "pyproject.toml", *(REPO_ROOT / "packages").glob("*/pyproject.toml")]:
        project = tomllib.loads(manifest.read_text(encoding="utf-8"))["project"]
        for dependency in project.get("dependencies", []):
            name = re.split(r"[ @<>=;\[]", dependency, maxsplit=1)[0].lower()
            if name.startswith(("agentic-", "agentic_")) and name not in allowed:
                violations.append(f"{manifest.relative_to(REPO_ROOT).as_posix()}: {name}")
    for manifest in REPO_ROOT.rglob("package.json"):
        if "node_modules" in manifest.parts:
            continue
        package = json.loads(manifest.read_text(encoding="utf-8"))
        dependencies = {
            str(name).lower()
            for field in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies")
            for name in package.get(field, {})
        }
        for name in dependencies:
            if "external-consumer" in name or "adapter-fixture" in name:
                violations.append(f"{manifest.relative_to(REPO_ROOT).as_posix()}: {name}")
    return violations


def _snapshot(target: Path) -> dict[str, bytes]:
    return {
        p.relative_to(target).as_posix(): p.read_bytes()
        for p in target.rglob("*")
        if p.is_file() and ".git" not in p.relative_to(target).parts
    }


def exercise_native_lifecycle(call: Any, target: Path) -> dict[str, Any]:
    """Installed public calls, each in a fresh process; no fixture-created custody."""
    target.mkdir(parents=True, exist_ok=True)
    sentinel = target / "example.txt"
    sentinel.write_bytes(b"preserve unrelated consumer work\n")
    task = "Maintain the installed consumer Planning owner"

    def start(request=None):
        context = {"target": str(target), "task": task, "projection": "full"}
        if request is not None:
            context["request"] = [request]
        return _ok(call({"action": "start", "context": context}), "native start")

    def invoke(action):
        return call({"action": "invoke", "context": {"target": str(target), "task": task, "invocation": action}})

    def admit(request):
        return start(request)["decision_packet"]["primary_action"]

    before = _snapshot(target)
    initial = start()
    assert initial["decision_packet"]["status"] == "direct"
    assert _snapshot(target) == before, "unconfigured startup must leave no footprint"
    create = initial["planning"]["creation_requests"][0]
    material = json.loads((FIXTURE_ROOT / "planning-material.json").read_text())
    create["arguments"] = {"material": material}
    created = _ok(invoke(admit(create)), "native create")
    _ok(invoke(admit(start()["planning"]["created_owner"]["selection_request"])), "native select")
    current = start()
    assert current["planning"]["current_owner"]["current"] is True
    path = target / created["value"]["owner_path"]
    body = json.loads(path.read_bytes())
    update = current["planning"]["update_requests"][0]
    update["arguments"]["material"] = {key: body[key] for key in material}
    update["arguments"]["material"].update(lifecycle=body["lifecycle"], phase=body["phase"])
    update["arguments"]["material"]["continuation"]["frontier"] = "Fresh installed consumers recover this retained frontier."
    action = admit(update)
    stale_update = copy.deepcopy(update)
    stale_update["arguments"]["material"]["continuation"]["frontier"] = "Never publish this stale alternative."
    stale_action = admit(stale_update)
    applied = _ok(invoke(action), "native update")
    before = _snapshot(target)
    duplicate = invoke(action)
    assert _rejected(duplicate) or all(duplicate["result"][key] == applied[key] for key in ("status", "effects", "value", "custody")), (
        duplicate
    )
    assert _snapshot(target) == before, "an idempotent duplicate cannot publish again"
    _ok(invoke(admit(start()["planning"]["requests"][0])), "native reconcile")
    before = _snapshot(target)
    assert _rejected(invoke(stale_action)), "an unconsumed stale action cannot survive owner reconciliation"
    assert _snapshot(target) == before
    assert start()["planning"]["current_owner"]["current"] is True
    final = json.loads(path.read_bytes())
    assert final["id"] == body["id"] and final["scope"] == body["scope"]
    assert final["continuation"]["frontier"] == update["arguments"]["material"]["continuation"]["frontier"]
    assert sentinel.read_bytes() == b"preserve unrelated consumer work\n"
    assert not any(part in {"adapters", "plugins", "adapter.lock", "plugin.lock"} for ref in _snapshot(target) for part in Path(ref).parts)
    return {"fresh_process_owner_recovery": "passed", "stale_replay_preserves_state": "passed", "unrelated_state": "preserved"}


def _configuration_cases(call: Any, target: Path) -> dict[str, str]:
    target.mkdir(parents=True)
    context = {"target": str(target), "task": "Correct an explicit repository configuration", "projection": "full"}

    def start(request=None):
        return _ok(call({"action": "start", "context": {**context, **({"request": [request]} if request else {})}}), "configuration start")

    source = target / ".agentic-workspace/config.toml"
    source.parent.mkdir()
    # Explicit human-owned input, not a product installation or custody grant.
    original = b"# retained human policy\r\nschema_version=1\r\n[workspace]\r\ncli_invoke='old-command' # retain comment\r\nagent_instructions_file='AGENTS.md'\r\n"
    source.write_bytes(original)
    guidance = "Preserve human work. Delivery grants no proof or publication authority.\n"
    (target / "AGENTS.md").write_text(guidance, encoding="utf-8", newline="\n")
    initial = start()
    assert initial["startup_adapter"]["response"]["text"] == guidance
    request = next(r for r in initial["configuration_write"]["requests"] if r["arguments"]["key"] == "workspace.cli_invoke")
    assert start(request)["configuration_write"]["status"] == "unchanged"
    request["arguments"]["value"] = "agentic-workspace"
    answer = start(request)["decision_packet"]["decision_request"]["response_request"]
    answer["arguments"]["answer"] = "authorize-write"  # bounded human-decision fixture
    action = start(answer)["decision_packet"]["primary_action"]
    invoke = {"action": "invoke", "context": {**context, "invocation": action}}
    source.write_bytes(original + b"# concurrent human edit\r\n")
    before = _snapshot(target)
    assert _rejected(call(invoke))
    assert _snapshot(target) == before
    source.write_bytes(original)
    result = _ok(call(invoke), "configuration write")
    assert result["value"]["completion_authority"] is False
    assert any(r["owner"] == "startup-adapter" for r in action["source_requests"])
    assert result["continuation"]["result"]["startup_adapter"]["response"]["text"] == guidance
    assert source.read_bytes() == original.replace(b"'old-command'", b'"agentic-workspace"')
    assert start()["configuration"]["cli_invoke"] == "agentic-workspace"
    before = _snapshot(target)
    assert _rejected(call(invoke))
    assert _snapshot(target) == before
    for body, check in [
        ("schema_version=1\n[modules]\nenabled=[]\n", "disabled"),
        ("schema_version=1\n[cli_compatibility]\nminimum_reader_epoch=999\n", "incompatible"),
        ("[malformed", "malformed"),
    ]:
        source.write_text(body)
        before = _snapshot(target)
        result = start()
        if check == "disabled":
            assert all(result[owner]["status"] == "disabled" for owner in ("planning", "memory", "verification"))
        else:
            assert result.get("status", result.get("decision_packet", {}).get("status")) == "blocked"
        assert _snapshot(target) == before
    return {
        "exact_write": "passed",
        "no_op": "passed",
        "source_drift": "rejected",
        "replay": "rejected",
        "disabled_modules": "passed",
        "incompatible_reader": "rejected",
        "malformed_source": "rejected",
    }


def _verification_case(call: Any, target: Path) -> dict[str, str]:
    """Positive replacement for the retired proof CLI: exact native invoke."""
    target.mkdir(parents=True)
    source = target / "a.txt"
    source.write_text("current source")
    command = "Add-Content -Path count.txt -Value executed" if os.name == "nt" else "echo executed >> count.txt"
    manifest = target / ".agentic-workspace/verification/manifest.toml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        'schema_version="agentic-workspace/verification-manifest/v1"\n[protocols.check]\napplies_to_paths=["a.txt"]\n[proof_routes.check]\nprotocol_refs=["check"]\ncommands=['
        + json.dumps(command)
        + "]\n"
    )
    context = {"target": str(target), "task": "Check the current source", "changed": ["a.txt"], "projection": "full"}

    def start(request=None):
        return _ok(call({"action": "start", "context": {**context, **({"request": [request]} if request else {})}}), "Verification start")

    request = start()["verification"]["execution_requests"][0]
    action = start(request)["decision_packet"]["primary_action"]
    assert action["operation_id"] == "proof.report"
    invocation = {"action": "invoke", "context": {**context, "invocation": action}}
    value = _ok(call(invocation), "native proof execution")["value"]
    assert value["process"]["status"] == "passed"
    assert value["publication"]["status"] == "published"
    assert value["claim_boundary"]["completion_claim_allowed"] is False
    assert _ok(call(invocation), "idempotent proof recovery")["value"] == value
    assert (target / "count.txt").read_text().splitlines() == ["executed"]
    claim = start()["verification"]["requests"][0]
    claim["arguments"]["evidence_refs"] = [value["publication"]["reference"]]
    evidence = start(claim)["verification"]["evidence"][0]
    assert evidence["publication_admission"]["status"] == "admitted"
    assert evidence["evidence_freshness"] == "reusable"
    assert evidence["task_judgment"]["current_judgment_count"] == 0
    source.write_text("material change")
    before = _snapshot(target)
    assert start(claim)["verification"]["evidence"][0]["evidence_freshness"] != "reusable"
    assert _rejected(call(invocation))
    assert _snapshot(target) == before
    return {
        "exact_command_publication": "passed",
        "idempotent_recovery": "passed",
        "current_evidence": "admitted",
        "changed_source": "rejected",
        "completion_authority": "not-granted",
    }


def _payload_cases(call: Any, target: Path, wheel: Path) -> dict[str, str]:
    """Faithful artifact-byte fixtures; no claim of a native payload installer."""
    target.mkdir(parents=True)
    context = {"target": str(target), "task": "Inspect optional artifact payload", "projection": "full"}

    def start():
        return _ok(call({"action": "start", "context": context}), "payload start")

    absent = start()
    with zipfile.ZipFile(wheel) as archive:
        manifest = json.loads(archive.read("agentic_workspace/contracts/workspace_surfaces.json"))
        refs = manifest["payload_files"]
        for ref in refs:
            path = target / ref
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(archive.read("agentic_workspace/_payload/" + ref))
        metadata = next(name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))
        version = next(line[9:] for line in archive.read(metadata).decode().splitlines() if line.startswith("Version: "))
    before = _snapshot(target)
    present = start()
    # Exact source/owner revisions change with shipped context; effective
    # action, obligations and claim authority must remain identical.
    for key in (
        "status",
        "primary_action",
        "decision_request",
        "blockers",
        "claim_boundary",
        "pending_consequences",
        "ready_actions",
        "terminal_authority",
        "operation_revisions",
    ):
        assert absent["decision_packet"][key] == present["decision_packet"][key], key
    assert absent["configuration"] == present["configuration"]
    assert absent["planning"] == present["planning"]
    assert _snapshot(target) == before
    config = target / ".agentic-workspace/config.toml"
    config.write_text('schema_version=1\n[payload]\ntarget_release="source-current"\npolicy="required-before-work"\n')
    provenance = target / ".agentic-workspace/payload-provenance.json"
    provenance.write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/payload-provenance/v1",
                "payload_schema": "agentic-workspace/payload/v1",
                "release_identity": {"package": "agentic-workspace", "version": version},
                "payload_capabilities": ["installed-state-sync-v2"],
                "payload_files": refs,
            }
        )
    )
    assert start()["configuration"]["payload"]["status"] == "satisfied"
    path = target / refs[0]
    original = path.read_bytes()
    path.write_bytes(original + b"\nchanged after admission\n")
    before = _snapshot(target)
    drifted = start()
    assert drifted["configuration"]["payload"]["status"] == "unresolved"
    assert any(b["code"] == "native-payload-target-unproven" and "task" in b["affects"] for b in drifted["decision_packet"]["blockers"])
    assert _snapshot(target) == before
    path.write_bytes(original)
    assert start()["configuration"]["payload"]["status"] == "satisfied"
    path.unlink()
    assert start()["configuration"]["payload"]["status"] == "unresolved"
    return {
        "optional_absence_presence": "equivalent",
        "exact_artifact_bytes": "admitted",
        "drift_and_missing_bytes": "rejected",
        "fixture_authority": "read-only conformance, not installation custody",
    }


def run(*, dist_dir: Path | None = None, require_node: bool = False) -> dict[str, Any]:
    node = shutil.which("node")
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if not node or not npm:
        if require_node:
            raise ReadinessCheckError("Node.js and npm are required")
        return {"kind": "agentic-workspace/external-consumer-readiness/v2", "status": "unavailable", "reason": "node-unavailable"}
    with tempfile.TemporaryDirectory(prefix="agentic-workspace-external-consumer-") as directory:
        temp_root = Path(directory).resolve()
        assert not temp_root.is_relative_to(REPO_ROOT)
        dist = dist_dir.resolve() if dist_dir else temp_root / "dist"
        dist.mkdir(parents=True, exist_ok=True)
        wheels = sorted(dist.glob("*.whl"))
        if len(wheels) < 4:
            wheels = _build_python_artifacts(dist)
        wheel = next(p for p in wheels if p.name.startswith("agentic_workspace-"))
        archive = _pack_typescript_artifact(dist, npm)
        host_env = temp_root / "host-env"
        _install_python_stack(host_env, wheels)
        host_cli = _console_script(host_env, "agentic-workspace")
        python_root = temp_root / "python-consumer"
        # Native owners are artifact-owned: optional Python module distributions
        # are absent here and present in the independent host environment.
        python, python_script = _prepare_python_consumer(python_root, [wheel])
        typescript_root = temp_root / "typescript-consumer"
        typescript_script = _prepare_typescript_consumer(typescript_root, archive, npm)
        results = {}
        targets = []
        for language, consumer_root, executable, script in [
            ("python", python_root, python, python_script),
            ("typescript", typescript_root, node, typescript_script),
        ]:

            def call(request):
                return _consumer_request(
                    language=language, consumer_root=consumer_root, executable=executable, script=script, request=request
                )

            provenance = _ok(call({"action": "provenance"}), "installed provenance")
            assert all(Path(p).resolve().is_relative_to(consumer_root) for p in provenance.values()), provenance
            target = temp_root / (language + "-repo")
            lifecycle = exercise_native_lifecycle(call, target)
            results[language] = {
                "provenance": "installed-artifact",
                "lifecycle": lifecycle,
                "configuration": _configuration_cases(call, temp_root / (language + "-config")),
                "payload": _payload_cases(call, temp_root / (language + "-payload"), wheel),
                "verification": _verification_case(call, temp_root / (language + "-proof")),
            }
            targets.append(target)
        retained = {target: _snapshot(target) for target in targets}
        shutil.rmtree(python_root)
        shutil.rmtree(typescript_root)
        for target in targets:
            completed = _run(
                [
                    host_cli,
                    "start",
                    "--target",
                    target,
                    "--task",
                    "Maintain the installed consumer Planning owner",
                    "--format",
                    "json",
                    "--projection",
                    "full",
                ],
                cwd=target,
            )
            assert json.loads(completed.stdout)["planning"]["current_owner"]["current"] is True
            assert _snapshot(target) == retained[target], "consumer removal cannot alter repository state"
            assert str(host_env).encode() not in b"".join(retained[target].values())
        assert not _reverse_dependency_violations()
        return {
            "kind": "agentic-workspace/external-consumer-readiness/v2",
            "status": "passed",
            "artifacts": {"python_wheels": [p.name for p in wheels], "typescript_package": archive.name},
            "consumers": results,
            "supported_operations": list(REQUIRED_OPERATIONS),
            "claim_boundary": "Executed native lifecycle only; no retired generated-operation readiness or payload-installation claim.",
            "package_boundary": {
                "source_checkout_imports": 0,
                "reverse_dependency_violations": 0,
                "checked_in_residue_after_removal": 0,
                "ordinary_aw_after_removal": "passed",
            },
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prove independent external-consumer readiness from built artifacts.")
    parser.add_argument("--dist-dir", type=Path)
    parser.add_argument("--require-node", action="store_true")
    parser.add_argument("--format", choices=("json", "text"), default="text")
    args = parser.parse_args()
    try:
        report = run(dist_dir=args.dist_dir, require_node=args.require_node)
    except (ReadinessCheckError, AssertionError) as error:
        if args.format == "json":
            print(json.dumps({"kind": "agentic-workspace/external-consumer-readiness/v2", "status": "failed", "message": str(error)}))
        else:
            print(f"External consumer readiness: failed\n{error}")
        return 1
    if args.format == "json":
        print(json.dumps(report, sort_keys=True))
    else:
        print(f"External consumer readiness: {report['status']}")
        if report.get("status") == "passed":
            print("Consumers: python, typescript")
            print("Supported operations: " + ", ".join(report["supported_operations"]))
            print("Removal/no-residue/reverse-dependency proof: passed")
    return 0 if report.get("status") in {"passed", "unavailable"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
