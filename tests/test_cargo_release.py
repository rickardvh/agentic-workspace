"""Cargo source closure and immutable coordinated registry identity."""

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/release"))
import cargo_release as cargo  # noqa: E402


def test_cargo_projection_preserves_inputs_and_source_identity(tmp_path, monkeypatch):
    origin = tmp_path / "crates/example"
    (origin / "src").mkdir(parents=True)
    (origin / "Cargo.toml").write_text('[package]\nname="example"\nversion="1.0.0"\n[lints]\nworkspace = true\n')
    source = 'const OWN: &str = include_str!("main.rs");\nconst POLICY: &str = include_str!("../../../policy.json");\n'
    (origin / "src/main.rs").write_bytes(source.encode())
    (tmp_path / "policy.json").write_bytes(b'{"exact": "bytes"}\r\n')
    (tmp_path / "Cargo.lock").write_text('version=4\n[[package]]\nname="example"\nversion="1.0.0"\n')
    for name in ("README.md", "LICENSE"):
        (tmp_path / name).write_text(name)
    monkeypatch.setattr(cargo.subprocess, "run", lambda *a, **k: None)
    destination = tmp_path / "staged"
    cargo.stage_crate(tmp_path, {"path": "crates/example", "name": "example"}, destination, "a" * 40)
    assert (destination / "README.md").read_bytes() == (tmp_path / "README.md").read_bytes()
    transformed = (destination / "src/main.rs").read_text()
    assert 'include_str!("../_inputs/crates/example/src/main.rs")' in transformed
    assert (destination / "_inputs/crates/example/src/main.rs").read_bytes() == source.encode()
    assert (destination / "_inputs/policy.json").read_bytes() == (tmp_path / "policy.json").read_bytes()
    manifest = (destination / "Cargo.toml").read_text()
    assert "[workspace]" in manifest and '"_inputs/policy.json"' in manifest
    provenance = json.loads((destination / "release-source.json").read_text())
    assert provenance["compile_inputs"]["policy.json"] == cargo.sha256(tmp_path / "policy.json")


def test_cargo_projection_carries_declared_portable_build_inputs(tmp_path, monkeypatch):
    """The standalone build must retain the same closed derivation inputs."""
    monkeypatch.setattr(cargo.subprocess, "run", lambda *a, **k: None)
    destination = tmp_path / "staged"
    cargo.stage_crate(ROOT, {"path": "src/core", "name": "agentic-workspace-core"}, destination, "a" * 40)
    contract = json.loads((ROOT / "src/core/contracts/workspace_surfaces.json").read_text())
    provenance = json.loads((destination / "release-source.json").read_text())
    assert not any("/skills/" in path and path.endswith(".py") for path in provenance["compile_inputs"])
    for module in ("memory", "planning", "verification"):
        projection = ROOT / "generated" / module / "typescript"
        assert not list(projection.rglob("*.py")), f"{module} acquired an undeclared Python runtime"
    references = list(contract["derivation"]["portable_sources"])
    for reference in references:
        assert (destination / "_inputs" / reference).read_bytes() == (ROOT / reference).read_bytes()
        assert provenance["compile_inputs"][reference] == cargo.sha256(ROOT / reference)


def test_cargo_registry_recovery_distinguishes_absence_conflict_and_uncertainty():
    data = b"immutable crate source"
    crate = {"name": "agentic-workspace-core", "version": "1.0.0-rc.1", "sha256": hashlib.sha256(data).hexdigest()}
    metadata = {"version": {"crate": crate["name"], "num": crate["version"], "checksum": crate["sha256"], "yanked": False}}
    assert cargo.observe(crate, get=lambda _: None) == "absent"
    assert cargo.observe(crate, get=lambda _: metadata, download=lambda _: data) == "matching"
    with pytest.raises(ValueError, match="Public crate bytes"):
        cargo.observe(crate, get=lambda _: metadata, download=lambda _: b"changed")
    metadata["version"]["yanked"] = True
    with pytest.raises(ValueError, match="conflict"):
        cargo.observe(crate, get=lambda _: metadata)

    def unavailable(_):
        raise TimeoutError("no absence evidence")

    with pytest.raises(TimeoutError):
        cargo.observe(crate, get=unavailable)


@pytest.mark.parametrize("scenario", ["fresh", "partial", "conflict", "uncertain", "repack-drift"])
def test_cargo_publication_orders_exact_pair_and_stops_before_unsafe_effects(tmp_path, monkeypatch, scenario):
    import registry_release

    packages = []
    staging = tmp_path / "stage"
    for name, binary in (("agentic-workspace-core", "agentic-workspace-core"), ("agentic-workspace-cli", "agentic-workspace")):
        asset = f"{name}-1.0.0-rc.1.crate"
        data = name.encode()
        (tmp_path / asset).write_bytes(data)
        packaged = staging / name / "target/package"
        packaged.mkdir(parents=True)
        (packaged / asset).write_bytes(b"changed" if scenario == "repack-drift" else data)
        packages.append(
            {"name": name, "binary": binary, "version": "1.0.0-rc.1", "asset": asset, "sha256": hashlib.sha256(data).hexdigest()}
        )
    (tmp_path / "cargo-release-manifest.json").write_text(
        json.dumps(
            {
                "source_commit": "a" * 40,
                "version": "1.0.0-rc.1",
                "package_build": "passed",
                "paired_install": "passed",
                "packages": packages,
            }
        )
    )
    monkeypatch.setattr(cargo.coordinated_release, "load_ownership", lambda: {"cargo_packages": packages})
    monkeypatch.setattr(cargo.subprocess, "check_output", lambda *a, **k: "a" * 40)
    monkeypatch.setattr(
        registry_release, "admitted_artifacts", lambda *a: ({"version": "1.0.0rc1", "package_versions": {"cargo": "1.0.0-rc.1"}}, [])
    )
    monkeypatch.delenv("CARGO_TARGET_DIR", raising=False)
    monkeypatch.setattr(
        sys, "argv", ["cargo_release", "publish", "--artifact-dir", str(tmp_path), "--staging", str(staging), "--tag", "v1.0.0-rc.1"]
    )
    published = {packages[0]["name"]} if scenario == "partial" else set()
    uploads, observations = [], []

    def observe(crate):
        name = crate["name"]
        observations.append(name)
        if scenario == "conflict" and name == packages[1]["name"]:
            raise ValueError("Immutable conflict")
        if scenario == "uncertain" and uploads:
            raise TimeoutError("Unknown publication visibility")
        return "matching" if name in published else "absent"

    def execute(command, **kwargs):
        if command[1] == "publish":
            name = Path(command[-1]).parent.name
            assert observations[:2] == [p["name"] for p in packages]
            if name == packages[1]["name"]:
                assert packages[0]["name"] in published
            uploads.append(name)
            published.add(name)

    monkeypatch.setattr(cargo, "observe", observe)
    monkeypatch.setattr(cargo.subprocess, "run", execute)
    if scenario in {"conflict", "repack-drift"}:
        with pytest.raises(ValueError):
            cargo.main()
        assert uploads == []
    elif scenario == "uncertain":
        with pytest.raises(TimeoutError):
            cargo.main()
        assert uploads == [packages[0]["name"]]
    else:
        cargo.main()
        assert uploads == [p["name"] for p in packages[1 if scenario == "partial" else 0 :]]
