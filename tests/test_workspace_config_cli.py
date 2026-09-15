from __future__ import annotations

# ruff: noqa: F403,F405
from tests.workspace_cli_support import *


@pytest.fixture
def owner_storage(monkeypatch):
    from dataclasses import replace

    from agentic_workspace import agent_guidance

    locations = {}
    load = agent_guidance.load_workspace_config

    def observed(*, target_root, **kwargs):
        config = load(target_root=target_root, **kwargs)
        return replace(
            config,
            local_override=replace(
                config.local_override,
                user_guidance_root=str(locations[target_root.resolve()]) if locations.get(target_root.resolve()) else None,
            ),
        )

    monkeypatch.setattr(agent_guidance, "load_workspace_config", observed)
    return locations


def test_assurance_semantic_route_is_applicability_only_and_does_not_replace_path_authority() -> None:
    route_requirement = {"id": "route", "applies_to_semantic_routes": ["github/issues/**"]}
    matched, reasons, facts = workspace_runtime_core._assurance_requirement_match(
        requirement=route_requirement,
        changed_paths=[],
        task_text="wording without issue terminology",
        planning_facts={},
        selected_semantic_routes=["github/issues/create"],
    )
    assert matched is True
    assert reasons == ["current semantic task route matched"]
    assert facts == []

    path_requirement = {"id": "path", "applies_to_paths": ["src/**"], "applies_to_semantic_routes": ["github/issues/**"]}
    path_matched, path_reasons, path_facts = workspace_runtime_core._assurance_requirement_match(
        requirement=path_requirement,
        changed_paths=["src/runtime.py"],
        task_text="",
        planning_facts={},
        selected_semantic_routes=[],
    )
    assert path_matched is True
    assert path_reasons == ["changed path matched src/**"]
    assert path_facts[0]["activation_kind"] == "source-behavior"


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


