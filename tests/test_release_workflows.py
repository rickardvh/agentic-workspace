from __future__ import annotations

import fnmatch
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = ROOT / ".github" / "workflows"
OWNERSHIP_PATH = ROOT / ".github" / "release-ownership.json"
GENERATOR_PATH = ROOT / "scripts" / "generate" / "workspace_command_generation.py"


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


def _load_workspace_command_generation():
    spec = importlib.util.spec_from_file_location("workspace_command_generation_under_test", GENERATOR_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


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

    typescript_package_names = [package["name"] for package in ownership["typescript_packages"]]
    assert typescript_package_names == [
        "@agentic-workspace/workspace-cli",
        "@agentic-workspace/memory-cli",
        "@agentic-workspace/planning-cli",
        "@agentic-workspace/verification-cli",
    ]
    for package in ownership["typescript_packages"]:
        package_json = json.loads((ROOT / package["package_json"]).read_text(encoding="utf-8"))
        assert package_json["name"] == package["name"]
        assert package_json["private"] is False
        assert package_json["publishConfig"]["access"] == "public"
        assert package_json["engines"]["node"] == ">=20"
        assert package["runtime_requirement"] == "node>=20"
        assert package["release_policy"] == "pack-and-publishable"
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
    assert "scripts/release/" in paths
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
    assert "pull_request:" not in workflow
    assert "github.event.pull_request" not in workflow
    assert "contents: write" in workflow
    assert "issues: read" in workflow
    assert "pull-requests: read" in workflow
    assert ".github/release-ownership.json" in workflow
    assert 'ownership["packages"]' in workflow
    assert 'ownership["first_coordinated_release"]["floor_version"]' in workflow
    assert "def pr_label_names(pr_number: str) -> set[str]:" in workflow
    assert "/issues/{pr_number}/labels" in workflow
    assert ".[].filename" in workflow
    assert "associated_pr_numbers" in workflow
    assert "commits/{commit_sha}/pulls" in workflow
    assert "Package-affecting push is associated with a merged PR" not in workflow
    assert "def skip_release(reason: str) -> None:" in workflow
    assert 'output("release_needed", "false")' in workflow
    assert "Merge pull request #" not in workflow
    assert "Package-affecting push has no semver-label context and no coordinated explicit version bump" in workflow
    assert "must have exactly one semver label before release" in workflow
    assert "for pyproject in package_pyprojects:" in workflow
    assert "uv lock" in workflow
    assert "typescript_package_jsons" in workflow
    assert "package_json_version_text" in workflow
    assert "actions/setup-node@v6.4.0" in workflow
    assert 'node-version: "24"' in workflow
    assert "make test-workspace" in workflow
    assert "make lint" in workflow
    assert "make typecheck" in workflow
    assert "make verify" in workflow
    assert "check_generated_command_packages.py" in workflow
    assert "npm test" in workflow
    assert "npm pack --pack-destination" in workflow
    assert "scripts/release/patch_workspace_release_wheel.py" in workflow
    assert "release-asset-base-url" in workflow
    assert "generated/workspace/typescript/package.json" in workflow
    assert "check_no_absolute_paths.py" in workflow
    assert "agentic-workspace-release-manifest.json" in workflow
    assert "SHA256SUMS" in workflow
    assert "Release commit contains disallowed product changes" in workflow
    assert 'git commit -m "Release ${{ steps.release-bump.outputs.tag }}"' in workflow
    assert 'git push origin "${{ steps.release-bump.outputs.tag }}"' in workflow
    assert "softprops/action-gh-release@v3.0.0" in workflow


def test_releaseable_typescript_package_generation_preserves_release_owned_versions() -> None:
    generator = _load_workspace_command_generation()
    rendered_by_path = {
        output.path.relative_to(ROOT).as_posix(): json.loads(output.content)
        for output in generator.render_workspace_command_package_outputs(repo_root=ROOT)
        if output.path.name == "package.json" and "typescript" in output.path.as_posix()
    }

    for package in _ownership()["typescript_packages"]:
        package_json_path = package["package_json"]
        current = json.loads((ROOT / package_json_path).read_text(encoding="utf-8"))
        rendered = rendered_by_path[package_json_path]
        assert rendered["version"] == current["version"]
        assert rendered["private"] is False
        assert rendered["publishConfig"]["access"] == "public"


def test_manual_release_workflow_verifies_all_package_versions_and_assets() -> None:
    workflow = (WORKFLOW_ROOT / "release.yml").read_text(encoding="utf-8")

    assert '"v[0-9]+.[0-9]+.[0-9]+"' in workflow
    assert ".github/release-ownership.json" in workflow
    assert "must match every package version" in workflow
    assert "uv build --wheel --sdist --out-dir dist" in workflow
    assert "uv build --wheel --sdist --out-dir dist packages/memory" in workflow
    assert "uv build --wheel --sdist --out-dir dist packages/planning" in workflow
    assert "uv build --wheel --sdist --out-dir dist packages/verification" in workflow
    assert "scripts/release/patch_workspace_release_wheel.py" in workflow
    assert "release-asset-base-url" in workflow
    assert "actions/setup-node@v6.4.0" in workflow
    assert 'node-version: "24"' in workflow
    assert "npm test && npm pack --pack-destination" in workflow
    assert "typescript_packages" in workflow
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
            "dist/agentic-workspace-workspace-cli-0.4.0.tgz",
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
        "dist/agentic-workspace-workspace-cli-0.4.0.tgz",
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
    assert "for package_json in typescript_package_jsons:" in post_merge_workflow
    assert "version_files = [*package_pyprojects, *typescript_package_jsons]" in post_merge_workflow
    assert 'payload["version"] = next_version' in post_merge_workflow
    assert sorted(ownership["release_commit_allowed_paths"]) == [
        "generated/memory/typescript/package.json",
        "generated/planning/typescript/package.json",
        "generated/verification/typescript/package.json",
        "generated/workspace/typescript/package.json",
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
