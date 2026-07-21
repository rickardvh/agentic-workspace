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


def _step_run_block(workflow: str, step_name: str) -> str:
    lines = workflow.splitlines()
    step_line = f"      - name: {step_name}"
    step_index = lines.index(step_line)
    run_index = next(index for index in range(step_index, len(lines)) if lines[index].strip() == "run: |")
    block_indent = len(lines[run_index]) - len(lines[run_index].lstrip()) + 2
    block_lines: list[str] = []
    for line in lines[run_index + 1 :]:
        if line.strip() and len(line) - len(line.lstrip()) < block_indent:
            break
        block_lines.append(line[block_indent:] if line.startswith(" " * block_indent) else "")
    return "\n".join(block_lines)


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
    assert ownership["changeset_dir"] == ".release/changes"
    assert ownership["release_notes_dir"] == ".release/releases"
    assert ownership["release_pr_branch"] == "automation/coordinated-release"
    assert ownership["publisher"]["trigger"] == "existing-tag-only"
    assert ownership["semver_labels"] == ["semver:major", "semver:minor", "semver:patch"]
    assert "every existing vMAJOR.MINOR.PATCH tag" in ownership["version_floor_rule"]

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
    assert ".release/changes/" in paths
    assert ".release/releases/" in paths
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
    assert 'ownership["changeset_dir"]' in workflow
    assert 'ownership["release_pr_branch"]' in workflow
    assert "release changeset" in workflow
    assert "agentic-workspace/release-change/v1" in workflow
    assert 'coordinated_release.py", "verify' in workflow


def test_master_release_workflow_prepares_release_pr_and_only_tags_verified_release_commit() -> None:
    workflow = (WORKFLOW_ROOT / "release-from-semver-label.yml").read_text(encoding="utf-8")

    assert "branches:" in workflow
    assert "master" in workflow
    assert "pull_request:" not in workflow
    assert "github.event.pull_request" not in workflow
    assert "contents: write" in workflow
    assert "pull-requests: write" in workflow
    assert "actions: write" in workflow
    assert "concurrency:" in workflow
    assert "prepare-coordinated-release-${{ github.ref }}" in workflow
    assert "cancel-in-progress: false" in workflow
    assert "coordinated_release.py plan" in workflow
    assert "coordinated_release.py prepare" in workflow
    assert "coordinated_release.py verify" in workflow
    assert "coordinated_release.py tag-plan" in workflow
    assert "uv lock" in workflow
    assert "peter-evans/create-pull-request@v7" in workflow
    assert "automation/coordinated-release" in workflow
    assert "Resolve pending release tag" in workflow
    assert "git tag -a" in workflow
    assert '"${{ steps.release-commit.outputs.release_commit }}"' in workflow
    assert "git fetch origin master --tags" in workflow
    assert 'git push origin "${{ steps.release-commit.outputs.tag }}"' in workflow
    assert "Resolve publisher dispatch" in workflow
    assert "steps.release-commit.outputs.publish_candidate == 'true'" in workflow
    assert "gh release view" in workflow
    assert "agentic-workspace-release-manifest.json" in workflow
    assert "release-assets-missing-or-draft" in workflow
    assert "steps.publisher.outputs.publish_needed == 'true'" in workflow
    assert "steps.release-commit.outputs.tag_needed == 'true'" in workflow
    assert workflow.count("gh workflow run release.yml") == 1
    assert '-f tag="${{ steps.publisher.outputs.tag }}"' in workflow
    assert '-f source_commit="${{ steps.publisher.outputs.release_commit }}"' in workflow
    assert "softprops/action-gh-release" not in workflow


def test_release_publisher_dispatch_heredoc_terminates_at_shell_column_zero() -> None:
    workflow = (WORKFLOW_ROOT / "release-from-semver-label.yml").read_text(encoding="utf-8")
    run_block = _step_run_block(workflow, "Resolve publisher dispatch")

    assert "python - <<'PY'\n" in run_block
    assert "\nPY\n" in run_block
    assert "\n  PY\n" not in run_block
    assert "\n    PY\n" not in run_block


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
    assert "workflow_dispatch:" in workflow
    assert "source_commit:" in workflow
    assert ".github/release-ownership.json" in workflow
    assert "fetch-depth: 0" in workflow
    assert "Verify tag targets coordinated release commit" in workflow
    assert "git rev-list -n 1" in workflow
    assert "EXPECTED_SOURCE_COMMIT" in workflow
    assert "must point at a commit reachable from origin/master" in workflow
    assert 'coordinated_release.py verify --tag "${RELEASE_TAG}"' in workflow
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
    assert "source_commit" in workflow
    assert "body_path: .release/releases/${{ env.RELEASE_TAG }}.md" in workflow
    assert "generate_release_notes: true" not in workflow
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

    assert "coordinated_release.py verify --tag" in release_workflow
    assert 'manifest.get("source_commit")' in release_workflow
    assert "coordinated_release.py prepare" in post_merge_workflow
    assert "coordinated_release.py tag-plan" in post_merge_workflow
    assert "gh workflow run release.yml" in post_merge_workflow
    assert sorted(ownership["release_commit_allowed_paths"]) == [
        ".release/releases/",
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


def test_release_model_uses_existing_tags_instead_of_stale_bootstrap_floor() -> None:
    helper = (ROOT / "scripts" / "release" / "coordinated_release.py").read_text(encoding="utf-8")

    assert "existing_release_versions" in helper
    assert 'git", "tag", "--list"' in helper
    assert "floor = max([*package_versions, *tag_versions])" in helper
    assert "pending_tag_plan" in helper
    assert "first_coordinated_release" not in helper
