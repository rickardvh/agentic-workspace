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
    assert ownership["canonical_version_source"] == "pyproject.toml"
    assert ownership["changeset_dir"] == ".release/changes"
    assert ownership["release_notes_dir"] == ".release/releases"
    assert ownership["release_pr_branch"] == "automation/coordinated-release"
    assert ownership["publisher"]["trigger"] == "existing-tag-only"
    assert ownership["semver_labels"] == ["semver:major", "semver:minor", "semver:patch"]
    assert "every AW coordinated-release vMAJOR.MINOR.PATCH tag" in ownership["version_floor_rule"]
    assert "other package domains do not set the AW release floor" in ownership["version_floor_rule"]

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

    assert [entry["path"] for entry in ownership["non_semver_generated_metadata"]] == ["src/tooling/contracts/support_bearing_install.json"]
    classify = _load_release_ownership_classifier().classify_changed_paths
    projection = "src/tooling/contracts/support_bearing_install.json"
    assert classify([projection], ownership)["package_affecting"] is False
    assert classify([projection], ownership)["integrity_metadata_paths"] == [projection]
    assert classify([projection, "src/core/src/lib.rs"], ownership)["package_affecting"] is True


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
    assert 'ownership["release_pr_branch"]' in workflow
    assert "release changeset" in workflow
    assert "agentic-workspace/release-change/v1" in workflow
    assert 'coordinated_release.py", "verify' in workflow


def test_master_release_workflow_prepares_release_pr_and_only_tags_verified_release_commit() -> None:
    import yaml

    workflow = yaml.load((WORKFLOW_ROOT / "release.yml").read_text(), Loader=yaml.BaseLoader)
    jobs = workflow["jobs"]
    prepare_id, prepare = next((key, job) for key, job in jobs.items() if "coordinated_release.py prepare" in str(job))
    qualification = jobs[prepare["needs"]]
    assert qualification["uses"].endswith("/ci.yml")
    assert qualification["with"]["expected_head_sha"] == "$" + "{{ github.sha }}"
    assert "always()" not in prepare["if"]
    assert prepare["permissions"]["contents"] == "write"
    commands = "\n".join(step.get("run", "") for step in prepare["steps"])
    assert 'test "$GITHUB_REF" = refs/heads/master' in commands
    assert commands.index("coordinated_release.py prepare") < commands.index("coordinated_release.py verify")
    assert "coordinated_release.py tag-plan" in commands
    assert "git merge-base --is-ancestor" in commands
    assert "gh workflow run release.yml" not in commands
    admission = next(job for job in jobs.values() if "release_lifecycle.py admit" in str(job))
    assert prepare_id in admission["needs"]
    assert "source_commit" in admission["env"]["EXPECTED_SOURCE_COMMIT"]


def test_manual_release_workflow_verifies_all_package_versions_and_assets() -> None:
    import yaml

    workflow = yaml.load((WORKFLOW_ROOT / "release.yml").read_text(), Loader=yaml.BaseLoader)
    jobs = workflow["jobs"]
    assert workflow["on"]["workflow_dispatch"]["inputs"]["release_class"]["options"] == ["stable", "preview", "release-candidate"]
    assert jobs["release-runtime-matrix"]["strategy"]["matrix"] == "${{ fromJSON(needs.promotion-admission.outputs.runtimes) }}"
    assert jobs["platform-build"]["strategy"]["matrix"] == "${{ fromJSON(needs.promotion-admission.outputs.platforms) }}"
    assert jobs["agentic-workspace-package"]["needs"] == ["promotion-admission", "release-runtime-matrix", "platform-consumer"]
    steps = jobs["agentic-workspace-package"]["steps"]
    compose = next(step for step in steps if step.get("id") == "compose")
    assert 'release_lifecycle.py compose --github-output "$GITHUB_OUTPUT"' in compose["run"]
    publish = next(step for step in steps if step.get("name") == "Publish GitHub release assets")
    assert publish["with"]["files"] == "${{ steps.compose.outputs.assets }}"
    assert publish["with"]["overwrite_files"] == "false"
    assert publish["if"] == "${{ !inputs.qualify_only }}"
    assert not (WORKFLOW_ROOT / "platform-release.yml").exists()


def test_release_asset_patterns_exclude_incidental_dist_files() -> None:
    # Publication consumes only the validated checksum inventory, not a directory glob.
    workflow = (WORKFLOW_ROOT / "release.yml").read_text()
    lifecycle = (ROOT / "src/tooling/release/release_lifecycle.py").read_text()
    assert "files: ${{ steps.compose.outputs.assets }}" in workflow
    assert 'Path("dist/SHA256SUMS").read_text().splitlines()' in lifecycle
    assert "if Path(name).name != name:" in lifecycle


