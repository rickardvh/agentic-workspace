from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = ROOT / ".github" / "workflows"
OWNERSHIP_PATH = ROOT / ".github" / "release-ownership.json"


def _ownership() -> dict[str, object]:
    return json.loads(OWNERSHIP_PATH.read_text(encoding="utf-8"))


def test_release_ownership_keeps_preview_distinct_from_support_bearing_release() -> None:
    ownership = _ownership()
    preview = ownership["preview_publisher"]
    stable = ownership["publisher"]
    distribution = ownership["distribution_identity"]

    assert stable["workflow"] == ".github/workflows/release.yml"
    assert "workflow_dispatch" in stable["trigger"]
    assert {key: preview[key] for key in ("workflow", "release_class", "support_bearing")} == {
        "workflow": ".github/workflows/release.yml",
        "release_class": "preview",
        "support_bearing": False,
    }
    assert distribution["preview_release_base_url_template"].endswith("/preview-v{version}")
    assert "stable/preview" in ownership["version_floor_rule"]

    preview_allowed = set(ownership["preview_release_commit_allowed_paths"])
    stable_allowed = set(ownership["release_commit_allowed_paths"])
    assert ".agentic-workspace/payload-provenance.json" in preview_allowed
    assert ".release/previews/" in preview_allowed
    assert ".agentic-workspace/payload-provenance.json" in stable_allowed
    assert ".release/previews/" not in stable_allowed
    assert not any(path == "generated/" for path in preview_allowed)


def test_preview_helper_defaults_to_fetched_reconstruction_authority() -> None:
    helper = (ROOT / "src" / "tooling" / "release" / "preview_release.py").read_text(encoding="utf-8")

    assert 'DEFAULT_RECONSTRUCTION_REF = "master"' in helper
    assert 'f"{head_ref}:{tracking_ref}"' in helper
    assert "source_commit = _resolve_commit(source_ref or fetched_reconstruction_ref)" in helper
    assert 'default="HEAD"' not in helper
    assert "--source-commit" in helper
    assert '"merge-base", "--is-ancestor", source_commit, remote_ref' in helper
    assert '_git("push", remote, f"refs/tags/{tag}")' in helper
    assert "refs/heads/" in helper
    assert "refs/remotes/" in helper


def test_preview_manifest_is_explicitly_non_support_bearing_and_ownership_driven() -> None:
    manifest = (ROOT / "src" / "tooling" / "release" / "preview_manifest.py").read_text(encoding="utf-8")

    assert '"kind": "agentic-workspace/coordinated-preview-release-manifest/v1"' in manifest
    assert "coordinated_release.release_identity(tag)" in manifest
    assert '"support_bearing": False' in manifest
    assert '"required": False' in manifest
    assert '"receipt": None' in manifest
    assert '"artifact_commit": artifact_commit' in manifest
    assert '"reconstruction_source_commit": reconstruction_source_commit' in manifest
    assert "preview_release_base_url_template" in manifest
    assert "releases/download/{tag}" not in manifest
    assert '"registry_resolution_used": False' in manifest


def test_existing_tag_recovery_skips_all_artifact_builds():
    import yaml

    workflow = yaml.load((WORKFLOW_ROOT / "release.yml").read_text(), Loader=yaml.BaseLoader)
    assert "needs.source-version.outputs.build_required == 'true'" in workflow["jobs"]["platform-build"]["if"]
    assert "needs.platform-assemble.result == 'success'" in workflow["jobs"]["release-runtime-matrix"]["if"]
    assert "needs.source-version.outputs.build_required == 'true'" in workflow["jobs"]["agentic-workspace-package"]["if"]
