from __future__ import annotations

import hashlib
import json
import os
import subprocess
from collections.abc import Mapping
from fnmatch import fnmatch
from pathlib import Path, PurePosixPath
from typing import Any

from .durability import atomic_create_json, atomic_write_json
from .generated_semantics import operation_contract, semantic_digest
from .modules import Module
from .operations import Operation

POLICY = ".agentic-workspace/local/delegation.json"
EVIDENCE = ".agentic-workspace/local/target-evidence.json"
ATTEMPTS = ".agentic-workspace/local/delegation-attempts.json"
PLANNING = ".agentic-workspace/planning.json"
_replace_artifact = os.replace


def _json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def _write_local(path: Path, value: dict[str, Any], *, kind: str) -> None:
    value = {"kind": kind, "schema_version": 1, **value}
    if path.exists():
        current = _json(path)
        if current.get("kind") != kind or current.get("schema_version") != 1:
            raise FileExistsError(f"refusing to overwrite unknown local state: {path}")
        atomic_write_json(path, value)
    else:
        atomic_create_json(path, value)


def _subject(root: Path, context: Mapping[str, Any]) -> dict[str, Any]:
    planning = _json(root / PLANNING)
    item = planning.get("subject")
    if isinstance(item, dict):
        return {
            "id": item.get("id"),
            "outcome": item.get("outcome", ""),
            "scope": list(item.get("scope", [])),
            "constraints": list(item.get("constraints", [])),
            "stops": list(item.get("stops", [])),
            "proof_claims": list(item.get("proof_claims", [])),
            "semantic_revision": item.get("semantic_revision"),
            "context_class": str(context.get("context_class") or "general"),
        }
    task = str(context.get("task") or "")
    return {
        "id": "direct",
        "outcome": task,
        "scope": list(context.get("changed_paths", [])),
        "constraints": [],
        "stops": [],
        "proof_claims": list(context.get("claims", [])),
        "semantic_revision": semantic_digest({"task": task, "paths": context.get("changed_paths", [])}),
        "context_class": str(context.get("context_class") or "general"),
    }


def _applies(policy: dict[str, Any], context: Mapping[str, Any]) -> bool:
    applies = policy.get("applies", {})
    if not isinstance(applies, dict):
        return False
    task = str(context.get("task") or "").lower()
    paths = [str(item) for item in context.get("changed_paths", [])]
    terms = [str(item).lower() for item in applies.get("task_terms", [])]
    patterns = [str(item) for item in applies.get("paths", [])]
    return bool(task) and (
        not terms
        and not patterns
        or any(t in task for t in terms)
        or any(fnmatch(p, x) for p in paths for x in patterns)
    )


def _score(target: dict[str, Any], evidence: list[dict[str, Any]], subject: dict[str, Any]) -> tuple[int, list[str]]:
    cost = int(target.get("cost", 100))
    reasons = [f"declared-cost:{cost}"]
    task = str(subject.get("outcome") or "").lower()
    for record in evidence:
        if record.get("target_id") != target.get("id"):
            continue
        terms = [str(item).lower() for item in record.get("task_terms", [])]
        if terms and not any(term in task for term in terms):
            continue
        if (
            record.get("authority") not in {"maintainer", "repository", "verification"}
            or record.get("currentness") != "current"
            or record.get("disputed") is True
            or not isinstance(record.get("confidence"), int)
            or isinstance(record.get("confidence"), bool)
            or int(record["confidence"]) < 50
            or record.get("context_class") != subject.get("context_class")
        ):
            continue
        burden = sum(
            int(record.get(field, 0)) for field in ("repair_cost", "review_cost", "context_cost", "retry_cost")
        )
        if record.get("outcome") == "success":
            burden -= int(record.get("success_credit", 1))
        cost += burden
        reasons.append(f"evidence:{record.get('id', 'record')}:{burden:+d}")
    return cost, reasons


