"""Planning procedures join the explicit closure without acquiring owner authority."""

import json
import shutil
from pathlib import Path

from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli

ROOT = Path(__file__).resolve().parents[1]
PLANNING = ".agentic-workspace/planning/skills"


def test_planning_registry_closure_and_selected_assignment_method(tmp_path, shared_core_binary, native_cli):
    registry = tmp_path / ".agentic-workspace/skills/REGISTRY.json"
    registry.parent.mkdir(parents=True)
    registry.write_bytes((ROOT / registry.relative_to(tmp_path)).read_bytes())
    context = {"target": str(tmp_path), "task": "Assess assignment for a bounded implementation"}

    def call(request=None):
        return consume("native", shared_core_binary, native_cli, context | ({"request": request} if request else {}))

    absent = call()
    assert "planning" not in {row["id"] for row in absent["semantic_routes"]["discovery"]["children"]}
    shutil.copytree(ROOT / PLANNING, tmp_path / PLANNING)
    local = tmp_path / ".agentic-workspace/config.local.toml"
    local.write_text(
        '[delegation]\nassignment_policy="required-best-fit"\ncurrent_target="local"\n[delegation_targets.local]\ntransports=[{kind="internal"}]\n',
        encoding="utf-8",
    )
    initial = call()
    assert "planning" in {row["id"] for row in initial["semantic_routes"]["discovery"]["children"]}
    declarations = json.loads((tmp_path / PLANNING / "REGISTRY.json").read_text(encoding="utf-8"))
    expected = {
        route if isinstance(route, str) else route["id"] for skill in declarations["skills"] for route in skill.get("semantic_routes", [])
    }
    for route in expected:
        request = initial["semantic_routes"]["requests"][0]
        request["arguments"] = {"parent": route}
        selected = call(request)
        assert selected["semantic_routes"]["discovery"]["detail"]["id"] == route
    request["arguments"] = {"parent": "planning/assignment/lifecycle"}
    selected = call(request)
    detail = selected["semantic_routes"]["discovery"]["detail"]
    assert len(detail["sources"]) == 1
    source = detail["sources"][0]
    assert source["skill_id"] == "planning-assignment"
    assert source["source_ref"] == f"{PLANNING}/REGISTRY.json"
    assert source["procedure"]["status"] == "available"
    assert selected["task_requirements"]["implementation_admission"] == initial["task_requirements"]["implementation_admission"]
    assert selected["task_requirements"]["assignment"]["result"]["selected"] is None
    procedure = selected["procedure"]["requests"][0]
    current = call(procedure)
    answer = current["procedure"]["requests"][0]
    answer["arguments"]["answer"] = {"disposition": "answered", "branches": ["assessment"], "material": {}}
    answered = call(answer)
    assert answered["procedure"]["status"] == "current"
    request["arguments"]["resource"] = answered["procedure"]["next"][0]
    assessment = call(request)["semantic_routes"]["discovery"]["detail"]
    text = assessment["sources"][0]["procedure"]["resource"]["selected"]["text"]
    assert "Only the owner" in text or "only the owner" in text
    assert "Follow current role" not in text
    unrelated = tmp_path / PLANNING / "planning-assignment/unrelated.md"
    unrelated.write_text("Unselected material", encoding="utf-8")
    assert call(request)["semantic_routes"]["discovery"]["detail"] == assessment
    reference = tmp_path / PLANNING / "planning-assignment/references/assessment.md"
    reference.write_text(reference.read_text(encoding="utf-8") + "\nChanged selected material.\n", encoding="utf-8")
    assert call(request)["semantic_routes"]["discovery"]["detail"] != assessment
    (tmp_path / PLANNING / "REGISTRY.json").write_text("{}", encoding="utf-8")
    assert call()["semantic_routes"]["discovery"] != initial["semantic_routes"]["discovery"]
