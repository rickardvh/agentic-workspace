from __future__ import annotations

import hashlib
import sys
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
[modules]
enabled = ["verification"]

[workspace]
cli_invoke = "{REPO_LOCAL_CLI_INVOKE}"

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


def _append_focused_proof_runtime_lane(target: Path) -> None:
    config = target / ".agentic-workspace" / "verification" / "manifest.toml"
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
authority_refs = [".agentic-workspace/verification/manifest.toml", "docs/maintainer/testing-strategy.md"]
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
    config = target / ".agentic-workspace" / "verification" / "manifest.toml"
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
    config = target / ".agentic-workspace" / "verification" / "manifest.toml"
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
authority_refs = [".agentic-workspace/verification/manifest.toml", "docs/maintainer/testing-strategy.md"]
escalation = ["focused route cannot prove the changed guidance behavior"]
claim_boundary = "focused-root-guidance-required"
owner = "workspace-cli-runtime"
route_role = "behavior"
""",
        encoding="utf-8",
    )


def _append_session_logging_lane(target: Path) -> None:
    config = target / ".agentic-workspace" / "verification" / "manifest.toml"
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
authority_refs = [".agentic-workspace/verification/manifest.toml"]
escalation = ["session-log persistence or local diagnostic boundaries changed"]
claim_boundary = "focused-session-logging-required"
owner = "workspace-cli-runtime"
""",
        encoding="utf-8",
    )


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
        target / ".agentic-workspace" / "verification" / "manifest.toml",
        (target / ".agentic-workspace" / "verification" / "manifest.toml").read_text(encoding="utf-8")
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
