from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = REPO_ROOT / "docs" / "maintainer" / "validation-runtime-2435" / "validation-plan.json"
EVIDENCE_PATH = REPO_ROOT / "docs" / "maintainer" / "validation-runtime-2435" / "runtime-evidence.json"
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


@dataclass(frozen=True)
class Finding:
    path: str
    message: str


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the repository validation-runtime plan and evidence.")
    parser.add_argument("--quiet-success", action="store_true", help="Emit a compact success message.")
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
    return findings


def validation_findings() -> list[Finding]:
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
    findings.extend(_validate_makefile(plan, MAKEFILE_PATH.read_text(encoding="utf-8")))
    findings.extend(_validate_ci(CI_PATH.read_text(encoding="utf-8")))
    findings.extend(_validate_traces(plan))
    findings.extend(_validate_evidence(evidence))
    return findings


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    findings = validation_findings()
    if findings:
        print("Validation runtime plan check failed:", file=sys.stderr)
        for finding in findings:
            print(f"- {finding.path}: {finding.message}", file=sys.stderr)
        return 1
    if args.quiet_success:
        print("Validation runtime plan check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
