from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator
from tests.test_workspace_proof_cli import _verified_host_fixture, _write_independent_review_host_result

import agentic_workspace.client as public_client
from agentic_workspace import (
    AWClientError,
    cli,
    detect_workspace,
    external_conformance_profile,
    external_contract_bundle,
    external_readiness_report,
    invoke_operation,
    negotiate_requirements,
    operation_compatibility_fingerprint,
    require_operations,
    resolve_invocation,
)
from agentic_workspace.config import WorkspaceUsageError
from agentic_workspace.generated_operations import (
    agent_guidance_delete,
    agent_guidance_edit,
    agent_guidance_merge,
    agent_guidance_promote,
    agent_guidance_retire,
    agent_guidance_revalidate,
    agent_guidance_split,
    agent_guidance_supersede,
    agent_guidance_suppress,
    agent_guidance_weaken,
    assignment_admit,
    assignment_close,
    assignment_dispatch,
    assignment_export,
    assignment_import,
    assignment_integrate,
    assignment_override,
    config_report,
    correction_event_prune_compact,
    correction_event_query,
    correction_event_submit,
    delegation_outcome_append,
)
from agentic_workspace.workspace_runtime_proof import (
    INDEPENDENT_REVIEW_HOST_RESULT_DIR,
    INDEPENDENT_REVIEW_HOST_RESULT_INDEX_KIND,
    INDEPENDENT_REVIEW_RESULT_DIR,
    INDEPENDENT_REVIEW_RESULT_INDEX_KIND,
    _independent_review_scope_digest,
    admit_independent_review_result_operation,
    record_trusted_independent_review_result,
)

ROOT = Path(__file__).resolve().parents[1]


