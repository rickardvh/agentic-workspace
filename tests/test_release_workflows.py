from __future__ import annotations

import fnmatch
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = ROOT / ".github" / "workflows"
OWNERSHIP_PATH = ROOT / ".github" / "release-ownership.json"


def _ownership() -> dict[str, object]:
    return json.loads(OWNERSHIP_PATH.read_text(encoding="utf-8"))


def _release_asset_patterns(workflow: str) -> list[str]:
    lines = workflow.splitlines()
    files_line = lines.index("          files: |")
    patterns: list[str] = []
    for line in lines[files_line + 1 :]:
        if not line.startswith("            "):
            break
        patterns.append(line.strip())
    return patterns


def _matching_release_assets(patterns: list[str], assets: list[str]) -> list[str]:
    return [asset for asset in assets if any(fnmatch.fnmatchcase(asset, pattern) for pattern in patterns)]


def test_release_ownership_manifest_declares_coordinated_workspace_packages() -> None:
    ownership = _ownership()

    assert ownership["schema_version"] == "agentic-workspace/release-ownership/v1"
    assert ownership["release_model"] == "coordinated-workspace"
    assert ownership["canonical_version_source"] == "pyproject.toml"
    assert ownership["semver_labels"] == ["semver:major", "semver:minor", "semver:patch"]
    assert ownership["first_coordinated_release"]["floor_version"] == "0.4.0"

    package_names = [package["name"] for package in ownership["packages"]]
    assert package_names == [
        "agentic-workspace",
        "agentic-memory",
        "agentic-planning",
        "agentic-verification",
    ]
    for package in ownership["packages"]:
        assert package["pyproject"]
        assert package["wheel_prefix"]
        assert package["sdist_prefix"]
        assert package["payload_schema"]
        assert package["payload_provenance"]
        assert package["generated_command_contract"] == "agentic-workspace/command-package-ir/v1"


def test_package_affecting_scope_is_manifest_owned_and_covers_release_surfaces() -> None:
    paths = set(_ownership()["package_affecting_paths"])

    assert ".github/release-ownership.json" in paths
    assert ".github/workflows/pr-semver-label.yml" in paths
    assert ".github/workflows/release-from-semver-label.yml" in paths
    assert ".github/workflows/release.yml" in paths
    assert "docs/release-and-versioning.md" in paths
    assert "generated/" in paths
    assert "packages/" in paths
    assert "src/" in paths
    assert "tests/test_release_workflows.py" in paths
    assert "uv.lock" in paths


def test_pr_semver_label_workflow_uses_release_ownership_manifest() -> None:
    workflow = (WORKFLOW_ROOT / "pr-semver-label.yml").read_text(encoding="utf-8")

    assert "pull_request:" in workflow
    assert "labeled" in workflow
    assert "unlabeled" in workflow
    assert ".github/release-ownership.json" in workflow
    assert 'ownership["package_affecting_paths"]' in workflow
    assert 'ownership["semver_labels"]' in workflow
    assert "must have exactly one semver label" in workflow


def test_post_merge_release_workflow_bumps_all_packages_from_pr_label() -> None:
    workflow = (WORKFLOW_ROOT / "release-from-semver-label.yml").read_text(encoding="utf-8")

    assert "branches:" in workflow
    assert "master" in workflow
    assert "contents: write" in workflow
    assert "issues: read" in workflow
    assert "pull-requests: read" in workflow
    assert ".github/release-ownership.json" in workflow
    assert 'ownership["packages"]' in workflow
    assert 'ownership["first_coordinated_release"]["floor_version"]' in workflow
    assert "Merge pull request #(\\d+)" in workflow
    assert "Package-affecting direct push did not change package versions" in workflow
    assert "must have exactly one semver label before release" in workflow
    assert "for pyproject in package_pyprojects:" in workflow
    assert "uv lock" in workflow
    assert "make test-workspace" in workflow
    assert "make lint" in workflow
    assert "make typecheck" in workflow
    assert "make verify" in workflow
    assert "check_generated_command_packages.py" in workflow
    assert "check_no_absolute_paths.py" in workflow
    assert "agentic-workspace-release-manifest.json" in workflow
    assert "SHA256SUMS" in workflow
    assert "Release commit contains disallowed product changes" in workflow
    assert 'git commit -m "Release ${{ steps.release-bump.outputs.tag }}"' in workflow
    assert 'git push origin "${{ steps.release-bump.outputs.tag }}"' in workflow
    assert "softprops/action-gh-release@v3.0.0" in workflow


