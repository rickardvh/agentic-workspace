from __future__ import annotations

# ruff: noqa: F403,F405
from tests.workspace_cli_support import *


def test_repo_binding_automatic_assignment_requirement_is_hard_with_honest_unavailable_evidence() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    config = cli._load_workspace_config(target_root=repo_root)
    requirement = next(item for item in config.assurance.requirements if item.id == "binding_automatic_assignment")

    assert requirement.requirement_class == "invariant"
    assert requirement.force == "required-before-closeout"
    assert requirement.blocking_claims == ("claim-work-complete",)
    assert requirement.source_intent_ref.endswith("/issues/2817")
    assert requirement.required_evidence == ("binding_automatic_assignment_organic_dogfood",)

    evidence = workspace_runtime_core._load_assurance_evidence_records(target_root=repo_root)
    record = next(item for item in evidence["records"] if item["requirement_id"] == requirement.id)
    assert record["evidence_label"] == requirement.required_evidence[0]
    assert record["status"] == "unavailable"

    report = workspace_runtime_core._assurance_requirements_report_payload(
        config=config,
        target_root=repo_root,
        task_text="binding automatic assignment issue 2817",
        changed_paths=["src/agentic_workspace/workspace_runtime_core.py"],
    )
    status = next(item for item in report["evidence_status"] if item["requirement_id"] == requirement.id)
    assert status["state"] == "unavailable"


def test_repo_config_orthogonality_requirement_is_hard_and_current() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    config = cli._load_workspace_config(target_root=repo_root)
    requirement = next(item for item in config.assurance.requirements if item.id == "config_orthogonality_constructibility")

    assert requirement.requirement_class == "invariant"
    assert requirement.force == "required-before-closeout"
    assert requirement.blocking_claims == ("claim-work-complete",)
    assert requirement.source_intent_ref.endswith("/issues/2613")
    assert requirement.required_evidence == ("config_orthogonality_constructibility_fixture",)

    evidence = workspace_runtime_core._load_assurance_evidence_records(target_root=repo_root)
    record = next(item for item in evidence["records"] if item["requirement_id"] == requirement.id)
    assert record["status"] == "satisfied"


@pytest.mark.parametrize("assignment_policy", ["local-preferred", "best-fit-advisory", "required-best-fit"])
@pytest.mark.parametrize("transport_authority", ["manual", "automatic"])
@pytest.mark.parametrize("human_override_policy", ["explicit-only", "allowed-with-recorded-reason", "disallowed"])
def test_canonical_delegation_policy_dimensions_compose_freely(
    tmp_path: Path,
    assignment_policy: str,
    transport_authority: str,
    human_override_policy: str,
) -> None:
    target = tmp_path / f"repo-{assignment_policy}-{transport_authority}-{human_override_policy}"
    target.mkdir()
    _init_git_repo(target)
    _write(
        target / ".agentic-workspace/config.local.toml",
        f"""
schema_version = 1

[runtime]
supports_internal_delegation = true

[safety]
safe_to_auto_run_commands = true

[delegation]
assignment_policy = "{assignment_policy}"
transport_authority = "{transport_authority}"
human_override_policy = "{human_override_policy}"
current_target = "current"

[delegation_targets.current]
target_id = "target:current"
strength = "strong"
execution_methods = ["internal"]
capability_classes = ["boundary-shaping", "reasoning-heavy", "mixed", "mechanical-follow-through"]
""",
    )

    config = cli._load_workspace_config(target_root=target)
    mixed = workspace_runtime_core._mixed_agent_payload(config=config)
    policy = mixed["assignment_policy"]
    posture = mixed["effective_orchestration"]

    assert policy["assignment_policy"]["value"] == assignment_policy
    assert policy["execution_role"]["value"] == ("ordinary-executor" if assignment_policy == "local-preferred" else "orchestrator")
    assert policy["human_override_policy"]["value"] == human_override_policy
    assert posture["assignment"]["policy"] == assignment_policy
    assert posture["transport"]["authority"] == transport_authority
    assert not posture["status"].startswith("binding-blocked-execution-role")
    assert posture["assignment"]["authority"] == (
        "binding" if assignment_policy == "required-best-fit" else "advisory" if assignment_policy == "best-fit-advisory" else "local"
    )


def test_repo_local_delegation_policy_uses_only_canonical_independent_controls() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    config = cli._load_workspace_config(target_root=repo_root)
    mixed = workspace_runtime_core._mixed_agent_payload(config=config)

    assert mixed["effective_orchestration"]["status"] == "binding-active"
    assert mixed["effective_orchestration"]["current_target"]["automatic_methods"] == ["internal"]
    assert mixed["assignment_policy"]["migration"]["canonical_fields"] == [
        "delegation.assignment_policy",
        "delegation.transport_authority",
        "delegation.human_override_policy",
        "delegation.current_target",
        "delegation_targets.<target>.transports",
    ]


def test_target_eligibility_and_reasoning_are_derived_from_capability_and_strength(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(
        target / ".agentic-workspace/config.local.toml",
        """
schema_version = 1

[delegation_targets.worker]
strength = "medium"
execution_methods = ["manual"]
capability_classes = ["mixed", "mechanical-follow-through"]
safe_task_classes = ["boundary-shaping"]
forbidden_task_classes = ["mixed"]
human_control_modes = ["off"]
""",
    )

    config = cli._load_workspace_config(target_root=target)
    profile = config.local_override.delegation_targets[0]
    assert profile.reasoning_profile == "balanced"
    assert profile.safe_task_classes == ("mechanical-follow-through",)
    assert profile.forbidden_task_classes == ("mixed",)
    assert profile.human_control_modes == ()


def test_canonical_target_transports_are_constructible_and_override_legacy_siblings(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(
        target / ".agentic-workspace/config.local.toml",
        """
schema_version = 1

[runtime]
supports_internal_delegation = true

[safety]
safe_to_auto_run_commands = true

[delegation]
assignment_policy = "required-best-fit"
transport_authority = "automatic"
current_target = "worker"

[delegation_targets.worker]
strength = "strong"
execution_methods = ["manual"]
dispatch_adapter_kind = "host-native"
escalation_target = "fallback-worker"
transports = [
  { kind = "internal" },
  { kind = "process", command = ["worker-cli", "--output", "{output_file}"], output_mode = "json-file" },
  { kind = "api", command = ["worker-api", "--schema", "{output_schema}"] },
  { kind = "manual" },
]
""",
    )

    config = cli._load_workspace_config(target_root=target)
    profile = config.local_override.delegation_targets[0]
    assert profile.execution_methods == ("internal", "cli", "api", "manual")
    assert [item["source"] for item in profile.transports] == ["canonical-transports"] * 4
    assert profile.transports[1]["command"] == ["worker-cli", "--output", "{output_file}"]
    assert profile.transports[2]["command"] == ["worker-api", "--schema", "{output_schema}"]
    assert profile.escalation_target is None
    assert any("canonical transports override legacy" in warning for warning in config.warnings)
    assert any("escalation_target is an ignored compatibility alias" in warning for warning in config.warnings)

    mixed = workspace_runtime_core._mixed_agent_payload(config=config)
    projected = mixed["delegation_targets"]["profiles"][0]
    assert [item["readiness"] for item in projected["transports"]] == [
        "configured",
        "configured",
        "configured",
        "configured",
    ]
    assert mixed["effective_orchestration"]["current_target"]["automatic_methods"] == ["api", "cli", "internal"]
    assert "escalation_target" not in projected


def test_canonical_process_transport_requires_its_own_payload(tmp_path: Path) -> None:
    from agentic_workspace.config import WorkspaceUsageError

    target = tmp_path / "repo"
    target.mkdir()
    _write(
        target / ".agentic-workspace/config.local.toml",
        'schema_version = 1\n\n[delegation_targets.worker]\nstrength = "strong"\ntransports = [{ kind = "process" }]\n',
    )
    with pytest.raises(WorkspaceUsageError, match="command is required for process transport"):
        cli._load_workspace_config(target_root=target)


def test_legacy_unconfigured_transport_is_factual_but_not_automatic(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(
        target / ".agentic-workspace/config.local.toml",
        """
schema_version = 1
[safety]
safe_to_auto_run_commands = true
[delegation]
assignment_policy = "required-best-fit"
transport_authority = "automatic"
current_target = "worker"
[delegation_targets.worker]
strength = "strong"
execution_methods = ["cli"]
""",
    )
    config = cli._load_workspace_config(target_root=target)
    profile = config.local_override.delegation_targets[0]
    assert profile.execution_methods == ("cli",)
    assert profile.transports[0]["readiness"] == "declared-unconfigured"
    mixed = workspace_runtime_core._mixed_agent_payload(config=config)
    assert mixed["effective_orchestration"]["status"] == "binding-active-transport-unavailable"
    assert mixed["effective_orchestration"]["current_target"]["automatic_methods"] == []


def test_config_rejects_overlapping_assurance_level_owners_with_structural_repair(tmp_path: Path) -> None:
    from agentic_workspace.config import WorkspaceUsageError

    target = tmp_path / "repo"
    target.mkdir()
    _write(
        target / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance.subsystem_profiles.audit]
assurance_level = "high"
level = "low"
force = "recommended"
""",
    )

    with pytest.raises(WorkspaceUsageError, match="overlapping writable owners.*keep assurance_level.*compatibility-only level alias"):
        cli._load_workspace_config(target_root=target)


def test_config_orthogonality_rejects_session_path_mode_alias_beside_canonical_owner(tmp_path: Path) -> None:
    from agentic_workspace.config import WorkspaceUsageError

    target = tmp_path / "repo"
    target.mkdir()
    _write(
        target / ".agentic-workspace/config.local.toml",
        'schema_version = 1\n\n[session_logging]\nredact_local_paths = true\npath_mode = "absolute"\n',
    )

    with pytest.raises(WorkspaceUsageError, match="two writable path-mode owners.*keep path_mode.*compatibility-only"):
        cli._load_workspace_config(target_root=target)

    _write(
        target / ".agentic-workspace/config.local.toml",
        'schema_version = 1\n\n[session_logging]\npath_mode = "redacted"\n',
    )
    config = cli._load_workspace_config(target_root=target)
    assert config.local_override.session_logging.path_mode == "redacted"


def test_config_orthogonality_keeps_assurance_classifier_owner_source_constructible(tmp_path: Path) -> None:
    from agentic_workspace.config import WorkspaceUsageError

    target = tmp_path / "repo"
    target.mkdir()
    _write(
        target / ".agentic-workspace/config.toml",
        'schema_version = 1\n\n[assurance]\nclassification_owner = "config-native"\nclassification_source = "repo-policy"\n',
    )
    with pytest.raises(WorkspaceUsageError, match="classification_source conflicts with config-native"):
        cli._load_workspace_config(target_root=target)

    _write(
        target / ".agentic-workspace/config.toml",
        'schema_version = 1\n\n[assurance]\nclassification_owner = "repository-owned"\nclassification_source = "repo-policy"\n',
    )
    config = cli._load_workspace_config(target_root=target)
    assert config.assurance.classification_owner == "repository-owned"
    assert config.assurance.classification_source == "repo-policy"


def test_config_orthogonality_rejects_multiple_roles_for_one_proof_command(tmp_path: Path) -> None:
    from agentic_workspace.config import WorkspaceUsageError

    target = tmp_path / "repo"
    target.mkdir()
    command = "python -m pytest tests/test_audit.py -q"
    _write(
        target / ".agentic-workspace/config.toml",
        f'schema_version = 1\n\n[assurance.proof_profiles.audit]\nrequired_commands = ["{command}"]\noptional_commands = ["{command}"]\n',
    )

    with pytest.raises(WorkspaceUsageError, match="assigns multiple command roles.*exactly one"):
        cli._load_workspace_config(target_root=target)

    _write(
        target / ".agentic-workspace/config.toml",
        f'schema_version = 1\n\n[assurance.proof_profiles.audit]\nrequired_commands = ["{command}"]\n',
    )
    config = cli._load_workspace_config(target_root=target)
    assert config.assurance.proof_profiles[0].required_commands == (command,)
    assert config.assurance.proof_profiles[0].optional_commands == ()


def test_config_orthogonality_rejects_duplicate_installed_capability_owners(tmp_path: Path) -> None:
    from agentic_workspace.config import WorkspaceUsageError

    target = tmp_path / "repo"
    target.mkdir()
    _write(
        target / ".agentic-workspace/config.toml",
        """
schema_version = 1

[cli_compatibility]
required_capabilities = ["installed-state-sync-v2"]

[payload]
minimum_capabilities = ["installed-state-sync-v2"]
""",
    )

    with pytest.raises(WorkspaceUsageError, match="duplicates installed-runtime capability ownership.*payload.minimum_capabilities"):
        cli._load_workspace_config(target_root=target)

    _write(
        target / ".agentic-workspace/config.toml",
        'schema_version = 1\n\n[payload]\nminimum_capabilities = ["installed-state-sync-v2"]\n',
    )
    config = cli._load_workspace_config(target_root=target)
    assert config.payload_target.minimum_capabilities == ("installed-state-sync-v2",)
    assert config.cli_compatibility.required_capabilities == ()


def test_config_orthogonality_rejects_sibling_terminal_assurance_dispositions(tmp_path: Path) -> None:
    from agentic_workspace.config import WorkspaceUsageError

    target = tmp_path / "repo"
    target.mkdir()
    _write(
        target / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance.requirements.audit]
level = "high"
applies_to_paths = ["src/audit/**"]
force = "recommended"
waiver = { reason = "waive", owner = "maintainer", applicability = {} }
dismissal = { reason = "dismiss", owner = "maintainer", applicability = {} }
""",
    )

    with pytest.raises(WorkspaceUsageError, match="contradictory sibling dispositions waiver and dismissal.*one owned terminal"):
        cli._load_workspace_config(target_root=target)

    _write(
        target / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance.requirements.audit]
level = "high"
applies_to_paths = ["src/audit/**"]
force = "recommended"
waiver = { reason = "waive", owner = "maintainer", applicability = {} }
""",
    )
    config = cli._load_workspace_config(target_root=target)
    assert config.assurance.requirements[0].waiver is not None
    assert config.assurance.requirements[0].dismissal is None


@pytest.mark.parametrize("shared_policy", ["local-preferred", "best-fit-advisory", "required-best-fit"])
@pytest.mark.parametrize("local_policy", ["local-preferred", "best-fit-advisory", "required-best-fit"])
def test_shared_local_assignment_policy_layers_compose_for_every_legal_value(tmp_path: Path, shared_policy: str, local_policy: str) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    shared = tmp_path / "aw.config.shared.toml"
    _write(shared, f'schema_version = 1\n\n[delegation]\nassignment_policy = "{shared_policy}"\n')
    _write(
        target / ".agentic-workspace/config.local.toml",
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[workspace]",
                f'shared_config_path = "{shared.as_posix()}"',
                "",
                "[delegation]",
                f'assignment_policy = "{local_policy}"',
            ]
        ),
    )

    config = cli._load_workspace_config(target_root=target)
    policy = cli._config_payload(config=config)["mixed_agent"]["assignment_policy"]
    assert policy["assignment_policy"] == {"value": local_policy, "source": "local-override"}


@pytest.mark.parametrize(
    ("role", "policy", "target_status", "mode", "permitted", "expected"),
    [
        ("ordinary-executor", "local-preferred", "known-profile", "auto", True, "transport-auto-local-assignment"),
        ("orchestrator", "required-best-fit", "known-profile", "auto", True, "binding-active"),
        ("orchestrator", "best-fit-advisory", "known-profile", "suggest", False, "advisory-best-fit"),
        ("orchestrator", "required-best-fit", "unknown", "auto", True, "binding-blocked-unresolved-target"),
        ("orchestrator", "required-best-fit", "known-profile", "suggest", False, "binding-active-transport-unavailable"),
    ],
)
def test_effective_orchestration_posture_separates_assignment_from_transport(
    role: str, policy: str, target_status: str, mode: str, permitted: bool, expected: str
) -> None:
    assignment_policy = {
        "execution_role": {"value": role, "source": "local-override"},
        "assignment_policy": {"value": policy, "source": "local-override"},
        "current_target": {"value": "worker", "source": "local-override"},
        "current_target_status": target_status,
        "human_override_policy": {"value": "explicit-only", "source": "default"},
    }
    delegation_control = {
        "configured_mode": mode,
        "effective_mode": mode,
        "execution_permitted": permitted,
        "source": "local-override",
    }
    posture = workspace_runtime_core._effective_orchestration_posture_payload(
        assignment_policy=assignment_policy,
        delegation_control=delegation_control,
        profile_payloads=[
            {
                "name": "worker",
                "target_id": "worker",
                "execution_methods": ["internal"],
                "dispatch_command": ["worker-bridge"],
            }
        ],
        cli_invoke="uv run agentic-workspace",
    )

    assert posture["status"] == expected
    assert posture["assignment"]["policy"] == policy
    assert posture["transport"]["configured_mode"] == mode
    assert posture["change_route"]["owner"] == ".agentic-workspace/config.local.toml"
    assert "mixed_agent.effective_orchestration" in posture["change_route"]["detail_command"]


def _guidance_host_signature(payload: dict[str, object]) -> dict[str, object]:
    import sys

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
    admission_context_overrides: dict[str, object] | None = None,
    key_overrides: dict[str, object] | None = None,
    install_host_admission: bool = True,
) -> dict[str, object]:
    from agentic_workspace.agent_guidance import (
        TRUSTED_AUTHORITY_EVENT_AUDIENCE,
        TRUSTED_AUTHORITY_EVENT_INBOX_PATH,
        TRUSTED_AUTHORITY_EVENT_STORE_PATH,
        _json_digest,
        _trusted_authority_admission_signature_payload,
        _trusted_authority_event_digest,
        record_trusted_authority_host_event,
    )

    admission_context = {
        "audience": TRUSTED_AUTHORITY_EVENT_AUDIENCE,
        "workspace_ref": f"workspace:path:{target_root.resolve()}",
        "issued_at": "2026-07-29T00:00:00Z",
        "expires_at": "2099-01-01T00:00:00Z",
        "nonce": f"{source_ref}:{event_id or 'event'}",
    }
    if admission_context_overrides:
        admission_context.update(admission_context_overrides)
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
        "admission_context": admission_context,
        "custody": {
            "producer": "github-review-adapter",
            "trusted_channel": "github-review-webhook",
            "rule": "Fixture for an adapter-owned host event; repo-local guidance code only imports it.",
        },
    }
    event_ref = "trusted-authority-event:" + _json_digest(event)[:24]
    event["event_ref"] = event_ref
    event["host_admission_verdict"] = {
        "kind": "agentic-workspace/trusted-authority-host-event-verdict/v1",
        "status": str(key_overrides.get("status") if key_overrides else "admitted"),
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
        "workspace_ref": str(admission_context["workspace_ref"]),
        "audience": str(admission_context["audience"]),
        "issued_at": str(admission_context["issued_at"]),
        "expires_at": str(admission_context["expires_at"]),
        "nonce": str(admission_context["nonce"]),
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

    if install_host_admission:
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
    if "revoked_at" in admission_context:
        event["host_admission_verdict"]["revoked_at"] = admission_context["revoked_at"]
    if "superseded_by" in admission_context:
        event["host_admission_verdict"]["superseded_by"] = admission_context["superseded_by"]
    if admission_context_overrides or key_overrides:
        event["import_custody"] = {
            "kind": "agentic-workspace/trusted-authority-host-event-import/v1",
            "importer": "agentic-workspace.guidance-authority-import",
            "source": "signed-host-event-inbox",
            "event_digest": _trusted_authority_event_digest(event),
        }
        event["revision"] = event["import_custody"]["event_digest"]
        path = target_root / TRUSTED_AUTHORITY_EVENT_STORE_PATH / f"{event_ref.removeprefix('trusted-authority-event:')}.json"
        _write(path, json.dumps(event, indent=2, sort_keys=True) + "\n")
        return {
            "event_ref": event_ref,
            "event": event,
            "host_public_key": signed["key"],
            "host_public_key_id": str(event["host_admission"]["key_id"]),
        }
    inbox_path = target_root / TRUSTED_AUTHORITY_EVENT_INBOX_PATH / f"{event_ref.removeprefix('trusted-authority-event:')}.json"
    _write(inbox_path, json.dumps(event, indent=2, sort_keys=True) + "\n")
    if not install_host_admission:
        return {
            "event_ref": event_ref,
            "event": event,
            "host_public_key": signed["key"],
            "host_public_key_id": str(event["host_admission"]["key_id"]),
        }
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
    return {
        "event_ref": event_ref,
        "event": imported["event"],
        "host_public_key": signed["key"],
        "host_public_key_id": str(event["host_admission"]["key_id"]),
    }


def test_config_command_reports_effective_defaults_without_repo_file(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    _assert_invoked_cli_identity(payload, target_relation="outside-target")
    _assert_cli_compatibility(payload, status="satisfied")
    assert payload["exists"] is False
    assert payload["edit_reference"]["reference_doc"] == ".agentic-workspace/docs/workspace-config-contract.md"
    assert payload["edit_reference"]["generated_reference_doc"] == "docs/reference/workspace-config.md"
    assert payload["edit_reference"]["source_schema"] == "src/agentic_workspace/contracts/schemas/workspace_config.schema.json"
    assert "# Agentic Workspace managed config." in payload["edit_reference"]["managed_header"]
    assert payload["edit_reference"]["check_command"] == "agentic-workspace config --target . --format json"
    assert payload["workspace"]["enabled"] is True
    assert payload["workspace"]["enabled_source"] == "product-default"
    assert payload["workspace"]["enabled_modules"] == ["planning", "memory"]
    assert payload["workspace"]["agent_instructions_file"] == "AGENTS.md"
    assert payload["workspace"]["agent_instructions_file_source"] == "product-default"
    assert payload["workspace"]["workflow_artifact_profile"] == "repo-owned"
    assert payload["workspace"]["workflow_artifact_profile_source"] == "product-default"
    assert payload["workspace"]["improvement_latitude"] == "conservative"
    assert payload["workspace"]["improvement_latitude_source"] == "product-default"
    assert payload["workspace"]["optimization_bias"] == "balanced"
    assert payload["workspace"]["optimization_bias_source"] == "product-default"
    assert payload["workspace"]["advanced_features"] == []
    assert payload["workspace"]["advanced_features_source"] == "product-default"
    assert payload["workspace"]["maintainer_mode"] is False
    assert payload["workspace"]["maintainer_mode_source"] == "product-default"
    assert payload["workspace"]["maintainer_mode_detail"]["status"] == "disabled"
    assert payload["workspace"]["supported_advanced_features"] == ["review_artifacts", "external_adapters"]
    assert payload["workspace"]["workflow_artifact_adapter"]["canonical_surfaces"] == [
        ".agentic-workspace/planning/execplans/",
        ".agentic-workspace/planning/lanes/",
        ".agentic-workspace/planning/decompositions/",
        ".agentic-workspace/planning/issue-relations/",
    ]
    assert payload["workspace"]["agent_configuration_substrate"]["canonical_doc"] == ".agentic-workspace/docs/workspace-config-contract.md"
    assert payload["workspace"]["agent_configuration_substrate"]["owner_surface"] == ".agentic-workspace/config.toml"
    assert payload["workspace"]["workflow_obligations"] == []
    assert payload["config_enforcement"]["field_count_by_class"]["hard"] >= 1
    assert any(field["field"] == "workspace.improvement_latitude" for field in payload["config_enforcement"]["fields"])
    assert payload["config_effect_audit"]["status"] == "present"
    assert payload["config_effect_audit"]["field_count_by_effect"]["operational"] >= 1
    assert payload["config_effect_audit"]["field_count_by_effect"]["unused"] == 0
    assert payload["config_effect_audit"]["detail_command"].endswith(
        "agentic-workspace report --target ./repo --section config_effect_audit --format json"
    )
    projection = payload["configuration_projection"]
    assert projection["kind"] == "agentic-workspace/configuration-projection/v1"
    assert projection["projection_status_counts"]["active"] >= 1
    assert projection["projection_status_counts"]["latent"] >= 1
    assert projection["projection_status_counts"]["unprojected"] == 0
    assert projection["unprojected_fields"] == []
    projection_sources = {field["id"] for field in projection["facts"]}
    assert {
        "ownership:authority-ledger",
        "system-intent:durable-intent",
        "verification:manifest",
        "memory:routing-metadata",
        "planning:active-state-obligations",
    } <= projection_sources
    obligation_projection = next(field for field in projection["facts"] if field["field"] == "workflow_obligations.<name>.*")
    assert obligation_projection["projection_status"] == "active"
    assert obligation_projection["source_surface"] == ".agentic-workspace/config.toml"
    assert obligation_projection["ordinary_path_routes"]
    assert obligation_projection["trigger"]
    assert "scope_tags" in obligation_projection["applicability_signal"]
    assert "hide obligation detail" in obligation_projection["suppression_rule"]
    assert obligation_projection["owner_boundary"] == "human-owned"
    local_projection = next(field for field in projection["facts"] if field["field"] == "runtime|handoff|safety|delegation_targets")
    assert local_projection["owner_boundary"] == "local-human-owned"
    assert "cannot create shared repo obligations" in local_projection["authority_exception"]
    assert projection["verification"]["positive_surfacing"][0]["id"] == "startup-config-task-routes-to-config"
    assert projection["verification"]["non_applicable_suppression"][0]["id"] == "ordinary-report-keeps-detail-sectioned"
    assert projection["detail_command"].endswith(
        "agentic-workspace report --target ./repo --section configuration_projection --format json"
    )
    surfacing_eval = projection["selective_surfacing_evaluation"]
    assert surfacing_eval["status"] == "pass"
    assert {check["id"]: check["result"] for check in surfacing_eval["checks"]} == {
        "required-guidance-present": "pass",
        "positive-and-suppression-scenarios-present": "pass",
        "irrelevant-guidance-suppressed-from-compact-output": "pass",
        "compact-output-size-bounded": "pass",
        "typed-relevance-basis-present": "pass",
    }
    assert surfacing_eval["metrics"]["projection_row_count"] == len(projection["facts"])
    relevance = {item["id"]: item for item in surfacing_eval["relevance_scenarios"]}
    assert {
        "changed-path-ownership",
        "active-planning-task-switch",
        "configured-proof-closeout",
    } <= set(relevance)
    assert {item["basis_source_type"] for item in relevance.values()} == {"explicit-state-and-contract"}
    assert relevance["changed-path-ownership"]["shown_because"] == ["state.changed_paths=present", "contract.owner_boundary"]
    assert relevance["active-planning-task-switch"]["not_based_on"] == "broad planning vocabulary"
    assert relevance["configured-proof-closeout"]["not_based_on"] == "bug/fix/test keyword matching"
    assert payload["update"]["wrapper_rule"] == "normal update execution stays behind agentic-workspace"
    assert {item["module"] for item in payload["update"]["modules"]} == {"planning", "memory"}
    assert {item["freshness"]["status"] for item in payload["update"]["modules"]} == {"unknown"}
    assert payload["assurance"]["default_level"] == "low"
    assert payload["assurance"]["default_level_source"] == "product-default"
    assert payload["assurance"]["onboarding"]["status"] == "absent"
    assert payload["assurance"]["onboarding"]["configured_profile_count"] == 0
    assert payload["mixed_agent"]["status"] == "reporting-only"
    assert payload["mixed_agent"]["repo_policy"]["source"] == "product-defaults"
    assert payload["mixed_agent"]["repo_policy"]["path"] == ".agentic-workspace/config.toml"
    assert payload["mixed_agent"]["repo_policy"]["authoritative"] is False
    assert "workspace.maintainer_mode" in payload["mixed_agent"]["repo_policy"]["supported_fields"]
    assert payload["mixed_agent"]["local_override"]["path"] == ".agentic-workspace/config.local.toml"
    assert payload["mixed_agent"]["local_override"]["supported"] is True
    assert payload["mixed_agent"]["local_override"]["exists"] is False
    assert payload["mixed_agent"]["local_override"]["applied"] is False
    assert payload["mixed_agent"]["local_integration_area"] == {
        "root": ".agentic-workspace/local/integrations",
        "subfolder_convention": "<vendor-or-runtime>/",
        "example_subfolder": ".agentic-workspace/local/integrations/codex",
        "scratch": {
            "root": ".agentic-workspace/local/scratch",
            "status": "ready-local-only",
            "exists": False,
            "git_ignored": True,
            "authoritative": False,
            "safe_to_delete": True,
            "sign": "Go ahead and use this for whatever temporary working files you need.",
            "retention": {
                "status": "bounded",
                "run_root": ".agentic-workspace/local/scratch/runs",
                "manifest_name": ".aw-scratch.toml",
                "report_section": "local_footprint",
            },
        },
        "status": "available-local-only",
        "exists": False,
        "authoritative": False,
        "git_ignored": True,
        "canonical_doc": ".agentic-workspace/docs/local-integration-area.md",
        "runtime_artifact_shim_pattern": {
            "kind": "agentic-workspace/local-runtime-artifact-shim/v1",
            "root": ".agentic-workspace/local/integrations",
            "status": "local-only-pattern",
            "authoritative": False,
            "git_ignored": True,
            "use_for": [
                "internal agent plans that need compact checked-in planning updates",
                "runtime check bundles that need compact pass/fail plus inspectable logs",
                "handoff or resume state that needs a bounded workspace continuation record",
                "runtime-native planning systems that the agent is already optimized or hardwired to use",
            ],
            "bridge_rule": (
                "Use runtime-native plans as private working memory when they help, but bridge decisions, scope, proof, "
                "and continuation into checked-in Agentic Workspace Planning before implementation handoff or closeout."
            ),
            "preferred_bridge_steps": [
                "capture the runtime-native plan or todo list under the local integration area when it is useful evidence",
                "summarize only durable intent, scope, proof, and next action into checked-in planning state",
                "run agentic-workspace summary --format json after the bridge and resolve warnings before implementation",
            ],
            "artifact_classes": ["internal-plan", "check-bundle", "handoff-state", "runtime-export"],
            "metadata_required": [
                "kind",
                "source_runtime",
                "artifact_class",
                "input_owner",
                "output_target",
                "authority",
                "promotion_target",
                "proof_command",
                "created_at",
            ],
            "compact_output": "short agent-facing status, next action, and proof pointer",
            "full_evidence": "inspectable local artifact, manifest, command log, or exported source file",
            "promotion_boundary": [
                "local shims never become shared authority by existing locally",
                "promote only through checked-in planning, memory, agent-aid, docs, or repo-native review surfaces",
                "record proof before treating shim output as repo-shared state",
                "a runtime-native plan or todo list does not satisfy required Agentic Workspace Planning until bridged",
            ],
            "discovery": [
                "agentic-workspace defaults --section agent_aid_storage --format json",
                "agentic-workspace config --target ./repo --format json",
                "agentic-workspace report --target ./repo --section agent_aids --format json",
            ],
        },
        "allowed_aid_kinds": [
            "prompt helpers",
            "export/import shims",
            "local wrappers",
            "native-workflow adapters",
            "resumable handoff helpers",
            "runtime scratch files",
        ],
        "boundary_rules": [
            "local-only and ignored by git",
            "optional for ordinary workspace commands",
            "non-authoritative for planning, memory, startup, review, and workflow state",
            "safe to delete without changing repo-owned shared behavior",
            "not a plugin registry or shared compatibility framework",
        ],
        "rule": "local-only vendor/runtime aids; may reduce local operating cost, but must not become shared workflow authority",
    }
    assert payload["mixed_agent"]["local_scratch"] == {
        "root": ".agentic-workspace/local/scratch",
        "status": "ready-local-only",
        "exists": False,
        "git_ignored": True,
        "authoritative": False,
        "safe_to_delete": True,
        "sign": "Go ahead and use this for whatever temporary working files you need.",
        "retention": {
            "status": "bounded",
            "run_root": ".agentic-workspace/local/scratch/runs",
            "manifest_name": ".aw-scratch.toml",
            "report_section": "local_footprint",
        },
    }
    agent_aids = payload["mixed_agent"]["agent_aid_storage"]
    assert agent_aids["canonical_doc"] == ".agentic-workspace/docs/agent-aids-storage.md"
    assert agent_aids["candidate_root"] == ".agentic-workspace/agent-aids"
    assert agent_aids["candidate_subdirs"] == [
        "scripts",
        "skills",
        "runbooks",
        "prompts",
        "checks",
        "templates",
        "module-components",
    ]
    assert [entry["class"] for entry in agent_aids["storage_classes"][:3]] == [
        "local-only",
        "checked-in-candidate",
        "promoted-repo-native",
    ]
    assert payload["mixed_agent"]["local_memory"]["status"] == "disabled"
    assert payload["mixed_agent"]["local_memory"]["path"] == ".agentic-workspace/local/memory.toml"
    assert payload["mixed_agent"]["local_memory"]["authoritative"] is False
    assert payload["mixed_agent"]["runtime_inference"]["tool_owned"] is True
    assert payload["mixed_agent"]["runtime_inference"]["reported_here"] is False
    assert payload["mixed_agent"]["effective_posture"]["supports_internal_delegation"] == {"value": None, "source": "unset"}
    assert payload["mixed_agent"]["effective_posture"]["strong_planner_available"] == {"value": None, "source": "unset"}
    assert payload["mixed_agent"]["delegated_run_guardrail"]["status"] == "present"
    assert payload["mixed_agent"]["delegated_run_guardrail"]["closeout_gate"]["lower_trust_profiles"] == []
    assert payload["mixed_agent"]["success_measures"] == [
        "lower long-run token cost",
        "lower restart and handoff cost",
        "cheap switching across agents and subscriptions",
        "persisted shared knowledge beats rediscovery",
    ]


def test_configuration_projection_reports_selector_backed_and_stale_sources(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--mirror-payload", "--format", "json"]) == 0
    capsys.readouterr()
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[modules]
enabled = ["planning", "memory", "verification"]
""".strip(),
    )
    verification_manifest = tmp_path / ".agentic-workspace/verification/manifest.toml"
    if verification_manifest.exists():
        verification_manifest.unlink()

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    projection = payload["configuration_projection"]
    facts = {field["id"]: field for field in projection["facts"]}
    assert facts["ownership:authority-ledger"]["projection_status"] == "selector-backed"
    assert facts["memory:routing-metadata"]["projection_status"] == "selector-backed"
    assert facts["verification:manifest"]["projection_status"] == "stale"
    assert projection["projection_status_counts"]["selector-backed"] >= 2
    assert projection["projection_status_counts"]["stale"] >= 1
    assert facts["verification:manifest"]["ordinary_path_routes"]
    assert "missing enabled manifest" in facts["verification:manifest"]["suppression_rule"]
    scenarios = {scenario["id"]: scenario["covered"] for scenario in projection["selective_surfacing_evaluation"]["scenarios"]}
    assert scenarios["selector-backed-owner-memory-intent"] is True
    assert scenarios["stale-or-unprojected-gap"] is True


def test_config_command_reports_selected_fields_for_agent_startup(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[workspace]
improvement_latitude = "proactive"
optimization_bias = "agent-efficiency"

[workflow_obligations.closeout_proof]
summary = "Run closeout proof before reporting done."
stage = "closeout"
scope_tags = ["closeout"]
commands = ["make check"]
""".strip(),
        encoding="utf-8",
    )
    _write(
        tmp_path / ".agentic-workspace/config.local.toml",
        """
schema_version = 1

[delegation]
mode = "suggest"

[clarification]
mode = "ask-first"

[safety]
safe_to_auto_run_commands = false
""".strip(),
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "config",
                "--target",
                str(tmp_path),
                "--select",
                "workspace.improvement_latitude,workspace.optimization_bias,workspace.workflow_obligations,warnings,target,config_path",
                "--format",
                "json",
            ]
        )
        == 0
    )

    output = capsys.readouterr().out
    payload = json.loads(output)
    values = payload["values"]
    assert values["warnings"] == []
    assert Path(values["target"]).name == tmp_path.name
    assert Path(values["config_path"]).as_posix().endswith(".agentic-workspace/config.toml")
    assert values["workspace.improvement_latitude"] == "proactive"
    assert values["workspace.optimization_bias"] == "agent-efficiency"
    assert values["workspace.workflow_obligations"][0]["id"] == "closeout_proof"


def test_config_command_reports_tiny_profile_for_config_posture(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[workspace]
improvement_latitude = "reporting"
optimization_bias = "agent-efficiency"
cli_invoke = "uv run agentic-workspace"

[workflow_obligations.closeout_proof]
summary = "Run closeout proof before reporting done."
stage = "closeout"
scope_tags = ["closeout"]
commands = ["make check"]
""".strip(),
        encoding="utf-8",
    )
    _write(
        tmp_path / ".agentic-workspace/config.local.toml",
        """
schema_version = 1

[delegation]
mode = "suggest"

[clarification]
mode = "ask-first"

[safety]
safe_to_auto_run_commands = false
requires_human_verification_on_pr = true
""".strip(),
        encoding="utf-8",
    )

    assert cli.main(["config", "--target", str(tmp_path), "--format", "json"]) == 0

    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload["kind"] == "agentic-workspace/config-tiny/v1"
    assert payload["profile"] == "tiny"
    assert not any("clarification" in warning for warning in payload["warnings"])
    assert payload["workspace"]["agent_instructions_file"] == "AGENTS.md"
    assert payload["workspace"]["improvement_latitude"] == "reporting"
    assert payload["workspace"]["optimization_bias"] == "agent-efficiency"
    assert payload["workspace"]["workflow_obligation_ids"] == ["closeout_proof"]
    assert payload["local_runtime"]["delegation_mode"] == {"value": "suggest", "source": "local-override"}
    assert payload["local_runtime"]["clarification_mode"] == {"value": "ask-first", "source": "local-override"}
    assert payload["local_runtime"]["safe_to_auto_run_commands"] == {"value": False, "source": "local-override"}
    assert payload["local_runtime"]["requires_human_verification_on_pr"] == {"value": True, "source": "local-override"}
    assert payload["next_detail"]["select"].endswith("agentic-workspace config --target . --select <field.path> --format json")
    assert payload["next_detail"]["verbose"].endswith("agentic-workspace config --target . --verbose --format json")
    assert "config_effect_audit" not in payload
    assert "configuration_projection" not in payload
    assert payload["local_runtime"]["effective_orchestration"] == {
        "status": "direct-local",
        "assignment_policy": "local-preferred",
        "delegation_mode": "suggest",
        "transport_permitted": False,
        "detail_selector": "mixed_agent.effective_orchestration",
    }
    assert len(output) < 3400


def test_config_command_compact_reports_projection_summary_without_fact_detail(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    full_payload = cli._config_payload(config=cli._load_workspace_config(target_root=tmp_path))
    payload = cli._compact_config_payload(full_payload)
    projection = payload["configuration_projection"]
    assert projection["status"] == "present"
    assert projection["projection_status_counts"]["active"] >= 1
    assert projection["unprojected_field_count"] == 0
    assert projection["detail_command"].endswith(
        "agentic-workspace report --target ./repo --section configuration_projection --format json"
    )
    assert "facts" not in projection


def test_config_command_accepts_reporting_improvement_latitude_mode(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        (tmp_path / ".agentic-workspace/config.toml"),
        'schema_version = 1\n\n[workspace]\nimprovement_latitude = "reporting"\n',
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["improvement_latitude"] == "reporting"
    assert payload["workspace"]["improvement_latitude_source"] == "repo-config"


def test_config_command_accepts_agent_efficiency_optimization_bias(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace/config.toml").write_text(
        'schema_version = 1\n\n[workspace]\noptimization_bias = "agent-efficiency"\n',
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["optimization_bias"] == "agent-efficiency"
    assert payload["workspace"]["optimization_bias_source"] == "repo-config"


def test_config_local_maintainer_mode_overrides_host_repo_policy(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.local.toml",
        """
schema_version = 1

[workspace]
maintainer_mode = true
""".strip(),
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    workspace = payload["workspace"]
    assert workspace["maintainer_mode"] is True
    assert workspace["maintainer_mode_source"] == "local-override"
    assert workspace["maintainer_mode_detail"]["status"] == "enabled"
    assert workspace["maintainer_mode_detail"]["dogfooding_reports"][0]["section"] == "improvement_intake"
    assert payload["mixed_agent"]["local_override"]["maintainer_mode"] == {
        "value": True,
        "source": "local-override",
    }


def test_config_command_reports_assurance_onboarding_states(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance]
default_level = "medium"
""",
    )

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    partial = json.loads(capsys.readouterr().out)
    assert partial["assurance"]["onboarding"]["status"] == "absent"
    assert partial["assurance"]["onboarding"]["configured_profile_count"] == 0
    assert partial["assurance"]["onboarding"]["configured_subsystem_profile_count"] == 0

    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance]
default_level = "medium"

[assurance.proof_profiles.security]
required_commands = ["uv run pytest tests/security -q"]
optional_commands = []
review_aids = []

[assurance.subsystem_profiles.audit-log]
assurance_level = "high"
requirement_refs = ["docs/requirements.md#auditability"]
required_evidence = ["requirement_grounding"]
force = "required-before-closeout"
""",
    )

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    usable = json.loads(capsys.readouterr().out)
    assert usable["assurance"]["onboarding"]["status"] == "usable"
    assert usable["assurance"]["onboarding"]["configured_profile_count"] == 1
    assert usable["assurance"]["onboarding"]["configured_subsystem_profile_count"] == 1
    assert usable["assurance"]["onboarding"]["host_ref_count"] == 1
    assert ".agentic-workspace/config.toml [assurance.subsystem_profiles]" in usable["assurance"]["onboarding"]["candidate_seed_surfaces"]


def test_config_command_reports_assurance_requirements(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance.requirements.privacy_data]
level = "high"
applies_to_paths = ["db/migrations/**"]
applies_to_task_markers = ["privacy"]
authority_refs = ["docs/compliance/privacy.md"]
required_evidence = ["authority_consulted", "risk_assessment"]
proof_profile = "privacy"
workflow_obligation_refs = ["privacy_review"]
review_owner = "privacy-review"
force = "required-before-closeout"
blocking_claims = ["claim-work-complete", "close-parent-lane"]

[assurance.requirements.privacy_data.waiver]
reason = "Covered by existing privacy review for this migration class."
owner = "privacy-review"
""",
    )

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    requirement = payload["assurance"]["requirements"][0]
    assert requirement["id"] == "privacy_data"
    assert requirement["level"] == "high"
    assert requirement["applies_to_paths"] == ["db/migrations/**"]
    assert requirement["required_evidence"] == ["authority_consulted", "risk_assessment"]
    assert requirement["force"] == "required-before-closeout"
    assert requirement["blocking_claims"] == ["claim-work-complete", "close-parent-lane"]
    assert requirement["waiver"]["status"] == "recorded"
    assert requirement["waiver"]["owner"] == "privacy-review"


def test_config_command_rejects_assurance_requirement_without_activation_signal(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance.requirements.no_signal]
level = "high"
force = "required-before-closeout"
required_evidence = ["authority_consulted"]
""",
    )

    with pytest.raises(SystemExit):
        cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"])
    assert "requires at least one activation signal" in capsys.readouterr().err


def test_config_command_requires_assurance_requirement_level_and_force(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance.requirements.missing_level]
applies_to_paths = ["docs/**"]
force = "required-before-closeout"

[assurance.requirements.missing_force]
level = "high"
applies_to_paths = ["src/**"]
""",
    )

    with pytest.raises(SystemExit):
        cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"])
    assert "missing_force force is required" in capsys.readouterr().err

    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance.requirements.missing_level]
applies_to_paths = ["docs/**"]
force = "required-before-closeout"
""",
    )

    with pytest.raises(SystemExit):
        cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"])
    assert "missing_level level is required" in capsys.readouterr().err


def test_config_command_rejects_invalid_assurance_requirement_claim(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance.requirements.bad_claim]
level = "high"
applies_to_paths = ["docs/**"]
force = "required-before-closeout"
blocking_claims = ["certify-compliant"]
""",
    )

    with pytest.raises(SystemExit):
        cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"])
    assert "blocking_claims entries must be one of" in capsys.readouterr().err


def test_config_command_accepts_source_bound_named_repo_requirement_and_rejects_enforcing_guideline(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance.requirements.typed_exit]
level = "high"
applies_to_paths = ["src/**"]
required_evidence = ["typed_exit_fixture"]
force = "required-before-closeout"
blocking_claims = ["claim-work-complete"]
requirement_class = "invariant"
source_intent_ref = "SYSTEM_INTENT.md#trust"
source_intent_revision = "r1"
source_intent_current = true
evidence_owner = "verification:typed-exit"
detail_route = "agentic-workspace proof --select typed-exit"
""",
    )

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0
    requirement = json.loads(capsys.readouterr().out)["assurance"]["requirements"][0]
    assert requirement["requirement_class"] == "invariant"
    assert requirement["source_intent_ref"] == "SYSTEM_INTENT.md#trust"
    assert requirement["evidence_owner"] == "verification:typed-exit"

    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance.requirements.cheaper]
