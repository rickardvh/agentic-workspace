from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


def contracts_root() -> Path:
    return Path(__file__).resolve().parent / "contracts"


@lru_cache(maxsize=None)
def load_contract_json(relative_path: str) -> dict[str, Any]:
    path = contracts_root() / relative_path
    return json.loads(path.read_text(encoding="utf-8"))


def compact_contract_manifest() -> dict[str, Any]:
    return load_contract_json("compact_contract_profile.json")


def proof_routes_manifest() -> dict[str, Any]:
    return load_contract_json("proof_routes.json")


def report_contract_manifest() -> dict[str, Any]:
    return load_contract_json("report_contract.json")


def contract_inventory_manifest() -> dict[str, Any]:
    return load_contract_json("contract_inventory.json")


def contract_schema(relative_path: str) -> dict[str, Any]:
    return load_contract_json(f"schemas/{relative_path}")