def test_assignment_cli_transport_invokes_allow_listed_adapter_and_returns_untrusted_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from agentic_workspace.contracts import python_primitive_support

    returned = {
        "assignment_revision": "assignment-rev-1",
        "run_id": "run-1",
        "target": "planner",
        "changed_paths": ["src/feature.py"],
        "summary": "Implemented the bounded change.",
        "stop_conditions_hit": [],
        "patch": "--- a/src/feature.py\n+++ b/src/feature.py\n@@ -1 +1 @@\n-old\n+new\n",
    }
    observed: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        observed["command"] = command
        observed["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout=json.dumps(returned), stderr="")

    monkeypatch.setattr(python_primitive_support.subprocess, "run", fake_run)
    receipt = python_primitive_support._dispatch_assignment_packet(
        packet={
            "assignment_identity": {
                "role": "implementer",
                "dispatch_adapter": {
                    "kind": "process",
                    "command": [
                        "codex",
                        "exec",
                        "--ephemeral",
                        "--ignore-rules",
                        "--sandbox",
                        "read-only",
                        "--cd",
                        "{target_root}",
                        "--model",
                        "{model}",
                        "--output-schema",
                        "{output_schema}",
                        "--output-last-message",
                        "{output_file}",
                        "-",
                    ],
                    "output_mode": "stdout",
                    "timeout_seconds": 1800,
                    "model": "gpt-5.6-terra",
                    "execution_methods": ["cli"],
                },
            }
        },
        prompt="sealed packet",
        target_root=tmp_path,
        transport="cli",
    )

    assert receipt["status"] == "returned"
    assert receipt["returned_work"] == returned
    assert receipt["stdout_tail"] == json.dumps(returned)
    assert receipt["claim_boundary"].startswith("transport-only")
    context_cost = receipt["context_cost"]
    assert context_cost["kind"] == "agentic-workspace/assignment-context-cost/v1"
    assert context_cost["transport"] == "cli"
    assert context_cost["assignment_packet_bytes"] > 0
    assert context_cost["rendered_prompt_bytes"] == len("sealed packet".encode("utf-8"))
    assert context_cost["effective_input_tokens"] is None
    assert context_cost["unknown_fields"] == [
        "effective_input_tokens",
        "cached_input_tokens",
        "output_tokens",
        "orientation_command_count",
        "retry_count",
        "repair_loop_count",
    ]
    assert context_cost["raw_transcript_stored"] is False
    command = observed["command"]
    assert isinstance(command, list)
    assert command[:10] == [
        "codex",
        "exec",
        "--ephemeral",
        "--ignore-rules",
        "--sandbox",
        "read-only",
        "--cd",
        str(tmp_path),
        "--model",
        "gpt-5.6-terra",
    ]
    assert command[10] == "--output-schema"
    assert Path(command[11]).name == "delegated-return.schema.json"
    assert command[12] == "--output-last-message"
    assert Path(command[13]).name == "last-message.json"
    assert command[14] == "-"
    assert observed["kwargs"]["input"] == "sealed packet"  # type: ignore[index]
    assert observed["kwargs"]["encoding"] == "utf-8"  # type: ignore[index]
    assert observed["kwargs"]["errors"] == "replace"  # type: ignore[index]
    assert python_primitive_support._assignment_patch_paths("--- a/outside.txt\n+++ /dev/null\n") == ["outside.txt"]
    assert python_primitive_support._assignment_patch_paths(
        "diff --git a/src/feature.py b/outside.py\nsimilarity index 100%\nrename from src/feature.py\nrename to outside.py\n"
    ) == ["outside.py", "src/feature.py"]


def test_assignment_transport_metrics_sidecar_is_validated_and_admitted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agentic_workspace.contracts import python_primitive_support

    returned = {
        "assignment_revision": "sha256:assignment",
        "run_id": "run-metrics",
        "target": "worker",
        "changed_paths": [],
        "summary": "Completed the bounded assignment.",
        "stop_conditions_hit": [],
    }
    metrics = {
        "kind": "agentic-workspace/assignment-transport-metrics/v1",
        "effective_input_tokens": 1234,
        "cached_input_tokens": 1000,
        "output_tokens": 55,
        "orientation_command_count": 2,
        "retry_count": 1,
        "repair_loop_count": 0,
    }

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        metrics_path = Path(command[command.index("--metrics") + 1])
        metrics_path.write_text(json.dumps(metrics), encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout=json.dumps(returned), stderr="")

    monkeypatch.setattr(python_primitive_support.subprocess, "run", fake_run)
    receipt = python_primitive_support._dispatch_assignment_packet(
        packet={
            "assignment_identity": {
                "role": "implementer",
                "dispatch_adapter": {
                    "kind": "process",
                    "command": ["worker-bridge", "--metrics", "{metrics_file}"],
                    "output_mode": "stdout",
                    "timeout_seconds": 60,
                    "execution_methods": ["cli"],
                },
            }
        },
        prompt="sealed packet",
        target_root=tmp_path,
        transport="cli",
    )

    metrics_schema = json.loads((ROOT / "src/agentic_workspace/contracts/schemas/assignment_transport_metrics.schema.json").read_text())
    cost_schema = json.loads((ROOT / "src/agentic_workspace/contracts/schemas/assignment_context_cost.schema.json").read_text())
    Draft202012Validator.check_schema(metrics_schema)
    Draft202012Validator(metrics_schema).validate(metrics)
    Draft202012Validator.check_schema(cost_schema)
    Draft202012Validator(cost_schema).validate(receipt["context_cost"])
    assert receipt["context_cost"] | {"elapsed_ms": 0} == {
        "kind": "agentic-workspace/assignment-context-cost/v1",
        "transport": "cli",
        "adapter_revision": receipt["adapter_revision"],
        "assignment_packet_bytes": receipt["context_cost"]["assignment_packet_bytes"],
        "rendered_prompt_bytes": len("sealed packet".encode("utf-8")),
        "effective_input_tokens": 1234,
        "cached_input_tokens": 1000,
        "output_tokens": 55,
        "orientation_command_count": 2,
        "retry_count": 1,
        "repair_loop_count": 0,
        "elapsed_ms": 0,
        "unknown_fields": [],
        "observation_authority": "adapter-sidecar-or-host-measurement",
        "raw_transcript_stored": False,
    }


def test_assignment_transport_rejects_unrecognized_metrics_sidecar_without_fabricating_zeroes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from agentic_workspace.contracts import python_primitive_support

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        metrics_path = Path(command[command.index("--metrics") + 1])
        metrics_path.write_text('{"kind":"provider-private-metrics/v1","effective_input_tokens":0}', encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="{}", stderr="")

    monkeypatch.setattr(python_primitive_support.subprocess, "run", fake_run)
    receipt = python_primitive_support._dispatch_assignment_packet(
        packet={
            "assignment_identity": {
                "dispatch_adapter": {
                    "kind": "process",
                    "command": ["worker-bridge", "--metrics", "{metrics_file}"],
                    "output_mode": "stdout",
                    "timeout_seconds": 60,
                    "execution_methods": ["cli"],
                }
            }
        },
        prompt="sealed packet",
        target_root=tmp_path,
        transport="cli",
    )

    assert receipt["context_cost"]["effective_input_tokens"] is None
    assert "effective_input_tokens" in receipt["context_cost"]["unknown_fields"]


def test_assignment_cli_transport_accepts_explicit_no_change_implementer_return(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agentic_workspace.contracts import python_primitive_support

    returned = {
        "assignment_revision": "sha256:assignment",
        "run_id": "run-no-change",
        "target": "worker",
        "changed_paths": [],
        "summary": "The scoped reference is already accurate.",
        "stop_conditions_hit": [],
        "patch": "",
    }

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        last_message_path = Path(command[command.index("--output-last-message") + 1])
        last_message_path.write_text(json.dumps(returned), encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(python_primitive_support.subprocess, "run", fake_run)
    receipt = python_primitive_support._dispatch_assignment_packet(
        packet={
            "assignment_identity": {
                "role": "implementer",
                "dispatch_adapter": {
                    "kind": "process",
                    "command": ["codex", "exec", "--output-last-message", "{output_file}", "-"],
                    "output_mode": "json-file",
                    "timeout_seconds": 1800,
                    "model": "gpt-5.6-luna",
                    "execution_methods": ["internal"],
                },
            }
        },
        prompt="sealed packet",
        target_root=tmp_path,
        transport="internal",
    )

    assert receipt["status"] == "returned"
    assert receipt["returned_work"] == returned


def test_assignment_process_and_host_native_adapters_share_one_prompt_and_return_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from agentic_workspace.contracts import python_primitive_support

    returned = {
        "assignment_revision": "sha256:assignment",
        "run_id": "run-peer",
        "target": "worker",
        "changed_paths": [],
        "summary": "Validated the bounded assignment.",
        "stop_conditions_hit": [],
    }
    observed_prompts: list[str] = []
    observed_schemas: list[dict[str, object]] = []

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        observed_prompts.append(str(kwargs["input"]))
        schema_path = Path(command[command.index("--schema") + 1])
        observed_schemas.append(json.loads(schema_path.read_text(encoding="utf-8")))
        return SimpleNamespace(returncode=0, stdout=json.dumps(returned), stderr="")

    monkeypatch.setattr(python_primitive_support.subprocess, "run", fake_run)
    base_identity = {
        "role": "validator",
        "target": "worker",
        "allowed_paths": ["docs/reference.md"],
        "return_contract": {"kind": "agentic-workspace/delegated-return/v1"},
    }
    packet = {"kind": "agentic-workspace/assignment-export-packet/v1", "assignment_identity": base_identity}
    prompt = python_primitive_support._assignment_export_prompt(packet)
    receipts = []
    for adapter_kind, transport in (("process", "cli"), ("host-native", "internal")):
        receipts.append(
            python_primitive_support._dispatch_assignment_packet(
                packet={
                    **packet,
                    "assignment_identity": {
                        **base_identity,
                        "dispatch_adapter": {
                            "kind": adapter_kind,
                            "command": [
                                "configured-worker-bridge",
                                "--root",
                                "{target_root}",
                                "--schema",
                                "{output_schema}",
                            ],
                            "output_mode": "stdout",
                            "timeout_seconds": 60,
                            "execution_methods": [transport],
                        },
                    },
                },
                prompt=prompt,
                target_root=tmp_path,
                transport=transport,
            )
        )

    assert observed_prompts == [prompt, prompt]
    assert [receipt["status"] for receipt in receipts] == ["returned", "returned"]
    assert [receipt["adapter_kind"] for receipt in receipts] == ["process", "host-native"]
    assert all(receipt["returned_work"] == returned for receipt in receipts)
    assert all(receipt["claim_boundary"].startswith("transport-only") for receipt in receipts)
    assert all("patch" not in schema["properties"] for schema in observed_schemas)
    assert all(set(schema["required"]) == set(schema["properties"]) for schema in observed_schemas)


def test_assignment_dispatch_selects_payload_from_exact_canonical_transport_variant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from agentic_workspace.contracts import python_primitive_support

    observed: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        observed["command"] = command
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "assignment_revision": "sha256:assignment",
                    "run_id": "run-api",
                    "target": "worker",
                    "changed_paths": [],
                    "summary": "API variant completed.",
                    "stop_conditions_hit": [],
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(python_primitive_support.subprocess, "run", fake_run)
    receipt = python_primitive_support._dispatch_assignment_packet(
        packet={
            "assignment_identity": {
                "role": "validator",
                "dispatch_adapter": {
                    "kind": "process",
                    "command": ["legacy-wrong-command"],
                    "execution_methods": ["cli", "api"],
                    "transports": [
                        {
                            "kind": "process",
                            "method": "cli",
                            "command": ["cli-worker"],
                            "output_mode": "stdout",
                            "timeout_seconds": 60,
                            "readiness": "configured",
                        },
                        {
                            "kind": "api",
                            "method": "api",
                            "command": ["api-worker", "--schema", "{output_schema}"],
                            "output_mode": "stdout",
                            "timeout_seconds": 30,
                            "readiness": "configured",
                        },
                    ],
                },
            }
        },
        prompt="sealed packet",
        target_root=tmp_path,
        transport="api",
    )

    assert receipt["status"] == "returned"
    assert receipt["adapter_kind"] == "process"
    assert observed["command"][0] == "api-worker"  # type: ignore[index]


def test_assignment_worker_context_projects_only_canonical_bounded_authority() -> None:
    from agentic_workspace.contracts import python_primitive_support

    packet = {
        "kind": "agentic-workspace/assignment-export-packet/v1",
        "assignment_id": "assignment-1",
        "assignment_revision": "sha256:assignment",
        "run_id": "run-1",
        "target": "worker",
        "assignment_identity": {
            "revision": "sha256:identity",
            "human_intent": "Validate the bounded documentation slice.",
            "task_class": "validation",
            "role": "validator",
            "scope_class": "documentation",
            "allowed_paths": ["docs/reference.md"],
            "allowed_effects": ["read"],
            "prohibited_effects": ["write", "merge", "proof-authority"],
            "required_inputs": ["current checkout"],
            "read_first": ["docs/reference.md", "summary:planning_record"],
            "proof_obligation_id": "proof-1",
            "proof_obligation_revision": "sha256:proof",
            "stop_conditions": ["scope mismatch"],
            "claim_authority": {
                "worker_result": "evidence-only",
                "proof": "orchestrator-owned",
                "integration": "orchestrator-owned",
                "completion": "orchestrator-owned",
            },
            "dispatch_adapter": {"kind": "process", "command": ["secret-provider-command"]},
        },
        "return_contract": {
            "kind": "agentic-workspace/delegated-return/v1",
            "required_fields": ["assignment_revision", "run_id", "summary"],
            "worker_proof_authority": False,
            "worker_completion_authority": False,
        },
        "authority_refs": {"planning_assignment": "broad/planning/state.json"},
        "parent_conversation": "must never be transmitted",
        "broad_workspace_summary": "must never be transmitted",
    }

    context = python_primitive_support._assignment_worker_context(packet)
    prompt = python_primitive_support._assignment_export_prompt({**packet, "worker_context": context})
    schema = json.loads((ROOT / "src/agentic_workspace/contracts/schemas/assignment_worker_context.schema.json").read_text())

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(context)
    assert context == {
        "kind": "agentic-workspace/assignment-worker-context/v1",
        "assignment": {
            "id": "assignment-1",
            "revision": "sha256:assignment",
            "run_id": "run-1",
            "target": "worker",
        },
        "intent": {
            "outcome": "Validate the bounded documentation slice.",
            "task_class": "validation",
            "role": "validator",
        },
        "scope": {"class": "documentation", "allowed_paths": ["docs/reference.md"]},
        "effects": {"allowed": ["read"], "prohibited": ["write", "merge", "proof-authority"]},
        "inputs": {
            "required": ["current checkout"],
            "read_first": ["docs/reference.md", "summary:planning_record"],
            "lazy_expansion_rule": (
                "Read only these exact references first; request or resolve deeper context only when the assignment requires it."
            ),
        },
        "proof": {"obligation_id": "proof-1", "obligation_revision": "sha256:proof", "worker_authority": False},
        "stop_conditions": ["scope mismatch"],
        "authority": {
            "semantic_source": "canonical-assignment-identity",
            "claim_authority": {
                "worker_result": "evidence-only",
                "proof": "orchestrator-owned",
                "integration": "orchestrator-owned",
                "completion": "orchestrator-owned",
            },
            "scope_widening_allowed": False,
        },
        "return_contract": packet["return_contract"],
    }
    assert '"kind": "agentic-workspace/assignment-worker-context/v1"' in prompt
    assert "docs/reference.md" in prompt
    assert "summary:planning_record" in prompt
    assert "must never be transmitted" not in prompt
    assert "secret-provider-command" not in prompt
    assert "broad/planning/state.json" not in prompt


def test_assignment_worker_context_ignores_non_authoritative_packet_overrides() -> None:
    from agentic_workspace.contracts import python_primitive_support

    packet = {
        "assignment_id": "assignment-1",
        "assignment_revision": "sha256:assignment",
        "run_id": "run-1",
        "target": "worker",
        "scope": ["outside/**"],
        "allowed_effects": ["write"],
        "assignment_identity": {
            "human_intent": "Read one file.",
            "allowed_paths": ["docs/reference.md"],
            "allowed_effects": ["read"],
            "prohibited_effects": ["write"],
            "read_first": ["docs/reference.md"],
            "claim_authority": {"worker_result": "evidence-only"},
        },
        "return_contract": {"worker_proof_authority": False, "worker_completion_authority": False},
    }

    context = python_primitive_support._assignment_worker_context(packet)

    assert context["scope"]["allowed_paths"] == ["docs/reference.md"]
    assert context["effects"] == {"allowed": ["read"], "prohibited": ["write"]}
    assert context["authority"]["scope_widening_allowed"] is False
    assert context["proof"]["worker_authority"] is False


def test_assignment_dispatch_fails_closed_without_configured_adapter(tmp_path: Path) -> None:
    from agentic_workspace.contracts import python_primitive_support

    receipt = python_primitive_support._dispatch_assignment_packet(
        packet={
            "assignment_identity": {
                "role": "validator",
                "dispatch_adapter": {"execution_methods": ["cli"]},
            }
        },
        prompt="sealed packet",
        target_root=tmp_path,
        transport="cli",
    )

    assert receipt["status"] == "blocked"
    assert receipt["reason"] == "configured-dispatch-adapter-unavailable"


@pytest.mark.parametrize("timeout", [0, -1, True, 1.5])
def test_assignment_dispatch_rejects_non_positive_or_non_integer_timeout(tmp_path: Path, timeout: object) -> None:
    from agentic_workspace.contracts import python_primitive_support

    receipt = python_primitive_support._dispatch_assignment_packet(
        packet={
            "assignment_identity": {
                "role": "validator",
                "dispatch_adapter": {
                    "kind": "process",
                    "command": ["configured-worker-bridge"],
                    "output_mode": "stdout",
                    "timeout_seconds": timeout,
                    "execution_methods": ["cli"],
                },
            }
        },
        prompt="sealed packet",
        target_root=tmp_path,
        transport="cli",
    )

    assert receipt["status"] == "blocked"
    assert receipt["reason"] == "configured-dispatch-timeout-invalid"


def test_assignment_admission_accepts_no_change_but_rejects_changed_paths_without_patch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agentic_workspace.contracts import python_primitive_support

    identity = {
        "complete": True,
        "revision": "sha256:assignment",
        "target": "worker",
        "role": "implementer",
        "mutation_baseline": "baseline-1",
        "allowed_paths": ["docs/reference.md"],
    }
    monkeypatch.setattr(python_primitive_support, "_assignment_identity", lambda _authorities: identity)
    authorities = {
        "assignment_gate": {"status": "handoff-required"},
        "assignment_policy": {"assignment_policy": "required-best-fit"},
        "delegation_decision": {"decision": "assign-best-fit"},
        "structural_proof_receipt": {
            "kind": "agentic-workspace/assignment-structural-proof-receipt/v1",
            "result": "passed",
            "verified_by": "aw",
            "assignment_revision": "sha256:assignment",
        },
        "run_state": {"run_id": "run-1", "status": "awaiting-admission"},
        "live_mutation_baseline": "baseline-1",
    }
    no_change = {
        "assignment_revision": "sha256:assignment",
        "run_id": "run-1",
        "target": "worker",
        "changed_paths": [],
        "stop_conditions_hit": [],
        "patch": "",
    }

    admitted = python_primitive_support._assignment_admit_with_current_authority(
        current_authorities=authorities,
        returned_work=no_change,
    )
    rejected = python_primitive_support._assignment_admit_with_current_authority(
        current_authorities=authorities,
        returned_work={**no_change, "changed_paths": ["docs/reference.md"]},
    )

    assert admitted["status"] == "admitted"
    assert rejected["status"] == "rejected"
    assert [failure["reason"] for failure in rejected["failures"]] == ["missing-implementation-patch"]


def _guidance_host_signature(payload: dict[str, object]) -> dict[str, object]:
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
        "issuer": "github-review-adapter",
        "trusted_channel": "github-review-webhook",
        "n": format(n, "x"),
        "e": "010001",
        "status": "current",
    },
    "signature": base64.urlsafe_b64encode(raw).decode("ascii").rstrip("="),
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


def _trusted_guidance_host_event(
    target_root: Path,
    *,
    authority: str,
    producer_class: str,
    producer_id: str,
    source_ref: str,
    host_admission_monkeypatch: pytest.MonkeyPatch | None = None,
    source: str = "",
    target_revision: str = "",
    event_id: str = "",
    import_event: bool = True,
    event_fields: dict[str, object] | None = None,
) -> dict[str, object]:
    from agentic_workspace.agent_guidance import (
        TRUSTED_AUTHORITY_EVENT_AUDIENCE,
        TRUSTED_AUTHORITY_EVENT_INBOX_PATH,
        _json_digest,
        _trusted_authority_admission_signature_payload,
        _trusted_authority_event_digest,
        record_trusted_authority_host_event,
    )

    event = {
        "kind": "agentic-workspace/trusted-authority-host-event/v1",
        "status": "current",
        "authority": authority,
        "producer_class": producer_class,
        "producer_id": producer_id,
        "source": source or authority,
        "source_ref": source_ref,
        "target_revision": target_revision,
        "event_id": event_id,
        "recorded_at": "2026-07-29T00:00:00Z",
        "admission_context": {
            "audience": TRUSTED_AUTHORITY_EVENT_AUDIENCE,
            "workspace_ref": f"workspace:path:{target_root.resolve()}",
            "issued_at": "2026-07-29T00:00:00Z",
            "expires_at": "2099-01-01T00:00:00Z",
            "nonce": f"{source_ref}:{event_id or 'event'}",
        },
        "custody": {
            "producer": "github-review-adapter",
            "trusted_channel": "github-review-webhook",
            "rule": "Fixture for an adapter-owned host event; repo-local guidance code only imports it.",
        },
    }
    event.update(event_fields or {})
    event_ref = "trusted-authority-event:" + _json_digest(event)[:24]
    event["event_ref"] = event_ref
    event["host_admission_verdict"] = {
        "kind": "agentic-workspace/trusted-authority-host-event-verdict/v1",
        "status": "admitted",
        "admission_authority": "signed-host-adapter",
        "event_ref": event_ref,
        "event_digest": _trusted_authority_event_digest(event),
        "producer": "github-review-adapter",
        "trusted_channel": "github-review-webhook",
        "correction_authority": authority,
        "producer_class": producer_class,
        "source_ref": source_ref,
        "target_revision": target_revision,
        "event_id": event_id,
        "workspace_ref": f"workspace:path:{target_root.resolve()}",
        "audience": TRUSTED_AUTHORITY_EVENT_AUDIENCE,
        "issued_at": "2026-07-29T00:00:00Z",
        "expires_at": "2099-01-01T00:00:00Z",
        "nonce": f"{source_ref}:{event_id or 'event'}",
        "verifier_revision": "guidance-host-test-verifier:1",
    }
    event["host_admission"] = {
        "kind": "agentic-workspace/trusted-authority-host-admission/v1",
        "algorithm": "RS256",
        "key_id": "github-review-adapter:external-host-fixture:" + event_ref.removeprefix("trusted-authority-event:"),
    }
    signature_payload = _trusted_authority_admission_signature_payload(
        ref=event_ref,
        event=event,
        verdict=event["host_admission_verdict"],
        admission=event["host_admission"],
    )
    signed = _guidance_host_signature(signature_payload)
    event["host_admission"]["signature"] = str(signed["signature"])
    import agentic_workspace.agent_guidance as guidance_runtime

    trusted_keys = {
        **guidance_runtime._TRUSTED_AUTHORITY_HOST_PUBLIC_KEYS,  # type: ignore[attr-defined]
        str(event["host_admission"]["key_id"]): signed["key"],
    }
    if host_admission_monkeypatch is None:
        guidance_runtime._TRUSTED_AUTHORITY_HOST_PUBLIC_KEYS = trusted_keys  # type: ignore[attr-defined]
    else:
        host_admission_monkeypatch.setattr(
            guidance_runtime,
            "_TRUSTED_AUTHORITY_HOST_PUBLIC_KEYS",
            trusted_keys,
        )
    inbox_path = target_root / TRUSTED_AUTHORITY_EVENT_INBOX_PATH / f"{event_ref.removeprefix('trusted-authority-event:')}.json"
    inbox_path.parent.mkdir(parents=True, exist_ok=True)
    inbox_path.write_text(json.dumps(event, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if import_event:
        imported = record_trusted_authority_host_event(
            target_root=target_root,
            authority=authority,
            producer_class=producer_class,
            producer_id=producer_id,
            source_ref=source_ref,
            source=source or authority,
            target_revision=target_revision,
            event_id=event_id,
            trusted_channel="github-review-webhook",
            host_event_ref=event_ref,
        )
        return {"event_ref": event_ref, "event": imported["event"]}
    return {"event_ref": event_ref, "event": event}


def _independent_review_host_result_fixture(tmp_path: Path, *, changed_paths: list[str] | None = None, **overrides: object):
    changed = ["src/feature.py"] if changed_paths is None else changed_paths
    review_result = {
        "kind": "agentic-workspace/independent-review-result/v1",
        "status": "accepted",
        "required_mode": "separate-actor",
        "assignment_id": str(overrides.get("assignment_id") or "assign-1"),
        "assignment_revision": str(overrides.get("assignment_revision") or "assignment-rev-1"),
        "proof_subject_revision": str(overrides.get("proof_subject_revision") or "proof-rev-1"),
        "review_revision": str(overrides.get("review_revision") or "review-rev-1"),
        "scope_digest": _independent_review_scope_digest(changed),
        "changed_paths": changed,
        "implementer": {"actor_id": "codex-implementer", "provider": "openai", "role": "implementer"},
        "reviewer": {"actor_id": "human-reviewer", "provider": "github", "role": "reviewer", "fresh_context": True},
        "reviewed_at": "2026-07-31T00:00:00Z",
        "expires_at": str(overrides.get("expires_at") or "2099-01-01T00:00:00Z"),
        "custody": {
            "producer": "github-review-adapter",
            "trusted_channel": "github-review-webhook",
            "authority_ref": "github-pr-review:1",
        },
    }
    if overrides.get("revoked_at"):
        review_result["admission_revoked_at"] = str(overrides["revoked_at"])
    if overrides.get("verdict_expires_at"):
        review_result["admission_expires_at"] = str(overrides["verdict_expires_at"])
    host_result_ref = _write_independent_review_host_result(tmp_path, review_result)
    host_result_id = host_result_ref.removeprefix("independent-review-host-result:")
    host_result = json.loads((tmp_path / INDEPENDENT_REVIEW_HOST_RESULT_DIR / f"{host_result_id}.json").read_text(encoding="utf-8"))

    def resolver(ref: str) -> dict[str, object]:
        if ref != host_result_ref:
            raise AssertionError(f"unexpected host result ref: {ref}")
        return host_result

    return host_result_ref, host_result, resolver


def _readiness_conformance_evidence(profile: dict, operation: dict, *, status: str = "passed") -> dict:
    authority = profile.get("readiness_authority", {})
    return {
        "kind": "agentic-workspace/external-operation-conformance-result/v1",
        "status": status,
        "operation_id": operation["id"],
        "operation_fingerprint": operation["operation_compatibility"]["fingerprint"],
        "profile_fingerprint": profile["compatibility"]["fingerprint"],
        "runtime_exception_revision": "#2044@accepted",
        "result_identity": {
            "runner_revision": authority.get("runner_revision", ""),
            "client_semantics_revision": authority.get("client_semantics_revision", ""),
        },
        "transports": {
            "cli-json": {"status": "passed"},
            "python": {"status": "passed"},
            "typescript": {"status": "passed"},
            "vendor-neutral": {"status": "passed"},
        },
        "executors": {
            "cli-json": {"status": "passed", "executor_id": "direct-cli-json"},
            "python": {"status": "passed", "executor_id": "generated-python-client"},
            "typescript": {"status": "passed", "executor_id": "generated-typescript-client"},
            "vendor-neutral": {"status": "passed", "executor_id": "packed-typescript-client"},
        },
        "cases": {
            "absent": {"status": "passed"},
            "disabled": {"status": "passed"},
            "incompatible": {"status": "passed"},
            "malformed": {"status": "passed"},
            "retryable": {"status": "passed"},
            "additive-field": {"status": "passed"},
            "mutation-applied": {"status": "passed"},
            "mutation-noop": {"status": "passed"},
            "mutation-rejected": {"status": "passed"},
            "mutation-failed": {"status": "passed"},
        },
        "case_transport_matrix": {
            case: {transport: {"status": "passed"} for transport in ("cli-json", "python", "typescript", "vendor-neutral")}
            for case in (
                "absent",
                "disabled",
                "incompatible",
                "malformed",
                "retryable",
                "additive-field",
                "mutation-applied",
                "mutation-noop",
                "mutation-rejected",
                "mutation-failed",
            )
        },
        "footprints": {
            "necessary-surfaces": {"status": "passed"},
            "full-mirror": {"status": "passed"},
            "semantic-parity": {"status": "passed"},
        },
    }


def _readiness_conformance_receipt_store(profile: dict, operation: dict, *, status: str = "passed") -> dict:
    receipt = {
        **_readiness_conformance_evidence(profile, operation, status=status),
        "kind": "agentic-workspace/external-operation-conformance-receipt/v1",
        "receipt_ref": f"external-conformance:{operation['id']}:test",
        "executed_at": "2026-07-26T20:00:00Z",
        "custody": {
            "operation_id": "external-operation-conformance.run",
            "producer": "agentic-workspace.operation-conformance-runner",
            "trusted_channel": "producer-owned-test-fixture",
        },
    }
    return {"kind": "agentic-workspace/external-operation-conformance-receipt-store/v1", "receipts": [receipt]}


def _published_readiness_receipt_store(store: dict) -> dict:
    payload = copy.deepcopy(store)
    publication_payload = {key: value for key, value in payload.items() if key != "mirror_publication"}
    digest = hashlib.sha256(json.dumps(publication_payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    payload["mirror_publication"] = {
        "kind": "agentic-workspace/external-operation-conformance-mirror-publication/v1",
        "status": "published",
        "payload_digest": f"sha256:{digest}",
    }
    return payload


def test_external_readiness_report_fails_closed_for_runtime_backed_operations() -> None:
    report = external_readiness_report(["assignment.export", "does.not.exist"])
    assert report["status"] == "not-ready"
    runtime_backed, unknown = report["excluded_operations"]
    assert runtime_backed["id"] == "assignment.export"
    assert runtime_backed["status"] == "runtime-backed"
    assert runtime_backed["evidence"]["conformance_refs"]
    assert runtime_backed["evidence"]["conformance_result"] == {}
    assert "executed-conformance-receipt" in runtime_backed["missing_evidence"]
    assert runtime_backed["evidence"]["runtime_exceptions"]
    assert unknown["id"] == "does.not.exist"
    assert "released-python-resource" in unknown["missing_evidence"]


def test_external_readiness_report_requires_released_client_and_conformance_evidence(monkeypatch) -> None:
    profile = copy.deepcopy(public_client.external_consumer_profile())
    candidate = next(entry for entry in profile["operations"] if entry["id"] == "assignment.export")
    candidate["external_consumption"] = {"status": "supported"}
    candidate["operation_resources"]["typescript"]["exists"] = False
    candidate["conformance"] = []
    monkeypatch.setattr(public_client, "external_consumer_profile", lambda: profile)

    report = external_readiness_report(["assignment.export"])

    assert report["status"] == "not-ready"
    excluded = report["excluded_operations"][0]
    assert set(excluded["missing_evidence"]) == {
        "released-typescript-resource",
        "conformance-reference",
        "executed-conformance-receipt",
    }
    assert excluded["evidence"]["conformance_result"] == {}


def test_external_readiness_report_requires_current_executed_cross_transport_conformance(monkeypatch) -> None:
    profile = copy.deepcopy(public_client.external_consumer_profile())
    candidate = next(entry for entry in profile["operations"] if entry["id"] == "assignment.export")
    candidate["external_consumption"]["status"] = "supported"
    monkeypatch.setattr(public_client, "external_consumer_profile", lambda: profile)
    monkeypatch.setattr(
        public_client, "external_operation_conformance_receipts", lambda: _readiness_conformance_receipt_store(profile, candidate)
    )

    report = external_readiness_report(["assignment.export"])

    assert report["status"] == "ready"
    assert report["supported_operations"] == ["assignment.export"]
    assert report["supported_operation_evidence"][0]["id"] == "assignment.export"
    assert report["supported_operation_evidence"][0]["receipt_ref"]
    assert report["operation_accounting"]["profile_operation_count"] == len(profile["operations"])
    assert report["operation_accounting"]["not_advertised_count"] > 0
    assert report["excluded_operations"] == []

    stale_profile = copy.deepcopy(profile)
    stale_profile["compatibility"]["fingerprint"] = "sha256:stale"
    monkeypatch.setattr(public_client, "external_consumer_profile", lambda: stale_profile)
    monkeypatch.setattr(
        public_client,
        "external_operation_conformance_receipts",
        lambda: _readiness_conformance_receipt_store(profile, candidate),
    )

    stale_report = external_readiness_report(["assignment.export"])

    assert stale_report["status"] == "not-ready"
    assert "executed-conformance-receipt" in stale_report["excluded_operations"][0]["missing_evidence"]


@pytest.mark.parametrize(
    ("mutation", "expected_reason"),
    [
        ("missing", "executed-conformance-receipt"),
        ("failed", "executed-conformance-passed"),
        ("stale-runner", "current-runner-revision"),
        ("stale-client", "current-client-semantics-revision"),
        ("missing-transport", "transport-typescript"),
        ("missing-case", "case-mutation-failed"),
    ],
)
def test_require_operations_uses_readiness_receipts(monkeypatch: pytest.MonkeyPatch, mutation: str, expected_reason: str) -> None:
    profile = copy.deepcopy(public_client.external_consumer_profile())
    candidate = next(entry for entry in profile["operations"] if entry["id"] == "assignment.export")
    candidate["external_consumption"]["status"] = "supported"
    store = _readiness_conformance_receipt_store(profile, candidate)
    receipt = store["receipts"][0]
    if mutation == "missing":
        store["receipts"] = []
    elif mutation == "failed":
        receipt["status"] = "failed"
    elif mutation == "stale-runner":
        receipt["result_identity"]["runner_revision"] = "stale-runner"
    elif mutation == "stale-client":
        receipt["result_identity"]["client_semantics_revision"] = "stale-client"
    elif mutation == "missing-transport":
        receipt["transports"].pop("typescript")
    elif mutation == "missing-case":
        receipt["cases"].pop("mutation-failed")
    monkeypatch.setattr(public_client, "external_consumer_profile", lambda: profile)
    monkeypatch.setattr(public_client, "external_operation_conformance_receipts", lambda: store)

    with pytest.raises(AWClientError) as excinfo:
        require_operations(["assignment.export"])

    assert expected_reason in excinfo.value.details["requirements"][0]["missing_evidence"]


def test_generated_python_and_typescript_require_operations_share_readiness_reasons(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profile = copy.deepcopy(json.loads((ROOT / "generated/workspace/python/external_consumer_profile.json").read_text(encoding="utf-8")))
    candidate = next(entry for entry in profile["operations"] if entry["id"] == "assignment.export")
    candidate["external_consumption"]["status"] = "supported"
    store = _readiness_conformance_receipt_store(profile, candidate)
    receipt = store["receipts"][0]
    receipt["result_identity"]["runner_revision"] = "stale-runner"
    receipt["cases"].pop("mutation-failed")

    python_client = _python_client()
    monkeypatch.setattr(python_client, "external_consumer_profile", lambda: profile)
    monkeypatch.setattr(python_client, "external_operation_conformance_receipts", lambda: store)
    with pytest.raises(ValueError) as python_error:
        python_client.require_operations(["assignment.export"])
    assert "current-runner-revision" in str(python_error.value)
    assert "case-mutation-failed" in str(python_error.value)

    package_root = tmp_path / "typescript-readiness"
    shutil.copytree(ROOT / "generated/workspace/typescript", package_root)
    published = _published_readiness_receipt_store(store)
    (package_root / "external_consumer_profile.json").write_text(json.dumps(profile), encoding="utf-8")
    (package_root / "external_operation_conformance_receipts.json").write_text(json.dumps(published), encoding="utf-8")
    script = """
import { requireOperations } from './src/client.mjs';
try { requireOperations(['assignment.export']); }
catch (error) { console.log(JSON.stringify(error.details.requirements[0].missing_evidence)); }
"""
    completed = subprocess.run(["node", "--input-type=module", "--eval", script], cwd=package_root, text=True, capture_output=True)
    assert completed.returncode == 0, completed.stderr
    typescript_reasons = json.loads(completed.stdout)
    assert "current-runner-revision" in typescript_reasons
    assert "case-mutation-failed" in typescript_reasons


def test_external_readiness_report_ignores_inline_profile_conformance_evidence(monkeypatch) -> None:
    profile = copy.deepcopy(public_client.external_consumer_profile())
    candidate = next(entry for entry in profile["operations"] if entry["id"] == "assignment.export")
    candidate["external_consumption"]["status"] = "supported"
    candidate["conformance_evidence"] = _readiness_conformance_evidence(profile, candidate)
    monkeypatch.setattr(public_client, "external_consumer_profile", lambda: profile)
    monkeypatch.setattr(
        public_client,
        "external_operation_conformance_receipts",
        lambda: {"kind": "agentic-workspace/external-operation-conformance-receipt-store/v1", "receipts": []},
    )

    report = external_readiness_report(["assignment.export"])

    assert report["status"] == "not-ready"
    assert "executed-conformance-receipt" in report["excluded_operations"][0]["missing_evidence"]


def test_packaged_conformance_receipt_store_publishes_executed_external_evidence() -> None:
    store = public_client.external_operation_conformance_receipts()
    assert store["kind"] == "agentic-workspace/external-operation-conformance-receipt-store/v1"
    assert store["status"] == "recorded"
    receipts = {receipt["operation_id"]: receipt for receipt in store["receipts"]}
    assert {"config.report", "delegation-outcome.append"}.issubset(receipts)
    config_receipt = receipts["config.report"]
    assert config_receipt["status"] == "passed"
    assert {item["status"] for item in config_receipt["transports"].values()} == {"passed"}
    assert {transport: item["executor_id"] for transport, item in config_receipt["executors"].items()} == {
        "cli-json": "direct-cli-json",
        "python": "generated-python-client",
        "typescript": "generated-typescript-client",
        "vendor-neutral": "packed-typescript-client",
    }
    assert {item["status"] for item in config_receipt["cases"].values()} == {"passed"}
    assert config_receipt["freshness"]["strategy"] == "runner-client-operation-profile-revision-bound"
    delegation_receipt = receipts["delegation-outcome.append"]
    assert delegation_receipt["status"] == "passed"
    assert delegation_receipt["runtime_exception_revision"] == "github-2044-closure:delegation-outcome.append@pr-2256"
    assert delegation_receipt["runtime_exception_admission"]["status"] == "admitted"
    assert {item["status"] for item in delegation_receipt["transports"].values()} == {"passed"}
    assert {item["status"] for item in delegation_receipt["cases"].values()} == {"passed"}
    assert {
        cell["status"] for transport_cells in delegation_receipt["case_transport_matrix"].values() for cell in transport_cells.values()
    } == {"passed"}
    assert {item["status"] for item in delegation_receipt["footprints"].values()} == {"passed"}
    assert "reason" not in delegation_receipt["cases"]["mutation-noop"]
    assert delegation_receipt["operation_result_evidence"]
    report = external_readiness_report(["config.report", "delegation-outcome.append"], allow_runtime_backed=True)
    assert report["status"] == "ready"
    assert report["supported_operations"] == ["config.report", "delegation-outcome.append"]


def test_external_readiness_report_rejects_explicitly_revoked_and_superseded_receipts(monkeypatch) -> None:
    profile = copy.deepcopy(public_client.external_consumer_profile())
    candidate = next(entry for entry in profile["operations"] if entry["id"] == "assignment.export")
    candidate["external_consumption"]["status"] = "supported"
    base_receipt = _readiness_conformance_receipt_store(profile, candidate)["receipts"][0]
    monkeypatch.setattr(public_client, "external_consumer_profile", lambda: profile)
    for marker in ({"revoked_at": "2026-07-29T00:00:00Z"}, {"superseded_by": "newer"}, {"status": "stale"}):
        stale = {**base_receipt, **marker}
        monkeypatch.setattr(
            public_client,
            "external_operation_conformance_receipts",
            lambda stale=stale: {"kind": "agentic-workspace/external-operation-conformance-receipt-store/v1", "receipts": [stale]},
        )
        report = external_readiness_report(["assignment.export"])
        assert report["status"] == "not-ready"
        assert "executed-conformance-receipt" in report["excluded_operations"][0]["missing_evidence"]
    expired_only = {**base_receipt, "expires_at": "2000-01-01T00:00:00Z"}
    monkeypatch.setattr(
        public_client,
        "external_operation_conformance_receipts",
        lambda: {"kind": "agentic-workspace/external-operation-conformance-receipt-store/v1", "receipts": [expired_only]},
    )
    report = external_readiness_report(["assignment.export"])
    assert report["status"] == "not-ready"
    assert "executed-conformance-receipt" in report["excluded_operations"][0]["missing_evidence"]


def test_generated_clients_reject_expired_conformance_receipts(monkeypatch, tmp_path: Path) -> None:
    profile = copy.deepcopy(json.loads((ROOT / "generated/workspace/python/external_consumer_profile.json").read_text(encoding="utf-8")))
    candidate = next(entry for entry in profile["operations"] if entry["id"] == "assignment.export")
    candidate["external_consumption"]["status"] = "supported"
    receipt_store = _published_readiness_receipt_store(_readiness_conformance_receipt_store(profile, candidate))
    receipt_store["receipts"][0]["expires_at"] = "2000-01-01T00:00:00Z"

    python_client = _python_client()
    monkeypatch.setattr(python_client, "external_consumer_profile", lambda: profile)
    monkeypatch.setattr(python_client, "external_operation_conformance_receipts", lambda: receipt_store)
    python_report = python_client.external_readiness_report(["assignment.export"])
    assert python_report["status"] == "not-ready"
    assert "executed-conformance-receipt" in python_report["excluded_operations"][0]["missing_evidence"]

    package_root = tmp_path / "typescript"
    shutil.copytree(ROOT / "generated/workspace/typescript", package_root)
    (package_root / "external_consumer_profile.json").write_text(json.dumps(profile), encoding="utf-8")
    (package_root / "external_operation_conformance_receipts.json").write_text(json.dumps(receipt_store), encoding="utf-8")
    script = (
        "import { externalReadinessReport } from './src/client.mjs';"
        "console.log(JSON.stringify(externalReadinessReport(['assignment.export'])));"
    )
    completed = subprocess.run(["node", "--input-type=module", "--eval", script], cwd=package_root, text=True, capture_output=True)
    assert completed.returncode == 0, completed.stderr
    typescript_report = json.loads(completed.stdout)
    assert typescript_report["status"] == "not-ready"
    assert "executed-conformance-receipt" in typescript_report["excluded_operations"][0]["missing_evidence"]


def _python_client():
    path = ROOT / "generated/workspace/python/client.py"
    spec = importlib.util.spec_from_file_location("generated_external_client", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.files = lambda _package: ROOT / "generated/workspace/python"
    return module


def test_python_client_negotiates_and_invokes_json(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _python_client()
    profile = json.loads((ROOT / "generated/workspace/python/external_consumer_profile.json").read_text(encoding="utf-8"))
    candidate = next(entry for entry in profile["operations"] if entry["external_consumption"]["status"] != "internal")
    monkeypatch.setattr(client, "external_consumer_profile", lambda: profile)
    monkeypatch.setattr(
        client,
        "external_operation_conformance_receipts",
        lambda: _readiness_conformance_receipt_store(profile, candidate),
    )
    client.require_operations([candidate["id"]], allow_runtime_backed=True)
    payload = client.invoke_json(
        ["summary"],
        target=ROOT,
        executable=[sys.executable, str(ROOT / "scripts/run_agentic_workspace.py")],
    )
    assert payload


def test_generated_python_client_resolves_config_local_cli_invoke(tmp_path: Path) -> None:
    client = _python_client()
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    config_dir = tmp_path / ".agentic-workspace"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text(
        'schema_version = 1\n[workspace]\ncli_invoke = "agentic-workspace"\n',
        encoding="utf-8",
    )
    local_command = f"{Path(sys.executable).as_posix()} {(ROOT / 'scripts/run_agentic_workspace.py').as_posix()}"
    (config_dir / "config.local.toml").write_text(
        "schema_version = 1\n[workspace]\ncli_invoke = " + json.dumps(local_command) + "\n",
        encoding="utf-8",
    )

    assert client.resolve_invocation(tmp_path) == [Path(sys.executable).as_posix(), (ROOT / "scripts/run_agentic_workspace.py").as_posix()]
    payload = client.invoke_json(["config", "--verbose"], target=tmp_path)

    assert local_command in json.dumps(payload)


def test_python_client_fails_closed_for_unknown_operation() -> None:
    with pytest.raises(ValueError, match="does.not.exist"):
        _python_client().require_operations(["does.not.exist"])


def test_typescript_client_public_export_reads_profile() -> None:
    script = "import { externalConsumerProfile } from './generated/workspace/typescript/src/client.mjs'; console.log(externalConsumerProfile().schema_version);"
    completed = subprocess.run(["node", "--input-type=module", "--eval", script], cwd=ROOT, text=True, capture_output=True, check=False)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "agentic-workspace/external-consumer-profile/v1"


def test_typescript_assignment_patch_paths_parse_quoted_headers_without_backtracking() -> None:
    script = r"""
import { assignmentPatchPaths } from './src/agentic_workspace/contracts/typescript_primitive_support.mjs';
const valid = 'diff --git "a/src/feature file.py" "b/src/feature file.py"';
const sizes = [1, 10, 1000, 50000];
const adversarial = sizes.map((size) => assignmentPatchPaths('diff --git "' + '\\!'.repeat(size) + ' a/unterminated'));
console.log(JSON.stringify({adversarial, valid: assignmentPatchPaths(valid)}));
"""
    completed = subprocess.run(
        ["node", "--input-type=module", "--eval", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "adversarial": [[], [], [], []],
        "valid": ["src/feature file.py"],
    }
    support = (ROOT / "src/agentic_workspace/contracts/typescript_primitive_support.mjs").read_text(encoding="utf-8")
    parser = support.split("function diffGitPathTokens(line) {", 1)[1].split("\n}\n\nexport function assignmentPatchPaths", 1)[0]
    assert "while (offset < value.length)" in parser
    assert parser.count("offset += 1") == 5
    assert ".match(" not in parser and ".exec(" not in parser


def test_generated_clients_share_fail_closed_readiness_contract() -> None:
    python_report = _python_client().external_readiness_report(["assignment.export", "does.not.exist"])
    script = "import { externalReadinessReport } from './generated/workspace/typescript/src/client.mjs'; console.log(JSON.stringify(externalReadinessReport(['assignment.export', 'does.not.exist'])));"
    completed = subprocess.run(["node", "--input-type=module", "--eval", script], cwd=ROOT, text=True, capture_output=True, check=False)
    assert completed.returncode == 0, completed.stderr
    assert python_report == json.loads(completed.stdout)


def test_packed_typescript_client_loads_and_enforces_shipped_constraints(tmp_path: Path) -> None:
    completed = subprocess.run(
        [shutil.which("npm") or shutil.which("npm.cmd") or "npm", "pack", "--json", "--pack-destination", str(tmp_path)],
        cwd=ROOT / "generated/workspace/typescript",
        text=True,
        capture_output=True,
    )
    assert completed.returncode == 0, completed.stderr
    with tarfile.open(tmp_path / json.loads(completed.stdout)[0]["filename"]) as archive:
        archive.extractall(tmp_path, filter="data")
    script = "import {invokeOperation} from './package/src/client.mjs'; try { invokeOperation('delegation-outcome.append',{delegation_target:'',task_class:'',outcome:'success'},{target:'.',allowRuntimeBacked:true}); } catch(e) { console.log(e.kind); }"
    loaded = subprocess.run(["node", "--input-type=module", "--eval", script], cwd=tmp_path, text=True, capture_output=True)
    assert loaded.returncode == 0, loaded.stderr
    assert loaded.stdout.strip() == "malformed"


def test_packed_python_client_loads_external_readiness_without_source_checkout(tmp_path: Path) -> None:
    wheel_dir = tmp_path / "wheels"
    site_dir = tmp_path / "site"
    build = subprocess.run(
        [shutil.which("uv") or shutil.which("uv.exe") or "uv", "build", "--wheel", "--out-dir", str(wheel_dir)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert build.returncode == 0, build.stderr
    wheel = next(wheel_dir.glob("agentic_workspace-*.whl"))
    install = subprocess.run(
        [
            shutil.which("uv") or shutil.which("uv.exe") or "uv",
            "pip",
            "install",
            "--python",
            sys.executable,
            "--no-deps",
            "--target",
            str(site_dir),
            str(wheel),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert install.returncode == 0, install.stderr
    install_jsonschema = subprocess.run(
        [
            shutil.which("uv") or shutil.which("uv.exe") or "uv",
            "pip",
            "install",
            "--python",
            sys.executable,
            "--target",
            str(site_dir),
            "jsonschema",
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert install_jsonschema.returncode == 0, install_jsonschema.stderr
    script = f"""
import json
import sys
from pathlib import Path

site = Path({str(site_dir)!r})
root = Path({str(ROOT)!r}).resolve()
sys.path = [str(site)] + [item for item in sys.path if str(root) not in str(Path(item or '.').resolve())]
import agentic_workspace

report = agentic_workspace.external_readiness_report(['does.not.exist'])
print(json.dumps({{'module': agentic_workspace.__file__, 'status': report['status'], 'missing': report['excluded_operations'][0]['missing_evidence']}}))
"""
    loaded = subprocess.run(
        [shutil.which("uv") or shutil.which("uv.exe") or "uv", "run", "--project", str(ROOT), "python", "-c", script],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert loaded.returncode == 0, loaded.stderr
    payload = json.loads(loaded.stdout)
    assert str(ROOT) not in payload["module"]
    assert payload["status"] == "not-ready"
    assert "released-python-resource" in payload["missing"]


def test_typescript_client_fails_closed_and_detects_workspace() -> None:
    script = """
import { AWClientError, detectWorkspace, requireOperations } from './generated/workspace/typescript/src/client.mjs';
const state = detectWorkspace('.');
let kind = '';
try { requireOperations(['does.not.exist']); } catch (error) { if (error instanceof AWClientError) kind = error.kind; }
console.log(JSON.stringify({ status: state.status, kind }));
"""
    completed = subprocess.run(["node", "--input-type=module", "--eval", script], cwd=ROOT, text=True, capture_output=True, check=False)
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {"status": "enabled", "kind": "incompatible"}


def test_typescript_client_resolves_config_local_cli_invoke(tmp_path: Path) -> None:
    config_dir = tmp_path / ".agentic-workspace"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text(
        'schema_version = 1\n[workspace]\ncli_invoke = "agentic-workspace"\n',
        encoding="utf-8",
    )
    local_command = f"{Path(sys.executable).as_posix()} {(ROOT / 'scripts/run_agentic_workspace.py').as_posix()}"
    (config_dir / "config.local.toml").write_text(
        "schema_version = 1\n[workspace]\ncli_invoke = " + json.dumps(local_command) + "\n",
        encoding="utf-8",
    )
    script = f"""
import {{ detectWorkspace, resolveInvocation }} from './generated/workspace/typescript/src/client.mjs';
const target = {json.dumps(str(tmp_path))};
console.log(JSON.stringify({{ state: detectWorkspace(target), command: resolveInvocation(target) }}));
"""
    completed = subprocess.run(["node", "--input-type=module", "--eval", script], cwd=ROOT, text=True, capture_output=True)
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["state"]["status"] == "enabled"
    assert payload["state"]["config"] == "config.local.toml"
    assert payload["command"] == [Path(sys.executable).as_posix(), (ROOT / "scripts/run_agentic_workspace.py").as_posix()]


def test_typescript_invokes_same_schema_valid_operation_as_python() -> None:
    script = f"""
import {{ invokeOperation }} from './generated/workspace/typescript/src/client.mjs';
const payload = invokeOperation('config.report', {{}}, {{ target: {json.dumps(str(ROOT))}, invocation: [{json.dumps(sys.executable)}, {json.dumps(str(ROOT / "scripts/run_agentic_workspace.py"))}], allowRuntimeBacked: true }});
console.log(JSON.stringify({{ kind: payload.kind, additivePreserved: Object.keys(payload).length > 4 }}));
"""
    completed = subprocess.run(["node", "--input-type=module", "--eval", script], cwd=ROOT, text=True, capture_output=True, check=False)
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {"kind": "agentic-workspace/config-tiny/v1", "additivePreserved": True}


def test_public_python_client_detects_and_resolves_workspace(tmp_path: Path) -> None:
    assert detect_workspace(tmp_path)["status"] == "absent"
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_text('[workspace]\ncli_invoke = "uv run agentic-workspace"\n', encoding="utf-8")
    assert detect_workspace(tmp_path)["status"] == "enabled"
    assert resolve_invocation(tmp_path) == ["uv", "run", "agentic-workspace"]


def test_public_clients_detect_exact_version_incompatibility(tmp_path: Path) -> None:
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_text('[workspace]\nenabled = true\n\n[cli_compatibility]\nexact_version = "999.0.0"\n', encoding="utf-8")

    python_state = detect_workspace(tmp_path)
    assert python_state["status"] == "incompatible"
    assert python_state["reason"] == "exact-client-version-mismatch"

    script = f"""
import {{ detectWorkspace }} from './generated/workspace/typescript/src/client.mjs';
console.log(JSON.stringify(detectWorkspace({json.dumps(str(tmp_path))})));
"""
    completed = subprocess.run(["node", "--input-type=module", "--eval", script], cwd=ROOT, text=True, capture_output=True)
    assert completed.returncode == 0, completed.stderr
    typescript_state = json.loads(completed.stdout)
    assert typescript_state["status"] == "incompatible"
    assert typescript_state["reason"] == "exact-client-version-mismatch"


def test_public_requirement_negotiation_rejects_unknown_status() -> None:
    with pytest.raises(AWClientError) as exc:
        require_operations(["does.not.exist"])
    assert exc.value.kind == "incompatible"


def test_public_operation_client_invokes_by_operation_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    profile = copy.deepcopy(public_client.external_consumer_profile())
    candidate = next(entry for entry in profile["operations"] if entry["id"] == "config.report")
    monkeypatch.setattr(public_client, "external_consumer_profile", lambda: profile)
    monkeypatch.setattr(
        public_client,
        "external_operation_conformance_receipts",
        lambda: _readiness_conformance_receipt_store(profile, candidate),
    )
    payload = invoke_operation(
        "config.report",
        {},
        target=ROOT,
        invocation=[sys.executable, str(ROOT / "scripts/run_agentic_workspace.py")],
        allow_runtime_backed=True,
    )
    assert payload["kind"] == "agentic-workspace/config-tiny/v1"


def test_assignment_lifecycle_operations_are_declared_but_not_ready_without_receipts() -> None:
    operation_ids = [
        "assignment.dispatch",
        "assignment.export",
        "assignment.import",
        "assignment.admit",
        "assignment.reject",
        "assignment.repair",
        "assignment.reassign",
        "assignment.integrate",
        "assignment.close",
        "assignment.cleanup",
        "assignment.override",
    ]
    with pytest.raises(AWClientError) as excinfo:
        require_operations(operation_ids, allow_runtime_backed=True)
    assert excinfo.value.kind == "incompatible"
    assert all("executed-conformance-receipt" in item["missing_evidence"] for item in excinfo.value.details["requirements"])
    statuses = {
        entry["identity"]: entry["external_consumption"]["status"]
        for entry in external_contract_bundle()["operations"].values()
        if entry["identity"] in operation_ids
    }
    assert set(statuses) == set(operation_ids)
    assert set(statuses.values()) == {"runtime-backed"}


def test_assignment_dispatch_public_operation_rejects_missing_current_authority(tmp_path: Path) -> None:
    (tmp_path / ".agentic-workspace").mkdir()
    (tmp_path / ".agentic-workspace/config.toml").write_text(
        'schema_version = 1\n[workspace]\ncli_invoke = "agentic-workspace"\n', encoding="utf-8"
    )

    result = assignment_dispatch(
        {
            "assignment_id": "missing-assignment",
            "assignment_revision": "revision-1",
            "target_name": "planner",
            "run_id": "run-1",
            "transport": "cli",
        },
        target=tmp_path,
        invocation=[sys.executable, str(ROOT / "scripts/run_agentic_workspace.py")],
    )

    assert result["operation_id"] == "assignment.dispatch"
    assert result["transition"] == "dispatch"
    assert result["status"] == "blocked"
    assert result["mutation_applied"] is False
    assert result["reason_code"] == "missing-current-authority"


def test_assignment_lifecycle_generated_wrappers_persist_local_artifacts(tmp_path: Path) -> None:
    from agentic_workspace import workspace_runtime_core

    (tmp_path / ".agentic-workspace").mkdir()
    (tmp_path / ".agentic-workspace/config.toml").write_text(
        'schema_version = 1\n[workspace]\ncli_invoke = "agentic-workspace"\n', encoding="utf-8"
    )
    invocation = [sys.executable, str(ROOT / "scripts/run_agentic_workspace.py")]
    assignment_gate = {
        "status": "handoff-required",
        "assignment_policy": "required-best-fit",
        "selected_target": "planner",
        "required_next_action": "prepare-assigned-handoff",
        "target_identity_ref": "target:planner@2026-07-21",
        "task_class": "mechanical-follow-through",
        "scope_class": "narrow-code-change",
        "plan_ref": ".agentic-workspace/planning/execplans/plan.plan.json",
        "plan_revision": "plan-rev-1",
        "slice_id": "slice-1",
        "slice_revision": "slice-rev-1",
        "assignment_decision_revision": "assignment-rev-1",
        "role": "implementer",
        "human_intent": "Implement the bounded feature change.",
        "allowed_effects": ["repo-write"],
        "allowed_paths": ["src/feature.py"],
        "required_inputs": ["current checkout"],
        "read_first": ["src/feature.py", "summary:planning_record"],
        "proof_obligation": {
            "kind": "agentic-workspace/assignment-task-proof-obligation/v1",
            "id": "proof:feature",
            "revision": "proof-rev-1",
            "subject": {"assignment_id": "assign-1", "run_id": "run-1"},
        },
        "stop_conditions": ["scope-expanded"],
        "mutation_baseline": "baseline-1",
    }
    assignment_policy = {"manual_transport_policy": {"value": "allowed"}}
    delegation_decision = {
        "decision": "assignment-handoff-required",
        "delegation_next_step": {
            "execution_methods": ["manual"],
            "handoff_run_id": "run-1",
            "return_schema": "delegated-return/v1",
        },
    }
    identity = workspace_runtime_core._assignment_identity_payload(
        assignment_gate=assignment_gate,
        assignment_policy=assignment_policy,
        delegation_decision=delegation_decision,
    )
    assignment_dir = tmp_path / ".agentic-workspace/planning/assignments"
    assignment_dir.mkdir(parents=True)
    proof_dir = tmp_path / ".agentic-workspace/proof/receipts"
    proof_dir.mkdir(parents=True)
    baseline_file = tmp_path / ".agentic-workspace/planning/mutation-baseline.json"
    baseline_file.parent.mkdir(parents=True, exist_ok=True)
    feature_path = tmp_path / "src/feature.py"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    feature_path.write_text("old\n", encoding="utf-8")
    proof_ref = ".agentic-workspace/proof/receipts/proof-feature.json"
    structural_proof_receipt = {
        "kind": "agentic-workspace/assignment-structural-proof-receipt/v1",
        "result": "passed",
        "verified_by": "aw",
        "assignment_revision": identity["revision"],
    }
    (tmp_path / proof_ref).write_text(json.dumps(structural_proof_receipt), encoding="utf-8")
    baseline_file.write_text(json.dumps({"current_baseline": "baseline-1"}), encoding="utf-8")
    (assignment_dir / "assign-1.assignment.json").write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/planning-assignment/v1",
                "assignment_id": "assign-1",
                "current_revision": identity["revision"],
                "status": "current",
                "target_name": "planner",
                "assignment_gate": assignment_gate,
                "assignment_policy": assignment_policy,
                "delegation_decision": delegation_decision,
                "structural_proof_receipt_ref": proof_ref,
                "current_attempt": {"run_id": "run-1", "owner": "planner", "status": "handoff-prepared"},
                "accepted_result_refs": [],
            }
        ),
        encoding="utf-8",
    )
    export = assignment_export(
        {
            "assignment_id": "assign-1",
            "assignment_revision": identity["revision"],
            "target_name": "planner",
            "run_id": "run-1",
        },
        target=tmp_path,
        invocation=invocation,
    )
    malformed = assignment_import(
        {
            "run_id": "run-1",
            "return_json": json.dumps(
                {"assignment_revision": identity["revision"], "target": "planner", "changed_paths": ["src/feature.py"]}
            ),
        },
        target=tmp_path,
        invocation=invocation,
    )
    missing_patch = assignment_import(
        {
            "run_id": "run-1",
            "return_json": json.dumps(
                {
                    "assignment_revision": identity["revision"],
                    "run_id": "run-1",
                    "target": "planner",
                    "changed_paths": ["src/feature.py"],
                    "summary": "Claimed implementation without a patch.",
                    "stop_conditions_hit": [],
                    "patch": " \n",
                }
            ),
        },
        target=tmp_path,
        invocation=invocation,
    )
    imported = assignment_import(
        {
            "run_id": "run-1",
            "return_json": json.dumps(
                {
                    "assignment_revision": identity["revision"],
                    "run_id": "run-1",
                    "target": "planner",
                    "changed_paths": ["src/feature.py"],
                    "summary": "Implemented the bounded feature change.",
                    "stop_conditions_hit": [],
                    "patch": "diff --git a/src/feature.py b/src/feature.py\n--- a/src/feature.py\n+++ b/src/feature.py\n@@ -1 +1 @@\n-old\n+new\n",
                }
            ),
        },
        target=tmp_path,
        invocation=invocation,
    )
    unrelated_proof_ref = ".agentic-workspace/proof/receipts/unrelated-proof.json"
    (tmp_path / unrelated_proof_ref).write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/proof-receipt/v1",
                "command": "pytest tests/test_feature.py",
                "result": "passed",
                "recorded_at": "2026-08-27T12:00:00+00:00",
                "changed_paths": ["src/feature.py"],
            }
        ),
        encoding="utf-8",
    )
    premature_close = assignment_close(
        {"run_id": "run-1", "task_proof_receipt_ref": unrelated_proof_ref},
        target=tmp_path,
        invocation=invocation,
    )
    assert premature_close["status"] == "blocked"
    still_current = json.loads((assignment_dir / "assign-1.assignment.json").read_text(encoding="utf-8"))
    assert still_current["status"] == "current"
    blocked = assignment_integrate(
        {"run_id": "run-1"},
        target=tmp_path,
        invocation=invocation,
    )
    admitted = assignment_admit(
        {"run_id": "run-1"},
        target=tmp_path,
        invocation=invocation,
    )
    integrated = assignment_integrate(
        {"run_id": "run-1"},
        target=tmp_path,
        invocation=invocation,
    )
    assert integrated["status"] == "integrated", integrated["failures"]
    proof_command = "python -c \"print('assignment proof passed')\""
    proof_result = workspace_runtime_core._record_proof_receipt_payload(
        target_root=tmp_path,
        command=proof_command,
        result="passed",
        changed_paths=["src/feature.py"],
        task_text="Implement the bounded feature change",
    )
    task_proof_ref = proof_result["trusted_producer_receipt_ref"]
    close_action = workspace_runtime_core._assignment_primary_action_payload(
        target_root=tmp_path,
        assignment_policy={
            "execution_role": {"value": "orchestrator"},
            "assignment_policy": {"value": "required-best-fit"},
        },
        assignment_decision={"decision": "assign-best-fit", "assignment_decision_revision": "assignment-rev-1"},
        assignment_gate={
            "status": "handoff-required",
            "implementation_allowed": False,
            "selected_target": "planner",
            "target_identity_ref": "target:planner@2026-07-21",
        },
        selected_target={"name": "planner", "execution_methods": ["manual"]},
        delegation_control={"execution_permitted": False},
        cli_invoke="agentic-workspace",
    )
    assert close_action["operation_invocation"]["operation_id"] == "assignment.close"
    assert close_action["operation_invocation"]["arguments"]["task_proof_receipt_ref"] == task_proof_ref
    wrong_task_proof_ref = ".agentic-workspace/proof/receipts/wrong-task-proof.json"
    indexed_task_proof_path = proof_dir / f"{task_proof_ref.rsplit('/', 1)[-1]}.json"
    wrong_task_proof = json.loads(indexed_task_proof_path.read_text(encoding="utf-8"))
    wrong_task_proof["assignment_proof_obligation"] = {
        **assignment_gate["proof_obligation"],
        "revision": "stale-proof-revision",
    }
    (tmp_path / wrong_task_proof_ref).write_text(json.dumps(wrong_task_proof), encoding="utf-8")
    typescript_wrong_close = subprocess.run(
        [
            "node",
            str(ROOT / "generated/workspace/typescript/src/cli.mjs"),
            "assignment",
            "close",
            "--target",
            str(tmp_path),
            "--run-id",
            "run-1",
            "--task-proof-receipt-ref",
            wrong_task_proof_ref,
            "--format",
            "json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert typescript_wrong_close.returncode == 0, typescript_wrong_close.stderr
    assert json.loads(typescript_wrong_close.stdout)["status"] == "blocked"
    wrong_proof_close = assignment_close(
        {"run_id": "run-1", "task_proof_receipt_ref": wrong_task_proof_ref},
        target=tmp_path,
        invocation=invocation,
    )
    assert wrong_proof_close["status"] == "blocked"
    closed = assignment_close(
        {"run_id": "run-1", "task_proof_receipt_ref": task_proof_ref},
        target=tmp_path,
        invocation=invocation,
    )
    assert closed["status"] == "closed"
    reopened_assignment = json.loads((assignment_dir / "assign-1.assignment.json").read_text(encoding="utf-8"))
    reopened_assignment["status"] = "current"
    reopened_assignment["current_attempt"]["status"] = "integrated"
    (assignment_dir / "assign-1.assignment.json").write_text(json.dumps(reopened_assignment), encoding="utf-8")
    state_path = tmp_path / ".agentic-workspace/local/assignment-runs/run-1/state.json"
    reopened_state = json.loads(state_path.read_text(encoding="utf-8"))
    reopened_state["current_state"] = "integrated"
    state_path.write_text(json.dumps(reopened_state), encoding="utf-8")
    typescript_closed = subprocess.run(
        [
            "node",
            str(ROOT / "generated/workspace/typescript/src/cli.mjs"),
            "assignment",
            "close",
            "--target",
            str(tmp_path),
            "--run-id",
            "run-1",
            "--task-proof-receipt-ref",
            task_proof_ref,
            "--format",
            "json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert typescript_closed.returncode == 0, typescript_closed.stderr
    assert json.loads(typescript_closed.stdout)["status"] == "closed"
    override = assignment_override(
        {"assignment_id": "assign-1", "reason": "maintainer approved", "scope": "src/feature.py", "expires_at": "2026-07-23T00:00:00Z"},
        target=tmp_path,
        invocation=invocation,
    )

    assert export["status"] == "handoff-prepared"
    assert malformed["status"] == "blocked"
    assert malformed["reason_code"] == "malformed-return"
    assert missing_patch["status"] == "blocked"
    assert missing_patch["reason_code"] == "malformed-return"
    assert imported["status"] == "awaiting-admission"
    assert blocked["reason_code"] == "return-not-admitted"
    assert admitted["status"] == "admitted"
    assert integrated["status"] == "integrated"
    closed_assignment = json.loads((assignment_dir / "assign-1.assignment.json").read_text(encoding="utf-8"))
    assert closed_assignment["status"] == "closed"
    assert closed_assignment["current_attempt"]["status"] == "closed"
    assert override["status"] == "override-recorded"
    assert (tmp_path / ".agentic-workspace/local/assignment-runs/run-1/received/awaiting-admission").is_dir()
    override_ref = next(ref for ref in override["artifact_refs"] if ref.endswith("override/override.json"))
    override_receipt = json.loads((tmp_path / override_ref).read_text())
    assert override_receipt["claim_effect"] == "downgrade-until-revalidated"
    packet_ref = next(ref for ref in export["artifact_refs"] if ref.endswith("export/packet.json"))
    packet = json.loads((tmp_path / packet_ref).read_text())
    assert packet["authority_refs"]["planning_assignment"] == ".agentic-workspace/planning/assignments/assign-1.assignment.json"
    assert packet["dispatch_contract"]["semantic_authority"] == "assignment_identity"
    assert packet["dispatch_contract"]["silent_local_fallback_allowed"] is False
    assert packet["return_contract"]["worker_completion_authority"] is False
    assert packet["assignment_identity"]["claim_authority"]["completion"] == "orchestrator-owned"
    assert packet["worker_context"]["intent"]["outcome"] == "Implement the bounded feature change."
    assert packet["worker_context"]["scope"]["allowed_paths"] == ["src/feature.py"]
    assert packet["worker_context"]["inputs"]["read_first"] == ["src/feature.py", "summary:planning_record"]
    assert packet["worker_context"]["authority"]["scope_widening_allowed"] is False
    prompt_ref = next(ref for ref in export["artifact_refs"] if ref.endswith("export/prompt.md"))
    prompt = (tmp_path / prompt_ref).read_text(encoding="utf-8")
    assert '"kind": "agentic-workspace/assignment-worker-context/v1"' in prompt
    assert "dispatch_adapter" not in prompt
    assert "authority_refs" not in prompt
    assert "current_authorities" not in export["state"]


def test_assignment_lifecycle_public_admit_rejects_caller_authority_strings(tmp_path: Path) -> None:
    (tmp_path / ".agentic-workspace").mkdir()
    (tmp_path / ".agentic-workspace/config.toml").write_text(
        'schema_version = 1\n[workspace]\ncli_invoke = "agentic-workspace"\n', encoding="utf-8"
    )
    invocation = [sys.executable, str(ROOT / "scripts/run_agentic_workspace.py")]
    with pytest.raises(AWClientError) as excinfo:
        assignment_admit(
            {"run_id": "run-1", "current_authority_ref": "planning:rev", "live_mutation_baseline": "baseline-1"},
            target=tmp_path,
            invocation=invocation,
        )

    assert excinfo.value.kind == "malformed"
    assert "current_authority_ref" in excinfo.value.details["errors"][0]
    assert "live_mutation_baseline" in excinfo.value.details["errors"][0]


def test_assignment_lifecycle_public_contract_omits_caller_authority_inputs() -> None:
    authority_inputs = {
        "assignment_gate_json",
        "assignment_policy_json",
        "delegation_decision_json",
        "aw_proof_receipt_json",
        "run_state_json",
        "current_authority_ref",
        "live_mutation_baseline",
        "packet_json",
    }
    for operation in external_contract_bundle()["operations"].values():
        if not operation["identity"].startswith("assignment."):
            continue
        input_names = {entry["name"] for entry in operation["contract"]["inputs"]}
        assert not authority_inputs & input_names


def test_independent_review_import_uses_protected_host_store_and_append_preserves_indexes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first_ref, _first_host, first_resolver = _independent_review_host_result_fixture(tmp_path)
    second_ref, _second_host, second_resolver = _independent_review_host_result_fixture(
        tmp_path,
        changed_paths=["src/other.py"],
        assignment_id="assign-2",
        assignment_revision="assignment-rev-2",
        proof_subject_revision="proof-rev-2",
        review_revision="review-rev-2",
    )

    with _verified_host_fixture(monkeypatch, first_ref):
        first = record_trusted_independent_review_result(
            target_root=tmp_path,
            review_result={"host_result_ref": first_ref},
        )
        replay = record_trusted_independent_review_result(
            target_root=tmp_path,
            review_result={"host_result_ref": first_ref},
        )
    with _verified_host_fixture(monkeypatch, second_ref):
        second = record_trusted_independent_review_result(
            target_root=tmp_path,
            review_result={"host_result_ref": second_ref},
        )
    with pytest.raises(WorkspaceUsageError, match="caller-provided independent review host result resolvers are rejected"):
        record_trusted_independent_review_result(
            target_root=tmp_path,
            review_result={"host_result_ref": first_ref},
            host_result_resolver=first_resolver,
        )

    assert replay["result_ref"] == first["result_ref"]
    host_index = json.loads((tmp_path / INDEPENDENT_REVIEW_HOST_RESULT_DIR / "index.json").read_text(encoding="utf-8"))
    trusted_index = json.loads((tmp_path / INDEPENDENT_REVIEW_RESULT_DIR / "index.json").read_text(encoding="utf-8"))
    assert host_index["kind"] == INDEPENDENT_REVIEW_HOST_RESULT_INDEX_KIND
    assert set(host_index["results"]) == {
        first_ref.removeprefix("independent-review-host-result:"),
        second_ref.removeprefix("independent-review-host-result:"),
    }
    assert trusted_index["kind"] == INDEPENDENT_REVIEW_RESULT_INDEX_KIND
    assert len(trusted_index["results"]) == 2
    assert first["status"] == "stored"
    assert second["status"] == "stored"


def test_independent_review_import_rejects_caller_written_host_file_without_resolver(tmp_path: Path) -> None:
    host_id = "caller-authored"
    host_ref = f"independent-review-host-result:{host_id}"
    host_result = {"kind": "agentic-workspace/independent-review-host-result/v1", "status": "current", "host_result_ref": host_ref}
    old_path = tmp_path / ".agentic-workspace/local/independent-review-host-results" / f"{host_id}.json"
    old_path.parent.mkdir(parents=True, exist_ok=True)
    old_path.write_text(json.dumps(host_result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(WorkspaceUsageError, match="protected host-result index"):
        record_trusted_independent_review_result(target_root=tmp_path, review_result={"host_result_ref": host_ref})

    assert not (tmp_path / INDEPENDENT_REVIEW_RESULT_DIR / "index.json").exists()


def test_assignment_admit_host_result_ref_succeeds_with_protected_host_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    host_ref, _host_result, _resolver = _independent_review_host_result_fixture(tmp_path)

    with _verified_host_fixture(monkeypatch, host_ref):
        admitted = admit_independent_review_result_operation(
            target_root=tmp_path,
            values={"host_result_ref": host_ref, "required_mode": "separate-actor"},
            changed_paths=["src/feature.py"],
        )

    assert admitted["status"] == "admitted"
    assert admitted["receipt"]["review_result"]["custody"]["host_result_ref"] == host_ref


def test_assignment_admit_preserves_explicit_empty_independent_review_scope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    host_ref, host_result, _resolver = _independent_review_host_result_fixture(tmp_path, changed_paths=[])

    assert host_result["review_result"]["changed_paths"] == []
    assert host_result["review_result"]["scope_digest"] == _independent_review_scope_digest([])
    with _verified_host_fixture(monkeypatch, host_ref):
        admitted = admit_independent_review_result_operation(
            target_root=tmp_path,
            values={"host_result_ref": host_ref, "required_mode": "separate-actor"},
            changed_paths=[],
        )

    assert admitted["status"] == "admitted"
    assert admitted["receipt"]["changed_paths"] == []
    assert admitted["receipt"]["scope_digest"] == _independent_review_scope_digest([])


def test_correction_event_generated_operations_store_query_and_preserve_low_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".agentic-workspace").mkdir()
    (tmp_path / ".agentic-workspace/config.toml").write_text(
        'schema_version = 1\n[workspace]\ncli_invoke = "agentic-workspace"\n', encoding="utf-8"
    )
    (tmp_path / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'current_target = "user-local:fast-worker"',
                "",
                "[local_memory]",
                "target_guidance_enabled = true",
                'user_guidance_root = "~/.agentic-workspace/target-guidance"',
                'correction_events_path = ".agentic-workspace/local/correction-events.json"',
                "",
                "[delegation_targets.fast_worker]",
                'target_id = "user-local:fast-worker"',
                'target_revision = "rev-1"',
                'aliases = ["fast"]',
                'revision_policy = "preserve"',
                'strength = "strong"',
                'execution_methods = ["internal"]',
            ]
        ),
        encoding="utf-8",
    )
    invocation = [sys.executable, str(ROOT / "scripts/run_agentic_workspace.py")]
    event = {
        "delivery_id": "delivery-1",
        "target_identity_ref": "fast",
        "target_revision": "rev-1",
        "task_class": "mechanical-follow-through",
        "scope_class": "narrow-code-change",
        "phase": "proof",
        "subsystem": "workspace-runtime",
        "surface": "final-response",
        "invariant_id": "narrow-edits",
        "behavior_class": "edit-scope",
        "desired_behavior": "Prefer narrow edits.",
        "replaced_behavior": "Broad edits.",
        "source_ref": "review-thread-1",
        "evidence_hash": "sha256:review-thread-1",
        "route_decisions": ["target-guidance", "target-suitability"],
    }
    from agentic_workspace.agent_guidance import record_trusted_authority_receipt

    host_event = _trusted_guidance_host_event(
        tmp_path,
        authority="pr-review",
        producer_class="human-reviewer",
        producer_id="reviewer-1",
        source="github-review",
        source_ref="review-thread-1",
        host_admission_monkeypatch=monkeypatch,
        target_revision="rev-1",
    )
    receipt_ref = record_trusted_authority_receipt(
        target_root=tmp_path,
        authority="pr-review",
        producer_class="human-reviewer",
        producer_id="reviewer-1",
        source="github-review",
        source_ref="review-thread-1",
        target_revision="rev-1",
        host_event_ref=host_event["event_ref"],
    )["receipt_ref"]

    submitted = correction_event_submit(
        {"event_json": json.dumps(event), "trusted_authority_receipt_ref": receipt_ref},
        target=tmp_path,
        invocation=invocation,
    )
    low_authority = correction_event_submit(
        {"event_json": json.dumps({**event, "delivery_id": "delivery-2", "source_ref": "agent-note-1"})},
        target=tmp_path,
        invocation=invocation,
    )
    duplicate_low_authority = correction_event_submit(
        {"event_json": json.dumps({**event, "delivery_id": "delivery-2", "source_ref": "agent-note-1"})},
        target=tmp_path,
        invocation=invocation,
    )
    queried = correction_event_query({}, target=tmp_path, invocation=invocation)
    compacted = correction_event_prune_compact({}, target=tmp_path, invocation=invocation)

    assert submitted["status"] == "stored"
    assert submitted["admitted_event_count"] == 1
    assert low_authority["status"] == "stored"
    assert low_authority["low_authority_event_count"] == 1
    assert duplicate_low_authority["status"] == "stored"
    assert duplicate_low_authority["mutation_applied"] is False
    assert duplicate_low_authority["low_authority_event_count"] == 1
    assert low_authority["admission"]["derived_routes"]["low_authority"]
    low_authority_ids = set(low_authority["admission"]["derived_routes"]["low_authority"])
    assert low_authority_ids.isdisjoint(low_authority["admission"]["derived_routes"]["target_guidance"])
    assert queried["admitted_event_count"] == 1
    assert queried["low_authority_event_count"] == 1
    assert compacted["status"] == "compacted"
    assert (tmp_path / ".agentic-workspace/local/correction-events.json").is_file()
    assert submitted["receipt_ref"].startswith(".agentic-workspace/local/correction-event-receipts/")


def test_correction_event_query_filters_full_low_authority_context(tmp_path: Path) -> None:
    (tmp_path / ".agentic-workspace").mkdir()
    (tmp_path / ".agentic-workspace/config.toml").write_text("schema_version = 1\n", encoding="utf-8")
    (tmp_path / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation_targets.fast_worker]",
                'target_id = "user-local:fast-worker"',
                'target_revision = "rev-1"',
                'aliases = ["fast"]',
                'strength = "strong"',
                'execution_methods = ["internal"]',
            ]
        ),
        encoding="utf-8",
    )
    from agentic_workspace.agent_guidance import apply_correction_event_operation

    context = {
        "target_identity_ref": "fast",
        "target_revision": "rev-1",
        "task_class": "code-change",
        "scope_class": "narrow",
        "phase": "proof",
        "subsystem": "workspace-runtime",
        "surface": "final-response",
    }
    submitted = apply_correction_event_operation(
        target_root=tmp_path,
        operation_id="correction-event.submit",
        values={
            **context,
            "delivery_id": "delivery-context-1",
            "source_ref": "agent-context-1",
            "desired_behavior": "Use narrow proof.",
            "replaced_behavior": "Use broad proof.",
            "invariant_id": "routed-narrow-proof",
            "behavior_class": "proof-claim",
        },
    )
    matching = apply_correction_event_operation(target_root=tmp_path, operation_id="correction-event.query", values=context)
    unrelated = apply_correction_event_operation(
        target_root=tmp_path,
        operation_id="correction-event.query",
        values={**context, "surface": "proof-receipt"},
    )

    assert submitted["low_authority_event_count"] == 1
    assert matching["low_authority_event_count"] == 1
    assert unrelated["low_authority_event_count"] == 0


def test_signed_host_observation_survives_without_agent_normalization_and_routes_later(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".agentic-workspace").mkdir()
    (tmp_path / ".agentic-workspace/config.toml").write_text("schema_version = 1\n", encoding="utf-8")
    (tmp_path / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation_targets.fast_worker]",
                'target_id = "user-local:fast-worker"',
                'target_revision = "rev-1"',
                'aliases = ["fast"]',
                'strength = "strong"',
                'execution_methods = ["internal"]',
            ]
        ),
        encoding="utf-8",
    )
    from agentic_workspace.agent_guidance import apply_correction_event_operation, unresolved_correction_signals

    host = _trusted_guidance_host_event(
        tmp_path,
        authority="explicit-user-correction",
        producer_class="human",
        producer_id="user-1",
        source_ref="host-conversation:event-42",
        source="explicit-user-correction",
        host_admission_monkeypatch=monkeypatch,
        import_event=False,
        event_fields={"evidence_ref": "host-conversation:event-42#correction", "task_class": "code-change"},
    )
    observed = apply_correction_event_operation(
        target_root=tmp_path,
        operation_id="correction-event.submit",
        values={"trusted_host_event_json": json.dumps(host["event"])},
    )
    replayed = apply_correction_event_operation(
        target_root=tmp_path,
        operation_id="correction-event.submit",
        values={"trusted_host_event_json": json.dumps(host["event"])},
    )

    assert observed["status"] == "pending-normalization"
    assert observed["observation"]["authority"] == "explicit-user-correction"
    assert observed["next_action"]["route_decisions_required"] is False
    assert replayed["mutation_applied"] is False
    assert unresolved_correction_signals(target_root=tmp_path, task="implement code change")[0]["status"] == "pending-normalization"
    assert unresolved_correction_signals(target_root=tmp_path, task="write release notes") == []
    assert not (tmp_path / ".agentic-workspace/local/correction-events.json").exists()

    self_capture = apply_correction_event_operation(
        target_root=tmp_path,
        operation_id="correction-event.submit",
        values={
            "delivery_id": "agent-self-capture-42",
            "target_identity_ref": "fast",
            "source_ref": "agent-note:event-42",
            "desired_behavior": "Use the routed narrow proof.",
            "replaced_behavior": "Use broad proof and overclaim completion.",
            "invariant_id": "routed-narrow-proof",
            "behavior_class": "proof-claim",
            "task_class": "code-change",
            "scope_class": "narrow",
        },
    )
    assert self_capture["low_authority_event_count"] == 1

    normalized = apply_correction_event_operation(
        target_root=tmp_path,
        operation_id="correction-event.submit",
        values={
            "host_event_ref": host["event_ref"],
            "target_identity_ref": "fast",
            "desired_behavior": "Use the routed narrow proof.",
            "replaced_behavior": "Use broad proof and overclaim completion.",
            "invariant_id": "routed-narrow-proof",
            "behavior_class": "proof-claim",
            "task_class": "code-change",
            "scope_class": "narrow",
        },
    )

    assert normalized["status"] == "stored"
    admitted = normalized["admission"]["admitted_events"][0]
    assert admitted["authority_resolution_source"] == "signed-host-observation"
    assert admitted["admission_state"] == "accepted-unrouted"
    assert admitted["routing_state"] == "pending-owner-route"
    assert admitted["recurrence_count"] == 1
    assert normalized["low_authority_event_count"] == 1
    assert unresolved_correction_signals(target_root=tmp_path, task="implement code change")[0]["status"] == "pending-disposition"

    from agentic_workspace.operating_decision import compile_operating_decision

    decision = compile_operating_decision(
        inputs={
            "target_root": str(tmp_path),
            "task": "implement code change",
            "reconciliation": {
                "result": {"status": "succeeded"},
                "intent": {"status": "satisfied"},
                "proof": {"status": "passed"},
            },
        }
    )
    assert decision["future_context_signals"][0]["status"] == "pending-disposition"
    assert decision["reconciliation"]["claim"]["permission"] == "bounded"
    assert decision["reconciliation"]["next_action"]["operation_invocation"]["operation_id"] == "correction-event.submit"

    routed = apply_correction_event_operation(
        target_root=tmp_path,
        operation_id="correction-event.submit",
        values={"event_id": admitted["event_id"], "route_decisions": ["no-retention"]},
    )
    assert routed["admission"]["admitted_events"][0]["routing_state"] == "routed"
    assert unresolved_correction_signals(target_root=tmp_path, task="implement code change") == []


def test_explicit_correction_can_resolve_to_existing_canonical_owner_without_duplicate_memory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".agentic-workspace").mkdir()
    (tmp_path / ".agentic-workspace/config.toml").write_text("schema_version = 1\n", encoding="utf-8")
    (tmp_path / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation_targets.implementer]",
                'target_id = "user-local:implementer"',
                'target_revision = "rev-1"',
                'aliases = ["implementer"]',
                'strength = "strong"',
                'execution_methods = ["internal"]',
            ]
        ),
        encoding="utf-8",
    )
    from agentic_workspace.agent_guidance import (
        apply_correction_event_operation,
        guidance_promotion_from_store,
        record_guidance_remember_receipt,
        unresolved_correction_signals,
    )

    host = _trusted_guidance_host_event(
        tmp_path,
        authority="explicit-user-correction",
        producer_class="human",
        producer_id="user-1",
        source_ref="host-conversation:self-review-correction",
        source="explicit-user-correction",
        host_admission_monkeypatch=monkeypatch,
        import_event=False,
        event_fields={"evidence_ref": "host-conversation:self-review-correction#correction", "task_class": "code-change"},
    )
    observed = apply_correction_event_operation(
        target_root=tmp_path,
        operation_id="correction-event.submit",
        values={"trusted_host_event_json": json.dumps(host["event"])},
    )
    remember = record_guidance_remember_receipt(
        target_root=tmp_path,
        producer_class="human",
        producer_id="user-1",
        source_ref="host-conversation:self-review-correction",
        instruction="Make this correction affect future review decisions.",
        host_event_ref=host["event_ref"],
    )
    incomplete_disposition = apply_correction_event_operation(
        target_root=tmp_path,
        operation_id="correction-event.submit",
        values={
            "host_event_ref": host["event_ref"],
            "target_identity_ref": "implementer",
            "desired_behavior": "Report fixes applied and request independent re-review.",
            "replaced_behavior": "Approve the implementation agent's own PR and claim merge-ready authority.",
            "invariant_id": "implementation-review-separation",
            "behavior_class": "review-authority",
            "task_class": "code-change",
            "scope_class": "code-change",
            "route_decisions": ["canonical-owner"],
            "canonical_owner_ref": "policy:#2264",
        },
    )

    normalized = apply_correction_event_operation(
        target_root=tmp_path,
        operation_id="correction-event.submit",
        values={
            "host_event_ref": host["event_ref"],
            "target_identity_ref": "implementer",
            "desired_behavior": "Report fixes applied and request independent re-review.",
            "replaced_behavior": "Approve the implementation agent's own PR and claim merge-ready authority.",
            "invariant_id": "implementation-review-separation",
            "behavior_class": "review-authority",
            "task_class": "code-change",
            "scope_class": "code-change",
            "route_decisions": ["canonical-owner"],
            "canonical_owner_ref": "policy:#2264",
            "canonical_owner_evidence_ref": "issue:#2725",
            "remember_receipt_ref": remember["receipt_ref"],
        },
    )

    assert observed["status"] == "pending-normalization"
    assert incomplete_disposition["status"] == "blocked"
    assert incomplete_disposition["admission"]["rejected_events"][0]["reason"] == "rejected-missing-canonical-owner-evidence"
    admitted = normalized["admission"]["admitted_events"][0]
    assert admitted["routing_state"] == "routed"
    assert normalized["admission"]["derived_routes"]["canonical_owner"] == [admitted["event_id"]]
    assert unresolved_correction_signals(target_root=tmp_path, task="implement code change") == []

    disposition = guidance_promotion_from_store(target_root=tmp_path, task_class="code-change", scope_class="code-change")
    assert disposition["status"] == "resolved-existing-owner"
    candidate = disposition["guidance"][0]
    assert candidate["status"] == "resolved-existing-owner"
    assert candidate["destination"]["owner_ref"] == "policy:#2264"
    assert candidate["destination"]["owner_evidence_ref"] == "issue:#2725"
    assert candidate["promotion_authority"]["remember_receipt"]["receipt_ref"] == remember["receipt_ref"]
    assert not (tmp_path / ".agentic-workspace/memory/guidance-lifecycle.json").exists()


def test_generated_python_operation_carries_signed_host_observation_without_private_imports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".agentic-workspace").mkdir()
    (tmp_path / ".agentic-workspace/config.toml").write_text("schema_version = 1\n", encoding="utf-8")
    host = _trusted_guidance_host_event(
        tmp_path,
        authority="explicit-user-correction",
        producer_class="human",
        producer_id="user-2",
        source_ref="host-conversation:event-99",
        host_admission_monkeypatch=monkeypatch,
        import_event=False,
    )
    import agentic_workspace.generated_operations as generated
    from agentic_workspace.agent_guidance import apply_correction_event_operation

    def invoke(operation_id: str, values: dict[str, object], **_kwargs: object) -> dict[str, object]:
        return apply_correction_event_operation(target_root=tmp_path, operation_id=operation_id, values=dict(values))

    monkeypatch.setattr(generated, "invoke_operation", invoke)
    result = generated.correction_event_submit(
        {"trusted_host_event_json": json.dumps(host["event"])},
        target=tmp_path,
    )

    assert result["status"] == "pending-normalization"
    assert result["observation"]["event_ref"] == host["event_ref"]


def test_caller_labels_cannot_mint_trusted_host_observation(tmp_path: Path) -> None:
    (tmp_path / ".agentic-workspace").mkdir()
    (tmp_path / ".agentic-workspace/config.toml").write_text("schema_version = 1\n", encoding="utf-8")
    from agentic_workspace.agent_guidance import apply_correction_event_operation

    forged = {
        "kind": "agentic-workspace/trusted-authority-host-event/v1",
        "status": "current",
        "event_ref": "trusted-authority-event:forged",
        "authority": "explicit-user-correction",
        "producer_class": "human",
        "source_ref": "caller-label",
    }
    with pytest.raises(WorkspaceUsageError, match="inputs do not match|not admitted"):
        apply_correction_event_operation(
            target_root=tmp_path,
            operation_id="correction-event.submit",
            values={"trusted_host_event_json": json.dumps(forged)},
        )


def test_correction_event_public_contract_omits_caller_authority_inputs() -> None:
    caller_authority_inputs = {"subjects_json", "trusted_authority_receipt_json"}
    correction_operations = {
        "correction-event.submit",
        "correction-event.query",
        "correction-event.correct-dispute",
        "correction-event.withdraw-supersede",
        "correction-event.prune-compact",
    }
    for operation in external_contract_bundle()["operations"].values():
        if operation["identity"] not in correction_operations:
            continue
        input_names = {entry["name"] for entry in operation["contract"]["inputs"]}
        assert not caller_authority_inputs & input_names
        assert "trusted_authority_receipt_ref" in input_names
        if operation["identity"] in {"correction-event.submit", "correction-event.query"}:
            assert {"phase", "subsystem", "surface"} <= input_names
        if operation["identity"] == "correction-event.submit":
            assert {"trusted_host_event_json", "host_event_ref"} <= input_names


def test_external_contract_bundle_exposes_ir_owned_conformance_profile() -> None:
    conformance = external_contract_bundle()["external_conformance"]

    assert conformance["kind"] == "agentic-workspace/packaged-external-conformance-profile/v1"
    assert conformance["source"] == "operation_conformance_test_ir.json#external_readiness"
    assert conformance["transport_matrix"] == ["cli-json", "python", "typescript", "vendor-neutral"]
    assert conformance["executor_matrix"] == {
        "cli-json": "direct-cli-json",
        "python": "generated-python-client",
        "typescript": "generated-typescript-client",
        "vendor-neutral": "packed-typescript-client",
    }
    assert {
        "config.report",
        "delegation-outcome.append",
    }.issubset({entry["operation_id"] for entry in conformance["operations"]})
    delegation = next(entry for entry in conformance["operations"] if entry["operation_id"] == "delegation-outcome.append")
    assert delegation["case_exceptions"] == {}
    selected = external_conformance_profile(["config.report"])
    assert [entry["operation_id"] for entry in selected["operations"]] == ["config.report"]


def test_generated_typescript_client_selects_packaged_conformance_profile() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required for generated TypeScript client coverage")
    script = """
import { externalConformanceProfile } from './generated/workspace/typescript/src/client.mjs';
const profile = externalConformanceProfile(['delegation-outcome.append']);
console.log(JSON.stringify({ kind: profile.kind, operations: profile.operations.map((item) => item.operation_id) }));
"""
    completed = subprocess.run(
        [node, "--input-type=module", "--eval", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(completed.stdout) == {
        "kind": "agentic-workspace/packaged-external-conformance-profile/v1",
        "operations": ["delegation-outcome.append"],
    }


def test_agent_guidance_generated_lifecycle_operations_are_external_runtime_backed(tmp_path: Path) -> None:
    operation_wrappers = {
        "agent-guidance.delete": agent_guidance_delete,
        "agent-guidance.edit": agent_guidance_edit,
        "agent-guidance.merge": agent_guidance_merge,
        "agent-guidance.promote": agent_guidance_promote,
        "agent-guidance.retire": agent_guidance_retire,
        "agent-guidance.revalidate": agent_guidance_revalidate,
        "agent-guidance.split": agent_guidance_split,
        "agent-guidance.supersede": agent_guidance_supersede,
        "agent-guidance.suppress": agent_guidance_suppress,
        "agent-guidance.weaken": agent_guidance_weaken,
    }
    profile_entries = external_contract_bundle()["operations"]
    for operation_id in operation_wrappers:
        assert profile_entries[operation_id]["external_consumption"]["status"] == "runtime-backed"
        assert profile_entries[operation_id]["contract"]["ir_plan"]["steps"][1]["uses"] == "guidance.lifecycle.apply"

    (tmp_path / ".agentic-workspace").mkdir()
    (tmp_path / ".agentic-workspace/config.toml").write_text(
        'schema_version = 1\n[workspace]\ncli_invoke = "agentic-workspace"\n',
        encoding="utf-8",
    )
    (tmp_path / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'current_target = "user-local:fast-worker"',
                "",
                "[local_memory]",
                "target_guidance_enabled = true",
                'target_guidance_overlay_path = ".agentic-workspace/local/guidance-lifecycle.json"',
                "",
                "[delegation_targets.fast_worker]",
                'target_id = "user-local:fast-worker"',
                'target_revision = "rev-1"',
                'aliases = ["fast"]',
                'revision_policy = "preserve"',
                'strength = "strong"',
                'execution_methods = ["internal"]',
            ]
        ),
        encoding="utf-8",
    )
    store_path = tmp_path / ".agentic-workspace/local/guidance-lifecycle.json"
    store_path.parent.mkdir(parents=True)

    def lifecycle_record(guidance_id: str, instruction: str) -> dict[str, object]:
        return {
            "kind": "agentic-workspace/guidance-lifecycle-record/v1",
            "guidance_id": guidance_id,
            "status": "active",
            "instruction": instruction,
            "applicability": {"target_identity_ref": "user-local:fast-worker"},
            "destination": {
                "owner": "repo-local-target-guidance-overlay",
                "owner_operation_id": "agent-guidance.promote.target-guidance",
                "store": ".agentic-workspace/local/guidance-lifecycle.json",
            },
            "provenance": {"source_event_refs": [guidance_id]},
            "transitions": [{"operation": "promote", "reason": "fixture"}],
            "revision": 1,
        }

    store_path.write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/guidance-lifecycle-store/v1",
                "records": [
                    lifecycle_record("guidance:generated-edit", "Prefer broad edits."),
                    lifecycle_record("guidance:generated-merge-target", "Prefer precise edits."),
                    lifecycle_record("guidance:generated-merge-source", "Prefer precise edits too."),
                    lifecycle_record("guidance:generated-split", "Prefer precise edits and proof."),
                    lifecycle_record("guidance:generated-suppress", "Prefer temporary guidance."),
                    lifecycle_record("guidance:generated-revalidate", "Prefer current target guidance."),
                    lifecycle_record("guidance:generated-weaken", "Prefer advisory guidance."),
                    lifecycle_record("guidance:generated-supersede", "Prefer old guidance."),
                    lifecycle_record("guidance:generated-replacement", "Prefer replacement guidance."),
                    lifecycle_record("guidance:generated-retire", "Prefer retiring guidance."),
                    lifecycle_record("guidance:generated-delete", "Prefer deleting guidance."),
                ],
            }
        ),
        encoding="utf-8",
    )
    correction_store = tmp_path / ".agentic-workspace/local/correction-events.json"
    correction_store.write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/correction-event-store/v1",
                "events": [
                    {
                        "target_identity_ref": "fast",
                        "target_revision": "rev-1",
                        "task_class": "mechanical-follow-through",
                        "scope_class": "narrow-code-change",
                        "invariant_id": "generated-promote",
                        "behavior_class": "edit-scope",
                        "desired_behavior": "Prefer generated promotion.",
                        "replaced_behavior": "Manual promotion.",
                        "authority": "explicit-user-correction",
                        "source": "pr-review",
                        "source_ref": "generated-promote-1",
                        "producer_class": "human-reviewer",
                        "producer_id": "reviewer-1",
                        "evidence_hash": "sha256:generated-promote-1",
                        "route_decisions": ["target-guidance", "target-suitability"],
                    },
                    {
                        "target_identity_ref": "fast",
                        "target_revision": "rev-1",
                        "task_class": "mechanical-follow-through",
                        "scope_class": "narrow-code-change",
                        "invariant_id": "generated-promote",
                        "behavior_class": "edit-scope",
                        "desired_behavior": "Prefer generated promotion.",
                        "replaced_behavior": "Manual promotion.",
                        "authority": "explicit-user-correction",
                        "source": "pr-review",
                        "source_ref": "generated-promote-2",
                        "producer_class": "human-reviewer",
                        "producer_id": "reviewer-1",
                        "evidence_hash": "sha256:generated-promote-2",
                        "route_decisions": ["target-guidance", "target-suitability"],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    invocation = [sys.executable, str(ROOT / "scripts/run_agentic_workspace.py")]

    edited = agent_guidance_edit(
        {
            "guidance_id": "guidance:generated-edit",
            "expected_revision": 1,
            "reason": "generated external edit",
            "instruction": "Prefer narrow edits.",
        },
        target=tmp_path,
        invocation=invocation,
    )

    assert edited["status"] == "transitioned"
    assert edited["mutation_applied"] is True
    assert edited["record"]["revision"] == 2
    assert edited["record"]["instruction"] == "Prefer narrow edits."
    merged = agent_guidance_merge(
        {
            "guidance_id": "guidance:generated-merge-target",
            "expected_revision": 1,
            "expected_record_revisions_json": json.dumps({"guidance:generated-merge-source": 1}),
            "merge_guidance_ids": ["guidance:generated-merge-source"],
            "reason": "generated external merge",
        },
        target=tmp_path,
        invocation=invocation,
    )
    split = agent_guidance_split(
        {
            "guidance_id": "guidance:generated-split",
            "expected_revision": 1,
            "split_instructions": ["Prefer precise edits.", "Prefer precise proof."],
            "reason": "generated external split",
        },
        target=tmp_path,
        invocation=invocation,
    )
    suppressed = agent_guidance_suppress(
        {"guidance_id": "guidance:generated-suppress", "expected_revision": 1, "reason": "generated external suppress"},
        target=tmp_path,
        invocation=invocation,
    )
    revalidated = agent_guidance_revalidate(
        {"guidance_id": "guidance:generated-revalidate", "expected_revision": 1, "reason": "generated external revalidate"},
        target=tmp_path,
        invocation=invocation,
    )
    weakened = agent_guidance_weaken(
        {"guidance_id": "guidance:generated-weaken", "expected_revision": 1, "reason": "generated external weaken"},
        target=tmp_path,
        invocation=invocation,
    )
    superseded = agent_guidance_supersede(
        {
            "guidance_id": "guidance:generated-supersede",
            "expected_revision": 1,
            "expected_record_revisions_json": json.dumps({"guidance:generated-replacement": 1}),
            "replacement_guidance_id": "guidance:generated-replacement",
            "reason": "generated external supersede",
        },
        target=tmp_path,
        invocation=invocation,
    )
    retired = agent_guidance_retire(
        {"guidance_id": "guidance:generated-retire", "expected_revision": 1, "reason": "generated external retire"},
        target=tmp_path,
        invocation=invocation,
    )
    deleted = agent_guidance_delete(
        {"guidance_id": "guidance:generated-delete", "expected_revision": 1, "reason": "generated external delete"},
        target=tmp_path,
        invocation=invocation,
    )
    from agentic_workspace.agent_guidance import guidance_promotion_from_store

    promotion_decision = guidance_promotion_from_store(target_root=tmp_path)
    promoted = agent_guidance_promote(
        {"guidance_id": promotion_decision["guidance"][0]["guidance_id"]},
        target=tmp_path,
        invocation=invocation,
    )

    assert merged["status"] == "transitioned"
    assert "guidance:generated-merge-source" in merged["record"]["merged_guidance_ids"]
    assert split["status"] == "transitioned"
    assert split["record"]["status"] == "split-retired"
    assert suppressed["record"]["status"] == "suppressed"
    assert revalidated["record"]["authority_revalidation"]["status"] == "current"
    assert weakened["record"]["claim_effect"] == "advisory-only"
    assert superseded["record"]["status"] == "superseded"
    assert retired["record"]["status"] == "retired"
    assert deleted["record"]["status"] == "deleted"
    assert promoted["status"] == "promoted"
    receipt_index = json.loads((tmp_path / ".agentic-workspace/local/guidance-receipts.json").read_text(encoding="utf-8"))
    mutation_receipts = [item for item in receipt_index["receipts"] if item.get("receipt_type") == "guidance-mutation"]
    assert {item["operation"] for item in mutation_receipts} >= {
        "promote",
        "edit",
        "merge",
        "split",
        "suppress",
        "revalidate",
        "weaken",
        "supersede",
        "retire",
        "delete",
    }


def test_correction_event_typescript_cli_delegates_to_python_authority_boundary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".agentic-workspace").mkdir()
    (tmp_path / ".agentic-workspace/config.toml").write_text(
        'schema_version = 1\n[workspace]\ncli_invoke = "agentic-workspace"\n', encoding="utf-8"
    )
    (tmp_path / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'current_target = "user-local:fast-worker"',
                "",
                "[local_memory]",
                "target_guidance_enabled = true",
                'user_guidance_root = "~/.agentic-workspace/target-guidance"',
                'correction_events_path = ".agentic-workspace/local/correction-events.json"',
                "",
                "[delegation_targets.fast_worker]",
                'target_id = "user-local:fast-worker"',
                'target_revision = "rev-1"',
                'aliases = ["fast"]',
                'revision_policy = "preserve"',
                'strength = "strong"',
                'execution_methods = ["internal"]',
            ]
        ),
        encoding="utf-8",
    )
    from agentic_workspace.agent_guidance import record_trusted_authority_receipt

    host_event = _trusted_guidance_host_event(
        tmp_path,
        authority="pr-review",
        producer_class="human-reviewer",
        producer_id="reviewer-1",
        source="github-review",
        source_ref="review-thread-1",
        host_admission_monkeypatch=monkeypatch,
        target_revision="rev-1",
    )
    receipt_ref = record_trusted_authority_receipt(
        target_root=tmp_path,
        authority="pr-review",
        producer_class="human-reviewer",
        producer_id="reviewer-1",
        source="github-review",
        source_ref="review-thread-1",
        target_revision="rev-1",
        host_event_ref=host_event["event_ref"],
    )["receipt_ref"]
    event = {
        "delivery_id": "delivery-ts-1",
        "target_identity_ref": "fast",
        "target_revision": "rev-1",
        "task_class": "mechanical-follow-through",
        "scope_class": "narrow-code-change",
        "invariant_id": "narrow-edits",
        "behavior_class": "edit-scope",
        "desired_behavior": "Prefer narrow edits.",
        "replaced_behavior": "Broad edits.",
        "source_ref": "review-thread-1",
        "evidence_hash": "sha256:review-thread-1",
        "route_decisions": ["target-guidance", "target-suitability"],
    }

    result = subprocess.run(
        [
            "node",
            str(ROOT / "generated/workspace/typescript/src/cli.mjs"),
            "correction-event",
            "submit",
            "--target",
            str(tmp_path),
            "--event-json",
            json.dumps(event),
            "--trusted-authority-receipt-ref",
            receipt_ref,
            "--format",
            "json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "stored"
    assert payload["admitted_event_count"] == 1
    assert payload["low_authority_event_count"] == 0
    assert payload["receipt_ref"].startswith(".agentic-workspace/local/correction-event-receipts/")


def test_contract_requirement_negotiation_distinguishes_change_classes() -> None:
    bundle = external_contract_bundle()
    operation_id, operation = next(iter(bundle["operations"].items()))
    compatible = negotiate_requirements({operation_id: operation["compatibility_fingerprint"]}, allow_runtime_backed=True)
    assert compatible["compatible"] is True
    additive = dict(operation["contract"])
    additive["future_additive_field"] = {"preserved": True}
    assert operation_compatibility_fingerprint(additive) == operation["compatibility_fingerprint"]
    breaking_contract = dict(operation["contract"])
    breaking_contract["output"] = {"kind": "breaking"}
    breaking_fingerprint = operation_compatibility_fingerprint(breaking_contract)
    assert breaking_fingerprint != operation["compatibility_fingerprint"]
    breaking = negotiate_requirements({operation_id: breaking_fingerprint}, allow_runtime_backed=True)
    assert breaking == {
        "compatible": False,
        "requirements": [{"operation": operation_id, "status": "incompatible", "reason": "operation fingerprint mismatch"}],
    }
    missing = negotiate_requirements({"does.not.exist": None})
    assert missing["requirements"][0]["status"] == "missing"
    runtime_backed = negotiate_requirements({operation_id: None})
    assert runtime_backed["requirements"][0]["status"] == "runtime-backed"
    script = f"""
import {{ negotiateRequirements, operationCompatibilityFingerprint, externalContractBundle }} from './generated/workspace/typescript/src/client.mjs';
const operation = externalContractBundle().operations[{json.dumps(operation_id)}];
console.log(JSON.stringify([negotiateRequirements({{{json.dumps(operation_id)}: null}}).requirements[0].status, negotiateRequirements({{'does.not.exist': null}}).requirements[0].status, operationCompatibilityFingerprint(operation.contract) === operation.compatibility_fingerprint]));
"""
    result = subprocess.run(["node", "--input-type=module", "--eval", script], cwd=ROOT, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == ["runtime-backed", "missing", True]


def test_schema_compatibility_distinguishes_optional_addition_from_breaking_change(monkeypatch) -> None:
    bundle = external_contract_bundle()
    operation_id, operation = next(iter(bundle["operations"].items()))
    requirement = {"compatibility_surface": copy.deepcopy(operation["compatibility_surface"])}
    additive = copy.deepcopy(bundle)
    role = next(role for role, schemas in operation["compatibility_surface"]["schemas"].items() if schemas)
    schema_name = next(iter(operation["compatibility_surface"]["schemas"][role]))
    schema = additive["operations"][operation_id]["compatibility_surface"]["schemas"][role][schema_name]
    schema.setdefault("properties", {})["future_optional"] = {"type": "string"}
    monkeypatch.setattr(public_client, "external_contract_bundle", lambda: additive)
    assert negotiate_requirements({operation_id: requirement}, allow_runtime_backed=True)["compatible"] is True
    breaking = copy.deepcopy(bundle)
    changed = breaking["operations"][operation_id]["compatibility_surface"]["schemas"][role][schema_name]
    optional = next(name for name in changed.get("properties", {}) if name not in changed.get("required", []))
    del changed["properties"][optional]
    monkeypatch.setattr(public_client, "external_contract_bundle", lambda: breaking)
    assert negotiate_requirements({operation_id: requirement}, allow_runtime_backed=True)["compatible"] is False


def test_requirement_matrix_reports_unsupported(monkeypatch) -> None:
    bundle = copy.deepcopy(external_contract_bundle())
    operation_id, operation = next(iter(bundle["operations"].items()))
    operation["external_consumption"]["status"] = "target-specific"
    monkeypatch.setattr(public_client, "external_contract_bundle", lambda: bundle)
    assert negotiate_requirements({operation_id: None})["requirements"][0]["status"] == "unsupported"


@pytest.mark.parametrize(
    ("role", "old_schema", "new_schema", "compatible"),
    [
        ("input", {"required": ["a"]}, {"required": ["a", "b"]}, False),
        ("input", {"enum": ["a", "b"]}, {"enum": ["a"]}, False),
        ("input", {"enum": ["a"]}, {"enum": ["a", "b"]}, True),
        ("input", {"type": ["string"]}, {"type": ["string", "null"]}, True),
        ("output", {"required": ["a"]}, {"required": []}, False),
        ("output", {"enum": ["a"]}, {"enum": ["a", "b"]}, False),
        ("output", {"type": ["string"]}, {"type": ["string", "null"]}, False),
    ],
)
def test_python_and_typescript_role_aware_compatibility(
    role: str, old_schema: dict[str, object], new_schema: dict[str, object], compatible: bool
) -> None:
    old = {"contract": {}, "schemas": {role: {"fixture": old_schema}}}
    new = {"contract": {}, "schemas": {role: {"fixture": new_schema}}}
    assert public_client.compatibility_surface_satisfied(old, new) is compatible
    script = f"import {{compatibilitySurfaceSatisfied}} from './generated/workspace/typescript/src/client.mjs'; console.log(compatibilitySurfaceSatisfied({json.dumps(old)}, {json.dumps(new)}));"
    result = subprocess.run(["node", "--input-type=module", "--eval", script], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(compatible).lower()


@pytest.mark.parametrize(
    "change,compatible",
    [("add_optional", True), ("add_required", False), ("make_required", False), ("remove_optional", False), ("tighten_type", False)],
)
def test_python_and_typescript_operation_input_evolution(change: str, compatible: bool) -> None:
    old = {
        "contract": {"inputs": [{"name": "a", "required": False, "type": "string"}]},
        "schemas": {"input": {"fixture": {"type": "object", "properties": {"a": {"type": "string"}}, "required": []}}},
    }
    new = copy.deepcopy(old)
    if change.startswith("add_"):
        required = change == "add_required"
        new["contract"]["inputs"].append({"name": "b", "required": required, "type": "string"})
        new["schemas"]["input"]["fixture"]["properties"]["b"] = {"type": "string"}
        if required:
            new["schemas"]["input"]["fixture"]["required"].append("b")
    elif change == "make_required":
        new["contract"]["inputs"][0]["required"] = True
        new["schemas"]["input"]["fixture"]["required"].append("a")
    elif change == "remove_optional":
        new["contract"]["inputs"] = []
        del new["schemas"]["input"]["fixture"]["properties"]["a"]
    else:
        new["contract"]["inputs"][0]["type"] = "integer"
        new["schemas"]["input"]["fixture"]["properties"]["a"]["type"] = "integer"
    assert public_client.compatibility_surface_satisfied(old, new) is compatible
    script = f"import {{compatibilitySurfaceSatisfied}} from './generated/workspace/typescript/src/client.mjs'; console.log(compatibilitySurfaceSatisfied({json.dumps(old)}, {json.dumps(new)}));"
    result = subprocess.run(["node", "--input-type=module", "--eval", script], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(compatible).lower()


def test_generated_operation_specific_wrapper_uses_public_contract() -> None:
    payload = config_report(
        {},
        target=ROOT,
        invocation=[sys.executable, str(ROOT / "scripts/run_agentic_workspace.py")],
    )
    assert payload["kind"] == "agentic-workspace/config-tiny/v1"
    assert callable(delegation_outcome_append)


def test_public_delegation_outcome_append_persists_validated_context_cost(tmp_path: Path) -> None:
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_text("[workspace]\nenabled = true\n", encoding="utf-8")
    context_cost = {
        "kind": "agentic-workspace/assignment-context-cost/v1",
        "transport": "cli",
        "adapter_revision": "sha256:adapter",
        "assignment_packet_bytes": 3662,
        "rendered_prompt_bytes": 3913,
        "effective_input_tokens": 81752,
        "cached_input_tokens": 62464,
        "output_tokens": 1591,
        "orientation_command_count": 3,
        "retry_count": 0,
        "repair_loop_count": 0,
        "elapsed_ms": 1000,
        "unknown_fields": [],
        "observation_authority": "adapter-sidecar-or-host-measurement",
        "raw_transcript_stored": False,
    }
    values = {
        "delegation_target": "worker",
        "task_class": "implementation",
        "scope_class": "bounded",
        "outcome": "success",
        "context_cost_json": json.dumps(context_cost),
    }

    payload = invoke_operation(
        "delegation-outcome.append",
        values,
        target=tmp_path,
        invocation=[sys.executable, str(ROOT / "scripts/run_agentic_workspace.py")],
        allow_runtime_backed=True,
    )

    assert payload["recorded"]["context_cost"] == context_cost
    stored_path = tmp_path / ".agentic-workspace/delegation-outcomes.json"
    stored = json.loads(stored_path.read_text(encoding="utf-8"))
    assert stored["records"][0]["context_cost"] == context_cost

    invalid = {**context_cost, "effective_input_tokens": -1}
    with pytest.raises(AWClientError) as error:
        invoke_operation(
            "delegation-outcome.append",
            {**values, "context_cost_json": json.dumps(invalid)},
            target=tmp_path,
            invocation=[sys.executable, str(ROOT / "scripts/run_agentic_workspace.py")],
            allow_runtime_backed=True,
        )
    assert error.value.kind == "rejected"
    unchanged = json.loads(stored_path.read_text(encoding="utf-8"))
    assert len(unchanged["records"]) == 1


def test_public_client_classifies_disabled_and_invocation_unavailable(tmp_path: Path) -> None:
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_text("[workspace]\nenabled = false\n", encoding="utf-8")
    with pytest.raises(AWClientError) as disabled:
        invoke_operation("config.report", {}, target=tmp_path, allow_runtime_backed=True)
    assert disabled.value.kind == "disabled"
    config.write_text("[workspace]\nenabled = true\n", encoding="utf-8")
    with pytest.raises(AWClientError) as unavailable:
        invoke_operation("config.report", {}, target=tmp_path, invocation=[str(tmp_path / "missing")], allow_runtime_backed=True)
    assert unavailable.value.kind == "invocation-unavailable"


@pytest.mark.parametrize(
    ("returncode", "stdout", "stderr", "expected"),
    [
        (0, "[]", "", "malformed"),
        (0, "not-json", "", "malformed"),
        (2, '{"status":"rejected"}', "", "rejected"),
        (1, '{"status":"failed"}', "", "failed"),
        (1, "{}", "", "malformed"),
    ],
)
def test_public_client_classifies_result_and_failure_envelopes(
    monkeypatch, returncode: int, stdout: str, stderr: str, expected: str
) -> None:
    monkeypatch.setattr(
        public_client.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr),
    )
    with pytest.raises(AWClientError) as error:
        invoke_operation("config.report", {}, target=ROOT, allow_runtime_backed=True)
    assert error.value.kind == expected


def test_python_and_typescript_mutation_operation_parity(tmp_path: Path) -> None:
    python_target = tmp_path / "python"
    typescript_target = tmp_path / "typescript"
    for target in (python_target, typescript_target):
        config = target / ".agentic-workspace/config.toml"
        config.parent.mkdir(parents=True)
        config.write_text("[workspace]\nenabled = true\n", encoding="utf-8")
    values = {"delegation_target": "fixture", "task_class": "parity", "scope_class": "parity", "outcome": "success"}
    python_payload = invoke_operation(
        "delegation-outcome.append",
        values,
        target=python_target,
        invocation=[sys.executable, str(ROOT / "scripts/run_agentic_workspace.py")],
        allow_runtime_backed=True,
    )
    script = f"""
import {{ invokeOperation }} from './generated/workspace/typescript/src/client.mjs';
const payload = invokeOperation('delegation-outcome.append', {json.dumps(values)}, {{ target: {json.dumps(str(typescript_target))}, invocation: [{json.dumps(sys.executable)}, {json.dumps(str(ROOT / "scripts/run_agentic_workspace.py"))}], allowRuntimeBacked: true }});
console.log(JSON.stringify(payload));
"""
    completed = subprocess.run(["node", "--input-type=module", "--eval", script], cwd=ROOT, text=True, capture_output=True, check=False)
    assert completed.returncode == 0, completed.stderr
    typescript_payload = json.loads(completed.stdout)
    assert python_payload["kind"] == typescript_payload["kind"] == "agentic-workspace/delegation-outcomes/v1"
    assert python_payload["recorded"]["outcome"] == typescript_payload["recorded"]["outcome"] == "success"


def test_config_policy_generated_python_and_typescript_preview_parity(tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.syspath_prepend(str(ROOT))
    from generated.workspace.python.commands.config_policy_apply import invoke as invoke_python_config_policy

    targets = {name: tmp_path / name for name in ("python-policy", "typescript-policy")}
    contexts: dict[str, dict[str, object]] = {}
    for name, target in targets.items():
        subprocess.run(["git", "init", "-q", str(target)], check=True)
        assert cli.main(["init", "--target", str(target), "--modules", "planning,memory", "--format", "json"]) == 0
        capsys.readouterr()
        assert cli.main(["setup", "--target", str(target), "--format", "json"]) == 0
        contexts[name] = json.loads(capsys.readouterr().out)["configuration_concerns"]["mutation_context"]

    def values(name: str) -> dict[str, object]:
        context = contexts[name]
        decision = {
            "kind": "agentic-workspace/config-policy-decision/v1",
            "concern_id": "orchestration-posture",
            "authority": "human-answer",
            "scope": "local",
            "setup_identity": context["setup_identity"],
            "changes": {
                "setup.prompt_disposition": "deferred",
                "setup.setup_identity": context["setup_identity"],
                "setup.context_revision": "sha256:fixture-context",
                "setup.unresolved_concerns": ["orchestration-posture"],
                "setup.required_concerns": ["orchestration-posture"],
            },
        }
        return {
            "target": str(targets[name]),
            "decision_json": json.dumps(decision),
            "expect_config_revision": context["local_config_revision"],
            "expect_setup_identity": context["setup_identity"],
            "dry_run": True,
            "format": "json",
        }

    python_payload = invoke_python_config_policy(values("python-policy"))
    script = f"""
import {{ invokeGeneratedOperation }} from './generated/workspace/typescript/src/runtime.mjs';
const payload = invokeGeneratedOperation({{
  operationId: 'config.policy-apply',
  operationPath: 'operations/config.policy-apply.json',
  values: {json.dumps(values("typescript-policy"))}
}});
console.log(JSON.stringify(payload));
"""
    completed = subprocess.run(["node", "--input-type=module", "--eval", script], cwd=ROOT, text=True, capture_output=True)
    assert completed.returncode == 0, completed.stderr
    typescript_payload = json.loads(completed.stdout)
    for field in (
        "kind",
        "status",
        "scope",
        "authority",
        "path",
        "previous_revision",
        "revision",
        "readiness_status",
        "outcome",
        "mutation_applied",
        "reason_code",
        "effects",
    ):
        assert python_payload[field] == typescript_payload[field]

    def completion_values(name: str) -> dict[str, object]:
        context = contexts[name]
        return {
            "target": str(targets[name]),
            "decision_json": json.dumps(context["reconciliation_completion"]["decision"]),
            "expect_config_revision": context["local_config_revision"],
            "expect_setup_identity": context["setup_identity"],
            "dry_run": True,
            "format": "json",
        }

    python_completion = invoke_python_config_policy(completion_values("python-policy"))
    completion_script = f"""
import {{ invokeGeneratedOperation }} from './generated/workspace/typescript/src/runtime.mjs';
const payload = invokeGeneratedOperation({{
  operationId: 'config.policy-apply',
  operationPath: 'operations/config.policy-apply.json',
  values: {json.dumps(completion_values("typescript-policy"))}
}});
console.log(JSON.stringify(payload));
"""
    completion_run = subprocess.run(["node", "--input-type=module", "--eval", completion_script], cwd=ROOT, text=True, capture_output=True)
    assert completion_run.returncode == 0, completion_run.stderr
    typescript_completion = json.loads(completion_run.stdout)
    for field in (
        "kind",
        "status",
        "scope",
        "authority",
        "path",
        "previous_revision",
        "revision",
        "readiness_status",
        "outcome",
        "mutation_applied",
        "reason_code",
        "effects",
    ):
        assert python_completion[field] == typescript_completion[field]


@pytest.mark.parametrize(
    "payload",
    [
        {"kind": "wrong", "path": "x", "record_count": 1, "recorded": {}},
        {"kind": "agentic-workspace/delegation-outcomes/v1", "path": "x", "record_count": 0, "recorded": {}},
    ],
)
def test_python_and_typescript_reject_same_invalid_result(payload: dict[str, object], tmp_path: Path) -> None:
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_text("[workspace]\nenabled = true\n", encoding="utf-8")
    values = {"delegation_target": "fixture", "task_class": "parity", "scope_class": "parity", "outcome": "success"}
    with pytest.raises(AWClientError) as python_error:
        invoke_operation(
            "delegation-outcome.append",
            values,
            target=tmp_path,
            invocation=[sys.executable, "-c", f"print({json.dumps(json.dumps(payload))})"],
            allow_runtime_backed=True,
        )
    script = f"""
import {{ invokeOperation }} from './generated/workspace/typescript/src/client.mjs';
try {{ invokeOperation('delegation-outcome.append', {json.dumps(values)}, {{ target: {json.dumps(str(tmp_path))}, invocation: ['node', '-e', {json.dumps("console.log(" + json.dumps(json.dumps(payload)) + ")")}], allowRuntimeBacked: true }}); }} catch (error) {{ console.log(error.kind); }}
"""
    result = subprocess.run(["node", "--input-type=module", "--eval", script], cwd=ROOT, text=True, capture_output=True)
    assert python_error.value.kind == "malformed"
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "malformed"
