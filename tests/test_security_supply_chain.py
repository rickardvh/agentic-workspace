from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts/check"))
from check_security_supply_chain import evaluate_security_supply_chain  # noqa: E402

from agentic_workspace import workspace_runtime_core  # noqa: E402


def _copy_security_surface(target: Path) -> None:
    paths = [
        "SECURITY.md",
        "docs/security/threat-model.md",
        "uv.lock",
        "src/agentic_workspace/trusted_execution.py",
        "src/agentic_workspace/contracts/security_supply_chain_policy.json",
    ]
    for relative in paths:
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / relative, destination)
    shutil.copytree(REPO_ROOT / ".github/workflows", target / ".github/workflows")


def test_repository_security_supply_chain_readiness_is_exact_and_ready() -> None:
    receipt = evaluate_security_supply_chain(REPO_ROOT)

    assert receipt["status"] == "ready", receipt["failures"]
    assert receipt["release_promotion_allowed"] is True
    assert receipt["subject_fingerprint"].startswith("sha256:")
    assert {control["status"] for control in receipt["controls"]} == {"pass"}


def test_workspace_report_projects_exact_security_readiness() -> None:
    receipt = workspace_runtime_core._security_supply_chain_readiness_payload(target_root=REPO_ROOT)

    assert receipt["kind"] == "agentic-workspace/security-supply-chain-readiness/v1"
    assert receipt["status"] == "ready"
    assert receipt["release_promotion_allowed"] is True


def test_unpinned_action_blocks_release_readiness(tmp_path: Path) -> None:
    _copy_security_surface(tmp_path)
    workflow = tmp_path / ".github/workflows/ci.yml"
    workflow.write_text(
        workflow.read_text(encoding="utf-8").replace("actions/checkout@df4cb1c069e1874edd31b4311f1884172cec0e10", "actions/checkout@v6"),
        encoding="utf-8",
    )

    receipt = evaluate_security_supply_chain(tmp_path)

    assert receipt["status"] == "blocked"
    assert receipt["release_promotion_allowed"] is False
    assert any(failure["control"] == "immutable-least-privilege-actions" for failure in receipt["failures"])


def test_new_unadmitted_shell_boundary_blocks_release_readiness(tmp_path: Path) -> None:
    _copy_security_surface(tmp_path)
    extra = tmp_path / "src/agentic_workspace/unsafe.py"
    extra.write_text("import subprocess\nsubprocess.run('echo unsafe', shell=True)\n", encoding="utf-8")

    receipt = evaluate_security_supply_chain(tmp_path)

    assert receipt["status"] == "blocked"
    shell = next(control for control in receipt["controls"] if control["id"] == "trusted-shell-admission")
    assert "src/agentic_workspace/unsafe.py" in shell["shell_true_paths"]