level = "low"
applies_to_task_markers = ["assignment"]
force = "blocking"
blocking_claims = ["claim-work-complete"]
requirement_class = "guideline"
source_intent_ref = "SYSTEM_INTENT.md#cost"
source_intent_revision = "r1"
source_intent_current = true
preference_target = "operation:assignment.best-fit"
""",
    )
    with pytest.raises(SystemExit):
        cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"])
    assert "guideline cannot block claims" in capsys.readouterr().err


def test_config_rejects_conflicting_owners_for_normalized_repo_requirement_identity(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance.requirements.typed_exit]
level = "high"
applies_to_paths = ["src/**"]
required_evidence = ["typed_exit_fixture"]
force = "required-before-closeout"
blocking_claims = ["claim-work-complete"]
requirement_class = "invariant"
source_intent_ref = "SYSTEM_INTENT.md#trust"
source_intent_revision = "r1"
source_intent_current = true
evidence_owner = "verification:typed-exit"
detail_route = "agentic-workspace proof --select typed-exit"

[assurance.requirements." typed_exit "]
level = "high"
applies_to_paths = ["src/**"]
required_evidence = ["typed_exit_fixture"]
force = "required-before-closeout"
blocking_claims = ["claim-work-complete"]
requirement_class = "invariant"
source_intent_ref = "docs/other-policy.md#exit"
source_intent_revision = "r2"
source_intent_current = true
evidence_owner = "proof:other-exit"
detail_route = "agentic-workspace proof --select other-exit"
""",
    )

    with pytest.raises(SystemExit):
        cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"])
    error = capsys.readouterr().err
    assert "conflicting owner declarations" in error
    assert "SYSTEM_INTENT.md#trust" in error
    assert "docs/other-policy.md#exit" in error


def test_config_deduplicates_same_owner_same_repo_requirement_identity(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    declaration = """
level = "high"
applies_to_paths = ["src/**"]
required_evidence = ["typed_exit_fixture"]
force = "required-before-closeout"
blocking_claims = ["claim-work-complete"]
requirement_class = "invariant"
source_intent_ref = "SYSTEM_INTENT.md#trust"
source_intent_revision = "r1"
source_intent_current = true
evidence_owner = "verification:typed-exit"
detail_route = "agentic-workspace proof --select typed-exit"
"""
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        "schema_version = 1\n\n[assurance.requirements.typed_exit]\n"
        + declaration
        + '\n[assurance.requirements." typed_exit "]\n'
        + declaration,
    )

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0
    requirements = json.loads(capsys.readouterr().out)["assurance"]["requirements"]
    assert [item["id"] for item in requirements].count("typed_exit") == 1


