"""One selected declaration/hygiene journey; native admission owns semantics."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli

ROOT = Path(__file__).resolve().parents[1]


def test_memory_declaration_and_selected_hygiene(tmp_path, shared_core_binary, native_cli):
    reference = ".agentic-workspace/memory/repo/domains/lesson.md"
    note = tmp_path / reference
    note.parent.mkdir(parents=True)
    note.write_text("Preserve this useful lesson.")
    manifest = note.parent.parent / "manifest.toml"
    source = f'''version=1
[rules]
canonical_dirs=[".agentic-workspace/memory/repo/decisions"]
task_board_globs=["tasks/**"]
[notes."{reference}"]
routes_from=["tasks/**"]
summary="Read before selecting a durable owner"
[durable_facts."stable-id"]
note_ref="{reference}"
authority_class="advisory"
summary="A useful fact"
promotion_target="current source owner"
promotion_trigger="Repeated observation"
'''
    manifest.write_text(source)
    registry = tmp_path / ".agentic-workspace/memory/skills/REGISTRY.json"
    registry.parent.mkdir(parents=True)
    registry.write_bytes((ROOT / "packages/memory/bootstrap/.agentic-workspace/memory/skills/REGISTRY.json").read_bytes())
    context = {"target": str(tmp_path), "task": "Assess selected Memory"}

    def call(**extra):
        return consume("native", shared_core_binary, native_cli, {**context, **extra})

    assert not call()["memory"].get("hygiene")
    selected = call(changed=["tasks/one.md"])["memory"]
    assert selected["selected_notes"][0]["metadata"]["summary"] == "Read before selecting a durable owner"
    assert selected["diagnostics"][0]["review_context"]["promotion_trigger"] == "Repeated observation"
    helper = ROOT / "packages/memory/bootstrap/.agentic-workspace/memory/skills/memory-hygiene/prepare.py"

    def check(binary=native_cli):
        result = subprocess.run(
            [sys.executable, str(helper), "--native-cli", str(binary), "--target", str(tmp_path), "--task", context["task"]],
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout)["hygiene"]

    findings = check()
    assert {row["code"] for row in findings["findings"]} == {"outside-canonical-directories", "task-board-dependence"}
    manifest.write_text(
        source.replace('/decisions"]', '/domains"]').replace('task_board_globs=["tasks/**"]', 'task_board_globs=["backlog/**"]')
    )
    assert check()["findings"] == []
    assert check(tmp_path / "missing-native")["status"] == "unexecuted"
    manifest.write_text(source + "unknown_control=true\n")
    invalid = call(changed=["tasks/one.md"])["memory"]
    assert invalid["selected_notes"] == []
    assert "unsupported declaration" in str(invalid["diagnostics"])
    assert check()["status"] == "unexecuted"
    assert call()["memory"]["selected_notes"] == []
    assert not (tmp_path / ".agentic-workspace/local").exists()
