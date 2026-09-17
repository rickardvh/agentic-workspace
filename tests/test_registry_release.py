"""Release-to-registry identity and uncertain-publication recovery boundary."""

import base64
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/release"))
import registry_release as registry  # noqa: E402


@pytest.mark.parametrize("ecosystem", ["python", "npm"])
def test_registry_absence_matching_bytes_and_conflict(tmp_path, ecosystem):
    data = b"exact admitted artifact"
    path = tmp_path / ("package.whl" if ecosystem == "python" else "package.tgz")
    path.write_bytes(data)
    name = "agentic-workspace" if ecosystem == "python" else "@agentic-workspace/workspace-cli"
    artifact = {
        "ecosystem": ecosystem,
        "name": name,
        "version": "1.0.0",
        "asset": path.name,
        "sha256": hashlib.sha256(data).hexdigest(),
        "release_assets": [path.name],
    }
    if ecosystem == "python":
        metadata = {
            "info": {"name": name, "version": "1.0.0"},
            "urls": [
                {"filename": path.name, "digests": {"sha256": artifact["sha256"]}, "url": "https://files.pythonhosted.org/package.whl"}
            ],
        }
    else:
        metadata = {
            "name": name,
            "version": "1.0.0",
            "dist": {
                "integrity": "sha512-" + base64.b64encode(hashlib.sha512(data).digest()).decode(),
                "tarball": "https://registry.npmjs.org/package.tgz",
            },
        }
    assert registry.observe(artifact, tmp_path, get=lambda _: None) == "absent"
    assert registry.observe(artifact, tmp_path, get=lambda _: metadata, download=lambda _: data) == "matching"
    with pytest.raises(ValueError, match="Public registry bytes"):
        registry.observe(artifact, tmp_path, get=lambda _: metadata, download=lambda _: b"different")

    def unavailable(_):
        raise TimeoutError("uncertain transport")

    with pytest.raises(TimeoutError):
        registry.observe(artifact, tmp_path, get=unavailable)
    artifact["sha256"] = "0" * 64
    with pytest.raises(ValueError):
        registry.observe(artifact, tmp_path, get=lambda _: metadata, download=lambda _: data)


@pytest.mark.parametrize("tag", ["v1.0.0-rc.1", "v1.0.0"])
def test_registry_requires_exact_admitted_subject(tmp_path, tag):
    identity = registry.coordinated_release.release_identity(tag)
    source = "a" * 40
    packages = []
    for ecosystem, name, kinds in [
        ("python", "agentic-workspace", ["wheel", "sdist"]),
        ("npm", "@agentic-workspace/workspace-cli", ["tarball"]),
    ]:
        package = {"ecosystem": ecosystem, "name": name, "version": identity["package_versions"][ecosystem]}
        for kind in kinds:
            path = tmp_path / kind
            path.write_bytes(kind.encode())
            package[kind] = {"asset": kind, "sha256": registry.sha256(path)}
        packages.append(package)
    manifest_name = (
        "agentic-workspace-release-manifest.json" if identity["support_bearing"] else "agentic-workspace-preview-release-manifest.json"
    )
    extra = tmp_path / "windows-wheel"
    extra.write_bytes(b"windows wheel")
    packages[0]["wheels"] = [packages[0]["wheel"], {"asset": extra.name, "sha256": registry.sha256(extra)}]
    (tmp_path / manifest_name).write_text(json.dumps({**identity, "source_commit": source, "packages": packages}))
    (tmp_path / "security-supply-chain-readiness.json").write_text(json.dumps({"status": "ready", "subject": {"source_identity": source}}))
    for name in ("distribution-install-readiness.json", "redistributable-package-readiness.json"):
        (tmp_path / name).write_text("{}")
    if identity["support_bearing"]:
        (tmp_path / "support-bearing-promotion.json").write_text(json.dumps({"status": "passed", "source_commit": source}))
    (tmp_path / "SHA256SUMS").write_text("".join(f"{registry.sha256(p)}  {p.name}\n" for p in tmp_path.iterdir()))
    assert len(registry.admitted_artifacts(tmp_path, tag, source)[1]) == 4
    with pytest.raises(ValueError, match="source"):
        registry.admitted_artifacts(tmp_path, tag, "b" * 40)
    (tmp_path / "wheel").write_bytes(b"changed")
    with pytest.raises(ValueError, match="asset changed"):
        registry.admitted_artifacts(tmp_path, tag, source)


def test_registry_workflow_is_gated_projection_without_rebuild():
    workflow = (ROOT / ".github/workflows/registry-release.yml").read_text()
    assert "workflow_call:" in workflow and "workflow_dispatch:" not in workflow
    assert "pypa/gh-action-pypi-publish@" not in workflow
    import yaml

    for filename, dependency in (("preview-release.yml", "preview-package"), ("release.yml", "agentic-workspace-package")):
        publisher = yaml.safe_load((ROOT / ".github/workflows" / filename).read_text())
        job = publisher["jobs"]["language-packages"]
        assert dependency in job["needs"]
        assert "uses" not in job
        assert job["environment"] == "package-registries"
        assert job["permissions"] == {"contents": "read", "id-token": "write", "attestations": "read"}
        steps = job["steps"]
        assert any(step.get("uses", "").startswith("pypa/gh-action-pypi-publish@") for step in steps)
        names = [step.get("name") for step in steps]
        assert (
            names.index("Reobserve immutable registry versions")
            < names.index("Publish missing exact PyPI artifacts with trusted identity")
            < names.index("Verify public bytes and clean native consumers")
        )
        content = str(job)
        assert "npm@11.5.1" in content and '--tag "$NPM_TAG"' in content
        assert "uv build" not in content and "npm pack" not in content and "secrets." not in content
        assert "${{ inputs.tag }}" not in content
    with pytest.raises(ValueError, match="Exploratory"):
        registry.admitted_artifacts(Path("unused"), "preview-v0.57.0", "a" * 40)


def test_linux_wheel_tag_requires_abi_evidence(tmp_path, monkeypatch):
    import admit_linux_wheel

    monkeypatch.setattr(admit_linux_wheel.platform, "machine", lambda: "x86_64")
    wheel = tmp_path / "agentic_workspace-1.0.0-py3-none-linux_x86_64.whl"
    wheel.write_bytes(b"fixture")
    calls = []
    monkeypatch.setattr(admit_linux_wheel.subprocess, "run", lambda args, **_: calls.append(args))
    monkeypatch.setattr(admit_linux_wheel.subprocess, "check_output", lambda *a, **k: 'following platform tag:\n"manylinux_2_34_x86_64"')
    admit_linux_wheel.admit(tmp_path)
    assert len(calls) == 1 and "tags" in calls[0] and "repair" not in calls[0]
    monkeypatch.setattr(admit_linux_wheel.subprocess, "check_output", lambda *a, **k: 'following platform tag:\n"manylinux_2_40_x86_64"')
    with pytest.raises(ValueError, match="ABI"):
        admit_linux_wheel.admit(tmp_path)
    assert len(calls) == 1
