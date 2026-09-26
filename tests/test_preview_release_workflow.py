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
        "workflow": ".github/workflows/release.yml",
        "trigger": "workflow_dispatch on master with immutable preview tag and exact artifact SHA",
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
    assert ".agentic-workspace/payload-provenance.json" in stable_allowed
    assert ".release/previews/" not in stable_allowed
    assert not any(path == "generated/" for path in preview_allowed)


def test_preview_workflow_reuses_release_authorities_without_support_bearing_admission() -> None:
    import yaml

    release = yaml.load((WORKFLOW_ROOT / "release.yml").read_text(), Loader=yaml.BaseLoader)
    jobs = release["jobs"]
    assert not (WORKFLOW_ROOT / "preview-release.yml").exists()
    assert jobs["promotion-admission"]["env"]["RELEASE_CLASS"] == "${{ inputs.release_class || 'stable' }}"
    steps = jobs["agentic-workspace-package"]["steps"]
    publish = next(step for step in steps if step.get("name") == "Publish GitHub release assets")
    assert publish["with"]["prerelease"] == "${{ needs.promotion-admission.outputs.support_bearing != 'true' }}"
    assert publish["with"]["make_latest"] == "${{ needs.promotion-admission.outputs.support_bearing == 'true' }}"
    assert publish["with"]["overwrite_files"] == "false"
    for name in ("Download exact-commit promotion receipts", "Download declared runtime receipts"):
        assert (
            next(step for step in steps if step.get("name") == name)["if"] == "needs.promotion-admission.outputs.support_bearing == 'true'"
        )


def test_preview_helper_defaults_to_fetched_reconstruction_authority() -> None:
    helper = (ROOT / "src" / "tooling" / "release" / "preview_release.py").read_text(encoding="utf-8")

    assert 'DEFAULT_RECONSTRUCTION_REF = "master"' in helper
    assert 'f"{head_ref}:{tracking_ref}"' in helper
    assert "source_commit = _resolve_commit(source_ref or fetched_reconstruction_ref)" in helper
    assert 'default="HEAD"' not in helper
    assert "--source-commit" in helper
    assert "freshly fetched master head" in helper
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


def test_release_docs_describe_preview_as_testing_not_stable_admission() -> None:
    docs = (ROOT / "docs" / "release-and-versioning.md").read_text(encoding="utf-8")

    assert "## Preview and first-stable recovery" in docs
    assert "remain non-support-bearing" in docs
    assert "preview_release.py --version <unused-version>" in docs
    assert "Recovery reuses the immutable tag and exact assets" in docs


def test_publication_admission_is_owned_by_trusted_dispatch_not_the_tag() -> None:
    import yaml

    workflow = yaml.load((WORKFLOW_ROOT / "release.yml").read_text(), Loader=yaml.BaseLoader)
    admission = workflow["jobs"]["promotion-admission"]
    assert "trusted master workflow authority" in (ROOT / "src/tooling/release/release_lifecycle.py").read_text()
    checkout = admission["steps"][0]
    assert checkout["with"]["ref"] == "${{ github.sha }}"
    assert checkout["with"]["persist-credentials"] == "false"
    gate = next(step for step in admission["steps"] if step.get("id") == "admit")
    assert 'release_lifecycle.py admit --github-output "$GITHUB_OUTPUT"' in gate["run"]
    assert not any("${{ inputs." in step.get("run", "") for step in admission["steps"])
    for name in ("release-runtime-matrix", "agentic-workspace-package", "platform-build", "platform-assemble", "platform-consumer"):
        job = workflow["jobs"][name]
        assert "promotion-admission" in job["needs"]
        assert job["steps"][0]["with"]["ref"] == "${{ needs.promotion-admission.outputs.source_commit }}"


def test_complete_existing_preview_skips_local_artifact_operations():
    import yaml

    workflow = yaml.load((WORKFLOW_ROOT / "release.yml").read_text(), Loader=yaml.BaseLoader)
    for name in ("platform-build", "release-runtime-matrix", "agentic-workspace-package"):
        assert "needs.promotion-admission.outputs.build_required == 'true'" in workflow["jobs"][name]["if"]
    assert "needs.promotion-admission.outputs.build_required == 'false'" in workflow["jobs"]["language-packages"]["if"]