def _model(root: Path, context: Mapping[str, Any]) -> dict[str, Any] | None:
    policy = _json(root / POLICY)
    if not policy or not _applies(policy, context):
        return None
    subject = _subject(root, context)
    required = set(str(item) for item in policy.get("required_capabilities", []))
    evidence_state = _json(root / EVIDENCE)
    evidence = evidence_state.get("records", []) if isinstance(evidence_state.get("records", []), list) else []
    candidates = []
    for raw in policy.get("targets", []):
        if not isinstance(raw, dict) or not raw.get("id"):
            continue
        capabilities = set(str(item) for item in raw.get("capabilities", []))
        transport = raw.get("transport", {})
        reasons: list[str] = []
        if raw.get("available") is not True:
            reasons.append("unavailable")
        if not required <= capabilities:
            reasons.append("missing-capability")
        proof_claims = set(str(item) for item in subject.get("proof_claims", []))
        if proof_claims and not proof_claims <= set(str(item) for item in raw.get("proof_claims", [])):
            reasons.append("proof-incompatible")
        constraints = set(str(item) for item in subject.get("constraints", []))
        if constraints and not constraints <= set(str(item) for item in raw.get("constraints", [])):
            reasons.append("constraint-incompatible")
        scope = [str(item) for item in subject.get("scope", [])]
        allowed_scope = [str(item) for item in raw.get("allowed_scope", [])]
        if scope and (
            not allowed_scope or any(not any(fnmatch(path, pattern) for pattern in allowed_scope) for path in scope)
        ):
            reasons.append("scope-incompatible")
        if subject.get("stops") and raw.get("honors_stops") is not True:
            reasons.append("stop-incompatible")
        required_trust = policy.get("required_trust")
        if required_trust and raw.get("trust") != required_trust:
            reasons.append("trust-incompatible")
        if policy.get("human_required") is True and raw.get("human_authority") is not True:
            reasons.append("human-authority-required")
        score, ranking = _score(raw, [item for item in evidence if isinstance(item, dict)], subject)
        constructible = isinstance(transport, dict) and (
            raw.get("id") == policy.get("current_target")
            or transport.get("kind") in {"host-native", "process", "external"}
            and transport.get("ready") is True
        )
        if raw.get("id") != policy.get("current_target") and not constructible:
            reasons.append("transport-not-constructible")
        eligible = not reasons
        candidates.append(
            {
                "id": str(raw["id"]),
                "eligible": eligible,
                "exclusions": reasons,
                "score": score,
                "ranking": ranking,
                "transport": transport,
            }
        )
    eligible = sorted((item for item in candidates if item["eligible"]), key=lambda item: (item["score"], item["id"]))
    revision = semantic_digest({"policy": policy, "subject": subject, "evidence": evidence})
    return {"policy": policy, "subject": subject, "candidates": candidates, "eligible": eligible, "revision": revision}


