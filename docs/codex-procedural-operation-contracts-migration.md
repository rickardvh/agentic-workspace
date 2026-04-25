# Codex migration: procedural operation contracts

## Context

This branch starts the next step after declarative contract extraction: describing procedural behavior in implementation-independent contracts.

The goal is not to replace `cli.py` yet. The first migration should make operation contracts validated, discoverable, and connected to command metadata while preserving current runtime behavior.

## Added contract files

- `src/agentic_workspace/contracts/schemas/operation.schema.json`
- `src/agentic_workspace/contracts/operation_primitives.json`
- `src/agentic_workspace/contracts/operation_contracts.json`
- `src/agentic_workspace/contracts/operations/config.report.json`
- `src/agentic_workspace/contracts/operations/preflight.report.json`
- `src/agentic_workspace/contracts/operations/system-intent.sync.json`

## Intended model

Operation contracts are JSON documents validated by JSON Schema.

They describe:

- operation identity and command surface
- inputs and output kind
- filesystem reads and writes
- safety/effect annotations
- local execution assumptions
- ordered steps using named primitive capabilities
- guards and proof expectations
- projection hints for CLI, MCP, and generated skills

They do not embed Python, shell, JSONLogic-heavy condition trees, or executable DSL logic.

## Codex wiring steps

### 1. Add contract accessors

In `src/agentic_workspace/contract_tooling.py`, add:

```python
def operation_contracts_manifest() -> dict[str, Any]:
    return load_contract_json("operation_contracts.json")


def operation_primitives_manifest() -> dict[str, Any]:
    return load_contract_json("operation_primitives.json")


def operation_manifest(relative_path: str) -> dict[str, Any]:
    return load_contract_json(relative_path)
```

Keep this generic so future operation files do not require a new Python accessor per operation.

### 2. Validate operation contracts

In `scripts/check/check_contract_tooling_surfaces.py`:

1. Import the new accessors.
2. Validate `operation_contracts.json` and `operation_primitives.json` with lightweight inline checks or future schemas.
3. For each entry in `operation_contracts.json["operations"]`, load the referenced file and validate it against `operation.schema.json`.

Suggested check shape:

```python
operation_contracts = operation_contracts_manifest()
for operation_ref in operation_contracts["operations"]:
    operation = operation_manifest(operation_ref["path"])
    checks.append((
        f"operation contract {operation_ref['id']}",
        _validate(operation, "operation.schema.json"),
    ))
```

### 3. Add command-surface parity

Still in `check_contract_tooling_surfaces.py`, verify that each operation command exists in `cli_commands.json`:

```python
known_commands = {command["name"] for command in cli_commands_manifest()["commands"]}
for operation_ref in operation_contracts["operations"]:
    if operation_ref["command"] not in known_commands:
        checks.append(("operation command parity", [f"unknown command for operation {operation_ref['id']}"]))
```

Then validate each operation file agrees with its registry entry:

```python
operation = operation_manifest(operation_ref["path"])
if operation["id"] != operation_ref["id"]:
    checks.append(("operation registry parity", [f"operation id mismatch for {operation_ref['path']}"]))
if operation["command_surface"]["command"] != operation_ref["command"]:
    checks.append(("operation registry parity", [f"operation command mismatch for {operation_ref['id']}"]))
```

### 4. Validate primitive references

Verify every `steps[*].uses` exists in `operation_primitives.json`:

```python
known_primitives = {primitive["id"] for primitive in operation_primitives_manifest()["primitives"]}
for operation_ref in operation_contracts["operations"]:
    operation = operation_manifest(operation_ref["path"])
    missing = [step["uses"] for step in operation["steps"] if step["uses"] not in known_primitives]
    if missing:
        checks.append(("operation primitive parity", [f"{operation_ref['id']} uses unknown primitive(s): {', '.join(missing)}"]))
```

### 5. Add inventory entry

In `src/agentic_workspace/contracts/contract_inventory.json`, add an area entry:

```json
{
  "area": "procedural_operation_contracts",
  "classification": "procedural-contract",
  "owner_surface": "src/agentic_workspace/contracts/operation_contracts.json",
  "consumers": [
    "scripts/check/check_contract_tooling_surfaces.py",
    "future CLI/MCP/skill generators"
  ],
  "notes": "Draft operation contracts describe behavior, effects, guards, proof expectations, and primitive sequencing without replacing current runtime logic yet."
}
```

### 6. Keep runtime unchanged for this slice

Do not rewrite command handlers yet.

This PR should prove that operation contracts are:

- valid
- discoverable
- command-linked
- primitive-linked
- projection-ready

Runtime consumption can be a later PR once the contract boundary has been reviewed.

### 7. Run checks

Expected commands:

```bash
uv run pytest tests/test_workspace_cli.py -q
uv run pytest tests/test_contract_tooling.py -q
uv run python scripts/check/check_contract_tooling_surfaces.py
uv run ruff check src tests scripts
```

## Suggested review focus

Reviewers should focus on the contract boundary, not whether the first three operations perfectly model every detail.

Questions to ask:

- Are effects and locality easy to inspect?
- Are steps understandable without becoming a private programming language?
- Are primitive names stable enough to project into future generated CLIs, MCP tools, and skills?
- Is the first validation slice small enough to merge without runtime risk?

## Non-goals

- No workflow engine.
- No generated CLI yet.
- No generated MCP server yet.
- No generated skills yet.
- No executable DSL embedded in JSON.
- No runtime behavior changes in the first slice.
