"""Closed source admission and consequential current command selection."""

from __future__ import annotations

from pathlib import Path

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli


def test_verification_declaration_admission_and_selected_context(tmp_path, shared_core_binary, native_cli):
    source = tmp_path / ".agentic-workspace/verification/manifest.toml"
    source.parent.mkdir(parents=True)
    valid = """schema_version="agentic-workspace/verification-manifest/v1"
[protocols.bounded]
applies_to_paths=["src/**"]
commands=["echo current"]
purpose="Check the changed boundary"
review_owner="independent owner"
scenario_refs=["observation"]
[scenarios.observation]
protocol_id="bounded"
expected_observations=["The intended boundary survives"]
[assurance.proof_profiles.focused]
required_commands=["echo required"]
optional_commands=["echo optional"]
disallowed_commands=["echo denied"]
[assurance.requirements.current]
level="high"
force="required-before-closeout"
applies_to_paths=["src/**"]
proof_profile="focused"
"""
    context = {"target": str(tmp_path), "task": "Check bounded work", "changed": ["src/a.rs"]}

    def call(**extra):
        return consume("native", shared_core_binary, native_cli, {**context, **extra})

    source.write_text(valid)
    first = call()["verification"]
    assert any(row["arguments"]["command"] == "echo current" for row in first["execution_requests"])
    assert first["strategy"]["protocols"]["bounded"]["purpose"] == "Check the changed boundary"
    assert first["strategy"]["scenarios"]["observation"]["expected_observations"] == ["The intended boundary survives"]
    assert first["strategy_control"]["obligations"][0]["required_commands"] == ["echo required"]
    source.write_text(valid.replace('required_commands=["echo required"]', 'required_commands=["echo second"]'))
    assert call()["verification"]["strategy_control"]["obligations"][0]["required_commands"] == ["echo second"]
    assert call(changed=["unrelated.txt"])["verification"]["execution_requests"] == []
    for invalid, reason in [
        (valid.replace('commands=["echo current"]', 'commmands=["echo current"]'), "invalid Verification declaration"),
        (valid.replace('scenario_refs=["observation"]', 'scenario_refs=["missing"]'), "missing declaration"),
        (valid.replace('proof_profile="focused"', 'proof_profile="missing"'), "missing profile"),
        (valid.replace('disallowed_commands=["echo denied"]', 'disallowed_commands=["echo required"]'), "contradictory command roles"),
    ]:
        source.write_text(invalid)
        with pytest.raises(AssertionError, match=reason):
            call()
    source.write_text(valid.replace('applies_to_paths=["src/**"]', 'applies_to_task_markers=["semantic boundary"]'))
    unresolved = call()
    assert any("protocol-semantic-scope-requires-owner-judgment" in gap for gap in unresolved["verification"]["evidence_gaps"])
    assert unresolved["decision_packet"]["claim_boundary"]["allowed"] == []
    assert not (tmp_path / ".agentic-workspace/local").exists()


def test_repository_proof_commands_resolve_current_source_tools() -> None:
    import shlex
    import tomllib

    root = Path(__file__).resolve().parents[1]
    manifest = tomllib.loads((root / ".agentic-workspace/verification/manifest.toml").read_text(encoding="utf-8"))

    def commands(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "commands":
                    yield from child
                else:
                    yield from commands(child)
        elif isinstance(value, list):
            for child in value:
                yield from commands(child)

    for command in commands(manifest):
        for token in shlex.split(command):
            if "/" in token and token.endswith((".py", ".mjs")):
                assert (root / token).is_file(), f"Declared proof command names a missing source: {command}"
