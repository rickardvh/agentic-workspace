from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPO_ROOT / "tests/fixtures/external_consumer"
REQUIRED_OPERATIONS = ("config.report", "delegation-outcome.append")
READINESS_CASES = (
    "absent",
    "disabled",
    "incompatible",
    "malformed",
    "retryable",
    "additive-field",
    "mutation-applied",
    "mutation-noop",
    "mutation-rejected",
    "mutation-failed",
)
READINESS_EXECUTORS = {
    "cli-json": "direct-cli-json",
    "python": "generated-python-client",
    "typescript": "generated-typescript-client",
    "vendor-neutral": "packed-typescript-client",
}
MUTATION_VALUES = {
    "delegation_target": "external-consumer",
    "task_class": "bounded-conformance",
    "scope_class": "bounded-conformance",
    "source_type": "proof-receipt",
    "source_ref": "external-consumer/delegation-outcome.append",
    "idempotency_key": "external-consumer-delegation-outcome-append",
    "outcome": "success",
}
MUTATION_PATH = Path(".agentic-workspace/delegation-outcomes.json")


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
    for package in ("agentic-memory", "agentic-planning", "agentic-verification"):
        _run([uv, "build", "--wheel", "--package", package, "--out-dir", dist], cwd=REPO_ROOT)
    wheels = sorted(dist.glob("*.whl"))
    if len(wheels) < 4:
        raise ReadinessCheckError("expected workspace plus three module wheels")
    return wheels


def _pack_typescript_artifact(dist: Path, npm: str) -> Path:
    completed = _run(
        [npm, "pack", "--json", "--pack-destination", dist],
        cwd=REPO_ROOT / "generated/workspace/typescript",
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


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "--quiet"], cwd=root)
    _run(["git", "config", "user.email", "external-consumer@example.invalid"], cwd=root)
    _run(["git", "config", "user.name", "External Consumer Proof"], cwd=root)


def _prepare_target(host_cli: Path, root: Path, *, mirror_payload: bool = False, modules: str = "") -> None:
    _init_repo(root)
    command: list[str | Path] = [host_cli, "install", "--target", root, "--non-interactive", "--format", "json"]
    if modules:
        command.extend(["--modules", modules])
    if mirror_payload:
        command.append("--mirror-payload")
    _run(command, cwd=root)
    _run(["git", "add", "-A"], cwd=root)
    _run(["git", "commit", "--quiet", "-m", "baseline"], cwd=root)


def _git_status(root: Path) -> str:
    return _run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=root).stdout.strip()


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
    completed = _run([executable, script, request_path], cwd=consumer_root)
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
    return payload.get("result")


def _error(payload: Mapping[str, Any], kind: str, label: str) -> Mapping[str, Any]:
    if payload.get("status") != "error" or payload.get("kind") != kind:
        raise ReadinessCheckError(f"{label} expected {kind}: {json.dumps(payload, sort_keys=True)}")
    return payload


def _semantic_projection(value: Any, roots: Sequence[Path]) -> Any:
    if isinstance(value, dict):
        return {key: _semantic_projection(item, roots) for key, item in value.items()}
    if isinstance(value, list):
        return [_semantic_projection(item, roots) for item in value]
    if isinstance(value, str):
        normalized = value.replace("\\", "/")
        for root in roots:
            normalized = normalized.replace(root.resolve().as_posix(), "<target>")
        return normalized
    return value


