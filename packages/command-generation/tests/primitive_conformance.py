from __future__ import annotations

import json
import tempfile
from pathlib import Path

from agentic_command_generation.primitive_executor import PrimitiveContext, PrimitiveExecutionError, execute_primitive, run_operation_steps


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
        target = root / "target"
        target.mkdir()
        context = PrimitiveContext(cwd=root, roots={"package": package_root})

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