def test_repo_without_machine_local_delegation_policy_stays_quiet_and_canonical(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    _init_git_repo(tmp_path)
    _write(tmp_path / ".agentic-workspace/config.toml", (repo_root / ".agentic-workspace/config.toml").read_text(encoding="utf-8"))
    config = cli._load_workspace_config(target_root=tmp_path)
    mixed = workspace_runtime_core._mixed_agent_payload(config=config)

    assert mixed["effective_orchestration"]["status"] == "direct-local"
    assert mixed["effective_orchestration"]["current_target"] == {
        "identity": None,
        "status": "not-configured",
        "automatic_methods": [],
    }
    assert mixed["assignment_policy"]["status"] == "default-quiet"


def test_canonical_process_transport_requires_its_own_payload(tmp_path: Path) -> None:
    from agentic_workspace.config import WorkspaceUsageError

    target = tmp_path / "repo"
    target.mkdir()
    _write(
        target / ".agentic-workspace/config.local.toml",
        '\n[delegation_targets.worker]\ntransports = [{ kind = "process" }]\n',
    )
    with pytest.raises(WorkspaceUsageError, match="Invalid configuration"):
        cli._load_workspace_config(target_root=target)


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


def test_identity_init_preserves_explicit_noncurrent_target_profile_option(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    local_config = target / ".agentic-workspace/config.local.toml"
    local_config.parent.mkdir(parents=True)
    local_config.write_text(
        "\n".join(
            [
                "",
                "[delegation]",
                'current_target = "codex_sol"',
                "",
                "[delegation_targets.codex_sol]",
                'transports = [{kind="internal"}]',
                "",
                "[delegation_targets.codex_luna]",
                'transports = [{kind="manual"}]',
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
                "",
                "[delegation]",
                'current_target = "codex_sol"',
                "",
                "[delegation_targets.codex_sol]",
                'transports = [{kind="internal"}]',
                "",
            ]
        ),
        encoding="utf-8",
    )
    before = local_config.read_text(encoding="utf-8")

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()
    posture = workspace_runtime_core._mixed_agent_payload(config=cli._load_workspace_config(target_root=target))["target_identity"][
        "current_target_identity"
    ]
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
    capsys.readouterr()
    current = workspace_runtime_core._mixed_agent_payload(config=cli._load_workspace_config(target_root=target))["target_identity"][
        "current_target_identity"
    ]
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


def _write_guidance_lifecycle_fixture(target: Path, *, user_root: Path | None, owner_storage: dict) -> None:
    owner_storage[target.resolve()] = user_root
    (target / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "",
                "",
                "[delegation_targets.fast_worker]",
                'target_id = "user-local:fast-worker"',
                'target_revision = "rev-b"',
                'aliases = ["fast"]',
                'transports = [{kind="internal"}]',
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
                "",
                "[delegation]",
                'current_target = "user-local:fast-worker"',
                "",
                "[delegation_targets.fast_worker]",
                'target_id = "user-local:fast-worker"',
                'target_revision = "rev-b"',
                'aliases = ["fast"]',
                'transports = [{kind="internal"}]',
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
        '\n[delegation_targets.fast_worker]\ntarget_id = "user-local:fast-worker"\ntarget_revision = "rev-b"\ntransports = [{kind="internal"}]\n',
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
        '\n[delegation_targets.fast_worker]\ntarget_id = "user-local:fast-worker"\ntarget_revision = "rev-b"\ntransports = [{kind="internal"}]\n',
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
        '\n[delegation_targets.fast_worker]\ntarget_id = "user-local:fast-worker"\ntarget_revision = "rev-b"\ntransports = [{kind="internal"}]\n',
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
        '\n[delegation_targets.fast_worker]\ntarget_id = "user-local:fast-worker"\ntarget_revision = "rev-b"\ntransports = [{kind="internal"}]\n',
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
        '\n[delegation_targets.fast_worker]\ntarget_id = "user-local:fast-worker"\ntarget_revision = "rev-b"\ntransports = [{kind="internal"}]\n',
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


def test_guidance_lifecycle_supports_external_user_store_and_detects_user_to_overlay_conflict(tmp_path: Path, owner_storage) -> None:
    from agentic_workspace.agent_guidance import apply_guidance_promotion, guidance_promotion_from_store, transition_guidance

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    user_root = tmp_path / "user-guidance"
    _write_guidance_lifecycle_fixture(target, owner_storage=owner_storage, user_root=user_root)

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

    _write_guidance_lifecycle_fixture(target, owner_storage=owner_storage, user_root=None)
    conflict = apply_guidance_promotion(target_root=target, guidance_id=guidance_id)
    assert conflict["status"] == "promotion-owner-conflict"
    assert conflict["migration"]["status"] == "required"
    assert conflict["canonical_store_scan"]["active_stores"][0]["scope"] == "user-local-external"


def test_guidance_promotion_detects_overlay_to_user_store_conflict(tmp_path: Path, owner_storage) -> None:
    from agentic_workspace.agent_guidance import apply_guidance_promotion, guidance_promotion_from_store

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write_guidance_lifecycle_fixture(target, owner_storage=owner_storage, user_root=None)
    decision = guidance_promotion_from_store(target_root=target)
    guidance_id = decision["guidance"][0]["guidance_id"]
    promoted = apply_guidance_promotion(target_root=target, guidance_id=guidance_id)
    assert promoted["status"] == "promoted"
    assert promoted["store_location"]["scope"] == "repository-local"

    _write_guidance_lifecycle_fixture(target, owner_storage=owner_storage, user_root=tmp_path / "user-guidance")
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
        '\n[delegation_targets.fast_worker]\ntarget_id = "user-local:fast-worker"\ntarget_revision = "rev-b"\ntransports = [{kind="internal"}]\n',
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
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_boundary: str,
    owner_storage,
) -> None:
    import agentic_workspace.agent_guidance as guidance_runtime

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write_guidance_lifecycle_fixture(target, owner_storage=owner_storage, user_root=None)
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
    owner_storage,
) -> None:
    import shutil

    import agentic_workspace.agent_guidance as guidance_runtime

    user_root = tmp_path / "user-guidance"
    origin = tmp_path / "repo-a"
    successor = tmp_path / "repo-b"
    for target in (origin, successor):
        target.mkdir()
        _init_git_repo(target)
        _write_guidance_lifecycle_fixture(target, owner_storage=owner_storage, user_root=user_root)

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
    owner_storage,
) -> None:
    import shutil

    import agentic_workspace.agent_guidance as guidance_runtime

    user_root = tmp_path / "user-guidance"
    origin = tmp_path / "repo-a"
    successor = tmp_path / "repo-b"
    for target in (origin, successor):
        target.mkdir()
        _init_git_repo(target)
        _write_guidance_lifecycle_fixture(target, owner_storage=owner_storage, user_root=user_root)

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
    owner_storage,
) -> None:
    import agentic_workspace.agent_guidance as guidance_runtime
    from agentic_workspace.config import WorkspaceUsageError

    user_root = tmp_path / "user-guidance"
    origin = tmp_path / "repo-a"
    successor = tmp_path / "repo-b"
    for target in (origin, successor):
        target.mkdir()
        _init_git_repo(target)
        _write_guidance_lifecycle_fixture(target, owner_storage=owner_storage, user_root=user_root)
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
    owner_storage,
) -> None:
    import agentic_workspace.agent_guidance as guidance_runtime
    from agentic_workspace.config import WorkspaceUsageError

    user_root = tmp_path / "user-guidance"
    origin = tmp_path / "repo-a"
    successor = tmp_path / "repo-b"
    for target in (origin, successor):
        target.mkdir()
        _init_git_repo(target)
        _write_guidance_lifecycle_fixture(target, owner_storage=owner_storage, user_root=user_root)
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


