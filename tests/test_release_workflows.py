from __future__ import annotations

import ast
import fnmatch
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = ROOT / ".github" / "workflows"
OWNERSHIP_PATH = ROOT / ".github" / "release-ownership.json"
RULESET_PATH = ROOT / ".github" / "rulesets" / "master-support-bearing.json"
SUPPORT_POLICY_PATH = ROOT / ".github" / "support-bearing-promotion.json"
RELEASE_OWNERSHIP_CLASSIFIER_PATH = ROOT / "src" / "tooling" / "release" / "release_ownership.py"


def test_release_publication_permissions_and_pinned_source():
    import yaml

    workflow = yaml.safe_load((WORKFLOW_ROOT / "release.yml").read_text())
    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert all(not value.get("required") for value in workflow["on"]["workflow_dispatch"]["inputs"].values())
    assert workflow["concurrency"]["cancel-in-progress"] is False
    jobs = workflow["jobs"]
    for name, job in jobs.items():
        permissions = job.get("permissions", workflow["permissions"])
        assert permissions.get("pull-requests") != "write"
        assert permissions.get("actions") != "write"
        commands = "\n".join(step.get("run", "") for step in job.get("steps", []))
        assert "gh workflow run" not in commands
        if any(
            command in commands for command in ("platform_release.py build", "release_lifecycle.py build", "release_lifecycle.py compose")
        ):
            assert permissions.get("contents") != "write"
            assert permissions.get("id-token") != "write"
        if job.get("environment") in {"package-registries", "cargo-registry"}:
            assert "publish-github" in job["needs"]
            assert "!inputs.qualify_only" in job["if"]
            assert not any(command in commands for command in ("uv build", "npm pack", "cargo package", "cargo_release.py build"))
        for step in job.get("steps", []):
            if step.get("uses", "").startswith("actions/checkout@"):
                assert step["with"]["ref"] in {"${{ github.sha }}", "${{ needs.source-version.outputs.source_commit }}"}
                assert step["with"]["persist-credentials"] is False
    publisher = jobs["publish-github"]
    assert "!inputs.qualify_only" in publisher["if"]
    assert any(step.get("uses", "").startswith("actions/download-artifact@") for step in publisher["steps"])
    assert any(step.get("with", {}).get("name") == "verified-release-bundle" for job in jobs.values() for step in job.get("steps", []))
    assert set(jobs["verify-destinations"]["needs"]) >= {"language-registries", "language-packages"}


def test_ci_pr_path_is_merge_sufficiency_not_release_admission():
    import yaml

    workflow = yaml.safe_load((WORKFLOW_ROOT / "ci.yml").read_text())
    jobs = workflow["jobs"]
    merge = jobs["merge-sufficiency"]
    assert "github.event_name == 'pull_request'" in merge["if"]
    assert "uv build" not in str(merge)
    assert set(jobs["readiness"]["needs"]) == {"merge-sufficiency", "security"}
    assert "github.event_name == 'workflow_dispatch'" in jobs["workspace-checks"]["if"]


def test_ci_supports_explicit_exact_source_validation():
    import yaml

    workflow = yaml.safe_load((WORKFLOW_ROOT / "ci.yml").read_text())
    inputs = workflow["on"]["workflow_dispatch"]["inputs"]
    assert set(inputs) == {"expected_head_sha", "reason"}
    assert all(value["required"] for value in inputs.values())
    admission = workflow["jobs"]["exhaustive-admission"]
    assert admission["if"] == "github.event_name == 'workflow_dispatch'"
    assert "${{ inputs.expected_head_sha }}" in str(admission)


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


