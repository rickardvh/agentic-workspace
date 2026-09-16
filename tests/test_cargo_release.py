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
    transformed = (destination / "src/main.rs").read_text()
    assert 'include_str!("../_inputs/crates/example/src/main.rs")' in transformed
    assert (destination / "_inputs/crates/example/src/main.rs").read_bytes() == source.encode()
    assert (destination / "_inputs/policy.json").read_bytes() == (tmp_path / "policy.json").read_bytes()
    manifest = (destination / "Cargo.toml").read_text()
    assert "[workspace]" in manifest and '"_inputs/policy.json"' in manifest
    provenance = json.loads((destination / "release-source.json").read_text())
    assert provenance["compile_inputs"]["policy.json"] == cargo.sha256(tmp_path / "policy.json")


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
