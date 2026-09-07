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
    if surface == "python":
        from agentic_workspace.proof_receipt_admission import proof_receipt_admissions

        actual = proof_receipt_admissions(receipts)
    else:
        items = []
        for receipt in receipts:
            try:
                timestamp = datetime.fromisoformat(receipt["recorded_at"].replace("Z", "+00:00"))
                valid = timestamp.tzinfo is not None
            except ValueError:
                valid = False
            items.append({"receipt": receipt, "timestamp_valid": valid})
        request = {"action": "admit-many", "items": items}
        if surface == "json":
            result = subprocess.run(
                [str(shared_core_binary)], input=json.dumps({"proof_receipt": request}), text=True, capture_output=True, check=True
            )
        else:
            module = (ROOT / "bindings/node/semantic-decision.mjs").as_uri()
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


def test_assignment_binding_uses_same_identity_owner(shared_core_binary: Path) -> None:
    from agentic_workspace.assignment_lifecycle import assignment_task_proof_binding

    fixture = json.loads((ROOT / "tests/fixtures/proof_receipt_admission.json").read_text())["assignment_binding"]
    assert assignment_task_proof_binding(fixture["receipt"]) == fixture["expected"]
