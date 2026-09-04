from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Any


def _run(argv: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=True)


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

import json
from pathlib import Path

from agentic_workspace.modules import Module
from agentic_workspace.operations import Operation


def _path(context):
    return Path(str(context["target"])) / ".delegate-result.json"


def _contribute(context):
    request = context.get("delegate")
    if not isinstance(request, dict):
        return None
    path = _path(context)
    if path.is_file():
        return {"revision": path.read_text(encoding="utf-8"), "terminal": True}
    return {
        "revision": "absent",
        "actions": [{
            "operation_id": "delegate.run",
            "arguments": {"target": str(Path(str(context["target"])).resolve()), "task": str(request["task"])},
            "effects": ["delegation-state"],
            "priority": 75,
        }],
        "claims": {"blocked": ["complete"]},
    }


def _run(arguments):
    path = Path(arguments["target"]) / ".delegate-result.json"
    value = {"agent": "external", "task": arguments["task"], "status": "complete"}
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
    return {"status": "applied", "effects": ["delegation-state"], "value": value}


def module():
    return Module(
        name="delegate",
        contribute=_contribute,
        operations=(Operation(
            "delegate.run",
            {
                "type": "object",
                "properties": {"target": {"type": "string"}, "task": {"type": "string", "minLength": 1}},
                "required": ["target", "task"],
                "additionalProperties": False,
            },
            ("delegation-state",),
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
    with tempfile.TemporaryDirectory(prefix="agentic-workspace-v1-") as raw_temp:
        temp = Path(raw_temp)
        dist = temp / "dist"
        _run([uv, "build", "--wheel", "--sdist", "--out-dir", str(dist)], cwd=root)
        wheel = next(dist.glob("*.whl"))
        sdist = next(dist.glob("*.tar.gz"))
        _assert_artifacts(wheel, sdist)

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
        direct = _json([str(cli), "start", "--target", str(repository), "--task", "edit one file"])
        assert isinstance(direct, dict) and direct["status"] == "direct"
        assert not (repository / ".agentic-workspace").exists()

        probe = (
            "import json,sys; from agentic_workspace.workspace import Workspace; "
            "print(json.dumps(Workspace(sys.argv[1]).start(task='edit one file'), sort_keys=True))"
        )
        python_decision = _json([str(python), "-c", probe, str(repository)])
        assert python_decision == direct

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
        delegated = _json(
            [
                str(cli),
                "start",
                "--target",
                str(repository),
                "--intent",
                json.dumps({"delegate": {"task": "external review"}}),
            ]
        )
        assert isinstance(delegated, dict) and delegated["primary_action"]["operation_id"] == "delegate.run"
        delegation_result = _json(
            [
                str(cli),
                "invoke",
                "--target",
                str(repository),
                "--invocation",
                json.dumps(delegated["primary_action"]),
            ]
        )
        assert isinstance(delegation_result, dict) and delegation_result["next_decision"]["status"] == "terminal"
        assert delegation_result["value"]["agent"] == "external"
        delegation_retry = _json(
            [
                str(cli),
                "invoke",
                "--target",
                str(repository),
                "--invocation",
                json.dumps(delegated["primary_action"]),
            ]
        )
        assert delegation_retry == delegation_result

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
            "direct_work": "passed",
            "cli_python_parity": "passed",
            "legacy_removal": "passed",
            "proof_and_completion": "passed",
            "first_party_relevance_matrix": "passed",
            "partial_compliance_exact_flow": "passed",
            "operation_client_parity": "passed",
            "typed_read_mutation_currentness": "passed",
            "external_module_and_delegation": "passed",
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