def test_guidance_promotion_retry_repairs_stale_registry_and_missing_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, owner_storage
) -> None:
    import agentic_workspace.agent_guidance as guidance_runtime

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write_guidance_lifecycle_fixture(target, owner_storage=owner_storage, user_root=None)
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


def test_guidance_transaction_recovery_rejects_concurrent_registry_writer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, owner_storage
) -> None:
    import agentic_workspace.agent_guidance as guidance_runtime
    from agentic_workspace.config import WorkspaceUsageError

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write_guidance_lifecycle_fixture(target, owner_storage=owner_storage, user_root=None)
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


def test_guidance_transition_retry_completes_interrupted_custody_transaction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, owner_storage
) -> None:
    import agentic_workspace.agent_guidance as guidance_runtime

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write_guidance_lifecycle_fixture(target, owner_storage=owner_storage, user_root=None)
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


def test_target_evidence_suitability_is_context_isolated(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        '\n[delegation_targets.fast_worker]\ntransports = [{kind="manual"}]\n',
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

    capsys.readouterr()
    suitability = workspace_runtime_core._mixed_agent_payload(config=cli._load_workspace_config(target_root=target))["target_evidence"][
        "suitability"
    ]
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
    from dataclasses import replace

    from agentic_workspace.config import DelegationOutcomeRecord
    from agentic_workspace.target_evidence import target_evidence_posture

    records = [
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
    ]
    posture = target_evidence_posture(target_root=None, profiles=(), records=records)
    assert posture["suitability"] == []
    assert "target-quality-stronger-owner-required" in posture["uncertainty_accounts"][0]["uncertainty_reasons"]
    # Synthetic local-operator control exercises arithmetic only. The historical
    # provider observation above remains censored, not admitted target quality.
    control = replace(records[0], authority="local-outcome-ledger", producer_class="local-operator", confidence="medium")
    posture = target_evidence_posture(target_root=None, profiles=(), records=[control])

    costs = posture["suitability"][0]["transport_costs"]
    assert costs == [
        {
            "transport": "cli",
            "record_count": 1,
            "expected_burden_component": -30,
            "burden_metric_support": {
                "effective_input_tokens": {"record_count": 1, "average_penalty": -30},
                "output_tokens": {"record_count": 1, "average_penalty": 0},
                "elapsed_ms": {"record_count": 1, "average_penalty": 0},
                "orientation_command_count": {"record_count": 1, "average_penalty": 0},
                "retry_count": {"record_count": 1, "average_penalty": 0},
                "repair_loop_count": {"record_count": 1, "average_penalty": 0},
            },
            "burden_aggregation": "sum-of-observed-metric-means-not-a-measured-lifecycle-total",
            "observed_metric_counts": {
                "assignment_packet_bytes": 1,
                "cached_input_tokens": 1,
                "effective_input_tokens": 1,
                "elapsed_ms": 1,
                "output_tokens": 1,
                "rendered_prompt_bytes": 1,
            },
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
    assert "low-authority:model-self-report" in posture["uncertainty_accounts"][0]["uncertainty_reasons"]
    assert {"target-quality-stronger-owner-required", "low-confidence:low"} <= set(
        posture["uncertainty_accounts"][1]["uncertainty_reasons"]
    )


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
        "current_economics",
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


def test_assignment_cost_evidence_does_not_pool_different_continuity_configurations() -> None:
    from agentic_workspace.target_evidence import assignment_decision_from_policy

    contexts = ["sha256:" + "a" * 64, "sha256:" + "b" * 64]
    configurations = [
        {
            "eligible": True,
            "configuration": {"id": mode, "target": "worker", "transport": "process", "execution": {"comparison_context": context}},
        }
        for mode, context in zip(("fresh", "resume"), contexts, strict=True)
    ]
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
                    "score": 8,
                    "capability_mismatch": False,
                    "execution_methods": ["process"],
                    "human_control_modes": ["auto"],
                    "execution_configurations": configurations,
                }
            ],
        },
        target_evidence={
            "status": "present",
            "record_count": 2,
            "suitability": [
                {
                    "target": "worker",
                    "context_key": "implementation::bounded",
                    "route_effect": "no-change",
                    "transport_costs": [
                        {"transport": "process", "configuration_context": contexts[0], "record_count": 1, "expected_burden_component": -12},
                        {"transport": "process", "record_count": 1, "expected_burden_component": -99},
                    ],
                }
            ],
        },
    )
    options = decision["candidate_scores"][0]["transport_options"]
    assert [(option["expected_burden"], option["record_count"]) for option in options] == [(-12, 1), (None, 0)]
    assert decision["selected_execution_configuration"]["id"] == "fresh"


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


