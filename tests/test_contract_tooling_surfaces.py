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


def test_non_enum_keyword_routing_audit_rejects_unclassified_candidate(tmp_path: Path) -> None:
    module = _load_module()
    source = tmp_path / "src" / "sample.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "\n".join(
            [
                "def neutral_helper_name(value):",
                '    local_markers = ("alpha", "beta", "gamma")',
                "    return any(marker in value for marker in local_markers)",
            ]
        ),
        encoding="utf-8",
    )
    audit = tmp_path / "docs" / "maintainer" / "non-enum-keyword-routing-audit.json"
    audit.parent.mkdir(parents=True)
    audit.write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/non-enum-keyword-routing-audit/v1",
                "entries": [],
            }
        ),
        encoding="utf-8",
    )

    errors = module._validate_non_enum_keyword_routing_audit(repo_root=tmp_path, audit_path=audit)

    assert errors == ["non-enum-keyword-routing-audit missing structural candidate: src/sample.py|neutral_helper_name|local_markers"]


def test_non_enum_keyword_routing_audit_rejects_disallowed_policy(tmp_path: Path) -> None:
    module = _load_module()
    source = tmp_path / "src" / "sample.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "\n".join(
            [
                "def neutral_helper_name(value):",
                '    local_markers = ("alpha", "beta", "gamma")',
                "    return any(marker in value for marker in local_markers)",
            ]
        ),
        encoding="utf-8",
    )
    audit = tmp_path / "docs" / "maintainer" / "non-enum-keyword-routing-audit.json"
    audit.parent.mkdir(parents=True)
    audit.write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/non-enum-keyword-routing-audit/v1",
                "entries": [
                    {
                        "path": "src/sample.py",
                        "function": "neutral_helper_name",
                        "variable": "local_markers",
                        "classification": "disallowed-package-policy",
                        "decision_authority": "advisory-only",
                        "authority": "sample",
                        "agent_judgment_boundary": "Agent decides.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    errors = module._validate_non_enum_keyword_routing_audit(repo_root=tmp_path, audit_path=audit)

    assert errors == [
        "src/sample.py|neutral_helper_name|local_markers is classified as disallowed-package-policy; "
        "remove the keyword table or demote it to non-authoritative evidence"
    ]


def test_non_enum_keyword_routing_audit_rejects_decision_affecting_package_policy(tmp_path: Path) -> None:
    module = _load_module()
    source = tmp_path / "src" / "sample.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "\n".join(
            [
                "def neutral_helper_name(value):",
                '    local_markers = ("alpha", "beta", "gamma")',
                "    return any(marker in value for marker in local_markers)",
            ]
        ),
        encoding="utf-8",
    )
    audit = tmp_path / "docs" / "maintainer" / "non-enum-keyword-routing-audit.json"
    audit.parent.mkdir(parents=True)
    audit.write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/non-enum-keyword-routing-audit/v1",
                "entries": [
                    {
                        "path": "src/sample.py",
                        "function": "neutral_helper_name",
                        "variable": "local_markers",
                        "classification": "advisory-diagnostic",
                        "decision_authority": "decision-affecting-package-policy",
                        "authority": "sample",
                        "agent_judgment_boundary": "Agent decides.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    errors = module._validate_non_enum_keyword_routing_audit(repo_root=tmp_path, audit_path=audit)

    assert errors == [
        "src/sample.py|neutral_helper_name|local_markers is decision-affecting package policy; "
        "migrate it to structured authority before accepting the audit"
    ]
