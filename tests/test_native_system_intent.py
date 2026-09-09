"""Governing-source reads preserve source authority without granting alignment."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from tests.test_native_public_cli import ROOT, consume
from tests.test_native_public_cli import native_cli as native_cli

MIRROR = ".agentic-workspace/system-intent/intent.toml"


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_real_governing_sources_are_lazy_exact_and_not_alignment(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_text('schema_version=1\n[system_intent]\nsources=["SYSTEM_INTENT.md","README.md"]\npreferred_source="SYSTEM_INTENT.md"\n')
    for reference in ("SYSTEM_INTENT.md", "README.md", MIRROR):
        path = tmp_path / reference
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / reference).read_bytes())
    context = {"target": str(tmp_path), "task": "Inspect current intent"}
    result = consume(surface, shared_core_binary, native_cli, context)
    owner = result["system_intent"]
    assert owner["preferred_source"] == "SYSTEM_INTENT.md"
    assert owner["interpretation"]["status"] == "retained"
    assert owner["interpretation"]["alignment"] == "unresolved-owner-judgment"
    assert len(json.dumps(owner)) < 16000
    assert "governing_intents =" not in json.dumps(owner)
    assert not any(r["field"].startswith("system_intent.") for r in result["configuration"]["residuals"])
    request = next(r for r in owner["requests"] if r["arguments"]["reference"] == MIRROR)
    read = consume(surface, shared_core_binary, native_cli, {**context, "request": request})["system_intent"]["response"]
    assert read["text"] == (tmp_path / MIRROR).read_bytes().decode("utf-8")
    assert "governing_intents" in read["text"]
    assert "grants no alignment" in read["authority_boundary"]
    for projection in ("compact", "carried"):
        delivered = consume(surface, shared_core_binary, native_cli, {**context, "request": request, "projection": projection})
        visible = delivered["view"] if projection == "carried" else delivered
        assert visible["decision_packet"]["material"]["system-intent"] == read
    with pytest.raises(AssertionError):
        consume(surface, shared_core_binary, native_cli, {**context, "task": "A different task", "request": request})
    forged = json.loads(json.dumps(request))
    forged["arguments"]["reference"] = "secret.txt"
    with pytest.raises(AssertionError, match="outside current declared"):
        consume(surface, shared_core_binary, native_cli, {**context, "request": forged})
    original_config = config.read_bytes()
    config.write_text(config.read_text().replace('preferred_source="SYSTEM_INTENT.md"', 'preferred_source="README.md"'))
    with pytest.raises(AssertionError, match="stale"):
        consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    config.write_bytes(original_config)
    with (tmp_path / "SYSTEM_INTENT.md").open("ab") as f:
        f.write(b"\nChanged governing source\n")
    with pytest.raises(AssertionError, match="stale"):
        consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    current = consume(surface, shared_core_binary, native_cli, context)["system_intent"]
    assert "retained-interpretation-source-currentness-unproven" in current["gaps"]
    assert not (tmp_path / ".agentic-workspace/local").exists()


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_governing_source_absence_is_quiet_and_missing_declaration_is_not_waived(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    (tmp_path / "README.md").write_text("Unrelated generic repository prose")
    context = {"target": str(tmp_path), "task": "Describe the repository"}
    quiet = consume(surface, shared_core_binary, native_cli, context)
    assert quiet["system_intent"]["status"] == "absent"
    assert quiet["system_intent"]["requests"] == []
    assert quiet["decision_packet"]["status"] == "direct"
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_text('schema_version=1\n[system_intent]\nsources=["missing.md"]\npreferred_source="missing.md"\n')
    blocked = consume(surface, shared_core_binary, native_cli, context)
    assert blocked["system_intent"]["gaps"] == ["governing-source-unavailable:missing.md"]
    assert blocked["decision_packet"]["blockers"]
    assert not (tmp_path / MIRROR).exists()


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
@pytest.mark.parametrize("condition", ["unreviewed", "invalid"])
def test_existing_interpretation_uncertainty_is_preserved(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str, condition: str
) -> None:
    mirror = tmp_path / MIRROR
    mirror.parent.mkdir(parents=True)
    text = (ROOT / MIRROR).read_text(encoding="utf-8")
    text = text.replace("needs_review = false", "needs_review = true") if condition == "unreviewed" else "unparseable retained authority"
    mirror.write_text(text, encoding="utf-8")
    context = {"target": str(tmp_path), "task": "Inspect retained intent"}
    result = consume(surface, shared_core_binary, native_cli, context)
    gap = "retained-interpretation-review-unresolved" if condition == "unreviewed" else "retained-interpretation-invalid-or-unavailable"
    assert gap in result["system_intent"]["gaps"]
    assert result["decision_packet"]["blockers"]
    assert mirror.read_text(encoding="utf-8") == text
    request = result["system_intent"]["requests"][0]
    read = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    assert read["system_intent"]["response"]["text"] == mirror.read_bytes().decode("utf-8")
    assert read["system_intent"]["gaps"] == result["system_intent"]["gaps"]
    with pytest.raises(AssertionError, match="one current request"):
        consume(surface, shared_core_binary, native_cli, {**context, "request": [request, request]})