def test_ci_pr_path_is_merge_sufficiency_not_release_admission() -> None:
    workflow = (WORKFLOW_ROOT / "ci.yml").read_text(encoding="utf-8")
    merge = workflow.partition("  merge-sufficiency:\n")[2].partition("\n  workspace-checks:\n")[0]
    exhaustive = workflow.partition("\n  workspace-checks:\n")[2]

    assert "name: Merge proof" in merge
    assert "name: Merge sufficiency" in workflow
    assert "needs: [merge-sufficiency, security]" in workflow
    assert "github.event_name == 'push'" in merge
    assert "github.event_name == 'pull_request'" in merge
    assert "cargo check --locked --workspace --all-targets" in merge
    assert "make lint-workspace" in merge
    assert "make typecheck-nosync" in merge
    assert "test_public_read_real_repository_decision_preserves_currentness" in merge
    assert "tests/test_native_source_reconciliation.py" in merge
    assert "tests/test_native_operating_carriage.py" in merge
    assert "tests/test_native_invoke_continuation.py" in merge
    assert "tests/test_native_independent_owner.py" in merge
    assert "public_creation_then_separate_selection" in merge
    assert "Priority " not in merge
    assert "tests/test_preview_release.py" not in merge
    assert "test_current_check_releases_claim_but_preserves_same_instruction_protection" in merge
    assert "test_resource_transport_matches_native_contract" in merge
    assert "timeout-minutes: 3" in merge

    for release_only in (
        "cargo test --locked --workspace",
        "uv build --wheel --sdist",
        "make check-memory-nosync",
        "make check-planning-nosync",
        "make check-verification-nosync",
        "Runtime ${{ matrix.os }}",
        "support-bearing-promotion",
        "packed-artifact-conformance",
        "windows-latest",
        "Support-bearing promotion",
        "tests/test_workspace_cli.py tests/test_workspace_proof_generated_packages_cli.py",
    ):
        assert release_only not in merge

    assert workflow.count("if: ${{ github.event_name == 'workflow_dispatch' }}") == 2
    assert workflow.count("inputs.source_run_id == ''") == 3
    assert "if: ${{ always() && github.event_name == 'workflow_dispatch' }}" in exhaustive
    assert "name: Support-bearing promotion" in exhaustive
    assert (
        "needs: [exhaustive-admission, workspace-checks, planning-handoff-checks, independent-owner-ingress, workspace-package-artifacts, declared-runtime-matrix]"
        in exhaustive
    )
    assert "uv build --wheel --sdist --out-dir dist" in exhaustive
    assert "packed-artifact-conformance" in exhaustive
    assert "windows-latest" not in exhaustive
    assert "cargo test --locked --workspace" in exhaustive


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


def test_ci_supports_exact_head_dispatch_for_generated_release_prs() -> None:
    workflow = (WORKFLOW_ROOT / "ci.yml").read_text(encoding="utf-8")
    dispatch = workflow.partition("workflow_dispatch:\n")[2].partition("permissions:\n")[0]
    admission = workflow.partition("  exhaustive-admission:\n")[2].partition("  workspace-checks:\n")[0]

    assert "workflow_dispatch:" in workflow
    assert "expected_head_sha:" in workflow
    assert "explicitly escalated head" in workflow
    assert "reason:" in workflow
    assert "Why exhaustive proof is required for this exact head." in workflow
    assert "Verify dispatched release head" in workflow
    assert "${{ inputs.expected_head_sha }}" in workflow
    assert '"${GITHUB_SHA}" != "${EXPECTED_HEAD_SHA}"' in workflow
    assert dispatch.count("required: true") == 2
    assert "if: github.event_name == 'workflow_dispatch'" in admission
    assert "${{ inputs.reason }}" in admission
    assert "requires a non-empty reason" in admission
    assert workflow.count("if: ${{ github.event_name == 'workflow_dispatch' }}") == 2
    assert workflow.count("inputs.source_run_id == ''") == 3
    assert "if: ${{ always() && github.event_name == 'workflow_dispatch' }}" in workflow


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
    post_merge_workflow = (WORKFLOW_ROOT / "release.yml").read_text(encoding="utf-8")

    assert "release_lifecycle.py admit" in release_workflow
    assert 'manifest.get("source_commit")' in (ROOT / "src/tooling/release/stable_manifest.py").read_text()
    assert "coordinated_release.py prepare" in post_merge_workflow
    assert "coordinated_release.py tag-plan" in post_merge_workflow
    assert "gh workflow run release.yml" not in post_merge_workflow
    assert sorted(ownership["release_commit_allowed_paths"]) == [
        ".agentic-workspace/payload-provenance.json",
        ".release/changes/",
        ".release/promotions/v1.0.0.json",
        ".release/releases/",
        "Cargo.lock",
        "pyproject.toml",
        "src/cli/rust/Cargo.toml",
        "src/core/Cargo.toml",
        "tests/fixtures/native-independent-owner/Cargo.lock",
        "uv.lock",
    ]


def test_release_model_uses_existing_tags_instead_of_stale_bootstrap_floor() -> None:
    helper = (ROOT / "src" / "tooling" / "release" / "coordinated_release.py").read_text(encoding="utf-8")

    assert "existing_release_versions" in helper
    assert '"git",' in helper and '"tag",' in helper and '"--list",' in helper
    assert "floor = max([*package_versions, *tag_versions])" in helper
    assert "_tag_declares_coordinated_release_version" in helper
    assert "pending_tag_plan" in helper
    assert "first_coordinated_release" not in helper


def test_release_runtime_matrix_fetches_history_for_retained_evidence_ancestry() -> None:
    workflow = (WORKFLOW_ROOT / "release.yml").read_text(encoding="utf-8")
    runtime = workflow.partition("release-runtime-matrix:")[2].partition("agentic-workspace-package:")[0]

    assert "fetch-depth: 0" in runtime
    assert "uv run pytest tests -q" not in runtime
    assert "src/tooling/check/check_native_release_topology.py" in runtime
    assert "--native-archive-dir runtime-dist" in runtime


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
