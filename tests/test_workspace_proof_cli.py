from __future__ import annotations

import copy
import hashlib
import os
import sys
import tomllib
from contextlib import contextmanager

# ruff: noqa: F403,F405
from tests.workspace_cli_support import *

ROOT = Path(__file__).resolve().parents[1]
_INDEPENDENT_REVIEW_HOST_FIXTURE_KEYS: dict[str, dict[str, object]] = {}


@contextmanager
def _test_owned_proof_local_state(
    monkeypatch: pytest.MonkeyPatch,
    *,
    canonical_root: Path,
    local_state_root: Path,
):
    """Keep canonical repo inputs while making mutable local proof state test-owned."""

    import agentic_workspace.workspace_runtime_proof as proof_runtime

    original_receipt_reader = proof_runtime._read_proof_receipt_records
    original_consequence_summary = proof_runtime._improvement_consequence_summary
    original_consequence_history = proof_runtime.read_consequence_history
    canonical_resolved = canonical_root.resolve()

    def reroot(target_root: Path | None) -> Path | None:
        if target_root is not None and target_root.resolve() == canonical_resolved:
            return local_state_root
        return target_root

    def read_receipts(target_root: Path):
        return original_receipt_reader(reroot(target_root) or target_root)

    def consequence_summary(*, target_root: Path | None, active_finding_ids: set[str]):
        return original_consequence_summary(
            target_root=reroot(target_root),
            active_finding_ids=active_finding_ids,
        )

    def read_history(*, target_root: Path | None):
        return original_consequence_history(target_root=reroot(target_root))

    with monkeypatch.context() as local_state_patch:
        local_state_patch.setattr(proof_runtime, "_read_proof_receipt_records", read_receipts)
        local_state_patch.setattr(proof_runtime, "_improvement_consequence_summary", consequence_summary)
        local_state_patch.setattr(proof_runtime, "read_consequence_history", read_history)
        yield


@contextmanager
def _verified_host_fixture(monkeypatch: pytest.MonkeyPatch, host_result_ref: str):
    import agentic_workspace.workspace_runtime_proof as proof_runtime

    key = _INDEPENDENT_REVIEW_HOST_FIXTURE_KEYS[host_result_ref]
    original_verifier = proof_runtime._signed_independent_review_host_verdict_with_keys

    def verify_fixture(*, host_result_ref: str, host_result: dict[str, object], target_root: Path) -> dict[str, object]:
        return original_verifier(
            host_result_ref=host_result_ref,
            host_result=host_result,
            target_root=target_root,
            public_keys={str(key["key_id"]): key},
        )

    with monkeypatch.context() as fixture_patch:
        fixture_patch.setattr(proof_runtime, "_signed_independent_review_host_verdict", verify_fixture)
        yield


def _independent_review_host_signature(payload: dict[str, object]) -> dict[str, object]:
    script = r"""
import base64
import hashlib
import json
import os
import random
import sys

RSA_SHA256_DER_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")


def is_probable_prime(candidate):
    if candidate < 2:
        return False
    small_primes = (3, 5, 7, 11, 13, 17, 19, 23, 29, 31)
    if candidate in small_primes:
        return True
    if candidate % 2 == 0 or any(candidate % prime == 0 for prime in small_primes):
        return False
    d = candidate - 1
    s = 0
    while d % 2 == 0:
        s += 1
        d //= 2
    for base in (2, 3, 5, 7, 11, 13, 17):
        if base >= candidate:
            continue
        x = pow(base, d, candidate)
        if x in (1, candidate - 1):
            continue
        for _ in range(s - 1):
            x = pow(x, 2, candidate)
            if x == candidate - 1:
                break
        else:
            return False
    return True


def random_prime(bits):
    while True:
        candidate = int.from_bytes(os.urandom(bits // 8), "big")
        candidate |= (1 << (bits - 1)) | 1
        if is_probable_prime(candidate):
            return candidate


payload = json.loads(sys.stdin.read())
random.seed()
e = 65537
while True:
    p = random_prime(256)
    q = random_prime(256)
    if p == q:
        continue
    phi = (p - 1) * (q - 1)
    if phi % e != 0:
        break
n = p * q
d = pow(e, -1, phi)
key_size = (n.bit_length() + 7) // 8
message = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
digest_info = RSA_SHA256_DER_PREFIX + hashlib.sha256(message).digest()
encoded = b"\x00\x01" + (b"\xff" * (key_size - len(digest_info) - 3)) + b"\x00" + digest_info
raw = pow(int.from_bytes(encoded, "big"), d, n).to_bytes(key_size, "big")
print(json.dumps({
    "key": {
        "algorithm": "RS256",
        "issuer": "github-review-webhook",
        "producer": "github-review-adapter",
        "trusted_channel": "github-review-webhook",
        "n": format(n, "x"),
        "e": 65537,
        "status": "current",
    },
    "signature": base64.b64encode(raw).decode("ascii"),
}, sort_keys=True))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        input=json.dumps(payload, sort_keys=True, default=str),
        capture_output=True,
        text=True,
        check=True,
    )
    signed = json.loads(completed.stdout)
    assert isinstance(signed, dict)
    return signed


def _write_independent_review_host_result(
    target_root: Path,
    review_result: dict[str, object],
    *,
    host_admission_monkeypatch: pytest.MonkeyPatch | None = None,
    install_host_admission: bool = True,
    caller_env_admission_keys: bool = False,
    return_capability_inputs: bool = False,
) -> str | dict[str, object]:
    from agentic_workspace.workspace_runtime_proof import (
        INDEPENDENT_REVIEW_HOST_RESULT_AUDIENCE,
        INDEPENDENT_REVIEW_HOST_RESULT_DIR,
        INDEPENDENT_REVIEW_HOST_RESULT_INDEX_KIND,
        _host_result_body_for_admission,
        _stable_review_json_digest,
    )

    result = dict(review_result)
    result.setdefault("proof_subject_revision", "proof-subject-rev-1")
    custody = dict(result.get("custody") if isinstance(result.get("custody"), dict) else {})
    custody.update({"producer": "github-review-adapter", "trusted_channel": "github-review-webhook"})
    result["custody"] = custody
    admission_context = {
        "audience": str(result.get("audience") or INDEPENDENT_REVIEW_HOST_RESULT_AUDIENCE),
        "workspace_ref": str(result.get("workspace_ref") or f"workspace:path:{target_root.resolve()}"),
        "operation": str(result.get("operation") or "assignment.admit.independent-review"),
        "assignment_revision": str(result.get("assignment_revision") or "assignment-rev-1"),
        "proof_subject_revision": str(result.get("proof_subject_revision") or "proof-subject-rev-1"),
        "issued_at": str(result.get("admission_issued_at") or "2026-07-29T00:00:00Z"),
        "expires_at": str(result.get("admission_expires_at") or "2099-01-01T00:00:00Z"),
        "nonce": str(
            result["nonce"]
            if "nonce" in result
            else f"{result.get('review_id', 'review')}:{result.get('assignment_revision', 'assignment-rev-1')}"
        ),
    }
    host_result = {
        "kind": "agentic-workspace/independent-review-host-result/v1",
        "status": "current",
        "admission_context": admission_context,
        "custody": {
            "producer": "github-review-adapter",
            "trusted_channel": "github-review-webhook",
            "authority_ref": custody.get("authority_ref", ""),
            "source_ref": custody.get("source_ref", ""),
        },
        "review_result": result,
    }
    host_id = _stable_review_json_digest(host_result)[:24]
    host_result_ref = f"independent-review-host-result:{host_id}"
    host_result["host_result_id"] = host_id
    host_result["host_result_ref"] = host_result_ref
    signed_payload = {
        "kind": "agentic-workspace/independent-review-host-result-admission-payload/v1",
        "host_result_ref": host_result_ref,
        "host_result_body_digest": _stable_review_json_digest(_host_result_body_for_admission(host_result)),
        "issuer": "github-review-webhook",
        "producer": "github-review-adapter",
        "trusted_channel": "github-review-webhook",
        **admission_context,
    }
    if result.get("admission_revoked_at"):
        signed_payload["revoked_at"] = str(result["admission_revoked_at"])
    if result.get("admission_superseded_by"):
        signed_payload["superseded_by"] = str(result["admission_superseded_by"])
    root = target_root / INDEPENDENT_REVIEW_HOST_RESULT_DIR
    path = root / f"{host_id}.json"
    key_id = f"github-review-adapter:external-host-fixture:{host_id}"
    key_revision = f"fixture-key:{host_id}"
    signed_payload["key_revision"] = key_revision
    signed = _independent_review_host_signature(signed_payload)
    key = dict(signed["key"]) if isinstance(signed.get("key"), dict) else {}
    key.update(
        {
            "authority": "pinned-host-runtime",
            "status": str(result.get("key_status") or "current"),
            "key_id": key_id,
            "key_revision": key_revision,
            "workspace_ref": str(result.get("key_workspace_ref") or f"workspace:path:{target_root.resolve()}"),
            "workspace_path": str(result.get("key_workspace_path") or target_root.resolve()),
            "not_before": str(result.get("key_not_before") or "2026-01-01T00:00:00Z"),
            "expires_at": str(result.get("key_expires_at") or "2099-01-01T00:00:00Z"),
        }
    )
    if result.get("key_revoked_at"):
        key["revoked_at"] = str(result["key_revoked_at"])
    host_result["host_admission"] = {
        "kind": "agentic-workspace/independent-review-host-result-admission/v1",
        "status": "current",
        "algorithm": "RS256",
        "key_id": key_id,
        "signed_payload": signed_payload,
        "signature": str(signed["signature"]),
    }
    capability = {
        "kind": "agentic-workspace/independent-review-host-admission-capability/v1",
        "status": "current",
        "capability_id": "github-review-adapter:" + _stable_review_json_digest({"host_result_ref": host_result_ref})[:16],
        "host_result_ref": host_result_ref,
        "operation": "assignment.admit.independent-review",
        "audience": INDEPENDENT_REVIEW_HOST_RESULT_AUDIENCE,
        "authority": "host-adapter-owned",
    }
    if install_host_admission:
        _INDEPENDENT_REVIEW_HOST_FIXTURE_KEYS[host_result_ref] = key
    if caller_env_admission_keys:
        import os

        os.environ["AW_INDEPENDENT_REVIEW_HOST_RESULT_ADMISSION_KEYS"] = json.dumps({key_id: key})
    _write(path, json.dumps(host_result, indent=2, sort_keys=True) + "\n")
    index_path = root / "index.json"
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        index = {"kind": INDEPENDENT_REVIEW_HOST_RESULT_INDEX_KIND, "results": {}}
    if index.get("kind") != INDEPENDENT_REVIEW_HOST_RESULT_INDEX_KIND or not isinstance(index.get("results"), dict):
        index = {"kind": INDEPENDENT_REVIEW_HOST_RESULT_INDEX_KIND, "results": {}}
    index["results"][host_id] = {
        "path": path.relative_to(root).as_posix(),
        "status": "current",
        "producer": "github-review-adapter",
        "trusted_channel": "github-review-webhook",
        "host_result_digest": _stable_review_json_digest(host_result),
        "review_result_digest": _stable_review_json_digest(result),
    }
    _write(index_path, json.dumps(index, indent=2, sort_keys=True) + "\n")
    if return_capability_inputs:
        return {
            "host_result_ref": host_result_ref,
            "host_admission": host_result["host_admission"],
            "host_public_key": key,
            "host_capability": capability,
        }
    return host_result_ref


def _write_repo_local_proof_target(target: Path) -> None:
    _init_git_repo(target)
    _write(
        target / "Makefile",
        """
schema-reference-docs:
\tpython -c "print('schema docs')"

typecheck:
\tpython -m compileall src

typecheck-planning:
\tpython -m compileall packages/planning/src

lint-planning:
\tpython -m compileall packages/planning/src

check-planning:
\tpython -c "print('planning checks')"

check-planning-nosync:
\tpython -c "print('planning owner acceptance')"

test-workspace:
\tpython -c "print('workspace tests')"

test-planning:
\tpython -c "print('planning tests')"
""",
    )
    _write(target / "scripts" / "check" / "check_agent_aids.py", "print('agent aids ok')\n")
    _write(target / "scripts" / "check" / "check_contract_tooling_surfaces.py", "print('contract tooling ok')\n")
    _write(target / "scripts" / "check" / "check_generated_command_packages.py", "print('generated packages ok')\n")
    _write(target / "scripts" / "generate" / "generate_command_packages.py", "print('generate packages ok')\n")
    _write(target / "scripts" / "run_agentic_workspace.py", "print('workspace report ok')\n")
    _write(target / "README.md", "# Fixture\n")
    _write(target / "docs" / ".keep", "")
    _write(target / ".agentic-workspace" / "docs" / "agent-installation.md", "# Install\n")
    _write(target / "packages" / "planning" / "README.md", "# Planning\n")
    _write(target / "packages" / "memory" / "README.md", "# Memory\n")
    _write(
        target / ".agentic-workspace" / "config.toml",
        f"""
schema_version = 1

[workspace]
cli_invoke = "{REPO_LOCAL_CLI_INVOKE}"

[assurance.proof_profiles.workspace_behavior]
required_commands = ["make test-workspace"]
optional_commands = []
review_aids = []

[assurance.subsystem_profiles.workspace-cli-runtime]
assurance_level = "high"
scope_refs = ["ownership.subsystems.workspace-cli-runtime"]
requirement_refs = [".agentic-workspace/OWNERSHIP.toml#subsystems.workspace-cli-runtime"]
required_evidence = ["workspace_runtime_proof"]
proof_profile = "workspace_behavior"
force = "required-before-closeout"
blocked_without_evidence = ["claim-work-complete"]
claim_boundary = "workspace-runtime-routing"
""",
    )
    _write(
        target / ".agentic-workspace" / "OWNERSHIP.toml",
        """
[[subsystems]]
id = "workspace-cli-runtime"
paths = ["generated/workspace/python/**", "src/agentic_workspace/workspace_runtime*.py"]
owns = ["workspace command routing"]
proof = ["make test-workspace"]
""",
    )
    _write(
        target / ".agentic-workspace" / "verification" / "manifest.toml",
        """
schema_version = "agentic-workspace/verification-manifest/v1"

[scenarios.generated_adapter_local_conformance]
protocol_id = "generated_adapter_conformance"
title = "Generated adapter local conformance"
steps = []
expected_observations = []
pass_evidence_labels = ["generated_adapter_conformance"]
fail_evidence_labels = ["generated_adapter_conformance_drift"]

[scenarios.closeout_intent_satisfaction_review]
protocol_id = "closeout_intent_satisfaction"
title = "Closeout intent satisfaction review"
steps = []
expected_observations = []
pass_evidence_labels = ["closeout_intent_satisfaction"]
fail_evidence_labels = ["closeout_intent_gap"]

[scenarios.requirement_grounding_delegation_review]
protocol_id = "requirement_grounding_delegation"
title = "Requirement grounding delegation review"
steps = []
expected_observations = []
pass_evidence_labels = ["requirement_grounding_delegation"]
fail_evidence_labels = ["requirement_grounding_gap"]

[protocols.generated_adapter_conformance]
title = "Generated adapter conformance"
purpose = "Generated workspace adapter changes need conformance evidence."
applies_to_paths = ["generated/workspace/python/**"]
scenario_refs = ["generated_adapter_local_conformance"]
steps = []
expected_evidence = ["generated_adapter_conformance"]
review_owner = "maintainer"

[protocols.closeout_intent_satisfaction]
title = "Closeout intent satisfaction"
purpose = "Workspace runtime changes need closeout intent review."
applies_to_paths = ["generated/workspace/python/**", "src/agentic_workspace/workspace_runtime*.py"]
scenario_refs = ["closeout_intent_satisfaction_review"]
steps = []
expected_evidence = ["closeout_intent_satisfaction"]
review_owner = "maintainer"

[protocols.requirement_grounding_delegation]
title = "Requirement grounding delegation"
purpose = "Workspace runtime changes need requirement grounding review."
applies_to_paths = ["generated/workspace/python/**", "src/agentic_workspace/workspace_runtime*.py"]
scenario_refs = ["requirement_grounding_delegation_review"]
steps = []
expected_evidence = ["requirement_grounding_delegation"]
review_owner = "maintainer"

[proof_routes.generated_adapter_conformance]
protocol_refs = ["generated_adapter_conformance"]
scenario_refs = ["generated_adapter_local_conformance"]
commands = [
  "uv run python scripts/generate/generate_command_packages.py --check",
  "uv run python scripts/check/check_generated_command_packages.py --require-node",
]
proof_lane_hint = "generated-adapter-conformance"

[proof_routes.closeout_intent_satisfaction]
protocol_refs = ["closeout_intent_satisfaction"]
scenario_refs = ["closeout_intent_satisfaction_review"]
commands = ["uv run python scripts/run_agentic_workspace.py report --target . --section closeout_trust --format json"]
proof_lane_hint = "closeout-intent-satisfaction"

[proof_routes.requirement_grounding_delegation]
protocol_refs = ["requirement_grounding_delegation"]
scenario_refs = ["requirement_grounding_delegation_review"]
commands = [
  "uv run python scripts/run_agentic_workspace.py implement --changed src/agentic_workspace/workspace_runtime_proof.py --select requirement_grounding,context.delegation_decision,context.plan_delegation_packet --format json",
]
proof_lane_hint = "requirement-grounding-delegation"
""",
    )
    _write(
        target / ".agentic-workspace" / "system-intent" / "intent.toml",
        """
schema_version = 1
kind = "workspace-system-intent/v1"
summary = "Keep proof routing scoped."
governing_intents = []
anti_intents = []
decision_tests = ["Use focused proof selection for changed paths."]
open_questions = []
confidence = "high"
needs_review = false
""",
    )


def _write_installed_host_proof_target(target: Path) -> None:
    _write_repo_local_proof_target(target)
    source_checkout_entrypoint = target / "scripts" / "run_agentic_workspace.py"
    source_checkout_entrypoint.unlink()
    config_path = target / ".agentic-workspace" / "config.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(REPO_LOCAL_CLI_INVOKE, "agentic-workspace"),
        encoding="utf-8",
    )


def _write_empty_proof_planning_state(target_root: Path) -> None:
    _write(
        target_root / ".agentic-workspace" / "planning" / "state.toml",
        """
[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )


def test_proof_runtime_helpers_route_through_proof_owner(tmp_path: Path) -> None:
    assert workspace_runtime_primitives._verification_report_payload is workspace_runtime_proof._verification_report_payload
    assert workspace_runtime_primitives._tiny_proof_payload is workspace_runtime_proof._tiny_proof_payload
    assert workspace_runtime_primitives._tiny_proof_obligations_payload is workspace_runtime_proof._tiny_proof_obligations_payload
    assert workspace_runtime_primitives._active_planning_record_for_proof is workspace_runtime_proof._active_planning_record_for_proof
    assert workspace_runtime_implement._verification_report_payload is workspace_runtime_proof._verification_report_payload
    assert workspace_runtime_implement._tiny_proof_obligations_payload is workspace_runtime_proof._tiny_proof_obligations_payload
    assert workspace_runtime_core._active_planning_record_for_proof(target_root=tmp_path) == {
        "status": "unavailable",
        "reason": "planning state unavailable",
    }


def test_tiny_proof_obligations_summarizes_multiple_manual_obligations() -> None:
    payload = workspace_runtime_proof._tiny_proof_obligations_payload(
        {
            "kind": "agentic-workspace/proof-obligations/v1",
            "required_proof": {
                "status": "required",
                "commands": ["make test-workspace"],
                "manual_verification_required": True,
                "manual_obligation_count": 2,
                "manual_obligations": [
                    {
                        "id": "verification:first",
                        "required": True,
                        "status": "missing-evidence",
                        "missing_evidence": ["first"],
                        "reference_material": ["docs/first.md"],
                        "claim_boundary": "blocked",
                    },
                    {
                        "id": "verification:second",
                        "required": True,
                        "status": "missing-evidence",
                        "missing_evidence": ["second"],
                        "reference_material": ["docs/second.md"],
                        "claim_boundary": "blocked",
                    },
                ],
                "action_effect": {"force": "required_before_claim", "blocked_until_reconciled": ["claim-task-complete"]},
            },
            "recommended_confidence_checks": {"status": "available", "commands": [], "rule": "advisory only"},
            "completion_claim_rule": "Completion claims remain blocked.",
        }
    )

    required = payload["required_proof"]
    assert required["manual_obligation_count"] == 2
    assert [item["id"] for item in required["manual_obligations"]] == ["verification:first", "verification:second"]
    assert required["manual_obligations"][0]["resolution"] == {
        "inspect": ["docs/first.md"],
        "record": ["first"],
        "detail_selector": "proof.proof_obligations.required_proof.manual_obligations",
        "closeout_format": "manual obligation <id>: inspected <refs>; recorded <evidence>; claim boundary <claim_boundary>",
    }


def test_proof_command_reports_routes_and_current_health(tmp_path: Path, monkeypatch, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    (tmp_path / "planning").mkdir()
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))
    monkeypatch.setattr(
        cli,
        "_run_lifecycle_command",
        lambda **kwargs: {
            "health": "healthy",
            "warnings": [],
            "needs_review": [],
            "stale_generated_surfaces": [],
        },
    )

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["canonical_doc"] == ".agentic-workspace/docs/proof-surfaces-contract.md"
    assert payload["command"] == "agentic-workspace proof --target ./repo --format json"
    assert payload["default_routes"]["planning_surfaces"] == "agentic-workspace summary --target ./repo --format json"
    assert payload["current"]["installed_modules"] == ["planning"]
    assert payload["current"]["status_health"] == "healthy"
    assert payload["current"]["doctor_health"] == "healthy"
    assert payload["current"]["warnings"] == []
    assert payload["current"]["needs_review"] == []
    assert calls == []


def test_proof_route_selector_returns_compact_contract_answer(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, []))
    monkeypatch.setattr(
        cli,
        "_run_lifecycle_command",
        lambda **kwargs: {
            "health": "healthy",
            "warnings": [],
            "needs_review": [],
            "stale_generated_surfaces": [],
        },
    )

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--route", "workspace_proof", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "proof"
    assert payload["selector"] == {"route": "workspace_proof"}
    assert payload["matched"] is True
    assert payload["answer"] == {
        "id": "workspace_proof",
        "command": "agentic-workspace proof --target ./repo --format json",
    }
    assert payload["target"] == tmp_path.as_posix()


def test_proof_current_selector_returns_compact_contract_answer(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "planning").mkdir()
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, []))
    monkeypatch.setattr(
        cli,
        "_run_lifecycle_command",
        lambda **kwargs: {
            "health": "healthy",
            "warnings": [],
            "needs_review": [],
            "stale_generated_surfaces": [],
        },
    )

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--current", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["selector"] == {"current": True}
    assert payload["answer"]["installed_modules"] == ["planning"]
    assert payload["answer"]["status_health"] == "healthy"


@pytest.mark.parametrize(
    "select",
    [
        "selected_commands,route_refinement_required,proof_route_strategy_claim_gate",
        "focused_route_coverage_audit,route_refinement_required",
    ],
)
def test_proof_unscoped_scope_dependent_selectors_fail_before_full_construction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], select: str
) -> None:
    _init_git_repo(tmp_path)

    def fail_full_construction(**_: object) -> dict[str, object]:
        raise AssertionError("unscoped selected proof must not construct the full proof payload")

    monkeypatch.setattr(cli, "_proof_payload", fail_full_construction)

    assert cli.main(["proof", "--target", str(tmp_path), "--select", select, "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    assert payload["kind"] == "agentic-workspace/proof-scope-required/v1"
    assert payload["status"] == "scope-required"
    assert payload["selector"] == {
        "requested": select.split(","),
        "scope_dependent": select.split(","),
        "scope": "missing",
    }
    assert payload["next"]["action"] == "provide-proof-scope"
    assert "--changed <paths>" in payload["next"]["command"]
    assert f"--select {select}" in payload["next"]["command"]
    assert payload["construction"] == {
        "status": "not-started",
        "full_proof_payload_built": False,
        "rule": "Scope admission happens before lifecycle health, proof-route, subject, provenance, or diagnostic construction.",
    }
    assert payload["claim_boundary"]["completion_claim_allowed"] is False
    assert len(encoded) < 4000


def test_proof_current_scope_dependent_selectors_require_changed_path_subject_before_construction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _init_git_repo(tmp_path)

    def fail_full_construction(**_: object) -> dict[str, object]:
        raise AssertionError("current status must not construct changed-path selected proof")

    monkeypatch.setattr(cli, "_proof_payload", fail_full_construction)
    select = "selected_commands,route_refinement_required,proof_route_strategy_claim_gate"

    assert cli.main(["proof", "--target", str(tmp_path), "--current", "--select", select, "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["selector"]["scope"] == "current-insufficient"
    assert payload["construction"]["full_proof_payload_built"] is False
    assert "--changed <paths>" in payload["next"]["command"]
    assert "--current --format json" in payload["next"]["alternatives"][0]


def test_proof_unscoped_scope_independent_selector_remains_available(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _init_git_repo(tmp_path)

    assert cli.main(["proof", "--target", str(tmp_path), "--select", "selector_inventory", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["values"]["selector_inventory"]["source_command"] == "proof"


def test_bounded_selected_proof_projection_routes_nested_command_and_claim_detail() -> None:
    payload = {
        "selected_commands": [
            {
                "kind": "proof-command/v1",
                "command": "agentic-workspace implement --changed <paths> --format json",
                "command_identity": "command-1",
                "route_id": "focused",
                "required": True,
                "proof_requirement": "exercise changed behavior",
                "proof_responsibility": "local-closeout",
                "subject_contract": {"changed_paths": ["src/app.py"]},
                "authority_resolution": {
                    "kind": "agentic-workspace/proof-template-obligation-resolution/v1",
                    "status": "resolved",
                    "source": "repo-proof-obligation-resolver",
                    "current_identity": {"lane_id": "focused", "lane_revision": "lane-1"},
                    "authority_states": {
                        "lane_id": {
                            "status": "current",
                            "revision": "focused",
                            "source": "repo-proof-obligation-resolver",
                            "provenance": "selected proof lane",
                            "payload": {"large": "omitted"},
                        }
                    },
                },
                "receipt_contract": {"binds": ["operation"]},
            }
        ],
        "proof_route_strategy_claim_gate": {
            "kind": "agentic-workspace/proof-route-strategy-claim-gate/v1",
            "status": "allowed-after-selected-proof",
            "decision_id": "decision-1",
            "route_health_id": "health-1",
            "claim_effect": "focused-proof-required",
            "selected_requirement": "focused-proof",
            "completion_claim_authorized": True,
            "consumer_gate": {
                "kind": "agentic-workspace/proof-route-strategy-consumer-gate/v1",
                "status": "current",
                "mismatch_effect": "claim-blocked",
                "required_consumers": ["proof", "closeout"],
                "large_diagnostic": {"omitted": True},
            },
            "handoff": {"large": "omitted"},
            "closeout": {"large": "omitted"},
        },
    }

    projected = cli._bounded_selected_proof_projection(
        payload,
        select="selected_commands,proof_route_strategy_claim_gate",
        cli_invoke="agentic-workspace",
    )

    command = projected["selected_commands"][0]
    assert command["command"] == "agentic-workspace implement --changed <paths> --format json"
    assert command["proof_requirement"] == "exercise changed behavior"
    assert command["proof_responsibility"] == "local-closeout"
    assert "--changed <paths> --verbose" in command["detail_route"]
    assert set(command).isdisjoint({"subject_contract", "receipt_contract"})
    authority = command["authority_resolution"]
    assert authority["current_identity"] == {"lane_id": "focused", "lane_revision": "lane-1"}
    assert authority["authority_states"]["lane_id"]["revision"] == "focused"
    assert "payload" not in authority["authority_states"]["lane_id"]
    assert projected["proof_route_strategy_claim_gate"]["handoff"] == {"large": "omitted"}
    assert projected["proof_route_strategy_claim_gate"]["consumer_gate"]["large_diagnostic"] == {"omitted": True}
    assert payload["selected_commands"][0]["authority_resolution"]["status"] == "resolved"
    assert payload["proof_route_strategy_claim_gate"]["handoff"] == {"large": "omitted"}


def test_proof_scoped_selected_projection_is_decision_sized_and_actionable(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    changed = "src/agentic_workspace/workspace_runtime_core.py"
    select = "selected_commands,route_refinement_required,proof_route_strategy_claim_gate"

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                changed,
                "--select",
                select,
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    commands = payload["values"]["selected_commands"]
    assert commands
    assert all(command["command"] and command["proof_requirement"] for command in commands)
    assert all("--changed <paths> --verbose" in command["detail_route"] for command in commands)
    assert all(set(command).isdisjoint({"subject_contract", "authority_resolution", "receipt_contract"}) for command in commands)
    gate = payload["values"]["proof_route_strategy_claim_gate"]
    assert gate["claim_effect"]
    assert gate["consumer_gate"]["mismatch_effect"] == "claim-blocked"
    assert gate["handoff"]["required_identity_field"] == "proof_route_strategy_preservation.decision_id"
    assert gate["proof_route_health"]["surface"] == "proof_route_maintenance.route_health"
    assert payload["values"]["route_refinement_required"]["status"] in {"not-required", "required"}
    assert len(encoded) < 20000

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                changed,
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )
    full = json.loads(capsys.readouterr().out)["answer"]
    full_commands = {command["command_identity"]: command for command in full["selected_commands"]}
    assert set(full_commands) == {command["command_identity"] for command in commands}
    assert all(full_commands[command["command_identity"]]["command"] == command["command"] for command in commands)
    assert any("subject_contract" in command and "receipt_contract" in command for command in full_commands.values())


def test_proof_route_selector_smoke_works_without_mocked_lifecycle(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target), "--modules", "planning"]) == 0
    capsys.readouterr()

    assert cli.main(["proof", "--verbose", "--target", str(target), "--route", "workspace_proof", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["selector"] == {"route": "workspace_proof"}
    assert payload["answer"]["id"] == "workspace_proof"
    assert payload["answer"]["command"] == "agentic-workspace proof --target ./repo --format json"


def test_proof_changed_selector_returns_path_based_validation_lane(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                ".agentic-workspace/planning/state.toml",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["surface"] == "proof"
    assert payload["selector"] == {"changed": [".agentic-workspace/planning/state.toml"]}
    answer = payload["answer"]
    expected_target = Path(os.path.relpath(tmp_path, Path.cwd())).as_posix()
    assert answer["kind"] == "proof-selection/v1"
    assert answer["selected_lanes"][0]["id"] == "planning_surfaces"
    assert answer["required_commands"] == [
        f'{REPO_LOCAL_CLI_INVOKE} summary --target "{expected_target}" --format json',
        f'{REPO_LOCAL_CLI_INVOKE} doctor --target "{expected_target}" --modules planning --format json',
    ]
    assert answer["validation_plan"]["kind"] == "validation-plan/v1"
    assert answer["validation_plan"]["status"] == "inspect-before-run"
    first_step = answer["validation_plan"]["required"][0]
    assert first_step["order"] == 1
    assert first_step["command"] == f'{REPO_LOCAL_CLI_INVOKE} summary --target "{expected_target}" --format json'
    assert first_step["cwd"] == "."
    assert first_step["run"] == f'{REPO_LOCAL_CLI_INVOKE} summary --target "{expected_target}" --format json'
    assert first_step["required"] is True
    assert first_step["lane_id"] == "planning_surfaces"
    assert first_step["action"] == "run-validation-command"
    assert first_step["risk"] == "read-only validation"
    assert first_step["required_inputs"] == ["changed_paths", "selected_lanes"]
    assert first_step["next_proof"] == "continue to the next required step, then rerun proof selection if changed paths expand"
    assert answer["validation_plan"]["primary_next_action"] == first_step
    assert answer["validation_plan"]["next_proof"] == "proof is complete when all required steps pass for the current changed paths"
    assert answer["durable_intent"]["kind"] == "agentic-workspace/durable-intent-decision/v1"
    assert any(item.startswith("Relevant durable intent may add proof") for item in answer["escalate_when"])


def _append_focused_proof_runtime_lane(target: Path) -> None:
    config = target / ".agentic-workspace" / "config.toml"
    config.write_text(
        config.read_text(encoding="utf-8")
        + """

[assurance.domain_proof_lanes.proof_runtime]
purpose = "Focused proof runtime behavior."
applies_to_paths = ["src/agentic_workspace/workspace_runtime_proof.py", "tests/test_workspace_proof_cli.py"]
commands = ["uv run pytest tests/test_workspace_proof_cli.py -k changed_selector -q"]
review_aids = ["Confirm changed proof routing behavior is exercised."]
evidence_concepts = ["focused-proof-runtime"]
proof_profiles = ["workspace_behavior"]
authority_refs = [".agentic-workspace/config.toml", "docs/maintainer/testing-strategy.md"]
escalation = ["focused proof does not exercise the changed behavior"]
claim_boundary = "focused-proof-runtime-required"
owner = "workspace-cli-runtime"
""",
        encoding="utf-8",
    )


def _append_task_selected_broad_proof_lane(target: Path) -> None:
    makefile = target / "Makefile"
    makefile.write_text(
        makefile.read_text(encoding="utf-8")
        + """

test-workspace-proof:
\tpython -c "print('workspace proof')"

test-workspace-session-review:
\tpython -c "print('workspace session review')"
""",
        encoding="utf-8",
    )
    config = target / ".agentic-workspace" / "config.toml"
    config.write_text(
        config.read_text(encoding="utf-8")
        + """

[assurance.domain_proof_lanes.workspace_broad_suite]
purpose = "Explicit broad workspace validation route."
applies_to_task_markers = ["broad workspace proof"]
commands = ["make test-workspace-proof", "make test-workspace-session-review"]
proof_profiles = ["workspace_behavior"]
escalation_conditions = ["explicit-request"]
claim_boundary = "explicit-broad-escalation-required"
owner = "workspace-cli-runtime"
route_role = "broad"
precedence = "10"
allowed_composition = ["behavior"]
""",
        encoding="utf-8",
    )


def _replace_workspace_subsystem_proof(target: Path, command: str) -> None:
    ownership = target / ".agentic-workspace" / "OWNERSHIP.toml"
    text = ownership.read_text(encoding="utf-8")
    ownership.write_text(
        text.replace('proof = ["uv run pytest tests/test_workspace_cli.py -q"]', f'proof = ["{command}"]'), encoding="utf-8"
    )


def _append_root_workspace_guidance_lane(target: Path) -> None:
    config = target / ".agentic-workspace" / "config.toml"
    config.write_text(
        config.read_text(encoding="utf-8")
        + """

[assurance.domain_proof_lanes.root_workspace_guidance]
purpose = "Focused root Workspace startup/report/defaults guidance behavior."
applies_to_paths = ["src/agentic_workspace/config.py", "src/agentic_workspace/reporting_support.py", "src/agentic_workspace/workspace_runtime_generated_surface.py", "src/agentic_workspace/workspace_runtime_startup.py", "src/agentic_workspace/contracts/skill_specs.json", "tests/test_maintainer_surfaces.py", "tests/test_workspace_defaults_cli.py"]
applies_to_task_markers = ["host guidance target localization", "root workspace guidance", "startup fallback authority"]
commands = ["uv run pytest tests/test_workspace_proof_cli.py -k root_workspace_guidance -q", "uv run pytest tests/test_workspace_defaults_cli.py -q", "uv run pytest tests/test_maintainer_surfaces.py -q", "make typecheck"]
review_aids = ["Confirm root guidance proof stays focused."]
evidence_concepts = ["root-workspace-guidance"]
proof_profiles = ["workspace_behavior"]
authority_refs = [".agentic-workspace/config.toml", "docs/maintainer/testing-strategy.md"]
escalation = ["focused route cannot prove the changed guidance behavior"]
claim_boundary = "focused-root-guidance-required"
owner = "workspace-cli-runtime"
route_role = "behavior"
""",
        encoding="utf-8",
    )


def _append_session_logging_lane(target: Path) -> None:
    config = target / ".agentic-workspace" / "config.toml"
    config.write_text(
        config.read_text(encoding="utf-8")
        + """

[assurance.domain_proof_lanes.session_logging]
purpose = "Focused session logging behavior."
applies_to_paths = ["src/agentic_workspace/session_logging.py", "tests/test_workspace_session_logging.py"]
commands = ["uv run pytest tests/test_workspace_session_logging.py -q"]
review_aids = ["Confirm local diagnostic boundaries and persistence behavior."]
evidence_concepts = ["focused-session-logging"]
proof_profiles = ["workspace_behavior"]
authority_refs = [".agentic-workspace/config.toml"]
escalation = ["session-log persistence or local diagnostic boundaries changed"]
claim_boundary = "focused-session-logging-required"
owner = "workspace-cli-runtime"
""",
        encoding="utf-8",
    )


def test_proof_root_workspace_guidance_2383_replay_uses_focused_lane_without_broad_workspace_cli(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _append_root_workspace_guidance_lane(tmp_path)
    changed_paths = [
        "src/agentic_workspace/config.py",
        "src/agentic_workspace/reporting_support.py",
        "src/agentic_workspace/workspace_runtime_core.py",
        "src/agentic_workspace/workspace_runtime_generated_surface.py",
        "src/agentic_workspace/workspace_runtime_primitives.py",
        "src/agentic_workspace/workspace_runtime_startup.py",
        "src/agentic_workspace/contracts/skill_specs.json",
        "src/agentic_workspace/contracts/workspace_defaults/payload.json",
        "tests/test_maintainer_surfaces.py",
        "tests/test_workspace_defaults_cli.py",
    ]
    for changed_path in changed_paths:
        _write(tmp_path / changed_path, "# fixture\n")
    _write(tmp_path / "tests" / "test_workspace_proof_cli.py", "# fixture\n")
    _write(tmp_path / "scripts" / "run_agentic_workspace.py", "# fixture\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                *changed_paths,
                "--task",
                "Replay PR 2383 host guidance target localization proof plan",
                "--select",
                "proof_route_strategy_decision,route_refinement_required,required_commands,selected_lanes,proof_route_maintenance,proof_route_strategy_preservation,proof_route_strategy_claim_gate",
                "--format",
                "json",
            ]
        )
        == 0
    )

    values = json.loads(capsys.readouterr().out)["values"]
    assert values["proof_route_strategy_decision"]["outcome"] == "focused"
    assert values["route_refinement_required"]["status"] == "not-required"
    assert "domain:root_workspace_guidance" in [lane["id"] for lane in values["selected_lanes"]]
    assert "uv run pytest tests/test_workspace_cli.py -q" not in values["required_commands"]
    assert "make test-workspace" not in values["required_commands"]
    subsystem_lane = next(lane for lane in values["selected_lanes"] if lane["id"] == "subsystem:workspace-cli-runtime")
    assert subsystem_lane["focused_route_reduction"]["status"] == "required-proof-satisfied-by-domain-proof-lane"
    assert "make test-workspace" in subsystem_lane["focused_route_reduction"]["withheld_commands"]
    route_health_classes = {finding["finding_class"] for finding in values["proof_route_maintenance"]["route_health"]["findings"]}
    assert "missing_coverage" not in route_health_classes
    assert "excessive_breadth_cost" not in route_health_classes
    preservation = values["proof_route_strategy_preservation"]
    claim_gate = values["proof_route_strategy_claim_gate"]
    assert preservation["route_health_id"]
    assert claim_gate["route_health_id"] == preservation["route_health_id"]
    assert claim_gate["proof_route_health"]["surface"] == "proof_route_maintenance.route_health"
    for consumer in preservation["consumers"].values():
        assert consumer["route_health_id"] == preservation["route_health_id"]


def test_proof_route_maintenance_selector_reports_route_health_repair_packet(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _append_focused_proof_runtime_lane(tmp_path)
    changed_path = "src/agentic_workspace/workspace_runtime_primitives.py"
    _write(tmp_path / changed_path, "# fixture\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                changed_path,
                "--select",
                "proof_route_maintenance,route_refinement_required",
                "--format",
                "json",
            ]
        )
        == 0
    )

    values = json.loads(capsys.readouterr().out)["values"]
    assert values["route_refinement_required"]["status"] == "required"
    route_health = values["proof_route_maintenance"]["route_health"]
    assert route_health["status"] == "attention"
    finding_classes = {finding["finding_class"] for finding in route_health["findings"]}
    assert {"missing_coverage", "excessive_breadth_cost"}.issubset(finding_classes)
    repair_packets = values["proof_route_maintenance"]["route_health"]["repair_packets"]
    assert any(packet["canonical_edit_surface"].startswith(".agentic-workspace/config.toml") for packet in repair_packets)
    assert all(packet["finding_id"] for packet in repair_packets)
    assert all(packet["consequence_record"]["kind"] == "workspace-improvement-pressure-record/v1" for packet in repair_packets)
    assert all(packet["disposition"]["status"] == "active" for packet in repair_packets)
    assert all(packet["repair_operation"]["expected_authority_revision"] for packet in repair_packets)
    assert all(packet["repair_operation"]["preview_command"] for packet in repair_packets)
    assert all(packet["repair_operation"]["field_selector"] for packet in repair_packets)
    assert all(packet["repair_operation"]["apply_command"] for packet in repair_packets)
    assert route_health["duplicate_disposition_contract"]["status"] == "external-lifecycle-owned"
    assert "#2310" not in json.dumps(route_health)
    assert "#2367" not in json.dumps(route_health)
    assert "5058804538" not in json.dumps(route_health)


def test_proof_route_health_retires_failed_broad_receipt_after_focused_root_route_repair(tmp_path: Path, capsys) -> None:
    _write_installed_host_proof_target(tmp_path)
    assert not (tmp_path / "scripts" / "run_agentic_workspace.py").exists()
    _write(tmp_path / "src" / "agentic_workspace" / "config.py", "# fixture\n")
    config_path = tmp_path / ".agentic-workspace" / "config.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8")
        + """

[assurance.domain_proof_lanes.root_workspace_guidance]
purpose = "Focused root Workspace guidance behavior."
applies_to_paths = ["src/agentic_workspace/config.py"]
commands = ['python -c "import sys; sys.exit(1)"']
review_aids = ["Confirm the selected proof route and route-health packet match the changed root workspace behavior."]
evidence_concepts = ["root-workspace-guidance", "focused-serial-proof"]
proof_profiles = ["workspace_behavior"]
authority_refs = [".agentic-workspace/config.toml"]
escalation = ["the change crosses package, generated-command, lifecycle, or closeout behavior boundaries"]
claim_boundary = "focused-root-workspace-guidance-required-before-runtime-routing-claim"
owner = "workspace-cli-runtime"
""",
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/config.py",
                "--record-receipt",
                "--receipt-command",
                'python -c "import sys; sys.exit(1)"',
                "--receipt-result",
                "failed",
                "--receipt-log",
                "make test-workspace timed out after 240s",
                "--receipt-timeout",
                "--receipt-duration-seconds",
                "240",
                "--receipt-route-id",
                "root_workspace_guidance",
                "--receipt-claim-sufficiency",
                "insufficient",
                "--receipt-route-budget-seconds",
                "120",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/config.py",
                "--select",
                "proof_route_maintenance,proof_route_strategy_preservation,proof_route_strategy_claim_gate",
                "--format",
                "json",
            ]
        )
        == 0
    )
    before_values = json.loads(capsys.readouterr().out)["values"]
    before_health = before_values["proof_route_maintenance"]["route_health"]
    before_findings = {finding["finding_class"]: finding for finding in before_health["findings"]}
    assert "route_execution_failure" in before_findings
    execution_finding = before_findings["route_execution_failure"]
    assert execution_finding["consequence_record"]["kind"] == "workspace-improvement-pressure-record/v1"
    assert execution_finding["disposition"]["durable_owner_ref"] == execution_finding["consequence_record"]["id"]
    assert execution_finding["repair_operation"]["apply_contract"]["idempotency_key"].startswith("proof-route-health:")
    assert execution_finding["repair_operation"]["apply_contract"]["authority_path"] == ".agentic-workspace/config.toml"
    assert execution_finding["repair_operation"]["apply_contract"]["field_selector"] == "assurance.domain_proof_lanes"
    assert before_values["proof_route_strategy_claim_gate"]["consumer_gate"]["status"] == "blocked"

    delta = {
        "action": "upsert_domain_lane",
        "lane_id": "root_workspace_guidance",
        "lane": {
            "purpose": "Focused root Workspace guidance behavior.",
            "applies_to_paths": ["src/agentic_workspace/config.py"],
            "commands": ["python -c \"print('route validation ok')\""],
            "review_aids": ["Confirm the selected proof route and route-health packet match the changed root workspace behavior."],
            "evidence_concepts": ["root-workspace-guidance", "focused-serial-proof"],
            "proof_profiles": ["workspace_behavior"],
            "authority_refs": [".agentic-workspace/config.toml"],
            "escalation": ["the change crosses package, generated-command, lifecycle, or closeout behavior boundaries"],
            "claim_boundary": "focused-root-workspace-guidance-required-before-runtime-routing-claim",
            "owner": "workspace-cli-runtime",
        },
    }

    _write(tmp_path / "tests" / "test_workspace_proof_cli.py", "# fixture\n")
    _write(tmp_path / "tests" / "test_workspace_defaults_cli.py", "# fixture\n")
    _write(tmp_path / "tests" / "test_maintainer_surfaces.py", "# fixture\n")
    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/config.py",
                "--route-repair-mode",
                "apply",
                "--route-repair-finding-id",
                execution_finding["id"],
                "--route-repair-authority-path",
                ".agentic-workspace/config.toml",
                "--route-repair-field-selector",
                "assurance.domain_proof_lanes",
                "--route-repair-expected-revision",
                execution_finding["route_authority_revision"],
                "--route-repair-delta-json",
                json.dumps(delta),
                "--route-repair-disposition",
                "fixed",
                "--route-repair-idempotency-key",
                execution_finding["repair_operation"]["apply_contract"]["idempotency_key"],
                "--format",
                "json",
            ]
        )
        == 0
    )
    apply_payload = json.loads(capsys.readouterr().out)
    assert apply_payload["status"] == "applied"
    assert apply_payload["semantic_delta"]["action"] == "upsert_domain_lane"
    assert apply_payload["apply_receipt"]["id"]
    assert apply_payload["apply_receipt"]["validation_authority"] == (
        "proof_route_maintenance.route_health.repair_packets.validation_commands"
    )
    assert all(command.startswith("agentic-workspace proof ") for command in apply_payload["apply_receipt"]["validation_commands"])
    assert all("scripts/run_agentic_workspace.py" not in command for command in apply_payload["apply_receipt"]["validation_commands"])
    assert set(apply_payload["apply_receipt"]["validation_commands"]) != set(delta["lane"]["commands"])
    assert apply_payload["apply_receipt"]["candidate_route_commands"] == delta["lane"]["commands"]
    assert apply_payload["apply_receipt"]["candidate_route_status"] == "passed"
    assert apply_payload["apply_receipt"]["candidate_route_commands_complete"] is True
    post_authority_revision = apply_payload["post_authority_revision"]

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/config.py",
                "--select",
                "proof_route_strategy_decision,route_refinement_required,proof_route_maintenance,proof_route_strategy_preservation,proof_route_strategy_claim_gate",
                "--format",
                "json",
            ]
        )
        == 0
    )

    values = json.loads(capsys.readouterr().out)["values"]
    assert values["proof_route_strategy_decision"]["outcome"] == "focused"
    assert values["route_refinement_required"]["status"] == "not-required"
    route_health = values["proof_route_maintenance"]["route_health"]
    assert route_health["status"] == "attention"
    assert route_health["retired_finding_count"] == 0
    assert route_health["retirement_candidate_count"] == 1
    assert values["proof_route_strategy_claim_gate"]["consumer_gate"]["status"] == "blocked"

    assert (
        cli.main(
            [
                "summary",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/config.py",
                "--select",
                "closeout_trust_inspection",
                "--format",
                "json",
            ]
        )
        == 0
    )
    closeout_before = json.loads(capsys.readouterr().out)["values"]["closeout_trust_inspection"]
    assert closeout_before["status"] == "required"
    assert closeout_before["proof_route_strategy_consumer_gate"]["status"] == "blocked"

    assert (
        cli.main(
            [
                "planning",
                "handoff",
                "--target",
                str(tmp_path),
                "--changed-surfaces",
                "src/agentic_workspace/config.py",
                "--format",
                "json",
            ]
        )
        == 0
    )
    handoff_transition_before = json.loads(capsys.readouterr().out)
    assert handoff_transition_before["kind"] == "agentic-workspace/planning-handoff-proof-route-gate/v1"
    assert handoff_transition_before["status"] == "blocked"
    assert handoff_transition_before["proof_route_transition_gate"]["blocked_finding_ids"]

    assert (
        cli.main(
            [
                "planning",
                "closeout",
                "--target",
                str(tmp_path),
                "--changed-surfaces",
                "src/agentic_workspace/config.py",
                "--format",
                "json",
            ]
        )
        == 0
    )
    closeout_transition_before = json.loads(capsys.readouterr().out)
    assert closeout_transition_before["kind"] == "agentic-workspace/planning-closeout-proof-route-gate/v1"
    assert closeout_transition_before["status"] == "blocked"
    assert closeout_transition_before["proof_route_transition_gate"]["blocked_finding_ids"]

    focused_command = apply_payload["apply_receipt"]["validation_commands"][0]
    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/config.py",
                "--record-receipt",
                "--receipt-command",
                focused_command,
                "--receipt-result",
                "passed",
                "--receipt-repair-finding-id",
                execution_finding["id"],
                "--receipt-repair-authority-revision",
                post_authority_revision,
                "--receipt-repair-disposition",
                "fixed",
                "--receipt-repair-idempotency-key",
                execution_finding["repair_operation"]["apply_contract"]["idempotency_key"],
                "--receipt-claim-sufficiency",
                "sufficient",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/config.py",
                "--select",
                "proof_route_strategy_decision,route_refinement_required,proof_route_maintenance,proof_route_strategy_preservation,proof_route_strategy_claim_gate",
                "--format",
                "json",
            ]
        )
        == 0
    )

    values = json.loads(capsys.readouterr().out)["values"]
    route_health = values["proof_route_maintenance"]["route_health"]
    assert route_health["status"] == "quiet"
    assert route_health["findings"] == []
    assert route_health["retired_finding_count"] == 1
    assert route_health["retired_findings"][0]["finding_id"] == execution_finding["id"]
    assert route_health["retired_findings"][0]["verified_authority_revision"]
    assert values["proof_route_strategy_claim_gate"]["consumer_gate"]["status"] == "current"

    assert (
        cli.main(
            [
                "summary",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/config.py",
                "--select",
                "closeout_trust_inspection",
                "--format",
                "json",
            ]
        )
        == 0
    )
    closeout_after = json.loads(capsys.readouterr().out)["values"]["closeout_trust_inspection"]
    assert closeout_after["proof_route_strategy_consumer_gate"]["status"] == "current"
    assert "claim-proof-route-health-resolved" not in closeout_after["action_effect"]["blocked_until_reconciled"]

    assert cli.main(["planning", "handoff", "--target", str(tmp_path), "--format", "json"]) == 0
    handoff_transition_after = json.loads(capsys.readouterr().out)
    assert handoff_transition_after.get("kind") != "agentic-workspace/planning-handoff-proof-route-gate/v1"

    assert cli.main(["planning", "closeout", "--target", str(tmp_path), "--format", "json"]) == 0
    closeout_transition_after = json.loads(capsys.readouterr().out)
    assert closeout_transition_after.get("kind") != "agentic-workspace/planning-closeout-proof-route-gate/v1"
    assert values["proof_route_strategy_preservation"]["proof_route_health"] == {
        "status": "quiet",
        "finding_count": 0,
        "finding_ids": [],
        "repair_packet_count": 0,
        "repair_packet_ids": [],
        "retired_finding_count": 1,
        "execution_observation_status": "quiet",
        "surface": "proof_route_maintenance.route_health",
    }


def test_proof_route_repair_rejects_raw_append_delta(tmp_path: Path) -> None:
    from agentic_workspace.config import WorkspaceUsageError
    from agentic_workspace.workspace_runtime_proof import _proof_route_authority_revision, _proof_route_repair_operation_payload

    _write_repo_local_proof_target(tmp_path)
    revision = _proof_route_authority_revision(
        target_root=tmp_path,
        canonical_edit_surface=".agentic-workspace/config.toml [assurance.domain_proof_lanes]",
        selected_commands=[],
        changed_paths=[],
    )

    with pytest.raises(WorkspaceUsageError, match="append_text is not admitted"):
        _proof_route_repair_operation_payload(
            target_root=tmp_path,
            changed_paths=["src/agentic_workspace/config.py"],
            mode="apply",
            finding_id="finding-alpha",
            authority_path=".agentic-workspace/config.toml",
            field_selector="assurance.domain_proof_lanes",
            expected_revision=revision,
            delta_json=json.dumps({"append_text": "[assurance.domain_proof_lanes.bad]\n"}),
            disposition="fixed",
            idempotency_key="proof-route-health:finding-alpha:test",
        )

    config_text = (tmp_path / ".agentic-workspace" / "config.toml").read_text(encoding="utf-8")
    assert "[assurance.domain_proof_lanes.bad]" not in config_text


def test_proof_route_repair_receipt_rejects_forged_retirement_without_apply(tmp_path: Path) -> None:
    from agentic_workspace.config import WorkspaceUsageError
    from agentic_workspace.workspace_runtime_primitives import _record_proof_receipt_payload

    _write_repo_local_proof_target(tmp_path)
    before = _proof_owned_publication_snapshot(tmp_path)

    with pytest.raises(WorkspaceUsageError, match="matching guarded apply receipt"):
        _record_proof_receipt_payload(
            target_root=tmp_path,
            command="uv run pytest tests/test_workspace_proof_cli.py -k changed_selector -q",
            result="passed",
            changed_paths=["src/agentic_workspace/config.py"],
            receipt_repair_finding_id="forged-finding",
            receipt_repair_authority_revision="forged-revision",
            receipt_repair_disposition="fixed",
            receipt_repair_idempotency_key="proof-route-health:forged:test",
            receipt_claim_sufficiency="sufficient",
        )

    assert _proof_owned_publication_snapshot(tmp_path) == before


def test_proof_route_consequence_owner_does_not_bulk_retire_unrelated_findings(tmp_path: Path) -> None:
    from agentic_workspace.workspace_runtime_proof import _improvement_consequence_record_event, _improvement_consequence_summary

    _write_repo_local_proof_target(tmp_path)

    _improvement_consequence_record_event(
        target_root=tmp_path,
        event={
            "event": "observed",
            "finding_id": "finding-alpha",
            "record_id": "pressure-proof-route-finding-alpha",
            "finding_class": "route_execution_failure",
            "authority_revision": "rev-a",
        },
    )
    _improvement_consequence_record_event(
        target_root=tmp_path,
        event={
            "event": "observed",
            "finding_id": "finding-beta",
            "record_id": "pressure-proof-route-finding-beta",
            "finding_class": "route_execution_failure",
            "authority_revision": "rev-b",
        },
    )
    _improvement_consequence_record_event(
        target_root=tmp_path,
        event={
            "event": "retired",
            "finding_id": "finding-alpha",
            "record_id": "pressure-proof-route-finding-alpha",
            "disposition": "fixed",
            "authority_revision": "rev-a2",
            "apply_receipt_id": "apply-alpha",
        },
    )

    summary = _improvement_consequence_summary(target_root=tmp_path, active_finding_ids=set())
    assert summary["open_finding_ids"] == ["finding-beta"]

    _improvement_consequence_record_event(
        target_root=tmp_path,
        event={
            "event": "observed",
            "finding_id": "finding-alpha",
            "record_id": "pressure-proof-route-finding-alpha",
            "finding_class": "route_execution_failure",
            "authority_revision": "rev-a3",
        },
    )
    recurrence = _improvement_consequence_summary(target_root=tmp_path, active_finding_ids=set())
    assert recurrence["open_finding_ids"] == ["finding-alpha", "finding-beta"]


def test_proof_route_consequence_store_corruption_fails_closed(tmp_path: Path) -> None:
    from agentic_workspace.improvement_consequence import IMPROVEMENT_CONSEQUENCE_HISTORY_RELATIVE_PATH
    from agentic_workspace.workspace_runtime_proof import _improvement_consequence_summary, _proof_route_transition_gate_payload

    _write_repo_local_proof_target(tmp_path)
    history_path = tmp_path / IMPROVEMENT_CONSEQUENCE_HISTORY_RELATIVE_PATH
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text('{"kind": "ok"}\n{broken-json\n', encoding="utf-8")

    summary = _improvement_consequence_summary(target_root=tmp_path, active_finding_ids=set())
    assert summary["status"] == "blocked-store-unavailable"
    assert summary["fail_closed"] is True
    assert summary["open_finding_ids"] == ["consequence-store-unavailable"]

    gate = _proof_route_transition_gate_payload(
        target_root=tmp_path,
        transition="planning-handoff",
        changed_paths=["README.md"],
    )
    assert gate["status"] == "blocked"
    assert gate["blocked_finding_ids"] == ["consequence-store-unavailable"]


def test_proof_route_consequence_store_writer_lock_fails_closed_for_readers(tmp_path: Path) -> None:
    from agentic_workspace.improvement_consequence import ConsequenceStoreUnavailable, read_consequence_history
    from agentic_workspace.workspace_runtime_proof import _improvement_consequence_summary, _proof_route_transition_gate_payload

    _write_repo_local_proof_target(tmp_path)
    lock_path = tmp_path / ".agentic-workspace" / "local" / "improvement-pressure" / "consequence-history.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text('{"pid":1}\n', encoding="utf-8")

    with pytest.raises(ConsequenceStoreUnavailable, match="write is in progress"):
        read_consequence_history(target_root=tmp_path)

    summary = _improvement_consequence_summary(target_root=tmp_path, active_finding_ids=set())
    assert summary["status"] == "blocked-store-unavailable"
    assert summary["fail_closed"] is True

    gate = _proof_route_transition_gate_payload(
        target_root=tmp_path,
        transition="planning-handoff",
        changed_paths=["src/agentic_workspace/config.py"],
    )
    assert gate["status"] == "blocked"
    assert gate["blocked_finding_ids"] == ["consequence-store-unavailable"]


def test_proof_route_consequence_store_writer_waits_for_transient_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agentic_workspace import improvement_consequence

    _write_repo_local_proof_target(tmp_path)
    lock_path = tmp_path / ".agentic-workspace" / "local" / "improvement-pressure" / "consequence-history.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text('{"pid":1}\n', encoding="utf-8")
    monkeypatch.setattr(improvement_consequence, "CONSEQUENCE_LOCK_WAIT_SECONDS", 1.0)
    sleep_calls = 0
    real_sleep = improvement_consequence.time.sleep

    def release_lock_after_first_poll(duration: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        lock_path.unlink()
        real_sleep(0)

    monkeypatch.setattr(improvement_consequence.time, "sleep", release_lock_after_first_poll)

    record = improvement_consequence.record_consequence_event(
        target_root=tmp_path,
        event={"source": "test", "event": "observed", "finding_id": "finding-alpha"},
    )

    assert sleep_calls == 1
    assert record["finding_id"] == "finding-alpha"
    assert not lock_path.exists()
    assert improvement_consequence.read_consequence_history(target_root=tmp_path)[0]["finding_id"] == "finding-alpha"


def test_proof_route_consequence_store_writer_waits_for_windows_permission_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agentic_workspace import improvement_consequence

    _write_repo_local_proof_target(tmp_path)
    lock_path = tmp_path / ".agentic-workspace" / "local" / "improvement-pressure" / "consequence-history.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    real_open = improvement_consequence.os.open
    real_sleep = improvement_consequence.time.sleep
    open_calls = 0

    def transient_permission_error_once(path: str, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
        nonlocal open_calls
        open_calls += 1
        if open_calls == 1 and Path(path) == lock_path:
            raise PermissionError("simulated Windows lock contention")
        if dir_fd is None:
            return real_open(path, flags, mode)
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(improvement_consequence.os, "open", transient_permission_error_once)
    monkeypatch.setattr(improvement_consequence.time, "sleep", lambda _duration: real_sleep(0))

    record = improvement_consequence.record_consequence_event(
        target_root=tmp_path,
        event={"source": "test", "event": "observed", "finding_id": "finding-permission-lock"},
    )

    assert open_calls == 2
    assert record["finding_id"] == "finding-permission-lock"
    assert not lock_path.exists()
    assert improvement_consequence.read_consequence_history(target_root=tmp_path)[0]["finding_id"] == "finding-permission-lock"


def test_proof_route_transition_gate_blocks_only_matching_scoped_findings(tmp_path: Path) -> None:
    from agentic_workspace.workspace_runtime_proof import _improvement_consequence_record_event, _proof_route_transition_gate_payload

    _write_repo_local_proof_target(tmp_path)
    _improvement_consequence_record_event(
        target_root=tmp_path,
        event={
            "event": "observed",
            "finding_id": "finding-config",
            "finding_class": "route_execution_failure",
            "affected_route": "domain:config",
            "scope": {
                "changed_paths": ["src/agentic_workspace/config.py"],
                "scope_ref": "domain:config",
            },
        },
    )

    unrelated = _proof_route_transition_gate_payload(
        target_root=tmp_path,
        transition="planning-handoff",
        changed_paths=["README.md"],
    )
    assert unrelated["status"] == "current"
    assert unrelated["blocked_finding_ids"] == []
    assert unrelated["non_blocking_open_finding_ids"] == ["finding-config"]

    matching = _proof_route_transition_gate_payload(
        target_root=tmp_path,
        transition="planning-handoff",
        changed_paths=["src/agentic_workspace/config.py"],
    )
    assert matching["status"] == "blocked"
    assert matching["blocked_finding_ids"] == ["finding-config"]

    expanded_scope = _proof_route_transition_gate_payload(
        target_root=tmp_path,
        transition="planning-handoff",
        changed_paths=["src/agentic_workspace/config.py", "README.md"],
    )
    assert expanded_scope["status"] == "current"
    assert expanded_scope["blocked_finding_ids"] == []


def test_proof_route_transition_gate_uses_latest_finding_scope(tmp_path: Path) -> None:
    from agentic_workspace.workspace_runtime_proof import _improvement_consequence_record_event, _proof_route_transition_gate_payload

    _write_repo_local_proof_target(tmp_path)
    for changed_path in ("src/agentic_workspace/config.py", "README.md"):
        _improvement_consequence_record_event(
            target_root=tmp_path,
            event={
                "event": "observed",
                "finding_id": "finding-moved",
                "finding_class": "route_execution_failure",
                "affected_route": "domain:config",
                "scope": {"changed_paths": [changed_path]},
            },
        )

    stale_scope = _proof_route_transition_gate_payload(
        target_root=tmp_path,
        transition="planning-closeout",
        changed_paths=["src/agentic_workspace/config.py"],
    )
    assert stale_scope["status"] == "current"
    assert stale_scope["blocked_finding_ids"] == []

    current_scope = _proof_route_transition_gate_payload(
        target_root=tmp_path,
        transition="planning-closeout",
        changed_paths=["README.md"],
    )
    assert current_scope["status"] == "blocked"
    assert current_scope["blocked_finding_ids"] == ["finding-moved"]


def test_proof_route_repair_validation_failure_rolls_back_without_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agentic_workspace import workspace_runtime_proof
    from agentic_workspace.config import WorkspaceUsageError
    from agentic_workspace.workspace_runtime_proof import (
        PROOF_ROUTE_REPAIR_HISTORY_RELATIVE_PATH,
        _proof_route_authority_revision,
        _proof_route_repair_operation_payload,
    )

    _write_repo_local_proof_target(tmp_path)
    authority_path = tmp_path / ".agentic-workspace" / "config.toml"
    before = authority_path.read_text(encoding="utf-8")
    revision = _proof_route_authority_revision(
        target_root=tmp_path,
        canonical_edit_surface=".agentic-workspace/config.toml [assurance.domain_proof_lanes]",
        selected_commands=[],
        changed_paths=["src/agentic_workspace/config.py"],
    )
    delta = {
        "action": "upsert_domain_lane",
        "lane_id": "broken_validation_route",
        "lane": {
            "purpose": "Broken validation route.",
            "applies_to_paths": ["src/agentic_workspace/config.py"],
            "commands": ["python -c \"print('proposed route command is not validation authority')\""],
        },
    }
    monkeypatch.setattr(
        workspace_runtime_proof,
        "_proof_route_independent_validation_commands",
        lambda **_: (['python -c "import sys; sys.exit(7)"'], "test-independent-validation-owner"),
    )

    with pytest.raises(WorkspaceUsageError, match="validation command failed"):
        _proof_route_repair_operation_payload(
            target_root=tmp_path,
            changed_paths=["src/agentic_workspace/config.py"],
            mode="apply",
            finding_id="finding-validation-fails",
            authority_path=".agentic-workspace/config.toml",
            field_selector="assurance.domain_proof_lanes",
            expected_revision=revision,
            delta_json=json.dumps(delta),
            disposition="fixed",
            idempotency_key="proof-route-health:finding-validation-fails:test",
        )

    assert authority_path.read_text(encoding="utf-8") == before
    assert not (tmp_path / PROOF_ROUTE_REPAIR_HISTORY_RELATIVE_PATH).exists()


def test_proof_route_repair_candidate_command_failure_rolls_back_without_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agentic_workspace import workspace_runtime_proof
    from agentic_workspace.config import WorkspaceUsageError
    from agentic_workspace.workspace_runtime_proof import (
        PROOF_ROUTE_REPAIR_HISTORY_RELATIVE_PATH,
        _proof_route_authority_revision,
        _proof_route_repair_operation_payload,
    )

    _write_repo_local_proof_target(tmp_path)
    authority_path = tmp_path / ".agentic-workspace" / "config.toml"
    before = authority_path.read_text(encoding="utf-8")
    revision = _proof_route_authority_revision(
        target_root=tmp_path,
        canonical_edit_surface=".agentic-workspace/config.toml [assurance.domain_proof_lanes]",
        selected_commands=[],
        changed_paths=["src/agentic_workspace/config.py"],
    )
    delta = {
        "action": "upsert_domain_lane",
        "lane_id": "candidate_fails",
        "lane": {
            "purpose": "Failing candidate route must not be promoted.",
            "applies_to_paths": ["src/agentic_workspace/config.py"],
            "commands": ['python -c "import sys; sys.exit(5)"'],
        },
    }
    monkeypatch.setattr(
        workspace_runtime_proof,
        "_proof_route_independent_validation_commands",
        lambda **_: (["python -c \"print('independent ok')\""], "test-independent-validation-owner"),
    )

    with pytest.raises(WorkspaceUsageError, match="validation command failed"):
        _proof_route_repair_operation_payload(
            target_root=tmp_path,
            changed_paths=["src/agentic_workspace/config.py"],
            mode="apply",
            finding_id="finding-candidate-fails",
            authority_path=".agentic-workspace/config.toml",
            field_selector="assurance.domain_proof_lanes",
            expected_revision=revision,
            delta_json=json.dumps(delta),
            disposition="fixed",
            idempotency_key="proof-route-health:finding-candidate-fails:test",
        )

    assert authority_path.read_text(encoding="utf-8") == before
    assert not (tmp_path / PROOF_ROUTE_REPAIR_HISTORY_RELATIVE_PATH).exists()


def test_proof_route_repair_candidate_must_be_selected_for_repaired_scope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agentic_workspace import workspace_runtime_proof
    from agentic_workspace.config import WorkspaceUsageError
    from agentic_workspace.workspace_runtime_proof import (
        PROOF_ROUTE_REPAIR_HISTORY_RELATIVE_PATH,
        _proof_route_authority_revision,
        _proof_route_repair_operation_payload,
    )

    _write_repo_local_proof_target(tmp_path)
    authority_path = tmp_path / ".agentic-workspace" / "config.toml"
    before = authority_path.read_text(encoding="utf-8")
    revision = _proof_route_authority_revision(
        target_root=tmp_path,
        canonical_edit_surface=".agentic-workspace/config.toml [assurance.domain_proof_lanes]",
        selected_commands=[],
        changed_paths=["src/agentic_workspace/config.py"],
    )
    delta = {
        "action": "upsert_domain_lane",
        "lane_id": "wrong_scope_candidate",
        "lane": {
            "purpose": "Wrong-scope route must not repair config.py.",
            "applies_to_paths": ["README.md"],
            "commands": ["python -c \"print('wrong scope')\""],
        },
    }
    monkeypatch.setattr(
        workspace_runtime_proof,
        "_proof_route_independent_validation_commands",
        lambda **_: (["python -c \"print('independent ok')\""], "test-independent-validation-owner"),
    )

    with pytest.raises(WorkspaceUsageError, match="candidate route was not selected"):
        _proof_route_repair_operation_payload(
            target_root=tmp_path,
            changed_paths=["src/agentic_workspace/config.py"],
            mode="apply",
            finding_id="finding-wrong-scope",
            authority_path=".agentic-workspace/config.toml",
            field_selector="assurance.domain_proof_lanes",
            expected_revision=revision,
            delta_json=json.dumps(delta),
            disposition="fixed",
            idempotency_key="proof-route-health:finding-wrong-scope:test",
        )

    assert authority_path.read_text(encoding="utf-8") == before
    assert not (tmp_path / PROOF_ROUTE_REPAIR_HISTORY_RELATIVE_PATH).exists()


def test_proof_route_repair_replace_subsystem_proof_executes_candidate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agentic_workspace import workspace_runtime_proof
    from agentic_workspace.workspace_runtime_proof import _proof_route_authority_revision, _proof_route_repair_operation_payload

    _write_repo_local_proof_target(tmp_path)
    candidate = "python -c \"print('subsystem candidate ok')\""
    revision = _proof_route_authority_revision(
        target_root=tmp_path,
        canonical_edit_surface=".agentic-workspace/OWNERSHIP.toml [subsystems]",
        selected_commands=[],
        changed_paths=["src/agentic_workspace/workspace_runtime_proof.py"],
    )
    selection = {
        "changed_paths": ["src/agentic_workspace/workspace_runtime_proof.py"],
        "selected_commands": [{"command": candidate, "route_budget_seconds": 5, "route_id": "subsystem:workspace-cli-runtime"}],
        "route_refinement_required": {"status": "not-required"},
        "proof_route_strategy_decision": {"outcome": "focused"},
    }
    monkeypatch.setattr(workspace_runtime_proof, "_proof_selection_for_changed_paths", lambda **_: selection)
    monkeypatch.setattr(
        workspace_runtime_proof,
        "_proof_route_independent_validation_commands",
        lambda **_: (["python -c \"print('independent ok')\""], "test-independent-validation-owner"),
    )

    payload = _proof_route_repair_operation_payload(
        target_root=tmp_path,
        changed_paths=["src/agentic_workspace/workspace_runtime_proof.py"],
        mode="apply",
        finding_id="finding-subsystem-proof",
        authority_path=".agentic-workspace/OWNERSHIP.toml",
        field_selector="subsystems",
        expected_revision=revision,
        delta_json=json.dumps(
            {
                "action": "replace_subsystem_proof",
                "subsystem_id": "workspace-cli-runtime",
                "proof": [candidate],
            }
        ),
        disposition="fixed",
        idempotency_key="proof-route-health:finding-subsystem-proof:test",
    )

    receipt = payload["apply_receipt"]
    assert receipt["candidate_route_commands"] == [candidate]
    assert receipt["candidate_route_status"] == "passed"
    assert receipt["candidate_route_commands_complete"] is True


def test_proof_route_repair_upsert_hint_executes_candidate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agentic_workspace import workspace_runtime_proof
    from agentic_workspace.workspace_runtime_proof import _proof_route_authority_revision, _proof_route_repair_operation_payload

    _write_repo_local_proof_target(tmp_path)
    candidate = "python -c \"print('hint candidate ok')\""
    _write(
        tmp_path / ".agentic-workspace" / "proof-route-hints.json",
        json.dumps({"kind": "agentic-workspace/proof-route-hints/v1", "hints": []}),
    )
    revision = _proof_route_authority_revision(
        target_root=tmp_path,
        canonical_edit_surface=".agentic-workspace/proof-route-hints.json [hints]",
        selected_commands=[],
        changed_paths=["src/app.py"],
    )
    selection = {
        "changed_paths": ["src/app.py"],
        "selected_commands": [{"command": candidate, "route_budget_seconds": 5, "route_id": "hint:python"}],
        "route_refinement_required": {"status": "not-required"},
        "proof_route_strategy_decision": {"outcome": "focused"},
    }
    monkeypatch.setattr(workspace_runtime_proof, "_proof_selection_for_changed_paths", lambda **_: selection)
    monkeypatch.setattr(
        workspace_runtime_proof,
        "_proof_route_independent_validation_commands",
        lambda **_: (["python -c \"print('independent ok')\""], "test-independent-validation-owner"),
    )

    payload = _proof_route_repair_operation_payload(
        target_root=tmp_path,
        changed_paths=["src/app.py"],
        mode="apply",
        finding_id="finding-hint-proof",
        authority_path=".agentic-workspace/proof-route-hints.json",
        field_selector="hints",
        expected_revision=revision,
        delta_json=json.dumps(
            {
                "action": "upsert_hint",
                "hint_id": "python:app",
                "hint": {
                    "candidate_command": candidate,
                    "state": "confirmed",
                    "intent_type": "behavior-test",
                    "source": "test",
                    "confidence": "high",
                    "requires_live_confirmation": False,
                },
            }
        ),
        disposition="fixed",
        idempotency_key="proof-route-health:finding-hint-proof:test",
    )

    receipt = payload["apply_receipt"]
    assert receipt["candidate_route_commands"] == [candidate]
    assert receipt["candidate_route_status"] == "passed"
    assert receipt["candidate_route_commands_complete"] is True


def test_proof_route_repair_rejects_proposed_route_as_sole_validation_authority(tmp_path: Path) -> None:
    from agentic_workspace.config import WorkspaceUsageError
    from agentic_workspace.workspace_runtime_proof import _proof_route_authority_revision, _proof_route_repair_operation_payload

    _write_repo_local_proof_target(tmp_path)
    revision = _proof_route_authority_revision(
        target_root=tmp_path,
        canonical_edit_surface=".agentic-workspace/config.toml [assurance.domain_proof_lanes]",
        selected_commands=[],
        changed_paths=["src/agentic_workspace/config.py"],
    )
    delta = {
        "action": "upsert_domain_lane",
        "lane_id": "self_validating_route",
        "lane": {
            "purpose": "Self-validating route must not authorize itself.",
            "applies_to_paths": ["src/agentic_workspace/config.py"],
            "commands": ["make test-workspace"],
        },
    }

    with pytest.raises(WorkspaceUsageError, match="proposed route commands cannot overlap validation authority"):
        _proof_route_repair_operation_payload(
            target_root=tmp_path,
            changed_paths=["src/agentic_workspace/config.py"],
            mode="apply",
            finding_id="finding-self-validating",
            authority_path=".agentic-workspace/config.toml",
            field_selector="assurance.domain_proof_lanes",
            expected_revision=revision,
            delta_json=json.dumps(delta),
            disposition="fixed",
            idempotency_key="proof-route-health:finding-self-validating:test",
        )


def test_proof_route_repair_rejects_candidate_that_contains_validation_command(tmp_path: Path) -> None:
    from agentic_workspace.config import WorkspaceUsageError
    from agentic_workspace.workspace_runtime_proof import _proof_route_authority_revision, _proof_route_repair_operation_payload

    _write_repo_local_proof_target(tmp_path)
    revision = _proof_route_authority_revision(
        target_root=tmp_path,
        canonical_edit_surface=".agentic-workspace/config.toml [assurance.domain_proof_lanes]",
        selected_commands=[],
        changed_paths=["src/agentic_workspace/config.py"],
    )
    delta = {
        "action": "upsert_domain_lane",
        "lane_id": "partly_self_validating_route",
        "lane": {
            "purpose": "Partly self-validating route must not authorize itself.",
            "applies_to_paths": ["src/agentic_workspace/config.py"],
            "commands": ["make test-workspace", "uv run pytest tests/test_workspace_defaults_cli.py -q"],
        },
    }

    with pytest.raises(WorkspaceUsageError, match="proposed route commands cannot overlap validation authority"):
        _proof_route_repair_operation_payload(
            target_root=tmp_path,
            changed_paths=["src/agentic_workspace/config.py"],
            mode="apply",
            finding_id="finding-partly-self-validating",
            authority_path=".agentic-workspace/config.toml",
            field_selector="assurance.domain_proof_lanes",
            expected_revision=revision,
            delta_json=json.dumps(delta),
            disposition="fixed",
            idempotency_key="proof-route-health:finding-partly-self-validating:test",
        )


def test_proof_route_repair_rejects_equivalent_wrapper_self_validation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agentic_workspace import workspace_runtime_proof
    from agentic_workspace.config import WorkspaceUsageError
    from agentic_workspace.workspace_runtime_proof import _proof_route_authority_revision, _proof_route_repair_operation_payload

    _write_repo_local_proof_target(tmp_path)
    revision = _proof_route_authority_revision(
        target_root=tmp_path,
        canonical_edit_surface=".agentic-workspace/config.toml [assurance.domain_proof_lanes]",
        selected_commands=[],
        changed_paths=["src/agentic_workspace/config.py"],
    )
    delta = {
        "action": "upsert_domain_lane",
        "lane_id": "equivalent_self_validating_route",
        "lane": {
            "purpose": "Equivalent wrapper self-validation must not authorize itself.",
            "applies_to_paths": ["src/agentic_workspace/config.py"],
            "commands": ["uv run --active python scripts/check.py"],
        },
    }
    monkeypatch.setattr(
        workspace_runtime_proof,
        "_proof_route_independent_validation_commands",
        lambda **_: (["uv run python scripts/check.py"], "test-independent-validation-owner"),
    )

    with pytest.raises(WorkspaceUsageError, match="proposed route commands cannot overlap validation authority"):
        _proof_route_repair_operation_payload(
            target_root=tmp_path,
            changed_paths=["src/agentic_workspace/config.py"],
            mode="apply",
            finding_id="finding-equivalent-self-validating",
            authority_path=".agentic-workspace/config.toml",
            field_selector="assurance.domain_proof_lanes",
            expected_revision=revision,
            delta_json=json.dumps(delta),
            disposition="fixed",
            idempotency_key="proof-route-health:finding-equivalent-self-validating:test",
        )


def test_proof_route_repair_enforces_selected_route_budget(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agentic_workspace import workspace_runtime_proof
    from agentic_workspace.config import WorkspaceUsageError
    from agentic_workspace.workspace_runtime_proof import (
        PROOF_ROUTE_REPAIR_HISTORY_RELATIVE_PATH,
        _proof_route_authority_revision,
        _proof_route_repair_operation_payload,
    )

    _write_repo_local_proof_target(tmp_path)
    authority_path = tmp_path / ".agentic-workspace" / "config.toml"
    before = authority_path.read_text(encoding="utf-8")
    candidate = 'python -c "import time; time.sleep(1)"'
    revision = _proof_route_authority_revision(
        target_root=tmp_path,
        canonical_edit_surface=".agentic-workspace/config.toml [assurance.domain_proof_lanes]",
        selected_commands=[],
        changed_paths=["src/agentic_workspace/config.py"],
    )
    selection = {
        "changed_paths": ["src/agentic_workspace/config.py"],
        "selected_commands": [{"command": candidate, "route_budget_seconds": 0.01, "route_id": "domain:slow"}],
        "route_refinement_required": {"status": "not-required"},
        "proof_route_strategy_decision": {"outcome": "focused"},
    }
    monkeypatch.setattr(workspace_runtime_proof, "_proof_selection_for_changed_paths", lambda **_: selection)
    monkeypatch.setattr(
        workspace_runtime_proof,
        "_proof_route_independent_validation_commands",
        lambda **_: (["python -c \"print('independent ok')\""], "test-independent-validation-owner"),
    )

    with pytest.raises(WorkspaceUsageError, match="exceeded selected route budget"):
        _proof_route_repair_operation_payload(
            target_root=tmp_path,
            changed_paths=["src/agentic_workspace/config.py"],
            mode="apply",
            finding_id="finding-slow-budget",
            authority_path=".agentic-workspace/config.toml",
            field_selector="assurance.domain_proof_lanes",
            expected_revision=revision,
            delta_json=json.dumps(
                {
                    "action": "upsert_domain_lane",
                    "lane_id": "slow_budget_candidate",
                    "lane": {
                        "purpose": "Slow route must honor selected budget.",
                        "applies_to_paths": ["src/agentic_workspace/config.py"],
                        "commands": [candidate],
                    },
                }
            ),
            disposition="fixed",
            idempotency_key="proof-route-health:finding-slow-budget:test",
        )

    assert authority_path.read_text(encoding="utf-8") == before
    assert not (tmp_path / PROOF_ROUTE_REPAIR_HISTORY_RELATIVE_PATH).exists()


def test_proof_route_repair_audit_rejects_residual_ordinary_broad_proof() -> None:
    from agentic_workspace.config import WorkspaceUsageError
    from agentic_workspace.workspace_runtime_proof import _proof_route_audit_repaired_candidate

    selection = {
        "changed_paths": ["src/agentic_workspace/config.py"],
        "selected_commands": [
            {"command": "python -c \"print('focused ok')\"", "route_id": "domain:focused"},
            {"command": "make test-workspace", "proof_kind": "full-test", "route_id": "workspace_broad_suite"},
        ],
        "route_refinement_required": {"status": "not-required"},
        "proof_route_strategy_decision": {"outcome": "focused"},
    }

    with pytest.raises(WorkspaceUsageError, match="ordinary broad proof"):
        _proof_route_audit_repaired_candidate(
            selection=selection,
            candidate_commands=["python -c \"print('focused ok')\""],
        )


def test_proof_route_repair_receipt_uses_aw_admission_not_caller_sufficiency(tmp_path: Path) -> None:
    from agentic_workspace.config import WorkspaceUsageError
    from agentic_workspace.workspace_runtime_primitives import _record_proof_receipt_payload
    from agentic_workspace.workspace_runtime_proof import (
        PROOF_ROUTE_REPAIR_HISTORY_RELATIVE_PATH,
        _proof_route_append_jsonl,
        _proof_route_apply_receipt_id,
        _proof_route_authority_revision,
    )

    _write_repo_local_proof_target(tmp_path)
    command = "python -c \"print('route validation ok')\""
    revision = _proof_route_authority_revision(
        target_root=tmp_path,
        canonical_edit_surface=".agentic-workspace/config.toml [assurance.domain_proof_lanes]",
        selected_commands=[],
        changed_paths=["src/agentic_workspace/config.py"],
    )
    receipt_id = _proof_route_apply_receipt_id(
        finding_id="finding-aw-sufficiency",
        idempotency_key="proof-route-health:finding-aw-sufficiency:test",
        post_revision=revision,
        delta_digest="digest",
    )
    _proof_route_append_jsonl(
        tmp_path / PROOF_ROUTE_REPAIR_HISTORY_RELATIVE_PATH,
        {
            "kind": "agentic-workspace/proof-route-apply-receipt/v1",
            "id": receipt_id,
            "status": "applied",
            "finding_id": "finding-aw-sufficiency",
            "idempotency_key": "proof-route-health:finding-aw-sufficiency:test",
            "authority_path": ".agentic-workspace/config.toml",
            "field_selector": "assurance.domain_proof_lanes",
            "post_authority_revision": revision,
            "delta_digest": "digest",
            "validation_commands": [command],
            "validation_results": [{"command": command, "status": "passed", "returncode": 0}],
            "validation_status": "passed",
            "validation_commands_complete": True,
        },
    )

    with pytest.raises(WorkspaceUsageError, match="passed validation receipt"):
        _record_proof_receipt_payload(
            target_root=tmp_path,
            command=command,
            result="failed",
            changed_paths=["src/agentic_workspace/config.py"],
            receipt_repair_finding_id="finding-aw-sufficiency",
            receipt_repair_authority_revision=revision,
            receipt_repair_disposition="fixed",
            receipt_repair_idempotency_key="proof-route-health:finding-aw-sufficiency:test",
            receipt_claim_sufficiency="sufficient",
        )

    assert not (tmp_path / ".agentic-workspace" / "local" / "proof-receipts" / "last.json").exists()


def test_proof_changed_selector_uses_focused_domain_route(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _append_focused_proof_runtime_lane(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_proof.py", "VALUE = 1\n")
    _write(tmp_path / "tests" / "test_workspace_proof_cli.py", "def test_changed_selector():\n    assert True\n")

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    answer = payload.get("answer", payload)
    lane = next(lane for lane in answer["selected_lanes"] if lane["id"] == "domain:proof_runtime")

    assert lane["execution_mode"] == "serial-recommended"
    assert lane["domain_lane"]["source"] == ".agentic-workspace/config.toml [assurance.domain_proof_lanes]"
    assert lane["domain_lane"]["purpose"] == "Focused proof runtime behavior."
    assert "make test-workspace" not in answer["required_commands"]
    assert "focused proof does not exercise the changed behavior" in lane["escalate_when"]
    assert answer["focused_route_coverage_audit"]["status"] == "covered"


def test_pr_comment_delta_maps_to_its_focused_proof_owner_only() -> None:
    target_root = Path(__file__).resolve().parents[1]
    selection = workspace_runtime_proof._proof_selection_for_changed_paths(
        changed_paths=["scripts/github/pr_comment_delta.py"],
        target_root=target_root,
        include_durable_intent=False,
        include_assurance_requirements=False,
        include_routine_work_context=False,
        include_runtime_diagnostics=False,
        include_test_strategy_check=False,
    )

    lane_ids = {lane["id"] for lane in selection["selected_lanes"]}
    assert "domain:pr_comment_delta" in lane_ids
    assert "domain:review_stack_operations" not in lane_ids
    assert "uv run --active pytest tests/test_pr_comment_delta.py -q" in selection["required_commands"]
    assert "make test-workspace" not in selection["required_commands"]
    assert selection["focused_route_coverage_audit"]["status"] == "covered"


def test_generated_cli_catalogue_maps_to_its_freshness_owner() -> None:
    target_root = Path(__file__).resolve().parents[1]
    selection = workspace_runtime_proof._proof_selection_for_changed_paths(
        changed_paths=["docs/reference/cli-catalogue.md"],
        target_root=target_root,
        include_durable_intent=False,
        include_assurance_requirements=False,
        include_routine_work_context=False,
        include_runtime_diagnostics=False,
        include_test_strategy_check=False,
    )

    lane_ids = {lane["id"] for lane in selection["selected_lanes"]}
    assert "domain:generated_cli_catalogue" in lane_ids
    assert "uv run --active python scripts/generate/generate_contract_catalogues.py --check" in selection["required_commands"]
    assert selection["focused_route_coverage_audit"]["status"] == "covered"


def test_proof_receipt_resolves_selected_route_identity_when_caller_omits_it(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _append_focused_proof_runtime_lane(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_proof.py", "VALUE = 1\n")
    _write(tmp_path / "tests" / "test_workspace_proof_cli.py", "def test_changed_selector():\n    assert True\n")
    command = "uv run pytest tests/test_workspace_proof_cli.py -k changed_selector -q"

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "--record-receipt",
                "--receipt-command",
                command,
                "--receipt-result",
                "passed",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()

    receipt = json.loads((tmp_path / ".agentic-workspace" / "local" / "proof-receipts" / "last.json").read_text(encoding="utf-8"))
    execution = receipt["execution"]
    assert execution["route_id"] == "domain:proof_runtime"
    assert execution["command_id"] == execution["command_identity"]
    assert execution["route_identity_source"] == "proof_selection.selected_commands"


def test_task_selected_broad_commands_can_be_selected_and_recorded_with_identical_context(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _append_focused_proof_runtime_lane(tmp_path)
    _append_task_selected_broad_proof_lane(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_proof.py", "VALUE = 1\n")
    _write(tmp_path / "tests" / "test_workspace_proof_cli.py", "def test_changed_selector():\n    assert True\n")
    task = "Run broad workspace proof for this change."
    changed = "src/agentic_workspace/workspace_runtime_proof.py"
    expected_commands = ["make test-workspace-proof", "make test-workspace-session-review"]

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--task",
                task,
                "--changed",
                changed,
                "--select",
                "required_commands",
                "--format",
                "json",
            ]
        )
        == 0
    )
    required_commands = json.loads(capsys.readouterr().out)["values"]["required_commands"]
    for command in expected_commands:
        assert command in required_commands

    for command in expected_commands:
        assert (
            cli.main(
                [
                    "proof",
                    "--target",
                    str(tmp_path),
                    "--task",
                    task,
                    "--changed",
                    changed,
                    "--record-receipt",
                    "--receipt-command",
                    command,
                    "--receipt-result",
                    "passed",
                    "--format",
                    "json",
                ]
            )
            == 0
        )
        capsys.readouterr()
        receipt = json.loads((tmp_path / ".agentic-workspace" / "local" / "proof-receipts" / "last.json").read_text(encoding="utf-8"))
        assert receipt["command"] == command
        assert receipt["execution"]["route_id"] == "domain:workspace_broad_suite"
        assert receipt["execution"]["route_identity_source"] == "proof_selection.selected_commands"


@pytest.mark.parametrize("command", ["make test-workspace", "make test-workspace-contracts"])
def test_task_selected_broad_receipt_rejects_stale_or_unselected_command(tmp_path: Path, command: str) -> None:
    from agentic_workspace.config import WorkspaceUsageError
    from agentic_workspace.workspace_runtime_primitives import _record_proof_receipt_payload

    _write_repo_local_proof_target(tmp_path)
    _append_focused_proof_runtime_lane(tmp_path)
    _append_task_selected_broad_proof_lane(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_proof.py", "VALUE = 1\n")
    _write(tmp_path / "tests" / "test_workspace_proof_cli.py", "def test_changed_selector():\n    assert True\n")

    with pytest.raises(WorkspaceUsageError, match="does not resolve to a current selected proof command"):
        _record_proof_receipt_payload(
            target_root=tmp_path,
            command=command,
            result="passed",
            changed_paths=["src/agentic_workspace/workspace_runtime_proof.py"],
            task_text="Run broad workspace proof for this change.",
        )


def test_proof_receipt_rejects_unmatched_wrapper_command(tmp_path: Path) -> None:
    from agentic_workspace.config import WorkspaceUsageError
    from agentic_workspace.workspace_runtime_primitives import _record_proof_receipt_payload

    _write_repo_local_proof_target(tmp_path)
    _append_focused_proof_runtime_lane(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_proof.py", "VALUE = 1\n")
    _write(tmp_path / "tests" / "test_workspace_proof_cli.py", "def test_changed_selector():\n    assert True\n")

    with pytest.raises(WorkspaceUsageError, match="does not resolve to a current selected proof command"):
        _record_proof_receipt_payload(
            target_root=tmp_path,
            command='powershell -Command "uv run pytest tests/test_workspace_proof_cli.py -k changed_selector -q"',
            result="passed",
            changed_paths=["src/agentic_workspace/workspace_runtime_proof.py"],
        )


def test_proof_changed_selector_does_not_cover_unrelated_workspace_runtime(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _append_focused_proof_runtime_lane(tmp_path)
    _append_root_workspace_guidance_lane(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_core.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_core.py",
                "--select",
                "required_commands,selected_lanes,proof_route_maintenance",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["values"]
    assert "uv run pytest tests/test_workspace_proof_cli.py -k changed_selector -q" not in answer["required_commands"]
    assert answer["required_commands"] == [
        "make typecheck",
        "uv run python scripts/run_agentic_workspace.py report --target . --section runtime_mirror_consistency --format json",
        "uv run python scripts/run_agentic_workspace.py report --target . --section closeout_trust --format json",
    ]
    assert "domain:proof_runtime" not in [lane["id"] for lane in answer["selected_lanes"]]
    assert "domain:root_workspace_guidance" not in [lane["id"] for lane in answer["selected_lanes"]]


def test_proof_root_workspace_guidance_does_not_claim_unrelated_primitives_without_task_marker(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _append_root_workspace_guidance_lane(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_primitives.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--select",
                "required_commands,selected_lanes,focused_route_coverage_audit",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["values"]
    assert "domain:root_workspace_guidance" not in [lane["id"] for lane in answer["selected_lanes"]]
    assert answer["required_commands"] == [
        "make typecheck",
        "uv run python scripts/run_agentic_workspace.py report --target . --section runtime_mirror_consistency --format json",
        "uv run python scripts/run_agentic_workspace.py report --target . --section closeout_trust --format json",
    ]


def test_proof_changed_selector_domain_route_covers_multi_path_scope(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _append_focused_proof_runtime_lane(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_proof.py", "VALUE = 1\n")
    _write(tmp_path / "tests" / "test_workspace_proof_cli.py", "def test_changed_selector():\n    assert True\n")

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "tests/test_workspace_proof_cli.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    answer = payload.get("answer", payload)
    lanes = [lane for lane in answer["selected_lanes"] if lane["id"] == "domain:proof_runtime"]

    assert len(lanes) == 1
    assert lanes[0]["matched_paths"] == [
        "src/agentic_workspace/workspace_runtime_proof.py",
        "tests/test_workspace_proof_cli.py",
    ]
    assert answer["required_commands"].count("uv run pytest tests/test_workspace_proof_cli.py -k changed_selector -q") == 1
    assert "make test-workspace" not in answer["required_commands"]
    assert answer["focused_route_coverage_audit"]["missing_focused_route_paths"] == []


def test_proof_changed_selector_uses_domain_route_without_broad_coverage_fallback(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _append_session_logging_lane(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "session_logging.py", "VALUE = 1\n")
    _write(tmp_path / "tests" / "test_workspace_session_logging.py", "def test_session_logging():\n    assert True\n")

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/session_logging.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    lane = next(lane for lane in answer["selected_lanes"] if lane["id"] == "domain:session_logging")

    assert lane["domain_lane"]["purpose"] == "Focused session logging behavior."
    assert answer["required_commands"] == ["uv run pytest tests/test_workspace_session_logging.py -q"]
    assert answer["proof_narrowness"]["status"] == "narrow_required"
    assert "does not authorize broad-suite fallback" in answer["focused_route_coverage_audit"]["coverage_evidence"]["rule"]


def test_proof_changed_selector_reports_missing_focused_route_as_maintenance_gap(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _append_focused_proof_runtime_lane(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "unknown_runtime.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/unknown_runtime.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    audit = answer["focused_route_coverage_audit"]

    assert audit["status"] == "attention"
    assert audit["missing_focused_route_paths"] == ["src/agentic_workspace/unknown_runtime.py"]
    assert audit["maintenance_gap"]["status"] == "present"
    assert answer["route_refinement_required"]["status"] == "required"
    assert answer["route_refinement_required"]["uncovered_paths"] == ["src/agentic_workspace/unknown_runtime.py"]
    assert "make test-workspace" not in answer["required_commands"]
    assert "make lint-workspace" not in answer["required_commands"]
    assert answer["manual_verification"]["status"] == "route-refinement-required"
    assert answer["proof_next_decision"]["next"]["action"] == "route-refinement-required"


def test_proof_changed_selector_blocks_claim_for_partial_focused_route_gap(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _append_focused_proof_runtime_lane(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_proof.py", "VALUE = 1\n")
    _write(tmp_path / "src" / "agentic_workspace" / "unknown_runtime.py", "VALUE = 1\n")
    _write(tmp_path / "tests" / "test_workspace_proof_cli.py", "def test_changed_selector():\n    assert True\n")

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "src/agentic_workspace/unknown_runtime.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]

    assert answer["route_refinement_required"]["status"] == "required"
    assert answer["route_refinement_required"]["uncovered_paths"] == ["src/agentic_workspace/unknown_runtime.py"]
    assert "uv run pytest tests/test_workspace_proof_cli.py -k changed_selector -q" in answer["required_commands"]
    assert "make test-workspace" not in answer["required_commands"]
    assert "make lint-workspace" not in answer["required_commands"]
    assert answer["manual_verification"]["status"] == "route-refinement-required"
    assert answer["proof_next_decision"]["next"]["action"] == "route-refinement-required"
    assert answer["proof_next_decision"]["next"]["command"] is None
    assert answer["proof_route_decision"]["manual_fallback"]["status"] == "route-refinement-required"


def test_proof_changed_reports_domain_route_inventory_audit(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _append_focused_proof_runtime_lane(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_proof.py", "VALUE = 1\n")
    _write(tmp_path / "tests" / "test_workspace_proof_cli.py", "def test_changed_selector():\n    assert True\n")

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    inventory = json.loads(capsys.readouterr().out)["answer"]["domain_proof_route_inventory_audit"]
    assert inventory["kind"] == "agentic-workspace/domain-proof-route-inventory-audit/v1"
    assert inventory["route_count"] == 1
    assert inventory["routes"][0]["id"] == "proof_runtime"
    assert inventory["routes"][0]["live_match_count"] == 2
    assert inventory["coverage_evidence"]["status"] == "advisory-only"


def test_proof_routine_context_surfaces_workflow_obligation_match(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[workflow_obligations.workspace_closeout]
summary = "Run workspace closeout checks."
stage = "closeout"
force = "required-before-closeout"
scope_tags = ["workspace"]
commands = ["agentic-workspace report --target . --section closeout_trust --format json"]
review_hint = "Workspace orchestration applies to workspace paths."
""",
    )

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/runtime.py",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    binding = answer["current_work_context"]
    assert binding["kind"] == "agentic-workspace/current-work-context/v1"
    assert binding["authority"] == "local-advisory-binding"
    routine = answer["routine_work_context"]
    assert routine["surface"] == "proof"
    assert routine["categories"]["authority"]["status"] == "attention"
    assert routine["categories"]["authority"]["signals"]["workflow_obligation_matches"] == 1
    assert routine["categories"]["evidence_proof"]["status"] == "attention"
    assert routine["categories"]["evidence_proof"]["signals"]["workflow_obligation_matches"] == 1
    assert routine["knowledge_authority_review"]["workflow_obligation_match_count"] == 1


def test_proof_routes_changed_path_to_verification_protocol(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "tests" / "test_runbook_review.py", "def test_runbook_review_fixture():\n    assert True\n")
    _write(
        tmp_path / ".agentic-workspace/verification/manifest.toml",
        """
schema_version = "agentic-workspace/verification-manifest/v1"

[scenarios.runbook_walkthrough]
protocol_id = "runbook_review"
title = "Runbook walkthrough"
steps = ["Review the recovery runbook"]
expected_observations = ["Recovery steps and owner are visible"]
pass_evidence_labels = ["manual_runbook_review"]
fail_evidence_labels = ["runbook_gap"]

[protocols.runbook_review]
title = "Runbook review"
purpose = "Manual verification for runbook changes."
applies_to_paths = ["docs/runbooks/**"]
scenario_refs = ["runbook_walkthrough"]
steps = ["Run the runbook walkthrough"]
expected_evidence = ["manual_runbook_review"]
review_owner = "ops-review"
review_aids = ["Record observations in the closeout evidence."]

[proof_routes.runbook_review_route]
protocol_refs = ["runbook_review"]
scenario_refs = ["runbook_walkthrough"]
commands = ["uv run pytest tests/test_runbook_review.py"]
review_aids = ["Record route-specific proof notes."]
proof_lane_hint = "runbook-verification"
""",
    )

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "docs/runbooks/recovery.md",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert answer["verification"]["active_count"] == 1
    assert answer["verification"]["evidence_status"][0]["state"] == "missing-evidence"
    lanes = {lane["id"]: lane for lane in answer["selected_lanes"]}
    assert "verification:runbook_review" in lanes
    assert lanes["verification:runbook_review"]["verification_scenario_refs"] == ["runbook_walkthrough"]
    assert lanes["verification:runbook_review"]["verification_proof_route_ids"] == ["runbook_review_route"]
    assert lanes["verification:runbook_review"]["required_commands"] == ["uv run pytest tests/test_runbook_review.py"]
    assert answer["routine_work_context"]["categories"]["evidence_proof"]["signals"]["active_verification_protocols"] == 1


def test_proof_routes_active_assurance_requirement_to_verification_protocol(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "tests" / "test_privacy.py", "def test_privacy_fixture():\n    assert True\n")
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance.proof_profiles.privacy]
required_commands = ["uv run pytest tests/test_privacy.py"]
review_aids = ["Review privacy data handling manually."]

[assurance.requirements.privacy_data]
level = "high"
applies_to_paths = ["src/privacy/**"]
required_evidence = ["manual_privacy_review"]
proof_profile = "privacy"
force = "required-before-closeout"
blocking_claims = ["claim-work-complete", "close-parent-lane"]
review_owner = "privacy-review"
""",
    )
    _write(
        tmp_path / ".agentic-workspace/verification/manifest.toml",
        """
schema_version = "agentic-workspace/verification-manifest/v1"

[protocols.privacy_manual_review]
title = "Privacy manual review"
purpose = "Repeatable review protocol for privacy-sensitive code."
applies_to_paths = ["src/privacy/**"]
assurance_requirement_refs = ["privacy_data"]
proof_profiles = ["privacy"]
expected_evidence = ["manual_privacy_review"]
review_owner = "privacy-review"
review_aids = ["Confirm data minimisation and retention assumptions."]
""",
    )

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/privacy/export.py",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert answer["verification"]["active_protocols"][0]["id"] == "privacy_manual_review"
    lanes = {lane["id"]: lane for lane in answer["selected_lanes"]}
    assert "assurance-requirement:privacy_data" in lanes
    assert "verification:privacy_manual_review" in lanes
    status = answer["assurance_requirements"]["evidence_status"][0]
    assert status["verification_protocols"][0]["protocol_id"] == "privacy_manual_review"
    assert status["verification_missing_evidence"] == ["manual_privacy_review"]
    obligations = answer["manual_proof_obligations"]
    assert obligations[0]["id"] == "verification:privacy_manual_review"
    assert obligations[0]["required"] is True
    assert obligations[0]["missing_evidence"] == ["manual_privacy_review"]
    assert obligations[0]["authority"]["authority"] == "verification-manual-protocol"
    required = answer["proof_obligations"]["required_proof"]
    assert required["manual_verification_required"] is True
    assert required["manual_obligation_count"] == 1
    assert required["manual_obligations"][0]["id"] == "verification:privacy_manual_review"


def test_proof_routes_manual_verification_protocol_without_command(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/verification/manifest.toml",
        """
schema_version = "agentic-workspace/verification-manifest/v1"

[protocols.retention_policy_review]
title = "Retention policy review"
purpose = "Manual verification for retention-sensitive changes."
applies_to_paths = ["privacy/**"]
expected_evidence = ["manual_retention_review"]
review_owner = "privacy-review"
authority_refs = ["docs/privacy-policy.md#retention", "regulation:P.3"]
steps = ["Read the retention rule", "Compare changed behavior to the rule"]
review_aids = ["Record whether regulation P.3 remains satisfied."]
""",
    )

    assert cli.main(["proof", "--target", str(tmp_path), "--changed", "privacy/export.txt", "--verbose", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    obligation = answer["manual_proof_obligations"][0]
    assert obligation["id"] == "verification:retention_policy_review"
    assert obligation["reference_material"] == ["docs/privacy-policy.md#retention", "regulation:P.3"]
    assert obligation["missing_evidence"] == ["manual_retention_review"]
    assert obligation["claim_boundary"] == "completion-claims-qualified-until-manual-evidence-recorded-or-waived"
    assert answer["proof_route_maintenance"]["status"] == "attention"
    assert answer["proof_route_maintenance"]["manual_obligation_count"] == 1
    route_health = answer["proof_route_maintenance"]["route_health"]
    assert all(finding["finding_class"] != "insufficient_evidence" for finding in route_health["findings"])


def test_proof_accumulates_repeated_changed_flags(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    script_path = tmp_path / "scripts" / "run_agentic_workspace.py"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text("print('ok')\n", encoding="utf-8")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--changed",
                "tests/test_workspace_proof_cli.py",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["answer"]["changed_paths"] == [
        "src/agentic_workspace/workspace_runtime_primitives.py",
        "tests/test_workspace_proof_cli.py",
    ]
    lanes = {lane["id"]: lane for lane in payload["answer"]["selected_lanes"]}
    assert "runtime_mirror_consistency" in lanes
    assert (
        "uv run python scripts/run_agentic_workspace.py report --target . --section runtime_mirror_consistency --format json"
        in lanes["runtime_mirror_consistency"]["required_commands"]
    )


def test_proof_tiny_profile_returns_next_validation_action(capsys) -> None:
    from agentic_workspace.workspace_runtime_proof import PROOF_TINY_SEMANTIC_BUDGET_BYTES

    assert (
        cli.main(
            [
                "proof",
                "--changed",
                "generated/workspace/python/cli.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    encoded = json.dumps(payload)
    assert payload["kind"] == "proof-next-decision/v1"
    assert set(payload) >= {
        "kind",
        "target",
        "selector",
        "identity",
        "next",
        "required_commands",
        "route",
        "receipt",
        "sufficiency",
        "claim_boundary",
        "detail_routes",
        "absence_states",
    }
    assert payload["selector"] == {"changed": ["generated/workspace/python/cli.py"]}
    assert payload["route"]["narrowness"]["status"] == "narrow_required"
    assert payload["route"]["narrowness"]["broad_suite_boundary_status"] == "explicit-escalation-required"
    assert "broad_suite_boundary_reason" not in payload["route"]["narrowness"]
    assert payload["next"]["action"] == "route-refinement-required"
    assert payload["next"]["command"] is None
    assert payload["manual_verification"]["status"] == "route-refinement-required"
    assert "make test-workspace" not in payload["required_commands"]
    assert payload.get("warnings", []) == []
    assert "answer" not in payload
    assert "selected_lanes" not in encoded
    assert "validation_plan" not in encoded
    assert "<paths>" in payload["detail_routes"]["select"]
    assert len(encoded) > PROOF_TINY_SEMANTIC_BUDGET_BYTES
    assert "manual-verification-required" in payload["expansion_reasons"]


def test_proof_tiny_semantic_budget_is_invocation_independent_and_fails_on_command_growth(capsys) -> None:
    from agentic_workspace.workspace_runtime_proof import (
        PROOF_TINY_SEMANTIC_BUDGET_BYTES,
        _proof_tiny_semantic_budget_bytes,
        _proof_tiny_semantic_budget_projection,
    )

    assert cli.main(["proof", "--changed", "generated/workspace/python/cli.py", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    configured = payload["detail_routes"]["verbose"].split(" proof ", 1)[0]
    sizes: set[int] = set()
    for invocation in ("agentic-workspace", "uv run python scripts/run_agentic_workspace.py", configured):
        rendered = json.loads(json.dumps(payload).replace(configured, invocation))
        sizes.add(_proof_tiny_semantic_budget_bytes(rendered))
        assert rendered["detail_routes"]["verbose"].startswith(invocation)

    assert len(sizes) == 1
    normalized = _proof_tiny_semantic_budget_projection(payload)
    assert str(Path.cwd()) not in json.dumps(normalized)

    grown = copy.deepcopy(payload)
    baseline_size = _proof_tiny_semantic_budget_bytes(grown)
    grown["detail_routes"]["verbose"] += "".join(f" --changed semantic/path-{index}.py" for index in range(40))
    grown_size = _proof_tiny_semantic_budget_bytes(grown)
    assert grown_size > baseline_size
    assert grown_size >= PROOF_TINY_SEMANTIC_BUDGET_BYTES


def test_proof_route_escalation_gate_blocks_generic_broad_fallback(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "generated/workspace/python/cli.py",
                "--select",
                "proof_route_escalation_gate,proof_narrowness,proof_route_strategy_decision,proof_next_decision,manual_verification",
                "--format",
                "json",
            ]
        )
        == 0
    )

    values = json.loads(capsys.readouterr().out)["values"]
    boundary = values["proof_narrowness"]["broad_suite_boundary"]
    gate = values["proof_route_escalation_gate"]
    assert boundary["status"] == "explicit-escalation-required"
    assert boundary["requires_explicit_escalation"] is True
    assert gate["status"] == "blocked-explicit-escalation-required"
    assert gate["requires_explicit_escalation"] is True
    assert gate["friction_inputs"]["recurring_validation_friction"] == "lifecycle-managed active validation-friction improvement signals"
    assert gate["friction_inputs"]["applicable_live_findings"] == []
    assert gate["friction_inputs"]["candidate_only_sources"] == ["session-log slow-command friction candidates"]
    assert gate["proof_route_strategy_decision"]["outcome"] == "broad-escalation-required"
    assert gate["cross_surface_projection"]["route_decision_surface"] == "proof_route_strategy_decision"
    assert values["proof_route_strategy_decision"]["claim_effect"] == "claim-blocked"
    assert values["proof_next_decision"]["next"]["action"] == "route-refinement-required"
    assert values["proof_next_decision"]["next"]["command"] is None
    assert values["manual_verification"]["status"] == "route-refinement-required"


def test_proof_changed_uses_available_target_makefile_targets(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "Makefile", "test:\n\tpytest\n\nlint:\n\truff check .\n\nmaintainer-surfaces:\n\ttrue\n")

    assert cli.main(["proof", "--target", str(tmp_path), "--changed", "llms.txt", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["required_commands"] == ["make test", "make lint"]
    assert payload["next"]["command"] == "make test"
    assert payload["next"]["route_source"] == "live-adapted-target-capability"
    assert payload["next"]["why"] == "behavior-test intent selected live-adapted-target-capability."
    assert payload["route"]["source"] == "live-adapted-target-capability"
    assert payload["route"]["authority"] == "live-target-capability"
    assert payload["route"]["health"] == {"status": "attention", "finding_count": 2}
    assert payload["route"]["narrowness"]["status"] == "broad_required"
    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "llms.txt", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)["answer"]
    assert payload["proof_route_selection"]["route_source"] == "live-adapted-target-capability"
    assert payload["proof_route_selection"]["manual_fallback"] is None
    assert payload["proof_route_selection"]["explanation_field"] == "proof_route_explanation"
    assert payload["proof_route_selection"]["next_action"]["command"] == "make test"
    assert payload["proof_route_selection"]["required_commands"] == ["make test", "make lint"]
    assert payload["proof_command_adjustments"] == [
        {
            "lane": "workspace_cli",
            "command": "make test-workspace",
            "replacement": "make test",
            "reason": "target Makefile does not define 'test-workspace'; using available 'test' target",
        },
        {
            "lane": "workspace_cli",
            "command": "make lint-workspace",
            "replacement": "make lint",
            "reason": "target Makefile does not define 'lint-workspace'; using available 'lint' target",
        },
    ]
    assert payload["target_proof_capabilities"]["make"]["targets"] == ["lint", "maintainer-surfaces", "test"]


def test_proof_changed_does_not_assume_makefile_exists(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "llms.txt",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["required_commands"] == []
    assert payload["next"]["action"] == "manual-verification"
    assert payload["next"]["command"] is None
    assert payload["manual_verification"]["status"] == "required"
    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "llms.txt", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)["answer"]
    assert payload["proof_route_selection"]["manual_fallback"]["unavailable_command_count"] == 0
    assert payload["proof_route_selection"]["selected_command"] is None
    assert payload["proof_route_selection"]["route_source"] == "manual-fallback"
    assert "no executable proof route" in payload["manual_verification"]["summary"]
    assert payload.get("unavailable_proof_commands", []) == []


def test_proof_retired_selector_returns_exact_replacement_command(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "llms.txt",
                "--select",
                "required_commands,next,target_proof_capabilities",
                "--format",
                "json",
            ]
        )
        == 2
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["replacement_selectors"] == {"target_proof_capabilities": "proof_next_decision"}
    assert payload["replacement_command"] == (
        "agentic-workspace proof --target . --select required_commands,next,proof_next_decision --format json"
    )
    assert payload["corrected_action"] == payload["replacement_command"]


def test_proof_changed_reports_manual_verification_templates(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert cli.main(["proof", "--target", str(tmp_path), "--changed", "llms.txt", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    templates = payload["manual_verification"]["templates"]
    assert templates == [
        {
            "kind": "manual-verification-template/v1",
            "intent_type": "behavior-test",
            "title": "Behavior verification",
            "trust": "lower-than-executable-proof",
            "checklist": [
                "Identify the behavior the changed paths are expected to affect.",
                "Inspect the implementation path and the user-visible or API-facing result.",
                "Exercise the smallest available manual scenario or explain why no scenario is available.",
            ],
            "evidence_to_record": [
                "changed behavior inspected",
                "scenario or reasoning used",
                "residual risk compared with executable tests",
            ],
        }
    ]


def test_proof_verbose_exposes_manual_fallback_decision_layers(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "llms.txt", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert answer["proof_route_selection"] == answer["proof_route_decision"]
    decision = answer["proof_route_selection"]
    assert decision["next_action"]["action"] == "manual-verification"
    assert decision["selected_command"] is None
    assert decision["manual_fallback"]["status"] == "required"
    assert decision["manual_fallback"]["unavailable_command_count"] == 0
    assert decision["critical_warnings"] == []
    explanation = answer["proof_route_explanation"]
    assert explanation["selected_commands"] == []
    assert explanation["unavailable_commands"] == []
    assert explanation["manual_verification"]["status"] == "required"
    assert explanation["manual_verification"]["templates"][0]["intent_type"] == "behavior-test"
    assert explanation["manual_verification"]["templates"][0]["trust"] == "lower-than-executable-proof"
    execution_evidence = explanation["proof_execution_evidence"]
    assert execution_evidence["kind"] == "proof-execution-evidence/v1"
    assert execution_evidence["status"] == "not-run-or-not-recorded"
    assert execution_evidence["state_model"] == ["selected", "run", "passed", "failed", "skipped", "unavailable", "waived", "missing"]
    assert execution_evidence["expected_commands"] == []
    assert execution_evidence["manual_verification_expected"] is True
    assert execution_evidence["receipt_reconciliation"]["commands"] == []
    assert execution_evidence["missing_evidence_diagnostics"]["not-run-or-not-recorded"] == (
        "no trusted receipt exists for this selected command"
    )
    explanations = answer["proof_command_explanations"]
    assert explanations["status"] == "present"
    assert explanations["required"] == []
    assert explanations["manual_or_unavailable"][0]["reason_classes"] == ["unavailable-manual"]
    assert explanations["manual_or_unavailable"][0]["blocking"] is True
    assert "optional-confidence" in explanations["reason_class_model"]


def test_proof_command_explanations_status_present_for_policy_blockers_only() -> None:
    explanations = workspace_runtime_proof._proof_command_explanations_payload(
        selected_commands=[],
        required_commands=[],
        optional_commands=[],
        unavailable_commands=[],
        host_policy_blocked_commands=[
            {
                "command": "npm test",
                "lane": "concern:no_npm_test",
                "reason": "host-configured proof profile disallows this command",
                "configured_command": "npm test",
            }
        ],
        manual_verification=None,
    )

    assert explanations["status"] == "present"
    assert explanations["required"] == []
    assert explanations["optional_confidence"] == []
    assert explanations["manual_or_unavailable"] == [
        {
            "command": "npm test",
            "lane": "concern:no_npm_test",
            "reason": "host-configured proof profile disallows this command",
            "reason_classes": ["explicit-config-policy"],
            "blocking": True,
            "configured_command": "npm test",
        }
    ]


def test_proof_changed_uses_target_package_json_scripts_without_makefile(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "package.json", json.dumps({"scripts": {"test": "vitest run", "lint": "eslint ."}}))

    assert cli.main(["proof", "--target", str(tmp_path), "--changed", "llms.txt", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["required_commands"] == ["npm test", "npm run lint"]
    assert payload["next"]["route_source"] == "live-adapted-target-capability"
    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "llms.txt", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)["answer"]
    assert payload["target_proof_capabilities"]["package_json"]["scripts"] == ["lint", "test"]
    assert payload["proof_command_adjustments"] == [
        {
            "lane": "workspace_cli",
            "command": "make test-workspace",
            "replacement": "npm test",
            "reason": "target repo has no Makefile; using package.json script for 'test' proof",
        },
        {
            "lane": "workspace_cli",
            "command": "make lint-workspace",
            "replacement": "npm run lint",
            "reason": "target repo has no Makefile; using package.json script for 'lint' proof",
        },
    ]
    assert "manual_verification" not in payload


def test_proof_changed_uses_subrepo_makefile_for_package_paths(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "pyproject.toml", '[tool.uv.workspace]\nmembers = ["packages/other", "packages/planning"]\n')
    _write(tmp_path / "packages" / "other" / "Makefile", "test:\n\tfalse\n\nlint:\n\tfalse\n")
    _write(
        tmp_path / "packages" / "planning" / "Makefile",
        "test:\n\tpytest\n\nlint:\n\truff check .\n\ntypecheck:\n\tmypy src\n",
    )
    _write(tmp_path / "packages" / "planning" / "src" / "repo_planning_bootstrap" / "installer.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "packages/planning/src/repo_planning_bootstrap/installer.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert answer["required_commands"] == [
        "cd packages/planning && make test",
        "cd packages/planning && make lint",
        "cd packages/planning && make typecheck",
    ]
    assert answer["target_proof_capabilities"]["make"] == {"available": False, "targets": []}
    project_roots = {project_root["path"]: project_root for project_root in answer["target_proof_capabilities"]["project_roots"]}
    assert project_roots["packages/other"]["changed_path_matched"] is False
    assert project_roots["packages/planning"]["changed_path_matched"] is True
    assert project_roots["packages/planning"]["make"]["targets"] == ["lint", "test", "typecheck"]
    assert "cd packages/planning && make test" in answer["target_proof_capabilities"]["candidate_commands"]
    assert "cd packages/planning && make typecheck" in answer["target_proof_capabilities"]["candidate_commands"]
    assert (
        answer["selected_commands"][0].items()
        >= {
            "kind": "proof-command/v1",
            "command": "cd packages/planning && make test",
            "cwd": "packages/planning",
            "run": "make test",
            "selected_from": "live-adapted-target-capability",
            "intent_type": "behavior-test",
            "lane": "planning_package",
            "required": True,
        }.items()
    )
    assert answer["selected_commands"][0]["execution_mode"] == "parallel-ok"
    assert answer["selected_commands"][0]["execution_class"] == "focused-local"
    assert answer["selected_commands"][0]["execution_owner"] == "local"
    assert answer["selected_commands"][0]["requirement_posture"] == "required"
    assert answer["selected_commands"][0]["proof_requirement"]
    assert answer["selected_commands"][0]["subject_contract"]["changed_paths"] == [
        "packages/planning/src/repo_planning_bootstrap/installer.py"
    ]
    assert answer["selected_commands"][0]["duration_class"] == "medium"
    assert answer["selected_commands"][0]["progress_contract"]["timeout_outcome"] == "timeout"
    assert answer["selected_commands"][0]["receipt_contract"]["binds"] == [
        "operation",
        "proof-subject-revision",
        "run-identity",
        "attempt-identity",
        "elapsed-cost",
        "outcome",
    ]
    assert answer["proof_route_selection"]["selected_command"] == {
        "command": "cd packages/planning && make test",
        "lane": "planning_package",
        "route_source": "live-adapted-target-capability",
        "route_authority": "live-target-capability",
        "fallback_status": "candidate-live-confirmed",
        "authority_surface": "target repo command discovery",
        "intent_type": "behavior-test",
        "cwd": "packages/planning",
        "run": "make test",
    }
    first_step = answer["validation_plan"]["required"][0]
    assert first_step["command"] == "cd packages/planning && make test"
    assert first_step["cwd"] == "packages/planning"
    assert first_step["run"] == "make test"
    assert answer["validation_plan"]["required"][2]["command"] == "cd packages/planning && make typecheck"
    assert answer.get("manual_verification") is None


def test_proof_changed_uses_subrepo_package_json_for_package_paths(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "pyproject.toml", '[tool.uv.workspace]\nmembers = ["packages/ui"]\n')
    _write(tmp_path / "packages" / "ui" / "package.json", json.dumps({"scripts": {"test": "vitest run", "lint": "eslint ."}}))
    _write(tmp_path / "packages" / "ui" / "src" / "index.ts", "export const value = 1;\n")

    assert cli.main(["proof", "--target", str(tmp_path), "--changed", "packages/ui/src/index.ts", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["required_commands"] == ["cd packages/ui && npm test", "cd packages/ui && npm run lint"]
    assert payload["next"]["command"] == "cd packages/ui && npm test"
    assert payload["next"]["cwd"] == "packages/ui"
    assert payload["next"]["run"] == "npm test"
    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "packages/ui/src/index.ts", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)["answer"]
    assert payload["proof_command_adjustments"] == [
        {
            "lane": "workspace_cli",
            "command": "make test-workspace",
            "replacement": "cd packages/ui && npm test",
            "replacement_cwd": "packages/ui",
            "source_path": "packages/ui/package.json",
            "reason": "target repo has no root Makefile; using subrepo package.json script for 'test' proof in packages/ui",
        },
        {
            "lane": "workspace_cli",
            "command": "make lint-workspace",
            "replacement": "cd packages/ui && npm run lint",
            "replacement_cwd": "packages/ui",
            "source_path": "packages/ui/package.json",
            "reason": "target repo has no root Makefile; using subrepo package.json script for 'lint' proof in packages/ui",
        },
    ]
    assert "manual_verification" not in payload


def test_proof_changed_treats_plain_python_project_as_discovery_candidate(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / "pyproject.toml",
        """
[project]
name = "demo"
version = "0.1.0"
dependencies = ["agentic-workspace"]
""",
    )
    _write(tmp_path / "uv.lock", "# lock\n")

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "pyproject.toml", "uv.lock", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert "uv run pytest" not in answer["required_commands"]
    assert answer["manual_verification"]["status"] == "required"
    pytest_capability = answer["target_proof_capabilities"]["python"]["pytest"]
    assert pytest_capability["status"] == "candidate"
    assert pytest_capability["authority"] == "candidate-discovery"
    assert answer["target_proof_capabilities"]["role_commands"] == {}
    learning = answer["host_repo_learning"]
    assert learning["authority_rule"].startswith("Host-repo heuristics may propose discovery candidates")
    assert learning["negative_evidence"]["status"] == "none"
    assert learning["negative_evidence"]["items"] == []
    assert answer["unavailable_commands"] == []


def test_proof_changed_uses_declared_pytest_dependency_as_confirmed_evidence(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / "pyproject.toml",
        """
[project]
name = "demo"
version = "0.1.0"
dependencies = ["pytest>=8"]
""",
    )

    assert cli.main(["proof", "--target", str(tmp_path), "--changed", "pyproject.toml", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert "uv run pytest" in payload["required_commands"]
    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "pyproject.toml", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)["answer"]
    pytest_capability = payload["target_proof_capabilities"]["python"]["pytest"]
    assert pytest_capability["status"] == "confirmed"
    assert pytest_capability["evidence"] == [
        {"state": "confirmed", "source": "declared-dependency", "path": "pyproject.toml:project.dependencies"}
    ]


def test_proof_changed_release_version_surface_exposes_named_release_profile(capsys) -> None:
    repo_root = Path(__file__).resolve().parents[1]

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(repo_root),
                "--changed",
                "pyproject.toml",
                "--select",
                "selected_lanes,required_commands,release_proof_profile",
                "--format",
                "json",
            ]
        )
        == 0
    )

    values = json.loads(capsys.readouterr().out)["values"]
    lane_ids = [lane["id"] for lane in values["selected_lanes"]]
    assert "coordinated_release_proof" in lane_ids
    assert "make test-workspace" in values["required_commands"]
    assert "make test-memory" not in values["required_commands"]
    assert "make test-planning" not in values["required_commands"]
    assert "make test-verification" not in values["required_commands"]
    assert any("scripts/check/check_generated_command_packages.py" in command for command in values["required_commands"])
    assert any("scripts/check/run_operation_conformance_tests.py --target all" in command for command in values["required_commands"])
    assert any("pytest tests/test_release_workflows.py -q" in command for command in values["required_commands"])

    profile = values["release_proof_profile"]
    assert profile["kind"] == "agentic-workspace/release-proof-profile/v1"
    assert profile["id"] == "coordinated-release-proof"
    assert profile["status"] == "required"
    assert profile["matched_paths"] == ["pyproject.toml"]
    groups = {group["id"]: group for group in profile["groups"]}
    assert groups["workspace-runtime"]["proof_purpose"] == "behavioral"
    assert groups["memory-package"]["commands"] == []
    assert groups["planning-package"]["commands"] == []
    assert groups["verification-package"]["commands"] == []
    assert groups["generated-command-package-freshness"]["proof_purpose"] == "freshness-parity"
    assert any(
        "scripts/check/check_generated_command_packages.py" in command
        for command in groups["generated-command-package-freshness"]["commands"]
    )
    assert len(groups["operation-conformance"]["commands"]) == 1
    assert "scripts/check/run_operation_conformance_tests.py --target all" in groups["operation-conformance"]["commands"][0]
    assert groups["release-defaults-version-authority"]["proof_purpose"] == "release-authority"
    assert any(
        "pytest tests/test_release_workflows.py -q" in command for command in groups["release-defaults-version-authority"]["commands"]
    )
    assert profile["selection_posture"] == "focused-release-runtime"
    assert profile["package_dependencies"][0]["requirement"] == "agentic-workspace-package-release-integrity"
    assert profile["package_dependencies"][0]["subject_dependency"] == ["pyproject.toml"]
    assert profile["command_dependencies"][0]["requirement"] == "coordinated-release-runtime-behavior"
    assert profile["cost_replay_evidence_ref"].endswith("issue-2645-proof-route-cost-replay.replay.json")


def test_proof_changed_release_package_surface_names_exact_package_dependency(capsys) -> None:
    repo_root = Path(__file__).resolve().parents[1]

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(repo_root),
                "--changed",
                "packages/planning/pyproject.toml",
                "--select",
                "required_commands,release_proof_profile",
                "--format",
                "json",
            ]
        )
        == 0
    )

    values = json.loads(capsys.readouterr().out)["values"]
    assert "make test-planning" in values["required_commands"]
    assert "make test-memory" not in values["required_commands"]
    assert "make test-verification" not in values["required_commands"]
    dependency = values["release_proof_profile"]["package_dependencies"][0]
    assert dependency["requirement"] == "agentic-workspace-planning-package-release-integrity"
    assert dependency["subject_dependency"] == ["packages/planning/pyproject.toml"]
    assert "agentic-workspace-planning package" in dependency["distinct_claim"]


def _coordinated_release_projection(capsys) -> dict[str, object]:
    repo_root = Path(__file__).resolve().parents[1]
    changed_paths = [
        "scripts/release/coordinated_release.py",
        "tests/test_coordinated_release.py",
        ".agentic-workspace/payload-provenance.json",
    ]

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(repo_root),
                "--changed",
                *changed_paths,
                "--select",
                "required_commands,release_proof_profile,focused_route_coverage_audit,route_refinement_required,proof_route_maintenance",
                "--format",
                "json",
            ]
        )
        == 0
    )
    return json.loads(capsys.readouterr().out)["values"]


def _write_unrelated_failed_proof_receipt(target_root: Path) -> None:
    receipt = {
        "kind": "agentic-workspace/proof-receipt/v1",
        "command": "make lint-workspace",
        "result": "failed",
        "recorded_at": "2026-08-28T10:03:34+00:00",
        "changed_paths": ["src/agentic_workspace/config.py", "tests/test_workspace_cli.py"],
        "execution": {
            "command_identity": "unrelated-lint-workspace",
            "command_id": "unrelated-lint-workspace",
            "result": "failed",
            "exit_state": "failed",
            "claim_sufficiency": "not-reviewed",
            "route_id": "workspace_cli",
            "route_identity_source": "test-fixture",
        },
    }
    receipt_root = target_root / ".agentic-workspace" / "local" / "proof-receipts"
    _write(receipt_root / "last.json", json.dumps(receipt, indent=2) + "\n")
    _write(receipt_root / "history.jsonl", json.dumps(receipt, sort_keys=True) + "\n")


def test_coordinated_release_replay_removes_unrelated_planning_runs_and_preserves_claim_coverage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    with _test_owned_proof_local_state(
        monkeypatch,
        canonical_root=repo_root,
        local_state_root=tmp_path / "owned-local-state",
    ):
        values = _coordinated_release_projection(capsys)

    assert "make test-planning" not in values["required_commands"]
    assert values["focused_route_coverage_audit"]["status"] == "covered"
    assert values["focused_route_coverage_audit"]["missing_focused_route_paths"] == []
    assert values["route_refinement_required"]["status"] == "not-required"
    assert values["proof_route_maintenance"]["route_health"]["findings"] == []
    dependency = values["release_proof_profile"]["command_dependencies"][0]
    assert dependency["subject_dependency"] == [
        "scripts/release/coordinated_release.py",
        ".agentic-workspace/payload-provenance.json",
    ]
    assert dependency["requirement"] == "coordinated-release-runtime-behavior"
    assert dependency["distinct_claim"]

    evidence_path = repo_root / values["release_proof_profile"]["cost_replay_evidence_ref"]
    replay = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert replay["comparison"] == {
        "summed_work_seconds_removed": 171.6,
        "critical_path_seconds_removed": 171.6,
        "planning_suite_run_count_before": 2,
        "planning_suite_run_count_after": 0,
        "claim_coverage_preserved": True,
        "claim_coverage_evidence": replay["comparison"]["claim_coverage_evidence"],
    }
    assert {item["decision"] for item in replay["after"]["subject_decisions"]} == {
        "rerun-required",
        "reused",
        "excluded-unrelated",
    }


def test_coordinated_release_replay_isolated_from_unrelated_failed_local_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    failed_state_root = tmp_path / "failed-local-state"
    _write_unrelated_failed_proof_receipt(failed_state_root)

    with _test_owned_proof_local_state(
        monkeypatch,
        canonical_root=repo_root,
        local_state_root=failed_state_root,
    ):
        receipt_aware = _coordinated_release_projection(capsys)
    assert {finding["finding_class"] for finding in receipt_aware["proof_route_maintenance"]["route_health"]["findings"]} == {
        "route_execution_failure"
    }

    with _test_owned_proof_local_state(
        monkeypatch,
        canonical_root=repo_root,
        local_state_root=tmp_path / "owned-empty-local-state",
    ):
        isolated = _coordinated_release_projection(capsys)
    assert isolated["proof_route_maintenance"]["route_health"]["findings"] == []
    assert isolated["required_commands"] == receipt_aware["required_commands"]
    assert isolated["release_proof_profile"] == receipt_aware["release_proof_profile"]


def test_unrelated_planning_timing_route_emits_generic_bound_improvement_signal() -> None:
    import agentic_workspace.workspace_runtime_proof as proof_runtime

    changed_paths = [
        "scripts/release/coordinated_release.py",
        "tests/test_coordinated_release.py",
        ".agentic-workspace/payload-provenance.json",
    ]
    selected_command = {
        "command": "make test-planning",
        "command_identity": "planning-timing-suite",
        "route_id": "legacy-coordinated-release-proof",
        "lane": "legacy-coordinated-release-proof",
        "selected_from": "live-confirmed-proof-rule",
        "route_authority": "package-seed-or-default-route",
        "authority_surface": "package proof defaults",
        "proof_kind": "full-test",
        "subject_contract": {
            "kind": "agentic-workspace/proof-subject-request/v1",
            "changed_paths": changed_paths,
            "declared_dependencies": [],
            "dependency_binding": "implicit",
            "requirement": "",
            "distinct_claim": "",
        },
    }

    health = proof_runtime._proof_route_health_payload(
        selected_commands=[selected_command],
        stale_hints=[],
        invalid_hints=[],
        manual_missing=[],
        changed_paths=changed_paths,
        target_root=None,
        cli_invoke="agentic-workspace",
        focused_route_coverage_audit={},
        route_refinement_required={},
        unavailable_commands=[],
        proof_execution_evidence={},
    )

    finding = next(item for item in health["findings"] if item["finding_class"] == "excessive_breadth_cost")
    signal = finding["improvement_signal_candidate"]
    assert signal["candidate_kind"] == "workspace-improvement-signal-candidate/v1"
    assert signal["source_owner_identity"] == {
        "route_id": "legacy-coordinated-release-proof",
        "authority": "package-seed-or-default-route",
        "authority_surface": "package proof defaults",
        "selected_from": "live-confirmed-proof-rule",
    }
    assert signal["applicability_identity"]["status"] == "unbound"
    assert signal["applicability_identity"]["changed_paths"] == changed_paths
    assert signal["dependency_claim_identity"] == {
        "requirement": "",
        "distinct_claim": "",
        "command_identity": "planning-timing-suite",
    }
    assert signal["consumer_contract"]["consumer"] == "bounded-route-adaptation"
    assert health["improvement_signal_candidates"] == [signal]


def test_explicit_broad_dependency_and_claim_do_not_emit_disproportionate_signal() -> None:
    import agentic_workspace.workspace_runtime_proof as proof_runtime

    changed_paths = ["packages/planning/pyproject.toml"]
    health = proof_runtime._proof_route_health_payload(
        selected_commands=[
            {
                "command": "make test-planning",
                "command_identity": "planning-release-suite",
                "route_id": "coordinated_release_proof",
                "lane": "coordinated_release_proof",
                "proof_kind": "full-test",
                "subject_contract": {
                    "kind": "agentic-workspace/proof-subject-request/v1",
                    "changed_paths": changed_paths,
                    "declared_dependencies": changed_paths,
                    "dependency_binding": "explicit",
                    "requirement": "agentic-workspace-planning-package-release-integrity",
                    "distinct_claim": "the changed Planning package remains releasable",
                },
            }
        ],
        stale_hints=[],
        invalid_hints=[],
        manual_missing=[],
        changed_paths=changed_paths,
        target_root=None,
        cli_invoke="agentic-workspace",
        focused_route_coverage_audit={},
        route_refinement_required={},
        unavailable_commands=[],
        proof_execution_evidence={},
    )

    assert health["findings"] == []
    assert health["improvement_signal_candidates"] == []


def test_proof_changed_uses_python_pytest_capability_without_makefile(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / "pyproject.toml",
        """
[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 120
""",
    )

    assert cli.main(["proof", "--target", str(tmp_path), "--changed", "llms.txt", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["required_commands"] == ["uv run pytest", "uv run ruff check ."]
    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "llms.txt", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)["answer"]
    assert payload["target_proof_capabilities"]["python"]["available"] is True
    assert payload["target_proof_capabilities"]["python"]["pytest"]["status"] == "confirmed"
    assert payload["target_proof_capabilities"]["python"]["pytest"]["authority"] == "confirmed-repo-evidence"
    assert payload["target_proof_capabilities"]["role_commands"] == {
        "test": ["uv run pytest"],
        "lint": ["uv run ruff check ."],
    }
    assert payload["proof_command_adjustments"] == [
        {
            "lane": "workspace_cli",
            "command": "make test-workspace",
            "replacement": "uv run pytest",
            "reason": "target repo has no Makefile; using detected 'test' proof capability",
        },
        {
            "lane": "workspace_cli",
            "command": "make lint-workspace",
            "replacement": "uv run ruff check .",
            "reason": "target repo has no Makefile; using detected 'lint' proof capability",
        },
    ]
    assert "manual_verification" not in payload


def test_proof_changed_preserves_configured_active_uv_posture(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.local.toml",
        'schema_version = 1\n\n[workspace]\ncli_invoke = "uv run --frozen --active python scripts/run_agentic_workspace.py"\n',
    )
    _write(
        tmp_path / "pyproject.toml",
        '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n\n[tool.ruff]\nline-length = 120\n',
    )

    assert cli.main(["proof", "--target", str(tmp_path), "--changed", "llms.txt", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["required_commands"] == ["uv run --active pytest", "uv run --active ruff check ."]
    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "llms.txt", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)["answer"]
    posture = payload["proof_invocation_posture"]
    assert posture["configured_active_uv"] is True
    assert [item["status"] for item in posture["commands"]] == ["inserted", "inserted"]
    assert all("preserve the configured active uv environment" in item["reason"] for item in posture["commands"])


def test_proof_changed_reports_rust_go_and_java_capability_candidates(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "Cargo.toml", '[package]\nname = "demo"\nversion = "0.1.0"\n')
    _write(tmp_path / "go.mod", "module example.com/demo\n")
    _write(tmp_path / "pom.xml", "<project />\n")

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "docs/notes.md", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    capabilities = answer["target_proof_capabilities"]
    assert capabilities["rust"]["available"] is True
    assert capabilities["go"]["available"] is True
    assert capabilities["java"]["available"] is True
    assert capabilities["role_commands"]["test"] == ["cargo test", "go test ./...", "mvn test"]
    assert capabilities["role_commands"]["lint"] == ["cargo clippy --all-targets --all-features", "go vet ./..."]
    assert "cargo test" in capabilities["candidate_commands"]
    assert "go vet ./..." in capabilities["candidate_commands"]
    assert "mvn test" in capabilities["candidate_commands"]


def test_proof_changed_reports_live_confirmed_learned_route_hints(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "package.json", json.dumps({"scripts": {"test": "vitest run", "lint": "eslint ."}}))
    _write(
        tmp_path / ".agentic-workspace" / "proof-route-hints.json",
        json.dumps(
            {
                "kind": "agentic-workspace/proof-route-hints/v1",
                "schema_version": "proof-route-hints/v1",
                "source": "lifecycle-discovery",
                "rule": "Advisory proof route hints are not host policy; proof selection must live-confirm them before emitting commands.",
                "hints": [
                    {
                        "id": "package-json:test",
                        "intent_type": "behavior-test",
                        "candidate_command": "npm test",
                        "source": "package-json",
                        "source_path": "package.json",
                        "confidence": "medium",
                        "requires_live_confirmation": True,
                    },
                    {
                        "id": "package-json:stale",
                        "intent_type": "static-check",
                        "candidate_command": "npm run stale",
                        "source": "package-json",
                        "source_path": "package.json",
                        "confidence": "medium",
                        "requires_live_confirmation": True,
                    },
                ],
            }
        ),
    )

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "src/app.ts", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    hints = answer["learned_route_hints"]
    assert hints["status"] == "loaded"
    assert hints["confirmed"][0]["candidate_command"] == "npm test"
    assert hints["confirmed"][0]["confirmation"] == "live-confirmed"
    assert hints["stale"][0]["candidate_command"] == "npm run stale"
    assert hints["stale"][0]["confirmation"] == "stale-or-unavailable"
    assert hints["lifecycle"]["state_counts"] == {
        "candidate": 2,
        "confirmed": 0,
        "invalid-authority": 0,
        "negative": 0,
        "stale": 0,
        "superseded": 0,
    }
    assert hints["lifecycle"]["bucket_counts"]["confirmed"] == 1
    assert "invalid-authority" in {state["state"] for state in hints["lifecycle"]["state_model"]}
    decision = answer["proof_route_selection"]
    assert decision["critical_warnings"] == ["1 learned route hint(s) are stale or unavailable."]
    assert decision["selected_command"]["command"] == "npm test"
    explanation = answer["proof_route_explanation"]
    assert explanation["proof_intents"][0]["kind"] == "proof-intent/v1"
    assert explanation["target_capabilities"]["package_json"]["scripts"] == ["lint", "test"]
    assert explanation["setup_adopt_route_learning"] == {
        "kind": "setup-adopt-proof-route-learning/v1",
        "status": "advisory-hints-loaded",
        "persistent_surface": ".agentic-workspace/proof-route-hints.json",
        "hint_count": 2,
        "confirmed_count": 1,
        "stale_count": 1,
        "negative_count": 0,
        "superseded_count": 0,
        "invalid_authority_count": 0,
        "lifecycle_field": "learned_route_hints.lifecycle",
        "route_map_decision": "use-advisory-hints-only",
        "reason": (
            "Setup/adopt-discovered route hints are persisted as advisory memory and must be live-confirmed before command selection."
        ),
        "separation": {
            "configured_policy": "host-owned proof profiles and disallowed commands",
            "live_target_capabilities": "current Makefile, package.json, language, and role-command discovery",
            "setup_adopt_learning": "advisory route hints from lifecycle discovery, never host policy",
        },
    }
    assert explanation["selected_commands"][0]["kind"] == "proof-command/v1"
    assert explanation["proof_execution_evidence"]["status"] == "not-run-or-not-recorded"
    assert answer["proof_next_decision"]["warnings"] == ["1 learned route hint(s) are stale or unavailable."]
    maintenance = answer["proof_route_maintenance"]
    assert maintenance["status"] == "attention"
    assert maintenance["stale_route_count"] == 1
    assert maintenance["new_capability_candidate_count"] >= 1
    reasons = {item["reason"] for item in maintenance["suggested_updates"]}
    assert "learned proof route is stale or unavailable" in reasons
    assert "new target proof capability needs route-table promotion" in reasons


def test_proof_changed_reuses_confirmed_memory_proof_route(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "src" / "app.py", "print('ok')\n")
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "proof-routes.md",
        """
# Proof routes

agentic-workspace-proof-route: {"state":"confirmed","intent_type":"behavior-test","candidate_command":"python -m compileall src","source":"memory","confidence":"high","requires_live_confirmation":false,"scope":"src","owner":"Memory","provenance":"manual verification passed on 2026-06-02","learned_at":"2026-06-02"}
""",
    )

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "src/app.py", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    hints = answer["learned_route_hints"]
    assert hints["source_counts"]["memory"] == 1
    assert hints["confirmed"][0]["candidate_command"] == "python -m compileall src"
    assert hints["confirmed"][0]["confirmation"] == "learned-confirmed"
    assert answer["proof_route_selection"]["selected_command"]["command"] == "python -m compileall src"
    assert answer["proof_route_selection"]["selected_command"]["route_source"] == "live-adapted-target-capability"
    reliance = answer["proof_route_selection"]["learned_route_reliance"]
    assert reliance["status"] == "present"
    assert reliance["material_to_required_proof"] is True
    assert reliance["items"][0]["command"] == "python -m compileall src"
    assert reliance["items"][0]["provenance"] == "manual verification passed on 2026-06-02"
    assert answer["proof_route_selection"]["closeout_disclosure"]["status"] == "required"
    assert answer["proof_route_explanation"]["learned_route_reliance"] == reliance
    learning = answer["host_repo_learning"]
    assert learning["confirmed_evidence"]["status"] == "present"
    assert "memory capture-note" in learning["confirmed_evidence"]["items"][0]["capture"]["command_to_run"]
    assert learning["actionable_next_steps"]["memory_note_entries"][0].startswith("agentic-workspace-proof-route:")


def test_proof_changed_closeout_summary_preserves_learned_route_receipt(tmp_path: Path, capsys) -> None:
    from agentic_workspace.proof_subject import build_proof_subject

    _init_git_repo(tmp_path)
    _write(tmp_path / "src" / "app.py", "print('ok')\n")
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "proof-routes.md",
        """
# Proof routes

agentic-workspace-proof-route: {"state":"confirmed","intent_type":"behavior-test","candidate_command":"python -m compileall src","source":"memory","confidence":"high","requires_live_confirmation":false,"scope":"src","owner":"Memory","provenance":"manual verification passed on 2026-06-02","learned_at":"2026-06-02"}
""",
    )
    receipt = {
        "kind": "agentic-workspace/proof-receipt/v1",
        "command": "python -m compileall src",
        "result": "passed",
        "changed_paths": ["src/app.py"],
        "recorded_at": "2026-07-06T10:00:00Z",
    }
    receipt["proof_subject"] = build_proof_subject(target_root=tmp_path, changed_paths=receipt["changed_paths"], command=receipt["command"])
    _write(
        tmp_path / ".agentic-workspace" / "local" / "proof-receipts" / "last.json",
        json.dumps(receipt),
    )

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "src/app.py", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    summary = answer["proof_closeout_summary"]
    assert summary["status"] == "sufficient-recorded"
    assert summary["changed_paths"] == ["src/app.py"]
    assert summary["route"]["source"] == "memory"
    assert summary["route"]["maturity"] == "learned-confirmed"
    assert summary["proof_results"] == [
        {
            "command": "python -m compileall src",
            "result": "passed",
            "receipt_state": "accepted",
            "execution_state": "missing",
            "evidence_source": "proof-receipt",
        }
    ]
    assert summary["remaining_gaps"] == []
    assert any(line.startswith("Route:") and "learned-confirmed" in line for line in summary["pr_validation_lines"])
    assert any(line == "Remaining gaps: none known." for line in summary["pr_validation_lines"])


def test_proof_closeout_treats_conservative_route_maturity_as_advisory_after_accepted_receipt() -> None:
    from agentic_workspace.workspace_runtime_proof import _proof_closeout_summary_payload

    command = "make test-workspace"
    summary = _proof_closeout_summary_payload(
        changed_paths=["src/agentic_workspace/workspace_runtime_proof.py"],
        selected_lanes=[{"id": "workspace_cli"}],
        proof_route_decision={
            "selected_command": {
                "command": command,
                "route_source": "live-confirmed-proof-rule",
                "route_authority": "package-seed-or-default-route",
                "fallback_status": "seed-fallback",
                "authority_surface": "package proof defaults",
            }
        },
        proof_command_explanations={"required": [{"command": command, "reason_classes": ["conservative-fallback"]}]},
        proof_execution_evidence={"commands": []},
        proof_receipt_reconciliation={"commands": [{"command": command, "evidence_state": "accepted"}]},
        proof_receipt_bridge={"status": "clear", "missing_receipt_count": 0},
        learned_route_reliance={"items": []},
        manual_verification=None,
        unavailable_commands=[],
        host_policy_blocked_commands=[],
    )

    assert summary["status"] == "sufficient-recorded"
    assert summary["remaining_gaps"] == []
    assert summary["route"]["maturity"] == "conservative-fallback"
    assert summary["route_maturity_advisories"] == [
        f"{command}: conservative fallback; narrower learned route evidence is missing or immature"
    ]
    assert summary["route_maturity_gaps"] == []
    assert summary["route_maturity"]["authority_established"] is True
    assert summary["route_maturity"]["coverage_established"] is True


def test_proof_closeout_keeps_conservative_maturity_blocking_without_route_authority() -> None:
    from agentic_workspace.workspace_runtime_proof import _proof_closeout_summary_payload

    command = "make test-workspace"
    summary = _proof_closeout_summary_payload(
        changed_paths=["src/agentic_workspace/workspace_runtime_proof.py"],
        selected_lanes=[{"id": "workspace_cli"}],
        proof_route_decision={"selected_command": {"command": command, "route_source": "fallback"}},
        proof_command_explanations={"required": [{"command": command, "reason_classes": ["conservative-fallback"]}]},
        proof_execution_evidence={"commands": []},
        proof_receipt_reconciliation={"commands": [{"command": command, "evidence_state": "accepted"}]},
        proof_receipt_bridge={"status": "clear", "missing_receipt_count": 0},
        learned_route_reliance={"items": []},
        manual_verification=None,
        unavailable_commands=[],
        host_policy_blocked_commands=[],
    )

    assert summary["status"] == "not-yet-sufficient"
    assert summary["route_maturity"]["status"] == "blocked"
    assert summary["route_maturity"]["authority_established"] is False
    assert summary["route_maturity_advisories"] == []
    assert summary["route_maturity_gaps"] == [f"{command}: conservative fallback; narrower learned route evidence is missing or immature"]


def test_proof_cli_accepts_covering_receipts_for_authoritative_conservative_route(tmp_path: Path, capsys) -> None:
    from agentic_workspace.proof_subject import build_proof_subject

    _init_git_repo(tmp_path)
    _write(tmp_path / "Makefile", "test:\n\tpytest\n\nlint:\n\truff check .\n")
    _write(tmp_path / "llms.txt", "proof route fixture\n")

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "llms.txt", "--format", "json"]) == 0
    first = json.loads(capsys.readouterr().out)["answer"]
    commands = first["required_commands"]
    receipts = [
        {
            "kind": "agentic-workspace/proof-receipt/v1",
            "command": command,
            "result": "passed",
            "changed_paths": ["llms.txt"],
            "recorded_at": f"2026-07-10T10:00:0{index}Z",
        }
        for index, command in enumerate(commands)
    ]
    for receipt in receipts:
        receipt["proof_subject"] = build_proof_subject(
            target_root=tmp_path, changed_paths=receipt["changed_paths"], command=receipt["command"]
        )
    _write(tmp_path / ".agentic-workspace/local/proof-receipts/history.jsonl", "\n".join(json.dumps(item) for item in receipts) + "\n")

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "llms.txt",
                "--format",
                "json",
            ]
        )
        == 0
    )
    answer = json.loads(capsys.readouterr().out)["answer"]
    summary = answer["proof_closeout_summary"]
    assert summary["status"] == "sufficient-recorded"
    assert answer["proof_receipt_reconciliation"]["status"] == "accepted"
    assert answer["proof_receipt_reconciliation"]["accepted_count"] == len(commands)


def test_proof_changed_exposes_receipt_bridge_for_unrecorded_commands(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    bridge = answer["proof_receipt_bridge"]
    reconciliation = answer["proof_receipt_reconciliation"]
    assert bridge["kind"] == "agentic-workspace/proof-receipt-bridge/v1"
    assert bridge["status"] == "action-required"
    assert bridge["missing_receipt_count"] == len(reconciliation["commands"])
    assert bridge["ready_to_record_count"] >= 1
    assert bridge["template_blocked_count"] == 0
    assert bridge["next_action"] == "record the first concrete proof receipt"
    assert "--record-receipt" in bridge["next_recording_command"]
    action = next(item for item in bridge["actions"] if item["command"] == "make test-workspace")
    assert action["status"] == "ready-to-record-after-run"
    assert action["next_action"] == "record the actual proof result after this concrete command has run"
    assert action["recording_command"] == action["record_passed_command"]
    assert action["receipt_state"] in {"not-run-or-not-recorded", "run-but-not-recorded"}
    assert "--record-receipt" in action["record_passed_command"]
    assert '--receipt-command "make test-workspace"' in action["record_passed_command"]
    assert "--receipt-result passed" in action["record_passed_command"]
    assert action["result_options"] == ["passed", "failed", "skipped", "waived"]
    assert action["result_contract"]["proof_sufficient"] == ["passed"]
    summary_bridge = answer["proof_closeout_summary"]["receipt_bridge"]
    assert summary_bridge == {
        "status": "action-required",
        "missing_receipt_count": bridge["missing_receipt_count"],
        "detail_selector": "proof_receipt_bridge",
    }

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "--select",
                "proof_closeout_summary",
                "--format",
                "json",
            ]
        )
        == 0
    )
    compact = json.loads(capsys.readouterr().out)
    assert compact["values"]["proof_closeout_summary"]["receipt_bridge"]["status"] == "action-required"
    assert "record_passed_command" not in json.dumps(compact)


def test_proof_receipt_bridge_marks_template_commands_unrecordable() -> None:
    from agentic_workspace.workspace_runtime_proof import _proof_receipt_bridge_payload

    bridge = _proof_receipt_bridge_payload(
        changed_paths=["src/example.py"],
        proof_receipt_reconciliation={
            "commands": [
                {
                    "command": "uv run pytest <paths>",
                    "evidence_state": "not-run-or-not-recorded",
                    "diagnostic": "no trusted receipt exists for this selected command",
                },
                {
                    "command": "make typecheck",
                    "evidence_state": "run-but-not-recorded",
                    "diagnostic": "receipt missing for this command",
                },
            ]
        },
        cli_invoke=REPO_LOCAL_CLI_INVOKE,
    )

    assert bridge["status"] == "action-required"
    assert bridge["ready_to_record_count"] == 1
    assert bridge["template_blocked_count"] == 1
    assert "--record-receipt" in bridge["next_recording_command"]
    template = next(action for action in bridge["actions"] if action["command"] == "uv run pytest <paths>")
    assert template["status"] == "instantiate-before-recording"
    assert template["placeholders"] == ["<paths>"]
    assert template["admission_reason"] == "unresolved-command-template"
    assert "Substitute every placeholder" in template["safe_recovery"]
    assert "recording_command" not in template
    assert template["next_action"] == "instantiate placeholders, run the concrete command, then record the actual result"


def test_every_bridge_result_is_admissible_but_only_passed_satisfies_proof() -> None:
    from agentic_workspace.proof_receipt_admission import proof_receipt_admission
    from agentic_workspace.workspace_runtime_proof import _proof_receipt_bridge_payload

    bridge = _proof_receipt_bridge_payload(
        changed_paths=["src/example.py"],
        proof_receipt_reconciliation={"commands": [{"command": "make test", "evidence_state": "missing"}]},
        cli_invoke=REPO_LOCAL_CLI_INVOKE,
    )
    for result in bridge["actions"][0]["result_options"]:
        admission = proof_receipt_admission(
            {
                "kind": "agentic-workspace/proof-receipt/v1",
                "command": "make test",
                "result": result,
                "recorded_at": "2026-07-11T10:00:00+00:00",
                "changed_paths": ["src/example.py"],
            }
        )
        assert admission["admitted"] is True
        assert admission["result_class"] == result
        assert admission["proof_sufficient"] is (result == "passed")


@pytest.mark.parametrize(
    ("result", "expected_state"),
    [("passed", "accepted"), ("failed", "recorded-failed"), ("skipped", "recorded-skipped"), ("waived", "recorded-waived")],
)
def test_every_bridge_result_reconciles_through_admission_contract(tmp_path: Path, result: str, expected_state: str) -> None:
    from agentic_workspace.proof_subject import build_proof_subject
    from agentic_workspace.workspace_runtime_proof import _proof_receipt_reconciliation_payload

    receipt_path = tmp_path / ".agentic-workspace/local/proof-receipts/last.json"
    receipt_path.parent.mkdir(parents=True)
    _write(tmp_path / "src/example.py", "example\n")
    receipt = {
        "kind": "agentic-workspace/proof-receipt/v1",
        "command": "make test",
        "result": result,
        "recorded_at": "2026-07-11T10:00:00+00:00",
        "changed_paths": ["src/example.py"],
    }
    receipt["proof_subject"] = build_proof_subject(target_root=tmp_path, changed_paths=receipt["changed_paths"], command=receipt["command"])
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    reconciliation = _proof_receipt_reconciliation_payload(
        target_root=tmp_path,
        required_commands=["make test"],
        changed_paths=["src/example.py"],
        selected_commands=[{"command": "make test", "lane": "workspace_cli"}],
    )
    state = reconciliation["commands"][0]
    assert state["evidence_state"] == expected_state
    assert state["evidence_state"] != "record-stale-untrusted"
    if result in {"skipped", "waived"}:
        assert state["proof_sufficient"] is False
        assert state["result_class"] == result


def test_proof_changed_projects_learned_route_model_for_two_route_classes(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "docs" / "runbook.md", "# Runbook\n")
    _write(tmp_path / "src" / "security" / "policy.py", "ALLOW = True\n")
    _write(tmp_path / "scripts" / "check_docs.py", "print('docs ok')\n")
    _write(tmp_path / "scripts" / "check_access.py", "print('access ok')\n")
    docs_route = {
        "state": "confirmed",
        "route_class": "docs-process",
        "intent_type": "static-check",
        "candidate_command": "python scripts/check_docs.py",
        "source": "memory",
        "confidence": "high",
        "requires_live_confirmation": False,
        "scope": "docs",
        "owner": "Memory",
        "provenance": "review feedback showed docs/process changes need path-reference checks",
        "learned_at": "2026-07-06",
        "risk_markers": ["docs-link-drift"],
        "evidence": [{"source": "review", "review_ref": "#1993", "summary": "docs path-reference misses recurred"}],
        "proof_classes": {
            "required": ["python scripts/check_docs.py"],
            "recommended": ["manual changed-link spot check"],
            "not_applicable": ["full workspace typecheck"],
        },
        "override_semantics": {
            "escalate_when": ["docs generator or published output changes"],
            "repo_policy_overrides": True,
            "rule": "Docs-process learned routes may not weaken generated documentation proof.",
        },
    }
    access_route = {
        "state": "confirmed",
        "route_class": "access-audit",
        "intent_type": "behavior-test",
        "candidate_command": "python scripts/check_access.py",
        "source": "memory",
        "confidence": "high",
        "requires_live_confirmation": False,
        "scope": "src/security",
        "owner": "Memory",
        "provenance": "access-control closeout required stronger route than generic test",
        "learned_at": "2026-07-06",
        "risk_markers": ["authorization", "audit"],
        "evidence": [{"source": "dogfood", "source_path": "tests/test_access_control.py", "summary": "access paths need focused checks"}],
        "proof_classes": {
            "required": ["python scripts/check_access.py"],
            "optional_confidence": ["manual policy-diff review"],
            "unavailable_manual": ["record unavailable audit harness evidence"],
        },
        "override_semantics": {
            "escalate_when": ["auth boundary changes", "user requests high assurance"],
            "requires_human_review_when": ["legal/compliance certification is claimed"],
        },
    }
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "proof-routes.md",
        "\n".join(
            [
                "# Proof routes",
                "",
                f"agentic-workspace-proof-route: {json.dumps(docs_route, sort_keys=True)}",
                f"agentic-workspace-proof-route: {json.dumps(access_route, sort_keys=True)}",
            ]
        ),
    )

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "docs/runbook.md",
                "src/security/policy.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    compact = json.loads(capsys.readouterr().out)
    assert "learned_proof_route_model" not in compact
    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "docs/runbook.md",
                "src/security/policy.py",
                "--select",
                "learned_proof_route_model",
                "--format",
                "json",
            ]
        )
        == 0
    )
    selected_model = json.loads(capsys.readouterr().out)["values"]["learned_proof_route_model"]
    assert selected_model["status"] == "selected"
    assert set(selected_model["route_classes"]) >= {"docs-process", "access-audit"}

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "docs/runbook.md",
                "src/security/policy.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    model = answer["learned_proof_route_model"]
    assert model["status"] == "selected"
    selected = {route["route_class"]: route for route in model["selected_routes"]}
    assert selected["docs-process"]["proof_classes"]["required"] == ["python scripts/check_docs.py"]
    assert selected["docs-process"]["proof_classes"]["recommended"] == ["manual changed-link spot check"]
    assert selected["docs-process"]["proof_classes"]["not_applicable"] == ["full workspace typecheck"]
    assert selected["access-audit"]["proof_classes"]["required"] == ["python scripts/check_access.py"]
    assert selected["access-audit"]["proof_classes"]["optional_confidence"] == ["manual policy-diff review"]
    assert selected["access-audit"]["proof_classes"]["unavailable_manual"] == ["record unavailable audit harness evidence"]
    assert selected["access-audit"]["override_semantics"]["escalate_when"] == [
        "auth boundary changes",
        "user requests high assurance",
    ]
    assert selected["docs-process"]["source"]["provenance"] == "review feedback showed docs/process changes need path-reference checks"
    assert "python scripts/check_docs.py" in answer["required_commands"]
    assert "python scripts/check_access.py" in answer["required_commands"]
    assert model["closeout_semantics"]["issue_closure"] == "learned proof route selection alone never authorizes issue or parent closure"


def test_proof_tiny_includes_closeout_summary_for_pr_validation(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "Makefile", "test:\n\tpytest\n\nlint:\n\truff check .\n")

    assert cli.main(["proof", "--target", str(tmp_path), "--changed", "llms.txt", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    summary = payload["sufficiency"]
    assert summary["remaining_gap_count"] == 4
    assert summary["status"] == "not-yet-sufficient"
    assert payload["claim_boundary"]["completion_claim_allowed"] is False


def test_proof_changed_memory_negative_route_suppresses_candidate(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "package.json", json.dumps({"scripts": {"test": "pytest"}}))
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "mistakes" / "proof-routes.md",
        """
# Failed proof routes

agentic-workspace-proof-route: {"state":"negative","intent_type":"behavior-test","candidate_command":"npm test","source":"memory","confidence":"high","requires_live_confirmation":true,"scope":"repo","owner":"Memory","provenance":"npm test failed because pytest is not installed","learned_at":"2026-06-02"}
""",
    )

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "src/app.ts", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert answer["learned_route_hints"]["negative"][0]["candidate_command"] == "npm test"
    assert "npm test" not in answer["target_proof_capabilities"]["candidate_commands"]
    assert answer["required_commands"] == []
    model = answer["learned_proof_route_model"]
    assert model["fallback"]["status"] == "used"
    assert model["routes"][0]["proof_classes"]["not_applicable"] == ["npm test"]
    assert model["routes"][0]["state"] == "negative"
    assert answer["proof_route_selection"]["selected_command"] is None
    assert answer["proof_route_selection"]["critical_warnings"] == ["1 learned negative route(s) suppressed candidate proof commands."]
    learning = answer["host_repo_learning"]
    assert learning["negative_evidence"]["status"] == "present"
    assert learning["negative_evidence"]["items"][0]["command"] == "npm test"
    assert learning["actionable_next_steps"]["status"] == "present"


def test_proof_changed_reports_proof_route_lifecycle_states(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "package.json", json.dumps({"scripts": {"test": "vitest run", "lint": "eslint ."}}))
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "proof-routes.md",
        """
# Proof route lifecycle

agentic-workspace-proof-route: {"state":"confirmed","intent_type":"static-check","candidate_command":"npm run lint","source":"memory","confidence":"high","requires_live_confirmation":false,"scope":"repo","owner":"Memory","provenance":"lint route confirmed in prior closeout","learned_at":"2026-06-02"}
agentic-workspace-proof-route: {"state":"stale","intent_type":"behavior-test","candidate_command":"npm run old-test","source":"memory","confidence":"medium","requires_live_confirmation":true,"scope":"repo","owner":"Memory","provenance":"old route was not found during setup","learned_at":"2026-06-02"}
agentic-workspace-proof-route: {"state":"negative","intent_type":"behavior-test","candidate_command":"npm test","source":"memory","confidence":"high","requires_live_confirmation":true,"scope":"repo","owner":"Memory","provenance":"npm test invokes the wrong runner","learned_at":"2026-06-02"}
agentic-workspace-proof-route: {"state":"superseded","intent_type":"behavior-test","candidate_command":"npm run legacy-test","source":"memory","confidence":"medium","requires_live_confirmation":true,"scope":"repo","owner":"Memory","provenance":"legacy route replaced by package lint route","learned_at":"2026-06-02","superseded_by":"npm run lint"}
agentic-workspace-proof-route: {"state":"confirmed","intent_type":"behavior-test","candidate_command":"npm run missing-owner","source":"memory","confidence":"high","requires_live_confirmation":false}
""",
    )

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "src/app.ts", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    hints = answer["learned_route_hints"]
    lifecycle = hints["lifecycle"]
    assert lifecycle["state_counts"] == {
        "candidate": 0,
        "confirmed": 1,
        "invalid-authority": 1,
        "negative": 1,
        "stale": 1,
        "superseded": 1,
    }
    assert lifecycle["bucket_counts"] == {
        "confirmed": 1,
        "stale": 1,
        "negative": 1,
        "superseded": 1,
        "invalid": 1,
    }
    assert hints["confirmed"][0]["candidate_command"] == "npm run lint"
    assert hints["negative"][0]["candidate_command"] == "npm test"
    assert hints["superseded"][0]["superseded_by"] == "npm run lint"
    assert hints["invalid"][0]["state"] == "invalid-authority"
    assert hints["invalid"][0]["original_state"] == "confirmed"
    assert "npm test" not in answer["target_proof_capabilities"]["candidate_commands"]
    warnings = answer["proof_next_decision"]["warnings"]
    assert "1 learned route lesson(s) are missing authoritative provenance metadata." in warnings
    assert "1 learned route hint(s) are stale or unavailable." in warnings
    assert "1 learned negative route(s) suppressed candidate proof commands." in warnings


def test_proof_changed_incomplete_confirmed_memory_route_is_not_authoritative(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "src" / "app.py", "print('ok')\n")
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "proof-routes.md",
        """
# Incomplete proof routes

agentic-workspace-proof-route: {"state":"confirmed","intent_type":"behavior-test","candidate_command":"python -m compileall src","source":"memory","confidence":"high","requires_live_confirmation":false}
""",
    )

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "src/app.py", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    hints = answer["learned_route_hints"]
    assert hints["confirmed"] == []
    assert hints["invalid"][0]["original_state"] == "confirmed"
    assert hints["invalid"][0]["state"] == "invalid-authority"
    assert hints["lifecycle"]["state_counts"]["invalid-authority"] == 1
    assert set(hints["invalid"][0]["missing_fields"]) == {"owner", "scope", "provenance", "learned_at"}
    assert answer["required_commands"] == []
    assert answer["proof_route_selection"]["selected_command"] is None
    learning = answer["host_repo_learning"]
    assert learning["invalid_learning_evidence"]["status"] == "present"
    assert (
        "candidate_command, state, intent_type, owner, scope, provenance, and learned_at" in learning["invalid_learning_evidence"]["rule"]
    )
    assert "recapture this proof-route lesson" in learning["invalid_learning_evidence"]["items"][0]["recovery"]


def test_proof_changed_incomplete_negative_memory_route_does_not_suppress_candidate(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "package.json", json.dumps({"scripts": {"test": "vitest run"}}))
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "mistakes" / "proof-routes.md",
        """
# Incomplete failed proof routes

agentic-workspace-proof-route: {"state":"negative","intent_type":"behavior-test","candidate_command":"npm test","source":"memory","confidence":"high","requires_live_confirmation":true}
""",
    )

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "src/app.ts", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    hints = answer["learned_route_hints"]
    assert hints["negative"] == []
    assert hints["invalid"][0]["original_state"] == "negative"
    assert hints["invalid"][0]["state"] == "invalid-authority"
    assert "npm test" in answer["target_proof_capabilities"]["candidate_commands"]
    assert answer["proof_route_selection"]["selected_command"]["command"] == "npm test"
    learning = answer["host_repo_learning"]
    assert learning["negative_evidence"]["status"] == "none"
    assert learning["invalid_learning_evidence"]["items"][0]["command"] == "npm test"


def test_proof_changed_host_policy_disallows_generic_discovered_commands(tmp_path: Path, capsys) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    _init_git_repo(tmp_path)
    _write(tmp_path / "package.json", json.dumps({"scripts": {"test": "vitest run", "lint": "eslint ."}}))
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        """
schema_version = 1

[assurance.proof_profiles.no_npm_test]
required_commands = []
optional_commands = []
review_aids = []
disallowed_commands = ["npm test"]
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "proof-route-hints.json",
        json.dumps(
            {
                "kind": "agentic-workspace/proof-route-hints/v1",
                "schema_version": "proof-route-hints/v1",
                "source": "lifecycle-discovery",
                "rule": "Advisory proof route hints are not host policy; proof selection must live-confirm them before emitting commands.",
                "hints": [
                    {
                        "id": "package-json:test",
                        "intent_type": "behavior-test",
                        "candidate_command": "npm test",
                        "source": "package-json",
                        "source_path": "package.json",
                        "confidence": "medium",
                        "requires_live_confirmation": True,
                    }
                ],
            }
        ),
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
[todo]
active_items = [
  { id = "plan-alpha", status = "in-progress", surface = ".agentic-workspace/planning/execplans/plan-alpha.plan.json", why_now = "prove host policy precedence." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json"
    record = planning_installer._build_execplan_record_from_todo_item(
        title="Plan Alpha",
        item_id="plan-alpha",
        status="in-progress",
        why_now="prove host policy precedence.",
        next_action="run proof selection.",
        done_when="host policy blocks disallowed command.",
    )
    record["adaptive_assurance"] = {
        "level": "medium",
        "reason": "host disallows npm test",
        "proof_profiles": ["no_npm_test"],
    }
    planning_installer._write_execplan_record(record_path=record_path, record=record)

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "src/app.ts", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert answer["learned_route_hints"]["confirmed"][0]["candidate_command"] == "npm test"
    assert "npm test" not in answer["required_commands"]
    assert "npm run lint" in answer["required_commands"]
    assert answer["configured_policy"][0]["disallowed_commands"] == ["npm test"]
    blocked_commands = answer["host_policy_blocked_commands"]
    assert {item["selected_by_lane"] for item in blocked_commands} == {"workspace_cli", "learned_route:package-json:test"}
    assert all(
        {
            "lane": "concern:no_npm_test",
            "proof_profile": "no_npm_test",
            "command": "npm test",
            "configured_command": "npm test",
            "reason": "host-configured proof profile disallows this command",
        }.items()
        <= item.items()
        for item in blocked_commands
    )
    assert answer["proof_route_selection"]["critical_warnings"] == ["Host proof policy blocked one or more candidate proof commands."]
    assert answer["proof_route_explanation"]["host_policy_blocked_commands"] == answer["host_policy_blocked_commands"]
    assert answer["proof_next_decision"]["warnings"] == ["Host proof policy blocked one or more candidate proof commands."]


def test_proof_verbose_explains_live_discovery_when_no_setup_adopt_route_hints(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "Makefile", "test:\n\tpytest\n\nlint:\n\truff check .\n")

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "llms.txt", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    learning = answer["proof_route_explanation"]["setup_adopt_route_learning"]
    assert learning["status"] == "live-discovery-sufficient"
    assert learning["hint_count"] == 0
    assert learning["route_map_decision"] == "no-persisted-route-map-needed"
    assert "live target capability discovery is sufficient" in learning["reason"]
    assert learning["separation"]["setup_adopt_learning"] == "advisory route hints from lifecycle discovery, never host policy"


def test_proof_changed_validation_plan_uses_resolved_cli_invoke(tmp_path: Path, capsys) -> None:
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        'schema_version = 1\n\n[workspace]\ncli_invoke = "uv run agentic-workspace"\n',
    )

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                ".agentic-workspace/planning/state.toml",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    step = payload["answer"]["validation_plan"]["required"][0]
    expected_target = Path(os.path.relpath(tmp_path, Path.cwd())).as_posix()
    assert step["command"] == f'uv run agentic-workspace summary --target "{expected_target}" --format json'
    assert step["run"] == f'uv run agentic-workspace summary --target "{expected_target}" --format json'


def test_proof_tiny_detail_commands_use_resolved_cli_invoke(tmp_path: Path, capsys) -> None:
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        'schema_version = 1\n\n[workspace]\ncli_invoke = "uv run agentic-workspace"\n',
    )

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "README.md",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["detail_routes"]["verbose"].startswith("uv run agentic-workspace proof ")
    assert payload["next"]["command"] is None or not payload["next"]["command"].startswith("agentic-workspace ")


def test_proof_changed_includes_active_assurance_concern_profiles(tmp_path: Path, capsys) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    _write(tmp_path / "tests" / "test_access_control.py", "def test_access_control_fixture():\n    assert True\n")
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        """
schema_version = 1

[assurance]
default_level = "medium"
strict_closeout = true

[assurance.proof_profiles.access_control]
required_commands = ["uv run pytest tests/test_access_control.py"]
optional_commands = ["uv run pytest tests/test_auth_integration.py"]
review_aids = [".agentic-workspace/agent-aids/access-control.md"]
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
[todo]
active_items = [
  { id = "plan-alpha", status = "in-progress", surface = ".agentic-workspace/planning/execplans/plan-alpha.plan.json", why_now = "prove concern-based proof." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json"
    record = planning_installer._build_execplan_record_from_todo_item(
        title="Plan Alpha",
        item_id="plan-alpha",
        status="in-progress",
        why_now="prove concern-based proof.",
        next_action="run proof selection.",
        done_when="concern proof appears.",
    )
    record["adaptive_assurance"] = {
        "level": "high",
        "reason": "touches access control",
        "agent_may_escalate": True,
        "agent_may_deescalate": False,
        "strict_closeout": True,
        "required_refs": ["security_refs"],
        "proof_profiles": ["access_control"],
        "required_gates": ["security-review"],
    }
    record["traceability_refs"] = {"security_refs": ["SEC-1"]}
    record["control_gates"] = [
        {
            "id": "security-review",
            "owner_role": "security",
            "required_for": ["access-control"],
            "status": "pending",
            "evidence": [],
            "blocking": True,
            "next_action": "obtain security review",
        }
    ]
    planning_installer._write_execplan_record(record_path=record_path, record=record)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                ".agentic-workspace/planning/state.toml",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert "uv run pytest tests/test_access_control.py" in answer["required_commands"]
    assert "uv run pytest tests/test_auth_integration.py" in answer["optional_commands"]
    assert answer["planning_assurance"]["adaptive_assurance"]["level"] == "high"
    assert answer["planning_assurance"]["missing_required_refs"] == []
    assert answer["planning_assurance"]["closeout_status"] == "blocked"
    assert answer["planning_assurance"]["trust_state"]["assurance_level"] == "high"
    assert answer["planning_assurance"]["trust_state"]["assurance_level_source"] == "explicit-slice-field"
    assert answer["planning_assurance"]["trust_state"]["gate_states"][0]["enforcement"] == "blocking"
    assert answer["planning_assurance"]["trust_state"]["ref_states"][0]["trust"] == "satisfied"
    assert answer["planning_assurance"]["trust_state"]["proof_profile_states"][0]["state"] == "selected"
    assert answer["planning_assurance"]["trust_state"]["proof_execution_evidence"]["counts"]["missing"] >= 1
    assert answer["planning_assurance"]["pending_blocking_gates"][0]["id"] == "security-review"
    concern_step = [step for step in answer["validation_plan"]["required"] if step.get("lane_id") == "concern:access_control"][0]
    assert concern_step["command"] == "uv run pytest tests/test_access_control.py"
    assert answer["selected_lanes"][-1]["id"] == "concern:access_control"
    assert answer["selected_lanes"][-1]["review_aids"] == [".agentic-workspace/agent-aids/access-control.md"]


def test_proof_changed_includes_matched_assurance_requirement_profile(tmp_path: Path, capsys) -> None:
    _write(tmp_path / "tests" / "privacy" / "test_privacy.py", "def test_privacy_fixture():\n    assert True\n")
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        """
schema_version = 1

[assurance.proof_profiles.privacy]
required_commands = ["uv run pytest tests/privacy -q"]
optional_commands = ["uv run pytest tests/privacy_integration -q"]
review_aids = ["docs/compliance/privacy.md"]

[assurance.requirements.privacy_data]
level = "high"
applies_to_paths = ["db/migrations/**"]
authority_refs = ["docs/compliance/privacy.md"]
required_evidence = ["authority_consulted"]
proof_profile = "privacy"
force = "required-before-closeout"
blocking_claims = ["claim-work-complete", "close-parent-lane"]
""",
    )

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "db/migrations/001_privacy.sql",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert "uv run pytest tests/privacy -q" in answer["required_commands"]
    assert "uv run pytest tests/privacy_integration -q" in answer["optional_commands"]
    assert answer["assurance_requirements"]["active"][0]["id"] == "privacy_data"
    lane = [item for item in answer["selected_lanes"] if item.get("requirement_id") == "privacy_data"][0]
    assert lane["proof_profile"] == "privacy"
    assert lane["applies_because"] == ["changed path matched db/migrations/**"]


def test_proof_changed_marks_missing_path_specific_proof_unavailable(tmp_path: Path, capsys) -> None:
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        """
schema_version = 1

[assurance.proof_profiles.model_harness]
required_commands = ["uv run pytest tests/test_model_cli_harness.py -q"]

[assurance.requirements.model_harness]
level = "medium"
applies_to_paths = ["scripts/model_cli_harness/**"]
authority_refs = ["docs/maintainer/test-knowledge-inventory.md"]
required_evidence = ["current harness proof selected"]
proof_profile = "model_harness"
force = "required-before-closeout"
""",
    )

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "scripts/model_cli_harness/run_model_cli_harness.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert "uv run pytest tests/test_model_cli_harness.py -q" not in answer["required_commands"]
    assert answer["unavailable_proof_commands"] == [
        {
            "lane": "assurance-requirement:model_harness",
            "command": "uv run pytest tests/test_model_cli_harness.py -q",
            "reason": "selected proof command references path-like arguments absent from the target repo",
            "missing_paths": "tests/test_model_cli_harness.py",
        }
    ]
    assert answer["unavailable_commands"] == [
        {
            "kind": "proof-command-unavailable/v1",
            "command": "uv run pytest tests/test_model_cli_harness.py -q",
            "lane": "assurance-requirement:model_harness",
            "reason": "selected proof command references path-like arguments absent from the target repo",
            "missing_paths": "tests/test_model_cli_harness.py",
        }
    ]
    assert answer["manual_verification"]["status"] == "required"
    assert answer["manual_verification"]["unavailable_commands"] == answer["unavailable_commands"]
    route_health = answer["proof_route_maintenance"]["route_health"]
    assert "execution_environment_mismatch" in {finding["finding_class"] for finding in route_health["findings"]}
    repair_packet = next(packet for packet in route_health["repair_packets"] if packet["finding_class"] == "execution_environment_mismatch")
    assert repair_packet["affected_route"] == "assurance-requirement:model_harness"
    assert repair_packet["claim_effect"] == "repair-required-before-route-claim"
    decision = answer["proof_decision"]
    assert decision["owner_coverage"]["status"] == "incomplete"
    assert "assurance-requirement:model_harness" in decision["owner_coverage"]["uncovered_owners"]
    assert decision["sufficiency"] == {
        "status": "insufficient-owner-coverage",
        "owner_coverage_complete": False,
        "route_currentness_complete": False,
        "selected_commands_passed": False,
        "claim_allowed": False,
        "rule": "Command success is not sufficient without complete current owner coverage.",
    }


def test_proof_selection_composes_feature_and_affected_owner_baselines() -> None:
    selection = workspace_runtime_proof._proof_selection_for_changed_paths(
        changed_paths=[
            "src/agentic_workspace/contracts/schemas/implementer_context.schema.json",
            "src/agentic_workspace/operating_decision.py",
            "src/agentic_workspace/workspace_runtime_startup.py",
        ],
        target_root=None,
        include_durable_intent=False,
        include_assurance_requirements=False,
        include_routine_work_context=False,
        include_runtime_diagnostics=False,
        include_test_strategy_check=False,
    )

    lane_ids = {lane["id"] for lane in selection["selected_lanes"]}
    assert {"contract_tooling", "workspace_cli"}.issubset(lane_ids)
    coverage = selection["proof_decision"]["owner_coverage"]
    covered_ids = set(coverage["covered_owners"])
    assert {"contract_tooling", "workspace_cli"}.issubset(covered_ids)
    assert "make test-workspace" in selection["required_commands"]


def test_proof_selection_keeps_affected_subsystem_gap_until_owner_acceptance_gate_is_declared(tmp_path: Path) -> None:
    _write_repo_local_proof_target(tmp_path)
    changed_path = "packages/planning/src/repo_planning_bootstrap/installer.py"
    _write(tmp_path / changed_path, "# fixture\n")
    ownership = tmp_path / ".agentic-workspace" / "OWNERSHIP.toml"
    ownership.write_text(
        ownership.read_text(encoding="utf-8")
        + """

[[subsystems]]
id = "planning"
paths = ["packages/planning/**"]
owns = ["planning semantics"]
""",
        encoding="utf-8",
    )
    config = tmp_path / ".agentic-workspace" / "config.toml"
    config.write_text(
        config.read_text(encoding="utf-8")
        + """

[assurance.domain_proof_lanes.planning_feature]
purpose = "Focused Planning feature proof."
applies_to_paths = ["packages/planning/**"]
commands = ["make test-planning"]
escalation = ["owner acceptance remains uncovered"]
claim_boundary = "focused-feature-only"
owner = "planning"
route_role = "behavior"
""",
        encoding="utf-8",
    )

    missing = workspace_runtime_proof._proof_selection_for_changed_paths(
        changed_paths=[changed_path],
        target_root=tmp_path,
        include_durable_intent=False,
        include_assurance_requirements=False,
        include_routine_work_context=False,
        include_runtime_diagnostics=False,
        include_test_strategy_check=False,
    )

    assert "domain:planning_feature" in {lane["id"] for lane in missing["selected_lanes"]}
    assert "subsystem:planning" in missing["proof_decision"]["owner_coverage"]["uncovered_owners"]
    assert missing["proof_decision"]["sufficiency"]["claim_allowed"] is False
    assert missing["proof_decision"]["safe_claim_now"]["state"] == "proof-missing"

    ownership.write_text(
        ownership.read_text(encoding="utf-8").replace(
            'owns = ["planning semantics"]',
            'owns = ["planning semantics"]\nproof = ["make check-planning-nosync"]',
        ),
        encoding="utf-8",
    )
    covered = workspace_runtime_proof._proof_selection_for_changed_paths(
        changed_paths=[changed_path],
        target_root=tmp_path,
        include_durable_intent=False,
        include_assurance_requirements=False,
        include_routine_work_context=False,
        include_runtime_diagnostics=False,
        include_test_strategy_check=False,
    )

    assert "subsystem:planning" in covered["proof_decision"]["owner_coverage"]["covered_owners"]
    assert "make check-planning-nosync" in covered["required_commands"]
    assert "make test-planning" in covered["required_commands"]
    assert "make check-memory-nosync" not in covered["required_commands"]


def test_proof_changed_keeps_existing_path_specific_proof_required(tmp_path: Path, capsys) -> None:
    _write(tmp_path / "tests" / "test_model_cli_harness.py", "def test_harness_fixture():\n    assert True\n")
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        """
schema_version = 1

[assurance.proof_profiles.model_harness]
required_commands = ["uv run pytest tests/test_model_cli_harness.py -q"]

[assurance.requirements.model_harness]
level = "medium"
applies_to_paths = ["scripts/model_cli_harness/**"]
authority_refs = ["docs/maintainer/test-knowledge-inventory.md"]
required_evidence = ["current harness proof selected"]
proof_profile = "model_harness"
force = "required-before-closeout"
""",
    )

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "scripts/model_cli_harness/run_model_cli_harness.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert "uv run pytest tests/test_model_cli_harness.py -q" in answer["required_commands"]
    assert answer.get("unavailable_proof_commands", []) == []


def test_proof_changed_includes_matched_subsystem_assurance_profile(tmp_path: Path, capsys) -> None:
    _write(tmp_path / "tests" / "audit" / "test_audit.py", "def test_audit_fixture():\n    assert True\n")
    _write(
        tmp_path / ".agentic-workspace" / "OWNERSHIP.toml",
        """
[[subsystems]]
id = "audit-log"
paths = ["src/audit/**"]
owns = ["audit trail semantics"]
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        """
schema_version = 1

[assurance.proof_profiles.audit]
required_commands = ["uv run pytest tests/audit -q"]
optional_commands = ["uv run pytest tests/audit_integration -q"]
review_aids = ["docs/reviews/audit.md"]

[assurance.subsystem_profiles.audit-log]
assurance_level = "high"
requirement_refs = ["docs/system-requirements.md#auditability"]
required_evidence = ["requirement_grounding", "manual_review"]
proof_profile = "audit"
force = "required-before-closeout"
blocked_without_evidence = ["auditability-complete"]
claim_boundary = "subsystem-scoped"
""",
    )

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/audit/events.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert "uv run pytest tests/audit -q" in answer["required_commands"]
    assert "uv run pytest tests/audit_integration -q" in answer["optional_commands"]
    subsystem = answer["assurance_requirements"]["subsystem_assurance"]
    assert subsystem["matched_subsystem_ids"] == ["audit-log"]
    assert subsystem["effective_assurance_level"] == "high"
    lane = [item for item in answer["selected_lanes"] if item.get("requirement_id") == "subsystem:audit-log"][0]
    assert lane["proof_profile"] == "audit"
    assert lane["applies_because"] == ["changed path matched subsystem audit-log"]


def test_proof_current_includes_active_planning_assurance_requirement_profile(tmp_path: Path, capsys) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    _write(tmp_path / "tests" / "privacy" / "test_privacy.py", "def test_privacy_fixture():\n    assert True\n")
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        """
schema_version = 1

[assurance.proof_profiles.privacy]
required_commands = ["uv run pytest tests/privacy -q"]
optional_commands = ["uv run pytest tests/privacy_integration -q"]
review_aids = ["docs/compliance/privacy.md"]

[assurance.requirements.privacy_data]
level = "high"
applies_to_planning_refs = ["privacy_data"]
authority_refs = ["docs/compliance/privacy.md"]
required_evidence = ["authority_consulted"]
proof_profile = "privacy"
force = "required-before-closeout"
blocking_claims = ["claim-work-complete", "close-parent-lane"]
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
[todo]
active_items = [
  { id = "privacy-plan", status = "in-progress", surface = ".agentic-workspace/planning/execplans/privacy-plan.plan.json", why_now = "prove privacy requirement." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    record = planning_installer._build_execplan_record_from_todo_item(
        title="Privacy Plan",
        item_id="privacy-plan",
        status="in-progress",
        why_now="prove privacy requirement.",
        next_action="run proof selection.",
        done_when="privacy proof appears.",
    )
    record["adaptive_assurance"] = {
        "level": "high",
        "requirement_refs": ["privacy_data"],
        "strict_closeout": True,
    }
    _write_json(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "privacy-plan.plan.json", record)

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--current", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert "uv run pytest tests/privacy -q" in answer["required_commands"]
    assert "uv run pytest tests/privacy_integration -q" in answer["optional_commands"]
    assert answer["assurance_requirements"]["active"][0]["id"] == "privacy_data"
    lane = [item for item in answer["selected_lanes"] if item.get("requirement_id") == "privacy_data"][0]
    assert lane["proof_profile"] == "privacy"
    assert lane["applies_because"] == ["planning ref matched privacy_data"]


def test_proof_current_selects_active_plan_validation_commands(tmp_path: Path, capsys) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    _write(
        tmp_path / "tests" / "test_workspace_proof_cli.py",
        "def test_proof_current_selects_active_plan_validation_commands():\n    assert True\n",
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
[todo]
active_items = [
  { id = "validation-plan", status = "in-progress", surface = ".agentic-workspace/planning/execplans/validation-plan.plan.json", why_now = "prove current validation routing." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    record = planning_installer._build_execplan_record_from_todo_item(
        title="Validation Plan",
        item_id="validation-plan",
        status="in-progress",
        why_now="prove current validation routing.",
        next_action="run proof selection.",
        done_when="current proof names the active validation commands.",
    )
    record["validation_commands"] = [
        "uv run pytest tests/test_workspace_proof_cli.py::test_proof_current_selects_active_plan_validation_commands -q"
    ]
    _write_json(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "validation-plan.plan.json", record)

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--current", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert answer["required_commands"] == [
        "uv run pytest tests/test_workspace_proof_cli.py::test_proof_current_selects_active_plan_validation_commands -q"
    ]
    assert answer["selected_lanes"][0]["id"] == "planning:active_validation"
    assert "manual_verification" not in answer


def test_proof_changed_reports_compact_proof_execution_evidence_states(tmp_path: Path, capsys) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        """
schema_version = 1

[assurance]
strict_closeout = true

[assurance.proof_profiles.assurance_matrix]
required_commands = [
  "selected-command",
  "run-command",
  "pass-command",
  "fail-command",
  "skip-command",
  "unavailable-command",
  "waived-command",
]
optional_commands = []
review_aids = []
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
[todo]
active_items = [
  { id = "proof-evidence", status = "in-progress", surface = ".agentic-workspace/planning/execplans/proof-evidence.plan.json", why_now = "prove evidence states." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "proof-evidence.plan.json"
    record = planning_installer._build_execplan_record_from_todo_item(
        title="Proof Evidence",
        item_id="proof-evidence",
        status="in-progress",
        why_now="prove evidence states.",
        next_action="run proof selection.",
        done_when="proof evidence states appear.",
    )
    record["adaptive_assurance"] = {
        "level": "critical",
        "strict_closeout": True,
        "proof_profiles": ["assurance_matrix"],
    }
    record["proof_report"] = {
        "validation proof": "synthetic assurance commands",
        "proof achieved now": "mixed",
        "proof execution evidence": json.dumps(
            [
                {"command": "selected-command", "status": "selected", "evidence_ref": "local:selected"},
                {"command": "run-command", "status": "run", "evidence_ref": "local:run"},
                {"command": "pass-command", "status": "passed", "evidence_ref": "local:pass"},
                {"command": "fail-command", "status": "failed", "evidence_ref": "local:fail"},
                {"command": "skip-command", "status": "skipped", "reason": "not applicable"},
                {"command": "unavailable-command", "status": "unavailable", "reason": "tool missing"},
                {"command": "waived-command", "status": "waived", "reason": "covered by manual review"},
            ]
        ),
    }
    planning_installer._write_execplan_record(record_path=record_path, record=record)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                ".agentic-workspace/planning/state.toml",
                "--format",
                "json",
            ]
        )
        == 0
    )

    evidence = json.loads(capsys.readouterr().out)["answer"]["planning_assurance"]["trust_state"]["proof_execution_evidence"]
    assert evidence["state_model"] == ["selected", "run", "passed", "failed", "skipped", "unavailable", "waived", "missing"]
    assert evidence["counts"] == {
        "selected": 1,
        "run": 1,
        "passed": 1,
        "failed": 1,
        "skipped": 1,
        "unavailable": 1,
        "waived": 1,
        "missing": 2,
    }
    assert evidence["lower_trust_required_count"] == 7
    selected = next(item for item in evidence["commands"] if item["command"] == "selected-command")
    assert selected["trust"] == "lower-trust"
    run = next(item for item in evidence["commands"] if item["command"] == "run-command")
    assert run["trust"] == "lower-trust"
    waived = next(item for item in evidence["commands"] if item["command"] == "waived-command")
    assert waived["trust"] == "satisfied"
    assert waived["waiver_state"] == "waived-with-reason"


def test_proof_changed_selector_routes_agent_aid_changes_to_manifest_lane(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                ".agentic-workspace/agent-aids/scripts/workspace-validation/manifest.json",
                ".agentic-workspace/agent-aids/scripts/workspace-validation/workspace_validation.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert [lane["id"] for lane in answer["selected_lanes"]] == ["agent_aid_manifests"]
    assert answer["required_commands"] == ["uv run python scripts/check/check_agent_aids.py --quiet-success"]
    assert "candidate aids" in answer["selected_lanes"][0]["recovery_signal"]
    assert "uv run pytest tests -q" not in answer["required_commands"]


def test_proof_changed_selector_routes_readme_to_docs_review(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "README.md", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    docs_diff = "git diff -- README.md docs .agentic-workspace/docs packages/planning/README.md packages/memory/README.md"
    assert [lane["id"] for lane in answer["selected_lanes"]] == ["repo_docs_review"]
    assert answer["selected_lanes"][0]["proof_kind"] == "diff-review"
    assert answer["required_commands"] == [docs_diff]
    assert answer["selected_lanes"][0]["non_local_references"] == ["https://github.com/rickardvh/command-generation/blob/main/README.md"]
    assert "https://github.com" not in answer["required_commands"][0]
    assert "uv run pytest tests -q" not in answer["required_commands"]
    assert answer["surface_value_review"]["reviewed_paths"][0]["surface_class"] == "adapter_or_repo_intent_surface"


def test_proof_changed_selector_applies_learned_docs_process_route(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    docs_process_command = (
        "git diff -- README.md docs .agentic-workspace/docs packages/planning/README.md packages/memory/README.md "
        ".github/pull_request_template.md .github/ISSUE_TEMPLATE"
    )
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "docs-process-proof.md",
        f"""
# Docs/process proof

agentic-workspace-proof-route: {{"state":"confirmed","intent_type":"docs-diff-review","candidate_command":"{docs_process_command}","source":"memory","confidence":"high","requires_live_confirmation":false,"scope":"repo","owner":"Memory","provenance":"docs/process route confirmed from markdown path reference, template-burden, and local-tool coupling review","learned_at":"2026-07-06"}}
""",
    )
    _write(
        tmp_path / ".github" / "pull_request_template.md",
        """
# Pull Request

## Optional high-risk evidence

- Not applicable; no high-risk lanes.
""",
    )
    _write(tmp_path / ".github" / "ISSUE_TEMPLATE" / "bug.md", "# Bug\n")

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "README.md",
                ".github/pull_request_template.md",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    lane_ids = [lane["id"] for lane in answer["selected_lanes"]]
    assert "workspace_cli" not in lane_ids
    assert lane_ids[0] == "repo_docs_review"
    assert answer["docs_process_route"]["status"] == "active"
    assert answer["docs_process_route"]["route_maturity"] == "repo-learned"
    assert answer["required_commands"] == [docs_process_command]
    assert answer["proof_route_selection"]["selected_command"]["route_source"] == "repo-learned-proof-route"
    assert answer["proof_command_explanations"]["required"][0]["reason_classes"] == ["learned-repo-evidence"]
    assert answer["proof_closeout_summary"]["route"]["maturity"] == "learned-confirmed"
    assert answer["template_burden_review"]["status"] == "clear"
    assert answer["routing_reductions"][0]["from_lane"] == "workspace_cli"


def test_proof_changed_selector_reviews_markdown_repo_path_references(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _write(tmp_path / "docs" / "existing.md", "# Existing\n")
    _write(
        tmp_path / "docs" / "guide.md",
        """
# Guide

Concrete path: `docs/missing.md`
Valid path: [existing](docs/existing.md)
Example path: `docs/<area>/template.md`
Command snippet: `uv run python scripts/check.py`
Anchor only: [section](#local-anchor)
Remote link: [site](https://example.com/docs/missing.md)
""",
    )

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "docs/guide.md", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    review = answer["markdown_path_reference_review"]
    assert review["status"] == "attention-needed"
    assert review["changed_paths"] == ["docs/guide.md"]
    assert review["missing_count"] == 1
    assert review["valid_count"] == 1
    assert review["ambiguous_count"] == 2
    assert review["missing_references"][0]["reference"] == "docs/missing.md"
    assert review["missing_references"][0]["line"] == 4
    assert review["valid_references"][0]["reference"] == "docs/existing.md"
    assert {item["reference"] for item in review["ambiguous_references"]} == {
        "docs/<area>/template.md",
        "uv run python scripts/check.py",
    }
    route_learning = review["route_learning_evidence"]
    assert route_learning["candidate_route"] == "docs/process path-reference check"
    assert "--files docs/guide.md" in route_learning["capture_command"]
    assert route_learning["memory_note_entry"].startswith("agentic-workspace-proof-route:")
    assert '"intent_type": "static-check"' in route_learning["memory_note_entry"]


def test_proof_changed_selector_reviews_scoped_local_tool_coupling(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _write(
        tmp_path / "docs" / "guide.md",
        """
# Guide

This repository guidance must stay tool-neutral.
Contributors must run `agentic-workspace start` before opening a PR.
Optional local evidence may include `.agentic-workspace` proof receipts.
Agentic Workspace notes appear during local investigation.
""",
    )

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "docs/guide.md",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    review = answer["local_tool_coupling_review"]
    assert review["status"] == "attention-needed"
    assert review["flagged_count"] == 1
    assert review["accepted_optional_count"] == 1
    assert review["ambiguous_count"] == 1
    assert review["flagged_references"][0]["line"] == 5
    assert "mandatory repository-process" in review["flagged_references"][0]["reason"]
    assert ".agentic-workspace" in review["accepted_optional_references"][0]["matched_terms"]


def test_proof_changed_selector_does_not_globally_ban_local_tool_references(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _write(tmp_path / "docs" / "guide.md", "Local setup can mention `agentic-workspace start`.\n")

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "docs/guide.md", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert "local_tool_coupling_review" not in answer


def test_proof_changed_selector_reviews_template_burden(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "template-burden.md",
        """
# Template burden review

agentic-workspace-proof-route: {"state":"confirmed","intent_type":"static-check","candidate_command":"agentic-workspace proof --changed <template paths> --format json","source":"memory","confidence":"high","requires_live_confirmation":false,"scope":"docs/process template-burden","owner":"Memory","provenance":"human review asked PR templates to include low-risk answer paths","learned_at":"2026-07-06"}
""",
    )
    _write(
        tmp_path / ".github" / "pull_request_template.md",
        """
# Pull Request

## Evidence gaps

- List all missing evidence.
""",
    )

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                ".github/pull_request_template.md",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    review = answer["template_burden_review"]
    assert review["status"] == "attention-needed"
    assert review["activation"]["signals"][0]["source"] == "repo-learned-proof-route"
    assert review["flagged_count"] == 1
    assert review["flagged_sections"][0]["line"] == 4
    assert "low-risk answer path" in review["flagged_sections"][0]["reason"]
    assert review["route_learning_evidence"]["memory_note_entry"].startswith("agentic-workspace-proof-route:")


def test_proof_changed_selector_accepts_optional_template_burden_guidance(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "template-burden.md",
        """
# Template burden review

agentic-workspace-proof-route: {"state":"confirmed","intent_type":"static-check","candidate_command":"agentic-workspace proof --changed <template paths> --format json","source":"memory","confidence":"high","requires_live_confirmation":false,"scope":"docs/process template-burden","owner":"Memory","provenance":"human review asked PR templates to include low-risk answer paths","learned_at":"2026-07-06"}
""",
    )
    _write(
        tmp_path / ".github" / "pull_request_template.md",
        """
# Pull Request

## Optional high-risk evidence

- Not applicable; no high-risk lanes.
""",
    )

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                ".github/pull_request_template.md",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    review = answer["template_burden_review"]
    assert review["status"] == "clear"
    assert review["flagged_count"] == 0
    assert review["accepted_count"] == 1


def test_proof_changed_selector_does_not_globally_require_template_burden_review(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _write(
        tmp_path / ".github" / "pull_request_template.md",
        """
# Pull Request

## Evidence gaps

- List missing evidence.
""",
    )

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                ".github/pull_request_template.md",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    review = answer["template_burden_review"]
    assert review["status"] == "not-active"
    assert review["changed_paths"] == [".github/pull_request_template.md"]
    assert review["flagged_count"] == 0


def test_proof_changed_selector_routes_package_readmes_to_docs_review(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "packages/planning/README.md", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert [lane["id"] for lane in answer["selected_lanes"]] == ["repo_docs_review"]
    assert answer["selected_lanes"][0]["proof_kind"] == "diff-review"
    assert "make test-planning" not in answer["required_commands"]
    assert "git diff -- README.md docs .agentic-workspace/docs" in answer["required_commands"][0]


def _proof_owned_publication_snapshot(target: Path) -> dict[str, bytes]:
    """Capture every persistent surface owned by ordinary proof receipt publication."""
    roots = [
        target / ".agentic-workspace" / "local" / "proof-receipts",
        target / ".agentic-workspace" / "proof" / "receipts",
    ]
    files = [
        target / ".agentic-workspace" / "local" / "cache" / "proof-reuse.json",
        target / ".agentic-workspace" / "delegation-outcomes.json",
    ]
    reviews_root = target / ".agentic-workspace" / "planning" / "reviews"
    if reviews_root.is_dir():
        files.extend(reviews_root.glob("*-review-stack-*-lifecycle.review.json*"))
    for root in roots:
        if root.is_dir():
            files.extend(path for path in root.rglob("*") if path.is_file())
    return {path.relative_to(target).as_posix(): path.read_bytes() for path in sorted(set(files)) if path.is_file()}


def test_proof_record_receipt_writes_latest_execution_evidence(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    (target / ".agentic-workspace").mkdir()
    (target / ".agentic-workspace" / "config.toml").write_text("schema_version = 1\n", encoding="utf-8")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(target),
                "--changed",
                "tests/test_workspace_proof_cli.py",
                "--record-receipt",
                "--receipt-command",
                "uv run pytest tests/test_workspace_proof_cli.py -q",
                "--receipt-result",
                "passed",
                "--receipt-plan",
                "plan-alpha",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    receipt_path = target / ".agentic-workspace" / "local" / "proof-receipts" / "last.json"
    history_path = target / ".agentic-workspace" / "local" / "proof-receipts" / "history.jsonl"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    history = [json.loads(line) for line in history_path.read_text(encoding="utf-8").splitlines()]
    assert payload["status"] == "written"
    assert payload["path"] == ".agentic-workspace/local/proof-receipts/last.json"
    assert payload["history_path"] == ".agentic-workspace/local/proof-receipts/history.jsonl"
    assert receipt["command"] == "uv run pytest tests/test_workspace_proof_cli.py -q"
    assert receipt["result"] == "passed"
    assert receipt["changed_paths"] == ["tests/test_workspace_proof_cli.py"]
    assert receipt["plan_id"] == "plan-alpha"
    assert history == [receipt]
    assert "repair_retry_ladder" not in receipt
    assert "repair_retry_ladder" not in payload


def test_proof_record_receipt_cmd_20260827215319_3506eca4_rejection_has_zero_persistent_delta(tmp_path: Path) -> None:
    _write_repo_local_proof_target(tmp_path)
    _write(tmp_path / ".agentic-workspace/local/proof-receipts/last.json", '{"sentinel":"last"}\n')
    _write(tmp_path / ".agentic-workspace/local/proof-receipts/history.jsonl", '{"sentinel":"history"}\n')
    _write(tmp_path / ".agentic-workspace/local/cache/proof-reuse.json", '{"sentinel":"cache"}\n')
    _write(tmp_path / ".agentic-workspace/proof/receipts/index.json", '{"sentinel":"index"}\n')
    before = _proof_owned_publication_snapshot(tmp_path)

    with pytest.raises(SystemExit) as exc_info:
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "README.md",
                "--record-receipt",
                "--receipt-command",
                "make test-workspace",
                "--receipt-result",
                "passed",
                "--format",
                "json",
            ]
        )

    assert exc_info.value.code == 2
    assert _proof_owned_publication_snapshot(tmp_path) == before


def test_proof_record_receipt_stale_subject_rejection_has_zero_persistent_delta(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import agentic_workspace.workspace_runtime_core as runtime_core
    from agentic_workspace.config import WorkspaceUsageError

    _write_repo_local_proof_target(tmp_path)
    changed_path = "src/agentic_workspace/workspace_runtime_proof.py"
    _write(tmp_path / changed_path, "before\n")
    before = _proof_owned_publication_snapshot(tmp_path)
    original_failure_context = runtime_core._proof_receipt_failure_context

    def mutate_subject_after_capture(**kwargs):
        result = original_failure_context(**kwargs)
        _write(tmp_path / changed_path, "after\n")
        return result

    monkeypatch.setattr(runtime_core, "_proof_receipt_failure_context", mutate_subject_after_capture)
    with pytest.raises(WorkspaceUsageError, match="subject changed before publication"):
        runtime_core._record_proof_receipt_payload(
            target_root=tmp_path,
            command="make test-workspace",
            result="passed",
            changed_paths=[changed_path],
        )

    assert _proof_owned_publication_snapshot(tmp_path) == before


def test_proof_record_receipt_rolls_back_injected_partial_publication(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import agentic_workspace.workspace_runtime_core as runtime_core

    _write_repo_local_proof_target(tmp_path)
    changed_path = "src/agentic_workspace/workspace_runtime_proof.py"
    _write(tmp_path / changed_path, "subject\n")
    before = _proof_owned_publication_snapshot(tmp_path)
    original_writer = runtime_core._write_trusted_producer_receipt

    def fail_after_producer_write(**kwargs):
        original_writer(**kwargs)
        raise RuntimeError("injected proof publication failure")

    monkeypatch.setattr(runtime_core, "_write_trusted_producer_receipt", fail_after_producer_write)
    with pytest.raises(RuntimeError, match="injected proof publication failure"):
        runtime_core._record_proof_receipt_payload(
            target_root=tmp_path,
            command="make test-workspace",
            result="passed",
            changed_paths=[changed_path],
        )

    assert _proof_owned_publication_snapshot(tmp_path) == before


def test_proof_record_receipt_successful_retry_is_byte_idempotent(tmp_path: Path) -> None:
    import agentic_workspace.workspace_runtime_core as runtime_core

    _write_repo_local_proof_target(tmp_path)
    changed_path = "src/agentic_workspace/workspace_runtime_proof.py"
    _write(tmp_path / changed_path, "subject\n")
    kwargs = {
        "target_root": tmp_path,
        "command": "make test-workspace",
        "result": "passed",
        "changed_paths": [changed_path],
    }

    runtime_core._record_proof_receipt_payload(**kwargs)
    after_first = _proof_owned_publication_snapshot(tmp_path)
    runtime_core._record_proof_receipt_payload(**kwargs)

    assert _proof_owned_publication_snapshot(tmp_path) == after_first
    history = (tmp_path / ".agentic-workspace/local/proof-receipts/history.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(history) == 1


def test_proof_record_receipt_rejects_unresolved_template_before_persistence(tmp_path: Path) -> None:
    from agentic_workspace.config import WorkspaceUsageError
    from agentic_workspace.workspace_runtime_primitives import _record_proof_receipt_payload

    target = tmp_path / "repo"
    target.mkdir()

    with pytest.raises(WorkspaceUsageError, match="unresolved-command-template") as error:
        _record_proof_receipt_payload(
            target_root=target,
            command="uv run agentic-workspace implement --changed <paths>",
            result="passed",
            changed_paths=["src/agentic_workspace/workspace_runtime_proof.py"],
        )

    assert "Substitute every placeholder" in str(error.value)
    assert not (target / ".agentic-workspace" / "local" / "proof-receipts" / "last.json").exists()
    assert not (target / ".agentic-workspace" / "local" / "proof-receipts" / "history.jsonl").exists()


def test_proof_receipt_admission_rejects_missing_scope_and_consumers_ignore_it(tmp_path: Path) -> None:
    from agentic_workspace.proof_receipt_admission import proof_receipt_admission
    from agentic_workspace.workspace_runtime_proof import _proof_receipt_reconciliation_payload

    receipt = {
        "kind": "agentic-workspace/proof-receipt/v1",
        "command": "make test-workspace",
        "result": "passed",
        "recorded_at": "2026-07-11T08:00:00+00:00",
        "changed_paths": [],
    }
    admission = proof_receipt_admission(receipt)
    assert admission["status"] == "rejected"
    assert admission["reason"] == "missing-changed-path-scope"

    receipt_path = tmp_path / ".agentic-workspace" / "local" / "proof-receipts" / "last.json"
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    reconciliation = _proof_receipt_reconciliation_payload(
        target_root=tmp_path,
        changed_paths=["src/agentic_workspace/workspace_runtime_proof.py"],
        required_commands=["make test-workspace"],
        selected_commands=[],
    )
    assert reconciliation["status"] == "not-recorded"
    assert "receipt" not in reconciliation
    assert reconciliation["commands"][0]["evidence_state"] == "not-run-or-not-recorded"
    assert reconciliation["rejected_latest_receipt"]["admission_reason"] == "missing-changed-path-scope"


def test_reconciliation_selects_newest_admitted_history_when_latest_file_is_rejected(tmp_path: Path) -> None:
    from agentic_workspace.proof_subject import build_proof_subject
    from agentic_workspace.workspace_runtime_proof import _proof_receipt_reconciliation_payload

    receipt_dir = tmp_path / ".agentic-workspace/local/proof-receipts"
    receipt_dir.mkdir(parents=True)
    _write(tmp_path / "src/agentic_workspace/workspace_runtime_proof.py", "fixture\n")
    admitted = {
        "kind": "agentic-workspace/proof-receipt/v1",
        "command": "make test-workspace",
        "result": "passed",
        "recorded_at": "2026-07-11T08:00:00+00:00",
        "changed_paths": ["src/agentic_workspace/workspace_runtime_proof.py"],
    }
    admitted["proof_subject"] = build_proof_subject(
        target_root=tmp_path, changed_paths=admitted["changed_paths"], command=admitted["command"]
    )
    older = {**admitted, "result": "failed", "recorded_at": "2026-07-11T07:00:00+00:00"}
    rejected = {**admitted, "command": "make <target>", "recorded_at": "2026-07-11T09:00:00+00:00"}
    (receipt_dir / "history.jsonl").write_text("\n".join(json.dumps(item) for item in (older, admitted)) + "\n", encoding="utf-8")
    (receipt_dir / "last.json").write_text(json.dumps(rejected), encoding="utf-8")

    reconciliation = _proof_receipt_reconciliation_payload(
        target_root=tmp_path,
        changed_paths=["src/agentic_workspace/workspace_runtime_proof.py"],
        required_commands=["make test-workspace"],
        selected_commands=[],
    )

    assert reconciliation["status"] == "accepted"
    assert reconciliation["receipt"]["recorded_at"] == admitted["recorded_at"]
    assert reconciliation["receipt"]["command"] == "make test-workspace"
    assert reconciliation["rejected_latest_receipt"]["status"] == "rejected-untrusted"
    assert reconciliation["rejected_latest_receipt"]["admission_reason"] == "unresolved-command-template"
    assert reconciliation["receipt_history"]["record_count"] == 2


def _proof_template_current_identity_fixture(
    *,
    lane_id: str = "proof-template-lane",
    owner_ref: str = ".agentic-workspace/planning/execplans/proof-template.plan.json",
) -> dict[str, str]:
    return {
        "lane_id": lane_id,
        "lane_revision": "lane-rev-1",
        "owner_ref": owner_ref,
        "owner_revision": "owner-rev-1",
        "assignment_target": "user-local:codex-current",
        "assignment_context_key": "workspace/proof-template",
        "assignment_revision": "assignment-rev-1",
        "selector_registry_revision": "selector-registry-rev-1",
        "template_revision": "template-rev-1",
        "evaluation_result_revision": "eval-1",
        "mutation_baseline": "baseline-1",
    }


def _proof_template_authority_resolution_fixture(identity: dict[str, str]) -> dict[str, object]:
    authority_states = {
        key: {
            "status": "current",
            "revision": value,
            "source": "repo-proof-obligation-resolver",
            "provenance": "test fixture authoritative selected proof obligation",
        }
        for key, value in identity.items()
    }
    return {
        "kind": "agentic-workspace/proof-template-obligation-resolution/v1",
        "status": "resolved",
        "source": "repo-proof-obligation-resolver",
        "current_identity": identity,
        "authority_states": authority_states,
        "changed_paths": ["src/agentic_workspace/workspace_runtime_proof.py", "tests/test_workspace_proof_cli.py"],
    }


def _proof_template_selected_command_fixture(*, command: str, lane_id: str = "proof-template-lane") -> dict[str, object]:
    identity = _proof_template_current_identity_fixture(lane_id=lane_id)
    lane = identity.pop("lane_id")
    selected_identity = {"lane_id": lane, **identity}
    return {
        "command": command,
        "lane": lane,
        **identity,
        "authority_resolution": _proof_template_authority_resolution_fixture(selected_identity),
    }


def _proof_template_binding_fixture(
    *,
    template_command: str,
    concrete_command: str,
    changed_paths: list[str],
    selected_command: dict[str, object],
    receipt: dict[str, object],
) -> dict[str, object]:
    from agentic_workspace.workspace_runtime_proof import _proof_template_live_obligation_id

    authority_revisions = _proof_template_current_identity_fixture(
        lane_id=str(selected_command["lane"]),
        owner_ref=str(selected_command["owner_ref"]),
    )
    return {
        "kind": "agentic-workspace/proof-template-binding/v1",
        "status": "current",
        "live_obligation_id": _proof_template_live_obligation_id(
            required_command=template_command,
            changed_paths=changed_paths,
            selected_command=selected_command,
        ),
        "command": {
            "template": template_command,
            "concrete": concrete_command,
            "selector_parameters": {
                "selectors": _command_selector_parameters_for_fixture(template_command),
            },
        },
        "owner_identity": {
            "lane_id": selected_command["lane"],
            "owner_ref": selected_command["owner_ref"],
        },
        "assignment": {
            "target_identity_ref": selected_command["assignment_target"],
            "context_key": selected_command["assignment_context_key"],
        },
        "authority_revisions": authority_revisions,
        "authority_states": _proof_template_authority_resolution_fixture(authority_revisions)["authority_states"],
        "artifact_provenance": {"changed_paths": changed_paths},
        "result_provenance": {
            "result": "passed",
            "recorded_at": "2026-07-11T08:00:00+00:00",
            "proof_subject_fingerprint": receipt["proof_subject"]["fingerprint"],  # type: ignore[index]
        },
        "freshness": {"status": "current", "baseline_revision": "baseline-1", "evaluation_result": "eval-1"},
    }


def _command_selector_parameters_for_fixture(command: str) -> list[str]:
    if "--select " not in command:
        return []
    selected = command.split("--select ", 1)[1].split(" ", 1)[0]
    return sorted(part.strip() for part in selected.split(",") if part.strip())


def test_reconciliation_accepts_instantiated_paths_template_receipt(tmp_path: Path) -> None:
    from agentic_workspace.proof_subject import build_proof_subject
    from agentic_workspace.workspace_runtime_proof import _proof_receipt_reconciliation_payload

    receipt_dir = tmp_path / ".agentic-workspace/local/proof-receipts"
    receipt_dir.mkdir(parents=True)
    changed_paths = ["src/agentic_workspace/workspace_runtime_proof.py", "tests/test_workspace_proof_cli.py"]
    for path in changed_paths:
        _write(tmp_path / path, f"fixture for {path}\n")
    template_command = (
        "uv run python scripts/run_agentic_workspace.py implement --changed <paths> "
        "--select requirement_grounding,context.delegation_decision,context.plan_delegation_packet --format json"
    )
    concrete_command = (
        "uv run python scripts/run_agentic_workspace.py implement "
        "--changed src/agentic_workspace/workspace_runtime_proof.py tests/test_workspace_proof_cli.py "
        "--select requirement_grounding,context.delegation_decision,context.plan_delegation_packet --format json"
    )
    receipt = {
        "kind": "agentic-workspace/proof-receipt/v1",
        "command": concrete_command,
        "result": "passed",
        "recorded_at": "2026-07-11T08:00:00+00:00",
        "changed_paths": changed_paths,
    }
    receipt["proof_subject"] = build_proof_subject(target_root=tmp_path, changed_paths=changed_paths, command=concrete_command)
    selected_command = _proof_template_selected_command_fixture(
        command=template_command,
        lane_id="requirement-grounding-delegation",
    )
    receipt["proof_template_binding"] = _proof_template_binding_fixture(
        template_command=template_command,
        concrete_command=concrete_command,
        changed_paths=changed_paths,
        selected_command=selected_command,
        receipt=receipt,
    )
    (receipt_dir / "last.json").write_text(json.dumps(receipt), encoding="utf-8")

    reconciliation = _proof_receipt_reconciliation_payload(
        target_root=tmp_path,
        changed_paths=changed_paths,
        required_commands=[template_command],
        selected_commands=[selected_command],
    )

    assert reconciliation["status"] == "accepted"
    assert reconciliation["commands"][0]["evidence_state"] == "accepted"
    assert reconciliation["commands"][0]["receipt_match"] == "instantiated-template"
    assert reconciliation["commands"][0]["receipt"]["command"] == concrete_command
    assert reconciliation["commands"][0]["live_obligation_binding"]["status"] == "accepted"
    assert reconciliation["commands"][0]["live_obligation_binding"]["assignment"] == {
        "target_identity_ref": "user-local:codex-current",
        "context_key": "workspace/proof-template",
    }


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        (lambda binding: None, "missing-live-obligation-binding"),
        (lambda binding: binding["owner_identity"].update({"lane_id": "other-lane"}), "cross-lane-receipt"),
        (lambda binding: binding.update({"status": "superseded"}), "superseded-template-binding"),
        (
            lambda binding: binding["freshness"].update({"status": "evaluation-result-replaced"}),
            "stale-evaluation-result-replaced-template-binding",
        ),
        (lambda binding: binding["result_provenance"].pop("proof_subject_fingerprint"), "proof-subject-provenance-mismatch"),
    ],
)
def test_reconciliation_rejects_stale_or_cross_context_instantiated_template_receipt(tmp_path: Path, mutate, reason: str) -> None:
    from agentic_workspace.proof_subject import build_proof_subject
    from agentic_workspace.workspace_runtime_proof import _proof_receipt_reconciliation_payload

    receipt_dir = tmp_path / ".agentic-workspace/local/proof-receipts"
    receipt_dir.mkdir(parents=True)
    changed_paths = ["src/agentic_workspace/workspace_runtime_proof.py", "tests/test_workspace_proof_cli.py"]
    for path in changed_paths:
        _write(tmp_path / path, f"fixture for {path}\n")
    template_command = (
        "uv run python scripts/run_agentic_workspace.py implement --changed <paths> --select requirement_grounding --format json"
    )
    concrete_command = (
        "uv run python scripts/run_agentic_workspace.py implement "
        "--changed src/agentic_workspace/workspace_runtime_proof.py tests/test_workspace_proof_cli.py "
        "--select requirement_grounding --format json"
    )
    selected_command = _proof_template_selected_command_fixture(command=template_command)
    receipt = {
        "kind": "agentic-workspace/proof-receipt/v1",
        "command": concrete_command,
        "result": "passed",
        "recorded_at": "2026-07-11T08:00:00+00:00",
        "changed_paths": changed_paths,
    }
    receipt["proof_subject"] = build_proof_subject(target_root=tmp_path, changed_paths=changed_paths, command=concrete_command)
    binding = _proof_template_binding_fixture(
        template_command=template_command,
        concrete_command=concrete_command,
        changed_paths=changed_paths,
        selected_command=selected_command,
        receipt=receipt,
    )
    if reason != "missing-live-obligation-binding":
        mutate(binding)
        receipt["proof_template_binding"] = binding
    (receipt_dir / "last.json").write_text(json.dumps(receipt), encoding="utf-8")

    reconciliation = _proof_receipt_reconciliation_payload(
        target_root=tmp_path,
        changed_paths=changed_paths,
        required_commands=[template_command],
        selected_commands=[selected_command],
    )

    assert reconciliation["status"] == "attention"
    state = reconciliation["commands"][0]
    assert state["evidence_state"] == "template-binding-rejected"
    assert state["diagnostic"] == reason
    assert state["receipt_match"] == "instantiated-template"


@pytest.mark.parametrize(
    ("current_field", "stale_value", "reason"),
    [
        ("owner_revision", "owner-rev-2", "stale-owner_revision-template-binding"),
        ("assignment_revision", "assignment-rev-2", "stale-assignment_revision-template-binding"),
        ("selector_registry_revision", "selector-registry-rev-2", "stale-selector_registry_revision-template-binding"),
        ("template_revision", "template-rev-2", "stale-template_revision-template-binding"),
    ],
)
def test_reconciliation_rejects_current_authority_drift_when_receipt_still_claims_current(
    tmp_path: Path, current_field: str, stale_value: str, reason: str
) -> None:
    from agentic_workspace.proof_subject import build_proof_subject
    from agentic_workspace.workspace_runtime_proof import _proof_receipt_reconciliation_payload

    receipt_dir = tmp_path / ".agentic-workspace/local/proof-receipts"
    receipt_dir.mkdir(parents=True)
    changed_paths = ["src/agentic_workspace/workspace_runtime_proof.py", "tests/test_workspace_proof_cli.py"]
    for path in changed_paths:
        _write(tmp_path / path, f"fixture for {path}\n")
    template_command = (
        "uv run python scripts/run_agentic_workspace.py implement --changed <paths> --select requirement_grounding --format json"
    )
    concrete_command = (
        "uv run python scripts/run_agentic_workspace.py implement "
        "--changed src/agentic_workspace/workspace_runtime_proof.py tests/test_workspace_proof_cli.py "
        "--select requirement_grounding --format json"
    )
    receipt_selected_command = _proof_template_selected_command_fixture(command=template_command)
    current_selected_command = json.loads(json.dumps(receipt_selected_command))
    current_selected_command[current_field] = stale_value
    current_selected_command["authority_resolution"]["current_identity"][current_field] = stale_value
    current_selected_command["authority_resolution"]["authority_states"][current_field]["revision"] = stale_value
    receipt = {
        "kind": "agentic-workspace/proof-receipt/v1",
        "command": concrete_command,
        "result": "passed",
        "recorded_at": "2026-07-11T08:00:00+00:00",
        "changed_paths": changed_paths,
    }
    receipt["proof_subject"] = build_proof_subject(target_root=tmp_path, changed_paths=changed_paths, command=concrete_command)
    receipt["proof_template_binding"] = _proof_template_binding_fixture(
        template_command=template_command,
        concrete_command=concrete_command,
        changed_paths=changed_paths,
        selected_command=receipt_selected_command,
        receipt=receipt,
    )
    (receipt_dir / "last.json").write_text(json.dumps(receipt), encoding="utf-8")

    reconciliation = _proof_receipt_reconciliation_payload(
        target_root=tmp_path,
        changed_paths=changed_paths,
        required_commands=[template_command],
        selected_commands=[current_selected_command],
    )

    assert reconciliation["status"] == "attention"
    state = reconciliation["commands"][0]
    assert state["evidence_state"] == "template-binding-rejected"
    assert state["diagnostic"] == reason
    assert state["live_obligation_binding"]["binding"]["freshness"]["status"] == "current"


@pytest.mark.parametrize(
    ("current_field", "current_value"),
    [
        ("evaluation_result_revision", "eval-2"),
        ("mutation_baseline", "baseline-2"),
    ],
)
def test_reconciliation_accepts_not_required_template_authority_drift(tmp_path: Path, current_field: str, current_value: str) -> None:
    from agentic_workspace.proof_subject import build_proof_subject
    from agentic_workspace.workspace_runtime_proof import _proof_receipt_reconciliation_payload

    receipt_dir = tmp_path / ".agentic-workspace/local/proof-receipts"
    receipt_dir.mkdir(parents=True)
    changed_paths = ["src/agentic_workspace/workspace_runtime_proof.py", "tests/test_workspace_proof_cli.py"]
    for path in changed_paths:
        _write(tmp_path / path, f"fixture for {path}\n")
    template_command = (
        "uv run python scripts/run_agentic_workspace.py implement --changed <paths> --select requirement_grounding --format json"
    )
    concrete_command = (
        "uv run python scripts/run_agentic_workspace.py implement "
        "--changed src/agentic_workspace/workspace_runtime_proof.py tests/test_workspace_proof_cli.py "
        "--select requirement_grounding --format json"
    )
    receipt_selected_command = _proof_template_selected_command_fixture(command=template_command)
    current_selected_command = json.loads(json.dumps(receipt_selected_command))
    current_selected_command[current_field] = current_value
    current_selected_command["authority_resolution"]["current_identity"][current_field] = current_value
    current_selected_command["authority_resolution"]["authority_states"][current_field]["revision"] = current_value
    receipt = {
        "kind": "agentic-workspace/proof-receipt/v1",
        "command": concrete_command,
        "result": "passed",
        "recorded_at": "2026-07-11T08:00:00+00:00",
        "changed_paths": changed_paths,
    }
    receipt["proof_subject"] = build_proof_subject(target_root=tmp_path, changed_paths=changed_paths, command=concrete_command)
    receipt["proof_template_binding"] = _proof_template_binding_fixture(
        template_command=template_command,
        concrete_command=concrete_command,
        changed_paths=changed_paths,
        selected_command=receipt_selected_command,
        receipt=receipt,
    )
    assert receipt["proof_template_binding"]["authority_revisions"][current_field] != current_value
    (receipt_dir / "last.json").write_text(json.dumps(receipt), encoding="utf-8")

    reconciliation = _proof_receipt_reconciliation_payload(
        target_root=tmp_path,
        changed_paths=changed_paths,
        required_commands=[template_command],
        selected_commands=[current_selected_command],
    )

    assert reconciliation["status"] == "accepted"
    state = reconciliation["commands"][0]
    assert state["evidence_state"] == "accepted"
    admission = state["live_obligation_binding"]
    assert admission["status"] == "accepted"


def test_reconciliation_rejects_template_receipt_when_current_obligation_identity_is_incomplete(tmp_path: Path) -> None:
    from agentic_workspace.proof_subject import build_proof_subject
    from agentic_workspace.workspace_runtime_proof import _proof_receipt_reconciliation_payload

    receipt_dir = tmp_path / ".agentic-workspace/local/proof-receipts"
    receipt_dir.mkdir(parents=True)
    changed_paths = ["src/agentic_workspace/workspace_runtime_proof.py", "tests/test_workspace_proof_cli.py"]
    for path in changed_paths:
        _write(tmp_path / path, f"fixture for {path}\n")
    template_command = (
        "uv run python scripts/run_agentic_workspace.py implement --changed <paths> --select requirement_grounding --format json"
    )
    concrete_command = (
        "uv run python scripts/run_agentic_workspace.py implement "
        "--changed src/agentic_workspace/workspace_runtime_proof.py tests/test_workspace_proof_cli.py "
        "--select requirement_grounding --format json"
    )
    complete_selected_command = _proof_template_selected_command_fixture(command=template_command)
    incomplete_selected_command = json.loads(json.dumps(complete_selected_command))
    incomplete_selected_command.pop("owner_revision")
    incomplete_selected_command["authority_resolution"]["current_identity"].pop("owner_revision")
    incomplete_selected_command["authority_resolution"]["authority_states"].pop("owner_revision")
    receipt = {
        "kind": "agentic-workspace/proof-receipt/v1",
        "command": concrete_command,
        "result": "passed",
        "recorded_at": "2026-07-11T08:00:00+00:00",
        "changed_paths": changed_paths,
    }
    receipt["proof_subject"] = build_proof_subject(target_root=tmp_path, changed_paths=changed_paths, command=concrete_command)
    receipt["proof_template_binding"] = _proof_template_binding_fixture(
        template_command=template_command,
        concrete_command=concrete_command,
        changed_paths=changed_paths,
        selected_command=complete_selected_command,
        receipt=receipt,
    )
    (receipt_dir / "last.json").write_text(json.dumps(receipt), encoding="utf-8")

    reconciliation = _proof_receipt_reconciliation_payload(
        target_root=tmp_path,
        changed_paths=changed_paths,
        required_commands=[template_command],
        selected_commands=[incomplete_selected_command],
    )

    assert reconciliation["status"] == "attention"
    state = reconciliation["commands"][0]
    assert state["evidence_state"] == "template-binding-rejected"
    assert state["diagnostic"] == "missing-current-obligation-identity"
    assert state["live_obligation_binding"]["missing_identity"] == ["owner_revision"]


def test_proof_receipt_persistence_redacts_sensitive_values() -> None:
    from agentic_workspace.workspace_runtime_core import _proof_receipt_redact_sensitive_data

    payload = _proof_receipt_redact_sensitive_data(
        {
            "command": "TOKEN=ghp_abcdefghijklmnopqrstuvwxyz012345 pytest -q",
            "execution": {
                "environment": {
                    "platform": "windows",
                    "api_key": "plain-text-value",
                    "nested": "authorization=Bearer-value",
                }
            },
        }
    )

    assert payload["command"] == "TOKEN=[redacted] pytest -q"
    assert payload["execution"]["environment"] == {
        "platform": "windows",
        "api_key": "[redacted]",
        "nested": "authorization=[redacted]",
    }
    assert "plain-text-value" not in json.dumps(payload)
    assert "ghp_" not in json.dumps(payload)


def test_proof_record_receipt_builds_template_binding_from_current_obligation(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_proof_planning_state(tmp_path)
    changed_paths = ["src/agentic_workspace/workspace_runtime_proof.py", "tests/test_workspace_proof_cli.py"]
    for path in changed_paths:
        _write(tmp_path / path, f"fixture for {path}\n")
    _write(tmp_path / "scripts" / "run_agentic_workspace.py", "print('fixture aw')\n")
    template_command = (
        "uv run python scripts/run_agentic_workspace.py implement --changed <paths> --select requirement_grounding --format json"
    )
    concrete_command = (
        "uv run python scripts/run_agentic_workspace.py implement "
        "--changed src/agentic_workspace/workspace_runtime_proof.py tests/test_workspace_proof_cli.py "
        "--select requirement_grounding --format json"
    )
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        f"""
schema_version = 1

[workspace]
cli_invoke = "{REPO_LOCAL_CLI_INVOKE}"

[assurance.domain_proof_lanes.proof_template_receipts]
purpose = "Proof template receipt replay."
applies_to_paths = ["src/agentic_workspace/workspace_runtime_proof.py", "tests/test_workspace_proof_cli.py"]
commands = ["{template_command}"]
owner = "workspace-proof-runtime"
""",
    )

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                changed_paths[0],
                "--changed",
                changed_paths[1],
                "--record-receipt",
                "--receipt-command",
                concrete_command,
                "--receipt-result",
                "passed",
                "--format",
                "json",
            ]
        )
        == 0
    )
    receipt = json.loads(capsys.readouterr().out)["receipt"]
    binding = receipt["proof_template_binding"]
    assert binding["command"]["template"] == template_command
    assert binding["command"]["concrete"] == concrete_command
    after_first = _proof_owned_publication_snapshot(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                changed_paths[0],
                "--changed",
                changed_paths[1],
                "--record-receipt",
                "--receipt-command",
                concrete_command,
                "--receipt-result",
                "passed",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert _proof_owned_publication_snapshot(tmp_path) == after_first
    assert binding["authority_states"]["evaluation_result_revision"]["status"] == "not-required"
    assert binding["authority_revisions"]["evaluation_result_revision"] == "not-required:evaluation"
    assert binding["authority_states"]["mutation_baseline"]["status"] == "not-required"
    assert binding["authority_revisions"]["mutation_baseline"]
    assert "payload" in binding["authority_states"]["mutation_baseline"]

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                changed_paths[0],
                "--changed",
                changed_paths[1],
                "--select",
                "proof_closeout_summary,proof_command_tiers",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    answer = payload.get("values", payload.get("answer", payload))
    assert answer["proof_closeout_summary"]["receipt_bridge"]["status"] == "complete"
    assert answer["proof_closeout_summary"]["status"] == "sufficient-recorded"
    receipt_tiers = [item for tier in answer["proof_command_tiers"]["tiers"] for item in tier["commands"]]
    assert next(item for item in receipt_tiers if item["command"] == template_command)["posture"] == "already-satisfied"

    config_path = tmp_path / ".agentic-workspace" / "config.toml"
    config_path.write_text(config_path.read_text(encoding="utf-8") + '\nnotes = "registry changed after receipt"\n', encoding="utf-8")
    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                changed_paths[0],
                "--changed",
                changed_paths[1],
                "--select",
                "proof_closeout_summary",
                "--format",
                "json",
            ]
        )
        == 0
    )
    stale_payload = json.loads(capsys.readouterr().out)
    stale_answer = stale_payload.get("values", stale_payload.get("answer", stale_payload))
    assert stale_answer["proof_closeout_summary"]["status"] != "sufficient-recorded"

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                changed_paths[0],
                "--changed",
                changed_paths[1],
                "--select",
                "selected_commands,required_commands",
                "--format",
                "json",
            ]
        )
        == 0
    )
    selected = json.loads(capsys.readouterr().out)["values"]
    from agentic_workspace.workspace_runtime_proof import _proof_receipt_reconciliation_payload

    reconciliation = _proof_receipt_reconciliation_payload(
        target_root=tmp_path,
        changed_paths=changed_paths,
        required_commands=selected["required_commands"],
        selected_commands=selected["selected_commands"],
    )
    stale_state = reconciliation["commands"][0]
    assert stale_state["evidence_state"] == "template-binding-rejected"
    assert stale_state["diagnostic"] == "stale-lane_revision-template-binding"
    assert stale_state["minimum_rerun_command"] == template_command


def test_proof_template_receipt_only_commit_is_fixed_point_but_subject_change_is_stale(tmp_path: Path, capsys) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "agent@example.test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Agent"], cwd=tmp_path, check=True)
    _write_empty_proof_planning_state(tmp_path)
    changed_paths = ["src/agentic_workspace/workspace_runtime_proof.py", "tests/test_workspace_proof_cli.py"]
    for path in changed_paths:
        _write(tmp_path / path, f"fixture for {path}\n")
    _write(tmp_path / "scripts" / "run_agentic_workspace.py", "print('fixture aw')\n")
    template_command = (
        "uv run python scripts/run_agentic_workspace.py implement --changed <paths> --select requirement_grounding --format json"
    )
    concrete_command = (
        "uv run python scripts/run_agentic_workspace.py implement "
        "--changed src/agentic_workspace/workspace_runtime_proof.py tests/test_workspace_proof_cli.py "
        "--select requirement_grounding --format json"
    )
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        f'''\
schema_version = 1

[workspace]
cli_invoke = "{REPO_LOCAL_CLI_INVOKE}"

[assurance.domain_proof_lanes.proof_template_receipts]
purpose = "Proof template receipt fixed point."
applies_to_paths = ["src/agentic_workspace/workspace_runtime_proof.py", "tests/test_workspace_proof_cli.py"]
commands = ["{template_command}"]
owner = "workspace-proof-runtime"
''',
    )
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "subject A"], cwd=tmp_path, check=True, capture_output=True)
    head_a = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True).strip()

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                *changed_paths,
                "--record-receipt",
                "--receipt-command",
                concrete_command,
                "--receipt-result",
                "passed",
                "--format",
                "json",
            ]
        )
        == 0
    )
    written = json.loads(capsys.readouterr().out)
    receipt_ref = written["trusted_producer_receipt_ref"].removeprefix("proof://receipts/")
    canonical_receipt = tmp_path / ".agentic-workspace" / "proof" / "receipts" / f"{receipt_ref}.json"
    canonical_index = tmp_path / ".agentic-workspace" / "proof" / "receipts" / "index.json"
    receipt = json.loads(canonical_receipt.read_text(encoding="utf-8"))
    baseline = receipt["proof_template_binding"]["authority_states"]["mutation_baseline"]
    assert baseline["status"] == "not-required"
    assert baseline["payload"]["head"] == head_a
    subprocess.run(["git", "add", str(canonical_receipt), str(canonical_index)], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "receipt B"], cwd=tmp_path, check=True, capture_output=True)
    head_b = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True).strip()
    assert head_b != head_a

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                *changed_paths,
                "--select",
                "proof_closeout_summary,proof_receipt_reconciliation",
                "--format",
                "json",
            ]
        )
        == 0
    )
    fixed_point = json.loads(capsys.readouterr().out)["values"]
    assert fixed_point["proof_closeout_summary"]["status"] == "sufficient-recorded"
    state = fixed_point["proof_receipt_reconciliation"]["commands"][0]
    assert state["evidence_state"] == "accepted"
    assert state["live_obligation_binding"]["status"] == "accepted"
    assert head_b != baseline["payload"]["head"]

    subject_path = tmp_path / changed_paths[0]
    subject_path.write_text(subject_path.read_text(encoding="utf-8") + "# review fix\n", encoding="utf-8")
    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                *changed_paths,
                "--select",
                "proof_closeout_summary,proof_receipt_reconciliation",
                "--format",
                "json",
            ]
        )
        == 0
    )
    stale = json.loads(capsys.readouterr().out)["values"]
    assert stale["proof_closeout_summary"]["status"] != "sufficient-recorded"
    stale_state = stale["proof_receipt_reconciliation"]["commands"][0]
    assert stale_state["evidence_state"] == "subject-stale"
    assert stale_state["subject_freshness"]["status"] != "reusable"


@pytest.mark.parametrize(
    ("latest_text", "reason"),
    [("{broken", "latest-receipt-unreadable"), (json.dumps(["not", "an", "object"]), "latest-receipt-not-object")],
)
@pytest.mark.parametrize("with_history", [True, False])
def test_damaged_latest_receipt_does_not_poison_admitted_history(tmp_path: Path, latest_text: str, reason: str, with_history: bool) -> None:
    from agentic_workspace.proof_subject import build_proof_subject
    from agentic_workspace.workspace_runtime_proof import _proof_receipt_reconciliation_payload

    receipt_dir = tmp_path / ".agentic-workspace/local/proof-receipts"
    receipt_dir.mkdir(parents=True)
    _write(tmp_path / "src/agentic_workspace/workspace_runtime_proof.py", "fixture\n")
    admitted = {
        "kind": "agentic-workspace/proof-receipt/v1",
        "command": "make test-workspace",
        "result": "passed",
        "recorded_at": "2026-07-11T08:00:00+00:00",
        "changed_paths": ["src/agentic_workspace/workspace_runtime_proof.py"],
    }
    admitted["proof_subject"] = build_proof_subject(
        target_root=tmp_path, changed_paths=admitted["changed_paths"], command=admitted["command"]
    )
    if with_history:
        (receipt_dir / "history.jsonl").write_text(json.dumps(admitted) + "\n", encoding="utf-8")
    (receipt_dir / "last.json").write_text(latest_text, encoding="utf-8")

    reconciliation = _proof_receipt_reconciliation_payload(
        target_root=tmp_path,
        changed_paths=["src/agentic_workspace/workspace_runtime_proof.py"],
        required_commands=["make test-workspace"],
        selected_commands=[],
    )

    assert reconciliation["rejected_latest_receipt"]["admission_reason"] == reason
    if with_history:
        assert reconciliation["status"] == "accepted"
        assert reconciliation["receipt"]["command"] == "make test-workspace"
    else:
        assert reconciliation["status"] == "not-recorded"
        assert "receipt" not in reconciliation


def test_proof_failed_receipt_includes_repair_retry_ladder(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    (target / ".agentic-workspace").mkdir()
    (target / ".agentic-workspace" / "config.toml").write_text("schema_version = 1\n", encoding="utf-8")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(target),
                "--changed",
                "tests/test_workspace_proof_cli.py",
                "--record-receipt",
                "--receipt-command",
                "make test-workspace",
                "--receipt-result",
                "failed",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    receipt_path = target / ".agentic-workspace" / "local" / "proof-receipts" / "last.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    ladder = payload["repair_retry_ladder"]
    written_ladder = receipt["repair_retry_ladder"]
    assert ladder == written_ladder
    assert ladder["kind"] == "agentic-workspace/proof-repair-retry-ladder/v1"
    assert ladder["trigger"] == "failed-proof-receipt"
    assert ladder["failed_command"] == "make test-workspace"
    assert ladder["full_selected_proof"] == "make test-workspace"
    assert ladder["full_proof_still_required"] is True
    assert ladder["full_rerun_premature"] is True
    assert ladder["focused_commands"] == ["uv run pytest tests/test_workspace_proof_cli.py -q"]
    assert ladder["steps"][0]["commands"] == ["uv run pytest tests/test_workspace_proof_cli.py -q"]
    assert ladder["steps"][1]["command_source"] == "smallest affected package or workspace subset after the focused failure passes"
    assert ladder["steps"][2]["command"] == "make test-workspace"


def test_proof_failed_receipt_clusters_supplied_log(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    (target / ".agentic-workspace").mkdir()
    (target / ".agentic-workspace" / "config.toml").write_text("schema_version = 1\n", encoding="utf-8")
    log_path = target / ".agentic-workspace" / "local" / "proof-logs" / "workspace-test.log"
    log_path.parent.mkdir(parents=True)
    log_path.write_text(
        "\n".join(
            [
                "FAILED tests/test_workspace_proof_cli.py::test_proof_current_selects_active_plan_validation_commands - AssertionError",
                "FAILED tests/test_workspace_proof_cli.py::test_proof_current_selects_active_plan_validation_commands - AssertionError",
                "FAILED tests/test_workspace_proof_generated_packages_cli.py::test_proof_changed_selector_routes_generated_command_packages - AssertionError",
                "=========================== short test summary info ===========================",
            ]
        ),
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(target),
                "--changed",
                "tests/test_workspace_proof_cli.py",
                "--record-receipt",
                "--receipt-command",
                "make test-workspace",
                "--receipt-result",
                "failed",
                "--receipt-log",
                ".agentic-workspace/local/proof-logs/workspace-test.log",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    receipt_path = target / ".agentic-workspace" / "local" / "proof-receipts" / "last.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    summary = payload["failure_summary"]
    assert summary == receipt["failure_summary"]
    assert summary["kind"] == "agentic-workspace/proof-failure-summary/v1"
    assert summary["failed_command"] == "make test-workspace"
    assert summary["log_source"]["path"] == ".agentic-workspace/local/proof-logs/workspace-test.log"
    assert summary["summary_trust"] == {
        "level": "higher",
        "source_kind": "repo-local-path",
        "rule": "Repo-local log references preserve audit access.",
    }
    assert summary["failure_line_count"] == 3
    assert summary["cluster_count"] == 2
    assert summary["top_root_cause_clusters"][0]["likely_root"] == "tests/test_workspace_proof_cli.py"
    assert summary["top_root_cause_clusters"][0]["occurrences"] == 2
    assert summary["focused_rerun_commands"][0] == (
        "uv run pytest tests/test_workspace_proof_cli.py::test_proof_current_selects_active_plan_validation_commands -q"
    )
    assert summary["full_suite_rerun_premature"] is True
    assert "Use the referenced full log" in summary["guardrails"][1]


def test_proof_failed_receipt_marks_excerpt_failure_summary_lower_trust(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(target),
                "--changed",
                "tests/test_workspace_proof_cli.py",
                "--record-receipt",
                "--receipt-command",
                "uv run pytest tests/test_workspace_proof_cli.py -q",
                "--receipt-result",
                "failed",
                "--receipt-log",
                "FAILED tests/test_workspace_proof_cli.py::test_example - AssertionError",
                "--format",
                "json",
            ]
        )
        == 0
    )

    summary = json.loads(capsys.readouterr().out)["failure_summary"]
    assert summary["log_source"]["kind"] == "caller-supplied-excerpt"
    assert summary["summary_trust"] == {
        "level": "lower",
        "source_kind": "caller-supplied-excerpt",
        "rule": "Caller-supplied excerpts are useful repair hints but lower trust than repo-local logs.",
    }


def test_proof_changed_reconciles_receipt_history_without_duplicate_runs(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _write(tmp_path / "src/agentic_workspace/workspace_runtime_proof.py", "# proof subject fixture\n")

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "--format",
                "json",
            ]
        )
        == 0
    )
    selected_commands = json.loads(capsys.readouterr().out)["answer"]["required_commands"]
    for command in selected_commands:
        assert (
            cli.main(
                [
                    "proof",
                    "--target",
                    str(tmp_path),
                    "--changed",
                    "src/agentic_workspace/workspace_runtime_proof.py",
                    "--record-receipt",
                    "--receipt-command",
                    command,
                    "--receipt-result",
                    "passed",
                    "--format",
                    "json",
                ]
            )
            == 0
        )
        capsys.readouterr()

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    reconciliation = answer["proof_receipt_reconciliation"]
    states = {item["command"]: item for item in reconciliation["commands"]}
    assert reconciliation["status"] == "accepted"
    assert reconciliation["accepted_count"] == len(selected_commands)
    assert reconciliation["receipt"]["command"] == selected_commands[-1]
    assert reconciliation["receipt_history"]["record_count"] == len(selected_commands)
    assert reconciliation["receipt_history"]["accepted_record_count"] == len(selected_commands)
    assert states["make test-workspace"]["evidence_state"] == "accepted"
    assert states["make test-workspace"]["diagnostic"] == "passed receipt accepted"
    assert states["make typecheck"]["evidence_state"] == "accepted"
    assert states["make typecheck"]["diagnostic"] == "passed receipt accepted"
    assert answer["proof_execution_evidence"]["status"] == "recorded-and-accepted"
    assert answer["proof_receipt_bridge"]["status"] == "complete"
    assert answer["proof_receipt_bridge"]["ready_to_record_count"] == 0
    assert answer["proof_receipt_bridge"]["template_blocked_count"] == 0
    assert answer["proof_receipt_bridge"]["next_action"] == "no receipt action required"
    assert answer["proof_receipt_bridge"]["next_recording_command"] == ""
    assert answer["proof_receipt_bridge"]["actions"] == []
    assert answer["proof_closeout_summary"]["receipt_bridge"] == {
        "status": "complete",
        "missing_receipt_count": 0,
        "detail_selector": "proof_receipt_bridge",
    }
    assert "closeout review" in answer["proof_execution_evidence"]["rule"]


def test_proof_changed_accepts_aggregate_receipt_for_selected_proof_set(tmp_path: Path, capsys) -> None:
    from agentic_workspace.proof_subject import build_proof_subject

    _write_repo_local_proof_target(tmp_path)
    receipt_dir = tmp_path / ".agentic-workspace" / "local" / "proof-receipts"
    _write(tmp_path / "src/agentic_workspace/workspace_runtime_proof.py", "# aggregate fixture\n")
    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "--format",
                "json",
            ]
        )
        == 0
    )
    selected_commands = json.loads(capsys.readouterr().out)["answer"]["required_commands"]
    receipt = {
        "kind": "agentic-workspace/proof-receipt/v1",
        "command": "selected proof set",
        "result": "passed",
        "recorded_at": "2026-07-09T00:00:00+00:00",
        "changed_paths": ["src/agentic_workspace/workspace_runtime_proof.py"],
        "proof_commands": selected_commands,
        "plan_id": "aggregate-proof",
    }
    receipt["proof_subject"] = build_proof_subject(
        target_root=tmp_path,
        changed_paths=receipt["changed_paths"],
        command=receipt["command"],
    )
    _write(receipt_dir / "last.json", json.dumps(receipt, indent=2))
    _write(receipt_dir / "history.jsonl", json.dumps(receipt, sort_keys=True) + "\n")

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    reconciliation = answer["proof_receipt_reconciliation"]
    states = {item["command"]: item for item in reconciliation["commands"]}
    assert reconciliation["status"] == "accepted"
    assert reconciliation["accepted_count"] == len(selected_commands)
    assert states["make test-workspace"]["receipt_match"] == "aggregate-selected-proof"
    assert states["make typecheck"]["diagnostic"] == "aggregate proof_commands receipt accepted"
    assert answer["proof_receipt_bridge"]["status"] == "complete"
    assert answer["proof_execution_evidence"]["status"] == "recorded-and-accepted"


def test_proof_changed_rejects_stale_aggregate_subject(tmp_path: Path, capsys) -> None:
    from agentic_workspace.proof_subject import build_proof_subject

    _write_repo_local_proof_target(tmp_path)
    source = tmp_path / "src/agentic_workspace/workspace_runtime_proof.py"
    _write(source, "before\n")
    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "--format",
                "json",
            ]
        )
        == 0
    )
    selected_commands = json.loads(capsys.readouterr().out)["answer"]["required_commands"]
    receipt = {
        "kind": "agentic-workspace/proof-receipt/v1",
        "command": "selected proof set",
        "result": "passed",
        "recorded_at": "2026-07-09T00:00:00+00:00",
        "changed_paths": ["src/agentic_workspace/workspace_runtime_proof.py"],
        "proof_commands": selected_commands,
    }
    receipt["proof_subject"] = build_proof_subject(target_root=tmp_path, changed_paths=receipt["changed_paths"], command=receipt["command"])
    receipt_dir = tmp_path / ".agentic-workspace" / "local" / "proof-receipts"
    _write(receipt_dir / "history.jsonl", json.dumps(receipt) + "\n")
    _write(source, "after\n")

    assert (
        cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", str(receipt["changed_paths"][0]), "--format", "json"]) == 0
    )

    states = {item["command"]: item for item in json.loads(capsys.readouterr().out)["answer"]["proof_receipt_reconciliation"]["commands"]}
    state = states["make test-workspace"]
    assert state["evidence_state"] == "subject-stale"
    assert state["receipt_match"] == "aggregate-selected-proof"
    assert state["minimum_rerun_command"] == "make test-workspace"


@pytest.mark.parametrize(
    ("subject", "changed_path", "expected_status"),
    [
        ("declared", "src/b.py", "partially-reusable"),
        ("incompatible", "src/a.py", "incompatible"),
        ("legacy", "src/a.py", "unverifiable"),
    ],
)
def test_proof_changed_reports_nonreusable_direct_subject_states(
    tmp_path: Path, capsys, subject: str, changed_path: str, expected_status: str
) -> None:
    from agentic_workspace.proof_subject import build_proof_subject

    _write_repo_local_proof_target(tmp_path)
    _write(tmp_path / "src/a.py", "a\n")
    _write(tmp_path / "src/b.py", "b\n")
    receipt = {
        "kind": "agentic-workspace/proof-receipt/v1",
        "command": "make test-workspace",
        "result": "passed",
        "recorded_at": "2026-07-09T00:00:00+00:00",
        "changed_paths": ["src/a.py"],
    }
    if subject != "legacy":
        receipt["proof_subject"] = build_proof_subject(
            target_root=tmp_path, changed_paths=receipt["changed_paths"], command=receipt["command"]
        )
    if subject == "incompatible":
        receipt["proof_subject"]["claim_classes"] = ["documentation-review"]
    receipt_dir = tmp_path / ".agentic-workspace" / "local" / "proof-receipts"
    _write(receipt_dir / "history.jsonl", json.dumps(receipt) + "\n")

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", changed_path, "--format", "json"]) == 0

    state = {item["command"]: item for item in json.loads(capsys.readouterr().out)["answer"]["proof_receipt_reconciliation"]["commands"]}[
        "make test-workspace"
    ]
    assert state["evidence_state"] == f"subject-{expected_status}"
    assert state["minimum_rerun_command"] == "make test-workspace"


def test_reconciliation_selects_reusable_history_before_newer_stale_subject(tmp_path: Path) -> None:
    from agentic_workspace.proof_subject import build_proof_subject
    from agentic_workspace.workspace_runtime_proof import _proof_receipt_reconciliation_payload

    source = tmp_path / "src/app.py"
    _write(source, "reusable\n")
    older = {
        "kind": "agentic-workspace/proof-receipt/v1",
        "command": "make test",
        "result": "passed",
        "recorded_at": "2026-07-09T00:00:00+00:00",
        "changed_paths": ["src/app.py"],
    }
    older["proof_subject"] = build_proof_subject(target_root=tmp_path, changed_paths=older["changed_paths"], command="make test")
    _write(source, "stale\n")
    newer = {**older, "recorded_at": "2026-07-10T00:00:00+00:00"}
    newer["proof_subject"] = build_proof_subject(target_root=tmp_path, changed_paths=newer["changed_paths"], command="make test")
    _write(source, "reusable\n")
    receipt_dir = tmp_path / ".agentic-workspace" / "local" / "proof-receipts"
    _write(receipt_dir / "history.jsonl", "\n".join(json.dumps(item) for item in (older, newer)) + "\n")

    reconciliation = _proof_receipt_reconciliation_payload(
        target_root=tmp_path, required_commands=["make test"], changed_paths=["src/app.py"]
    )

    assert reconciliation["status"] == "accepted"
    assert reconciliation["commands"][0]["receipt"]["recorded_at"] == older["recorded_at"]


def test_proof_requirement_tiers_keep_environmental_probes_non_blocking() -> None:
    from agentic_workspace.workspace_runtime_proof import _proof_receipt_reconciliation_payload, _proof_requirement_tiers_payload

    selected_commands = [
        {"command": "make test-workspace", "lane": "workspace_cli", "intent_type": "behavior-test"},
        {"command": "docker compose run conformance", "lane": "release_conformance", "intent_type": "environment-check"},
    ]
    required_commands = ["make test-workspace", "docker compose run conformance"]

    tiers = _proof_requirement_tiers_payload(
        selected_commands=selected_commands,
        required_commands=required_commands,
        optional_commands=["agentic-workspace summary --format json"],
        manual_proof_obligations=[],
        unavailable_commands=[],
        host_policy_blocked_commands=[],
    )
    assert tiers["counts"]["selected_required"] == 1
    assert tiers["counts"]["optional_environmental"] == 1
    assert tiers["categories"]["optional_environmental"][0]["blocking"] is False

    reconciliation = _proof_receipt_reconciliation_payload(
        target_root=None,
        required_commands=required_commands,
        changed_paths=["src/app.py"],
        selected_commands=selected_commands,
    )
    assert reconciliation["required_command_count"] == 1
    assert reconciliation["non_blocking_selected_count"] == 1
    assert [item["command"] for item in reconciliation["commands"]] == ["make test-workspace"]


def test_proof_record_receipt_rejects_command_not_selected_for_changed_paths(tmp_path: Path) -> None:
    _write_repo_local_proof_target(tmp_path)

    with pytest.raises(SystemExit) as exc_info:
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "README.md",
                "--record-receipt",
                "--receipt-command",
                "make test-workspace",
                "--receipt-result",
                "passed",
                "--format",
                "json",
            ]
        )
    assert exc_info.value.code == 2


def test_proof_changed_reports_dependency_scoped_staleness_and_minimum_rerun(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    source = tmp_path / "src/agentic_workspace/workspace_runtime_proof.py"
    _write(source, "before\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "--record-receipt",
                "--receipt-command",
                "make test-workspace",
                "--receipt-result",
                "passed",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()
    _write(source, "after\n")

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    states = {item["command"]: item for item in json.loads(capsys.readouterr().out)["answer"]["proof_receipt_reconciliation"]["commands"]}
    state = states["make test-workspace"]
    assert state["evidence_state"] == "subject-stale"
    assert state["subject_freshness"]["reasons"] == ["dependency-input-changed"]
    assert state["minimum_rerun_command"] == "make test-workspace"


def test_proof_changed_selector_routes_installed_docs_to_docs_review(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                ".agentic-workspace/docs/agent-installation.md",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert [lane["id"] for lane in answer["selected_lanes"]] == ["repo_docs_review"]
    assert answer["selected_lanes"][0]["proof_kind"] == "diff-review"
    assert ".agentic-workspace/docs" in answer["required_commands"][0]


def test_proof_changed_selector_reduces_package_docs_prefix_to_review(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert (
        cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "packages/planning/docs/usage.md", "--format", "json"]) == 0
    )

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert [lane["id"] for lane in answer["selected_lanes"]] == ["repo_docs_review"]
    assert answer["routing_reductions"] == [
        {
            "path": "packages/planning/docs/usage.md",
            "from_lane": "planning_package",
            "to_lane": "repo_docs_review",
            "reason": (
                "Markdown-only package documentation edits use review proof unless behavior, generated payload, install contracts, "
                "or implementation semantics also changed."
            ),
        }
    ]


def test_proof_changed_selector_composes_package_code_and_docs_without_reduction(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    changed_paths = [
        "packages/planning/src/repo_planning_bootstrap/example.py",
        "packages/planning/tests/test_example.py",
        "packages/planning/docs/usage.md",
    ]
    for path in changed_paths:
        _write(tmp_path / path, "# fixture\n")

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", *changed_paths, "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    lanes = {lane["id"]: lane for lane in answer["selected_lanes"]}
    assert {"planning_package", "repo_docs_review"}.issubset(lanes)
    assert lanes["planning_package"]["obligation_role"] == "primary-executable"
    assert lanes["repo_docs_review"]["obligation_role"] == "complementary-review"
    assert lanes["planning_package"]["changed_test_owner_route"]["status"] == "focused-owner-selected"
    assert answer.get("routing_reductions", []) == []
    assert answer["routing_compositions"] == [
        {
            "paths": ["packages/planning/docs/usage.md"],
            "primary_lane": "planning_package",
            "complementary_lanes": ["repo_docs_review"],
            "reason": "Docs review complements executable proof because the matched source lane is not documentation-only.",
        }
    ]


def test_proof_changed_selector_keeps_workspace_behavior_primary_for_memory_code_and_docs(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    changed_paths = [
        "src/agentic_workspace/memory_effectiveness.py",
        "tests/test_memory_effectiveness.py",
        ".agentic-workspace/docs/memory-metadata-contract.md",
        "packages/memory/README.md",
    ]
    for path in changed_paths:
        _write(tmp_path / path, "# fixture\n")

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", *changed_paths, "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    lanes = {lane["id"]: lane for lane in answer["selected_lanes"]}
    assert lanes["workspace_cli"]["obligation_role"] == "primary-executable"
    assert lanes["workspace_cli"]["changed_test_owner_route"]["status"] == "focused-owner-selected"
    assert lanes["repo_docs_review"]["obligation_role"] == "complementary-review"
    assert answer["proof_route_strategy_decision"]["outcome"] != "route-refinement-required"
    assert answer["proof_route_decision"]["route_source"] != "manual-fallback"
    assert any("tests/test_memory_effectiveness.py" in command for command in answer["required_commands"])
    assert any(command.startswith("git diff --") for command in answer["required_commands"])


def test_proof_changed_selector_retains_multiple_executable_owners_with_docs(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    changed_paths = [
        "src/agentic_workspace/example.py",
        "tests/test_example.py",
        "packages/planning/src/repo_planning_bootstrap/example.py",
        "packages/planning/tests/test_example.py",
        "packages/planning/docs/usage.md",
    ]
    for path in changed_paths:
        _write(tmp_path / path, "# fixture\n")

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", *changed_paths, "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    lanes = {lane["id"]: lane for lane in answer["selected_lanes"]}
    assert lanes["workspace_cli"]["obligation_role"] == "primary-executable"
    assert lanes["planning_package"]["obligation_role"] == "primary-executable"
    assert lanes["repo_docs_review"]["obligation_role"] == "complementary-review"
    assert any("tests/test_example.py" in command for command in answer["required_commands"])
    assert any("packages/planning/tests/test_example.py" in command for command in answer["required_commands"])


def test_proof_changed_selector_is_independent_of_rule_order(tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch) -> None:
    from agentic_workspace import workspace_runtime_proof

    _write_repo_local_proof_target(tmp_path)
    changed_paths = [
        "packages/planning/src/repo_planning_bootstrap/example.py",
        "packages/planning/tests/test_example.py",
        "packages/planning/docs/usage.md",
    ]
    for path in changed_paths:
        _write(tmp_path / path, "# fixture\n")

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", *changed_paths, "--format", "json"]) == 0
    original = json.loads(capsys.readouterr().out)["answer"]
    rules = list(workspace_runtime_proof._PROOF_SELECTION_RULES["rules"])
    monkeypatch.setitem(workspace_runtime_proof._PROOF_SELECTION_RULES, "rules", list(reversed(rules)))

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", *changed_paths, "--format", "json"]) == 0
    reordered = json.loads(capsys.readouterr().out)["answer"]

    assert [lane["id"] for lane in reordered["selected_lanes"]] == [lane["id"] for lane in original["selected_lanes"]]
    assert reordered["required_commands"] == original["required_commands"]
    assert reordered.get("routing_compositions") == original.get("routing_compositions")


def test_proof_changed_selector_keeps_contract_only_changes_focused(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "packages/planning/README.md",
                "src/agentic_workspace/contracts/proof_selection_rules.json",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert [lane["id"] for lane in answer["selected_lanes"]] == ["repo_docs_review", "contract_tooling"]
    assert {lane["proof_kind"] for lane in answer["selected_lanes"]} == {"diff-review", "surface-check"}
    assert not any(composition["primary_lane"] == "contract_tooling" for composition in answer.get("routing_compositions", []))


def test_proof_changed_selector_routes_structured_inventory_contract_change_to_focused_lane(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/contracts/structured_file_inventory.json",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert [lane["id"] for lane in answer["selected_lanes"]] == ["contract_tooling"]
    assert "make test-workspace" not in answer["required_commands"]


def test_proof_changed_selector_includes_schema_reference_docs_for_workspace_schema(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/contracts/schemas/operation_primitives.schema.json",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    lane_ids = [lane["id"] for lane in answer["selected_lanes"]]
    assert "contract_tooling" in lane_ids
    assert "schema_reference_docs" in lane_ids
    assert "make schema-reference-docs" in answer["required_commands"]
    schema_lane = next(lane for lane in answer["selected_lanes"] if lane["id"] == "schema_reference_docs")
    assert schema_lane["matched_paths"] == ["src/agentic_workspace/contracts/schemas/operation_primitives.schema.json"]
    assert "generated docs/reference" in schema_lane["when"]
    options = {option["id"]: option for option in answer["completion_options"]}
    assert tuple(options) == (
        "run-proof",
        "claim-slice-complete",
        "claim-work-complete",
        "keep-parent-open",
        "close-parent-lane",
        "route-residue",
        "request-review",
        "stop-with-status",
    )
    assert options["run-proof"]["allowed"] is True
    assert options["claim-slice-complete"]["allowed"] is False
    assert "proof selection is not proof execution" in options["claim-slice-complete"]["why"]
    assert options["claim-work-complete"]["allowed"] is False
    assert options["close-parent-lane"]["allowed"] is False
    assert options["stop-with-status"]["allowed"] is True


def test_proof_changed_surfaces_compact_intent_proof_prompt(capsys) -> None:
    assert (
        cli.main(
            [
                "proof",
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)
    assert answer["claim_boundary"]["completion_claim_allowed"] is False
    assert (
        cli.main(
            [
                "proof",
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--select",
                "intent_proof",
                "--format",
                "json",
            ]
        )
        == 0
    )
    intent_proof = json.loads(capsys.readouterr().out)["values"]["intent_proof"]
    assert intent_proof["status"] == "needs-agent-judgment"
    assert intent_proof["regression_only_risk"] == "possible"
    assert intent_proof["suggested_dimensions"]
    assert "question" in intent_proof
    assert "proof strength" not in json.dumps(answer["required_commands"]).lower()


def test_proof_changed_verbose_surfaces_proof_confidence(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    proof_confidence = answer["proof_confidence"]
    assert proof_confidence["confidence"] == "needs-review"
    assert proof_confidence["claim_boundary"] == "slice"
    assert proof_confidence["proven_dimensions"] == []
    assert proof_confidence["unproven_dimensions"]
    assert "Selected proof" in proof_confidence["residual_risk"]
    proof_adequacy = answer["proof_adequacy"]
    assert proof_adequacy["protocol"] == "Proof Adequacy"
    assert proof_adequacy["proof_surface_role"] == "proof selects evidence for the claim; it does not close work by itself"
    assert proof_adequacy["implement_surface_role"].startswith("implement --changed carries changed-path work context")
    assert proof_adequacy["required_evidence"]["commands"] == answer["required_commands"]
    assert proof_adequacy["confidence_evidence"]["commands"] == answer["optional_commands"]
    assert "completion permission without closeout" in proof_adequacy["claim_boundary"]["does_not_authorize"]
    assert "semantic intent satisfaction" in proof_adequacy["claim_boundary"]["does_not_authorize"]
    assert "parent issue, lane, or epic closure" in proof_adequacy["claim_boundary"]["does_not_authorize"]
    assert proof_adequacy["proof_confidence"]["claim_boundary"] == "slice"


def test_proof_changed_selector_includes_planning_schema_reference_wrapper(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "packages/planning/src/repo_planning_bootstrap/contracts/schemas/planning-execplan.schema.json",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    lane_ids = [lane["id"] for lane in answer["selected_lanes"]]
    assert "planning_package" in lane_ids
    assert "planning_schema_reference_docs" in lane_ids
    assert "make check-planning" in answer["required_commands"]


def test_planning_changed_test_owners_keep_proof_and_implement_narrow_and_in_sync(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    config = tmp_path / ".agentic-workspace" / "config.toml"
    config.write_text(
        config.read_text(encoding="utf-8")
        + """

[assurance.domain_proof_lanes.planning_package_behavior]
purpose = "Focused Planning package behavior."
applies_to_paths = ["packages/planning/src/**", "packages/planning/tests/**"]
commands = ["make test-planning"]
owner = "planning"
route_role = "behavior"
precedence = "50"

[assurance.domain_proof_lanes.test_evidence_decision]
purpose = "Focused test-evidence change review."
applies_to_paths = ["packages/**/tests/**"]
commands = ["uv run python scripts/run_agentic_workspace.py report --target . --section verification --format json"]
owner = "verification"
route_role = "evidence"
precedence = "70"

""",
        encoding="utf-8",
    )
    changed_paths = [
        "packages/planning/src/repo_planning_bootstrap/installer.py",
        "packages/planning/src/repo_planning_bootstrap/runtime_projection.py",
        "packages/planning/src/repo_planning_bootstrap/contracts/operations/planning.closeout.lifecycle.json",
        "packages/planning/tests/test_archive.py",
        "packages/planning/tests/test_branch_safe_planning.py",
    ]
    for path in changed_paths:
        _write(tmp_path / path, "{}\n" if path.endswith(".json") else "# fixture\n")

    assert cli.main(["proof", "--target", str(tmp_path), "--changed", *changed_paths, "--format", "json"]) == 0
    compact_proof = json.loads(capsys.readouterr().out)
    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                *changed_paths,
                "--task",
                "Keep Planning proof proportional after pruning",
                "--format",
                "json",
            ]
        )
        == 0
    )
    compact_implement_proof = json.loads(capsys.readouterr().out)["decision_packet"]["proof"]
    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", *changed_paths, "--format", "json"]) == 0
    proof = json.loads(capsys.readouterr().out)["answer"]

    owner_command = "uv run pytest packages/planning/tests/test_archive.py packages/planning/tests/test_branch_safe_planning.py -q"
    expected = {
        owner_command,
        "make lint-planning",
        "make typecheck-planning",
        "uv run python scripts/check/check_contract_tooling_surfaces.py --quiet-success",
        "uv run python scripts/check/check_generated_command_packages.py",
        f"{REPO_LOCAL_CLI_INVOKE} report --target . --section verification --format json",
    }
    assert expected.issubset(compact_proof["required_commands"])
    assert "make test-planning" not in compact_proof["required_commands"]
    assert compact_implement_proof["required_commands"] == compact_proof["required_commands"]
    assert proof["proof_narrowness"]["status"] == "narrow_required"
    assert compact_implement_proof["detail_route"]
    domain_lane = next(lane for lane in proof["selected_lanes"] if lane["id"] == "domain:planning_package_behavior")
    assert domain_lane["changed_test_owner_route"]["status"] == "focused-owner-selected"
    assert domain_lane["changed_test_owner_route"]["owner_paths"] == changed_paths[-2:]
    assert proof["proof_route_maintenance"]["fallback_selected_count"] == 0
    assert all(item.get("command") != "make test-planning" for item in proof["proof_route_maintenance"]["suggested_updates"])


def test_proof_changed_selector_includes_planning_source_typecheck_ci_parity(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "packages/planning/src/repo_planning_bootstrap/installer.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    lane_ids = [lane["id"] for lane in answer["selected_lanes"]]
    assert "planning_package" in lane_ids
    assert "planning_source_typecheck_ci_parity" in lane_ids
    assert "make typecheck-planning" in answer["required_commands"]
    planning_lane = next(lane for lane in answer["selected_lanes"] if lane["id"] == "planning_package")
    assert planning_lane["changed_test_owner_route"]["status"] == "full-package-fallback"
    assert "make test-planning" in answer["required_commands"]
    obligations = answer["proof_obligations"]
    assert obligations["required_proof"]["commands"] == answer["required_commands"]
    assert obligations["required_proof"]["status"] == "required"
    authority = {item["command"]: item for item in obligations["required_proof"]["command_authority"]}
    assert authority["make typecheck-planning"]["lane"] == "planning_source_typecheck_ci_parity"
    assert authority["make typecheck-planning"]["authority_source"]
    assert "agent still owns proof sufficiency" in authority["make typecheck-planning"]["rule"]
    assert obligations["recommended_confidence_checks"]["commands"] == answer["optional_commands"]
    assert obligations["recommended_confidence_checks"]["commands"] != answer["required_commands"]
    assert "do not replace or relax required proof" in obligations["recommended_confidence_checks"]["rule"]
    assert "Completion claims remain blocked" in obligations["completion_claim_rule"]
    assert answer["proof_adequacy"]["claim_boundary"]["completion_rule"] == obligations["completion_claim_rule"]
    assert answer["proof_adequacy"]["selected_lane_ids"][0] == "planning_package"
    assert obligations["compatibility"]["required_commands"] == "unchanged hard-gate field for existing callers"
    typecheck_lane = next(lane for lane in answer["selected_lanes"] if lane["id"] == "planning_source_typecheck_ci_parity")
    assert typecheck_lane["matched_paths"] == ["packages/planning/src/repo_planning_bootstrap/installer.py"]
    typecheck_step = next(step for step in answer["validation_plan"]["required"] if step["command"] == "make typecheck-planning")
    assert typecheck_step["lane_id"] == "planning_source_typecheck_ci_parity"
    typecheck_command = next(command for command in answer["selected_commands"] if command["command"] == "make typecheck-planning")
    assert typecheck_command["intent_type"] == "static-check"
    explanations = answer["proof_command_explanations"]
    typecheck_explanation = next(item for item in explanations["required"] if item["command"] == "make typecheck-planning")
    assert typecheck_explanation["blocking"] is True
    assert "changed-surface-risk" in typecheck_explanation["reason_classes"]
    assert "conservative-fallback" in typecheck_explanation["reason_classes"]
    assert all(item["blocking"] is False for item in explanations["optional_confidence"])
    assert explanations["blocking_rule"].startswith("Only required commands")


def test_proof_changed_selector_includes_workspace_runtime_typecheck_ci_parity(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _append_focused_proof_runtime_lane(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    lane_ids = [lane["id"] for lane in answer["selected_lanes"]]
    assert "domain:proof_runtime" in lane_ids
    assert "workspace_runtime_typecheck_ci_parity" in lane_ids
    assert "make typecheck" in answer["required_commands"]
    typecheck_lane = next(lane for lane in answer["selected_lanes"] if lane["id"] == "workspace_runtime_typecheck_ci_parity")
    assert typecheck_lane["matched_paths"] == ["src/agentic_workspace/workspace_runtime_proof.py"]
    assert typecheck_lane["route_authority"]["fallback_status"] == "seed-fallback"
    typecheck_command = next(command for command in answer["selected_commands"] if command["command"] == "make typecheck")
    assert typecheck_command["lane"] == "workspace_runtime_typecheck_ci_parity"
    assert typecheck_command["fallback_status"] == "seed-fallback"
    authority = {item["command"]: item for item in answer["proof_obligations"]["required_proof"]["command_authority"]}
    assert authority["make typecheck"]["route_authority"] == "package-seed-or-default-route"
    assert answer["proof_route_maintenance"]["fallback_selected_count"] >= 1
    assert answer["proof_route_maintenance"]["ci_gap_candidate_count"] >= 1
    maintenance = answer["proof_route_maintenance"]
    assert maintenance["route_hints_surface_contract"]["surface"] == ".agentic-workspace/proof-route-hints.json"
    assert maintenance["route_hints_surface_contract"]["surface_status"] == "absent"
    reasons = {item["reason"] for item in answer["proof_route_maintenance"]["suggested_updates"]}
    assert "CI-learned proof gap should be captured as repo route authority" in reasons
    route_hint_suggestions = [
        item for item in maintenance["suggested_updates"] if item.get("target_surface") == ".agentic-workspace/proof-route-hints.json"
    ]
    assert route_hint_suggestions
    assert all(item["target_surface_status"] == "absent" for item in route_hint_suggestions)
    assert all(item["target_surface_contract"]["owner"] == "repo" for item in route_hint_suggestions)


def test_proof_changed_learned_route_table_can_override_package_default_authority(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "Makefile", "typecheck:\n\tpython -m compileall src\n")
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_proof.py", "VALUE = 1\n")
    _write(
        tmp_path / ".agentic-workspace" / "proof-route-hints.json",
        json.dumps(
            {
                "kind": "agentic-workspace/proof-route-hints/v1",
                "schema_version": "proof-route-hints/v1",
                "hints": [
                    {
                        "id": "workspace-runtime:typecheck",
                        "state": "confirmed",
                        "intent_type": "static-check",
                        "candidate_command": "make typecheck",
                        "source": "memory",
                        "source_path": ".agentic-workspace/proof-route-hints.json",
                        "confidence": "high",
                        "requires_live_confirmation": False,
                        "scope": "src/agentic_workspace",
                        "owner": "Memory",
                        "provenance": "CI failed on workspace runtime type errors; route confirmed by prior closeout.",
                        "learned_at": "2026-06-29",
                    }
                ],
            }
        ),
    )

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    lane_ids = [lane["id"] for lane in answer["selected_lanes"]]
    assert "workspace_runtime_typecheck_ci_parity" in lane_ids
    assert "learned_route:workspace-runtime:typecheck" in lane_ids
    assert answer["required_commands"].count("make typecheck") == 1
    selected_typecheck = [command for command in answer["selected_commands"] if command["command"] == "make typecheck"]
    selected_authorities = {command["route_authority"] for command in selected_typecheck}
    assert "package-seed-or-default-route" in selected_authorities
    assert "repo-learned-route-table" in selected_authorities
    obligations = {item["command"]: item for item in answer["proof_obligations"]["required_proof"]["command_authority"]}
    assert obligations["make typecheck"]["route_authority"] == "repo-learned-route-table"
    precedence = answer["proof_route_precedence"]
    assert precedence["status"] == "competing-routes"
    assert precedence["cases"][0]["winner"]["route_source"] == "repo-learned-proof-route"
    overridden_authorities = {item["route_authority"] for item in precedence["cases"][0]["overridden"]}
    assert "package-seed-or-default-route" in overridden_authorities


def test_proof_changed_selector_keeps_docs_only_work_off_workspace_runtime_typecheck(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "README.md", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert "make typecheck" not in answer["required_commands"]
    assert "workspace_runtime_typecheck_ci_parity" not in [lane["id"] for lane in answer["selected_lanes"]]


def test_proof_changed_selector_flags_high_impact_skill_behavior_evidence(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "packages/planning/skills/planning-closeout-trust/SKILL.md",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    review = answer["skill_behavior_impact_review"]
    assert review["status"] == "behavior-evidence-required"
    assert review["high_impact_paths"] == ["packages/planning/skills/planning-closeout-trust/SKILL.md"]
    assert "What behavior is this skill meant to steer?" in review["required_answers"]
    assert "Tests passed, so completion is claimable." in json.dumps(answer["proof_strategy"]["anti_rationalization_gates"])


def test_proof_tiny_readme_profile_keeps_docs_only_validation_light(capsys) -> None:
    assert cli.main(["proof", "--changed", "README.md", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    encoded = json.dumps(payload)
    docs_diff = "git diff -- README.md docs .agentic-workspace/docs packages/planning/README.md packages/memory/README.md"
    assert payload["kind"] == "proof-next-decision/v1"
    assert payload["next"]["command"] == docs_diff
    assert payload["required_commands"] == [docs_diff]
    assert "uv run pytest tests -q" not in encoded
    assert len(encoded) < 6000


def test_proof_default_is_one_complete_claim_safe_decision_with_exact_escape_hatches(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "README.md", "# Proof fixture\n")

    assert cli.main(["proof", "--target", str(tmp_path), "--changed", "README.md", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["kind"] == "proof-next-decision/v1"
    assert payload["identity"]["decision_id"]
    assert payload["identity"]["proof_subject"]["changed_paths"] == ["README.md"]
    assert payload["next"]["action"]
    assert payload["next"]["action"] == "manual-verification"
    assert payload["manual_verification"]["status"] == "required"
    assert payload["receipt"]["status"]
    assert payload["sufficiency"]["status"] == "not-yet-sufficient"
    assert payload["claim_boundary"]["completion_claim_allowed"] is False
    assert set(payload["detail_routes"]) >= {"route", "receipts", "command_tiers", "closeout", "select", "verbose"}
    assert payload["absence_states"]["raw_workspace_files"] == "not-required-for-ordinary-action"
    assert "proof_route_selection" not in payload
    assert "proof_closeout_summary" not in payload

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "README.md",
                "--select",
                "proof_route_strategy_decision,proof_receipt_reconciliation,proof_closeout_summary",
                "--format",
                "json",
            ]
        )
        == 0
    )
    detail = json.loads(capsys.readouterr().out)["values"]
    assert set(detail) == {"proof_route_strategy_decision", "proof_receipt_reconciliation", "proof_closeout_summary"}


def _compression_field_count(value: object) -> int:
    if isinstance(value, dict):
        return len(value) + sum(_compression_field_count(item) for item in value.values())
    if isinstance(value, list):
        return sum(_compression_field_count(item) for item in value)
    return 0


def _compression_measurement(value: dict[str, object]) -> dict[str, int]:
    compact = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return {
        "json_bytes": len(compact),
        "human_lines": len(json.dumps(value, ensure_ascii=False, indent=2).splitlines()),
        "field_count": _compression_field_count(value),
        "aw_roundtrips": 1,
    }


def _proof_compression_scenario_payloads() -> dict[str, dict[str, dict[str, object]]]:
    from agentic_workspace.workspace_runtime_proof import _ordinary_proof_next_decision_payload

    def scenario(
        *,
        name: str,
        commands: list[str],
        closeout_status: str = "not-yet-sufficient",
        receipt_status: str = "not-recorded",
        remaining_gaps: list[str] | None = None,
        manual: dict[str, object] | None = None,
        unavailable: list[dict[str, object]] | None = None,
        narrowness: dict[str, object] | None = None,
        module_rich: bool = False,
    ) -> dict[str, dict[str, object]]:
        changed = [f"fixtures/{name}.py"]
        answer: dict[str, object] = {
            "proof_route_decision": {
                "route_source": "changed-paths",
                "selected_command": {
                    "route_authority": "live-confirmed-proof-rule",
                    "lane": name,
                },
            },
            "proof_route_strategy_preservation": {
                "decision_id": f"decision-{name}",
                "route_health_id": f"health-{name}",
                "claim_effect": "selected-proof-required",
                "proof_route_health": {"status": "current", "finding_count": 0},
            },
            "proof_receipt_reconciliation": {
                "status": receipt_status,
                "selected_proof_identity": {
                    "id": f"proof-{name}",
                    "fingerprint": f"fingerprint-{name}",
                    "command_count": len(commands),
                },
            },
            "proof_receipt_bridge": {
                "missing_receipt_count": 0 if receipt_status == "recorded" else len(commands),
                "next_recording_command": "agentic-workspace proof --record-receipt --format json",
            },
            "proof_closeout_summary": {
                "status": closeout_status,
                "remaining_gaps": remaining_gaps or [],
            },
            "proof_route_strategy_claim_gate": {"claim_effect": "selected-proof-required"},
            "manual_verification": manual,
            "unavailable_proof_commands": unavailable or [],
        }
        if module_rich:
            answer.update(
                {
                    "architecture_principles": {"status": "applicable", "items": [{"id": "one-phase-authority"}]},
                    "verification": {"status": "configured", "scenario_count": 12},
                    "test_strategy_check": {"status": "present", "recommendations": ["keep proof narrow"]},
                }
            )
        next_decision: dict[str, object] = {
            "kind": "proof-next-decision/v1",
            "next": {
                "action": "run-validation-command" if commands else "manual-verification",
                "command": commands[0] if commands else None,
                "required": bool(commands or manual),
                "route_source": "changed-paths",
            },
            "required_commands": commands,
            "manual_verification": manual,
            "warnings": [],
        }
        if narrowness:
            next_decision["proof_narrowness"] = narrowness
        before = {
            "profile": "compact-contract-answer/v1",
            "surface": "proof",
            "target": ".",
            "selector": {"changed": changed},
            "answer": answer,
            **answer,
            "proof_next_decision": next_decision,
        }
        after = _ordinary_proof_next_decision_payload(
            next_decision=next_decision,
            answer=answer,
            target=".",
            selector={"changed": changed},
            cli_invoke="agentic-workspace",
        )
        return {"before": before, "after": after}

    return {
        "passed_clean": scenario(
            name="passed-clean",
            commands=["uv run pytest tests/test_passed.py -q"],
            closeout_status="sufficient-recorded",
            receipt_status="recorded",
        ),
        "failed_result": scenario(
            name="failed-result",
            commands=["uv run pytest tests/test_failed.py -q"],
            receipt_status="failed",
            remaining_gaps=["proof result failed"],
        ),
        "stale_receipt": scenario(
            name="stale-receipt",
            commands=["uv run pytest tests/test_stale.py -q"],
            receipt_status="stale",
            remaining_gaps=["proof result missing or stale"],
        ),
        "missing_receipt": scenario(
            name="missing-receipt",
            commands=["uv run pytest tests/test_missing.py -q"],
            receipt_status="not-recorded",
            remaining_gaps=["proof result missing"],
        ),
        "manual_verification": scenario(
            name="manual",
            commands=[],
            manual={"status": "required", "summary": "Inspect the rendered result.", "templates": ["record outcome"]},
            remaining_gaps=["manual verification remains"],
        ),
        "multi_command_broad_required": scenario(
            name="multi-command",
            commands=[
                "uv run pytest tests/test_workspace_cli.py -q",
                "make lint-workspace",
                "make typecheck",
            ],
            narrowness={"status": "broad_required", "broad_suite_boundary_status": "required"},
            remaining_gaps=["multiple proof commands remain"],
        ),
        "unavailable_runtime": scenario(
            name="unavailable-runtime",
            commands=["docker compose run proof"],
            unavailable=[{"command": "docker compose run proof", "reason": "docker unavailable"}],
            remaining_gaps=["runtime unavailable"],
        ),
        "module_rich": scenario(
            name="module-rich",
            commands=["uv run pytest tests/test_module.py -q"],
            module_rich=True,
            remaining_gaps=["proof result missing"],
        ),
    }


def test_proof_compression_evidence_records_cost_and_named_safety_expansion() -> None:
    evidence = json.loads(Path("docs/maintainer/proof-compression-2684.json").read_text(encoding="utf-8"))
    assert evidence["schema_version"] == "agentic-workspace/proof-compression-evidence/v1"
    assert evidence["projection_disposition"]["authoritative"] == "proof_next_decision"
    fixtures = _proof_compression_scenario_payloads()
    assert set(evidence["scenarios"]) == set(fixtures)
    budget = evidence["accepted_ordinary_budget"]
    for name, payloads in fixtures.items():
        recorded = evidence["scenarios"][name]
        assert recorded["before"] == _compression_measurement(payloads["before"])
        assert recorded["after"] == _compression_measurement(payloads["after"])
        assert recorded["after"]["aw_roundtrips"] == recorded["before"]["aw_roundtrips"] == 1
        over_budget = (
            recorded["after"]["json_bytes"] > budget["max_json_bytes"]
            or recorded["after"]["field_count"] > budget["max_field_count"]
            or recorded["after"]["human_lines"] > budget["max_human_text_lines"]
            or (recorded["after"]["json_bytes"] + 3) // 4 > budget["max_estimated_tokens"]
        )
        assert not over_budget or recorded.get("expansion_reason") in evidence["named_expansion_reasons"]
    assert evidence["scenarios"]["manual_verification"]["expansion_reason"]
    assert evidence["scenarios"]["unavailable_runtime"]["expansion_reason"]
    assert evidence["scenarios"]["missing_receipt"]["expansion_reason"] == "failed-stale-or-missing-receipt"
    assert evidence["default_guidance_proof"]["mandatory_selector_calls"] == 0
    assert evidence["default_guidance_proof"]["interaction_trace"]["claim"] == "blocked"
    assert evidence["total_operating_cost"]["assessment"] == "reduced-with-explicit-safety-expansion"


def test_default_only_weak_agent_consumes_actual_proof_guidance_without_follow_up_reads() -> None:
    operation = json.loads(Path("src/agentic_workspace/contracts/operations/proof.report.json").read_text(encoding="utf-8"))
    guidance = next(guard for guard in operation["guards"] if "proof_next_decision is authoritative" in guard)
    packet = _proof_compression_scenario_payloads()["multi_command_broad_required"]["after"]

    trace = {
        "guidance_source": "src/agentic_workspace/contracts/operations/proof.report.json#guards",
        "guidance": guidance,
        "workspace_commands": ["agentic-workspace proof --changed fixtures/multi-command.py --format json"],
        "required_commands_enumerated": list(packet["required_commands"]),
        "manual_blocker": packet.get("manual_verification"),
        "runtime_blockers": packet.get("blockers", []),
        "receipt_freshness": packet["identity"]["freshness"],
        "claim": packet["claim_boundary"]["status"],
        "selector_calls": 0,
        "verbose_calls": 0,
        "raw_workspace_reads": 0,
        "route_reversals": 0,
    }

    assert trace["required_commands_enumerated"] == [
        "uv run pytest tests/test_workspace_cli.py -q",
        "make lint-workspace",
        "make typecheck",
    ]
    assert trace["claim"] == "blocked"
    assert packet["claim_boundary"]["completion_claim_allowed"] is False
    assert trace["selector_calls"] == trace["verbose_calls"] == trace["raw_workspace_reads"] == 0
    evidence = json.loads(Path("docs/maintainer/proof-compression-2684.json").read_text(encoding="utf-8"))
    assert evidence["default_guidance_proof"]["interaction_trace"] == trace


def test_proof_changed_selector_flags_direct_cli_edits(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "generated/workspace/python/cli.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert [lane["id"] for lane in answer["selected_lanes"]] == [
        "workspace_cli",
        "cli_authority",
        "generated_command_packages",
        "subsystem:workspace-cli-runtime",
        "assurance-requirement:subsystem:workspace-cli-runtime",
        "verification:closeout_intent_satisfaction",
        "verification:generated_adapter_conformance",
        "verification:requirement_grounding_delegation",
    ]
    authority_review = answer["cli_authority_review"]
    assert authority_review["status"] == "blocked-direct-edit-route-to-source"
    assert answer["escalate_when"][0] == "changed paths span multiple validation lanes; run all selected commands or split the work"
    root_cli = authority_review["classifications"][0]
    assert root_cli["role"] == "projection"
    assert root_cli["direct_edit_allowed"] is False
    assert root_cli["source_contract"] == "src/agentic_workspace/contracts/command_package_ir.json"
    assert root_cli["regeneration_path"] == "uv run python scripts/generate/generate_command_packages.py"
    assert authority_review["authority_query"] == "agentic-workspace defaults --section root_cli_authority --format json"
    review = payload["answer"]["direct_cli_edit_review"]
    assert review["status"] == "review-needed"
    assert review["changed_paths"] == ["generated/workspace/python/cli.py"]
    assert "normal interface authoring belongs in command contracts" in review["rule"]
    assert "runtime primitive implementation and live workspace inspection" in review["allowed_direct_cli_work"]
    assert "route interface or generated-surface changes back" in review["recovery_signal"]
    assert answer["subsystem_ownership"]["matched_subsystems"][0]["id"] == "workspace-cli-runtime"


def test_proof_routes_root_generated_fingerprint_through_existing_generated_package_authority(capsys) -> None:
    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(ROOT),
                "--changed",
                "generated/workspace/.agentic-workspace-cli-fingerprint.json",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    lane_ids = [lane["id"] for lane in answer["selected_lanes"]]
    assert "generated_command_packages" in lane_ids
    assert "cli_authority" in lane_ids
    assert "uv run --active python scripts/check/check_generated_command_packages.py --require-node" in answer["required_commands"]
    assert (
        "uv run --active python scripts/check/check_generated_command_packages.py --conformance --require-node"
        in answer["required_commands"]
    )
    assert answer["generated_cli_freshness"]["freshness_check_command"] == (
        "uv run python scripts/generate/generate_command_packages.py --check"
    )
    classification = answer["cli_authority_review"]["classifications"][0]
    assert classification["classification_id"] == "generated-command-package-output"
    assert classification["role"] == "projection"
    assert classification["direct_edit_allowed"] is False
    assert classification["source_contract"] == "src/agentic_workspace/contracts/command_package_ir.json"
    assert classification["regeneration_path"] == "uv run python scripts/check/check_generated_command_packages.py"


def test_assignment_adapter_support_surfaces_compose_focused_proof_owners(capsys) -> None:
    changed = [
        "docs/reference/workspace-local-override.md",
        "src/agentic_workspace/contracts/python_primitive_support.py",
        "src/agentic_workspace/contracts/schemas/workspace_local_override.schema.json",
        "tools/model-cli-harness/external-agent-evaluation/representative-result.json",
    ]

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(ROOT),
                "--changed",
                *changed,
                "--select",
                "proof_route_strategy_decision,focused_route_coverage_audit,route_refinement_required,required_commands,selected_lanes",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["values"]
    lane_ids = {lane["id"] for lane in answer["selected_lanes"]}
    assert answer["proof_route_strategy_decision"]["outcome"] == "focused"
    assert answer["focused_route_coverage_audit"]["status"] == "covered"
    assert answer["route_refinement_required"]["uncovered_paths"] == []
    assert {
        "domain:generated_command_packages",
        "domain:maintained_external_evaluation_evidence",
        "domain:workspace_local_override_contract",
    }.issubset(lane_ids)
    assert "domain:correction_guidance_authority" not in lane_ids
    assert "domain:session_logging_friction" not in lane_ids
    assert "domain:workspace_root_guidance" not in lane_ids
    assert len(answer["required_commands"]) <= 9
    assert not any("-k correction" in command for command in answer["required_commands"])
    assert not any("session_logging" in command for command in answer["required_commands"])


def test_assignment_adapter_support_route_retains_genuine_additional_owner(capsys) -> None:
    changed = [
        "docs/reference/workspace-local-override.md",
        "src/agentic_workspace/contracts/python_primitive_support.py",
        "src/agentic_workspace/contracts/schemas/workspace_local_override.schema.json",
        "tools/model-cli-harness/external-agent-evaluation/representative-result.json",
        "src/agentic_workspace/session_logging.py",
    ]

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(ROOT),
                "--changed",
                *changed,
                "--select",
                "proof_route_strategy_decision,route_refinement_required,required_commands,selected_lanes",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["values"]
    lane_ids = {lane["id"] for lane in answer["selected_lanes"]}
    assert answer["proof_route_strategy_decision"]["outcome"] == "focused"
    assert answer["route_refinement_required"]["uncovered_paths"] == []
    assert "domain:session_logging_friction" in lane_ids
    assert any("tests/test_workspace_session_logging.py -k slow_commands -q" in command for command in answer["required_commands"])


def test_generated_fingerprint_route_reports_typed_node_gap_without_losing_ownership(capsys, monkeypatch) -> None:
    from agentic_workspace import workspace_runtime_proof

    real_which = workspace_runtime_proof.shutil.which
    monkeypatch.setattr(
        workspace_runtime_proof.shutil, "which", lambda executable: None if executable == "node" else real_which(executable)
    )

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(ROOT),
                "--changed",
                "generated/workspace/.agentic-workspace-cli-fingerprint.json",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert "generated_command_packages" in [lane["id"] for lane in answer["selected_lanes"]]
    unavailable = [item for item in answer["unavailable_proof_commands"] if item["lane"] == "domain:generated_command_packages"]
    assert [item["command"] for item in unavailable] == [
        "uv run python scripts/check/check_generated_command_packages.py --require-node",
        "uv run python scripts/check/check_generated_command_packages.py --conformance --require-node",
    ]
    assert {item["required_runtime"] for item in unavailable} == {"node"}
    assert answer["proof_route_strategy_decision"]["outcome"] == "broad-escalation-required"
    assert answer["proof_route_strategy_decision"]["claim_effect"] == "claim-blocked"
    assert answer["route_refinement_required"]["status"] == "not-required"
    assert answer["manual_verification"]["status"] == "route-refinement-required"


def test_generated_package_authority_keeps_sibling_output_and_unknown_root_file_distinct(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "generated/workspace/typescript/cli.mjs",
                "generated/unknown-root-metadata.json",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    classified_paths = {item["path"] for item in answer["cli_authority_review"]["classifications"]}
    assert "generated/workspace/typescript/cli.mjs" in classified_paths
    assert "generated/unknown-root-metadata.json" not in classified_paths


def test_generated_fingerprint_route_authorities_remain_consistent() -> None:
    fingerprint = "generated/workspace/.agentic-workspace-cli-fingerprint.json"
    config = tomllib.loads((ROOT / ".agentic-workspace/config.toml").read_text(encoding="utf-8"))
    rules = json.loads((ROOT / "src/agentic_workspace/contracts/proof_selection_rules.json").read_text(encoding="utf-8"))

    domain_paths = config["assurance"]["domain_proof_lanes"]["generated_command_packages"]["applies_to_paths"]
    route = next(item for item in rules["rules"] if item["id"] == "generated-command-packages")
    classification = next(item for item in rules["cli_authority"]["classifications"] if item["id"] == "generated-command-package-output")

    assert fingerprint in domain_paths
    assert fingerprint in route["exact"]
    assert fingerprint in classification["exact"]
    assert classification["direct_edit_allowed"] is False
    assert any(
        "check_generated_command_packages.py --require-node" in command
        for command in config["assurance"]["domain_proof_lanes"]["generated_command_packages"]["commands"]
    )


def test_proof_changed_selector_broadens_contract_plus_cli_changes(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/contracts/proof_selection_rules.json",
                "generated/workspace/python/cli.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert [lane["id"] for lane in answer["selected_lanes"]] == [
        "contract_tooling",
        "workspace_cli",
        "cli_authority",
        "generated_command_packages",
        "subsystem:workspace-cli-runtime",
        "assurance-requirement:subsystem:workspace-cli-runtime",
        "verification:closeout_intent_satisfaction",
        "verification:generated_adapter_conformance",
        "verification:requirement_grounding_delegation",
    ]
    assert answer["escalate_when"][0] == "changed paths span multiple validation lanes; run all selected commands or split the work"
    assert "make test-workspace" not in answer["required_commands"]
    assert "make test-workspace" in answer["optional_commands"]
    workspace_lane = next(lane for lane in answer["selected_lanes"] if lane["id"] == "workspace_cli")
    assert workspace_lane["focused_route_reduction"]["status"] == "broad-proof-withheld-for-explicit-escalation"
    assert answer["proof_narrowness"]["broad_suite_boundary"]["status"] == "explicit-escalation-required"
    assert answer["proof_route_escalation_gate"]["status"] == "blocked-explicit-escalation-required"


def test_proof_changed_selector_escalates_for_cross_lane_changes(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "packages/planning/src/repo_planning_bootstrap/installer.py",
                "generated/workspace/python/cli.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert [lane["id"] for lane in answer["selected_lanes"]] == [
        "planning_package",
        "workspace_cli",
        "cli_authority",
        "generated_command_packages",
        "subsystem:workspace-cli-runtime",
        "planning_source_typecheck_ci_parity",
        "assurance-requirement:subsystem:workspace-cli-runtime",
        "verification:closeout_intent_satisfaction",
        "verification:generated_adapter_conformance",
        "verification:requirement_grounding_delegation",
    ]
    assert answer["escalate_when"][0] == "changed paths span multiple validation lanes; run all selected commands or split the work"
    assert "make typecheck-planning" in answer["required_commands"]
    package_step = answer["validation_plan"]["required"][0]
    assert package_step["command"] == "make test-planning"
    assert package_step["cwd"] == "."
    assert package_step["run"] == "make test-planning"
    assert package_step["lane_id"] == "planning_package"


def test_proof_changed_selector_accepts_existing_durable_surface_update(tmp_path: Path, capsys) -> None:
    contract_path = tmp_path / "src" / "agentic_workspace" / "contracts" / "report_contract.json"
    contract_path.parent.mkdir(parents=True)
    contract_path.write_text("{}\n", encoding="utf-8")

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/contracts/report_contract.json",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    review = payload["answer"]["surface_value_review"]
    assert review["kind"] == "surface-value-review/v1"
    assert review["status"] == "accepted"
    assert review["accepted_count"] == 1
    assert review["flagged_count"] == 0
    assert review["reviewed_paths"][0]["surface_class"] == "workspace_contract_surface"
    assert review["reviewed_paths"][0]["result"] == "accepted"
    assert review["review_gate"]["ordinary_path"] == "agentic-workspace proof --target ./repo --changed <paths> --format json"


def test_proof_changed_selector_flags_additive_only_durable_surface(tmp_path: Path, capsys) -> None:
    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "docs/new-first-line-concept.md",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    review = payload["answer"]["surface_value_review"]
    assert review["status"] == "attention-needed"
    assert review["accepted_count"] == 0
    assert review["flagged_count"] == 1
    assert review["reviewed_paths"][0]["result"] == "flagged"
    assert review["reviewed_paths"][0]["disposition"] == "additive-only durable surface candidate"
    assert "what repeated cost does this remove?" in review["reviewed_paths"][0]["required_answers"]


def test_proof_changed_selector_accepts_deleted_durable_surface(tmp_path: Path, capsys) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "agent@example.test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Agent"], cwd=tmp_path, check=True)
    contract_path = tmp_path / "src" / "agentic_workspace" / "contracts" / "old_surface.json"
    contract_path.parent.mkdir(parents=True)
    contract_path.write_text("{}\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=tmp_path, check=True, capture_output=True)
    contract_path.unlink()
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/contracts/old_surface.json",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    review = payload["answer"]["surface_value_review"]
    assert review["status"] == "accepted"
    assert review["accepted_count"] == 1
    assert review["flagged_count"] == 0
    assert review["reviewed_paths"][0]["result"] == "accepted"
    assert review["reviewed_paths"][0]["disposition"] == "removed durable surface"


def _write_proof_architecture_principles(target_root: Path) -> None:
    _write(
        target_root / ".agentic-workspace" / "system-intent" / "intent.toml",
        """
kind = "agentic-workspace/system-intent/v1"
summary = "Portable host-neutral operating intent."
governing_intents = []
anti_intents = []
decision_tests = []
confidence = "high"
needs_review = false

[[architecture_principles]]
id = "host-agnostic-agent-judgment"
title = "Preserve host-agnostic agent judgment"
authority = "repo-system-intent"
owner = "workspace-runtime"
summary = "AW provides infrastructure for agent judgment instead of package-owned host assumptions."
path_globs = ["src/agentic_workspace/workspace_runtime*.py"]
guardrail_refs = ["docs/maintainer/non-enum-keyword-routing-audit.json"]
derived_applications = ["non-enum-keyword-routing"]
proof_expectation = "Closeout must state whether the principle was preserved or re-scoped."
review_aids = ["Confirm proof selection did not infer from prose keywords."]
claim_boundary = "architecture-principle-preservation"
""",
    )


def test_proof_changed_selects_host_declared_domain_proof_lane(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_proof_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        f"""
schema_version = 1

[workspace]
cli_invoke = "{REPO_LOCAL_CLI_INVOKE}"

[assurance.domain_proof_lanes.access_control]
purpose = "Access-control changes need domain proof and review evidence."
applies_to_paths = ["services/auth/**"]
commands = ["python -c \\"print('access proof')\\""]
manual_evidence = ["host:access_matrix"]
review_aids = ["Inspect role-to-permission impact."]
evidence_concepts = ["host:access_matrix"]
authority_refs = ["SECURITY.md#access-control"]
claim_boundary = "access-control-proof-required-before-full-claim"
owner = "security"
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "verification" / "manifest.toml",
        """
schema_version = "agentic-workspace/verification-manifest/v1"

[evidence_concepts."host:access_matrix"]
title = "Access Matrix"
meaning = "Host-owned role-to-permission review matrix."
owner = "security"
""",
    )
    _write(tmp_path / "services" / "auth" / "policy.py", "ALLOW = True\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "services/auth/policy.py",
                "--select",
                "proof_decision",
                "--format",
                "json",
            ]
        )
        == 0
    )

    packet = json.loads(capsys.readouterr().out)["values"]["proof_decision"]
    domain = next(lane for lane in packet["selected_lanes"] if lane["id"] == "domain:access_control")
    assert domain["domain_lane"]["source"] == ".agentic-workspace/config.toml [assurance.domain_proof_lanes]"
    assert domain["manual_evidence"] == ["host:access_matrix"]
    assert domain["evidence_concept_usage"]["used"][0]["id"] == "host:access_matrix"
    assert domain["evidence_concept_usage"]["degraded"] == []
    assert domain["claim_boundary"] == "access-control-proof-required-before-full-claim"
    assert domain["route_authority"]["authority"] == "repo-owned-domain-proof-lane"
    assert packet["safe_claim_now"]["state"] == "manual-review-required"


def test_domain_proof_lane_undeclared_host_concepts_degrade(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_proof_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        f"""
schema_version = 1

[workspace]
cli_invoke = "{REPO_LOCAL_CLI_INVOKE}"

[assurance.domain_proof_lanes.access_control]
purpose = "Access-control changes need domain proof and review evidence."
applies_to_paths = ["services/auth/**"]
manual_evidence = ["host:access_matrix"]
evidence_concepts = ["host:access_matrix"]
owner = "security"
""",
    )
    _write(tmp_path / "services" / "auth" / "policy.py", "ALLOW = True\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "services/auth/policy.py",
                "--select",
                "proof_decision",
                "--format",
                "json",
            ]
        )
        == 0
    )

    packet = json.loads(capsys.readouterr().out)["values"]["proof_decision"]
    domain = next(lane for lane in packet["selected_lanes"] if lane["id"] == "domain:access_control")
    usage = domain["evidence_concept_usage"]
    assert usage["used"] == []
    assert usage["degraded"][0]["id"] == "host:access_matrix"
    assert usage["degraded"][0]["state"] == "undeclared-host-concept"
    assert "domain proof lane contains undeclared or unclassified evidence concepts" in packet["missing_or_unresolved"]["blockers"]
    assert packet["missing_or_unresolved"]["degraded_evidence_concepts"][0]["lane"] == "domain:access_control"


def test_domain_proof_lanes_compose_and_skip_non_matching_changes(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_proof_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        f"""
schema_version = 1

[workspace]
cli_invoke = "{REPO_LOCAL_CLI_INVOKE}"

[assurance.domain_proof_lanes.access_control]
purpose = "Access-control changes need access proof."
applies_to_paths = ["services/auth/**"]
commands = ["python -c \\"print('access proof')\\""]

[assurance.domain_proof_lanes.audit_events]
purpose = "Access-control changes need audit-event proof."
applies_to_paths = ["services/auth/**"]
commands = ["python -c \\"print('audit proof')\\""]
""",
    )
    _write(tmp_path / "services" / "auth" / "policy.py", "ALLOW = True\n")
    _write(tmp_path / "docs" / "readme.md", "# Docs\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "services/auth/policy.py",
                "--select",
                "proof_decision",
                "--format",
                "json",
            ]
        )
        == 0
    )

    packet = json.loads(capsys.readouterr().out)["values"]["proof_decision"]
    lane_ids = [lane["id"] for lane in packet["selected_lanes"]]
    assert "domain:access_control" in lane_ids
    assert "domain:audit_events" in lane_ids
    assert packet["selected_lane_count"] >= 2

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "docs/readme.md",
                "--select",
                "proof_decision",
                "--format",
                "json",
            ]
        )
        == 0
    )

    packet = json.loads(capsys.readouterr().out)["values"]["proof_decision"]
    assert all(not lane["id"].startswith("domain:") for lane in packet["selected_lanes"])


def _append_explicit_broad_proof_fixture(target: Path, *, explicit_request: bool = True) -> None:
    _write(
        target / "Makefile",
        (target / "Makefile").read_text(encoding="utf-8")
        + """
test-workspace-cli:
\tpython -c "print('workspace cli')"

test-workspace-proof:
\tpython -c "print('workspace proof')"

test-workspace-session-review:
\tpython -c "print('workspace session review')"

test-workspace-contracts:
\tpython -c "print('workspace contracts')"

test-workspace-generated-release:
\tpython -c "print('workspace generated release')"

test-workspace-integration:
\tpython -c "print('workspace integration')"

lint-workspace:
\tpython -c "print('workspace lint')"
""",
    )
    broad_conditions = '["explicit-request"]' if explicit_request else '["cross-owner"]'
    _write(
        target / ".agentic-workspace" / "config.toml",
        (target / ".agentic-workspace" / "config.toml").read_text(encoding="utf-8")
        + f"""

[assurance.domain_proof_lanes.runtime_contract]
purpose = "Runtime contract behavior."
applies_to_paths = ["src/agentic_workspace/workspace_runtime_proof.py"]
commands = ["python -c \\"print('runtime proof')\\""]
proof_profiles = ["workspace_behavior"]
escalation_conditions = ["explicit-request"]
claim_boundary = "runtime-contract-proof"
owner = "workspace-cli-runtime"

[assurance.domain_proof_lanes.workspace_broad_suite]
purpose = "Explicit broad workspace validation route."
applies_to_task_markers = ["broad workspace proof"]
commands = [
  "make test-workspace-cli",
  "make test-workspace-proof",
  "make test-workspace-session-review",
  "make test-workspace-contracts",
  "make test-workspace-generated-release",
  "make test-workspace-integration",
  "make lint-workspace",
]
proof_profiles = ["workspace_behavior"]
escalation_conditions = {broad_conditions}
claim_boundary = "explicit-broad-escalation-required"
owner = "workspace-cli-runtime"
route_role = "broad"
""",
    )


def test_explicit_broad_marker_selects_structured_broad_route_after_healthy_coverage(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _append_explicit_broad_proof_fixture(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_proof.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "--task",
                "Run broad workspace proof for this change.",
                "--select",
                "proof_route_strategy_decision,route_refinement_required,required_commands,selected_lanes",
                "--format",
                "json",
            ]
        )
        == 0
    )

    values = json.loads(capsys.readouterr().out)["values"]
    decision = values["proof_route_strategy_decision"]
    assert decision["outcome"] == "broad-escalated"
    assert decision["reason_code"] == "explicit-request"
    assert decision["broad_escalation"]["matched_task_markers"] == ["broad workspace proof"]
    assert values["route_refinement_required"]["status"] == "not-required"
    assert "domain:workspace_broad_suite" in [lane["id"] for lane in values["selected_lanes"]]
    expected = {
        "make test-workspace-cli",
        "make test-workspace-proof",
        "make test-workspace-session-review",
        "make test-workspace-contracts",
        "make test-workspace-generated-release",
        "make test-workspace-integration",
    }
    assert expected.issubset(values["required_commands"])


def test_explicit_broad_marker_cannot_bypass_focused_coverage_gap(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _append_explicit_broad_proof_fixture(tmp_path)
    changed = "src/agentic_workspace/workspace_runtime_uncovered.py"
    _write(tmp_path / changed, "VALUE = 1\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                changed,
                "--task",
                "Run broad workspace proof for this change.",
                "--select",
                "proof_route_strategy_decision,route_refinement_required,required_commands",
                "--format",
                "json",
            ]
        )
        == 0
    )

    values = json.loads(capsys.readouterr().out)["values"]
    assert values["proof_route_strategy_decision"]["outcome"] == "route-refinement-required"
    assert values["route_refinement_required"]["uncovered_paths"] == [changed]
    assert all(not command.startswith("make test-workspace-") for command in values["required_commands"])


def test_explicit_broad_marker_requires_typed_explicit_request_condition(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _append_explicit_broad_proof_fixture(tmp_path, explicit_request=False)
    changed = "src/agentic_workspace/workspace_runtime_proof.py"
    _write(tmp_path / changed, "VALUE = 1\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                changed,
                "--task",
                "Run broad workspace proof for this change.",
                "--select",
                "proof_route_strategy_decision,required_commands",
                "--format",
                "json",
            ]
        )
        == 0
    )

    values = json.loads(capsys.readouterr().out)["values"]
    assert values["proof_route_strategy_decision"]["outcome"] == "focused"
    assert values["proof_route_strategy_decision"]["explicit_broad_lane_selected"] is False
    assert all(not command.startswith("make test-workspace-") for command in values["required_commands"])


def test_ordinary_focused_task_does_not_select_explicit_broad_route(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _append_explicit_broad_proof_fixture(tmp_path)
    changed = "src/agentic_workspace/workspace_runtime_proof.py"
    _write(tmp_path / changed, "VALUE = 1\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                changed,
                "--task",
                "Check the focused runtime change.",
                "--select",
                "proof_route_strategy_decision,required_commands,selected_lanes",
                "--format",
                "json",
            ]
        )
        == 0
    )

    values = json.loads(capsys.readouterr().out)["values"]
    assert values["proof_route_strategy_decision"]["outcome"] == "focused"
    assert "domain:workspace_broad_suite" not in [lane["id"] for lane in values["selected_lanes"]]
    assert all(not command.startswith("make test-workspace-") for command in values["required_commands"])


def test_proof_route_strategy_decision_selects_structured_broad_escalation_for_two_domain_owners(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _write(
        tmp_path / "Makefile",
        (tmp_path / "Makefile").read_text(encoding="utf-8")
        + """
test-workspace-cli:
\tpython -c "print('workspace cli')"

test-workspace-proof:
\tpython -c "print('workspace proof')"

test-workspace-session-review:
\tpython -c "print('workspace session review')"

test-workspace-contracts:
\tpython -c "print('workspace contracts')"

test-workspace-generated-release:
\tpython -c "print('workspace generated release')"

test-workspace-integration:
\tpython -c "print('workspace integration')"

lint-workspace:
\tpython -c "print('workspace lint')"
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        (tmp_path / ".agentic-workspace" / "config.toml").read_text(encoding="utf-8")
        + """

[assurance.domain_proof_lanes.runtime_contract]
purpose = "Runtime contract behavior."
applies_to_paths = ["src/agentic_workspace/workspace_runtime_proof.py"]
commands = ["python -c \\"print('runtime proof')\\""]
proof_profiles = ["workspace_behavior"]
escalation_conditions = ["cross-owner"]
claim_boundary = "runtime-contract-proof"
owner = "workspace-cli-runtime"

[assurance.domain_proof_lanes.generated_command_packages]
purpose = "Generated command package behavior."
applies_to_paths = ["generated/workspace/python/**"]
commands = ["python -c \\"print('generated proof')\\""]
proof_profiles = ["workspace_behavior"]
escalation_conditions = ["cross-owner"]
claim_boundary = "generated-adapter-proof"
owner = "generated-adapters"

[assurance.domain_proof_lanes.workspace_broad_suite]
purpose = "Explicit broad workspace validation route."
applies_to_task_markers = ["full workspace validation"]
commands = [
  "make test-workspace-cli",
  "make test-workspace-proof",
  "make test-workspace-session-review",
  "make test-workspace-contracts",
  "make test-workspace-generated-release",
  "make test-workspace-integration",
  "make lint-workspace",
]
proof_profiles = ["workspace_behavior"]
escalation_conditions = ["cross-owner", "explicit-request"]
claim_boundary = "explicit-broad-escalation-required"
owner = "workspace-cli-runtime"
""",
        encoding="utf-8",
    )
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_proof.py", "VALUE = 1\n")
    _write(tmp_path / "generated" / "workspace" / "python" / "cli.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "generated/workspace/python/cli.py",
                "--select",
                "proof_route_strategy_decision,required_commands,selected_lanes,proof_command_tiers",
                "--format",
                "json",
            ]
        )
        == 0
    )

    values = json.loads(capsys.readouterr().out)["values"]
    decision = values["proof_route_strategy_decision"]
    assert decision["outcome"] == "broad-escalated"
    assert decision["reason_code"] == "cross-owner"
    assert decision["broad_escalation"]["distinct_owners"] == ["generated-adapters", "workspace-cli-runtime"]
    expected_broad_commands = [
        "make test-workspace-cli",
        "make test-workspace-proof",
        "make test-workspace-session-review",
        "make test-workspace-contracts",
        "make test-workspace-generated-release",
        "make test-workspace-integration",
        "make lint-workspace",
    ]
    for command in expected_broad_commands:
        assert command in values["required_commands"]
    assert "make test-workspace" not in values["required_commands"]
    assert "domain:workspace_broad_suite" in [lane["id"] for lane in values["selected_lanes"]]
    tier_commands = [item for tier in values["proof_command_tiers"]["tiers"] for item in tier["commands"]]
    broad = [item for item in tier_commands if item["command"].startswith("make test-workspace-")]
    assert broad
    assert all(
        (item["execution_class"], item["execution_owner"], item["posture"]) == ("exhaustive-local", "local", "required") for item in broad
    )
    lint = next(item for item in tier_commands if item["command"] == "make lint-workspace")
    assert (lint["execution_class"], lint["execution_owner"], lint["posture"]) == ("focused-local", "local", "required")


def test_proof_route_strategy_decision_ignores_untyped_escalation_prose(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        (tmp_path / ".agentic-workspace" / "config.toml").read_text(encoding="utf-8")
        + """

[assurance.domain_proof_lanes.runtime_contract]
purpose = "Runtime contract behavior."
applies_to_paths = ["src/agentic_workspace/workspace_runtime_proof.py"]
commands = ["python -c \\"print('runtime proof')\\""]
proof_profiles = ["workspace_behavior"]
escalation = ["cross-owner generated/runtime changes require broad workspace validation"]
claim_boundary = "runtime-contract-proof"
owner = "workspace-cli-runtime"

[assurance.domain_proof_lanes.generated_command_packages]
purpose = "Generated command package behavior."
applies_to_paths = ["generated/workspace/python/**"]
commands = ["python -c \\"print('generated proof')\\""]
proof_profiles = ["workspace_behavior"]
escalation = ["cross-owner generated/runtime changes require broad workspace validation"]
claim_boundary = "generated-adapter-proof"
owner = "generated-adapters"

[assurance.domain_proof_lanes.workspace_broad_suite]
purpose = "Explicit broad workspace validation route."
applies_to_task_markers = ["full workspace validation"]
commands = ["make test-workspace"]
proof_profiles = ["workspace_behavior"]
claim_boundary = "explicit-broad-escalation-required"
owner = "workspace-cli-runtime"
""",
        encoding="utf-8",
    )
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_proof.py", "VALUE = 1\n")
    _write(tmp_path / "generated" / "workspace" / "python" / "cli.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "generated/workspace/python/cli.py",
                "--select",
                "proof_route_strategy_decision,required_commands,selected_lanes",
                "--format",
                "json",
            ]
        )
        == 0
    )

    values = json.loads(capsys.readouterr().out)["values"]
    assert values["proof_route_strategy_decision"]["outcome"] == "broad-escalation-required"
    assert values["proof_route_strategy_decision"]["broad_escalation"]["status"] == "missing"
    assert "make test-workspace" not in values["required_commands"]
    assert "domain:workspace_broad_suite" not in [lane["id"] for lane in values["selected_lanes"]]


def test_focused_operation_route_bounds_and_deduplicates_generated_proof(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        (tmp_path / ".agentic-workspace" / "config.toml").read_text(encoding="utf-8")
        + """

[assurance.domain_proof_lanes.generated_command_packages]
purpose = "Generic generated command package behavior."
applies_to_paths = ["generated/workspace/python/**", "generated/workspace/typescript/**"]
commands = ["python -c \\"print('docker --docker')\\"", "python -c \\"print('all operations --target all')\\""]
evidence_concepts = ["generated-package-freshness"]
proof_profiles = ["workspace_behavior"]
claim_boundary = "generic-generated-proof"
owner = "workspace-cli-runtime"
route_role = "behavior"
precedence = "55"

[assurance.domain_proof_lanes.evaluation_operation_runtime]
purpose = "Exact Evaluation operation behavior and generated projection proof."
applies_to_paths = ["src/agentic_workspace/evaluation.py", "src/agentic_workspace/contracts/operations/evaluation.*.json", "generated/workspace/python/operations/evaluation.*.json", "generated/workspace/typescript/resources/operations/evaluation.*.json", "tests/test_workspace_evaluation.py"]
commands = ["python -c \\"print('evaluation behavior')\\"", "python -c \\"print('contract tooling')\\"", "python -c \\"print('smallest generated consumer')\\""]
evidence_concepts = ["evaluation-operation-runtime", "generated-package-freshness"]
proof_profiles = ["workspace_behavior"]
claim_boundary = "focused-evaluation-operation-proof"
owner = "workspace-cli-runtime"
route_role = "behavior"
precedence = "70"
allowed_composition = ["maintenance", "evidence", "broad"]
""",
        encoding="utf-8",
    )
    changed_paths = [
        "src/agentic_workspace/evaluation.py",
        "src/agentic_workspace/contracts/operations/evaluation.status.json",
        "generated/workspace/python/operations/evaluation.status.json",
        "generated/workspace/typescript/resources/operations/evaluation.status.json",
        "tests/test_workspace_evaluation.py",
    ]
    for path in changed_paths:
        _write(tmp_path / path, "{}\n" if path.endswith(".json") else "VALUE = 1\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                *changed_paths,
                "--select",
                "proof_route_strategy_decision,route_refinement_required,required_commands,selected_commands",
                "--format",
                "json",
            ]
        )
        == 0
    )

    values = json.loads(capsys.readouterr().out)["values"]
    assert values["proof_route_strategy_decision"]["outcome"] == "focused"
    assert values["route_refinement_required"]["status"] == "not-required"
    required_commands = values["required_commands"]
    assert len(required_commands) == len(set(required_commands))
    assert len(required_commands) <= 10
    assert all("--docker" not in command for command in required_commands)
    assert all("--target all" not in command for command in required_commands)
    assert all("run_operation_conformance_tests.py" not in command for command in required_commands)
    assert sum("evaluation behavior" in command for command in required_commands) == 1
    assert sum("contract tooling" in command for command in required_commands) == 1
    assert sum("smallest generated consumer" in command for command in required_commands) == 1
    assert all(command["lane"] != "domain:generated_command_packages" for command in values["selected_commands"])


def test_proof_route_strategy_decision_requires_matching_high_risk_requirement_ref(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        (tmp_path / ".agentic-workspace" / "config.toml").read_text(encoding="utf-8")
        + """

[assurance.requirements.security_delta]
level = "high"
applies_to_paths = ["services/auth/**"]
authority_refs = ["docs/security.md"]
required_evidence = ["security review"]
force = "required-before-closeout"

[assurance.domain_proof_lanes.auth_runtime]
purpose = "Auth runtime behavior."
applies_to_paths = ["services/auth/**"]
commands = ["python -c \\"print('auth proof')\\""]
proof_profiles = ["workspace_behavior"]
assurance_requirement_refs = ["security_delta"]
escalation_conditions = ["high-risk-requirement"]
claim_boundary = "auth-runtime-proof"
owner = "auth"
route_role = "behavior"

[assurance.domain_proof_lanes.workspace_broad_suite]
purpose = "Explicit broad workspace validation route."
applies_to_task_markers = ["full workspace validation"]
commands = ["make test-workspace"]
proof_profiles = ["workspace_behavior"]
escalation_conditions = ["high-risk-requirement"]
claim_boundary = "explicit-broad-escalation-required"
owner = "workspace-cli-runtime"
route_role = "broad"
""",
        encoding="utf-8",
    )
    _write(tmp_path / "services" / "auth" / "policy.py", "ALLOW = True\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "services/auth/policy.py",
                "--select",
                "proof_route_strategy_decision,required_commands,selected_lanes",
                "--format",
                "json",
            ]
        )
        == 0
    )

    values = json.loads(capsys.readouterr().out)["values"]
    decision = values["proof_route_strategy_decision"]
    assert decision["outcome"] == "broad-escalated"
    assert decision["reason_code"] == "high-risk-requirement"
    assert decision["broad_escalation"]["matched_assurance_requirement_refs"] == ["security_delta"]
    assert "make test-workspace" in values["required_commands"]


def test_proof_route_strategy_decision_consumes_applicable_memory_validation_friction(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    config_path = tmp_path / ".agentic-workspace" / "config.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8")
        + """

[assurance.domain_proof_lanes.generated_command_packages]
purpose = "Focused generated-component behavior."
applies_to_paths = ["src/generated_component.py"]
commands = ["python -c \\"print('generated focused proof')\\""]
claim_boundary = "generated-adapter-proof"
owner = "generated-adapters"
""",
        encoding="utf-8",
    )
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "manifest.toml",
        """
version = 1

[notes.".agentic-workspace/memory/repo/current/proof-route-friction.md"]
memory_role = "improvement_signal"
kind = "validation_friction"
lifecycle_state = "active"
applicable_live = true
applicable_to_current_route = true
recurrence = "repeated"
occurrence_count = 2
route_identity = "proof-route-friction:generated"
summary = "Repeated validation proof friction on generated command package checks."
routes_from = ["src/generated_component.py"]
stale_when = ["src/generated_component.py"]
preferred_remediation = "validation"
promotion_target = "proof-route-maintenance"
promotion_trigger = "Route generated-command package changes through focused proof before broad suites."
improvement_note = "Do not repeat broad/generated validation until the proof route is refined or this signal is retired."
evidence = ["session-log:slow-command:generated"]
""",
    )
    _write(tmp_path / "src" / "generated_component.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/generated_component.py",
                "--select",
                "proof_route_strategy_decision,proof_route_escalation_gate,proof_route_strategy_preservation,proof_route_strategy_claim_gate,proof_closeout_summary,manual_verification,next",
                "--format",
                "json",
            ]
        )
        == 0
    )

    values = json.loads(capsys.readouterr().out)["values"]
    decision = values["proof_route_strategy_decision"]
    assert decision["outcome"] == "focused"
    assert decision["reason_code"] == "focused-route-sufficient"
    assert decision["claim_effect"] == "focused-proof-required"
    assert decision["applicable_friction_findings"][0]["note_path"].endswith("proof-route-friction.md")
    assert decision["applicable_friction_findings"][0]["route_identity"] == "proof-route-friction:generated"
    assert decision["applicable_friction_findings"][0]["recurrence"] == "repeated"
    assert values["proof_route_escalation_gate"]["friction_inputs"]["applicable_live_findings"]
    preservation = values["proof_route_strategy_preservation"]
    assert preservation["status"] == "selected"
    assert preservation["consumers"]["proof"]["decision_id"] == preservation["decision_id"]
    assert preservation["consumers"]["handoff"]["claim_effect"] == "focused-proof-required"
    claim_gate = values["proof_route_strategy_claim_gate"]
    assert claim_gate["decision_id"] == preservation["decision_id"]
    assert claim_gate["handoff"]["required_identity_field"] == "proof_route_strategy_preservation.decision_id"
    assert values["proof_closeout_summary"]["proof_route_strategy_claim_gate"]["decision_id"] == preservation["decision_id"]
    assert values.get("manual_verification") is None
    assert values["next"]["action"] == "run-validation-command"


def test_proof_route_strategy_decision_ignores_non_live_memory_validation_friction(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    manifest_path = tmp_path / ".agentic-workspace" / "memory" / "repo" / "manifest.toml"
    manifest_template = """
version = 1

[notes.".agentic-workspace/memory/repo/current/proof-route-friction.md"]
memory_role = "improvement_signal"
lifecycle_state = "{lifecycle_state}"
kind = "validation_friction"
applicable_live = true
applicable_to_current_route = true
recurrence = "repeated"
occurrence_count = 2
summary = "Old validation proof friction on generated command package checks."
routes_from = ["generated/workspace/python/**"]
preferred_remediation = "validation"
promotion_target = "proof-route-maintenance"
promotion_trigger = "Retired after focused proof route was added."
improvement_note = "This signal is intentionally quiet."
"""
    _write(tmp_path / "generated" / "workspace" / "python" / "cli.py", "VALUE = 1\n")

    for lifecycle_state in ("stale", "mitigated", "superseded"):
        manifest_path.write_text(manifest_template.format(lifecycle_state=lifecycle_state), encoding="utf-8")
        assert (
            cli.main(
                [
                    "proof",
                    "--target",
                    str(tmp_path),
                    "--changed",
                    "generated/workspace/python/cli.py",
                    "--select",
                    "proof_route_strategy_decision",
                    "--format",
                    "json",
                ]
            )
            == 0
        )
        decision = json.loads(capsys.readouterr().out)["values"]["proof_route_strategy_decision"]
        assert decision["reason_code"] != "applicable-validation-friction"
        assert decision["applicable_friction_findings"] == []


def test_proof_route_strategy_decision_requires_typed_live_repeated_friction(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    manifest_path = tmp_path / ".agentic-workspace" / "memory" / "repo" / "manifest.toml"
    _write(tmp_path / "generated" / "workspace" / "python" / "cli.py", "VALUE = 1\n")
    cases = [
        'summary = "Repeated validation proof friction."',
        'kind = "validation_friction"\napplicable_live = true\napplicable_to_current_route = true\nrecurrence = "first_seen"',
        'kind = "validation_friction"\napplicable_live = false\napplicable_to_current_route = true\nrecurrence = "repeated"\noccurrence_count = 2',
    ]
    for extra_fields in cases:
        manifest_path.write_text(
            f"""
version = 1

[notes.".agentic-workspace/memory/repo/current/proof-route-friction.md"]
memory_role = "improvement_signal"
lifecycle_state = "active"
routes_from = ["generated/workspace/python/**"]
{extra_fields}
""",
            encoding="utf-8",
        )
        assert (
            cli.main(
                [
                    "proof",
                    "--target",
                    str(tmp_path),
                    "--changed",
                    "generated/workspace/python/cli.py",
                    "--select",
                    "proof_route_strategy_decision,proof_route_escalation_gate",
                    "--format",
                    "json",
                ]
            )
            == 0
        )
        values = json.loads(capsys.readouterr().out)["values"]
        assert values["proof_route_strategy_decision"]["applicable_friction_findings"] == []
        assert values["proof_route_escalation_gate"]["friction_inputs"]["applicable_live_findings"] == []


def test_domain_proof_route_inventory_reports_profile_and_command_gaps(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_proof_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        f"""
schema_version = 1

[workspace]
cli_invoke = "{REPO_LOCAL_CLI_INVOKE}"

[assurance.proof_profiles.workspace_behavior]
required_commands = []

[assurance.proof_profiles.uncovered_profile]
required_commands = []

[assurance.domain_proof_lanes.runtime_contract]
purpose = "Runtime contract behavior."
applies_to_paths = ["src/agentic_workspace/workspace_runtime_proof.py"]
commands = ["uv run pytest tests/missing_runtime_contract.py -q"]
proof_profiles = ["workspace_behavior"]
""",
    )
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_proof.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "--select",
                "domain_proof_route_inventory_audit",
                "--format",
                "json",
            ]
        )
        == 0
    )

    audit = json.loads(capsys.readouterr().out)["values"]["domain_proof_route_inventory_audit"]
    assert audit["status"] == "attention"
    assert audit["missing_profile_coverage"] == [
        {
            "proof_profile": "uncovered_profile",
            "reason": "configured proof profile has no domain proof lane coverage",
            "refinement_owner": "repo proof-route authority",
        }
    ]
    assert any(item.get("missing_path") == "tests/missing_runtime_contract.py" for item in audit["non_executable_commands"])


def test_domain_proof_route_inventory_ignores_disjoint_shared_prefix_globs(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_proof_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        f"""
schema_version = 1

[workspace]
cli_invoke = "{REPO_LOCAL_CLI_INVOKE}"

[assurance.domain_proof_lanes.package_tests]
purpose = "Package tests."
applies_to_paths = ["packages/**/tests/**"]
commands = ["python -c \\"print('tests')\\""]
claim_boundary = "package-test-proof"
owner = "verification"
route_role = "evidence"
precedence = "80"
allowed_composition = ["behavior"]

[assurance.domain_proof_lanes.memory_source]
purpose = "Memory source."
applies_to_paths = ["packages/memory/src/**"]
commands = ["python -c \\"print('memory')\\""]
claim_boundary = "memory-source-proof"
owner = "memory"
route_role = "behavior"
precedence = "50"
allowed_composition = ["evidence"]
""",
    )
    _write(tmp_path / "packages" / "memory" / "src" / "repo_memory_bootstrap" / "core.py", "VALUE = 1\n")
    _write(tmp_path / "packages" / "memory" / "tests" / "test_core.py", "def test_core(): pass\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "packages/memory/src/repo_memory_bootstrap/core.py",
                "--select",
                "domain_proof_route_inventory_audit",
                "--format",
                "json",
            ]
        )
        == 0
    )

    audit = json.loads(capsys.readouterr().out)["values"]["domain_proof_route_inventory_audit"]
    assert audit["semantic_overlaps"] == []
    assert audit["contradictory_ownership"] == []


def test_route_refinement_removes_broad_commands_when_focused_command_becomes_unavailable(tmp_path: Path, capsys) -> None:
    _write_repo_local_proof_target(tmp_path)
    _write(
        tmp_path / "Makefile",
        (tmp_path / "Makefile").read_text(encoding="utf-8") + "\nlint-workspace:\n\tpython -c \"print('workspace lint')\"\n",
    )
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        (tmp_path / ".agentic-workspace" / "config.toml").read_text(encoding="utf-8")
        + """

[assurance.domain_proof_lanes.runtime_contract]
purpose = "Runtime contract behavior."
applies_to_paths = ["src/agentic_workspace/workspace_runtime_proof.py"]
commands = ["make missing-runtime-proof"]
proof_profiles = ["workspace_behavior"]
escalation_conditions = ["cross-owner"]
claim_boundary = "runtime-contract-proof"
owner = "workspace-cli-runtime"
route_role = "behavior"

[assurance.domain_proof_lanes.generated_command_packages]
purpose = "Generated command package behavior."
applies_to_paths = ["generated/workspace/python/**"]
commands = ["python -c \\"print('generated proof')\\""]
proof_profiles = ["workspace_behavior"]
escalation_conditions = ["cross-owner"]
claim_boundary = "generated-adapter-proof"
owner = "generated-adapters"
route_role = "behavior"

[assurance.domain_proof_lanes.workspace_broad_suite]
purpose = "Explicit broad workspace validation route."
applies_to_task_markers = ["full workspace validation"]
commands = ["make test-workspace", "make lint-workspace"]
proof_profiles = ["workspace_behavior"]
escalation_conditions = ["cross-owner"]
claim_boundary = "explicit-broad-escalation-required"
owner = "workspace-cli-runtime"
route_role = "broad"
""",
        encoding="utf-8",
    )
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_proof.py", "VALUE = 1\n")
    _write(tmp_path / "generated" / "workspace" / "python" / "cli.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "generated/workspace/python/cli.py",
                "--select",
                "proof_route_strategy_decision,route_refinement_required,manual_verification,required_commands,selected_commands",
                "--format",
                "json",
            ]
        )
        == 0
    )

    values = json.loads(capsys.readouterr().out)["values"]
    assert values["proof_route_strategy_decision"]["outcome"] == "route-refinement-required"
    assert values["route_refinement_required"]["status"] == "required"
    assert values["manual_verification"]["status"] == "route-refinement-required"
    assert "make test-workspace" not in values["required_commands"]
    assert "make lint-workspace" not in values["required_commands"]
    assert all(command["lane"] != "domain:workspace_broad_suite" for command in values["selected_commands"])


def test_domain_proof_lane_coexists_with_package_default_lane(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_proof_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        f"""
schema_version = 1

[workspace]
cli_invoke = "{REPO_LOCAL_CLI_INVOKE}"

[assurance.domain_proof_lanes.runtime_contract]
purpose = "Runtime changes need host contract proof."
applies_to_paths = ["src/agentic_workspace/**"]
commands = ["python -c \\"print('runtime contract proof')\\""]
proof_profiles = ["runtime_contract"]
""",
    )
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_proof.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_proof.py",
                "--select",
                "proof_decision",
                "--format",
                "json",
            ]
        )
        == 0
    )

    packet = json.loads(capsys.readouterr().out)["values"]["proof_decision"]
    lane_ids = [lane["id"] for lane in packet["selected_lanes"]]
    assert "domain:runtime_contract" in lane_ids


def test_local_high_risk_overlay_shapes_proof_decision_with_provenance(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_proof_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        f"""
schema_version = 1

[workspace]
cli_invoke = "{REPO_LOCAL_CLI_INVOKE}"
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        """
schema_version = 1

[local_overlay.high_risk.source_maps.auth_docs]
applies_to_paths = ["services/auth/**"]
authority_refs = ["SECURITY.md#auth", "docs/adr/auth-boundary.md"]
required_sources = ["docs/risk/auth-risk-register.md"]
manual_evidence = ["host:auth-risk-review"]
review_aids = ["Confirm auth ADR still matches changed code."]
claim_boundary = "auth-source-map-review"
impact = "human-review-only"

[local_overlay.high_risk.validation_profiles.security_sensitive]
category = "security-sensitive"
applies_to_paths = ["services/auth/**"]
required_commands = ["python -c \\"print('security validation')\\""]
manual_checks = ["Review auth threat-model delta."]
claim_boundary = "security-validation-profile"
impact = "blocking"

[local_overlay.high_risk.ci_validation.github_actions]
applies_to_paths = ["services/auth/**"]
validation_state = "ci_unavailable"
local_substitute_commands = ["python -c \\"print('local substitute')\\""]
local_substitute_policy = "human-review-only"
claim_boundary = "local-substitute-is-not-ci"

[local_overlay.high_risk.templates.security_issue]
applies_to_paths = ["services/auth/**"]
host = "github"
kind = "issue"
paths = [".github/ISSUE_TEMPLATE/security.yml"]
headings = ["Risk", "Evidence", "Reviewer"]
state = "missing"
impact = "blocking"

[local_overlay.high_risk.guardrails.synthetic_auth_data]
applies_to_paths = ["services/auth/**"]
sensitive_data = ["production tokens", "customer emails"]
synthetic_fixture_guidance = ["Use example.com addresses.", "Use placeholder credentials."]
impact = "claim-limiting"

[local_overlay.high_risk.unresolved_questions.legal_review]
applies_to_paths = ["services/auth/**"]
category = "human-review-required"
question = "Does this auth change require legal/security review before merge?"
owner = "security"
residue_route = "human-review"
reason = "local high-risk overlay declares auth changes review-sensitive"
""",
    )
    _write(tmp_path / "services" / "auth" / "policy.py", "ALLOW = True\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "services/auth/policy.py",
                "--select",
                "proof_decision",
                "--format",
                "json",
            ]
        )
        == 0
    )

    packet = json.loads(capsys.readouterr().out)["values"]["proof_decision"]
    overlay = packet["local_high_risk_overlay"]
    assert packet["local_overlay"]["status"] == "configured-no-match"
    assert overlay["status"] == "active"
    assert overlay["active_count"] == 6
    source_lane = next(lane for lane in packet["selected_lanes"] if lane["id"] == "local-overlay-source:auth_docs")
    assert source_lane["route_authority"]["authority"] == "local-only-high-risk-profile"
    assert source_lane["local_overlay"]["source_layer"] == "repo-local-override"
    assert "SECURITY.md#auth" in source_lane["commands"] or source_lane["manual_evidence"] == ["host:auth-risk-review"]
    validation_lane = next(lane for lane in packet["selected_lanes"] if lane["id"] == "local-overlay-validation:security_sensitive")
    assert validation_lane["validation_profile"]["category"] == "security-sensitive"
    assert "python -c \"print('security validation')\"" in validation_lane["commands"]
    unresolved = packet["missing_or_unresolved"]
    assert "validation-state:ci_unavailable" in unresolved["local_overlay_blockers"]
    assert "local-substitute-policy:human-review-only" in unresolved["local_overlay_blockers"]
    assert "template-preservation:missing" in unresolved["local_overlay_blockers"]
    assert "guardrail:claim-limiting" in unresolved["local_overlay_blockers"]
    assert "unresolved-question:human-review-required" in unresolved["local_overlay_blockers"]
    assert packet["safe_claim_now"]["state"] == "human-waiver-required"


def test_local_high_risk_overlay_no_match_stays_out_of_tiny_proof(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_proof_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        f"""
schema_version = 1

[workspace]
cli_invoke = "{REPO_LOCAL_CLI_INVOKE}"
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        """
schema_version = 1

[local_overlay.high_risk.guardrails.auth_data]
applies_to_paths = ["services/auth/**"]
sensitive_data = ["production token"]
impact = "blocking"
""",
    )
    _write(tmp_path / "docs" / "readme.md", "# Docs\n")

    assert cli.main(["proof", "--target", str(tmp_path), "--changed", "docs/readme.md", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload.get("high_risk_overlay") is None


def test_high_assurance_closeout_posture_projects_missing_and_non_applicable_states(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_proof_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        f"""
schema_version = 1

[workspace]
cli_invoke = "{REPO_LOCAL_CLI_INVOKE}"

[assurance.closeout_postures.critical_access]
purpose = "Critical access changes need explicit closeout evidence."
applies_to_paths = ["services/auth/**"]
required_evidence = ["domain_review_recorded"]
review_owner = "security"
authority_refs = ["SECURITY.md#critical-access"]
claim_boundary = "critical-access-closeout"
certification_limits = ["does not certify production authorization safety"]
""",
    )
    _write(tmp_path / "services" / "auth" / "policy.py", "ALLOW = True\n")
    _write(tmp_path / "docs" / "readme.md", "# Docs\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "services/auth/policy.py",
                "--select",
                "proof_decision",
                "--format",
                "json",
            ]
        )
        == 0
    )

    packet = json.loads(capsys.readouterr().out)["values"]["proof_decision"]
    posture = packet["high_assurance_closeout_posture"]
    assert posture["status"] == "missing-proof"
    assert posture["matched_count"] == 1
    assert posture["matched_postures"][0]["claim_boundary"] == "critical-access-closeout"
    assert packet["separation_of_duty"] == {
        "kind": "agentic-workspace/separation-of-duty-gate/v1",
        "status": "required",
        "required_mode": "human",
    }
    assert posture["missing_evidence"] == ["domain_review_recorded"]
    assert "high-assurance closeout posture evidence is missing" in packet["missing_or_unresolved"]["blockers"]

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "docs/readme.md",
                "--select",
                "proof_decision",
                "--format",
                "json",
            ]
        )
        == 0
    )

    posture = json.loads(capsys.readouterr().out)["values"]["proof_decision"]["high_assurance_closeout_posture"]
    assert posture["status"] == "not-applicable"
    assert posture["matched_count"] == 0


def test_high_assurance_closeout_posture_accepts_admitted_independent_review_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    from agentic_workspace.workspace_runtime_proof import (
        WorkspaceUsageError,
        _independent_review_scope_digest,
        admit_independent_review_result_operation,
        record_trusted_independent_review_result,
    )

    _init_git_repo(tmp_path)
    _write_empty_proof_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        f"""
schema_version = 1

[workspace]
cli_invoke = "{REPO_LOCAL_CLI_INVOKE}"

[assurance.closeout_postures.critical_access]
purpose = "Critical access changes need explicit closeout evidence."
applies_to_paths = ["services/auth/**"]
required_evidence = ["domain_review_recorded"]
review_owner = "security"
authority_refs = ["SECURITY.md#critical-access"]
claim_boundary = "critical-access-closeout"
certification_limits = ["does not certify production authorization safety"]
""",
    )
    _write(tmp_path / "services" / "auth" / "policy.py", "ALLOW = True\n")
    review_result = {
        "kind": "agentic-workspace/independent-review-result/v1",
        "status": "accepted",
        "required_mode": "human",
        "assignment_id": "critical-access-review",
        "assignment_revision": "assignment-rev-1",
        "review_revision": "review-rev-1",
        "reviewed_at": "2026-07-26T13:22:00Z",
        "changed_paths": ["services/auth/policy.py"],
        "scope_digest": _independent_review_scope_digest(["services/auth/policy.py"]),
        "implementer": {"actor_id": "agent-implementer", "provider": "codex", "role": "implementer"},
        "reviewer": {"actor_id": "human-reviewer", "provider": "human", "role": "human-approver", "fresh_context": True},
        "custody": {
            "producer": "github-review-adapter",
            "authority_ref": "SECURITY.md#critical-access",
            "source_ref": "pull-request-review:1",
        },
    }
    with pytest.raises(WorkspaceUsageError, match="host_result_ref"):
        record_trusted_independent_review_result(target_root=tmp_path, review_result=review_result)
    host_result_ref = _write_independent_review_host_result(
        tmp_path,
        review_result,
        host_admission_monkeypatch=monkeypatch,
    )
    with _verified_host_fixture(monkeypatch, host_result_ref):
        trusted = record_trusted_independent_review_result(target_root=tmp_path, review_result={"host_result_ref": host_result_ref})
        inline = admit_independent_review_result_operation(
            target_root=tmp_path,
            values={"review_result": review_result, "required_mode": "human", "changed": ["services/auth/policy.py"]},
        )
        assert inline["status"] == "rejected"
        assert inline["failures"][0]["reason"] == "caller-authored-review-result-rejected"
        receipt = admit_independent_review_result_operation(
            target_root=tmp_path,
            values={"review_result_ref": trusted["result_ref"], "required_mode": "human", "changed": ["services/auth/policy.py"]},
        )
        assert receipt["status"] == "admitted"

        assert (
            cli.main(
                [
                    "proof",
                    "--target",
                    str(tmp_path),
                    "--changed",
                    "services/auth/policy.py",
                    "--select",
                    "proof_decision",
                    "--format",
                    "json",
                ]
            )
            == 0
        )

        packet = json.loads(capsys.readouterr().out)["values"]["proof_decision"]
        assert packet["separation_of_duty"]["status"] == "satisfied"
        assert packet["separation_of_duty"]["authority"] == "repo-local-admitted-independent-review-receipt"
        assert packet["separation_of_duty"]["receipt"]["source_path"] == ".agentic-workspace/local/independent-review-receipts.json"
        assert packet["separation_of_duty"]["receipt"]["receipt_ref"] == receipt["receipt_ref"]
        assert receipt["receipt"]["review_result"]["custody"]["host_result_ref"] == host_result_ref
        assert "high-assurance review separation is required" not in packet["missing_or_unresolved"]["blockers"]
        assert "high-assurance closeout posture evidence is missing" in packet["missing_or_unresolved"]["blockers"]


def test_assignment_admit_accepts_preinstalled_host_capability_ref(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agentic_workspace.workspace_runtime_proof import _independent_review_scope_digest, admit_independent_review_result_operation

    review_result = {
        "kind": "agentic-workspace/independent-review-result/v1",
        "status": "accepted",
        "required_mode": "human",
        "assignment_id": "critical-access-review",
        "assignment_revision": "assignment-rev-1",
        "review_revision": "review-rev-1",
        "reviewed_at": "2026-07-26T13:22:00Z",
        "changed_paths": ["services/auth/policy.py"],
        "scope_digest": _independent_review_scope_digest(["services/auth/policy.py"]),
        "implementer": {"actor_id": "agent-implementer", "provider": "codex", "role": "implementer"},
        "reviewer": {"actor_id": "human-reviewer", "provider": "human", "role": "human-approver", "fresh_context": True},
        "custody": {
            "producer": "github-review-adapter",
            "authority_ref": "SECURITY.md#critical-access",
            "source_ref": "pull-request-review:1",
        },
    }
    host_result_ref = _write_independent_review_host_result(
        tmp_path,
        review_result,
        host_admission_monkeypatch=monkeypatch,
        install_host_admission=True,
    )
    assert isinstance(host_result_ref, str)

    with _verified_host_fixture(monkeypatch, host_result_ref):
        receipt = admit_independent_review_result_operation(
            target_root=tmp_path,
            values={
                "host_result_ref": host_result_ref,
                "required_mode": "human",
                "changed": ["services/auth/policy.py"],
            },
        )

    assert receipt["status"] == "admitted"
    assert receipt["receipt"]["review_result"]["custody"]["host_result_ref"] == host_result_ref


def test_assignment_admit_accepts_release_pinned_provider_envelope_across_process(tmp_path: Path) -> None:
    import subprocess
    import sys

    from agentic_workspace.workspace_runtime_proof import (
        INDEPENDENT_REVIEW_HOST_RESULT_DIR,
        INDEPENDENT_REVIEW_HOST_RESULT_INDEX_KIND,
        _stable_review_json_digest,
    )

    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "remote", "add", "origin", "https://github.com/rickardvh/agentic-workspace.git"],
        check=True,
        capture_output=True,
        text=True,
    )
    _write(tmp_path / "services" / "auth" / "policy.py", "ALLOW = True\n")
    fixture_path = ROOT / "tests/fixtures/independent_review/github_review_adapter_release_2026_08.json"
    host_result = json.loads(fixture_path.read_text(encoding="utf-8"))
    host_result_ref = str(host_result["host_result_ref"])
    host_id = str(host_result["host_result_id"])
    host_root = tmp_path / INDEPENDENT_REVIEW_HOST_RESULT_DIR
    _write(host_root / f"{host_id}.json", json.dumps(host_result, indent=2, sort_keys=True) + "\n")
    _write(
        host_root / "index.json",
        json.dumps(
            {
                "kind": INDEPENDENT_REVIEW_HOST_RESULT_INDEX_KIND,
                "results": {
                    host_id: {
                        "path": f"{host_id}.json",
                        "status": "current",
                        "producer": "github-review-adapter",
                        "trusted_channel": "github-review-webhook",
                        "host_result_digest": _stable_review_json_digest(host_result),
                    }
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    script = f"""
import json
from datetime import datetime, timezone
from pathlib import Path
import agentic_workspace.workspace_runtime_proof as proof_runtime


class _ConformanceFixtureTime(datetime):
    @classmethod
    def now(cls, tz=None):
        current = cls(2026, 8, 8, 12, 2, tzinfo=timezone.utc)
        return current if tz is None else current.astimezone(tz)


# This immutable signed vector proves release-pinned provider compatibility.
# Freeze only this clean subprocess inside the vector's declared validity
# window; production admission continues to use the real wall clock.
proof_runtime.datetime = _ConformanceFixtureTime

payload = proof_runtime.admit_independent_review_result_operation(
    target_root=Path({str(tmp_path)!r}),
    values={{
        "host_result_ref": {host_result_ref!r},
        "required_mode": "human",
        "changed": ["services/auth/policy.py"],
    }},
)
print(json.dumps(payload, sort_keys=True))
"""
    completed = subprocess.run([sys.executable, "-c", script], capture_output=True, cwd=ROOT, text=True)

    assert completed.returncode == 0, completed.stderr or completed.stdout
    payload = json.loads(completed.stdout)
    assert payload["status"] == "admitted", payload
    assert payload["receipt"]["review_result"]["custody"]["host_result_ref"] == host_result_ref


def test_assignment_admit_rejects_unpinned_signed_host_evidence_across_process(tmp_path: Path) -> None:
    import subprocess
    import sys

    from agentic_workspace.workspace_runtime_proof import _independent_review_scope_digest

    _write(tmp_path / "services" / "auth" / "policy.py", "ALLOW = True\n")
    review_result = {
        "kind": "agentic-workspace/independent-review-result/v1",
        "status": "accepted",
        "required_mode": "human",
        "assignment_id": "critical-access-review",
        "assignment_revision": "assignment-rev-1",
        "review_revision": "review-rev-1",
        "reviewed_at": "2026-07-26T13:22:00Z",
        "changed_paths": ["services/auth/policy.py"],
        "scope_digest": _independent_review_scope_digest(["services/auth/policy.py"]),
        "implementer": {"actor_id": "agent-implementer", "provider": "codex", "role": "implementer"},
        "reviewer": {"actor_id": "human-reviewer", "provider": "human", "role": "human-approver", "fresh_context": True},
        "custody": {
            "producer": "github-review-adapter",
            "authority_ref": "SECURITY.md#critical-access",
            "source_ref": "pull-request-review:1",
        },
    }
    host_inputs = _write_independent_review_host_result(
        tmp_path,
        review_result,
        install_host_admission=False,
        return_capability_inputs=True,
    )
    assert isinstance(host_inputs, dict)
    host_result_ref = str(host_inputs["host_result_ref"])
    script = f"""
import json
from pathlib import Path
from agentic_workspace.workspace_runtime_proof import admit_independent_review_result_operation

payload = admit_independent_review_result_operation(
    target_root=Path({str(tmp_path)!r}),
    values={{
        "host_result_ref": {host_result_ref!r},
        "required_mode": "human",
        "changed": ["services/auth/policy.py"],
    }},
)
print(json.dumps(payload, sort_keys=True))
"""
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
        ],
        capture_output=True,
        cwd=ROOT,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    payload = json.loads(completed.stdout)
    assert payload["status"] == "rejected"
    assert payload["failures"][0]["reason"] == "host-capability-admission-rejected"


def test_independent_review_rejects_nonce_replay_across_distinct_host_results(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agentic_workspace.workspace_runtime_proof import (
        WorkspaceUsageError,
        _independent_review_scope_digest,
        record_trusted_independent_review_result,
    )

    base_result = {
        "kind": "agentic-workspace/independent-review-result/v1",
        "status": "accepted",
        "required_mode": "human",
        "assignment_id": "critical-access-review",
        "assignment_revision": "assignment-rev-1",
        "proof_subject_revision": "proof-subject-rev-1",
        "review_revision": "review-rev-1",
        "reviewed_at": "2026-08-08T12:00:00Z",
        "changed_paths": ["services/auth/policy.py"],
        "scope_digest": _independent_review_scope_digest(["services/auth/policy.py"]),
        "nonce": "provider-nonce-replay-1",
        "implementer": {"actor_id": "agent-implementer", "provider": "codex", "role": "implementer"},
        "reviewer": {"actor_id": "human-reviewer", "provider": "human", "role": "human-approver", "fresh_context": True},
        "custody": {
            "producer": "github-review-adapter",
            "authority_ref": "SECURITY.md#critical-access",
            "source_ref": "pull-request-review:1",
        },
    }
    first_ref = _write_independent_review_host_result(tmp_path, {**base_result, "review_id": "review-first"})
    second_ref = _write_independent_review_host_result(tmp_path, {**base_result, "review_id": "review-second"})
    assert isinstance(first_ref, str)
    assert isinstance(second_ref, str)

    with _verified_host_fixture(monkeypatch, first_ref):
        record_trusted_independent_review_result(target_root=tmp_path, review_result={"host_result_ref": first_ref})
    with _verified_host_fixture(monkeypatch, second_ref), pytest.raises(WorkspaceUsageError, match="nonce was already used"):
        record_trusted_independent_review_result(target_root=tmp_path, review_result={"host_result_ref": second_ref})


def test_assignment_admit_does_not_load_repo_or_pythonpath_host_verifiers() -> None:
    source = (ROOT / "src/agentic_workspace/workspace_runtime_proof.py").read_text(encoding="utf-8")
    test_source = (ROOT / "tests/test_workspace_proof_cli.py").read_text(encoding="utf-8")

    assert "agentic_workspace_host_adapters.independent_review" not in source
    assert "importlib.import_module" not in source
    private_key_marker = "BEGIN " + "PRIVATE KEY"
    assert private_key_marker not in source
    assert private_key_marker not in test_source
    assert "_INDEPENDENT_REVIEW_HOST_TEST_RSA" + "_D" not in test_source
    assert "_independent_review_host" + "_test_signature" not in test_source
    assert "github-review-adapter:" + "test-v1" not in source
    assert "_INDEPENDENT_REVIEW_HOST_ADMISSION_KEYS" not in source
    assert "def independent_review_host_runtime_trust_registry(" not in source
    assert "\nINDEPENDENT_REVIEW_HOST_PUBLIC_KEYS:" not in source
    assert "_INDEPENDENT_REVIEW_HOST_RUNTIME_KEYS" not in source


def test_independent_review_release_pinned_verifier_exposes_no_runtime_registry() -> None:
    import agentic_workspace.workspace_runtime_proof as proof_runtime

    assert not hasattr(proof_runtime, "independent_review_host_runtime_trust_registry")
    assert not hasattr(proof_runtime, "INDEPENDENT_REVIEW_HOST_PUBLIC_KEYS")
    assert not hasattr(proof_runtime, "_INDEPENDENT_REVIEW_HOST_RUNTIME_KEYS")
    assert not hasattr(proof_runtime, "_PINNED_INDEPENDENT_REVIEW_HOST_PUBLIC_KEYS")


@pytest.mark.parametrize(
    ("key_change", "admitted"),
    [
        ({}, True),
        ({"status": "revoked"}, False),
        ({"revoked_at": "2026-08-01T00:00:00Z"}, False),
        ({"superseded_by": "github-review-adapter:replacement"}, False),
        ({"expires_at": "2026-08-01T00:00:00Z"}, False),
    ],
)
def test_independent_review_cryptographic_verifier_enforces_pinned_key_lifecycle(
    tmp_path: Path, key_change: dict[str, str], admitted: bool
) -> None:
    import agentic_workspace.workspace_runtime_proof as proof_runtime

    review_result = {
        "kind": "agentic-workspace/independent-review-result/v1",
        "status": "accepted",
        "required_mode": "human",
        "assignment_revision": "assignment-rev-1",
        "proof_subject_revision": "proof-subject-rev-1",
        "changed_paths": ["services/auth/policy.py"],
        "scope_digest": proof_runtime._independent_review_scope_digest(["services/auth/policy.py"]),
        "implementer": {"actor_id": "agent-implementer", "provider": "codex", "role": "implementer"},
        "reviewer": {"actor_id": "human-reviewer", "provider": "human", "role": "human-approver", "fresh_context": True},
        "custody": {"producer": "github-review-adapter", "trusted_channel": "github-review-webhook"},
    }
    host_inputs = _write_independent_review_host_result(
        tmp_path,
        review_result,
        install_host_admission=False,
        return_capability_inputs=True,
    )
    assert isinstance(host_inputs, dict)
    host_result_ref = str(host_inputs["host_result_ref"])
    host_id = host_result_ref.removeprefix("independent-review-host-result:")
    host_result = json.loads((tmp_path / proof_runtime.INDEPENDENT_REVIEW_HOST_RESULT_DIR / f"{host_id}.json").read_text(encoding="utf-8"))
    key = dict(host_inputs["host_public_key"])
    key.update(key_change)

    verdict = proof_runtime._signed_independent_review_host_verdict_with_keys(
        host_result_ref=host_result_ref,
        host_result=host_result,
        target_root=tmp_path,
        public_keys={str(key["key_id"]): key},
    )

    assert (verdict.get("status") == "admitted") is admitted


def test_independent_review_ignores_caller_recreated_legacy_authority_attributes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import agentic_workspace.workspace_runtime_proof as proof_runtime

    review_result = {
        "kind": "agentic-workspace/independent-review-result/v1",
        "status": "accepted",
        "required_mode": "human",
        "assignment_revision": "assignment-rev-1",
        "proof_subject_revision": "proof-subject-rev-1",
        "changed_paths": ["services/auth/policy.py"],
        "scope_digest": proof_runtime._independent_review_scope_digest(["services/auth/policy.py"]),
        "implementer": {"actor_id": "agent-implementer", "provider": "codex", "role": "implementer"},
        "reviewer": {"actor_id": "human-reviewer", "provider": "human", "role": "human-approver", "fresh_context": True},
        "custody": {"producer": "github-review-adapter", "trusted_channel": "github-review-webhook"},
    }
    host_inputs = _write_independent_review_host_result(
        tmp_path,
        review_result,
        install_host_admission=False,
        return_capability_inputs=True,
    )
    assert isinstance(host_inputs, dict)
    key = host_inputs["host_public_key"]
    monkeypatch.setattr(proof_runtime, "INDEPENDENT_REVIEW_HOST_PUBLIC_KEYS", {key["key_id"]: key}, raising=False)
    monkeypatch.setattr(proof_runtime, "_INDEPENDENT_REVIEW_HOST_RUNTIME_KEYS", {key["key_id"]: key}, raising=False)
    monkeypatch.setattr(proof_runtime, "_PINNED_INDEPENDENT_REVIEW_HOST_PUBLIC_KEYS", {key["key_id"]: key}, raising=False)

    receipt = proof_runtime.admit_independent_review_result_operation(
        target_root=tmp_path,
        values={
            "host_result_ref": host_inputs["host_result_ref"],
            "required_mode": "human",
            "changed": ["services/auth/policy.py"],
        },
    )

    assert receipt["status"] == "rejected"
    assert receipt["failures"][0]["reason"] == "host-capability-admission-rejected"


def test_assignment_admit_rejects_caller_supplied_host_trust_root(tmp_path: Path) -> None:
    from agentic_workspace.workspace_runtime_proof import _independent_review_scope_digest, admit_independent_review_result_operation

    review_result = {
        "kind": "agentic-workspace/independent-review-result/v1",
        "status": "accepted",
        "required_mode": "human",
        "assignment_id": "critical-access-review",
        "assignment_revision": "assignment-rev-1",
        "review_revision": "review-rev-1",
        "reviewed_at": "2026-07-26T13:22:00Z",
        "changed_paths": ["services/auth/policy.py"],
        "scope_digest": _independent_review_scope_digest(["services/auth/policy.py"]),
        "implementer": {"actor_id": "agent-implementer", "provider": "codex", "role": "implementer"},
        "reviewer": {"actor_id": "human-reviewer", "provider": "human", "role": "human-approver", "fresh_context": True},
        "custody": {
            "producer": "github-review-adapter",
            "authority_ref": "SECURITY.md#critical-access",
            "source_ref": "pull-request-review:1",
        },
    }
    host_inputs = _write_independent_review_host_result(
        tmp_path,
        review_result,
        install_host_admission=False,
        return_capability_inputs=True,
    )
    assert isinstance(host_inputs, dict)

    receipt = admit_independent_review_result_operation(
        target_root=tmp_path,
        values={
            "host_result_ref": host_inputs["host_result_ref"],
            "host_admission_json": json.dumps(host_inputs["host_admission"], sort_keys=True),
            "host_public_key_json": json.dumps(host_inputs["host_public_key"], sort_keys=True),
            "host_capability_json": json.dumps(host_inputs["host_capability"], sort_keys=True),
            "required_mode": "human",
            "changed": ["services/auth/policy.py"],
        },
    )

    assert receipt["status"] == "rejected"
    assert receipt["failures"][0]["reason"] == "caller-supplied-host-trust-root-rejected"


def test_trusted_independent_review_rejects_repo_generated_signature_without_host_trust(tmp_path: Path) -> None:
    from agentic_workspace.workspace_runtime_proof import (
        WorkspaceUsageError,
        _independent_review_scope_digest,
        record_trusted_independent_review_result,
    )

    review_result = {
        "kind": "agentic-workspace/independent-review-result/v1",
        "status": "accepted",
        "required_mode": "human",
        "assignment_id": "critical-access-review",
        "assignment_revision": "assignment-rev-1",
        "review_revision": "review-rev-1",
        "reviewed_at": "2026-07-26T13:22:00Z",
        "changed_paths": ["services/auth/policy.py"],
        "scope_digest": _independent_review_scope_digest(["services/auth/policy.py"]),
        "implementer": {"actor_id": "agent-implementer", "provider": "codex", "role": "implementer"},
        "reviewer": {"actor_id": "human-reviewer", "provider": "human", "role": "human-approver", "fresh_context": True},
        "custody": {
            "producer": "github-review-adapter",
            "authority_ref": "SECURITY.md#critical-access",
            "source_ref": "pull-request-review:1",
        },
    }
    host_result_ref = _write_independent_review_host_result(tmp_path, review_result, install_host_admission=False)
    assert isinstance(host_result_ref, str)

    with pytest.raises(WorkspaceUsageError, match="host boundary"):
        record_trusted_independent_review_result(target_root=tmp_path, review_result={"host_result_ref": host_result_ref})


def test_trusted_independent_review_rejects_unsigned_embedded_host_verdict(tmp_path: Path) -> None:
    from agentic_workspace.workspace_runtime_proof import (
        INDEPENDENT_REVIEW_HOST_RESULT_AUDIENCE,
        INDEPENDENT_REVIEW_HOST_RESULT_DIR,
        WorkspaceUsageError,
        _host_result_body_for_admission,
        _independent_review_scope_digest,
        _stable_review_json_digest,
        record_trusted_independent_review_result,
    )

    review_result = {
        "kind": "agentic-workspace/independent-review-result/v1",
        "status": "accepted",
        "review_id": "independent-review-unsigned-verdict",
        "assignment_revision": "assignment-rev-1",
        "proof_subject_revision": "proof-subject-rev-1",
        "required_mode": "high-assurance",
        "changed_paths": ["services/auth/policy.py"],
        "scope_digest": _independent_review_scope_digest(["services/auth/policy.py"]),
        "reviewer_role": "independent-reviewer",
        "implementer_role": "implementer",
        "custody": {"producer": "github-review-adapter", "trusted_channel": "github-review-webhook"},
        "proof_status": "passed",
        "decision": "accepted",
    }
    host_result_ref = _write_independent_review_host_result(tmp_path, review_result, install_host_admission=False)
    host_id = str(host_result_ref).removeprefix("independent-review-host-result:")
    host_root = tmp_path / INDEPENDENT_REVIEW_HOST_RESULT_DIR
    host_path = host_root / f"{host_id}.json"
    host_result = json.loads(host_path.read_text(encoding="utf-8"))
    custody = host_result["custody"]
    admission_context = host_result["admission_context"]
    host_result["host_admission_verdict"] = {
        "kind": "agentic-workspace/independent-review-host-result-verdict/v1",
        "status": "admitted",
        "authority": "host-adapter-resolver",
        "host_result_ref": host_result_ref,
        "host_result_body_digest": _stable_review_json_digest(_host_result_body_for_admission(host_result)),
        "producer": custody["producer"],
        "trusted_channel": custody["trusted_channel"],
        "audience": INDEPENDENT_REVIEW_HOST_RESULT_AUDIENCE,
        "workspace_ref": f"workspace:path:{tmp_path.resolve()}",
        "operation": "assignment.admit.independent-review",
        "assignment_revision": "assignment-rev-1",
        "proof_subject_revision": "proof-subject-rev-1",
        "nonce": admission_context["nonce"],
        "issued_at": admission_context["issued_at"],
        "expires_at": admission_context["expires_at"],
        "verifier_revision": "caller-authored-unsigned-verdict",
    }
    _write(host_path, json.dumps(host_result, indent=2, sort_keys=True) + "\n")
    index_path = host_root / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["results"][host_id]["host_result_digest"] = _stable_review_json_digest(host_result)
    _write(index_path, json.dumps(index, indent=2, sort_keys=True) + "\n")

    with pytest.raises(WorkspaceUsageError, match="host boundary"):
        record_trusted_independent_review_result(target_root=tmp_path, review_result={"host_result_ref": host_result_ref})


def test_independent_review_host_admission_rejects_inline_caller_trust_roots(tmp_path: Path) -> None:
    from agentic_workspace.workspace_runtime_proof import (
        WorkspaceUsageError,
        _independent_review_scope_digest,
        record_trusted_independent_review_result,
    )

    review_result = {
        "kind": "agentic-workspace/independent-review-result/v1",
        "status": "accepted",
        "required_mode": "human",
        "assignment_id": "critical-access-review",
        "assignment_revision": "assignment-rev-1",
        "review_revision": "review-rev-1",
        "reviewed_at": "2026-07-26T13:22:00Z",
        "changed_paths": ["services/auth/policy.py"],
        "scope_digest": _independent_review_scope_digest(["services/auth/policy.py"]),
        "implementer": {"actor_id": "agent-implementer", "provider": "codex", "role": "implementer"},
        "reviewer": {"actor_id": "human-reviewer", "provider": "human", "role": "human-approver", "fresh_context": True},
        "custody": {
            "producer": "github-review-adapter",
            "authority_ref": "SECURITY.md#critical-access",
            "source_ref": "pull-request-review:1",
        },
    }
    host_inputs = _write_independent_review_host_result(
        tmp_path,
        review_result,
        install_host_admission=False,
        return_capability_inputs=True,
    )
    assert isinstance(host_inputs, dict)

    with pytest.raises(WorkspaceUsageError, match="opaque independent-review-host-result reference"):
        record_trusted_independent_review_result(
            target_root=tmp_path,
            review_result={
                "host_result_ref": ".agentic-workspace/local/independent-review-host-results/caller-authored.json",
                "host_admission": host_inputs["host_admission"],
                "host_public_key": host_inputs["host_public_key"],
                "host_capability": host_inputs["host_capability"],
            },
        )


def test_independent_review_host_capability_issuer_is_not_public_runtime_entrypoint() -> None:
    source = (ROOT / "src/agentic_workspace/workspace_runtime_proof.py").read_text(encoding="utf-8")

    assert "def issue_independent_review_host_result_capability_for_adapter(" not in source
    assert "def admit_independent_review_host_result_capability(" not in source
    assert "def _install_independent_review_host_result_admission_for_adapter_test(" not in source
    assert "IndependentReviewHostAdmissionCapability" not in source
    assert "_INDEPENDENT_REVIEW_HOST_BOUNDARY_TOKEN" not in source
    assert "_CURRENT_INDEPENDENT_REVIEW_HOST_RESULT_ADMISSIONS" not in source


def test_trusted_independent_review_rejects_caller_controlled_environment_trust_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from agentic_workspace.workspace_runtime_proof import (
        INDEPENDENT_REVIEW_HOST_RESULT_DIR,
        WorkspaceUsageError,
        _independent_review_scope_digest,
        _stable_review_json_digest,
        record_trusted_independent_review_result,
    )

    review_result = {
        "kind": "agentic-workspace/independent-review-result/v1",
        "status": "accepted",
        "required_mode": "human",
        "assignment_id": "critical-access-review",
        "assignment_revision": "assignment-rev-1",
        "review_revision": "review-rev-1",
        "reviewed_at": "2026-07-26T13:22:00Z",
        "changed_paths": ["services/auth/policy.py"],
        "scope_digest": _independent_review_scope_digest(["services/auth/policy.py"]),
        "implementer": {"actor_id": "agent-implementer", "provider": "codex", "role": "implementer"},
        "reviewer": {"actor_id": "human-reviewer", "provider": "human", "role": "human-approver", "fresh_context": True},
        "custody": {
            "producer": "github-review-adapter",
            "authority_ref": "SECURITY.md#critical-access",
            "source_ref": "pull-request-review:1",
        },
    }
    monkeypatch.delenv("AW_INDEPENDENT_REVIEW_HOST_RESULT_ADMISSION_KEYS", raising=False)
    host_result_ref = _write_independent_review_host_result(
        tmp_path,
        review_result,
        install_host_admission=False,
        caller_env_admission_keys=True,
    )
    monkeypatch.setenv(
        "AW_INDEPENDENT_REVIEW_HOST_RESULT_ADMISSIONS",
        json.dumps(
            {
                host_result_ref: {
                    "kind": "agentic-workspace/independent-review-host-result-admission/v1",
                    "status": "current",
                    "issuer": "github-review-webhook",
                    "producer": "github-review-adapter",
                }
            }
        ),
    )
    host_id = host_result_ref.removeprefix("independent-review-host-result:")
    host_path = tmp_path / INDEPENDENT_REVIEW_HOST_RESULT_DIR / f"{host_id}.json"
    host_result = json.loads(host_path.read_text(encoding="utf-8"))
    host_result["host_admission"]["signature"] = "caller-forged-signature"
    _write(host_path, json.dumps(host_result, indent=2, sort_keys=True) + "\n")
    index_path = tmp_path / INDEPENDENT_REVIEW_HOST_RESULT_DIR / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["results"][host_id]["host_result_digest"] = _stable_review_json_digest(host_result)
    _write(index_path, json.dumps(index, indent=2, sort_keys=True) + "\n")

    with pytest.raises(WorkspaceUsageError, match="host boundary"):
        record_trusted_independent_review_result(target_root=tmp_path, review_result={"host_result_ref": host_result_ref})


@pytest.mark.parametrize(
    ("case_name", "overrides"),
    [
        ("wrong-audience", {"audience": "other-consumer"}),
        ("missing-nonce", {"nonce": ""}),
        ("expired-admission", {"admission_expires_at": "2026-01-01T00:00:00Z"}),
        ("revoked-admission", {"admission_revoked_at": "2026-07-29T00:00:00Z"}),
        ("wrong-workspace", {"workspace_ref": "workspace:path:not-this-workspace"}),
        ("wrong-operation", {"operation": "assignment.admit.other"}),
    ],
)
def test_trusted_independent_review_rejects_invalid_host_admission_lifecycle(
    tmp_path: Path, case_name: str, overrides: dict[str, object]
) -> None:
    from agentic_workspace.workspace_runtime_proof import WorkspaceUsageError, record_trusted_independent_review_result

    review_result = {
        "kind": "agentic-workspace/independent-review-result/v1",
        "status": "accepted",
        "required_mode": "human",
        "assignment_id": "critical-access-review",
        "assignment_revision": "assignment-rev-1",
        "proof_subject_revision": "proof-subject-rev-1",
        "review_revision": "review-rev-1",
        "review_id": f"review-{case_name}",
        "reviewed_at": "2026-07-26T13:22:00Z",
        "changed_paths": ["services/auth/policy.py"],
        "custody": {
            "producer": "github-review-adapter",
            "authority_ref": "SECURITY.md#critical-access",
            "source_ref": "pull-request-review:1",
        },
        **overrides,
    }
    host_result_ref = _write_independent_review_host_result(tmp_path, review_result)

    with pytest.raises(WorkspaceUsageError, match="host boundary"):
        record_trusted_independent_review_result(target_root=tmp_path, review_result={"host_result_ref": host_result_ref})


def test_high_assurance_closeout_posture_rejects_expired_independent_review_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    from agentic_workspace.workspace_runtime_proof import (
        _independent_review_scope_digest,
        admit_independent_review_result_operation,
        record_trusted_independent_review_result,
    )

    _init_git_repo(tmp_path)
    _write_empty_proof_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        f"""
schema_version = 1

[workspace]
cli_invoke = "{REPO_LOCAL_CLI_INVOKE}"

[assurance.closeout_postures.critical_access]
purpose = "Critical access changes need explicit closeout evidence."
applies_to_paths = ["services/auth/**"]
required_evidence = ["domain_review_recorded"]
review_owner = "security"
claim_boundary = "critical-access-closeout"
""",
    )
    _write(tmp_path / "services" / "auth" / "policy.py", "ALLOW = True\n")
    review_result = {
        "kind": "agentic-workspace/independent-review-result/v1",
        "status": "accepted",
        "required_mode": "human",
        "assignment_id": "critical-access-review",
        "assignment_revision": "assignment-rev-1",
        "review_revision": "review-rev-1",
        "reviewed_at": "2026-07-26T13:22:00Z",
        "expires_at": "2026-07-26T14:00:00Z",
        "changed_paths": ["services/auth/policy.py"],
        "scope_digest": _independent_review_scope_digest(["services/auth/policy.py"]),
        "implementer": {"actor_id": "agent-implementer", "provider": "codex", "role": "implementer"},
        "reviewer": {"actor_id": "human-reviewer", "provider": "human", "role": "human-approver", "fresh_context": True},
        "custody": {"producer": "github-review-adapter", "authority_ref": "SECURITY.md#critical-access"},
    }
    host_result_ref = _write_independent_review_host_result(
        tmp_path,
        review_result,
        host_admission_monkeypatch=monkeypatch,
    )
    with _verified_host_fixture(monkeypatch, host_result_ref):
        trusted = record_trusted_independent_review_result(target_root=tmp_path, review_result={"host_result_ref": host_result_ref})
        admission = admit_independent_review_result_operation(
            target_root=tmp_path,
            values={"review_result_ref": trusted["result_ref"], "required_mode": "human", "changed": ["services/auth/policy.py"]},
        )
    assert admission["status"] == "rejected"
    assert admission["failures"][0]["reason"] == "review-result-expired"


def test_high_assurance_closeout_revalidates_admitted_receipt_against_current_host_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    from agentic_workspace.workspace_runtime_proof import (
        INDEPENDENT_REVIEW_HOST_RESULT_DIR,
        WorkspaceUsageError,
        _independent_review_scope_digest,
        _stable_review_json_digest,
        admit_independent_review_result_operation,
        record_trusted_independent_review_result,
    )

    _init_git_repo(tmp_path)
    _write_empty_proof_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        f"""
schema_version = 1

[workspace]
cli_invoke = "{REPO_LOCAL_CLI_INVOKE}"

[assurance.closeout_postures.critical_access]
purpose = "Critical access changes need explicit closeout evidence."
applies_to_paths = ["services/auth/**"]
required_evidence = ["domain_review_recorded"]
review_owner = "security"
claim_boundary = "critical-access-closeout"
""",
    )
    _write(tmp_path / "services" / "auth" / "policy.py", "ALLOW = True\n")
    review_result = {
        "kind": "agentic-workspace/independent-review-result/v1",
        "status": "accepted",
        "required_mode": "human",
        "assignment_id": "critical-access-review",
        "assignment_revision": "assignment-rev-1",
        "proof_subject_revision": "proof-subject-rev-1",
        "review_revision": "review-rev-1",
        "reviewed_at": "2026-07-26T13:22:00Z",
        "changed_paths": ["services/auth/policy.py"],
        "scope_digest": _independent_review_scope_digest(["services/auth/policy.py"]),
        "implementer": {"actor_id": "agent-implementer", "provider": "codex", "role": "implementer"},
        "reviewer": {"actor_id": "human-reviewer", "provider": "human", "role": "human-approver", "fresh_context": True},
        "custody": {
            "producer": "github-review-adapter",
            "authority_ref": "SECURITY.md#critical-access",
            "source_ref": "pull-request-review:1",
        },
    }
    host_result_ref = _write_independent_review_host_result(
        tmp_path,
        review_result,
        host_admission_monkeypatch=monkeypatch,
    )
    with _verified_host_fixture(monkeypatch, host_result_ref):
        trusted = record_trusted_independent_review_result(target_root=tmp_path, review_result={"host_result_ref": host_result_ref})
        receipt = admit_independent_review_result_operation(
            target_root=tmp_path,
            values={"review_result_ref": trusted["result_ref"], "required_mode": "human", "changed": ["services/auth/policy.py"]},
        )
    assert receipt["status"] == "admitted"

    host_id = host_result_ref.removeprefix("independent-review-host-result:")
    host_root = tmp_path / INDEPENDENT_REVIEW_HOST_RESULT_DIR
    host_path = host_root / f"{host_id}.json"
    host_result = json.loads(host_path.read_text(encoding="utf-8"))
    host_result["status"] = "superseded"
    host_result["superseded_by"] = "independent-review-host-result:replacement"
    _write(host_path, json.dumps(host_result, indent=2, sort_keys=True) + "\n")
    index_path = host_root / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["results"][host_id]["host_result_digest"] = _stable_review_json_digest(host_result)
    _write(index_path, json.dumps(index, indent=2, sort_keys=True) + "\n")

    with _verified_host_fixture(monkeypatch, host_result_ref):
        with pytest.raises(WorkspaceUsageError, match="not current"):
            record_trusted_independent_review_result(target_root=tmp_path, review_result={"host_result_ref": host_result_ref})
        assert (
            cli.main(
                [
                    "proof",
                    "--target",
                    str(tmp_path),
                    "--changed",
                    "services/auth/policy.py",
                    "--select",
                    "proof_decision",
                    "--format",
                    "json",
                ]
            )
            == 0
        )
    packet = json.loads(capsys.readouterr().out)["values"]["proof_decision"]
    assert packet["separation_of_duty"]["status"] == "required"
    assert "high-assurance review separation is required" in packet["missing_or_unresolved"]["blockers"]


def test_assignment_admit_exposes_independent_review_admission_contract() -> None:
    source = json.loads((ROOT / "src/agentic_workspace/contracts/operations/assignment.admit.json").read_text(encoding="utf-8"))
    generated = json.loads((ROOT / "generated/workspace/python/operations/assignment.admit.json").read_text(encoding="utf-8"))
    for payload in (source, generated):
        input_names = {item["name"] for item in payload["inputs"]}
        assert {"review_result_json", "review_result_ref", "host_result_ref", "required_mode", "changed"}.issubset(input_names)
        assert {"host_admission_json", "host_public_key_json", "host_capability_json"}.isdisjoint(input_names)
        assert any("producer-owned review result" in guard for guard in payload["guards"])
        assert any("caller-supplied verifier keys/signatures" in guard for guard in payload["guards"])
        assert any("assignment.admit admits independent-review host results" in proof for proof in payload["proof"])


def test_high_assurance_closeout_posture_rejects_hand_written_independent_review_receipt(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_proof_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        f"""
schema_version = 1

[workspace]
cli_invoke = "{REPO_LOCAL_CLI_INVOKE}"

[assurance.closeout_postures.critical_access]
purpose = "Critical access changes need explicit closeout evidence."
applies_to_paths = ["services/auth/**"]
required_evidence = ["domain_review_recorded"]
review_owner = "security"
claim_boundary = "critical-access-closeout"
""",
    )
    _write(tmp_path / "services" / "auth" / "policy.py", "ALLOW = True\n")
    _write(
        tmp_path / ".agentic-workspace" / "local" / "review-receipts" / "critical-access.json",
        json.dumps(
            {
                "kind": "agentic-workspace/independent-review-receipt/v1",
                "status": "admitted",
                "review_revision": "review-rev-1",
                "reviewed_at": "2026-07-26T13:22:00Z",
                "assignment_id": "critical-access-review",
                "implementer": {"actor_id": "agent-implementer", "provider": "codex", "role": "implementer"},
                "reviewer": {"actor_id": "human-reviewer", "provider": "human", "role": "human-approver", "fresh_context": True},
            }
        ),
    )

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "services/auth/policy.py",
                "--select",
                "proof_decision",
                "--format",
                "json",
            ]
        )
        == 0
    )

    packet = json.loads(capsys.readouterr().out)["values"]["proof_decision"]
    assert packet["separation_of_duty"]["status"] == "required"
    assert "high-assurance review separation is required" in packet["missing_or_unresolved"]["blockers"]


def test_high_assurance_closeout_posture_projects_waiver_and_uncertainty(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_proof_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        f"""
schema_version = 1

[workspace]
cli_invoke = "{REPO_LOCAL_CLI_INVOKE}"

[assurance.closeout_postures.access_waiver]
purpose = "Access changes with unresolved policy uncertainty need human waiver."
applies_to_paths = ["services/auth/**"]
uncertainty = "External policy owner must confirm the residual risk."
human_waiver_refs = ["SECURITY.md#waivers"]
certification_limits = ["agent output is not a policy approval"]
""",
    )
    _write(tmp_path / "services" / "auth" / "policy.py", "ALLOW = True\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "services/auth/policy.py",
                "--select",
                "proof_decision",
                "--format",
                "json",
            ]
        )
        == 0
    )

    packet = json.loads(capsys.readouterr().out)["values"]["proof_decision"]
    posture = packet["high_assurance_closeout_posture"]
    assert posture["status"] == "human-waiver-required"
    assert posture["human_waiver_refs"] == ["SECURITY.md#waivers"]
    assert posture["uncertainty"] == ["External policy owner must confirm the residual risk."]
    assert packet["safe_claim_now"]["state"] == "human-waiver-required"


def test_proof_decision_packet_includes_architecture_pressure(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_proof_planning_state(tmp_path)
    _write_proof_architecture_principles(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_core.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_core.py",
                "--select",
                "proof_decision",
                "--format",
                "json",
            ]
        )
        == 0
    )

    packet = json.loads(capsys.readouterr().out)["values"]["proof_decision"]
    assert packet["kind"] == "agentic-workspace/proof-decision-packet/v1"
    assert packet["active_pressure"]["architecture_principle_match_count"] == 1
    assert "matched architecture principle preservation claim is unresolved" in packet["missing_or_unresolved"]["blockers"]
    assert packet["safe_claim_now"]["state"] in {"proof-missing", "manual-review-required"}


def test_verification_distinguishes_host_evidence_concepts(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_proof_planning_state(tmp_path)
    _write(tmp_path / ".agentic-workspace" / "config.toml", f'schema_version = 1\n\n[workspace]\ncli_invoke = "{REPO_LOCAL_CLI_INVOKE}"\n')
    _write(
        tmp_path / ".agentic-workspace" / "verification" / "manifest.toml",
        """
schema_version = "agentic-workspace/verification-manifest/v1"

[evidence_concepts."host:scenario_matrix"]
title = "Scenario Matrix"
meaning = "Host-owned scenario coverage matrix."
owner = "qa"
claim_effect = "manual-review-required"
render_as = "scenario matrix"

[protocols.access_review]
title = "Access Review"
purpose = "Access changes need declared evidence."
applies_to_paths = ["services/auth/**"]
expected_evidence = ["scenario_coverage", "host:scenario_matrix", "host:missing"]
review_owner = "security"
""",
    )
    _write(tmp_path / "services" / "auth" / "policy.py", "ALLOW = True\n")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "services/auth/policy.py",
                "--select",
                "verification",
                "--format",
                "json",
            ]
        )
        == 0
    )

    verification = json.loads(capsys.readouterr().out)["values"]["verification"]
    concepts = verification["evidence_status"][0]["expected_evidence_concepts"]
    assert [item["kind"] for item in concepts["used"]] == ["core", "host-declared"]
    assert concepts["degraded"][0]["state"] == "undeclared-host-concept"
    assert verification["evidence_concepts"]["status"] == "attention"


def _selected_execution_fixture(commands: list[str], *, local: bool = True) -> dict[str, object]:
    return {
        "required_commands": commands,
        "changed_paths": [".agentic-workspace/config.local.toml" if local else "changed.py"],
        "selected_commands": [
            {
                "command": command,
                "lane": "domain:machine_local_config" if local else "domain:shared_config",
                "command_identity": hashlib.sha256(command.encode("utf-8")).hexdigest()[:16],
            }
            for command in commands
        ],
        "selected_lanes": [
            {
                "id": "domain:machine_local_config" if local else "domain:shared_config",
                "required_commands": commands,
            }
        ],
    }


def test_selected_proof_execution_reconciles_and_reuses_local_receipts(tmp_path: Path, monkeypatch) -> None:
    _init_git_repo(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    _write(tmp_path / ".gitignore", ".agentic-workspace/local/\n.agentic-workspace/config.local.toml\n")
    _write(tmp_path / ".agentic-workspace/config.toml", "schema_version = 1\n")
    _write(tmp_path / ".agentic-workspace/config.local.toml", "schema_version = 1\n")
    commands = ["check-one", "check-two", "check-three", "check-four"]
    calls: list[str] = []
    monkeypatch.setattr(
        workspace_runtime_core,
        "_proof_selection_for_changed_paths",
        lambda **_: _selected_execution_fixture(commands),
    )
    monkeypatch.setattr(
        workspace_runtime_proof,
        "_proof_selection_for_changed_paths",
        lambda **_: _selected_execution_fixture(commands),
    )

    def run(command: str, **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=f"{command} passed", stderr="")

    monkeypatch.setattr(workspace_runtime_core, "run_trusted_shell", run)
    before = subprocess.run(["git", "status", "--short"], cwd=tmp_path, capture_output=True, text=True, check=True).stdout
    first = workspace_runtime_core._execute_selected_proof_payload(
        target_root=tmp_path,
        changed_paths=[".agentic-workspace/config.local.toml"],
        task_text="verify local config",
        run_id="",
        timeout_seconds="30",
        cancel_file="",
        dry_run=False,
    )
    after = subprocess.run(["git", "status", "--short"], cwd=tmp_path, capture_output=True, text=True, check=True).stdout
    assert first["status"] == "completed"
    assert first["coverage"]["passed_count"] == 4
    assert first["preexecution_admission"]["status"] == "admitted"
    assert first["preexecution_admission"]["process_launch_count"] == 4
    assert first["canonical_receipt_admission"] == {
        "recorded_count": 4,
        "rejected_count": 0,
        "authority": "proof_receipt_admission",
    }
    assert first["claim_boundary"]["status"] == "effective-local-configuration-verified"
    assert first["claim_boundary"]["shared_repository_claim_allowed"] is False
    assert len(json.dumps(first).encode("utf-8")) < 16_384
    assert before == after
    canonical = json.loads((tmp_path / ".agentic-workspace/local/proof-receipts/last.json").read_text(encoding="utf-8"))
    assert canonical["command"] == "check-four"
    assert canonical["admission"]["proof_sufficient"] is True
    reconciliation = workspace_runtime_proof._proof_receipt_reconciliation_payload(
        target_root=tmp_path,
        required_commands=commands,
        changed_paths=[".agentic-workspace/config.local.toml"],
        selected_commands=_selected_execution_fixture(commands)["selected_commands"],
    )
    assert reconciliation["status"] == "accepted"
    assert {item["evidence_state"] for item in reconciliation["commands"]} == {"accepted"}

    _write(tmp_path / "README.md", "unrelated repository edit\n")
    reused = workspace_runtime_core._execute_selected_proof_payload(
        target_root=tmp_path,
        changed_paths=[".agentic-workspace/config.local.toml"],
        task_text="verify local config",
        run_id=first["run"]["id"],
        timeout_seconds="30",
        cancel_file="",
        dry_run=False,
    )
    assert reused["status"] == "reused-fresh-evidence"
    assert calls == commands


def test_selected_proof_execution_materializes_changed_path_templates_before_admission(tmp_path: Path, monkeypatch) -> None:
    _init_git_repo(tmp_path)
    changed_path = "src/feature file.py"
    _write(tmp_path / changed_path, "VALUE = 1\n")
    template = "uv run agentic-workspace implement --changed <paths> --format json"
    selection = _selected_execution_fixture([template], local=False)
    selection["changed_paths"] = [changed_path]
    calls: list[str] = []
    monkeypatch.setattr(workspace_runtime_core, "_proof_selection_for_changed_paths", lambda **_: selection)
    monkeypatch.setattr(workspace_runtime_proof, "_proof_selection_for_changed_paths", lambda **_: selection)

    def run(command: str, **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="passed", stderr="")

    monkeypatch.setattr(workspace_runtime_core, "run_trusted_shell", run)
    monkeypatch.setattr(
        workspace_runtime_core,
        "_record_proof_receipt_payload",
        lambda **_: {"status": "written", "receipt": {"admission": {"proof_sufficient": True}}},
    )
    result = workspace_runtime_core._execute_selected_proof_payload(
        target_root=tmp_path,
        changed_paths=[changed_path],
        task_text="verify a concrete changed-path command",
        run_id="",
        timeout_seconds="30",
        cancel_file="",
        dry_run=False,
    )

    assert result["status"] == "completed"
    assert calls == ['uv run agentic-workspace implement --changed "src/feature file.py" --format json']
    assert result["preexecution_admission"]["status"] == "admitted"


def test_selected_proof_rejects_known_unrecordable_broad_command_before_launch(tmp_path: Path, monkeypatch) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "changed.py", "VALUE = 1\n")
    selection = _selected_execution_fixture(["make test-workspace"], local=False)
    selection["selected_commands"] = [
        {
            "command": "make test-workspace --task-context corrected",
            "lane": "domain:workspace_broad_suite",
        }
    ]
    monkeypatch.setattr(workspace_runtime_core, "_proof_selection_for_changed_paths", lambda **_: selection)

    def forbidden_launch(*_: object, **__: object) -> subprocess.CompletedProcess[str]:
        raise AssertionError("deterministically unrecordable proof must not launch")

    monkeypatch.setattr(workspace_runtime_core, "run_trusted_shell", forbidden_launch)
    result = workspace_runtime_core._execute_selected_proof_payload(
        target_root=tmp_path,
        changed_paths=["changed.py"],
        task_text="PR #2746 broad acceptance repair",
        run_id="",
        timeout_seconds="30",
        cancel_file="",
        dry_run=False,
    )

    assert result["status"] == "admission-blocked-before-execution"
    assert result["preexecution_admission"]["process_launch_count"] == 0
    assert result["preexecution_admission"]["commands"][0]["reason"] == "current-selected-command-binding-rejected"
    assert "rerun proof selection" in result["next_action"]["command"].lower()
    assert result["persistence"]["local_run_receipt_written"] is False


def test_selected_proof_execution_resumes_failure_and_blocks_stale_subject(tmp_path: Path, monkeypatch) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / ".agentic-workspace/config.toml", "schema_version = 1\n")
    local_path = tmp_path / ".agentic-workspace/config.local.toml"
    _write(local_path, "schema_version = 1\n")
    commands = ["check-one", "check-two"]
    calls: list[str] = []
    fail_second = True
    monkeypatch.setattr(
        workspace_runtime_core,
        "_proof_selection_for_changed_paths",
        lambda **_: _selected_execution_fixture(commands),
    )
    monkeypatch.setattr(
        workspace_runtime_proof,
        "_proof_selection_for_changed_paths",
        lambda **_: _selected_execution_fixture(commands),
    )

    def run(command: str, **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        returncode = 1 if command == "check-two" and fail_second else 0
        return subprocess.CompletedProcess(command, returncode, stdout="", stderr="failed" if returncode else "")

    monkeypatch.setattr(workspace_runtime_core, "run_trusted_shell", run)
    first = workspace_runtime_core._execute_selected_proof_payload(
        target_root=tmp_path,
        changed_paths=[".agentic-workspace/config.local.toml"],
        task_text=None,
        run_id="proof-run",
        timeout_seconds="30",
        cancel_file="",
        dry_run=False,
    )
    assert first["status"] == "partial"
    assert first["outcome"] == "failed"

    fail_second = False
    resumed = workspace_runtime_core._execute_selected_proof_payload(
        target_root=tmp_path,
        changed_paths=[".agentic-workspace/config.local.toml"],
        task_text=None,
        run_id="proof-run",
        timeout_seconds="30",
        cancel_file="",
        dry_run=False,
    )
    assert resumed["status"] == "completed"
    assert calls == ["check-one", "check-two", "check-two"]

    _write(local_path, "schema_version = 1\n# changed subject\n")
    stale = workspace_runtime_core._execute_selected_proof_payload(
        target_root=tmp_path,
        changed_paths=[".agentic-workspace/config.local.toml"],
        task_text=None,
        run_id="proof-run",
        timeout_seconds="30",
        cancel_file="",
        dry_run=False,
    )
    assert stale["status"] == "stale-subject-blocked"
    assert stale["claim_boundary"]["completion_claim_allowed"] is False


def test_selected_proof_execution_records_cancel_and_timeout_outcomes(tmp_path: Path, monkeypatch) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / ".agentic-workspace/config.toml", "schema_version = 1\n")
    _write(tmp_path / ".agentic-workspace/config.local.toml", "schema_version = 1\n")
    monkeypatch.setattr(
        workspace_runtime_core,
        "_proof_selection_for_changed_paths",
        lambda **_: _selected_execution_fixture(["slow-check"]),
    )
    monkeypatch.setattr(
        workspace_runtime_proof,
        "_proof_selection_for_changed_paths",
        lambda **_: _selected_execution_fixture(["slow-check"]),
    )
    cancel = tmp_path / ".agentic-workspace/local/cancel"
    _write(cancel, "cancel\n")
    cancelled = workspace_runtime_core._execute_selected_proof_payload(
        target_root=tmp_path,
        changed_paths=[".agentic-workspace/config.local.toml"],
        task_text=None,
        run_id="cancelled-run",
        timeout_seconds="1",
        cancel_file=".agentic-workspace/local/cancel",
        dry_run=False,
    )
    assert cancelled["outcome"] == "cancelled"

    def timeout(*_: object, **__: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired("slow-check", 1)

    monkeypatch.setattr(workspace_runtime_core, "run_trusted_shell", timeout)
    timed_out = workspace_runtime_core._execute_selected_proof_payload(
        target_root=tmp_path,
        changed_paths=[".agentic-workspace/config.local.toml"],
        task_text=None,
        run_id="timeout-run",
        timeout_seconds="1",
        cancel_file="",
        dry_run=False,
    )
    assert timed_out["outcome"] == "timeout"
    assert timed_out["next_action"]["action"] == "resume-selected-proof"


def test_selected_proof_execution_keeps_route_refinement_claim_blocked(tmp_path: Path, monkeypatch) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "changed.py", "VALUE = 1\n")
    selection = _selected_execution_fixture(["focused-check"], local=False)
    selection["route_refinement_required"] = {"status": "required"}
    monkeypatch.setattr(workspace_runtime_core, "_proof_selection_for_changed_paths", lambda **_: selection)
    monkeypatch.setattr(workspace_runtime_proof, "_proof_selection_for_changed_paths", lambda **_: selection)
    monkeypatch.setattr(
        workspace_runtime_core,
        "run_trusted_shell",
        lambda command, **_: subprocess.CompletedProcess(command, 0, stdout="", stderr=""),
    )
    result = workspace_runtime_core._execute_selected_proof_payload(
        target_root=tmp_path,
        changed_paths=["changed.py"],
        task_text=None,
        run_id="",
        timeout_seconds="30",
        cancel_file="",
        dry_run=False,
    )
    assert result["status"] == "completed-with-unresolved-obligations"
    assert result["outcome"] == "blocked"
    assert result["claim_boundary"]["completion_claim_allowed"] is False
    assert result["next_action"]["action"] == "repair-proof-route"
    from agentic_workspace.workspace_selector_validation import _detail_route_command_validation

    validation = _detail_route_command_validation(result["next_action"]["command"])
    assert validation["status"] == "valid"
    assert validation["selectors"] == ["route_refinement_required", "manual_proof_obligations"]


def test_machine_local_config_has_focused_local_lane_but_shared_config_does_not(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    local = workspace_runtime_proof._proof_selection_for_changed_paths(
        changed_paths=[".agentic-workspace/config.local.toml"],
        target_root=tmp_path,
        include_durable_intent=False,
    )
    local_lane = next(lane for lane in local["selected_lanes"] if lane["id"] == "domain:machine_local_config")
    assert local_lane["claim_boundary"] == "effective-local-configuration-only"
    assert local["route_refinement_required"]["status"] != "required"

    shared = workspace_runtime_proof._proof_selection_for_changed_paths(
        changed_paths=[".agentic-workspace/config.toml"],
        target_root=tmp_path,
        include_durable_intent=False,
    )
    assert all(lane["id"] != "domain:machine_local_config" for lane in shared["selected_lanes"])


def test_proof_cli_exposes_typed_selected_execution_dry_run(tmp_path: Path, capsys, monkeypatch) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    monkeypatch.setattr(
        workspace_runtime_core,
        "_proof_selection_for_changed_paths",
        lambda **_: _selected_execution_fixture(["check-local-config"]),
    )
    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                ".agentic-workspace/config.local.toml",
                "--execute-selected",
                "--dry-run",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/proof-execution-result/v1"
    assert payload["status"] == "dry-run"
    assert payload["persistence"]["repository_residue"] is False
