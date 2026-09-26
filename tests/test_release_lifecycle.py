"""Controlled source/candidate/publication journeys and immutable recovery."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/tooling/release"))
import registry_release as registry  # noqa: E402
import release_lifecycle as lifecycle  # noqa: E402


@pytest.mark.parametrize(
    "tag,release_class,support,registries",
    [
        ("preview-v0.99.0", "preview", False, False),
        ("v1.0.0-rc.3", "release-candidate", False, True),
        ("v1.9.0", "stable", True, True),
    ],
)
def test_release_model_keeps_class_and_support_explicit(tag, release_class, support, registries):
    model = lifecycle.release_model(tag, release_class)
    assert model["support_bearing"] is support
    assert model["registries"] is registries
    with pytest.raises(ValueError, match="class"):
        lifecycle.release_model(tag, "preview" if release_class == "stable" else "stable")


def test_publish_dispatch_still_requires_exact_source_after_preparation_inputs_became_optional(monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    monkeypatch.setenv("GITHUB_REF", "refs/heads/master")
    with pytest.raises(ValueError, match="exact source"):
        lifecycle.admit("v1.9.0", "", "stable", "owner/repo")


@pytest.mark.parametrize("outcomes,passes", [(["matching"], True), (["absent", "matching"], True), (["absent"] * 8, False)])
def test_registry_convergence_is_bounded_and_reobserves(outcomes, passes):
    now = [0]
    observations = iter(outcomes)
    sleeps = []

    def sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    def execute():
        return registry.converge(
            [{"asset": "immutable.whl"}],
            Path("unused"),
            timeout=6,
            observe_artifact=lambda *_: next(observations),
            clock=lambda: now[0],
            sleep=sleep,
        )

    if passes:
        assert execute()[0]["status"] == "matching"
    else:
        with pytest.raises(ValueError, match="timed out"):
            execute()
        assert now[0] == 6
    assert sum(sleeps) <= 6


def test_registry_conflict_is_never_retried_and_channel_wait_does_not_republish():
    def conflict(*_):
        raise ValueError("immutable digest conflict")

    sleeps = []
    with pytest.raises(ValueError, match="digest conflict"):
        registry.converge([{"asset": "x"}], Path("unused"), observe_artifact=conflict, sleep=sleeps.append)
    assert sleeps == []
    channel = iter([False, True])
    result = registry.converge(
        [{"asset": "x"}], Path("unused"), observe_artifact=lambda *_: "matching", channel_ready=lambda: next(channel), sleep=sleeps.append
    )
    assert result[0]["status"] == "matching" and sleeps == [2]


@pytest.mark.parametrize("producer", ["release", "ci"])
@pytest.mark.parametrize("defect", [None, "source-proof", "normalization", "missing-claim", "wrong-subject"])
def test_candidate_requires_source_evidence_and_exact_normalization(monkeypatch, defect, producer):
    source = "a" * 40

    def api(_repository, endpoint):
        if "/jobs?" in endpoint:
            return {
                "jobs": [
                    {"name": ("source-qualification / " if producer == "release" else "") + name, "conclusion": "success"}
                    for name in lifecycle.SOURCE_CLAIMS
                    if defect != "missing-claim" or name != "workspace-checks"
                ]
            }
        return {
            "head_sha": "c" * 40 if defect == "wrong-subject" else source,
            "conclusion": "failure" if defect == "source-proof" else (None if producer == "release" else "success"),
            "path": f".github/workflows/{producer}.yml",
            "status": "in_progress" if producer == "release" else "completed",
            "head_branch": "master",
            "event": "workflow_dispatch",
            "display_title": f"CI / release-source-{source}-nonce",
            "head_repository": {"full_name": "owner/repo"},
        }

    monkeypatch.setattr(lifecycle, "api", api)
    monkeypatch.setattr(lifecycle, "git", lambda *_: "b" * 40)
    monkeypatch.setattr(lifecycle.coordinated_release, "load_ownership", lambda: {})
    monkeypatch.setattr(lifecycle.coordinated_release, "verify_workspace_versions", lambda _: {"version": "1.9.0", "tag": "v1.9.0"})
    normalized = []

    def normalization(_ownership, **kwargs):
        normalized.append(kwargs)
        if defect == "normalization":
            raise SystemExit("Non-version release normalization delta")

    monkeypatch.setattr(lifecycle.coordinated_release, "verify_normalization_delta", normalization)
    if defect:
        with pytest.raises((ValueError, SystemExit)):
            lifecycle.candidate_admission("owner/repo", source, "7")
    else:
        lifecycle.candidate_admission("owner/repo", source, "7")
        assert normalized[0]["source"] == source and normalized[0]["consume_changesets"] is True
    if defect == "source-proof":
        assert normalized == []


@pytest.mark.parametrize("release_class,tag", [("stable", "v1.9.0"), ("preview", "preview-v0.99.0"), ("release-candidate", "v1.0.0-rc.3")])
def test_shared_composition_keeps_required_evidence_and_support_distinctions(tmp_path, monkeypatch, release_class, tag):
    monkeypatch.chdir(tmp_path)
    calls = []
    monkeypatch.setattr(lifecycle, "operation", lambda *args: calls.append(args))
    monkeypatch.setattr(lifecycle, "git", lambda *_: "a" * 40)
    monkeypatch.setattr(lifecycle.coordinated_release, "load_ownership", lambda: {"semantic_conformance": {"runtime_majors": [20, 24, 25]}})
    lifecycle.compose(tag, release_class)
    assert sum(call[0] == "check/check_native_release_topology.py" for call in calls) == 3
    assert any(call[0] == "check/check_security_supply_chain.py" for call in calls)
    assert any(call[:2] == ("release/platform_release.py", "extend") for call in calls)
    assert any(call[0] == "release/support_bearing_promotion.py" for call in calls) is (release_class == "stable")
    assert any(call[0] == "release/preview_manifest.py" for call in calls) is (release_class != "stable")
    if release_class != "stable":
        (tmp_path / "dist").mkdir()
        (tmp_path / "dist/support-bearing-promotion.json").write_text("{}")
        with pytest.raises(ValueError, match="cannot carry"):
            lifecycle.compose(tag, release_class)


def test_immutable_recovery_reuses_matching_assets_and_rejects_conflicts(tmp_path, monkeypatch):
    release = {"tag_name": "v1.9.0", "prerelease": False, "draft": False, "assets": [{"name": "package.whl"}]}
    monkeypatch.setattr(lifecycle.subprocess, "run", lambda *a, **kw: subprocess.CompletedProcess(a, 0, json.dumps(release), ""))
    package = b"admitted package"
    import hashlib

    def download(*args):
        directory = Path(args[-1])
        manifest = directory / "agentic-workspace-release-manifest.json"
        manifest.write_text(json.dumps({"tag": "v1.9.0", "source_commit": "a" * 40}))
        (directory / "package.whl").write_bytes(package)
        (directory / "SHA256SUMS").write_text(f"{hashlib.sha256(package).hexdigest()}  package.whl\n")

    monkeypatch.setattr(lifecycle, "run", download)
    admitted = []
    monkeypatch.setattr(lifecycle.stable_manifest, "verify", lambda dist: admitted.append(dist))
    monkeypatch.setattr(lifecycle.registry_release, "admitted_artifacts", lambda *args: admitted.append(args))
    assert lifecycle.inspect_publication("v1.9.0", "a" * 40, "stable", "owner/repo") is True
    assert len(admitted) == 2
    with pytest.raises(ValueError, match="immutable release asset differs"):
        lifecycle.inspect_publication("v1.9.0", "a" * 40, "stable", "owner/repo", tmp_path)


def test_publication_and_maintenance_have_separate_verdicts():
    release = yaml.load((ROOT / ".github/workflows/release.yml").read_text(), Loader=yaml.BaseLoader)
    assert "public-consumers" not in release["jobs"] and "current-install-projection" not in release["jobs"]
    for name in ("language-packages", "language-registries"):
        assert "!inputs.qualify_only" in release["jobs"][name]["if"]
    maintenance = yaml.load((ROOT / ".github/workflows/maintenance.yml").read_text(), Loader=yaml.BaseLoader)
    assert maintenance["on"]["workflow_run"]["workflows"] == ["Release"]