def _contribute(context: Mapping[str, Any]) -> dict[str, Any] | None:
    root = Path(str(context["target"])).resolve()
    model = _model(root, context)
    if model is None:
        return None
    policy, subject, eligible, revision = model["policy"], model["subject"], model["eligible"], model["revision"]
    requested = context.get("assignment")
    if isinstance(requested, dict) and requested.get("operation") == "record-evidence":
        return {
            "revision": revision,
            "actions": [
                {
                    "operation_id": "assignment.record-evidence",
                    "arguments": {"target": str(root), "record": dict(requested.get("record", {}))},
                    "effects": ["target-evidence"],
                    "priority": 80,
                }
            ],
        }
    returns = context.get("delegation_return")
    if isinstance(returns, dict):
        returned_attempt = next(
            (
                item
                for item in _json(root / ATTEMPTS).get("attempts", [])
                if isinstance(item, dict)
                and item.get("id") == returns.get("attempt_id")
                and item.get("status") in {"returned", "integrated"}
            ),
            None,
        )
        if returned_attempt is None:
            return {
                "revision": revision,
                "actions": [
                    {
                        "operation_id": "delegation.return",
                        "arguments": {"target": str(root), **dict(returns)},
                        "effects": ["delegation-attempt"],
                        "priority": 90,
                    }
                ],
                "claims": {"blocked": ["complete"]},
            }
    if not eligible:
        return {
            "revision": revision,
            "facts": {
                "assignment": {"requirements": subject, "candidates": model["candidates"], "decision": "no-safe-route"}
            },
            "blockers": [
                {
                    "code": "no-safe-route",
                    "message": "no configured target satisfies capability and transport constraints",
                    "recovery": str(policy.get("override_owner", "human")),
                }
            ],
            "claims": {"blocked": ["complete"]},
        }
    best_score = eligible[0]["score"]
    tied = [item for item in eligible if item["score"] == best_score]
    choice = policy.get("choice")
    if choice not in {item["id"] for item in tied}:
        choice = None
    if len(tied) > 1 and choice is None:
        return {
            "revision": revision,
            "facts": {"assignment": {"requirements": subject, "eligible": tied, "uncertainty": "equal-total-cost"}},
            "decisions": [
                {
                    "id": "assignment-choice",
                    "question": "Which equally eligible target should own this bounded work?",
                    "authority": str(policy.get("override_owner", "human")),
                    "response_operation_id": "assignment.choose",
                    "effects": ["assignment-state"],
                    "choices": [{"id": item["id"], "label": item["id"]} for item in tied],
                }
            ],
            "claims": {"blocked": ["complete"]},
        }
    selected = next(item for item in eligible if item["id"] == choice) if choice else eligible[0]
    assignment = {
        "revision": revision,
        "subject": subject,
        "selected_target": selected["id"],
        "authority": policy.get("assignment_policy", "retain-local"),
        "override_owner": policy.get("override_owner", "human"),
        "reasons": selected["ranking"],
        "transport": selected["transport"],
    }
    if selected["id"] == policy.get("current_target") or policy.get("assignment_policy") != "binding-best-fit":
        return {"revision": revision, "facts": {"assignment": assignment}, "terminal": True}
    attempts = _json(root / ATTEMPTS).get("attempts", [])
    current = next(
        (item for item in attempts if isinstance(item, dict) and item.get("assignment_revision") == revision), None
    )
    if current and current.get("status") == "returned" and current.get("delivery") == "unapplied-delta":
        return {
            "revision": revision,
            "facts": {"assignment": assignment, "returned": current},
            "actions": [
                {
                    "operation_id": "delegation.integrate",
                    "arguments": {
                        "target": str(root),
                        "attempt_id": current["id"],
                        "assignment_revision": current["assignment_revision"],
                    },
                    "effects": ["delegation-attempt", "workspace-managed-files"],
                    "priority": 90,
                }
            ],
            "claims": {"blocked": ["complete"]},
        }
    if current and current.get("status") == "integrated":
        return {
            "revision": revision,
            "facts": {
                "assignment": assignment,
                "worker_result": current.get("result"),
                "delivery": current.get("delivery"),
            },
            "claims": {"blocked": ["complete"]},
            "terminal": True,
        }
    if current:
        failed = current.get("status") == "failed"
        return {
            "revision": revision,
            "facts": {"assignment": assignment, "handoff": current},
            "blockers": [
                {
                    "code": "assigned-work-in-flight",
                    "message": (
                        "binding transport failed; recover or retry the same assignment without local fallback"
                        if failed
                        else "binding non-local work awaits return through delegation.return"
                    ),
                    "recovery": current["id"],
                }
            ],
            "claims": {"blocked": ["complete"]},
        }
    attempt_id = semantic_digest({"assignment": revision, "target": selected["id"]})[:23]
    return {
        "revision": revision,
        "facts": {"assignment": assignment},
        "actions": [
            {
                "operation_id": "delegation.dispatch",
                "arguments": {
                    "target": str(root),
                    "assignment_revision": revision,
                    "target_id": selected["id"],
                    "attempt_id": attempt_id,
                    "subject_revision": str(subject["semantic_revision"]),
                    "scope": list(subject["scope"]),
                    "stops": list(subject["stops"]),
                    "transport": dict(selected["transport"]),
                    "transport_authority": str(policy.get("transport_authority") or "manual"),
                },
                "effects": ["delegation-attempt"],
                "priority": 90,
            }
        ],
        "claims": {"blocked": ["complete"]},
    }


def _choose(arguments: dict[str, Any]) -> dict[str, Any]:
    path = Path(arguments["target"]).resolve() / POLICY
    policy = _json(path)
    policy["choice"] = arguments["target_id"]
    _write_local(path, policy, kind="delegation-policy")
    return {"status": "applied", "effects": ["assignment-state"], "value": {"target_id": arguments["target_id"]}}


