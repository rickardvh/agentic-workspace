from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
IR_PATH = REPO_ROOT / "src/agentic_workspace/contracts/command_package_ir.json"
OUTPUTS = (
    REPO_ROOT / "src/agentic_workspace/contracts/external_consumer_profile.json",
    REPO_ROOT / "generated/workspace/python/external_consumer_profile.json",
    REPO_ROOT / "generated/workspace/typescript/external_consumer_profile.json",
)


def _commands(command: dict[str, object], inherited: dict[str, object] | None = None):
    current = dict(inherited or {})
    if "operation_ref" not in command:
        current.pop("operation_ref", None)
    current.update(command)
    yield current
    interface = command.get("interface", {})
    if isinstance(interface, dict):
        for child in interface.get("subcommands", []):
            if isinstance(child, dict):
                yield from _commands(child, current)


def build_profile(ir: dict[str, object]) -> dict[str, object]:
    operations: list[dict[str, object]] = []
    for package in ir.get("packages", []):
        if not isinstance(package, dict):
            continue
        targets = {
            str(target.get("kind")): {
                "package": target.get("package_name"),
                "status": target.get("generation_status"),
                "maturity": target.get("maturity_level_ref"),
            }
            for target in package.get("targets", [])
            if isinstance(target, dict)
        }
        for root in package.get("commands", []):
            if not isinstance(root, dict):
                continue
            for command in _commands(root):
                ref = command.get("operation_ref", {})
                if not isinstance(ref, dict) or not ref.get("id") or not ref.get("path"):
                    continue
                effects = command.get("effect_hints", {})
                conformance = [value for value in command.get("conformance_refs", []) if isinstance(value, str)]
                boundary = command.get("projection_boundary", {})
                runtime_owned = boundary.get("runtime_owned", []) if isinstance(boundary, dict) else []
                required = bool(effects) and bool(conformance) and {"python", "typescript"}.issubset(targets)
                if command.get("status") != "generated" or not required:
                    maturity = "internal"
                elif runtime_owned:
                    maturity = "runtime-backed"
                else:
                    maturity = "supported"
                entry = {
                    "id": ref["id"],
                    "owner": package.get("id"),
                    "operation_contract": f"{package.get('operation_contract_root')}/{ref['path']}",
                    "schemas": command.get("schemas", {"input": [], "output": []}),
                    "effects": effects,
                    "targets": targets,
                    "conformance": conformance,
                    "external_consumption": {
                        "status": maturity,
                        "runtime_exceptions": runtime_owned,
                        "dependency": "#2044" if runtime_owned else None,
                    },
                }
                operations.append(entry)
    operations.sort(key=lambda item: str(item["id"]))
    operation_ids = [str(item["id"]) for item in operations]
    duplicates = sorted({operation_id for operation_id in operation_ids if operation_ids.count(operation_id) > 1})
    if duplicates:
        raise ValueError(f"duplicate explicit operation ids: {', '.join(duplicates)}")
    fingerprint_input = json.dumps(operations, sort_keys=True, separators=(",", ":")).encode()
    return {
        "schema_version": "agentic-workspace/external-consumer-profile/v1",
        "authority": "command_package_ir.json",
        "compatibility": {
            "protocol": "1.0.0",
            "fingerprint": f"sha256:{hashlib.sha256(fingerprint_input).hexdigest()}",
            "additive_fields": "allowed",
        },
        "support_rule": "Operations fail closed unless generated status, effects, conformance, and Python/TypeScript target accounting are present.",
        "operations": operations,
    }


def render() -> str:
    return json.dumps(build_profile(json.loads(IR_PATH.read_text(encoding="utf-8"))), indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = render()
    stale = [path for path in OUTPUTS if not path.is_file() or path.read_text(encoding="utf-8") != expected]
    if args.check:
        for path in stale:
            print(f"{path.relative_to(REPO_ROOT).as_posix()} is stale")
        return int(bool(stale))
    for path in OUTPUTS:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(expected, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