def test_manual_release_workflow_verifies_all_package_versions_and_assets() -> None:
    workflow = (WORKFLOW_ROOT / "release.yml").read_text(encoding="utf-8")

    assert '"v[0-9]+.[0-9]+.[0-9]+"' in workflow
    assert ".github/release-ownership.json" in workflow
    assert "must match every package version" in workflow
    assert "uv build --wheel --sdist --out-dir dist" in workflow
    assert "uv build --wheel --sdist --out-dir dist packages/memory" in workflow
    assert "uv build --wheel --sdist --out-dir dist packages/planning" in workflow
    assert "uv build --wheel --sdist --out-dir dist packages/verification" in workflow
    assert "agentic-workspace-release-manifest.json" in workflow
    assert "SHA256SUMS" in workflow
    assert "Missing checksums for release assets" in workflow
    assert "softprops/action-gh-release@v3.0.0" in workflow
    assert "fail_on_unmatched_files: true" in workflow


def test_release_asset_patterns_exclude_incidental_dist_files() -> None:
    workflow = (WORKFLOW_ROOT / "release.yml").read_text(encoding="utf-8")

    patterns = _release_asset_patterns(workflow)

    assert _matching_release_assets(
        patterns,
        [
            "dist/agentic_workspace-0.4.0-py3-none-any.whl",
            "dist/agentic_workspace-0.4.0.tar.gz",
            "dist/agentic_memory-0.4.0-py3-none-any.whl",
            "dist/agentic_memory-0.4.0.tar.gz",
            "dist/agentic-workspace-release-manifest.json",
            "dist/SHA256SUMS",
            "dist/.gitignore",
            "dist/default.gitignore",
            "dist/agentic_workspace-0.4.0-py3-none-any.whl.sha256",
        ],
    ) == [
        "dist/agentic_workspace-0.4.0-py3-none-any.whl",
        "dist/agentic_workspace-0.4.0.tar.gz",
        "dist/agentic_memory-0.4.0-py3-none-any.whl",
        "dist/agentic_memory-0.4.0.tar.gz",
        "dist/agentic-workspace-release-manifest.json",
        "dist/SHA256SUMS",
    ]


def test_release_notes_classify_compatibility_significant_changes() -> None:
    release_config = (ROOT / ".github" / "release.yml").read_text(encoding="utf-8")

    assert "Compatibility-significant changes" in release_config
    assert "schema" in release_config
    assert "generated-runtime" in release_config
    assert "conformance" in release_config
    assert "compatibility" in release_config


def test_release_workflows_prevent_coordinated_version_drift_at_release_time() -> None:
    ownership = _ownership()
    release_workflow = (WORKFLOW_ROOT / "release.yml").read_text(encoding="utf-8")
    post_merge_workflow = (WORKFLOW_ROOT / "release-from-semver-label.yml").read_text(encoding="utf-8")

    assert "if declared != version:" in release_workflow
    assert "Direct release push must set every package to the same version" in post_merge_workflow
    assert "would downgrade below floor" in post_merge_workflow
    assert "for pyproject in package_pyprojects:" in post_merge_workflow
    assert sorted(ownership["release_commit_allowed_paths"]) == [
        "packages/memory/pyproject.toml",
        "packages/planning/pyproject.toml",
        "packages/verification/pyproject.toml",
        "pyproject.toml",
        "uv.lock",
    ]


def test_post_merge_release_uses_floor_for_first_coordinated_normalization() -> None:
    workflow = (WORKFLOW_ROOT / "release-from-semver-label.yml").read_text(encoding="utf-8")

    assert "needs_first_normalization" in workflow
    assert "current_package_floor" in workflow
    assert "next_version = floor_version" in workflow
    assert "else:" in workflow
    assert "next_version = bump_version(current_floor, selected[0])" in workflow


def test_current_versions_have_no_downgrade_floor_for_first_coordinated_release() -> None:
    ownership = _ownership()
    versions = [
        tomllib.loads((ROOT / package["pyproject"]).read_text(encoding="utf-8"))["project"]["version"] for package in ownership["packages"]
    ]
    floor = ownership["first_coordinated_release"]["floor_version"]

    assert tuple(int(part) for part in floor.split(".")) >= max(tuple(int(part) for part in version.split(".")) for version in versions)