def _assert_receipts(receipt_store: Mapping[str, Any]) -> None:
    receipts = {
        str(item.get("operation_id")): item
        for item in receipt_store.get("receipts", [])
        if isinstance(item, Mapping) and item.get("status") == "passed"
    }
    for operation_id in REQUIRED_OPERATIONS:
        receipt = receipts.get(operation_id)
        if not isinstance(receipt, Mapping):
            raise ReadinessCheckError(f"missing passing packaged receipt for {operation_id}")
        for case in READINESS_CASES:
            if (receipt.get("cases", {}).get(case) or {}).get("status") != "passed":
                raise ReadinessCheckError(f"{operation_id} receipt lacks case {case}")
            for transport in READINESS_EXECUTORS:
                if (receipt.get("case_transport_matrix", {}).get(case, {}).get(transport) or {}).get("status") != "passed":
                    raise ReadinessCheckError(f"{operation_id} receipt lacks {case} × {transport}")
        for transport, executor in READINESS_EXECUTORS.items():
            evidence = receipt.get("executors", {}).get(transport) or {}
            if evidence.get("status") != "passed" or evidence.get("executor_id") != executor:
                raise ReadinessCheckError(f"{operation_id} receipt lacks executor provenance for {transport}")
        footprints = receipt.get("footprints", {})
        for footprint in ("necessary-surfaces", "full-mirror", "semantic-parity"):
            if (footprints.get(footprint) or {}).get("status") != "passed":
                raise ReadinessCheckError(f"{operation_id} receipt lacks footprint {footprint}")


def _mutation_scenarios(
    *,
    language: str,
    call: Any,
    source_target: Path,
    target: Path,
    host_invocation: list[str],
) -> dict[str, Any]:
    shutil.copytree(source_target, target)
    sentinel = target / "unrelated-state.txt"
    sentinel.write_text("preserve-me", encoding="utf-8", newline="\n")
    request = {
        "action": "invoke",
        "target": str(target),
        "invocation": host_invocation,
        "operation_id": "delegation-outcome.append",
        "values": MUTATION_VALUES,
        "allow_runtime_backed": True,
    }
    _ok(call(request), f"{language} mutation applied")
    ledger = target / MUTATION_PATH
    if not ledger.is_file():
        raise ReadinessCheckError(f"{language} mutation did not create {MUTATION_PATH.as_posix()}")
    before = ledger.read_bytes()
    duplicate = call(request)
    duplicate_error = duplicate.get("details", {}).get("error", {})
    if (
        duplicate.get("status") != "error"
        or duplicate.get("kind") != "rejected"
        or duplicate_error.get("failure_class") != "duplicate-mutation"
        or duplicate_error.get("completion_boundary") != "mutation-not-applied"
        or ledger.read_bytes() != before
        or sentinel.read_text(encoding="utf-8") != "preserve-me"
    ):
        raise ReadinessCheckError(
            f"{language} duplicate mutation was not safely blocked: {json.dumps(duplicate, sort_keys=True)}"
        )
    rejected = dict(request)
    rejected["values"] = {**MUTATION_VALUES, "operation": "correct-or-dispute", "predecessor_id": "missing-predecessor"}
    rejected_result = call(rejected)
    rejected_error = rejected_result.get("details", {}).get("error", {})
    if (
        rejected_result.get("status") != "error"
        or rejected_result.get("kind") != "rejected"
        or rejected_error.get("failure_class") != "invalid-lifecycle-transition"
        or rejected_error.get("completion_boundary") != "mutation-not-applied"
        or ledger.read_bytes() != before
        or sentinel.read_text(encoding="utf-8") != "preserve-me"
    ):
        raise ReadinessCheckError(f"{language} invalid transition did not preserve state")
    failure_target = target.parent / f"{target.name}-write-failure"
    shutil.copytree(target, failure_target)
    failure_ledger = failure_target / MUTATION_PATH
    failure_ledger.unlink()
    failure_ledger.mkdir()
    failed_request = {**request, "target": str(failure_target)}
    failed_result = call(failed_request)
    failed_error = failed_result.get("details", {}).get("error", {})
    if (
        failed_result.get("status") != "error"
        or failed_result.get("kind") != "failed"
        or failed_error.get("failure_class") != "unexpected-runtime-exception"
        or failed_error.get("completion_boundary") != "command-did-not-complete"
        or not str(failed_error.get("message") or "").strip()
        or not failure_ledger.is_dir()
    ):
        raise ReadinessCheckError(f"{language} write failure was not surfaced")
    if (failure_target / "unrelated-state.txt").read_text(encoding="utf-8") != "preserve-me":
        raise ReadinessCheckError(f"{language} write failure changed unrelated state")
    return {
        "mutation-applied": "passed",
        "mutation-noop": str(duplicate.get("kind") or "error"),
        "mutation-rejected": str(rejected_result.get("kind") or "error"),
        "mutation-failed": str(failed_result.get("kind") or "error"),
        "unrelated_state_unchanged": True,
    }


