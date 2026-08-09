from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/release/support_bearing_promotion.py"
spec = importlib.util.spec_from_file_location("support_bearing_promotion_under_test", SCRIPT)
assert spec is not None and spec.loader is not None
PROMOTION = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = PROMOTION
spec.loader.exec_module(PROMOTION)


def _write(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_server_check_receipt_binds_required_check_to_exact_commit() -> None:
    receipt = PROMOTION.server_check_receipt(
        repository="owner/repo",
        commit="expected",
        required=["Support-bearing promotion"],
        check_runs={
            "check_runs": [
                {
                    "name": "Support-bearing promotion",
                    "conclusion": "success",
                    "head_sha": "expected",
                    "html_url": "https://example.test/check",
                }
            ]
        },
    )
    assert receipt["status"] == "passed"
    assert receipt["source_commit"] == "expected"

    mismatched = PROMOTION.server_check_receipt(
        repository="owner/repo",
        commit="expected",
        required=["Support-bearing promotion"],
        check_runs={"check_runs": [{"name": "Support-bearing promotion", "conclusion": "success", "head_sha": "other"}]},
    )
    assert mismatched["status"] == "blocked"


def test_checked_in_master_ruleset_requires_pr_and_support_bearing_check() -> None:
    policy = json.loads((ROOT / ".github/support-bearing-promotion.json").read_text(encoding="utf-8"))
    ruleset = json.loads((ROOT / ".github/rulesets/master-support-bearing.json").read_text(encoding="utf-8"))
    assert policy["live_ruleset_id"] == 20615912
    assert policy["required_check"] == "Support-bearing promotion"
    assert ruleset["enforcement"] == "active"
    assert ruleset["bypass_actors"] == []
    assert ruleset["conditions"]["ref_name"]["include"] == ["refs/heads/master"]
    rules = {rule["type"]: rule for rule in ruleset["rules"]}
    assert "non_fast_forward" in rules
    assert rules["pull_request"]["parameters"]["required_review_thread_resolution"] is True
    assert rules["required_status_checks"]["parameters"]["required_status_checks"] == [{"context": "Support-bearing promotion"}]


def _compose_fixture(tmp_path: Path, commit: str = "release-commit") -> list[str]:
    dist = tmp_path / "dist"
    runtime = tmp_path / "runtime"
    dist.mkdir()
    runtime.mkdir()
    wheel = dist / "agentic_workspace-1.0.0-py3-none-any.whl"
    wheel.write_bytes(b"wheel")
    wheel_digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    server = _write(
        tmp_path / "server.json",
        {
            "kind": "agentic-workspace/server-promotion-receipt/v1",
            "status": "passed",
            "source_commit": commit,
        },
    )
    for os_name, python, node in (("ubuntu-latest", "3.13", "20"), ("windows-latest", "3.14", "24")):
        _write(
            runtime / f"{os_name}.json",
            {
                "kind": "agentic-workspace/runtime-support-receipt/v1",
                "status": "passed",
                "source_commit": commit,
                "os": os_name,
                "python": python,
                "node": node,
            },
        )
    semantic = []
    for major in (20, 24, 25):
        semantic.append(
            _write(
                dist / f"generated-command-conformance-node{major}.json",
                {
                    "kind": "agentic-workspace/generated-command-semantic-conformance-receipt/v1",
                    "status": "passed",
                    "subject": {"node_version": f"{major}.0.0"},
                },
            )
        )
    _write(
        dist / "distribution-install-readiness.json",
        {
            "kind": "agentic-workspace/distribution-install-readiness/v1",
            "status": "passed",
            "artifact": {"name": wheel.name, "sha256": wheel_digest},
        },
    )
    _write(
        dist / "redistributable-package-readiness.json",
        {
            "kind": "agentic-workspace/redistributable-package-readiness/v1",
            "status": "passed",
            "license_spdx": "MIT",
        },
    )
    _write(
        dist / "security-supply-chain-readiness.json",
        {
            "kind": "agentic-workspace/security-supply-chain-readiness/v1",
            "status": "ready",
            "release_promotion_allowed": True,
            "subject": {"source_identity": commit},
        },
    )
    return [
        "compose",
        "--commit",
        commit,
        "--artifact-dir",
        str(dist),
        "--server-receipt",
        str(server),
        "--runtime-receipt-dir",
        str(runtime),
        *[argument for path in semantic for argument in ("--semantic-receipt", str(path))],
        "--output",
        str(dist / "support-bearing-promotion.json"),
    ]


def test_composed_promotion_passes_only_with_every_exact_receipt(tmp_path: Path) -> None:
    args = _compose_fixture(tmp_path)
    assert PROMOTION.main(args) == 0
    result = json.loads((tmp_path / "dist/support-bearing-promotion.json").read_text(encoding="utf-8"))
    assert result["status"] == "passed"
    assert set(result["domains"].values()) == {"passed", "ready"}
    assert result["artifacts"]


def test_composed_promotion_fails_closed_on_stale_or_missing_evidence(tmp_path: Path) -> None:
    args = _compose_fixture(tmp_path)
    (tmp_path / "runtime/windows-latest.json").unlink()
    security = tmp_path / "dist/security-supply-chain-readiness.json"
    payload = json.loads(security.read_text(encoding="utf-8"))
    payload["subject"]["source_identity"] = "stale"
    _write(security, payload)
    assert PROMOTION.main(args) == 1
    result = json.loads((tmp_path / "dist/support-bearing-promotion.json").read_text(encoding="utf-8"))
    assert result["status"] == "blocked"
    assert any("runtime support receipt" in failure for failure in result["failures"])
    assert any("exact source commit" in failure for failure in result["failures"])
