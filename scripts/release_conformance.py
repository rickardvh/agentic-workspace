from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Any


def _run(
    argv: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        command = " ".join(argv[:3])
        raise RuntimeError(
            f"command failed ({completed.returncode}): {command}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return completed


def _json(argv: list[str], *, cwd: Path | None = None) -> dict[str, Any] | list[Any]:
    return json.loads(_run(argv, cwd=cwd).stdout)


def _python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def _cli(venv: Path) -> Path:
    return venv / ("Scripts/agentic-workspace.exe" if sys.platform == "win32" else "bin/agentic-workspace")


def _write_external_module(root: Path) -> None:
    package = root / "src" / "external_delegate"
    package.mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        """[build-system]
requires = [\"hatchling\"]
build-backend = \"hatchling.build\"

[project]
name = \"agentic-workspace-external-delegate\"
version = \"1.0.0\"
dependencies = [\"agentic-workspace>=1,<2\"]

[project.entry-points.\"agentic_workspace.modules\"]
delegate = \"external_delegate:module\"

[tool.hatch.build.targets.wheel]
packages = [\"src/external_delegate\"]
""",
        encoding="utf-8",
    )
    (package / "__init__.py").write_text(
        """from __future__ import annotations

import hashlib
import json
from pathlib import Path

from agentic_workspace.modules import Module
from agentic_workspace.operations import Operation


def _digest(path):
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _paths(root):
    state = root / ".agentic-workspace"
    return state / "planning.json", state / "delegation-evidence.json"


def _contribute(context):
    request = context.get("delegate")
    if not isinstance(request, dict):
        return None
    root = Path(str(context["target"])).resolve()
    planning_path, evidence_path = _paths(root)
    planning = json.loads(planning_path.read_text(encoding="utf-8"))
    parent = planning.get("active", {})
    if evidence_path.is_file():
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        return {
            "revision": _digest(evidence_path),
            "facts": {"worker_result": evidence},
            "claims": {"allowed": ["delegated-result"]},
            "terminal": True,
        }
    if parent.get("id") != request.get("parent_id"):
        return {
            "revision": _digest(planning_path),
            "blockers": [{"code": "parent-mismatch", "message": "delegation does not belong to active parent"}],
            "claims": {"blocked": ["complete"]},
        }
    return {
        "revision": _digest(planning_path),
        "actions": [{
            "operation_id": "delegate.run",
            "arguments": {
                "target": str(root),
                "parent_id": str(request["parent_id"]),
                "task": str(request["task"]),
                "expected_parent_revision": _digest(planning_path),
            },
            "effects": ["delegation-evidence", "planning-state"],
            "priority": 75,
        }],
        "claims": {"blocked": ["complete"]},
    }


def _run(arguments):
    root = Path(arguments["target"])
    planning_path, evidence_path = _paths(root)
    if _digest(planning_path) != arguments["expected_parent_revision"]:
        return {"status": "rejected", "effects": [], "value": {"reason": "stale-parent"}}
    planning = json.loads(planning_path.read_text(encoding="utf-8"))
    output = root / "delegated-review.txt"
    output.write_text("bounded external review complete\\n", encoding="utf-8")
    evidence = {
        "parent_id": arguments["parent_id"],
        "worker": "external",
        "outcome": "complete",
        "evidence": [{"path": output.name, "sha256": _digest(output)}],
        "execution_count": 1,
    }
    evidence_path.write_text(json.dumps(evidence, sort_keys=True), encoding="utf-8")
    planning["revision"] = int(planning.get("revision", 0)) + 1
    planning["active"] = {"id": arguments["parent_id"], "status": "ready-to-complete"}
    planning_path.write_text(json.dumps(planning, sort_keys=True), encoding="utf-8")
    return {
        "status": "applied",
        "effects": ["delegation-evidence", "planning-state"],
        "value": evidence,
    }


def module():
    return Module(
        name="delegate",
        claims=("delegated-result",),
        contribute=_contribute,
        operations=(Operation(
            "delegate.run",
            {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "minLength": 1},
                    "parent_id": {"type": "string", "minLength": 1},
                    "task": {"type": "string", "minLength": 1},
                    "expected_parent_revision": {"type": "string", "minLength": 1},
                },
                "required": ["target", "parent_id", "task", "expected_parent_revision"],
                "additionalProperties": False,
            },
            ("delegation-evidence", "planning-state"),
            _run,
        ),),
    )
""",
        encoding="utf-8",
    )


def _assert_artifacts(wheel: Path, sdist: Path) -> None:
    forbidden = ("generated/", "packages/", ".agentic-workspace/")
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
    assert "agentic_workspace/decision.py" in names
    assert not any(name.startswith(forbidden) for name in names)
    with tarfile.open(sdist) as archive:
        names = archive.getnames()
    assert not any(any(f"/{part}" in name for part in forbidden) for name in names)


def _assert_typescript_artifact(package: Path) -> None:
    with tarfile.open(package) as archive:
        names = set(archive.getnames())
    assert {
        "package/package.json",
        "package/semantic-ir.json",
        "package/dist/index.js",
        "package/dist/index.d.ts",
    } <= names
    assert not any("src/agentic_workspace" in name or ".agentic-workspace" in name for name in names)


def _follow_exact(cli: Path, repository: Path, decision: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Model a partial-compliance client that knows only start, invoke, and next_decision."""

    results: list[dict[str, Any]] = []
    current = decision
    for _ in range(8):
        invocation = current.get("primary_action")
        if invocation is None:
            return results, current
        result = _json([str(cli), "invoke", "--target", str(repository), "--invocation", json.dumps(invocation)])
        assert isinstance(result, dict)
        results.append(result)
        current = result["next_decision"]
    raise AssertionError("exact-invocation flow did not terminate within eight operations")


def run(root: Path) -> dict[str, Any]:
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv is required for release conformance")
    npm = shutil.which("npm")
    node = shutil.which("node")
    if npm is None or node is None:
        raise RuntimeError("Node.js and npm are required for two-language release conformance")
    with tempfile.TemporaryDirectory(prefix="agentic-workspace-v1-") as raw_temp:
        temp = Path(raw_temp)
        dist = temp / "dist"
        _run([uv, "build", "--wheel", "--sdist", "--out-dir", str(dist)], cwd=root)
        wheel = next(dist.glob("*.whl"))
        sdist = next(dist.glob("*.tar.gz"))
        _assert_artifacts(wheel, sdist)
        _run([npm, "pack", str(root / "typescript"), "--pack-destination", str(dist)])
        typescript_package = next(dist.glob("*.tgz"))
        _assert_typescript_artifact(typescript_package)

        venv = temp / "venv"
        _run([uv, "venv", "--seed", str(venv)])
        python = _python(venv)
        cli = _cli(venv)
        _run([uv, "pip", "install", "--python", str(python), str(wheel)])

        installed = _json([uv, "pip", "list", "--python", str(python), "--format", "json"])
        assert isinstance(installed, list)
        names = {str(item["name"]).lower() for item in installed if isinstance(item, dict)}
        assert "agentic-workspace" in names
        assert not {"agentic-workspace-core", "agentic-workspace-planning", "agentic-workspace-memory"} & names

        repository = temp / "repository"
        repository.mkdir()
        default_env = dict(os.environ)
        default_env.pop("AW_SESSION_LOG", None)
        direct = json.loads(
            _run([str(cli), "start", "--target", str(repository), "--task", "edit one file"], env=default_env).stdout
        )
        assert isinstance(direct, dict) and direct["status"] == "direct"
        assert not (repository / ".agentic-workspace").exists()

        logging_repository = temp / "logging-repository"
        logging_repository.mkdir()
        logging_env = {**default_env, "AW_SESSION_LOG": "release-conformance"}
        logged = json.loads(
            _run(
                [str(cli), "start", "--target", str(logging_repository), "--task", "edit one file"], env=logging_env
            ).stdout
        )
        assert logged == direct
        session_log = (
            logging_repository / ".agentic-workspace" / "local" / "logs" / "aw-session-release-conformance.jsonl"
        )
        event = json.loads(session_log.read_text(encoding="utf-8"))
        assert event["payload"] == direct
        analysis = _json(
            [
                str(python),
                "-m",
                "agentic_workspace.session_logging",
                "analyze",
                "--target",
                str(logging_repository),
                "--session",
                "release-conformance",
            ]
        )
        assert isinstance(analysis, dict) and analysis["command_count"] == 1
        exported = _json(
            [
                str(python),
                "-m",
                "agentic_workspace.session_logging",
                "export",
                "--target",
                str(logging_repository),
                "--session",
                "release-conformance",
            ]
        )
        assert isinstance(exported, dict) and Path(str(exported["path"])).is_file()
        invalid_logging_env = {**default_env, "AW_SESSION_LOG": "../invalid"}
        isolated = _run(
            [str(cli), "start", "--target", str(logging_repository), "--task", "edit one file"],
            env=invalid_logging_env,
        )
        assert json.loads(isolated.stdout) == direct
        assert "session logging failed" in isolated.stderr

        probe = (
            "import json,sys; from agentic_workspace.workspace import Workspace; "
            "print(json.dumps(Workspace(sys.argv[1]).start(task='edit one file'), sort_keys=True))"
        )
        python_decision = _json([str(python), "-c", probe, str(repository)])
        assert python_decision == direct

        typescript_consumer = temp / "typescript-consumer"
        typescript_consumer.mkdir()
        (typescript_consumer / "package.json").write_text(
            json.dumps({"name": "aw-black-box-consumer", "private": True, "type": "module"}), encoding="utf-8"
        )
        _run(
            [npm, "install", "--ignore-scripts", "--no-audit", "--no-fund", str(typescript_package)],
            cwd=typescript_consumer,
        )
        typescript_probe = (
            'import { compileSourceDecision } from "@rickardvh/agentic-workspace"; '
            "console.log(JSON.stringify(compileSourceDecision([], "
            "{task: 'edit one file', changed_paths: [], claims: []})));"
        )
        typescript_decision = json.loads(
            _run([node, "--input-type=module", "-e", typescript_probe], cwd=typescript_consumer).stdout
        )
        assert typescript_decision == direct
        external_vector = {
            "intent": {"task": "review external change"},
            "contributions": [
                {
                    "owner": "external.review",
                    "revision": "external-1",
                    "facts": {"subject": "change"},
                    "resources": [{"id": "contract", "revision": "one", "locator": "external://contract"}],
                    "procedures": [{"id": "review", "revision": "one", "locator": "external://review"}],
                    "actions": [
                        {
                            "operation_id": "external.review",
                            "arguments": {"subject": "change"},
                            "effects": ["review-evidence"],
                        }
                    ],
                }
            ],
        }
        python_external_probe = (
            "import json,sys; from agentic_workspace import compile_source_decision; "
            "value=json.loads(sys.argv[1]); "
            "print(json.dumps(compile_source_decision(value['contributions'], intent=value['intent'])))"
        )
        python_external = json.loads(
            _run([str(python), "-c", python_external_probe, json.dumps(external_vector)]).stdout
        )
        typescript_external_probe = (
            'import { compileSourceDecision } from "@rickardvh/agentic-workspace"; '
            "const value=JSON.parse(process.argv[1]); "
            "console.log(JSON.stringify(compileSourceDecision(value.contributions, value.intent)));"
        )
        typescript_external = json.loads(
            _run(
                [node, "--input-type=module", "-e", typescript_external_probe, json.dumps(external_vector)],
                cwd=typescript_consumer,
            ).stdout
        )
        assert typescript_external == python_external
        assert typescript_external["procedures"][0]["authority"] == "reference-only"

        help_text = _run([str(cli), "--help"]).stdout.lower()
        for removed in ("checkpoint", "work-thread", "carry", "final-response", "autopilot", "research", "provider"):
            assert removed not in help_text

        memory_repo = temp / "memory-repository"
        memory_repo.mkdir()
        memory_intent = {"memory": {"key": "decision", "value": "small"}}
        memory = _json([str(cli), "start", "--target", str(memory_repo), "--intent", json.dumps(memory_intent)])
        assert isinstance(memory, dict) and memory["relevant_owners"] == ["memory"]
        unrelated = memory_repo / "unrelated.txt"
        unrelated.write_text("does not invalidate source-owned memory", encoding="utf-8")
        recorded = _json(
            [str(cli), "invoke", "--target", str(memory_repo), "--invocation", json.dumps(memory["primary_action"])]
        )
        assert isinstance(recorded, dict) and recorded["next_decision"]["status"] == "terminal"
        retried = _json(
            [str(cli), "invoke", "--target", str(memory_repo), "--invocation", json.dumps(memory["primary_action"])]
        )
        assert retried == recorded

        read_intent = {"memory": {"operation": "read", "key": "decision"}}
        read = _json([str(cli), "start", "--target", str(memory_repo), "--intent", json.dumps(read_intent)])
        assert isinstance(read, dict) and read["primary_action"]["operation_id"] == "memory.read"
        read_result = _json(
            [str(cli), "invoke", "--target", str(memory_repo), "--invocation", json.dumps(read["primary_action"])]
        )
        assert isinstance(read_result, dict) and read_result["value"] == {"key": "decision", "value": "small"}

        python_repo = temp / "python-memory-repository"
        python_repo.mkdir()
        operation_probe = (
            "import json,sys; from agentic_workspace.workspace import Workspace; "
            "w=Workspace(sys.argv[1]); i=json.loads(sys.argv[2]); "
            "d=w.start(intent=i); print(json.dumps(w.invoke(d['primary_action']),sort_keys=True))"
        )
        python_recorded = _json([str(python), "-c", operation_probe, str(python_repo), json.dumps(memory_intent)])
        assert isinstance(python_recorded, dict)
        for field in ("kind", "operation_id", "status", "effects", "value"):
            assert python_recorded[field] == recorded[field]
        assert python_recorded["next_decision"]["status"] == recorded["next_decision"]["status"]

        stale = _json(
            [
                str(cli),
                "start",
                "--target",
                str(memory_repo),
                "--intent",
                json.dumps({"memory": {"key": "decision", "value": "new"}}),
            ]
        )
        assert isinstance(stale, dict)
        memory_path = memory_repo / ".agentic-workspace" / "memory.json"
        memory_path.write_text(memory_path.read_text(encoding="utf-8") + " ", encoding="utf-8")
        stale_run = subprocess.run(
            [str(cli), "invoke", "--target", str(memory_repo), "--invocation", json.dumps(stale["primary_action"])],
            capture_output=True,
            text=True,
            check=False,
        )
        assert stale_run.returncode == 2 and "source state changed" in stale_run.stdout
        fresh = _json(
            [
                str(cli),
                "start",
                "--target",
                str(memory_repo),
                "--intent",
                json.dumps({"memory": {"key": "decision", "value": "new"}}),
            ]
        )
        assert isinstance(fresh, dict) and fresh["input_revision"] != stale["input_revision"]

        legacy = repository / ".agentic-workspace"
        legacy.mkdir()
        (legacy / "WORKFLOW.md").write_text("pre-v1 managed marker", encoding="utf-8")
        unknown = legacy / "repository-owned.md"
        unknown.write_text("preserve", encoding="utf-8")
        migration = _json([str(cli), "start", "--target", str(repository), "--task", "continue"])
        assert isinstance(migration, dict)
        assert migration["primary_action"]["operation_id"] == "workspace.remove-legacy"
        migrated = _json(
            [str(cli), "invoke", "--target", str(repository), "--invocation", json.dumps(migration["primary_action"])]
        )
        assert isinstance(migrated, dict) and migrated["next_decision"]["status"] == "direct"
        assert unknown.read_text(encoding="utf-8") == "preserve"

        planning_only = temp / "planning-only"
        planning_only.mkdir()
        planning_only_state = {
            "schema_version": 1,
            "revision": 1,
            "active": {"id": "draft", "status": "in-progress"},
        }
        planning_only_path = planning_only / ".agentic-workspace" / "planning.json"
        planning_only_path.parent.mkdir()
        planning_only_path.write_text(json.dumps(planning_only_state), encoding="utf-8")
        planning_decision = _json([str(cli), "start", "--target", str(planning_only), "--task", "draft"])
        assert isinstance(planning_decision, dict)
        assert planning_decision["relevant_owners"] == ["planning"]
        assert planning_decision["claim_boundary"]["blocked"] == ["complete"]

        verification_only = temp / "verification-only"
        verification_only.mkdir()
        verification_path = verification_only / ".agentic-workspace" / "verification.json"
        verification_path.parent.mkdir()
        verification_path.write_text(
            json.dumps({"schema_version": 1, "subject_revision": "standalone", "status": "passed", "results": []}),
            encoding="utf-8",
        )
        verification_decision = _json(
            [str(cli), "start", "--target", str(verification_only), "--task", "inspect proof"]
        )
        assert isinstance(verification_decision, dict)
        assert verification_decision["relevant_owners"] == ["verification"]
        assert verification_decision["claim_boundary"]["allowed"] == ["complete"]

        combined = temp / "combined-modules"
        combined_state = combined / ".agentic-workspace"
        combined_state.mkdir(parents=True)
        (combined_state / "planning.json").write_text(
            json.dumps({"schema_version": 1, "revision": 1, "active": {"id": "combined", "status": "complete"}}),
            encoding="utf-8",
        )
        (combined_state / "memory.json").write_text(
            json.dumps({"schema_version": 1, "revision": 1, "records": [{"key": "combined", "value": True}]}),
            encoding="utf-8",
        )
        (combined_state / "verification.json").write_text(
            json.dumps({"schema_version": 1, "subject_revision": "combined", "status": "passed", "results": []}),
            encoding="utf-8",
        )
        combined_decision = _json([str(cli), "start", "--target", str(combined), "--task", "resume"])
        assert isinstance(combined_decision, dict)
        assert combined_decision["relevant_owners"] == ["memory", "planning", "verification"]
        assert combined_decision["status"] == "terminal"

        planning = {
            "schema_version": 1,
            "revision": 1,
            "active": {"id": "release", "status": "ready-to-complete"},
            "validation": [[str(python), "-c", "raise SystemExit(0)"]],
        }
        (legacy / "planning.json").write_text(json.dumps(planning), encoding="utf-8")
        proof = _json([str(cli), "start", "--target", str(repository), "--task", "release"])
        assert isinstance(proof, dict) and proof["primary_action"]["operation_id"] == "verification.run"
        assert proof["relevant_owners"] == ["planning", "verification"]
        flow, terminal = _follow_exact(cli, repository, proof)
        assert [result["operation_id"] for result in flow] == ["verification.run", "planning.complete"]
        assert terminal["status"] == "terminal"
        assert "complete" in terminal["claim_boundary"]["allowed"]

        detail_probe = (
            "import json,sys; from agentic_workspace.decision import select_decision_detail; "
            "d=json.loads(sys.argv[1]); "
            "v=select_decision_detail(d,['status','claim_boundary']); print(json.dumps(v,sort_keys=True))"
        )
        detail = _json([str(python), "-c", detail_probe, json.dumps(terminal)])
        assert isinstance(detail, dict) and detail["authoritative"] is False
        assert detail["decision_id"] == terminal["decision_id"]
        assert detail["values"]["claim_boundary"] == terminal["claim_boundary"]

        external = temp / "external"
        _write_external_module(external)
        _run([uv, "pip", "install", "--python", str(python), str(external)])
        delegated_repo = temp / "delegated-parent"
        delegated_state = delegated_repo / ".agentic-workspace"
        delegated_state.mkdir(parents=True)
        delegated_planning_path = delegated_state / "planning.json"
        delegated_planning = {
            "schema_version": 1,
            "revision": 1,
            "active": {"id": "release-parent", "status": "in-progress"},
            "validation": [[str(python), "-c", "raise SystemExit(0)"]],
        }
        delegated_planning_path.write_text(json.dumps(delegated_planning), encoding="utf-8")
        delegate_intent = {"delegate": {"parent_id": "release-parent", "task": "review the release"}}
        delegated = _json(
            [
                str(cli),
                "start",
                "--target",
                str(delegated_repo),
                "--intent",
                json.dumps(delegate_intent),
            ]
        )
        assert isinstance(delegated, dict) and delegated["primary_action"]["operation_id"] == "delegate.run"

        delegated_planning["revision"] = 2
        delegated_planning_path.write_text(json.dumps(delegated_planning), encoding="utf-8")
        stale_child = subprocess.run(
            [
                str(cli),
                "invoke",
                "--target",
                str(delegated_repo),
                "--invocation",
                json.dumps(delegated["primary_action"]),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert stale_child.returncode == 2 and "source state changed" in stale_child.stdout
        fresh_child = _json(
            [
                str(cli),
                "start",
                "--target",
                str(delegated_repo),
                "--intent",
                json.dumps(delegate_intent),
            ]
        )
        assert isinstance(fresh_child, dict)
        assert fresh_child["input_revision"] != delegated["input_revision"]
        delegation_result = _json(
            [
                str(cli),
                "invoke",
                "--target",
                str(delegated_repo),
                "--invocation",
                json.dumps(fresh_child["primary_action"]),
            ]
        )
        assert isinstance(delegation_result, dict)
        assert delegation_result["value"]["worker"] == "external"
        assert delegation_result["value"]["parent_id"] == "release-parent"
        assert delegation_result["value"]["evidence"][0]["path"] == "delegated-review.txt"
        assert delegation_result["next_decision"]["primary_action"]["operation_id"] == "verification.run"
        delegation_retry = _json(
            [
                str(cli),
                "invoke",
                "--target",
                str(delegated_repo),
                "--invocation",
                json.dumps(fresh_child["primary_action"]),
            ]
        )
        assert delegation_retry == delegation_result
        evidence_path = delegated_state / "delegation-evidence.json"
        assert json.loads(evidence_path.read_text(encoding="utf-8"))["execution_count"] == 1

        parent_flow, parent_terminal = _follow_exact(cli, delegated_repo, delegation_result["next_decision"])
        assert [result["operation_id"] for result in parent_flow] == ["verification.run", "planning.complete"]
        assert parent_terminal["status"] == "terminal"
        assert "complete" in parent_terminal["claim_boundary"]["allowed"]
        state_paths = [path.relative_to(delegated_repo).as_posix().lower() for path in delegated_repo.rglob("*")]
        assert not any(
            removed in path
            for path in state_paths
            for removed in ("coordinator", "packet", "checkpoint", "carry", "continuation")
        )

        _run([uv, "pip", "uninstall", "--python", str(python), "agentic-workspace"])
        assert unknown.read_text(encoding="utf-8") == "preserve"
        assert not cli.exists()
        _run([uv, "pip", "install", "--python", str(python), str(wheel)])
        recovered = _json([str(cli), "start", "--target", str(temp / "recovered"), "--task", "resume"])
        assert isinstance(recovered, dict) and recovered["status"] == "direct"
        _run([uv, "pip", "uninstall", "--python", str(python), "agentic-workspace"])

        return {
            "artifact_boundary": "passed",
            "clean_install": "passed",
            "typescript_clean_install": "passed",
            "generated_two_language_parity": "passed",
            "direct_work": "passed",
            "maintainer_session_logging": "passed",
            "cli_python_parity": "passed",
            "legacy_removal": "passed",
            "proof_and_completion": "passed",
            "first_party_relevance_matrix": "passed",
            "partial_compliance_exact_flow": "passed",
            "operation_client_parity": "passed",
            "typed_read_mutation_currentness": "passed",
            "external_module_and_delegation": "passed",
            "delegated_parent_continuation": "passed",
            "terminal_view_boundary": "passed",
            "runtime_recovery": "passed",
            "uninstall_preservation": "passed",
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(json.dumps(run(args.root.resolve()), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