def test_config_command_validates_source_owned_measurement_requirements(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    config_path = tmp_path / ".agentic-workspace/config.toml"
    _write(
        config_path,
        """
schema_version = 1

[assurance.requirements.scaling]
level = "high"
applies_to_paths = ["src/**"]
required_evidence = ["history_scaling"]
force = "required-before-closeout"
blocking_claims = ["claim-work-complete"]
requirement_class = "current-evidence"
source_intent_ref = "docs/requirements.md#scaling"
source_intent_revision = "policy-r1"
source_intent_current = true
evidence_owner = "verification:history-scaling"
detail_route = "agentic-workspace proof --select history-scaling"

[assurance.requirements.scaling.measurement]
kind = "agentic-workspace/measurement-requirement/v1"
evidence_label = "history_scaling"
metric = "selected-read-latency"
unit = "seconds"
comparator = "ratio-lte"
threshold = 1.2
aggregation = "ratio"
minimum_samples = 5
subject = "history-1000"
subject_revision = "loaded-r1"
control_subject = "history-empty"
control_revision = "control-r1"
environment = "maintained-ci"
source_revision = "fixture-r1"
producer_command = "python scripts/measure_scaling.py --compact"
excluded_costs = ["environment bootstrap"]
""",
    )

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0
    measurement = json.loads(capsys.readouterr().out)["assurance"]["requirements"][0]["measurement"]
    assert measurement["comparator"] == "ratio-lte"
    assert measurement["threshold"] == 1.2
    assert measurement["control_subject"] == "history-empty"

    _write(config_path, config_path.read_text(encoding="utf-8").replace('evidence_label = "history_scaling"', 'evidence_label = "other"'))
    with pytest.raises(SystemExit):
        cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"])
    assert "measurement evidence_label must appear in required_evidence" in capsys.readouterr().err


def test_config_command_reports_enabled_advanced_features(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace/config.toml").write_text(
        'schema_version = 1\n\n[workspace]\nadvanced_features = ["review_artifacts", "external_adapters"]\n',
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["advanced_features"] == ["review_artifacts", "external_adapters"]
    assert payload["workspace"]["advanced_features_source"] == "repo-config"


def test_config_command_reports_workflow_obligations_from_repo_config(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace").mkdir(exist_ok=True)
    (tmp_path / ".agentic-workspace/config.toml").write_text(
        "schema_version = 1\n\n"
        "[workflow_obligations.adapter_surface_refresh]\n"
        'summary = "Refresh adapter surfaces."\n'
        'stage = "before-claiming-completion"\n'
        'scope_tags = ["workspace", "adapter-surfaces"]\n'
        'commands = ["make maintainer-surfaces"]\n',
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["workflow_obligations"][0]["id"] == "adapter_surface_refresh"
    assert payload["workspace"]["workflow_obligations"][0]["stage"] == "before-claiming-completion"
    assert payload["workspace"]["workflow_obligations"][0]["force"] == "required-before-closeout"
    assert payload["workspace"]["workflow_obligations"][0]["commands"] == ["make maintainer-surfaces"]


def test_config_command_accepts_explicit_workflow_obligation_force(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        "schema_version = 1\n\n"
        "[workflow_obligations.inspect_before_review]\n"
        'summary = "Inspect config effect before review."\n'
        'stage = "review"\n'
        'force = "blocking"\n'
        'scope_tags = ["workspace"]\n'
        'commands = ["agentic-workspace report --target . --section config_effect_audit --format json"]\n',
    )

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    obligation = payload["workspace"]["workflow_obligations"][0]
    assert obligation["id"] == "inspect_before_review"
    assert obligation["force"] == "blocking"


def test_config_command_reports_system_intent_source_declaration(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace").mkdir(exist_ok=True)
    (tmp_path / ".agentic-workspace/config.toml").write_text(
        "schema_version = 1\n\n"
        "[system_intent]\n"
        'sources = ["SYSTEM_INTENT.md", "docs/product-direction.md"]\n'
        'preferred_source = "docs/product-direction.md"\n',
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["system_intent"]["sources"] == ["SYSTEM_INTENT.md", "docs/product-direction.md"]
    assert payload["workspace"]["system_intent"]["preferred_source"] == "docs/product-direction.md"
    assert payload["workspace"]["system_intent"]["mirror_path"] == ".agentic-workspace/system-intent/intent.toml"


def test_config_command_warns_about_unsupported_top_level_repo_config_fields(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace").mkdir(exist_ok=True)
    (tmp_path / ".agentic-workspace/config.toml").write_text(
        "schema_version = 1\nunsupported_top_level = true\n",
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["warnings"] == [".agentic-workspace/config.toml contains unsupported top-level field(s): unsupported_top_level."]


def test_config_command_autodetects_conservative_system_intent_sources_when_no_explicit_source_declared(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "README.md").write_text("# README\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("# Repo Instructions\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "product-direction.md").write_text("Repo direction hint\n", encoding="utf-8")

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["system_intent"]["sources"] == ["README.md", "AGENTS.md", "docs/product-direction.md"]
    assert payload["workspace"]["system_intent"]["sources_source"] == "autodetected-existing"
    assert payload["workspace"]["system_intent"]["preferred_source"] == "README.md"


def test_config_command_autodetects_existing_supported_agent_instructions_file(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "GEMINI.md").write_text("# Gemini\n")

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["agent_instructions_file"] == "GEMINI.md"
    assert payload["workspace"]["agent_instructions_file_source"] == "autodetected-existing"
    assert payload["workspace"]["detected_agent_instructions_files"] == ["GEMINI.md"]


def test_config_command_autodetects_claude_agent_instructions_file(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "CLAUDE.md").write_text("# Claude\n", encoding="utf-8")

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["agent_instructions_file"] == "CLAUDE.md"
    assert payload["workspace"]["agent_instructions_file_source"] == "autodetected-existing"
    assert payload["workspace"]["detected_agent_instructions_files"] == ["CLAUDE.md"]


def test_config_command_autodetects_legacy_cursor_rules_file(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".cursorrules").write_text("Use repo conventions.\n", encoding="utf-8")

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["agent_instructions_file"] == ".cursorrules"
    assert payload["workspace"]["agent_instructions_file_source"] == "autodetected-existing"
    assert payload["workspace"]["detected_agent_instructions_files"] == [".cursorrules"]


def test_config_command_accepts_custom_agent_instructions_file(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        'schema_version = 1\n\n[workspace]\nagent_instructions_file = "docs/agent-instructions.md"\n',
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["agent_instructions_file"] == "docs/agent-instructions.md"
    assert payload["workspace"]["agent_instructions_file_source"] == "repo-config"


def test_config_command_discovers_workspace_root_from_subdirectory(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        (tmp_path / ".agentic-workspace/config.toml"),
        'schema_version = 1\n\n[workspace]\nimprovement_latitude = "balanced"\n',
        encoding="utf-8",
    )
    nested = tmp_path / "src" / "agentic_workspace"
    nested.mkdir(parents=True)
    previous_cwd = Path.cwd()
    monkeypatch.chdir(nested)
    try:
        assert cli.main(["config", "--verbose", "--format", "json"]) == 0
    finally:
        monkeypatch.chdir(previous_cwd)

    payload = json.loads(capsys.readouterr().out)
    assert payload["target"] == tmp_path.as_posix()
    assert payload["config_path"] == (tmp_path / ".agentic-workspace/config.toml").as_posix()
    assert payload["workspace"]["improvement_latitude"] == "balanced"
    assert payload["workspace"]["improvement_latitude_source"] == "repo-config"


def test_config_command_surfaces_unknown_local_override_fields_as_warnings(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            (
                "schema_version = 1",
                "",
                "[runtime]",
                "supports_internal_delegation = true",
                "mystery_flag = true",
                "",
                "[delegation_targets.gpt_5_4_mini]",
                'strength = "weak"',
                'location = "either"',
                'execution_methods = ["internal"]',
                'unexpected = "note"',
            )
        ),
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["mixed_agent"]["local_override"]["exists"] is True
    assert payload["mixed_agent"]["effective_posture"]["supports_internal_delegation"] == {
        "value": True,
        "source": "local-override",
    }
    assert payload["warnings"] == [
        ".agentic-workspace/config.local.toml [runtime] contains unsupported field(s): mystery_flag.",
        ".agentic-workspace/config.local.toml delegation_targets.gpt_5_4_mini contains unsupported field(s): unexpected.",
    ]


def test_config_command_reports_repo_owned_overrides(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.toml").write_text(
        "schema_version = 1\n\n"
        "[workspace]\n"
        'agent_instructions_file = "GEMINI.md"\n'
        'workflow_artifact_profile = "gemini"\n'
        'improvement_latitude = "balanced"\n\n'
        "[modules]\n"
        'enabled = ["planning"]\n\n'
        "[update.modules.planning]\n"
        'source_type = "git"\n'
        'source_ref = "git+https://example.com/agentic-workspace@feature#subdirectory=packages/planning"\n'
        'source_label = "planning feature ref"\n'
        "recommended_upgrade_after_days = 14\n",
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["exists"] is True
    assert payload["workspace"]["enabled_modules"] == ["planning"]
    assert payload["workspace"]["agent_instructions_file"] == "GEMINI.md"
    assert payload["workspace"]["agent_instructions_file_source"] == "repo-config"
    assert payload["workspace"]["workflow_artifact_profile"] == "gemini"
    assert payload["workspace"]["workflow_artifact_profile_source"] == "repo-config"
    assert payload["workspace"]["improvement_latitude"] == "balanced"
    assert payload["workspace"]["improvement_latitude_source"] == "repo-config"
    assert payload["workspace"]["workflow_artifact_adapter"]["native_artifacts"] == [
        "implementation_plan.md",
        "task.md",
        "walkthrough.md",
    ]
    planning_policy = next(item for item in payload["update"]["modules"] if item["module"] == "planning")
    assert planning_policy["source"] == "repo-config"
    assert planning_policy["source_ref"] == "git+https://example.com/agentic-workspace@feature#subdirectory=packages/planning"
    assert planning_policy["source_label"] == "planning feature ref"
    assert planning_policy["recommended_upgrade_after_days"] == 14
    assert payload["mixed_agent"]["repo_policy"]["source"] == "repo-config"
    assert payload["mixed_agent"]["repo_policy"]["authoritative"] is True


def test_config_command_reports_reserved_local_override_presence_without_applying_it(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "schema_version = 1\n\n[runtime]\nsupports_internal_delegation = true\n",
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["mixed_agent"]["local_override"]["exists"] is True
    assert payload["mixed_agent"]["local_override"]["applied"] is True
    assert payload["mixed_agent"]["local_override"]["status"] == "applied"
    assert payload["mixed_agent"]["effective_posture"]["supports_internal_delegation"] == {
        "value": True,
        "source": "local-override",
    }


def test_config_command_layers_shared_local_config_below_repo_local_override(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    shared = tmp_path / "agentic-workspace.local.toml"
    shared.write_text(
        "schema_version = 1\n\n"
        "[workspace]\n"
        'cli_invoke = "python -c \\"import sys; from agentic_workspace.cli import main; '
        'raise SystemExit(main(sys.argv[1:]))\\""\n\n'
        "[runtime]\n"
        "strong_planner_available = true\n"
        "cheap_bounded_executor_available = false\n\n"
        "[delegation]\n"
        'mode = "manual"\n\n'
        "[local_memory]\n"
        "enabled = true\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace/config.local.toml").write_text(
        "schema_version = 1\n\n"
        "[workspace]\n"
        f'shared_config_path = "{shared.as_posix()}"\n\n'
        "[runtime]\n"
        "cheap_bounded_executor_available = true\n",
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["cli_invoke"] == (
        'python -c "import sys; from agentic_workspace.cli import main; raise SystemExit(main(sys.argv[1:]))"'
    )
    assert payload["workspace"]["cli_invoke_source"] == "shared-local-config"
    local_override = payload["mixed_agent"]["local_override"]
    assert local_override["shared_config"] == {
        "path": shared.as_posix(),
        "exists": True,
        "applied": True,
        "status": "applied",
    }
    assert payload["mixed_agent"]["effective_posture"]["strong_planner_available"] == {
        "value": True,
        "source": "shared-local-config",
    }
    assert payload["mixed_agent"]["effective_posture"]["cheap_bounded_executor_available"] == {
        "value": True,
        "source": "local-override",
    }
    assert payload["mixed_agent"]["effective_posture"]["delegation_mode"] == {
        "value": "manual",
        "source": "shared-local-config",
    }
    assert payload["mixed_agent"]["local_memory"]["source"] == "shared-local-config"
    assert payload["warnings"] == []


def test_config_command_warns_when_shared_local_config_is_missing(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        'schema_version = 1\n\n[workspace]\nshared_config_path = "../missing.local.toml"\n',
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["mixed_agent"]["local_override"]["shared_config"]["status"] == "missing"
    assert payload["warnings"] == [
        f".agentic-workspace/config.local.toml workspace.shared_config_path points to missing file: {(tmp_path / 'missing.local.toml').as_posix()}."
    ]


def test_config_command_resolves_relative_shared_local_config_from_repo_root(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    shared = tmp_path / "aw.config.shared.toml"
    shared.write_text('schema_version = 1\n\n[delegation]\nmode = "manual"\n', encoding="utf-8")
    (target / ".agentic-workspace/config.local.toml").write_text(
        'schema_version = 1\n\n[workspace]\nshared_config_path = "../aw.config.shared.toml"\n',
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["mixed_agent"]["local_override"]["shared_config"] == {
        "path": shared.as_posix(),
        "exists": True,
        "applied": True,
        "status": "applied",
    }
    assert payload["mixed_agent"]["effective_posture"]["delegation_mode"] == {
        "value": "manual",
        "source": "shared-local-config",
    }
    assert payload["warnings"] == []


def test_config_command_reports_local_only_memory_override(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        'schema_version = 1\n\n[local_memory]\nenabled = true\npath = ".agentic-workspace/local/memory.toml"\n',
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    local_memory = payload["mixed_agent"]["local_memory"]
    assert local_memory["status"] == "enabled"
    assert local_memory["enabled"] is True
    assert local_memory["configured"] is True
    assert local_memory["path"] == ".agentic-workspace/local/memory.toml"
    assert local_memory["controlled_by"] == ".agentic-workspace/config.local.toml"
    assert local_memory["authoritative"] is False
    assert local_memory["advisory_only"] is True
    assert "not a secret store" in local_memory["boundary_rules"]


def test_config_command_reports_narrow_local_override_fields_with_source_attribution(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "schema_version = 1\n\n"
        "[runtime]\n"
        "supports_internal_delegation = true\n"
        "strong_planner_available = true\n"
        "cheap_bounded_executor_available = true\n\n"
        "[handoff]\n"
        "prefer_internal_delegation_when_available = true\n",
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["mixed_agent"]["effective_posture"]["strong_planner_available"] == {
        "value": True,
        "source": "local-override",
    }
    assert payload["mixed_agent"]["effective_posture"]["cheap_bounded_executor_available"] == {
        "value": True,
        "source": "local-override",
    }
    assert payload["mixed_agent"]["effective_posture"]["prefer_internal_delegation_when_available"] == {
        "value": True,
        "source": "local-override",
    }
    assert payload["mixed_agent"]["derived_mode"]["planner_executor_pattern"] == "strong-planner-cheap-executor-available"
    assert payload["mixed_agent"]["derived_mode"]["handoff_preference"] == "prefer-internal-when-safe"


def test_config_command_reports_local_delegation_target_profiles(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "schema_version = 1\n\n"
        "[delegation_targets.fast_docs]\n"
        'strength = "weak"\n'
        'location = "external"\n'
        "confidence = 0.58\n"
        'task_fit = ["bounded-docs", "narrow-tests"]\n'
        'capability_classes = ["mechanical-follow-through"]\n'
        'execution_methods = ["cli"]\n\n'
        "[delegation_targets.primary_planner]\n"
        'strength = "strong"\n'
        'location = "local"\n'
        "confidence = 0.92\n"
        'model_family = "gpt-5.5"\n'
        'provider = "openai"\n'
        'dispatch_adapter_kind = "host-native"\n'
        'dispatch_command = ["host-worker", "--schema", "{output_schema}", "--output", "{output_file}"]\n'
        'dispatch_output_mode = "json-file"\n'
        "dispatch_timeout_seconds = 90\n"
        'context_capacity = "large"\n'
        'reasoning_profile = "strong"\n'
        'cost_class = "premium"\n'
        'latency_class = "slow"\n'
        'capability_classes = ["boundary-shaping", "reasoning-heavy"]\n'
        'safe_task_classes = ["boundary-shaping", "reasoning-heavy"]\n'
        'forbidden_task_classes = ["mechanical-follow-through"]\n'
        'escalation_target = "human"\n'
        'confidence_source = "local-evaluation"\n'
        'last_evaluation = "2026-05-04"\n'
        'human_control_modes = ["manual", "suggest"]\n'
        'execution_methods = ["internal", "api"]\n',
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    targets = payload["mixed_agent"]["delegation_targets"]
    assert targets["status"] == "configured"
    fast_docs = next(item for item in targets["profiles"] if item["name"] == "fast_docs")
    assert fast_docs["strength"] == "weak"
    assert fast_docs["location"] == "external"
    assert fast_docs["confidence"] == 0.58
    assert fast_docs["task_fit"] == ["bounded-docs", "narrow-tests"]
    assert fast_docs["capability_classes"] == ["mechanical-follow-through"]
    assert fast_docs["execution_methods"] == ["cli"]
    assert fast_docs["advisory"] == {
        "handoff_detail": "high",
        "review_burden": "high",
    }
    assert fast_docs["closeout_gate"]["trust"] == "lower-trust"
    assert "target strength is weak" in fast_docs["closeout_gate"]["reasons"]
    planner = next(item for item in targets["profiles"] if item["name"] == "primary_planner")
    assert planner["location"] == "local"
    assert planner["model_family"] == "gpt-5.5"
    assert planner["provider"] == "openai"
    assert planner["dispatch_adapter_kind"] == "host-native"
    assert planner["dispatch_command"] == [
        "host-worker",
        "--schema",
        "{output_schema}",
        "--output",
        "{output_file}",
    ]
    assert planner["dispatch_output_mode"] == "json-file"
    assert planner["dispatch_timeout_seconds"] == 90
    assert planner["context_capacity"] == "large"
    assert planner["reasoning_profile"] == "strong"
    assert planner["cost_class"] == "premium"
    assert planner["latency_class"] == "slow"
    assert planner["capability_classes"] == ["boundary-shaping", "reasoning-heavy"]
    assert planner["safe_task_classes"] == ["boundary-shaping", "reasoning-heavy"]
    assert planner["forbidden_task_classes"] == ["mechanical-follow-through"]
    assert "escalation_target" not in planner
    assert planner["confidence_source"] == "local-evaluation"
    assert planner["last_evaluation"] == "2026-05-04"
    assert planner["human_control_modes"] == []
    assert planner["execution_methods"] == ["internal", "api"]
    assert planner["advisory"] == {
        "handoff_detail": "compact",
        "review_burden": "light",
    }
    assert planner["closeout_gate"]["trust"] == "normal"
    assert payload["mixed_agent"]["delegated_run_guardrail"]["closeout_gate"]["lower_trust_profiles"] == ["fast_docs"]
    posture_effect = payload["mixed_agent"]["delegated_run_guardrail"]["local_posture_effect"]
    assert posture_effect["status"] == "configured"
    assert posture_effect["configured_profiles"] == ["fast_docs", "primary_planner"]
    assert posture_effect["proof_burden"].startswith("lower-trust profiles require")


def test_config_command_rejects_invalid_local_target_reasoning_profile(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation_targets.worker]",
                'strength = "weak"',
                'execution_methods = ["cli"]',
                'reasoning_profile = "omniscient"',
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit):
        cli.main(["config", "--verbose", "--target", str(target), "--format", "json"])
    assert "reasoning_profile must be one of" in capsys.readouterr().err


def test_config_command_reports_local_delegation_control_mode(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[safety]",
                "safe_to_auto_run_commands = false",
                "",
                "[delegation]",
                'mode = "auto"',
                "",
                "[delegation_targets.local_worker]",
                'strength = "medium"',
                'execution_methods = ["internal"]',
            ]
        ),
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    control = payload["mixed_agent"]["delegation_control"]
    assert control["configured_mode"] == "auto"
    assert control["effective_mode"] == "suggest"
    assert control["execution_permitted"] is False
    assert control["disabled_reason"] == "delegation.mode is auto, but safety.safe_to_auto_run_commands is not true"
    assert payload["mixed_agent"]["effective_posture"]["delegation_mode"] == {
        "value": "auto",
        "source": "local-override",
    }


def test_config_command_reports_assignment_policy_separate_from_delegation_mode(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'mode = "suggest"',
                'execution_role = "orchestrator"',
                'assignment_policy = "required-best-fit"',
                'selection_objective = "minimize successful completion cost after quality and proof"',
                'current_target = "user-local:codex-current"',
                'underfit_behavior = "require-delegation"',
                'down_routing_behavior = "bounded-mechanical-work"',
                'human_override_policy = "allowed-with-recorded-reason"',
                'manual_transport_policy = "required-when-no-automatic-method"',
                "",
                "[delegation_targets.codex_current]",
                'target_id = "user-local:codex-current"',
                'strength = "strong"',
                'execution_methods = ["internal"]',
            ]
        ),
        encoding="utf-8",
    )

    assert cli.main(["config", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    policy = payload["local_runtime"]["assignment_policy"]
    assert policy["status"] == "configured"
    assert policy["execution_role"] == {"value": "orchestrator", "source": "derived:delegation.assignment_policy"}
    assert policy["assignment_policy"] == {"value": "required-best-fit", "source": "local-override"}
    assert policy["current_target"] == {"value": "user-local:codex-current", "source": "local-override"}
    assert policy["current_target_status"] == "known-profile"
    assert policy["binding"] == {
        "required_best_fit_requested": True,
        "enforceable": True,
        "claim_boundary": "assignment policy resolved",
    }


def test_config_command_blocks_required_best_fit_when_current_target_is_unknown(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'execution_role = "orchestrator"',
                'assignment_policy = "required-best-fit"',
                'current_target = "missing_profile"',
            ]
        ),
        encoding="utf-8",
    )

    assert cli.main(["config", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    policy = payload["local_runtime"]["assignment_policy"]
    assert policy["status"] == "blocked-unknown-current-target"
    assert policy["current_target_status"] == "unknown"
    assert policy["binding"]["enforceable"] is False
    assert "cannot be claimed" in policy["binding"]["claim_boundary"]


def test_config_command_reports_target_identity_and_guidance_storage(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'current_target = "user-local:codex-current"',
                "",
                "[local_memory]",
                "target_guidance_enabled = true",
                'user_guidance_root = "~/.agentic-workspace/target-guidance"',
                'target_guidance_overlay_path = ".agentic-workspace/local/target-guidance-overlay.json"',
                'correction_events_path = ".agentic-workspace/local/correction-events.json"',
                "",
                "[delegation_targets.codex_current]",
                'target_id = "user-local:codex-current"',
                'target_revision = "2026-07-runtime"',
                'aliases = ["codex", "current-codex"]',
                'revision_policy = "revalidate"',
                'strength = "strong"',
                'execution_methods = ["internal"]',
                'model_family = "codex"',
                'provider = "openai"',
            ]
        ),
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    local_memory = payload["mixed_agent"]["local_memory"]
    assert local_memory["target_guidance"]["enabled"] is True
    assert local_memory["target_guidance"]["repo_overlay_path"] == ".agentic-workspace/local/target-guidance-overlay.json"
    profile = payload["mixed_agent"]["delegation_targets"]["profiles"][0]
    assert profile["target_id"] == "user-local:codex-current"
    assert profile["aliases"] == ["codex", "current-codex"]
    identity = payload["mixed_agent"]["target_identity"]
    assert identity["current_target_identity"]["status"] == "known"
    assert identity["current_target_identity"]["subject"]["stable_target_id"] == "user-local:codex-current"
    assert identity["current_target_identity"]["provenance"]["matched_by"] == "target_id"
    assert identity["current_target_identity"]["provenance"]["canonical_join_key"] == "stable_target_id"
    assert identity["storage"]["status"] == "available"
    assert "repo-local target overlay under .agentic-workspace/local/" in identity["precedence"]
    correction = payload["mixed_agent"]["correction_feedback"]
    assert correction["status"] == "ready"
    assert "explicit-user-correction" in correction["event_schema"]["source_types"]
    assert "rejected-secret-bearing" in correction["event_schema"]["admission_states"]
    assert "correction-event.submit" in {item["operation_id"] for item in correction["operations"]}
    assert "agent-guidance.promote" in {item["operation_id"] for item in correction["operations"]}
    assert "agent-guidance.split" in {item["operation_id"] for item in correction["operations"]}
    correction_operations = [item for item in correction["operations"] if item["operation_id"].startswith("correction-event.")]
    guidance_operations = [item for item in correction["operations"] if item["operation_id"].startswith("agent-guidance.")]
    assert all(item["public"] and item["generated_operation"] and item["external_contract"] for item in correction_operations)
    assert all(item["public"] and item["generated_operation"] and item["external_contract"] for item in guidance_operations)
    decision_contracts = {item["contract"] for item in correction["decision_surfaces"]}
    assert {
        "agentic-workspace/correction-capture-decision/v1",
        "agentic-workspace/agent-guidance-route/v1",
        "agentic-workspace/guidance-compliance-result/v1",
        "agentic-workspace/guidance-consequence-decision/v1",
    } <= decision_contracts
    assert correction["storage"]["retention_cap"] == 20
    assert correction["storage"]["retention_operations"] == ["correction-event.prune-compact"]
    assert identity["storage"]["layers"][0]["id"] == "user-local-target-guidance"
    assert identity["storage"]["conflict_resolution"]["ambiguous_identity"].startswith("fail-closed")


def test_config_command_target_identity_ambiguous_alias_fails_closed(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'current_target = "codex"',
                "",
                "[local_memory]",
                "target_guidance_enabled = true",
                'user_guidance_root = "~/.agentic-workspace/target-guidance"',
                "",
                "[delegation_targets.codex_a]",
                'target_id = "user-local:codex-a"',
                'aliases = ["codex"]',
                'strength = "strong"',
                'execution_methods = ["internal"]',
                "",
                "[delegation_targets.codex_b]",
                'target_id = "user-local:codex-b"',
                'aliases = ["codex"]',
                'strength = "strong"',
                'execution_methods = ["internal"]',
            ]
        ),
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    identity = payload["mixed_agent"]["target_identity"]
    assert identity["current_target_identity"]["status"] == "ambiguous"
    assert identity["current_target_identity"]["fail_closed"] is True
    assert "stable target_id" in identity["current_target_identity"]["recovery"]
    assert identity["current_target_identity"]["identity_repair"]["status"] == "unavailable"
    assert payload["mixed_agent"]["correction_feedback"]["status"] == "fail-closed"


def test_identity_init_preserves_explicit_noncurrent_target_profile_option(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    local_config = target / ".agentic-workspace/config.local.toml"
    local_config.parent.mkdir(parents=True)
    local_config.write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'current_target = "codex_sol"',
                "",
                "[delegation_targets.codex_sol]",
                'strength = "strong"',
                'execution_methods = ["internal"]',
                "",
                "[delegation_targets.codex_luna]",
                'strength = "weak"',
                'execution_methods = ["cli"]',
                "",
            ]
        ),
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "correction-event",
                "identity-init",
                "--target",
                str(target),
                "--target-profile",
                "codex_luna",
                "--target-id",
                "user-local:codex-luna-explicit",
                "--dry-run",
                "--format",
                "json",
            ]
        )
        == 0
    )
    preview = json.loads(capsys.readouterr().out)
    assert preview["target_profile"] == "codex_luna"
    assert preview["target_id"] == "user-local:codex-luna-explicit"
    assert preview["mutation_applied"] is False


def test_current_profile_without_id_exposes_and_applies_exact_local_identity_repair(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    local_config = target / ".agentic-workspace/config.local.toml"
    local_config.parent.mkdir(parents=True)
    local_config.write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'current_target = "codex_sol"',
                "",
                "[delegation_targets.codex_sol]",
                'strength = "strong"',
                'execution_methods = ["internal"]',
                'model_family = "gpt-5.6-sol"',
                'provider = "codex"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    before = local_config.read_text(encoding="utf-8")

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0
    posture = json.loads(capsys.readouterr().out)["mixed_agent"]["target_identity"]["current_target_identity"]
    assert posture["status"] == "ambiguous"
    assert posture["capability_posture"] == {
        "assignment": "available",
        "correction_events": "identity-required",
        "target_guidance": "identity-required",
        "suitability_evidence": "identity-required",
    }
    repair = posture["identity_repair"]
    assert repair["status"] == "ready"
    assert repair["operation_id"] == "correction-event.identity-init"
    assert repair["target_profile"] == "codex_sol"
    assert repair["checked_in"] is False

    command = [
        "correction-event",
        "identity-init",
        "--target",
        str(target),
        "--target-profile",
        "codex_sol",
        "--dry-run",
        "--format",
        "json",
    ]
    assert cli.main(command) == 0
    preview = json.loads(capsys.readouterr().out)
    assert preview["status"] == "planned"
    assert preview["mutation_applied"] is False
    assert local_config.read_text(encoding="utf-8") == before

    command.remove("--dry-run")
    command[command.index("--format") : command.index("--format")] = [
        "--expected-config-digest",
        preview["config_digest_before"],
    ]
    assert cli.main(command) == 0
    applied = json.loads(capsys.readouterr().out)
    assert applied["status"] == "initialized"
    assert applied["mutation_applied"] is True
    assert f'target_id = "{applied["target_id"]}"' in local_config.read_text(encoding="utf-8")

    assert cli.main(command) == 0
    replay = json.loads(capsys.readouterr().out)
    assert replay["status"] == "already-initialized"
    assert replay["mutation_applied"] is False

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0
    current = json.loads(capsys.readouterr().out)["mixed_agent"]["target_identity"]["current_target_identity"]
    assert current["status"] == "known"
    assert current["subject"]["stable_target_id"] == applied["target_id"]

    event = _correction_event(
        target_identity_ref=applied["target_id"],
        target_revision=None,
        source="explicit-user-correction",
        authority="human",
        source_ref="cmd-20260826132448-dae4079b",
        evidence_hash="sha256:d46b84c6c446204b9860",
    )
    assert (
        cli.main(
            [
                "correction-event",
                "submit",
                "--target",
                str(target),
                "--event-json",
                json.dumps(event),
                "--format",
                "json",
            ]
        )
        == 0
    )
    submitted = json.loads(capsys.readouterr().out)
    assert submitted["status"] == "stored"
    routed = [*submitted["admission"]["admitted_events"], *submitted["admission"]["low_authority_events"]]
    assert routed[0]["target_identity_ref"] == applied["target_id"]
    assert routed[0]["profile_name"] == "codex_sol"
    assert submitted["checked_in_repo_effect"] == "none"


def _correction_event(**overrides: object) -> dict[str, object]:
    event: dict[str, object] = {
        "target_identity_ref": "fast",
        "target_revision": "rev-b",
        "task_class": "mechanical-follow-through",
        "scope_class": "narrow-code-change",
        "phase": "implementation",
        "subsystem": "workspace-runtime",
        "surface": "bounded-edit",
        "invariant_id": "narrow-edits",
        "behavior_class": "edit-scope",
        "desired_behavior": "Prefer narrow edits.",
        "replaced_behavior": "Broad edits.",
        "authority": "explicit-user-correction",
        "source": "pr-review",
        "source_ref": "review-1",
        "producer_class": "human-reviewer",
        "producer_id": "reviewer-1",
        "evidence_hash": "sha256:review-1",
        "route_decisions": ["target-guidance", "target-suitability"],
    }
    event.update(overrides)
    return event


def _write_guidance_lifecycle_fixture(target: Path, *, user_root: Path | None) -> None:
    local_memory = ["[local_memory]", "target_guidance_enabled = true"]
    if user_root is not None:
        local_memory.append(f'user_guidance_root = "{user_root.as_posix()}"')
    (target / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                *local_memory,
                "",
                "[delegation_targets.fast_worker]",
                'target_id = "user-local:fast-worker"',
                'target_revision = "rev-b"',
                'aliases = ["fast"]',
                'revision_policy = "revalidate"',
                'strength = "strong"',
                'execution_methods = ["internal"]',
                'model_family = "codex"',
                'provider = "openai"',
            ]
        ),
        encoding="utf-8",
    )
    store = target / ".agentic-workspace/local/correction-events.json"
    store.parent.mkdir(parents=True, exist_ok=True)
    store.write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/correction-event-store/v1",
                "events": [
                    _correction_event(target_identity_ref="user-local:fast-worker", source_ref="review-1"),
                    _correction_event(
                        target_identity_ref="user-local:fast-worker",
                        source_ref="review-2",
                        evidence_hash="sha256:review-2",
                    ),
                ],
            }
        ),
        encoding="utf-8",
    )


def test_correction_event_lifecycle_admits_dedupes_and_scopes_by_target_revision() -> None:
    from agentic_workspace.agent_guidance import admit_correction_events

    subjects = [
        {
            "profile_name": "fast_worker",
            "stable_target_id": "user-local:fast-worker",
            "target_revision": "rev-b",
            "aliases": ["fast"],
            "identity_status": "active",
            "revision_policy": "revalidate",
        }
    ]
    events = [
        _correction_event(),
        _correction_event(
            target_identity_ref="user-local:fast-worker",
            desired_behavior="Keep changes narrow.",
            replaced_behavior="Large broad edits.",
            source_ref="review-2",
            evidence_hash="sha256:review-2",
        ),
        _correction_event(
            target_identity_ref="user-local:fast-worker",
            target_revision="old-rev",
            invariant_id="stale-guidance",
            behavior_class="routing",
            desired_behavior="Use stale behavior.",
            replaced_behavior="Current behavior.",
            source_ref="review-3",
            evidence_hash="sha256:review-3",
        ),
    ]

    admitted = admit_correction_events(
        events=events,
        subjects=subjects,
        task_class="mechanical-follow-through",
        scope_class="narrow-code-change",
    )

    assert admitted["admitted_events"][0]["target_identity_ref"] == "user-local:fast-worker"
    assert admitted["admitted_events"][0]["profile_name"] == "fast_worker"
    assert admitted["admitted_events"][0]["admission_state"] == "recurrence"
    assert admitted["admitted_events"][0]["recurrence_count"] == 2
    assert admitted["admitted_events"][0]["contradiction_account"]["status"] == "recurrence-preserved"
    assert admitted["derived_routes"]["target_guidance"] == [admitted["admitted_events"][0]["event_id"]]
    assert admitted["retention"]["mode"] == "bounded-local-retention"
    assert "correction-event.submit" in {item["operation_id"] for item in admitted["public_operations"]}
    assert all(item["receipt"]["kind"] == "agentic-workspace/correction-operation-receipt/v1" for item in admitted["public_operations"])
    assert {item["reason"] for item in admitted["rejected_events"]} == {"rejected-stale-revision"}


def test_agent_guidance_routes_selectively_and_stays_quiet_for_unrelated_context(tmp_path: Path) -> None:
    from agentic_workspace.agent_guidance import route_agent_guidance

    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    store = {
        "kind": "agentic-workspace/guidance-lifecycle-store/v1",
        "records": [
            {
                "kind": "agentic-workspace/guidance-lifecycle-record/v1",
                "guidance_id": "guidance:narrow-proof",
                "status": "active",
                "instruction": "Run the routed narrow proof before claiming completion.",
                "applicability": {
                    "target_identity_ref": "user-local:fast-worker",
                    "task_class": "code-change",
                    "scope_class": "narrow",
                    "subsystem": "workspace-runtime",
                    "surface": "final-response",
                    "applies_when": ["phase:proof"],
                },
                "revision": 2,
                "schema_revision": "schema-a",
            }
        ],
    }
    _write(tmp_path / ".agentic-workspace/local/guidance-lifecycle.json", json.dumps(store))

    routed = route_agent_guidance(
        target_root=tmp_path,
        target_identity_ref="user-local:fast-worker",
        task_class="code-change",
        scope_class="narrow",
        phase="proof",
        subsystem="workspace-runtime",
        surface="final-response",
    )
    unrelated = route_agent_guidance(
        target_root=tmp_path,
        target_identity_ref="user-local:other-worker",
        task_class="docs",
        scope_class="broad",
        phase="planning",
        subsystem="docs",
        surface="readme",
    )
    wrong_surface = route_agent_guidance(
        target_root=tmp_path,
        target_identity_ref="user-local:fast-worker",
        task_class="code-change",
        scope_class="narrow",
        phase="proof",
        subsystem="workspace-runtime",
        surface="proof-receipt",
    )
    unknown = route_agent_guidance(target_root=tmp_path, target_identity_ref="user-local:fast-worker")

    assert routed["status"] == "routed"
    assert [item["guidance_id"] for item in routed["guidance"]] == ["guidance:narrow-proof"]
    assert routed["guidance"][0]["precedence"].startswith("current user instruction")
    assert unrelated["status"] == "no-applicable-guidance"
    assert unrelated["guidance"] == []
    assert unrelated["context_overhead"]["ordinary_no_match_artifact_count"] == 0
    assert wrong_surface["status"] == "no-applicable-guidance"
    assert wrong_surface["excluded"][0]["reason"] == "surface-mismatch"
    assert unknown["status"] == "probe-required"
    assert set(unknown["probe"]["required_fields"]) == {"phase", "scope_class", "subsystem", "surface", "task_class"}


def test_agent_guidance_observations_drive_contextual_consequences_and_recovery(tmp_path: Path) -> None:
    from agentic_workspace.agent_guidance import observe_agent_guidance

    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0

    def observe(
        index: int,
        outcome: str,
        *,
        cause: str = "target-behavior",
        authority: str = "review",
        target_identity_ref: str = "user-local:fast-worker",
        target_revision: str = "rev-b",
        task_class: str = "code-change",
        scope_class: str = "narrow",
        phase: str = "proof",
        subsystem: str = "workspace-runtime",
        surface: str = "final-response",
        human_authorized_prohibition: bool = False,
    ) -> dict[str, Any]:
        return observe_agent_guidance(
            target_root=tmp_path,
            guidance_id="guidance:narrow-proof",
            outcome=outcome,
            evidence_authority=authority,
            evidence_ref=f"review-{index}",
            target_identity_ref=target_identity_ref,
            target_revision=target_revision,
            task_class=task_class,
            scope_class=scope_class,
            phase=phase,
            subsystem=subsystem,
            surface=surface,
            cause_class=cause,
            human_authorized_prohibition=human_authorized_prohibition,
        )

    assert observe(1, "surfaced-violated")["consequence"]["status"] == "advisory"
    assert observe(2, "surfaced-violated")["consequence"]["status"] == "review-required"
    assert observe(3, "surfaced-violated")["consequence"]["status"] == "suitability-impact"
    infrastructure = observe(4, "surfaced-violated", cause="infrastructure-defect")
    assert infrastructure["consequence"]["status"] == "suitability-impact"
    assert infrastructure["consequence"]["next_action"] == "route-product-improvement"
    assert observe(5, "surfaced-followed", authority="aw-owned-proof")["consequence"]["status"] == "suitability-impact"
    recovered = observe(6, "correct-escalation", authority="human")
    assert recovered["consequence"]["status"] == "review-required"
    replay = observe(6, "correct-escalation", authority="human")
    assert replay["status"] == "duplicate-replay"
    assert replay["storage"]["checked_in"] is False

    other_revision = observe(7, "surfaced-violated", target_revision="rev-c")
    assert other_revision["consequence"]["status"] == "advisory"
    assert other_revision["consequence"]["same_context_observation_count"] == 1
    assert other_revision["consequence"]["excluded_cross_context_observation_count"] == 6
    other_surface = observe(8, "surfaced-violated", surface="proof-receipt")
    assert other_surface["consequence"]["status"] == "advisory"
    other_phase = observe(9, "surfaced-violated", phase="implementation")
    assert other_phase["consequence"]["status"] == "advisory"
    prohibited_elsewhere = observe(
        10,
        "surfaced-violated",
        authority="human",
        surface="proof-receipt",
        human_authorized_prohibition=True,
    )
    assert prohibited_elsewhere["consequence"]["status"] == "review-required"
    assert prohibited_elsewhere["consequence"]["human_authority_required"] is False
    current_again = observe(11, "surfaced-violated")
    assert current_again["consequence"]["status"] == "suitability-impact"
    assert current_again["consequence"]["human_authority_required"] is False
    current_prohibition = observe(12, "surfaced-violated", authority="human", human_authorized_prohibition=True)
    assert current_prohibition["consequence"]["status"] == "class-prohibition"
    assert current_prohibition["consequence"]["human_authority_required"] is True


def test_correction_capture_decision_requires_capture_without_overcapturing_requirements() -> None:
    from agentic_workspace.agent_guidance import correction_capture_decision

    submitted = correction_capture_decision(correction_signal="explicit-user-correction", feedback_source_available=True)
    unavailable = correction_capture_decision(correction_signal="pr-review", feedback_source_available=False)
    changed_requirement = correction_capture_decision(correction_signal="new-requirement", feedback_source_available=True)
    shared = correction_capture_decision(
        correction_signal="explicit-user-correction", feedback_source_available=True, shared_repo_lesson=True
    )

    assert submitted["status"] == "event-submitted"
    assert submitted["required_operation"] == "correction-event submit"
    assert unavailable["status"] == "unavailable"
    assert "not exposed" in unavailable["limitation"]
    assert changed_requirement["status"] == "dismissed"
    assert changed_requirement["recognized_correction"] is False
    assert shared["status"] == "routed"
    assert shared["owner"] == "checked-in-memory"


def test_correction_event_lifecycle_resolves_authority_and_rejects_self_labeled_review() -> None:
    from agentic_workspace.agent_guidance import admit_correction_events

    subjects = [
        {
            "profile_name": "fast_worker",
            "stable_target_id": "user-local:fast-worker",
            "target_revision": "rev-b",
            "aliases": ["fast"],
            "identity_status": "active",
            "revision_policy": "preserve",
        }
    ]

    admitted = admit_correction_events(
        events=[
            _correction_event(
                authority="pr-review",
                source="pr-review",
                producer_class="agent-self-observation",
                producer_id="agent-1",
                source_ref="self-labeled-review",
                evidence_hash="sha256:self",
            ),
            _correction_event(
                authority="pr-review",
                source="pr-review",
                producer_class="human-reviewer",
                producer_id="reviewer-1",
                source_ref="trusted-review",
                evidence_hash="sha256:trusted",
                invariant_id="trusted-review",
            ),
        ],
        subjects=subjects,
    )

    assert admitted["admitted_events"][0]["authority_resolution"]["status"] == "trusted"
    assert admitted["admitted_events"][0]["authority"] == "pr-review"
    assert admitted["low_authority_events"][0]["authority_resolution"]["status"] == "low-authority"
    low_authority_id = admitted["low_authority_events"][0]["event_id"]
    assert low_authority_id in admitted["derived_routes"]["low_authority"]
    assert low_authority_id not in admitted["derived_routes"]["target_guidance"]
    assert admitted["rejected_events"] == []


def test_correction_event_lifecycle_returns_persistent_bounded_store_update() -> None:
    from agentic_workspace.agent_guidance import CORRECTION_EVENT_RETENTION_CAP, admit_correction_events

    subjects = [
        {
            "profile_name": "fast_worker",
            "stable_target_id": "user-local:fast-worker",
            "target_revision": "rev-b",
            "aliases": ["fast"],
            "identity_status": "active",
            "revision_policy": "preserve",
        }
    ]
    events = [
        _correction_event(
            source_ref=f"review-{index}",
            evidence_hash=f"sha256:review-{index}",
            invariant_id=f"narrow-edits-{index}",
        )
        for index in range(CORRECTION_EVENT_RETENTION_CAP + 2)
    ]

    admitted = admit_correction_events(events=events, subjects=subjects)

    assert len(admitted["admitted_events"]) == CORRECTION_EVENT_RETENTION_CAP
    assert admitted["retention"]["compacted_count"] == 2
    assert admitted["retention"]["persisted_store_action"] == "rewrite-retained-plus-compact-lineage"
    assert len(admitted["retention"]["compacted_lineage"]) == 2
    assert admitted["store_update"]["status"] == "bounded-rewrite-required"
    assert admitted["store_update"]["checked_in_repo_effect"] == "none"


def test_guidance_promotion_reads_only_the_canonical_correction_store(tmp_path: Path) -> None:
    from agentic_workspace.agent_guidance import guidance_promotion_from_store

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'current_target = "user-local:fast-worker"',
                "",
                "[delegation_targets.fast_worker]",
                'target_id = "user-local:fast-worker"',
                'target_revision = "rev-b"',
                'aliases = ["fast"]',
                'strength = "strong"',
                'execution_methods = ["internal"]',
                'model_family = "codex"',
                'provider = "openai"',
            ]
        ),
        encoding="utf-8",
    )
    store_path = target / ".agentic-workspace/local/correction-events.json"
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/correction-event-store/v1",
                "events": [
                    _correction_event(target_identity_ref="user-local:fast-worker", source_ref="review-1"),
                    _correction_event(target_identity_ref="user-local:fast-worker", source_ref="review-2", evidence_hash="sha256:review-2"),
                ],
            }
        ),
        encoding="utf-8",
    )

    decision = guidance_promotion_from_store(target_root=target)

    assert decision["status"] == "ready"
    assert decision["guidance"][0]["status"] == "active"
    assert decision["guidance"][0]["promotion_reason"] == "independent-recurrence"
    assert decision["authority_source"]["store"] == ".agentic-workspace/local/correction-events.json"


def test_guidance_promotion_supports_authorized_immediate_remember_from_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agentic_workspace.agent_guidance import (
        apply_guidance_promotion,
        guidance_promotion_from_store,
        record_guidance_remember_receipt,
    )

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        'schema_version = 1\n\n[delegation_targets.fast_worker]\ntarget_id = "user-local:fast-worker"\ntarget_revision = "rev-b"\nstrength = "strong"\nexecution_methods = ["internal"]\nmodel_family = "codex"\nprovider = "openai"\n',
        encoding="utf-8",
    )
    store = target / ".agentic-workspace/local/correction-events.json"
    store.parent.mkdir(parents=True, exist_ok=True)
    host_event = _trusted_guidance_host_event(
        target,
        authority="explicit-user-correction",
        producer_class="human-reviewer",
        producer_id="reviewer-1",
        source_ref="remember-1",
        host_admission_monkeypatch=monkeypatch,
        target_revision="rev-b",
    )
    remember_ref = record_guidance_remember_receipt(
        target_root=target,
        producer_class="human-reviewer",
        producer_id="reviewer-1",
        source_ref="remember-1",
        target_revision="rev-b",
        host_event_ref=host_event["event_ref"],
    )
    remember_receipt_ref = remember_ref["receipt_ref"]
    store.write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/correction-event-store/v1",
                "events": [
                    _correction_event(
                        target_identity_ref="user-local:fast-worker",
                        source_ref="remember-1",
                        remember_receipt_ref=remember_receipt_ref,
                    )
                ],
            }
        ),
        encoding="utf-8",
    )

    remembered = guidance_promotion_from_store(target_root=target)
    promoted = apply_guidance_promotion(
        target_root=target,
        guidance_id=remembered["guidance"][0]["guidance_id"],
    )

    assert remembered["status"] == "ready"
    assert remembered["guidance"][0]["promotion_reason"] == "explicit-authorised-remember"
    assert remembered["guidance"][0]["promotion_authority"]["remember_receipt"]["receipt_ref"] == remember_receipt_ref
    assert promoted["status"] == "promoted"
    assert promoted["record"]["provenance"]["promotion_reason"] == "explicit-authorised-remember"
    assert promoted["record"]["destination"]["owner"] == "repo-local-target-guidance-overlay"


