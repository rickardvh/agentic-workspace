"""Former route intent requires explicit task-current adoption, with no writes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = Path(".agentic-workspace/local/current-task-routes.json")
REGISTRY = Path("tools/skills/REGISTRY.json")


@pytest.mark.parametrize("surface", ["native", "python", "typescript", "json"])
def test_declared_custom_registry_is_shared_and_unrelated_state_is_ignored(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    registry = tmp_path / REGISTRY
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({"registry_sources": ["custom/routes.json"]}))
    custom = tmp_path / "custom/routes.json"
    custom.parent.mkdir()
    custom.write_text(json.dumps({"skills": [{"semantic_routes": ["custom/first"]}]}))
    context = {"target": str(tmp_path), "task": "Inspect custom routes"}
    first = consume(surface, shared_core_binary, native_cli, context)
    unrelated = tmp_path / ".agentic-workspace/local/scratch/nested/skills/REGISTRY.json"
    unrelated.parent.mkdir(parents=True)
    unrelated.write_text("not a registry source")
    unchanged = consume(surface, shared_core_binary, native_cli, context)
    assert unchanged["semantic_routes"] == first["semantic_routes"]
    custom.write_text(json.dumps({"skills": [{"semantic_routes": ["custom/second"]}]}))
    changed = consume(surface, shared_core_binary, native_cli, context)
    assert (
        changed["decision_packet"]["semantic_task_routes"]["source_revision"]
        != first["decision_packet"]["semantic_task_routes"]["source_revision"]
    )
    custom.unlink()
    with pytest.raises(AssertionError, match="required route registry unavailable"):
        consume(surface, shared_core_binary, native_cli, context)


def fixture(root: Path) -> tuple[dict, bytes]:
    text = (ROOT / REGISTRY).read_text(encoding="utf-8")
    registry = root / REGISTRY
    registry.parent.mkdir(parents=True)
    registry.write_text(text, encoding="utf-8")
    declared = json.loads(text)
    route = next(
        route if isinstance(route, str) else route["id"] for skill in declared["skills"] for route in skill.get("semantic_routes", [])
    )

    def digest(value: str) -> str:
        return "sha256:" + hashlib.sha256(value.encode()).hexdigest()

    source = digest(f"{REGISTRY.as_posix()}\0{digest(text)}")
    fact = {
        "kind": "agentic-workspace/semantic-task-route-fact/v1",
        "posture": "selected",
        "routes": [route],
        "task_identity": {"kind": "current-work", "id": "former-branch-planning-context"},
        "current_work_id": "former-branch-planning-context",
        "source_revision": source,
        "provenance": "agent-selected",
        "authority_effect": "applicability-only",
    }
    path = root / REFERENCE
    path.parent.mkdir(parents=True)
    raw = (json.dumps(fact, indent=2) + "\n").encode()
    path.write_bytes(raw)
    return fact, raw


@pytest.mark.parametrize("surface", ["native", "python", "typescript", "json"])
def test_former_selection_requires_exact_current_agent_request(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    fact, raw = fixture(tmp_path)
    context = {"target": str(tmp_path), "task": "Inspect the current route contract", "changed": ["docs/routes.md"]}
    first = consume(surface, shared_core_binary, native_cli, context)
    candidate = first["semantic_routes"]["former_selection"]
    assert candidate["status"] == "candidate"
    assert candidate["current_task_relation"] == "unproven"
    assert candidate["routes"] == fact["routes"]
    assert first["decision_packet"]["semantic_task_routes"]["posture"] == "unresolved"
    assert len(json.dumps(first)) < 100_000
    assert len(json.dumps(candidate)) < 8_000
    request = candidate["selection_request"]
    assert request["task_identity"] != fact["task_identity"]
    selected = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    assert selected["decision_packet"]["semantic_task_routes"]["status"] == "current"
    assert selected["decision_packet"]["semantic_task_routes"]["routes"] == fact["routes"]
    assert (tmp_path / REFERENCE).read_bytes() == raw
    unrelated = consume(surface, shared_core_binary, native_cli, {**context, "task": "An unrelated direct task"})
    assert unrelated["decision_packet"]["semantic_task_routes"]["posture"] == "unresolved"
    stale_task = consume(surface, shared_core_binary, native_cli, {**context, "task": "An unrelated direct task", "request": request})
    assert stale_task["decision_packet"]["semantic_task_routes"]["status"] == "stale"
    # A changed former record cannot keep an earlier current-task adoption valid.
    (tmp_path / REFERENCE).write_bytes(raw + b" ")
    stale_source = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    assert stale_source["decision_packet"]["semantic_task_routes"]["status"] == "stale"
    assert (tmp_path / REFERENCE).read_bytes() == raw + b" "
    (tmp_path / REGISTRY).write_text((tmp_path / REGISTRY).read_text() + " ", encoding="utf-8")
    changed_catalogue = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    assert changed_catalogue["semantic_routes"]["former_selection"]["status"] == "stale"
    assert changed_catalogue["decision_packet"]["semantic_task_routes"]["status"] == "stale"


@pytest.mark.parametrize("surface", ["native", "python", "typescript", "json"])
@pytest.mark.parametrize("failure", ["stale", "invalid", "oversized"])
def test_unadoptable_former_source_is_preserved_and_explicit(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str, failure: str
) -> None:
    fact, raw = fixture(tmp_path)
    if failure == "stale":
        fact["source_revision"] = "old-vocabulary"
    elif failure == "invalid":
        fact["authority_effect"] = "grant-authority"
    else:
        fact["routes"] = fact["routes"] * 17
    raw = json.dumps(fact).encode()
    (tmp_path / REFERENCE).write_bytes(raw)
    result = consume(surface, shared_core_binary, native_cli, {"target": str(tmp_path), "task": "Read an unrelated document"})
    diagnostic = result["semantic_routes"]["former_selection"]
    assert diagnostic["status"] == ("stale" if failure == "stale" else "unresolved")
    assert (
        diagnostic["reason"]
        == {
            "stale": "former-route-vocabulary-revision-changed",
            "invalid": "former-route-source-invalid-or-unsupported",
            "oversized": "former-route-selection-exceeds-candidate-bound",
        }[failure]
    )
    assert "selection_request" not in diagnostic
    assert result["decision_packet"]["semantic_task_routes"]["posture"] == "unresolved"
    assert result["decision_packet"]["status"] == "direct"
    assert (tmp_path / REFERENCE).read_bytes() == raw


@pytest.mark.parametrize("surface", ["native", "python", "typescript", "json"])
def test_no_former_source_direct_work_has_no_candidate_or_state(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    result = consume(surface, shared_core_binary, native_cli, {"target": str(tmp_path), "task": "Read the short document"})
    assert "former_selection" not in (result["semantic_routes"] or {})
    assert result["decision_packet"]["status"] == "direct"
    assert not (tmp_path / ".agentic-workspace").exists()


@pytest.mark.parametrize("surface", ["native", "python", "typescript", "json"])
def test_new_unreadable_former_source_stales_an_earlier_selection(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    fixture(tmp_path)
    (tmp_path / REFERENCE).unlink()
    context = {"target": str(tmp_path), "task": "Inspect the current route contract"}
    initial = consume(surface, shared_core_binary, native_cli, context)
    request = next(r for r in initial["semantic_routes"]["requests"] if r["request_kind"] == "semantic-routes/select/v1")
    request["arguments"] = {"posture": "none", "routes": []}
    (tmp_path / REFERENCE).mkdir()
    result = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    assert result["semantic_routes"]["former_selection"]["reason"] == "former-route-source-unreadable-or-linked"
    assert result["decision_packet"]["semantic_task_routes"]["status"] == "stale"
    assert (tmp_path / REFERENCE).is_dir()
