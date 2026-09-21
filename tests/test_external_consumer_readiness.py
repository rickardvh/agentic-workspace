from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

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
    private_generated_package = "_generated" + "_cli_package_impl"
    assert "import agentic_workspace as binding" in python
    assert "@agentic-workspace/workspace-cli" in typescript
    for source in (python, typescript):
        assert "sys.path" not in source
        assert "generated/workspace" not in source
        assert private_generated_package not in source
        assert "scripts/run_agentic_workspace" not in source
        assert "tests/fixtures" not in source


def test_workspace_has_no_reverse_dependency_on_external_consumers() -> None:
    assert _module()._reverse_dependency_violations() == []


def test_ci_runs_the_independent_consumer_proof() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "run_external_consumer_readiness.py --dist-dir dist --require-node" in workflow


@pytest.mark.parametrize("output_format", ["text", "json"])
def test_assertion_failure_identifies_the_failing_case(monkeypatch, capsys, output_format) -> None:
    module = _module()

    def failing_case(**kwargs):
        assert False

    monkeypatch.setattr(module, "run", failing_case)
    monkeypatch.setattr("sys.argv", [str(CHECKER), "--format", output_format])
    assert module.main() == 1
    output = capsys.readouterr().out
    message = json.loads(output)["message"] if output_format == "json" else output
    assert "failing_case (test_external_consumer_readiness.py:" in message
    assert "assert False" in message
