from __future__ import annotations

import json
import tempfile
from pathlib import Path

from command_generation.primitive_executor import PrimitiveContext, PrimitiveExecutionError, execute_primitive, run_operation_steps


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        package_root = root / "package"
        package_root.mkdir()
        (package_root / "alpha.txt").write_text("alpha", encoding="utf-8")
        (package_root / "nested").mkdir()
        (package_root / "nested" / "beta.txt").write_text("beta", encoding="utf-8")
        (package_root / "REGISTRY.json").write_text(
            json.dumps({"skills": [{"id": "review", "path": "review/SKILL.md"}]}),
            encoding="utf-8",
        )
        contracts_root = root / "contracts"
        contracts_root.mkdir()
        (package_root / "AGENTS.template.md").write_text("agent instructions", encoding="utf-8")
        (package_root / ".agentic-workspace" / "memory").mkdir(parents=True)
        (package_root / ".agentic-workspace" / "memory" / "VERSION.md").write_text("Version: 3\n", encoding="utf-8")
        (package_root / ".agentic-workspace" / "memory" / "UPGRADE-SOURCE.toml").write_text(
            'source_type = "git"\nsource_ref = "abc123"\n',
            encoding="utf-8",
        )
        (package_root / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True)
        (package_root / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text("[notes]\n", encoding="utf-8")
        (contracts_root / "payload.json").write_text(
            json.dumps(
                {
                    "schema_version": "agentic-workspace/payload-verification-policy/v1",
                    "package": "memory",
                    "bootstrap_version": 3,
                    "version_path": ".agentic-workspace/memory/VERSION.md",
                    "legacy_version_path": "memory/system/VERSION.md",
                    "manifest_path": ".agentic-workspace/memory/repo/manifest.toml",
                    "upgrade_source": {
                        "path": ".agentic-workspace/memory/UPGRADE-SOURCE.toml",
                        "legacy_path": "legacy/UPGRADE-SOURCE.toml",
                        "allowed_source_types": ["git"],
                        "required_fields": ["source_ref"],
                        "date_fields": {},
                        "integer_fields": [],
                    },
                    "payload_path_aliases": [{"source": "AGENTS.template.md", "target": "AGENTS.md"}],
                    "required_files": [
                        "AGENTS.md",
                        ".agentic-workspace/memory/VERSION.md",
                        ".agentic-workspace/memory/UPGRADE-SOURCE.toml",
                        ".agentic-workspace/memory/repo/manifest.toml",
                    ],
                    "compatibility_contract_files": ["AGENTS.md"],
                    "current_memory": {"prefix": ".agentic-workspace/memory/repo/current/", "required": [], "optional": []},
                    "forbidden_files": [],
                    "forbidden_prefixes": [],
                    "guidance_fragments": {},
                }
            ),
            encoding="utf-8",
        )
        target = root / "target"
        target.mkdir()
        context = PrimitiveContext(cwd=root, roots={"package": package_root, "contracts": contracts_root})

        target_root = execute_primitive(
            "path.target_root.resolve",
            values={"target": "target"},
            context=context,
        )
        assert target_root == str(target.resolve())

        registry_text = execute_primitive(
            "filesystem.read",
            values={},
            arguments={"root": "package", "path": "REGISTRY.json"},
            context=context,
        )
        assert '"skills"' in registry_text

        registry = execute_primitive(
            "json.parse",
            values={"registry_text": registry_text},
            context=context,
        )
        assert registry["skills"][0]["id"] == "review"

        files = execute_primitive(
            "filesystem.glob",
            values={},
            arguments={"root": "package", "pattern": "**/*.txt"},
            context=context,
        )
        assert files == [{"relative_path": "alpha.txt"}, {"relative_path": "nested/beta.txt"}]

        file_payload = execute_primitive(
            "payload.assemble",
            values={"target_root": target_root, "files": files},
            arguments={"fields": {"dry_run": True, "message": "Files", "actions_from": "files"}},
            context=context,
        )
        assert file_payload["actions"] == [{"kind": "file", "path": "alpha.txt"}, {"kind": "file", "path": "nested/beta.txt"}]

        skill_payload = execute_primitive(
            "payload.assemble",
            values={"registry": registry},
            arguments={"fields": {"dry_run": True, "message": "Skills", "actions_from": "registry.skills", "mode": "skills"}},
            context=context,
        )
        assert skill_payload["actions"] == [{"kind": "skill", "id": "review", "path": "review/SKILL.md"}]

        verify_payload = execute_primitive(
            "payload.verify",
            values={"target_root": target_root},
            arguments={"policy_root": "contracts", "policy_path": "payload.json", "payload_root": "package"},
            context=context,
        )
        assert verify_payload["dry_run"] is True
        assert verify_payload["bootstrap_version"] == 3
        assert {action["path"] for action in verify_payload["actions"] if action["kind"] == "current"} >= {
            "AGENTS.md",
            ".agentic-workspace/memory/VERSION.md",
        }

        status_payload = execute_primitive(
            "payload.status",
            values={"target_root": target_root},
            arguments={"policy_root": "contracts", "policy_path": "payload.json", "target_root_value": "target_root"},
            context=context,
        )
        assert status_payload["message"] == "Status report"
        assert status_payload["bootstrap_version"] == 3
        assert status_payload["active"]["status"] in {"missing", "present"}

        emitted_json = execute_primitive(
            "output.emit",
            values={"result": skill_payload, "format": "json"},
            context=context,
        )
        assert json.loads(emitted_json)["actions"][0]["id"] == "review"

        emitted_text = execute_primitive(
            "output.emit",
            values={"result": file_payload, "format": "text"},
            context=context,
        )
        assert "Files" in emitted_text
        assert "- nested/beta.txt" in emitted_text

        emitted_install_text = execute_primitive(
            "output.emit.install-result",
            values={"result": verify_payload, "format": "text"},
            context=context,
        )
        assert "Payload verification" in emitted_install_text
        assert ".agentic-workspace/memory/VERSION.md" in emitted_install_text

        emitted_planning_report_text = execute_primitive(
            "output.emit",
            values={
                "result": {
                    "kind": "planning-module-report/v1",
                    "profile": "tiny",
                    "target_root": str(root),
                    "module": "planning",
                    "health": "healthy",
                    "status": {
                        "active_todo_count": 1,
                        "queued_todo_count": 2,
                        "active_execplan_count": 3,
                        "roadmap_lane_count": 4,
                        "roadmap_candidate_count": 5,
                    },
                    "next_action": {"summary": "continue"},
                },
                "format": "text",
            },
            context=context,
        )
        assert "Command: planning" in emitted_planning_report_text
        assert (
            "Status: 1 active TODO / 2 queued TODO / 3 active execplans / 4 roadmap lanes / 5 roadmap candidates"
            in emitted_planning_report_text
        )

        operation = {
            "ir_plan": {
                "steps": [
                    {
                        "id": "read_registry",
                        "uses": "filesystem.read",
                        "arguments": {"root": "package", "path": "REGISTRY.json"},
                        "outputs": ["registry_text"],
                    },
                    {"id": "parse_registry", "uses": "json.parse", "outputs": ["registry"]},
                    {
                        "id": "assemble",
                        "uses": "payload.assemble",
                        "arguments": {"fields": {"dry_run": True, "message": "Skills", "actions_from": "registry.skills"}},
                        "outputs": ["result"],
                    },
                    {"id": "emit", "uses": "output.emit", "outputs": ["emitted"]},
                ]
            }
        }
        values = run_operation_steps(operation, initial_values={"format": "json"}, context=context)
        assert json.loads(values["emitted"])["actions"][0]["id"] == "review"

        guarded_operation = {
            "ir_plan": {
                "steps": [
                    {
                        "id": "skip_text",
                        "uses": "filesystem.exists",
                        "when": {"value": "format", "equals": "text"},
                        "arguments": {"root": "package", "path": "alpha.txt"},
                        "outputs": ["skipped"],
                    },
                    {
                        "id": "use_json",
                        "uses": "filesystem.exists",
                        "when": {
                            "all": [
                                {"value": "format", "equals": "json"},
                                {"not": {"value": "missing", "present": True}},
                            ]
                        },
                        "arguments": {"root": "package", "path": "alpha.txt"},
                        "outputs": ["selected"],
                    },
                ]
            }
        }
        guarded_values = run_operation_steps(guarded_operation, initial_values={"format": "json"}, context=context)
        assert "skipped" not in guarded_values
        assert guarded_values["selected"] is True

        try:
            run_operation_steps(
                {
                    "ir_plan": {
                        "steps": [
                            {
                                "id": "mixed_guard",
                                "uses": "payload.assemble",
                                "when": {"value": "format", "equals": "json", "present": True},
                            }
                        ]
                    }
                },
                initial_values={"format": "json"},
                context=context,
            )
        except PrimitiveExecutionError as exc:
            assert "exactly one" in str(exc)
        else:
            raise AssertionError("step when accepted mixed condition operators")

        try:
            execute_primitive(
                "filesystem.read",
                values={},
                arguments={"root": "package", "path": "../escape.txt"},
                context=context,
            )
        except PrimitiveExecutionError:
            pass
        else:
            raise AssertionError("filesystem.read accepted a path escape")

    print("[ok] command-generation primitive conformance")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
