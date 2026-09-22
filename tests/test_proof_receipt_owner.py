"""Original owner fixtures through independently invoked shared-core consumers."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("surface", ["python", "json", "typescript"])
def test_original_receipt_admission_fixture_through_shared_owner(shared_core_binary: Path, surface: str) -> None:
    fixture = json.loads((ROOT / "tests/fixtures/proof_receipt_admission.json").read_text())
    receipts = [case["receipt"] for case in fixture["cases"]]
    items = []
    for receipt in receipts:
        try:
            timestamp = datetime.fromisoformat(receipt["recorded_at"].replace("Z", "+00:00"))
            valid = timestamp.tzinfo is not None
        except ValueError:
            valid = False
        items.append({"receipt": receipt, "timestamp_valid": valid})
    request = {"action": "admit-many", "items": items}
    if surface == "python":
        from aw_maintainer.native_conformance import proof_receipt

        actual = proof_receipt(request)["items"]
        assert actual == [case["expected"] for case in fixture["cases"]]
        return
    if surface == "json":
        result = subprocess.run(
            [str(shared_core_binary)], input=json.dumps({"proof_receipt": request}), text=True, capture_output=True, check=True
        )
    else:
        module = (ROOT / "src/cli/typescript/semantic-decision.mjs").as_uri()
        result = subprocess.run(
            [
                "node",
                "--input-type=module",
                "-e",
                f"import {{proofReceipt}} from {json.dumps(module)}; console.log(JSON.stringify(proofReceipt(JSON.parse(process.argv[1]))));",
                json.dumps(request),
            ],
            text=True,
            capture_output=True,
            check=True,
        )
    actual = json.loads(result.stdout)["items"]
    assert actual == [case["expected"] for case in fixture["cases"]]