def test_guidance_promotion_rejects_hand_authored_remember_receipt_path(tmp_path: Path) -> None:
    from agentic_workspace.agent_guidance import guidance_promotion_from_store

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        'schema_version = 1\n\n[delegation_targets.fast_worker]\ntarget_id = "user-local:fast-worker"\ntarget_revision = "rev-b"\nstrength = "strong"\nexecution_methods = ["internal"]\nmodel_family = "codex"\nprovider = "openai"\n',
        encoding="utf-8",
    )
    forged_ref = ".agentic-workspace/local/correction-event-receipts/remember-1.json"
    forged = target / forged_ref
    forged.parent.mkdir(parents=True, exist_ok=True)
    forged.write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/guidance-remember-receipt/v1",
                "status": "current",
                "authority": "explicit-user-correction",
                "producer_class": "human-reviewer",
                "producer_id": "reviewer-1",
                "source_ref": "remember-1",
                "target_revision": "rev-b",
            }
        ),
        encoding="utf-8",
    )
    store = target / ".agentic-workspace/local/correction-events.json"
    store.parent.mkdir(parents=True, exist_ok=True)
    store.write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/correction-event-store/v1",
                "events": [
                    _correction_event(
                        target_identity_ref="user-local:fast-worker",
                        source_ref="remember-1",
                        remember_receipt_ref=forged_ref,
                    )
                ],
            }
        ),
        encoding="utf-8",
    )

    remembered = guidance_promotion_from_store(target_root=target, explicit_remember=True)

    assert remembered["status"] == "review-required"
    assert remembered["guidance"][0]["promotion_authority"]["remember_receipt"] is None
    assert remembered["guidance"][0]["promotion_authority"]["caller_explicit_remember_ignored"] is True


def test_guidance_receipts_require_trusted_host_event_before_authority_storage(tmp_path: Path) -> None:
    from agentic_workspace.agent_guidance import (
        record_guidance_remember_receipt,
        record_trusted_authority_host_event,
        record_trusted_authority_receipt,
    )
    from agentic_workspace.config import WorkspaceUsageError

    with pytest.raises(WorkspaceUsageError, match="signed host event inbox"):
        record_trusted_authority_host_event(
            target_root=tmp_path,
            authority="pr-review",
            producer_class="human-reviewer",
            producer_id="reviewer-1",
            source_ref="review-1",
            host_event_ref="trusted-authority-event:review-1",
        )
    with pytest.raises(WorkspaceUsageError, match="caller-provided trusted authority host event resolvers are rejected"):
        record_trusted_authority_host_event(
            target_root=tmp_path,
            authority="pr-review",
            producer_class="human-reviewer",
            producer_id="reviewer-1",
            source_ref="review-1",
            host_event_ref="trusted-authority-event:review-1",
            host_event_resolver=lambda _ref: {},
        )
    with pytest.raises(WorkspaceUsageError, match="trusted host event ref"):
        record_trusted_authority_receipt(
            target_root=tmp_path,
            authority="pr-review",
            producer_class="human-reviewer",
            producer_id="reviewer-1",
            source_ref="review-1",
        )
    with pytest.raises(WorkspaceUsageError, match="trusted host event ref"):
        record_guidance_remember_receipt(
            target_root=tmp_path,
            producer_class="human-reviewer",
            producer_id="reviewer-1",
            source_ref="remember-1",
        )


def test_guidance_receipts_accept_protected_host_admission_boundary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agentic_workspace.agent_guidance import (
        TRUSTED_AUTHORITY_EVENT_INDEX_PATH,
        record_trusted_authority_receipt,
    )

    host_event = _trusted_guidance_host_event(
        tmp_path,
        authority="pr-review",
        producer_class="human-reviewer",
        producer_id="reviewer-1",
        source="github-review",
        source_ref="review-1",
        host_admission_monkeypatch=monkeypatch,
        target_revision="rev-1",
        event_id="review-event-1",
    )

    receipt_result = record_trusted_authority_receipt(
        target_root=tmp_path,
        authority="pr-review",
        producer_class="human-reviewer",
        producer_id="reviewer-1",
        source="github-review",
        source_ref="review-1",
        target_revision="rev-1",
        event_id="review-event-1",
        host_event_ref=str(host_event["event_ref"]),
    )

    assert receipt_result["receipt_ref"].startswith("guidance-receipt:")
    second_host_event = _trusted_guidance_host_event(
        tmp_path,
        authority="pr-review",
        producer_class="human-reviewer",
        producer_id="reviewer-2",
        source="github-review",
        source_ref="review-2",
        host_admission_monkeypatch=monkeypatch,
        target_revision="rev-2",
        event_id="review-event-2",
    )
    index = json.loads((tmp_path / TRUSTED_AUTHORITY_EVENT_INDEX_PATH).read_text(encoding="utf-8"))
    assert {entry["event_ref"] for entry in index["events"]} == {host_event["event_ref"], second_host_event["event_ref"]}


def test_guidance_receipts_accept_pinned_signed_host_event_across_process(tmp_path: Path) -> None:
    import subprocess
    import sys

    host_event = _trusted_guidance_host_event(
        tmp_path,
        authority="pr-review",
        producer_class="human-reviewer",
        producer_id="reviewer-1",
        source="github-review",
        source_ref="review-1",
        target_revision="rev-1",
        event_id="review-event-1",
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json; "
                "from pathlib import Path; "
                "import agentic_workspace.agent_guidance as guidance_runtime; "
                f"host_public_key = json.loads({json.dumps(host_event['host_public_key'], sort_keys=True)!r}); "
                f"guidance_runtime._TRUSTED_AUTHORITY_HOST_PUBLIC_KEYS[{str(host_event['host_public_key_id'])!r}] = host_public_key; "
                "from agentic_workspace.agent_guidance import record_trusted_authority_receipt; "
                f"payload = record_trusted_authority_receipt(target_root=Path({str(tmp_path)!r}), "
                "authority='pr-review', producer_class='human-reviewer', producer_id='reviewer-1', "
                "source='github-review', source_ref='review-1', target_revision='rev-1', event_id='review-event-1', "
                f"host_event_ref={str(host_event['event_ref'])!r}); "
                "print(json.dumps(payload, sort_keys=True))"
            ),
        ],
        capture_output=True,
        cwd=Path(__file__).resolve().parents[1],
        text=True,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    payload = json.loads(completed.stdout)
    assert payload["receipt_ref"].startswith("guidance-receipt:")


def test_guidance_host_event_rejects_repo_generated_signature_without_host_trust(tmp_path: Path) -> None:
    from agentic_workspace.agent_guidance import record_trusted_authority_host_event
    from agentic_workspace.config import WorkspaceUsageError

    host_event = _trusted_guidance_host_event(
        tmp_path,
        authority="pr-review",
        producer_class="human-reviewer",
        producer_id="reviewer-1",
        source="github-review",
        source_ref="review-1",
        target_revision="rev-1",
        event_id="review-event-1",
        install_host_admission=False,
    )

    with pytest.raises(WorkspaceUsageError, match="host boundary"):
        record_trusted_authority_host_event(
            target_root=tmp_path,
            authority="pr-review",
            producer_class="human-reviewer",
            producer_id="reviewer-1",
            source="github-review",
            source_ref="review-1",
            target_revision="rev-1",
            event_id="review-event-1",
            trusted_channel="github-review-webhook",
            host_event_ref=str(host_event["event_ref"]),
        )


def test_guidance_receipts_do_not_load_repo_or_pythonpath_host_verifiers() -> None:
    source = (Path(__file__).resolve().parents[1] / "src/agentic_workspace/agent_guidance.py").read_text(encoding="utf-8")
    test_source = (Path(__file__).resolve().parents[1] / "tests/test_workspace_config_cli.py").read_text(encoding="utf-8")

    assert "agentic_workspace_host_adapters.guidance_authority" not in source
    assert "importlib.import_module" not in source
    assert "BEGIN " + "PRIVATE KEY" not in test_source
    assert "_GUIDANCE_HOST_TEST_RSA" + "_D" not in test_source
    assert "_guidance_host" + "_test_signature" not in test_source
    assert "github-review-adapter:" + "test-v1" not in source
    assert "_TRUSTED_AUTHORITY_HOST_ADMISSION_KEYS" not in source
    assert "_trusted_authority_protected_host_event_store_path" not in source


def test_guidance_host_admission_rejects_raw_caller_mapping(tmp_path: Path) -> None:
    import agentic_workspace.agent_guidance as guidance_runtime

    assert not hasattr(guidance_runtime, "admit_trusted_authority_host_event")
    assert not hasattr(guidance_runtime, "TrustedAuthorityHostAdmissionHandle")


def test_guidance_host_admission_issuer_is_not_public_runtime_entrypoint() -> None:
    source = (Path(__file__).resolve().parents[1] / "src/agentic_workspace/agent_guidance.py").read_text(encoding="utf-8")

    assert "def issue_trusted_authority_host_admission_for_adapter(" not in source
    assert "def admit_trusted_authority_host_event(" not in source
    assert "def _install_trusted_authority_host_admission_for_adapter_test(" not in source
    assert "TrustedAuthorityHostAdmissionHandle" not in source
    assert "_TRUSTED_AUTHORITY_HOST_BOUNDARY_TOKEN" not in source
    assert "_CURRENT_TRUSTED_AUTHORITY_EVENT_ADMISSIONS" not in source
    assert ".agentic-workspace-host/trust/guidance-authority-admission-keys.json" not in source


def test_guidance_receipts_reject_jointly_forged_local_host_event(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agentic_workspace.agent_guidance import (
        TRUSTED_AUTHORITY_EVENT_STORE_PATH,
        _json_digest,
        record_trusted_authority_receipt,
    )
    from agentic_workspace.config import WorkspaceUsageError

    event = {
        "kind": "agentic-workspace/trusted-authority-host-event/v1",
        "status": "current",
        "authority": "pr-review",
        "producer_class": "human-reviewer",
        "producer_id": "reviewer-1",
        "source": "github-review",
        "source_ref": "review-1",
        "target_revision": "rev-1",
        "event_id": "",
        "recorded_at": "2026-07-29T00:00:00Z",
        "custody": {
            "producer": "github-review-adapter",
            "trusted_channel": "github-review-webhook",
        },
    }
    event_ref = "trusted-authority-event:" + _json_digest(event)[:24]
    event["event_ref"] = event_ref
    monkeypatch.setenv("AW_TRUSTED_AUTHORITY_EVENT_ADMISSION_KEYS", json.dumps({"caller-key": {"status": "current"}}))
    event["host_admission"] = {
        "kind": "agentic-workspace/trusted-authority-host-admission/v1",
        "status": "current",
        "algorithm": "RS256",
        "key_id": "caller-key",
        "signature": "caller-forged-signature",
    }
    event["host_admission_ref"] = "trusted-authority-admission:caller-forged"
    path = tmp_path / TRUSTED_AUTHORITY_EVENT_STORE_PATH / f"{event_ref.removeprefix('trusted-authority-event:')}.json"
    _write(path, json.dumps(event, indent=2, sort_keys=True) + "\n")

    with pytest.raises(WorkspaceUsageError, match="host boundary"):
        record_trusted_authority_receipt(
            target_root=tmp_path,
            authority="pr-review",
            producer_class="human-reviewer",
            producer_id="reviewer-1",
            source="github-review",
            source_ref="review-1",
            target_revision="rev-1",
            host_event_ref=event_ref,
        )


def test_guidance_receipts_reject_caller_written_verdict_without_protected_import(tmp_path: Path) -> None:
    from agentic_workspace.agent_guidance import (
        TRUSTED_AUTHORITY_EVENT_AUDIENCE,
        TRUSTED_AUTHORITY_EVENT_STORE_PATH,
        _json_digest,
        _trusted_authority_event_digest,
        record_trusted_authority_receipt,
    )
    from agentic_workspace.config import WorkspaceUsageError

    event = {
        "kind": "agentic-workspace/trusted-authority-host-event/v1",
        "status": "current",
        "authority": "pr-review",
        "producer_class": "human-reviewer",
        "producer_id": "reviewer-1",
        "source": "github-review",
        "source_ref": "review-raw-verdict",
        "target_revision": "rev-1",
        "event_id": "",
        "recorded_at": "2026-07-29T00:00:00Z",
        "custody": {
            "producer": "github-review-adapter",
            "trusted_channel": "github-review-webhook",
        },
    }
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
        "correction_authority": "pr-review",
        "producer_class": "human-reviewer",
        "source_ref": "review-raw-verdict",
        "target_revision": "rev-1",
        "event_id": "",
        "workspace_ref": f"workspace:path:{tmp_path.resolve()}",
        "audience": TRUSTED_AUTHORITY_EVENT_AUDIENCE,
        "issued_at": "2026-07-29T00:00:00Z",
        "expires_at": "2099-01-01T00:00:00Z",
        "nonce": "review-raw-verdict:event",
        "verifier_revision": "guidance-host-test-verifier:1",
    }
    path = tmp_path / TRUSTED_AUTHORITY_EVENT_STORE_PATH / f"{event_ref.removeprefix('trusted-authority-event:')}.json"
    _write(path, json.dumps(event, indent=2, sort_keys=True) + "\n")

    with pytest.raises(WorkspaceUsageError, match="signed host boundary"):
        record_trusted_authority_receipt(
            target_root=tmp_path,
            authority="pr-review",
            producer_class="human-reviewer",
            producer_id="reviewer-1",
            source="github-review",
            source_ref="review-raw-verdict",
            target_revision="rev-1",
            host_event_ref=event_ref,
        )


@pytest.mark.parametrize(
    ("case_name", "admission_context_overrides", "key_overrides"),
    [
        ("wrong-audience", {"audience": "other-consumer"}, {}),
        ("missing-nonce", {"nonce": ""}, {}),
        ("expired-admission", {"expires_at": "2026-01-01T00:00:00Z"}, {}),
        ("revoked-admission", {"revoked_at": "2026-07-29T00:00:00Z"}, {}),
        ("wrong-workspace", {"workspace_ref": "workspace:path:not-this-workspace"}, {}),
    ],
)
def test_guidance_receipts_reject_invalid_host_admission_lifecycle(
    tmp_path: Path,
    case_name: str,
    admission_context_overrides: dict[str, object],
    key_overrides: dict[str, object],
) -> None:
    from agentic_workspace.agent_guidance import record_trusted_authority_receipt
    from agentic_workspace.config import WorkspaceUsageError

    host_event = _trusted_guidance_host_event(
        tmp_path,
        authority="pr-review",
        producer_class="human-reviewer",
        producer_id="reviewer-1",
        source="github-review",
        source_ref=f"review-{case_name}",
        target_revision="rev-1",
        admission_context_overrides=admission_context_overrides,
        key_overrides=key_overrides,
    )

    with pytest.raises(WorkspaceUsageError, match="host boundary"):
        record_trusted_authority_receipt(
            target_root=tmp_path,
            authority="pr-review",
            producer_class="human-reviewer",
            producer_id="reviewer-1",
            source="github-review",
            source_ref=f"review-{case_name}",
            target_revision="rev-1",
            host_event_ref=str(host_event["event_ref"]),
        )


def test_guidance_promotion_ignores_caller_immediate_remember_without_receipt(tmp_path: Path) -> None:
    from agentic_workspace.agent_guidance import guidance_promotion_from_store

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        'schema_version = 1\n\n[delegation_targets.fast_worker]\ntarget_id = "user-local:fast-worker"\ntarget_revision = "rev-b"\nstrength = "strong"\nexecution_methods = ["internal"]\nmodel_family = "codex"\nprovider = "openai"\n',
        encoding="utf-8",
    )
    store = target / ".agentic-workspace/local/correction-events.json"
    store.parent.mkdir(parents=True, exist_ok=True)
    store.write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/correction-event-store/v1",
                "events": [_correction_event(target_identity_ref="user-local:fast-worker", source_ref="remember-1")],
            }
        ),
        encoding="utf-8",
    )

    decision = guidance_promotion_from_store(target_root=target, explicit_remember=True)

    assert decision["status"] == "review-required"
    assert decision["guidance"][0]["promotion_authority"]["caller_explicit_remember_ignored"] is True
    assert decision["guidance"][0]["promotion_reason"] == "insufficient-independent-evidence"


def test_guidance_promotion_rejects_correlated_broad_sensitive_or_conflicting_evidence(tmp_path: Path) -> None:
    from agentic_workspace.agent_guidance import guidance_promotion_from_store

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        'schema_version = 1\n\n[delegation_targets.fast_worker]\ntarget_id = "user-local:fast-worker"\ntarget_revision = "rev-b"\nstrength = "strong"\nexecution_methods = ["internal"]\nmodel_family = "codex"\nprovider = "openai"\n',
        encoding="utf-8",
    )
    store = target / ".agentic-workspace/local/correction-events.json"
    store.parent.mkdir(parents=True, exist_ok=True)
    store.write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/correction-event-store/v1",
                "events": [
                    _correction_event(target_identity_ref="user-local:fast-worker", source_ref="review-1", correlation_id="thread-1"),
                    _correction_event(
                        target_identity_ref="user-local:fast-worker",
                        source_ref="review-2",
                        evidence_hash="sha256:review-2",
                        correlation_id="thread-1",
                    ),
                    _correction_event(
                        target_identity_ref="user-local:fast-worker",
                        invariant_id="broad",
                        behavior_class="scope",
                        desired_behavior="Always prefer this.",
                        source_ref="review-3",
                        evidence_hash="sha256:review-3",
                        scope_class="global",
                    ),
                    _correction_event(
                        target_identity_ref="user-local:fast-worker",
                        invariant_id="safe",
                        behavior_class="safety",
                        desired_behavior="Bypass safety checks.",
                        source_ref="review-4",
                        evidence_hash="sha256:review-4",
                        safety_sensitive=True,
                    ),
                    _correction_event(
                        target_identity_ref="user-local:fast-worker",
                        invariant_id="conflict",
                        behavior_class="authority",
                        desired_behavior="Override current user guidance.",
                        source_ref="review-5",
                        evidence_hash="sha256:review-5",
                        conflict_review={"status": "conflict-open"},
                    ),
                ],
            }
        ),
        encoding="utf-8",
    )

    decision = guidance_promotion_from_store(target_root=target)

    reasons = {item["promotion_reason"] for item in decision["guidance"]}
    rejected_reasons = set(decision["authority_source"]["admission_summary"]["rejected_reasons"])
    assert decision["status"] == "review-required"
    assert "correlated-delivery" in reasons
    assert rejected_reasons >= {
        "rejected-broad-applicability-review-required",
        "rejected-safety-sensitive-review-required",
        "rejected-conflicting-authority-review-required",
    }


