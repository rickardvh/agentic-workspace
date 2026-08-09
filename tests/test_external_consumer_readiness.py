from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts/check/run_external_consumer_readiness.py"
FIXTURES = ROOT / "tests/fixtures/external_consumer"


def _module():
    spec = importlib.util.spec_from_file_location("external_consumer_readiness", CHECKER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_consumers_use_only_public_package_entrypoints() -> None:
    python = (FIXTURES / "consumer.py").read_text(encoding="utf-8")
    typescript = (FIXTURES / "consumer.mjs").read_text(encoding="utf-8")
    assert "from agentic_workspace import" in python
    assert "@agentic-workspace/workspace-cli" in typescript
    for source in (python, typescript):
        assert "sys.path" not in source
        assert "generated/workspace" not in source
        assert "scripts/run_agentic_workspace" not in source
        assert "tests/fixtures" not in source


def test_semantic_projection_normalizes_only_environment_roots(tmp_path: Path) -> None:
    module = _module()
    left = tmp_path / "necessary"
    right = tmp_path / "full-mirror"
    left_payload = {"target": left.as_posix(), "nested": [f"{left.as_posix()}/.agentic-workspace", "stable"]}
    right_payload = {"target": right.as_posix(), "nested": [f"{right.as_posix()}/.agentic-workspace", "stable"]}
    assert module._semantic_projection(left_payload, [left]) == module._semantic_projection(right_payload, [right])


def test_workspace_has_no_reverse_dependency_on_external_consumers() -> None:
    assert _module()._reverse_dependency_violations() == []


def test_ci_runs_the_independent_consumer_proof() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "run_external_consumer_readiness.py --dist-dir dist --require-node" in workflow