def _record(arguments: dict[str, Any]) -> dict[str, Any]:
    path = Path(arguments["target"]).resolve() / EVIDENCE
    state = _json(path) or {"records": []}
    record = dict(arguments["record"])
    required = {"id", "target_id", "source", "authority", "outcome", "context_class", "currentness", "confidence"}
    if (
        not required <= set(record)
        or record.get("authority") not in {"maintainer", "repository", "verification"}
        or record.get("currentness") not in {"current", "stale", "unknown"}
        or not isinstance(record.get("confidence"), int)
        or isinstance(record.get("confidence"), bool)
        or not 0 <= int(record["confidence"]) <= 100
        or any(
            not isinstance(record.get(field, 0), int)
            for field in ("repair_cost", "review_cost", "context_cost", "retry_cost")
        )
    ):
        return {
            "status": "rejected",
            "effects": [],
            "value": {"reason": "invalid-target-evidence-contract"},
        }
    supersedes = set(str(item) for item in record.get("supersedes", []))
    records = [
        item
        for item in state.get("records", [])
        if isinstance(item, dict) and item.get("id") != record["id"] and item.get("id") not in supersedes
    ]
    records.append(record)
    _write_local(path, {"records": records[-50:]}, kind="target-evidence")
    return {"status": "applied", "effects": ["target-evidence"], "value": record}


def _baseline(root: Path, scope: list[str]) -> dict[str, str]:
    values = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if (
            path.is_file()
            and not relative.startswith(".agentic-workspace/")
            and (not scope or any(fnmatch(relative, pattern) for pattern in scope))
        ):
            values[relative] = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    return values


def _dispatch(arguments: dict[str, Any]) -> dict[str, Any]:
    root = Path(arguments["target"]).resolve()
    path = root / ATTEMPTS
    state = _json(path) or {"attempts": []}
    attempt = {
        "id": arguments["attempt_id"],
        "assignment_revision": arguments["assignment_revision"],
        "subject_revision": arguments["subject_revision"],
        "target_id": arguments["target_id"],
        "scope": arguments["scope"],
        "stops": arguments["stops"],
        "transport": arguments["transport"],
        "baseline": _baseline(root, arguments["scope"]),
        "status": "prepared-manual",
    }
    transport = attempt["transport"]
    command = transport.get("command") if isinstance(transport, dict) else None
    automatic = arguments.get("transport_authority") == "automatic"
    if automatic and isinstance(command, list) and command and all(isinstance(part, str) for part in command):
        completed = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
        attempt["transport_result"] = {
            "returncode": completed.returncode,
            "stdout_sha256": "sha256:" + hashlib.sha256(completed.stdout.encode()).hexdigest(),
            "stderr_sha256": "sha256:" + hashlib.sha256(completed.stderr.encode()).hexdigest(),
        }
        attempt["status"] = "in-flight" if completed.returncode == 0 else "failed"
    state["attempts"] = [
        item for item in state.get("attempts", []) if isinstance(item, dict) and item.get("id") != attempt["id"]
    ] + [attempt]
    _write_local(path, {"attempts": state["attempts"][-20:]}, kind="delegation-attempts")
    return {"status": "applied", "effects": ["delegation-attempt"], "value": attempt}


