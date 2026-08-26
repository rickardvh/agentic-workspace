from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = REPO_ROOT / "docs" / "maintainer" / "validation-runtime-2435" / "validation-plan.json"
EVIDENCE_PATH = REPO_ROOT / "docs" / "maintainer" / "validation-runtime-2435" / "runtime-evidence.json"
MANIFEST_PATH = REPO_ROOT / "docs" / "maintainer" / "validation-runtime-2435" / "check-bounded-parallel-manifest.json"
MAKEFILE_PATH = REPO_ROOT / "Makefile"
CI_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"

SYNC_TARGETS = {"sync-all", "sync-memory", "sync-planning", "sync-verification"}
SETUP_BEARING_TARGETS = {
    "test": ("sync-all", "test-nosync"),
    "lint": ("sync-all", "lint-nosync"),
    "typecheck": ("sync-all", "typecheck-nosync"),
    "format": ("sync-all", "format-nosync"),
    "format-check": ("sync-all", "format-check-nosync"),
    "verify": ("sync-all", "verify-nosync"),
    "check": ("sync-all", "check-nosync"),
    "check-memory": ("sync-all", "check-memory-nosync"),
    "check-planning": ("sync-all", "check-planning-nosync"),
    "check-verification": ("sync-all", "check-verification-nosync"),
}
NOSYNC_TARGETS = {nosync for _, nosync in SETUP_BEARING_TARGETS.values()}
BROAD_TRACE_COMMAND = "make check-bounded-parallel"


@dataclass(frozen=True)
class Finding:
    path: str
    message: str


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the repository validation-runtime plan and evidence.")
    parser.add_argument("--quiet-success", action="store_true", help="Emit a compact success message.")
    parser.add_argument(
        "--measurement-phase",
        action="store_true",
        help="Validate the measurement graph while deferring only its self-referential checked-in manifest freshness proof.",
    )
    return parser.parse_args(argv)


def _load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return None, str(exc)
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON: {exc.msg}"
    if not isinstance(payload, dict):
        return None, "root must be a JSON object"
    return payload, None


