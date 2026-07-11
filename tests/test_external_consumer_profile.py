from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
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
    profile = json.loads(expected)
    assert profile["authority"] == "command_package_ir.json"
    assert profile["compatibility"]["fingerprint"].startswith("sha256:")
    assert profile["operations"]
    assert all(entry["operation_compatibility"]["fingerprint"].startswith("sha256:") for entry in profile["operations"])
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


def test_present_but_deferred_targets_fail_closed() -> None:
    module = _module()
    ir = {
        "packages": [
            {
                "id": "fixture",
                "operation_contract_root": "contracts",
                "targets": [
                    {"kind": "python", "generation_status": "deferred"},
                    {"kind": "typescript", "generation_status": "deferred"},
                ],
                "commands": [
                    {
                        "status": "generated",
                        "operation_ref": {"id": "fixture.read", "path": "read.json"},
                        "effect_hints": {"read_only": True},
                        "conformance_refs": ["fixture.read.process"],
                        "schemas": {"input": ["input.schema.json"], "output": ["result.schema.json"]},
                    }
                ],
            }
        ]
    }
    assert module.build_profile(ir)["operations"][0]["external_consumption"]["status"] == "internal"


def test_single_usable_target_is_target_specific() -> None:
    module = _module()
    ir = {
        "packages": [
            {
                "id": "fixture",
                "operation_contract_root": "contracts",
                "targets": [
                    {"kind": "python", "generation_status": "mutation-capable-adapter", "maturity_level_ref": "mutation-capable-adapter"},
                    {"kind": "typescript", "generation_status": "deferred"},
                ],
                "commands": [
                    {
                        "status": "generated",
                        "operation_ref": {"id": "fixture.read", "path": "read.json"},
                        "effect_hints": {"read_only": True},
                        "conformance_refs": ["fixture.read.process"],
                        "schemas": {"input": ["input.schema.json"], "output": ["result.schema.json"]},
                    }
                ],
            }
        ]
    }
    assert module.build_profile(ir)["operations"][0]["external_consumption"]["status"] == "target-specific"


def test_runtime_exception_provenance_is_structured() -> None:
    profile = json.loads(_module().render())
    runtime_backed = next(entry for entry in profile["operations"] if entry["external_consumption"]["status"] == "runtime-backed")
    exception = runtime_backed["external_consumption"]["runtime_exceptions"][0]
    assert {"owner", "scope", "reason", "proof", "migration_dependency"}.issubset(exception)


def test_empty_input_or_result_schema_fails_closed() -> None:
    module = _module()
    base = {
        "status": "generated",
        "operation_ref": {"id": "fixture.read", "path": "read.json"},
        "effect_hints": {"read_only": True},
        "conformance_refs": ["fixture.read.process"],
    }
    targets = [
        {"kind": "python", "generation_status": "mutation-capable-adapter", "maturity_level_ref": "mutation-capable-adapter"},
        {"kind": "typescript", "generation_status": "mutation-capable-adapter", "maturity_level_ref": "mutation-capable-adapter"},
    ]
    for schemas in ({"input": [], "output": ["result.schema.json"]}, {"input": ["input.schema.json"], "output": []}):
        command = {**base, "schemas": schemas}
        ir = {"packages": [{"id": "fixture", "operation_contract_root": "contracts", "targets": targets, "commands": [command]}]}
        assert module.build_profile(ir)["operations"][0]["external_consumption"]["status"] == "internal"


def test_typescript_packed_artifact_exports_profile() -> None:
    with tempfile.TemporaryDirectory() as directory:
        completed = subprocess.run(
            [shutil.which("npm") or shutil.which("npm.cmd") or "npm", "pack", "--json", "--pack-destination", directory],
            cwd=ROOT / "generated/workspace/typescript",
            text=True,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        archive = Path(directory) / json.loads(completed.stdout)[0]["filename"]
        with tarfile.open(archive) as packed:
            packed.extractall(directory, filter="data")
        script = "import profile from './package/external_consumer_profile.json' with {type:'json'}; console.log(profile.schema_version)"
        loaded = subprocess.run(
            [shutil.which("node") or "node", "--input-type=module", "-e", script], cwd=directory, text=True, capture_output=True
        )
        assert loaded.returncode == 0, loaded.stderr
        assert loaded.stdout.strip() == "agentic-workspace/external-consumer-profile/v1"


def test_built_wheel_resolves_profile_outside_checkout(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    subprocess.run(
        [shutil.which("uv") or "uv", "build", "--wheel", "--out-dir", str(dist)], cwd=ROOT, check=True, capture_output=True, text=True
    )
    site = tmp_path / "site"
    with zipfile.ZipFile(next(dist.glob("*.whl"))) as wheel:
        wheel.extractall(site)
    code = "from importlib.resources import files; import json; print(json.loads(files('agentic_workspace._generated_cli_package_impl').joinpath('external_consumer_profile.json').read_text())['schema_version'])"
    loaded = subprocess.run(
        [sys.executable, "-I", "-c", f"import sys; sys.path.insert(0, {str(site)!r}); {code}"], cwd=tmp_path, text=True, capture_output=True
    )
    assert loaded.returncode == 0, loaded.stderr
    assert loaded.stdout.strip() == "agentic-workspace/external-consumer-profile/v1"


def test_usable_generation_with_unusable_maturity_fails_closed() -> None:
    module = _module()
    base = {"kind": "python", "package_name": "fixture", "generation_status": "mutation-capable-adapter"}
    for maturity in (None, "experimental", "parser-help-proof", "deferred"):
        target = {**base, "maturity_level_ref": maturity}
        ir = {
            "packages": [
                {
                    "id": "fixture",
                    "operation_contract_root": "contracts",
                    "targets": [target],
                    "commands": [
                        {
                            "status": "generated",
                            "operation_ref": {"id": "fixture.read", "path": "read.json"},
                            "effect_hints": {"read_only": True},
                            "conformance_refs": ["fixture.read.process"],
                            "schemas": {"input": ["input.schema.json"], "output": ["result.schema.json"]},
                        }
                    ],
                }
            ]
        }
        assert module.build_profile(ir)["operations"][0]["external_consumption"]["status"] == "internal"