def _return(arguments: dict[str, Any]) -> dict[str, Any]:
    root = Path(arguments["target"]).resolve()
    path = root / ATTEMPTS
    state = _json(path)
    attempt = next(
        (
            item
            for item in state.get("attempts", [])
            if isinstance(item, dict) and item.get("id") == arguments["attempt_id"]
        ),
        None,
    )
    if not attempt or attempt.get("assignment_revision") != arguments["assignment_revision"]:
        return {"status": "rejected", "effects": [], "value": {"reason": "stale-or-unknown-attempt"}}
    changed = [PurePosixPath(item).as_posix() for item in arguments["changed_paths"]]
    if any(
        item.startswith("../")
        or item.startswith("/")
        or not any(fnmatch(item, pattern) for pattern in attempt["scope"])
        for item in changed
    ):
        return {"status": "rejected", "effects": [], "value": {"reason": "returned-delta-out-of-scope"}}
    if arguments["delivery"] == "already-materialized":
        current = _baseline(root, attempt["scope"])
        actual = sorted(
            path
            for path in set(attempt["baseline"]) | set(current)
            if attempt["baseline"].get(path) != current.get(path)
        )
        if actual != sorted(changed):
            return {"status": "rejected", "effects": [], "value": {"reason": "returned-delta-does-not-match-baseline"}}
    artifacts = arguments.get("artifacts", [])
    if arguments["delivery"] == "unapplied-delta":
        if (
            not isinstance(artifacts, list)
            or {str(item.get("path")) for item in artifacts if isinstance(item, dict)} != set(changed)
            or any(
                not isinstance(item, dict)
                or not isinstance(item.get("content"), str)
                or not isinstance(item.get("before_sha256"), str)
                or not isinstance(item.get("after_sha256"), str)
                for item in artifacts
            )
        ):
            return {"status": "rejected", "effects": [], "value": {"reason": "invalid-unapplied-artifacts"}}
    attempt.update(
        status="integrated" if arguments["delivery"] == "already-materialized" else "returned",
        delivery=arguments["delivery"],
        changed_paths=changed,
        artifacts=artifacts,
        result=arguments["result"],
    )
    _write_local(path, {"attempts": state["attempts"]}, kind="delegation-attempts")
    return {"status": "applied", "effects": ["delegation-attempt"], "value": attempt}


def _scoped_artifact_path(root: Path, relative: str, scope: list[str]) -> Path:
    path = PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts or not any(fnmatch(relative, pattern) for pattern in scope):
        raise ValueError("artifact path is outside delegated scope")
    candidate = root.joinpath(*path.parts)
    parent = candidate.parent.resolve()
    if parent != root and root not in parent.parents:
        raise ValueError("artifact path escapes target through indirection")
    return candidate


def _digest_path(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes() if path.is_file() else b"").hexdigest()


def _mark_integrated(root: Path, state: dict[str, Any], attempt: dict[str, Any]) -> dict[str, Any]:
    attempt["status"] = "integrated"
    _write_local(root / ATTEMPTS, {"attempts": state["attempts"]}, kind="delegation-attempts")
    return attempt


def _integrate(arguments: dict[str, Any]) -> dict[str, Any]:
    root = Path(arguments["target"]).resolve()
    state = _json(root / ATTEMPTS)
    attempt = next(
        (
            item
            for item in state.get("attempts", [])
            if isinstance(item, dict) and item.get("id") == arguments["attempt_id"]
        ),
        None,
    )
    if not attempt or attempt.get("assignment_revision") != arguments["assignment_revision"]:
        return {"status": "rejected", "effects": [], "value": {"reason": "stale-or-unknown-attempt"}}
    if attempt.get("status") == "integrated":
        return {"status": "unchanged", "effects": [], "value": attempt}
    if attempt.get("status") != "returned" or attempt.get("delivery") != "unapplied-delta":
        return {"status": "rejected", "effects": [], "value": {"reason": "attempt-not-ready-for-integration"}}
    prepared: list[tuple[Path, bytes]] = []
    for artifact in attempt.get("artifacts", []):
        path = _scoped_artifact_path(root, str(artifact["path"]), list(attempt["scope"]))
        content = str(artifact["content"]).encode()
        if _digest_path(path) != artifact["before_sha256"]:
            return {"status": "rejected", "effects": [], "value": {"reason": "artifact-baseline-mismatch"}}
        if "sha256:" + hashlib.sha256(content).hexdigest() != artifact["after_sha256"]:
            return {"status": "rejected", "effects": [], "value": {"reason": "artifact-content-mismatch"}}
        prepared.append((path, content))
    for path, content in prepared:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{os.getpid()}.delegation")
        temporary.write_bytes(content)
        _replace_artifact(temporary, path)
    integrated = _mark_integrated(root, state, attempt)
    return {"status": "applied", "effects": ["delegation-attempt", "workspace-managed-files"], "value": integrated}