def test_assignment_uses_only_current_available_marginal_cost_evidence() -> None:
    from agentic_workspace.target_evidence import assignment_decision_from_policy

    def decide(
        *,
        status: str = "available",
        expires_at: str = "2099-01-01T00:00:00Z",
        mismatch: bool = False,
        repair_penalty: bool = False,
    ) -> dict[str, object]:
        profiles = []
        for name, marginal_cost in (("paid", "equivalent"), ("spark", "near-zero")):
            profiles.append(
                {
                    "name": name,
                    "recommendation": "recommended",
                    "score": 10,
                    "cost_class": "cheap",
                    "latency_class": "fast",
                    "capability_mismatch": mismatch and name == "spark",
                    "required_action": "escalate-before-execution" if mismatch and name == "spark" else "none",
                    "execution_methods": ["internal"],
                    "human_control_modes": ["auto"],
                    "current_economic_evidence": {
                        "status": status if name == "spark" else "available",
                        "marginal_cost": marginal_cost,
                        "resource_domain": f"pool:{name}",
                        "source": "runtime-adapter",
                        "observed_at": "2026-01-01T00:00:00Z",
                        "expires_at": expires_at if name == "spark" else "2099-01-01T00:00:00Z",
                    },
                }
            )
        return assignment_decision_from_policy(
            assignment_policy={
                "assignment_policy": {"value": "required-best-fit"},
                "current_target": {"value": "paid"},
                "binding": {"enforceable": True},
            },
            runtime_resolution={
                "recommendation": "stay-local",
                "capability_context": {"task_class": "implementation", "scope_class": "bounded"},
                "profile_recommendations": profiles,
            },
            target_evidence={
                "status": "present" if repair_penalty else "absent",
                "record_count": 1 if repair_penalty else 0,
                "suitability": [
                    {
                        "target": "spark",
                        "context_key": "implementation::bounded",
                        "route_effect": "strong-review-required",
                    }
                ]
                if repair_penalty
                else [],
            },
        )

    current = decide()
    assert current["selected_target"] == "spark"
    spark = next(item for item in current["candidate_scores"] if item["target"] == "spark")
    assert spark["ranking_components"]["current_economics"] == 8
    assert spark["current_economic_evidence"]["usable"] is True
    assert spark["ranking_reasons"] == ["current-economic-evidence:near-zero"]

    for decision in (
        decide(status="exhausted"),
        decide(status="unknown"),
        decide(expires_at="2026-02-01T00:00:00Z"),
    ):
        assert decision["selected_target"] == "paid"
        spark = next(item for item in decision["candidate_scores"] if item["target"] == "spark")
        assert spark["ranking_components"]["current_economics"] == 0
        assert spark["current_economic_evidence"]["usable"] is False

    rejected = decide(mismatch=True)
    assert rejected["selected_target"] == "paid"
    spark = next(item for item in rejected["candidate_scores"] if item["target"] == "spark")
    assert spark["eligible"] is False

    repair_heavy = decide(repair_penalty=True)
    assert repair_heavy["selected_target"] == "paid"