def _repo_relative(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _plan_graph_payload(plan: dict[str, Any]) -> dict[str, Any]:
    trace_fixtures = []
    for trace in plan.get("trace_fixtures", []):
        if not isinstance(trace, dict):
            continue
        events = [
            {
                "constituent_id": str(event.get("constituent_id", "")),
                "outcome": str(event.get("outcome", "")),
                **({"repeat_allowed": True} if event.get("repeat_allowed") else {}),
            }
            for event in trace.get("events", [])
            if isinstance(event, dict)
        ]
        trace_fixtures.append({"id": trace.get("id"), "command": trace.get("command"), "events": events})
    return {
        "kind": plan.get("kind"),
        "schema_version": plan.get("schema_version"),
        "issue": plan.get("issue"),
        "parallel_modes": plan.get("parallel_modes", []),
        "compact_label_map": plan.get("compact_label_map", {}),
        "constituents": plan.get("constituents", []),
        "duplicate_dispositions": plan.get("duplicate_dispositions", []),
        "trace_fixtures": trace_fixtures,
    }


def _sha256_json(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _plan_identity(plan: dict[str, Any]) -> dict[str, Any]:
    raw = PLAN_PATH.read_bytes() if PLAN_PATH.is_file() else b""
    return {
        "kind": "agentic-workspace/validation-plan-identity/v1",
        "path": _repo_relative(PLAN_PATH),
        "schema_version": plan.get("schema_version"),
        "issue": plan.get("issue"),
        "file_sha256": hashlib.sha256(raw).hexdigest(),
        "graph_sha256": _sha256_json(_plan_graph_payload(plan)),
    }


def _git_value(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _git_success(*args: str) -> bool:
    return (
        subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        ).returncode
        == 0
    )


def _expected_broad_constituents(plan: dict[str, Any]) -> list[str]:
    for trace in plan.get("trace_fixtures", []):
        if not isinstance(trace, dict) or trace.get("command") != BROAD_TRACE_COMMAND:
            continue
        events = trace.get("events")
        if isinstance(events, list):
            return [str(event.get("constituent_id")) for event in events if isinstance(event, dict)]
    return []


def _constituents_by_id(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item.get("id")): item for item in plan.get("constituents", []) if isinstance(item, dict) and item.get("id")}


def _label_metadata_by_id(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    metadata_by_id: dict[str, dict[str, Any]] = {}
    label_map = plan.get("compact_label_map", {})
    if not isinstance(label_map, dict):
        return metadata_by_id
    for label, metadata in label_map.items():
        if not isinstance(metadata, dict):
            continue
        constituent_id = str(metadata.get("id") or "")
        if constituent_id:
            metadata_by_id[constituent_id] = {"label": label, **metadata}
    return metadata_by_id


def _target_map(makefile_text: str) -> dict[str, list[str]]:
    targets: dict[str, list[str]] = {}
    pattern = re.compile(r"^([A-Za-z0-9_.-]+):\s*(.*)$")
    for line in makefile_text.splitlines():
        match = pattern.match(line)
        if not match:
            continue
        target, raw_deps = match.groups()
        if target.startswith("."):
            continue
        deps = [part for part in raw_deps.split() if part and not part.startswith("$")]
        targets[target] = deps
    return targets


def _recursive_dependencies(targets: dict[str, list[str]], target: str, *, seen: set[str] | None = None) -> set[str]:
    seen = set() if seen is None else seen
    deps: set[str] = set()
    for dep in targets.get(target, []):
        if dep in seen:
            continue
        seen.add(dep)
        deps.add(dep)
        deps.update(_recursive_dependencies(targets, dep, seen=seen))
    return deps


def _ci_jobs(workflow_text: str) -> dict[str, list[str]]:
    jobs: dict[str, list[str]] = {}
    current_job: str | None = None
    for line in workflow_text.splitlines():
        if line.startswith("  ") and not line.startswith("    ") and line.rstrip().endswith(":"):
            current_job = line.strip().removesuffix(":")
            jobs[current_job] = []
            continue
        if current_job is not None and "run:" in line:
            jobs[current_job].append(line.strip().removeprefix("run:").strip())
    return jobs


def _required_fields_findings(path: str, payload: dict[str, Any], fields: tuple[str, ...]) -> list[Finding]:
    return [Finding(path=path, message=f"missing required field: {field}") for field in fields if field not in payload]


def _validate_constituents(plan: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    constituents = plan.get("constituents")
    if not isinstance(constituents, list) or not constituents:
        return [Finding(path=PLAN_PATH.as_posix(), message="constituents must be a non-empty list")]

    ids: list[str] = []
    commands: dict[str, list[str]] = defaultdict(list)
    for index, constituent in enumerate(constituents):
        location = f"{PLAN_PATH.as_posix()}#constituents[{index}]"
        if not isinstance(constituent, dict):
            findings.append(Finding(path=location, message="constituent must be an object"))
            continue
        findings.extend(
            _required_fields_findings(
                location,
                constituent,
                ("id", "command", "proof_purpose", "execution_posture", "dependencies", "owner_boundary"),
            )
        )
        constituent_id = str(constituent.get("id", ""))
        command = str(constituent.get("command", ""))
        ids.append(constituent_id)
        commands[command].append(constituent_id)
        if not constituent_id or not re.fullmatch(r"[a-z0-9][a-z0-9_.-]*", constituent_id):
            findings.append(Finding(path=location, message="id must be a stable lowercase identifier"))
        if not constituent.get("proof_purpose"):
            findings.append(Finding(path=location, message="proof_purpose must be non-empty"))
        if not isinstance(constituent.get("dependencies"), list):
            findings.append(Finding(path=location, message="dependencies must be a list"))

    duplicate_ids = [item for item, count in Counter(ids).items() if count > 1]
    findings.extend(Finding(path=PLAN_PATH.as_posix(), message=f"duplicate constituent id: {item}") for item in duplicate_ids)

    dispositions = plan.get("duplicate_dispositions", [])
    disposition_commands = {
        str(disposition.get("command"))
        for disposition in dispositions
        if isinstance(disposition, dict) and disposition.get("distinct_proof_claims") is True
    }
    for command, command_ids in commands.items():
        if command and len(command_ids) > 1 and command not in disposition_commands:
            findings.append(
                Finding(
                    path=PLAN_PATH.as_posix(),
                    message=f"command appears in multiple constituents without a distinct-proof disposition: {command}",
                )
            )
    return findings


def _compact_makefile_labels(makefile_text: str) -> set[str]:
    return set(re.findall(r'--label\s+"([^"]+)"', makefile_text))


def _validate_compact_label_map(plan: dict[str, Any], makefile_text: str) -> list[Finding]:
    findings: list[Finding] = []
    label_map = plan.get("compact_label_map")
    if not isinstance(label_map, dict) or not label_map:
        return [Finding(path=PLAN_PATH.as_posix(), message="compact_label_map must be a non-empty object")]
    makefile_labels = _compact_makefile_labels(makefile_text)
    missing_labels = sorted(makefile_labels.difference(label_map))
    findings.extend(Finding(path="Makefile", message=f"compact label missing from validation plan: {label}") for label in missing_labels)

    constituent_ids = {str(item.get("id")) for item in plan.get("constituents", []) if isinstance(item, dict)}
    for label, metadata in label_map.items():
        location = f"{PLAN_PATH.as_posix()}#compact_label_map.{label}"
        if not isinstance(metadata, dict):
            findings.append(Finding(path=location, message="label metadata must be an object"))
            continue
        constituent_id = str(metadata.get("id", ""))
        if constituent_id not in constituent_ids:
            findings.append(Finding(path=location, message=f"unknown constituent id: {constituent_id}"))
        dependencies = metadata.get("dependencies")
        if not isinstance(dependencies, list):
            findings.append(Finding(path=location, message="dependencies must be a list"))
            continue
        for dependency in dependencies:
            if str(dependency) not in constituent_ids:
                findings.append(Finding(path=location, message=f"unknown mapped dependency: {dependency}"))
        command = metadata.get("command")
        if command is not None and (
            not isinstance(command, list) or not command or not all(isinstance(item, str) and item.strip() for item in command)
        ):
            findings.append(Finding(path=location, message="command must be a non-empty string list when present"))
        if not metadata.get("proof_purpose"):
            findings.append(Finding(path=location, message="proof_purpose must be non-empty"))
    return findings


def _validate_makefile(plan: dict[str, Any], makefile_text: str) -> list[Finding]:
    findings: list[Finding] = []
    targets = _target_map(makefile_text)

    for target, required_deps in SETUP_BEARING_TARGETS.items():
        deps = targets.get(target)
        if deps is None:
            findings.append(Finding(path="Makefile", message=f"missing setup-bearing target: {target}"))
            continue
        for dep in required_deps:
            if dep not in deps:
                findings.append(Finding(path="Makefile", message=f"{target} must depend on {dep}"))
        sync_deps = [dep for dep in deps if dep in SYNC_TARGETS]
        if sync_deps != [required_deps[0]]:
            findings.append(Finding(path="Makefile", message=f"{target} must perform exactly one setup dependency"))

    for target in NOSYNC_TARGETS:
        recursive = _recursive_dependencies(targets, target)
        forbidden = sorted(recursive.intersection(SYNC_TARGETS).union(recursive.intersection(SETUP_BEARING_TARGETS)))
        if forbidden:
            findings.append(Finding(path="Makefile", message=f"{target} must not depend on setup-bearing targets: {', '.join(forbidden)}"))

    check_deps = targets.get("check-nosync", [])
    if "validation-runtime-plan" not in check_deps:
        findings.append(Finding(path="Makefile", message="check-nosync must include validation-runtime-plan"))

    planned_targets = {
        str(item.get("make_target")) for item in plan.get("constituents", []) if isinstance(item, dict) and item.get("make_target")
    }
    missing_targets = sorted(target for target in planned_targets if target not in targets)
    findings.extend(Finding(path="Makefile", message=f"validation plan references missing target: {target}") for target in missing_targets)
    return findings


def _validate_ci(workflow_text: str) -> list[Finding]:
    findings: list[Finding] = []
    jobs = _ci_jobs(workflow_text)
    expected_jobs = {"workspace-checks", "workspace-package-artifacts", "package-checks"}
    for job in sorted(expected_jobs.difference(jobs)):
        findings.append(Finding(path=CI_PATH.as_posix(), message=f"missing CI job: {job}"))

    for job, commands in jobs.items():
        sync_commands = [command for command in commands if command.startswith("make sync-")]
        if job in expected_jobs and len(sync_commands) != 1:
            findings.append(Finding(path=CI_PATH.as_posix(), message=f"{job} must run exactly one explicit sync command"))
        if job == "workspace-checks" and "make typecheck-nosync" not in commands:
            findings.append(Finding(path=CI_PATH.as_posix(), message="workspace-checks must use typecheck-nosync after sync-all"))
        if job == "package-checks":
            if "make sync-${{ matrix.package }}" not in commands:
                findings.append(Finding(path=CI_PATH.as_posix(), message="package-checks must sync the package-scoped environment once"))
            if "make check-${{ matrix.package }}-nosync" not in commands:
                findings.append(Finding(path=CI_PATH.as_posix(), message="package-checks must use package nosync checks"))
            if any(command == "make check-${{ matrix.package }}" for command in commands):
                findings.append(Finding(path=CI_PATH.as_posix(), message="package-checks must not call setup-bearing package checks"))
    return findings


def _validate_traces(plan: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    constituent_ids = {str(item.get("id")) for item in plan.get("constituents", []) if isinstance(item, dict)}
    dependencies = {
        str(item.get("id")): [str(dep) for dep in item.get("dependencies", [])]
        for item in plan.get("constituents", [])
        if isinstance(item, dict)
    }
    for trace_index, trace in enumerate(plan.get("trace_fixtures", [])):
        events = trace.get("events") if isinstance(trace, dict) else None
        if not isinstance(events, list):
            findings.append(Finding(path=f"{PLAN_PATH.as_posix()}#trace_fixtures[{trace_index}]", message="events must be a list"))
            continue
        seen: set[str] = set()
        for event_index, event in enumerate(events):
            constituent_id = str(event.get("constituent_id", "")) if isinstance(event, dict) else ""
            location = f"{PLAN_PATH.as_posix()}#trace_fixtures[{trace_index}].events[{event_index}]"
            if constituent_id not in constituent_ids:
                findings.append(Finding(path=location, message=f"unknown constituent id: {constituent_id}"))
                continue
            if constituent_id in seen and not event.get("repeat_allowed"):
                findings.append(Finding(path=location, message=f"duplicate constituent execution: {constituent_id}"))
            missing = [dep for dep in dependencies.get(constituent_id, []) if dep not in seen]
            if missing:
                findings.append(Finding(path=location, message=f"dependencies must execute first: {', '.join(missing)}"))
            seen.add(constituent_id)
    return findings


def _record_by_metric(evidence: dict[str, Any], phase: str, metric: str) -> dict[str, Any] | None:
    for record in evidence.get("runtime_records", []):
        if not isinstance(record, dict):
            continue
        if record.get("phase") == phase and record.get("metric") == metric:
            return record
    return None


def _validate_evidence(evidence: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(
        _required_fields_findings(
            EVIDENCE_PATH.as_posix(),
            evidence,
            ("kind", "schema_version", "issue", "environment", "runtime_records", "critical_path_reports"),
        )
    )
    if evidence.get("kind") != "agentic-workspace/validation-runtime-evidence/v1":
        findings.append(Finding(path=EVIDENCE_PATH.as_posix(), message="unexpected evidence kind"))

    records = evidence.get("runtime_records", [])
    if not isinstance(records, list) or len(records) < 6:
        findings.append(Finding(path=EVIDENCE_PATH.as_posix(), message="runtime_records must include before and after measurements"))
        return findings

    before_records = [record for record in records if isinstance(record, dict) and record.get("phase") == "before"]
    after_records = [record for record in records if isinstance(record, dict) and record.get("phase") == "after"]
    if len(before_records) < 3:
        findings.append(Finding(path=EVIDENCE_PATH.as_posix(), message="before baseline must include at least three records"))
    if len(after_records) < 3:
        findings.append(Finding(path=EVIDENCE_PATH.as_posix(), message="after evidence must include at least three records"))

    structured_before = _record_by_metric(evidence, "before", "structured_file_inventory.full")
    structured_after = _record_by_metric(evidence, "after", "structured_file_inventory.full")
    changed_after = _record_by_metric(evidence, "after", "structured_file_inventory.changed_path_narrow")
    broad_after = _record_by_metric(evidence, "after", "broad_validation.full")
    for label, record in (
        ("before structured inventory", structured_before),
        ("after structured inventory", structured_after),
        ("after changed-path inventory", changed_after),
        ("after broad validation", broad_after),
    ):
        if record is None:
            findings.append(Finding(path=EVIDENCE_PATH.as_posix(), message=f"missing runtime evidence: {label}"))
    if structured_before and structured_after:
        before_seconds = float(structured_before["duration_seconds"])
        after_seconds = float(structured_after["duration_seconds"])
        if after_seconds > 30:
            findings.append(Finding(path=EVIDENCE_PATH.as_posix(), message="full structured inventory must complete within 30 seconds"))
        if before_seconds / max(after_seconds, 0.001) < 5:
            findings.append(
                Finding(path=EVIDENCE_PATH.as_posix(), message="full structured inventory must be at least 5x faster than baseline")
            )
    if changed_after and float(changed_after["duration_seconds"]) > 5:
        findings.append(Finding(path=EVIDENCE_PATH.as_posix(), message="changed-path structured inventory must complete within 5 seconds"))
    if broad_after and float(broad_after["duration_seconds"]) > 600:
        findings.append(Finding(path=EVIDENCE_PATH.as_posix(), message="broad validation must complete within 10 minutes"))
    if broad_after and broad_after.get("outcome") != "passed":
        findings.append(Finding(path=EVIDENCE_PATH.as_posix(), message="broad validation evidence must be a passing measured run"))
    if broad_after and "placeholder" in str(broad_after.get("source", "")).lower():
        findings.append(Finding(path=EVIDENCE_PATH.as_posix(), message="broad validation evidence must not be a placeholder"))
    series = evidence.get("measurement_series", [])
    if not isinstance(series, list):
        findings.append(Finding(path=EVIDENCE_PATH.as_posix(), message="measurement_series must be a list"))
        return findings
    required_series = {
        "structured_file_inventory.full": (3, 30.0),
        "structured_file_inventory.changed_path_narrow": (3, 5.0),
        "broad_validation.full": (2, 600.0),
    }
    series_by_metric = {
        str(record.get("metric")): record for record in series if isinstance(record, dict) and record.get("phase") == "after"
    }
    for metric, (minimum_count, budget_seconds) in required_series.items():
        record = series_by_metric.get(metric)
        if record is None:
            findings.append(Finding(path=EVIDENCE_PATH.as_posix(), message=f"missing measurement series: {metric}"))
            continue
        durations = record.get("durations_seconds")
        if not isinstance(durations, list) or len(durations) < minimum_count:
            findings.append(
                Finding(path=EVIDENCE_PATH.as_posix(), message=f"{metric} measurement series must contain at least {minimum_count} runs")
            )
            continue
        for duration in durations:
            if float(duration) > budget_seconds:
                findings.append(Finding(path=EVIDENCE_PATH.as_posix(), message=f"{metric} measurement exceeds budget"))
        if record.get("outcome") != "passed":
            findings.append(Finding(path=EVIDENCE_PATH.as_posix(), message=f"{metric} measurement series must pass"))
    return findings


def _validate_manifest(plan: dict[str, Any], evidence: dict[str, Any]) -> list[Finding]:
    manifest, manifest_error = _load_json(MANIFEST_PATH)
    if manifest_error is not None:
        return [Finding(path=MANIFEST_PATH.as_posix(), message=manifest_error)]
    if manifest is None:
        return [Finding(path=MANIFEST_PATH.as_posix(), message="manifest must be a JSON object")]
    findings: list[Finding] = []
    if manifest.get("kind") != "agentic-workspace/validation-run-manifest/v1":
        findings.append(Finding(path=MANIFEST_PATH.as_posix(), message="unexpected manifest kind"))
    results = manifest.get("results")
    if not isinstance(results, list) or not results:
        return [Finding(path=MANIFEST_PATH.as_posix(), message="results must be a non-empty list")]

    expected_plan_identity = _plan_identity(plan)
    manifest_plan_identity = manifest.get("plan_identity")
    if not isinstance(manifest_plan_identity, dict):
        findings.append(Finding(path=MANIFEST_PATH.as_posix(), message="manifest must include plan_identity"))
    elif manifest_plan_identity.get("graph_sha256") != expected_plan_identity["graph_sha256"]:
        findings.append(Finding(path=MANIFEST_PATH.as_posix(), message="manifest plan_identity graph_sha256 is stale"))

    repository = manifest.get("repository")
    if not isinstance(repository, dict):
        findings.append(Finding(path=MANIFEST_PATH.as_posix(), message="manifest must include repository identity"))
        repository = {}
    for field in ("head", "tree"):
        if not isinstance(repository.get(field), str) or not repository.get(field):
            findings.append(Finding(path=MANIFEST_PATH.as_posix(), message=f"manifest repository.{field} must be non-empty"))
    if repository.get("tracked_dirty") is True:
        findings.append(Finding(path=MANIFEST_PATH.as_posix(), message="manifest measured repository must not have tracked dirty state"))

    constituent_map = _constituents_by_id(plan)
    label_metadata = _label_metadata_by_id(plan)
    constituent_ids = set(constituent_map)
    expected_broad = _expected_broad_constituents(plan)
    if not expected_broad:
        findings.append(Finding(path=PLAN_PATH.as_posix(), message=f"missing trace fixture for {BROAD_TRACE_COMMAND}"))
    result_ids = [str(result.get("constituent_id", "")) for result in results if isinstance(result, dict)]
    if Counter(result_ids) != Counter(expected_broad):
        missing = sorted((Counter(expected_broad) - Counter(result_ids)).elements())
        extra = sorted((Counter(result_ids) - Counter(expected_broad)).elements())
        if missing:
            findings.append(Finding(path=MANIFEST_PATH.as_posix(), message=f"manifest missing broad constituents: {', '.join(missing)}"))
        if extra:
            findings.append(Finding(path=MANIFEST_PATH.as_posix(), message=f"manifest has extra broad constituents: {', '.join(extra)}"))

    seen: set[str] = set()
    outcomes = Counter()
    for index, result in enumerate(results):
        location = f"{MANIFEST_PATH.as_posix()}#results[{index}]"
        if not isinstance(result, dict):
            findings.append(Finding(path=location, message="result must be an object"))
            continue
        constituent_id = str(result.get("constituent_id", ""))
        if constituent_id not in constituent_ids:
            findings.append(Finding(path=location, message=f"unknown constituent id: {constituent_id}"))
            plan_constituent = {}
        else:
            plan_constituent = constituent_map[constituent_id]
        metadata = label_metadata.get(constituent_id, {})
        if constituent_id in seen:
            findings.append(Finding(path=location, message=f"duplicate constituent result: {constituent_id}"))
        seen.add(constituent_id)
        dependencies = result.get("dependencies")
        if not isinstance(dependencies, list):
            findings.append(Finding(path=location, message="dependencies must be a list"))
        else:
            for dependency in dependencies:
                if str(dependency) not in constituent_ids:
                    findings.append(Finding(path=location, message=f"unknown dependency: {dependency}"))
            if plan_constituent and dependencies != plan_constituent.get("dependencies"):
                findings.append(Finding(path=location, message="dependencies do not match validation plan"))
        expected_command = metadata.get("command")
        if constituent_id in expected_broad:
            if not isinstance(expected_command, list):
                findings.append(
                    Finding(path=PLAN_PATH.as_posix(), message=f"missing expected command for broad constituent: {constituent_id}")
                )
            elif result.get("command") != expected_command:
                findings.append(Finding(path=location, message="command does not match validation plan"))
        if not result.get("proof_purpose"):
            findings.append(Finding(path=location, message="proof_purpose must be non-empty"))
        elif plan_constituent and result.get("proof_purpose") != plan_constituent.get("proof_purpose"):
            findings.append(Finding(path=location, message="proof_purpose does not match validation plan"))
        for field in ("execution_posture", "owner_boundary"):
            if not result.get(field):
                findings.append(Finding(path=location, message=f"{field} must be non-empty"))
            elif plan_constituent and result.get(field) != plan_constituent.get(field):
                findings.append(Finding(path=location, message=f"{field} does not match validation plan"))
        result_plan_identity = result.get("plan_identity")
        if not isinstance(result_plan_identity, dict) or result_plan_identity.get("graph_sha256") != expected_plan_identity["graph_sha256"]:
            findings.append(Finding(path=location, message="result plan_identity graph_sha256 is stale"))
        result_repository = result.get("repository")
        if not isinstance(result_repository, dict) or result_repository != repository:
            findings.append(Finding(path=location, message="result repository identity must match manifest repository"))
        if result.get("kind") != "agentic-workspace/validation-constituent-result/v1":
            findings.append(Finding(path=location, message="unexpected result kind"))
        outcomes[str(result.get("outcome") or "unknown")] += 1

    if int(manifest.get("result_count", -1)) != len(results):
        findings.append(Finding(path=MANIFEST_PATH.as_posix(), message="result_count must match results length"))
    if dict(outcomes) != manifest.get("outcomes"):
        findings.append(Finding(path=MANIFEST_PATH.as_posix(), message="outcomes must match result records"))
    if outcomes and set(outcomes) != {"passed"}:
        findings.append(Finding(path=MANIFEST_PATH.as_posix(), message="closeout manifest must contain only passing results"))

    broad_after = _record_by_metric(evidence, "after", "broad_validation.full")
    if broad_after:
        manifest_ref = broad_after.get("manifest")
        expected_ref = _repo_relative(MANIFEST_PATH)
        if manifest_ref != expected_ref:
            findings.append(Finding(path=EVIDENCE_PATH.as_posix(), message=f"broad validation must reference {expected_ref}"))
        if round(float(broad_after.get("duration_seconds") or 0.0), 3) != round(float(manifest.get("critical_path_seconds") or 0.0), 3):
            findings.append(Finding(path=EVIDENCE_PATH.as_posix(), message="broad validation duration must match manifest critical path"))
        for field in ("measured_head", "measured_tree", "plan_graph_sha256"):
            if not isinstance(broad_after.get(field), str) or not broad_after.get(field):
                findings.append(Finding(path=EVIDENCE_PATH.as_posix(), message=f"broad validation must include {field}"))
        if broad_after.get("measured_head") != repository.get("head"):
            findings.append(
                Finding(path=EVIDENCE_PATH.as_posix(), message="broad validation measured_head must match manifest repository head")
            )
        if broad_after.get("measured_tree") != repository.get("tree"):
            findings.append(
                Finding(path=EVIDENCE_PATH.as_posix(), message="broad validation measured_tree must match manifest repository tree")
            )
        if broad_after.get("plan_graph_sha256") != expected_plan_identity["graph_sha256"]:
            findings.append(
                Finding(path=EVIDENCE_PATH.as_posix(), message="broad validation plan_graph_sha256 must match current plan graph")
            )
    after_reference = (
        evidence.get("pinned_revisions", {}).get("after_reference", {}) if isinstance(evidence.get("pinned_revisions"), dict) else {}
    )
    if isinstance(after_reference, dict):
        if after_reference.get("measured_head") != repository.get("head"):
            findings.append(
                Finding(path=EVIDENCE_PATH.as_posix(), message="after_reference measured_head must match manifest repository head")
            )
        if after_reference.get("measured_tree") != repository.get("tree"):
            findings.append(
                Finding(path=EVIDENCE_PATH.as_posix(), message="after_reference measured_tree must match manifest repository tree")
            )
        if after_reference.get("plan_graph_sha256") != expected_plan_identity["graph_sha256"]:
            findings.append(
                Finding(path=EVIDENCE_PATH.as_posix(), message="after_reference plan_graph_sha256 must match current plan graph")
            )
        if "after this evidence file is committed" in str(after_reference.get("tree_identity", "")):
            findings.append(
                Finding(
                    path=EVIDENCE_PATH.as_posix(), message="after_reference must not use a future/self-referential revision placeholder"
                )
            )
    after_reports = [
        report
        for report in evidence.get("critical_path_reports", [])
        if isinstance(report, dict) and report.get("phase") == "after" and report.get("command") == BROAD_TRACE_COMMAND
    ]
    if not after_reports:
        findings.append(Finding(path=EVIDENCE_PATH.as_posix(), message="missing after critical path report for broad validation"))
    else:
        report = after_reports[0]
        if round(float(report.get("critical_path_seconds") or 0.0), 3) != round(float(manifest.get("critical_path_seconds") or 0.0), 3):
            findings.append(Finding(path=EVIDENCE_PATH.as_posix(), message="critical path report must match manifest critical path"))
        if round(float(report.get("summed_work_seconds") or 0.0), 3) != round(float(manifest.get("summed_work_seconds") or 0.0), 3):
            findings.append(Finding(path=EVIDENCE_PATH.as_posix(), message="critical path report must match manifest summed work"))
        dict_results = [item for item in results if isinstance(item, dict)]
        expected_top = [
            {"constituent_id": item.get("constituent_id"), "duration_seconds": item.get("duration_seconds")}
            for item in sorted(dict_results, key=lambda item: float(item.get("duration_seconds") or 0.0), reverse=True)[:3]
        ]
        actual_top = [
            {"constituent_id": item.get("constituent_id"), "duration_seconds": item.get("duration_seconds")}
            for item in report.get("top_contributors", [])
            if isinstance(item, dict)
        ][:3]
        if actual_top != expected_top:
            findings.append(Finding(path=EVIDENCE_PATH.as_posix(), message="top contributors must be derived from manifest durations"))
    if float(manifest.get("critical_path_seconds") or 0.0) > 600:
        findings.append(Finding(path=MANIFEST_PATH.as_posix(), message="manifest critical path must complete within 10 minutes"))
    head = str(repository.get("head") or "")
    if head and not _git_success("merge-base", "--is-ancestor", head, "HEAD"):
        findings.append(Finding(path=MANIFEST_PATH.as_posix(), message="manifest measured head must be an ancestor of current HEAD"))
    return findings


def validation_findings(*, measurement_phase: bool = False) -> list[Finding]:
    plan, plan_error = _load_json(PLAN_PATH)
    evidence, evidence_error = _load_json(EVIDENCE_PATH)
    findings: list[Finding] = []
    if plan_error is not None:
        findings.append(Finding(path=PLAN_PATH.as_posix(), message=plan_error))
    if evidence_error is not None:
        findings.append(Finding(path=EVIDENCE_PATH.as_posix(), message=evidence_error))
    if plan is None or evidence is None:
        return findings
    if plan.get("kind") != "agentic-workspace/validation-runtime-plan/v1":
        findings.append(Finding(path=PLAN_PATH.as_posix(), message="unexpected plan kind"))
    findings.extend(_validate_constituents(plan))
    makefile_text = MAKEFILE_PATH.read_text(encoding="utf-8")
    findings.extend(_validate_compact_label_map(plan, makefile_text))
    findings.extend(_validate_makefile(plan, makefile_text))
    findings.extend(_validate_ci(CI_PATH.read_text(encoding="utf-8")))
    findings.extend(_validate_traces(plan))
    findings.extend(_validate_evidence(evidence))
    if not measurement_phase:
        findings.extend(_validate_manifest(plan, evidence))
    return findings


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    findings = validation_findings(measurement_phase=args.measurement_phase)
    if findings:
        print("Validation runtime plan check failed:", file=sys.stderr)
        for finding in findings:
            print(f"- {finding.path}: {finding.message}", file=sys.stderr)
        return 1
    if args.quiet_success:
        posture = " measurement phase" if args.measurement_phase else ""
        print(f"Validation runtime plan{posture} check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
