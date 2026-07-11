from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/generate/generate_external_consumer_profile.py"


def _module():
    spec = importlib.util.spec_from_file_location("external_profile_generator", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_profile_is_fresh_and_fail_closed() -> None:
    module = _module()
    expected = module.render()
    for output in module.OUTPUTS:
        assert output.read_text(encoding="utf-8") == expected
    assert module.PYTHON_CLIENT.read_text(encoding="utf-8") == module.render_python_client()
    assert module.TYPESCRIPT_CLIENT.read_text(encoding="utf-8") == module.render_typescript_client()
    profile = json.loads(expected)
    assert profile["authority"] == "command_package_ir.json"
    assert profile["compatibility"]["fingerprint"].startswith("sha256:")
    assert profile["operations"]
    assert all(entry["external_consumption"]["status"] in {"supported", "runtime-backed", "internal"} for entry in profile["operations"])


def test_incomplete_operation_is_not_advertised_as_supported() -> None:
    module = _module()
    ir = {
        "packages": [
            {
                "id": "fixture",
                "operation_contract_root": "contracts",
                "targets": [{"kind": "python", "package_name": "fixture", "generation_status": "generated"}],
                "commands": [{"status": "generated", "operation_ref": {"id": "fixture.read", "path": "read.json"}}],
            }
        ]
    }
    entry = module.build_profile(ir)["operations"][0]
    assert entry["external_consumption"]["status"] == "internal"


def test_child_without_explicit_operation_does_not_duplicate_parent() -> None:
    module = _module()
    ir = {
        "packages": [
            {
                "id": "fixture",
                "operation_contract_root": "contracts",
                "targets": [],
                "commands": [
                    {
                        "status": "generated",
                        "operation_ref": {"id": "fixture.root", "path": "root.json"},
                        "interface": {"subcommands": [{"name": "child"}]},
                    }
                ],
            }
        ]
    }
    assert [entry["id"] for entry in module.build_profile(ir)["operations"]] == ["fixture.root"]


def test_conflicting_explicit_operation_ids_fail_closed() -> None:
    module = _module()
    first = {"status": "generated", "operation_ref": {"id": "fixture.read", "path": "read.json"}}
    second = {"status": "generated", "operation_ref": {"id": "fixture.read", "path": "other.json"}}
    ir = {"packages": [{"id": "fixture", "operation_contract_root": "contracts", "targets": [], "commands": [first, second]}]}
    with pytest.raises(ValueError, match="conflicting explicit operation id"):
        module.build_profile(ir)