def test_assignment_equivalent_current_economics_preserves_an_explicit_tie() -> None:
    from agentic_workspace.target_evidence import assignment_decision_from_policy

    evidence = {
        "status": "available",
        "marginal_cost": "equivalent",
        "resource_domain": "shared-pool",
        "source": "runtime-adapter",
        "observed_at": "2026-01-01T00:00:00Z",
        "expires_at": "2099-01-01T00:00:00Z",
    }
    decision = assignment_decision_from_policy(
        assignment_policy={"assignment_policy": {"value": "required-best-fit"}, "binding": {"enforceable": True}},
        runtime_resolution={
            "recommendation": "stay-local",
            "capability_context": {"task_class": "implementation", "scope_class": "bounded"},
            "profile_recommendations": [
                {
                    "name": name,
                    "recommendation": "recommended",
                    "score": 10,
                    "cost_class": "cheap",
                    "latency_class": "fast",
                    "capability_mismatch": False,
                    "execution_methods": ["internal"],
                    "human_control_modes": ["auto"],
                    "current_economic_evidence": evidence,
                }
                for name in ("one", "two")
            ],
        },
        target_evidence={"status": "absent", "record_count": 0, "suitability": []},
    )

    assert decision["decision"] == "tie"
    assert decision["selected_target"] is None


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
    assert all(item["expected_burden"] is None for item in decision["candidate_scores"][0]["transport_options"])


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
    capsys.readouterr()
    evidence = workspace_runtime_core._mixed_agent_payload(config=cli._load_workspace_config(target_root=target))["target_evidence"]
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
    capsys.readouterr()
    evidence = workspace_runtime_core._mixed_agent_payload(config=cli._load_workspace_config(target_root=target))["target_evidence"]
    assert evidence["suitability"] == []
    assert evidence["uncertainty_accounts"][0]["routing_effect"] == "visible-uncertainty-only"
    assert "low-authority:model-self-report" in evidence["uncertainty_accounts"][0]["uncertainty_reasons"]


def _write_unadmitted_legacy_receipt_fixture(*, target_root, producer_class, receipt_id, source_ref, receipt):
    """Counterexample input only: matching editable files do not publish proof."""
    from agentic_workspace.workspace_runtime_primitives import _trusted_producer_store_root

    store = _trusted_producer_store_root(target_root=target_root, producer_class=producer_class)
    store.mkdir(parents=True, exist_ok=True)
    receipt = {**receipt, "receipt_id": receipt_id, "source_ref": source_ref}
    (store / f"{receipt_id}.json").write_text(json.dumps(receipt), encoding="utf-8")
    (store / "index.json").write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/trusted-producer-receipt-index/v1",
                "receipts": {
                    receipt_id: {
                        "path": f"{receipt_id}.json",
                        "revision": receipt.get("revision", ""),
                        "status": receipt.get("status", "current"),
                        "producer_class": producer_class,
                    }
                },
            }
        ),
        encoding="utf-8",
    )