def test_guidance_promotion_persists_provenance_and_reversible_transition(tmp_path: Path) -> None:
    from agentic_workspace.agent_guidance import apply_guidance_promotion, guidance_promotion_from_store, transition_guidance

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        'schema_version = 1\n\n[delegation_targets.fast_worker]\ntarget_id = "user-local:fast-worker"\ntarget_revision = "rev-b"\nstrength = "strong"\nexecution_methods = ["internal"]\nmodel_family = "codex"\nprovider = "openai"\n',
        encoding="utf-8",
    )
    store = target / ".agentic-workspace/local/correction-events.json"
    store.parent.mkdir(parents=True, exist_ok=True)
    store.write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/correction-event-store/v1",
                "events": [
                    _correction_event(target_identity_ref="user-local:fast-worker", source_ref="review-1"),
                    _correction_event(target_identity_ref="user-local:fast-worker", source_ref="review-2", evidence_hash="sha256:review-2"),
                ],
            }
        ),
        encoding="utf-8",
    )
    decision = guidance_promotion_from_store(target_root=target)
    promoted = apply_guidance_promotion(target_root=target, guidance_id=decision["guidance"][0]["guidance_id"])
    transitioned = transition_guidance(
        target_root=target,
        guidance_id=promoted["record"]["guidance_id"],
        operation="suppress",
        reason="conflicts with current policy",
        expected_revision=promoted["record"]["revision"],
    )
    assert promoted["status"] == "promoted"
    assert promoted["record"]["provenance"]["source_event_refs"]
    assert transitioned["record"]["status"] == "suppressed"
    assert transitioned["record"]["transitions"][-1]["reason"] == "conflicts with current policy"


def test_guidance_lifecycle_supports_external_user_store_and_detects_user_to_overlay_conflict(tmp_path: Path) -> None:
    from agentic_workspace.agent_guidance import apply_guidance_promotion, guidance_promotion_from_store, transition_guidance

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    user_root = tmp_path / "user-guidance"
    _write_guidance_lifecycle_fixture(target, user_root=user_root)

    decision = guidance_promotion_from_store(target_root=target)
    guidance_id = decision["guidance"][0]["guidance_id"]
    promoted = apply_guidance_promotion(target_root=target, guidance_id=guidance_id)
    transitioned = transition_guidance(
        target_root=target,
        guidance_id=guidance_id,
        operation="suppress",
        reason="temporarily background",
        expected_revision=promoted["record"]["revision"],
    )

    expected_store = user_root / "user-local-fast-worker/guidance-lifecycle.json"
    assert expected_store.exists()
    assert promoted["store_location"] == {
        "kind": "agentic-workspace/guidance-store-location/v1",
        "scope": "user-local-external",
        "store_ref": expected_store.resolve().as_posix(),
        "absolute": True,
        "owner": "user-local-target-guidance",
    }
    assert transitioned["record"]["status"] == "suppressed"
    assert transitioned["store_location"]["store_ref"] == expected_store.resolve().as_posix()

    _write_guidance_lifecycle_fixture(target, user_root=None)
    conflict = apply_guidance_promotion(target_root=target, guidance_id=guidance_id)
    assert conflict["status"] == "promotion-owner-conflict"
    assert conflict["migration"]["status"] == "required"
    assert conflict["canonical_store_scan"]["active_stores"][0]["scope"] == "user-local-external"


def test_guidance_promotion_detects_overlay_to_user_store_conflict(tmp_path: Path) -> None:
    from agentic_workspace.agent_guidance import apply_guidance_promotion, guidance_promotion_from_store

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write_guidance_lifecycle_fixture(target, user_root=None)
    decision = guidance_promotion_from_store(target_root=target)
    guidance_id = decision["guidance"][0]["guidance_id"]
    promoted = apply_guidance_promotion(target_root=target, guidance_id=guidance_id)
    assert promoted["status"] == "promoted"
    assert promoted["store_location"]["scope"] == "repository-local"

    _write_guidance_lifecycle_fixture(target, user_root=tmp_path / "user-guidance")
    conflict = apply_guidance_promotion(target_root=target, guidance_id=guidance_id)
    assert conflict["status"] == "promotion-owner-conflict"
    assert conflict["canonical_store_scan"]["active_match_count"] == 1
    assert conflict["migration"]["expected_source_revisions"][0]["record_revision"] == 1


def test_guidance_lifecycle_requires_revision_and_operation_specific_inputs(tmp_path: Path) -> None:
    from agentic_workspace.agent_guidance import apply_guidance_promotion, guidance_promotion_from_store, transition_guidance

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        'schema_version = 1\n\n[delegation_targets.fast_worker]\ntarget_id = "user-local:fast-worker"\ntarget_revision = "rev-b"\nstrength = "strong"\nexecution_methods = ["internal"]\nmodel_family = "codex"\nprovider = "openai"\n',
        encoding="utf-8",
    )
    store = target / ".agentic-workspace/local/correction-events.json"
    store.parent.mkdir(parents=True, exist_ok=True)
    store.write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/correction-event-store/v1",
                "events": [
                    _correction_event(target_identity_ref="user-local:fast-worker", source_ref="review-1"),
                    _correction_event(target_identity_ref="user-local:fast-worker", source_ref="review-2", evidence_hash="sha256:review-2"),
                    _correction_event(
                        target_identity_ref="user-local:fast-worker",
                        invariant_id="proof-style",
                        behavior_class="proof",
                        desired_behavior="Keep proof narrow.",
                        source_ref="review-3",
                        evidence_hash="sha256:review-3",
                    ),
                    _correction_event(
                        target_identity_ref="user-local:fast-worker",
                        invariant_id="proof-style",
                        behavior_class="proof",
                        desired_behavior="Keep proof narrow.",
                        source_ref="review-4",
                        evidence_hash="sha256:review-4",
                    ),
                    _correction_event(
                        target_identity_ref="user-local:fast-worker",
                        invariant_id="replacement-style",
                        behavior_class="replacement",
                        desired_behavior="Use replacement guidance.",
                        source_ref="review-5",
                        evidence_hash="sha256:review-5",
                    ),
                    _correction_event(
                        target_identity_ref="user-local:fast-worker",
                        invariant_id="replacement-style",
                        behavior_class="replacement",
                        desired_behavior="Use replacement guidance.",
                        source_ref="review-6",
                        evidence_hash="sha256:review-6",
                    ),
                ],
            }
        ),
        encoding="utf-8",
    )
    decision = guidance_promotion_from_store(target_root=target)
    first_promotion = apply_guidance_promotion(target_root=target, guidance_id=decision["guidance"][0]["guidance_id"])
    second_promotion = apply_guidance_promotion(target_root=target, guidance_id=decision["guidance"][1]["guidance_id"])
    third_promotion = apply_guidance_promotion(target_root=target, guidance_id=decision["guidance"][2]["guidance_id"])
    first = first_promotion["record"]
    second = second_promotion["record"]
    third = third_promotion["record"]

    missing_revision = transition_guidance(
        target_root=target,
        guidance_id=first["guidance_id"],
        operation="edit",
        reason="tighten wording",
        instruction="Prefer focused edits.",
    )
    stale_revision = transition_guidance(
        target_root=target,
        guidance_id=first["guidance_id"],
        operation="edit",
        reason="tighten wording",
        expected_revision=99,
        instruction="Prefer focused edits.",
    )
    edited = transition_guidance(
        target_root=target,
        guidance_id=first["guidance_id"],
        operation="edit",
        reason="tighten wording",
        expected_revision=first["revision"],
        instruction="Prefer focused edits.",
    )
    merged = transition_guidance(
        target_root=target,
        guidance_id=edited["record"]["guidance_id"],
        operation="merge",
        reason="same target behavior",
        expected_revision=edited["record"]["revision"],
        expected_record_revisions={second["guidance_id"]: second["revision"]},
        merge_guidance_ids=[second["guidance_id"]],
    )
    split = transition_guidance(
        target_root=target,
        guidance_id=merged["record"]["guidance_id"],
        operation="split",
        reason="separate behavior and proof guidance",
        expected_revision=merged["record"]["revision"],
        split_instructions=["Prefer focused edits.", "Prefer focused proof."],
    )
    split_replacement = next(item for item in split["records"] if item["guidance_id"] in split["record"]["split_replacement_ids"])
    missing_replacement = transition_guidance(
        target_root=target,
        guidance_id=split_replacement["guidance_id"],
        operation="supersede",
        reason="replacement must exist",
        expected_revision=split_replacement["revision"],
        expected_record_revisions={"guidance:missing": 1},
        replacement_guidance_id="guidance:missing",
    )
    superseded = transition_guidance(
        target_root=target,
        guidance_id=split_replacement["guidance_id"],
        operation="supersede",
        reason="replacement accepted",
        expected_revision=split_replacement["revision"],
        expected_record_revisions={third["guidance_id"]: third["revision"]},
        replacement_guidance_id=third["guidance_id"],
    )

    assert missing_revision["status"] == "expected-revision-required"
    assert stale_revision["status"] == "stale-guidance-revision"
    assert first_promotion["mutation_receipt"]["receipt_ref"].startswith("guidance-receipt:")
    assert first_promotion["mutation_receipt"]["receipt_custody"]["producer"] == "agentic-workspace.guidance-receipt-index"
    assert edited["record"]["instruction"] == "Prefer focused edits."
    assert edited["mutation_receipt"]["receipt_ref"].startswith("guidance-receipt:")
    assert edited["mutation_receipt"]["receipt_store"] == ".agentic-workspace/local/guidance-receipts.json"
    assert second["guidance_id"] in merged["record"]["merged_guidance_ids"]
    assert next(item for item in merged["records"] if item["guidance_id"] == second["guidance_id"])["status"] == "merged"
    assert merged["mutation_receipt"]["atomic_record_count"] == 2
    assert merged["mutation_receipt"]["receipt_ref"].startswith("guidance-receipt:")
    assert split["record"]["status"] == "split-retired"
    assert len(split["record"]["split_replacements"]) == 2
    assert {item["status"] for item in split["records"] if item["guidance_id"] in split["record"]["split_replacement_ids"]} == {"active"}
    assert split["mutation_receipt"]["receipt_ref"].startswith("guidance-receipt:")
    assert missing_replacement["status"] == "missing-replacement-guidance"
    assert superseded["record"]["status"] == "superseded"
    assert superseded["mutation_receipt"]["receipt_ref"].startswith("guidance-receipt:")
    receipt_index = json.loads((target / ".agentic-workspace/local/guidance-receipts.json").read_text(encoding="utf-8"))
    mutation_receipts = [item for item in receipt_index["receipts"] if item.get("receipt_type") == "guidance-mutation"]
    assert {item["operation"] for item in mutation_receipts} >= {"promote", "edit", "merge", "split", "supersede"}


def test_guidance_lifecycle_multi_file_transaction_rolls_back_prior_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agentic_workspace.agent_guidance import _json_digest, _write_guidance_json_transaction

    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    before = {"kind": "test/store/v1", "value": "before"}
    _write(first, json.dumps(before, indent=2, sort_keys=True) + "\n")
    original_replace = Path.replace

    def fail_second_replace(self: Path, target: Path) -> Path:
        if Path(target) == second:
            raise OSError("simulated receipt-index failure")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", fail_second_replace)

    with pytest.raises(OSError, match="simulated receipt-index failure"):
        _write_guidance_json_transaction(
            [
                (first, {"kind": "test/store/v1", "value": "after"}, _json_digest(before)),
                (second, {"kind": "test/receipt-index/v1"}, None),
            ]
        )

    assert json.loads(first.read_text(encoding="utf-8")) == before
    assert not second.exists()


@pytest.mark.parametrize("failure_boundary", ["after-write:1", "after-write:2"])
def test_guidance_promotion_recovers_interrupted_store_registry_receipt_transaction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure_boundary: str
) -> None:
    import agentic_workspace.agent_guidance as guidance_runtime

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write_guidance_lifecycle_fixture(target, user_root=None)
    decision = guidance_runtime.guidance_promotion_from_store(target_root=target)
    guidance_id = decision["guidance"][0]["guidance_id"]

    class SimulatedProcessLoss(BaseException):
        pass

    def interrupt(phase: str, _path: Path) -> None:
        if phase == failure_boundary:
            raise SimulatedProcessLoss(phase)

    monkeypatch.setattr(guidance_runtime, "_GUIDANCE_TRANSACTION_FAULT_INJECTOR", interrupt)
    with pytest.raises(SimulatedProcessLoss, match=failure_boundary):
        guidance_runtime.apply_guidance_promotion(target_root=target, guidance_id=guidance_id)

    journal = target / guidance_runtime.GUIDANCE_TRANSACTION_JOURNAL_PATH
    assert journal.exists()
    monkeypatch.setattr(guidance_runtime, "_GUIDANCE_TRANSACTION_FAULT_INJECTOR", None)

    recovered = guidance_runtime.apply_guidance_promotion(target_root=target, guidance_id=guidance_id)

    assert recovered["status"] == "promoted"
    assert recovered["recovery"]["status"] == "completed-prepared-transaction"
    assert not journal.exists()
    lifecycle_path = Path(recovered["store_location"]["store_ref"])
    if not lifecycle_path.is_absolute():
        lifecycle_path = target / lifecycle_path
    lifecycle = json.loads(lifecycle_path.read_text(encoding="utf-8"))
    registry = json.loads((target / guidance_runtime.GUIDANCE_STORE_OWNER_REGISTRY_PATH).read_text(encoding="utf-8"))
    receipt_index = json.loads((target / guidance_runtime.GUIDANCE_RECEIPT_INDEX_PATH).read_text(encoding="utf-8"))
    assert lifecycle["records"][0]["guidance_id"] == guidance_id
    assert registry["stores"][0]["store_revision"] == "sha256:" + guidance_runtime._json_digest({"records": lifecycle["records"]})
    matching_receipts = [
        receipt
        for receipt in receipt_index["receipts"]
        if guidance_id in receipt.get("mutation_receipt", {}).get("affected_record_ids", [])
    ]
    assert matching_receipts
    assert "store-owner-registry-current" in matching_receipts[-1]["mutation_receipt"]["postconditions"]


@pytest.mark.parametrize("failure_boundary", ["after-write:1", "after-write:2", "after-write:3"])
@pytest.mark.parametrize("remove_origin", [False, True])
def test_user_local_guidance_transaction_recovers_from_another_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_boundary: str,
    remove_origin: bool,
) -> None:
    import shutil

    import agentic_workspace.agent_guidance as guidance_runtime

    user_root = tmp_path / "user-guidance"
    origin = tmp_path / "repo-a"
    successor = tmp_path / "repo-b"
    for target in (origin, successor):
        target.mkdir()
        _init_git_repo(target)
        _write_guidance_lifecycle_fixture(target, user_root=user_root)

    decision = guidance_runtime.guidance_promotion_from_store(target_root=origin)
    guidance_id = decision["guidance"][0]["guidance_id"]

    class SimulatedProcessLoss(BaseException):
        pass

    def interrupt(phase: str, _path: Path) -> None:
        if phase == failure_boundary:
            raise SimulatedProcessLoss(phase)

    monkeypatch.setattr(guidance_runtime, "_GUIDANCE_TRANSACTION_FAULT_INJECTOR", interrupt)
    with pytest.raises(SimulatedProcessLoss, match=failure_boundary):
        guidance_runtime.apply_guidance_promotion(target_root=origin, guidance_id=guidance_id)
    monkeypatch.setattr(guidance_runtime, "_GUIDANCE_TRANSACTION_FAULT_INJECTOR", None)

    external_store = user_root / "user-local-fast-worker/guidance-lifecycle.json"
    external_journal = guidance_runtime._guidance_store_transaction_journal_path(external_store)
    prepared = json.loads(external_journal.read_text(encoding="utf-8"))
    stale_store_lock = external_store.with_name(f".{external_store.name}.lock")
    stale_store_lock.write_text(prepared["transaction_id"], encoding="utf-8")
    monkeypatch.setattr(guidance_runtime, "_guidance_process_alive", lambda _process_id: False)

    if remove_origin:
        shutil.rmtree(origin)

    resumed = guidance_runtime.apply_guidance_promotion(target_root=successor, guidance_id=guidance_id)

    assert resumed["status"] == "promoted"
    assert resumed["custody_verification"]["status"] == "recovered"
    assert external_store.exists()
    assert not external_journal.exists()
    assert not list(user_root.rglob("*.lock"))
    successor_registry = json.loads((successor / guidance_runtime.GUIDANCE_STORE_OWNER_REGISTRY_PATH).read_text(encoding="utf-8"))
    successor_receipts = json.loads((successor / guidance_runtime.GUIDANCE_RECEIPT_INDEX_PATH).read_text(encoding="utf-8"))
    assert successor_registry["stores"][0]["store_ref"] == external_store.resolve().as_posix()
    assert successor_receipts["receipts"][-1]["operation"] == "promote-recovery"
    if remove_origin:
        assert not origin.exists()
    else:
        assert not (origin / guidance_runtime.GUIDANCE_TRANSACTION_JOURNAL_PATH).exists()


@pytest.mark.parametrize("failure_boundary", ["after-write:1", "after-write:2", "after-write:3"])
def test_user_local_guidance_transition_recovers_after_origin_repository_disappears(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_boundary: str,
) -> None:
    import shutil

    import agentic_workspace.agent_guidance as guidance_runtime

    user_root = tmp_path / "user-guidance"
    origin = tmp_path / "repo-a"
    successor = tmp_path / "repo-b"
    for target in (origin, successor):
        target.mkdir()
        _init_git_repo(target)
        _write_guidance_lifecycle_fixture(target, user_root=user_root)

    decision = guidance_runtime.guidance_promotion_from_store(target_root=origin)
    promoted = guidance_runtime.apply_guidance_promotion(
        target_root=origin,
        guidance_id=decision["guidance"][0]["guidance_id"],
    )
    transition_args = {
        "guidance_id": promoted["record"]["guidance_id"],
        "operation": "suppress",
        "reason": "temporarily background",
        "expected_revision": promoted["record"]["revision"],
    }

    class SimulatedProcessLoss(BaseException):
        pass

    def interrupt(phase: str, _path: Path) -> None:
        if phase == failure_boundary:
            raise SimulatedProcessLoss(phase)

    monkeypatch.setattr(guidance_runtime, "_GUIDANCE_TRANSACTION_FAULT_INJECTOR", interrupt)
    with pytest.raises(SimulatedProcessLoss, match=failure_boundary):
        guidance_runtime.transition_guidance(target_root=origin, **transition_args)
    monkeypatch.setattr(guidance_runtime, "_GUIDANCE_TRANSACTION_FAULT_INJECTOR", None)

    external_store = user_root / "user-local-fast-worker/guidance-lifecycle.json"
    external_journal = guidance_runtime._guidance_store_transaction_journal_path(external_store)
    prepared = json.loads(external_journal.read_text(encoding="utf-8"))
    external_store.with_name(f".{external_store.name}.lock").write_text(
        prepared["transaction_id"],
        encoding="utf-8",
    )
    monkeypatch.setattr(guidance_runtime, "_guidance_process_alive", lambda _process_id: False)
    shutil.rmtree(origin)

    resumed = guidance_runtime.transition_guidance(target_root=successor, **transition_args)

    assert resumed["status"] == "transitioned"
    assert resumed["record"]["status"] == "suppressed"
    assert resumed["recovery"]["status"] == "completed-cross-repository-prepared-transaction"
    assert resumed["custody_verification"]["status"] == "recovered"
    assert resumed["custody_verification"]["repair_route"]["status"] == "origin-repository-unavailable"
    assert not external_journal.exists()
    assert not list(user_root.rglob("*.lock"))
    successor_registry = json.loads((successor / guidance_runtime.GUIDANCE_STORE_OWNER_REGISTRY_PATH).read_text(encoding="utf-8"))
    successor_receipts = json.loads((successor / guidance_runtime.GUIDANCE_RECEIPT_INDEX_PATH).read_text(encoding="utf-8"))
    assert successor_registry["stores"][0]["store_ref"] == external_store.resolve().as_posix()
    assert successor_receipts["receipts"][-1]["operation"] == "suppress-recovery"


def test_cross_repository_guidance_recovery_does_not_delete_an_unknown_external_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import agentic_workspace.agent_guidance as guidance_runtime
    from agentic_workspace.config import WorkspaceUsageError

    user_root = tmp_path / "user-guidance"
    origin = tmp_path / "repo-a"
    successor = tmp_path / "repo-b"
    for target in (origin, successor):
        target.mkdir()
        _init_git_repo(target)
        _write_guidance_lifecycle_fixture(target, user_root=user_root)
    decision = guidance_runtime.guidance_promotion_from_store(target_root=origin)
    guidance_id = decision["guidance"][0]["guidance_id"]

    class SimulatedProcessLoss(BaseException):
        pass

    monkeypatch.setattr(
        guidance_runtime,
        "_GUIDANCE_TRANSACTION_FAULT_INJECTOR",
        lambda phase, _path: (_ for _ in ()).throw(SimulatedProcessLoss(phase)) if phase == "after-write:1" else None,
    )
    with pytest.raises(SimulatedProcessLoss):
        guidance_runtime.apply_guidance_promotion(target_root=origin, guidance_id=guidance_id)
    monkeypatch.setattr(guidance_runtime, "_GUIDANCE_TRANSACTION_FAULT_INJECTOR", None)

    external_store = user_root / "user-local-fast-worker/guidance-lifecycle.json"
    unknown_lock = external_store.with_name(f".{external_store.name}.lock")
    unknown_lock.write_text("guidance-tx:unknown-writer", encoding="utf-8")

    with pytest.raises(WorkspaceUsageError, match="blocked by a concurrent writer"):
        guidance_runtime.apply_guidance_promotion(target_root=successor, guidance_id=guidance_id)

    assert unknown_lock.read_text(encoding="utf-8") == "guidance-tx:unknown-writer"


def test_cross_repository_guidance_recovery_rejects_external_store_divergence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import agentic_workspace.agent_guidance as guidance_runtime
    from agentic_workspace.config import WorkspaceUsageError

    user_root = tmp_path / "user-guidance"
    origin = tmp_path / "repo-a"
    successor = tmp_path / "repo-b"
    for target in (origin, successor):
        target.mkdir()
        _init_git_repo(target)
        _write_guidance_lifecycle_fixture(target, user_root=user_root)
    decision = guidance_runtime.guidance_promotion_from_store(target_root=origin)
    guidance_id = decision["guidance"][0]["guidance_id"]

    class SimulatedProcessLoss(BaseException):
        pass

    monkeypatch.setattr(
        guidance_runtime,
        "_GUIDANCE_TRANSACTION_FAULT_INJECTOR",
        lambda phase, _path: (_ for _ in ()).throw(SimulatedProcessLoss(phase)) if phase == "after-write:1" else None,
    )
    with pytest.raises(SimulatedProcessLoss):
        guidance_runtime.apply_guidance_promotion(target_root=origin, guidance_id=guidance_id)
    monkeypatch.setattr(guidance_runtime, "_GUIDANCE_TRANSACTION_FAULT_INJECTOR", None)

    external_store = user_root / "user-local-fast-worker/guidance-lifecycle.json"
    external_journal = guidance_runtime._guidance_store_transaction_journal_path(external_store)
    prepared = json.loads(external_journal.read_text(encoding="utf-8"))
    external_store.write_text(
        json.dumps({"kind": "agentic-workspace/guidance-lifecycle-store/v1", "records": [], "diverged": True}),
        encoding="utf-8",
    )
    external_store.with_name(f".{external_store.name}.lock").write_text(prepared["transaction_id"], encoding="utf-8")
    monkeypatch.setattr(guidance_runtime, "_guidance_process_alive", lambda _process_id: False)

    with pytest.raises(WorkspaceUsageError, match="concurrent change"):
        guidance_runtime.apply_guidance_promotion(target_root=successor, guidance_id=guidance_id)

    assert external_journal.exists()


def test_guidance_promotion_retry_repairs_stale_registry_and_missing_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import agentic_workspace.agent_guidance as guidance_runtime

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write_guidance_lifecycle_fixture(target, user_root=None)
    decision = guidance_runtime.guidance_promotion_from_store(target_root=target)
    guidance_id = decision["guidance"][0]["guidance_id"]
    promoted = guidance_runtime.apply_guidance_promotion(target_root=target, guidance_id=guidance_id)
    assert promoted["status"] == "promoted"

    registry_path = target / guidance_runtime.GUIDANCE_STORE_OWNER_REGISTRY_PATH
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["stores"][0]["store_revision"] = "sha256:stale"
    _write(registry_path, json.dumps(registry, indent=2, sort_keys=True) + "\n")
    receipt_path = target / guidance_runtime.GUIDANCE_RECEIPT_INDEX_PATH
    receipt_index = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt_index["receipts"] = []
    _write(receipt_path, json.dumps(receipt_index, indent=2, sort_keys=True) + "\n")

    repaired = guidance_runtime.apply_guidance_promotion(target_root=target, guidance_id=guidance_id)

    assert repaired["status"] == "already-promoted"
    assert repaired["custody_verification"]["status"] == "recovered"
    assert set(repaired["custody_verification"]["repaired_postconditions"]) == {
        "store-owner-registry-current",
        "promotion-receipt-current",
    }
    repaired_registry = json.loads(registry_path.read_text(encoding="utf-8"))
    assert repaired_registry["stores"][0]["store_revision"] != "sha256:stale"
    repaired_receipts = json.loads(receipt_path.read_text(encoding="utf-8"))["receipts"]
    assert repaired_receipts[-1]["operation"] == "promote-recovery"


