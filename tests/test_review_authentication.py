"""Fixture signatures establish predicate behavior, never real acceptance."""

from __future__ import annotations

import copy
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest
from tests.test_native_public_cli import native_cli as native_cli
from tests.test_workspace_proof_cli import _independent_review_host_signature, _write_independent_review_host_result

from agentic_workspace import workspace_runtime_proof as proof
from agentic_workspace.decision import review_authentication

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def signed(tmp_path):
    inputs = _write_independent_review_host_result(
        tmp_path,
        {
            "kind": "agentic-workspace/independent-review-result/v1",
            "status": "accepted",
            "assignment_revision": "assignment:exact",
            "proof_subject_revision": "subject:exact",
            "changed_paths": ["a.txt"],
            "reviewer": {"actor_id": "fixture-reviewer"},
        },
        install_host_admission=False,
        return_capability_inputs=True,
    )
    reference = inputs["host_result_ref"]
    host = json.loads((tmp_path / proof.INDEPENDENT_REVIEW_HOST_RESULT_DIR / (reference.split(":", 1)[1] + ".json")).read_text())
    key = inputs["host_public_key"]
    return {
        "host_result_ref": reference,
        "host_result": host,
        "workspace_ref": f"workspace:path:{tmp_path.resolve()}",
        "now_unix_micros": int(datetime.now(timezone.utc).timestamp() * 1_000_000),
        "public_keys": {key["key_id"]: key},
    }


@pytest.mark.parametrize("surface", ["python", "node", "json"])
def test_fixture_authentication_exact_body_then_tamper_rejected(signed, shared_core_binary, surface):
    module = (ROOT / "bindings/node/semantic-decision.mjs").as_uri()

    def consume(context):
        if surface == "python":
            return review_authentication(context)
        if surface == "node":
            args = [
                "node",
                "--input-type=module",
                "-e",
                f"import {{reviewAuthentication}} from {json.dumps(module)}; console.log(JSON.stringify(reviewAuthentication(JSON.parse(process.argv[1]))));",
                json.dumps(context),
            ]
            data = None
        else:
            args = [str(shared_core_binary)]
            data = json.dumps({"review_authentication": context})
        return json.loads(subprocess.run(args, input=data, capture_output=True, text=True, check=True).stdout)

    accepted = consume(signed)
    assert accepted["status"] == "admitted"
    assert accepted["assignment_revision"] == "assignment:exact"
    assert accepted["proof_subject_revision"] == "subject:exact"
    for field in ["assignment_revision", "proof_subject_revision"]:
        changed = copy.deepcopy(signed)
        changed["host_result"]["review_result"][field] = "unrelated"
        assert consume(changed) == {}
    unpinned = {**signed, "public_keys": None}
    assert consume(unpinned) == {}


@pytest.mark.parametrize("change", ["workspace", "reference", "issuer", "channel", "audience", "key-revoked", "key-expired", "signature"])
def test_current_authority_and_signed_provenance_are_independent_requirements(signed, change):
    candidate = copy.deepcopy(signed)
    key = next(iter(candidate["public_keys"].values()))
    admission = candidate["host_result"]["host_admission"]
    if change == "workspace":
        candidate["workspace_ref"] = "workspace:unrelated"
    elif change == "reference":
        candidate["host_result_ref"] = "independent-review-host-result:unrelated"
    elif change == "issuer":
        key["issuer"] = "other"
    elif change == "channel":
        key["trusted_channel"] = "caller"
    elif change == "audience":
        admission["signed_payload"]["audience"] = "unrelated"
    elif change == "key-revoked":
        key["revoked_at"] = "2026-01-01T00:00:00Z"
    elif change == "key-expired":
        key["expires_at"] = "2026-01-01T00:00:00Z"
    else:
        admission["signature"] = "forged"
    assert review_authentication(candidate) == {}


@pytest.mark.parametrize(
    "field", ["audience", "operation", "workspace_ref", "host_result_ref", "assignment_revision", "proof_subject_revision", "key_revision"]
)
def test_valid_signature_cannot_grant_wrong_current_subject_or_authority(signed, field):
    admission = signed["host_result"]["host_admission"]
    admission["signed_payload"][field] = "unrelated"
    replacement = _independent_review_host_signature(admission["signed_payload"])
    admission["signature"] = replacement["signature"]
    key = next(iter(signed["public_keys"].values()))
    key.update(n=replacement["key"]["n"], e=replacement["key"]["e"])
    assert review_authentication(signed) == {}


@pytest.mark.parametrize("field", ["not_before", "expires_at"])
@pytest.mark.parametrize("value", ["invalid-date", "2026-01-01T00:00:00", 123, {}, None, "", " "])
def test_present_malformed_key_bounds_fail_closed_but_absence_remains_optional(signed, field, value):
    key = next(iter(signed["public_keys"].values()))
    key[field] = value
    result = review_authentication(signed)
    assert (result.get("status") == "admitted") is (value is None or value in ("", " "))


def test_native_reference_does_not_admit_fixture_keys_or_public_verdicts(signed, tmp_path, shared_core_binary, native_cli):
    from tests.test_native_public_cli import consume

    context = {"target": str(tmp_path), "task": "Inspect the current bounded review", "changed": ["a.txt"]}
    initial = consume("native", shared_core_binary, native_cli, context)
    request = initial["verification"]["authentication_request"]
    request["arguments"]["host_result_ref"] = signed["host_result_ref"]
    result = consume("native", shared_core_binary, native_cli, {**context, "request": request})
    assert result["verification"]["host_authentication"] == {
        "status": "unadmitted",
        "reason": "release-pinned-host-authentication-rejected",
        "authority_effect": "none",
    }
    assert result["verification"]["evidence"] == []
    request["arguments"]["public_keys"] = signed["public_keys"]
    with pytest.raises(AssertionError, match="public_keys|Additional properties"):
        consume("native", shared_core_binary, native_cli, {**context, "request": request})
