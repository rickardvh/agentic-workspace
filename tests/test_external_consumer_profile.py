from __future__ import annotations

import importlib.util
import json
from pathlib import Path

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