def _reverse_dependency_violations() -> list[str]:
    violations: list[str] = []
    allowed = {"agentic-workspace", "agentic-memory", "agentic-planning", "agentic-verification"}
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


def run(*, dist_dir: Path | None = None, require_node: bool = False) -> dict[str, Any]:
    node = shutil.which("node")
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if not node or not npm:
        if require_node:
            raise ReadinessCheckError("Node.js and npm are required")
        return {"kind": "agentic-workspace/external-consumer-readiness/v1", "status": "unavailable", "reason": "node-unavailable"}
    with tempfile.TemporaryDirectory(prefix="agentic-workspace-external-consumer-") as directory:
        temp_root = Path(directory).resolve()
        if temp_root == REPO_ROOT or REPO_ROOT in temp_root.parents:
            raise ReadinessCheckError("external consumer root must be outside the source checkout")
        dist = dist_dir.resolve() if dist_dir else temp_root / "dist"
        dist.mkdir(parents=True, exist_ok=True)
        wheels = sorted(dist.glob("*.whl"))
        if len(wheels) < 4:
            wheels = _build_python_artifacts(dist)
        typescript_archive = _pack_typescript_artifact(dist, npm)

        host_env = temp_root / "host-env"
        _install_python_stack(host_env, wheels)
        host_cli = _console_script(host_env, "agentic-workspace")
        host_invocation = [str(host_cli)]

        python_root = temp_root / "python-consumer"
        python_executable, python_script = _prepare_python_consumer(python_root, wheels)
        typescript_root = temp_root / "typescript-consumer"
        typescript_script = _prepare_typescript_consumer(typescript_root, typescript_archive, npm)

        targets = temp_root / "targets"
        necessary = targets / "necessary"
        mirrored = targets / "full-mirror"
        optional_absent = targets / "optional-absent"
        optional_present = targets / "optional-present"
        absent = targets / "absent"
        disabled = targets / "disabled"
        incompatible = targets / "incompatible"
        _prepare_target(host_cli, necessary)
        _prepare_target(host_cli, mirrored, mirror_payload=True)
        _prepare_target(host_cli, optional_absent, modules="planning")
        _prepare_target(host_cli, optional_present, modules="planning,memory,verification")
        _init_repo(absent)
        _init_repo(disabled)
        _init_repo(incompatible)
        (disabled / ".agentic-workspace").mkdir()
        (disabled / ".agentic-workspace/config.toml").write_text(
            "schema_version = 1\n[workspace]\nenabled = false\n", encoding="utf-8", newline="\n"
        )
        (incompatible / ".agentic-workspace").mkdir()
        (incompatible / ".agentic-workspace/config.toml").write_text(
            'schema_version = 1\n[workspace]\nenabled = true\n\n[cli_compatibility]\nexact_version = "999.0.0"\n',
            encoding="utf-8",
            newline="\n",
        )

        def request_for(language: str, request: Mapping[str, Any]) -> dict[str, Any]:
            if language == "python":
                return _consumer_request(
                    language=language,
                    consumer_root=python_root,
                    executable=python_executable,
                    script=python_script,
                    request=request,
                )
            return _consumer_request(
                language=language,
                consumer_root=typescript_root,
                executable=node,
                script=typescript_script,
                request=request,
            )

        language_results: dict[str, Any] = {}
        for language in ("python", "typescript"):

            def call(request: Mapping[str, Any], current: str = language) -> dict[str, Any]:
                return request_for(current, request)

            provenance = _ok(call({"action": "provenance"}), f"{language} provenance")
            for path in provenance.values():
                resolved = Path(str(path)).resolve()
                if resolved == REPO_ROOT or REPO_ROOT in resolved.parents:
                    raise ReadinessCheckError(f"{language} loaded a source-checkout path: {resolved}")
            readiness = _ok(
                call({"action": "readiness", "operations": REQUIRED_OPERATIONS, "allow_runtime_backed": True}),
                f"{language} readiness",
            )
            if readiness.get("status") != "ready" or set(readiness.get("supported_operations", [])) != set(REQUIRED_OPERATIONS):
                raise ReadinessCheckError(f"{language} readiness was not complete: {json.dumps(readiness, sort_keys=True)}")
            supported_evidence = readiness.get("supported_operation_evidence", [])
            if (
                {str(item.get("id")) for item in supported_evidence if isinstance(item, Mapping)} != set(REQUIRED_OPERATIONS)
                or any(not str(item.get("receipt_ref") or "") for item in supported_evidence if isinstance(item, Mapping))
                or int((readiness.get("operation_accounting") or {}).get("not_advertised_count") or 0) <= 0
            ):
                raise ReadinessCheckError(f"{language} readiness evidence/accounting was incomplete")
            receipts = _ok(call({"action": "receipts"}), f"{language} receipts")
            _assert_receipts(receipts)
            negotiated = _ok(
                call(
                    {
                        "action": "negotiate",
                        "requirements": {operation: None for operation in REQUIRED_OPERATIONS},
                        "allow_runtime_backed": True,
                    }
                ),
                f"{language} negotiation",
            )
            incompatible_negotiation = _ok(
                call(
                    {
                        "action": "negotiate",
                        "requirements": {"config.report": "sha256:intentional-incompatibility"},
                        "allow_runtime_backed": True,
                    }
                ),
                f"{language} incompatibility",
            )
            if not negotiated.get("compatible") or incompatible_negotiation.get("compatible"):
                raise ReadinessCheckError(f"{language} compatibility negotiation was not fail-closed")
            for target, expected in (
                (absent, "absent"),
                (disabled, "disabled"),
                (necessary, "enabled"),
                (incompatible, "incompatible"),
            ):
                detected = _ok(call({"action": "detect", "target": str(target)}), f"{language} detect {expected}")
                if detected.get("status") != expected:
                    raise ReadinessCheckError(f"{language} detection expected {expected}: {detected}")
                if expected == "enabled":
                    continue
                _error(
                    call(
                        {
                            "action": "invoke",
                            "target": str(target),
                            "invocation": host_invocation,
                            "operation_id": "config.report",
                            "values": {},
                            "allow_runtime_backed": True,
                        }
                    ),
                    expected,
                    f"{language} invoke {expected}",
                )
            _error(
                call(
                    {
                        "action": "invoke",
                        "target": str(necessary),
                        "invocation": host_invocation,
                        "operation_id": "config.report",
                        "values": {"unexpected_external_field": True},
                        "allow_runtime_backed": True,
                    }
                ),
                "malformed",
                f"{language} malformed",
            )
            operation_request = {
                "action": "invoke",
                "invocation": host_invocation,
                "operation_id": "config.report",
                "values": {},
                "allow_runtime_backed": True,
            }
            necessary_result = _ok(call({**operation_request, "target": str(necessary)}), f"{language} necessary")
            mirrored_result = _ok(call({**operation_request, "target": str(mirrored)}), f"{language} mirrored")
            if _semantic_projection(necessary_result, [necessary]) != _semantic_projection(mirrored_result, [mirrored]):
                raise ReadinessCheckError(f"{language} necessary/full-mirror semantics diverged")
            _ok(call({**operation_request, "target": str(optional_absent)}), f"{language} optional absent")
            _ok(call({**operation_request, "target": str(optional_present)}), f"{language} optional present")

            stub_target = targets / f"{language}-stub"
            shutil.copytree(necessary, stub_target)
            response_path = temp_root / f"{language}-config-result.json"
            response_path.write_text(json.dumps(necessary_result), encoding="utf-8", newline="\n")
            stub = temp_root / "transport_stub.py"
            stub.write_text(
                "import json, pathlib, sys\n"
                "mode = sys.argv[1]\n"
                "response = pathlib.Path(sys.argv[2])\n"
                "if mode == 'retryable':\n"
                " print(json.dumps({'kind':'agentic-workspace/retryable-operation-error/v1','status':'retryable','message':'retry after refresh'}))\n"
                " raise SystemExit(3)\n"
                "payload = json.loads(response.read_text(encoding='utf-8'))\n"
                "payload['future_additive_field'] = {'preserved': True}\n"
                "print(json.dumps(payload))\n",
                encoding="utf-8",
                newline="\n",
            )
            retry_request = {
                **operation_request,
                "target": str(stub_target),
                "invocation": [str(_python(host_env)), str(stub), "retryable", str(response_path)],
            }
            _error(call(retry_request), "retryable", f"{language} retryable")
            additive = _ok(
                call(
                    {
                        **retry_request,
                        "invocation": [str(_python(host_env)), str(stub), "additive", str(response_path)],
                    }
                ),
                f"{language} additive",
            )
            if (additive.get("future_additive_field") or {}).get("preserved") is not True:
                raise ReadinessCheckError(f"{language} additive field was not preserved")
            mutation = _mutation_scenarios(
                language=language,
                call=call,
                source_target=necessary,
                target=targets / f"{language}-mutation",
                host_invocation=host_invocation,
            )
            language_results[language] = {
                "provenance": "installed-artifact",
                "readiness": readiness.get("status"),
                "readiness_report": readiness,
                "negotiation": "compatible-and-fail-closed",
                "scenarios": {
                    "absent": "passed",
                    "disabled": "passed",
                    "incompatible": "passed",
                    "malformed": "passed",
                    "retryable": "passed",
                    "additive-field": "passed",
                    "necessary/full-mirror": "equivalent",
                    "optional-module-absence/presence": "passed",
                    **mutation,
                },
            }

        for target in (necessary, mirrored, optional_absent, optional_present):
            if _git_status(target):
                raise ReadinessCheckError(f"consumer execution changed checked-in target state: {target.name}")
        shutil.rmtree(python_root)
        shutil.rmtree(typescript_root)
        for target in (necessary, mirrored):
            _run([host_cli, "status", "--target", target, "--format", "json"], cwd=target)
            if _git_status(target):
                raise ReadinessCheckError(f"consumer removal changed checked-in target state: {target.name}")
        violations = _reverse_dependency_violations()
        if violations:
            raise ReadinessCheckError("reverse dependency violations: " + "; ".join(violations))
        return {
            "kind": "agentic-workspace/external-consumer-readiness/v1",
            "status": "passed",
            "artifacts": {
                "python_wheels": [path.name for path in wheels],
                "typescript_package": typescript_archive.name,
            },
            "consumers": language_results,
            "package_boundary": {
                "source_checkout_imports": 0,
                "reverse_dependency_violations": 0,
                "checked_in_residue_after_execution": 0,
                "checked_in_residue_after_removal": 0,
                "ordinary_aw_after_removal": "passed",
            },
            "supported_operations": list(REQUIRED_OPERATIONS),
            "supported_operation_evidence": language_results["python"]["readiness_report"]["supported_operation_evidence"],
            "operation_accounting": language_results["python"]["readiness_report"]["operation_accounting"],
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prove independent external-consumer readiness from built artifacts.")
    parser.add_argument("--dist-dir", type=Path)
    parser.add_argument("--require-node", action="store_true")
    parser.add_argument("--format", choices=("json", "text"), default="text")
    args = parser.parse_args()
    try:
        report = run(dist_dir=args.dist_dir, require_node=args.require_node)
    except ReadinessCheckError as error:
        if args.format == "json":
            print(json.dumps({"kind": "agentic-workspace/external-consumer-readiness/v1", "status": "failed", "message": str(error)}))
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