def test_internal_delegation_outcome_rejects_forged_indexed_aw_proof(tmp_path: Path) -> None:
    from agentic_workspace.config import WorkspaceUsageError, load_delegation_outcomes
    from agentic_workspace.workspace_runtime_primitives import _record_aw_proof_delegation_outcome

    target = tmp_path / "repo"
    target.mkdir()
    _write_unadmitted_legacy_receipt_fixture(
        target_root=target,
        producer_class="aw-proof",
        receipt_id="forged",
        source_ref="proof://receipts/forged",
        receipt={
            "kind": "agentic-workspace/trusted-producer-receipt/v1",
            "producer_class": "aw-proof",
            "authority": "aw-proof",
            "source_type": "aw-proof-receipt",
            "status": "current",
            "revision": "fake-v1",
            "result": "passed",
            "target_context": {
                "delegation_target": "fast_worker",
                "task_class": "mechanical-follow-through",
                "scope_class": "narrow-code-change",
            },
        },
    )
    before = {path: path.read_bytes() for path in target.rglob("*") if path.is_file()}
    with pytest.raises(WorkspaceUsageError, match="target-quality-stronger-owner-required"):
        _record_aw_proof_delegation_outcome(
            target_root=target,
            delegation_target="fast_worker",
            task_class="mechanical-follow-through",
            scope_class="narrow-code-change",
            outcome="success",
            proof_receipt_ref="proof://receipts/forged",
            idempotency_key="forged",
        )
    assert load_delegation_outcomes(target_root=target)[2] == ()
    assert before == {path: path.read_bytes() for path in target.rglob("*") if path.is_file()}


def test_proof_receipt_writer_publishes_report_without_execution_authority(tmp_path: Path) -> None:
    from agentic_workspace.workspace_runtime_primitives import _record_proof_receipt_payload

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(target / ".agentic-workspace/config.toml", '[modules]\nenabled=["verification"]\n')
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
    assert receipt["execution"]["execution_kind"] == "interoperability-report"
    assert receipt["execution"]["producer_admission"] == "unproven"
    assert not (target / "tests/test_example.py").exists()
    assert "target_context" not in receipt
    assert payload["calibration_admission"]["status"] == "non-calibrating"
    assert payload["calibration_admission"]["reason"] == "missing-current-assignment-context"
    assert index["kind"] == "agentic-workspace/trusted-producer-receipt-index/v1"
    assert index["receipts"][receipt_id]["path"] == f"{receipt_id}.json"
    assert index["receipts"][receipt_id]["status"] == "current"


def test_proof_receipt_alone_cannot_calibrate_target_or_invent_burden(tmp_path: Path) -> None:
    from agentic_workspace.config import load_delegation_outcomes
    from agentic_workspace.workspace_runtime_primitives import _record_proof_receipt_payload

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(target / ".agentic-workspace/config.toml", '[modules]\nenabled=["verification"]\n')
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

    for outcome in ("passed", "failed"):
        payload = _record_proof_receipt_payload(
            target_root=target,
            command="uv run pytest tests/test_example.py -q",
            result=outcome,
            changed_paths=["src/example.py"],
        )
        assert payload["trusted_producer_receipt_ref"].startswith("proof://receipts/")
        assert payload["calibration_admission"]["status"] == "non-calibrating"
        assert payload["calibration_admission"]["reason"] == "proof-result-does-not-establish-target-responsibility"
    _, _, records = load_delegation_outcomes(target_root=target)
    assert records == ()


