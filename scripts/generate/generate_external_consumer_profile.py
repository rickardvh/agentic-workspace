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
PYTHON_CLIENT = REPO_ROOT / "generated/workspace/python/client.py"
TYPESCRIPT_CLIENT = REPO_ROOT / "generated/workspace/typescript/src/client.mjs"


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
    unique: dict[str, dict[str, object]] = {}
    for entry in operations:
        operation_id = str(entry["id"])
        previous = unique.get(operation_id)
        if previous is not None and previous["operation_contract"] != entry["operation_contract"]:
            raise ValueError(f"conflicting explicit operation id: {operation_id}")
        unique.setdefault(operation_id, entry)
    operations = sorted(unique.values(), key=lambda item: str(item["id"]))
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


def render_python_client() -> str:
    return '''# Generated from command_package_ir.json. Do not edit.\nfrom __future__ import annotations\n\nimport json\nimport subprocess\nfrom importlib.resources import files\nfrom pathlib import Path\nfrom typing import Any, Sequence\n\n\ndef external_consumer_profile() -> dict[str, Any]:\n    resource = files("agentic_workspace._generated_cli_package_impl").joinpath("external_consumer_profile.json")\n    return json.loads(resource.read_text(encoding="utf-8"))\n\n\ndef require_operations(operation_ids: Sequence[str], *, allow_runtime_backed: bool = False) -> None:\n    entries = {entry["id"]: entry for entry in external_consumer_profile()["operations"]}\n    failures = []\n    for operation_id in operation_ids:\n        entry = entries.get(operation_id)\n        status = entry and entry["external_consumption"]["status"]\n        if entry is None or status == "internal" or (status == "runtime-backed" and not allow_runtime_backed):\n            failures.append(f"{operation_id}: {status or 'unknown'}")\n    if failures:\n        raise ValueError("incompatible operation requirements: " + ", ".join(failures))\n\n\ndef invoke_json(argv: Sequence[str], *, target: str | Path | None = None, executable: Sequence[str] = ("agentic-workspace",)) -> dict[str, Any]:\n    command = [*executable, *argv]\n    if target is not None and "--target" not in command:\n        command.extend(["--target", str(target)])\n    if "--format" not in command:\n        command.extend(["--format", "json"])\n    completed = subprocess.run(command, text=True, capture_output=True, check=False)\n    stream = completed.stdout or completed.stderr\n    try:\n        payload = json.loads(stream)\n    except json.JSONDecodeError as exc:\n        raise RuntimeError(f"AW returned non-JSON output (exit {completed.returncode})") from exc\n    if completed.returncode:\n        raise RuntimeError(json.dumps({"exit_code": completed.returncode, "error": payload}))\n    return payload\n'''


def render_typescript_client() -> str:
    return '''// Generated from command_package_ir.json. Do not edit.\nimport { readFileSync } from 'node:fs';\nimport { spawnSync } from 'node:child_process';\n\nconst profileUrl = new URL('../external_consumer_profile.json', import.meta.url);\nexport function externalConsumerProfile() { return JSON.parse(readFileSync(profileUrl, 'utf8')); }\nexport function requireOperations(operationIds, { allowRuntimeBacked = false } = {}) {\n  const entries = new Map(externalConsumerProfile().operations.map((entry) => [entry.id, entry]));\n  const failures = operationIds.flatMap((id) => {\n    const status = entries.get(id)?.external_consumption?.status ?? 'unknown';\n    return status === 'internal' || status === 'unknown' || (status === 'runtime-backed' && !allowRuntimeBacked) ? [`${id}: ${status}`] : [];\n  });\n  if (failures.length) throw new Error(`incompatible operation requirements: ${failures.join(', ')}`);\n}\nexport function invokeJson(argv, { target, executable = 'agentic-workspace' } = {}) {\n  const args = [...argv];\n  if (target !== undefined && !args.includes('--target')) args.push('--target', String(target));\n  if (!args.includes('--format')) args.push('--format', 'json');\n  const result = spawnSync(executable, args, { encoding: 'utf8' });\n  const text = result.stdout || result.stderr;\n  let payload;\n  try { payload = JSON.parse(text); } catch (error) { throw new Error(`AW returned non-JSON output (exit ${result.status})`, { cause: error }); }\n  if (result.status !== 0) throw new Error(JSON.stringify({ exit_code: result.status, error: payload }));\n  return payload;\n}\n'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = render()
    rendered = {**{path: expected for path in OUTPUTS}, PYTHON_CLIENT: render_python_client(), TYPESCRIPT_CLIENT: render_typescript_client()}
    stale = [path for path, content in rendered.items() if not path.is_file() or path.read_text(encoding="utf-8") != content]
    if args.check:
        for path in stale:
            print(f"{path.relative_to(REPO_ROOT).as_posix()} is stale")
        return int(bool(stale))
    for path, content in rendered.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