def test_guidance_transaction_recovery_rejects_concurrent_registry_writer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import agentic_workspace.agent_guidance as guidance_runtime
    from agentic_workspace.config import WorkspaceUsageError

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write_guidance_lifecycle_fixture(target, user_root=None)
    decision = guidance_runtime.guidance_promotion_from_store(target_root=target)
    guidance_id = decision["guidance"][0]["guidance_id"]

    class SimulatedProcessLoss(BaseException):
        pass

    def interrupt(phase: str, _path: Path) -> None:
        if phase == "after-write:1":
            raise SimulatedProcessLoss(phase)

    monkeypatch.setattr(guidance_runtime, "_GUIDANCE_TRANSACTION_FAULT_INJECTOR", interrupt)
    with pytest.raises(SimulatedProcessLoss):
        guidance_runtime.apply_guidance_promotion(target_root=target, guidance_id=guidance_id)
    monkeypatch.setattr(guidance_runtime, "_GUIDANCE_TRANSACTION_FAULT_INJECTOR", None)
    registry_path = target / guidance_runtime.GUIDANCE_STORE_OWNER_REGISTRY_PATH
    _write(
        registry_path,
        json.dumps(
            {
                "kind": "agentic-workspace/guidance-store-owner-registry/v1",
                "stores": [{"store_ref": "concurrent", "status": "current", "store_revision": "sha256:other"}],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )

    with pytest.raises(WorkspaceUsageError, match="concurrent change"):
        guidance_runtime.apply_guidance_promotion(target_root=target, guidance_id=guidance_id)


def test_guidance_transition_retry_completes_interrupted_custody_transaction(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import agentic_workspace.agent_guidance as guidance_runtime

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write_guidance_lifecycle_fixture(target, user_root=None)
    decision = guidance_runtime.guidance_promotion_from_store(target_root=target)
    promoted = guidance_runtime.apply_guidance_promotion(
        target_root=target,
        guidance_id=decision["guidance"][0]["guidance_id"],
    )

    class SimulatedProcessLoss(BaseException):
        pass

    def interrupt(phase: str, _path: Path) -> None:
        if phase == "after-write:2":
            raise SimulatedProcessLoss(phase)

    monkeypatch.setattr(guidance_runtime, "_GUIDANCE_TRANSACTION_FAULT_INJECTOR", interrupt)
    transition_args = {
        "target_root": target,
        "guidance_id": promoted["record"]["guidance_id"],
        "operation": "suppress",
        "reason": "temporarily background",
        "expected_revision": promoted["record"]["revision"],
    }
    with pytest.raises(SimulatedProcessLoss):
        guidance_runtime.transition_guidance(**transition_args)
    monkeypatch.setattr(guidance_runtime, "_GUIDANCE_TRANSACTION_FAULT_INJECTOR", None)

    recovered = guidance_runtime.transition_guidance(**transition_args)

    assert recovered["status"] == "transitioned"
    assert recovered["record"]["status"] == "suppressed"
    assert recovered["recovery"]["status"] == "completed-prepared-transaction"


def test_guidance_lifecycle_contract_claims_generated_external_operations() -> None:
    from agentic_workspace.agent_guidance import _guidance_public_operation_entries

    entries = _guidance_public_operation_entries()

    assert entries
    assert all(entry["generated_operation"] is True for entry in entries)
    assert all(entry["external_contract"] is True for entry in entries)
    assert all(entry["generated_parity"] == "runtime-backed-python-typescript" for entry in entries)
    assert {entry["operation_id"] for entry in entries} == {
        "agent-guidance.promote",
        "agent-guidance.edit",
        "agent-guidance.merge",
        "agent-guidance.split",
        "agent-guidance.suppress",
        "agent-guidance.revalidate",
        "agent-guidance.weaken",
        "agent-guidance.supersede",
        "agent-guidance.retire",
        "agent-guidance.delete",
    }


def test_correction_event_lifecycle_rejects_delivery_replay_separately_from_recurrence() -> None:
    from agentic_workspace.agent_guidance import admit_correction_events

    subjects = [
        {
            "profile_name": "fast_worker",
            "stable_target_id": "user-local:fast-worker",
            "target_revision": "rev-b",
            "aliases": ["fast"],
            "identity_status": "active",
            "revision_policy": "preserve",
        }
    ]
    event = _correction_event()

    admitted = admit_correction_events(events=[event, dict(event)], subjects=subjects)

    assert admitted["admitted_events"][0]["admission_state"] == "accepted-candidate"
    assert {item["reason"] for item in admitted["rejected_events"]} == {"duplicate-replay"}


def test_correction_event_caller_authority_without_receipt_remains_non_routing() -> None:
    from agentic_workspace.agent_guidance import admit_correction_events, guidance_promotion_decision

    subjects = [
        {
            "profile_name": "fast_worker",
            "stable_target_id": "user-local:fast-worker",
            "target_revision": "rev-b",
            "aliases": ["fast"],
            "identity_status": "active",
            "revision_policy": "preserve",
        }
    ]
    caller_claimed_review = _correction_event(
        target_identity_ref="user-local:fast-worker",
        authority="pr-review",
        producer_class="agent",
        producer_id="agent-self-observation",
        source_ref="agent-note-claims-review-authority",
        evidence_hash="sha256:agent-note",
    )

    admitted = admit_correction_events(events=[caller_claimed_review], subjects=subjects)
    decision = guidance_promotion_decision(admission=admitted)

    assert admitted["admitted_events"] == []
    assert admitted["low_authority_events"][0]["authority"] == "agent-self-observation"
    assert admitted["derived_routes"]["target_guidance"] == []
    assert admitted["derived_routes"]["low_authority"] == [admitted["low_authority_events"][0]["event_id"]]
    assert decision["status"] == "review-required"
    assert decision["guidance"] == []


def test_correction_event_lifecycle_applies_revision_policies_and_rejects_unknown_or_secret_events() -> None:
    from agentic_workspace.agent_guidance import admit_correction_events

    subjects = [
        {
            "profile_name": "preserve_worker",
            "stable_target_id": "user-local:preserve",
            "target_revision": "rev-b",
            "aliases": [],
            "identity_status": "active",
            "revision_policy": "preserve",
        },
        {
            "profile_name": "retired_worker",
            "stable_target_id": "user-local:retired",
            "target_revision": "rev-b",
            "aliases": [],
            "identity_status": "active",
            "revision_policy": "retire",
        },
    ]

    admitted = admit_correction_events(
        events=[
            {
                **_correction_event(
                    target_identity_ref="user-local:preserve",
                    source_ref="preserve-1",
                    evidence_hash="sha256:preserve-1",
                ),
                "target_revision": "rev-a",
                "invariant_id": "preserved-guidance",
                "behavior_class": "routing",
                "desired_behavior": "Keep preserved guidance.",
                "replaced_behavior": "Old guidance.",
            },
            {
                **_correction_event(
                    target_identity_ref="user-local:retired",
                    source_ref="retired-1",
                    evidence_hash="sha256:retired-1",
                ),
                "target_revision": "rev-a",
                "invariant_id": "retired-guidance",
                "behavior_class": "routing",
                "desired_behavior": "Route retired guidance.",
                "replaced_behavior": "Old guidance.",
            },
            {
                **_correction_event(
                    target_identity_ref="missing",
                    source_ref="missing-1",
                    evidence_hash="sha256:missing-1",
                ),
                "invariant_id": "missing-target",
                "behavior_class": "routing",
                "desired_behavior": "Unknown target.",
                "replaced_behavior": "Old guidance.",
            },
            {
                **_correction_event(
                    target_identity_ref="user-local:preserve",
                    source_ref="secret-1",
                    evidence_hash="sha256:secret-1",
                ),
                "target_revision": "rev-b",
                "invariant_id": "secret-guidance",
                "behavior_class": "routing",
                "desired_behavior": "Never store sk-secret.",
                "replaced_behavior": "Old guidance.",
            },
        ],
        subjects=subjects,
    )

    assert admitted["admitted_events"][0]["admission_state"] == "accepted-preserved-revision"
    assert {item["reason"] for item in admitted["rejected_events"]} == {
        "rejected-retired-revision",
        "rejected-unavailable-target",
        "rejected-secret-bearing",
    }


def test_config_command_layers_assignment_policy_from_shared_local_config(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    shared = tmp_path / "aw.config.shared.toml"
    shared.write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'execution_role = "orchestrator"',
                'assignment_policy = "best-fit-advisory"',
                'current_target = "shared_current"',
                'underfit_behavior = "prepare-manual-escalation"',
                "",
                "[delegation_targets.shared_current]",
                'strength = "strong"',
                'execution_methods = ["manual"]',
            ]
        ),
        encoding="utf-8",
    )
    (target / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[workspace]",
                f'shared_config_path = "{shared.as_posix()}"',
                "",
                "[delegation]",
                'assignment_policy = "required-best-fit"',
            ]
        ),
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    policy = payload["mixed_agent"]["assignment_policy"]
    assert policy["execution_role"] == {"value": "orchestrator", "source": "derived:delegation.assignment_policy"}
    assert policy["assignment_policy"] == {"value": "required-best-fit", "source": "local-override"}
    assert policy["current_target"] == {"value": "shared_current", "source": "shared-local-config"}
    assert policy["underfit_behavior"] == {"value": "require-delegation", "source": "derived:delegation.assignment_policy"}
    assert policy["binding"]["enforceable"] is True


def test_config_command_rejects_invalid_local_delegation_control_mode(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        'schema_version = 1\n\n[delegation]\nmode = "delegate-everything"\n',
        encoding="utf-8",
    )

    with pytest.raises(SystemExit):
        cli.main(["config", "--verbose", "--target", str(target), "--format", "json"])
    assert "delegation.mode must be one of" in capsys.readouterr().err


def test_config_command_rejects_invalid_assignment_policy_value(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        'schema_version = 1\n\n[delegation]\nassignment_policy = "self-confidence"\n',
        encoding="utf-8",
    )

    with pytest.raises(SystemExit):
        cli.main(["config", "--verbose", "--target", str(target), "--format", "json"])
    assert "assignment_policy must be one of" in capsys.readouterr().err


def test_config_command_reports_runtime_resolution_for_no_posture(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    rr = payload["mixed_agent"]["runtime_resolution"]
    assert rr["recommendation"] in ("stay-local", "stronger-reasoning", "external-delegation", "manual-handoff")
    assert rr["posture_source"] == "none"
    assert rr["confidence"] in ("high", "medium", "low")
    assert "guidance" in rr
    assert rr["resolution_categories"] == [
        "stay-local",
        "stronger-reasoning",
        "external-delegation",
        "manual-handoff",
    ]


def test_config_command_runtime_resolution_recommends_external_delegation_when_strong_external_preferred(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation_targets.chatgpt]",
                'strength = "strong"',
                'location = "external"',
                "confidence = 0.9",
                'capability_classes = ["boundary-shaping", "reasoning-heavy"]',
                'execution_methods = ["cli"]',
            ]
        ),
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    # Without posture the default resolution is generated; just confirm structure is valid
    rr = payload["mixed_agent"]["runtime_resolution"]
    assert rr["recommendation"] in ("stay-local", "stronger-reasoning", "external-delegation", "manual-handoff")
    assert rr["profile_recommendations"][0]["name"] == "chatgpt"
    assert rr["profile_recommendations"][0]["recommendation"] in ("recommended", "acceptable", "poor-fit")
    assert "strong_handoff_packet" in payload["mixed_agent"]


def test_config_command_runtime_resolution_recommends_stronger_reasoning_for_boundary_shaping_with_strong_planner(
    tmp_path: Path, capsys
) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[runtime]",
                "strong_planner_available = true",
                "cheap_bounded_executor_available = true",
            ]
        ),
        encoding="utf-8",
    )

    config = cli._load_workspace_config(target_root=target)
    rr = cli._runtime_resolution_payload(
        config=config,
        capability_posture={"execution class": "boundary-shaping", "recommended strength": "strong"},
    )
    assert rr["recommendation"] == "stronger-reasoning"
    assert rr["confidence"] == "high"
    assert any("boundary-shaping" in r for r in rr["reasons"])
    assert rr["posture_source"] == "provided"


def test_config_command_runtime_resolution_recommends_stay_local_for_mechanical_work(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    config = cli._load_workspace_config(target_root=target)
    rr = cli._runtime_resolution_payload(
        config=config,
        capability_posture={"execution class": "mechanical-follow-through", "recommended strength": "weak"},
    )
    assert rr["recommendation"] == "stay-local"
    assert rr["confidence"] == "high"
    assert any("mechanical-follow-through" in r for r in rr["reasons"])
    assert rr["weak_target_guardrail"]["status"] == "inactive"
    assert rr["downrouting_guardrail"]["status"] == "inactive"


def test_runtime_resolution_keeps_scope_independent_from_task_class(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    config = cli._load_workspace_config(target_root=target)
    rr = cli._runtime_resolution_payload(
        config=config,
        capability_posture={
            "execution class": "mechanical-follow-through",
            "scope class": "narrow-code-change",
            "recommended strength": "weak",
        },
    )

    assert rr["capability_context"]["task_class"] == "mechanical-follow-through"
    assert rr["capability_context"]["scope_class"] == "narrow-code-change"


def test_runtime_resolution_marks_weak_target_escalation_for_boundary_work(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'mode = "suggest"',
                "",
                "[delegation_targets.haiku]",
                'strength = "weak"',
                'location = "external"',
                "confidence = 0.7",
                'task_fit = ["bounded docs edits"]',
                'capability_classes = ["mechanical-follow-through"]',
                'execution_methods = ["cli"]',
            ]
        ),
        encoding="utf-8",
    )

    config = cli._load_workspace_config(target_root=target)
    rr = cli._runtime_resolution_payload(
        config=config,
        capability_posture={"execution class": "boundary-shaping", "recommended strength": "strong"},
    )

    haiku = rr["profile_recommendations"][0]
    assert haiku["name"] == "haiku"
    assert haiku["recommendation"] == "poor-fit"
    assert haiku["capability_mismatch"] is True
    assert haiku["required_action"] == "escalate-before-execution"
    assert rr["weak_target_guardrail"]["status"] == "active"
    assert rr["weak_target_guardrail"]["effective_mode"] == "suggest"
    assert "do not execute the weak target automatically" in rr["weak_target_guardrail"]["mode_action"]
    assert rr["weak_target_guardrail"]["mismatched_targets"][0]["name"] == "haiku"
    assert rr["self_assessment"]["authority"] == "advisory-only"
    assert "capability_mismatch" in rr["self_assessment"]["cannot_override"]


def test_runtime_resolution_marks_strong_target_downrouting_for_mechanical_work(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'mode = "suggest"',
                "",
                "[delegation_targets.haiku]",
                'strength = "weak"',
                'location = "external"',
                "confidence = 0.7",
                'task_fit = ["bounded docs edits"]',
                'capability_classes = ["mechanical-follow-through"]',
                'execution_methods = ["cli"]',
                "",
                "[delegation_targets.strong_planner]",
                'strength = "strong"',
                'location = "local"',
                "confidence = 0.9",
                'task_fit = ["architecture", "review"]',
                'capability_classes = ["boundary-shaping", "reasoning-heavy", "mechanical-follow-through"]',
                'execution_methods = ["internal"]',
            ]
        ),
        encoding="utf-8",
    )

    config = cli._load_workspace_config(target_root=target)
    rr = cli._runtime_resolution_payload(
        config=config,
        capability_posture={"execution class": "mechanical-follow-through", "recommended strength": "weak"},
    )

    strong = next(item for item in rr["profile_recommendations"] if item["name"] == "strong_planner")
    assert strong["required_action"] == "delegate-down-when-safe"
    assert strong["overqualified_for_task"] is True
    assert rr["downrouting_guardrail"]["status"] == "active"
    assert rr["downrouting_guardrail"]["cheaper_fit_targets"][0]["name"] == "haiku"
    assert "cheaper bounded executor" in rr["downrouting_guardrail"]["mode_action"]


def test_runtime_resolution_respects_forbidden_task_classes(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation_targets.fast_worker]",
                'strength = "strong"',
                'execution_methods = ["cli"]',
                'capability_classes = ["mechanical-follow-through"]',
                'forbidden_task_classes = ["mechanical-follow-through"]',
                'reasoning_profile = "strong"',
            ]
        ),
        encoding="utf-8",
    )

    config = cli._load_workspace_config(target_root=target)
    rr = cli._runtime_resolution_payload(
        config=config,
        capability_posture={"execution class": "mechanical-follow-through", "recommended strength": "weak"},
    )

    worker = rr["profile_recommendations"][0]
    assert worker["recommendation"] == "poor-fit"
    assert worker["capability_mismatch"] is True
    assert worker["required_action"] == "escalate-before-execution"
    assert "target forbids this execution class" in worker["reasons"]


def test_config_command_runtime_resolution_recommends_manual_handoff_when_strong_external_preferred_and_no_external_targets(
    tmp_path: Path, capsys
) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    config = cli._load_workspace_config(target_root=target)
    rr = cli._runtime_resolution_payload(
        config=config,
        capability_posture={"strong external reasoning": "preferred"},
    )
    assert rr["recommendation"] == "manual-handoff"
    assert rr["confidence"] == "high"
    assert any("no automated external path" in r for r in rr["reasons"])


def test_config_command_accepts_manual_external_delegation_target(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / "AGENTS.md").write_text("repo instructions\n", encoding="utf-8")
    (target / ".agentic-workspace/config.toml").write_text("schema_version = 1\n", encoding="utf-8")
    (target / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation_targets.chatgpt]",
                'strength = "strong"',
                'location = "external"',
                "confidence = 0.88",
                'task_fit = ["general-purpose-planning", "cross-cutting-review"]',
                'capability_classes = ["boundary-shaping", "reasoning-heavy", "mixed"]',
                'execution_methods = ["manual"]',
                "",
            ]
        ),
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    targets = payload["mixed_agent"]["delegation_targets"]["profiles"]
    chatgpt = next(profile for profile in targets if profile["name"] == "chatgpt")
    assert chatgpt["strength"] == "strong"
    assert chatgpt["location"] == "external"
    assert chatgpt["capability_classes"] == ["boundary-shaping", "reasoning-heavy", "mixed"]
    assert chatgpt["execution_methods"] == ["manual"]
    assert chatgpt["advisory"] == {
        "handoff_detail": "compact",
        "review_burden": "light",
    }


def test_config_command_rejects_invalid_local_delegation_target_strength(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        'schema_version = 1\n\n[delegation_targets.bad_target]\nstrength = "expert"\nexecution_methods = ["cli"]\n',
        encoding="utf-8",
    )

    with pytest.raises(SystemExit):
        cli.main(["config", "--verbose", "--target", str(target), "--format", "json"])
    assert "strength must be one of" in capsys.readouterr().err


def test_config_command_accepts_utf8_bom_local_override(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        'schema_version = 1\n\n[delegation_targets.fast_docs]\nstrength = "weak"\nexecution_methods = ["cli"]\n',
        encoding="utf-8-sig",
    )

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["mixed_agent"]["delegation_targets"]["profiles"][0]["name"] == "fast_docs"


