"""Retained selectors may create absent carriers, never infer overwrite custody."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from repo_planning_bootstrap import installer
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli

ROOT = Path(__file__).resolve().parents[1]
SELECTION = Path(".agentic-workspace/local/planning/owner-selection.json")
RECEIPT = SELECTION.with_name("owner-selection-receipt.json")


def owner(root: Path) -> None:
    installer.install_bootstrap(target=root)
    result = installer.create_execplan_scaffold(plan_id="existing-owner", title="Existing owner", target=root)
    assert not [a for a in result.actions if a.kind == "manual review"]


def select(surface: str, root: Path, **options: str) -> dict:
    if surface == "python":
        from generated.planning.python.commands.planning_owner_select_lifecycle import invoke

        return invoke({"owner": "existing-owner", "target": str(root), **options}).to_dict()
    node = shutil.which("node")
    assert node
    args = [
        node,
        str(ROOT / "generated/planning/typescript/src/cli.mjs"),
        "owner-select",
        "--owner",
        "existing-owner",
        "--target",
        str(root),
        "--format",
        "json",
    ]
    for key, value in options.items():
        args += ["--" + key.replace("_", "-"), value]
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert result.stdout, result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize("surface", ["python", "typescript"])
@pytest.mark.parametrize("carrier", [SELECTION, RECEIPT])
@pytest.mark.parametrize(
    "content", [b"not JSON: owned elsewhere", b'{"kind":"agentic-planning/owner-selection/v1","selected_owner":{"id":"other"}}']
)
def test_unretained_carrier_is_preserved(surface: str, carrier: Path, content: bytes, tmp_path: Path) -> None:
    owner(tmp_path)
    path = tmp_path / carrier
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    result = select(surface, tmp_path)
    assert result["reason_code"] == "owner-selection-acquisition-required", result
    assert result["mutation_applied"] is False
    assert "transfer" in str(result["actions"])
    assert path.read_bytes() == content
    peer = RECEIPT if carrier == SELECTION else SELECTION
    assert not (tmp_path / peer).exists()


@pytest.mark.parametrize("surface", ["python", "typescript"])
def test_absent_creation_exact_noop_and_nonnoop_preservation(surface: str, tmp_path: Path) -> None:
    owner(tmp_path)
    created = select(surface, tmp_path)
    assert created["operation_receipt"]["outcome"] == "selected", created
    before = {p: (tmp_path / p).read_bytes() for p in (SELECTION, RECEIPT)}
    same = select(surface, tmp_path)
    assert same["operation_receipt"]["outcome"] == "no-op"
    changed = select(surface, tmp_path, reason="Different reason is not overwrite authority")
    assert changed["reason_code"] == "owner-selection-acquisition-required"
    assert before == {p: (tmp_path / p).read_bytes() for p in before}


@pytest.mark.parametrize("carrier", [SELECTION, RECEIPT])
def test_exclusive_acquisition_race_never_rolls_back_winner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, carrier: Path) -> None:
    owner(tmp_path)
    original = Path.open
    winner = tmp_path / carrier
    payload = b"independent writer won acquisition"

    def race(path, mode="r", *args, **kwargs):
        if path == winner and mode == "x":
            with original(path, "wb") as stream:
                stream.write(payload)
        return original(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", race)
    result = installer.select_existing_owner("existing-owner", target=tmp_path).to_dict()
    assert result["reason_code"] == "owner-selection-acquisition-incomplete"
    assert result["mutation_applied"] is (carrier == RECEIPT)
    assert not result.get("operation_receipt")
    assert winner.read_bytes() == payload
    if carrier == RECEIPT:
        assert json.loads((tmp_path / SELECTION).read_text())["selected_owner"]["id"] == "existing-owner"
    else:
        assert not (tmp_path / RECEIPT).exists()


@pytest.mark.parametrize("surface", ["python", "typescript"])
def test_native_retained_reconciliation_survives_selector_attempt(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    ref = Path(".agentic-workspace/planning/execplans/delegation-lane-sweep.plan.json")
    path = tmp_path / ref
    path.parent.mkdir(parents=True)
    path.write_bytes((ROOT / ref).read_bytes())
    # Preserve the actual former record's semantic owner identity.
    (tmp_path / ".agentic-workspace/planning/state.toml").write_text(
        f'[[active.execplans]]\nid="delegation-lane-sweep"\npath="{ref.as_posix()}"\nstatus="active"\n'
    )
    context = {"target": str(tmp_path), "task": "Preserve the current reconstruction scope and returned work"}
    first = consume("native", shared_core_binary, native_cli, context)
    request = first["decision_packet"]["decision_request"]["response_request"]
    request["arguments"]["answer"] = "continue-selected"
    ready = consume("native", shared_core_binary, native_cli, {**context, "request": request})
    action = ready["decision_packet"]["primary_action"]
    applied = consume("native", shared_core_binary, native_cli, {**context, "invocation": action})
    assert applied["status"] == "applied"
    before = (tmp_path / SELECTION).read_bytes()
    assert json.loads(before)["reconciliation"]["custody"]["committed"]
    # A separate legitimate candidate still cannot replace the retained carrier.
    installer.create_execplan_scaffold(plan_id="existing-owner", title="Existing owner", target=tmp_path)
    result = select(surface, tmp_path)
    assert result["reason_code"] == "owner-selection-acquisition-required", result
    assert (tmp_path / SELECTION).read_bytes() == before
    fresh = consume("native", shared_core_binary, native_cli, context)
    assert fresh["planning"]["current_owner"]["current"] is True
    replay = consume("native", shared_core_binary, native_cli, {**context, "invocation": action})
    assert replay["value"] == applied["value"]


@pytest.mark.parametrize("carrier", [SELECTION, RECEIPT])
def test_typescript_exclusive_acquisition_preserves_race_winner(tmp_path: Path, carrier: Path) -> None:
    owner(tmp_path)
    winner = tmp_path / carrier
    script = """
import fs from 'node:fs';
import { syncBuiltinESMExports } from 'node:module';
const winner = process.argv[1];
const target = process.argv[2];
const cli = process.argv[3];
const original = fs.openSync;
fs.openSync = (path, flags, ...rest) => {
  if (String(path) === winner && flags === 'wx') fs.writeFileSync(path, 'independent writer won acquisition');
  return original(path, flags, ...rest);
};
syncBuiltinESMExports();
process.argv = ['node', cli, 'owner-select', '--owner', 'existing-owner', '--target', target, '--format', 'json'];
await import(cli);
"""
    result = subprocess.run(
        [
            shutil.which("node"),
            "--input-type=module",
            "-e",
            script,
            str(winner),
            str(tmp_path),
            (ROOT / "generated/planning/typescript/src/cli.mjs").as_uri(),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.stdout, result.stderr
    payload = json.loads(result.stdout)
    assert payload["reason_code"] == "owner-selection-acquisition-incomplete", payload
    assert payload["mutation_applied"] is (carrier == RECEIPT)
    assert not payload.get("operation_receipt")
    assert winner.read_text() == "independent writer won acquisition"
