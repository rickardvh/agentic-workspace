from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_contract_tooling_surfaces.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_contract_tooling_surfaces", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_documented_proof_command_inventory_rejects_stale_obsolete_command(tmp_path: Path) -> None:
    module = _load_module()
    docs = tmp_path / "docs" / "maintainer"
    docs.mkdir(parents=True)
    (tmp_path / "AGENTS.md").write_text("Use uv run python tests/primitive_conformance.py\n", encoding="utf-8")
    inventory = docs / "proof-command-inventory.json"
    inventory.write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/documented-proof-command-inventory/v1",
                "sources": ["AGENTS.md"],
                "commands": [
                    {
                        "id": "legacy-primitive-conformance-script",
                        "command": "uv run python tests/primitive_conformance.py",
                        "status": "obsolete",
                        "source_refs": ["AGENTS.md"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    errors = module._validate_documented_proof_command_inventory(repo_root=tmp_path, inventory_path=inventory)

    assert errors == ["legacy-primitive-conformance-script obsolete command still appears in ordinary routing sources: AGENTS.md"]


def test_documented_proof_command_inventory_accepts_runnable_source_ref(tmp_path: Path) -> None:
    module = _load_module()
    docs = tmp_path / "docs" / "maintainer"
    docs.mkdir(parents=True)
    command = "uv run python scripts/check/check_generated_command_packages.py"
    (docs / "maintainer-commands.md").write_text(f"Run `{command}`.\n", encoding="utf-8")
    inventory = docs / "proof-command-inventory.json"
    inventory.write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/documented-proof-command-inventory/v1",
                "sources": ["docs/maintainer/maintainer-commands.md"],
                "commands": [
                    {
                        "id": "generated-command-packages-static",
                        "command": command,
                        "status": "runnable",
                        "source_refs": ["docs/maintainer/maintainer-commands.md"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    assert module._validate_documented_proof_command_inventory(repo_root=tmp_path, inventory_path=inventory) == []
