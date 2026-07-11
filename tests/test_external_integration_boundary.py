from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from agentic_workspace import cli

ROOT = Path(__file__).resolve().parents[1]


def test_necessary_surface_payload_has_no_adapter_lifecycle() -> None:
    payload = json.loads((ROOT / "src/agentic_workspace/contracts/workspace_defaults/payload.json").read_text(encoding="utf-8"))
    encoded = json.dumps(payload).lower()
    forbidden_paths = (
        ".agentic-workspace/adapters/",
        ".agentic-workspace/plugins/",
        ".agentic-workspace/adapter.lock",
        ".agentic-workspace/plugin.lock",
    )
    assert all(path not in encoded for path in forbidden_paths)


def test_external_profile_is_package_owned_not_installed_payload() -> None:
    payload = json.loads((ROOT / "src/agentic_workspace/contracts/workspace_defaults/payload.json").read_text(encoding="utf-8"))
    encoded = json.dumps(payload)
    assert "external_consumer_profile.json" not in encoded
    assert (ROOT / "generated/workspace/python/external_consumer_profile.json").is_file()
    assert (ROOT / "generated/workspace/typescript/external_consumer_profile.json").is_file()


def test_local_integration_area_is_explicitly_non_authoritative() -> None:
    text = (ROOT / ".agentic-workspace/docs/local-integration-area.md").read_text(encoding="utf-8")
    for phrase in ("git-ignored", "non-authoritative", "safe to delete", "external tool's own storage"):
        assert phrase in text


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "--quiet", str(path)], check=True)


def _tree(path: Path) -> set[str]:
    return {item.relative_to(path).as_posix() for item in path.rglob("*") if item.is_file()}


def _assert_no_adapter_managed_residue(path: Path) -> None:
    forbidden = {"adapters", "plugins", "adapter.lock", "plugin.lock"}
    assert not any(part.lower() in forbidden for item in path.rglob("*") for part in item.relative_to(path).parts)


def test_lifecycle_profiles_preserve_zero_adapter_footprint_and_equivalent_consumption(tmp_path: Path, capsys) -> None:
    necessary = tmp_path / "necessary"
    mirrored = tmp_path / "mirrored"
    necessary.mkdir()
    mirrored.mkdir()
    _init_repo(necessary)
    _init_repo(mirrored)

    assert cli.main(["install", "--target", str(necessary), "--modules", "planning,memory", "--format", "json"]) == 0
    capsys.readouterr()
    assert cli.main(["install", "--target", str(mirrored), "--modules", "planning,memory", "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()
    _assert_no_adapter_managed_residue(necessary)
    _assert_no_adapter_managed_residue(mirrored)
    assert "external_consumer_profile.json" not in "\n".join(_tree(necessary))

    profile = json.loads((ROOT / "generated/workspace/python/external_consumer_profile.json").read_text(encoding="utf-8"))
    assert profile["compatibility"]["fingerprint"]
    assert cli.main(["status", "--target", str(necessary), "--format", "json"]) == 0
    necessary_status = json.loads(capsys.readouterr().out)
    assert cli.main(["status", "--target", str(mirrored), "--format", "json"]) == 0
    mirrored_status = json.loads(capsys.readouterr().out)
    assert necessary_status["health"] == mirrored_status["health"] == "healthy"

    assert cli.main(["upgrade", "--target", str(necessary), "--modules", "planning,memory", "--format", "json"]) == 0
    capsys.readouterr()
    _assert_no_adapter_managed_residue(necessary)

    local_consumer = necessary / ".agentic-workspace/local/integrations/test-consumer"
    local_consumer.mkdir(parents=True)
    (local_consumer / "cache.json").write_text("{}\n", encoding="utf-8")
    before = (necessary / ".agentic-workspace/config.toml").read_text(encoding="utf-8")
    shutil.rmtree(local_consumer)
    assert (necessary / ".agentic-workspace/config.toml").read_text(encoding="utf-8") == before
    assert cli.main(["status", "--target", str(necessary), "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["health"] == "healthy"

    assert cli.main(["uninstall", "--target", str(necessary), "--modules", "planning,memory", "--format", "json"]) == 0
    capsys.readouterr()
    _assert_no_adapter_managed_residue(necessary)


def test_runtime_and_payload_have_no_external_adapter_reverse_dependency() -> None:
    roots = [ROOT / "src", ROOT / "packages", ROOT / "generated"]
    forbidden_imports = ("agentic_workspace_adapter_", "agentic_workspace_plugin_", "aw_adapter_")
    for root in roots:
        for path in root.rglob("*"):
            if path.suffix not in {".py", ".mjs", ".ts", ".json", ".toml"}:
                continue
            text = path.read_text(encoding="utf-8")
            import_lines = "\n".join(line for line in text.splitlines() if re.match(r"\s*(?:from|import)\s", line))
            assert not any(name in import_lines for name in forbidden_imports), path
