"""Controlled source/candidate/publication journeys and immutable recovery."""

import hashlib
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


@pytest.mark.parametrize("interruption", ["before-tag", "after-tag", "after-asset", None])
def test_publication_resumes_retained_bytes_without_replacing_assets(tmp_path, monkeypatch, interruption):
    """Controlled GitHub endpoint state persists across an interrupted publisher."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(lifecycle, "ROOT", tmp_path)
    monkeypatch.setenv("GITHUB_RUN_ID", "123")
    dist = tmp_path / "dist"
    dist.mkdir()
    identity = {"source_commit": "a" * 40, "tag": "v1.9.0", "version": "1.9.0", "legacy": True}
    for name, content in (("package.whl", b"admitted bytes"), ("release-notes.md", b"release notes")):
        (dist / name).write_bytes(content)
    (dist / "SHA256SUMS").write_text(
        "".join(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n" for path in sorted(dist.iterdir()))
    )
    monkeypatch.setattr(lifecycle.registry_release, "admitted_artifacts", lambda *args: (identity, []))
    monkeypatch.setattr(
        lifecycle, "observe_stable", lambda _: ({"source_commit": "b" * 40, "tag": "v1.8.0", "version": "1.8.0"}, ["1.8.0"], [])
    )
    monkeypatch.setattr(lifecycle.coordinated_release, "load_ownership", lambda: {})
    monkeypatch.setattr(lifecycle.coordinated_release, "select_release", lambda *args, **kwargs: identity)
    state = {"tag": None, "release": None, "assets": {}, "uploads": [], "fault": interruption}

    def stop(point):
        if state["fault"] == point:
            state["fault"] = None
            raise TimeoutError(point)

    def git(*args):
        if "tag" in args:
            state["annotation"] = json.loads(args[-1])
        elif args[0] == "push":
            stop("before-tag")
            state["tag"] = identity["source_commit"]
            stop("after-tag")
        return ""

    def api(repository, endpoint):
        if endpoint.startswith("commits/"):
            return {"sha": state["tag"]}
        if endpoint.startswith("git/tags/"):
            return {"message": json.dumps(state["annotation"])}
        if endpoint.startswith("releases/tags/"):
            return {**state["release"], "assets": [{"name": name, "browser_download_url": name} for name in state["assets"]]}
        raise AssertionError(endpoint)

    def request(command, **kwargs):
        endpoint = command[-1]
        if "/git/ref/tags/" in endpoint:
            value = {"object": {"type": "tag", "sha": "tag-object"}} if state["tag"] else None
        elif "/releases/tags/" in endpoint:
            value = api("repo", "releases/tags/" + identity["tag"]) if state["release"] else None
        else:
            raise AssertionError(command)
        return subprocess.CompletedProcess(command, 0 if value else 1, json.dumps(value), "" if value else "HTTP 404")

    def effect(*command):
        if command[:3] == ("gh", "release", "create"):
            state["release"] = {"tag_name": identity["tag"], "draft": False, "prerelease": False}
        elif command[:3] == ("gh", "release", "upload"):
            path = Path(command[4])
            assert path.name not in state["assets"]
            state["assets"][path.name] = path.read_bytes()
            state["uploads"].append(path.name)
            stop("after-asset")
        elif command != ("gh", "auth", "setup-git"):
            raise AssertionError(command)

    monkeypatch.setattr(lifecycle, "git", git)
    monkeypatch.setattr(lifecycle, "api", api)
    monkeypatch.setattr(lifecycle.subprocess, "run", request)
    monkeypatch.setattr(lifecycle, "run", effect)
    monkeypatch.setattr(lifecycle.registry_release, "fetch", lambda url: state["assets"][url])
    if interruption:
        with pytest.raises(TimeoutError):
            lifecycle.publish_github("repo", identity)
    lifecycle.publish_github("repo", identity)
    lifecycle.publish_github("repo", identity)
    assert len(state["uploads"]) == 3
    assert state["assets"]["package.whl"] == b"admitted bytes"
    state["assets"]["package.whl"] = b"conflicting public bytes"
    with pytest.raises(ValueError, match="conflict"):
        lifecycle.publish_github("repo", identity)
    (dist / "package.whl").unlink()
    with pytest.raises(FileNotFoundError):
        lifecycle.publish_github("repo", identity)


def test_recovery_fails_when_original_artifact_is_expired(monkeypatch, tmp_path):
    monkeypatch.setattr(lifecycle, "api", lambda *args: {"artifacts": [{"name": lifecycle.BUNDLE_NAME, "expired": True}]})
    with pytest.raises(ValueError, match="Recovery gap"):
        lifecycle.download_run_artifact("repo", 12, lifecycle.BUNDLE_NAME, tmp_path)


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
