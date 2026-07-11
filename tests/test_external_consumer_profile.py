from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
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
    assert module.PYTHON_CLIENT.read_text(encoding="utf-8") == module.render_python_client()
    assert module.TYPESCRIPT_CLIENT.read_text(encoding="utf-8") == module.render_typescript_client()
    bundle = module.render_bundle(profile)
    assert all(output.read_text(encoding="utf-8") == bundle for output in module.BUNDLE_OUTPUTS)
    bundle_payload = json.loads(bundle)
    assert bundle_payload["profile_fingerprint"] == profile["compatibility"]["fingerprint"]
    assert bundle_payload["operations"]
    assert all(item["contract"] for item in bundle_payload["operations"].values())
    referenced = {name for item in bundle_payload["operations"].values() for name in item["schemas"]}
    assert referenced.issubset(bundle_payload["schemas"])
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
        {"kind": "python", "generation_status": "mutation-capable-adapter"},
        {"kind": "typescript", "generation_status": "mutation-capable-adapter"},
    ]
    for schemas in ({"input": [], "output": ["result.schema.json"]}, {"input": ["input.schema.json"], "output": []}):
        command = {**base, "schemas": schemas}
        ir = {"packages": [{"id": "fixture", "operation_contract_root": "contracts", "targets": targets, "commands": [command]}]}
        assert module.build_profile(ir)["operations"][0]["external_consumption"]["status"] == "internal"


def test_typescript_packed_artifact_exports_profile() -> None:
    completed = subprocess.run(
        [shutil.which("npm") or shutil.which("npm.cmd") or "npm", "pack", "--dry-run", "--json"],
        cwd=ROOT / "generated/workspace/typescript",
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    files = {item["path"] for item in json.loads(completed.stdout)[0]["files"]}
    assert "external_consumer_profile.json" in files


def test_packed_typescript_artifact_resolves_profile_and_bundle(tmp_path: Path) -> None:
    npm = shutil.which("npm") or shutil.which("npm.cmd") or "npm"
    completed = subprocess.run(
        [npm, "pack", "--json", "--pack-destination", str(tmp_path)],
        cwd=ROOT / "generated/workspace/typescript",
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    archive = tmp_path / json.loads(completed.stdout)[0]["filename"]
    unpacked = tmp_path / "unpacked"
    shutil.unpack_archive(archive, unpacked, "gztar")
    client = unpacked / "package/src/client.mjs"
    script = f"import {{ externalConsumerProfile, externalContractBundle }} from {json.dumps(client.as_uri())}; console.log(JSON.stringify([externalConsumerProfile().schema_version, externalContractBundle().schema_version]));"
    result = subprocess.run(["node", "--input-type=module", "--eval", script], text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == [
        "agentic-workspace/external-consumer-profile/v1",
        "agentic-workspace/external-contract-bundle/v1",
    ]


def test_schema_resolution_is_provenance_safe_and_fragment_aware(tmp_path: Path) -> None:
    module = _module()
    schema = tmp_path / "src/owner/schemas/result.schema.json"
    schema.parent.mkdir(parents=True)
    schema.write_text("{}\n", encoding="utf-8")
    schema.write_text('{"$defs":{"value":{"type":"string"}}}\n', encoding="utf-8")
    assert module.resolve_schema_reference("owner/schemas/result.schema.json#/$defs/value", repo_root=tmp_path) == schema
    with pytest.raises(ValueError, match="missing schema fragment"):
        module.resolve_schema_reference("owner/schemas/result.schema.json#/$defs/missing", repo_root=tmp_path)
    duplicate = tmp_path / "packages/other/result.schema.json"
    duplicate.parent.mkdir(parents=True)
    duplicate.write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="ambiguous transitive schema reference"):
        module.resolve_schema_reference("result.schema.json", repo_root=tmp_path)
    with pytest.raises(ValueError, match="missing transitive schema"):
        module.resolve_schema_reference("missing.schema.json", repo_root=tmp_path)
