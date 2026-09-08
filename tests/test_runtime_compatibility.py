from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from agentic_workspace.config import WorkspaceUsageError, load_workspace_config
from agentic_workspace.runtime_compatibility import (
    READER_CONTRACT_EPOCH,
    admit_runtime_compatibility,
    target_root_from_argv,
)


def _write_config(
    root: Path,
    *,
    minimum_epoch: int | None = None,
    capabilities: tuple[str, ...] = (),
    invocation: str = "agentic-workspace",
) -> Path:
    config_dir = root / ".agentic-workspace"
    config_dir.mkdir(parents=True)
    lines = [
        "schema_version = 1",
        "",
        "[workspace]",
        f"cli_invoke = {json.dumps(invocation)}",
        "",
        "[cli_compatibility]",
        'contract_schema = "agentic-workspace/installed-state-compatibility/v1"',
    ]
    if minimum_epoch is not None:
        lines.append(f"minimum_reader_epoch = {minimum_epoch}")
    if capabilities:
        lines.append(f"required_reader_capabilities = {json.dumps(list(capabilities))}")
    path = config_dir / "config.toml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_matching_reader_is_admitted_before_managed_state(tmp_path: Path) -> None:
    _write_config(
        tmp_path,
        minimum_epoch=READER_CONTRACT_EPOCH,
        capabilities=("pre-state-runtime-compatibility-v1",),
    )

    admission = admit_runtime_compatibility(tmp_path)

    assert admission["status"] == "admitted"
    assert admission["managed_state_interpreted"] is False
    assert admission["observed_runtime"]["reader_epoch"] == READER_CONTRACT_EPOCH
    assert admission["identity_digest"].startswith("sha256:")
    loaded = load_workspace_config(target_root=tmp_path)
    assert loaded.cli_compatibility.minimum_reader_epoch == READER_CONTRACT_EPOCH
    assert loaded.cli_compatibility.required_reader_capabilities == ("pre-state-runtime-compatibility-v1",)
    assert not loaded.warnings


def test_new_reader_accepts_repository_without_epoch_contract(tmp_path: Path) -> None:
    _write_config(tmp_path)

    admission = admit_runtime_compatibility(tmp_path)

    assert admission["status"] == "admitted"
    assert admission["expected_repository"]["minimum_reader_epoch"] == 0


def test_missing_configured_source_runner_does_not_trigger_state_fallback(tmp_path: Path) -> None:
    missing_runner = "python missing/source runner.py"
    _write_config(tmp_path, minimum_epoch=READER_CONTRACT_EPOCH + 1, invocation=missing_runner)

    admission = admit_runtime_compatibility(tmp_path)

    assert admission["status"] == "blocked"
    assert admission["recovery_command"] == missing_runner
    assert admission["managed_state_interpreted"] is False


def test_target_parser_preserves_paths_with_spaces(tmp_path: Path) -> None:
    target = tmp_path / "repo with spaces"
    target.mkdir()

    assert target_root_from_argv(["summary", "--target", str(target)], cwd=tmp_path) == target.resolve()
    assert target_root_from_argv(["summary", f"--target={target}"], cwd=tmp_path) == target.resolve()


def test_full_config_rejects_malformed_reader_epoch(tmp_path: Path) -> None:
    _write_config(tmp_path, minimum_epoch=READER_CONTRACT_EPOCH)
    config_path = tmp_path / ".agentic-workspace" / "config.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace("minimum_reader_epoch = 1", "minimum_reader_epoch = 0"), encoding="utf-8"
    )

    admission = admit_runtime_compatibility(tmp_path)
    assert admission["status"] == "blocked"
    assert admission["failed_checks"] == ["compatibility_contract_shape"]
    with pytest.raises(WorkspaceUsageError, match="minimum_reader_epoch must be a positive integer"):
        load_workspace_config(target_root=tmp_path)


def test_reader_identity_keeps_existing_sorted_ascii_encoding(tmp_path: Path) -> None:
    target = tmp_path / "work ÃƒÂ© Ã°Å¸Ëœâ‚¬"
    target.mkdir()
    _write_config(target, minimum_epoch=1, capabilities=(" z ", "pre-state-runtime-compatibility-v1", "z"))
    admission = admit_runtime_compatibility(target)
    identity = {"expected": admission["expected_repository"], "observed": admission["observed_runtime"], "target": str(target.resolve())}
    assert admission["identity_digest"] == "sha256:" + hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    assert admission["missing_reader_capabilities"] == ["z"]


def test_invalid_configuration_cannot_disappear_before_reader_admission(tmp_path: Path) -> None:
    source = _write_config(tmp_path)
    source.write_text("[broken")
    assert admit_runtime_compatibility(tmp_path)["status"] == "blocked"


@pytest.mark.parametrize(
    "declaration,failed_check",
    [
        ('cli_compatibility="invalid"', "compatibility_contract_shape"),
        ('cli_compatibility=["invalid"]', "compatibility_contract_shape"),
        ('[cli_compatibility]\ncontract_schema=""', "compatibility_contract_shape"),
        ("[cli_compatibility]\nrequired_reader_capabilities=[1]", "compatibility_contract_shape"),
        ('[cli_compatibility]\ncontract_schema="agentic-workspace/future-contract/v99"', "contract_schema"),
    ],
)
def test_binding_reader_rejects_invalid_or_unknown_contract(tmp_path: Path, declaration: str, failed_check: str) -> None:
    source = tmp_path / ".agentic-workspace/config.toml"
    source.parent.mkdir()
    source.write_text("schema_version=1\n" + declaration + "\n")
    result = admit_runtime_compatibility(tmp_path)
    assert result["status"] == "blocked"
    assert result["failed_checks"] == [failed_check]
