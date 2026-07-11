from __future__ import annotations

import json
from pathlib import Path

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