def _recover_choose(arguments: dict[str, Any]) -> dict[str, Any] | None:
    value = _json(Path(arguments["target"]).resolve() / POLICY)
    return (
        {"status": "applied", "effects": ["assignment-state"], "value": {"target_id": arguments["target_id"]}}
        if value.get("choice") == arguments["target_id"]
        else None
    )


def _recover_record(arguments: dict[str, Any]) -> dict[str, Any] | None:
    records = _json(Path(arguments["target"]).resolve() / EVIDENCE).get("records", [])
    record = next(
        (item for item in records if isinstance(item, dict) and item.get("id") == arguments["record"].get("id")), None
    )
    return (
        {"status": "applied", "effects": ["target-evidence"], "value": record}
        if record == arguments["record"]
        else None
    )


def _recover_attempt(arguments: dict[str, Any]) -> dict[str, Any] | None:
    attempts = _json(Path(arguments["target"]).resolve() / ATTEMPTS).get("attempts", [])
    attempt = next(
        (item for item in attempts if isinstance(item, dict) and item.get("id") == arguments["attempt_id"]), None
    )
    if attempt is None:
        return None
    expected = {"returned", "integrated"} if "delivery" in arguments else {"prepared-manual", "in-flight", "failed"}
    effects = ["delegation-attempt"]
    return {"status": "applied", "effects": effects, "value": attempt} if attempt.get("status") in expected else None


def _recover_integrate(arguments: dict[str, Any]) -> dict[str, Any] | None:
    root = Path(arguments["target"]).resolve()
    state = _json(root / ATTEMPTS)
    attempt = next(
        (
            item
            for item in state.get("attempts", [])
            if isinstance(item, dict) and item.get("id") == arguments["attempt_id"]
        ),
        None,
    )
    if not attempt or attempt.get("assignment_revision") != arguments["assignment_revision"]:
        return None
    if attempt.get("status") == "integrated":
        return {
            "status": "applied",
            "effects": ["delegation-attempt", "workspace-managed-files"],
            "value": attempt,
        }
    if attempt.get("status") != "returned" or attempt.get("delivery") != "unapplied-delta":
        return None
    for artifact in attempt.get("artifacts", []):
        path = _scoped_artifact_path(root, str(artifact["path"]), list(attempt["scope"]))
        current = _digest_path(path)
        if current == artifact["after_sha256"]:
            continue
        if current != artifact["before_sha256"]:
            return None
        content = str(artifact["content"]).encode()
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{os.getpid()}.delegation-recover")
        temporary.write_bytes(content)
        _replace_artifact(temporary, path)
    integrated = _mark_integrated(root, state, attempt)
    return {
        "status": "applied",
        "effects": ["delegation-attempt", "workspace-managed-files"],
        "value": integrated,
    }


def _operation(operation_id: str, handler: Any, recover: Any) -> Operation:
    contract = operation_contract(operation_id)
    return Operation(operation_id, contract["input"], tuple(contract["effects"]), handler, recover)


def assignment_module() -> Module:
    return Module(
        name="assignment",
        owns=("assignment-state", "target-evidence", "delegation-attempt"),
        claims=(),
        required_capabilities=("contribution/decisions", "operation/durable-commit"),
        contribute=_contribute,
        operations=(
            _operation("assignment.choose", _choose, _recover_choose),
            _operation("assignment.record-evidence", _record, _recover_record),
            _operation("delegation.dispatch", _dispatch, _recover_attempt),
            _operation("delegation.return", _return, _recover_attempt),
            _operation("delegation.integrate", _integrate, _recover_integrate),
        ),
        currentness=lambda context: (
            semantic_digest(
                {
                    "policy": _json(Path(str(context["target"])) / POLICY),
                    "evidence": _json(Path(str(context["target"])) / EVIDENCE),
                    "attempts": _json(Path(str(context["target"])) / ATTEMPTS),
                    "planning": _json(Path(str(context["target"])) / PLANNING),
                    "task": context.get("task"),
                    "changed_paths": context.get("changed_paths", []),
                    "assignment": context.get("assignment"),
                    "return": context.get("delegation_return"),
                }
            )
            if (Path(str(context["target"])) / POLICY).is_file()
            else None
        ),
    )
