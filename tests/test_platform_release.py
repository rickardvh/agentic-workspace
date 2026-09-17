"""Complete native inventory and compiler-free consumer admission boundaries."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/release"))
import platform_release as release  # noqa: E402


@pytest.mark.parametrize(
    "system,machine,target",
    [
        ("Windows", "ARM64", "aarch64-pc-windows-msvc"),
        ("Windows", "AMD64", "x86_64-pc-windows-msvc"),
        ("Darwin", "arm64", "aarch64-apple-darwin"),
        ("Darwin", "x86_64", "x86_64-apple-darwin"),
        ("Linux", "aarch64", "aarch64-unknown-linux-gnu"),
        ("Linux", "x86_64", "x86_64-unknown-linux-gnu"),
    ],
)
def test_host_selects_its_native_release_target(monkeypatch, system, machine, target):
    monkeypatch.setattr(release.platform, "system", lambda: system)
    monkeypatch.setattr(release.platform, "machine", lambda: machine)
    assert release.current_platform()["target"] == target


@pytest.fixture
def inventory(tmp_path):
    rows = []
    for platform in release.platforms():
        row = dict(platform)
        for key, suffix in (("wheel", ".whl"), ("native_archive", ".zip")):
            path = tmp_path / (platform["target"] + suffix)
            path.write_bytes(path.name.encode())
            row[key] = release.asset(path)
        rows.append(row)
    npm = tmp_path / "universal.tgz"
    npm.write_bytes(b"all platforms")
    data = {
        "kind": "agentic-workspace/platform-release/v1",
        "version": "1.0.0rc3",
        "source_commit": "a" * 40,
        "platforms": rows,
        "npm": release.asset(npm),
    }
    (tmp_path / release.MANIFEST).write_text(json.dumps(data))
    for row in rows:
        (tmp_path / f"platform-consumer-{row['target']}.json").write_text(
            json.dumps(
                {
                    "kind": "agentic-workspace/platform-consumer/v1",
                    "status": "passed",
                    "target": row["target"],
                    "source_commit": data["source_commit"],
                    "inventory_sha256": release.digest(tmp_path / release.MANIFEST),
                    "rust_available": False,
                    "checks": ["uv-sync", "npm-install", "native-start"],
                }
            )
        )
    return tmp_path, data


@pytest.mark.parametrize(
    "failure",
    [
        None,
        "missing-platform",
        "duplicate-platform",
        "wrong-target",
        "wheel-drift",
        "npm-drift",
        "missing-proof",
        "stale-proof",
        "compiler-present",
    ],
)
def test_publication_requires_complete_exact_platforms_and_compiler_free_proof(inventory, failure):
    root, data = inventory
    row = data["platforms"][0]
    receipt_path = root / f"platform-consumer-{row['target']}.json"
    if failure in {"missing-platform", "duplicate-platform", "wrong-target"}:
        if failure == "missing-platform":
            data["platforms"].pop()
        elif failure == "duplicate-platform":
            data["platforms"][-1] = row
        else:
            row["node_arch"] = "wrong"
        (root / release.MANIFEST).write_text(json.dumps(data))
    elif failure in {"wheel-drift", "npm-drift"}:
        item = row["wheel"] if failure == "wheel-drift" else data["npm"]
        (root / item["asset"]).write_bytes(b"changed")
    elif failure == "missing-proof":
        receipt_path.unlink()
    elif failure in {"stale-proof", "compiler-present"}:
        receipt = json.loads(receipt_path.read_text())
        receipt["inventory_sha256" if failure == "stale-proof" else "rust_available"] = "old" if failure == "stale-proof" else True
        receipt_path.write_text(json.dumps(receipt))
    if failure:
        with pytest.raises((ValueError, OSError)):
            release.verify_consumers(root)
    else:
        assert len(release.verify_consumers(root)["platforms"]) == 6


def test_platform_receipts_do_not_change_when_manifest_is_extended(inventory):
    root, data = inventory
    install = root / "distribution-install-readiness.json"
    redistribution = root / "redistributable-package-readiness.json"
    install.write_text('{"status":"passed"}')
    redistribution.write_text('{"artifacts":[],"artifact_count":0}')
    release.update_receipts(root, "v1.0.0-rc.3")
    before = install.read_bytes(), redistribution.read_bytes()
    release.update_receipts(root, "v1.0.0-rc.3")
    assert before == (install.read_bytes(), redistribution.read_bytes())
    assert len(json.loads(install.read_text())["platforms"]) == 6
    assert json.loads(redistribution.read_text())["artifact_count"] == 12