def _load_release_ownership_classifier():
    spec = importlib.util.spec_from_file_location("release_ownership_under_test", RELEASE_OWNERSHIP_CLASSIFIER_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_release_ownership_manifest_declares_coordinated_workspace_packages() -> None:
    ownership = _ownership()

    assert ownership["schema_version"] == "agentic-workspace/release-ownership/v1"
    assert ownership["release_model"] == "coordinated-workspace"
    assert ownership["changeset_dir"] == ".release/changes"
    assert ownership["release_notes_dir"] == ".release/releases"
    assert ownership["semver_labels"] == ["semver:major", "semver:minor", "semver:patch"]

    package_names = [package["name"] for package in ownership["packages"]]
    assert package_names == ["agentic-workspace"]
    for package in ownership["packages"]:
        assert package["pyproject"]
        assert package["wheel_prefix"]
        assert package["sdist_prefix"]
        assert package["payload_schema"]
        assert package["payload_provenance"]

    typescript_package_names = [package["name"] for package in ownership["typescript_packages"]]
    assert typescript_package_names == ["@agentic-workspace/workspace-cli"]
    for package in ownership["typescript_packages"]:
        package_json = json.loads((ROOT / package["package_json"]).read_text(encoding="utf-8"))
        assert package_json["name"] == package["name"]
        assert package_json["private"] is True
        assert "version" not in package_json
        assert package_json["publishConfig"] == {"access": "public"}
        assert package_json["license"] == "MIT"
        assert "LICENSE" in package_json["files"]
        assert package_json["engines"]["node"] == ">=20"
        assert package["runtime_requirement"] == "node>=20"
        assert package["release_policy"] == "coordinated-public-registry"
        assert package["registry_status"] == "trusted-publication-required"

    lifecycle = (ROOT / "src/tooling/release/release_lifecycle.py").read_text()
    assert 'package.get("release_policy") != "coordinated-public-registry"' in lifecycle


@pytest.mark.parametrize(
    ("private", "policy", "accepted"),
    [
        (False, "coordinated-public-registry", True),
        (True, "coordinated-public-registry", False),
        (False, "release-asset-only", False),
        (True, "release-asset-only", False),
    ],
)
def test_stable_manifest_admits_only_public_registry_contract(private, policy, accepted):
    source = (ROOT / "src/tooling/release/stable_manifest.py").read_text()
    guards = [
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.If) and any(isinstance(child, ast.Constant) and child.value == "private" for child in ast.walk(node.test))
    ]
    assert len(guards) == 1
    guard = compile(ast.Module(body=guards, type_ignores=[]), "stable-manifest-guard", "exec")
    context = {"package_json": {"private": private}, "package": {"release_policy": policy, "package_json": "package.json"}}
    if accepted:
        exec(guard, context)
    else:
        with pytest.raises(SystemExit, match="coordinated public registry publication"):
            exec(guard, context)


def test_package_affecting_scope_excludes_github_automation() -> None:
    ownership = _ownership()
    paths = set(ownership["package_affecting_paths"])

    assert not any(path.startswith(".github/") for path in paths)
    assert ".release/changes/" in paths
    assert ".release/releases/" in paths
    assert "docs/release-and-versioning.md" in paths
    assert "src/" in paths
    assert "src/tooling/release/" in paths
    assert "src/" in paths
    assert "uv.lock" in paths

    assert ownership["non_semver_generated_metadata"] == []
    classify = _load_release_ownership_classifier().classify_changed_paths
    assert classify(["src/core/src/lib.rs"], ownership)["package_affecting"] is True


def test_release_path_classification_covers_native_sources_and_bindings() -> None:
    classify = _load_release_ownership_classifier().classify_changed_paths
    ownership = _ownership()
    assert classify(["docs/maintenance.md"], ownership)["package_affecting"] is False
    for path in ("src/cli/python/agentic_workspace/__init__.py", "src/cli/typescript/package.json", "src/core/src/lib.rs"):
        result = classify([path], ownership)
        assert result["package_affecting"] is True
        assert result["package_affecting_paths"] == [path]


