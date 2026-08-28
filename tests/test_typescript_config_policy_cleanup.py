from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULES = (
    "./src/agentic_workspace/contracts/typescript_primitive_support.mjs",
    "./generated/workspace/typescript/src/hostPrimitiveSupport.mjs",
)


def _apply_clear_setup(target: Path, module: str, source: str) -> dict[str, object]:
    workspace = target / ".agentic-workspace"
    workspace.mkdir(parents=True)
    config = workspace / "config.local.toml"
    config.write_bytes(source.encode("utf-8"))
    setup_identity = "sha256:setup-cleanup-fixture"
    (workspace / "adoption-receipt.json").write_text(
        json.dumps({"configuration_readiness": {"identity": setup_identity}}), encoding="utf-8"
    )
    decision = {
        "kind": "agentic-workspace/config-policy-decision/v1",
        "concern_id": "setup-cleanup-fixture",
        "authority": "human-answer",
        "scope": "local",
        "setup_identity": setup_identity,
        "changes": {},
        "clear_setup_disposition": True,
    }
    values = {
        "target": str(target),
        "decision_json": json.dumps(decision),
        "expect_config_revision": "sha256:" + hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "expect_setup_identity": setup_identity,
        "dry_run": False,
        "format": "json",
    }
    script = f"""
import {{ executeHostPrimitive }} from {json.dumps(module)};
const payload = executeHostPrimitive('config.policy.apply', {json.dumps(values)}, {{}}, 'config.policy-apply');
console.log(JSON.stringify(payload));
"""
    completed = subprocess.run(["node", "--input-type=module", "--eval", script], cwd=ROOT, text=True, capture_output=True, check=False)
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


@pytest.mark.parametrize("module", MODULES)
@pytest.mark.parametrize("newline", ("\n", "\r\n"))
def test_typescript_clear_setup_removes_complete_table_and_preserves_adjacent_toml(tmp_path: Path, module: str, newline: str) -> None:
    before = (
        newline.join(
            (
                "schema_version = 1",
                "[workspace]",
                "enabled = true",
                "# setup disposition follows",
            )
        )
        + newline
    )
    setup = (
        newline.join(
            (
                "[setup]",
                'prompt_disposition = "deferred"',
                'setup_identity = "sha256:setup-cleanup-fixture"',
                'context_revision = "sha256:context"',
                'unresolved_concerns = ["orchestration-posture"]',
                'required_concerns = ["orchestration-posture"]',
            )
        )
        + newline
    )
    after = newline.join(("[other]", 'value = "preserved"', "# preserved tail")) + newline
    target = tmp_path / f"target-{MODULES.index(module)}-{len(newline)}"

    payload = _apply_clear_setup(target, module, before + setup + after)

    assert (target / ".agentic-workspace/config.local.toml").read_bytes().decode("utf-8") == before + after
    assert payload["status"] == "applied"
    assert payload["effects"] == [{"owner": "config.local", "field": "setup", "value": "removed"}]


@pytest.mark.parametrize("module", MODULES)
def test_typescript_clear_setup_without_table_is_idempotent(tmp_path: Path, module: str) -> None:
    source = 'schema_version = 1\n[workspace]\nenabled = true\n[other]\nvalue = "preserved"\n'
    target = tmp_path / f"no-table-{MODULES.index(module)}"

    payload = _apply_clear_setup(target, module, source)

    assert (target / ".agentic-workspace/config.local.toml").read_text(encoding="utf-8") == source
    assert payload["status"] == "current"
    assert payload["mutation_applied"] is False
    assert payload["effects"] == []