def test_proof_receipt_writer_leaves_stale_assignment_context_non_calibrating(tmp_path: Path) -> None:
    from agentic_workspace.config import load_delegation_outcomes
    from agentic_workspace.workspace_runtime_primitives import _record_proof_receipt_payload

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(target / ".agentic-workspace/config.toml", '[modules]\nenabled=["verification"]\n')
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
def test_trusted_producer_family_index_shape_cannot_grant_quality_authority(
    tmp_path: Path, producer_class: str, source_type: str, authority: str, result: str
) -> None:
    from agentic_workspace.config import WorkspaceUsageError
    from agentic_workspace.workspace_runtime_primitives import _load_trusted_producer_receipt

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    receipt_id = f"{producer_class}-receipt"
    source_ref = f"{producer_class}://receipts/{receipt_id}"
    _write_unadmitted_legacy_receipt_fixture(
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

    with pytest.raises(WorkspaceUsageError, match="target-quality-stronger-owner-required"):
        _load_trusted_producer_receipt(
            target_root=target,
            producer_class=producer_class,
            receipt_ref=source_ref,
            delegation_target="fast_worker",
            task_class="mechanical-follow-through",
            scope_class="narrow-code-change",
            outcome="success",
        )


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
    from agentic_workspace.workspace_runtime_primitives import _record_aw_proof_delegation_outcome

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

    _write_unadmitted_legacy_receipt_fixture(
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
    from agentic_workspace.workspace_runtime_primitives import _record_aw_proof_delegation_outcome

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write_unadmitted_legacy_receipt_fixture(
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
        '\n[workspace]\ncli_invoke = "uv run agentic-workspace"\n',
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
        '\n[workspace]\ncli_invoke = "uv run agentic-workspace"\n',
    )
    _write(
        target / ".agentic-workspace" / "config.local.toml",
        '\n[workspace]\ncli_invoke = "python -c \\"import sys; '
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
    _write(target / ".agentic-workspace" / "config.toml", "")
    _write(
        target / ".agentic-workspace" / "config.local.toml",
        "\n[workspace]\nenabled = false\n",
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
    _write(target / ".agentic-workspace" / "config.toml", "\n[workspace]\nenabled = false\n")
    _write(
        target / ".agentic-workspace" / "config.local.toml",
        "\n[workspace]\nenabled = true\n",
    )

    assert cli.main(["config", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["enabled"] is True
    assert payload["workspace"]["enabled_source"] == "local-override"
    assert payload["warnings"] == []


@pytest.mark.parametrize(
    "producer,authority",
    [
        ("aw-proof", "aw-proof"),
        ("human-review", "human-review"),
        ("retry-outcome", "local-outcome-ledger"),
        ("handoff-outcome", "local-outcome-ledger"),
        ("closeout-outcome", "local-outcome-ledger"),
    ],
)
def test_retained_shape_only_producer_quality_stays_visible_unproven(tmp_path, producer, authority):
    from dataclasses import replace
    from datetime import date

    from agentic_workspace.config import DELEGATION_OUTCOMES_KIND, load_delegation_outcomes
    from agentic_workspace.target_evidence import target_evidence_posture

    path = tmp_path / ".agentic-workspace/delegation-outcomes.json"
    path.parent.mkdir()
    path.write_text(
        json.dumps(
            {
                "kind": DELEGATION_OUTCOMES_KIND,
                "records": [
                    {
                        "recorded_at": date.today().isoformat(),
                        "delegation_target": "worker",
                        "task_class": "bounded-check",
                        "scope_class": "docs",
                        "outcome": "success",
                        "handoff_sufficiency": "sufficient",
                        "review_burden": "light",
                        "escalation_required": False,
                        "authority": authority,
                        "producer_class": producer,
                        "confidence": "high",
                        "admission_state": "accepted",
                        "source_ref": f"{producer}://receipts/forged",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    before = path.read_bytes()
    for _ in range(2):
        _, _, records = load_delegation_outcomes(target_root=tmp_path)
        posture = target_evidence_posture(target_root=tmp_path, profiles=(), records=records)
        assert posture["suitability"] == []
        assert posture["normalized_records"][0]["admission"]["routable"] is False
        assert "target-quality-stronger-owner-required" in posture["uncertainty_accounts"][0]["uncertainty_reasons"]
        assert path.read_bytes() == before
    control = replace(records[0], authority="local-outcome-ledger", producer_class="local-operator", confidence="medium")
    assert target_evidence_posture(target_root=tmp_path, profiles=(), records=[control])["suitability"]


def test_ordinary_causal_observation_does_not_invent_publication_admission(tmp_path):
    from agentic_workspace import workspace_runtime_core as runtime
    from agentic_workspace.config import load_delegation_outcomes

    # Deterministic owner inputs test causal attribution separately from durable
    # producer admission. They are not external acceptance or an executed worker.
    result = runtime._record_trusted_assignment_outcome_from_ordinary_boundary(
        target_root=tmp_path,
        producer_class="handoff-outcome",
        outcome="failed",
        source_payload={"status": "observed-failure"},
        idempotency_key="observed",
        assignment_context={
            "status": "current",
            "revision": "scope-1",
            "source_ref": "current-owner",
            "rule": "fixture owner observations",
            "target_context": {
                "assignment_id": "assignment-1",
                "assignment_revision": "attempt-1",
                "run_id": "run-1",
                "delegation_target": "worker",
                "task_class": "bounded-check",
                "scope_class": "docs",
                "slice_id": "slice-1",
                "semantic_revision": "scope-1",
            },
        },
        responsibility_evidence={
            "target_executed": True,
            "context_sufficient": True,
            "transport_sufficient": True,
            "failure_stage": "target-execution",
        },
    )
    assert result["status"] == "preserved-unproven"
    assert result["recorded_target_evidence"] is False
    assert result["attribution"]["routing_effect"]["target_evidence_allowed"] is True
    assert result["reason"] == "target-quality-stronger-owner-required"
    assert load_delegation_outcomes(target_root=tmp_path)[2] == ()
    source = tmp_path / ".agentic-workspace/local/handoff-receipts/observed.json"
    assert json.loads(source.read_text(encoding="utf-8"))["source_payload"] == {"status": "observed-failure"}


def test_current_native_execution_proof_does_not_supply_target_responsibility(tmp_path, shared_core_binary):
    from tests.test_native_proof_producer import fixture

    from agentic_workspace.config import WorkspaceUsageError, load_delegation_outcomes
    from agentic_workspace.decision import invoke, start
    from agentic_workspace.workspace_runtime_primitives import _record_aw_proof_delegation_outcome

    context = {**fixture(tmp_path), "projection": "full"}
    request = start(context)["verification"]["execution_requests"][0]
    action = start({**context, "request": request})["decision_packet"]["primary_action"]
    result = invoke({**context, "invocation": action})
    assert result["value"]["process"]["status"] == "passed"
    assert result["value"]["publication"]["status"] == "published"
    reference = result["value"]["publication"]["reference"]
    claim = start(context)["verification"]["requests"][0]
    claim["arguments"]["evidence_refs"] = [reference]
    evidence = start({**context, "request": claim})["verification"]["evidence"][0]
    assert evidence["publication_admission"]["status"] == "admitted"
    assert evidence["evidence_freshness"] == "reusable"
    with pytest.raises(WorkspaceUsageError, match="source type is not accepted"):
        _record_aw_proof_delegation_outcome(
            target_root=tmp_path,
            delegation_target="unrelated-worker",
            task_class="bounded-check",
            scope_class="docs",
            outcome="success",
            proof_receipt_ref=reference,
            idempotency_key="unrelated",
        )
    assert load_delegation_outcomes(target_root=tmp_path)[2] == ()
    assert invoke({**context, "invocation": action})["value"] == result["value"]
    assert (tmp_path / "count.txt").read_text().splitlines() == ["executed"]


def test_current_configuration_reader_and_report_share_the_closed_grammar(tmp_path):
    from agentic_workspace.config import load_workspace_config

    _write(
        tmp_path / ".agentic-workspace/config.toml", '[workspace]\nimprovement_latitude="proactive"\n[modules]\nenabled=["verification"]\n'
    )
    _write(
        tmp_path / ".agentic-workspace/config.local.toml",
        '[session_logging]\npath_mode="redacted"\n[delegation_targets.local]\ntransports=[{kind="internal"}]\n',
    )
    config = load_workspace_config(target_root=tmp_path)
    report = workspace_runtime_core._config_payload(config=config)
    assert report["workspace"]["improvement_latitude"] == "proactive"
    assert report["local"]["session_logging"] == {"enabled": None, "path_mode": "redacted"}
    assert report["local"]["delegation_targets"]["local"]["transports"][0]["kind"] == "internal"
    assert "schema_version" not in report
    assert "cli_compatibility" not in report
    assert not (tmp_path / ".agentic-workspace/local").exists()
