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
    assert stable["trigger"] == "existing-tag-only"
    assert preview == {
        "workflow": ".github/workflows/preview-release.yml",
        "trigger": "preview-vMAJOR.MINOR.PATCH tag",
        "release_class": "preview",
        "support_bearing": False,
        "tag_rule": (
            "preview-vMAJOR.MINOR.PATCH must point at a release-only commit whose single parent is the exact reconstruction source commit"
        ),
    }
    assert distribution["preview_release_base_url_template"].endswith("/preview-v{version}")
    assert "preview-vMAJOR.MINOR.PATCH" in ownership["version_floor_rule"]

    preview_allowed = set(ownership["preview_release_commit_allowed_paths"])
    stable_allowed = set(ownership["release_commit_allowed_paths"])
    assert ".agentic-workspace/payload-provenance.json" in preview_allowed
    assert ".release/previews/" in preview_allowed
    assert ".agentic-workspace/payload-provenance.json" not in stable_allowed
    assert ".release/previews/" not in stable_allowed
    assert not any(path == "generated/" for path in preview_allowed)


def test_preview_workflow_reuses_release_authorities_without_support_bearing_admission() -> None:
    preview = (WORKFLOW_ROOT / "preview-release.yml").read_text(encoding="utf-8")
    stable = (WORKFLOW_ROOT / "release.yml").read_text(encoding="utf-8")

    assert '"preview-v[0-9]+.[0-9]+.[0-9]+"' in preview
    assert '"v[0-9]+.[0-9]+.[0-9]+"' in stable
    assert "preview-v" not in stable
    assert "verify-preview" in preview
    assert "prerelease: true" in preview
    assert "agentic-workspace-preview-release-manifest.json" in preview
    assert "agentic-workspace-release-manifest.json" not in preview
    assert "support_bearing_promotion.py" not in preview
    assert "test ! -e dist/support-bearing-promotion.json" in preview
    assert "overwrite_files: false" in preview
    assert "--check-published" in preview
    assert "support_bearing_promotion.py github-checks" in stable
    assert "support_bearing_promotion.py compose" in stable

    shared_authorities = (
        "uv build --wheel --sdist --out-dir dist",
        "scripts/release/patch_workspace_release_wheel.py",
        "scripts/release/stage_native_npm.py",
        "make packed-artifact-conformance",
        "scripts/check/check_package_identity.py",
        "scripts/check/check_security_supply_chain.py",
        "anchore/sbom-action@aa80c8c5bd439a416a62804f2151ab38c671a638",
        "actions/attest-build-provenance@4d101475d8b20a2381f78447822ac1eab6504dd8",
        "softprops/action-gh-release@3d0d9888cb7fd7b750713d6e236d1fcb99157228",
    )
    for authority in shared_authorities:
        assert authority in preview
        assert authority in stable

    assert "refs/heads/reconstruct/first-stable:refs/remotes/origin/reconstruct/first-stable" in preview
    assert '--release-asset-base-url "https://github.com/${GITHUB_REPOSITORY}/releases/download/${RELEASE_TAG}"' in preview
    assert "test_release_root_wheel_installs_workspace_stack_from_same_release_assets" in preview


def test_preview_helper_defaults_to_fetched_reconstruction_authority() -> None:
    helper = (ROOT / "scripts" / "release" / "preview_release.py").read_text(encoding="utf-8")

    assert 'DEFAULT_RECONSTRUCTION_REF = "reconstruct/first-stable"' in helper
    assert 'f"{head_ref}:{tracking_ref}"' in helper
    assert "source_commit = _resolve_commit(source_ref or fetched_reconstruction_ref)" in helper
    assert 'default="HEAD"' not in helper
    assert "--source-commit" in helper
    assert "freshly fetched reconstruction branch head" in helper
    assert '"merge-base", "--is-ancestor", source_commit, remote_ref' in helper
    assert '_git("push", remote, f"refs/tags/{tag}")' in helper
    assert "refs/heads/" in helper
    assert "refs/remotes/" in helper


def test_preview_manifest_is_explicitly_non_support_bearing_and_ownership_driven() -> None:
    manifest = (ROOT / "scripts" / "release" / "preview_manifest.py").read_text(encoding="utf-8")

    assert '"kind": "agentic-workspace/coordinated-preview-release-manifest/v1"' in manifest
    assert '"release_class": "preview"' in manifest
    assert '"support_bearing": False' in manifest
    assert '"required": False' in manifest
    assert '"receipt": None' in manifest
    assert '"artifact_commit": artifact_commit' in manifest
    assert '"reconstruction_source_commit": reconstruction_source_commit' in manifest
    assert "preview_release_base_url_template" in manifest
    assert "releases/download/{tag}" not in manifest
    assert '"registry_resolution_used": False' in manifest


def test_release_docs_describe_preview_as_testing_not_stable_admission() -> None:
    docs = (ROOT / "docs" / "release-and-versioning.md").read_text(encoding="utf-8")

    assert "## Preview Releases" in docs
    assert "**non-support-bearing**" in docs
    assert "does not satisfy #2990 support-bearing admission" in docs
    assert "preview_release.py --version 0.52.0 --push" in docs
    assert "only that tag is pushed" in docs
    assert "A public preview therefore burns its numeric package version" in docs
    assert "only support-bearing GitHub Release" in docs
