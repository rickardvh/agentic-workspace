"""One selected declaration/hygiene journey; native admission owns semantics."""

from __future__ import annotations

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
    registry.write_bytes((ROOT / ".agentic-workspace/memory/skills/REGISTRY.json").read_bytes())
    context = {"target": str(tmp_path), "task": "Assess selected Memory"}

    def call(**extra):
        return consume("native", shared_core_binary, native_cli, {**context, **extra})

    assert not call()["memory"].get("hygiene")
    selected = call(changed=["tasks/one.md"])["memory"]
    assert selected["selected_notes"][0]["metadata"]["summary"] == "Read before selecting a durable owner"
    assert selected["diagnostics"][0]["review_context"]["promotion_trigger"] == "Repeated observation"

    def check():
        request = next(r for r in call()["semantic_routes"]["requests"] if r["request_kind"] == "semantic-routes/select/v1")
        request["arguments"] = {"posture": "selected", "routes": ["memory/hygiene"]}
        return call(request=request)["memory"].get("hygiene")

    findings = check()
    assert {row["code"] for row in findings["findings"]} == {"outside-canonical-directories", "task-board-dependence"}
    manifest.write_text(
        source.replace('/decisions"]', '/domains"]').replace('task_board_globs=["tasks/**"]', 'task_board_globs=["backlog/**"]')
    )
    assert check()["findings"] == []
    manifest.write_text(source + "unknown_control=true\n")
    invalid = call(changed=["tasks/one.md"])["memory"]
    assert invalid["selected_notes"] == []
    assert "unsupported declaration" in str(invalid["diagnostics"])
    assert not check() or check()["status"] != "checked"
    assert call()["memory"]["selected_notes"] == []
    assert not (tmp_path / ".agentic-workspace/local").exists()


def test_selected_advice_is_delivered_and_large_detail_is_procedure_carried(tmp_path, shared_core_binary, native_cli):
    from tests.test_native_proof_procedure import install, procedure

    install(tmp_path)
    reference = ".agentic-workspace/memory/repo/domains/lesson.md"
    note = tmp_path / reference
    note.parent.mkdir(parents=True)
    lesson = "After publication, inspect committed effect truth before considering a retry."
    note.write_text(lesson)
    manifest = note.parent.parent / "manifest.toml"
    text = f'version=1\n[notes."{reference}"]\nroutes_from=["src/**"]\nsemantic_routes=["sample/recovery"]\nsummary="Preserve a committed publication after continuation loss."\n'
    manifest.write_text(text)
    context = {"target": str(tmp_path), "task": "Repair interrupted publication", "changed": ["src/publish.rs"]}

    def call(**kw):
        return consume("json", shared_core_binary, native_cli, context | kw)

    compact = call(projection="compact")
    assert compact["advisory_context"][0]["body"] == lesson
    assert compact["advisory_context"][0]["authority_effect"] == "advisory-only"
    assert not compact["advisory_context"][0]["delivery_is_disposition"]
    full = call()
    assert compact["decision_packet"]["blockers"] == full["decision_packet"]["blockers"]
    assert not full["memory"]["selected_notes"][0].get("disposition")
    quiet = call(changed=["docs/help.md"], projection="compact")
    for index in range(100):
        # Unrelated note bodies are never needed, even if unavailable or huge.
        with manifest.open("a") as stream:
            stream.write(f'[notes.".agentic-workspace/memory/repo/domains/other-{index}.md"]\nroutes_from=["other/**"]\n')
    assert call(changed=["docs/help.md"], projection="compact") == quiet
    assert call(projection="compact")["advisory_context"] == compact["advisory_context"]
    note.write_text(lesson + "\n" + "Large supporting detail. " * 300)
    large = call(projection="compact")
    assert "body" not in large["advisory_context"][0]
    assert "summary" in large["advisory_context"][0]
    prepared = procedure(shared_core_binary, context, "prepare")
    assert prepared["operating"]["advisory_context"][0]["body"] == note.read_bytes().decode()
    manifest.write_text(text + 'stale_when=["src/**"]\n')
    stale = call(projection="compact")["advisory_context"][0]
    assert stale["status"] == "reconciliation-required" and "body" not in stale
    manifest.write_text(text)
    note.unlink()
    assert call(projection="compact")["advisory_context"][0]["status"] == "reconciliation-required"