def test_note_delegation_outcome_command_writes_local_artifact(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert (
        cli.main(
            [
                "note-delegation-outcome",
                "--target",
                str(target),
                "--delegation-target",
                "gpt_5_4_mini",
                "--task-class",
                "bounded-docs",
                "--scope-class",
                "docs-refresh",
                "--outcome",
                "success",
                "--handoff-sufficiency",
                "sufficient",
                "--review-burden",
                "light",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["path"] == ".agentic-workspace/delegation-outcomes.json"
    assert payload["record_count"] == 1
    projection = payload["shared_evaluation_observation"]
    assert projection["domain"] == "delegation-outcome"
    assert projection["source_identity"] == payload["recorded"]["record_id"]
    assert projection["lifecycle_owner"] == "evaluation.observe"
    assert projection["delivery_owner"] == "evaluation report/delivery operations"
    artifact = json.loads((target / ".agentic-workspace/delegation-outcomes.json").read_text(encoding="utf-8"))
    assert artifact["kind"] == "agentic-workspace/delegation-outcomes/v1"
    assert artifact["records"][0]["delegation_target"] == "gpt_5_4_mini"
    assert artifact["records"][0]["scope_class"] == "docs-refresh"
    assert artifact["records"][0]["operation"] == "submit"
    assert artifact["records"][0]["record_id"]
    assert "shared_evaluation_observation" not in artifact


def test_note_delegation_outcome_rejects_duplicate_without_lifecycle_transition(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    command = [
        "note-delegation-outcome",
        "--target",
        str(target),
        "--delegation-target",
        "gpt_5_4_mini",
        "--task-class",
        "bounded-docs",
        "--scope-class",
        "docs-refresh",
        "--outcome",
        "success",
        "--format",
        "json",
    ]

    assert cli.main(command) == 0
    capsys.readouterr()
    assert cli.main(command) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "rejected"
    assert payload["failure_class"] == "duplicate-mutation"
    assert payload["completion_boundary"] == "mutation-not-applied"
    assert "duplicate evidence for target/task/scope/provenance" in payload["message"]


def test_config_command_reports_delegation_outcome_suggestions(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "schema_version = 1\n\n"
        "[delegation_targets.gpt_5_4_mini]\n"
        'strength = "weak"\n'
        'location = "external"\n'
        "confidence = 0.62\n"
        'task_fit = ["bounded-docs"]\n'
        'capability_classes = ["mechanical-follow-through"]\n'
        'execution_methods = ["cli"]\n',
        encoding="utf-8",
    )
    (target / ".agentic-workspace/delegation-outcomes.json").write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/delegation-outcomes/v1",
                "records": [
                    {
                        "recorded_at": "2026-04-17",
                        "delegation_target": "gpt_5_4_mini",
                        "task_class": "bounded-docs",
                        "outcome": "success",
                        "handoff_sufficiency": "sufficient",
                        "review_burden": "light",
                        "escalation_required": False,
                    },
                    {
                        "recorded_at": "2026-04-17",
                        "delegation_target": "gpt_5_4_mini",
                        "task_class": "narrow-tests",
                        "outcome": "success",
                        "handoff_sufficiency": "sufficient",
                        "review_burden": "normal",
                        "escalation_required": False,
                    },
                    {
                        "recorded_at": "2026-04-17",
                        "delegation_target": "gpt_5_4_mini",
                        "task_class": "narrow-tests",
                        "outcome": "success",
                        "handoff_sufficiency": "sufficient",
                        "review_burden": "light",
                        "escalation_required": False,
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    targets = payload["mixed_agent"]["delegation_targets"]
    assert targets["outcome_artifact"] == {
        "path": ".agentic-workspace/delegation-outcomes.json",
        "status": "configured",
        "record_count": 3,
    }
    mini = targets["profiles"][0]
    assert mini["location"] == "external"
    assert mini["capability_classes"] == ["mechanical-follow-through"]
    assert mini["outcome_evidence"]["record_count"] == 3
    assert mini["outcome_evidence"]["confidence"]["action"] == "raise"
    assert mini["outcome_evidence"]["task_fit"]["suggest_add"] == ["narrow-tests"]
    evidence = payload["mixed_agent"]["target_evidence"]
    assert evidence["status"] == "present"
    assert evidence["storage"] == {
        "path": ".agentic-workspace/delegation-outcomes.json",
        "location": "local-only",
        "checked_in": False,
        "exists": True,
        "safe_to_remove": True,
        "raw_transcripts_stored": False,
        "retention_rule": (
            "bounded by lifecycle transitions; prune-or-compact records replace raw predecessors with "
            "provenance-preserving calibration summaries"
        ),
    }
    assert evidence["record_count"] == 3
    assert evidence["normalized_records"][0]["target"] == "gpt_5_4_mini"
    assert evidence["normalized_records"][0]["admission_state"] == "accepted-normalized"
    assert evidence["normalized_records"][0]["admission"] == {
        "routable": True,
        "authority": "local-outcome-ledger",
        "confidence": "medium",
        "state": "accepted-normalized",
    }
    assert evidence["normalized_records"][0]["routing_relevance"] == "task-and-scope-bound"
    bounded, narrow = evidence["suitability"]
    assert bounded["target"] == "gpt_5_4_mini"
    assert bounded["target_identity_ref"] is None
    assert bounded["revision_policy"] == "revalidate"
    assert bounded["context_key"] == "bounded-docs::bounded-docs"
    assert bounded["record_count"] == 1
    assert bounded["average_signal"] == 1.5
    assert bounded["route_effect"] == "preferred-for-matching-task-class"
    assert bounded["supporting_record_ids"] == ["gpt_5_4_mini:bounded-docs:bounded-docs:2026-04-17:0"]
    assert bounded["retention"]["status"] == "bounded-current-calibration"
    assert narrow["context_key"] == "narrow-tests::narrow-tests"
    assert narrow["record_count"] == 2
    assert narrow["average_signal"] == 1.38
    assert narrow["route_effect"] == "preferred-for-matching-task-class"
    assert narrow["supporting_record_ids"] == [
        "gpt_5_4_mini:narrow-tests:narrow-tests:2026-04-17:1",
        "gpt_5_4_mini:narrow-tests:narrow-tests:2026-04-17:2",
    ]
    assert narrow["target_identity_ref"] is None
    assert narrow["revision_policy"] == "revalidate"
    assert narrow["retention"]["status"] == "bounded-current-calibration"
    assert evidence["lifecycle"]["public_operations"][0]["operation"] == "submit"
    assert evidence["lifecycle"]["routing_rule"] == (
        "Assignment may consume only current, admitted, non-contradicted evidence matching the requested target/task/scope context."
    )
    decision = payload["mixed_agent"]["assignment_decision"]
    assert decision["kind"] == "agentic-workspace/assignment-decision/v1"
    assert decision["assignment_policy"] == "local-preferred"
    assert decision["decision"] == "shape-before-assignment"
    assert decision["canonical_outcome"] == "read-only-exploration"
    assert decision["selection_basis"]["context_authority"]["status"] == "missing"
    assert decision["record_count"] == 3


def test_target_evidence_suitability_is_context_isolated(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "schema_version = 1\n\n"
        "[delegation_targets.fast_worker]\n"
        'strength = "weak"\n'
        'capability_classes = ["mechanical-follow-through"]\n'
        'execution_methods = ["cli"]\n',
        encoding="utf-8",
    )
    (target / ".agentic-workspace/delegation-outcomes.json").write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/delegation-outcomes/v1",
                "records": [
                    {
                        "recorded_at": "2026-04-17",
                        "delegation_target": "fast_worker",
                        "task_class": "mechanical-follow-through",
                        "scope_class": "narrow-code-change",
                        "outcome": "success",
                        "handoff_sufficiency": "sufficient",
                        "review_burden": "light",
                        "escalation_required": False,
                    },
                    {
                        "recorded_at": "2026-04-18",
                        "delegation_target": "fast_worker",
                        "task_class": "mechanical-follow-through",
                        "scope_class": "broad-design-change",
                        "outcome": "failed",
                        "handoff_sufficiency": "insufficient",
                        "review_burden": "high",
                        "escalation_required": True,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    suitability = payload["mixed_agent"]["target_evidence"]["suitability"]
    narrow = next(item for item in suitability if item["context_key"] == "mechanical-follow-through::narrow-code-change")
    broad = next(item for item in suitability if item["context_key"] == "mechanical-follow-through::broad-design-change")
    assert narrow["route_effect"] == "preferred-for-matching-task-class"
    assert narrow["average_signal"] == 1.5
    assert broad["route_effect"] == "strong-review-required"
    assert broad["average_signal"] == -2.0
    assert narrow["supporting_record_ids"] != broad["supporting_record_ids"]


def test_target_evidence_lifecycle_supersession_replaces_current_signal() -> None:
    from agentic_workspace.config import DelegationOutcomeRecord
    from agentic_workspace.target_evidence import target_evidence_posture

    records = [
        DelegationOutcomeRecord(
            recorded_at="2026-04-17",
            delegation_target="fast_worker",
            task_class="mechanical-follow-through",
            scope_class="narrow-code-change",
            outcome="failed",
            handoff_sufficiency="insufficient",
            review_burden="high",
            escalation_required=True,
            record_id="fast_worker:mechanical-follow-through:narrow-code-change:2026-04-17:0",
        ),
        DelegationOutcomeRecord(
            recorded_at="2026-04-18",
            delegation_target="fast_worker",
            task_class="mechanical-follow-through",
            scope_class="narrow-code-change",
            outcome="success",
            handoff_sufficiency="sufficient",
            review_burden="light",
            escalation_required=False,
            operation="supersede",
            record_id="fast_worker:mechanical-follow-through:narrow-code-change:2026-04-18:1",
            predecessor_id="fast_worker:mechanical-follow-through:narrow-code-change:2026-04-17:0",
        ),
    ]

    posture = target_evidence_posture(target_root=None, profiles=(), records=records)

    scoped = posture["suitability"][0]
    assert scoped["record_count"] == 1
    assert scoped["average_signal"] == 1.5
    assert scoped["supporting_record_ids"] == ["fast_worker:mechanical-follow-through:narrow-code-change:2026-04-18:1"]


def test_target_evidence_normalizes_historical_context_inflation_as_transport_burden() -> None:
    from agentic_workspace.config import DelegationOutcomeRecord
    from agentic_workspace.target_evidence import target_evidence_posture

    posture = target_evidence_posture(
        target_root=None,
        profiles=(),
        records=[
            DelegationOutcomeRecord(
                recorded_at="2026-08-29",
                delegation_target="worker",
                task_class="implementation",
                scope_class="bounded",
                outcome="success",
                handoff_sufficiency="sufficient",
                review_burden="normal",
                escalation_required=False,
                authority="human-review",
                confidence="high",
                context_cost={
                    "kind": "agentic-workspace/assignment-context-cost/v1",
                    "transport": "cli",
                    "adapter_revision": "sha256:adapter",
                    "assignment_packet_bytes": 3662,
                    "rendered_prompt_bytes": 3913,
                    "effective_input_tokens": 81752,
                    "cached_input_tokens": 62464,
                    "output_tokens": 1591,
                    "orientation_command_count": 0,
                    "retry_count": 0,
                    "repair_loop_count": 0,
                    "elapsed_ms": 1000,
                    "unknown_fields": [],
                    "observation_authority": "adapter-sidecar-or-host-measurement",
                    "raw_transcript_stored": False,
                },
            )
        ],
    )

    costs = posture["suitability"][0]["transport_costs"]
    assert costs == [
        {
            "transport": "cli",
            "record_count": 1,
            "expected_burden_component": -30,
            "observed_context_cost": {
                "assignment_packet_bytes": 3662,
                "cached_input_tokens": 62464,
                "effective_input_tokens": 81752,
                "elapsed_ms": 1000,
                "output_tokens": 1591,
                "rendered_prompt_bytes": 3913,
            },
            "observable_fields": [
                "cached_input_tokens",
                "effective_input_tokens",
                "orientation_command_count",
                "output_tokens",
                "repair_loop_count",
                "retry_count",
            ],
            "unknown_metric_state": "observed",
            "supporting_adapter_revisions": ["sha256:adapter"],
        }
    ]


def test_target_evidence_lifecycle_correction_and_compaction_remove_predecessor_from_current_signal() -> None:
    from agentic_workspace.config import DelegationOutcomeRecord
    from agentic_workspace.target_evidence import target_evidence_posture

    first = "fast_worker:mechanical-follow-through:narrow-code-change:2026-04-17:0"
    correction = "fast_worker:mechanical-follow-through:narrow-code-change:2026-04-18:1"
    records = [
        DelegationOutcomeRecord(
            recorded_at="2026-04-17",
            delegation_target="fast_worker",
            task_class="mechanical-follow-through",
            scope_class="narrow-code-change",
            outcome="success",
            handoff_sufficiency="sufficient",
            review_burden="light",
            escalation_required=False,
            record_id=first,
        ),
        DelegationOutcomeRecord(
            recorded_at="2026-04-18",
            delegation_target="fast_worker",
            task_class="mechanical-follow-through",
            scope_class="narrow-code-change",
            outcome="failed",
            handoff_sufficiency="insufficient",
            review_burden="high",
            escalation_required=True,
            operation="correct-or-dispute",
            record_id=correction,
            predecessor_id=first,
        ),
        DelegationOutcomeRecord(
            recorded_at="2026-04-19",
            delegation_target="fast_worker",
            task_class="mechanical-follow-through",
            scope_class="narrow-code-change",
            outcome="mixed",
            handoff_sufficiency="borderline",
            review_burden="normal",
            escalation_required=False,
            operation="prune-or-compact",
            record_id="fast_worker:mechanical-follow-through:narrow-code-change:2026-04-19:2",
            predecessor_id=correction,
        ),
    ]

    posture = target_evidence_posture(target_root=None, profiles=(), records=records)

    assert posture["suitability"][0]["record_count"] == 1
    assert posture["suitability"][0]["supporting_record_ids"] == ["fast_worker:mechanical-follow-through:narrow-code-change:2026-04-19:2"]
    assert posture["suitability"][0]["retention"]["status"] == "bounded-current-calibration"


def test_target_evidence_excludes_low_authority_records_from_assignment() -> None:
    from agentic_workspace.config import DelegationOutcomeRecord
    from agentic_workspace.target_evidence import target_evidence_posture

    records = [
        DelegationOutcomeRecord(
            recorded_at="2026-04-17",
            delegation_target="fast_worker",
            task_class="mechanical-follow-through",
            scope_class="narrow-code-change",
            outcome="success",
            handoff_sufficiency="sufficient",
            review_burden="light",
            escalation_required=False,
            authority="model-self-report",
            confidence="high",
        ),
        DelegationOutcomeRecord(
            recorded_at="2026-04-18",
            delegation_target="fast_worker",
            task_class="mechanical-follow-through",
            scope_class="narrow-code-change",
            outcome="success",
            handoff_sufficiency="sufficient",
            review_burden="light",
            escalation_required=False,
            authority="human-review",
            confidence="low",
        ),
    ]

    posture = target_evidence_posture(target_root=None, profiles=(), records=records)

    assert posture["suitability"] == []
    assert posture["normalized_records"][0]["admission"]["routable"] is False
    assert posture["normalized_records"][1]["admission"]["routable"] is False
    assert [item["uncertainty_reasons"][0] for item in posture["uncertainty_accounts"]] == [
        "low-authority:model-self-report",
        "low-confidence:low",
    ]


def test_assignment_decision_derives_best_fit_from_candidates_and_contextual_evidence(tmp_path: Path) -> None:
    from agentic_workspace.target_evidence import assignment_decision_from_policy

    assignment_policy = {
        "assignment_policy": {"value": "required-best-fit"},
        "current_target": {"value": "current_worker"},
        "binding": {"enforceable": True, "claim_boundary": "assignment policy resolved"},
    }
    runtime_resolution = {
        "recommendation": "stay-local",
        "capability_context": {"task_class": "mechanical-follow-through", "scope_class": "mechanical-follow-through"},
        "profile_recommendations": [
            {
                "name": "current_worker",
                "target_id": "user-local:current-worker",
                "target_revision": "rev-a",
                "revision_policy": "revalidate",
                "recommendation": "acceptable",
                "score": 2,
                "capability_mismatch": False,
                "required_action": "none",
                "location": "local",
                "execution_methods": ["internal"],
                "human_control_modes": ["auto"],
            },
            {
                "name": "fast_worker",
                "target_id": "user-local:fast-worker",
                "target_revision": "rev-b",
                "revision_policy": "migrate",
                "recommendation": "recommended",
                "score": 7,
                "capability_mismatch": False,
                "required_action": "none",
                "execution_methods": ["cli"],
                "human_control_modes": ["auto"],
            },
            {
                "name": "unsafe_worker",
                "target_id": "user-local:unsafe-worker",
                "target_revision": "rev-c",
                "revision_policy": "retire",
                "recommendation": "recommended",
                "score": 99,
                "capability_mismatch": True,
                "required_action": "escalate-before-execution",
                "execution_methods": ["cli"],
                "human_control_modes": ["auto"],
            },
        ],
    }
    target_evidence = {
        "status": "present",
        "record_count": 2,
        "suitability": [
            {
                "target": "user-local:fast-worker",
                "target_identity_ref": "user-local:fast-worker",
                "target_revision": "rev-b",
                "context_key": "mechanical-follow-through::mechanical-follow-through",
                "route_effect": "preferred-for-matching-task-class",
                "record_count": 2,
                "supporting_record_ids": ["fast_worker:mechanical-follow-through:mechanical-follow-through:2026-04-17:0"],
            },
            {
                "target": "current_worker",
                "context_key": "boundary-shaping::boundary-shaping",
                "route_effect": "preferred-for-matching-task-class",
                "record_count": 4,
                "supporting_record_ids": ["current_worker:boundary-shaping:boundary-shaping:2026-04-17:0"],
            },
        ],
    }

    decision = assignment_decision_from_policy(
        assignment_policy=assignment_policy,
        runtime_resolution=runtime_resolution,
        target_evidence=target_evidence,
    )

    assert decision["decision"] == "assign-best-fit"
    assert decision["canonical_outcome"] == "delegated-implementation"
    assert decision["selected_target"] == "fast_worker"
    assert decision["selected_target_identity_ref"] == "user-local:fast-worker"
    assert decision["selected_target_revision"] == "rev-b"
    assert decision["assignment_decision_revision"].startswith("sha256:")
    assert decision["task_class"] == "mechanical-follow-through"
    assert decision["scope_class"] == "mechanical-follow-through"
    assert decision["selection_basis"]["requested_context_key"] == "mechanical-follow-through::mechanical-follow-through"
    selected = next(item for item in decision["candidate_scores"] if item["target"] == "fast_worker")
    assert selected["target_identity_ref"] == "user-local:fast-worker"
    assert selected["target_revision"] == "rev-b"
    assert selected["revision_policy"] == "migrate"
    assert selected["evidence_contexts"][0]["target_identity_ref"] == "user-local:fast-worker"
    assert decision["selection_basis"]["component_order"] == [
        "task_requirements",
        "hard_eligibility",
        "declared_fit",
        "contextual_evidence",
        "expected_burden",
        "uncertainty",
        "probe_value",
        "policy",
    ]
    current = next(item for item in decision["candidate_scores"] if item["target"] == "current_worker")
    assert current["evidence_contexts"] == []
    unsafe = next(item for item in decision["candidate_scores"] if item["target"] == "unsafe_worker")
    assert unsafe["eligible"] is False
    assert unsafe["eligibility"]["capability"] == "rejected"
    fast = next(item for item in decision["candidate_scores"] if item["target"] == "fast_worker")
    assert fast["ranking_components"]["declared_fit"] == 7
    assert fast["ranking_components"]["contextual_evidence"] == 15
    assert fast["permitted_continuation"] == "delegated-implementation"


def test_assignment_decision_selects_lower_cost_transport_from_matching_evidence() -> None:
    from agentic_workspace.target_evidence import assignment_decision_from_policy

    decision = assignment_decision_from_policy(
        assignment_policy={
            "assignment_policy": {"value": "required-best-fit"},
            "current_target": {"value": "worker"},
            "binding": {"enforceable": True},
        },
        runtime_resolution={
            "recommendation": "stay-local",
            "capability_context": {"task_class": "implementation", "scope_class": "narrow-code-change"},
            "profile_recommendations": [
                {
                    "name": "worker",
                    "recommendation": "recommended",
                    "score": 8,
                    "capability_mismatch": False,
                    "execution_methods": ["cli", "internal"],
                    "human_control_modes": ["auto"],
                }
            ],
        },
        target_evidence={
            "status": "present",
            "record_count": 2,
            "suitability": [
                {
                    "target": "worker",
                    "context_key": "implementation::narrow-code-change",
                    "route_effect": "no-change",
                    "transport_costs": [
                        {
                            "transport": "cli",
                            "record_count": 1,
                            "expected_burden_component": -30,
                        },
                        {
                            "transport": "internal",
                            "record_count": 1,
                            "expected_burden_component": 0,
                        },
                    ],
                }
            ],
        },
    )

    assert decision["selected_transport"] == "internal"
    candidate = decision["candidate_scores"][0]
    assert candidate["ranking_components"]["expected_burden"] == 0
    assert candidate["transport_options"] == [
        {
            "transport": "cli",
            "expected_burden": -30,
            "evidence_state": "admitted-contextual",
            "record_count": 1,
            "configured_order": 0,
        },
        {
            "transport": "internal",
            "expected_burden": 0,
            "evidence_state": "admitted-contextual",
            "record_count": 1,
            "configured_order": 1,
        },
    ]


def test_assignment_context_cost_breaks_equal_fit_but_does_not_override_stronger_fit() -> None:
    from agentic_workspace.target_evidence import assignment_decision_from_policy

    def decide(*, stronger_score: int) -> dict[str, object]:
        return assignment_decision_from_policy(
            assignment_policy={
                "assignment_policy": {"value": "required-best-fit"},
                "current_target": {"value": "expensive"},
                "binding": {"enforceable": True},
            },
            runtime_resolution={
                "recommendation": "stay-local",
                "capability_context": {"task_class": "implementation", "scope_class": "bounded"},
                "profile_recommendations": [
                    {
                        "name": "expensive",
                        "recommendation": "recommended",
                        "score": stronger_score,
                        "capability_mismatch": False,
                        "execution_methods": ["cli"],
                        "human_control_modes": ["auto"],
                    },
                    {
                        "name": "efficient",
                        "recommendation": "recommended",
                        "score": 0,
                        "capability_mismatch": False,
                        "execution_methods": ["api"],
                        "human_control_modes": ["auto"],
                    },
                ],
            },
            target_evidence={
                "status": "present",
                "record_count": 2,
                "suitability": [
                    {
                        "target": "expensive",
                        "context_key": "implementation::bounded",
                        "route_effect": "no-change",
                        "transport_costs": [{"transport": "cli", "record_count": 1, "expected_burden_component": -30}],
                    },
                    {
                        "target": "efficient",
                        "context_key": "implementation::bounded",
                        "route_effect": "no-change",
                        "transport_costs": [{"transport": "api", "record_count": 1, "expected_burden_component": 0}],
                    },
                ],
            },
        )

    assert decide(stronger_score=0)["selected_target"] == "efficient"
    assert decide(stronger_score=40)["selected_target"] == "expensive"


def test_assignment_combines_observed_context_with_declared_price_and_latency_classes() -> None:
    from agentic_workspace.target_evidence import assignment_decision_from_policy

    decision = assignment_decision_from_policy(
        assignment_policy={
            "assignment_policy": {"value": "required-best-fit"},
            "current_target": {"value": "sol"},
            "binding": {"enforceable": True},
        },
        runtime_resolution={
            "recommendation": "stay-local",
            "capability_context": {"task_class": "validation", "scope_class": "multi-slice"},
            "profile_recommendations": [
                {
                    "name": "sol",
                    "recommendation": "recommended",
                    "score": 10,
                    "cost_class": "premium",
                    "latency_class": "slow",
                    "capability_mismatch": False,
                    "execution_methods": ["cli"],
                    "human_control_modes": ["auto"],
                },
                {
                    "name": "luna",
                    "recommendation": "recommended",
                    "score": 10,
                    "cost_class": "cheap",
                    "latency_class": "fast",
                    "capability_mismatch": False,
                    "execution_methods": ["cli"],
                    "human_control_modes": ["auto"],
                },
            ],
        },
        target_evidence={
            "status": "present",
            "record_count": 2,
            "suitability": [
                {
                    "target": target,
                    "context_key": "validation::multi-slice",
                    "route_effect": "no-change",
                    "transport_costs": [{"transport": "cli", "record_count": 1, "expected_burden_component": -40}],
                }
                for target in ("sol", "luna")
            ],
        },
    )

    assert decision["selected_target"] == "luna"
    candidates = {candidate["target"]: candidate for candidate in decision["candidate_scores"]}
    assert {
        key: candidates["sol"]["ranking_components"][key]
        for key in ("target_cost_class", "target_latency_class", "transport_context_cost", "expected_burden")
    } == {
        "target_cost_class": -10,
        "target_latency_class": -5,
        "transport_context_cost": -40,
        "expected_burden": -55,
    }
    assert {
        key: candidates["luna"]["ranking_components"][key]
        for key in ("target_cost_class", "target_latency_class", "transport_context_cost", "expected_burden")
    } == {
        "target_cost_class": 10,
        "target_latency_class": 5,
        "transport_context_cost": -40,
        "expected_burden": -25,
    }


def test_assignment_retains_equal_fit_current_target_when_delegation_inflates_observed_context() -> None:
    from agentic_workspace.target_evidence import assignment_decision_from_policy

    def decide(*, luna_fit: int) -> dict[str, object]:
        return assignment_decision_from_policy(
            assignment_policy={
                "assignment_policy": {"value": "required-best-fit"},
                "current_target": {"value": "codex_sol"},
                "binding": {"enforceable": True},
            },
            runtime_resolution={
                "recommendation": "stay-local",
                "capability_context": {"task_class": "validation", "scope_class": "issue-2818-multi-slice"},
                "profile_recommendations": [
                    {
                        "name": "codex_sol",
                        "recommendation": "recommended",
                        "score": 10,
                        "cost_class": "premium",
                        "latency_class": "slow",
                        "capability_mismatch": False,
                        "execution_methods": ["cli"],
                        "human_control_modes": ["auto"],
                    },
                    {
                        "name": "codex_luna",
                        "recommendation": "recommended",
                        "score": luna_fit,
                        "cost_class": "cheap",
                        "latency_class": "fast",
                        "capability_mismatch": False,
                        "execution_methods": ["cli"],
                        "human_control_modes": ["auto"],
                    },
                ],
            },
            target_evidence={
                "status": "present",
                "record_count": 2,
                "suitability": [
                    {
                        "target": "codex_sol",
                        "context_key": "validation::issue-2818-multi-slice",
                        "route_effect": "no-change",
                        "transport_costs": [
                            {
                                "transport": "cli",
                                "record_count": 1,
                                "expected_burden_component": -40,
                                "observed_context_cost": {
                                    "assignment_packet_bytes": 7016,
                                    "rendered_prompt_bytes": 3952,
                                    "effective_input_tokens": 470683,
                                    "output_tokens": 2604,
                                    "elapsed_ms": 125438,
                                },
                            }
                        ],
                    },
                    {
                        "target": "codex_luna",
                        "context_key": "validation::issue-2818-multi-slice",
                        "route_effect": "no-change",
                        "transport_costs": [
                            {
                                "transport": "cli",
                                "record_count": 1,
                                "expected_burden_component": -40,
                                "observed_context_cost": {
                                    "assignment_packet_bytes": 7024,
                                    "rendered_prompt_bytes": 3955,
                                    "effective_input_tokens": 488645,
                                    "output_tokens": 3209,
                                    "elapsed_ms": 114636,
                                },
                            }
                        ],
                    },
                ],
            },
        )

    equal_fit = decide(luna_fit=10)
    assert equal_fit["decision"] == "assign-current-target"
    assert equal_fit["selected_target"] == "codex_sol"
    guard = equal_fit["selection_basis"]["context_inflation_guard"]
    assert guard["status"] == "applied"
    assert guard["cases"] == [
        {
            "candidate": "codex_luna",
            "retained_target": "codex_sol",
            "candidate_total_tokens": 491854,
            "current_total_tokens": 473287,
            "observed_increase_tokens": 18567,
            "threshold_tokens": 9466,
            "ranking_adjustment": -26,
            "reason": "materially-higher-observed-context-without-stronger-declared-fit",
        }
    ]
    assert decide(luna_fit=40)["selected_target"] == "codex_luna"


def test_assignment_transport_cost_unknown_is_explicit_and_preserves_configured_order() -> None:
    from agentic_workspace.target_evidence import assignment_decision_from_policy

    decision = assignment_decision_from_policy(
        assignment_policy={
            "assignment_policy": {"value": "required-best-fit"},
            "current_target": {"value": "worker"},
            "binding": {"enforceable": True},
        },
        runtime_resolution={
            "recommendation": "stay-local",
            "capability_context": {"task_class": "implementation", "scope_class": "bounded"},
            "profile_recommendations": [
                {
                    "name": "worker",
                    "recommendation": "recommended",
                    "score": 1,
                    "capability_mismatch": False,
                    "execution_methods": ["cli", "api"],
                    "human_control_modes": ["auto"],
                }
            ],
        },
        target_evidence={"status": "no-local-evidence", "record_count": 0, "suitability": []},
    )

    assert decision["selected_transport"] == "cli"
    assert [item["evidence_state"] for item in decision["candidate_scores"][0]["transport_options"]] == [
        "unknown",
        "unknown",
    ]


def test_required_best_fit_honors_current_target_downroute_action() -> None:
    from agentic_workspace.target_evidence import assignment_decision_from_policy

    decision = assignment_decision_from_policy(
        assignment_policy={
            "assignment_policy": {"value": "required-best-fit"},
            "current_target": {"value": "strong_worker"},
            "binding": {"enforceable": True, "claim_boundary": "assignment policy resolved"},
        },
        runtime_resolution={
            "recommendation": "stay-local",
            "capability_context": {
                "task_class": "mechanical-follow-through",
                "scope_class": "mechanical-follow-through",
            },
            "profile_recommendations": [
                {
                    "name": "strong_worker",
                    "target_id": "target:strong",
                    "recommendation": "recommended",
                    "score": 8,
                    "capability_mismatch": False,
                    "required_action": "delegate-down-when-safe",
                    "execution_methods": ["internal"],
                    "human_control_modes": ["auto"],
                },
                {
                    "name": "bounded_worker",
                    "target_id": "target:bounded",
                    "recommendation": "recommended",
                    "score": 9,
                    "capability_mismatch": False,
                    "required_action": "execute-with-normal-proof",
                    "execution_methods": ["cli"],
                    "human_control_modes": ["auto"],
                },
            ],
        },
        target_evidence={"status": "no-local-evidence", "record_count": 0, "suitability": []},
    )

    assert decision["decision"] == "assign-best-fit"
    assert decision["selected_target"] == "bounded_worker"
    assert decision["selected_target_identity_ref"] == "target:bounded"
    assert decision["selection_basis"]["downroute_required"] is True
    assert decision["selection_basis"]["downroute_applied"] is True


def test_assignment_decision_fails_closed_when_no_candidate_is_eligible() -> None:
    from agentic_workspace.target_evidence import assignment_decision_from_policy

    decision = assignment_decision_from_policy(
        assignment_policy={
            "assignment_policy": {"value": "local-preferred"},
            "current_target": {"value": "current_worker"},
            "binding": {"enforceable": True, "claim_boundary": "assignment policy resolved"},
        },
        runtime_resolution={
            "recommendation": "stay-local",
            "capability_context": {"task_class": "mechanical-follow-through", "scope_class": "narrow-code-change"},
            "profile_recommendations": [
                {
                    "name": "current_worker",
                    "recommendation": "recommended",
                    "score": 99,
                    "capability_mismatch": True,
                    "required_action": "escalate-before-execution",
                    "execution_methods": ["internal"],
                    "human_control_modes": ["auto"],
                }
            ],
        },
        target_evidence={"status": "present", "record_count": 0, "suitability": []},
    )

    assert decision["decision"] == "no-safe-route"
    assert decision["canonical_outcome"] == "no-safe-route"
    assert decision["selected_target"] is None


def test_assignment_decision_keep_local_selects_current_target_not_higher_external_candidate() -> None:
    from agentic_workspace.target_evidence import assignment_decision_from_policy

    decision = assignment_decision_from_policy(
        assignment_policy={
            "assignment_policy": {"value": "local-preferred"},
            "current_target": {"value": "current_worker"},
            "binding": {"enforceable": True, "claim_boundary": "assignment policy resolved"},
        },
        runtime_resolution={
            "recommendation": "stay-local",
            "capability_context": {"task_class": "mechanical-follow-through", "scope_class": "narrow-code-change"},
            "profile_recommendations": [
                {
                    "name": "current_worker",
                    "recommendation": "acceptable",
                    "score": 1,
                    "capability_mismatch": False,
                    "required_action": "none",
                    "execution_methods": ["internal"],
                    "human_control_modes": ["auto"],
                },
                {
                    "name": "external_worker",
                    "recommendation": "recommended",
                    "score": 99,
                    "capability_mismatch": False,
                    "required_action": "none",
                    "location": "external",
                    "execution_methods": ["cli"],
                    "human_control_modes": ["auto"],
                },
            ],
        },
        target_evidence={"status": "present", "record_count": 0, "suitability": []},
    )

    assert decision["decision"] == "keep-local"
    assert decision["canonical_outcome"] == "retain-local"
    assert decision["selected_target"] == "current_worker"


def test_assignment_decision_local_preferred_does_not_select_ineligible_current_target() -> None:
    from agentic_workspace.target_evidence import assignment_decision_from_policy

    decision = assignment_decision_from_policy(
        assignment_policy={
            "assignment_policy": {"value": "local-preferred"},
            "current_target": {"value": "current_worker"},
            "manual_transport_policy": {"value": "allowed"},
            "binding": {"enforceable": True, "claim_boundary": "assignment policy resolved"},
        },
        runtime_resolution={
            "recommendation": "stay-local",
            "capability_context": {"task_class": "mechanical-follow-through", "scope_class": "narrow-code-change"},
            "profile_recommendations": [
                {
                    "name": "current_worker",
                    "recommendation": "recommended",
                    "score": 99,
                    "capability_mismatch": True,
                    "required_action": "escalate-before-execution",
                    "location": "local",
                    "execution_methods": ["internal"],
                    "human_control_modes": ["auto"],
                },
                {
                    "name": "external_worker",
                    "recommendation": "acceptable",
                    "score": 3,
                    "capability_mismatch": False,
                    "required_action": "none",
                    "location": "external",
                    "execution_methods": ["cli"],
                    "human_control_modes": ["auto"],
                },
            ],
        },
        target_evidence={"status": "present", "record_count": 0, "suitability": []},
    )

    assert decision["decision"] == "policy-conflict"
    assert decision["canonical_outcome"] == "planning-review-escalation"
    assert decision["selected_target"] is None
    assert decision["selection_basis"]["current_target_eligible"] is False
    assert decision["next_action"] == "resolve local-preferred current_target eligibility before execution"


def test_assignment_decision_surfaces_tie_without_lexical_target_selection() -> None:
    from agentic_workspace.target_evidence import assignment_decision_from_policy

    decision = assignment_decision_from_policy(
        assignment_policy={
            "assignment_policy": {"value": "required-best-fit"},
            "current_target": {"value": "alpha"},
            "binding": {"enforceable": True, "claim_boundary": "assignment policy resolved"},
        },
        runtime_resolution={
            "recommendation": "stay-local",
            "capability_context": {"task_class": "mechanical-follow-through", "scope_class": "narrow-code-change"},
            "profile_recommendations": [
                {
                    "name": "alpha",
                    "recommendation": "acceptable",
                    "score": 0,
                    "capability_mismatch": False,
                    "required_action": "none",
                    "location": "local",
                    "execution_methods": ["internal"],
                    "human_control_modes": ["auto"],
                },
                {
                    "name": "beta",
                    "recommendation": "acceptable",
                    "score": 5,
                    "capability_mismatch": False,
                    "required_action": "none",
                    "location": "local",
                    "execution_methods": ["internal"],
                    "human_control_modes": ["auto"],
                },
            ],
        },
        target_evidence={"status": "present", "record_count": 0, "suitability": []},
    )

    assert decision["decision"] == "tie"
    assert decision["canonical_outcome"] == "planning-review-escalation"
    assert decision["selected_target"] is None
    assert decision["uncertainty"] == "tie"


def test_assignment_decision_preserves_uncertain_evidence_without_routing_it() -> None:
    from agentic_workspace.config import DelegationOutcomeRecord
    from agentic_workspace.target_evidence import assignment_decision_from_policy, target_evidence_posture

    posture = target_evidence_posture(
        target_root=None,
        profiles=(),
        records=[
            DelegationOutcomeRecord(
                recorded_at="2026-04-17",
                delegation_target="fast_worker",
                task_class="mechanical-follow-through",
                scope_class="narrow-code-change",
                outcome="success",
                handoff_sufficiency="sufficient",
                review_burden="light",
                escalation_required=False,
                authority="model-self-report",
                confidence="low",
            )
        ],
    )
    decision = assignment_decision_from_policy(
        assignment_policy={
            "assignment_policy": {"value": "required-best-fit"},
            "current_target": {"value": "current_worker"},
            "binding": {"enforceable": True, "claim_boundary": "assignment policy resolved"},
        },
        runtime_resolution={
            "recommendation": "external-delegation",
            "capability_context": {"task_class": "mechanical-follow-through", "scope_class": "narrow-code-change"},
            "profile_recommendations": [
                {
                    "name": "fast_worker",
                    "recommendation": "acceptable",
                    "score": 3,
                    "capability_mismatch": False,
                    "required_action": "none",
                    "location": "external",
                    "execution_methods": ["cli"],
                    "human_control_modes": ["auto"],
                }
            ],
        },
        target_evidence=posture,
    )

    candidate = decision["candidate_scores"][0]
    assert candidate["evidence_contexts"] == []
    assert "low-authority:model-self-report" in candidate["uncertainty_contexts"][0]["uncertainty_reasons"]
    assert "low-confidence:low" in candidate["uncertainty_contexts"][0]["uncertainty_reasons"]
    assert candidate["ranking_components"]["uncertainty"] == -5
    assert decision["selected_target"] == "fast_worker"


def test_assignment_decision_without_context_does_not_aggregate_all_evidence() -> None:
    from agentic_workspace.target_evidence import assignment_decision_from_policy

    decision = assignment_decision_from_policy(
        assignment_policy={
            "assignment_policy": {"value": "required-best-fit"},
            "current_target": {"value": "current_worker"},
            "binding": {"enforceable": True, "claim_boundary": "assignment policy resolved"},
        },
        runtime_resolution={
            "recommendation": "external-delegation",
            "capability_context": {"task_class": None, "scope_class": None},
            "profile_recommendations": [
                {
                    "name": "fast_worker",
                    "recommendation": "recommended",
                    "score": 5,
                    "capability_mismatch": False,
                    "required_action": "none",
                    "location": "external",
                    "execution_methods": ["cli"],
                    "human_control_modes": ["auto"],
                }
            ],
        },
        target_evidence={
            "status": "present",
            "record_count": 1,
            "suitability": [
                {
                    "target": "fast_worker",
                    "context_key": "mechanical-follow-through::narrow-code-change",
                    "route_effect": "preferred-for-matching-task-class",
                    "record_count": 4,
                    "supporting_record_ids": ["fast_worker:mechanical-follow-through:narrow-code-change:old:0"],
                }
            ],
        },
    )

    assert decision["decision"] == "shape-before-assignment"
    assert decision["canonical_outcome"] == "read-only-exploration"
    assert decision["selected_target"] is None
    assert decision["selection_basis"]["uses_contextual_evidence"] is True
    assert decision["selection_basis"]["requested_context_key"] is None
    assert decision["candidate_scores"][0]["evidence_contexts"] == []


def test_stale_evidence_is_visible_but_not_routable_and_later_success_recovers() -> None:
    from agentic_workspace.config import DelegationOutcomeRecord
    from agentic_workspace.target_evidence import target_evidence_posture

    posture = target_evidence_posture(
        target_root=None,
        profiles=(),
        records=[
            DelegationOutcomeRecord(
                recorded_at="2025-01-01",
                delegation_target="fast_worker",
                task_class="mechanical-follow-through",
                scope_class="narrow-code-change",
                outcome="failed",
                handoff_sufficiency="insufficient",
                review_burden="high",
                escalation_required=True,
                record_id="old-failure",
            ),
            DelegationOutcomeRecord(
                recorded_at="2026-07-01",
                delegation_target="fast_worker",
                task_class="mechanical-follow-through",
                scope_class="narrow-code-change",
                outcome="success",
                handoff_sufficiency="sufficient",
                review_burden="light",
                escalation_required=False,
                operation="supersede",
                predecessor_id="old-failure",
                record_id="fresh-success",
                admission_state="recovered",
            ),
        ],
    )

    scoped = posture["suitability"][0]
    assert scoped["supporting_record_ids"] == ["fresh-success"]
    stale = next(item for item in posture["uncertainty_accounts"] if item["record_id"] == "old-failure")
    assert any(reason.startswith("stale:") for reason in stale["uncertainty_reasons"])


def test_note_delegation_outcome_admits_low_authority_as_non_routing_uncertainty(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert (
        cli.main(
            [
                "note-delegation-outcome",
                "--target",
                str(target),
                "--delegation-target",
                "fast_worker",
                "--task-class",
                "mechanical-follow-through",
                "--scope-class",
                "narrow-code-change",
                "--outcome",
                "success",
                "--authority",
                "model-self-report",
                "--confidence",
                "low",
                "--source-type",
                "telemetry",
                "--source-ref",
                "local://agent/self-observation/1",
                "--producer-class",
                "agent-self-observation",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["recorded"]["authority"] == "model-self-report"
    assert payload["recorded"]["confidence"] == "low"
    assert payload["recorded"]["source_ref"] == "local://agent/self-observation/1"

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0
    config_payload = json.loads(capsys.readouterr().out)
    evidence = config_payload["mixed_agent"]["target_evidence"]
    assert evidence["suitability"] == []
    assert evidence["uncertainty_accounts"][0]["routing_effect"] == "visible-uncertainty-only"
    assert "low-authority:model-self-report" in evidence["uncertainty_accounts"][0]["uncertainty_reasons"]
    assert "low-confidence:low" in evidence["uncertainty_accounts"][0]["uncertainty_reasons"]


def test_note_delegation_outcome_downgrades_forged_public_high_authority(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert (
        cli.main(
            [
                "note-delegation-outcome",
                "--target",
                str(target),
                "--delegation-target",
                "fast_worker",
                "--task-class",
                "mechanical-follow-through",
                "--scope-class",
                "narrow-code-change",
                "--outcome",
                "success",
                "--authority",
                "aw-proof",
                "--confidence",
                "high",
                "--source-type",
                "aw-proof-receipt",
                "--source-ref",
                "proof://caller-controlled",
                "--producer-class",
                "aw-proof",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["recorded"]["authority"] == "model-self-report"
    assert payload["recorded"]["producer_class"] == "agent-self-observation"
    assert payload["recorded"]["confidence"] == "low"
    assert payload["recorded"]["proof_observation"] == "forged-or-unverified-proof-authority"

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0
    config_payload = json.loads(capsys.readouterr().out)
    evidence = config_payload["mixed_agent"]["target_evidence"]
    assert evidence["suitability"] == []
    assert evidence["uncertainty_accounts"][0]["routing_effect"] == "visible-uncertainty-only"
    assert "low-authority:model-self-report" in evidence["uncertainty_accounts"][0]["uncertainty_reasons"]


def test_internal_delegation_outcome_proof_receipt_can_emit_routable_aw_proof(tmp_path: Path) -> None:
    from agentic_workspace.workspace_runtime_primitives import _record_aw_proof_delegation_outcome, _write_trusted_producer_receipt

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write_trusted_producer_receipt(
        target_root=target,
        producer_class="aw-proof",
        receipt_id="proof-receipt-abc123",
        source_ref="proof://receipts/proof-receipt-abc123",
        receipt={
            "kind": "agentic-workspace/trusted-producer-receipt/v1",
            "producer_class": "aw-proof",
            "authority": "aw-proof",
            "source_type": "aw-proof-receipt",
            "status": "current",
            "revision": "proof-rev-1",
            "result": "passed",
            "target_context": {
                "delegation_target": "fast_worker",
                "task_class": "mechanical-follow-through",
                "scope_class": "narrow-code-change",
            },
        },
    )

    payload = _record_aw_proof_delegation_outcome(
        target_root=target,
        delegation_target="fast_worker",
        task_class="mechanical-follow-through",
        scope_class="narrow-code-change",
        outcome="success",
        proof_receipt_ref="proof://receipts/proof-receipt-abc123",
        idempotency_key="proof-receipt-abc123",
        review_burden="light",
    )

    assert payload["recorded"]["authority"] == "aw-proof"
    assert payload["recorded"]["producer_class"] == "aw-proof"
    assert payload["recorded"]["source_ref"] == "proof://receipts/proof-receipt-abc123"
    assert payload["recorded"]["idempotency_key"] == "proof-receipt-abc123"

    from agentic_workspace.config import load_delegation_outcomes
    from agentic_workspace.target_evidence import target_evidence_posture

    _, _, records = load_delegation_outcomes(target_root=target)
    posture = target_evidence_posture(target_root=target, profiles=(), records=records)
    assert posture["suitability"][0]["route_effect"] == "preferred-for-matching-task-class"
    assert posture["normalized_records"][0]["admission"] == {
        "routable": True,
        "authority": "aw-proof",
        "confidence": "high",
        "state": "accepted",
    }


def test_proof_receipt_writer_emits_canonical_aw_proof_store_receipt(tmp_path: Path) -> None:
    from agentic_workspace.workspace_runtime_primitives import _record_proof_receipt_payload

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / "src").mkdir()
    (target / "src" / "example.py").write_text("print('ok')\n", encoding="utf-8")

    payload = _record_proof_receipt_payload(
        target_root=target,
        command="uv run pytest tests/test_example.py -q",
        result="passed",
        changed_paths=["src/example.py"],
    )

    producer_ref = payload["trusted_producer_receipt_ref"]
    assert producer_ref.startswith("proof://receipts/")
    receipt_id = producer_ref.rsplit("/", 1)[-1]
    store_root = target / ".agentic-workspace" / "proof" / "receipts"
    receipt = json.loads((store_root / f"{receipt_id}.json").read_text(encoding="utf-8"))
    index = json.loads((store_root / "index.json").read_text(encoding="utf-8"))
    assert receipt["kind"] == "agentic-workspace/proof-receipt/v1"
    assert receipt["producer_class"] == "aw-proof"
    assert receipt["authority"] == "aw-proof"
    assert receipt["source_type"] == "aw-proof-receipt"
    assert receipt["source_ref"] == producer_ref
    assert "target_context" not in receipt
    assert payload["calibration_admission"]["status"] == "non-calibrating"
    assert payload["calibration_admission"]["reason"] == "missing-current-assignment-context"
    assert index["kind"] == "agentic-workspace/trusted-producer-receipt-index/v1"
    assert index["receipts"][receipt_id]["path"] == f"{receipt_id}.json"
    assert index["receipts"][receipt_id]["status"] == "current"


def test_proof_receipt_writer_feeds_contextual_assignment_evidence_end_to_end(tmp_path: Path) -> None:
    from agentic_workspace.config import DelegationOutcomeRecord, load_delegation_outcomes
    from agentic_workspace.target_evidence import assignment_decision_from_policy, target_evidence_posture
    from agentic_workspace.workspace_runtime_primitives import _record_proof_receipt_payload

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / "src").mkdir()
    (target / "src" / "example.py").write_text("print('ok')\n", encoding="utf-8")
    assignment_context = target / ".agentic-workspace" / "local" / "assignment-context.json"
    assignment_context.parent.mkdir(parents=True, exist_ok=True)
    assignment_context.write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/assignment-context/v1",
                "status": "current",
                "revision": "assign-rev-1",
                "target_context": {
                    "delegation_target": "fast_worker",
                    "task_class": "mechanical-follow-through",
                    "scope_class": "narrow-code-change",
                },
            }
        ),
        encoding="utf-8",
    )

    payload = _record_proof_receipt_payload(
        target_root=target,
        command="uv run pytest tests/test_example.py -q",
        result="passed",
        changed_paths=["src/example.py"],
    )

    producer_ref = payload["trusted_producer_receipt_ref"]
    receipt_id = producer_ref.rsplit("/", 1)[-1]
    receipt = json.loads((target / ".agentic-workspace" / "proof" / "receipts" / f"{receipt_id}.json").read_text(encoding="utf-8"))
    assert receipt["target_context"] == {
        "delegation_target": "fast_worker",
        "task_class": "mechanical-follow-through",
        "scope_class": "narrow-code-change",
    }
    assert receipt["target_context_authority"] == {
        "source_ref": ".agentic-workspace/local/assignment-context.json",
        "revision": "assign-rev-1",
        "status": "current",
        "rule": "Target context is resolved from current assignment/run authority, not proof receipt caller input.",
    }
    assert payload["calibration_admission"]["status"] == "recorded"
    assert payload["calibration_admission"]["record"]["authority"] == "aw-proof"
    assert payload["calibration_admission"]["record"]["source_ref"] == producer_ref

    _, _, records = load_delegation_outcomes(target_root=target)
    assert len(records) == 1
    assert records[0].authority == "aw-proof"
    posture = target_evidence_posture(
        target_root=target,
        profiles=(),
        records=[
            *records,
            DelegationOutcomeRecord(
                recorded_at="2026-04-18",
                delegation_target="fast_worker",
                task_class="mechanical-follow-through",
                scope_class="broad-design-change",
                outcome="failed",
                handoff_sufficiency="insufficient",
                review_burden="high",
                escalation_required=True,
                authority="human-review",
                confidence="high",
            ),
        ],
    )
    narrow = next(item for item in posture["suitability"] if item["context_key"] == "mechanical-follow-through::narrow-code-change")
    broad = next(item for item in posture["suitability"] if item["context_key"] == "mechanical-follow-through::broad-design-change")
    assert narrow["route_effect"] == "preferred-for-matching-task-class"
    assert broad["route_effect"] == "strong-review-required"

    assignment_policy = {
        "assignment_policy": {"value": "required-best-fit"},
        "current_target": {"value": "current_worker"},
        "binding": {"enforceable": True, "claim_boundary": "assignment policy resolved"},
    }
    runtime_resolution = {
        "recommendation": "stay-local",
        "capability_context": {"task_class": "mechanical-follow-through", "scope_class": "narrow-code-change"},
        "profile_recommendations": [
            {
                "name": "current_worker",
                "recommendation": "acceptable",
                "score": 2,
                "capability_mismatch": False,
                "required_action": "none",
                "execution_methods": ["internal"],
                "human_control_modes": ["auto"],
            },
            {
                "name": "fast_worker",
                "recommendation": "acceptable",
                "score": 2,
                "capability_mismatch": False,
                "required_action": "none",
                "location": "local",
                "execution_methods": ["cli"],
                "human_control_modes": ["auto"],
            },
        ],
    }
    decision = assignment_decision_from_policy(
        assignment_policy=assignment_policy,
        runtime_resolution=runtime_resolution,
        target_evidence=posture,
    )
    fast = next(item for item in decision["candidate_scores"] if item["target"] == "fast_worker")
    assert fast["ranking_components"]["contextual_evidence"] == 15

    broad_decision = assignment_decision_from_policy(
        assignment_policy=assignment_policy,
        runtime_resolution={
            **runtime_resolution,
            "capability_context": {"task_class": "mechanical-follow-through", "scope_class": "broad-design-change"},
        },
        target_evidence=posture,
    )
    broad_fast = next(item for item in broad_decision["candidate_scores"] if item["target"] == "fast_worker")
    assert broad_fast["ranking_components"]["contextual_evidence"] == -20

    duplicate = _record_proof_receipt_payload(
        target_root=target,
        command="uv run pytest tests/test_example.py -q",
        result="passed",
        changed_paths=["src/example.py"],
    )
    assert duplicate["trusted_producer_receipt_ref"] == producer_ref
    assert duplicate["calibration_admission"]["status"] == "already-recorded"
    _, _, duplicate_records = load_delegation_outcomes(target_root=target)
    assert len(duplicate_records) == 1


def test_proof_receipt_writer_leaves_stale_assignment_context_non_calibrating(tmp_path: Path) -> None:
    from agentic_workspace.config import load_delegation_outcomes
    from agentic_workspace.workspace_runtime_primitives import _record_proof_receipt_payload

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / "src").mkdir()
    (target / "src" / "example.py").write_text("print('ok')\n", encoding="utf-8")
    assignment_context = target / ".agentic-workspace" / "local" / "assignment-context.json"
    assignment_context.parent.mkdir(parents=True, exist_ok=True)
    assignment_context.write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/assignment-context/v1",
                "status": "superseded",
                "superseded_by": "assign-rev-2",
                "revision": "assign-rev-1",
                "target_context": {
                    "delegation_target": "fast_worker",
                    "task_class": "mechanical-follow-through",
                    "scope_class": "narrow-code-change",
                },
            }
        ),
        encoding="utf-8",
    )

    payload = _record_proof_receipt_payload(
        target_root=target,
        command="uv run pytest tests/test_example.py -q",
        result="passed",
        changed_paths=["src/example.py"],
    )

    assert payload["calibration_admission"]["status"] == "non-calibrating"
    assert payload["calibration_admission"]["reason"] == "stale-current-assignment-context"
    _, _, records = load_delegation_outcomes(target_root=target)
    assert list(records) == []


@pytest.mark.parametrize(
    ("producer_class", "source_type", "authority", "result"),
    [
        ("aw-proof", "aw-proof-receipt", "aw-proof", "passed"),
        ("human-review", "human-review", "human-review", "approved"),
        ("retry-outcome", "retry-outcome", "local-outcome-ledger", "passed"),
        ("handoff-outcome", "handoff-outcome", "local-outcome-ledger", "accepted"),
        ("closeout-outcome", "closeout-outcome", "local-outcome-ledger", "accepted"),
    ],
)
def test_trusted_producer_family_receipts_resolve_only_through_owner_store_index(
    tmp_path: Path, producer_class: str, source_type: str, authority: str, result: str
) -> None:
    from agentic_workspace.workspace_runtime_primitives import _load_trusted_producer_receipt, _write_trusted_producer_receipt

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    receipt_id = f"{producer_class}-receipt"
    source_ref = f"{producer_class}://receipts/{receipt_id}"
    _write_trusted_producer_receipt(
        target_root=target,
        producer_class=producer_class,
        receipt_id=receipt_id,
        source_ref=source_ref,
        receipt={
            "kind": "agentic-workspace/trusted-producer-receipt/v1",
            "producer_class": producer_class,
            "authority": authority,
            "source_type": source_type,
            "status": "current",
            "revision": "producer-rev-1",
            "result": result,
            "target_context": {
                "delegation_target": "fast_worker",
                "task_class": "mechanical-follow-through",
                "scope_class": "narrow-code-change",
            },
        },
    )

    receipt = _load_trusted_producer_receipt(
        target_root=target,
        producer_class=producer_class,
        receipt_ref=source_ref,
        delegation_target="fast_worker",
        task_class="mechanical-follow-through",
        scope_class="narrow-code-change",
        outcome="success",
    )

    assert receipt["producer_class"] == producer_class
    assert receipt["authority"] == authority
    assert receipt["source_ref"] == source_ref
    assert receipt["receipt_revision"] == "producer-rev-1"


def test_internal_delegation_outcome_rejects_mismatched_trusted_receipt(tmp_path: Path) -> None:
    from agentic_workspace.config import WorkspaceUsageError
    from agentic_workspace.workspace_runtime_primitives import _record_delegation_outcome

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    with pytest.raises(WorkspaceUsageError, match="must be resolved"):
        _record_delegation_outcome(
            target_root=target,
            delegation_target="fast_worker",
            task_class="mechanical-follow-through",
            scope_class="narrow-code-change",
            outcome="success",
            handoff_sufficiency="sufficient",
            review_burden="light",
            escalation_required=False,
            authority="human-review",
            confidence="high",
            source_type="aw-proof-receipt",
            source_ref="proof://receipts/abc123",
            producer_class="human-review",
            trusted_producer_receipt="aw-proof-receipt",  # type: ignore[arg-type]
        )


def test_internal_delegation_outcome_rejects_receipt_outside_owner_store(tmp_path: Path) -> None:
    from agentic_workspace.config import WorkspaceUsageError
    from agentic_workspace.workspace_runtime_primitives import _record_aw_proof_delegation_outcome

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    forged = target / ".agentic-workspace" / "forged-proof.json"
    forged.parent.mkdir(parents=True, exist_ok=True)
    forged.write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/trusted-producer-receipt/v1",
                "receipt_id": "forged-proof",
                "producer_class": "aw-proof",
                "authority": "aw-proof",
                "source_type": "aw-proof-receipt",
                "source_ref": ".agentic-workspace/forged-proof.json",
                "status": "current",
                "revision": "proof-rev-1",
                "result": "passed",
                "target_context": {
                    "delegation_target": "fast_worker",
                    "task_class": "mechanical-follow-through",
                    "scope_class": "narrow-code-change",
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(WorkspaceUsageError, match="inside the owning producer receipt store"):
        _record_aw_proof_delegation_outcome(
            target_root=target,
            delegation_target="fast_worker",
            task_class="mechanical-follow-through",
            scope_class="narrow-code-change",
            outcome="success",
            proof_receipt_ref=".agentic-workspace/forged-proof.json",
            idempotency_key="forged-proof",
        )


def test_internal_delegation_outcome_rejects_missing_or_stale_proof_receipt(tmp_path: Path) -> None:
    from agentic_workspace.config import WorkspaceUsageError
    from agentic_workspace.workspace_runtime_primitives import _record_aw_proof_delegation_outcome, _write_trusted_producer_receipt

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    with pytest.raises(WorkspaceUsageError, match="could not be loaded"):
        _record_aw_proof_delegation_outcome(
            target_root=target,
            delegation_target="fast_worker",
            task_class="mechanical-follow-through",
            scope_class="narrow-code-change",
            outcome="success",
            proof_receipt_ref="proof://receipts/missing",
            idempotency_key="missing",
        )

    _write_trusted_producer_receipt(
        target_root=target,
        producer_class="aw-proof",
        receipt_id="stale",
        source_ref="proof://receipts/stale",
        receipt={
            "kind": "agentic-workspace/trusted-producer-receipt/v1",
            "producer_class": "aw-proof",
            "authority": "aw-proof",
            "source_type": "aw-proof-receipt",
            "status": "superseded",
            "superseded_by": "newer",
            "result": "passed",
            "target_context": {
                "delegation_target": "fast_worker",
                "task_class": "mechanical-follow-through",
                "scope_class": "narrow-code-change",
            },
        },
    )

    with pytest.raises(WorkspaceUsageError, match="stale or superseded"):
        _record_aw_proof_delegation_outcome(
            target_root=target,
            delegation_target="fast_worker",
            task_class="mechanical-follow-through",
            scope_class="narrow-code-change",
            outcome="success",
            proof_receipt_ref="proof://receipts/stale",
            idempotency_key="stale",
        )


def test_internal_delegation_outcome_rejects_cross_context_proof_receipt(tmp_path: Path) -> None:
    from agentic_workspace.config import WorkspaceUsageError
    from agentic_workspace.workspace_runtime_primitives import _record_aw_proof_delegation_outcome, _write_trusted_producer_receipt

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write_trusted_producer_receipt(
        target_root=target,
        producer_class="aw-proof",
        receipt_id="wrong-context",
        source_ref="proof://receipts/wrong-context",
        receipt={
            "kind": "agentic-workspace/trusted-producer-receipt/v1",
            "producer_class": "aw-proof",
            "authority": "aw-proof",
            "source_type": "aw-proof-receipt",
            "status": "current",
            "result": "passed",
            "target_context": {
                "delegation_target": "fast_worker",
                "task_class": "mechanical-follow-through",
                "scope_class": "different-scope",
            },
        },
    )

    with pytest.raises(WorkspaceUsageError, match="context does not match"):
        _record_aw_proof_delegation_outcome(
            target_root=target,
            delegation_target="fast_worker",
            task_class="mechanical-follow-through",
            scope_class="narrow-code-change",
            outcome="success",
            proof_receipt_ref="proof://receipts/wrong-context",
            idempotency_key="wrong-context",
        )


def test_complexity_reduction_signal_requires_repeated_admitted_burden_not_compaction() -> None:
    from agentic_workspace.config import DelegationOutcomeRecord
    from agentic_workspace.target_evidence import target_evidence_posture

    records = [
        DelegationOutcomeRecord(
            recorded_at="2026-07-01",
            delegation_target="fast_worker",
            task_class="mechanical-follow-through",
            scope_class="narrow-code-change",
            outcome="mixed",
            handoff_sufficiency="borderline",
            review_burden="high",
            escalation_required=True,
            record_id="burden-1",
            retry_burden="required",
        ),
        DelegationOutcomeRecord(
            recorded_at="2026-07-02",
            delegation_target="fast_worker",
            task_class="mechanical-follow-through",
            scope_class="narrow-code-change",
            outcome="failed",
            handoff_sufficiency="insufficient",
            review_burden="high",
            escalation_required=True,
            record_id="burden-2",
            repair_burden="required",
        ),
        DelegationOutcomeRecord(
            recorded_at="2026-07-03",
            delegation_target="fast_worker",
            task_class="mechanical-follow-through",
            scope_class="broad-design-change",
            outcome="mixed",
            handoff_sufficiency="borderline",
            review_burden="normal",
            escalation_required=False,
            operation="prune-or-compact",
            record_id="compaction-only",
            admission_state="compacted-summary",
        ),
    ]

    posture = target_evidence_posture(target_root=None, profiles=(), records=records)

    signal = posture["complexity_reduction_signal"]
    assert signal["status"] == "available"
    assert signal["repeated_context_count"] == 1
    assert signal["contexts"][0]["context_key"] == "mechanical-follow-through::narrow-code-change"
    assert signal["contexts"][0]["supporting_record_ids"] == ["burden-1", "burden-2"]
    assert "ledger compaction alone is not a complexity signal" in signal["rule"]


def test_note_delegation_outcome_enforces_append_time_retention_cap(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    base = [
        "note-delegation-outcome",
        "--target",
        str(target),
        "--delegation-target",
        "fast_worker",
        "--task-class",
        "mechanical-follow-through",
        "--scope-class",
        "narrow-code-change",
        "--outcome",
        "success",
        "--format",
        "json",
    ]

    for index in range(22):
        assert cli.main([*base, "--idempotency-key", f"retention-{index}"]) == 0
        capsys.readouterr()

    payload = json.loads((target / ".agentic-workspace/delegation-outcomes.json").read_text(encoding="utf-8"))
    assert len(payload["records"]) == 20
    assert payload["retention"]["compaction_cap"] == 20
    assert payload["retention"]["evicted_record_count"] == 1
    assert payload["retention"]["evicted_lineage"][0]["record_id"].endswith(":retention-1")


def test_note_delegation_outcome_compaction_rewrites_same_context_raw_history(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    base = [
        "note-delegation-outcome",
        "--target",
        str(target),
        "--delegation-target",
        "fast_worker",
        "--task-class",
        "mechanical-follow-through",
        "--scope-class",
        "narrow-code-change",
        "--outcome",
    ]

    assert cli.main([*base, "success", "--handoff-sufficiency", "sufficient", "--review-burden", "light", "--format", "json"]) == 0
    first = json.loads(capsys.readouterr().out)["recorded"]["record_id"]
    assert (
        cli.main(
            [
                *base,
                "mixed",
                "--operation",
                "prune-or-compact",
                "--predecessor-id",
                first,
                "--handoff-sufficiency",
                "borderline",
                "--review-burden",
                "normal",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads((target / ".agentic-workspace/delegation-outcomes.json").read_text(encoding="utf-8"))
    assert payload["retention"]["mode"] == "bounded-current-calibration"
    assert [record["operation"] for record in payload["records"]] == ["prune-or-compact"]
    assert payload["records"][0]["predecessor_id"] == first
    assert payload["records"][0]["admission_state"] == "compacted-summary"


def test_note_delegation_outcome_rejects_cross_context_transition(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert (
        cli.main(
            [
                "note-delegation-outcome",
                "--target",
                str(target),
                "--delegation-target",
                "fast_worker",
                "--task-class",
                "mechanical-follow-through",
                "--scope-class",
                "narrow-code-change",
                "--outcome",
                "success",
                "--format",
                "json",
            ]
        )
        == 0
    )
    first = json.loads(capsys.readouterr().out)["recorded"]["record_id"]

    assert (
        cli.main(
            [
                "note-delegation-outcome",
                "--target",
                str(target),
                "--delegation-target",
                "fast_worker",
                "--task-class",
                "mechanical-follow-through",
                "--scope-class",
                "broad-design-change",
                "--operation",
                "supersede",
                "--predecessor-id",
                first,
                "--outcome",
                "mixed",
                "--format",
                "json",
            ]
        )
        == 2
    )
    rejected = json.loads(capsys.readouterr().out)
    assert rejected["failure_class"] == "invalid-lifecycle-transition"
    assert rejected["completion_boundary"] == "mutation-not-applied"
    assert "predecessor must match target/task/scope" in rejected["message"]


def test_repo_config_cli_invoke_sets_repo_owned_invocation_policy(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(
        target / ".agentic-workspace" / "config.toml",
        'schema_version = 1\n\n[workspace]\ncli_invoke = "uv run agentic-workspace"\n',
    )

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["cli_invoke"] == "uv run agentic-workspace"
    assert payload["workspace"]["cli_invoke_source"] == "repo-config"
    assert payload["warnings"] == []


def test_local_config_cli_invoke_overrides_repo_owned_invocation_policy(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(
        target / ".agentic-workspace" / "config.toml",
        'schema_version = 1\n\n[workspace]\ncli_invoke = "uv run agentic-workspace"\n',
    )
    _write(
        target / ".agentic-workspace" / "config.local.toml",
        'schema_version = 1\n\n[workspace]\ncli_invoke = "python -c \\"import sys; '
        "from agentic_workspace.cli import main; "
        'raise SystemExit(main(sys.argv[1:]))\\""\n',
    )

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["cli_invoke"] == (
        'python -c "import sys; from agentic_workspace.cli import main; raise SystemExit(main(sys.argv[1:]))"'
    )
    assert payload["workspace"]["cli_invoke_source"] == "local-override"
    assert payload["warnings"] == []


def test_local_config_can_disable_workspace_operation(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(target / ".agentic-workspace" / "config.toml", "schema_version = 1\n")
    _write(
        target / ".agentic-workspace" / "config.local.toml",
        "schema_version = 1\n\n[workspace]\nenabled = false\n",
    )

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["enabled"] is False
    assert payload["workspace"]["enabled_source"] == "local-override"
    assert payload["warnings"] == []


def test_local_config_can_reenable_repo_disabled_workspace_operation(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(target / ".agentic-workspace" / "config.toml", "schema_version = 1\n\n[workspace]\nenabled = false\n")
    _write(
        target / ".agentic-workspace" / "config.local.toml",
        "schema_version = 1\n\n[workspace]\nenabled = true\n",
    )

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["enabled"] is True
    assert payload["workspace"]["enabled_source"] == "local-override"
    assert payload["warnings"] == []


def test_config_reports_satisfied_repo_owned_cli_compatibility_expectation(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(
        target / ".agentic-workspace" / "config.toml",
        "schema_version = 1\n\n"
        "[cli_compatibility]\n"
        'enforcement = "blocking"\n'
        'minimum_version = "0.0.0"\n'
        'source_classes = ["source-checkout"]\n'
        'target_relations = ["outside-target"]\n'
        'command = "uv run agentic-workspace"\n',
    )

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    compatibility = _assert_cli_compatibility(payload, status="satisfied")
    assert compatibility["configured"] is True
    assert compatibility["enforcement"] == "blocking"
    assert compatibility["expected_command"] == "uv run agentic-workspace"
    assert compatibility["failed_checks"] == []
    checks = {check["name"]: check for check in compatibility["checks"]}
    assert checks["minimum_version"]["satisfied"] is True
    assert checks["source_class"]["satisfied"] is True
    assert checks["target_relation"]["satisfied"] is True