def test_pr_semver_label_workflow_uses_release_ownership_manifest() -> None:
    workflow = (WORKFLOW_ROOT / "pr-semver-label.yml").read_text(encoding="utf-8")

    assert "pull_request:" in workflow
    assert "labeled" in workflow
    assert "unlabeled" in workflow
    assert "BASE_REF: ${{ github.event.pull_request.base.ref }}" in workflow
    assert "HEAD_REF: ${{ github.event.pull_request.head.ref }}" in workflow
    assert "BASE_REF: ${{ github.base_ref }}" not in workflow
    assert "python src/tooling/release/pr_semver_admission.py" in workflow
    workflow = (WORKFLOW_ROOT.parent.parent / "src/tooling/release/pr_semver_admission.py").read_text()
    assert ".github/release-ownership.json" in workflow
    assert "classify_changed_paths(changed, ownership)" in workflow
    assert 'ownership["semver_labels"]' in workflow
    assert "must have exactly one semver label" in workflow
    assert 'ownership["changeset_dir"]' in workflow
    assert "release changeset" in workflow
    assert "agentic-workspace/release-change/v1" in workflow


def test_master_ruleset_and_release_policy_require_merge_sufficiency_before_support_proof() -> None:
    ruleset = json.loads(RULESET_PATH.read_text(encoding="utf-8"))
    support_policy = json.loads(SUPPORT_POLICY_PATH.read_text(encoding="utf-8"))
    release = (WORKFLOW_ROOT / "release.yml").read_text(encoding="utf-8")
    status_rule = next(rule for rule in ruleset["rules"] if rule["type"] == "required_status_checks")
    contexts = [item["context"] for item in status_rule["parameters"]["required_status_checks"]]

    assert set(contexts) == {"Merge sufficiency", "Semver admission"}
    assert support_policy["required_check"] == "Merge sufficiency"
    assert support_policy["protected_branch"] == "master"
    assert "release_lifecycle.py compose" in release
    assert "support-bearing-promotion.json" in (ROOT / "src/tooling/release/release_lifecycle.py").read_text()
    assert "release-runtime-matrix:" in release
    assert "workspace-package-artifacts" not in support_policy


def test_release_notes_classify_compatibility_significant_changes() -> None:
    release_config = (ROOT / ".github" / "release.yml").read_text(encoding="utf-8")

    assert "Compatibility-significant changes" in release_config
    assert "schema" in release_config
    assert "generated-runtime" in release_config
    assert "conformance" in release_config
    assert "compatibility" in release_config


def test_release_model_ignores_tags_from_other_package_domains(monkeypatch) -> None:
    spec = importlib.util.spec_from_file_location(
        "coordinated_release_under_test",
        ROOT / "src" / "tooling" / "release" / "coordinated_release.py",
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    def fake_run(args: list[str], *, check: bool = True):
        if args[:4] == ["git", "tag", "--list", "v[0-9]*.[0-9]*.[0-9]*"]:
            return subprocess.CompletedProcess(args, 0, stdout="v0.36.1\nv2.0.0\n", stderr="")
        if args[:4] == ["git", "rev-list", "-n", "1"] and args[4] == "v0.36.1":
            return subprocess.CompletedProcess(args, 0, stdout="aw-release\n", stderr="")
        if args[:4] == ["git", "rev-list", "-n", "1"] and args[4] == "v2.0.0":
            return subprocess.CompletedProcess(args, 0, stdout="cg-release\n", stderr="")
        if args == ["git", "show", "cg-release:pyproject.toml"]:
            return subprocess.CompletedProcess(
                args,
                0,
                stdout='[project]\nname = "command-generation"\nversion = "2.0.0"\n',
                stderr="",
            )
        if args[0:2] == ["git", "show"] and args[2].startswith("aw-release:"):
            if args[2].endswith("package.json"):
                return subprocess.CompletedProcess(args, 0, stdout='{"version": "0.36.1"}', stderr="")
            package_name = "agentic-workspace"
            if "packages/memory" in args[2]:
                package_name = "agentic-workspace-memory"
            elif "packages/planning" in args[2]:
                package_name = "agentic-workspace-planning"
            elif "packages/verification" in args[2]:
                package_name = "agentic-workspace-verification"
            return subprocess.CompletedProcess(
                args,
                0,
                stdout=f'[project]\nname = "{package_name}"\nversion = "0.36.1"\n',
                stderr="",
            )
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="missing")

    monkeypatch.setattr(module, "_run", fake_run)

    assert [str(version) for version in module.existing_release_versions(_ownership())] == ["0.36.1"]
