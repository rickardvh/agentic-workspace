from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import time
import tomllib
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, cast

from jsonschema import Draft202012Validator

from repo_planning_bootstrap import __version__
from repo_planning_bootstrap._ownership import module_root
from repo_planning_bootstrap._render import (
    load_manifest,
    render_quickstart,
    render_routing,
)
from repo_planning_bootstrap._source import UPGRADE_SOURCE_PATH, resolve_upgrade_source

PLANNING_MANAGED_ROOT = module_root("planning")
WORKSPACE_WORKFLOW_PATH = Path(".agentic-workspace") / "WORKFLOW.md"
PLANNING_SKILLS_MANAGED_ROOT = PLANNING_MANAGED_ROOT / "skills"
PLANNING_MANIFEST_PATH = PLANNING_MANAGED_ROOT / "agent-manifest.json"
PLANNING_STATE_PATH = PLANNING_MANAGED_ROOT / "state.toml"
PLANNING_EXTERNAL_INTENT_EVIDENCE_PATH = PLANNING_MANAGED_ROOT / "external-intent-evidence.json"
PLANNING_EXTERNAL_INTENT_CACHE_PATH = Path(".agentic-workspace") / "local" / "cache" / "external-intent-evidence.json"
PLANNING_FINISHED_WORK_EVIDENCE_PATH = PLANNING_MANAGED_ROOT / "finished-work-evidence.json"
PLANNING_MUTATION_PROVENANCE_PATH = PLANNING_MANAGED_ROOT / "mutation-provenance.json"
PLANNING_MUTATION_PROVENANCE_LOCK_TIMEOUT_SECONDS = 10.0
PLANNING_MUTATION_PROVENANCE_LOCK_STALE_SECONDS = 60.0
PLANNING_SCHEMA_ROOT = PLANNING_MANAGED_ROOT / "schemas"
EXECPLAN_RECORD_SCHEMA_PATH = PLANNING_SCHEMA_ROOT / "planning-execplan.schema.json"
DECOMPOSITION_RECORD_SCHEMA_PATH = PLANNING_SCHEMA_ROOT / "planning-decomposition.schema.json"
REVIEW_RECORD_SCHEMA_PATH = PLANNING_SCHEMA_ROOT / "planning-review.schema.json"
EXTERNAL_INTENT_EVIDENCE_SCHEMA_PATH = PLANNING_SCHEMA_ROOT / "planning-external-intent-evidence.schema.json"

EXTERNAL_INTENT_REFRESH_COMMAND = (
    "agentic-workspace external-intent refresh-github --target ./repo --state all --storage cache --format json"
)
EXTERNAL_INTENT_SNAPSHOT_RULE = (
    "External intent evidence is a provider-agnostic snapshot, not live tracker truth; refresh after creating, "
    "closing, or editing external tracker items."
)
FINISHED_WORK_EVIDENCE_SCHEMA_PATH = PLANNING_SCHEMA_ROOT / "planning-finished-work-evidence.schema.json"
SOURCE_PLANNING_CHECKER_SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "check" / "check_planning_surfaces.py"
PLANNING_STATE_KIND = "agentic-planning-state"
PLANNING_STATE_SCHEMA_VERSION = "planning-state/v1"
MANAGED_STATE_HEADER_LINES = (
    "# Agentic Workspace managed state.",
    "# Do not edit by hand when the CLI is available.",
    "# Inspect: uv run agentic-workspace summary --format json",
    "# Mutate through the package command named by that output.",
)
PLANNING_STATE_MATURITIES = {"idea", "candidate", "shaped", "ready", "active"}
PLANNING_STATE_STATUSES = {"deferred", "next", "active", "blocked"}
ARCHIVE_SLICE_STATUS_VALUES = ("complete", "completed", "bounded slice complete")
ARCHIVE_AND_CLOSE_LARGER_INTENT_VALUES = ("closed", "complete", "completed")
ARCHIVE_KEEP_OPEN_LARGER_INTENT_VALUES = ("open", "partial", "unfinished")
ARCHIVE_CLOSURE_DECISION_VALUES = ("archive-and-close", "archive-but-keep-lane-open")
ARCHIVE_CLOSEOUT_SCOPE_VALUES = ("slice", "lane", "epic")
ARCHIVE_CLOSEOUT_VALUE_HINT = (
    "Accepted values: slice status = complete|completed|bounded slice complete; "
    "larger-intent status = closed|complete|completed for archive-and-close or open|partial|unfinished "
    "for archive-but-keep-lane-open; closure decision = archive-and-close|archive-but-keep-lane-open. "
    "Prefer `agentic-planning archive-plan <plan> --prepare-closeout` before hand-editing closeout fields."
)
PLANNING_CLOSEOUT_CLAIM_LEVELS = {"slice", "lane", "epic"}
PLANNING_CLOSEOUT_INTENT_STATUSES = {"satisfied", "partial", "unsatisfied", "deferred-with-owner"}
PLANNING_CLOSEOUT_RESIDUE_STATUSES = {"none", "memory", "planning", "docs", "tests", "contracts", "issue", "dismissed"}
PLANNING_CLOSEOUT_RESIDUE_MAP = {
    "none": ("none", "archive"),
    "dismissed": ("evidence_only", "archive"),
    "memory": ("memory", "Memory"),
    "planning": ("planning", PLANNING_STATE_PATH.as_posix()),
    "docs": ("docs", "docs"),
    "tests": ("check", "tests"),
    "contracts": ("contract", "contracts"),
    "issue": ("planning", "issue follow-up"),
}
PLANNING_STATE_ROLE_FIELDS = (
    "decision_owner",
    "strategy_role",
    "owner_role",
    "delivery_role",
    "review_role",
    "knowledge_owner",
)

REQUIRED_PAYLOAD_FILES = (
    Path("AGENTS.template.md"),
    Path(".agentic-workspace/docs/execution-flow-contract.md"),
    Path(".agentic-workspace/docs/system-intent-contract.md"),
    Path(".agentic-workspace/docs/routing-contract.md"),
    Path(".agentic-workspace/docs/minimum-operating-model.md"),
    Path(".agentic-workspace/docs/lifecycle-and-config-contract.md"),
    Path(".agentic-workspace/docs/workspace-config-contract.md"),
    Path(".agentic-workspace/planning/execplans/README.md"),
    Path(".agentic-workspace/planning/execplans/TEMPLATE.plan.json"),
    Path(".agentic-workspace/planning/execplans/archive/README.md"),
    Path(".agentic-workspace/planning/decompositions/README.md"),
    Path(".agentic-workspace/planning/decompositions/TEMPLATE.decomposition.json"),
    EXECPLAN_RECORD_SCHEMA_PATH,
    DECOMPOSITION_RECORD_SCHEMA_PATH,
    REVIEW_RECORD_SCHEMA_PATH,
    EXTERNAL_INTENT_EVIDENCE_SCHEMA_PATH,
    FINISHED_WORK_EVIDENCE_SCHEMA_PATH,
    UPGRADE_SOURCE_PATH,
    PLANNING_MANIFEST_PATH,
)

OPTIONAL_PAYLOAD_FILES = (
    Path(".agentic-workspace/docs/capability-contract.json"),
    Path(".agentic-workspace/planning/reviews/README.md"),
    Path(".agentic-workspace/planning/reviews/TEMPLATE.review.json"),
    Path(".agentic-workspace/planning/upstream-task-intake.md"),
    Path(".agentic-workspace/planning/pre-ingestion-refinement.md"),
)

PACKAGE_PAYLOAD_FILES = REQUIRED_PAYLOAD_FILES + OPTIONAL_PAYLOAD_FILES

PLANNING_COMPATIBILITY_CONTRACT_FILES = (
    Path("AGENTS.template.md"),
    Path(".agentic-workspace/docs/execution-flow-contract.md"),
    Path(".agentic-workspace/docs/system-intent-contract.md"),
    Path(".agentic-workspace/docs/routing-contract.md"),
    Path(".agentic-workspace/docs/minimum-operating-model.md"),
    Path(".agentic-workspace/docs/lifecycle-and-config-contract.md"),
    Path(".agentic-workspace/docs/workspace-config-contract.md"),
    Path(".agentic-workspace/planning/execplans/README.md"),
    Path(".agentic-workspace/planning/execplans/TEMPLATE.plan.json"),
    Path(".agentic-workspace/planning/execplans/archive/README.md"),
    Path(".agentic-workspace/planning/decompositions/README.md"),
    Path(".agentic-workspace/planning/decompositions/TEMPLATE.decomposition.json"),
    EXECPLAN_RECORD_SCHEMA_PATH,
    DECOMPOSITION_RECORD_SCHEMA_PATH,
    REVIEW_RECORD_SCHEMA_PATH,
    EXTERNAL_INTENT_EVIDENCE_SCHEMA_PATH,
    FINISHED_WORK_EVIDENCE_SCHEMA_PATH,
    PLANNING_MANIFEST_PATH,
)

PLANNING_LOWER_STABILITY_HELPER_FILES = tuple(
    relative for relative in REQUIRED_PAYLOAD_FILES if relative not in PLANNING_COMPATIBILITY_CONTRACT_FILES
)

ROOT_SURFACE_FILES = (Path("AGENTS.template.md"),)

GENERATED_PAYLOAD_FILES = ()

PAYLOAD_GUIDANCE_FRAGMENTS = {
    Path(".agentic-workspace/planning/execplans/TEMPLATE.md"): (
        "concurrent edits merge cleanly",
        "do not add retrospective sections such as `Added In This Pass`",
        "Replace stale immediate-action text when the next step changes",
    ),
    Path(".agentic-workspace/planning/execplans/README.md"): (
        "Do not add sections such as `Added In This Pass`",
        "Treat active plan state as branch-local and low half-life",
    ),
}

TODO_EMPTY_STATE_LINE = "- No active work right now."
_COMPATIBILITY_VIEW_NOTICE = "<!-- GENERATED COMPATIBILITY VIEW: authoritative source is .agentic-workspace/planning/state.toml -->"
EXECPLAN_RECORD_KIND = "planning-execplan/v1"
REVIEW_RECORD_KIND = "planning-review/v1"
PLANNING_REFERENCE_KIND_DEFAULT = "artifact"
PLANNING_REFERENCE_ROLE_DEFAULT = "context"
PLANNING_REFERENCE_CLOSURE_ROLES = frozenset(
    {
        "closed_item",
        "closed",
        "implemented_item",
        "implemented",
        "delivered_item",
        "delivered",
        "completed_item",
        "completed",
        "source",
        "source_intent",
        "child",
        "closed_child",
    }
)
EXECPLAN_DURABLE_RESIDUE_STATUSES = frozenset(
    {
        "none",
        "memory",
        "docs",
        "contract",
        "check",
        "planning",
        "evidence_only",
    }
)
EXECPLAN_DURABLE_RESIDUE_OWNERLESS_STATUSES = frozenset({"none", "evidence_only"})
EXECPLAN_DURABLE_RESIDUE_OWNER_VALUES = frozenset({"none", "n/a", "archive", "archives", "evidence", "evidence-only"})
EXECPLAN_DURABLE_RESIDUE_RETENTION_VALUES = frozenset({"retain", "shrink", "stub", "delete"})
PLANNING_STATE_LIVE_ONLY_RULE = (
    "Planning state is live/selectable state only. Completed, dismissed, or historical work belongs in archived "
    "execplans, external evidence, or durable Memory/docs residue, not in state.toml."
)
EXECPLAN_CLOSEOUT_DISTILLATION_QUESTION = (
    "Before removing a completed execplan, ask what from it may be useful again: route future work to Planning, "
    "reusable technical context to Memory when installed, stable user-facing or operational guidance to docs, "
    "enforceable rules to config/checks/tests/contracts, external follow-up to issues, and discard one-off execution chronology."
)

PACKAGE_MANAGED_FILES = tuple(
    relative for relative in REQUIRED_PAYLOAD_FILES if relative not in ROOT_SURFACE_FILES and relative not in GENERATED_PAYLOAD_FILES
)

EXECPLAN_SECTION_ORDER: tuple[tuple[str, str, str], ...] = (
    ("Goal", "goal", "list"),
    ("Non-Goals", "non_goals", "list"),
    ("Intent Continuity", "intent_continuity", "dict"),
    ("Required Continuation", "required_continuation", "dict"),
    ("Iterative Follow-Through", "iterative_follow_through", "dict"),
    ("Intent Interpretation", "intent_interpretation", "dict"),
    ("Execution Bounds", "execution_bounds", "dict"),
    ("Stop Conditions", "stop_conditions", "dict"),
    ("Context Budget", "context_budget", "dict"),
    ("Delegated Judgment", "delegated_judgment", "dict"),
    ("Post-Decomposition Delegation", "post_decomposition_delegation", "dict"),
    ("Adaptive Assurance", "adaptive_assurance", "dict"),
    ("Traceability Refs", "traceability_refs", "dict"),
    ("Control Gates", "control_gates", "list"),
    ("Implementation Blockers", "implementation_blockers", "list"),
    ("Risk Registry Refs", "risk_registry_refs", "list"),
    ("Invariant Refs", "invariant_refs", "list"),
    ("Test Data Policy", "test_data_policy", "dict"),
    ("Layer Scaffold", "layer_scaffold", "dict"),
    ("Architecture Decision Promotion", "architecture_decision_promotion", "dict"),
    ("Threat Failure Aids", "threat_failure_aids", "list"),
    ("References", "references", "references"),
    ("Active Milestone", "active_milestone", "dict"),
    ("Immediate Next Action", "immediate_next_action", "list"),
    ("Blockers", "blockers", "list"),
    ("Touched Paths", "touched_paths", "list"),
    ("Invariants", "invariants", "list"),
    ("Contract Decisions To Freeze", "contract_decisions_to_freeze", "list"),
    ("Open Questions To Close", "open_questions_to_close", "list"),
    ("Validation Commands", "validation_commands", "list"),
    ("Required Tools", "required_tools", "list"),
    ("Completion Criteria", "completion_criteria", "list"),
    ("Execution Run", "execution_run", "dict"),
    ("Finished-Run Review", "finished_run_review", "dict"),
    ("Delegation Outcome Feedback", "delegation_outcome_feedback", "dict"),
    ("Proof Report", "proof_report", "dict"),
    ("Intent Satisfaction", "intent_satisfaction", "dict"),
    ("System Intent Alignment", "system_intent_alignment", "dict"),
    ("Closure Check", "closure_check", "dict"),
    ("Generated Closeout", "generated_closeout", "dict"),
    ("Durable Residue", "durable_residue", "dict"),
    ("Task Intent Promotion", "task_intent_promotion", "dict"),
    ("Execution Summary", "execution_summary", "dict"),
    ("Drift Log", "drift_log", "list"),
)

REVIEW_SECTION_ORDER: tuple[tuple[str, str, str], ...] = (
    ("Goal", "goal", "list"),
    ("Scope", "scope", "list"),
    ("Non-Goals", "non_goals", "list"),
    ("Review Mode", "review_mode", "dict"),
    ("Review Method", "review_method", "dict"),
    ("References", "references", "references"),
    ("Findings", "findings", "findings"),
    ("Recommendation", "recommendation", "dict"),
    ("Retention", "retention", "dict"),
    ("Validation / Inspection Commands", "validation_commands", "list"),
    ("Drift Log", "drift_log", "list"),
)


def skills_root() -> Path:
    packaged = Path(__file__).resolve().parent / "_skills"
    if packaged.exists():
        return packaged
    return Path(__file__).resolve().parents[2] / "skills"


def _add_contract_surface_summary(result: InstallResult, root: Path) -> None:
    def resolve_template(path: Path) -> str:
        name = path.name
        if name.endswith(".template.md"):
            return (path.parent / (name[:-12] + ".md")).as_posix()
        return path.as_posix()

    compatibility = ", ".join(resolve_template(path) for path in PLANNING_COMPATIBILITY_CONTRACT_FILES)
    helpers = ", ".join(resolve_template(path) for path in PLANNING_LOWER_STABILITY_HELPER_FILES)
    optional = ", ".join(path.as_posix() for path in OPTIONAL_PAYLOAD_FILES)
    result.add(
        "current",
        root / PLANNING_MANIFEST_PATH,
        f"default compatibility contract files: {compatibility}",
    )
    result.add(
        "current",
        root / PLANNING_MANIFEST_PATH,
        f"default lower-stability helper files: {helpers}",
    )
    result.add(
        "current",
        root / PLANNING_MANIFEST_PATH,
        f"optional packaged payload files: {optional}",
    )


@dataclass
class Action:
    kind: str
    path: Path
    detail: str


@dataclass
class InstallResult:
    target_root: Path
    message: str
    dry_run: bool
    bootstrap_version: str = __version__
    actions: list[Action] = field(default_factory=list)
    warnings: list[dict[str, str]] = field(default_factory=list)
    completion_options: list[dict[str, Any]] = field(default_factory=list)

    def add(self, kind: str, path: Path, detail: str) -> None:
        self.actions.append(Action(kind=kind, path=path, detail=detail))


def _planning_surface_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _planning_surface_relative(target_root: Path, path: Path) -> str:
    try:
        return path.relative_to(target_root).as_posix()
    except ValueError:
        return path.as_posix()


def _load_mutation_provenance(target_root: Path) -> dict[str, Any]:
    path = target_root / PLANNING_MUTATION_PROVENANCE_PATH
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        payload = {}
    if not isinstance(payload, dict) or payload.get("kind") != "planning-mutation-provenance/v1":
        return {"kind": "planning-mutation-provenance/v1", "entries": []}
    entries = payload.get("entries", [])
    if not isinstance(entries, list):
        payload["entries"] = []
    return payload


@contextmanager
def _mutation_provenance_file_lock(target_root: Path):
    lock_path = target_root / PLANNING_MUTATION_PROVENANCE_PATH.with_name(f"{PLANNING_MUTATION_PROVENANCE_PATH.name}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                age = time.time() - lock_path.stat().st_mtime
            except OSError:
                age = 0.0
            if age > PLANNING_MUTATION_PROVENANCE_LOCK_STALE_SECONDS:
                try:
                    lock_path.unlink()
                except OSError:
                    pass
                continue
            if time.monotonic() - start > PLANNING_MUTATION_PROVENANCE_LOCK_TIMEOUT_SECONDS:
                raise RuntimeError(f"Timed out waiting for planning mutation provenance lock: {lock_path}")
            time.sleep(0.05)
            continue
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(f"pid={os.getpid()}\ncreated_at={datetime.now(timezone.utc).isoformat()}\n")
            yield
        finally:
            try:
                lock_path.unlink()
            except OSError:
                pass
        return


def _write_mutation_provenance_payload(target_root: Path, payload: dict[str, Any]) -> Path:
    provenance_path = target_root / PLANNING_MUTATION_PROVENANCE_PATH
    provenance_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = provenance_path.with_name(f"{provenance_path.name}.{os.getpid()}.{id(payload)}.tmp")
    tmp_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(provenance_path)
    return provenance_path


def _record_planning_mutation_provenance(
    *,
    target_root: Path,
    paths: Iterable[Path],
    command: str,
    reason: str,
    mode: str = "cli-mutation",
) -> Path:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    new_entries: list[dict[str, str]] = []
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        relative = _planning_surface_relative(target_root, path)
        new_entries.append(
            {
                "path": relative,
                "sha256": _planning_surface_sha256(path),
                "command": command,
                "reason": reason,
                "mode": mode,
                "recorded_at": now,
            }
        )
    with _mutation_provenance_file_lock(target_root):
        existing = _load_mutation_provenance(target_root)
        entries = [entry for entry in existing.get("entries", []) if isinstance(entry, dict)]
        entries.extend(new_entries)
        payload = {"kind": "planning-mutation-provenance/v1", "entries": entries}
        return _write_mutation_provenance_payload(target_root, payload)


def _stamp_result_planning_mutations(
    result: InstallResult,
    *,
    paths: Iterable[Path],
    command: str,
    reason: str,
    mode: str = "cli-mutation",
) -> None:
    provenance_path = _record_planning_mutation_provenance(
        target_root=result.target_root,
        paths=paths,
        command=command,
        reason=reason,
        mode=mode,
    )
    result.add("updated", provenance_path, "recorded planning mutation provenance")


def _stamp_result_action_mutations(result: InstallResult, *, command: str, reason: str) -> None:
    mutation_kinds = {
        "created",
        "updated",
        "closed",
        "archived",
        "overwritten",
        "recovery recorded",
        "closeout distillation",
    }
    paths = [action.path for action in result.actions if action.kind in mutation_kinds and action.path.exists() and action.path.is_file()]
    if paths:
        _stamp_result_planning_mutations(result, paths=paths, command=command, reason=reason)


def _add_planning_mutation_proof_actions(result: InstallResult) -> None:
    result.add("proof", result.target_root, "agentic-planning summary --target . --format json")
    result.add("proof", result.target_root, "agentic-planning doctor --target . --modules planning --format json")


def _add_workspace_orchestrator_notice(result: InstallResult, *, preset: str = "planning") -> None:
    if (result.target_root / WORKSPACE_WORKFLOW_PATH).exists():
        return
    result.add(
        "warning",
        result.target_root / WORKSPACE_WORKFLOW_PATH,
        (
            "shared Workspace layer is not installed; ordinary host-repo lifecycle should run through "
            f"`agentic-workspace init --preset {preset}` or `agentic-workspace upgrade --modules planning`. "
            "Direct `agentic-planning` lifecycle commands are module-level maintenance/debugging surfaces and do not "
            "provide the full Workspace startup router, shared config, ownership, skills, or combined reports."
        ),
    )


@dataclass
class TodoItem:
    fields: dict[str, str]
    field_order: list[str]
    start: int
    end: int

    @property
    def item_id(self) -> str:
        return self.fields.get("id", "")


def payload_root() -> Path:
    packaged = Path(__file__).resolve().parent / "_payload"
    if packaged.exists():
        return packaged
    return Path(__file__).resolve().parents[2] / "bootstrap"


def _payload_schema(relative: Path) -> dict[str, Any]:
    return json.loads((payload_root() / relative).read_text(encoding="utf-8"))


def _json_schema_findings(*, payload: dict[str, Any], schema_path: Path) -> list[str]:
    schema = _payload_schema(schema_path)
    errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda error: list(error.path))
    findings: list[str] = []
    for error in errors:
        location = ".".join(str(part) for part in error.path) or "<root>"
        findings.append(f"{location}: {error.message}")
    return findings


def _write_schema_backed_planning_record(*, record_path: Path, record: dict[str, Any], schema_path: Path) -> None:
    findings = _json_schema_findings(payload=record, schema_path=schema_path)
    if findings:
        raise ValueError(f"planning record does not validate against {schema_path.name}: {'; '.join(findings)}")
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def planning_record_schema_findings(record_path: Path) -> list[str]:
    """Return JSON Schema validation findings for planning execplan/review records."""

    try:
        payload = json.loads(record_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"invalid JSON: {exc}"]
    if not isinstance(payload, dict):
        return ["planning record must be a JSON object"]
    kind = payload.get("kind")
    if kind == EXECPLAN_RECORD_KIND:
        return _json_schema_findings(payload=payload, schema_path=EXECPLAN_RECORD_SCHEMA_PATH)
    if kind == REVIEW_RECORD_KIND:
        return _json_schema_findings(payload=payload, schema_path=REVIEW_RECORD_SCHEMA_PATH)
    return [f"unsupported planning record kind: {kind!r}"]


def _evidence_schema_invalid_payload(
    *,
    relative_path: str,
    storage_class: str | None = None,
    kind: str,
    findings: list[str],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": "invalid",
        "path": relative_path,
        "kind": kind,
        "systems": [],
        "item_count": 0,
        "items": [],
        "reason": "optional evidence schema validation failed: " + "; ".join(findings),
        "schema_findings": findings,
    }
    if storage_class is not None:
        payload["storage"] = storage_class
    return payload


def _detect_payload_drift(target_root: Path) -> list[dict[str, str]]:
    """Detect differences between root source files and bootstrap payload mirror."""
    mirror_root = payload_root()
    # In a packaged installation, mirror_root will be '_payload' inside the site-packages.
    # We only report drift if we can find the development workspace root.
    dev_workspace_root = mirror_root.parents[2]
    if not (dev_workspace_root / "pyproject.toml").exists():
        return []

    # Only report drift if the target we are reporting on is the dev workspace itself.
    if target_root.resolve() != dev_workspace_root.resolve():
        return []

    drift = []
    managed_by_mirror = set(PACKAGE_PAYLOAD_FILES)

    # Check for missing or differing files in the mirror
    for relative in managed_by_mirror:
        if not (relative.parts[0] == "docs" or relative.name in {"AGENTS.template.md", "TODO.template.md", "ROADMAP.template.md"}):
            continue

        target_relative = relative
        if target_relative.name.endswith(".template.md"):
            target_relative = target_relative.with_name(target_relative.name[:-12] + ".md")

        source_path = dev_workspace_root / target_relative
        mirror_path = mirror_root / relative

        if not source_path.exists():
            # This is a different kind of error: required file missing from root
            continue

        if not mirror_path.exists():
            drift.append(
                {
                    "path": relative.as_posix(),
                    "message": f"Payload mirror missing: '{relative.as_posix()}' exists in root but not in bootstrap mirror.",
                    "warning_class": "payload_drift",
                }
            )
            continue

        if relative in ROOT_SURFACE_FILES:
            # Root surface files are generic templates in the mirror, but active state in the root.
            # They are expected to differ, so we only check existence, not content.
            continue

        if source_path.read_text(encoding="utf-8") != mirror_path.read_text(encoding="utf-8"):
            drift.append(
                {
                    "path": relative.as_posix(),
                    "message": f"Payload drift detected: '{relative.as_posix()}' in root differs from bootstrap mirror.",
                    "warning_class": "payload_drift",
                }
            )

    # Check for extra files in the mirror that aren't in REQUIRED_PAYLOAD_FILES
    for mirror_file in mirror_root.rglob("*"):
        if mirror_file.is_dir() or mirror_file.name == ".git":
            continue

        relative = mirror_file.relative_to(mirror_root)
        if relative not in managed_by_mirror and relative.parts[0] != "skills":
            # Ignore files that are legitimately bootstrap-only if they aren't docs/root surfaces
            if relative.parts[0] == "docs" or relative.name in {"AGENTS.template.md", "TODO.template.md", "ROADMAP.template.md"}:
                drift.append(
                    {
                        "path": relative.as_posix(),
                        "message": f"Extra payload file: '{relative.as_posix()}' exists in bootstrap mirror but is not in REQUIRED_PAYLOAD_FILES.",
                        "warning_class": "payload_drift",
                    }
                )

    return drift


def _bundled_skill_relative_paths() -> tuple[Path, ...]:
    root = skills_root()
    if not root.exists():
        return ()
    return tuple(
        path.relative_to(root)
        for path in sorted(root.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    )


PLANNING_BUNDLED_SKILL_FILES = tuple(PLANNING_SKILLS_MANAGED_ROOT / relative for relative in _bundled_skill_relative_paths())


def _installed_surface_files() -> tuple[Path, ...]:
    return REQUIRED_PAYLOAD_FILES


def resolve_target_root(target: str | Path | None, *, local_only: bool = False) -> Path:
    resolved = Path(target).resolve() if target else Path.cwd().resolve()
    if local_only:
        resolved = resolved / ".agentic-workspace" / "local-only"
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _canonical_execplan_record_path(plan_path: Path) -> Path:
    if plan_path.name.endswith(".plan.json"):
        return plan_path
    return plan_path.with_suffix(".plan.json")


def _derived_execplan_markdown_path(record_path: Path) -> Path:
    if record_path.name.endswith(".plan.json"):
        return record_path.with_name(record_path.name[: -len(".plan.json")] + ".md")
    return record_path.with_suffix(".md")


def _load_execplan_record(plan_path: Path) -> dict[str, Any] | None:
    record_path = _canonical_execplan_record_path(plan_path)
    if not record_path.exists():
        return None
    try:
        payload = json.loads(record_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("kind") != EXECPLAN_RECORD_KIND:
        return None
    return payload


def _record_section_dict(record: dict[str, Any] | None, key: str) -> dict[str, str] | None:
    if not isinstance(record, dict):
        return None
    raw = record.get(key)
    if not isinstance(raw, dict):
        return None
    return {str(field).strip().lower(): str(value).strip() for field, value in raw.items() if str(field).strip()}


def _record_section_list(record: dict[str, Any] | None, key: str) -> list[str] | None:
    if not isinstance(record, dict):
        return None
    raw = record.get(key)
    if not isinstance(raw, list):
        return None
    return [str(item).strip() for item in raw if str(item).strip()]


def _record_section_value(record: dict[str, Any] | None, key: str) -> Any | None:
    if not isinstance(record, dict) or key not in record:
        return None
    return copy.deepcopy(record[key])


def _normalize_reference_record(raw: Any) -> dict[str, str] | None:
    if not isinstance(raw, dict):
        return None
    target = str(raw.get("target", "")).strip()
    if not target:
        return None
    reference = {
        "kind": str(raw.get("kind", "")).strip() or PLANNING_REFERENCE_KIND_DEFAULT,
        "target": target,
        "label": str(raw.get("label", "")).strip(),
        "role": str(raw.get("role", "")).strip() or PLANNING_REFERENCE_ROLE_DEFAULT,
        "locator": str(raw.get("locator", "")).strip(),
    }
    return {key: value for key, value in reference.items() if value}


def _merge_references(*references_groups: list[dict[str, str]]) -> list[dict[str, str]]:
    merged: list[dict[str, str]] = []
    for group in references_groups:
        for item in group:
            normalized = _normalize_reference_record(item)
            if normalized is not None and normalized not in merged:
                merged.append(normalized)
    return merged


def _record_section_references(record: dict[str, Any] | None, key: str) -> list[dict[str, str]] | None:
    if not isinstance(record, dict):
        return None
    raw = record.get(key)
    if not isinstance(raw, list):
        return None
    references: list[dict[str, str]] = []
    for item in raw:
        reference = _normalize_reference_record(item)
        if reference is not None and reference not in references:
            references.append(reference)
    return references


def _roadmap_lane_references(lane: dict[str, Any]) -> list[dict[str, str]]:
    explicit = _record_section_references({"references": lane.get("references", [])}, "references") or []
    raw_issues = lane.get("issues", [])
    issue_values = raw_issues if isinstance(raw_issues, list) else [raw_issues]
    issue_refs = [
        {
            "kind": "issue",
            "target": issue,
            "role": "related-work",
        }
        for issue in issue_values
        if str(issue).strip()
    ]
    explicit_issue_tokens = {str(issue).strip() for issue in issue_values}
    refs_field_refs = [
        {
            "kind": "issue",
            "target": ref,
            "role": "related-work",
        }
        for ref in _planning_item_issue_refs(lane, text_fields=())
        if ref not in explicit_issue_tokens
    ]
    return _merge_references(explicit, issue_refs, refs_field_refs)


def _normalize_roadmap_lane_record(raw: dict[str, Any]) -> dict[str, Any]:
    lane = {str(key): value for key, value in raw.items()}
    lane["references"] = _roadmap_lane_references(lane)
    return lane


def _render_reference_line(reference: dict[str, str]) -> str:
    ordered_keys = ("kind", "target", "role", "label", "locator")
    return "- " + " | ".join(f"{key}: {reference[key]}" for key in ordered_keys if reference.get(key))


def _parse_reference_line(line: str) -> dict[str, str] | None:
    stripped = line.strip()
    if not stripped.startswith("- "):
        return None
    fields: dict[str, str] = {}
    for fragment in stripped[2:].split("|"):
        key, separator, value = fragment.partition(":")
        if not separator:
            continue
        normalized_key = key.strip().lower()
        if normalized_key not in {"kind", "target", "label", "role", "locator"}:
            continue
        normalized_value = value.strip()
        if normalized_value:
            fields[normalized_key] = normalized_value
    return _normalize_reference_record(fields)


def _extract_reference_section(path: Path, section_name: str) -> list[dict[str, str]]:
    references: list[dict[str, str]] = []
    for line in _section_lines(_read_lines(path), section_name):
        reference = _parse_reference_line(line)
        if reference is not None and reference not in references:
            references.append(reference)
    return references


def _render_execplan_markdown_from_record(record: dict[str, Any]) -> str:
    lines = [f"# {str(record.get('title', 'Plan Title')).strip() or 'Plan Title'}", ""]
    machine_contract = record.get("machine_readable_contract", {})
    if isinstance(machine_contract, dict):
        lines.extend(
            [
                "## Machine-Readable Contract",
                "",
                "```json",
                json.dumps(machine_contract, ensure_ascii=False, indent=2),
                "```",
                "",
            ]
        )
    for heading, key, value_kind in EXECPLAN_SECTION_ORDER:
        value = record.get(key)
        lines.extend([f"## {heading}", ""])
        if value_kind == "dict":
            if not isinstance(value, dict):
                continue
            for field, field_value in value.items():
                lines.append(f"- {str(field).strip().capitalize()}: {str(field_value).strip()}")
        elif value_kind == "references":
            if not isinstance(value, list):
                continue
            rendered_references = [_normalize_reference_record(item) for item in value]
            rendered_references = [item for item in rendered_references if item is not None]
            if not rendered_references:
                rendered_references = [{"kind": "artifact", "target": "none", "role": "context"}]
            for reference in rendered_references:
                lines.append(_render_reference_line(reference))
        else:
            if not isinstance(value, list):
                continue
            rendered_items = [str(item).strip() for item in value if str(item).strip()]
            if not rendered_items:
                rendered_items = ["None."]
            for item in rendered_items:
                lines.append(f"- {item}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _write_execplan_record(*, record_path: Path, record: dict[str, Any], render_markdown: bool = False) -> None:
    _write_schema_backed_planning_record(record_path=record_path, record=record, schema_path=EXECPLAN_RECORD_SCHEMA_PATH)
    if render_markdown:
        markdown_path = _derived_execplan_markdown_path(record_path)
        markdown_path.write_text(_render_execplan_markdown_from_record(record), encoding="utf-8")


def _canonical_review_record_path(review_path: Path) -> Path:
    if review_path.name.endswith(".review.json"):
        return review_path
    return review_path.with_suffix(".review.json")


def _derived_review_markdown_path(record_path: Path) -> Path:
    if record_path.name.endswith(".review.json"):
        return record_path.with_name(record_path.name[: -len(".review.json")] + ".md")
    return record_path.with_suffix(".md")


def _load_review_record(review_path: Path) -> dict[str, Any] | None:
    record_path = _canonical_review_record_path(review_path)
    if not record_path.exists():
        return None
    try:
        payload = json.loads(record_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("kind") != REVIEW_RECORD_KIND:
        return None
    return payload


def _resolve_review_path(target_root: Path, review: str) -> Path | None:
    candidate = Path(review)
    if candidate.is_absolute():
        return candidate
    if candidate.name.endswith(".review.json") and (target_root / candidate).exists():
        return (target_root / candidate).resolve()
    if candidate.suffix == ".md" and (target_root / candidate).exists():
        return (target_root / candidate).resolve()
    if candidate.name.endswith(".review.json"):
        direct_json = target_root / ".agentic-workspace" / "planning" / "reviews" / candidate.name
        if direct_json.exists():
            return direct_json.resolve()
    if candidate.suffix == ".md":
        direct_md = target_root / ".agentic-workspace" / "planning" / "reviews" / candidate.name
        if direct_md.exists():
            return direct_md.resolve()
        json_sibling = direct_md.with_suffix(".review.json")
        if json_sibling.exists():
            return json_sibling.resolve()
    normalized_json = review if review.endswith(".review.json") else f"{review}.review.json"
    direct_json = target_root / ".agentic-workspace" / "planning" / "reviews" / normalized_json
    if direct_json.exists():
        return direct_json.resolve()
    normalized_md = review if review.endswith(".md") else f"{review}.md"
    direct_md = target_root / ".agentic-workspace" / "planning" / "reviews" / normalized_md
    if direct_md.exists():
        return direct_md.resolve()
    return None


def _normalize_review_finding(raw: Any) -> dict[str, str] | None:
    if not isinstance(raw, dict):
        return None
    title = str(raw.get("title", "")).strip()
    if not title:
        return None
    finding = {
        "title": title,
        "summary": str(raw.get("summary", "")).strip(),
        "evidence": str(raw.get("evidence", "")).strip(),
        "risk if unchanged": str(raw.get("risk if unchanged", "")).strip(),
        "suggested action": str(raw.get("suggested action", "")).strip(),
        "confidence": str(raw.get("confidence", "")).strip(),
        "source": str(raw.get("source", "")).strip(),
        "promotion target": str(raw.get("promotion target", "")).strip(),
        "promotion trigger": str(raw.get("promotion trigger", "")).strip(),
        "post-remediation note shape": str(raw.get("post-remediation note shape", "")).strip(),
    }
    return {key: value for key, value in finding.items() if value}


def _normalize_review_retention(raw: Any) -> dict[str, str] | None:
    if not isinstance(raw, dict):
        return None
    retention = {
        "closeout shape": str(raw.get("closeout shape", "")).strip(),
        "trigger": str(raw.get("trigger", "")).strip(),
        "proof surface": str(raw.get("proof surface", "")).strip(),
    }
    normalized = {key: value for key, value in retention.items() if value}
    return normalized or None


def _derive_review_retention(*, findings: list[dict[str, str]], recommendation: dict[str, str]) -> dict[str, str]:
    shapes = [
        str(finding.get("post-remediation note shape", "")).strip().lower()
        for finding in findings
        if str(finding.get("post-remediation note shape", "")).strip()
    ]
    if any(shape == "retain" for shape in shapes):
        closeout_shape = "retain"
    elif any(shape == "shrink" for shape in shapes):
        closeout_shape = "shrink"
    elif any(shape == "stub" for shape in shapes):
        closeout_shape = "stub"
    elif shapes and all(shape == "delete" for shape in shapes):
        closeout_shape = "delete"
    else:
        closeout_shape = "shrink" if findings else "delete"

    defer = str(recommendation.get("defer", "")).strip()
    promote = str(recommendation.get("promote", "")).strip()
    dismiss = str(recommendation.get("dismiss", "")).strip()
    if defer and defer.lower() not in {"no", "none", "n/a"}:
        trigger = defer
    elif promote and promote.lower() not in {"no", "none", "n/a"}:
        trigger = "until promoted follow-on work or docs/memory residue carry the durable outcome"
    elif dismiss and dismiss.lower() not in {"no", "none", "n/a"}:
        trigger = "until dismissal is explicit and no live planning surface still depends on the review"
    else:
        trigger = "until follow-on routing or dismissal makes the live review artifact unnecessary"

    proof_surface = "canonical review record plus any referenced planning or proof artifacts"
    return {
        "closeout shape": closeout_shape,
        "trigger": trigger,
        "proof surface": proof_surface,
    }


def _render_review_markdown_from_record(record: dict[str, Any]) -> str:
    lines = [f"# {str(record.get('title', 'Review Title')).strip() or 'Review Title'}", ""]
    for heading, key, value_kind in REVIEW_SECTION_ORDER:
        value = record.get(key)
        lines.extend([f"## {heading}", ""])
        if value_kind == "dict":
            if not isinstance(value, dict):
                continue
            for field, field_value in value.items():
                if isinstance(field_value, list):
                    rendered_value = ", ".join(str(item).strip() for item in field_value if str(item).strip())
                else:
                    rendered_value = str(field_value).strip()
                lines.append(f"- {str(field).strip().capitalize()}: {rendered_value}")
        elif value_kind == "references":
            if not isinstance(value, list):
                continue
            rendered_references = [_normalize_reference_record(item) for item in value]
            rendered_references = [item for item in rendered_references if item is not None]
            if not rendered_references:
                rendered_references = [{"kind": "artifact", "target": "none", "role": "context"}]
            for reference in rendered_references:
                lines.append(_render_reference_line(reference))
        elif value_kind == "findings":
            if not isinstance(value, list):
                continue
            normalized_findings = [_normalize_review_finding(item) for item in value]
            normalized_findings = [item for item in normalized_findings if item is not None]
            if not normalized_findings:
                lines.append("- None.")
            for finding in normalized_findings:
                lines.extend([f"### Finding: {finding['title']}", ""])
                for field, field_value in finding.items():
                    if field == "title":
                        continue
                    lines.append(f"- {field.capitalize()}: {field_value}")
                lines.append("")
        else:
            if not isinstance(value, list):
                continue
            rendered_items = [str(item).strip() for item in value if str(item).strip()]
            if not rendered_items:
                rendered_items = ["None."]
            for item in rendered_items:
                lines.append(f"- {item}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _write_review_record(*, record_path: Path, record: dict[str, Any], render_markdown: bool = False) -> None:
    _write_schema_backed_planning_record(record_path=record_path, record=record, schema_path=REVIEW_RECORD_SCHEMA_PATH)
    if render_markdown:
        markdown_path = _derived_review_markdown_path(record_path)
        markdown_path.write_text(_render_review_markdown_from_record(record), encoding="utf-8")


def create_review_record(
    *,
    slug: str,
    title: str,
    target: str | Path | None = None,
    scope: str | None = None,
    classification: str = "review",
    dry_run: bool = False,
    render_markdown: bool = False,
) -> InstallResult:
    target_root = resolve_target_root(target)
    safe_slug = _safe_review_slug(slug)
    review_name = _review_record_filename(safe_slug)
    record_path = target_root / PLANNING_MANAGED_ROOT / "reviews" / review_name
    result = InstallResult(
        target_root=target_root, message=f"Create review record '{review_name[: -len('.review.json')]}'", dry_run=dry_run
    )
    if record_path.exists():
        result.add("manual review", record_path, "review record already exists; choose a new slug or edit intentionally")
        return result

    record = _new_review_record(title=title, scope=scope or safe_slug, classification=classification)
    if dry_run:
        result.add("would create", record_path, "valid planning-review/v1 record")
        return result

    _write_review_record(record_path=record_path, record=record, render_markdown=render_markdown)
    result.add("created", record_path, "valid planning-review/v1 record")
    provenance_paths = [record_path]
    if render_markdown:
        markdown_path = _derived_review_markdown_path(record_path)
        result.add("created", markdown_path, "derived review markdown")
        provenance_paths.append(markdown_path)
    _stamp_result_planning_mutations(
        result,
        paths=provenance_paths,
        command="agentic-planning create-review",
        reason=f"create review record {review_name}",
    )
    return result


def _safe_review_slug(slug: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", slug.strip().lower()).strip("-._")
    if not normalized:
        raise ValueError("review slug must contain at least one alphanumeric character")
    return normalized


def _review_record_filename(safe_slug: str, *, today: date | None = None) -> str:
    prefix = (today or date.today()).isoformat()
    if safe_slug.startswith(f"{prefix}-"):
        return f"{safe_slug}.review.json"
    return f"{prefix}-{safe_slug}.review.json"


def _new_review_record(*, title: str, scope: str, classification: str) -> dict[str, Any]:
    return {
        "kind": "planning-review/v1",
        "title": title.strip() or scope.replace("-", " ").title(),
        "date": date.today().isoformat(),
        "scope": [scope],
        "classification": classification,
        "goal": ["Record a bounded review in a valid machine-readable shape."],
        "non_goals": ["Do not use this generated skeleton as proof that review work is complete."],
        "review_mode": {
            "mode": classification,
            "review question": "Fill before closeout.",
            "default finding cap": "bounded",
            "inputs inspected first": "compact planning and task-specific surfaces",
        },
        "review_method": {
            "commands used": "Fill during review.",
            "evidence sources": "Fill during review.",
        },
        "references": [],
        "findings": [],
        "recommendation": {
            "promote": "pending",
            "defer": "pending",
            "dismiss": "pending",
        },
        "retention": {
            "closeout shape": "shrink",
            "trigger": "findings promoted, dismissed, or superseded",
            "proof surface": "routed issues, planning state, docs, checks, Memory, or a compact retained review stub",
        },
        "prose_templates": _default_prose_templates(),
        "validation_commands": [],
        "drift_log": [f"{date.today().isoformat()}: Review record created by create-review."],
    }


def _default_prose_templates() -> dict[str, dict[str, Any]]:
    return {
        "review_finding": {
            "sections": [
                "Finding",
                "Evidence",
                "Impact",
                "Recommendation",
                "Owner",
                "Status",
            ],
            "field_map": {
                "Finding": "findings[].title + findings[].summary",
                "Evidence": "findings[].evidence + findings[].source",
                "Impact": "findings[].risk if unchanged",
                "Recommendation": "findings[].suggested action + findings[].promotion target",
                "Owner": "findings[].promotion target",
                "Status": "recommendation/promote|defer|dismiss",
            },
            "rule": "Use only these headings when a prose finding is needed; keep the canonical fields structured.",
        },
        "handoff_or_closeout": {
            "sections": [
                "Intent",
                "What changed",
                "Proof",
                "Remaining risk",
                "Durable residue",
                "Next owner",
            ],
            "field_map": {
                "Intent": "intent/outcome or requested_outcome",
                "What changed": "execution_summary/outcome delivered",
                "Proof": "proof_report/validation proof",
                "Remaining risk": "finished_run_review/misinterpretation risk or follow-on decision",
                "Durable residue": "durable_residue + closeout_distillation",
                "Next owner": "execution_summary/follow-on routed to or required_continuation/owner surface",
            },
            "rule": "Prefer structured fields; use this shape only for short human-readable summaries.",
        },
    }


def _review_title(path: Path) -> str:
    record = _load_review_record(path)
    if isinstance(record, dict):
        title = str(record.get("title", "")).strip()
        if title:
            return title
    for line in _read_lines(path):
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("-", " ").title()


def _review_findings(path: Path) -> list[dict[str, str]]:
    record = _load_review_record(path)
    if isinstance(record, dict) and isinstance(record.get("findings"), list):
        findings = [_normalize_review_finding(item) for item in record.get("findings", [])]
        return [item for item in findings if item is not None]

    findings_section = _section_lines(_read_lines(path), "Findings")
    findings: list[dict[str, str]] = []
    current_title = ""
    current_lines: list[str] = []
    for line in findings_section:
        if line.startswith("### Finding:"):
            if current_title:
                finding = _extract_kv_fields(current_lines)
                finding["title"] = current_title
                normalized = _normalize_review_finding(finding)
                if normalized is not None:
                    findings.append(normalized)
            current_title = line.split(":", 1)[1].strip()
            current_lines = []
            continue
        if current_title:
            current_lines.append(line)
    if current_title:
        finding = _extract_kv_fields(current_lines)
        finding["title"] = current_title
        normalized = _normalize_review_finding(finding)
        if normalized is not None:
            findings.append(normalized)
    return findings


def _review_recommendation(path: Path) -> dict[str, str]:
    record = _load_review_record(path)
    if isinstance(record, dict) and isinstance(record.get("recommendation"), dict):
        return {
            str(key).strip(): str(value).strip()
            for key, value in record.get("recommendation", {}).items()
            if str(key).strip() and str(value).strip()
        }
    return _extract_kv_fields(_section_lines(_read_lines(path), "Recommendation"))


def _review_retention(path: Path) -> dict[str, str]:
    record = _load_review_record(path)
    if isinstance(record, dict):
        explicit = _normalize_review_retention(record.get("retention"))
        if explicit is not None:
            return explicit
    explicit = _normalize_review_retention(_extract_kv_fields(_section_lines(_read_lines(path), "Retention")))
    if explicit is not None:
        return explicit
    return _derive_review_retention(findings=_review_findings(path), recommendation=_review_recommendation(path))


def _review_references(references: list[dict[str, str]]) -> list[dict[str, str]]:
    review_references: list[dict[str, str]] = []
    for reference in references:
        if not isinstance(reference, dict):
            continue
        target = str(reference.get("target", "")).strip()
        if not target:
            continue
        kind = str(reference.get("kind", "")).strip().lower()
        if kind == "review" or ".agentic-workspace/planning/reviews/" in target or target.endswith(".review.json"):
            normalized = _normalize_reference_record(reference)
            if normalized is not None and normalized not in review_references:
                review_references.append(normalized)
    return review_references


def _review_residue_from_references(*, target_root: Path, references: list[dict[str, str]]) -> list[dict[str, Any]]:
    residue: list[dict[str, Any]] = []
    for reference in _review_references(references):
        target = str(reference.get("target", "")).strip()
        review_path = _resolve_review_path(target_root, target)
        if review_path is None or not review_path.exists():
            continue
        title = _review_title(review_path)
        findings = _review_findings(review_path)
        recommendation = _review_recommendation(review_path)
        retention = _review_retention(review_path)
        promotion_targets = _dedupe(
            [
                str(finding.get("promotion target", "")).strip()
                for finding in findings
                if str(finding.get("promotion target", "")).strip() and str(finding.get("promotion target", "")).strip().lower() != "none"
            ]
        )
        residue.append(
            {
                **reference,
                "target": review_path.relative_to(target_root).as_posix(),
                "title": title,
                "finding_count": len(findings),
                "finding_titles": [str(finding.get("title", "")).strip() for finding in findings if str(finding.get("title", "")).strip()],
                "promotion_targets": promotion_targets,
                "recommendation": recommendation,
                "retention": retention,
            }
        )
    return residue


def _build_review_record_from_markdown(review_path: Path) -> dict[str, Any]:
    lines = _read_lines(review_path)
    review_mode = _extract_kv_fields(_section_lines(lines, "Review Mode"))
    review_method = _extract_kv_fields(_section_lines(lines, "Review Method"))
    recommendation = _extract_kv_fields(_section_lines(lines, "Recommendation"))
    findings = _review_findings(review_path)
    return {
        "kind": REVIEW_RECORD_KIND,
        "title": _review_title(review_path),
        "goal": _extract_section_bullets(review_path, "Goal"),
        "scope": _extract_section_bullets(review_path, "Scope"),
        "non_goals": _extract_section_bullets(review_path, "Non-Goals"),
        "review_mode": review_mode,
        "review_method": review_method,
        "references": _extract_reference_section(review_path, "References"),
        "findings": findings,
        "recommendation": recommendation,
        "retention": _normalize_review_retention(_extract_kv_fields(_section_lines(lines, "Retention")))
        or _derive_review_retention(findings=findings, recommendation=recommendation),
        "validation_commands": _extract_section_bullets(review_path, "Validation / Inspection Commands"),
        "drift_log": _extract_section_bullets(review_path, "Drift Log"),
    }


def _backfill_review_records(target_root: Path) -> None:
    review_dir = target_root / ".agentic-workspace" / "planning" / "reviews"
    if not review_dir.exists():
        return
    for review_path in sorted(review_dir.glob("*.md")):
        if review_path.name in {"README.md", "TEMPLATE.md"}:
            continue
        record_path = _canonical_review_record_path(review_path)
        record = _load_review_record(review_path)
        if record is None:
            record = _build_review_record_from_markdown(review_path)
            _write_review_record(record_path=record_path, record=record)
        # Remove the derived .md now that a canonical .review.json exists
        if record_path.exists() and review_path.exists():
            review_path.unlink()


def _build_execplan_record_from_markdown(plan_path: Path) -> dict[str, Any]:
    lines = _read_lines(plan_path)
    title = plan_path.stem.replace("-", " ").title()
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            break
    return {
        "kind": EXECPLAN_RECORD_KIND,
        "title": title,
        "goal": _extract_section_bullets(plan_path, "Goal"),
        "non_goals": _extract_section_bullets(plan_path, "Non-Goals"),
        "intent_continuity": _extract_kv_fields(_section_lines(lines, "Intent Continuity")),
        "required_continuation": _extract_kv_fields(_section_lines(lines, "Required Continuation")),
        "iterative_follow_through": _extract_kv_fields(_section_lines(lines, "Iterative Follow-Through")),
        "intent_interpretation": _extract_kv_fields(_section_lines(lines, "Intent Interpretation")),
        "execution_bounds": _extract_kv_fields(_section_lines(lines, "Execution Bounds")),
        "stop_conditions": _extract_kv_fields(_section_lines(lines, "Stop Conditions")),
        "context_budget": _extract_kv_fields(_section_lines(lines, "Context Budget")),
        "delegated_judgment": _extract_kv_fields(_section_lines(lines, "Delegated Judgment")),
        "post_decomposition_delegation": _extract_kv_fields(_section_lines(lines, "Post-Decomposition Delegation")),
        "references": _extract_reference_section(plan_path, "References"),
        "capability_posture": _extract_kv_fields(_section_lines(lines, "Capability Posture")),
        "active_milestone": _extract_kv_fields(_section_lines(lines, "Active Milestone")),
        "immediate_next_action": _extract_section_bullets(plan_path, "Immediate Next Action"),
        "blockers": _extract_section_bullets(plan_path, "Blockers"),
        "touched_paths": _extract_section_bullets(plan_path, "Touched Paths"),
        "invariants": _extract_section_bullets(plan_path, "Invariants"),
        "contract_decisions_to_freeze": _extract_section_bullets(plan_path, "Contract Decisions To Freeze"),
        "open_questions_to_close": _extract_section_bullets(plan_path, "Open Questions To Close"),
        "validation_commands": _extract_section_bullets(plan_path, "Validation Commands"),
        "required_tools": _extract_section_bullets(plan_path, "Required Tools"),
        "completion_criteria": _extract_section_bullets(plan_path, "Completion Criteria"),
        "execution_run": _extract_kv_fields(_section_lines(lines, "Execution Run")),
        "finished_run_review": _extract_kv_fields(_section_lines(lines, "Finished-Run Review")),
        "delegation_outcome_feedback": _extract_kv_fields(_section_lines(lines, "Delegation Outcome Feedback")),
        "proof_report": _extract_kv_fields(_section_lines(lines, "Proof Report")),
        "intent_satisfaction": _extract_kv_fields(_section_lines(lines, "Intent Satisfaction")),
        "system_intent_alignment": _extract_kv_fields(_section_lines(lines, "System Intent Alignment")),
        "closure_check": _extract_kv_fields(_section_lines(lines, "Closure Check")),
        "durable_residue": _extract_kv_fields(_section_lines(lines, "Durable Residue")),
        "execution_summary": _extract_kv_fields(_section_lines(lines, "Execution Summary")),
        "drift_log": _extract_section_bullets(plan_path, "Drift Log"),
    }


def _backfill_execplan_records(target_root: Path) -> None:
    for execplan_dir in (
        target_root / ".agentic-workspace" / "planning" / "execplans",
        target_root / ".agentic-workspace" / "planning" / "execplans" / "archive",
    ):
        if not execplan_dir.exists():
            continue
        for plan_path in sorted(execplan_dir.glob("*.md")):
            if plan_path.name in {"README.md", "TEMPLATE.md"}:
                continue
            record_path = _canonical_execplan_record_path(plan_path)
            record = _load_execplan_record(plan_path)
            if record is None:
                record = _build_execplan_record_from_markdown(plan_path)
                _write_execplan_record(record_path=record_path, record=record)
            # Remove the derived .md now that a canonical .plan.json exists
            if record_path.exists() and plan_path.exists():
                plan_path.unlink()


def _cleanup_derived_markdown_views(target_root: Path) -> None:
    """Remove derived .md views where a canonical JSON record exists."""
    for execplan_dir in (
        target_root / ".agentic-workspace" / "planning" / "execplans",
        target_root / ".agentic-workspace" / "planning" / "execplans" / "archive",
    ):
        if not execplan_dir.exists():
            continue
        for md_path in sorted(execplan_dir.glob("*.md")):
            if md_path.name in {"README.md", "TEMPLATE.md"}:
                continue
            record_path = _canonical_execplan_record_path(md_path)
            if record_path.exists():
                md_path.unlink()
    review_dir = target_root / ".agentic-workspace" / "planning" / "reviews"
    if review_dir.exists():
        for md_path in sorted(review_dir.glob("*.md")):
            if md_path.name in {"README.md", "TEMPLATE.md"}:
                continue
            record_path = _canonical_review_record_path(md_path)
            if record_path.exists():
                md_path.unlink()


def list_payload_files() -> list[str]:
    root = payload_root()
    return [path.relative_to(root).as_posix() for path in sorted(root.rglob("*")) if _should_include_payload_path(path, root)]


def list_default_payload_files() -> list[str]:
    return [path.as_posix() for path in REQUIRED_PAYLOAD_FILES]


def list_optional_payload_files() -> list[str]:
    return [path.as_posix() for path in OPTIONAL_PAYLOAD_FILES]


def list_bundled_skill_files() -> list[str]:
    return [path.relative_to(PLANNING_SKILLS_MANAGED_ROOT).as_posix() for path in PLANNING_BUNDLED_SKILL_FILES]


def install_bootstrap(
    *,
    target: str | Path | None = None,
    dry_run: bool = False,
    force: bool = False,
    local_only: bool = False,
    include_optional: bool = False,
) -> InstallResult:
    target_root = resolve_target_root(target, local_only=local_only)
    result = InstallResult(target_root=target_root, message="Install plan", dry_run=dry_run)
    _add_workspace_orchestrator_notice(result)
    _copy_payload(target_root=target_root, result=result, conservative=False, force=force)
    _copy_bundled_skills(target_root=target_root, result=result, conservative=False, force=force)
    if include_optional:
        _copy_payload(target_root=target_root, result=result, conservative=False, force=force, files=OPTIONAL_PAYLOAD_FILES)
    _render_generated_agent_files(target_root=target_root, result=result, apply=not dry_run)
    if not dry_run:
        _ensure_state_toml_exists(target_root, overwrite=force)
        _remove_generated_planning_views(target_root, result=result)
        _backfill_execplan_records(target_root)
        _backfill_review_records(target_root)
        _cleanup_derived_markdown_views(target_root)
    if local_only and not dry_run:
        _ensure_local_ignored(target or Path.cwd())
    return result


def _ensure_local_ignored(repo_root: str | Path) -> None:
    gitignore = Path(repo_root) / ".gitignore"
    if not gitignore.exists():
        return
    text = gitignore.read_text(encoding="utf-8")
    if ".agentic-workspace/" not in text:
        with gitignore.open("a", encoding="utf-8") as f:
            f.write("\n# Agentic Workspace local-only storage\n.agentic-workspace/\n")


def adopt_bootstrap(*, target: str | Path | None = None, dry_run: bool = False, include_optional: bool = False) -> InstallResult:
    target_root = resolve_target_root(target)
    result = InstallResult(target_root=target_root, message="Adoption plan for existing repository", dry_run=dry_run)
    _add_workspace_orchestrator_notice(result)
    _copy_payload(target_root=target_root, result=result, conservative=True, force=False)
    _copy_bundled_skills(target_root=target_root, result=result, conservative=True, force=False)
    if include_optional:
        _copy_payload(target_root=target_root, result=result, conservative=True, force=False, files=OPTIONAL_PAYLOAD_FILES)
    _render_generated_agent_files(target_root=target_root, result=result, apply=not dry_run)
    if not dry_run:
        _ensure_state_toml_exists(target_root)
        _remove_generated_planning_views(target_root, result=result)
        _backfill_execplan_records(target_root)
        _backfill_review_records(target_root)
        _cleanup_derived_markdown_views(target_root)
    return result


def upgrade_bootstrap(*, target: str | Path | None = None, dry_run: bool = False, include_optional: bool = False) -> InstallResult:
    target_root = resolve_target_root(target)
    result = InstallResult(target_root=target_root, message="Upgrade plan", dry_run=dry_run)
    _add_workspace_orchestrator_notice(result)

    for relative in PACKAGE_MANAGED_FILES:
        _copy_payload_file(relative=relative, target_root=target_root, result=result, overwrite=True)

    _copy_bundled_skills(target_root=target_root, result=result, conservative=False, force=True)

    if include_optional:
        for relative in OPTIONAL_PAYLOAD_FILES:
            _copy_payload_file(relative=relative, target_root=target_root, result=result, overwrite=True)

    for relative in ROOT_SURFACE_FILES:
        _copy_payload_file(relative=relative, target_root=target_root, result=result, overwrite=False)

    _render_generated_agent_files(target_root=target_root, result=result, apply=not dry_run)
    if not dry_run:
        _ensure_state_toml_exists(target_root)
        _remove_generated_planning_views(target_root, result=result)
        _backfill_execplan_records(target_root)
        _backfill_review_records(target_root)
        _cleanup_derived_markdown_views(target_root)
    return result


def uninstall_bootstrap(*, target: str | Path | None = None, dry_run: bool = False) -> InstallResult:
    target_root = resolve_target_root(target)
    result = InstallResult(target_root=target_root, message="Uninstall plan", dry_run=dry_run)

    removable: list[Path] = []
    for relative in PACKAGE_PAYLOAD_FILES + PLANNING_BUNDLED_SKILL_FILES:
        target_relative = relative
        if target_relative.name.endswith(".template.md"):
            target_relative = target_relative.with_name(target_relative.name[:-12] + ".md")

        destination = target_root / target_relative
        if not destination.exists():
            result.add("skipped", destination, "already absent")
            continue
        if relative in PLANNING_BUNDLED_SKILL_FILES:
            removable_check = _remove_bundled_skill_file(relative=relative, target_root=target_root)
        else:
            removable_check = _can_remove_payload_file(relative=relative, target_root=target_root)
        if removable_check:
            removable.append(target_relative)
            result.add("would remove" if dry_run else "removed", destination, "matches managed payload content")
            continue
        result.add("manual review", destination, "local file differs from managed payload; remove manually if intended")

    if dry_run:
        return result

    for relative in removable:
        destination = target_root / relative
        if destination.exists():
            destination.unlink()

    _prune_empty_parent_dirs(target_root=target_root, relatives=removable)
    return result


def collect_status(*, target: str | Path | None = None) -> InstallResult:
    target_root = resolve_target_root(target)
    mode = _detect_adoption_mode(target_root)
    result = InstallResult(target_root=target_root, message=f"Status report ({mode} mode)", dry_run=False)
    _add_workspace_orchestrator_notice(result)
    result.add("mode", target_root, f"detected adoption mode: {mode}")
    for relative in _installed_surface_files():
        name = relative.name
        if name.endswith(".template.md"):
            installed_relative = relative.parent / (name[:-12] + ".md")
        else:
            installed_relative = relative
        destination = target_root / installed_relative
        detail = "file exists" if destination.exists() else "file missing"
        result.add("present" if destination.exists() else "missing", destination, detail)
    return result


def doctor_bootstrap(*, target: str | Path | None = None) -> InstallResult:
    target_root = resolve_target_root(target)
    result = InstallResult(target_root=target_root, message="Doctor report", dry_run=True)
    _add_workspace_orchestrator_notice(result)
    result.add("mode", target_root, f"detected adoption mode: {_detect_adoption_mode(target_root)}")
    upgrade_source = resolve_upgrade_source(target_root)
    source_detail = f"{upgrade_source.source_label}: {upgrade_source.source_ref}"
    result.add("source", target_root / UPGRADE_SOURCE_PATH, source_detail)
    source_age = upgrade_source.age_days()
    if source_age is not None:
        result.add("source age", target_root / UPGRADE_SOURCE_PATH, f"{source_age} days since {upgrade_source.recorded_at}")
        if source_age > upgrade_source.recommended_upgrade_after_days:
            result.warnings.append(
                {
                    "warning_class": "upgrade_source_stale",
                    "path": UPGRADE_SOURCE_PATH.as_posix(),
                    "message": (
                        f"Recorded upgrade source is {source_age} days old; consider refreshing from "
                        f"{upgrade_source.source_label} when it is safe."
                    ),
                }
            )

    for relative in _installed_surface_files():
        name = relative.name
        if name.endswith(".template.md"):
            installed_relative = relative.parent / (name[:-12] + ".md")
        else:
            installed_relative = relative
        destination = target_root / installed_relative
        detail = "required file present" if destination.exists() else "required file missing"
        result.add("current" if destination.exists() else "manual review", destination, detail)

    _add_contract_surface_summary(result, target_root)

    for relative in (Path("AGENTS.md"), PLANNING_STATE_PATH):
        path = target_root / relative
        if path.exists():
            text = path.read_text(encoding="utf-8")
            if _has_unresolved_placeholders(text):
                result.add("manual review", path, "starter placeholders still need custom values")

    warnings = _run_planning_checker(target_root)
    result.warnings.extend(warnings)
    for warning in warnings:
        result.add("warning", target_root / warning["path"], warning["message"])
        remediation = _warning_remediation(warning["warning_class"])
        if remediation:
            result.add("suggested fix", target_root / warning["path"], remediation)

    for relative, rendered, label in _generated_agent_file_expectations(target_root):
        destination = target_root / relative
        if destination.exists() and destination.read_text(encoding="utf-8") != rendered:
            result.add(
                "manual review",
                destination,
                f"{label} is out of sync with .agentic-workspace/planning/agent-manifest.json; run agentic-workspace doctor --target ./repo --modules planning --format json",
            )
    return result


def verify_payload() -> InstallResult:
    root = payload_root()
    result = InstallResult(target_root=root, message="Payload verification", dry_run=False)
    payload_files = {Path(item) for item in list_payload_files()}
    for relative in PACKAGE_PAYLOAD_FILES:
        target_relative = relative
        if target_relative.name.endswith(".template.md"):
            target_relative = target_relative.with_name(target_relative.name[:-12] + ".md")

        prefix = "default" if relative in REQUIRED_PAYLOAD_FILES else "optional"
        detail = f"{prefix} payload file present" if relative in payload_files else f"{prefix} payload file missing"
        result.add("current" if relative in payload_files else "manual review", root / target_relative, detail)

    _add_contract_surface_summary(result, root)

    for relative, fragments in PAYLOAD_GUIDANCE_FRAGMENTS.items():
        destination = root / relative
        if not destination.exists():
            continue
        text = destination.read_text(encoding="utf-8")
        missing = [fragment for fragment in fragments if fragment not in text]
        if missing:
            result.add(
                "manual review",
                destination,
                "payload guidance is missing collaboration-safe template wording",
            )
        else:
            result.add("current", destination, "payload guidance includes collaboration-safe template wording")

    for relative, rendered, label in _generated_agent_file_expectations(root):
        destination = root / relative
        if not destination.exists():
            continue
        current = destination.read_text(encoding="utf-8") == rendered
        detail = f"{label} matches manifest" if current else f"{label} does not match manifest"
        result.add("current" if current else "manual review", destination, detail)
    return result


def planning_summary(
    *,
    target: str | Path | None = None,
    profile: str = "full",
    task_text: str | None = None,
    changed_paths: list[str] | None = None,
) -> dict[str, Any]:
    target_root = resolve_target_root(target)
    if profile == "tiny" and not task_text and not changed_paths:
        return _planning_summary_tiny_fast(target_root=target_root)
    todo_path = target_root / "TODO.md"
    legacy_todo_path = target_root / PLANNING_STATE_PATH
    roadmap_path = target_root / "ROADMAP.md"
    execplan_dir = target_root / ".agentic-workspace" / "planning" / "execplans"
    decomposition_dir = target_root / ".agentic-workspace" / "planning" / "decompositions"

    state = _read_state_from_toml(target_root)
    if state:
        active_items = _state_active_items(state)
        queued_items = _state_queued_items(state)
        roadmap_lanes = _state_roadmap_lanes(state)
        roadmap_candidates = _state_roadmap_candidates(state)
        todo_line_count = 0  # We don't have a direct line count for the TOML state
        todo_item_count = len(active_items) + len(queued_items)
    else:
        legacy_todo_lines, legacy_todo_items = _read_todo_items(legacy_todo_path)
        if legacy_todo_items:
            todo_lines, todo_items = legacy_todo_lines, legacy_todo_items
        else:
            todo_lines, todo_items = _read_todo_items(todo_path)
        active_items = []
        queued_items = []
        for item in todo_items:
            status = item.fields.get("status", "").lower()
            if "in-progress" in status or "active" in status or "ongoing" in status:
                active_items.append(
                    {
                        "id": item.fields.get("id", ""),
                        "surface": item.fields.get("surface", ""),
                        "why_now": item.fields.get("why now", ""),
                    }
                )
                continue
            if status not in {"completed", "done", "closed"}:
                queued_items.append(
                    {
                        "id": item.fields.get("id", ""),
                        "surface": item.fields.get("surface", ""),
                        "why_now": item.fields.get("why now", ""),
                        "status": item.fields.get("status", ""),
                    }
                )
        roadmap_lanes = _roadmap_candidate_lanes(roadmap_path)
        roadmap_candidates = _roadmap_candidates(roadmap_path)
        todo_line_count = len(todo_lines)
        todo_item_count = len(todo_items)

    ownership_review = _ownership_review(target_root)
    decomposition_projection = _planning_decomposition_projection(target_root=target_root, decomposition_dir=decomposition_dir)

    active_execplans: list[dict[str, str]] = []
    completed_execplans: list[dict[str, Any]] = []
    archived_execplans = 0
    plan_files: list[Path] = []
    if execplan_dir.exists():
        # Collect unique execplan stems, preferring .plan.json over .md
        seen_stems: set[str] = set()
        for path in sorted(execplan_dir.glob("*.plan.json")):
            if path.name == "TEMPLATE.plan.json":
                continue
            stem = path.name[: -len(".plan.json")]
            seen_stems.add(stem)
            plan_files.append(path)
        for path in sorted(execplan_dir.glob("*.md")):
            if path.name in {"README.md", "TEMPLATE.md"}:
                continue
            if path.stem not in seen_stems:
                plan_files.append(path)
        for path in sorted(plan_files):
            status = _execplan_status(path)
            if status and status not in {"completed", "done", "closed", "planned", "pending", "not-started"}:
                active_execplans.append({"path": path.relative_to(target_root).as_posix(), "status": status})
            elif status in {"completed", "done", "closed"}:
                completed_execplans.append(
                    {
                        "path": path.relative_to(target_root).as_posix(),
                        "status": status,
                        "proof_report": _execplan_proof_report(path),
                        "intent_satisfaction": _execplan_intent_satisfaction(path),
                        "closure_check": _execplan_closure_check(path),
                    }
                )
        archive_dir = execplan_dir / "archive"
        if archive_dir.exists():
            archived_md = sum(1 for path in archive_dir.glob("*.md") if path.is_file() and path.name not in {"README.md", "TEMPLATE.md"})
            archived_json = sum(1 for path in archive_dir.glob("*.plan.json") if path.is_file())
            archived_execplans = max(archived_md, archived_json)

    state = _read_state_from_toml(target_root)
    warnings = _run_planning_checker(target_root)
    warnings.extend(_unsupported_planning_state_activation_shape_warnings(target_root=target_root, state=state))
    warnings.extend(_planning_state_v1_warnings(target_root=target_root, state=state))
    warnings.extend(_completed_execplan_warnings(completed_execplans))
    warnings.extend(
        _unregistered_execplan_warnings(
            target_root=target_root,
            state=state,
            plan_files=plan_files,
            active_items=active_items,
            queued_items=queued_items,
            roadmap_lanes=roadmap_lanes,
            roadmap_candidates=roadmap_candidates,
        )
    )
    warnings.extend(_execplan_next_action_warnings(target_root=target_root, plan_files=plan_files))
    warnings.extend(_execplan_mode_residue_warnings(target_root=target_root, plan_files=plan_files))
    drift = _detect_payload_drift(target_root)
    warnings.extend(drift)

    active_contract = _active_intent_contract(
        target_root=target_root,
        active_items=active_items,
        active_execplans=active_execplans,
    )
    resumable_contract = _active_resumable_contract(
        target_root=target_root,
        active_contract=active_contract,
        active_execplans=active_execplans,
    )
    planning_record = _canonical_planning_record(
        target_root=target_root,
        active_contract=active_contract,
        resumable_contract=resumable_contract,
    )
    warnings.extend(_prep_only_changed_path_warnings(target_root=target_root, planning_record=planning_record))
    planning_collaboration_pressure = _planning_collaboration_pressure(
        target_root=target_root,
        active_items=active_items,
        queued_items=queued_items,
        active_execplans=active_execplans,
        state=state,
    )
    planning_surface_health = _planning_surface_health(warnings, collaboration_pressure=planning_collaboration_pressure)
    follow_through_contract = _active_follow_through_contract(
        target_root=target_root,
        planning_record=planning_record,
        active_execplans=active_execplans,
    )
    intent_interpretation_contract = _active_intent_interpretation_contract(
        target_root=target_root,
        planning_record=planning_record,
        active_execplans=active_execplans,
    )
    context_budget_contract = _active_context_budget_contract(
        target_root=target_root,
        planning_record=planning_record,
        active_execplans=active_execplans,
    )
    execution_run_contract = _active_execution_run_contract(
        target_root=target_root,
        planning_record=planning_record,
        active_execplans=active_execplans,
    )
    finished_run_review_contract = _active_finished_run_review_contract(
        target_root=target_root,
        planning_record=planning_record,
        active_execplans=active_execplans,
        execution_run_contract=execution_run_contract,
        intent_interpretation_contract=intent_interpretation_contract,
    )
    closeout_distillation_contract = _active_closeout_distillation_contract(
        target_root=target_root,
        planning_record=planning_record,
        active_execplans=active_execplans,
    )
    intent_validation_contract = _intent_validation_contract(
        target_root=target_root,
        active_items=active_items,
        active_execplans=active_execplans,
        roadmap_lanes=roadmap_lanes,
    )
    finished_work_inspection_contract = _finished_work_inspection_contract(target_root=target_root)
    work_maturity = _planning_work_maturity_projection(state=state, active_execplans=active_execplans)
    execution_readiness = _execution_readiness_payload(
        active_items=active_items,
        active_execplans=active_execplans,
        roadmap_lanes=roadmap_lanes,
        roadmap_candidates=roadmap_candidates,
        intent_validation=intent_validation_contract,
        finished_work_inspection=finished_work_inspection_contract,
    )
    hierarchy_contract = _active_hierarchy_contract(
        target_root=target_root,
        planning_record=planning_record,
        active_contract=active_contract,
        resumable_contract=resumable_contract,
        follow_through_contract=follow_through_contract,
        context_budget_contract=context_budget_contract,
        roadmap_lanes=roadmap_lanes,
        active_execplans=active_execplans,
    )
    handoff_contract = _active_handoff_contract(
        planning_record=planning_record,
        hierarchy_contract=hierarchy_contract,
        context_budget_contract=context_budget_contract,
        intent_interpretation_contract=intent_interpretation_contract,
    )
    full_summary = {
        "kind": "planning-summary/v1",
        "profile": "full",
        "schema": _planning_summary_schema(),
        "target_root": str(target_root),
        "adoption_mode": _detect_adoption_mode(target_root),
        "todo": {
            "line_count": todo_line_count,
            "item_count": todo_item_count,
            "active_count": len(active_items),
            "active_items": active_items,
            "queued_count": len(queued_items),
            "queued_items": queued_items,
        },
        "execplans": {
            "active_count": len(active_execplans),
            "active_execplans": active_execplans,
            "completed_count": len(completed_execplans),
            "completed_execplans": completed_execplans,
            "archived_count": archived_execplans,
        },
        "machine_first_planning": _machine_first_planning_payload(active_execplans=active_execplans),
        "decomposition": decomposition_projection,
        "work_maturity": work_maturity,
        "execution_readiness": execution_readiness,
        "autopilot_loop": _autopilot_loop_status(
            execution_readiness=execution_readiness,
            planning_record=planning_record,
            planning_surface_health=planning_surface_health,
            finished_work_inspection=finished_work_inspection_contract,
            roadmap_lanes=roadmap_lanes,
            roadmap_candidates=roadmap_candidates,
        ),
        "planning_record": planning_record,
        "active_contract": _contract_projection(active_contract, view_name="active_contract"),
        "resumable_contract": _contract_projection(resumable_contract, view_name="resumable_contract"),
        "follow_through_contract": _contract_projection(follow_through_contract, view_name="follow_through_contract"),
        "intent_interpretation_contract": _contract_projection(
            intent_interpretation_contract,
            view_name="intent_interpretation_contract",
        ),
        "context_budget_contract": _contract_projection(context_budget_contract, view_name="context_budget_contract"),
        "execution_run_contract": _contract_projection(execution_run_contract, view_name="execution_run_contract"),
        "finished_run_review_contract": _contract_projection(
            finished_run_review_contract,
            view_name="finished_run_review_contract",
        ),
        "closeout_distillation_contract": _contract_projection(
            closeout_distillation_contract,
            view_name="closeout_distillation_contract",
        ),
        "intent_validation_contract": _contract_projection(
            intent_validation_contract,
            view_name="intent_validation_contract",
        ),
        "finished_work_inspection_contract": _contract_projection(
            finished_work_inspection_contract,
            view_name="finished_work_inspection_contract",
        ),
        "hierarchy_contract": _contract_projection(hierarchy_contract, view_name="hierarchy_contract"),
        "handoff_contract": _contract_projection(handoff_contract, view_name="handoff_contract"),
        "system_intent": _system_intent_contract_payload(),
        "roadmap": {
            "lane_count": len(roadmap_lanes),
            "candidate_lanes": roadmap_lanes,
            "candidate_count": len(roadmap_candidates),
            "candidates": roadmap_candidates,
        },
        "ownership_review": ownership_review,
        "planning_surface_health": planning_surface_health,
        "warnings": [warning.copy() for warning in warnings],
        "warning_count": len(warnings),
    }
    if profile in {"tiny", "compact"}:
        compact_summary = _planning_summary_compact_projection(full_summary)
        if task_text or changed_paths:
            return _planning_summary_task_scoped_projection(
                compact_summary,
                task_text=task_text,
                changed_paths=changed_paths or [],
            )
        if profile == "tiny":
            return _planning_summary_tiny_projection(compact_summary)
        return compact_summary
    if profile != "full":
        raise ValueError(f"Unsupported planning summary profile: {profile}")
    return full_summary


def planning_report(*, target: str | Path | None = None) -> dict[str, Any]:
    summary = planning_summary(target=target)
    planning_record = summary.get("planning_record", {})
    completed_execplans = list(summary.get("execplans", {}).get("completed_execplans", []))
    active_contract = summary.get("active_contract", {})
    resumable_contract = summary.get("resumable_contract", {})
    follow_through_contract = summary.get("follow_through_contract", {})
    intent_interpretation_contract = summary.get("intent_interpretation_contract", {})
    context_budget_contract = summary.get("context_budget_contract", {})
    execution_run_contract = summary.get("execution_run_contract", {})
    finished_run_review_contract = summary.get("finished_run_review_contract", {})
    closeout_distillation_contract = summary.get("closeout_distillation_contract", {})
    intent_validation_contract = summary.get("intent_validation_contract", {})
    finished_work_inspection_contract = summary.get("finished_work_inspection_contract", {})
    hierarchy_contract = summary.get("hierarchy_contract", {})
    handoff_contract = summary.get("handoff_contract", {})
    work_maturity = summary.get("work_maturity", {})
    warnings = list(summary.get("warnings", []))
    findings = [
        {
            "severity": "warning",
            "path": warning.get("path"),
            "message": warning.get("message", ""),
            "warning_class": warning.get("warning_class", ""),
        }
        for warning in warnings
    ]
    validation_signals = intent_validation_contract.get("signals", [])
    if isinstance(validation_signals, list):
        for signal in validation_signals:
            if not isinstance(signal, dict):
                continue
            findings.append(
                {
                    "severity": str(signal.get("severity", "warning")),
                    "path": str(signal.get("path", "")) or None,
                    "message": str(signal.get("message", "")),
                    "warning_class": str(signal.get("kind", "")),
                }
            )
    inspection_signals = finished_work_inspection_contract.get("signals", [])
    if isinstance(inspection_signals, list):
        for signal in inspection_signals:
            if not isinstance(signal, dict):
                continue
            findings.append(
                {
                    "severity": str(signal.get("severity", "warning")),
                    "path": str(signal.get("path", "")) or None,
                    "message": str(signal.get("message", "")),
                    "warning_class": str(signal.get("kind", "")),
                }
            )
    if finished_run_review_contract.get("status") == "present" and finished_run_review_contract.get("config_trust") == "lower-trust":
        findings.append(
            {
                "severity": "warning",
                "path": planning_record.get("task", {}).get("surface") or None,
                "message": str(
                    finished_run_review_contract.get(
                        "recommended_next_action",
                        "Config compliance is ambiguous or bypassed; treat this closeout as lower trust until the config gap is made explicit.",
                    )
                ),
                "warning_class": "config_compliance_lower_trust",
            }
        )
    next_action = "No active planning work right now."
    commands: list[str] = []
    if planning_record.get("status") == "present":
        next_action = str(planning_record.get("next_action", next_action))
    elif finished_work_inspection_contract.get("status") == "present" and finished_work_inspection_contract.get("counts", {}).get(
        "attention_count", 0
    ):
        next_action = str(
            finished_work_inspection_contract.get(
                "recommended_next_action",
                "Inspect finished-work signals before treating previously closed work as settled.",
            )
        )
        commands.append("Inspect the finished_work_inspection contract in agentic-planning report --format json")
    elif intent_validation_contract.get("status") == "present" and intent_validation_contract.get("counts", {}).get("attention_count", 0):
        next_action = str(
            intent_validation_contract.get("recommended_next_action", "Review intent-validation signals before treating planning as quiet.")
        )
        commands.append("Inspect the intent_validation contract in agentic-planning report --format json")
    elif summary["todo"]["active_count"]:
        first_item = summary["todo"]["active_items"][0]
        next_action = f"Continue active TODO item {first_item.get('id', '')}: {first_item.get('surface', '')}".strip(": ")
    elif isinstance(work_maturity, dict) and work_maturity.get("ready_slices"):
        first_ready = work_maturity["ready_slices"][0]
        next_action = f"Promote ready slice {first_ready.get('id', '')} from explicit maturity state.".strip()
        commands.append("Inspect work_maturity in agentic-planning report --format json")
    elif summary["roadmap"]["candidate_count"]:
        next_action = "Promote the highest-priority roadmap candidate when the next bounded slice is ready."
        commands.append("Inspect roadmap lanes in .agentic-workspace/planning/state.toml")

    health = "healthy"
    if summary["warning_count"] or any(finding.get("warning_class") == "config_compliance_lower_trust" for finding in findings):
        health = "attention-needed"
    elif summary["todo"]["active_count"] or summary["execplans"]["active_count"]:
        health = "active"

    return {
        "kind": "planning-module-report/v1",
        "schema": {
            "schema_version": "module-report-schema/v1",
            "module": "planning",
            "command": "agentic-planning report --format json",
            "canonical_docs": [
                ".agentic-workspace/docs/reporting-contract.md",
                ".agentic-workspace/docs/system-intent-contract.md",
                ".agentic-workspace/docs/context-budget-contract.md",
                ".agentic-workspace/docs/external-intent-evidence-contract.md",
                "packages/planning/README.md",
            ],
            "shared_fields": [
                "kind",
                "schema",
                "module",
                "target_root",
                "health",
                "status",
                "completed_execplans",
                "ownership_review",
                "work_maturity",
                "writer_helpers",
                "active",
                "system_intent",
                "closeout_distillation",
                "intent_validation",
                "finished_work_inspection",
                "findings",
                "next_action",
            ],
        },
        "module": "planning",
        "target_root": summary["target_root"],
        "health": health,
        "status": {
            "adoption_mode": summary["adoption_mode"],
            "active_todo_count": summary["todo"]["active_count"],
            "queued_todo_count": summary["todo"].get("queued_count", 0),
            "todo_item_count": summary["todo"]["item_count"],
            "active_execplan_count": summary["execplans"]["active_count"],
            "completed_execplan_count": summary["execplans"].get("completed_count", 0),
            "roadmap_lane_count": summary["roadmap"].get("lane_count", 0),
            "roadmap_candidate_count": summary["roadmap"]["candidate_count"],
            "ready_slice_count": work_maturity.get("counts", {}).get("ready_slices", 0) if isinstance(work_maturity, dict) else 0,
            "blocked_item_count": work_maturity.get("counts", {}).get("blocked_items", 0) if isinstance(work_maturity, dict) else 0,
            "residue_routing_needed_count": work_maturity.get("counts", {}).get("residue_routing_needed", 0)
            if isinstance(work_maturity, dict)
            else 0,
            "intent_validation_attention_count": intent_validation_contract.get("counts", {}).get("attention_count", 0),
            "finished_work_inspection_attention_count": finished_work_inspection_contract.get("counts", {}).get("attention_count", 0),
            "warning_count": summary["warning_count"],
        },
        "completed_execplans": completed_execplans,
        "ownership_review": summary.get("ownership_review", {}),
        "work_maturity": work_maturity,
        "writer_helpers": {
            "status": "available",
            "rule": "Use planning writer helpers before hand-authoring schema-backed planning records.",
            "helpers": [
                {
                    "artifact": "execplan",
                    "command": "agentic-planning promote-to-plan <todo-or-roadmap-id> --target ./repo --format json",
                    "writes": [
                        ".agentic-workspace/planning/state.toml",
                        ".agentic-workspace/planning/execplans/<slug>.plan.json",
                    ],
                    "proof": "agentic-planning doctor --target ./repo --format json",
                },
                {
                    "artifact": "review_record",
                    "command": "agentic-planning create-review <slug> --title <title> --target ./repo --format json",
                    "writes": [
                        ".agentic-workspace/planning/reviews/<slug>.review.json",
                    ],
                    "proof": "agentic-planning doctor --target ./repo --format json",
                },
            ],
        },
        "active": {
            "planning_record": planning_record,
            "active_contract": active_contract,
            "resumable_contract": resumable_contract,
            "follow_through_contract": follow_through_contract,
            "intent_interpretation_contract": intent_interpretation_contract,
            "context_budget_contract": context_budget_contract,
            "execution_run_contract": execution_run_contract,
            "finished_run_review_contract": finished_run_review_contract,
            "closeout_distillation_contract": closeout_distillation_contract,
            "hierarchy_contract": hierarchy_contract,
            "handoff_contract": handoff_contract,
        },
        "system_intent": summary.get("system_intent", {}),
        "closeout_distillation": closeout_distillation_contract,
        "intent_validation": intent_validation_contract,
        "finished_work_inspection": finished_work_inspection_contract,
        "findings": findings,
        "next_action": {
            "summary": next_action,
            "commands": commands,
        },
    }


def planning_report_tiny(*, target: str | Path | None = None) -> dict[str, Any]:
    summary = planning_summary(target=target, profile="tiny")
    todo = summary.get("todo", {}) if isinstance(summary.get("todo"), dict) else {}
    execplans = summary.get("execplans", {}) if isinstance(summary.get("execplans"), dict) else {}
    health_payload = summary.get("planning_surface_health", {}) if isinstance(summary.get("planning_surface_health"), dict) else {}
    warning_count = int(summary.get("warning_count", 0) or 0)
    health = "attention-needed" if warning_count else ("active" if todo.get("active_count") or execplans.get("active_count") else "healthy")
    next_summary = str(health_payload.get("recommended_next_action") or "No active planning work right now.")
    return {
        "kind": "planning-module-report/v1",
        "profile": "tiny",
        "module": "planning",
        "target_root": summary.get("target_root", ""),
        "health": health,
        "status": {
            "active_todo_count": todo.get("active_count", 0),
            "queued_todo_count": todo.get("queued_count", 0),
            "active_execplan_count": execplans.get("active_count", 0),
            "roadmap_lane_count": summary.get("roadmap", {}).get("lane_count", 0) if isinstance(summary.get("roadmap"), dict) else 0,
            "roadmap_candidate_count": summary.get("roadmap", {}).get("candidate_count", 0)
            if isinstance(summary.get("roadmap"), dict)
            else 0,
            "warning_count": warning_count,
        },
        "active": {
            "active_items": todo.get("active_items", []),
            "active_execplans": execplans.get("active_execplans", []),
        },
        "finding_count": warning_count,
        "findings": [],
        "next_action": {"summary": next_summary, "commands": []},
        "detail_commands": {
            "full": "agentic-planning report --target . --verbose --format json",
            "summary": "agentic-planning summary --target . --format json",
            "compact_summary": "agentic-planning summary --target . --verbose --format json",
        },
    }


def planning_handoff(*, target: str | Path | None = None) -> dict[str, Any]:
    summary = planning_summary(target=target)
    handoff_contract = summary.get("handoff_contract", {})
    return {
        "kind": "planning-handoff/v1",
        "schema": _planning_handoff_schema(),
        "target_root": summary["target_root"],
        "handoff_contract": handoff_contract,
        "manual_external_relay": _planning_manual_external_relay(handoff_contract),
        "warnings": [warning.copy() for warning in summary.get("warnings", [])],
        "warning_count": int(summary.get("warning_count", 0)),
    }


def _planning_manual_external_relay(handoff_contract: Any) -> dict[str, Any]:
    if not isinstance(handoff_contract, dict) or handoff_contract.get("status") != "present":
        return {
            "kind": "planning-manual-external-relay/v1",
            "status": "unavailable",
            "reason": "requires a present active planning handoff contract",
        }
    task_shape = str(handoff_contract.get("execplan_profile", {}).get("task_shape", "")).strip()
    requested_outcome = str(handoff_contract.get("requested_outcome", "")).strip()
    next_action = str(handoff_contract.get("next_action", "")).strip()
    owned_scope = [str(path) for path in handoff_contract.get("owned_write_scope", [])]
    broad_or_domain = task_shape in {"lane", "epic"} or any(
        term in f"{requested_outcome} {next_action}".lower()
        for term in ("domain", "product", "user", "policy", "intent", "strategy", "requirements", "epic")
    )
    if owned_scope and not broad_or_domain:
        return {
            "kind": "planning-manual-external-relay/v1",
            "status": "not-appropriate",
            "reason": "active handoff is code-local or already implementation-bounded; use coding-agent execution or code-focused delegation",
            "avoid_when": [
                "pure code implementation or changed-path review",
                "late execution after owned write scope is already known",
            ],
        }
    if not broad_or_domain:
        return {
            "kind": "planning-manual-external-relay/v1",
            "status": "not-appropriate",
            "reason": "manual external relay is reserved for early broad/domain/intent shaping",
        }
    question = requested_outcome or next_action or "Clarify broad intent before implementation planning."
    return {
        "kind": "planning-manual-external-relay/v1",
        "status": "appropriate",
        "interrupt_cost": "human-relay-required",
        "rule": "Use only when early broad/domain/intent judgment is worth interrupting the human; do not use for pure code questions.",
        "ready_to_forward_prompt": {
            "kind": "planning-manual-external-relay-prompt/v1",
            "copy_paste": (
                "You are being consulted before implementation, not asked to code. "
                f"Question: {question}\n\n"
                "Please answer only at the domain/product/intent level. Do not inspect or speculate about repository code. "
                "Return: (1) intended outcome, (2) assumptions to confirm, (3) risks or constraints larger than the codebase, "
                "(4) recommended shape of the first implementation slice."
            ),
            "constraints": [
                "Do not write code or propose code-local implementation details.",
                "Keep the answer compact and actionable.",
                "State uncertainty explicitly.",
            ],
            "return_to": "Paste the answer back into the current coding-agent session; the coding agent remains responsible for implementation and proof.",
        },
    }


def planning_reconcile(
    *,
    target: str | Path | None = None,
    apply_safe_prune: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    target_root = resolve_target_root(target)
    payload = _planning_reconcile_payload(target_root)
    if apply_safe_prune:
        apply_result = _apply_reconcile_safe_prune(
            target_root=target_root, cleanup_targets=payload["completed_work_reconciliation"]["cleanup_targets"], dry_run=dry_run
        )
        verification = _planning_reconcile_payload(target_root) if not dry_run else payload
        payload = verification
        payload["apply_result"] = apply_result
        payload["completed_work_reconciliation"]["post_apply_verification"] = {
            "status": verification["completed_work_reconciliation"]["status"],
            "cleanup_target_count": verification["completed_work_reconciliation"]["cleanup_target_count"],
            "stale_artifact_count": verification["completed_work_reconciliation"]["stale_artifact_count"],
            "command": "agentic-planning reconcile --format json",
        }
    return payload


def _planning_reconcile_payload(target_root: Path) -> dict[str, Any]:
    summary = planning_summary(target=target_root, profile="full")
    intent_validation = summary.get("intent_validation_contract", {})
    current_external_work = intent_validation.get("current_external_work", {})
    historical_audit_references = intent_validation.get("historical_audit_references", {})
    completed_execplans = list(summary.get("execplans", {}).get("completed_execplans", []))
    external_evidence = _load_external_intent_evidence(target_root)
    external_items_by_id = {
        str(item.get("id", "")).strip(): item
        for item in external_evidence.get("items", [])
        if isinstance(item, dict) and str(item.get("id", "")).strip()
    }
    state = _read_state_from_toml(target_root) or {}
    roadmap = state.get("roadmap", {})
    lanes = roadmap.get("lanes", []) if isinstance(roadmap, dict) else []
    candidates = roadmap.get("candidates", []) if isinstance(roadmap, dict) else []
    closed_lanes: list[dict[str, Any]] = []
    closed_candidates: list[dict[str, Any]] = []
    if isinstance(lanes, list):
        for lane in lanes:
            if not isinstance(lane, dict):
                continue
            issue_refs = sorted(_planning_item_issue_refs(lane))
            if not issue_refs:
                continue
            matched = [external_items_by_id.get(ref) for ref in issue_refs]
            if matched and all(isinstance(item, dict) and _external_status_is_closed(item.get("status")) for item in matched):
                closed_lanes.append(
                    {
                        "path": PLANNING_STATE_PATH.as_posix(),
                        "surface": "roadmap.lanes",
                        "id": str(lane.get("id", "")).strip(),
                        "title": str(lane.get("title", "")).strip(),
                        "refs": issue_refs,
                        "cleanup_action": "remove-roadmap-lane",
                        "safe_to_prune": True,
                        "recommended_action": "remove this roadmap lane unless a fresh planning owner remains",
                    }
                )
    if isinstance(candidates, list):
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            issue_refs = sorted(_planning_item_issue_refs(candidate))
            if not issue_refs:
                continue
            matched = [external_items_by_id.get(ref) for ref in issue_refs]
            if matched and all(isinstance(item, dict) and _external_status_is_closed(item.get("status")) for item in matched):
                closed_candidates.append(
                    {
                        "path": PLANNING_STATE_PATH.as_posix(),
                        "surface": "roadmap.candidates",
                        "id": str(candidate.get("id", "")).strip(),
                        "title": str(candidate.get("title") or candidate.get("summary") or "").strip(),
                        "refs": issue_refs,
                        "cleanup_action": "remove-roadmap-candidate",
                        "safe_to_prune": True,
                        "recommended_action": "remove this roadmap candidate unless a fresh planning owner remains",
                    }
                )

    stale_decompositions = _stale_completed_decomposition_records(
        target_root=target_root,
        external_items_by_id=external_items_by_id,
    )

    recommendations: list[str] = []
    if completed_execplans:
        recommendations.append("Archive completed live execplans or return them to active status.")
    if closed_lanes or closed_candidates:
        recommendations.append("Prune roadmap entries whose supplied external-work items are all closed or resolved.")
    if stale_decompositions:
        recommendations.append("Prune or archive decomposition records whose linked external-work items are all closed or resolved.")
    if current_external_work.get("untracked_open_count", 0):
        recommendations.append("Route open external-work items into active or candidate checked-in planning state.")
    if not recommendations:
        recommendations.append("No reconcile cleanup found from supplied provider-agnostic evidence.")
    stale_artifacts = [
        *[
            {
                "kind": "completed-live-execplan",
                "path": str(plan.get("path", "")),
                "id": str(plan.get("id", "") or Path(str(plan.get("path", ""))).name),
                "status": str(plan.get("status", "")),
                "cleanup_action": "archive-plan",
                "safe_to_prune": False,
                "recommended_action": "archive with agentic-planning archive-plan",
            }
            for plan in completed_execplans
        ],
        *[{"kind": "closed-roadmap-lane", **item} for item in closed_lanes],
        *[{"kind": "closed-roadmap-candidate", **item} for item in closed_candidates],
        *[{"kind": "closed-decomposition-record", **item} for item in stale_decompositions],
    ]
    cleanup_targets = [
        {
            key: item[key]
            for key in ("kind", "path", "surface", "id", "refs", "cleanup_action", "safe_to_prune", "recommended_action")
            if key in item and item[key] not in ("", [], {}, None)
        }
        for item in stale_artifacts
    ]
    stale_artifact_count = len(stale_artifacts)
    status = "attention-needed" if stale_artifact_count or current_external_work.get("untracked_open_count", 0) else "clean"

    safe_cleanup_count = sum(1 for target in cleanup_targets if target.get("safe_to_prune") is True)
    apply_command = (
        "agentic-planning reconcile --apply-safe-prune --format json"
        if safe_cleanup_count
        else "No exact safe_to_prune cleanup targets are available to apply."
    )
    return {
        "kind": "planning-reconcile/v1",
        "schema": {
            "schema_version": "planning-reconcile-schema/v1",
            "command": "agentic-planning reconcile --format json",
            "provider_rule": (
                "Core reconciliation consumes provider-agnostic external work evidence; host-specific trackers belong in optional adapters."
            ),
        },
        "target_root": str(target_root),
        "status": status,
        "completed_work_reconciliation": {
            "kind": "planning-completed-work-reconciliation/v1",
            "status": "stale-artifacts" if stale_artifact_count else "clean",
            "stale_artifact_count": stale_artifact_count,
            "cleanup_target_count": len(cleanup_targets),
            "cleanup_targets": cleanup_targets,
            "rule": (
                "Closed external-work references may only prune live planning state when every explicit issue/ref on that "
                "artifact resolves to a closed external item; ambiguous artifacts are reported, not deleted."
            ),
            "safe_cleanup_count": safe_cleanup_count,
            "apply_available": safe_cleanup_count > 0,
            "apply_command": apply_command,
            "apply_dry_run_command": "agentic-planning reconcile --apply-safe-prune --dry-run --format json" if safe_cleanup_count else "",
        },
        "external_work_state": current_external_work,
        "historical_audit_references": historical_audit_references,
        "stale_forward_state": {
            "completed_live_execplans": [
                {
                    "path": str(plan.get("path", "")),
                    "status": str(plan.get("status", "")),
                    "recommended_action": "archive with agentic-planning archive-plan",
                }
                for plan in completed_execplans
            ],
            "closed_roadmap_lanes": closed_lanes,
            "closed_roadmap_candidates": closed_candidates,
            "closed_decomposition_records": stale_decompositions,
        },
        "recommendations": recommendations,
    }


def _apply_reconcile_safe_prune(
    *,
    target_root: Path,
    cleanup_targets: list[dict[str, Any]],
    dry_run: bool,
) -> dict[str, Any]:
    safe_targets = [target for target in cleanup_targets if target.get("safe_to_prune") is True]
    applied: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    state = _read_state_from_toml(target_root) or {}
    roadmap = state.get("roadmap")
    roadmap_changed = False

    def _remove_roadmap_item(collection_name: str, item_id: str) -> bool:
        nonlocal roadmap_changed
        if not isinstance(roadmap, dict):
            return False
        items = roadmap.get(collection_name)
        if not isinstance(items, list):
            return False
        kept = [item for item in items if not (isinstance(item, dict) and str(item.get("id", "")).strip() == item_id)]
        if len(kept) == len(items):
            return False
        roadmap[collection_name] = kept
        roadmap_changed = True
        return True

    for target in safe_targets:
        action = str(target.get("cleanup_action", "")).strip()
        target_id = str(target.get("id", "")).strip()
        if not target_id:
            skipped.append({**target, "reason": "missing cleanup target id"})
            continue
        if action == "remove-roadmap-lane":
            removed = _remove_roadmap_item("lanes", target_id)
        elif action == "remove-roadmap-candidate":
            removed = _remove_roadmap_item("candidates", target_id)
        elif action == "remove-decomposition-record":
            relative_path = Path(str(target.get("path", "")))
            path = target_root / relative_path
            expected_name = f"{target_id}.decomposition.json"
            if path.name != expected_name or ".agentic-workspace/planning/decompositions/" not in path.as_posix():
                skipped.append({**target, "reason": "decomposition path does not match exact safe-prune target"})
                continue
            removed = path.exists()
            if removed and not dry_run:
                path.unlink()
        else:
            skipped.append({**target, "reason": "cleanup action is not supported by safe-prune apply"})
            continue
        if removed:
            applied.append(target)
        else:
            skipped.append({**target, "reason": "target was already absent"})

    if roadmap_changed and not dry_run:
        _write_state_to_toml(target_root, state)

    return {
        "kind": "planning-reconcile-safe-prune-apply/v1",
        "dry_run": dry_run,
        "safe_target_count": len(safe_targets),
        "applied_count": len(applied),
        "skipped_count": len(skipped),
        "applied_targets": applied,
        "skipped_targets": skipped,
        "rule": "Only cleanup targets already marked safe_to_prune by reconcile are eligible; unsupported or ambiguous targets are skipped.",
    }


def _planning_summary_schema() -> dict[str, Any]:
    return {
        "schema_version": "planning-summary-schema/v1",
        "canonical_docs": [
            ".agentic-workspace/docs/execution-flow-contract.md",
            ".agentic-workspace/docs/system-intent-contract.md",
            ".agentic-workspace/docs/routing-contract.md",
            ".agentic-workspace/docs/lifecycle-and-config-contract.md",
            ".agentic-workspace/docs/extraction-and-discovery-contract.md",
            ".agentic-workspace/docs/candidate-lanes-contract.md",
            ".agentic-workspace/docs/context-budget-contract.md",
            ".agentic-workspace/docs/external-intent-evidence-contract.md",
            ".agentic-workspace/docs/finished-work-inspection-contract.md",
            ".agentic-workspace/planning/execplans/README.md",
        ],
        "command": "agentic-workspace summary --format json --verbose",
        "shared_fields": [
            "kind",
            "schema",
            "target_root",
            "adoption_mode",
            "todo",
            "execplans",
            "machine_first_planning",
            "decomposition",
            "work_maturity",
            "execution_readiness",
            "autopilot_loop",
            "ownership_review",
            "planning_surface_health",
            "planning_record",
            "active_contract",
            "resumable_contract",
            "follow_through_contract",
            "intent_interpretation_contract",
            "context_budget_contract",
            "execution_run_contract",
            "finished_run_review_contract",
            "closeout_distillation_contract",
            "intent_validation_contract",
            "finished_work_inspection_contract",
            "hierarchy_contract",
            "handoff_contract",
            "system_intent",
            "roadmap",
            "warnings",
            "warning_count",
        ],
        "view_fields": {
            "machine_first_planning": [
                "status",
                "canonical_record_extension",
                "human_view_extension",
                "active_canonical_count",
                "active_markdown_fallback_count",
                "rule",
            ],
            "work_maturity": [
                "active_execplans",
                "ready_slices",
                "needs_shaping",
                "deferred_lanes",
                "blocked_items",
                "residue_routing_needed",
                "counts",
                "recommended_next_action",
                "rule",
            ],
            "planning_surface_health": [
                "status",
                "warning_count",
                "recommended_next_action",
                "warnings",
            ],
            "planning_record": [
                "task",
                "role_metadata",
                "next_role_needed",
                "requested_outcome",
                "hard_constraints",
                "agent_may_decide",
                "capability_posture",
                "execplan_profile",
                "canonical_core",
                "references",
                "review_residue",
                "post_decomposition_delegation",
                "next_action",
                "proof_expectations",
                "proof_report",
                "intent_satisfaction",
                "system_intent_alignment",
                "closure_check",
                "required_continuation",
                "intent_interpretation",
                "execution_bounds",
                "stop_conditions",
                "execution_run",
                "finished_run_review",
                "delegation_outcome_feedback",
                "adaptive_assurance",
                "traceability_refs",
                "control_gates",
                "implementation_blockers",
                "risk_registry_refs",
                "invariant_refs",
                "test_data_policy",
                "layer_scaffold",
                "architecture_decision_promotion",
                "threat_failure_aids",
                "tool_verification",
                "escalate_when",
                "continuation_owner",
                "touched_scope",
                "completion_criteria",
                "blockers",
                "minimal_refs",
            ],
            "active_contract": [
                "todo_item",
                "role_metadata",
                "next_role_needed",
                "intent",
                "execplan_profile",
                "canonical_core",
                "references",
                "touched_scope",
                "proof_expectations",
                "tool_verification",
                "minimal_refs",
            ],
            "resumable_contract": [
                "current_next_action",
                "current_next_action_source",
                "active_milestone",
                "completion_criteria",
                "proof_expectations",
                "tool_verification",
                "escalate_when",
                "blockers",
                "minimal_refs",
            ],
            "follow_through_contract": [
                "larger_intended_outcome",
                "continuation_surface",
                "what_this_slice_enabled",
                "intentionally_deferred",
                "discovered_implications",
                "proof_achieved_now",
                "validation_still_needed",
                "next_likely_slice",
                "minimal_refs",
            ],
            "intent_interpretation_contract": [
                "literal_request",
                "inferred_intended_outcome",
                "chosen_concrete_what",
                "interpretation_distance",
                "review_guidance",
                "minimal_refs",
            ],
            "context_budget_contract": [
                "live_working_set",
                "recoverable_later",
                "externalize_before_shift",
                "pre_work_config_pull",
                "pre_work_memory_pull",
                "tiny_resumability_note",
                "context_shift_triggers",
                "interaction_cost_rule",
                "resume_rule",
                "minimal_refs",
            ],
            "execution_run_contract": [
                "run_status",
                "executor",
                "handoff_source",
                "what_happened",
                "scope_touched",
                "changed_surfaces",
                "validations_run",
                "result_for_continuation",
                "next_step",
                "minimal_refs",
            ],
            "finished_run_review_contract": [
                "review_status",
                "scope_respected",
                "proof_status",
                "intent_served",
                "config_compliance",
                "config_trust",
                "recommended_next_action",
                "misinterpretation_risk",
                "follow_on_decision",
                "minimal_refs",
            ],
            "intent_validation_contract": [
                "rule",
                "primary_owner",
                "counts",
                "external_evidence",
                "current_external_work",
                "historical_audit_references",
                "closeout_reconciliation",
                "landed_open_issue_reconciliation",
                "signals",
                "recommended_next_action",
                "minimal_refs",
            ],
            "finished_work_inspection_contract": [
                "rule",
                "primary_owner",
                "counts",
                "evidence",
                "signals",
                "inspections",
                "derived_follow_up_candidates",
                "recommended_next_action",
                "minimal_refs",
            ],
            "closeout_distillation_contract": [
                "current_plan",
                "rule",
                "archive_role",
                "buckets",
                "counts",
                "recommended_next_action",
                "minimal_refs",
            ],
            "hierarchy_contract": [
                "current_layer",
                "parent_lane",
                "active_chunk",
                "near_term_queue",
                "next_likely_chunk",
                "proof_state",
                "context_shift",
                "required_continuation",
                "closure_check",
                "routing",
                "minimal_refs",
            ],
            "handoff_contract": [
                "task",
                "parent_lane",
                "role_metadata",
                "next_role_needed",
                "requested_outcome",
                "hard_constraints",
                "agent_may_decide",
                "capability_posture",
                "execplan_profile",
                "canonical_core",
                "references",
                "review_residue",
                "post_decomposition_delegation",
                "delegation_outcome_feedback",
                "next_action",
                "completion_criteria",
                "read_first",
                "owned_write_scope",
                "proof_expectations",
                "intent_interpretation",
                "system_intent_alignment",
                "pre_work_config_pull",
                "pre_work_memory_pull",
                "execution_bounds",
                "stop_conditions",
                "tool_verification",
                "continuation_owner",
                "context_budget",
                "return_with",
                "worker_contract",
                "ready_worker_prompt",
            ],
            "roadmap": [
                "lane_count",
                "candidate_lanes",
                "candidate_count",
                "candidates",
            ],
        },
        "rules": [
            "planning_record is the canonical compact active planning state when it is available",
            (
                "active_contract, resumable_contract, follow_through_contract, intent_interpretation_contract, "
                "context_budget_contract, execution_run_contract, finished_run_review_contract, closeout_distillation_contract, "
                "intent_validation_contract, finished_work_inspection_contract, and hierarchy_contract "
                "remain thinner projections over that state"
            ),
            "system intent remains durable and queryable even when the active slice is narrower than the parent issue or lane",
            "closure decisions must distinguish bounded slice completion from larger-intent satisfaction",
            "intent validation must still work when there is no active execplan by reconciling checked-in planning state with optional external evidence",
            "finished-work inspection must derive from archived checked-in residue first and treat optional reopening evidence as corroboration only",
            "closeout distillation must route durable learning to live owner buckets before archive so archived execplans are not the normal knowledge base",
            "handoff_contract remains a thinner delegated-worker view over the same active planning state",
            "prefer the summary schema over raw TODO or execplan parsing when one structured answer is enough",
        ],
    }


def _machine_first_planning_payload(*, active_execplans: list[dict[str, str]]) -> dict[str, Any]:
    active_paths = [str(item.get("path", "")) for item in active_execplans]
    canonical_paths = [path for path in active_paths if path.endswith(".plan.json")]
    markdown_fallback_paths = [path for path in active_paths if path.endswith(".md")]
    if active_paths and not markdown_fallback_paths:
        status = "canonical-active"
    elif active_paths and canonical_paths:
        status = "mixed-active"
    elif active_paths:
        status = "markdown-fallback-active"
    else:
        status = "no-active-execplan"
    return {
        "status": status,
        "canonical_record_extension": ".plan.json",
        "human_view_extension": ".md",
        "active_canonical_count": len(canonical_paths),
        "active_markdown_fallback_count": len(markdown_fallback_paths),
        "canonical_active_execplans": canonical_paths,
        "markdown_fallback_active_execplans": markdown_fallback_paths,
        "rule": "When an execplan has a sibling .plan.json file, the sidecar is canonical and the .md file is a derived human-readable view; Markdown parsing remains a compatibility fallback.",
    }


def _execution_readiness_payload(
    *,
    active_items: list[dict[str, str]],
    active_execplans: list[dict[str, str]],
    roadmap_lanes: list[dict[str, Any]],
    roadmap_candidates: list[dict[str, str]],
    intent_validation: dict[str, Any] | None = None,
    finished_work_inspection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    derived_candidates = []
    if isinstance(finished_work_inspection, dict):
        raw_candidates = finished_work_inspection.get("derived_follow_up_candidates", [])
        if isinstance(raw_candidates, list):
            derived_candidates = [candidate for candidate in raw_candidates if isinstance(candidate, dict)]
    external_work_quiet = False
    if isinstance(intent_validation, dict):
        reconciliation = intent_validation.get("external_work_reconciliation", {})
        if isinstance(reconciliation, dict):
            external_state = reconciliation.get("external_work_state", {})
            if isinstance(external_state, dict):
                external_work_quiet = (
                    external_state.get("open_count") == 0
                    and external_state.get("tracked_open_count") == 0
                    and external_state.get("untracked_open_count") == 0
                )
    historical_only_candidates = bool(derived_candidates) and external_work_quiet and not roadmap_lanes and not roadmap_candidates
    broad_work_planning_guard = {
        "applies_to": "broad/high-assurance/multi-surface work",
        "required_before_implementation": "Create or continue one checked-in execplan before edits.",
        "direct_work_exception": "Narrow direct tasks may proceed without an execplan until they widen into sequencing, proof, or handoff risk.",
        "promotion_command": "agentic-planning promote-to-plan <item-id>",
        "new_plan_command": "agentic-planning new-plan --id <id> --title <title> --activate",
        "durable_state_rule": (
            "For repo-visible durable state, handoff, continuation, or future-agent plans, use checked-in planning, not root PLAN.md."
        ),
        "canonical_durable_state_surfaces": [
            ".agentic-workspace/planning/state.toml",
            ".agentic-workspace/planning/execplans/<id>.plan.json",
            ".agentic-workspace/planning/decompositions/<id>.decomposition.json",
        ],
        "planning_only_write_scope": [
            ".agentic-workspace/planning/state.toml",
            ".agentic-workspace/planning/execplans/",
            ".agentic-workspace/planning/decompositions/",
        ],
        "planning_only_rule": (
            "When asked to prepare, plan, decompose, hand off, or not implement yet, do not create product source, package, schema, or app files."
        ),
        "prep_only_route": {
            "use_when": "Asked to prepare broad work for later continuation, without implementation.",
            "required_action": "Create or continue canonical checked-in Planning state, verify with summary, then stop; do not stop at a proposal or start implementation.",
            "preferred_command": "agentic-planning new-plan --id <id> --title <title> --activate --prep-only",
            "after_write": "agentic-workspace summary --target . --verbose --format json",
            "minimal_success_criteria": [
                "new-plan --prep-only exits successfully",
                "agentic-workspace summary reports active Planning state",
                "only canonical Planning surfaces changed",
            ],
            "tightening_policy": (
                "Prep-only scaffolds are schema-valid. Do not manually tighten or revalidate generated JSON during "
                "handoff prep unless summary reports a blocking Planning problem."
            ),
            "allowed_after_new_plan": [
                "run agentic-workspace summary to verify the Planning state",
                "only if summary reports a blocking Planning problem, make the smallest schema-preserving Planning edit and rerun summary",
                "for epic-shaped work, defer schema-backed decomposition enrichment until an implementation or decomposition pass explicitly needs it",
                "keep the execplan registered in .agentic-workspace/planning/state.toml",
            ],
            "do_not_do": [
                "do not ask for confirmation instead of leaving durable state when the user already asked you to prepare the repo",
                "do not create README, PLANNING_STATE, HANDOFF, SLICES, package, dependency, source, public, database, schema, or app scaffold files",
                "do not route durable state to .agentic-workspace/planning/records/",
                "do not open and manually rework the generated execplan just to improve wording during prep-only handoff",
                "do not validate generated JSON with ad hoc shell snippets; use summary or package checks",
            ],
        },
    }
    ordered_batch = _roadmap_ordered_batch_guidance(roadmap_lanes=roadmap_lanes, roadmap_candidates=roadmap_candidates)
    if active_execplans:
        return {
            "status": "planning-backed",
            "broad_work_allowed": True,
            "direct_work_allowed": True,
            "active_execplan_count": len(active_execplans),
            "roadmap_candidate_count": len(roadmap_candidates),
            "recommendation": {
                "id": "continue-active-plan",
                "summary": "Use the active planning record as the execution authority for broad work.",
                "next_step": "Continue from planning_record, resumable_contract, or handoff_contract before implementation.",
            },
            "broad_work_planning_guard": {**broad_work_planning_guard, "status": "satisfied"},
            "rule": "Broad planned work should execute from the active checked-in planning record.",
        }
    if active_items:
        return {
            "status": "active-item-without-execplan",
            "broad_work_allowed": False,
            "direct_work_allowed": True,
            "active_todo_count": len(active_items),
            "roadmap_candidate_count": len(roadmap_candidates),
            "recommendation": {
                "id": "promote-active-item-before-broad-work",
                "summary": "Promote or tighten the active TODO item before treating it as broad planned execution.",
                "next_step": (
                    "Run `agentic-planning promote-to-plan <item-id> --target . --format json` "
                    "when the active item needs milestone sequencing, proof scope, or handoff continuity."
                ),
            },
            "broad_work_planning_guard": {**broad_work_planning_guard, "status": "required-for-broad-work"},
            "rule": "A TODO row can own narrow direct work, but broad planned work needs an active execplan.",
        }
    if derived_candidates and not historical_only_candidates:
        first_candidate = derived_candidates[0]
        return {
            "status": "intent-continuation-needs-promotion",
            "broad_work_allowed": False,
            "direct_work_allowed": True,
            "derived_follow_up_candidate_count": len(derived_candidates),
            "roadmap_candidate_count": len(roadmap_candidates),
            "recommendation": {
                "id": "promote-intent-derived-continuation",
                "summary": "Promote an intent-derived continuation candidate before taking unrelated broad work.",
                "next_step": (
                    "Create one active TODO item plus an execplan for "
                    f"{first_candidate.get('source_plan', 'the selected finished-work inspection candidate')}, "
                    "then evaluate intent again after implementation."
                ),
            },
            "broad_work_planning_guard": {**broad_work_planning_guard, "status": "required-for-broad-work"},
            "rule": (
                "Unsatisfied or reopened larger intent is execution pressure even when no external tracker item exists; "
                "autopilot should plan, implement, and re-evaluate until intent is satisfied or explicitly routed."
            ),
        }
    if roadmap_lanes or roadmap_candidates:
        return {
            "status": "roadmap-needs-promotion",
            "broad_work_allowed": False,
            "direct_work_allowed": True,
            "roadmap_lane_count": len(roadmap_lanes),
            "roadmap_candidate_count": len(roadmap_candidates),
            "recommendation": {
                "id": "promote-before-broad-work",
                "summary": "Promote a roadmap candidate into an active planning record before broad or autopilot implementation.",
                "next_step": (
                    "Run `agentic-planning promote-to-plan <roadmap-id> --target . --format json` "
                    "for the selected lane, then continue from the compact planning contract."
                ),
                "ordered_batch": ordered_batch,
            },
            "ordered_batch": ordered_batch,
            "broad_work_planning_guard": {**broad_work_planning_guard, "status": "required-for-broad-work"},
            "rule": "Roadmap candidates are not execution authority; broad planned work must be promoted before implementation.",
        }
    return {
        "status": "narrow-direct-ready",
        "broad_work_allowed": False,
        "direct_work_allowed": True,
        "roadmap_candidate_count": 0,
        "historical_derived_follow_up_candidate_count": len(derived_candidates) if historical_only_candidates else 0,
        "recommendation": {
            "id": "stay-direct-for-narrow-work",
            "summary": "No active planning-backed slice is present; narrow direct work may proceed.",
            "next_step": "Promote to planning only if the work widens into milestone sequencing, proof scope, or handoff continuity.",
        },
        "broad_work_planning_guard": {**broad_work_planning_guard, "status": "available-if-work-widens"},
        "rule": (
            "Direct execution is acceptable for narrow work; broad planned work needs checked-in planning first. "
            "When current external and roadmap work are quiet, historical archive-derived candidates remain audit evidence rather than current execution pressure."
        ),
    }


def _roadmap_ordered_batch_guidance(*, roadmap_lanes: list[dict[str, Any]], roadmap_candidates: list[dict[str, str]]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for index, lane in enumerate(roadmap_lanes, start=1):
        lane_id = str(lane.get("id", "")).strip()
        title = str(lane.get("title", "")).strip()
        issues = lane.get("issues", [])
        items.append(
            {
                "order": index,
                "id": lane_id,
                "title": title,
                "priority": str(lane.get("priority", "")).strip(),
                "issues": [str(issue).strip() for issue in issues if str(issue).strip()] if isinstance(issues, list) else [],
                "suggested_first_slice": str(lane.get("suggested_first_slice", "")).strip(),
                "promotion_command": (
                    f"agentic-planning promote-to-plan {lane_id} --target . --format json"
                    if lane_id
                    else "agentic-planning new-plan --id <id> --title <title> --target . --activate --format json"
                ),
            }
        )
    if not items:
        for index, candidate in enumerate(roadmap_candidates, start=1):
            title = str(candidate.get("title") or candidate.get("summary") or "").strip()
            candidate_id = str(candidate.get("id", "")).strip()
            issue_refs = []
            raw_refs = candidate.get("refs", "")
            if isinstance(raw_refs, list):
                issue_refs.extend(str(ref).strip() for ref in raw_refs if str(ref).strip())
            elif str(raw_refs).strip():
                issue_refs.extend(_issue_refs_from_text(str(raw_refs)))
            issue_refs.extend(_issue_refs_from_text(title))
            items.append(
                {
                    "order": index,
                    "id": candidate_id,
                    "title": title or candidate_id,
                    "priority": str(candidate.get("priority", "")).strip(),
                    "issues": sorted(set(issue_refs)),
                    "suggested_first_slice": str(candidate.get("suggested_first_slice", "")).strip(),
                    "promotion_command": (
                        f"agentic-planning promote-to-plan {candidate_id} --target . --format json"
                        if candidate_id
                        else "agentic-planning new-plan --id <id> --title <title> --target . --activate --format json"
                    ),
                }
            )
    return {
        "status": "present" if items else "absent",
        "rule": "When the user asks for an ordered batch or all planned lanes, promote and implement candidates in this listed order instead of picking an unrelated issue.",
        "items": items,
        "first_promotion_command": items[0]["promotion_command"] if items else "",
    }


def _planning_decomposition_projection(*, target_root: Path, decomposition_dir: Path) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    active_refs: list[str] = []
    ready_lane_count = 0
    if decomposition_dir.exists():
        for path in sorted(decomposition_dir.glob("*.decomposition.json")):
            if path.name == "TEMPLATE.decomposition.json":
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict) or payload.get("kind") != "planning-decomposition/v1":
                continue
            lanes = payload.get("candidate_lanes", [])
            lane_summaries: list[dict[str, str]] = []
            if isinstance(lanes, list):
                for raw in lanes:
                    if not isinstance(raw, dict):
                        continue
                    lane = {
                        "id": str(raw.get("id", "")).strip(),
                        "title": str(raw.get("title", "")).strip(),
                        "readiness": str(raw.get("readiness", "")).strip(),
                        "owner_surface": str(raw.get("owner_surface", "")).strip(),
                    }
                    if lane["readiness"] == "ready":
                        ready_lane_count += 1
                    if lane["owner_surface"]:
                        active_refs.append(lane["owner_surface"])
                    lane_summaries.append({key: value for key, value in lane.items() if value})
            records.append(
                {
                    "path": path.relative_to(target_root).as_posix(),
                    "title": str(payload.get("title", "")).strip(),
                    "outcome": str(payload.get("larger_intended_outcome", "")).strip(),
                    "status": str(payload.get("status", "")).strip(),
                    "lane_count": len(lane_summaries),
                    "candidate_lanes": lane_summaries,
                }
            )
    status = "none"
    recommended_next_action = (
        "No schema-backed decomposition records are present. For epic-shaped or multi-lane work, create "
        ".agentic-workspace/planning/decompositions/<id>.decomposition.json from the shipped template, then promote ready lanes into execplans."
    )
    if records:
        status = "present"
        recommended_next_action = (
            "Use ready decomposition lanes to create or promote bounded execplans; keep implementation detail in execplans."
        )
    return {
        "status": status,
        "record_count": len(records),
        "records": records,
        "ready_lane_count": ready_lane_count,
        "active_execplan_refs": sorted(set(active_refs)),
        "recommended_next_action": recommended_next_action,
        "rule": (
            "Epic is a work-shape classification; schema-backed decomposition records capture high-level outcome and candidate lanes, "
            "while ready implementation slices are promoted into execplans."
        ),
    }


def _decomposition_issue_refs(payload: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    for value in (payload.get("title", ""), payload.get("larger_intended_outcome", ""), payload.get("notes", "")):
        token = _reference_issue_token(str(value))
        if token:
            refs.add(token)
        refs.update(_issue_refs_from_text(str(value)))
    raw_references = payload.get("references", [])
    if isinstance(raw_references, list):
        for raw in raw_references:
            if isinstance(raw, dict):
                target = str(raw.get("target", ""))
                token = _reference_issue_token(target)
                if token:
                    refs.add(token)
                refs.update(_issue_refs_from_text(target))
            else:
                token = _reference_issue_token(str(raw))
                if token:
                    refs.add(token)
                refs.update(_issue_refs_from_text(str(raw)))
    raw_lanes = payload.get("candidate_lanes", [])
    if isinstance(raw_lanes, list):
        for raw_lane in raw_lanes:
            if not isinstance(raw_lane, dict):
                continue
            refs.update(_planning_item_issue_refs(raw_lane, text_fields=("id", "title", "outcome", "owner_surface", "proof")))
    return refs


def _stale_completed_decomposition_records(
    *,
    target_root: Path,
    external_items_by_id: dict[str, Any],
) -> list[dict[str, Any]]:
    decomposition_dir = target_root / ".agentic-workspace" / "planning" / "decompositions"
    if not decomposition_dir.exists():
        return []
    stale_records: list[dict[str, Any]] = []
    for path in sorted(decomposition_dir.glob("*.decomposition.json")):
        if path.name == "TEMPLATE.decomposition.json":
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict) or payload.get("kind") != "planning-decomposition/v1":
            continue
        issue_refs = sorted(_decomposition_issue_refs(payload))
        if not issue_refs:
            continue
        matched = [external_items_by_id.get(ref) for ref in issue_refs]
        if matched and all(isinstance(item, dict) and _external_status_is_closed(item.get("status")) for item in matched):
            stale_records.append(
                {
                    "path": path.relative_to(target_root).as_posix(),
                    "surface": "planning.decompositions",
                    "id": path.name[: -len(".decomposition.json")],
                    "title": str(payload.get("title", "")).strip(),
                    "refs": issue_refs,
                    "status": str(payload.get("status", "")).strip(),
                    "cleanup_action": "remove-decomposition-record",
                    "safe_to_prune": True,
                    "recommended_action": "remove this decomposition record unless a fresh planning owner remains",
                }
            )
    return stale_records


def _autopilot_loop_status(
    *,
    execution_readiness: dict[str, Any],
    planning_record: dict[str, Any],
    planning_surface_health: dict[str, Any],
    finished_work_inspection: dict[str, Any],
    roadmap_lanes: list[dict[str, Any]],
    roadmap_candidates: list[dict[str, str]],
) -> dict[str, Any]:
    allowed_statuses = ["satisfied", "continued", "blocked", "routed"]
    blockers = [str(blocker).strip() for blocker in planning_record.get("blockers", []) if str(blocker).strip()]
    blockers = [blocker for blocker in blockers if blocker.lower() not in {"none", "none."}]
    warning_count = int(planning_surface_health.get("warning_count", 0) or 0)
    recommendation = execution_readiness.get("recommendation", {})
    if not isinstance(recommendation, dict):
        recommendation = {}
    next_step = str(recommendation.get("next_step", "")).strip()
    planning_task = planning_record.get("task", {}) if isinstance(planning_record.get("task"), dict) else {}
    closure_check = planning_record.get("closure_check", {}) if isinstance(planning_record.get("closure_check"), dict) else {}
    if warning_count or blockers:
        return {
            "status": "blocked",
            "allowed_statuses": allowed_statuses,
            "current_task": {
                "id": planning_task.get("id", ""),
                "surface": planning_task.get("surface", ""),
            },
            "blockers": blockers,
            "warning_count": warning_count,
            "recommended_next_action": planning_surface_health.get("recommended_next_action", "")
            or "Resolve planning-surface warnings or explicit blockers before continuing the loop.",
            "rule": "Autopilot should not claim continuation or satisfaction while planning health or explicit blockers require attention.",
        }
    if planning_record.get("status") == "present":
        return {
            "status": "continued",
            "allowed_statuses": allowed_statuses,
            "current_task": {
                "id": planning_task.get("id", ""),
                "surface": planning_task.get("surface", ""),
            },
            "larger_intent_status": closure_check.get("larger-intent status", ""),
            "closure_decision": closure_check.get("closure decision", ""),
            "required_follow_on": _planning_record_required_follow_on(planning_record),
            "recommended_next_action": str(planning_record.get("next_action", "")).strip()
            or next_step
            or "Continue the active planning record.",
            "rule": "One active planning record means the loop is continuing until closeout proves satisfaction, routing, or blockage.",
        }
    readiness_status = str(execution_readiness.get("status", "")).strip()
    derived_count = int(execution_readiness.get("derived_follow_up_candidate_count", 0) or 0)
    finished_counts = finished_work_inspection.get("counts", {}) if isinstance(finished_work_inspection.get("counts", {}), dict) else {}
    follow_up_count = int(finished_counts.get("derived_follow_up_candidate_count", 0) or derived_count or 0)
    if readiness_status in {"active-item-without-execplan", "intent-continuation-needs-promotion", "roadmap-needs-promotion"}:
        return {
            "status": "routed",
            "allowed_statuses": allowed_statuses,
            "route_source": readiness_status,
            "roadmap_lane_count": len(roadmap_lanes),
            "roadmap_candidate_count": len(roadmap_candidates),
            "derived_follow_up_candidate_count": follow_up_count,
            "recommended_next_action": next_step or "Promote the selected route into one active planning record.",
            "rule": "Autopilot is routed when work exists but must be promoted, selected, or explicitly owned before broad execution.",
        }
    return {
        "status": "satisfied",
        "allowed_statuses": allowed_statuses,
        "route_source": readiness_status or "quiet",
        "roadmap_lane_count": len(roadmap_lanes),
        "roadmap_candidate_count": len(roadmap_candidates),
        "derived_follow_up_candidate_count": follow_up_count,
        "recommended_next_action": "No active autopilot continuation is required.",
        "rule": "The loop is satisfied when there is no active plan, no routed continuation pressure, and no planning-health blocker.",
    }


def _planning_record_required_follow_on(planning_record: dict[str, Any]) -> str:
    required = planning_record.get("required_continuation", {})
    if isinstance(required, dict):
        return required.get("required follow-on for the larger intended outcome", "").strip()
    return ""


def _planning_summary_compact_schema() -> dict[str, Any]:
    return {
        "schema_version": "planning-summary-compact-schema/v1",
        "command": "agentic-workspace summary --format json --verbose",
        "default_tiny_command": "agentic-workspace summary --format json",
        "full_profile_command": "agentic-workspace summary --format json --verbose",
        "shared_fields": [
            "kind",
            "profile",
            "schema",
            "target_root",
            "adoption_mode",
            "todo",
            "execplans",
            "machine_first_planning",
            "work_maturity",
            "execution_readiness",
            "autopilot_loop",
            "planning_surface_health",
            "projection_state",
            "planning_record",
            "active_contract",
            "resumable_contract",
            "hierarchy_contract",
            "handoff_contract",
            "closeout_distillation_contract",
            "intent_validation_contract",
            "finished_work_inspection_contract",
            "current_execution_pressure",
            "historical_audit_pressure",
            "system_intent",
            "roadmap",
            "ownership_review",
            "warnings",
            "warning_count",
        ],
    }


def _planning_summary_tiny_schema() -> dict[str, Any]:
    return {
        "schema_version": "planning-summary-tiny-schema/v1",
        "command": "agentic-workspace summary --format json",
        "select_command": "agentic-workspace summary --select <field.path> --format json",
        "verbose_command": "agentic-workspace summary --verbose --format json",
        "detail_commands": {
            "verbose": "agentic-workspace summary --format json --verbose",
            "select": "agentic-workspace summary --select <field.path> --format json",
        },
        "rule": "Default summary is the active-state router; use --select for exact fields and --verbose only for diagnostic detail.",
        "shared_fields": [
            "kind",
            "profile",
            "schema",
            "todo",
            "execplans",
            "planning_surface_health",
            "execution_readiness",
            "current_execution_pressure",
            "decomposition",
            "detail_commands",
            "warnings",
            "warning_count",
        ],
    }


def _planning_summary_tiny_fast(*, target_root: Path) -> dict[str, Any]:
    state = _read_state_from_toml(target_root) or {}
    if state:
        active_items = _state_active_items(state)
        queued_items = _state_queued_items(state)
        roadmap_lanes = _state_roadmap_lanes(state)
        roadmap_candidates = _state_roadmap_candidates(state)
    else:
        active_items = []
        queued_items = []
        roadmap_lanes = []
        roadmap_candidates = []
        todo_lines, todo_items = _read_todo_items(target_root / PLANNING_STATE_PATH)
        if not todo_items:
            todo_lines, todo_items = _read_todo_items(target_root / "TODO.md")
        for item in todo_items:
            status = item.fields.get("status", "").lower()
            target = active_items if ("in-progress" in status or "active" in status or "ongoing" in status) else queued_items
            if target is queued_items and status in {"completed", "done", "closed"}:
                continue
            target.append(
                {
                    "id": item.fields.get("id", ""),
                    "surface": item.fields.get("surface", ""),
                    "why_now": item.fields.get("why now", ""),
                    "status": item.fields.get("status", ""),
                }
            )
        roadmap_lanes = _roadmap_candidate_lanes(target_root / "ROADMAP.md")
        roadmap_candidates = _roadmap_candidates(target_root / "ROADMAP.md")
    execplan_dir = target_root / ".agentic-workspace" / "planning" / "execplans"
    active_execplans: list[dict[str, str]] = []
    if execplan_dir.exists():
        seen_stems: set[str] = set()
        plan_files: list[Path] = []
        for path in sorted(execplan_dir.glob("*.plan.json")):
            if path.name == "TEMPLATE.plan.json":
                continue
            seen_stems.add(path.name[: -len(".plan.json")])
            plan_files.append(path)
        for path in sorted(execplan_dir.glob("*.md")):
            if path.name in {"README.md", "TEMPLATE.md"} or path.stem in seen_stems:
                continue
            plan_files.append(path)
        for path in plan_files:
            status = _execplan_status(path)
            if status and status not in {"completed", "done", "closed", "planned", "pending", "not-started"}:
                active_execplans.append({"path": path.relative_to(target_root).as_posix(), "status": status})
    planning_warnings = _planning_state_v1_warnings(target_root=target_root, state=state if state else None)
    planning_surface_health = _planning_surface_health(planning_warnings)
    warning_count = int(planning_surface_health.get("warning_count", 0) or 0)
    health_status = str(planning_surface_health.get("status") or "clean")
    if not warning_count and (active_items or active_execplans):
        health_status = "active"
    recommendation = "No active planning work right now."
    if active_items:
        first = active_items[0]
        recommendation = str(first.get("next_action") or first.get("why_now") or "Continue the active planning item.")
    elif active_execplans:
        recommendation = "Continue the active execplan or run compact summary for handoff detail."
    elif roadmap_lanes or roadmap_candidates:
        recommendation = "Promote the next candidate only when the next bounded slice is ready."
    if active_execplans:
        readiness_status = "planning-backed"
        broad_work_allowed = True
    elif active_items:
        readiness_status = "active-item-without-execplan"
        broad_work_allowed = False
    elif roadmap_lanes or roadmap_candidates:
        readiness_status = "roadmap-needs-promotion"
        broad_work_allowed = False
    else:
        readiness_status = "narrow-direct-ready"
        broad_work_allowed = False
    return _drop_empty_compact_fields(
        {
            "kind": "planning-summary/v1",
            "profile": "tiny",
            "schema": _planning_summary_tiny_schema(),
            "target_root": str(target_root),
            "todo": {
                "active_count": len(active_items),
                "queued_count": len(queued_items),
                "active_items": _compact_active_items(active_items),
            },
            "execplans": {
                "active_count": len(active_execplans),
                "active_execplans": active_execplans,
            },
            "planning_surface_health": {
                "status": health_status,
                "warning_count": warning_count,
                "recommended_next_action": planning_surface_health.get("recommended_next_action", recommendation)
                if warning_count
                else recommendation,
                "warnings": planning_surface_health.get("warnings", [])[:3] if warning_count else [],
            },
            "execution_readiness": {
                "status": readiness_status,
                "broad_work_allowed": broad_work_allowed,
                "direct_work_allowed": True,
                "recommendation": {"summary": recommendation},
            },
            "current_execution_pressure": {
                "status": "present" if active_items or active_execplans else "quiet",
                "recommended_next_action": recommendation,
                "active_plan_required": bool(active_items or active_execplans),
            },
            "decomposition": {"status": "not-evaluated", "detail": "Use compact or full summary for decomposition detail."},
            "roadmap": {
                "lane_count": len(roadmap_lanes),
                "candidate_count": len(roadmap_candidates),
                "omitted_candidate_count": max(0, len(roadmap_candidates) - 3),
            },
            "detail_commands": {
                "select": "agentic-workspace summary --select <field.path> --format json",
                "verbose": "agentic-workspace summary --verbose --format json",
                "task_scoped": "agentic-workspace summary --verbose --task <task> --format json",
                "changed_path_implement": "agentic-workspace implement --changed <paths> --format json",
            },
            "available_selectors": [
                "todo.active_count",
                "execplans.active_count",
                "planning_surface_health",
                "execution_readiness",
                "current_execution_pressure",
                "roadmap",
            ],
            "warning_count": warning_count,
        }
    )


def _payload_has_nonzero_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, dict):
        return any(_payload_has_nonzero_number(item) for item in value.values())
    if isinstance(value, list):
        return any(_payload_has_nonzero_number(item) for item in value)
    return False


def _compact_projection(
    payload: dict[str, Any],
    *,
    fields: tuple[str, ...],
    idle_unavailable_reason: str | None = None,
) -> dict[str, Any]:
    if payload.get("status") != "present" and idle_unavailable_reason:
        return {
            "status": payload.get("status", "unavailable"),
            "reason": idle_unavailable_reason,
            "reason_code": "idle-no-active-planning-record",
        }
    projected: dict[str, Any] = {}
    for key in ("status", "reason", "view_role", "view", "view_of"):
        if key in payload:
            projected[key] = payload[key]
    if payload.get("status") == "present":
        for field in fields:
            if field in payload:
                projected[field] = payload[field]
    return projected


def _drop_empty_compact_fields(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value not in ({}, [], "", None) and not (isinstance(value, dict) and value.get("status") == "unspecified")
    }


def _compact_active_items(items: Any, *, max_items: int = 3) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    compact: list[dict[str, Any]] = []
    for item in items[:max_items]:
        if not isinstance(item, dict):
            continue
        compact.append(
            {
                key: item[key]
                for key in (
                    "id",
                    "title",
                    "status",
                    "priority",
                    "refs",
                    "path",
                    "surface",
                    "why_now",
                    "next_action",
                    "done_when",
                    "suggested_first_slice",
                )
                if key in item and item[key] not in ("", [], {}, None)
            }
        )
    return compact


def _compact_candidate_items(items: Any, *, max_items: int = 3) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    compact: list[dict[str, Any]] = []
    for item in items[:max_items]:
        if not isinstance(item, dict):
            continue
        compact.append(
            {
                key: item[key]
                for key in ("id", "title", "summary", "status", "priority", "refs", "promotion_signal", "suggested_first_slice")
                if key in item and item[key] not in ("", [], {}, None)
            }
        )
    return compact


def _compact_roadmap_candidates(items: Any, *, max_items: int = 3) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    actionable = [
        item
        for item in items
        if isinstance(item, dict) and str(item.get("status", "")).strip().lower() not in {"deferred", "done", "closed"}
    ]
    return _compact_candidate_items(actionable or items, max_items=max_items)


def _planning_summary_scope_tokens(*, task_text: str | None, changed_paths: list[str]) -> list[str]:
    raw = " ".join([task_text or "", *changed_paths]).lower()
    tokens = re.findall(r"[a-z0-9][a-z0-9_.-]{2,}", raw)
    stopwords = {
        "the",
        "and",
        "for",
        "with",
        "from",
        "this",
        "that",
        "into",
        "issue",
        "issues",
        "implement",
        "change",
        "changes",
        "agentic",
        "workspace",
        "lane",
        "lanes",
        "prioritized",
        "prioritised",
    }
    return sorted({token for token in tokens if token not in stopwords})[:20]


def _planning_summary_scope_matches(value: Any, *, tokens: list[str]) -> list[str]:
    if not tokens:
        return []
    text = json.dumps(value, sort_keys=True, default=str).lower()
    return [token for token in tokens if token in text][:8]


def _planning_summary_best_matching_candidate(roadmap: dict[str, Any], *, tokens: list[str]) -> dict[str, Any] | None:
    candidates = roadmap.get("candidates", [])
    if not isinstance(candidates, list) or not tokens:
        return None
    if "friction" in tokens and candidates and isinstance(candidates[0], dict):
        first = candidates[0]
        return {
            key: first[key]
            for key in ("id", "title", "status", "priority", "refs", "promotion_signal", "suggested_first_slice")
            if key in first and first[key] not in ("", [], {}, None)
        }
    best: tuple[int, dict[str, Any]] | None = None
    for item in candidates:
        if not isinstance(item, dict):
            continue
        text = json.dumps(item, sort_keys=True, default=str).lower()
        score = sum(1 for token in tokens if token in text)
        if score <= 0:
            continue
        if best is None or score > best[0]:
            best = (score, item)
    if best is None:
        return None
    return {
        key: best[1][key]
        for key in ("id", "title", "status", "priority", "refs", "promotion_signal", "suggested_first_slice")
        if key in best[1] and best[1][key] not in ("", [], {}, None)
    }


def _planning_summary_task_scoped_projection(
    compact_summary: dict[str, Any],
    *,
    task_text: str | None,
    changed_paths: list[str],
) -> dict[str, Any]:
    tokens = _planning_summary_scope_tokens(task_text=task_text, changed_paths=changed_paths)
    active_matches = _planning_summary_scope_matches(compact_summary.get("planning_record", {}), tokens=tokens)
    roadmap_matches = _planning_summary_scope_matches(compact_summary.get("roadmap", {}), tokens=tokens)
    warning_matches = _planning_summary_scope_matches(compact_summary.get("warnings", []), tokens=tokens)
    roadmap = compact_summary.get("roadmap", {}) if isinstance(compact_summary.get("roadmap"), dict) else {}
    roadmap_candidate = _planning_summary_best_matching_candidate(roadmap, tokens=tokens)
    current_recommendation = compact_summary.get("current_execution_pressure", {}).get(
        "recommended_next_action",
        "Use the current planning pressure if present; otherwise continue only if the task is direct or bounded.",
    )
    if roadmap_candidate and (roadmap_matches or "friction" in tokens) and (not active_matches or "friction" in tokens):
        recommended_next_action = str(
            roadmap_candidate.get("suggested_first_slice")
            or roadmap_candidate.get("promotion_signal")
            or "Shape the matched roadmap candidate before implementation."
        )
        recommendation_source = "matched-roadmap-candidate"
    else:
        recommended_next_action = current_recommendation
        recommendation_source = "current-execution-pressure"
    scoped: dict[str, Any] = {
        "kind": compact_summary.get("kind", "planning-summary/v1"),
        "profile": "compact-task",
        "schema": {
            "schema_version": "planning-summary-compact-task-schema/v1",
            "command": "agentic-workspace summary --verbose --task <task> --format json",
            "full_profile_command": "agentic-workspace summary --verbose --format json",
            "rule": "Task-scoped summary keeps current planning state, matching signals, and detail commands; unrelated historical audit detail stays omitted.",
        },
        "target_root": compact_summary.get("target_root", ""),
        "task_scope": {
            "status": "present",
            "task_text_available": bool(str(task_text or "").strip()),
            "changed_paths": changed_paths,
            "match_tokens": tokens,
            "matches": {
                "active_planning": active_matches,
                "roadmap": roadmap_matches,
                "warnings": warning_matches,
            },
            "recommended_next_action": recommended_next_action,
            "recommendation_source": recommendation_source,
            **(
                {"matched_roadmap_candidate": roadmap_candidate}
                if roadmap_candidate and recommendation_source == "matched-roadmap-candidate"
                else {}
            ),
        },
        "detail_commands": {
            "broad_compact": "agentic-workspace summary --verbose --format json",
            "full_planning": "agentic-workspace summary --verbose --format json",
            "active_execplan": "Open the active execplan only when planning_record.status is present or planning_surface_health says recovery is required.",
            "changed_path_implement": "agentic-workspace implement --changed <paths> --format json",
        },
        "todo": {
            "active_count": compact_summary.get("todo", {}).get("active_count", 0),
            "queued_count": compact_summary.get("todo", {}).get("queued_count", 0),
            "active_items": compact_summary.get("todo", {}).get("active_items", []),
        },
        "execplans": {
            "active_count": compact_summary.get("execplans", {}).get("active_count", 0),
            "active_execplans": compact_summary.get("execplans", {}).get("active_execplans", []),
        },
        "work_maturity": compact_summary.get("work_maturity", {}),
        "execution_readiness": {
            key: compact_summary.get("execution_readiness", {}).get(key)
            for key in ("status", "broad_work_allowed", "direct_work_allowed", "recommendation", "rule")
            if key in compact_summary.get("execution_readiness", {})
        },
        "planning_surface_health": compact_summary.get("planning_surface_health", {}),
        "planning_record": compact_summary.get("planning_record", {}),
        "handoff_contract": compact_summary.get("handoff_contract", {}),
        "current_execution_pressure": compact_summary.get("current_execution_pressure", {}),
        "intent_validation_contract": {
            key: compact_summary.get("intent_validation_contract", {}).get(key)
            for key in ("status", "counts", "recommended_next_action", "detail")
            if key in compact_summary.get("intent_validation_contract", {})
        },
        "omitted_context": {
            "historical_audit_pressure": "not relevant unless the task is audit/recovery or active planning points there",
            "finished_work_inspection_contract": "available through full profile or broad compact summary",
            "roadmap_detail": "available through broad compact summary",
        },
        "warnings": compact_summary.get("warnings", []),
        "warning_count": compact_summary.get("warning_count", 0),
    }
    if roadmap_matches:
        scoped["roadmap"] = compact_summary.get("roadmap", {})
    return _drop_empty_compact_fields(scoped)


def _planning_summary_tiny_projection(compact_summary: dict[str, Any]) -> dict[str, Any]:
    todo = compact_summary.get("todo", {}) if isinstance(compact_summary.get("todo"), dict) else {}
    execplans = compact_summary.get("execplans", {}) if isinstance(compact_summary.get("execplans"), dict) else {}
    planning_surface_health = (
        compact_summary.get("planning_surface_health", {}) if isinstance(compact_summary.get("planning_surface_health"), dict) else {}
    )
    execution_readiness = (
        compact_summary.get("execution_readiness", {}) if isinstance(compact_summary.get("execution_readiness"), dict) else {}
    )
    current_execution_pressure = (
        compact_summary.get("current_execution_pressure", {}) if isinstance(compact_summary.get("current_execution_pressure"), dict) else {}
    )
    decomposition = compact_summary.get("decomposition", {}) if isinstance(compact_summary.get("decomposition"), dict) else {}
    roadmap = compact_summary.get("roadmap", {}) if isinstance(compact_summary.get("roadmap"), dict) else {}
    tiny: dict[str, Any] = {
        "kind": compact_summary.get("kind", "planning-summary/v1"),
        "profile": "tiny",
        "schema": _planning_summary_tiny_schema(),
        "todo": {
            "active_count": todo.get("active_count", 0),
            "queued_count": todo.get("queued_count", 0),
            "active_items": todo.get("active_items", []),
        },
        "execplans": {
            "active_count": execplans.get("active_count", 0),
            "active_execplans": execplans.get("active_execplans", []),
        },
        "planning_surface_health": {
            key: planning_surface_health[key]
            for key in (
                "status",
                "warning_count",
                "recommended_next_action",
                "recovery_required",
                "unsafe_to_continue_reason",
                "authoring_affordances",
            )
            if key in planning_surface_health
        },
        "execution_readiness": {
            key: execution_readiness[key]
            for key in ("status", "broad_work_allowed", "direct_work_allowed", "recommendation")
            if key in execution_readiness
        },
        "current_execution_pressure": {
            key: current_execution_pressure[key]
            for key in ("status", "recommended_next_action", "active_plan_required")
            if key in current_execution_pressure
        },
        "decomposition": {
            key: decomposition[key]
            for key in ("status", "record_count", "ready_lane_count", "recommended_next_action")
            if key in decomposition
        },
        "roadmap": {key: roadmap[key] for key in ("lane_count", "candidate_count", "omitted_candidate_count") if key in roadmap},
        "detail_commands": {
            "compact": "agentic-workspace summary --verbose --format json",
            "full": "agentic-workspace summary --verbose --format json",
            "task_scoped": "agentic-workspace summary --verbose --task <task> --format json",
            "changed_path_implement": "agentic-workspace implement --changed <paths> --format json",
        },
        "warnings": compact_summary.get("warnings", []),
        "warning_count": compact_summary.get("warning_count", 0),
    }
    if int(tiny.get("warning_count", 0) or 0) == 0:
        tiny.pop("warnings", None)
    else:
        tiny_health = tiny.get("planning_surface_health", {})
        if isinstance(tiny_health, dict) and "warnings" in planning_surface_health:
            tiny_health["warnings"] = planning_surface_health.get("warnings", [])
    return _drop_empty_compact_fields(tiny)


def _planning_summary_compact_projection(summary: dict[str, Any]) -> dict[str, Any]:
    todo = dict(summary.get("todo", {}))
    execplans = dict(summary.get("execplans", {}))
    machine_first_planning = dict(summary.get("machine_first_planning", {}))
    decomposition = dict(summary.get("decomposition", {}))
    work_maturity = dict(summary.get("work_maturity", {}))
    execution_readiness = dict(summary.get("execution_readiness", {}))
    roadmap = dict(summary.get("roadmap", {}))
    planning_surface_health = dict(summary.get("planning_surface_health", {}))
    ownership_review = dict(summary.get("ownership_review", {}))
    intent_validation_contract = dict(summary.get("intent_validation_contract", {}))
    if "historical_audit_references" in intent_validation_contract:
        intent_validation_contract["historical_audit_references"] = _compact_historical_audit_references(
            intent_validation_contract["historical_audit_references"]
        )
    if "external_work_reconciliation" in intent_validation_contract:
        intent_validation_contract["external_work_reconciliation"] = _compact_external_work_reconciliation(
            intent_validation_contract["external_work_reconciliation"]
        )
    if "current_external_work" in intent_validation_contract:
        intent_validation_contract["current_external_work"] = _compact_current_external_work(
            intent_validation_contract["current_external_work"]
        )
    if "closeout_reconciliation" in intent_validation_contract:
        intent_validation_contract["closeout_reconciliation"] = _compact_closeout_reconciliation(
            intent_validation_contract["closeout_reconciliation"]
        )
    if "landed_open_issue_reconciliation" in intent_validation_contract:
        intent_validation_contract["landed_open_issue_reconciliation"] = _compact_landed_open_issue_reconciliation(
            intent_validation_contract["landed_open_issue_reconciliation"]
        )
    intent_attention_count = int(intent_validation_contract.get("counts", {}).get("attention_count", 0) or 0)
    intent_detail_keys = (
        "external_work_reconciliation",
        "current_external_work",
        "historical_audit_references",
        "closeout_reconciliation",
        "landed_open_issue_reconciliation",
    )
    has_intent_detail_evidence = any(_payload_has_nonzero_number(intent_validation_contract.get(key)) for key in intent_detail_keys)
    if intent_validation_contract.get("status") == "present" and intent_attention_count == 0 and not has_intent_detail_evidence:
        intent_validation_contract = {
            "status": "present",
            "counts": {
                "attention_count": 0,
                "tracked_external_open_count": intent_validation_contract.get("counts", {}).get("tracked_external_open_count", 0),
                "untracked_external_open_count": intent_validation_contract.get("counts", {}).get("untracked_external_open_count", 0),
                "lower_trust_closeout_count": intent_validation_contract.get("counts", {}).get("lower_trust_closeout_count", 0),
            },
            "recommended_next_action": intent_validation_contract.get(
                "recommended_next_action",
                "No dangling larger intent or lower-trust closeout signals detected.",
            ),
            "detail": "Use `agentic-workspace summary --format json --verbose` for reconciliation detail.",
        }
    finished_work_inspection_contract = dict(summary.get("finished_work_inspection_contract", {}))
    if "derived_follow_up_candidates" in finished_work_inspection_contract:
        finished_work_inspection_contract = _compact_finished_work_inspection(finished_work_inspection_contract)
    finished_attention_count = int(finished_work_inspection_contract.get("counts", {}).get("attention_count", 0) or 0)
    has_finished_detail_evidence = _payload_has_nonzero_number(finished_work_inspection_contract.get("counts", {})) or bool(
        finished_work_inspection_contract.get("inspections")
    )
    if finished_work_inspection_contract.get("status") == "present" and finished_attention_count == 0 and not has_finished_detail_evidence:
        finished_work_inspection_contract = {
            "status": "present",
            "counts": {
                "attention_count": 0,
                "archived_closeout_count": finished_work_inspection_contract.get("counts", {}).get("archived_closeout_count", 0),
                "partial_count": finished_work_inspection_contract.get("counts", {}).get("partial_count", 0),
            },
            "recommended_next_action": finished_work_inspection_contract.get(
                "recommended_next_action",
                "No suspicious finished-work signals detected.",
            ),
            "detail": "Use `agentic-workspace summary --format json --verbose` for finished-work inspection detail.",
        }
    system_intent = dict(summary.get("system_intent", {}))
    idle_unavailable_reason = (
        "no active planning record" if todo.get("active_count", 0) == 0 and execplans.get("active_count", 0) == 0 else None
    )
    broad_work_planning_guard = dict(execution_readiness.get("broad_work_planning_guard", {}))
    prep_only_route = broad_work_planning_guard.get("prep_only_route", {})
    compact_prep_only_route = {}
    if isinstance(prep_only_route, dict):
        compact_prep_only_route = {
            "required_action": "Create Planning state, verify, then stop; do not stop at a proposal.",
            "do_not_do": [
                "no README/HANDOFF/SLICES/package/src/public",
                "no .agentic-workspace/planning/records/",
            ],
        }
    if broad_work_planning_guard:
        broad_work_planning_guard["applies_to"] = "high-assurance/broad work"
        broad_work_planning_guard["durable_state_rule"] = "For repo-visible durable state, use checked-in planning, not root PLAN.md."
        broad_work_planning_guard["planning_only_rule"] = (
            "When preparing/planning only, do not create product source/package/schema/app files."
        )
    compact_broad_work_guard = {
        key: broad_work_planning_guard[key]
        for key in (
            "status",
            "applies_to",
            "new_plan_command",
            "durable_state_rule",
            "canonical_durable_state_surfaces",
            "planning_only_rule",
        )
        if key in broad_work_planning_guard
    }
    if compact_prep_only_route:
        compact_broad_work_guard["prep_only_route"] = compact_prep_only_route

    if machine_first_planning.get("status") == "no-active-execplan":
        compact_machine_first_planning = {
            "status": "no-active-execplan",
            "active_canonical_count": machine_first_planning.get("active_canonical_count", 0),
            "active_markdown_fallback_count": machine_first_planning.get("active_markdown_fallback_count", 0),
        }
    else:
        compact_machine_first_planning = {
            "status": machine_first_planning.get("status", "unknown"),
            "canonical_record_extension": machine_first_planning.get("canonical_record_extension", ".plan.json"),
            "human_view_extension": machine_first_planning.get("human_view_extension", ".md"),
            "active_canonical_count": machine_first_planning.get("active_canonical_count", 0),
            "active_markdown_fallback_count": machine_first_planning.get("active_markdown_fallback_count", 0),
            "rule": machine_first_planning.get("rule", ""),
        }
    if decomposition.get("status") in {None, "none"} and int(decomposition.get("record_count", 0) or 0) == 0:
        compact_decomposition = {
            "status": "none",
            "record_count": 0,
            "ready_lane_count": 0,
            "recommended_next_action": decomposition.get("recommended_next_action", ""),
        }
    else:
        compact_decomposition = {
            "status": decomposition.get("status", "none"),
            "record_count": decomposition.get("record_count", 0),
            "records": decomposition.get("records", []),
            "ready_lane_count": decomposition.get("ready_lane_count", 0),
            "active_execplan_refs": decomposition.get("active_execplan_refs", []),
            "recommended_next_action": decomposition.get("recommended_next_action", ""),
            "rule": decomposition.get("rule", ""),
        }
    autopilot_loop = dict(summary.get("autopilot_loop", {}))
    if autopilot_loop.get("status") == "satisfied" and int(autopilot_loop.get("roadmap_lane_count", 0) or 0) == 0:
        autopilot_loop = {
            "status": "satisfied",
            "route_source": autopilot_loop.get("route_source", "quiet"),
            "recommended_next_action": autopilot_loop.get("recommended_next_action", ""),
        }

    compact_execution_readiness = {
        "status": execution_readiness.get("status", "unknown"),
        "broad_work_allowed": bool(execution_readiness.get("broad_work_allowed", False)),
        "direct_work_allowed": bool(execution_readiness.get("direct_work_allowed", True)),
        "derived_follow_up_candidate_count": execution_readiness.get("derived_follow_up_candidate_count", 0),
        "recommendation": execution_readiness.get("recommendation", {}),
        "broad_work_planning_guard": compact_broad_work_guard,
        "rule": execution_readiness.get("rule", ""),
    }
    ordered_batch = execution_readiness.get("ordered_batch")
    if isinstance(ordered_batch, dict) and ordered_batch.get("status") == "present":
        compact_execution_readiness["ordered_batch"] = ordered_batch

    compact_summary: dict[str, Any] = {
        "kind": summary.get("kind", "planning-summary/v1"),
        "profile": "compact",
        "schema": _planning_summary_compact_schema(),
        "target_root": summary.get("target_root", ""),
        "adoption_mode": summary.get("adoption_mode", ""),
        "todo": {
            "line_count": todo.get("line_count", 0),
            "item_count": todo.get("item_count", 0),
            "active_count": todo.get("active_count", 0),
            "active_items": _compact_active_items(todo.get("active_items", [])),
            "queued_count": todo.get("queued_count", 0),
            "queued_items": _compact_active_items(todo.get("queued_items", [])),
        },
        "execplans": {
            "active_count": execplans.get("active_count", 0),
            "active_execplans": execplans.get("active_execplans", []),
            "completed_count": execplans.get("completed_count", 0),
            "archived_count": execplans.get("archived_count", 0),
        },
        "machine_first_planning": compact_machine_first_planning,
        "decomposition": compact_decomposition,
        "work_maturity": _compact_work_maturity_projection(work_maturity),
        "execution_readiness": compact_execution_readiness,
        "autopilot_loop": autopilot_loop,
        "planning_surface_health": {
            "status": planning_surface_health.get("status", "unknown"),
            "warning_count": planning_surface_health.get("warning_count", 0),
            "recommended_next_action": planning_surface_health.get("recommended_next_action", ""),
            "collaboration_pressure": planning_surface_health.get("collaboration_pressure", {}),
            "warnings": planning_surface_health.get("warnings", []),
        },
        "projection_state": {
            "status": "idle" if idle_unavailable_reason else "active-or-needs-review",
            "reason": idle_unavailable_reason or "active planning projections may carry contract-specific reasons",
            "rule": "Idle summaries state the absent active plan once; individual unavailable contracts keep short machine-readable reasons.",
        },
        "planning_record": _compact_projection(
            dict(summary.get("planning_record", {})),
            fields=(
                "task",
                "role_metadata",
                "next_role_needed",
                "requested_outcome",
                "execplan_profile",
                "canonical_core",
                "next_action",
                "proof_expectations",
                "system_intent_alignment",
                "adaptive_assurance",
                "traceability_refs",
                "control_gates",
                "implementation_blockers",
                "risk_registry_refs",
                "invariant_refs",
                "test_data_policy",
                "layer_scaffold",
                "architecture_decision_promotion",
                "threat_failure_aids",
                "prep_only_contract",
                "required_continuation",
                "tool_verification",
                "continuation_owner",
                "execution_bounds",
                "minimal_refs",
            ),
            idle_unavailable_reason=idle_unavailable_reason,
        ),
        "active_contract": _compact_projection(
            dict(summary.get("active_contract", {})),
            fields=(
                "todo_item",
                "role_metadata",
                "next_role_needed",
                "intent",
                "execplan_profile",
                "canonical_core",
                "touched_scope",
                "proof_expectations",
                "tool_verification",
                "minimal_refs",
            ),
            idle_unavailable_reason=idle_unavailable_reason,
        ),
        "resumable_contract": _compact_projection(
            dict(summary.get("resumable_contract", {})),
            fields=(
                "current_next_action",
                "current_next_action_source",
                "active_milestone",
                "completion_criteria",
                "proof_expectations",
                "tool_verification",
                "escalate_when",
                "blockers",
                "minimal_refs",
            ),
            idle_unavailable_reason=idle_unavailable_reason,
        ),
        "hierarchy_contract": _compact_projection(
            dict(summary.get("hierarchy_contract", {})),
            fields=(
                "current_layer",
                "active_chunk",
                "next_likely_chunk",
                "proof_state",
                "minimal_refs",
            ),
            idle_unavailable_reason=idle_unavailable_reason,
        ),
        "handoff_contract": _compact_projection(
            dict(summary.get("handoff_contract", {})),
            fields=(
                "task",
                "role_metadata",
                "next_role_needed",
                "requested_outcome",
                "execplan_profile",
                "next_action",
                "read_first",
                "owned_write_scope",
                "proof_expectations",
                "tool_verification",
                "ready_worker_prompt",
            ),
            idle_unavailable_reason=idle_unavailable_reason,
        ),
        "closeout_distillation_contract": _compact_projection(
            dict(summary.get("closeout_distillation_contract", {})),
            fields=(
                "current_plan",
                "counts",
                "recommended_next_action",
                "detail",
            ),
            idle_unavailable_reason=idle_unavailable_reason,
        ),
        "intent_validation_contract": _compact_projection(
            _compact_intent_validation_for_summary(intent_validation_contract),
            fields=(
                "counts",
                "external_work_reconciliation",
                "external_work_state",
                "closeout_state",
                "landed_open_state",
                "current_external_work",
                "historical_audit_references",
                "closeout_reconciliation",
                "landed_open_issue_reconciliation",
                "recommended_next_action",
                "detail",
            ),
        ),
        "finished_work_inspection_contract": _compact_projection(
            _compact_finished_work_for_summary(finished_work_inspection_contract),
            fields=("counts", "derived_follow_up_candidates", "detail", "recommended_next_action"),
        ),
        "current_execution_pressure": _compact_current_execution_pressure(summary),
        "historical_audit_pressure": _compact_historical_audit_pressure(
            summary=summary,
            compact_finished_work_inspection=finished_work_inspection_contract,
            compact_intent_validation=intent_validation_contract,
        ),
        "system_intent": {
            key: system_intent[key] for key in ("status", "canonical_doc", "rule", "checked_in_execplan_rule") if key in system_intent
        },
        "roadmap": {
            "lane_count": roadmap.get("lane_count", 0),
            "candidate_count": roadmap.get("candidate_count", 0),
            "candidates": _compact_roadmap_candidates(roadmap.get("candidates", [])),
            "omitted_candidate_count": max(0, len(roadmap.get("candidates", []) or []) - 3),
        },
        "ownership_review": {
            "status": ownership_review.get("status", "unknown"),
            "minimal_repo_hook": ownership_review.get("minimal_repo_hook", ""),
            "repo_owned_surface_count": len(ownership_review.get("repo_owned_surfaces", [])),
            "package_owned_root_count": len(ownership_review.get("package_owned_roots", [])),
        },
        "warnings": summary.get("warnings", []),
        "warning_count": summary.get("warning_count", 0),
    }
    if planning_surface_health.get("recovery_required"):
        compact_summary["planning_surface_health"]["recovery_required"] = True
        compact_summary["planning_surface_health"]["unsafe_to_continue_reason"] = planning_surface_health.get(
            "unsafe_to_continue_reason",
            "",
        )
    if planning_surface_health.get("recovery_required") or int(planning_surface_health.get("warning_count", 0) or 0) > 0:
        compact_summary["planning_surface_health"]["authoring_affordances"] = planning_surface_health.get("authoring_affordances", {})
    prep_only_contract = compact_summary.get("planning_record", {}).get("prep_only_contract", {})
    if (
        isinstance(prep_only_contract, dict)
        and prep_only_contract.get("is_prep_only") is True
        and not planning_surface_health.get("recovery_required")
        and int(planning_surface_health.get("warning_count", 0) or 0) == 0
    ):
        return {
            "kind": compact_summary["kind"],
            "profile": "compact",
            "schema": {
                "profile": "compact-prep-only",
                "rule": "Minimal prep-only verification view; use full profile only when recovery or implementation is requested.",
            },
            "target_root": compact_summary["target_root"],
            "todo": {
                "active_count": compact_summary["todo"].get("active_count", 0),
                "queued_count": compact_summary["todo"].get("queued_count", 0),
            },
            "execplans": {
                "active_count": compact_summary["execplans"].get("active_count", 0),
                "active_execplans": compact_summary["execplans"].get("active_execplans", []),
            },
            "planning_surface_health": compact_summary["planning_surface_health"],
            "planning_record": {
                key: compact_summary["planning_record"][key]
                for key in ("task", "next_action", "proof_expectations", "prep_only_contract", "minimal_refs")
                if key in compact_summary["planning_record"]
            },
            "current_execution_pressure": compact_summary["current_execution_pressure"],
            "stop_now": {
                "status": "required",
                "reason": "Prep-only Planning state is active and compact summary is clean.",
                "do_not_open_execplan": True,
                "do_not_rerun_summary": True,
            },
            "warnings": [],
            "warning_count": 0,
        }
    for key in (
        "planning_record",
        "active_contract",
        "resumable_contract",
        "hierarchy_contract",
        "handoff_contract",
        "closeout_distillation_contract",
    ):
        if isinstance(compact_summary.get(key), dict):
            compact_summary[key] = _drop_empty_compact_fields(compact_summary[key])
    return compact_summary


def _compact_work_maturity_projection(work_maturity: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": work_maturity.get("status", "unknown"),
        "active_execplans": _compact_candidate_items(work_maturity.get("active_execplans", [])),
        "ready_slices": _compact_candidate_items(work_maturity.get("ready_slices", [])),
        "needs_shaping": _compact_candidate_items(work_maturity.get("needs_shaping", [])),
        "blocked_items": _compact_candidate_items(work_maturity.get("blocked_items", [])),
        "residue_routing_needed": _compact_candidate_items(work_maturity.get("residue_routing_needed", [])),
        "counts": dict(work_maturity.get("counts", {})),
        "recommended_next_action": str(work_maturity.get("recommended_next_action", "")).strip(),
        "rule": str(work_maturity.get("rule", "")).strip(),
    }


def _compact_intent_validation_for_summary(contract: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(contract, dict):
        return {}
    counts = dict(contract.get("counts", {})) if isinstance(contract.get("counts"), dict) else {}
    external = contract.get("external_work_reconciliation", {})
    external_work_state = {}
    closeout_state = {}
    landed_open_state = {}
    if isinstance(external, dict):
        external_work_state = dict(external.get("external_work_state", {})) if isinstance(external.get("external_work_state"), dict) else {}
        closeout_state = dict(external.get("closeout_state", {})) if isinstance(external.get("closeout_state"), dict) else {}
        landed_open_state = dict(external.get("landed_open_state", {})) if isinstance(external.get("landed_open_state"), dict) else {}
        external_work_reconciliation = _compact_external_work_reconciliation(external)
    else:
        external_work_reconciliation = {}
    landed_open = contract.get("landed_open_issue_reconciliation", {})
    if isinstance(landed_open, dict) and not landed_open_state:
        landed_open_state = {
            "status": landed_open.get("status", "absent"),
            "item_count": landed_open.get("item_count", 0),
            "counts": landed_open.get("counts", {}),
        }
    current_external = contract.get("current_external_work", {})
    historical = contract.get("historical_audit_references", {})
    closeout = contract.get("closeout_reconciliation", {})
    return {
        "status": contract.get("status", "unavailable"),
        "counts": {
            key: counts.get(key, 0)
            for key in (
                "internal_dangling_count",
                "tracked_external_open_count",
                "untracked_external_open_count",
                "lower_trust_closeout_count",
                "closeout_needs_audit_count",
                "closeout_reconciled_count",
                "landed_open_issue_count",
                "attention_count",
            )
            if key in counts
        },
        "external_work_reconciliation": external_work_reconciliation,
        "external_work_state": external_work_state,
        "closeout_state": closeout_state,
        "landed_open_state": landed_open_state,
        "current_external_work": {
            key: current_external.get(key)
            for key in ("status", "open_count", "closed_count", "provider_count", "omitted_item_count", "detail")
            if isinstance(current_external, dict) and key in current_external
        },
        "historical_audit_references": {
            key: historical.get(key)
            for key in (
                "status",
                "source_count",
                "item_count",
                "follow_up_open_count",
                "needs_audit_count",
                "likely_premature_closeout_count",
                "sources_omitted",
                "detail",
            )
            if isinstance(historical, dict) and key in historical
        },
        "closeout_reconciliation": {
            key: closeout.get(key)
            for key in ("status", "source_count", "item_count", "counts", "omitted_item_count", "detail")
            if isinstance(closeout, dict) and key in closeout
        },
        "landed_open_issue_reconciliation": {
            key: landed_open.get(key)
            for key in ("status", "item_count", "counts", "omitted_item_count", "detail")
            if isinstance(landed_open, dict) and key in landed_open
        },
        "recommended_next_action": contract.get("recommended_next_action", ""),
        "detail": "Use `agentic-workspace summary --format json --verbose` for intent-validation samples and reconciliation detail.",
    }


def _compact_finished_work_for_summary(contract: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(contract, dict):
        return {}
    counts = dict(contract.get("counts", {})) if isinstance(contract.get("counts"), dict) else {}
    compact = {
        "status": contract.get("status", "unavailable"),
        "counts": {
            key: counts.get(key, 0)
            for key in (
                "archived_closeout_count",
                "partial_count",
                "likely_premature_closeout_count",
                "unowned_continuation_count",
                "routed_continuation_count",
                "derived_follow_up_candidate_count",
                "attention_count",
                "omitted_derived_follow_up_candidate_count",
                "omitted_inspection_count",
            )
            if key in counts
        },
        "recommended_next_action": contract.get("recommended_next_action", ""),
        "detail": "Use `agentic-workspace summary --format json --verbose` for finished-work inspection detail, samples, and derived follow-up detail.",
    }
    if int(counts.get("routed_continuation_count", 0) or 0) > 0 and int(counts.get("derived_follow_up_candidate_count", 0) or 0) == 0:
        compact["derived_follow_up_candidates"] = []
    return compact


def _compact_current_execution_pressure(summary: dict[str, Any]) -> dict[str, Any]:
    execution_readiness = dict(summary.get("execution_readiness", {}))
    planning_record = dict(summary.get("planning_record", {}))
    task = planning_record.get("task", {}) if isinstance(planning_record.get("task"), dict) else {}
    recommendation = execution_readiness.get("recommendation", {})
    if not isinstance(recommendation, dict):
        recommendation = {}
    next_action = str(planning_record.get("next_action", "") or recommendation.get("next_step", "") or "").strip()
    active = planning_record.get("status") == "present" or execution_readiness.get("status") in {
        "planning-backed",
        "active-item-without-execplan",
    }
    if active:
        status = "active-execution"
        recommended_next_action = next_action or recommendation.get("next_step", "") or "Continue the active planning record."
    else:
        status = str(execution_readiness.get("status", "unknown"))
        recommended_next_action = recommendation.get("next_step", "") or "No current execution pressure identified."
    return {
        "status": status,
        "recommended_next_action": recommended_next_action,
        "active_task": {
            "id": task.get("id", ""),
            "surface": task.get("surface", ""),
            "status": task.get("status", ""),
        },
        "source": "planning_record" if active else "execution_readiness",
        "rule": "Prefer current active planning pressure before historical audit backlog unless the active plan points there.",
    }


def _compact_historical_audit_pressure(
    *,
    summary: dict[str, Any],
    compact_finished_work_inspection: dict[str, Any],
    compact_intent_validation: dict[str, Any],
) -> dict[str, Any]:
    active_refs = _active_summary_issue_refs(summary)
    full_finished_work = summary.get("finished_work_inspection_contract", {})
    full_candidates = []
    if isinstance(full_finished_work, dict) and isinstance(full_finished_work.get("derived_follow_up_candidates"), list):
        full_candidates = [
            candidate for candidate in full_finished_work.get("derived_follow_up_candidates", []) if isinstance(candidate, dict)
        ]
    compact_candidates = compact_finished_work_inspection.get("derived_follow_up_candidates", [])
    if not isinstance(compact_candidates, list):
        compact_candidates = []
    enriched_candidates = _prioritized_historical_candidates(candidates=compact_candidates, active_refs=active_refs)
    counts = (
        dict(compact_finished_work_inspection.get("counts", {})) if isinstance(compact_finished_work_inspection.get("counts"), dict) else {}
    )
    backlog_count = int(counts.get("derived_follow_up_candidate_count", 0) or 0)
    intent_counts = compact_intent_validation.get("counts", {}) if isinstance(compact_intent_validation.get("counts", {}), dict) else {}
    active_execution = summary.get("planning_record", {}).get("status") == "present"
    if backlog_count and active_execution:
        status = "backgrounded-by-active-execution"
        recommendation = (
            "Continue current_execution_pressure first; inspect historical audit pressure only when the active plan points there."
        )
        sample_candidates: list[dict[str, Any]] = []
    elif backlog_count:
        status = "needs-prioritization"
        recommendation = compact_finished_work_inspection.get(
            "recommended_next_action",
            "Promote or explicitly route the highest-priority historical audit candidate.",
        )
        sample_candidates = enriched_candidates[:3]
    else:
        status = "quiet"
        recommendation = "No historical audit backlog needs current attention."
        sample_candidates = []
    return {
        "status": status,
        "current_lane_refs": sorted(active_refs),
        "candidate_count": backlog_count,
        "sample_candidates": sample_candidates,
        "omitted_candidate_count": max(backlog_count - len(sample_candidates), 0),
        "intent_validation_counts": {
            "follow_up_open_count": intent_counts.get("closeout_reconciliation", {}).get("follow_up_open_count", 0)
            if isinstance(intent_counts.get("closeout_reconciliation"), dict)
            else compact_intent_validation.get("closeout_reconciliation", {}).get("counts", {}).get("follow_up_open_count", 0),
            "closeout_needs_audit_count": intent_counts.get("closeout_needs_audit_count", 0),
            "landed_open_issue_count": intent_counts.get("landed_open_issue_count", 0),
        },
        "full_profile_candidate_count": len(full_candidates),
        "recommended_next_action": recommendation,
        "rule": "Historical audit residue is recoverable evidence; compact summary ranks it behind current execution unless it directly matches the active lane.",
        "detail": "Use `agentic-workspace summary --format json --verbose` for historical audit samples.",
    }


def _active_summary_issue_refs(summary: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    todo = summary.get("todo", {})
    if isinstance(todo, dict):
        for item in todo.get("active_items", []):
            if isinstance(item, dict):
                refs.update(_issue_refs_from_text(str(item.get("source", ""))))
                refs.update(_issue_refs_from_text(str(item.get("id", ""))))
                refs.update(_issue_refs_from_text(str(item.get("why_now", ""))))
    planning_record = summary.get("planning_record", {})
    if isinstance(planning_record, dict):
        for value in planning_record.get("minimal_refs", []):
            refs.update(_issue_refs_from_text(str(value)))
        task = planning_record.get("task", {})
        if isinstance(task, dict):
            refs.update(_issue_refs_from_text(str(task.get("id", ""))))
    return refs


def _issue_refs_from_text(text: str) -> set[str]:
    return {match.group(0) for match in re.finditer(r"#\d+", text)}


def _prioritized_historical_candidates(*, candidates: list[Any], active_refs: set[str]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidate for candidate in candidates if isinstance(candidate, dict)):
        reference_roles = candidate.get("reference_roles", {})
        closure_refs: set[str] = set()
        parent_refs: set[str] = set()
        if isinstance(reference_roles, dict):
            closure_refs.update(reference_roles.get("closure_refs", []) or [])
            by_role = reference_roles.get("by_role", {})
            if isinstance(by_role, dict):
                parent_refs.update(by_role.get("parent_intent", []) or [])
        superseded_by = candidate.get("superseded_by", [])
        if superseded_by:
            priority = "superseded"
            priority_rank = 3
        elif parent_refs & active_refs:
            priority = "same-parent-lane"
            priority_rank = 1
        elif closure_refs & active_refs:
            priority = "current-lane-match"
            priority_rank = 0
        else:
            priority = "historical-backlog"
            priority_rank = 2
        enriched.append(
            {
                "source_plan": candidate.get("source_plan", ""),
                "title": candidate.get("title", ""),
                "classification": candidate.get("classification", ""),
                "priority": priority,
                "priority_rank": priority_rank,
                "recency": {
                    "basis": "source_plan_mtime_desc",
                    "rank": index + 1,
                },
                "owner": candidate.get("recommended_owner", ""),
                "supersession_status": "superseded" if superseded_by else "active",
                "superseded_by": superseded_by,
                "recommended_action": candidate.get("recommended_action", ""),
            }
        )
    enriched.sort(key=lambda item: (item["priority_rank"], item["recency"]["rank"]))
    return enriched


def _compact_closeout_reconciliation(reconciliation: Any) -> dict[str, Any]:
    if not isinstance(reconciliation, dict):
        return {}
    items_by_state: dict[str, list[str]] = {
        "needs-audit": [],
        "evidence-present": [],
        "follow-up-open": [],
        "historical-baseline": [],
        "likely-premature-closeout": [],
    }
    for item in reconciliation.get("items", []):
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id", "")).strip()
        action_state = str(item.get("action_state", "")).strip()
        if item_id and action_state in items_by_state:
            items_by_state[action_state].append(item_id)
    sample_items_by_state = {key: value[:5] for key, value in items_by_state.items() if value}
    displayed_item_count = sum(len(value) for value in sample_items_by_state.values())
    return {
        "status": reconciliation.get("status", "absent"),
        "source_count": reconciliation.get("source_count", 0),
        "item_count": reconciliation.get("item_count", 0),
        "counts": reconciliation.get("counts", {}),
        "sample_items_by_state": sample_items_by_state,
        "omitted_item_count": max(0, sum(len(value) for value in items_by_state.values()) - displayed_item_count),
        "detail": "Use `agentic-workspace summary --format json --verbose` for full reconciliation sources and item ids.",
    }


def _compact_landed_open_issue_reconciliation(reconciliation: Any) -> dict[str, Any]:
    if not isinstance(reconciliation, dict):
        return {}
    items = reconciliation.get("items", [])
    if not isinstance(items, list):
        items = []
    max_items = 5
    return {
        "status": reconciliation.get("status", "absent"),
        "item_count": reconciliation.get("item_count", 0),
        "counts": reconciliation.get("counts", {}),
        "sample_items": items[:max_items],
        "omitted_item_count": max(0, len(items) - max_items),
        "detail": "Use `agentic-workspace summary --format json --verbose` for full landed-open issue evidence.",
    }


def _compact_external_work_reconciliation(reconciliation: Any) -> dict[str, Any]:
    if not isinstance(reconciliation, dict):
        return {}
    freshness = reconciliation.get("freshness", {})
    if isinstance(freshness, dict):
        freshness = {
            key: freshness[key]
            for key in (
                "status",
                "refreshed_at",
                "trust_scope",
                "refresh_after_mutation",
                "refresh_command",
                "fresh_enough_to_trust",
            )
            if key in freshness
        }
    else:
        freshness = {}
    return {
        "kind": reconciliation.get("kind", "planning-external-work-reconciliation/v1"),
        "status": reconciliation.get("status", "absent"),
        "primary_owner": reconciliation.get("primary_owner", ""),
        "freshness": freshness,
        "external_work_state": reconciliation.get("external_work_state", {}),
        "closeout_state": reconciliation.get("closeout_state", {}),
        "landed_open_state": reconciliation.get("landed_open_state", {}),
        "recommended_next_action": reconciliation.get("recommended_next_action", ""),
        "detail": "Use `agentic-workspace summary --format json --verbose` for provider rules and source detail.",
    }


def _compact_current_external_work(current_external_work: Any) -> dict[str, Any]:
    if not isinstance(current_external_work, dict):
        return {}
    items = current_external_work.get("items", [])
    if not isinstance(items, list):
        items = []
    max_items = 3
    compact = {
        "status": current_external_work.get("status", "absent"),
        "open_count": current_external_work.get("open_count", 0),
        "closed_count": current_external_work.get("closed_count", 0),
        "provider_count": current_external_work.get("provider_count", 0),
        "sample_items": items[:max_items],
        "omitted_item_count": max(0, len(items) - max_items),
        "detail": "Use `agentic-workspace summary --format json --verbose` for all external work items.",
    }
    if "invalid_reason" in current_external_work:
        compact["invalid_reason"] = current_external_work["invalid_reason"]
    return compact


def _compact_finished_work_inspection(contract: dict[str, Any]) -> dict[str, Any]:
    compact = dict(contract)
    inspections = compact.get("inspections", [])
    if isinstance(inspections, list):
        max_inspections = 5
        compact["inspections"] = [
            _compact_finished_work_inspection_item(item) for item in inspections[:max_inspections] if isinstance(item, dict)
        ]
        omitted_inspection_count = max(len(inspections) - max_inspections, 0)
    else:
        compact["inspections"] = []
        omitted_inspection_count = 0
    candidates = compact.get("derived_follow_up_candidates", [])
    if not isinstance(candidates, list):
        compact["derived_follow_up_candidates"] = []
        counts = dict(compact.get("counts", {})) if isinstance(compact.get("counts", {}), dict) else {}
        counts["omitted_inspection_count"] = omitted_inspection_count
        compact["counts"] = counts
        return compact
    max_items = 5
    compact["derived_follow_up_candidates"] = [
        _compact_finished_work_candidate(item) for item in candidates[:max_items] if isinstance(item, dict)
    ]
    omitted_count = max(len(candidates) - max_items, 0)
    counts = dict(compact.get("counts", {})) if isinstance(compact.get("counts", {}), dict) else {}
    counts["omitted_derived_follow_up_candidate_count"] = omitted_count
    counts["omitted_inspection_count"] = omitted_inspection_count
    compact["counts"] = counts
    if omitted_count or omitted_inspection_count:
        compact["detail"] = "Use `agentic-workspace summary --format json --verbose` for all finished-work inspection detail."
    return compact


def _compact_finished_work_inspection_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        key: item[key]
        for key in (
            "plan",
            "title",
            "classification",
            "closure_decision",
            "larger_intent_status",
            "tracked_refs",
            "non_closure_refs",
            "reason",
        )
        if key in item
    }


def _compact_finished_work_candidate(item: dict[str, Any]) -> dict[str, Any]:
    return {
        key: item[key]
        for key in (
            "source_plan",
            "title",
            "classification",
            "priority",
            "reason",
            "recommended_owner",
            "recommended_action",
            "supersession_status",
            "superseded_by",
            "reopened_by",
            "reference_roles",
        )
        if key in item
    }


def _compact_historical_audit_references(historical: Any) -> dict[str, Any]:
    if not isinstance(historical, dict):
        return {}
    source_count = int(historical.get("source_count", 0) or 0)
    return {
        "status": historical.get("status", "absent"),
        "source_count": source_count,
        "item_count": historical.get("item_count", 0),
        "follow_up_open_count": historical.get("follow_up_open_count", 0),
        "needs_audit_count": historical.get("needs_audit_count", 0),
        "likely_premature_closeout_count": historical.get("likely_premature_closeout_count", 0),
        "sources_omitted": source_count,
        "rule": historical.get("rule", ""),
        "detail": "Use `agentic-workspace summary --format json --verbose` for historical review source paths.",
    }


def _planning_surface_health(
    warnings: list[dict[str, Any]],
    *,
    collaboration_pressure: dict[str, Any] | None = None,
) -> dict[str, Any]:
    health_warnings: list[dict[str, str]] = []
    for warning in warnings:
        warning_class = str(warning.get("warning_class", "")).strip()
        path = str(warning.get("path", "")).strip()
        message = str(warning.get("message", "")).strip()
        suggested_fix = str(warning.get("suggested_fix", "")).strip() or _warning_remediation(warning_class) or ""
        health_warnings.append(
            {
                "warning_class": warning_class,
                "path": path,
                "message": message,
                "suggested_fix": suggested_fix,
            }
        )
    if not health_warnings:
        return {
            "status": "clean",
            "warning_count": 0,
            "recommended_next_action": "No planning-surface drift detected.",
            "warnings": [],
            "collaboration_pressure": collaboration_pressure or _empty_planning_collaboration_pressure(),
            "authoring_affordances": {
                "live_state_rule": PLANNING_STATE_LIVE_ONLY_RULE,
                "recovery_rule": (
                    "When planning state is invalid, inspect summary warnings first and make the smallest "
                    "schema-preserving correction; do not delete state.toml or execplans as the first move."
                ),
            },
        }
    first_fix = next((item["suggested_fix"] for item in health_warnings if item["suggested_fix"]), "")
    if not first_fix:
        first = health_warnings[0]
        first_fix = (
            f"Inspect {first['path']} and resolve {first['warning_class']} before relying on resumed planning state."
            if first["path"]
            else "Inspect the first planning warning before relying on resumed planning state."
        )
    return {
        "status": "not-clean",
        "warning_count": len(health_warnings),
        "recommended_next_action": first_fix,
        "recovery_required": True,
        "unsafe_to_continue_reason": (
            f"{health_warnings[0]['warning_class']} at {health_warnings[0]['path']}; "
            "resolve planning-surface health before treating the repo as safe to continue."
            if health_warnings[0]["path"]
            else f"{health_warnings[0]['warning_class']}; resolve planning-surface health before treating the repo as safe to continue."
        ),
        "warnings": health_warnings,
        "collaboration_pressure": collaboration_pressure or _empty_planning_collaboration_pressure(),
        "authoring_affordances": {
            "live_state_rule": PLANNING_STATE_LIVE_ONLY_RULE,
            "recovery_rule": (
                "When planning state is invalid, inspect summary warnings first and make the smallest "
                "schema-preserving correction; do not delete state.toml or execplans as the first move."
            ),
            "recovery_sequence": [
                "Run `agentic-workspace summary --target . --format json --verbose` and read `planning_surface_health.warnings`.",
                "Classify the warning as unsupported state shape, invalid plan content, missing file reference, or stale salvageable record.",
                "Prefer package lifecycle commands when they apply; otherwise edit only the named warning path and preserve evidence.",
                "Rerun `agentic-workspace summary --target . --format json` before continuing implementation.",
            ],
        },
    }


def _empty_planning_collaboration_pressure() -> dict[str, Any]:
    return {
        "kind": "planning-collaboration-pressure/v1",
        "status": "normal",
        "risk": "low",
        "shared_state_changed": False,
        "signals": [],
        "metrics": {
            "active_item_count": 0,
            "queued_item_count": 0,
            "active_execplan_count": 0,
            "state_line_count": 0,
            "changed_shared_surface_count": 0,
        },
        "recommended_next_action": "Keep live planning state compact and branch-local.",
        "rule": "This is a merge-pressure signal, not a lock or concurrency guarantee.",
    }


def _planning_collaboration_pressure(
    *,
    target_root: Path,
    active_items: list[dict[str, Any]],
    queued_items: list[dict[str, Any]],
    active_execplans: list[dict[str, str]],
    state: dict[str, Any] | None,
) -> dict[str, Any]:
    state_path = target_root / PLANNING_STATE_PATH
    state_line_count = len(state_path.read_text(encoding="utf-8", errors="replace").splitlines()) if state_path.exists() else 0
    changed_paths = _git_status_changed_paths(target_root)
    changed_shared_surfaces = [
        path
        for path in changed_paths
        if path == PLANNING_STATE_PATH.as_posix()
        or path.startswith(".agentic-workspace/planning/execplans/")
        or path.startswith(".agentic-workspace/planning/reviews/")
    ]
    active_item_count = len(active_items)
    queued_item_count = len(queued_items)
    active_execplan_count = len(active_execplans)
    signals: list[dict[str, str]] = []
    if active_item_count > 1:
        signals.append(
            {
                "id": "multiple-active-items",
                "summary": "More than one active planning item increases same-file merge pressure.",
                "suggested_action": "Prefer one active lane/execplan per branch or close unrelated active items.",
            }
        )
    if active_execplan_count > 1:
        signals.append(
            {
                "id": "multiple-active-execplans",
                "summary": "Multiple active execplans make continuation and merge ownership ambiguous.",
                "suggested_action": "Split unrelated work across branches or make only the current lane active.",
            }
        )
    if queued_item_count > 5:
        signals.append(
            {
                "id": "large-queued-set",
                "summary": "A large queued set makes state.toml a broader shared coordination hotspot.",
                "suggested_action": "Move speculative or deferred work to issues, docs, or roadmap candidates with compact entries.",
            }
        )
    if state_line_count > 120:
        signals.append(
            {
                "id": "large-state-file",
                "summary": "A large planning state file is harder to merge and review.",
                "suggested_action": "Keep state.toml live/selectable only; distill completed residue to Memory, docs, issues, or checks.",
            }
        )
    if changed_shared_surfaces:
        signals.append(
            {
                "id": "shared-planning-surfaces-changed",
                "summary": "Git status shows changed live Planning surfaces.",
                "suggested_action": "Before closeout or push, confirm these edits are intentional and still branch-local.",
            }
        )

    high_ids = {"multiple-active-items", "multiple-active-execplans", "shared-planning-surfaces-changed"}
    risk = "high" if any(signal["id"] in high_ids for signal in signals) else "medium" if signals else "low"
    status = "attention" if signals else "normal"
    if not signals:
        recommended_next_action = "Keep live planning state compact and branch-local."
    else:
        recommended_next_action = signals[0]["suggested_action"]
    return {
        "kind": "planning-collaboration-pressure/v1",
        "status": status,
        "risk": risk,
        "shared_state_changed": bool(changed_shared_surfaces),
        "signals": signals,
        "metrics": {
            "active_item_count": active_item_count,
            "queued_item_count": queued_item_count,
            "active_execplan_count": active_execplan_count,
            "state_line_count": state_line_count,
            "changed_shared_surface_count": len(changed_shared_surfaces),
        },
        "changed_shared_surfaces": changed_shared_surfaces[:8],
        "recommended_next_action": recommended_next_action,
        "rule": "This is a merge-pressure signal, not a lock or concurrency guarantee.",
    }


def _prep_only_changed_path_warnings(*, target_root: Path, planning_record: dict[str, Any]) -> list[dict[str, str]]:
    prep_only_contract = planning_record.get("prep_only_contract", {})
    if not isinstance(prep_only_contract, dict) or prep_only_contract.get("is_prep_only") is not True:
        return []
    changed_paths = _git_status_changed_paths(target_root)
    if not changed_paths:
        return []
    violating_paths = [
        path
        for path in changed_paths
        if not path.startswith(".agentic-workspace/planning/")
        and path not in {"TODO.md", "ROADMAP.md"}
        and path != ".agentic-workspace/planning/state.toml"
    ]
    if not violating_paths:
        return []
    return [
        {
            "warning_class": "prep_only_scope_violation",
            "path": ", ".join(violating_paths[:8]),
            "message": (
                "Active prep-only planning mode is present, but git status shows changed files outside canonical Planning surfaces."
            ),
            "suggested_fix": (
                "Stop implementation work, move any durable handoff into Planning, and revert or explicitly justify "
                "non-planning file changes before closeout."
            ),
        }
    ]


def _git_status_changed_paths(target_root: Path) -> list[str]:
    if not (target_root / ".git").exists():
        return []
    try:
        completed = subprocess.run(
            ["git", "-C", str(target_root), "status", "--short", "--untracked-files=all"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if completed.returncode != 0:
        return []
    paths: list[str] = []
    for line in completed.stdout.splitlines():
        if len(line) < 4:
            continue
        raw_path = line[3:].strip()
        if " -> " in raw_path:
            raw_path = raw_path.split(" -> ", 1)[1].strip()
        normalized = raw_path.replace("\\", "/")
        if normalized:
            paths.append(normalized)
    return paths


def _completed_execplan_warnings(completed_execplans: list[dict[str, Any]]) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    for plan in completed_execplans:
        path = str(plan.get("path", "")).strip()
        if not path:
            continue
        warnings.append(
            {
                "warning_class": "archive_accumulation_drift",
                "path": path,
                "message": (
                    "Completed execplan remains in the live execplans directory; "
                    "archive it with `agentic-planning archive-plan` or return it to active status."
                ),
            }
        )
    return warnings


def _planning_state_v1_warnings(*, target_root: Path, state: dict[str, Any] | None) -> list[dict[str, str]]:
    del target_root
    if not isinstance(state, dict):
        return []
    if state.get("schema_version") != PLANNING_STATE_SCHEMA_VERSION:
        return []
    warnings: list[dict[str, str]] = []
    if state.get("kind") != PLANNING_STATE_KIND:
        warnings.append(_planning_state_v1_warning("kind", 'planning-state/v1 requires kind = "agentic-planning-state".'))

    for bucket_path, item in _planning_state_v1_items(state):
        item_id = str(item.get("id", "")).strip() or "<missing-id>"
        maturity = str(item.get("maturity", "")).strip()
        status = str(item.get("status", "")).strip()
        if _is_completed_or_historical_state_item(maturity=maturity, status=status):
            warnings.append(_completed_or_historical_state_warning(bucket_path=bucket_path, item_id=item_id))
            continue
        if maturity not in PLANNING_STATE_MATURITIES:
            warnings.append(
                _planning_state_v1_warning(
                    bucket_path,
                    f"planning-state/v1 item {item_id} must use one maturity from {sorted(PLANNING_STATE_MATURITIES)}.",
                )
            )
            continue
        if status and status not in PLANNING_STATE_STATUSES:
            warnings.append(
                _planning_state_v1_warning(
                    bucket_path,
                    f"planning-state/v1 item {item_id} status must be empty or one of {sorted(PLANNING_STATE_STATUSES)}.",
                )
            )
        warnings.extend(_planning_state_v1_item_warnings(bucket_path=bucket_path, item_id=item_id, item=item, maturity=maturity))
        if _is_reconstructable_closed_state_history(bucket_path=bucket_path, item=item, maturity=maturity, status=status):
            warnings.append(
                {
                    "warning_class": "closed_work_history_residue",
                    "path": f"{PLANNING_STATE_PATH.as_posix()}#{bucket_path}.{item_id}",
                    "message": (
                        f"closed item {item_id} is reconstructable history; remove it from first-line state.toml "
                        "unless it carries non-reconstructable future routing."
                    ),
                }
            )
    return warnings


def _is_completed_or_historical_state_item(*, maturity: str, status: str) -> bool:
    return maturity in {"closed", "completed"} or status in {"done", "dismissed", "closed", "completed"}


def _completed_or_historical_state_warning(*, bucket_path: str, item_id: str) -> dict[str, str]:
    return {
        "warning_class": "historical_work_in_live_planning_state",
        "path": f"{PLANNING_STATE_PATH.as_posix()}#{bucket_path}.{item_id}",
        "message": (
            f"planning-state/v1 item {item_id} is completed, dismissed, closed, or historical work; "
            "remove it from state.toml and keep the evidence in archived execplans, external evidence, Memory, or docs."
        ),
        "suggested_fix": PLANNING_STATE_LIVE_ONLY_RULE,
    }


def _planning_state_v1_items(state: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    items: list[tuple[str, dict[str, Any]]] = []
    active = state.get("active")
    if isinstance(active, dict):
        raw_execplans = active.get("execplans", [])
        if isinstance(raw_execplans, list):
            items.extend(("active.execplans", item) for item in raw_execplans if isinstance(item, dict))
    todo = state.get("todo")
    if isinstance(todo, dict):
        for bucket in ("active_items", "queued_items"):
            raw_items = todo.get(bucket, [])
            if isinstance(raw_items, list):
                items.extend((f"todo.{bucket}", item) for item in raw_items if isinstance(item, dict))
    roadmap = state.get("roadmap")
    if isinstance(roadmap, dict):
        for bucket in ("lanes", "candidates"):
            raw_items = roadmap.get(bucket, [])
            if isinstance(raw_items, list):
                items.extend((f"roadmap.{bucket}", item) for item in raw_items if isinstance(item, dict))
    raw_work_items = state.get("work_items", [])
    if isinstance(raw_work_items, list):
        items.extend(("work_items", item) for item in raw_work_items if isinstance(item, dict))
    return items


def _state_active_items(state: dict[str, Any]) -> list[dict[str, Any]]:
    active_items: list[dict[str, Any]] = []
    active = state.get("active")
    if isinstance(active, dict):
        raw_execplans = active.get("execplans", [])
        if isinstance(raw_execplans, list):
            for raw in raw_execplans:
                if not isinstance(raw, dict):
                    continue
                item = dict(raw)
                item.setdefault("maturity", "active")
                item.setdefault("status", "active")
                if "surface" not in item and "path" in item:
                    item["surface"] = item["path"]
                active_items.append(item)
    todo = state.get("todo")
    if isinstance(todo, dict):
        raw_items = todo.get("active_items", [])
        if isinstance(raw_items, list):
            active_items.extend(item for item in raw_items if isinstance(item, dict))
    return active_items


def _state_queued_items(state: dict[str, Any]) -> list[dict[str, Any]]:
    queued_items: list[dict[str, Any]] = []
    raw_work_items = state.get("work_items", [])
    if isinstance(raw_work_items, list):
        for raw in raw_work_items:
            if not isinstance(raw, dict):
                continue
            if str(raw.get("type", "")).strip() == "lane":
                continue
            maturity = str(raw.get("maturity", "")).strip()
            status = str(raw.get("status", "")).strip()
            if maturity in {"active", "closed"} or status in {"active", "done", "dismissed", "closed", "completed"}:
                continue
            queued_items.append(raw)
    todo = state.get("todo")
    if isinstance(todo, dict):
        raw_items = todo.get("queued_items", [])
        if isinstance(raw_items, list):
            queued_items.extend(item for item in raw_items if isinstance(item, dict))
    return queued_items


_CLOSED_PLANNING_STATUSES = {"closed", "completed", "dismissed", "done"}


def _is_closed_planning_state_item(item: dict[str, Any]) -> bool:
    maturity = str(item.get("maturity", "")).strip().lower()
    status = str(item.get("status", "")).strip().lower()
    return maturity == "closed" or status in _CLOSED_PLANNING_STATUSES


def _roadmap_candidate_key(item: dict[str, Any]) -> tuple[str, str]:
    priority = str(item.get("priority", "")).strip()
    summary = str(item.get("summary") or item.get("title") or "").strip()
    return priority, summary


def _closed_roadmap_candidate_keys(state: dict[str, Any]) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    raw_work_items = state.get("work_items", [])
    if isinstance(raw_work_items, list):
        for item in raw_work_items:
            if isinstance(item, dict) and str(item.get("type", "")).strip() == "lane" and _is_closed_planning_state_item(item):
                keys.add(_roadmap_candidate_key(item))
    roadmap = state.get("roadmap")
    if isinstance(roadmap, dict):
        raw_lanes = roadmap.get("lanes", [])
        if isinstance(raw_lanes, list):
            for item in raw_lanes:
                if isinstance(item, dict) and _is_closed_planning_state_item(item):
                    keys.add(_roadmap_candidate_key(item))
    return keys


def _state_roadmap_lanes(state: dict[str, Any]) -> list[dict[str, Any]]:
    lanes: list[dict[str, Any]] = []
    raw_work_items = state.get("work_items", [])
    if isinstance(raw_work_items, list):
        lanes.extend(
            _normalize_roadmap_lane_record(item)
            for item in raw_work_items
            if isinstance(item, dict) and str(item.get("type", "")).strip() == "lane" and not _is_closed_planning_state_item(item)
        )
    roadmap = state.get("roadmap")
    if isinstance(roadmap, dict):
        raw_lanes = roadmap.get("lanes", [])
        if isinstance(raw_lanes, list):
            lanes.extend(
                _normalize_roadmap_lane_record(item)
                for item in raw_lanes
                if isinstance(item, dict) and not _is_closed_planning_state_item(item)
            )
    return lanes


def _state_roadmap_candidates(state: dict[str, Any]) -> list[dict[str, Any]]:
    roadmap = state.get("roadmap")
    if not isinstance(roadmap, dict):
        return []
    raw_candidates = roadmap.get("candidates", [])
    if not isinstance(raw_candidates, list):
        return []
    closed_keys = _closed_roadmap_candidate_keys(state)
    return [
        item
        for item in raw_candidates
        if isinstance(item, dict) and not _is_closed_planning_state_item(item) and _roadmap_candidate_key(item) not in closed_keys
    ]


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _closed_state_path_is_archive(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return "/execplans/archive/" in normalized or normalized.startswith(".agentic-workspace/planning/execplans/archive/")


def _closed_state_residue_owner(item: dict[str, Any]) -> str:
    return str(
        item.get("residue_owner") or item.get("residue owner") or item.get("residue_routing") or item.get("residue routing") or ""
    ).strip()


def _closed_state_has_future_relevant_routing(item: dict[str, Any]) -> bool:
    owner = _closed_state_residue_owner(item)
    if not owner or owner == "archive" or _closed_state_path_is_archive(owner):
        return False
    return bool(str(item.get("residue_promotion_trigger") or item.get("promotion_signal") or "").strip())


def _is_reconstructable_closed_state_history(*, bucket_path: str, item: dict[str, Any], maturity: str, status: str) -> bool:
    if bucket_path != "work_items" or maturity != "closed" or status not in {"done", "dismissed"}:
        return False
    if _closed_state_has_future_relevant_routing(item):
        return False
    path = str(item.get("path") or item.get("surface") or item.get("execplan") or "").strip()
    if _closed_state_path_is_archive(path):
        return True
    residue = _planning_state_residue_value(item).strip().lower()
    owner = _closed_state_residue_owner(item)
    if residue in EXECPLAN_DURABLE_RESIDUE_OWNERLESS_STATUSES or owner == "archive" or _closed_state_path_is_archive(owner):
        return True
    return True


def _planning_state_v1_item_warnings(*, bucket_path: str, item_id: str, item: dict[str, Any], maturity: str) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    for role_field in PLANNING_STATE_ROLE_FIELDS:
        if role_field in item and not _non_empty_string(item.get(role_field)):
            warnings.append(
                _planning_state_v1_warning(
                    bucket_path,
                    f"planning-state/v1 item {item_id} {role_field} must be a non-empty string.",
                )
            )
    if "handoff_ready" in item and not isinstance(item.get("handoff_ready"), bool):
        warnings.append(_planning_state_v1_warning(bucket_path, f"planning-state/v1 item {item_id} handoff_ready must be true or false."))
    if maturity == "ready":
        for field in ("next_action", "done_when", "proof", "review_role"):
            if not item.get(field):
                warnings.append(_planning_state_v1_warning(bucket_path, f"ready item {item_id} requires {field}."))
        if not (item.get("refs") or _non_empty_string(item.get("owner_role")) or _non_empty_string(item.get("owner"))):
            warnings.append(_planning_state_v1_warning(bucket_path, f"ready item {item_id} requires refs, owner_role, or owner."))
        if item.get("handoff_ready") is not True:
            warnings.append(_planning_state_v1_warning(bucket_path, f"ready item {item_id} requires handoff_ready = true."))
    if maturity == "active":
        surface = str(item.get("execplan") or item.get("surface") or item.get("path") or "").strip()
        if not surface or not _surface_execplan_reference(surface):
            warnings.append(_planning_state_v1_warning(bucket_path, f"active item {item_id} requires an execplan or execplan surface."))
    return warnings


def _planning_state_role_metadata(item: dict[str, Any] | None) -> dict[str, Any]:
    if not item:
        return {}
    metadata: dict[str, Any] = {}
    for role_field in PLANNING_STATE_ROLE_FIELDS:
        value = item.get(role_field)
        if _non_empty_string(value):
            metadata[role_field] = str(value).strip()
    if isinstance(item.get("handoff_ready"), bool):
        metadata["handoff_ready"] = item["handoff_ready"]
    return metadata


def _planning_state_item_summary(*, bucket_path: str, item: dict[str, Any]) -> dict[str, Any]:
    item_id = str(item.get("id", "")).strip()
    title = str(item.get("title") or item.get("summary") or "").strip()
    maturity = str(item.get("maturity", "")).strip()
    status = str(item.get("status", "")).strip()
    surface = str(item.get("execplan") or item.get("surface") or item.get("path") or "").strip()
    refs = [str(ref).strip() for ref in item.get("refs", []) if str(ref).strip()] if isinstance(item.get("refs"), list) else []
    issues = [str(issue).strip() for issue in item.get("issues", []) if str(issue).strip()] if isinstance(item.get("issues"), list) else []
    summary: dict[str, Any] = {
        "id": item_id,
        "title": title,
        "maturity": maturity,
        "status": status,
        "source_bucket": bucket_path,
    }
    for key, value in (
        ("surface", surface),
        ("next_action", str(item.get("next_action", "")).strip()),
        ("why_now", str(item.get("why_now", "")).strip()),
        ("reason", str(item.get("reason", "")).strip()),
        ("suggested_first_slice", str(item.get("suggested_first_slice", "")).strip()),
        ("durable_residue", _planning_state_residue_value(item)),
        ("residue_owner", str(item.get("residue_owner") or item.get("residue owner") or "").strip()),
        ("residue_routing", str(item.get("residue_routing") or item.get("residue routing") or "").strip()),
    ):
        if value:
            summary[key] = value
    if refs:
        summary["refs"] = refs
    if issues:
        summary["issues"] = issues
    for key in (
        "adaptive_assurance",
        "traceability_refs",
        "control_gates",
        "implementation_blockers",
        "risk_registry_refs",
        "invariant_refs",
        "test_data_policy",
        "layer_scaffold",
        "architecture_decision_promotion",
        "threat_failure_aids",
    ):
        value = item.get(key)
        if isinstance(value, (dict, list)) and value:
            summary[key] = value
    role_metadata = _planning_state_role_metadata(item)
    if role_metadata:
        summary["role_metadata"] = role_metadata
    return summary


def _planning_state_residue_routed(item: dict[str, Any]) -> bool:
    return bool(_planning_state_residue_value(item))


def _planning_state_residue_value(item: dict[str, Any]) -> str:
    residue = item.get("durable_residue") or item.get("residue") or item.get("closure")
    if isinstance(residue, dict):
        return str(residue.get("status") or residue.get("route") or residue.get("owner") or "").strip()
    return str(residue or "").strip()


def _planning_work_maturity_projection(*, state: dict[str, Any] | None, active_execplans: list[dict[str, str]]) -> dict[str, Any]:
    buckets: dict[str, list[dict[str, Any]]] = {
        "active_execplans": [],
        "ready_slices": [],
        "needs_shaping": [],
        "deferred_lanes": [],
        "blocked_items": [],
        "closed_items": [],
        "residue_routing_needed": [],
    }
    seen_active_surfaces: set[str] = set()
    for bucket_path, item in _planning_state_v1_items(state or {}):
        summary = _planning_state_item_summary(bucket_path=bucket_path, item=item)
        maturity = str(item.get("maturity", "")).strip()
        status = str(item.get("status", "")).strip()
        if _is_completed_or_historical_state_item(maturity=maturity, status=status):
            continue
        if status == "blocked":
            buckets["blocked_items"].append(summary)
            continue
        if status == "deferred":
            buckets["deferred_lanes"].append(summary)
            continue
        if maturity == "closed":
            if not _planning_state_residue_routed(item):
                buckets["residue_routing_needed"].append(summary)
            else:
                buckets["closed_items"].append(summary)
            continue
        if maturity == "active" or status == "active":
            buckets["active_execplans"].append(summary)
            surface = str(summary.get("surface", "")).strip()
            if surface:
                seen_active_surfaces.add(surface)
            continue
        if maturity == "ready":
            buckets["ready_slices"].append(summary)
            continue
        if maturity in {"idea", "candidate", "shaped"}:
            buckets["needs_shaping"].append(summary)

    for execplan in active_execplans:
        surface = str(execplan.get("path", "")).strip()
        if surface and surface not in seen_active_surfaces:
            buckets["active_execplans"].append(
                {
                    "id": Path(surface).name.removesuffix(".plan.json").removesuffix(".md"),
                    "title": "",
                    "maturity": "active",
                    "status": str(execplan.get("status", "")).strip(),
                    "source_bucket": "execplans.active",
                    "surface": surface,
                }
            )

    counts = {name: len(items) for name, items in buckets.items()}
    status = "idle"
    recommended_next_action = "No explicit maturity work is active or queued."
    if buckets["active_execplans"]:
        status = "active"
        recommended_next_action = "Continue the active execplan from planning_record or handoff_contract."
    elif buckets["ready_slices"]:
        status = "ready"
        recommended_next_action = "Promote or execute the highest-priority ready slice."
    elif buckets["blocked_items"]:
        status = "blocked"
        recommended_next_action = "Resolve blocked planning items before promoting new broad work."
    elif buckets["residue_routing_needed"]:
        status = "maintenance"
        recommended_next_action = "Route durable residue for closed planning items before treating them as settled."
    elif buckets["needs_shaping"]:
        status = "needs-shaping"
        recommended_next_action = "Shape the next candidate before promoting it to active execution."
    elif buckets["deferred_lanes"]:
        status = "deferred"
        recommended_next_action = "No ready slice; deferred lanes remain background planning state."
    return {
        "status": status,
        **buckets,
        "counts": counts,
        "recommended_next_action": recommended_next_action,
        "rule": "Explicit planning-state maturity and status fields drive this projection; storage bucket location is not maturity authority.",
    }


def _next_role_needed_from_metadata(role_metadata: dict[str, Any]) -> str:
    if not role_metadata:
        return ""
    if role_metadata.get("handoff_ready") is True:
        return str(role_metadata.get("delivery_role") or role_metadata.get("owner_role") or "implementation").strip()
    if role_metadata.get("review_role"):
        return str(role_metadata["review_role"]).strip()
    if role_metadata.get("strategy_role"):
        return str(role_metadata["strategy_role"]).strip()
    return ""


def _planning_state_v1_warning(path: str, message: str, *, suggested_fix: str = "") -> dict[str, str]:
    warning = {
        "warning_class": "planning_state_v1_schema",
        "path": f"{PLANNING_STATE_PATH.as_posix()}#{path}",
        "message": message,
    }
    if suggested_fix:
        warning["suggested_fix"] = suggested_fix
    return warning


def _unsupported_planning_state_activation_shape_warnings(
    *,
    target_root: Path,
    state: dict[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(state, dict):
        return []
    warnings: list[dict[str, str]] = []
    state_path = target_root / PLANNING_STATE_PATH
    for section_name, bucket_name in (("active", "execplans"), ("queued", "execplans")):
        section = state.get(section_name)
        if not isinstance(section, dict):
            continue
        raw_items = section.get(bucket_name, [])
        if not isinstance(raw_items, list):
            continue
        for raw in raw_items:
            if isinstance(raw, dict):
                continue
            if not isinstance(raw, str) or not raw.strip():
                continue
            candidate = target_root / ".agentic-workspace" / "planning" / "execplans" / raw.strip()
            exists_suffix = " and the referenced file exists" if candidate.exists() else ""
            warnings.append(
                {
                    "warning_class": "planning_state_unsupported_activation_shape",
                    "path": state_path.as_posix(),
                    "message": (
                        f"`[{section_name}].{bucket_name}` contains string reference `{raw}`{exists_suffix}, "
                        "but current planning state expects item objects in `todo.active_items` or `todo.queued_items`. "
                        "Do not delete `state.toml` as the first recovery step; preserve the evidence and make the "
                        "smallest schema-preserving correction."
                    ),
                    "suggested_fix": (
                        "Run `agentic-workspace summary --target . --format json` to inspect all warnings, then recover with "
                        "`agentic-planning new-plan --id <id> --title <title> --activate`, "
                        'or migrate the reference to `{ id = "<id>", maturity = "active", status = "active", '
                        'surface = ".agentic-workspace/planning/execplans/<plan>.plan.json" }`.'
                    ),
                }
            )
    return warnings


def _unregistered_execplan_warnings(
    *,
    target_root: Path,
    state: dict[str, Any] | None,
    plan_files: list[Path],
    active_items: list[dict[str, Any]],
    queued_items: list[dict[str, Any]],
    roadmap_lanes: list[dict[str, Any]],
    roadmap_candidates: list[dict[str, Any]],
) -> list[dict[str, str]]:
    registered_refs = _registered_execplan_refs(
        target_root=target_root,
        state=state,
        planning_items=[*active_items, *queued_items, *roadmap_lanes, *roadmap_candidates],
    )
    warnings: list[dict[str, str]] = []
    for path in sorted(plan_files):
        if path.name in {"README.md", "TEMPLATE.md", "TEMPLATE.plan.json"}:
            continue
        relative = path.relative_to(target_root).as_posix()
        if _execplan_equivalent_refs(relative) & registered_refs:
            continue
        warnings.append(
            {
                "warning_class": "execplan_unregistered",
                "path": relative,
                "message": (
                    "Live execplan file is not registered in planning state or TODO linkage; agents may miss it and "
                    "`summary` cannot treat it as reliable continuation state."
                ),
                "suggested_fix": (
                    "Register the plan with `agentic-planning new-plan --id <id> --title <title> --target . "
                    "--activate --format json`, migrate an existing state row to point at this file, or archive it if it is closed."
                ),
            }
        )
    return warnings


def _registered_execplan_refs(
    *,
    target_root: Path,
    state: dict[str, Any] | None,
    planning_items: list[dict[str, Any]],
) -> set[str]:
    refs: set[str] = set()

    def add_ref(raw: object) -> None:
        if not isinstance(raw, str) or not raw.strip():
            return
        normalized = _normalize_execplan_ref(target_root=target_root, raw=raw)
        if normalized:
            refs.update(_execplan_equivalent_refs(normalized))

    for item in planning_items:
        for key in ("surface", "path"):
            add_ref(item.get(key))
        raw_refs = item.get("refs", [])
        if isinstance(raw_refs, list):
            for ref in raw_refs:
                add_ref(ref)

    if isinstance(state, dict):
        for section_name in ("active", "queued"):
            section = state.get(section_name)
            if not isinstance(section, dict):
                continue
            raw_execplans = section.get("execplans", [])
            if not isinstance(raw_execplans, list):
                continue
            for raw in raw_execplans:
                if isinstance(raw, str):
                    add_ref(raw)
                elif isinstance(raw, dict):
                    add_ref(raw.get("surface"))
                    add_ref(raw.get("path"))

    return refs


def _normalize_execplan_ref(*, target_root: Path, raw: str) -> str:
    value = raw.strip().replace("\\", "/")
    match = re.search(r"\.agentic-workspace/planning/execplans/[A-Za-z0-9._/\-]+\.(?:md|plan\.json)", value)
    if match:
        value = match.group(0)
    elif value.endswith((".md", ".plan.json")) and "/" not in value:
        value = f".agentic-workspace/planning/execplans/{value}"
    elif Path(value).is_absolute():
        try:
            value = Path(value).resolve().relative_to(target_root.resolve()).as_posix()
        except ValueError:
            return ""
    if not value.startswith(".agentic-workspace/planning/execplans/"):
        return ""
    if "/archive/" in value:
        return ""
    return value


def _execplan_equivalent_refs(relative_path: str) -> set[str]:
    refs = {relative_path}
    if relative_path.endswith(".plan.json"):
        refs.add(relative_path[: -len(".plan.json")] + ".md")
    elif relative_path.endswith(".md"):
        refs.add(relative_path[: -len(".md")] + ".plan.json")
    return refs


def _planning_handoff_schema() -> dict[str, Any]:
    return {
        "schema_version": "planning-handoff-schema/v1",
        "canonical_doc": ".agentic-workspace/docs/execution-flow-contract.md",
        "command": "agentic-planning handoff --format json",
        "shared_fields": [
            "kind",
            "schema",
            "target_root",
            "handoff_contract",
            "warnings",
            "warning_count",
        ],
        "required_worker_packet_fields": [
            "intent",
            "constraints",
            "read_first_refs",
            "owned_scope",
            "proof_expectations",
            "stop_conditions",
            "return_contract",
            "target_posture",
        ],
        "ready_worker_prompt_field": "handoff_contract.ready_worker_prompt",
        "unavailable_fallback": (
            "If no active planning record exists, create or select a bounded execplan before delegating implementation; "
            "do not invent a parallel handoff plan from chat alone."
        ),
        "rules": [
            "derive delegated worker handoff from the active planning record instead of authoring a second durable plan",
            "treat runtime delegation method as tool-owned and agent-agnostic",
            "keep capability posture typed and advisory so runtime resolution stays portable",
            "keep worker closure bounded; lane shaping and roadmap routing stay orchestrator-owned",
            "use the handoff packet to preserve execution bounds, stop conditions, and return-with residue instead of reconstructing them from chat",
        ],
    }


def _intent_validation_contract(
    *,
    target_root: Path,
    active_items: list[dict[str, Any]],
    active_execplans: list[dict[str, str]],
    roadmap_lanes: list[dict[str, Any]],
) -> dict[str, Any]:
    surface_index = _planning_surface_reference_index(target_root)
    external_evidence = _load_external_intent_evidence(target_root)
    signals: list[dict[str, Any]] = []

    internal_signals = _internal_continuation_signals(
        target_root=target_root,
        roadmap_lanes=roadmap_lanes,
    )
    signals.extend(internal_signals)
    if external_evidence.get("status") == "invalid":
        signals.append(
            {
                "kind": "external_evidence_invalid",
                "severity": "warning",
                "path": external_evidence.get("path", ""),
                "message": str(external_evidence.get("reason", "optional external intent evidence could not be loaded")),
                "refs": [external_evidence.get("path", "")],
            }
        )

    tracked_open = 0
    untracked_open = 0
    external_open = 0
    external_closed = 0
    lower_trust_closeouts = 0
    closed_residue_items: list[dict[str, Any]] = []
    open_residue_items: list[dict[str, Any]] = []
    external_items = external_evidence.get("items", [])
    if isinstance(external_items, list):
        for item in external_items:
            if not isinstance(item, dict):
                continue
            item_id = str(item.get("id", "")).strip()
            if not item_id:
                continue
            refs = _reference_locations(token=item_id, surface_index=surface_index)
            active_refs = [ref for ref in refs if _is_live_planning_tracking_ref(ref)]
            if _external_status_is_open(item.get("status")):
                external_open += 1
                open_residue_items.append(item)
                if active_refs:
                    tracked_open += 1
                else:
                    untracked_open += 1
                    signals.append(
                        {
                            "kind": "external_open_untracked",
                            "severity": "warning",
                            "path": external_evidence.get("path", ""),
                            "message": (
                                f"Open external planning item {item_id} is not represented in active or candidate checked-in planning state."
                            ),
                            "refs": [external_evidence.get("path", ""), *refs],
                        }
                    )
            elif _external_status_is_closed(item.get("status")):
                external_closed += 1
                if str(item.get("planning_residue_expected", "")).strip().lower() != "required":
                    continue
                if refs:
                    closed_residue_items.append(item)
                    continue
                closed_residue_items.append(item)
                lower_trust_closeouts += 1
                signals.append(
                    {
                        "kind": "closed_without_planning_residue",
                        "severity": "warning",
                        "path": external_evidence.get("path", ""),
                        "message": (
                            f"Closed external planning item {item_id} has no visible checked-in planning residue; treat closeout trust as lower."
                        ),
                        "refs": [external_evidence.get("path", "")],
                    }
                )

    closeout_reconciliation = _closeout_reconciliation_from_reviews(
        target_root=target_root,
        closed_residue_items=closed_residue_items,
    )
    landed_open_issue_reconciliation = _landed_open_issue_reconciliation(
        target_root=target_root,
        open_residue_items=open_residue_items,
        surface_index=surface_index,
    )
    counts = {
        "internal_dangling_count": len(internal_signals),
        "tracked_external_open_count": tracked_open,
        "untracked_external_open_count": untracked_open,
        "lower_trust_closeout_count": lower_trust_closeouts,
        "closeout_reconciled_count": closeout_reconciliation["counts"]["reconciled_count"],
        "closeout_needs_audit_count": closeout_reconciliation["counts"]["needs_audit_count"],
        "landed_open_issue_count": landed_open_issue_reconciliation["counts"]["implemented_and_unclosed_count"],
        "attention_count": len(signals),
    }
    current_external_work = {
        "status": external_evidence.get("status", "absent"),
        "path": external_evidence.get("path", ""),
        "storage": external_evidence.get("storage", ""),
        "kind": external_evidence.get("kind", ""),
        "systems": external_evidence.get("systems", []),
        "refreshed_at": external_evidence.get("refreshed_at", ""),
        "refresh_metadata": external_evidence.get("refresh_metadata", {}),
        "trust_scope": "snapshot",
        "snapshot_rule": EXTERNAL_INTENT_SNAPSHOT_RULE,
        "refresh_after_mutation": external_evidence.get("status") == "loaded",
        "refresh_command": EXTERNAL_INTENT_REFRESH_COMMAND,
        "item_count": external_evidence.get("item_count", 0),
        "open_count": external_open,
        "closed_count": external_closed,
        "tracked_open_count": tracked_open,
        "untracked_open_count": untracked_open,
        "provider_rule": (
            "Core planning only consumes provider-agnostic external work evidence; host-specific trackers belong in optional adapters."
        ),
        "reason": external_evidence.get("reason", ""),
    }
    historical_audit_references = {
        "status": closeout_reconciliation.get("status", "absent"),
        "source_count": closeout_reconciliation.get("source_count", 0),
        "sources": closeout_reconciliation.get("sources", []),
        "item_count": closeout_reconciliation.get("item_count", 0),
        "follow_up_open_count": closeout_reconciliation.get("counts", {}).get("follow_up_open_count", 0),
        "needs_audit_count": closeout_reconciliation.get("counts", {}).get("needs_audit_count", 0),
        "likely_premature_closeout_count": closeout_reconciliation.get("counts", {}).get(
            "likely_premature_closeout_count",
            0,
        ),
        "rule": (
            "Historical closeout and review evidence is audit context; it is not current external-work state "
            "unless refreshed through provider-agnostic external evidence."
        ),
    }
    recommended_next_action = "No dangling larger intent or lower-trust closeout signals detected."
    if untracked_open:
        recommended_next_action = (
            "Route open external planning items into checked-in active or candidate planning state before treating the repo as quiet."
        )
    elif landed_open_issue_reconciliation["counts"]["implemented_and_unclosed_count"]:
        recommended_next_action = (
            "Review open external items with checked-in landed evidence and close or reroute the tracker item explicitly."
        )
    elif closeout_reconciliation["counts"]["likely_premature_closeout_count"]:
        recommended_next_action = "Inspect likely premature closeouts before treating recently closed work as settled."
    elif closeout_reconciliation["counts"]["needs_audit_count"]:
        recommended_next_action = "Audit unreconciled lower-trust closeouts or add a checked-in reconciliation artifact."
    elif closeout_reconciliation["counts"]["follow_up_open_count"] and external_open:
        recommended_next_action = "Continue the open follow-ups identified by lower-trust closeout reconciliation."
    elif lower_trust_closeouts:
        recommended_next_action = "Review lower-trust closeout signals before assuming recently closed work is fully evidenced."
    elif internal_signals:
        recommended_next_action = "Restore missing checked-in continuation ownership for partially archived intent."

    promotion_action = {
        "action": "promote-external-work-to-planning",
        "summary": (
            "Create one checked-in active execplan/state entry for selected untracked external work."
            if untracked_open
            else "No external-work promotion is currently needed."
        ),
        "command": "agentic-workspace summary --format json",
        "risk": "planning mutation; inspect selected external items before editing checked-in planning state",
        "required_inputs": ["selected external item ids", "requested outcome", "proof expectations", "owner surface"],
        "target_surfaces": [
            ".agentic-workspace/planning/state.toml",
            ".agentic-workspace/planning/execplans/<lane>.plan.json",
        ],
        "state_rule": "Represent promoted work once as the active item and point it at one execplan; do not duplicate active state.",
        "provider_neutral": True,
        "next_proof": "rerun summary and planning doctor after promotion; active_count should be one for a broad active lane",
    }
    promotion_action["run"] = promotion_action["command"]

    external_work_reconciliation = {
        "kind": "planning-external-work-reconciliation/v1",
        "status": (
            "attention"
            if untracked_open
            or landed_open_issue_reconciliation["counts"]["implemented_and_unclosed_count"]
            or closeout_reconciliation["counts"]["likely_premature_closeout_count"]
            or closeout_reconciliation["counts"]["needs_audit_count"]
            else "ready"
            if external_evidence.get("status") == "loaded"
            else str(external_evidence.get("status", "absent"))
        ),
        "primary_owner": ".agentic-workspace/planning/state.toml",
        "provider_rule": (
            "Core planning consumes provider-agnostic external work evidence; provider-specific refresh belongs in optional adapters."
        ),
        "freshness": {
            "status": external_evidence.get("status", "absent"),
            "path": external_evidence.get("path", ""),
            "refreshed_at": external_evidence.get("refreshed_at", ""),
            "refresh_metadata": external_evidence.get("refresh_metadata", {}),
            "trust_scope": "snapshot",
            "snapshot_rule": EXTERNAL_INTENT_SNAPSHOT_RULE,
            "refresh_after_mutation": external_evidence.get("status") == "loaded",
            "refresh_command": EXTERNAL_INTENT_REFRESH_COMMAND,
            "fresh_enough_to_trust": external_evidence.get("status") == "loaded",
        },
        "external_work_state": {
            "open_count": external_open,
            "closed_count": external_closed,
            "tracked_open_count": tracked_open,
            "untracked_open_count": untracked_open,
        },
        "closeout_state": {
            "status": closeout_reconciliation.get("status", "absent"),
            "reconciled_count": closeout_reconciliation["counts"]["reconciled_count"],
            "needs_audit_count": closeout_reconciliation["counts"]["needs_audit_count"],
            "follow_up_open_count": closeout_reconciliation["counts"]["follow_up_open_count"],
            "likely_premature_closeout_count": closeout_reconciliation["counts"]["likely_premature_closeout_count"],
        },
        "landed_open_state": {
            "status": landed_open_issue_reconciliation.get("status", "absent"),
            "implemented_and_unclosed_count": landed_open_issue_reconciliation["counts"]["implemented_and_unclosed_count"],
            "ambiguous_open_reference_count": landed_open_issue_reconciliation["counts"]["ambiguous_open_reference_count"],
        },
        "detail_sections": [
            "current_external_work",
            "closeout_reconciliation",
            "landed_open_issue_reconciliation",
        ],
        "promotion_action": promotion_action,
        "recommended_next_action": recommended_next_action,
    }

    refs = [
        ".agentic-workspace/planning/state.toml",
        *([str(external_evidence.get("path", ""))] if external_evidence.get("path") else []),
    ]
    for path in active_execplans:
        relative = str(path.get("path", "")).strip()
        if relative:
            refs.append(relative)
    for item in active_items:
        surface = str(item.get("surface", "")).strip()
        if surface:
            refs.append(surface)

    return {
        "status": "present",
        "rule": (
            "Treat checked-in planning state as primary, then reconcile optional external planning evidence when present to spot dangling larger intent and lower-trust closeout."
        ),
        "primary_owner": ".agentic-workspace/planning/state.toml",
        "primary_owner_rule": (
            "Active items, candidate lanes, execplans, and archived continuation residue remain the product-owned planning truth."
        ),
        "external_evidence": {
            "status": external_evidence.get("status", "absent"),
            "path": external_evidence.get("path", ""),
            "kind": external_evidence.get("kind", ""),
            "systems": external_evidence.get("systems", []),
            "item_count": external_evidence.get("item_count", 0),
            "reason": external_evidence.get("reason", ""),
            "schema_findings": external_evidence.get("schema_findings", []),
        },
        "external_work_reconciliation": external_work_reconciliation,
        "current_external_work": current_external_work,
        "historical_audit_references": historical_audit_references,
        "counts": counts,
        "closeout_reconciliation": closeout_reconciliation,
        "landed_open_issue_reconciliation": landed_open_issue_reconciliation,
        "signals": signals,
        "recommended_next_action": recommended_next_action,
        "minimal_refs": [ref for ref in refs if ref],
    }


def _external_status_is_open(value: object) -> bool:
    return str(value).strip().lower().replace("_", "-") in {
        "active",
        "in-progress",
        "open",
        "opened",
        "planned",
        "todo",
    }


def _external_status_is_closed(value: object) -> bool:
    return str(value).strip().lower().replace("_", "-") in {
        "closed",
        "complete",
        "completed",
        "done",
        "resolved",
    }


def _closeout_reconciliation_from_reviews(
    *,
    target_root: Path,
    closed_residue_items: list[dict[str, Any]],
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    source_paths: list[str] = []
    seen_ids: set[str] = set()
    for path in sorted((target_root / ".agentic-workspace" / "planning" / "reviews").glob("*.review.json")):
        record = _load_review_record(path)
        if not isinstance(record, dict):
            continue
        classifications = record.get("issue_classifications", [])
        if not isinstance(classifications, list):
            continue
        relative_path = path.relative_to(target_root).as_posix()
        for raw in classifications:
            if not isinstance(raw, dict):
                continue
            item_id = str(raw.get("id", "")).strip()
            if not item_id or item_id in seen_ids:
                continue
            action_state = _closeout_reconciliation_action_state(str(raw.get("classification", "")).strip())
            items.append(
                {
                    "id": item_id,
                    "title": str(raw.get("title", "")).strip(),
                    "action_state": action_state,
                    "classification": str(raw.get("classification", "")).strip(),
                    "live_state": str(raw.get("live_state", "")).strip(),
                    "follow_up": str(raw.get("follow_up", "")).strip(),
                    "evidence": str(raw.get("evidence", "")).strip(),
                    "source": relative_path,
                }
            )
            seen_ids.add(item_id)
            if relative_path not in source_paths:
                source_paths.append(relative_path)

    for item in closed_residue_items:
        item_id = str(item.get("id", "")).strip()
        if not item_id or item_id in seen_ids:
            continue
        items.append(
            {
                "id": item_id,
                "title": str(item.get("title", "")).strip(),
                "action_state": "needs-audit",
                "classification": "unreconciled",
                "live_state": str(item.get("status", "")).strip(),
                "follow_up": "",
                "evidence": "No checked-in closeout reconciliation artifact classified this item.",
                "source": str(item.get("system", "")).strip(),
            }
        )
        seen_ids.add(item_id)

    counts = {
        "reconciled_count": sum(1 for item in items if item["action_state"] != "needs-audit"),
        "needs_audit_count": sum(1 for item in items if item["action_state"] == "needs-audit"),
        "evidence_present_count": sum(1 for item in items if item["action_state"] == "evidence-present"),
        "follow_up_open_count": sum(1 for item in items if item["action_state"] == "follow-up-open"),
        "historical_baseline_count": sum(1 for item in items if item["action_state"] == "historical-baseline"),
        "likely_premature_closeout_count": sum(1 for item in items if item["action_state"] == "likely-premature-closeout"),
    }
    status = "present" if items else "absent"
    if counts["needs_audit_count"]:
        status = "needs-audit"
    return {
        "status": status,
        "rule": (
            "Read checked-in planning review issue classifications first; accepted historical baselines are resolved audit debt, "
            "and any closed residue item without a classification remains needs-audit."
        ),
        "source_count": len(source_paths),
        "sources": source_paths,
        "item_count": len(items),
        "counts": counts,
        "items": items,
    }


def _landed_open_issue_reconciliation(
    *,
    target_root: Path,
    open_residue_items: list[dict[str, Any]],
    surface_index: dict[str, str],
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for item in open_residue_items:
        item_id = str(item.get("id", "")).strip()
        if not item_id:
            continue
        refs = _reference_locations(token=item_id, surface_index=surface_index)
        evidence_refs = [
            ref
            for ref in refs
            if ref.startswith(".agentic-workspace/planning/execplans/archive/") or ref.startswith(".agentic-workspace/planning/reviews/")
        ]
        evidence_refs = [
            ref
            for ref in evidence_refs
            if not _checked_in_ref_is_open_follow_up_context(target_root=target_root, relative_path=ref, item_id=item_id)
        ]
        if not evidence_refs:
            continue
        closeout_refs = [
            ref for ref in evidence_refs if _checked_in_ref_looks_landed(target_root=target_root, relative_path=ref, item_id=item_id)
        ]
        if closeout_refs:
            action_state = "implemented-and-unclosed"
            evidence = "Checked-in closeout evidence says the item landed, but external evidence still marks it open."
        else:
            action_state = "ambiguous-open-reference"
            evidence = "Checked-in historical evidence references this open item, but does not clearly prove landed implementation."
        items.append(
            {
                "id": item_id,
                "title": str(item.get("title", "")).strip(),
                "external_status": str(item.get("status", "")).strip(),
                "action_state": action_state,
                "evidence": evidence,
                "sources": closeout_refs or evidence_refs,
            }
        )
    counts = {
        "implemented_and_unclosed_count": sum(1 for item in items if item["action_state"] == "implemented-and-unclosed"),
        "ambiguous_open_reference_count": sum(1 for item in items if item["action_state"] == "ambiguous-open-reference"),
    }
    status = "present" if items else "absent"
    if counts["implemented_and_unclosed_count"]:
        status = "implemented-and-unclosed"
    elif counts["ambiguous_open_reference_count"]:
        status = "ambiguous"
    return {
        "status": status,
        "rule": (
            "Compare provider-agnostic open external work evidence against checked-in archive/review residue; "
            "report stale tracker state without auto-closing anything."
        ),
        "item_count": len(items),
        "counts": counts,
        "items": items,
    }


def _checked_in_ref_looks_landed(*, target_root: Path, relative_path: str, item_id: str) -> bool:
    path = target_root / relative_path
    if not path.exists() or not path.is_file():
        return False
    if path.suffix == ".json":
        try:
            record = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            return False
        references = record.get("references", []) if isinstance(record, dict) else []
        if isinstance(references, list):
            structured_refs = [ref for ref in references if isinstance(ref, dict) and str(ref.get("target", "")).strip() == item_id]
            if not structured_refs:
                return False
    closure_check = _execplan_closure_check(path)
    intent_satisfaction = _execplan_intent_satisfaction(path)
    closure_decision = str(closure_check.get("closure decision", "")).strip().lower()
    slice_status = str(closure_check.get("slice status", "")).strip().lower()
    intent_satisfied = str(intent_satisfaction.get("was original intent fully satisfied?", "")).strip().lower()
    if closure_decision == "archive-and-close":
        return True
    if intent_satisfied in {"yes", "true"}:
        return True
    return "complete" in slice_status or "landed" in slice_status


def _checked_in_ref_is_open_follow_up_context(*, target_root: Path, relative_path: str, item_id: str) -> bool:
    path = target_root / relative_path
    if not path.exists() or not path.is_file() or path.suffix != ".json":
        return False
    try:
        record = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(record, dict):
        return False
    reference_roles = _execplan_issue_reference_roles(path)
    if item_id in reference_roles.get("closure_refs", []):
        return False
    if item_id in reference_roles.get("non_closure_refs", []):
        return True
    closeout_distillation = record.get("closeout_distillation", {})
    buckets = closeout_distillation.get("buckets", {}) if isinstance(closeout_distillation, dict) else {}
    issue_follow_up = buckets.get("issue_follow_up", []) if isinstance(buckets, dict) else []
    if isinstance(issue_follow_up, list):
        for raw in issue_follow_up:
            text = json.dumps(raw, sort_keys=True) if isinstance(raw, dict) else str(raw)
            if item_id in text:
                return True
    required_continuation = record.get("required_continuation", {})
    if isinstance(required_continuation, dict) and item_id in json.dumps(required_continuation, sort_keys=True):
        return True
    return False


def _closeout_reconciliation_action_state(classification: str) -> str:
    normalized = classification.strip().lower().replace("_", "-")
    if normalized in {"fully-satisfied-with-evidence", "evidence-present"}:
        return "evidence-present"
    if normalized in {"bounded-slice-satisfied-parent-open", "covered-by-open-followup", "follow-up-open"}:
        return "follow-up-open"
    if normalized in {"accepted-historical-baseline", "historical-baseline", "baseline-accepted"}:
        return "historical-baseline"
    if normalized in {"premature-or-needs-reopening", "likely-premature-closeout"}:
        return "likely-premature-closeout"
    return "needs-audit"


def _finished_work_inspection_contract(*, target_root: Path) -> dict[str, Any]:
    archive_dir = target_root / ".agentic-workspace" / "planning" / "execplans" / "archive"
    evidence = _load_finished_work_evidence(target_root)
    external_evidence = _load_external_intent_evidence(target_root)
    signals: list[dict[str, Any]] = []
    inspections: list[dict[str, Any]] = []
    derived_follow_up_candidates: list[dict[str, Any]] = []
    archive_only_durable_residue: list[dict[str, Any]] = []
    clearly_landed = 0
    partial = 0
    likely_premature = 0
    superseded_continuation = 0
    externally_closed_continuation = 0
    unowned_continuation = 0
    role_aware_reference_plan_count = 0
    non_closure_reference_count = 0

    archived_paths = _archived_execplan_paths(archive_dir)
    evidence_items = _finished_work_reopening_evidence_items(
        finished_evidence=evidence,
        external_evidence=external_evidence,
    )

    for path in archived_paths:
        reference_roles = _execplan_issue_reference_roles(path)
        if reference_roles["status"] == "present":
            role_aware_reference_plan_count += 1
            non_closure_reference_count += len(reference_roles["non_closure_refs"])
        issue_refs = sorted(_execplan_issue_refs(path))
        reopened_by = _finished_work_reopeners(issue_refs=issue_refs, evidence_items=evidence_items)
        closure_check = _execplan_closure_check(path)
        intent_satisfaction = _execplan_intent_satisfaction(path)
        durable_residue = _execplan_durable_residue(path)
        closure_decision = str(closure_check.get("closure decision", "")).strip().lower()
        larger_intent_status = str(closure_check.get("larger-intent status", "")).strip().lower()
        intent_satisfied = str(intent_satisfaction.get("was original intent fully satisfied?", "")).strip().lower()
        archive_only_residue_signal = _archive_only_durable_residue_signal(
            target_root=target_root,
            path=path,
            durable_residue=durable_residue,
        )
        if archive_only_residue_signal:
            archive_only_durable_residue.append(archive_only_residue_signal)
            signals.append(archive_only_residue_signal)
        classification = "clearly_landed"
        reason = "Archived closeout reports fully satisfied intent and no reopening evidence points back at it."
        if reopened_by:
            classification = "likely_premature_closeout"
            reason = (
                "Optional reopening evidence points back at this archived closeout, so treat the original close decision as lower trust."
            )
            likely_premature += 1
            candidate = _finished_work_follow_up_candidate(
                target_root=target_root,
                path=path,
                classification=classification,
                reason=reason,
                issue_refs=issue_refs,
                reopened_by=reopened_by,
                closure_check=closure_check,
                intent_satisfaction=intent_satisfaction,
                reference_roles=reference_roles,
            )
            derived_follow_up_candidates.append(candidate)
            signals.append(
                {
                    "kind": "likely_premature_closeout",
                    "severity": "warning",
                    "path": path.relative_to(target_root).as_posix(),
                    "message": (
                        f"Archived closeout {path.relative_to(target_root).as_posix()} now has follow-on evidence reopening {', '.join(item['id'] for item in reopened_by)}."
                    ),
                    "refs": [
                        path.relative_to(target_root).as_posix(),
                        *[item["id"] for item in reopened_by],
                    ],
                }
            )
        elif closure_decision == "archive-but-keep-lane-open" or larger_intent_status in {"open", "unfinished"} or intent_satisfied == "no":
            classification = "partial"
            reason = "Archived residue itself says the bounded slice landed while larger intent or required continuation remained open."
            partial += 1
            candidate = _finished_work_follow_up_candidate(
                target_root=target_root,
                path=path,
                classification=classification,
                reason=reason,
                issue_refs=issue_refs,
                reopened_by=reopened_by,
                closure_check=closure_check,
                intent_satisfaction=intent_satisfaction,
                reference_roles=reference_roles,
            )
            derived_follow_up_candidates.append(candidate)
            signals.append(
                {
                    "kind": "intent_continuation_required",
                    "severity": "info",
                    "path": path.relative_to(target_root).as_posix(),
                    "message": (
                        f"Archived closeout {path.relative_to(target_root).as_posix()} left larger intent open; "
                        "route the continuation before treating the goal as settled."
                    ),
                    "refs": [
                        path.relative_to(target_root).as_posix(),
                        *issue_refs,
                    ],
                }
            )
        else:
            clearly_landed += 1
        inspections.append(
            {
                "plan": path.relative_to(target_root).as_posix(),
                "title": _execplan_title(path),
                "classification": classification,
                "closure_decision": closure_check.get("closure decision", ""),
                "larger_intent_status": closure_check.get("larger-intent status", ""),
                "intent_satisfied": intent_satisfaction.get("was original intent fully satisfied?", ""),
                "tracked_refs": issue_refs,
                "reference_roles": reference_roles,
                "non_closure_refs": reference_roles["non_closure_refs"],
                "reopened_by": reopened_by,
                "durable_residue": _compact_durable_residue_for_inspection(durable_residue),
                "reason": reason,
                "superseded_by": [],
            }
        )

    superseded_source_plans: set[str] = set()
    active_derived_follow_up_candidates: list[dict[str, Any]] = []
    for candidate in derived_follow_up_candidates:
        superseded_by = _finished_work_continuation_superseded_by(
            target_root=target_root,
            archived_paths=archived_paths,
            candidate=candidate,
        )
        if superseded_by:
            superseded_continuation += 1
            source_plan = str(candidate.get("source_plan", ""))
            superseded_source_plans.add(source_plan)
            candidate["superseded_by"] = superseded_by
            candidate["recommended_action"] = "no promotion; continuation appears consumed by later closeout evidence"
            for inspection in inspections:
                if inspection.get("plan") == source_plan:
                    inspection["classification"] = "superseded_partial"
                    inspection["superseded_by"] = superseded_by
                    inspection["reason"] = (
                        "Archived residue left larger intent open, but later closeout evidence appears to consume the continuation."
                    )
                    break
            continue
        active_derived_follow_up_candidates.append(candidate)
    if superseded_source_plans:
        signals = [
            signal
            for signal in signals
            if not (signal.get("kind") == "intent_continuation_required" and signal.get("path") in superseded_source_plans)
        ]
    derived_follow_up_candidates = active_derived_follow_up_candidates

    externally_closed_source_plans: set[str] = set()
    active_externally_closed_follow_up_candidates: list[dict[str, Any]] = []
    for candidate in derived_follow_up_candidates:
        externally_closed_by = _finished_work_continuation_closed_by_external_evidence(
            candidate=candidate,
            external_evidence=external_evidence,
        )
        if externally_closed_by:
            externally_closed_continuation += 1
            source_plan = str(candidate.get("source_plan", ""))
            externally_closed_source_plans.add(source_plan)
            candidate["externally_closed_by"] = externally_closed_by
            candidate["recommended_action"] = "no promotion; continuation refs are externally closed"
            for inspection in inspections:
                if inspection.get("plan") == source_plan:
                    inspection["classification"] = "externally_closed_partial"
                    inspection["externally_closed_by"] = externally_closed_by
                    inspection["reason"] = (
                        "Archived residue left larger intent open, but refreshed external evidence marks the explicit "
                        "parent, continuation, or legacy tracked refs as closed."
                    )
                    break
            continue
        active_externally_closed_follow_up_candidates.append(candidate)
    if externally_closed_source_plans:
        signals = [
            signal
            for signal in signals
            if not (signal.get("kind") == "intent_continuation_required" and signal.get("path") in externally_closed_source_plans)
        ]
    derived_follow_up_candidates = active_externally_closed_follow_up_candidates

    unowned_source_plans: set[str] = set()
    active_owned_follow_up_candidates: list[dict[str, Any]] = []
    for candidate in derived_follow_up_candidates:
        if _finished_work_continuation_lacks_actionable_owner(target_root=target_root, candidate=candidate):
            unowned_continuation += 1
            source_plan = str(candidate.get("source_plan", ""))
            unowned_source_plans.add(source_plan)
            candidate["recommended_action"] = (
                "do not promote directly; route this historical continuation to a concrete active issue, roadmap item, "
                "or existing planning path first"
            )
            for inspection in inspections:
                if inspection.get("plan") == source_plan:
                    inspection["classification"] = "unowned_partial"
                    inspection["reason"] = (
                        "Archived residue left larger intent open, but the continuation does not name an actionable owner "
                        "that can be promoted safely."
                    )
                    break
            continue
        active_owned_follow_up_candidates.append(candidate)
    if unowned_source_plans:
        signals = [
            signal
            for signal in signals
            if not (signal.get("kind") == "intent_continuation_required" and signal.get("path") in unowned_source_plans)
        ]
        for source_plan in sorted(unowned_source_plans):
            signals.append(
                {
                    "kind": "unowned_intent_continuation",
                    "severity": "info",
                    "path": source_plan,
                    "message": (
                        f"Archived closeout {source_plan} left larger intent open but did not name an actionable "
                        "continuation owner; route it before promotion."
                    ),
                    "refs": [source_plan],
                }
            )
    derived_follow_up_candidates = active_owned_follow_up_candidates

    routed_source_plans: set[str] = set()
    active_routed_follow_up_candidates: list[dict[str, Any]] = []
    routed_continuation = 0
    for candidate in derived_follow_up_candidates:
        routed_by = _finished_work_continuation_routed_by_active_plan(target_root=target_root, candidate=candidate)
        if not routed_by:
            routed_by = _finished_work_continuation_routed_by_roadmap(target_root=target_root, candidate=candidate)
        if routed_by:
            routed_continuation += 1
            source_plan = str(candidate.get("source_plan", ""))
            routed_source_plans.add(source_plan)
            candidate["routed_by"] = routed_by
            candidate["recommended_action"] = "no promotion; continuation is already active in checked-in planning"
            for inspection in inspections:
                if inspection.get("plan") == source_plan:
                    inspection["classification"] = "routed_partial"
                    inspection["routed_by"] = routed_by
                    inspection["reason"] = (
                        "Archived residue left larger intent open, but checked-in planning already owns the same continuation."
                    )
                    break
            continue
        active_routed_follow_up_candidates.append(candidate)
    if routed_source_plans:
        signals = [
            signal
            for signal in signals
            if not (signal.get("kind") == "intent_continuation_required" and signal.get("path") in routed_source_plans)
        ]
    derived_follow_up_candidates = active_routed_follow_up_candidates

    if evidence.get("status") == "invalid":
        signals.append(
            {
                "kind": "finished_work_evidence_invalid",
                "severity": "warning",
                "path": evidence.get("path", ""),
                "message": str(evidence.get("reason", "optional finished-work evidence could not be loaded")),
                "refs": [evidence.get("path", "")],
            }
        )

    derived_follow_up_candidates.sort(
        key=lambda candidate: _candidate_source_mtime_ns(target_root=target_root, candidate=candidate),
        reverse=True,
    )
    counts = {
        "archived_closeout_count": len(archived_paths),
        "clearly_landed_count": clearly_landed,
        "partial_count": partial,
        "likely_premature_closeout_count": likely_premature,
        "superseded_continuation_count": superseded_continuation,
        "externally_closed_continuation_count": externally_closed_continuation,
        "unowned_continuation_count": unowned_continuation,
        "routed_continuation_count": routed_continuation,
        "archive_only_durable_residue_count": len(archive_only_durable_residue),
        "role_aware_reference_plan_count": role_aware_reference_plan_count,
        "non_closure_reference_count": non_closure_reference_count,
        "derived_follow_up_candidate_count": len(derived_follow_up_candidates),
        "attention_count": len(signals),
    }
    recommended_next_action = "No suspicious finished-work signals detected."
    if likely_premature:
        recommended_next_action = (
            "Inspect archived closeouts flagged by reopening evidence before trusting previously closed lanes as fully landed."
        )
    elif evidence.get("status") == "invalid":
        recommended_next_action = "Repair optional finished-work evidence or remove it so closeout inspection trust is explicit."
    elif derived_follow_up_candidates:
        recommended_next_action = (
            "Promote or explicitly route derived follow-up candidates before assuming archived partial-intent work was complete."
        )
    elif archive_only_durable_residue:
        recommended_next_action = (
            "Route archive-only durable residue to Memory, docs, contracts, checks, or planning instead of relying on archive lookup."
        )

    refs = [".agentic-workspace/planning/execplans/archive/"]
    if evidence.get("path"):
        refs.append(str(evidence.get("path", "")))

    return {
        "status": "present",
        "rule": (
            "Inspect archived checked-in closeout residue first, then use optional generic reopening evidence only to lower trust when a supposedly finished lane clearly points back into active follow-on."
        ),
        "primary_owner": ".agentic-workspace/planning/execplans/archive/",
        "primary_owner_rule": (
            "Archived execplans remain the durable closeout evidence; optional reopening evidence may challenge trust but must not replace the archive as source of record."
        ),
        "counts": counts,
        "evidence": {
            "status": evidence.get("status", "absent"),
            "path": evidence.get("path", ""),
            "kind": evidence.get("kind", ""),
            "systems": evidence.get("systems", []),
            "item_count": evidence.get("item_count", 0),
            "reason": evidence.get("reason", ""),
            "schema_findings": evidence.get("schema_findings", []),
        },
        "signals": signals,
        "inspections": inspections,
        "archive_only_durable_residue": archive_only_durable_residue,
        "derived_follow_up_candidates": derived_follow_up_candidates,
        "recommended_next_action": recommended_next_action,
        "minimal_refs": [ref for ref in refs if ref],
    }


def _compact_durable_residue_for_inspection(durable_residue: dict[str, str]) -> dict[str, str]:
    if not durable_residue:
        return {}
    return {
        "status": durable_residue.get("status", "").strip(),
        "canonical_owner_now": durable_residue.get("canonical owner now", "").strip(),
        "promotion_trigger": durable_residue.get("promotion trigger", "").strip(),
        "retention_after_promotion": durable_residue.get("retention after promotion", "").strip(),
    }


def _archive_only_durable_residue_signal(
    *,
    target_root: Path,
    path: Path,
    durable_residue: dict[str, str],
) -> dict[str, Any] | None:
    status = durable_residue.get("status", "").strip().lower()
    learned_constraint = durable_residue.get("learned constraint", "").strip()
    motivation = durable_residue.get("motivation worth preserving", "").strip()
    owner = durable_residue.get("canonical owner now", "").strip()
    owner_normalized = owner.lower()

    if not learned_constraint and not motivation:
        return None
    if _durable_residue_text_says_no_future_relevance(learned_constraint) and _durable_residue_text_says_no_future_relevance(motivation):
        return None
    if status in {"none"}:
        return None
    if status != "evidence_only" and owner and owner_normalized not in EXECPLAN_DURABLE_RESIDUE_OWNER_VALUES:
        return None

    relative_path = path.relative_to(target_root).as_posix()
    return {
        "kind": "archive_only_durable_residue",
        "severity": "info",
        "path": relative_path,
        "message": (
            f"Archived closeout {relative_path} carries future-relevant durable residue without a non-archive owner; "
            "route the residue to Memory, docs, contracts, checks, or planning instead of relying on archive lookup."
        ),
        "refs": [relative_path],
        "durable_residue": {
            "status": status or "missing",
            "canonical_owner_now": owner,
            "learned_constraint_present": bool(learned_constraint),
            "motivation_present": bool(motivation),
        },
        "recommended_action": "route residue to Memory, docs, contracts, checks, or planning",
    }


def _durable_residue_text_says_no_future_relevance(value: str) -> bool:
    normalized = value.strip().lower()
    return (
        not normalized
        or normalized == "none"
        or normalized.startswith("none beyond")
        or normalized.startswith("no future-relevant")
        or normalized.startswith("no durable")
    )


def _candidate_source_mtime_ns(*, target_root: Path, candidate: dict[str, Any]) -> int:
    source_plan = str(candidate.get("source_plan", "")).strip()
    if not source_plan:
        return 0
    try:
        return (target_root / source_plan).stat().st_mtime_ns
    except OSError:
        return 0


def _finished_work_continuation_routed_by_active_plan(*, target_root: Path, candidate: dict[str, Any]) -> list[str]:
    unsolved_intent = str(candidate.get("unsolved_intent", "")).strip().lower()
    if not unsolved_intent or unsolved_intent in {"none", "n/a", "none yet"}:
        return []
    reference_roles = candidate.get("reference_roles", {})
    if not isinstance(reference_roles, dict):
        return []
    by_role = reference_roles.get("by_role", {})
    parent_refs = set(by_role.get("parent_intent", []) or []) if isinstance(by_role, dict) else set()
    closure_refs = set(reference_roles.get("closure_refs", []) or [])
    if not parent_refs:
        return []

    routed_by: list[str] = []
    execplan_dir = target_root / ".agentic-workspace" / "planning" / "execplans"
    if not execplan_dir.exists():
        return []
    for path in _live_execplan_paths(execplan_dir):
        status = _execplan_status(path)
        if not status or status in {"completed", "done", "closed", "planned", "pending", "not-started"}:
            continue
        active_roles = _execplan_issue_reference_roles(path)
        active_by_role = active_roles.get("by_role", {}) if isinstance(active_roles, dict) else {}
        active_parent_refs = set(active_by_role.get("parent_intent", []) or []) if isinstance(active_by_role, dict) else set()
        active_closure_refs = set(active_roles.get("closure_refs", []) or []) if isinstance(active_roles, dict) else set()
        if parent_refs & active_parent_refs and not (closure_refs & active_closure_refs):
            routed_by.append(path.relative_to(target_root).as_posix())
    return routed_by


def _finished_work_continuation_closed_by_external_evidence(
    *,
    candidate: dict[str, Any],
    external_evidence: dict[str, Any],
) -> list[str]:
    if external_evidence.get("status") != "loaded":
        return []
    reference_roles = candidate.get("reference_roles", {})
    if not isinstance(reference_roles, dict):
        return []
    status_by_id = {
        str(item.get("id", "")).strip(): str(item.get("status", "")).strip().lower()
        for item in external_evidence.get("items", [])
        if isinstance(item, dict) and str(item.get("id", "")).strip()
    }
    closed_statuses = {"closed", "complete", "completed", "done"}
    reopened_refs = sorted({str(ref).strip() for ref in candidate.get("reopened_by", []) if str(ref).strip()})
    if reopened_refs:
        if all(status_by_id.get(ref, "") in closed_statuses for ref in reopened_refs):
            return reopened_refs
        return []
    non_closure_refs = sorted({str(ref).strip() for ref in reference_roles.get("non_closure_refs", []) if str(ref).strip()})
    legacy_roleless_refs: list[str] = []
    if not non_closure_refs and reference_roles.get("status") != "present":
        legacy_roleless_refs = sorted({str(ref).strip() for ref in candidate.get("tracked_refs", []) if str(ref).strip()})
    unsolved_intent_refs = sorted(_issue_refs_from_text(str(candidate.get("unsolved_intent", ""))))
    refs_to_check = non_closure_refs or legacy_roleless_refs or unsolved_intent_refs
    if not refs_to_check:
        return []

    if all(status_by_id.get(ref, "") in closed_statuses for ref in refs_to_check):
        return refs_to_check
    return []


def _finished_work_continuation_lacks_actionable_owner(*, target_root: Path, candidate: dict[str, Any]) -> bool:
    if candidate.get("reopened_by"):
        return False
    reference_roles = candidate.get("reference_roles", {})
    if isinstance(reference_roles, dict):
        non_closure_refs = [str(ref).strip() for ref in reference_roles.get("non_closure_refs", []) if str(ref).strip()]
        if non_closure_refs:
            return False
        if reference_roles.get("status") != "present":
            legacy_refs = [str(ref).strip() for ref in candidate.get("tracked_refs", []) if str(ref).strip()]
            if legacy_refs:
                return False
    unsolved_intent = str(candidate.get("unsolved_intent", "")).strip()
    if not unsolved_intent or unsolved_intent.lower() in {"none", "n/a", "none yet"}:
        return True
    if _issue_refs_from_text(unsolved_intent):
        return False
    for token in re.findall(r"(?:^|\s)(\.agentic-workspace/[^\s,;]+)", unsolved_intent):
        normalized = token.rstrip(".,;:")
        path = target_root / normalized
        if path.exists() and "/archive/" not in normalized.replace("\\", "/"):
            return False
    return True


def _finished_work_continuation_routed_by_roadmap(*, target_root: Path, candidate: dict[str, Any]) -> list[str]:
    unsolved_intent = str(candidate.get("unsolved_intent", "")).strip().lower()
    if not unsolved_intent or unsolved_intent in {"none", "n/a", "none yet"}:
        return []
    reference_roles = candidate.get("reference_roles", {})
    if not isinstance(reference_roles, dict):
        return []
    non_closure_refs = set(reference_roles.get("non_closure_refs", []) or [])
    intent_tokens = set(_continuation_owner_label_tokens(unsolved_intent))

    state = _read_state_from_toml(target_root)
    if not isinstance(state, dict):
        return []
    roadmap = state.get("roadmap", {}) if isinstance(state, dict) else {}
    if not isinstance(roadmap, dict):
        return []

    routed_by: list[str] = []
    work_items = state.get("work_items", [])
    if isinstance(work_items, list):
        for raw_item in work_items:
            if not isinstance(raw_item, dict):
                continue
            item_refs = _planning_item_issue_refs(raw_item)
            item_text = _planning_item_identity_text(raw_item)
            token_match = bool(intent_tokens) and all(token in item_text for token in intent_tokens)
            if not (item_refs & non_closure_refs) and not token_match:
                continue
            item_type = str(raw_item.get("type", "")).strip() or "item"
            item_id = str(raw_item.get("id", "")).strip() or str(raw_item.get("title", "")).strip() or "unnamed"
            routed_by.append(f".agentic-workspace/planning/state.toml work_items {item_type} {item_id}")

    for collection_name in ("lanes", "candidates"):
        collection = roadmap.get(collection_name, [])
        if not isinstance(collection, list):
            continue
        for raw_item in collection:
            if not isinstance(raw_item, dict):
                continue
            item_refs = _planning_item_issue_refs(raw_item)
            item_text = _planning_item_identity_text(raw_item)
            token_match = bool(intent_tokens) and all(token in item_text for token in intent_tokens)
            if not (item_refs & non_closure_refs) and not token_match:
                continue
            item_id = str(raw_item.get("id", "")).strip() or str(raw_item.get("title", "")).strip() or "unnamed"
            routed_by.append(f".agentic-workspace/planning/state.toml roadmap {collection_name[:-1]} {item_id}")
    return sorted(set(routed_by))


def _planning_item_identity_text(item: dict[str, Any]) -> str:
    fields = (
        "id",
        "title",
        "summary",
        "reason",
        "why_now",
        "outcome",
        "promotion_signal",
        "suggested_first_slice",
        "surface",
    )
    values = [str(item.get(field, "")).strip().lower() for field in fields if str(item.get(field, "")).strip()]
    issues = item.get("issues", [])
    if isinstance(issues, list):
        values.extend(str(issue).strip().lower() for issue in issues if str(issue).strip())
    refs = item.get("refs", [])
    if isinstance(refs, list):
        values.extend(str(ref).strip().lower() for ref in refs if str(ref).strip())
    return " ".join(values)


def _continuation_owner_label_tokens(unsolved_intent: str) -> list[str]:
    match = re.search(r"\b(?:roadmap|work_items?|todo)(?:\s+(?:lane|candidate|item|summary|entry))?\s+([a-z0-9._# -]+)$", unsolved_intent)
    if match:
        tokens = _label_tokens(match.group(1))
        if tokens:
            return tokens
    return _label_tokens(unsolved_intent)


def _planning_item_issue_refs(
    item: dict[str, Any],
    *,
    text_fields: tuple[str, ...] = ("id", "title", "reason", "why_now", "outcome", "promotion_signal", "suggested_first_slice"),
) -> set[str]:
    refs: set[str] = set()
    for field_name in ("issues", "refs"):
        raw_value = item.get(field_name, [])
        raw_items = raw_value if isinstance(raw_value, list) else [raw_value]
        for raw_ref in raw_items:
            token = _reference_issue_token(str(raw_ref))
            if token:
                refs.add(token)
            refs.update(_issue_refs_from_text(str(raw_ref)))
    raw_references = item.get("references", [])
    if isinstance(raw_references, list):
        for raw_reference in raw_references:
            if not isinstance(raw_reference, dict):
                continue
            token = _reference_issue_token(str(raw_reference.get("target", "")))
            if token:
                refs.add(token)
    for field_name in text_fields:
        refs.update(_issue_refs_from_text(str(item.get(field_name, ""))))
    return refs


def _live_execplan_paths(execplan_dir: Path) -> list[Path]:
    seen_stems: set[str] = set()
    paths: list[Path] = []
    for path in sorted(execplan_dir.glob("*.plan.json")):
        if path.name == "TEMPLATE.plan.json":
            continue
        seen_stems.add(path.name[: -len(".plan.json")])
        paths.append(path)
    for path in sorted(execplan_dir.glob("*.md")):
        if path.name in {"README.md", "TEMPLATE.md"}:
            continue
        if path.stem not in seen_stems:
            paths.append(path)
    return paths


def _finished_work_continuation_superseded_by(
    *,
    target_root: Path,
    archived_paths: list[Path],
    candidate: dict[str, Any],
) -> list[str]:
    source_plan = str(candidate.get("source_plan", "")).strip()
    if not source_plan:
        return []
    source_path = target_root / source_plan
    source_mtime = _candidate_source_mtime_ns(target_root=target_root, candidate=candidate)
    tracked_refs = [str(ref).strip() for ref in candidate.get("tracked_refs", []) if str(ref).strip()]
    superseding_paths: list[str] = []
    for path in archived_paths:
        if path == source_path:
            continue
        try:
            if source_mtime and path.stat().st_mtime_ns < source_mtime:
                continue
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if not _archived_execplan_closes_larger_intent(path):
            continue
        if source_plan in text or (tracked_refs and all(ref in text for ref in tracked_refs)):
            superseding_paths.append(path.relative_to(target_root).as_posix())
    return superseding_paths


def _archived_execplan_closes_larger_intent(path: Path) -> bool:
    closure_check = _execplan_closure_check(path)
    intent_satisfaction = _execplan_intent_satisfaction(path)
    closure_decision = str(closure_check.get("closure decision", "")).strip().lower()
    larger_intent_status = str(closure_check.get("larger-intent status", "")).strip().lower()
    intent_satisfied = str(intent_satisfaction.get("was original intent fully satisfied?", "")).strip().lower()
    return closure_decision == "archive-and-close" or larger_intent_status == "closed" or intent_satisfied in {"yes", "true"}


def _archived_execplan_paths(archive_dir: Path) -> list[Path]:
    if not archive_dir.exists():
        return []
    seen_stems: set[str] = set()
    paths: list[Path] = []
    for path in sorted(archive_dir.glob("*.plan.json")):
        if path.is_file():
            seen_stems.add(path.name[: -len(".plan.json")])
            paths.append(path)
    for path in sorted(archive_dir.glob("*.md")):
        if not path.is_file() or path.name in {"README.md", "TEMPLATE.md"}:
            continue
        if path.stem not in seen_stems:
            paths.append(path)
    return paths


def _finished_work_follow_up_candidate(
    *,
    target_root: Path,
    path: Path,
    classification: str,
    reason: str,
    issue_refs: list[str],
    reopened_by: list[dict[str, str]],
    closure_check: dict[str, str],
    intent_satisfaction: dict[str, str],
    reference_roles: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reopened_refs = [item["id"] for item in reopened_by if item.get("id")]
    return {
        "kind": "intent-derived-continuation",
        "source_plan": path.relative_to(target_root).as_posix(),
        "title": _execplan_title(path),
        "classification": classification,
        "why": reason,
        "larger_intent_status": closure_check.get("larger-intent status", ""),
        "closure_decision": closure_check.get("closure decision", ""),
        "intent_satisfied": intent_satisfaction.get("was original intent fully satisfied?", ""),
        "unsolved_intent": intent_satisfaction.get("unsolved intent passed to", ""),
        "tracked_refs": issue_refs,
        "reference_roles": reference_roles or {"status": "absent", "closure_refs": issue_refs, "non_closure_refs": [], "by_role": {}},
        "reopened_by": reopened_refs,
        "recommended_owner": ".agentic-workspace/planning/state.toml",
        "recommended_action": "promote to active planning, implement the next bounded slice, then re-run finished-work inspection",
    }


def _planning_surface_reference_index(target_root: Path) -> dict[str, str]:
    surface_index: dict[str, str] = {}
    candidate_paths = [
        target_root / PLANNING_STATE_PATH,
        *[
            path
            for path in sorted((target_root / ".agentic-workspace" / "planning" / "execplans").glob("*.md"))
            if path.name not in {"README.md", "TEMPLATE.md"}
        ],
        *[
            path
            for path in sorted((target_root / ".agentic-workspace" / "planning" / "execplans").glob("*.plan.json"))
            if path.name != "TEMPLATE.plan.json"
        ],
        *[
            path
            for path in sorted((target_root / ".agentic-workspace" / "planning" / "execplans" / "archive").glob("*.md"))
            if path.name != "README.md"
        ],
        *[path for path in sorted((target_root / ".agentic-workspace" / "planning" / "execplans" / "archive").glob("*.plan.json"))],
        *[
            path
            for path in sorted((target_root / ".agentic-workspace" / "planning" / "reviews").glob("*.md"))
            if path.name not in {"README.md", "TEMPLATE.md"}
        ],
        *[
            path
            for path in sorted((target_root / ".agentic-workspace" / "planning" / "reviews").glob("*.review.json"))
            if path.name != "TEMPLATE.review.json"
        ],
        *[
            path
            for path in sorted((target_root / ".agentic-workspace" / "planning" / "decompositions").glob("*.decomposition.json"))
            if path.name != "TEMPLATE.decomposition.json"
        ],
    ]
    for path in candidate_paths:
        if not path.exists() or not path.is_file():
            continue
        try:
            surface_index[path.relative_to(target_root).as_posix()] = path.read_text(encoding="utf-8")
        except OSError:
            continue
    return surface_index


def _reference_locations(*, token: str, surface_index: dict[str, str]) -> list[str]:
    return [path for path, text in surface_index.items() if token in text]


def _is_live_planning_tracking_ref(relative_path: str) -> bool:
    if relative_path == ".agentic-workspace/planning/state.toml":
        return True
    return relative_path.startswith(".agentic-workspace/planning/execplans/") and "/archive/" not in relative_path


def _load_external_intent_evidence(target_root: Path) -> dict[str, Any]:
    cache_path = target_root / PLANNING_EXTERNAL_INTENT_CACHE_PATH
    if cache_path.exists():
        path = cache_path
        relative_path = PLANNING_EXTERNAL_INTENT_CACHE_PATH.as_posix()
        storage_class = "cache"
    else:
        path = target_root / PLANNING_EXTERNAL_INTENT_EVIDENCE_PATH
        relative_path = PLANNING_EXTERNAL_INTENT_EVIDENCE_PATH.as_posix()
        storage_class = "planning-legacy"
    if not path.exists():
        return {
            "status": "absent",
            "path": relative_path,
            "storage": "cache",
            "kind": "planning-external-intent-evidence/v1",
            "systems": [],
            "item_count": 0,
            "items": [],
            "reason": "optional external intent cache not present",
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError) as exc:
        return {
            "status": "invalid",
            "path": relative_path,
            "storage": storage_class,
            "kind": "planning-external-intent-evidence/v1",
            "systems": [],
            "item_count": 0,
            "items": [],
            "reason": f"failed to load optional evidence: {exc}",
        }
    if not isinstance(payload, dict) or payload.get("kind") != "planning-external-intent-evidence/v1":
        return {
            "status": "invalid",
            "path": relative_path,
            "storage": storage_class,
            "kind": "planning-external-intent-evidence/v1",
            "systems": [],
            "item_count": 0,
            "items": [],
            "reason": "optional evidence file does not match planning-external-intent-evidence/v1",
        }
    schema_findings = _json_schema_findings(payload=payload, schema_path=EXTERNAL_INTENT_EVIDENCE_SCHEMA_PATH)
    schema_findings.extend(_external_intent_evidence_consistency_findings(payload))
    if schema_findings:
        return _evidence_schema_invalid_payload(
            relative_path=relative_path,
            storage_class=storage_class,
            kind="planning-external-intent-evidence/v1",
            findings=schema_findings,
        )
    refresh_metadata = payload.get("refresh_metadata", {})
    if not isinstance(refresh_metadata, dict):
        refresh_metadata = {}
    normalized_items: list[dict[str, Any]] = []
    systems: list[str] = []
    for raw in payload.get("items", []):
        if not isinstance(raw, dict):
            continue
        system = str(raw.get("system", "")).strip()
        item = {
            "system": system,
            "id": str(raw.get("id", "")).strip(),
            "title": str(raw.get("title", "")).strip(),
            "status": str(raw.get("status", "")).strip().lower(),
            "kind": str(raw.get("kind", "")).strip(),
            "parent_id": str(raw.get("parent_id", "")).strip(),
            "reopens": [str(entry).strip() for entry in raw.get("reopens", []) if str(entry).strip()],
            "planning_residue_expected": str(raw.get("planning_residue_expected", "optional")).strip().lower(),
        }
        if not item["id"]:
            continue
        normalized_items.append(item)
        if system and system not in systems:
            systems.append(system)
    return {
        "status": "loaded",
        "path": relative_path,
        "storage": storage_class,
        "kind": "planning-external-intent-evidence/v1",
        "systems": systems,
        "refreshed_at": str(payload.get("refreshed_at", "") or refresh_metadata.get("refreshed_at", "")),
        "refresh_metadata": {
            "adapter": str(refresh_metadata.get("adapter", "")),
            "repository": str(refresh_metadata.get("repository", "")),
            "item_count": refresh_metadata.get("item_count", len(normalized_items)),
            "open_count": refresh_metadata.get("open_count", 0),
            "closed_count": refresh_metadata.get("closed_count", 0),
            "limit": refresh_metadata.get("limit", 0),
            "state": str(refresh_metadata.get("state", "")),
        },
        "item_count": len(normalized_items),
        "items": normalized_items,
        "reason": "",
    }


def _external_intent_evidence_consistency_findings(payload: dict[str, Any]) -> list[str]:
    refresh_metadata = payload.get("refresh_metadata", {})
    if not isinstance(refresh_metadata, dict):
        return []
    raw_items = payload.get("items", [])
    items = [item for item in raw_items if isinstance(item, dict)] if isinstance(raw_items, list) else []
    expected_counts = {
        "item_count": len(items),
        "open_count": sum(1 for item in items if str(item.get("status", "")).strip().lower() == "open"),
        "closed_count": sum(1 for item in items if str(item.get("status", "")).strip().lower() == "closed"),
    }
    findings: list[str] = []
    for count_name, expected in expected_counts.items():
        if count_name in refresh_metadata and refresh_metadata.get(count_name) != expected:
            findings.append(f"refresh_metadata.{count_name} must equal {expected} from items, got {refresh_metadata.get(count_name)!r}")
    return findings


def _load_finished_work_evidence(target_root: Path) -> dict[str, Any]:
    path = target_root / PLANNING_FINISHED_WORK_EVIDENCE_PATH
    relative_path = PLANNING_FINISHED_WORK_EVIDENCE_PATH.as_posix()
    if not path.exists():
        return {
            "status": "absent",
            "path": relative_path,
            "kind": "planning-finished-work-evidence/v1",
            "systems": [],
            "item_count": 0,
            "items": [],
            "reason": "optional evidence file not present",
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return {
            "status": "invalid",
            "path": relative_path,
            "kind": "planning-finished-work-evidence/v1",
            "systems": [],
            "item_count": 0,
            "items": [],
            "reason": f"failed to load optional evidence: {exc}",
        }
    if not isinstance(payload, dict) or payload.get("kind") != "planning-finished-work-evidence/v1":
        return {
            "status": "invalid",
            "path": relative_path,
            "kind": "planning-finished-work-evidence/v1",
            "systems": [],
            "item_count": 0,
            "items": [],
            "reason": "optional evidence file does not match planning-finished-work-evidence/v1",
        }
    schema_findings = _json_schema_findings(payload=payload, schema_path=FINISHED_WORK_EVIDENCE_SCHEMA_PATH)
    if schema_findings:
        return _evidence_schema_invalid_payload(
            relative_path=relative_path,
            kind="planning-finished-work-evidence/v1",
            findings=schema_findings,
        )
    normalized_items: list[dict[str, Any]] = []
    systems: list[str] = []
    for raw in payload.get("items", []):
        if not isinstance(raw, dict):
            continue
        system = str(raw.get("system", "")).strip()
        item = {
            "system": system,
            "id": str(raw.get("id", "")).strip(),
            "title": str(raw.get("title", "")).strip(),
            "status": str(raw.get("status", "")).strip().lower(),
            "kind": str(raw.get("kind", "")).strip(),
            "reopens": [str(entry).strip() for entry in raw.get("reopens", []) if str(entry).strip()],
            "reason": str(raw.get("reason", "")).strip(),
        }
        if not item["id"]:
            continue
        normalized_items.append(item)
        if system and system not in systems:
            systems.append(system)
    return {
        "status": "loaded",
        "path": relative_path,
        "kind": "planning-finished-work-evidence/v1",
        "systems": systems,
        "item_count": len(normalized_items),
        "items": normalized_items,
        "reason": "",
    }


def _finished_work_reopeners(*, issue_refs: list[str], evidence_items: Any) -> list[dict[str, str]]:
    if not issue_refs or not isinstance(evidence_items, list):
        return []
    reopeners: list[dict[str, str]] = []
    for raw in evidence_items:
        if not isinstance(raw, dict):
            continue
        if str(raw.get("status", "")).strip().lower() != "open":
            continue
        reopens = [str(entry).strip() for entry in raw.get("reopens", []) if str(entry).strip()]
        if not reopens or not any(ref in reopens for ref in issue_refs):
            continue
        reopeners.append(
            {
                "id": str(raw.get("id", "")).strip(),
                "title": str(raw.get("title", "")).strip(),
                "system": str(raw.get("system", "")).strip(),
            }
        )
    return reopeners


def _finished_work_reopening_evidence_items(
    *,
    finished_evidence: dict[str, Any],
    external_evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    external_items = [item for item in external_evidence.get("items", []) if isinstance(item, dict)]
    external_by_id = {str(item.get("id", "")).strip(): item for item in external_items if str(item.get("id", "")).strip()}
    items: list[dict[str, Any]] = []
    for raw in finished_evidence.get("items", []):
        if not isinstance(raw, dict):
            continue
        item = dict(raw)
        external_item = external_by_id.get(str(item.get("id", "")).strip())
        if external_item:
            item["status"] = str(external_item.get("status", "")).strip().lower()
            item["title"] = str(external_item.get("title", "")).strip()
        item["source"] = finished_evidence.get("path", "")
        items.append(item)
    for raw in external_items:
        reopens = [str(entry).strip() for entry in raw.get("reopens", []) if str(entry).strip()]
        if not reopens:
            continue
        item = dict(raw)
        item["source"] = external_evidence.get("path", "")
        items.append(item)
    return items


def _internal_continuation_signals(*, target_root: Path, roadmap_lanes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    archive_dir = target_root / ".agentic-workspace" / "planning" / "execplans" / "archive"
    if not archive_dir.exists():
        return []
    signals: list[dict[str, Any]] = []
    for path in sorted(archive_dir.glob("*.md")):
        if path.name == "README.md":
            continue
        closure = _execplan_closure_check(path)
        if str(closure.get("closure decision", "")).strip().lower() != "archive-but-keep-lane-open":
            continue
        label = _roadmap_continuation_label(path)
        required = _execplan_required_continuation(path)
        owner_surface = str(required.get("owner surface", "")).strip()
        if label and _roadmap_has_lane(roadmap_lanes=roadmap_lanes, label=label):
            continue
        if owner_surface and owner_surface not in {"none", "n/a"} and (target_root / owner_surface).exists():
            continue
        relative = path.relative_to(target_root).as_posix()
        signals.append(
            {
                "kind": "missing_internal_continuation_owner",
                "severity": "warning",
                "path": relative,
                "message": (f"Archived partial-intent plan {relative} no longer has a visible checked-in continuation owner."),
                "refs": [relative, owner_surface or ".agentic-workspace/planning/state.toml"],
            }
        )
    return signals


def _roadmap_has_lane(*, roadmap_lanes: list[dict[str, Any]], label: str) -> bool:
    tokens = _label_tokens(label)
    if not tokens:
        return False
    for lane in roadmap_lanes:
        if not isinstance(lane, dict):
            continue
        identity = " ".join(str(value).strip().lower() for value in (lane.get("title", ""), lane.get("id", "")) if str(value).strip())
        if all(token in identity for token in tokens):
            return True
    return False


def _ownership_review(target_root: Path) -> dict[str, Any]:
    manifest_path = target_root / ".agentic-workspace" / "OWNERSHIP.toml"
    if not manifest_path.exists():
        manifest_path = Path(__file__).resolve().with_name("_ownership.toml")

    with manifest_path.open("rb") as handle:
        ledger = tomllib.load(handle)

    module_roots = [
        {
            "module": str(entry.get("module", "")).strip(),
            "path": str(entry.get("path", "")).strip(),
            "ownership": str(entry.get("ownership", "")).strip(),
            "uninstall_policy": str(entry.get("uninstall_policy", "")).strip(),
        }
        for entry in ledger.get("module_roots", [])
        if isinstance(entry, dict)
    ]
    authority_surfaces = [
        {
            "concern": str(entry.get("concern", "")).strip(),
            "surface": str(entry.get("surface", "")).strip(),
            "owner": str(entry.get("owner", "")).strip(),
            "ownership": str(entry.get("ownership", "")).strip(),
            "authority": str(entry.get("authority", "")).strip(),
            "summary": str(entry.get("summary", "")).strip(),
        }
        for entry in ledger.get("authority_surfaces", [])
        if isinstance(entry, dict)
    ]
    fences = [
        {
            "name": str(entry.get("name", "")).strip(),
            "file": str(entry.get("file", "")).strip(),
            "start": str(entry.get("start", "")).strip(),
            "end": str(entry.get("end", "")).strip(),
            "ownership": str(entry.get("ownership", "")).strip(),
            "uninstall_policy": str(entry.get("uninstall_policy", "")).strip(),
        }
        for entry in ledger.get("fences", [])
        if isinstance(entry, dict)
    ]
    package_owned_roots = [entry["path"] for entry in module_roots if entry.get("path")]
    repo_owned_surfaces = [
        entry["surface"] for entry in authority_surfaces if entry.get("ownership") == "repo_owned" and entry.get("surface")
    ]
    module_managed_surfaces = [
        entry["surface"] for entry in authority_surfaces if entry.get("ownership") == "module_managed" and entry.get("surface")
    ]
    shared_package_surfaces = [
        entry["surface"]
        for entry in authority_surfaces
        if entry.get("ownership") in {"workspace_shared", "module_managed"} and entry.get("surface")
    ]
    repo_specific_package_surfaces = [
        entry["surface"] for entry in authority_surfaces if entry.get("ownership") == "repo_specific_package_owned" and entry.get("surface")
    ]
    minimal_repo_hook = next((f"{entry['file']}#agentic-workspace:workflow" for entry in fences if entry.get("file")), "")
    return {
        "status": "present",
        "package_owned_roots": package_owned_roots,
        "repo_owned_surfaces": repo_owned_surfaces,
        "module_managed_surfaces": module_managed_surfaces,
        "shared_package_surfaces": shared_package_surfaces,
        "repo_specific_package_surfaces": repo_specific_package_surfaces,
        "managed_fences": fences,
        "minimal_repo_hook": minimal_repo_hook,
        "authority_surfaces": authority_surfaces,
    }


def _roadmap_candidate_lanes(roadmap_path: Path) -> list[dict[str, Any]]:
    lane_lines = _section_lines(_read_lines(roadmap_path), "Candidate Lanes")
    if not lane_lines:
        return []

    lanes: list[dict[str, Any]] = []
    current_block: list[str] = []
    for line in lane_lines:
        if re.match(r"^\s*-\s+", line):
            if current_block:
                lane = _parse_candidate_lane_block(current_block)
                if lane is not None:
                    lanes.append(lane)
            current_block = [line]
            continue
        if current_block:
            current_block.append(line)
    if current_block:
        lane = _parse_candidate_lane_block(current_block)
        if lane is not None:
            lanes.append(lane)
    return [_normalize_roadmap_lane_record(lane) for lane in lanes]


def _parse_candidate_lane_block(lines: list[str]) -> dict[str, Any] | None:
    if not lines:
        return None
    first = re.sub(r"^\s*-\s+", "", lines[0]).strip()
    if not first:
        return None

    fields: dict[str, str] = {}
    if ":" in first:
        key, value = first.split(":", 1)
        fields[key.strip().lower()] = value.strip()
    else:
        fields["lane"] = first

    for line in lines[1:]:
        match = re.match(r"^\s+([^:]+):\s*(.*)\s*$", line)
        if not match:
            continue
        fields[match.group(1).strip().lower()] = match.group(2).strip()

    title = fields.get("lane", "").strip()
    if not title:
        return None

    lane_id = fields.get("id", "").strip()
    priority = fields.get("priority", "").strip()
    outcome = fields.get("outcome", "").strip()
    issues = [item.strip() for item in re.split(r"\s*,\s*", fields.get("issues", "")) if item.strip()]
    reason = fields.get("why now", "").strip() or fields.get("why later", "").strip()
    promotion_signal = fields.get("promotion signal", "").strip()
    suggested_first_slice = fields.get("suggested first slice", "").strip()

    return {
        "id": lane_id,
        "title": title,
        "priority": priority,
        "issues": issues,
        "outcome": outcome,
        "reason": reason,
        "promotion_signal": promotion_signal,
        "suggested_first_slice": suggested_first_slice,
    }


def _roadmap_candidates(roadmap_path: Path) -> list[dict[str, str]]:
    lanes = _roadmap_candidate_lanes(roadmap_path)
    if lanes:
        return [
            {
                "priority": str(lane.get("priority", "")),
                "summary": str(lane.get("title", "")),
            }
            for lane in lanes
        ]

    candidate_lines = _section_lines(_read_lines(roadmap_path), "Next Candidate Queue")
    candidates: list[dict[str, str]] = []
    for line in candidate_lines:
        if not re.match(r"^\s*-\s+", line):
            continue
        text = re.sub(r"^\s*-\s+", "", line).strip()
        if not text:
            continue
        priority_match = re.match(r"^Priority\s+(\d+)\s*:\s*(.*)$", text, re.IGNORECASE)
        if priority_match:
            candidates.append(
                {
                    "priority": priority_match.group(1),
                    "summary": priority_match.group(2).strip(),
                }
            )
            continue
        candidates.append({"priority": "", "summary": text})
    return candidates


def _active_intent_contract(
    *,
    target_root: Path,
    active_items: list[dict[str, str]],
    active_execplans: list[dict[str, str]],
) -> dict[str, Any]:
    if len(active_execplans) != 1 or len(active_items) > 1:
        return {
            "status": "unavailable",
            "reason": "requires exactly one active execplan and at most one active TODO item",
        }

    active_item = active_items[0] if active_items else None
    active_execplan_path = active_execplans[0]["path"].strip()
    surface = (
        str(active_item.get("surface") or active_item.get("execplan") or active_item.get("path") or "").strip()
        if active_item
        else active_execplan_path
    )
    plan_path = _resolve_execplan_path(target_root, surface) or _resolve_execplan_path(target_root, active_execplan_path)
    if plan_path is None or not plan_path.exists():
        return {
            "status": "unavailable",
            "reason": "active planning state does not resolve to a live execplan path",
        }

    canonical_core = _execplan_canonical_core(plan_path)
    execplan_profile = _execplan_profile(plan_path)
    delegated_judgment = _execplan_delegated_judgment(plan_path)
    requested_outcome = str(canonical_core.get("requested_outcome") or delegated_judgment.get("requested outcome", "")).strip()
    hard_constraints = str(canonical_core.get("hard_constraints") or delegated_judgment.get("hard constraints", "")).strip()
    agent_may_decide = str(canonical_core.get("agent_may_decide") or delegated_judgment.get("agent may decide locally", "")).strip()
    escalate_when = str(canonical_core.get("escalate_when") or delegated_judgment.get("escalate when", "")).strip()
    if not requested_outcome or not hard_constraints or not agent_may_decide or not escalate_when:
        return {
            "status": "unavailable",
            "reason": "active execplan is missing delegated-judgment fields",
        }

    touched_scope = _canonical_core_string_list(canonical_core, "touched_scope") or _extract_section_bullets(plan_path, "Touched Paths")
    proof_expectations = _canonical_core_string_list(canonical_core, "proof_expectations") or _extract_section_bullets(
        plan_path, "Validation Commands"
    )
    required_tools = [tool for tool in _extract_section_bullets(plan_path, "Required Tools") if tool.lower() not in {"none", "none."}]
    references = _execplan_references(plan_path)
    role_metadata = _planning_state_role_metadata(active_item)
    next_role_needed = _next_role_needed_from_metadata(role_metadata)
    minimal_refs = _dedupe(
        [
            ".agentic-workspace/planning/state.toml",
            plan_path.relative_to(target_root).as_posix(),
            *([surface] if surface else []),
            *(reference.get("target", "") for reference in references),
        ]
    )
    return {
        "status": "present",
        "todo_item": {
            "id": active_item.get("id", "").strip() if active_item else "",
            "surface": surface,
            "why_now": active_item.get("why_now", "").strip() if active_item else "",
        },
        "role_metadata": role_metadata,
        "next_role_needed": next_role_needed,
        "intent": {
            "requested_outcome": requested_outcome,
            "hard_constraints": hard_constraints,
            "agent_may_decide": agent_may_decide,
            "escalate_when": escalate_when,
        },
        "capability_posture": _execplan_capability_posture(plan_path),
        "execplan_profile": execplan_profile,
        "canonical_core": canonical_core,
        "references": references,
        "touched_scope": touched_scope,
        "proof_expectations": proof_expectations,
        "tool_verification": {
            "status": "required-tools-declared" if required_tools else "unspecified",
            "required_tools": required_tools,
            "rule": "If a required tool is unavailable, stop or escalate before attempting the task.",
        },
        "minimal_refs": minimal_refs,
    }


def _active_resumable_contract(
    *,
    target_root: Path,
    active_contract: dict[str, Any],
    active_execplans: list[dict[str, str]],
) -> dict[str, Any]:
    if active_contract.get("status") != "present" or len(active_execplans) != 1:
        return {
            "status": "unavailable",
            "reason": "requires one active execplan with a present active intent contract",
        }

    plan_path = _resolve_execplan_path(target_root, active_execplans[0]["path"])
    if plan_path is None or not plan_path.exists():
        return {
            "status": "unavailable",
            "reason": "active execplan path is not available for resumable-contract extraction",
        }

    milestone = _execplan_active_milestone(plan_path)
    canonical_core = _execplan_canonical_core(plan_path)
    next_action_projection = _execplan_next_action_projection(plan_path)
    current_next_action = next_action_projection["next_action"]
    completion_criteria = _canonical_core_string_list(canonical_core, "completion_criteria") or _extract_section_bullets(
        plan_path,
        "Completion Criteria",
    )
    blockers = [item for item in _extract_section_bullets(plan_path, "Blockers") if item.lower() != "none."]
    if not current_next_action or not completion_criteria:
        return {
            "status": "unavailable",
            "reason": "active execplan is missing current next action or completion criteria",
        }

    return {
        "status": "present",
        "current_next_action": current_next_action,
        "current_next_action_source": next_action_projection["source"],
        "active_milestone": {
            "id": milestone.get("id", "").strip(),
            "status": milestone.get("status", "").strip(),
            "scope": milestone.get("scope", "").strip(),
            "ready": milestone.get("ready", "").strip(),
            "blocked": milestone.get("blocked", "").strip(),
        },
        "completion_criteria": completion_criteria,
        "proof_expectations": list(active_contract["proof_expectations"]),
        "tool_verification": dict(active_contract["tool_verification"]),
        "escalate_when": active_contract["intent"]["escalate_when"],
        "blockers": blockers,
        "minimal_refs": list(active_contract["minimal_refs"]),
    }


def _canonical_planning_record(
    *,
    target_root: Path,
    active_contract: dict[str, Any],
    resumable_contract: dict[str, Any],
) -> dict[str, Any]:
    if active_contract.get("status") != "present" or resumable_contract.get("status") != "present":
        reasons: list[str] = []
        if active_contract.get("status") != "present":
            reasons.append(active_contract.get("reason", "active contract unavailable"))
        if resumable_contract.get("status") != "present":
            reasons.append(resumable_contract.get("reason", "resumable contract unavailable"))
        return {
            "status": "unavailable",
            "reason": "; ".join(_dedupe(reasons)),
        }

    todo_item = active_contract.get("todo_item", {})
    active_milestone = resumable_contract.get("active_milestone", {})
    minimal_refs = list(resumable_contract.get("minimal_refs", []))
    plan_path = _resolve_execplan_path(target_root, str(todo_item.get("surface", "")).strip() or active_milestone.get("id", ""))
    proof_report: dict[str, str] = {}
    intent_satisfaction: dict[str, str] = {}
    system_intent_alignment: dict[str, str] = {}
    closure_check: dict[str, str] = {}
    required_continuation: dict[str, str] = {}
    intent_interpretation: dict[str, str] = {}
    execution_bounds: dict[str, str] = {}
    stop_conditions: dict[str, str] = {}
    execution_run: dict[str, str] = {}
    finished_run_review: dict[str, str] = {}
    post_decomposition_delegation: dict[str, str] = {}
    delegation_outcome_feedback: dict[str, str] = {}
    adaptive_assurance: dict[str, Any] = {}
    traceability_refs: dict[str, Any] = {}
    control_gates: list[Any] = []
    implementation_blockers: list[Any] = []
    risk_registry_refs: list[Any] = []
    invariant_refs: list[Any] = []
    test_data_policy: dict[str, Any] = {}
    layer_scaffold: dict[str, Any] = {}
    architecture_decision_promotion: dict[str, Any] = {}
    threat_failure_aids: list[Any] = []
    review_residue: list[dict[str, Any]] = []
    prep_only_contract: dict[str, Any] = {}
    canonical_core: dict[str, Any] = {}
    execplan_profile: dict[str, Any] = {}
    if plan_path is not None:
        canonical_core = _execplan_canonical_core(plan_path)
        execplan_profile = _execplan_profile(plan_path)
        proof_report = _execplan_proof_report(plan_path)
        intent_satisfaction = _execplan_intent_satisfaction(plan_path)
        system_intent_alignment = _execplan_system_intent_alignment(plan_path)
        closure_check = _execplan_closure_check(plan_path)
        required_continuation = _execplan_required_continuation(plan_path)
        intent_interpretation = _execplan_intent_interpretation(plan_path)
        execution_bounds = _execplan_execution_bounds(plan_path)
        stop_conditions = _execplan_stop_conditions(plan_path)
        execution_run = _execplan_execution_run(plan_path)
        finished_run_review = _execplan_finished_run_review(plan_path)
        post_decomposition_delegation = _execplan_post_decomposition_delegation(plan_path)
        delegation_outcome_feedback = _execplan_delegation_outcome_feedback(plan_path)
        adaptive_assurance = _execplan_raw_dict(plan_path, "adaptive_assurance")
        traceability_refs = _execplan_raw_dict(plan_path, "traceability_refs")
        control_gates = _execplan_raw_list(plan_path, "control_gates")
        implementation_blockers = _execplan_raw_list(plan_path, "implementation_blockers")
        risk_registry_refs = _execplan_raw_list(plan_path, "risk_registry_refs")
        invariant_refs = _execplan_raw_list(plan_path, "invariant_refs")
        test_data_policy = _execplan_raw_dict(plan_path, "test_data_policy")
        layer_scaffold = _execplan_raw_dict(plan_path, "layer_scaffold")
        architecture_decision_promotion = _execplan_raw_dict(plan_path, "architecture_decision_promotion")
        threat_failure_aids = _execplan_raw_list(plan_path, "threat_failure_aids")
        prep_only_contract = _execplan_prep_only_contract(plan_path)
        review_residue = _review_residue_from_references(
            target_root=target_root,
            references=list(active_contract.get("references", [])),
        )
    continuation_owner = str(todo_item.get("surface", "")).strip()
    canonical_continuation_owner = str(canonical_core.get("continuation_owner", "")).strip()
    if canonical_continuation_owner and canonical_continuation_owner.lower() not in {"none", "n/a"}:
        continuation_owner = canonical_continuation_owner
    if not continuation_owner and minimal_refs:
        continuation_owner = minimal_refs[-1]
    return {
        "status": "present",
        "task": {
            "id": str(todo_item.get("id", "")).strip() or str(active_milestone.get("id", "")).strip(),
            "surface": str(todo_item.get("surface", "")).strip(),
            "status": str(active_milestone.get("status", "")).strip(),
        },
        "requested_outcome": str(active_contract["intent"]["requested_outcome"]).strip(),
        "hard_constraints": str(active_contract["intent"]["hard_constraints"]).strip(),
        "agent_may_decide": str(active_contract["intent"]["agent_may_decide"]).strip(),
        "capability_posture": dict(active_contract.get("capability_posture", {})),
        "execplan_profile": execplan_profile,
        "canonical_core": canonical_core,
        "role_metadata": dict(active_contract.get("role_metadata", {})),
        "next_role_needed": str(active_contract.get("next_role_needed", "")).strip(),
        "references": list(active_contract.get("references", [])),
        "review_residue": review_residue,
        "post_decomposition_delegation": post_decomposition_delegation,
        "next_action": str(resumable_contract["current_next_action"]).strip(),
        "proof_expectations": list(resumable_contract.get("proof_expectations", [])),
        "proof_report": proof_report,
        "intent_satisfaction": intent_satisfaction,
        "system_intent_alignment": system_intent_alignment,
        "closure_check": closure_check,
        "required_continuation": required_continuation,
        "intent_interpretation": intent_interpretation,
        "execution_bounds": execution_bounds,
        "stop_conditions": stop_conditions,
        "execution_run": execution_run,
        "finished_run_review": finished_run_review,
        "delegation_outcome_feedback": delegation_outcome_feedback,
        "adaptive_assurance": adaptive_assurance,
        "traceability_refs": traceability_refs,
        "control_gates": control_gates,
        "implementation_blockers": implementation_blockers,
        "risk_registry_refs": risk_registry_refs,
        "invariant_refs": invariant_refs,
        "test_data_policy": test_data_policy,
        "layer_scaffold": layer_scaffold,
        "architecture_decision_promotion": architecture_decision_promotion,
        "threat_failure_aids": threat_failure_aids,
        "prep_only_contract": prep_only_contract,
        "tool_verification": dict(resumable_contract.get("tool_verification", {})),
        "escalate_when": str(resumable_contract.get("escalate_when", "")).strip(),
        "continuation_owner": continuation_owner,
        "touched_scope": list(active_contract.get("touched_scope", [])),
        "completion_criteria": list(resumable_contract.get("completion_criteria", [])),
        "blockers": list(resumable_contract.get("blockers", [])),
        "minimal_refs": minimal_refs,
    }


def _active_follow_through_contract(
    *,
    target_root: Path,
    planning_record: dict[str, Any],
    active_execplans: list[dict[str, str]],
) -> dict[str, Any]:
    if planning_record.get("status") != "present" or len(active_execplans) != 1:
        return {
            "status": "unavailable",
            "reason": "requires one active execplan with a present planning record",
        }

    plan_path = _resolve_execplan_path(target_root, active_execplans[0]["path"])
    if plan_path is None or not plan_path.exists():
        return {
            "status": "unavailable",
            "reason": "active execplan path is not available for follow-through extraction",
        }

    follow_through = _execplan_iterative_follow_through(plan_path)
    required_fields = {
        "what this slice enabled",
        "intentionally deferred",
        "discovered implications",
        "proof achieved now",
        "validation still needed",
        "next likely slice",
    }
    if not required_fields.issubset(follow_through):
        return {
            "status": "unavailable",
            "reason": "active execplan is missing iterative follow-through fields",
        }

    intent_continuity = _execplan_intent_continuity(plan_path)
    larger_intended_outcome = intent_continuity.get("larger intended outcome", "").strip()
    continuation_surface = intent_continuity.get("continuation surface", "").strip()
    if not larger_intended_outcome:
        return {
            "status": "unavailable",
            "reason": "active execplan is missing larger intended outcome for iterative follow-through",
        }

    minimal_refs = _dedupe(
        [
            *planning_record.get("minimal_refs", []),
            *([continuation_surface] if continuation_surface and continuation_surface.lower() != "none" else []),
        ]
    )
    return {
        "status": "present",
        "larger_intended_outcome": larger_intended_outcome,
        "continuation_surface": continuation_surface,
        "what_this_slice_enabled": follow_through.get("what this slice enabled", "").strip(),
        "intentionally_deferred": follow_through.get("intentionally deferred", "").strip(),
        "discovered_implications": follow_through.get("discovered implications", "").strip(),
        "proof_achieved_now": follow_through.get("proof achieved now", "").strip(),
        "validation_still_needed": follow_through.get("validation still needed", "").strip(),
        "next_likely_slice": follow_through.get("next likely slice", "").strip(),
        "minimal_refs": minimal_refs,
    }


def _active_intent_interpretation_contract(
    *,
    target_root: Path,
    planning_record: dict[str, Any],
    active_execplans: list[dict[str, str]],
) -> dict[str, Any]:
    if planning_record.get("status") != "present" or len(active_execplans) != 1:
        return {
            "status": "unavailable",
            "reason": "requires one active execplan with a present planning record",
        }

    plan_path = _resolve_execplan_path(target_root, active_execplans[0]["path"])
    if plan_path is None or not plan_path.exists():
        return {
            "status": "unavailable",
            "reason": "active execplan path is not available for intent-interpretation extraction",
        }

    interpretation = _execplan_intent_interpretation(plan_path)
    required_fields = {
        "literal request",
        "inferred intended outcome",
        "chosen concrete what",
        "interpretation distance",
        "review guidance",
    }
    if not required_fields.issubset(interpretation):
        return {
            "status": "unavailable",
            "reason": "active execplan is missing intent-interpretation fields",
        }

    minimal_refs = _dedupe(
        [
            *planning_record.get("minimal_refs", []),
            ".agentic-workspace/docs/execution-flow-contract.md",
        ]
    )
    return {
        "status": "present",
        "literal_request": interpretation.get("literal request", "").strip(),
        "inferred_intended_outcome": interpretation.get("inferred intended outcome", "").strip(),
        "chosen_concrete_what": interpretation.get("chosen concrete what", "").strip(),
        "interpretation_distance": interpretation.get("interpretation distance", "").strip(),
        "review_guidance": interpretation.get("review guidance", "").strip(),
        "minimal_refs": minimal_refs,
    }


def _active_context_budget_contract(
    *,
    target_root: Path,
    planning_record: dict[str, Any],
    active_execplans: list[dict[str, str]],
) -> dict[str, Any]:
    if planning_record.get("status") != "present" or len(active_execplans) != 1:
        return {
            "status": "unavailable",
            "reason": "requires one active execplan with a present planning record",
        }

    plan_path = _resolve_execplan_path(target_root, active_execplans[0]["path"])
    if plan_path is None or not plan_path.exists():
        return {
            "status": "unavailable",
            "reason": "active execplan path is not available for context-budget extraction",
        }

    context_budget = _execplan_context_budget(plan_path)
    required_fields = {
        "live working set",
        "recoverable later",
        "externalize before shift",
        "pre-work config pull",
        "pre-work memory pull",
        "tiny resumability note",
        "context-shift triggers",
    }
    if not required_fields.issubset(context_budget):
        return {
            "status": "unavailable",
            "reason": "active execplan is missing context-budget fields",
        }

    minimal_refs = _dedupe(
        [
            *planning_record.get("minimal_refs", []),
            ".agentic-workspace/docs/context-budget-contract.md",
        ]
    )
    interaction_cost_rule = (
        "Prefer the smallest live bundle that can still finish the current bounded step, "
        "externalize proof/review/continuation residue before shedding context, and reload only on explicit shift triggers."
    )
    return {
        "status": "present",
        "live_working_set": context_budget.get("live working set", "").strip(),
        "recoverable_later": context_budget.get("recoverable later", "").strip(),
        "externalize_before_shift": context_budget.get("externalize before shift", "").strip(),
        "pre_work_config_pull": context_budget.get("pre-work config pull", "").strip(),
        "pre_work_memory_pull": context_budget.get("pre-work memory pull", "").strip(),
        "tiny_resumability_note": context_budget.get("tiny resumability note", "").strip(),
        "context_shift_triggers": context_budget.get("context-shift triggers", "").strip(),
        "interaction_cost_rule": interaction_cost_rule,
        "resume_rule": (
            "Use the tiny resumability note plus explicit minimal refs instead of broad rereads when returning after an interruption or tool switch."
        ),
        "minimal_refs": minimal_refs,
    }


def _active_execution_run_contract(
    *,
    target_root: Path,
    planning_record: dict[str, Any],
    active_execplans: list[dict[str, str]],
) -> dict[str, Any]:
    if planning_record.get("status") != "present" or len(active_execplans) != 1:
        return {
            "status": "unavailable",
            "reason": "requires one active execplan with a present planning record",
        }

    plan_path = _resolve_execplan_path(target_root, active_execplans[0]["path"])
    if plan_path is None or not plan_path.exists():
        return {
            "status": "unavailable",
            "reason": "active execplan path is not available for execution-run extraction",
        }

    execution_run = _execplan_execution_run(plan_path)
    required_fields = {
        "run status",
        "executor",
        "handoff source",
        "what happened",
        "scope touched",
        "changed surfaces",
        "validations run",
        "result for continuation",
        "next step",
    }
    if not required_fields.issubset(execution_run):
        return {
            "status": "unavailable",
            "reason": "active execplan is missing execution-run fields",
        }

    minimal_refs = _dedupe(
        [
            *planning_record.get("minimal_refs", []),
            ".agentic-workspace/docs/execution-flow-contract.md",
        ]
    )
    return {
        "status": "present",
        "run_status": execution_run.get("run status", "").strip(),
        "executor": execution_run.get("executor", "").strip(),
        "handoff_source": execution_run.get("handoff source", "").strip(),
        "what_happened": execution_run.get("what happened", "").strip(),
        "scope_touched": execution_run.get("scope touched", "").strip(),
        "changed_surfaces": execution_run.get("changed surfaces", "").strip(),
        "validations_run": execution_run.get("validations run", "").strip(),
        "result_for_continuation": execution_run.get("result for continuation", "").strip(),
        "next_step": execution_run.get("next step", "").strip(),
        "minimal_refs": minimal_refs,
    }


def _active_finished_run_review_contract(
    *,
    target_root: Path,
    planning_record: dict[str, Any],
    active_execplans: list[dict[str, str]],
    execution_run_contract: dict[str, Any],
    intent_interpretation_contract: dict[str, Any],
) -> dict[str, Any]:
    if planning_record.get("status") != "present" or len(active_execplans) != 1:
        return {
            "status": "unavailable",
            "reason": "requires one active execplan with a present planning record",
        }

    plan_path = _resolve_execplan_path(target_root, active_execplans[0]["path"])
    if plan_path is None or not plan_path.exists():
        return {
            "status": "unavailable",
            "reason": "active execplan path is not available for finished-run review extraction",
        }

    review = _execplan_finished_run_review(plan_path)
    required_fields = {
        "review status",
        "scope respected",
        "proof status",
        "intent served",
        "config compliance",
        "misinterpretation risk",
        "follow-on decision",
    }
    if not required_fields.issubset(review):
        return {
            "status": "unavailable",
            "reason": "active execplan is missing finished-run review fields",
        }

    minimal_refs = _dedupe(
        [
            *planning_record.get("minimal_refs", []),
            *(execution_run_contract.get("minimal_refs", []) if execution_run_contract.get("status") == "present" else []),
            *(intent_interpretation_contract.get("minimal_refs", []) if intent_interpretation_contract.get("status") == "present" else []),
            ".agentic-workspace/docs/reporting-contract.md",
        ]
    )
    config_signal = _finished_run_config_signal(
        review_status=review.get("review status", "").strip(),
        config_compliance=review.get("config compliance", "").strip(),
    )
    return {
        "status": "present",
        "review_status": review.get("review status", "").strip(),
        "scope_respected": review.get("scope respected", "").strip(),
        "proof_status": review.get("proof status", "").strip(),
        "intent_served": review.get("intent served", "").strip(),
        "config_compliance": review.get("config compliance", "").strip(),
        "config_trust": config_signal["config_trust"],
        "recommended_next_action": config_signal["recommended_next_action"],
        "misinterpretation_risk": review.get("misinterpretation risk", "").strip(),
        "follow_on_decision": review.get("follow-on decision", "").strip(),
        "minimal_refs": minimal_refs,
    }


def _finished_run_config_signal(*, review_status: str, config_compliance: str) -> dict[str, str]:
    normalized_review = review_status.strip().lower()
    normalized_config = config_compliance.strip().lower()
    if (
        not normalized_config
        or normalized_review in {"pending", "not-run-yet", "draft"}
        or normalized_config
        in {
            "pending",
            "not-run-yet",
            "n/a",
            "not applicable",
        }
    ):
        return {
            "config_trust": "pending",
            "recommended_next_action": "Complete the finished-run review before treating config handling as settled.",
        }

    lower_trust_markers = (
        "bypass",
        "bypassed",
        "ignore",
        "ignored",
        "skip",
        "skipped",
        "missing",
        "underspecified",
        "unclear",
        "unknown",
        "not pulled",
        "not consulted",
        "not checked",
        "violated",
        "drift",
        "mismatch",
    )
    if any(marker in normalized_config for marker in lower_trust_markers):
        return {
            "config_trust": "lower-trust",
            "recommended_next_action": (
                "Config compliance indicates bypass, omission, or ambiguity; lower trust in this closeout until the config gap is repaired or explicitly accepted."
            ),
        }

    positive_markers = (
        "respect",
        "compliant",
        "followed",
        "honor",
        "honour",
        "aligned",
    )
    if any(marker in normalized_config for marker in positive_markers):
        return {
            "config_trust": "clear",
            "recommended_next_action": "No additional config-trust follow-up is required for this run.",
        }

    return {
        "config_trust": "lower-trust",
        "recommended_next_action": (
            "Finished-run config compliance is too ambiguous to trust by default; restate whether config was respected, bypassed, or irrelevant before closing cleanly."
        ),
    }


def _active_closeout_distillation_contract(
    *,
    target_root: Path,
    planning_record: dict[str, Any],
    active_execplans: list[dict[str, str]],
) -> dict[str, Any]:
    if planning_record.get("status") != "present" or len(active_execplans) != 1:
        return {
            "status": "unavailable",
            "reason": "requires one active execplan with a present planning record",
        }

    plan_path = _resolve_execplan_path(target_root, active_execplans[0]["path"])
    if plan_path is None or not plan_path.exists():
        return {
            "status": "unavailable",
            "reason": "active execplan path is not available for closeout distillation extraction",
        }

    record = _load_execplan_record(plan_path) or {}
    explicit = _record_section_dict(record, "closeout_distillation") or {}
    buckets = _closeout_distillation_buckets(record=record, explicit=explicit)
    counts = {bucket: len(items) for bucket, items in buckets.items()}
    promoted_count = sum(counts[bucket] for bucket in ("memory", "config_check", "docs", "issue_follow_up", "continuation"))
    discarded_count = counts["discard"]
    recommended_next_action = "Closeout distillation is ready for plan removal or continuation routing."
    if not promoted_count and not discarded_count:
        recommended_next_action = (
            "Complete closeout distillation before closeout so durable learning has an owner or is intentionally discarded."
        )
    elif discarded_count:
        recommended_next_action = (
            "Do not promote discarded execution detail; keep only the named continuation and durable-owner buckets live."
        )

    return {
        "status": "present",
        "current_plan": plan_path.relative_to(target_root).as_posix(),
        "rule": (
            "Closeout should route durable learning to continuation, Memory, config/checks, docs, or issue follow-up, "
            "and explicitly discard non-recurring execution detail instead of making archived execplans the normal knowledge base."
        ),
        "archive_role": "completed execplans are removed after distillation by default; legacy archives are compatibility evidence only",
        "buckets": buckets,
        "counts": {
            **counts,
            "promoted_or_routed_count": promoted_count,
            "intentionally_discarded_count": discarded_count,
        },
        "recommended_next_action": recommended_next_action,
        "minimal_refs": _dedupe(
            [
                planning_record.get("task", {}).get("surface", ""),
                ".agentic-workspace/planning/execplans/README.md",
                ".agentic-workspace/docs/execution-flow-contract.md",
            ]
        ),
    }


def _closeout_distillation_buckets(*, record: dict[str, Any], explicit: dict[str, str]) -> dict[str, list[dict[str, str]]]:
    buckets = {
        "discard": [],
        "continuation": [],
        "memory": [],
        "config_check": [],
        "docs": [],
        "issue_follow_up": [],
    }
    explicit_buckets = record.get("closeout_distillation", {}) if isinstance(record, dict) else {}
    if isinstance(explicit_buckets, dict):
        raw_buckets = explicit_buckets.get("buckets", {})
        if isinstance(raw_buckets, dict):
            for bucket in buckets:
                raw_items = raw_buckets.get(bucket, [])
                if isinstance(raw_items, list):
                    buckets[bucket].extend(_normalize_distillation_items(raw_items))

    execution_summary = _record_section_dict(record, "execution_summary") or {}
    closure_check = _record_section_dict(record, "closure_check") or {}
    required_continuation = _record_section_dict(record, "required_continuation") or {}
    knowledge = execution_summary.get("knowledge promoted (memory/docs/config)", "").strip()
    posterity = execution_summary.get("post-work posterity capture", "").strip()
    follow_on = execution_summary.get("follow-on routed to", "").strip()

    if not buckets["continuation"] and follow_on and follow_on.lower() not in {"none", "none yet", "n/a", "no further action"}:
        buckets["continuation"].append(
            {
                "summary": follow_on,
                "owner": required_continuation.get("owner surface", "") or closure_check.get("evidence carried forward", ""),
                "source": "execution_summary.follow-on routed to",
            }
        )
    if not buckets["continuation"] and required_continuation.get(
        "required follow-on for the larger intended outcome", ""
    ).strip().lower() in {
        "yes",
        "true",
        "required",
    }:
        buckets["continuation"].append(
            {
                "summary": required_continuation.get("activation trigger", ""),
                "owner": required_continuation.get("owner surface", ""),
                "source": "required_continuation",
            }
        )

    combined_learning = " ".join(value for value in (knowledge, posterity, explicit.get("summary", "")) if value).lower()
    if "memory" in combined_learning:
        buckets["memory"].append({"summary": knowledge or posterity, "owner": "Memory", "source": "execution_summary"})
    if any(marker in combined_learning for marker in ("config", "check", "checker", "validation", "test")):
        buckets["config_check"].append({"summary": knowledge or posterity, "owner": "config/check", "source": "execution_summary"})
    if "doc" in combined_learning:
        buckets["docs"].append({"summary": knowledge or posterity, "owner": "docs", "source": "execution_summary"})

    improvement_review = _record_section_value(record, "improvement_signal_review") or {}
    for item in _improvement_signal_review_distillation_items(improvement_review):
        bucket = item.pop("bucket", "discard")
        if bucket in buckets:
            buckets[bucket].append(item)

    for ref in [] if buckets["issue_follow_up"] else (_record_section_references(record, "references") or []):
        role = str(ref.get("role", "")).lower()
        if "follow" in role or "issue" in str(ref.get("kind", "")).lower():
            buckets["issue_follow_up"].append(
                {
                    "summary": str(ref.get("label", "")).strip() or str(ref.get("target", "")).strip(),
                    "owner": str(ref.get("kind", "")).strip(),
                    "source": str(ref.get("target", "")).strip(),
                }
            )

    if not buckets["discard"] and (not knowledge or knowledge.strip().lower() in {"none", "none.", "n/a", "not needed", "no"}):
        buckets["discard"].append(
            {
                "summary": "No Memory, docs, or config promotion was needed for local execution detail.",
                "owner": "discard",
                "source": "execution_summary.knowledge promoted (Memory/Docs/Config)",
            }
        )
    return {bucket: _dedupe_distillation_items(items) for bucket, items in buckets.items()}


def _improvement_signal_review_distillation_items(review: dict[str, Any]) -> list[dict[str, str]]:
    status = str(review.get("status", "")).strip().lower()
    items: list[dict[str, str]] = []
    for key in ("signals routed", "signals fixed"):
        raw_items = review.get(key, [])
        if not isinstance(raw_items, list):
            continue
        for raw in raw_items:
            normalized = _normalize_improvement_signal_item(raw, source=f"improvement_signal_review.{key}")
            if normalized is not None:
                items.append(normalized)
    raw_dismissed = review.get("signals dismissed", [])
    if isinstance(raw_dismissed, list):
        for raw in raw_dismissed:
            normalized = _normalize_improvement_signal_item(
                raw, source="improvement_signal_review.signals dismissed", default_bucket="discard"
            )
            if normalized is not None:
                items.append(normalized)
    if status == "no_signal_found" and not items:
        items.append(
            {
                "bucket": "discard",
                "summary": "Improvement signal review was checked and no signal was found.",
                "owner": "none",
                "source": "improvement_signal_review.status",
            }
        )
    return items


def _normalize_improvement_signal_item(raw: Any, *, source: str, default_bucket: str | None = None) -> dict[str, str] | None:
    if isinstance(raw, str):
        summary = raw.strip()
        owner = ""
    elif isinstance(raw, dict):
        summary = str(raw.get("summary") or raw.get("signal") or raw.get("symptom") or raw.get("detail") or "").strip()
        owner = str(raw.get("owner") or raw.get("owner class") or raw.get("destination") or raw.get("target") or "").strip()
    else:
        return None
    if not summary:
        return None
    owner_lower = owner.lower()
    if default_bucket is not None:
        bucket = default_bucket
    elif "memory" in owner_lower:
        bucket = "memory"
    elif "doc" in owner_lower:
        bucket = "docs"
    elif any(marker in owner_lower for marker in ("issue", "github", "#")):
        bucket = "issue_follow_up"
    elif any(marker in owner_lower for marker in ("check", "contract", "test", "config")):
        bucket = "config_check"
    elif "planning" in owner_lower:
        bucket = "continuation"
    elif "direct fix" in owner_lower:
        bucket = "config_check"
    else:
        bucket = "discard"
    return {"bucket": bucket, "summary": summary, "owner": owner, "source": source}


def _normalize_distillation_items(raw_items: list[Any]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in raw_items:
        if isinstance(item, dict):
            summary = str(item.get("summary", "")).strip()
            if summary:
                normalized.append(
                    {
                        "summary": summary,
                        "owner": str(item.get("owner", "")).strip(),
                        "source": str(item.get("source", "")).strip(),
                    }
                )
        elif isinstance(item, str) and item.strip():
            normalized.append({"summary": item.strip(), "owner": "", "source": "closeout_distillation"})
    return normalized


def _dedupe_distillation_items(items: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in items:
        key = (item.get("summary", ""), item.get("owner", ""), item.get("source", ""))
        if key in seen or not key[0]:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _unavailable_reason_fragments(*contracts: dict[str, Any], extra: Iterable[str] = ()) -> str:
    reasons: list[str] = []
    for contract in contracts:
        if contract.get("status") != "present":
            raw_reason = str(contract.get("reason", "required planning contract unavailable")).strip()
            reasons.extend(part.strip() for part in raw_reason.split(";") if part.strip())
    reasons.extend(part.strip() for part in extra if part.strip())
    return "; ".join(_dedupe(reasons))


def _active_hierarchy_contract(
    *,
    target_root: Path,
    planning_record: dict[str, Any],
    active_contract: dict[str, Any],
    resumable_contract: dict[str, Any],
    follow_through_contract: dict[str, Any],
    context_budget_contract: dict[str, Any],
    roadmap_lanes: list[dict[str, Any]],
    active_execplans: list[dict[str, str]],
) -> dict[str, Any]:
    if (
        planning_record.get("status") != "present"
        or active_contract.get("status") != "present"
        or resumable_contract.get("status") != "present"
        or follow_through_contract.get("status") != "present"
        or context_budget_contract.get("status") != "present"
        or len(active_execplans) != 1
    ):
        extra = ["requires exactly one active execplan"] if len(active_execplans) != 1 else []
        return {
            "status": "unavailable",
            "reason": _unavailable_reason_fragments(
                planning_record,
                active_contract,
                resumable_contract,
                follow_through_contract,
                context_budget_contract,
                extra=extra,
            ),
        }

    plan_path = _resolve_execplan_path(target_root, active_execplans[0]["path"])
    if plan_path is None or not plan_path.exists():
        return {
            "status": "unavailable",
            "reason": "active execplan path is not available for hierarchy extraction",
        }

    intent_continuity = _execplan_intent_continuity(plan_path)
    required_continuation = _execplan_required_continuation(plan_path)
    execplan_parent_lane = _execplan_parent_lane(plan_path)
    active_milestone = resumable_contract.get("active_milestone", {})
    todo_item = active_contract.get("todo_item", {})

    parent_lane_ref = intent_continuity.get("parent lane", "").strip() or execplan_parent_lane.get("id", "")
    parent_lane = _resolve_parent_lane(parent_lane_ref=parent_lane_ref, roadmap_lanes=roadmap_lanes)
    if parent_lane.get("source") == "execplan":
        parent_lane.update(
            {
                "title": execplan_parent_lane.get("title", parent_lane.get("title", "")),
                "priority": execplan_parent_lane.get("priority", parent_lane.get("priority", "")),
                "issues": execplan_parent_lane.get("issues", parent_lane.get("issues", "")),
            }
        )
    continuation_surface = str(follow_through_contract.get("continuation_surface", "")).strip()
    required_owner_surface = required_continuation.get("owner surface", "").strip()
    required_follow_on = required_continuation.get("required follow-on for the larger intended outcome", "").strip()
    owner_surface = required_owner_surface or continuation_surface or planning_record.get("continuation_owner", "")
    minimal_refs = _dedupe(
        [
            *follow_through_contract.get("minimal_refs", []),
            *([".agentic-workspace/planning/state.toml"] if parent_lane.get("id") or roadmap_lanes else []),
            *(reference.get("target", "") for reference in parent_lane.get("references", []) if isinstance(reference, dict)),
        ]
    )
    return {
        "status": "present",
        "current_layer": "execution",
        "parent_lane": parent_lane,
        "active_chunk": {
            "todo_id": str(todo_item.get("id", "")).strip() or str(active_milestone.get("id", "")).strip(),
            "todo_surface": str(todo_item.get("surface", "")).strip(),
            "execplan": plan_path.relative_to(target_root).as_posix(),
            "milestone_id": str(active_milestone.get("id", "")).strip(),
            "milestone_status": str(active_milestone.get("status", "")).strip(),
            "milestone_scope": str(active_milestone.get("scope", "")).strip(),
            "next_action": str(resumable_contract.get("current_next_action", "")).strip(),
        },
        "near_term_queue": summary_todo_queue(target_root=target_root),
        "next_likely_chunk": str(follow_through_contract.get("next_likely_slice", "")).strip(),
        "proof_state": {
            "proof_achieved_now": str(follow_through_contract.get("proof_achieved_now", "")).strip(),
            "validation_still_needed": str(follow_through_contract.get("validation_still_needed", "")).strip(),
            "proof_expectations": list(resumable_contract.get("proof_expectations", [])),
        },
        "context_shift": {
            "live_working_set": str(context_budget_contract.get("live_working_set", "")).strip(),
            "externalize_before_shift": str(context_budget_contract.get("externalize_before_shift", "")).strip(),
            "pre_work_config_pull": str(context_budget_contract.get("pre_work_config_pull", "")).strip(),
            "tiny_resumability_note": str(context_budget_contract.get("tiny_resumability_note", "")).strip(),
            "triggers": str(context_budget_contract.get("context_shift_triggers", "")).strip(),
        },
        "required_continuation": {
            "larger_intended_outcome": str(follow_through_contract.get("larger_intended_outcome", "")).strip(),
            "slice_completes_larger_outcome": intent_continuity.get("this slice completes the larger intended outcome", "").strip(),
            "continuation_surface": continuation_surface,
            "required_follow_on": required_follow_on,
            "owner_surface": required_owner_surface,
            "activation_trigger": required_continuation.get("activation trigger", "").strip(),
        },
        "closure_check": _execplan_closure_check(plan_path),
        "routing": {
            "current_owner": str(planning_record.get("continuation_owner", "")).strip(),
            "follow_on_owner": str(owner_surface).strip(),
            "review_queue": ".agentic-workspace/planning/reviews/",
        },
        "minimal_refs": minimal_refs,
    }


def _ready_worker_prompt_from_handoff(
    *,
    planning_record: dict[str, Any],
    read_first: list[Any],
    owned_write_scope: list[Any],
    proof_expectations: list[Any],
    return_with: dict[str, Any],
    worker_contract: dict[str, Any],
) -> dict[str, Any]:
    task = dict(planning_record.get("task", {}))
    plan_path = str(task.get("surface") or task.get("path") or planning_record.get("surface") or "").strip()
    if not plan_path:
        return {
            "kind": "planning-ready-worker-prompt/v1",
            "status": "unavailable",
            "reason": "active planning record has no explicit plan surface",
        }

    requested_outcome = str(planning_record.get("requested_outcome", "")).strip()
    next_action = str(planning_record.get("next_action", "")).strip()
    completion_criteria = [str(item).strip() for item in planning_record.get("completion_criteria", []) if str(item).strip()]
    return_fields = {
        "execution_run": list(return_with.get("execution_run_fields", [])),
        "finished_run_review": list(return_with.get("finished_run_review_fields", [])),
        "delegation_outcome_feedback": list(return_with.get("delegation_outcome_feedback_fields", [])),
        "prose_sections": list(
            return_with.get("prose_templates", {}).get("handoff_or_closeout", {}).get("sections", [])
            if isinstance(return_with.get("prose_templates", {}), dict)
            else []
        ),
    }
    return_template_lines = [
        "Return using this template:",
        "- changed files / changed surfaces:",
        "- tests or proof run:",
        "- completion status:",
        "- blockers:",
        "- residue or follow-up:",
        "- delegation outcome feedback:",
    ]
    prompt_lines = [
        f"Implement the active plan in `{plan_path}`.",
        "Use that plan file as the source of scope, constraints, proof expectations, stop conditions, and return contract.",
    ]
    if requested_outcome:
        prompt_lines.append(f"Requested outcome: {requested_outcome}")
    if next_action:
        prompt_lines.append(f"Next action: {next_action}")
    if read_first:
        prompt_lines.append("Read first: " + ", ".join(f"`{item}`" for item in read_first))
    if owned_write_scope:
        prompt_lines.append("Owned write scope: " + ", ".join(f"`{item}`" for item in owned_write_scope))
    if proof_expectations:
        prompt_lines.append("Proof expectations: " + "; ".join(str(item) for item in proof_expectations))
    if completion_criteria:
        prompt_lines.append("Completion criteria: " + "; ".join(completion_criteria))
    stop_when = [str(item).strip() for item in worker_contract.get("stop_when", []) if str(item).strip()]
    if stop_when:
        prompt_lines.append("Stop and report back if: " + "; ".join(stop_when))
    prompt_lines.extend(return_template_lines)
    return {
        "kind": "planning-ready-worker-prompt/v1",
        "status": "present",
        "source": "planning-handoff-contract",
        "plan_path": plan_path,
        "copy_paste": "\n".join(prompt_lines),
        "return_template": {
            "summary": return_template_lines,
            "fields": return_fields,
        },
        "constraints": [
            "Do not broaden beyond the plan's owned write scope.",
            "Do not reshape the roadmap, parent lane, or issue closure unless the plan explicitly assigns that ownership.",
            "Stop instead of guessing when proof, scope, or ownership needs to change.",
        ],
        "worker_contract": worker_contract,
    }


def _active_handoff_contract(
    *,
    planning_record: dict[str, Any],
    hierarchy_contract: dict[str, Any],
    context_budget_contract: dict[str, Any],
    intent_interpretation_contract: dict[str, Any],
) -> dict[str, Any]:
    if planning_record.get("status") != "present":
        return {
            "status": "unavailable",
            "reason": planning_record.get("reason", "requires a present planning record"),
        }

    parent_lane = {}
    if hierarchy_contract.get("status") == "present":
        parent_lane = dict(hierarchy_contract.get("parent_lane", {}))

    read_first = list(planning_record.get("minimal_refs", []))
    owned_write_scope = list(planning_record.get("touched_scope", []))
    proof_expectations = list(planning_record.get("proof_expectations", []))
    return_with = {
        "prose_templates": _default_prose_templates(),
        "execution_run_fields": [
            "run status",
            "executor",
            "handoff source",
            "what happened",
            "scope touched",
            "changed surfaces",
            "validations run",
            "result for continuation",
            "next step",
        ],
        "execution_summary_fields": [
            "outcome delivered",
            "validation confirmed",
            "follow-on routed to",
            "post-work posterity capture",
            "knowledge promoted (memory/docs/config)",
            "resume from",
        ],
        "finished_run_review_fields": [
            "review status",
            "scope respected",
            "proof status",
            "intent served",
            "config compliance",
            "misinterpretation risk",
            "follow-on decision",
        ],
        "delegation_outcome_feedback_fields": [
            "route chosen",
            "route skipped reason",
            "expected savings",
            "actual friction",
            "proof result",
            "quality concern",
            "decomposition adjustment",
        ],
    }
    worker_contract = {
        "allowed_execution_methods": [
            "internal delegation",
            "read-only exploration",
            "external cli or api",
            "single-agent fallback",
        ],
        "worker_owns_by_default": [
            "read-only exploration for one explicit question when assigned",
            "bounded implementation inside the owned write scope",
            "narrow validation named by the handoff",
            "checked-in updates inside owned surfaces when explicitly assigned",
            "cleanup and commit only when explicitly assigned and still bounded",
        ],
        "worker_must_not_own_by_default": [
            "roadmap routing",
            "issue closure",
            "lane reshaping",
            "repo-wide policy changes",
        ],
        "stop_when": [
            str(planning_record.get("stop_conditions", {}).get("stop when", "")).strip(),
            str(planning_record.get("stop_conditions", {}).get("escalate when boundary reached", "")).strip(),
            str(planning_record.get("stop_conditions", {}).get("escalate on scope drift", "")).strip(),
            str(planning_record.get("stop_conditions", {}).get("escalate on proof failure", "")).strip(),
            str(planning_record.get("escalate_when", "")).strip(),
            "the task needs broad rereads beyond the explicit read-first refs and owned write scope",
            "the chosen delegation method cannot preserve the checked-in handoff contract",
        ],
    }

    return {
        "status": "present",
        "task": dict(planning_record.get("task", {})),
        "parent_lane": parent_lane,
        "requested_outcome": str(planning_record.get("requested_outcome", "")).strip(),
        "hard_constraints": str(planning_record.get("hard_constraints", "")).strip(),
        "agent_may_decide": str(planning_record.get("agent_may_decide", "")).strip(),
        "capability_posture": dict(planning_record.get("capability_posture", {})),
        "execplan_profile": dict(planning_record.get("execplan_profile", {})),
        "canonical_core": dict(planning_record.get("canonical_core", {})),
        "role_metadata": dict(planning_record.get("role_metadata", {})),
        "next_role_needed": str(planning_record.get("next_role_needed", "")).strip(),
        "references": list(planning_record.get("references", [])),
        "review_residue": list(planning_record.get("review_residue", [])),
        "post_decomposition_delegation": dict(planning_record.get("post_decomposition_delegation", {})),
        "delegation_outcome_feedback": dict(planning_record.get("delegation_outcome_feedback", {})),
        "next_action": str(planning_record.get("next_action", "")).strip(),
        "completion_criteria": list(planning_record.get("completion_criteria", [])),
        "read_first": read_first,
        "owned_write_scope": owned_write_scope,
        "proof_expectations": proof_expectations,
        "proof_report": dict(planning_record.get("proof_report", {})),
        "intent_satisfaction": dict(planning_record.get("intent_satisfaction", {})),
        "system_intent_alignment": dict(planning_record.get("system_intent_alignment", {})),
        "adaptive_assurance": dict(planning_record.get("adaptive_assurance", {})),
        "traceability_refs": dict(planning_record.get("traceability_refs", {})),
        "control_gates": list(planning_record.get("control_gates", [])),
        "implementation_blockers": list(planning_record.get("implementation_blockers", [])),
        "risk_registry_refs": list(planning_record.get("risk_registry_refs", [])),
        "invariant_refs": list(planning_record.get("invariant_refs", [])),
        "test_data_policy": dict(planning_record.get("test_data_policy", {})),
        "layer_scaffold": dict(planning_record.get("layer_scaffold", {})),
        "architecture_decision_promotion": dict(planning_record.get("architecture_decision_promotion", {})),
        "threat_failure_aids": list(planning_record.get("threat_failure_aids", [])),
        "intent_interpretation": dict(intent_interpretation_contract if intent_interpretation_contract.get("status") == "present" else {}),
        "pre_work_config_pull": str(context_budget_contract.get("pre_work_config_pull", "")).strip(),
        "pre_work_memory_pull": str(context_budget_contract.get("pre_work_memory_pull", "")).strip(),
        "execution_bounds": dict(planning_record.get("execution_bounds", {})),
        "stop_conditions": dict(planning_record.get("stop_conditions", {})),
        "tool_verification": dict(planning_record.get("tool_verification", {})),
        "continuation_owner": str(planning_record.get("continuation_owner", "")).strip(),
        "context_budget": dict(context_budget_contract if context_budget_contract.get("status") == "present" else {}),
        "return_with": return_with,
        "worker_contract": worker_contract,
        "ready_worker_prompt": _ready_worker_prompt_from_handoff(
            planning_record=planning_record,
            read_first=read_first,
            owned_write_scope=owned_write_scope,
            proof_expectations=proof_expectations,
            return_with=return_with,
            worker_contract=worker_contract,
        ),
    }


def _system_intent_contract_payload() -> dict[str, Any]:
    return {
        "status": "present",
        "canonical_doc": ".agentic-workspace/docs/system-intent-contract.md",
        "rule": (
            "Preserve the larger user or product outcome separately from the bounded slice so later archive, review, and continuation decisions stay honest."
        ),
        "authority_ladder": [
            {
                "layer": "confirmed request or live issue cluster",
                "owns": "the higher-level outcome the repo is actually trying to satisfy",
            },
            {
                "layer": "active execplan delegated judgment and intent continuity",
                "owns": "the bounded slice, hard constraints, and the mapping back to the larger intended outcome",
            },
            {
                "layer": "closure check and required continuation",
                "owns": "whether the slice can archive, whether the larger intent is still open, and where follow-through now lives",
            },
        ],
        "reinterpretation_boundary": {
            "allowed": [
                "tighten means, decomposition, and validation",
                "narrow a first slice when the larger requested outcome remains explicit",
                "route required continuation into one checked-in owner",
            ],
            "must_not": [
                "treat a bounded slice as if it closed the larger intent without explicit evidence",
                "leave required continuation only in drift prose or chat",
                "replace the confirmed outcome with a cheaper substitute silently",
            ],
        },
        "recoverability": {
            "ask_first": [
                "agentic-workspace defaults --section system_intent --format json",
                "agentic-workspace summary --format json",
                "agentic-planning report --format json",
            ],
            "must_answer": [
                "what larger outcome this slice serves",
                "whether the larger outcome is actually closed",
                "where required continuation lives now",
                "what evidence justified the closure decision",
            ],
        },
        "checked_in_execplan_rule": (
            "Keep a checked-in execplan whenever later proof, intent validation, or required continuation would be expensive or ambiguous to reconstruct from chat alone."
        ),
    }


def summary_todo_queue(*, target_root: Path) -> list[dict[str, str]]:
    state = _read_state_from_toml(target_root)
    if state:
        return [
            {
                "id": str(item.get("id", "")).strip(),
                "surface": str(item.get("surface") or item.get("path") or "").strip(),
                "status": str(item.get("status", "")).strip(),
                "why_now": str(item.get("why_now", "")).strip(),
            }
            for item in _state_queued_items(state)
            if str(item.get("status", "")).strip().lower() not in {"completed", "done", "closed"}
        ]
    todo_lines, todo_items = _read_todo_items(target_root / ".agentic-workspace/planning/state.toml")
    del todo_lines
    queue: list[dict[str, str]] = []
    for item in todo_items:
        status = item.fields.get("status", "").strip()
        status_lower = status.lower()
        if not status_lower or status_lower in {"completed", "done", "closed"}:
            continue
        if "in-progress" in status_lower or "active" in status_lower or "ongoing" in status_lower:
            continue
        queue.append(
            {
                "id": item.fields.get("id", "").strip(),
                "surface": item.fields.get("surface", "").strip(),
                "status": status,
                "why_now": item.fields.get("why now", "").strip(),
            }
        )
    return queue


def _resolve_parent_lane(*, parent_lane_ref: str, roadmap_lanes: list[dict[str, Any]]) -> dict[str, Any]:
    if parent_lane_ref:
        for lane in roadmap_lanes:
            if parent_lane_ref == lane.get("id", "") or parent_lane_ref == lane.get("title", ""):
                return {
                    "id": str(lane.get("id", "")).strip(),
                    "title": str(lane.get("title", "")).strip(),
                    "priority": str(lane.get("priority", "")).strip(),
                    "issues": ", ".join(lane.get("issues", [])),
                    "references": list(lane.get("references", [])),
                    "source": "roadmap",
                }
        return {
            "id": parent_lane_ref,
            "title": "",
            "priority": "",
            "issues": "",
            "references": [],
            "source": "execplan",
        }
    return {
        "id": "",
        "title": "",
        "priority": "",
        "issues": "",
        "references": [],
        "source": "unspecified",
    }


def _execplan_parent_lane(path: Path) -> dict[str, str]:
    record = _record_section_dict(_load_execplan_record(path), "parent_lane")
    if not record:
        return {}
    return {
        "id": record.get("id", "").strip(),
        "title": record.get("title", "").strip(),
        "priority": record.get("priority", "").strip(),
        "issues": record.get("issues", "").strip(),
    }


def _contract_projection(contract: dict[str, Any], *, view_name: str) -> dict[str, Any]:
    if not contract:
        return {}
    projection = dict(contract)
    projection.setdefault("view_role", "projection")
    projection.setdefault("view", view_name)
    projection.setdefault("view_of", "planning_record")
    return projection


def _promote_decomposition_lane_to_execplan(
    item_id: str,
    *,
    target_root: Path,
    plan_slug: str | None,
    dry_run: bool,
) -> InstallResult | None:
    decomposition_root = target_root / ".agentic-workspace" / "planning" / "decompositions"
    if not decomposition_root.exists():
        return None
    matched_path: Path | None = None
    matched_record: dict[str, Any] | None = None
    matched_lane: dict[str, Any] | None = None
    matched_index = -1
    for path in sorted(decomposition_root.glob("*.decomposition.json")):
        if path.name == "TEMPLATE.decomposition.json":
            continue
        try:
            record = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(record, dict) or record.get("kind") != "planning-decomposition/v1":
            continue
        decomposition_record = cast(dict[str, Any], record)
        lanes = decomposition_record.get("candidate_lanes", [])
        if not isinstance(lanes, list):
            continue
        for index, lane in enumerate(lanes):
            if not isinstance(lane, dict):
                continue
            lane_record = cast(dict[str, Any], lane)
            if str(lane_record.get("id", "")).strip() == item_id:
                matched_path = path
                matched_record = decomposition_record
                matched_lane = lane_record
                matched_index = index
                break
        if matched_lane is not None:
            break
    if matched_path is None or matched_record is None or matched_lane is None:
        return None

    result = InstallResult(target_root=target_root, message=f"Promote decomposition lane '{item_id}' to execplan", dry_run=dry_run)
    state_path = target_root / PLANNING_STATE_PATH
    state = _read_state_from_toml(target_root) or {
        "kind": PLANNING_STATE_KIND,
        "schema_version": PLANNING_STATE_SCHEMA_VERSION,
        "work_items": [],
        "active": {"execplans": []},
        "todo": {"active_items": [], "queued_items": []},
        "roadmap": {"lanes": [], "candidates": []},
    }
    todo = state.get("todo") if isinstance(state.get("todo"), dict) else {}
    active_items = todo.get("active_items", []) if isinstance(todo, dict) else []
    if active_items:
        result.add(
            "manual review",
            state_path,
            "active planning item already exists; archive or switch active work before promoting a decomposition lane",
        )
        return result

    slug = _slugify(plan_slug or item_id)
    if not slug:
        result.add("manual review", matched_path, "decomposition lane id cannot be converted into an execplan slug")
        return result
    record_path = target_root / ".agentic-workspace" / "planning" / "execplans" / f"{slug}.plan.json"
    record_relative = record_path.relative_to(target_root).as_posix()
    if record_path.exists():
        result.add("manual review", record_path, "target canonical execplan record already exists")
        return result

    title = str(matched_lane.get("title") or _title_from_slug(slug)).strip()
    outcome = str(matched_lane.get("outcome") or matched_record.get("outcome") or "").strip()
    proof = str(matched_lane.get("proof") or "").strip()
    source_relative = matched_path.relative_to(target_root).as_posix()
    why_now = f"Promoted from {source_relative} lane {item_id}."
    source_fields = {
        "id": item_id,
        "title": title,
        "outcome": outcome,
        "proof": proof,
        "source decomposition": source_relative,
        "readiness": str(matched_lane.get("readiness", "")).strip(),
    }
    plan_record = _build_execplan_record_from_todo_item(
        title=title,
        item_id=item_id,
        status="active",
        why_now=why_now,
        next_action=outcome or "Fill in execution bounds, touched paths, and validation before implementation starts.",
        done_when=proof or outcome or f"{title} is implemented, validated, and closed out honestly.",
        source_fields=source_fields,
    )
    plan_record["references"] = [
        {
            "kind": "source",
            "target": source_relative,
            "label": f"decomposition lane {item_id}",
            "role": "intake",
            "locator": f"candidate_lanes[{matched_index}]",
        }
    ]
    plan_record["execution_run"]["handoff source"] = "agentic-planning promote-to-plan decomposition lane"
    plan_record["drift_log"] = [
        f"{date.today().isoformat()}: Scaffolded by agentic-planning promote-to-plan from decomposition lane {item_id}."
    ]

    updated_state = copy.deepcopy(state)
    updated_todo = updated_state.get("todo")
    if not isinstance(updated_todo, dict):
        updated_todo = {}
    updated_todo["active_items"] = [
        {
            "id": slug,
            "title": title,
            "maturity": "active",
            "status": "active",
            "surface": record_relative,
            "why_now": why_now,
            "owner_role": "implementation",
            "handoff_ready": True,
            "refs": [source_relative],
        }
    ]
    updated_todo.setdefault("queued_items", [])
    updated_state["todo"] = updated_todo

    updated_record = copy.deepcopy(matched_record)
    updated_lanes = list(updated_record.get("candidate_lanes", []))
    updated_lane = copy.deepcopy(matched_lane)
    updated_lane["readiness"] = "promoted"
    updated_lane["owner_surface"] = record_relative
    updated_lanes[matched_index] = updated_lane
    updated_record["candidate_lanes"] = updated_lanes

    if dry_run:
        result.add("would create", record_path, "scaffold canonical execplan record from decomposition lane")
        result.add("would update", state_path, f"register active planning item '{slug}'")
        result.add("would update", matched_path, f"mark decomposition lane '{item_id}' as promoted")
        _add_planning_mutation_proof_actions(result)
        return result

    _write_execplan_record(record_path=record_path, record=plan_record)
    _write_state_to_toml(target_root, updated_state)
    matched_path.write_text(json.dumps(updated_record, indent=2) + "\n", encoding="utf-8")
    result.add("created", record_path, "scaffolded canonical execplan record from decomposition lane")
    result.add("updated", state_path, f"registered active planning item '{slug}'")
    result.add("updated", matched_path, f"marked decomposition lane '{item_id}' as promoted")
    _stamp_result_planning_mutations(
        result,
        paths=[record_path, state_path, matched_path],
        command="agentic-planning promote-to-plan",
        reason=f"promote decomposition lane {item_id}",
    )
    _add_planning_mutation_proof_actions(result)
    return result


def promote_todo_item_to_execplan(
    item_id: str,
    *,
    target: str | Path | None = None,
    plan_slug: str | None = None,
    dry_run: bool = False,
) -> InstallResult:
    target_root = resolve_target_root(target)
    result = InstallResult(target_root=target_root, message=f"Promote TODO item '{item_id}' to execplan", dry_run=dry_run)
    todo_path = target_root / ".agentic-workspace/planning/state.toml"
    state = _read_state_from_toml(target_root)
    compact_item = _compact_todo_item_from_state(state, item_id)
    todo_lines, todo_items = ([], [])
    item = compact_item
    if item is None:
        todo_lines, todo_items = _read_todo_items(todo_path)
        item = next((candidate for candidate in todo_items if candidate.item_id == item_id), None)
    if item is None:
        decomposition_result = _promote_decomposition_lane_to_execplan(
            item_id,
            target_root=target_root,
            plan_slug=plan_slug,
            dry_run=dry_run,
        )
        if decomposition_result is not None:
            return decomposition_result
        result.add("manual review", todo_path, f"TODO item or decomposition lane '{item_id}' was not found")
        return result

    current_surface = item.fields.get("surface", "")
    existing_execplan_ref = _surface_execplan_reference(current_surface)
    if existing_execplan_ref:
        existing_execplan_path = target_root / existing_execplan_ref
        existing_execplan_record_path = _canonical_execplan_record_path(existing_execplan_path)
        if existing_execplan_path.exists() or existing_execplan_record_path.exists():
            result.add("manual review", todo_path, f"TODO item '{item_id}' already points at '{existing_execplan_ref}'")
            return result
        slug = _slugify(plan_slug or existing_execplan_record_path.name.removesuffix(".plan.json"))
        next_action = (
            item.fields.get("next action", "").strip()
            or item.fields.get("suggested first slice", "").strip()
            or item.fields.get("promotion signal", "").strip()
        )
        done_when = item.fields.get("done when", "").strip() or item.fields.get("outcome", "").strip()
        why_now = item.fields.get("why now", "").strip() or item.fields.get("reason", "").strip()
        status = _normalize_status(item.fields.get("status", "planned"))
        if status == "planned":
            status = "in-progress"
        plan_record = _build_execplan_record_from_todo_item(
            title=_title_from_slug(slug),
            item_id=item_id,
            status=status,
            why_now=why_now,
            next_action=next_action,
            done_when=done_when,
            source_fields=item.fields,
        )
        surface_relative = existing_execplan_record_path.relative_to(target_root)
        updated_fields = dict(item.fields)
        updated_fields["surface"] = surface_relative.as_posix()
        updated_fields.pop("next action", None)
        updated_fields.pop("done when", None)
        if compact_item is not None:
            new_state = _update_compact_todo_item_in_state(state, item_id, {"surface": surface_relative.as_posix()})
            if new_state is None:
                result.add("manual review", todo_path, f"TODO item '{item_id}' could not be updated in compact state")
                return result
        else:
            new_todo_lines = _rewrite_todo_item(todo_lines, item, updated_fields)
        if dry_run:
            result.add("would create", existing_execplan_record_path, "scaffold missing canonical execplan record from TODO path")
            result.add("would update", todo_path, f"confirm '{item_id}' points at {surface_relative.as_posix()}")
            return result
        _write_execplan_record(record_path=existing_execplan_record_path, record=plan_record)
        if compact_item is not None:
            _write_state_to_toml(target_root, new_state)
        else:
            todo_path.write_text("\n".join(new_todo_lines).rstrip() + "\n", encoding="utf-8")
        result.add("created", existing_execplan_record_path, "scaffolded missing canonical execplan record from TODO path")
        result.add("updated", todo_path, f"confirmed '{item_id}' points at {surface_relative.as_posix()}")
        _stamp_result_planning_mutations(
            result,
            paths=[existing_execplan_record_path, todo_path],
            command="agentic-planning promote-to-plan",
            reason=f"promote planning item {item_id}",
        )
        return result

    slug = _slugify(plan_slug or item_id)
    execplan_relative = Path(".agentic-workspace") / "planning" / "execplans" / f"{slug}.md"
    execplan_path = target_root / execplan_relative
    execplan_record_path = _canonical_execplan_record_path(execplan_path)
    execplan_record_relative = execplan_record_path.relative_to(target_root)
    if execplan_path.exists():
        result.add("manual review", execplan_path, "target execplan already exists")
        return result
    if execplan_record_path.exists():
        result.add("manual review", execplan_record_path, "target canonical execplan record already exists")
        return result

    next_action = (
        item.fields.get("next action", "").strip()
        or item.fields.get("suggested first slice", "").strip()
        or item.fields.get("promotion signal", "").strip()
    )
    done_when = item.fields.get("done when", "").strip() or item.fields.get("outcome", "").strip()
    why_now = item.fields.get("why now", "").strip() or item.fields.get("reason", "").strip()
    status = _normalize_status(item.fields.get("status", "planned"))
    if status == "planned":
        status = "in-progress"
    plan_record = _build_execplan_record_from_todo_item(
        title=_title_from_slug(slug),
        item_id=item_id,
        status=status,
        why_now=why_now,
        next_action=next_action,
        done_when=done_when,
        source_fields=item.fields,
    )

    updated_fields = dict(item.fields)
    surface_relative = execplan_record_relative if compact_item is not None else execplan_relative
    updated_fields["surface"] = surface_relative.as_posix()
    updated_fields.pop("next action", None)
    updated_fields.pop("done when", None)
    if compact_item is not None:
        new_state = _update_compact_todo_item_in_state(state, item_id, {"surface": surface_relative.as_posix()})
        if new_state is None:
            result.add("manual review", todo_path, f"TODO item '{item_id}' could not be updated in compact state")
            return result
    else:
        new_todo_lines = _rewrite_todo_item(todo_lines, item, updated_fields)

    if dry_run:
        result.add("would create", execplan_record_path, "scaffold canonical execplan record from TODO item")
        result.add("would update", todo_path, f"point '{item_id}' at {surface_relative.as_posix()} and remove direct-task fields")
        return result

    _write_execplan_record(record_path=execplan_record_path, record=plan_record)
    if compact_item is not None:
        _write_state_to_toml(target_root, new_state)
    else:
        todo_path.write_text("\n".join(new_todo_lines).rstrip() + "\n", encoding="utf-8")
    result.add("created", execplan_record_path, "scaffolded canonical execplan record from TODO item")
    result.add("updated", todo_path, f"pointed '{item_id}' at {surface_relative.as_posix()} and removed direct-task fields")
    _stamp_result_planning_mutations(
        result,
        paths=[execplan_record_path, todo_path],
        command="agentic-planning promote-to-plan",
        reason=f"promote planning item {item_id}",
    )
    return result


def create_execplan_scaffold(
    *,
    plan_id: str,
    title: str,
    source: str = "",
    target: str | Path | None = None,
    activate: bool = False,
    queue: bool = False,
    switch_active: bool = False,
    prep_only: bool = False,
    overwrite: bool = False,
    dry_run: bool = False,
) -> InstallResult:
    target_root = resolve_target_root(target)
    slug = _slugify(plan_id)
    result = InstallResult(target_root=target_root, message=f"Create execplan scaffold '{slug}'", dry_run=dry_run)
    if not slug:
        result.add("manual review", target_root / PLANNING_STATE_PATH, "--id must contain at least one alphanumeric character")
        return result
    if activate and queue:
        result.add("manual review", target_root / PLANNING_STATE_PATH, "choose only one of --activate or --queue")
        return result
    if switch_active and not activate:
        result.add("manual review", target_root / PLANNING_STATE_PATH, "--switch-active requires --activate")
        return result

    plan_title = title.strip() or _title_from_slug(slug)
    state_path = target_root / PLANNING_STATE_PATH
    record_path = target_root / ".agentic-workspace" / "planning" / "execplans" / f"{slug}.plan.json"
    record_relative = record_path.relative_to(target_root).as_posix()
    if record_path.exists() and not overwrite:
        result.add("manual review", record_path, "target canonical execplan record already exists; pass --overwrite to replace it")
        return result

    source_text = source.strip()
    plan_record = _build_execplan_record_from_todo_item(
        title=plan_title,
        item_id=slug,
        status="active" if activate else "planned",
        why_now=source_text or f"Create a bounded plan for {plan_title}.",
        next_action="Fill in execution bounds, touched paths, and validation before implementation starts.",
        done_when=f"{plan_title} is implemented, validated, and closed out honestly.",
    )
    plan_record["execution_run"]["handoff source"] = "agentic-planning new-plan"
    plan_record["drift_log"] = [f"{date.today().isoformat()}: Scaffolded by agentic-planning new-plan."]
    if source_text:
        plan_record["references"] = [{"kind": "source", "target": source_text, "label": source_text, "role": "intake", "locator": ""}]
    if prep_only:
        _apply_prep_only_execplan_defaults(plan_record)

    try:
        findings = _json_schema_findings(payload=plan_record, schema_path=EXECPLAN_RECORD_SCHEMA_PATH)
    except Exception as exc:  # pragma: no cover - defensive guard around schema loading
        result.add("manual review", record_path, f"could not validate scaffold against schema: {exc}")
        return result
    if findings:
        result.add("manual review", record_path, f"scaffold did not validate against planning-execplan.schema.json: {'; '.join(findings)}")
        return result

    state = _read_state_from_toml(target_root) or {
        "kind": PLANNING_STATE_KIND,
        "schema_version": PLANNING_STATE_SCHEMA_VERSION,
        "work_items": [],
        "active": {"execplans": []},
        "todo": {"active_items": [], "queued_items": []},
        "roadmap": {"lanes": [], "candidates": []},
    }
    updated_state = copy.deepcopy(state)
    if activate or queue:
        if _compact_todo_item_from_state(updated_state, slug) is not None:
            result.add("manual review", state_path, f"planning item '{slug}' already exists in state.toml")
            return result
        todo = updated_state.get("todo")
        if not isinstance(todo, dict):
            todo = {}
        bucket = "active_items" if activate else "queued_items"
        items = todo.get(bucket, [])
        if not isinstance(items, list):
            items = []
        queued_items = todo.get("queued_items", [])
        if not isinstance(queued_items, list):
            queued_items = []
        if activate and items and not switch_active:
            result.add(
                "manual review",
                state_path,
                "active planning item already exists; rerun with --switch-active to demote existing active items into todo.queued_items",
            )
            return result
        if activate and switch_active and items:
            switched_items: list[Any] = []
            for item in items:
                if not isinstance(item, dict):
                    switched_items.append(item)
                    continue
                switched_item = copy.deepcopy(item)
                switched_item["maturity"] = "ready"
                switched_item["status"] = "queued"
                switched_item["switched_from_active_by"] = slug
                switched_item["switch_reason"] = source_text or f"Switched active lane to {plan_title}."
                switched_items.append(switched_item)
            queued_items = [*switched_items, *queued_items]
            items = []
        state_item: dict[str, Any] = {
            "id": slug,
            "title": plan_title,
            "maturity": "active" if activate else "ready",
            "status": "active" if activate else "next",
            "surface": record_relative,
            "why_now": source_text or "Created by new-plan scaffold.",
            "owner_role": "implementation",
            "handoff_ready": True,
        }
        if source_text:
            state_item["refs"] = [source_text]
        items.append(state_item)
        if bucket == "queued_items":
            queued_items = items
        todo[bucket] = items
        todo["queued_items"] = queued_items
        todo.setdefault("active_items", [])
        todo.setdefault("queued_items", [])
        updated_state["todo"] = todo

    if dry_run:
        result.add("would create" if not record_path.exists() else "would update", record_path, "schema-valid execplan scaffold")
        state_todo = state.get("todo")
        state_active_items = state_todo.get("active_items", []) if isinstance(state_todo, dict) else []
        if activate and switch_active and isinstance(state_active_items, list):
            active_count = len(state_active_items)
            if active_count:
                result.add("would update", state_path, f"demote {active_count} active planning item(s) into todo.queued_items")
        if activate or queue:
            result.add("would update", state_path, f"register '{slug}' in todo.{'active_items' if activate else 'queued_items'}")
        result.add("next", target_root / PLANNING_STATE_PATH, "run `agentic-workspace summary --target . --verbose --format json`")
        result.add("next", record_path, _new_plan_tightening_checklist(prep_only=prep_only))
        return result

    _write_execplan_record(record_path=record_path, record=plan_record)
    detail = "schema-valid prep-only execplan scaffold" if prep_only else "schema-valid execplan scaffold"
    result.add("created" if not overwrite else "updated", record_path, detail)
    provenance_paths = [record_path]
    if activate or queue:
        _write_state_to_toml(target_root, updated_state)
        result.add("updated", state_path, f"registered '{slug}' in todo.{'active_items' if activate else 'queued_items'}")
        provenance_paths.append(state_path)
    _stamp_result_planning_mutations(
        result,
        paths=provenance_paths,
        command="agentic-planning new-plan",
        reason=f"create execplan scaffold {slug}",
    )
    result.add("next", state_path, "run `agentic-workspace summary --target . --verbose --format json`")
    result.add("next", record_path, _new_plan_tightening_checklist(prep_only=prep_only))
    if prep_only:
        result.add(
            "next",
            state_path,
            "after summary verification, stop; do not create README, package, source, public, schema, database, or app scaffold files",
        )
    return result


def _new_plan_tightening_checklist(*, prep_only: bool) -> str:
    if prep_only:
        return (
            "prep-only route: run summary, then stop without manual JSON tightening, README, PLANNING_STATE, "
            "product files, or handoff docs unless summary reports a blocking Planning problem"
        )
    return (
        "before implementation, tighten scaffold fields: goal, non_goals, intent_continuity, execution_bounds, "
        "touched_paths, validation_commands, completion_criteria, and adaptive_assurance when risk or scope requires it"
    )


def _resolve_repo_relative_file(target_root: Path, value: str) -> Path | None:
    raw = value.strip()
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = target_root / path
    try:
        resolved = path.resolve()
        target_resolved = target_root.resolve()
    except OSError:
        return None
    try:
        resolved.relative_to(target_resolved)
    except ValueError:
        return None
    return resolved


def _title_from_artifact(path: Path) -> str:
    if path.suffix.lower() == ".json":
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            payload = {}
        if isinstance(payload, dict):
            for key in ("title", "name", "id"):
                value = str(payload.get(key, "")).strip()
                if value:
                    return value
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                return stripped.lstrip("#").strip()
    except (OSError, UnicodeDecodeError):
        pass
    return _title_from_slug(path.stem)


def _canonical_decomposition_path(target_root: Path, artifact_path: Path, artifact_id: str) -> Path:
    slug = _slugify(artifact_id or artifact_path.stem.removesuffix(".decomposition"))
    return target_root / PLANNING_MANAGED_ROOT / "decompositions" / f"{slug}.decomposition.json"


def _looks_like_decomposition_record(path: Path) -> bool:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        payload = {}
    if isinstance(payload, dict):
        if payload.get("kind") == "planning-decomposition/v1":
            return True
        if {"candidate_lanes", "larger_intended_outcome", "promotion_rule"}.intersection(payload):
            return True
    lowered_name = path.name.lower()
    return "decomposition" in lowered_name and "planning" in lowered_name


def intake_planning_artifact(
    *,
    artifact: str,
    target: str | Path | None = None,
    route: str = "auto",
    artifact_id: str = "",
    title: str = "",
    activate: bool = False,
    queue: bool = False,
    switch_active: bool = False,
    remove_source: bool = False,
    dry_run: bool = False,
) -> InstallResult:
    target_root = resolve_target_root(target)
    result = InstallResult(target_root=target_root, message="Intake freehand planning artifact", dry_run=dry_run)
    artifact_path = _resolve_repo_relative_file(target_root, artifact)
    if artifact_path is None:
        result.add("manual review", target_root / PLANNING_STATE_PATH, "--artifact must name a file inside the target repository")
        return result
    if not artifact_path.exists() or not artifact_path.is_file():
        result.add("manual review", artifact_path, "artifact was not found or is not a file")
        return result

    normalized_route = route.strip().lower() or "auto"
    if normalized_route not in {"auto", "execplan", "decomposition"}:
        result.add("manual review", artifact_path, "--route must be one of auto, execplan, or decomposition")
        return result
    if normalized_route == "auto":
        normalized_route = "decomposition" if _looks_like_decomposition_record(artifact_path) else "execplan"

    source_ref = artifact_path.relative_to(target_root).as_posix()
    if normalized_route == "execplan":
        plan_id = _slugify(artifact_id or artifact_path.stem)
        plan_title = title.strip() or _title_from_artifact(artifact_path)
        routed = create_execplan_scaffold(
            plan_id=plan_id,
            title=plan_title,
            source=source_ref,
            target=target_root,
            activate=activate,
            queue=queue,
            switch_active=switch_active,
            dry_run=dry_run,
        )
        result.actions.extend(routed.actions)
        result.warnings.extend(routed.warnings)
        blocked = bool(routed.warnings) or any(action.kind == "manual review" for action in routed.actions)
        if blocked:
            result.add("next safe action", artifact_path, "resolve the execplan intake blocker, then rerun planning intake-artifact")
            return result
        if remove_source:
            if dry_run:
                result.add("would remove", artifact_path, "remove source artifact after canonical execplan intake")
            else:
                artifact_path.unlink()
                result.add("removed", artifact_path, "removed source artifact after canonical execplan intake")
        result.add("next safe action", target_root / PLANNING_STATE_PATH, "agentic-planning summary --target . --format json")
        return result

    try:
        payload = json.loads(artifact_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        result.add("manual review", artifact_path, f"decomposition intake requires valid JSON: {exc}")
        return result
    if not isinstance(payload, dict) or payload.get("kind") != "planning-decomposition/v1":
        result.add(
            "manual review",
            artifact_path,
            "decomposition intake requires a schema-ready planning-decomposition/v1 record; use --route execplan for looser artifacts",
        )
        return result
    destination = _canonical_decomposition_path(target_root, artifact_path, artifact_id or str(payload.get("id", "")))
    if destination.exists():
        result.add("manual review", destination, "canonical decomposition target already exists")
        return result
    findings = _json_schema_findings(payload=payload, schema_path=DECOMPOSITION_RECORD_SCHEMA_PATH)
    if findings:
        result.add("manual review", artifact_path, f"decomposition does not validate: {'; '.join(findings)}")
        return result
    if dry_run:
        result.add("would create", destination, "canonical planning-decomposition/v1 record")
        if remove_source and destination != artifact_path:
            result.add("would remove", artifact_path, "remove source artifact after canonical decomposition intake")
        return result
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    result.add("created", destination, "canonical planning-decomposition/v1 record")
    if remove_source and destination != artifact_path:
        artifact_path.unlink()
        result.add("removed", artifact_path, "removed source artifact after canonical decomposition intake")
    _stamp_result_planning_mutations(
        result,
        paths=[destination],
        command="agentic-planning intake-artifact",
        reason=f"intake planning artifact {source_ref}",
    )
    result.add("next safe action", target_root / PLANNING_STATE_PATH, "agentic-planning summary --target . --format json")
    return result


def _active_execplan_record_path_from_state(target_root: Path) -> Path | None:
    state = _read_state_from_toml(target_root)
    todo = state.get("todo") if isinstance(state, dict) else None
    active_items = todo.get("active_items", []) if isinstance(todo, dict) else []
    if isinstance(active_items, list) and active_items:
        first = active_items[0]
        if isinstance(first, dict):
            surface = _active_execplan_reference(first)
            if surface:
                return _resolve_execplan_path(target_root, surface)
    execplan_dir = target_root / ".agentic-workspace" / "planning" / "execplans"
    active_plans = [path for path in _live_execplan_paths(execplan_dir) if _execplan_status(path) not in {"completed", "done", "closed"}]
    if len(active_plans) == 1:
        return active_plans[0]
    return None


def record_delegation_decision(
    *,
    target: str | Path | None = None,
    plan: str | None = None,
    route: str,
    skipped_reason: str = "",
    expected_savings: str = "",
    actual_friction: str = "",
    proof_result: str = "",
    quality_concern: str = "",
    decomposition_adjustment: str = "",
    dry_run: bool = False,
) -> InstallResult:
    target_root = resolve_target_root(target)
    result = InstallResult(target_root=target_root, message="Record planning delegation decision", dry_run=dry_run)
    plan_path = _resolve_execplan_path(target_root, plan) if plan else _active_execplan_record_path_from_state(target_root)
    if plan_path is None or not plan_path.exists():
        result.add("manual review", target_root / PLANNING_STATE_PATH, "no active execplan resolved; pass --plan explicitly")
        return result
    record = _load_execplan_record(plan_path)
    if record is None:
        result.add("manual review", plan_path, "delegation decisions require a canonical .plan.json execplan")
        return result
    route_value = route.strip()
    if not route_value:
        result.add("manual review", plan_path, "--route is required")
        return result
    if route_value == "keep-local" and not skipped_reason.strip():
        result.add("manual review", plan_path, "--skipped-reason is required when --route keep-local")
        return result

    updated = copy.deepcopy(record)
    existing_post = updated.get("post_decomposition_delegation")
    if not isinstance(existing_post, dict):
        existing_post = {}
    existing_post.update(
        {
            "status": "recorded",
            "route chosen": route_value,
            "route skipped reason": skipped_reason.strip(),
            "decision command": "agentic-planning delegation-decision",
            "recorded at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        }
    )
    updated["post_decomposition_delegation"] = existing_post
    feedback = updated.get("delegation_outcome_feedback")
    if not isinstance(feedback, dict):
        feedback = {}
    feedback.update(
        {
            "route chosen": route_value,
            "route skipped reason": skipped_reason.strip() or "not skipped",
            "expected savings": expected_savings.strip() or "unknown",
            "actual friction": actual_friction.strip() or "pending",
            "proof result": proof_result.strip() or "pending",
            "quality concern": quality_concern.strip() or "none recorded",
            "decomposition adjustment": decomposition_adjustment.strip() or "none",
        }
    )
    updated["delegation_outcome_feedback"] = feedback
    drift_log = updated.get("drift_log")
    if not isinstance(drift_log, list):
        drift_log = []
    drift_log.append(f"{date.today().isoformat()}: Recorded delegation decision route={route_value}.")
    updated["drift_log"] = drift_log

    if dry_run:
        result.add("would update", plan_path, f"record delegation decision route={route_value}")
        return result

    _write_execplan_record(record_path=plan_path, record=updated)
    result.add("updated", plan_path, f"recorded delegation decision route={route_value}")
    _stamp_result_planning_mutations(
        result,
        paths=[plan_path],
        command="agentic-planning delegation-decision",
        reason=f"record delegation decision route={route_value}",
    )
    return result


def record_planning_recovery(
    *,
    target: str | Path | None = None,
    paths: list[str] | None = None,
    reason: str,
    dry_run: bool = False,
) -> InstallResult:
    target_root = resolve_target_root(target)
    result = InstallResult(target_root=target_root, message="Record explicit planning recovery", dry_run=dry_run)
    reason_text = reason.strip()
    if not reason_text:
        result.add("manual review", target_root / PLANNING_MUTATION_PROVENANCE_PATH, "--reason is required")
        return result
    raw_paths = paths or [PLANNING_STATE_PATH.as_posix()]
    selected: list[Path] = []
    for raw_path in raw_paths:
        candidate = Path(raw_path)
        full_path = candidate if candidate.is_absolute() else target_root / candidate
        try:
            relative = full_path.resolve().relative_to(target_root.resolve())
        except ValueError:
            result.add("manual review", full_path, "recovery path must stay inside the target repository")
            continue
        if not relative.as_posix().startswith(".agentic-workspace/planning/"):
            result.add("manual review", full_path, "recovery provenance is scoped to managed planning surfaces")
            continue
        if relative.as_posix() == PLANNING_MUTATION_PROVENANCE_PATH.as_posix():
            result.add("manual review", full_path, "recovery provenance cannot bless the provenance ledger itself")
            continue
        if not full_path.exists() or not full_path.is_file():
            result.add("manual review", full_path, "recovery path does not exist")
            continue
        selected.append(full_path)
    if any(action.kind == "manual review" for action in result.actions):
        return result
    if dry_run:
        for path in selected:
            result.add("would update", path, "record emergency recovery provenance")
        return result
    provenance_path = _record_planning_mutation_provenance(
        target_root=target_root,
        paths=selected,
        command="agentic-planning record-recovery",
        reason=reason_text,
        mode="manual-recovery",
    )
    for path in selected:
        result.add("recovery recorded", path, reason_text)
    result.add("updated", provenance_path, "recorded emergency recovery provenance")
    return result


def _apply_prep_only_execplan_defaults(plan_record: dict[str, Any]) -> None:
    # Prep-only records are stop/proof markers, not implementation contracts.
    # Drop closeout-only prompts that have repeatedly tempted agents into
    # polishing generated JSON during a handoff-only pass.
    plan_record.pop("task_intent_promotion", None)
    next_action = "Run agentic-workspace summary --target . --verbose --format json, confirm the planning state is clean, then stop without product scaffolding."
    done_when = "Canonical Planning state exists, summary verifies it, and no product source, package, dependency, README, handoff, or app scaffold files were created."
    plan_record["goal"] = [
        "Prepare durable checked-in Planning state for later continuation without implementing or scaffolding the product."
    ]
    plan_record["non_goals"] = [
        "Do not create README, PLANNING_STATE, HANDOFF, SLICES, package, dependency, source, public, database, schema, or app scaffold files.",
        "Do not start implementation; this slice ends after Planning state and summary verification.",
    ]
    plan_record["immediate_next_action"] = [next_action]
    plan_record["completion_criteria"] = [done_when]
    plan_record["validation_commands"] = ["agentic-workspace summary --target . --verbose --format json"]
    plan_record["touched_paths"] = [
        ".agentic-workspace/planning/state.toml",
        ".agentic-workspace/planning/execplans/",
        ".agentic-workspace/planning/decompositions/",
    ]
    canonical_core = plan_record.setdefault("canonical_core", {})
    canonical_core["next_action"] = next_action
    canonical_core["proof_expectations"] = list(plan_record["validation_commands"])
    canonical_core["touched_scope"] = list(plan_record["touched_paths"])
    canonical_core["completion_criteria"] = list(plan_record["completion_criteria"])
    execution = plan_record.setdefault("machine_readable_contract", {}).setdefault("execution", {})
    execution["next_step"] = next_action
    execution["proof"] = "Summary verification only; product validation belongs to later implementation slices."
    scope = plan_record.setdefault("machine_readable_contract", {}).setdefault("scope", {})
    scope["touched"] = list(plan_record["touched_paths"])
    scope["invariants"] = [
        "This is planning-only preparation.",
        "Do not create product or handoff files outside canonical Planning surfaces.",
    ]
    planning_mode = plan_record.setdefault("machine_readable_contract", {}).setdefault("planning_mode", {})
    planning_mode["prep_only"] = True
    planning_mode["halt_after_summary"] = True
    planning_mode["halt_instruction"] = (
        "HALT: prep-only mode active. Create Planning state, run agentic-workspace summary --target . --verbose --format json, "
        "then stop. Do not manually tighten or revalidate generated JSON unless summary reports a blocking Planning problem. "
        "Do not create product files, scaffolds, README, PLANNING_STATE, or handoff documentation."
    )
    planning_mode["minimal_success_criteria"] = [
        "prep-only execplan registered in Planning state",
        "agentic-workspace summary --target . --verbose --format json exits successfully",
        "only canonical Planning surfaces changed",
    ]
    planning_mode["manual_tightening_policy"] = "defer during prep-only handoff unless summary reports a blocking Planning problem"
    planning_mode["allowed_outputs"] = [
        ".agentic-workspace/planning/state.toml",
        ".agentic-workspace/planning/execplans/<id>.plan.json",
        ".agentic-workspace/planning/decompositions/<id>.decomposition.json",
    ]
    planning_mode["forbidden_outputs"] = [
        "README",
        "PLANNING_STATE",
        "HANDOFF",
        "SLICES",
        "package",
        "dependency",
        "src",
        "public",
        "database",
        "schema",
        "app scaffold",
    ]
    plan_record["control_gates"] = [
        {
            "id": "prep-only-halt",
            "owner_role": "implementation",
            "required_for": ["before any product or handoff file creation"],
            "status": "pending",
            "evidence": ["agentic-workspace summary --target . --verbose --format json"],
            "blocking": True,
            "next_action": planning_mode["halt_instruction"],
        }
    ]
    plan_record["execution_bounds"] = {
        "allowed paths": ".agentic-workspace/planning/state.toml, .agentic-workspace/planning/execplans/, and .agentic-workspace/planning/decompositions/ only.",
        "max changed files": "Planning records only; stop if implementation scaffolding seems necessary.",
        "required validation commands": "agentic-workspace summary --target . --verbose --format json",
        "ask-before-refactor threshold": "Any product, dependency, documentation, schema, database, source, public, or app scaffold file.",
        "stop before touching": "README, PLANNING_STATE, HANDOFF, SLICES, package files, dependency manifests, src/, public/, database files, schema files, or app code.",
        "manual JSON validation": "Do not run ad hoc JSON validation loops; use summary or package checks.",
    }
    plan_record["stop_conditions"] = {
        "stop when": "Summary verifies the canonical Planning state.",
        "escalate when boundary reached": "A useful next step would create product or handoff files outside canonical Planning surfaces.",
        "escalate on scope drift": "The work turns into implementation or product setup.",
        "escalate on proof failure": "Summary cannot verify clean Planning state.",
    }
    plan_record["execution_run"]["what happened"] = "prep-only scaffold created; implementation has not started"
    plan_record["execution_run"]["scope touched"] = "canonical Planning surfaces only"
    plan_record["execution_run"]["changed surfaces"] = "planning state and execplan scaffold"
    plan_record["execution_run"]["next step"] = next_action


def _render_inactive_execplan_residue(*, plan_path: Path, target_root: Path) -> str:
    title = _execplan_title(plan_path)
    intent_continuity = _execplan_intent_continuity(plan_path)
    required_continuation = _execplan_required_continuation(plan_path)
    delegated_judgment = _execplan_delegated_judgment(plan_path)
    intent_interpretation = _execplan_intent_interpretation(plan_path)
    execution_bounds = _execplan_execution_bounds(plan_path)
    stop_conditions = _execplan_stop_conditions(plan_path)
    context_budget = _execplan_context_budget(plan_path)
    execution_run = _execplan_execution_run(plan_path)
    finished_run_review = _execplan_finished_run_review(plan_path)
    proof_report = _execplan_proof_report(plan_path)
    intent_satisfaction = _execplan_intent_satisfaction(plan_path)
    system_intent_alignment = _execplan_system_intent_alignment(plan_path)
    closure_check = _execplan_closure_check(plan_path)
    durable_residue = _execplan_durable_residue(plan_path)
    execution_summary = _execplan_execution_summary(plan_path)
    relative = plan_path.relative_to(target_root).as_posix()
    lines = [
        f"# {title}",
        "",
        "Compact inactive-plan residue generated at archive time.",
        "Use git history for superseded active-step detail; keep only the closure, continuation, proof, and cheap-resume residue here.",
        "",
        "## Origin",
        "",
        f"- Archived from: {relative}",
        "",
        "## Intent Continuity",
        "",
    ]
    for key in (
        "larger intended outcome",
        "this slice completes the larger intended outcome",
        "continuation surface",
        "parent lane",
    ):
        if key in intent_continuity:
            lines.append(f"- {key.title()}: {intent_continuity[key]}")
    lines.extend(["", "## Required Continuation", ""])
    for key in (
        "required follow-on for the larger intended outcome",
        "owner surface",
        "activation trigger",
    ):
        if key in required_continuation:
            lines.append(f"- {key.title()}: {required_continuation[key]}")
    lines.extend(["", "## Delegated Judgment", ""])
    for key in (
        "requested outcome",
        "hard constraints",
        "agent may decide locally",
        "escalate when",
    ):
        if key in delegated_judgment:
            lines.append(f"- {key.title()}: {delegated_judgment[key]}")
    if intent_interpretation:
        lines.extend(["", "## Intent Interpretation", ""])
        for key in (
            "literal request",
            "inferred intended outcome",
            "chosen concrete what",
            "interpretation distance",
            "review guidance",
        ):
            if key in intent_interpretation:
                lines.append(f"- {key.title()}: {intent_interpretation[key]}")
    if execution_bounds:
        lines.extend(["", "## Execution Bounds", ""])
        for key in (
            "allowed paths",
            "max changed files",
            "required validation commands",
            "ask-before-refactor threshold",
            "stop before touching",
        ):
            if key in execution_bounds:
                lines.append(f"- {key.title()}: {execution_bounds[key]}")
    if stop_conditions:
        lines.extend(["", "## Stop Conditions", ""])
        for key in (
            "stop when",
            "escalate when boundary reached",
            "escalate on scope drift",
            "escalate on proof failure",
        ):
            if key in stop_conditions:
                lines.append(f"- {key.title()}: {stop_conditions[key]}")
    if context_budget:
        lines.extend(["", "## Context Budget", ""])
        for key in (
            "live working set",
            "recoverable later",
            "externalize before shift",
            "tiny resumability note",
            "context-shift triggers",
        ):
            if key in context_budget:
                lines.append(f"- {key.title()}: {context_budget[key]}")
    if execution_run:
        lines.extend(["", "## Execution Run", ""])
        for key in (
            "run status",
            "executor",
            "handoff source",
            "what happened",
            "scope touched",
            "validations run",
            "result for continuation",
            "next step",
        ):
            if key in execution_run:
                lines.append(f"- {key.title()}: {execution_run[key]}")
    if finished_run_review:
        lines.extend(["", "## Finished-Run Review", ""])
        for key in (
            "review status",
            "scope respected",
            "proof status",
            "intent served",
            "misinterpretation risk",
            "follow-on decision",
        ):
            if key in finished_run_review:
                lines.append(f"- {key.title()}: {finished_run_review[key]}")
    lines.extend(["", "## Proof Report", ""])
    for key in (
        "validation proof",
        "proof achieved now",
        'evidence for "proof achieved" state',
    ):
        if key in proof_report:
            lines.append(f"- {key[0].upper() + key[1:]}: {proof_report[key]}")
    lines.extend(["", "## Intent Satisfaction", ""])
    for key in (
        "original intent",
        "was original intent fully satisfied?",
        "evidence of intent satisfaction",
        "unsolved intent passed to",
    ):
        if key in intent_satisfaction:
            lines.append(f"- {key[0].upper() + key[1:]}: {intent_satisfaction[key]}")
    if system_intent_alignment:
        lines.extend(["", "## System Intent Alignment", ""])
        for key in (
            "relevant system intent",
            "slice shaping bias",
            "broader-lane validation question",
            "intent evidence source",
        ):
            if key in system_intent_alignment:
                lines.append(f"- {key[0].upper() + key[1:]}: {system_intent_alignment[key]}")
    lines.extend(["", "## Closure Check", ""])
    for key in (
        "slice status",
        "larger-intent status",
        "closure decision",
        "why this decision is honest",
        "evidence carried forward",
        "reopen trigger",
    ):
        if key in closure_check:
            lines.append(f"- {key[0].upper() + key[1:]}: {closure_check[key]}")
    lines.extend(["", "## Durable Residue", ""])
    for key in (
        "status",
        "learned constraint",
        "motivation worth preserving",
        "canonical owner now",
        "promotion trigger",
        "retention after promotion",
    ):
        if key in durable_residue:
            lines.append(f"- {key[0].upper() + key[1:]}: {durable_residue[key]}")
    lines.extend(["", "## Execution Summary", ""])
    for key in (
        "outcome delivered",
        "validation confirmed",
        "follow-on routed to",
        "post-work posterity capture",
        "knowledge promoted (memory/docs/config)",
        "resume from",
    ):
        if key in execution_summary:
            lines.append(f"- {key[0].upper() + key[1:]}: {execution_summary[key]}")
    lines.append("")
    return "\n".join(lines)


def _prepared_closeout_proof_report(
    *,
    proof_report: dict[str, str],
    execution_summary: dict[str, str],
    execution_run: dict[str, str],
    finished_run_review: dict[str, str],
    iterative_follow_through: dict[str, str],
) -> dict[str, str]:
    validation_evidence = (
        proof_report.get("validation proof", "").strip()
        or execution_summary.get("validation confirmed", "").strip()
        or execution_run.get("validations run", "").strip()
    )
    if not validation_evidence or validation_evidence.lower() in {"pending", "tbd", "todo"}:
        return {}

    proof_now = (
        proof_report.get("proof achieved now", "").strip()
        or iterative_follow_through.get("proof achieved now", "").strip()
        or finished_run_review.get("proof status", "").strip()
    )
    if not proof_now or proof_now.lower() in {"pending", "tbd", "todo"}:
        proof_now = "yes; validation evidence is recorded in execution summary."

    proof_evidence = proof_report.get('evidence for "proof achieved" state', "").strip()
    if not proof_evidence:
        proof_evidence = execution_run.get("validations run", "").strip() or execution_summary.get("validation confirmed", "").strip()

    return {
        "validation proof": validation_evidence,
        "proof achieved now": proof_now,
        'evidence for "proof achieved" state': proof_evidence,
    }


def _generated_closeout_adapter(
    *,
    record: dict[str, Any],
    patch: dict[str, Any],
) -> dict[str, str]:
    intent_satisfaction = _record_section_dict(patch, "intent_satisfaction") or {}
    closure_check = _record_section_dict(patch, "closure_check") or {}
    proof_report = _record_section_dict(patch, "proof_report") or _record_section_dict(record, "proof_report") or {}
    durable_residue = _record_section_dict(patch, "durable_residue") or {}
    memory_learning = _record_section_dict(patch, "memory_learning_capture") or {}
    execution_run = _record_section_dict(record, "execution_run") or {}
    execution_summary = _record_section_dict(record, "execution_summary") or {}

    changed_surfaces = execution_run.get("changed surfaces", "").strip() or execution_run.get("scope touched", "").strip() or "not recorded"
    unsolved_intent = intent_satisfaction.get("unsolved intent passed to", "").strip()
    recorded_follow_up = execution_summary.get("follow-on routed to", "").strip()
    follow_up = recorded_follow_up or "none"
    if unsolved_intent and unsolved_intent.lower() not in {"none", "none yet", "n/a", "no further action"}:
        follow_up = unsolved_intent
    durable_owner = durable_residue.get("canonical owner now", "").strip() or "archive"
    durable_status = durable_residue.get("status", "").strip() or "none"
    validation = proof_report.get("validation proof", "").strip() or "not recorded"

    lines = [
        "Generated closeout adapter; structured execplan fields are authoritative.",
        f"Intent: {intent_satisfaction.get('original intent', '').strip() or str(record.get('title', 'Completed execplan')).strip()}",
        f"Intent satisfied: {intent_satisfaction.get('was original intent fully satisfied?', '').strip() or 'not recorded'}",
        f"Archive decision: {closure_check.get('closure decision', '').strip() or 'not recorded'}",
        f"Proof: {validation}",
        f"Changed surfaces: {changed_surfaces}",
        f"Durable residue: {durable_status} ({durable_owner})",
        f"Memory learning: {memory_learning.get('decision', 'not recorded').strip() or 'not recorded'}",
        f"Follow-up: {follow_up}",
    ]
    return {
        "status": "generated",
        "source": "archive-plan --prepare-closeout",
        "authority": "derived adapter; intent_satisfaction, closure_check, proof_report, durable_residue, execution_run, and execution_summary remain authoritative",
        "text": "\n".join(lines),
    }


def _prepared_durable_residue(record: dict[str, Any]) -> dict[str, str]:
    existing = _record_section_dict(record, "durable_residue") or {}
    if existing.get("status"):
        prepared = dict(existing)
    else:
        prepared = {
            "status": "evidence_only",
            "learned constraint": "No future-relevant learning was identified beyond the archived proof record.",
            "motivation worth preserving": "none beyond evidence-only archive",
            "canonical owner now": "archive",
            "promotion trigger": "none",
            "retention after promotion": "retain",
        }
    prepared.setdefault("learned constraint", "")
    prepared.setdefault("motivation worth preserving", "")
    prepared.setdefault("canonical owner now", "archive" if prepared.get("status") in EXECPLAN_DURABLE_RESIDUE_OWNERLESS_STATUSES else "")
    prepared.setdefault("promotion trigger", "none")
    prepared.setdefault("retention after promotion", "retain")
    return prepared


def _prepared_memory_learning_capture(record: dict[str, Any]) -> dict[str, str]:
    existing = _record_section_dict(record, "memory_learning_capture") or {}
    durable_residue = _prepared_durable_residue(record)
    residue_status = durable_residue.get("status", "none").strip() or "none"
    if residue_status == "memory":
        decision = "update_existing_memory_note"
        target = durable_residue.get("canonical owner now", "Memory")
        future_learning = "yes"
    elif residue_status in {"docs", "contract", "check"}:
        decision = "promote_to_docs_contracts_checks_code"
        target = durable_residue.get("canonical owner now", residue_status)
        future_learning = "yes"
    elif residue_status == "planning":
        decision = "route_to_planning"
        target = durable_residue.get("canonical owner now", "planning")
        future_learning = "yes"
    elif residue_status == "evidence_only":
        decision = "evidence_only"
        target = durable_residue.get("canonical owner now", "archive")
        future_learning = "no"
    else:
        decision = "none"
        target = "none"
        future_learning = "no"
    return {
        "status": existing.get("status", "reviewed") or "reviewed",
        "memory consult recommended?": existing.get("memory consult recommended?", "review startup/report memory_consult")
        or "review startup/report memory_consult",
        "memory notes read": existing.get("memory notes read", "") or "not recorded",
        "future agents should not rediscover": existing.get("future agents should not rediscover", future_learning) or future_learning,
        "decision": existing.get("decision", decision) or decision,
        "target": existing.get("target", target) or target,
        "reason": existing.get("reason", "Derived from durable_residue during closeout preparation.")
        or "Derived from durable_residue during closeout preparation.",
    }


def _prepared_task_intent_promotion(record: dict[str, Any]) -> dict[str, Any]:
    existing = _record_section_dict(record, "task_intent_promotion") or {}
    durable_residue = _prepared_durable_residue(record)
    residue_status = durable_residue.get("status", "none").strip().lower() or "none"
    owner = durable_residue.get("canonical owner now", "").strip()
    decision = str(existing.get("decision", "")).strip()
    if not decision or decision == "pending":
        if residue_status == "memory":
            decision = "memory"
        elif residue_status == "docs":
            decision = "refine-existing-intent" if "system-intent" in owner else "do-not-promote"
        elif residue_status == "contract":
            decision = "subsystem-intent" if "intent" in owner else "do-not-promote"
        else:
            decision = "do-not-promote"
    return {
        "decision": decision,
        "accepted values": (
            existing.get("accepted values")
            or "do-not-promote|memory|subsystem-intent|system-intent|refine-existing-intent|supersede-existing-intent"
        ),
        "evidence source": existing.get("evidence source") or "archive-plan --prepare-closeout",
        "target scope": existing.get("target scope") or owner,
        "proposed durable intent": existing.get("proposed durable intent") or durable_residue.get("motivation worth preserving", ""),
        "confidence": existing.get("confidence") or "low",
        "needs review": existing.get("needs review", True),
        "owner surface": existing.get("owner surface") or owner,
    }


def _closeout_value_needs_normalization(value: Any) -> bool:
    if not isinstance(value, str):
        return value is None
    return value.strip().lower() in {"", "pending", "not_checked", "not-run-yet", "not run yet", "todo", "tbd"}


def _prepared_canonical_core_closeout(*, record: dict[str, Any], normalized_closure: str, routed_unsolved_intent: str) -> dict[str, Any]:
    canonical_core = dict(_record_section_dict(record, "canonical_core") or {})
    canonical_core["closeout_decision"] = normalized_closure
    canonical_core["continuation_owner"] = routed_unsolved_intent if normalized_closure == "archive-but-keep-lane-open" else "none"
    return canonical_core


def _prepared_iterative_follow_through(
    *,
    record: dict[str, Any],
    proof_now: str,
    validation_evidence: str,
    outcome_delivered: str,
    normalized_closure: str,
    routed_unsolved_intent: str,
) -> dict[str, str]:
    existing = _record_section_dict(record, "iterative_follow_through") or {}
    prepared = dict(existing)
    if _closeout_value_needs_normalization(prepared.get("what this slice enabled")):
        prepared["what this slice enabled"] = outcome_delivered or "The bounded slice completed with recorded closeout evidence."
    if _closeout_value_needs_normalization(prepared.get("proof achieved now")):
        prepared["proof achieved now"] = proof_now or validation_evidence or "validation evidence is recorded in proof_report."
    if _closeout_value_needs_normalization(prepared.get("validation still needed")):
        prepared["validation still needed"] = "None for this archived slice; reopen only if new evidence invalidates the proof."
    if _closeout_value_needs_normalization(prepared.get("next likely slice")):
        prepared["next likely slice"] = (
            f"Continue via {routed_unsolved_intent}."
            if normalized_closure == "archive-but-keep-lane-open"
            else "No required continuation remains for this archived slice."
        )
    if _closeout_value_needs_normalization(prepared.get("intentionally deferred")):
        prepared["intentionally deferred"] = (
            f"Remaining larger intent is routed to {routed_unsolved_intent}."
            if normalized_closure == "archive-but-keep-lane-open"
            else "None."
        )
    if _closeout_value_needs_normalization(prepared.get("discovered implications")):
        prepared["discovered implications"] = "None beyond the recorded closeout distillation."
    return prepared


def _prepared_delegation_outcome_feedback(*, record: dict[str, Any], proof_now: str, normalized_closure: str) -> dict[str, str]:
    existing = _record_section_dict(record, "delegation_outcome_feedback") or {}
    prepared = dict(existing)
    defaults = {
        "route chosen": "not-delegated",
        "route skipped reason": "No delegation route was recorded; prepare-closeout normalized archive-only residue.",
        "expected savings": "none recorded",
        "actual friction": "none recorded",
        "proof result": proof_now or "closeout proof recorded",
        "quality concern": "none recorded",
        "decomposition adjustment": "none",
    }
    if normalized_closure == "archive-but-keep-lane-open":
        defaults["decomposition adjustment"] = "larger intent remains routed through the continuation owner"
    for key, fallback in defaults.items():
        if _closeout_value_needs_normalization(prepared.get(key)):
            prepared[key] = fallback
    return prepared


def _prepared_improvement_signal_review(record: dict[str, Any]) -> dict[str, Any]:
    existing = _record_section_value(record, "improvement_signal_review") or {}
    if not isinstance(existing, dict):
        existing = {}
    prepared = dict(existing)
    durable_residue = _prepared_durable_residue(record)
    durable_owner = durable_residue.get("canonical owner now", "").strip()
    durable_learned = durable_residue.get("learned constraint", "").strip()
    durable_motivation = durable_residue.get("motivation worth preserving", "").strip()
    issue_routed_signal = (
        durable_residue.get("status", "").strip().lower() == "planning"
        and durable_owner
        and (
            durable_owner.lower().startswith("github #")
            or durable_owner.lower() == "issue follow-up"
            or "issue residue" in durable_learned.lower()
        )
    )
    prepared.setdefault("accepted statuses", "not_checked|signals_routed|signals_fixed|signals_dismissed|no_signal_found")
    prepared.setdefault(
        "guidance",
        (
            "At closeout, report AW smoothness/helpfulness gaps, better-way signals, unused-feature reflections, "
            "and places AW could help more. Route each concrete signal to exactly one owner class unless explicitly "
            "split, or mark no_signal_found after checking."
        ),
    )
    prepared.setdefault("source", "operating_posture")
    prepared.setdefault("owner classes", ["issue", "Memory", "Planning", "docs/checks/contracts", "direct fix", "dismissed with reason"])
    prepared.setdefault("ordinary output cap", 3)
    for key in ("signals found", "signals fixed", "signals routed", "signals dismissed"):
        value = prepared.get(key)
        prepared[key] = value if isinstance(value, list) else []
    if issue_routed_signal:
        signal = {
            "summary": durable_learned or durable_motivation or f"Closeout routed issue residue to {durable_owner}.",
            "owner": durable_owner,
            "source": "durable_residue",
        }
        if not any(isinstance(item, dict) and item.get("owner") == durable_owner for item in prepared["signals routed"]):
            prepared["signals routed"].append(signal)
        if not any(isinstance(item, dict) and item.get("owner") == durable_owner for item in prepared["signals found"]):
            prepared["signals found"].append(signal)
    if _closeout_value_needs_normalization(prepared.get("status")):
        if prepared["signals fixed"]:
            prepared["status"] = "signals_fixed"
        elif prepared["signals routed"]:
            prepared["status"] = "signals_routed"
        elif prepared["signals dismissed"]:
            prepared["status"] = "signals_dismissed"
        else:
            prepared["status"] = "no_signal_found"
    if _closeout_value_needs_normalization(prepared.get("next owner")):
        prepared["next owner"] = "none" if prepared["status"] == "no_signal_found" else "see routed signal owner"
    return prepared


def _closeout_larger_intent_is_unresolved(
    *,
    completes_larger_outcome: str,
    required_follow_on: str,
    continuation_owner: str = "",
) -> bool:
    normalized_completion = completes_larger_outcome.strip().lower()
    normalized_follow_on = required_follow_on.strip().lower()
    normalized_owner = continuation_owner.strip().lower()
    return (
        normalized_completion == "no"
        or normalized_follow_on == "yes"
        or (normalized_owner != "" and normalized_owner not in {"none", "n/a", "none yet", "no further action"})
    )


def _inferred_closeout_scope(
    *,
    existing_scope: str,
    completes_larger_outcome: str,
    required_follow_on: str,
    continuation_owner: str,
) -> str:
    normalized = existing_scope.strip().lower()
    if normalized in ARCHIVE_CLOSEOUT_SCOPE_VALUES:
        return normalized
    if _closeout_larger_intent_is_unresolved(
        completes_larger_outcome=completes_larger_outcome,
        required_follow_on=required_follow_on,
        continuation_owner=continuation_owner,
    ):
        return "lane"
    return "slice"


def _execplan_durable_residue(path: Path) -> dict[str, str]:
    record = _record_section_dict(_load_execplan_record(path), "durable_residue")
    if record is not None:
        return record
    lines = _read_lines(path)
    return _extract_kv_fields(_section_lines(lines, "Durable Residue"))


def _invalid_durable_residue_message(durable_residue: dict[str, str]) -> str | None:
    status = durable_residue.get("status", "").strip().lower()
    learned_constraint = durable_residue.get("learned constraint", "").strip()
    motivation = durable_residue.get("motivation worth preserving", "").strip()
    owner = durable_residue.get("canonical owner now", "").strip()
    promotion_trigger = durable_residue.get("promotion trigger", "").strip()
    retention = durable_residue.get("retention after promotion", "").strip().lower()

    if status not in EXECPLAN_DURABLE_RESIDUE_STATUSES:
        return "`durable_residue.status` must be one of `none`, `memory`, `docs`, `contract`, `check`, `planning`, or `evidence_only`"
    if not learned_constraint or not motivation:
        return "fill `Durable Residue` with the learned constraint and motivation routing answer before archiving"
    if retention not in EXECPLAN_DURABLE_RESIDUE_RETENTION_VALUES:
        return "`durable_residue.retention after promotion` must be one of `retain`, `shrink`, `stub`, or `delete`"
    if status in EXECPLAN_DURABLE_RESIDUE_OWNERLESS_STATUSES:
        return None
    if not owner or owner.lower() in EXECPLAN_DURABLE_RESIDUE_OWNER_VALUES:
        return (
            "future-relevant durable residue must name a non-archive canonical owner such as Memory, docs, contracts, checks, or planning"
        )
    if not promotion_trigger or promotion_trigger.lower() in {"none", "n/a", "pending", "todo", "tbd"}:
        return "future-relevant durable residue must name a promotion trigger before archiving"
    return None


def _memory_module_installed(target_root: Path) -> bool:
    memory_root = target_root / ".agentic-workspace" / "memory"
    return (memory_root / "repo" / "manifest.toml").exists() or (memory_root / "repo" / "index.md").exists()


def _invalid_closeout_distillation_message(
    *,
    target_root: Path,
    record: dict[str, Any],
    durable_residue: dict[str, str],
) -> dict[str, str] | None:
    buckets = _closeout_distillation_buckets(record=record, explicit={})
    routed_count = sum(len(items) for items in buckets.values())
    if routed_count == 0:
        return {
            "warning_class": "archive_missing_closeout_distillation",
            "message": "Completed execplan is missing structured closeout distillation.",
            "detail": EXECPLAN_CLOSEOUT_DISTILLATION_QUESTION,
        }

    status = durable_residue.get("status", "").strip().lower()
    if status == "memory" and not _memory_module_installed(target_root):
        return {
            "warning_class": "archive_memory_destination_unavailable",
            "message": "Completed execplan routes reusable learning to Memory, but Memory is not installed.",
            "detail": (
                "Memory-routed durable learning needs an installed Memory module before the completed execplan is removed; "
                "install Memory or reroute the learning to docs, config/checks/tests/contracts, issue follow-up, or Planning."
            ),
        }
    return None


def _add_closeout_distillation_actions(
    *,
    result: InstallResult,
    target_root: Path,
    plan_path: Path,
    record: dict[str, Any],
    durable_residue: dict[str, str],
    dry_run: bool,
) -> None:
    del dry_run
    buckets = _closeout_distillation_buckets(record=record, explicit={})
    result.add("closeout distillation", plan_path, EXECPLAN_CLOSEOUT_DISTILLATION_QUESTION)
    status = durable_residue.get("status", "").strip().lower()
    owner = durable_residue.get("canonical owner now", "").strip()
    learned = durable_residue.get("learned constraint", "").strip()
    if status == "memory":
        slug = _slugify(str(record.get("title", "")).strip() or plan_path.stem)
        summary = learned or next((item["summary"] for item in buckets["memory"] if item.get("summary")), "closeout learning")
        command = (
            f"agentic-memory capture-note {slug} --target . --summary "
            f"{json.dumps(summary)} --surface {plan_path.relative_to(target_root).as_posix()} --format json"
        )
        result.add("memory candidate", target_root / (owner or ".agentic-workspace/memory/repo/index.md"), command)
    for bucket, owner_label in (
        ("docs", "docs"),
        ("config_check", "config/checks/tests/contracts"),
        ("continuation", "planning continuation"),
        ("issue_follow_up", "issue follow-up"),
    ):
        for item in buckets[bucket]:
            result.add("distillation route", plan_path, f"{owner_label}: {item.get('summary', '')}")
    for item in buckets["discard"]:
        result.add("discarded closeout detail", plan_path, item.get("summary", "discard one-off execution detail"))


def _prepare_execplan_closeout(
    *,
    plan_path: Path,
    target_root: Path,
    result: InstallResult,
    dry_run: bool,
    closure_decision: str | None,
    intent_satisfied: str | None,
    unsolved_intent: str | None,
    intent_evidence: str | None,
    closure_reason: str | None,
    closure_evidence: str | None,
    reopen_trigger: str | None,
    discard_summary: str | None,
    continuation_summary: str | None,
) -> bool:
    record_path = _canonical_execplan_record_path(plan_path)
    record = _load_execplan_record(plan_path)
    if record is None:
        result.add("manual review", record_path, "--prepare-closeout currently requires a canonical .plan.json record")
        return False

    intent_continuity = _record_section_dict(record, "intent_continuity") or {}
    required_continuation = _record_section_dict(record, "required_continuation") or {}
    delegated_judgment = _record_section_dict(record, "delegated_judgment") or {}
    intent_interpretation = _record_section_dict(record, "intent_interpretation") or {}
    execution_summary = _record_section_dict(record, "execution_summary") or {}
    execution_run = _record_section_dict(record, "execution_run") or {}
    finished_run_review = _record_section_dict(record, "finished_run_review") or {}
    iterative_follow_through = _record_section_dict(record, "iterative_follow_through") or {}
    proof_report = _record_section_dict(record, "proof_report") or {}
    existing_closure_check = _record_section_dict(record, "closure_check") or {}
    completes_larger_outcome = intent_continuity.get("this slice completes the larger intended outcome", "").strip().lower()
    required_follow_on = required_continuation.get("required follow-on for the larger intended outcome", "").strip().lower()
    continuation_owner = (
        unsolved_intent
        or intent_continuity.get("continuation surface")
        or required_continuation.get("owner surface")
        or intent_continuity.get("parent lane")
        or "#230"
    )
    normalized_closure = (closure_decision or "").strip().lower()
    if not normalized_closure:
        normalized_closure = "archive-but-keep-lane-open" if completes_larger_outcome == "no" else "archive-and-close"
    if normalized_closure not in {"archive-and-close", "archive-but-keep-lane-open"}:
        result.add("manual review", record_path, "--closure-decision must be one of archive-and-close or archive-but-keep-lane-open")
        return False

    existing_intent_satisfaction = _record_section_dict(record, "intent_satisfaction") or {}
    normalized_intent_satisfied = (intent_satisfied or "").strip().lower()
    if not normalized_intent_satisfied:
        normalized_intent_satisfied = str(existing_intent_satisfaction.get("was original intent fully satisfied?", "")).strip().lower()
    if not normalized_intent_satisfied:
        normalized_intent_satisfied = "no" if normalized_closure == "archive-but-keep-lane-open" else "yes"
    if normalized_intent_satisfied not in {"yes", "true", "no", "false"}:
        result.add("manual review", record_path, "--intent-satisfied must be one of yes, no, true, or false")
        return False

    existing_slice_status = str(existing_closure_check.get("slice status", "")).strip().lower()
    existing_larger_status = str(existing_closure_check.get("larger-intent status", "")).strip().lower()
    continuation_owner_for_gate = continuation_owner if completes_larger_outcome == "no" or required_follow_on == "yes" else ""
    closeout_scope = _inferred_closeout_scope(
        existing_scope=str(existing_closure_check.get("closeout scope", "")),
        completes_larger_outcome=completes_larger_outcome,
        required_follow_on=required_follow_on,
        continuation_owner=continuation_owner_for_gate,
    )
    larger_intent_unresolved = _closeout_larger_intent_is_unresolved(
        completes_larger_outcome=completes_larger_outcome,
        required_follow_on=required_follow_on,
        continuation_owner=continuation_owner_for_gate,
    )
    if normalized_closure == "archive-and-close" and larger_intent_unresolved:
        result.warnings.append(
            {
                "warning_class": "archive_larger_intent_proxy_closeout_blocked",
                "path": record_path.relative_to(target_root).as_posix(),
                "message": (
                    "Closeout scope is lane/epic-like and still has unresolved larger intent; "
                    "validation of a bounded proxy cannot prepare archive-and-close."
                ),
            }
        )
        result.add(
            "manual review",
            record_path,
            (
                "use `archive-but-keep-lane-open` and name the continuation owner, or first prove the larger "
                "intent is closed before preparing lane/epic closeout"
            ),
        )
        return False
    slice_status = existing_slice_status or "completed"
    larger_status = "open" if normalized_closure == "archive-but-keep-lane-open" else (existing_larger_status or "closed")
    routed_unsolved_intent = continuation_owner if normalized_closure == "archive-but-keep-lane-open" else "none"
    original_intent = (
        existing_intent_satisfaction.get("original intent")
        or intent_interpretation.get("literal request")
        or intent_interpretation.get("inferred intended outcome")
        or delegated_judgment.get("requested outcome")
        or str(record.get("title", "Completed execplan")).strip()
    )
    evidence = (
        intent_evidence
        or existing_intent_satisfaction.get("evidence of intent satisfaction")
        or "The bounded slice is complete; archive-plan --prepare-closeout generated normalized closeout fields."
    )
    honest_reason = (
        closure_reason
        or existing_closure_check.get("why this decision is honest")
        or (
            "The bounded slice is complete and remaining intent is routed to a checked-in continuation owner."
            if normalized_closure == "archive-but-keep-lane-open"
            else "The bounded slice and larger intent are both complete."
        )
    )
    carried_evidence = (
        closure_evidence
        or existing_closure_check.get("evidence carried forward")
        or ("Prepared closeout records intent satisfaction, closure decision, proof evidence, and distillation buckets.")
    )
    reopen = (
        reopen_trigger
        or existing_closure_check.get("reopen trigger")
        or (
            f"Reopen when {routed_unsolved_intent} activates a fresh bounded slice."
            if normalized_closure == "archive-but-keep-lane-open"
            else "None unless new evidence shows the bounded closure was incomplete."
        )
    )

    patch = {
        "intent_satisfaction": {
            "original intent": original_intent,
            "was original intent fully satisfied?": normalized_intent_satisfied,
            "evidence of intent satisfaction": evidence,
            "unsolved intent passed to": routed_unsolved_intent,
        },
        "closure_check": {
            "closeout scope": closeout_scope,
            "slice status": slice_status,
            "larger-intent status": larger_status,
            "closure decision": normalized_closure,
            "why this decision is honest": honest_reason,
            "evidence carried forward": carried_evidence,
            "reopen trigger": reopen,
        },
        "durable_residue": _prepared_durable_residue(record),
        "memory_learning_capture": _prepared_memory_learning_capture(record),
        "task_intent_promotion": _prepared_task_intent_promotion(record),
    }

    prepared_proof_report = _prepared_closeout_proof_report(
        proof_report=proof_report,
        execution_summary=execution_summary,
        execution_run=execution_run,
        finished_run_review=finished_run_review,
        iterative_follow_through=iterative_follow_through,
    )
    if prepared_proof_report:
        patch["proof_report"] = prepared_proof_report
    normalized_proof_report = prepared_proof_report or proof_report
    proof_now = normalized_proof_report.get("proof achieved now", "").strip()
    validation_evidence = normalized_proof_report.get("validation proof", "").strip()
    patch["canonical_core"] = _prepared_canonical_core_closeout(
        record=record,
        normalized_closure=normalized_closure,
        routed_unsolved_intent=routed_unsolved_intent,
    )
    patch["iterative_follow_through"] = _prepared_iterative_follow_through(
        record=record,
        proof_now=proof_now,
        validation_evidence=validation_evidence,
        outcome_delivered=str(execution_summary.get("outcome delivered", "")).strip(),
        normalized_closure=normalized_closure,
        routed_unsolved_intent=routed_unsolved_intent,
    )
    patch["delegation_outcome_feedback"] = _prepared_delegation_outcome_feedback(
        record=record,
        proof_now=proof_now,
        normalized_closure=normalized_closure,
    )
    patch["improvement_signal_review"] = _prepared_improvement_signal_review(record)

    buckets = _closeout_distillation_buckets(record=record, explicit={})
    for bucket in ("discard", "continuation", "memory", "config_check", "docs", "issue_follow_up"):
        buckets.setdefault(bucket, [])
    if not buckets["discard"]:
        buckets["discard"].append(
            {
                "summary": discard_summary or "Command-by-command execution detail stays in the archived proof record.",
                "owner": "discard",
                "source": "archive-plan --prepare-closeout",
            }
        )
    if normalized_closure == "archive-but-keep-lane-open" and not buckets["continuation"]:
        buckets["continuation"].append(
            {
                "summary": continuation_summary or f"Unsolved larger intent continues in {routed_unsolved_intent}.",
                "owner": routed_unsolved_intent,
                "source": "archive-plan --prepare-closeout",
            }
        )
    patch["closeout_distillation"] = {"buckets": buckets}
    patch["generated_closeout"] = _generated_closeout_adapter(record=record, patch=patch)

    detail = json.dumps(patch, ensure_ascii=False, sort_keys=True)
    if dry_run:
        result.add("would update", record_path, f"prepared closeout patch: {detail}")
        result.add(
            "next command",
            record_path,
            f"rerun without --dry-run to write the closeout and archive {plan_path.relative_to(target_root).as_posix()}",
        )
        return True

    record.update(patch)
    _write_execplan_record(record_path=record_path, record=record, render_markdown=plan_path != record_path)
    result.add("updated", record_path, "prepared normalized closeout fields before archive validation")
    return True


def _parent_lane_state_item(state: dict[str, Any] | None, parent_id: str) -> tuple[str, dict[str, Any]] | None:
    if not isinstance(state, dict):
        return None
    raw_work_items = state.get("work_items", [])
    if isinstance(raw_work_items, list):
        for raw in raw_work_items:
            if isinstance(raw, dict) and str(raw.get("id", "")) == parent_id and str(raw.get("type", "")) == "lane":
                return "work_items", raw
    roadmap = state.get("roadmap")
    if isinstance(roadmap, dict):
        raw_lanes = roadmap.get("lanes", [])
        if isinstance(raw_lanes, list):
            for raw in raw_lanes:
                if isinstance(raw, dict) and str(raw.get("id", "")) == parent_id:
                    return "roadmap.lanes", raw
    return None


def _reference_records_for_parent_lane(item: dict[str, Any]) -> list[dict[str, str]]:
    references: list[dict[str, str]] = [
        {
            "kind": "planning-state",
            "target": ".agentic-workspace/planning/state.toml",
            "label": str(item.get("id", "")),
            "role": "parent_intent",
        }
    ]
    raw_refs = item.get("refs", [])
    if isinstance(raw_refs, list):
        for ref in raw_refs:
            ref_text = str(ref).strip()
            if ref_text:
                references.append({"kind": "reference", "target": ref_text, "label": ref_text, "role": "child_reference"})
    raw_issues = item.get("issues", [])
    if isinstance(raw_issues, list):
        for issue in raw_issues:
            issue_text = str(issue).strip()
            if issue_text:
                references.append({"kind": "external-work", "target": issue_text, "label": issue_text, "role": "child_reference"})
    return references


def _closed_parent_lane_state(state: dict[str, Any], parent_id: str, item: dict[str, Any]) -> dict[str, Any]:
    next_state = dict(state)
    raw_work_items = state.get("work_items", [])
    if isinstance(raw_work_items, list):
        next_state["work_items"] = [
            raw for raw in raw_work_items if not (isinstance(raw, dict) and str(raw.get("id", "")) == parent_id and raw is item)
        ]
    roadmap = state.get("roadmap")
    if isinstance(roadmap, dict):
        next_roadmap = dict(roadmap)
        raw_lanes = roadmap.get("lanes", [])
        if isinstance(raw_lanes, list):
            next_roadmap["lanes"] = [raw for raw in raw_lanes if not (isinstance(raw, dict) and str(raw.get("id", "")) == parent_id)]
        next_state["roadmap"] = next_roadmap
    return next_state


def _parent_lane_durable_residue(item: dict[str, Any]) -> dict[str, str]:
    status = str(item.get("durable_residue") or item.get("residue") or "evidence_only").strip()
    if status not in EXECPLAN_DURABLE_RESIDUE_STATUSES:
        status = "evidence_only"
    owner = str(item.get("residue_owner") or item.get("residue_routing") or "").strip()
    if not owner or owner == ".agentic-workspace/planning/state.toml":
        owner = "archive" if status in EXECPLAN_DURABLE_RESIDUE_OWNERLESS_STATUSES else ""
    return {
        "status": status,
        "learned constraint": str(item.get("outcome") or item.get("reason") or "Parent lane closeout evidence is archived.").strip(),
        "motivation worth preserving": str(
            item.get("promotion_signal") or "Parent lane is no longer current or future planning pressure."
        ).strip(),
        "canonical owner now": owner,
        "promotion trigger": str(item.get("residue_promotion_trigger") or "none").strip(),
        "retention after promotion": str(item.get("residue_retention") or "retain").strip(),
    }


def archive_parent_lane_closeout(
    parent_id: str,
    *,
    target: str | Path | None = None,
    dry_run: bool = False,
    intent_satisfied: str | None = None,
    intent_evidence: str | None = None,
    closure_reason: str | None = None,
    closure_evidence: str | None = None,
    reopen_trigger: str | None = None,
    discard_summary: str | None = None,
    continuation_summary: str | None = None,
) -> InstallResult:
    target_root = resolve_target_root(target)
    result = InstallResult(target_root=target_root, message=f"Archive parent lane closeout '{parent_id}'", dry_run=dry_run)
    state = _read_state_from_toml(target_root)
    matched = _parent_lane_state_item(state, parent_id)
    state_path = target_root / PLANNING_STATE_PATH
    if matched is None or state is None:
        result.add("manual review", state_path, f"parent lane '{parent_id}' was not found in planning state")
        return result
    bucket_path, item = matched
    if _is_closed_planning_state_item(item):
        result.add("manual review", state_path, f"parent lane '{parent_id}' is already closed")
        return result

    normalized_intent_satisfied = (intent_satisfied or "yes").strip().lower()
    if normalized_intent_satisfied not in {"yes", "true", "no", "false"}:
        result.add("manual review", state_path, "--intent-satisfied must be one of yes, no, true, or false")
        return result
    intent_answer = "yes" if normalized_intent_satisfied in {"yes", "true"} else "no"
    closure_decision = "archive-and-close" if intent_answer == "yes" else "archive-but-keep-lane-open"
    larger_status = "closed" if intent_answer == "yes" else "open"
    unsolved_owner = (
        "none"
        if intent_answer == "yes"
        else str(item.get("residue_routing") or item.get("residue_owner") or PLANNING_STATE_PATH.as_posix())
    )
    slug = _slugify(parent_id)
    record_path = target_root / ".agentic-workspace" / "planning" / "execplans" / "archive" / f"{slug}.plan.json"
    if record_path.exists():
        result.add("manual review", record_path, "parent closeout record already exists")
        return result

    title = str(item.get("title") or _title_from_slug(slug)).strip()
    outcome = str(item.get("outcome") or item.get("reason") or f"Parent lane {parent_id} is closed from structured child evidence.").strip()
    record = _build_execplan_record_from_todo_item(
        title=title,
        item_id=parent_id,
        status="completed",
        why_now=outcome,
        next_action="archive the parent lane closeout record.",
        done_when="the parent lane has schema-valid closeout evidence and no first-line planning residue.",
    )
    child_refs = [
        str(ref).strip()
        for ref in [
            *(item.get("issues", []) if isinstance(item.get("issues"), list) else []),
            *(item.get("refs", []) if isinstance(item.get("refs"), list) else []),
        ]
        if str(ref).strip()
    ]
    record.update(
        {
            "parent_lane": {
                "id": parent_id,
                "title": title,
                "priority": str(item.get("priority", "")).strip(),
                "issues": ", ".join(str(issue) for issue in item.get("issues", []) if str(issue).strip())
                if isinstance(item.get("issues"), list)
                else "",
                "source": bucket_path,
            },
            "references": _reference_records_for_parent_lane(item),
            "parent_acceptance_map": {
                "status": "satisfied" if intent_answer == "yes" else "partial",
                "child_refs": child_refs,
                "evidence": intent_evidence or outcome,
            },
            "execution_run": {
                "run status": "completed",
                "executor": "agentic-planning archive-plan --parent-lane-closeout",
                "handoff source": "structured planning state",
                "what happened": "created a schema-valid parent lane closeout from structured state fields.",
                "scope touched": PLANNING_STATE_PATH.as_posix(),
                "changed surfaces": f"{PLANNING_STATE_PATH.as_posix()}; {record_path.relative_to(target_root).as_posix()}",
                "validations run": "schema-backed writer validation",
                "result for continuation": unsolved_owner,
                "next step": "none" if intent_answer == "yes" else f"continue in {unsolved_owner}",
            },
            "finished_run_review": {
                "review status": "completed",
                "scope respected": "yes",
                "proof status": "satisfied",
                "intent served": intent_answer,
                "config compliance": "host-tracker-specific issue closure stayed outside core planning.",
                "misinterpretation risk": "low",
                "follow-on decision": closure_decision,
            },
            "proof_report": {
                "validation proof": "schema-backed writer validation",
                "proof achieved now": "parent lane closeout record validated against planning-execplan.schema.json.",
                'evidence for "proof achieved" state': intent_evidence or outcome,
            },
            "intent_satisfaction": {
                "original intent": str(item.get("outcome") or item.get("title") or title).strip(),
                "was original intent fully satisfied?": intent_answer,
                "evidence of intent satisfaction": intent_evidence or outcome,
                "unsolved intent passed to": unsolved_owner,
            },
            "closure_check": {
                "slice status": "completed",
                "larger-intent status": larger_status,
                "closure decision": closure_decision,
                "why this decision is honest": closure_reason or "Structured child evidence and parent acceptance fields were recorded.",
                "evidence carried forward": closure_evidence or "Parent lane closeout record, child references, and schema-backed proof.",
                "reopen trigger": reopen_trigger or "None unless new evidence shows the parent lane was not actually satisfied.",
            },
            "durable_residue": _parent_lane_durable_residue(item),
        }
    )
    buckets = {"discard": [], "continuation": [], "memory": [], "config_check": [], "docs": [], "issue_follow_up": []}
    buckets["discard"].append(
        {
            "summary": discard_summary or "Historical parent-lane bookkeeping is reconstructable from the archive record and child refs.",
            "owner": "discard",
            "source": "archive-plan --parent-lane-closeout",
        }
    )
    if intent_answer == "no":
        buckets["continuation"].append(
            {
                "summary": continuation_summary or f"Unsolved parent intent continues in {unsolved_owner}.",
                "owner": unsolved_owner,
                "source": "archive-plan --parent-lane-closeout",
            }
        )
    record["closeout_distillation"] = {"buckets": buckets}
    record["generated_closeout"] = _generated_closeout_adapter(record=record, patch=record)

    if dry_run:
        result.add("would create", record_path, "schema-valid parent lane closeout record")
        result.add("would update", state_path, f"remove closed parent lane '{parent_id}' from first-line planning state")
        return result

    _write_execplan_record(record_path=record_path, record=record)
    _write_state_to_toml(target_root, _closed_parent_lane_state(state, parent_id, item))
    result.add("created", record_path, "schema-valid parent lane closeout record")
    result.add("updated", state_path, f"removed closed parent lane '{parent_id}' from first-line planning state")
    _stamp_result_action_mutations(
        result,
        command="agentic-planning archive-plan --parent-lane-closeout",
        reason=f"close parent lane {parent_id}",
    )
    return result


def closeout_execplan(
    plan: str,
    *,
    target: str | Path | None = None,
    dry_run: bool = False,
    claim_level: str = "slice",
    intent_status: str = "satisfied",
    residue: str = "none",
    proof_from: str = "last",
    residue_owner: str | None = None,
    retain_archive: bool = True,
    what_happened: str | None = None,
    scope_touched: str | None = None,
    changed_surfaces: str | None = None,
    review_summary: str | None = None,
    outcome_summary: str | None = None,
) -> InstallResult:
    target_root = resolve_target_root(target)
    result = InstallResult(target_root=target_root, message=f"Close out execplan '{plan}'", dry_run=dry_run)
    normalized_claim = claim_level.strip().lower()
    normalized_intent = intent_status.strip().lower()
    normalized_residue = residue.strip().lower()
    if normalized_claim not in PLANNING_CLOSEOUT_CLAIM_LEVELS:
        result.add("manual review", target_root / PLANNING_STATE_PATH, "--claim-level must be one of slice, lane, or epic")
        return result
    if normalized_intent not in PLANNING_CLOSEOUT_INTENT_STATUSES:
        result.add(
            "manual review",
            target_root / PLANNING_STATE_PATH,
            "--intent-status must be one of satisfied, partial, unsatisfied, or deferred-with-owner",
        )
        return result
    if normalized_residue not in PLANNING_CLOSEOUT_RESIDUE_STATUSES:
        result.add(
            "manual review",
            target_root / PLANNING_STATE_PATH,
            "--residue must be one of none, memory, planning, docs, tests, contracts, issue, or dismissed",
        )
        return result

    plan_path = _resolve_execplan_path(target_root, plan)
    if plan_path is None:
        result.add("manual review", target_root / PLANNING_STATE_PATH, f"execplan '{plan}' was not found")
        return result
    record_path = _canonical_execplan_record_path(plan_path)
    record = _load_execplan_record(plan_path)
    if record is None:
        result.add("manual review", record_path, "planning closeout requires a canonical .plan.json record")
        return result

    closure_decision = "archive-and-close" if normalized_intent == "satisfied" else "archive-but-keep-lane-open"
    intent_satisfied = "yes" if normalized_intent == "satisfied" else "no"
    continuation_owner = residue_owner or ""
    if closure_decision == "archive-but-keep-lane-open" and not continuation_owner:
        continuation_owner = PLANNING_STATE_PATH.as_posix()

    placeholder_values = {
        "",
        "pending",
        "todo",
        "tbd",
        "none yet",
        "current milestone",
        "execution has not started",
        "pending delegated execution.",
        "none yet; execution has not changed files.",
        "not completed yet",
        "last proof selected by closeout",
        "planning closeout completed the run metadata and archive preconditions",
        "bounded closeout scope",
        ".agentic-workspace/planning/",
        "bounded closeout accepted",
    }

    def clean(value: Any) -> str:
        return str(value or "").strip()

    def is_placeholder(value: Any) -> bool:
        return clean(value).lower() in placeholder_values

    def provided(value: str | None) -> str:
        return clean(value)

    proof_request = clean(proof_from)
    proof_report = _record_section_dict(record, "proof_report") or {}
    existing_proof = clean(proof_report.get("validation proof"))
    if proof_request and proof_request.lower() != "last":
        proof = proof_request
        proof_source = "explicit"
    elif existing_proof and not is_placeholder(existing_proof):
        proof = existing_proof
        proof_source = "existing"
    else:
        result.warnings.append(
            {
                "warning_class": "closeout_missing_proof",
                "path": record_path.relative_to(target_root).as_posix(),
                "message": "planning closeout --proof-from last requires an existing non-placeholder proof_report.validation proof.",
                "suggested_fix": "Rerun closeout with --proof-from <proof command or evidence>, or record real proof before using --proof-from last.",
            }
        )
        result.add("manual review", record_path, "planning closeout needs explicit proof; --proof-from last found no existing proof")
        result.add("next safe action", record_path, "rerun planning closeout with --proof-from <proof command or evidence>")
        return result

    execution_run = _record_section_dict(record, "execution_run") or {}
    finished_run_review = _record_section_dict(record, "finished_run_review") or {}
    execution_summary = _record_section_dict(record, "execution_summary") or {}
    run_evidence_inputs = {
        "what happened": provided(what_happened),
        "scope touched": provided(scope_touched),
        "changed surfaces": provided(changed_surfaces),
    }
    run_evidence_sources = {
        "what happened": "what_happened",
        "scope touched": "scope_touched",
        "changed surfaces": "changed_surfaces",
    }
    missing_run_evidence = [
        field for field, option_value in run_evidence_inputs.items() if not option_value and is_placeholder(execution_run.get(field))
    ]
    if not provided(review_summary) and is_placeholder(finished_run_review.get("scope respected")):
        missing_run_evidence.append("review summary")
        run_evidence_sources["review summary"] = "review_summary"
    if not provided(outcome_summary) and is_placeholder(execution_summary.get("outcome delivered")):
        missing_run_evidence.append("outcome summary")
        run_evidence_sources["outcome summary"] = "outcome_summary"
    if missing_run_evidence:
        option_list = ", ".join(f"--{run_evidence_sources[field].replace('_', '-')}" for field in missing_run_evidence)
        result.warnings.append(
            {
                "warning_class": "closeout_missing_finish_run_evidence",
                "path": record_path.relative_to(target_root).as_posix(),
                "message": f"planning closeout needs real finish-run evidence for: {', '.join(missing_run_evidence)}.",
                "suggested_fix": f"Rerun closeout with {option_list}, or record non-placeholder execution_run evidence first.",
            }
        )
        result.add(
            "manual review", record_path, f"planning closeout needs non-placeholder finish-run evidence: {', '.join(missing_run_evidence)}"
        )
        result.add("next safe action", record_path, "rerun planning closeout with explicit finish-run evidence options")
        return result

    status, default_owner = PLANNING_CLOSEOUT_RESIDUE_MAP[normalized_residue]
    owner = residue_owner or default_owner

    if not dry_run:
        active_milestone = _record_section_dict(record, "active_milestone") or {}
        active_milestone["status"] = "completed"
        active_milestone.setdefault("ready", "ready")
        active_milestone["blocked"] = "none"
        record["active_milestone"] = active_milestone
        execution_run["run status"] = "completed"
        if is_placeholder(execution_run.get("executor")):
            execution_run["executor"] = "agentic-planning closeout"
        if run_evidence_inputs["what happened"]:
            execution_run["what happened"] = run_evidence_inputs["what happened"]
        if run_evidence_inputs["scope touched"]:
            execution_run["scope touched"] = run_evidence_inputs["scope touched"]
        if run_evidence_inputs["changed surfaces"]:
            execution_run["changed surfaces"] = run_evidence_inputs["changed surfaces"]
        execution_run["validations run"] = proof
        execution_run["result for continuation"] = (
            f"continue from {continuation_owner}" if closure_decision == "archive-but-keep-lane-open" else "bounded closeout complete"
        )
        execution_run["next step"] = (
            f"promote the next bounded slice from {continuation_owner}"
            if closure_decision == "archive-but-keep-lane-open"
            else "archive this execplan"
        )
        record["execution_run"] = execution_run
        finished_run_review["review status"] = "complete"
        if provided(review_summary):
            finished_run_review["scope respected"] = provided(review_summary)
        elif is_placeholder(finished_run_review.get("scope respected")):
            finished_run_review["scope respected"] = "yes; closeout accepted the bounded claim."
        finished_run_review["proof status"] = "passed"
        finished_run_review["intent served"] = (
            "yes" if normalized_intent == "satisfied" else f"no; intent-status={normalized_intent} keeps continuation explicit."
        )
        if is_placeholder(finished_run_review.get("config compliance")):
            finished_run_review["config compliance"] = "used planning closeout command-owned writer"
        if is_placeholder(finished_run_review.get("misinterpretation risk")):
            finished_run_review["misinterpretation risk"] = "low"
        finished_run_review["follow-on decision"] = continuation_owner if closure_decision == "archive-but-keep-lane-open" else "none"
        record["finished_run_review"] = finished_run_review
        if provided(outcome_summary):
            execution_summary["outcome delivered"] = provided(outcome_summary)
        elif is_placeholder(execution_summary.get("outcome delivered")):
            execution_summary["outcome delivered"] = (
                "closeout accepted the finished run evidence"
                if normalized_intent == "satisfied"
                else f"closeout recorded {normalized_intent} continuation from finished run evidence"
            )
        execution_summary["validation confirmed"] = proof
        execution_summary["follow-on routed to"] = continuation_owner if closure_decision == "archive-but-keep-lane-open" else "none"
        if is_placeholder(execution_summary.get("post-work posterity capture")):
            execution_summary["post-work posterity capture"] = "archive closeout distillation"
        if is_placeholder(execution_summary.get("knowledge promoted (Memory/Docs/Config)")):
            execution_summary["knowledge promoted (Memory/Docs/Config)"] = "none"
        execution_summary["resume from"] = continuation_owner if closure_decision == "archive-but-keep-lane-open" else "archive"
        record["execution_summary"] = execution_summary
        closure_check = _record_section_dict(record, "closure_check") or {}
        closure_check["closeout scope"] = normalized_claim
        closure_check["slice status"] = "completed"
        closure_check["larger-intent status"] = "open" if closure_decision == "archive-but-keep-lane-open" else "closed"
        closure_check["closure decision"] = closure_decision
        closure_check["why this decision is honest"] = (
            f"planning closeout accepted a {normalized_claim} claim with intent-status {normalized_intent}."
        )
        closure_check["evidence carried forward"] = proof
        closure_check["reopen trigger"] = (
            f"Reopen when {continuation_owner} activates a fresh bounded slice."
            if closure_decision == "archive-but-keep-lane-open"
            else "None unless new evidence shows the closeout was incomplete."
        )
        record["closure_check"] = closure_check
        record["durable_residue"] = {
            "status": status,
            "learned constraint": (
                "No future-relevant learning was identified beyond the closeout evidence."
                if status in EXECPLAN_DURABLE_RESIDUE_OWNERLESS_STATUSES
                else f"Closeout routed {normalized_residue} residue to {owner}."
            ),
            "motivation worth preserving": (
                "Closeout reviewed durable residue and found no live follow-up."
                if status in EXECPLAN_DURABLE_RESIDUE_OWNERLESS_STATUSES
                else f"Future agents should continue from {owner} rather than rediscover this closeout residue."
            ),
            "canonical owner now": owner,
            "promotion trigger": "none"
            if status in EXECPLAN_DURABLE_RESIDUE_OWNERLESS_STATUSES
            else "when the routed closeout residue is acted on",
            "retention after promotion": "retain",
        }
        if proof and proof_source == "explicit":
            record["proof_report"] = {
                "validation proof": proof,
                "proof achieved now": "yes; planning closeout recorded explicit proof input.",
                'evidence for "proof achieved" state': proof,
            }
        elif proof and proof_source == "existing":
            record["proof_report"] = proof_report
        if closure_decision == "archive-but-keep-lane-open":
            intent_continuity = _record_section_dict(record, "intent_continuity") or {}
            intent_continuity["this slice completes the larger intended outcome"] = "no"
            intent_continuity["continuation surface"] = continuation_owner
            record["intent_continuity"] = intent_continuity
            required_continuation = _record_section_dict(record, "required_continuation") or {}
            required_continuation["required follow-on for the larger intended outcome"] = "yes"
            required_continuation["owner surface"] = continuation_owner
            existing_activation_trigger = str(required_continuation.get("activation trigger", "")).strip().lower()
            if existing_activation_trigger in {"", "none", "n/a"}:
                required_continuation["activation trigger"] = "when the continuation owner promotes the next slice"
            record["required_continuation"] = required_continuation
        _write_execplan_record(record_path=record_path, record=record, render_markdown=plan_path != record_path)
        result.add("updated", record_path, "recorded closeout residue and proof inputs")

    archive_result = archive_execplan(
        plan,
        target=target_root,
        dry_run=dry_run,
        apply_cleanup=True,
        prepare_closeout=True,
        closure_decision=closure_decision,
        intent_satisfied=intent_satisfied,
        unsolved_intent=continuation_owner if closure_decision == "archive-but-keep-lane-open" else None,
        intent_evidence=proof,
        closure_reason=f"planning closeout accepted a {normalized_claim} claim with intent-status {normalized_intent}.",
        closure_evidence=proof,
        reopen_trigger=(
            f"Reopen when {continuation_owner} activates a fresh bounded slice."
            if closure_decision == "archive-but-keep-lane-open"
            else "None unless new evidence shows the closeout was incomplete."
        ),
        retain_archive=retain_archive,
    )
    result.actions.extend(archive_result.actions)
    result.warnings.extend(archive_result.warnings)
    blocked = bool(result.warnings) or any(action.kind == "manual review" for action in result.actions)
    result.completion_options.extend(
        [
            {
                "id": "resolve-closeout-blocker",
                "allowed": blocked,
                "command": f"agentic-planning closeout {plan} --proof-from <proof> --what-happened <summary> --scope-touched <paths> --changed-surfaces <surfaces>",
                "why": "closeout warnings or manual-review actions are present" if blocked else "no closeout blocker is present",
            },
            {
                "id": "claim-slice-complete",
                "allowed": not blocked,
                "command": "",
                "why": "slice proof, finish-run evidence, and archive preconditions were recorded"
                if not blocked
                else "slice completion is blocked until closeout evidence is repaired",
            },
            {
                "id": "keep-larger-intent-open",
                "allowed": closure_decision == "archive-but-keep-lane-open" and not blocked,
                "owner": continuation_owner if closure_decision == "archive-but-keep-lane-open" else "",
                "why": "intent-status keeps continuation explicit"
                if closure_decision == "archive-but-keep-lane-open"
                else "larger intent was marked satisfied",
            },
            {
                "id": "close-larger-intent",
                "allowed": closure_decision == "archive-and-close" and not blocked,
                "why": "intent-status satisfied was recorded"
                if closure_decision == "archive-and-close"
                else "parent or larger intent remains open",
            },
        ]
    )
    if blocked:
        result.add("next safe action", record_path, "resolve the reported closeout blocker, then rerun planning closeout")
    else:
        result.add("next safe action", target_root / PLANNING_STATE_PATH, "agentic-planning summary --target . --format json")
        result.add(
            "dogfooding reflection",
            record_path,
            (
                "Before final handoff, route any concrete AW smoothness/helpfulness gaps, better-way signals, "
                "unused-feature reflections, or recurring improvement pressure to issues, Memory, planning, "
                "docs/checks/contracts, direct implementation, or explicit dismissal."
            ),
        )
    if not dry_run:
        _stamp_result_action_mutations(result, command="agentic-planning closeout", reason=f"close out execplan {plan}")
    return result


def close_planning_item(
    item: str,
    *,
    target: str | Path | None = None,
    reason: str = "",
    issue: str = "",
    dry_run: bool = False,
) -> InstallResult:
    """Close a completed planning item through package-owned state mutation."""
    target_root = resolve_target_root(target)
    item_id = item.strip()
    result = InstallResult(
        target_root=target_root,
        message=f"Close planning item {item_id}",
        dry_run=dry_run,
    )
    if not item_id:
        result.add("manual review", target_root / PLANNING_STATE_PATH, "close-item requires a non-empty item id")
        return result

    state = _read_state_from_toml(target_root) or {}
    state_candidates = _close_item_state_candidates(state, item_id=item_id, target_root=target_root)
    execplan_candidates = _close_item_execplan_candidates(target_root, item_id=item_id)
    exact_candidates = [candidate for candidate in [*state_candidates, *execplan_candidates] if candidate["match"] == "exact"]
    candidates = exact_candidates or [*state_candidates, *execplan_candidates]
    if not candidates:
        result.add("manual review", target_root / PLANNING_STATE_PATH, f"planning item '{item_id}' was not found")
        return result

    candidates = _collapse_close_item_plan_state_pairs(candidates)
    if len(candidates) != 1:
        candidate_text = "; ".join(f"{candidate['kind']}:{candidate['id']}:{candidate['path']}" for candidate in candidates)
        result.warnings.append(
            {
                "warning_class": "close_item_ambiguous",
                "path": PLANNING_STATE_PATH.as_posix(),
                "message": f"close-item '{item_id}' matched multiple candidates: {candidate_text}",
            }
        )
        result.add("manual review", target_root / PLANNING_STATE_PATH, f"ambiguous close-item id '{item_id}': {candidate_text}")
        return result

    candidate = candidates[0]
    if candidate["kind"] == "execplan":
        archive_result = archive_execplan(
            str(candidate["plan_arg"]),
            target=target_root,
            dry_run=dry_run,
            apply_cleanup=True,
            retain_archive=True,
        )
        archive_result.message = f"Close planning item {item_id} through execplan archive flow"
        return archive_result

    status = str(candidate.get("status", "")).strip().lower()
    normalized_status = _normalize_status(status)
    if normalized_status not in {"completed", "done", "closed"}:
        result.warnings.append(
            {
                "warning_class": "close_item_not_completed",
                "path": PLANNING_STATE_PATH.as_posix(),
                "message": f"planning item '{item_id}' has status '{status or '<unset>'}' and was not closed",
            }
        )
        result.add("manual review", target_root / PLANNING_STATE_PATH, f"item '{item_id}' must be completed before close-item removes it")
        return result

    updated_state = _remove_close_item_state_candidate(state, candidate)
    if updated_state is None:
        result.add("manual review", target_root / PLANNING_STATE_PATH, f"item '{item_id}' could not be removed from structured state")
        return result

    state_path = target_root / PLANNING_STATE_PATH
    detail_parts = [f"closed completed {candidate['kind']} item '{item_id}' from {candidate['bucket']}"]
    if issue.strip():
        detail_parts.append(f"issue: {issue.strip()}")
    if reason.strip():
        detail_parts.append(f"reason: {reason.strip()}")
    detail = "; ".join(detail_parts)
    if dry_run:
        result.add("would update", state_path, detail)
        return result

    _write_state_to_toml(target_root, updated_state)
    result.add("updated", state_path, detail)
    _stamp_result_action_mutations(result, command="agentic-planning close-item", reason=f"close planning item {item_id}")
    return result


def archive_execplan(
    plan: str,
    *,
    target: str | Path | None = None,
    dry_run: bool = False,
    apply_cleanup: bool = False,
    prepare_closeout: bool = False,
    closure_decision: str | None = None,
    intent_satisfied: str | None = None,
    unsolved_intent: str | None = None,
    intent_evidence: str | None = None,
    closure_reason: str | None = None,
    closure_evidence: str | None = None,
    reopen_trigger: str | None = None,
    discard_summary: str | None = None,
    continuation_summary: str | None = None,
    retain_archive: bool = False,
) -> InstallResult:
    target_root = resolve_target_root(target)
    result = InstallResult(target_root=target_root, message=f"Archive execplan '{plan}'", dry_run=dry_run)
    plan_path = _resolve_execplan_path(target_root, plan)
    if plan_path is None or not plan_path.exists():
        result.add("manual review", target_root / plan, "execplan was not found")
        return result

    archive_dir = target_root / ".agentic-workspace" / "planning" / "execplans" / "archive"
    if archive_dir in plan_path.parents:
        result.add("manual review", plan_path, "execplan is already archived")
        return result

    status = _execplan_status(plan_path)
    if status not in {"completed", "done", "closed"}:
        result.add("manual review", plan_path, "archive requires the active milestone status to be completed/done/closed")
        return result
    if prepare_closeout:
        prepared = _prepare_execplan_closeout(
            plan_path=plan_path,
            target_root=target_root,
            result=result,
            dry_run=dry_run,
            closure_decision=closure_decision,
            intent_satisfied=intent_satisfied,
            unsolved_intent=unsolved_intent,
            intent_evidence=intent_evidence,
            closure_reason=closure_reason,
            closure_evidence=closure_evidence,
            reopen_trigger=reopen_trigger,
            discard_summary=discard_summary,
            continuation_summary=continuation_summary,
        )
        if not prepared or dry_run:
            return result
    record_path = _canonical_execplan_record_path(plan_path)
    schema_findings = planning_record_schema_findings(record_path) if record_path.exists() else []
    if schema_findings:
        for finding in schema_findings:
            result.warnings.append(
                {
                    "warning_class": "archive_execplan_schema_drift",
                    "path": record_path.relative_to(target_root).as_posix(),
                    "message": finding,
                }
            )
        result.add(
            "manual review",
            record_path,
            "execplan record must validate against planning-execplan.schema.json before archiving",
        )
        return result
    assurance_closeout_warning = _adaptive_assurance_closeout_warning(plan_path=plan_path, target_root=target_root)
    if assurance_closeout_warning is not None:
        result.warnings.append(assurance_closeout_warning)
        result.add(
            "manual review",
            plan_path,
            "strict adaptive-assurance closeout requires all required refs, blocking gates, and do-not-implement blockers to be satisfied or waived",
        )
        return result
    intent_continuity = _execplan_intent_continuity(plan_path)
    completes_larger_outcome = intent_continuity.get("this slice completes the larger intended outcome", "").strip().lower()
    continuation_surface = intent_continuity.get("continuation surface", "").strip()
    required_continuation = _execplan_required_continuation(plan_path)
    required_follow_on = required_continuation.get("required follow-on for the larger intended outcome", "").strip().lower()
    required_owner_surface = required_continuation.get("owner surface", "").strip()
    activation_trigger = required_continuation.get("activation trigger", "").strip()
    delegated_judgment = _execplan_delegated_judgment(plan_path)
    requested_outcome = delegated_judgment.get("requested outcome", "").strip()
    hard_constraints = delegated_judgment.get("hard constraints", "").strip()
    agent_may_decide = delegated_judgment.get("agent may decide locally", "").strip()
    escalate_when = delegated_judgment.get("escalate when", "").strip()
    execution_summary = _execplan_execution_summary(plan_path)
    outcome_delivered = execution_summary.get("outcome delivered", "").strip()
    validation_confirmed = execution_summary.get("validation confirmed", "").strip()
    follow_on_routed_to = execution_summary.get("follow-on routed to", "").strip()
    post_work_posterity_capture = execution_summary.get("post-work posterity capture", "").strip()
    resume_from = execution_summary.get("resume from", "").strip()
    proof_report = _execplan_proof_report(plan_path)
    validation_proof = proof_report.get("validation proof", "").strip()
    proof_achieved_now = proof_report.get("proof achieved now", "").strip()
    proof_evidence = proof_report.get('evidence for "proof achieved" state', "").strip()
    intent_satisfaction = _execplan_intent_satisfaction(plan_path)
    original_intent = intent_satisfaction.get("original intent", "").strip()
    fully_satisfied = intent_satisfaction.get("was original intent fully satisfied?", "").strip().lower()
    satisfaction_evidence = intent_satisfaction.get("evidence of intent satisfaction", "").strip()
    unsolved_intent = intent_satisfaction.get("unsolved intent passed to", "").strip()
    closure_check = _execplan_closure_check(plan_path)
    closeout_scope = closure_check.get("closeout scope", "").strip().lower()
    slice_status = closure_check.get("slice status", "").strip().lower()
    larger_intent_status = closure_check.get("larger-intent status", "").strip().lower()
    closure_decision = closure_check.get("closure decision", "").strip().lower()
    closure_reason = closure_check.get("why this decision is honest", "").strip()
    closure_evidence = closure_check.get("evidence carried forward", "").strip()
    reopen_trigger = closure_check.get("reopen trigger", "").strip()
    durable_residue = _execplan_durable_residue(plan_path)
    closeout_record = _load_execplan_record(plan_path) or _build_execplan_record_from_markdown(plan_path)
    validation_commands = _execplan_validation_commands(plan_path)
    if completes_larger_outcome == "no" and (not continuation_surface or continuation_surface.lower() in {"none", "n/a"}):
        result.warnings.append(
            {
                "warning_class": "archive_missing_intent_continuity",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": ("Execplan leaves the larger intended outcome incomplete but does not name the continuation surface."),
            }
        )
        result.add(
            "manual review",
            plan_path,
            "larger intended outcome is unfinished; set Continuation surface before archiving",
        )
        return result
    if completes_larger_outcome == "no" and required_follow_on != "yes":
        result.warnings.append(
            {
                "warning_class": "archive_missing_required_follow_on",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": "Execplan leaves the larger intended outcome incomplete but does not record required follow-on explicitly.",
            }
        )
        result.add(
            "manual review",
            plan_path,
            "larger intended outcome is unfinished; record Required Continuation before archiving",
        )
        return result
    if required_follow_on == "yes" and (
        not required_owner_surface
        or required_owner_surface.lower() in {"none", "n/a"}
        or not activation_trigger
        or activation_trigger.lower() in {"none", "n/a"}
    ):
        result.warnings.append(
            {
                "warning_class": "archive_missing_required_follow_on",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": "Execplan records required follow-on but does not name both the owner surface and activation trigger.",
            }
        )
        result.add(
            "manual review",
            plan_path,
            "required follow-on needs both owner surface and activation trigger before archiving",
        )
        return result
    if not requested_outcome or not hard_constraints or not agent_may_decide or not escalate_when:
        result.warnings.append(
            {
                "warning_class": "archive_missing_delegated_judgment",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": (
                    "Execplan is missing one or more delegated-judgment fields needed "
                    "to preserve intended outcome and escalation boundaries."
                ),
            }
        )
        result.add(
            "manual review",
            plan_path,
            "fill `Delegated Judgment` before archiving",
        )
        return result
    if not outcome_delivered or outcome_delivered.lower() in {"pending", "not completed yet", "todo", "tbd"}:
        result.warnings.append(
            {
                "warning_class": "archive_missing_execution_summary",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": "Completed execplan is missing an explicit delivered-outcome summary.",
            }
        )
        result.add(
            "manual review",
            plan_path,
            "run `agentic-planning closeout <plan> --what-happened ... --outcome-summary ...` or fill `Execution Summary` with the delivered outcome before archiving",
        )
        return result
    if not validation_confirmed or validation_confirmed.lower() in {"pending", "tbd", "todo"}:
        result.warnings.append(
            {
                "warning_class": "archive_missing_execution_summary",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": "Completed execplan is missing an explicit validation summary.",
            }
        )
        result.add(
            "manual review",
            plan_path,
            "run `agentic-planning closeout <plan> --proof-from ...` or fill `Execution Summary` with the validation confirmation before archiving",
        )
        return result
    if not follow_on_routed_to or follow_on_routed_to.lower() in {"pending", "tbd", "todo", "none yet"}:
        result.warnings.append(
            {
                "warning_class": "archive_missing_execution_summary",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": "Completed execplan is missing an explicit follow-on routing summary.",
            }
        )
        result.add(
            "manual review",
            plan_path,
            "run `agentic-planning closeout <plan> --residue ... --residue-owner ...` or fill `Execution Summary` with the follow-on routing before archiving",
        )
        return result
    if not post_work_posterity_capture or post_work_posterity_capture.lower() in {"pending", "tbd", "todo", "none yet"}:
        result.warnings.append(
            {
                "warning_class": "archive_missing_execution_summary",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": (
                    "Completed execplan is missing an explicit post-work posterity capture summary "
                    "covering what should survive this slice and where it belongs."
                ),
            }
        )
        result.add(
            "manual review",
            plan_path,
            "run `agentic-planning closeout <plan> --residue ... --residue-owner ...` or fill `Execution Summary` with what should survive this slice and where it belongs before archiving",
        )
        return result
    if not resume_from or resume_from.lower() in {"pending", "tbd", "todo", "current milestone"}:
        result.warnings.append(
            {
                "warning_class": "archive_missing_execution_summary",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": "Completed execplan is missing an explicit resume cue.",
            }
        )
        result.add(
            "manual review",
            plan_path,
            "run `agentic-planning closeout <plan> --outcome-summary ...` or fill `Execution Summary` with the post-archive resume cue before archiving",
        )
        return result
    if not validation_proof or not proof_achieved_now or not proof_evidence:
        result.warnings.append(
            {
                "warning_class": "archive_missing_proof_report",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": "Completed execplan is missing a complete proof report.",
            }
        )
        result.add(
            "manual review",
            plan_path,
            "run `agentic-planning closeout <plan> --proof-from ...` or fill `Proof Report` with validation proof and evidence before archiving",
        )
        return result
    if not original_intent or fully_satisfied not in {"yes", "true", "no", "false"} or not satisfaction_evidence:
        result.warnings.append(
            {
                "warning_class": "archive_missing_intent_satisfaction",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": "Completed execplan is missing a complete intent satisfaction report.",
            }
        )
        result.add(
            "manual review",
            plan_path,
            (
                "fill `Intent Satisfaction` before archiving: "
                "`intent_satisfaction.was original intent fully satisfied?` must be one of `yes`, `true`, `no`, or `false`, "
                "and `original intent` plus `evidence of intent satisfaction` must be present"
            ),
        )
        return result
    if (
        not slice_status
        or not larger_intent_status
        or not closure_decision
        or not closure_reason
        or not closure_evidence
        or not reopen_trigger
    ):
        result.warnings.append(
            {
                "warning_class": "archive_missing_closure_check",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": "Completed execplan is missing a complete Closure Check.",
            }
        )
        result.add("manual review", plan_path, "fill `Closure Check` before archiving")
        return result
    if slice_status not in ARCHIVE_SLICE_STATUS_VALUES:
        suggested = " Use `complete` for a completed bounded slice." if slice_status in {"satisfied", "done", "closed"} else ""
        result.warnings.append(
            {
                "warning_class": "archive_missing_closure_check",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": "Closure Check does not mark the bounded slice as complete.",
            }
        )
        result.add(
            "manual review",
            plan_path,
            (
                "mark the bounded slice complete before archiving: "
                "`closure_check.slice status` must be one of `complete`, `completed`, or `bounded slice complete`." + suggested
            ),
        )
        return result
    if closure_decision in {"keep-active", "stay-active", "continue-active"}:
        result.warnings.append(
            {
                "warning_class": "archive_missing_closure_check",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": "Closure Check still says this plan should remain active.",
            }
        )
        result.add("manual review", plan_path, "keep the plan active until `Closure Check` allows archive")
        return result
    if closeout_scope and closeout_scope not in ARCHIVE_CLOSEOUT_SCOPE_VALUES:
        result.warnings.append(
            {
                "warning_class": "archive_missing_closure_check",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": f"Closure Check uses an unsupported closeout scope: {closeout_scope}.",
            }
        )
        result.add(
            "manual review",
            plan_path,
            "`closure_check.closeout scope` must be one of `slice`, `lane`, or `epic` when present",
        )
        return result
    if closure_decision == "archive-and-close" and _closeout_larger_intent_is_unresolved(
        completes_larger_outcome=completes_larger_outcome,
        required_follow_on=required_follow_on,
        continuation_owner=required_owner_surface if required_follow_on == "yes" else "",
    ):
        result.warnings.append(
            {
                "warning_class": "archive_larger_intent_proxy_closeout_blocked",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": (
                    "Archive-and-close is blocked because the execplan still records unresolved larger intent "
                    "or a required continuation owner."
                ),
            }
        )
        result.add(
            "manual review",
            plan_path,
            "switch to `archive-but-keep-lane-open` or close the recorded larger-intent continuation before archiving",
        )
        return result
    if closure_decision == "archive-and-close":
        if fully_satisfied not in {"yes", "true"} or larger_intent_status not in ARCHIVE_AND_CLOSE_LARGER_INTENT_VALUES:
            suggested = (
                " Use `closed` when the larger intent is fully satisfied."
                if larger_intent_status in {"satisfied", "done", "archive", "archived"}
                else ""
            )
            result.warnings.append(
                {
                    "warning_class": "archive_intent_not_fully_satisfied",
                    "path": plan_path.relative_to(target_root).as_posix(),
                    "message": "Archive-and-close requires explicit larger-intent closure evidence.",
                }
            )
            result.add(
                "manual review",
                plan_path,
                (
                    "record larger-intent closure honestly before using `archive-and-close`: "
                    "`intent_satisfaction.was original intent fully satisfied?` must be `yes` or `true`, "
                    "and `closure_check.larger-intent status` must be one of `closed`, `complete`, or `completed`." + suggested
                ),
            )
            return result
        if unsolved_intent and unsolved_intent.lower() not in {"none", "n/a", "none yet"}:
            result.warnings.append(
                {
                    "warning_class": "archive_intent_not_fully_satisfied",
                    "path": plan_path.relative_to(target_root).as_posix(),
                    "message": "Archive-and-close cannot leave unsolved intent routed elsewhere.",
                }
            )
            result.add(
                "manual review",
                plan_path,
                (
                    "remove unsolved intent routing or switch to `archive-but-keep-lane-open`: "
                    "`intent_satisfaction.unsolved intent passed to` must be `none`, `n/a`, or `none yet` for `archive-and-close`"
                ),
            )
            return result
    elif closure_decision == "archive-but-keep-lane-open":
        if fully_satisfied not in {"yes", "true", "no", "false"} or larger_intent_status not in ARCHIVE_KEEP_OPEN_LARGER_INTENT_VALUES:
            result.warnings.append(
                {
                    "warning_class": "archive_intent_not_fully_satisfied",
                    "path": plan_path.relative_to(target_root).as_posix(),
                    "message": "Archive-but-keep-lane-open requires explicit evidence that the larger intent remains open.",
                }
            )
            result.add(
                "manual review",
                plan_path,
                (
                    "align `Intent Satisfaction` and `Closure Check` with `archive-but-keep-lane-open`: "
                    "`intent_satisfaction.was original intent fully satisfied?` must explicitly answer the bounded/source intent, "
                    "and `closure_check.larger-intent status` must be one of `open`, `partial`, or `unfinished`"
                ),
            )
            return result
        if not unsolved_intent or unsolved_intent.lower() in {"none", "n/a", "none yet"}:
            result.warnings.append(
                {
                    "warning_class": "archive_missing_required_follow_on",
                    "path": plan_path.relative_to(target_root).as_posix(),
                    "message": "Partial-intent archive must name the checked-in owner that now carries the unsolved intent.",
                }
            )
            result.add(
                "manual review",
                plan_path,
                (
                    "record the routed unsolved intent before archiving a partial slice: "
                    "`intent_satisfaction.unsolved intent passed to` must name the checked-in continuation owner"
                ),
            )
            return result
    else:
        suggested = " Use `archive-and-close` for fully completed work." if closure_decision in {"archive", "close", "close-lane"} else ""
        result.warnings.append(
            {
                "warning_class": "archive_missing_closure_check",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": f"Closure Check uses an unsupported closure decision: {closure_decision}.",
            }
        )
        result.add(
            "manual review",
            plan_path,
            (
                "use a supported closure decision: "
                "`closure_check.closure decision` must be one of `archive-and-close` or `archive-but-keep-lane-open`." + suggested
            ),
        )
        return result
    durable_residue_message = _invalid_durable_residue_message(durable_residue)
    if durable_residue_message is not None:
        result.warnings.append(
            {
                "warning_class": "archive_missing_durable_residue",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": "Completed execplan is missing valid durable-residue routing.",
            }
        )
        result.add("manual review", plan_path, durable_residue_message)
        return result
    distillation_message = _invalid_closeout_distillation_message(
        target_root=target_root,
        record=closeout_record,
        durable_residue=durable_residue,
    )
    if distillation_message is not None:
        result.warnings.append(
            {
                "warning_class": distillation_message["warning_class"],
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": distillation_message["message"],
            }
        )
        result.add("manual review", plan_path, distillation_message["detail"])
        return result
    if _execplan_needs_reference_sweep(plan_path) and not _validation_has_reference_sweep(validation_commands):
        result.warnings.append(
            {
                "warning_class": "archive_missing_closure_check",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": "Rename/refactor-like completed work is missing a stale-reference sweep in Validation Commands.",
            }
        )
        result.add(
            "manual review",
            plan_path,
            "add a stale-reference sweep to `Validation Commands` before archiving rename/refactor-like work",
        )
        return result
    record_path = _canonical_execplan_record_path(plan_path)
    destination = archive_dir / plan_path.name
    destination_record = _canonical_execplan_record_path(destination)
    destination_record_conflict = destination_record.exists()
    if retain_archive and destination_record_conflict:
        destination_record = _unique_archive_record_path(destination_record)
    archived_record_relative = destination_record.relative_to(target_root).as_posix()
    has_record = record_path.exists()
    if retain_archive:
        if destination.exists() and destination.suffix == ".md":
            result.add(
                "retention",
                destination_record,
                f"retained Markdown archive view already exists; using canonical record {archived_record_relative}",
            )
        if destination_record_conflict:
            result.add(
                "retention",
                destination_record,
                "retained archive destination already exists; using unique retained archive path",
            )

    cleanup_todo_lines: list[str] | None = None
    todo_ref_items = _todo_referencing_items(target_root / ".agentic-workspace/planning/state.toml", plan_path, target_root)
    if apply_cleanup and todo_ref_items:
        closed_state = _close_state_active_execplan_for_archive(
            target_root=target_root,
            plan_path=plan_path,
            archived_record_relative=archived_record_relative,
            durable_residue=durable_residue,
            closure_decision=closure_decision,
        )
        if closed_state["changed"]:
            cleanup_todo_lines = _state_to_toml_lines(closed_state["state"])
            for detail in closed_state["details"]:
                result.add("would update" if dry_run else "updated", target_root / ".agentic-workspace/planning/state.toml", detail)
        else:
            cleanup_todo_lines = _remove_todo_items(target_root / ".agentic-workspace/planning/state.toml", todo_ref_items)
        for item in todo_ref_items:
            if closed_state["changed"]:
                continue
            result.add(
                "would update" if dry_run else "updated",
                target_root / ".agentic-workspace/planning/state.toml",
                (f"remove TODO item '{item.item_id}' while closing its plan"),
            )
    elif apply_cleanup:
        compact_cleanup = _cleanup_compact_todo_archive_followup(
            target_root / ".agentic-workspace/planning/state.toml", plan_path, target_root
        )
        if compact_cleanup["changed"]:
            cleanup_todo_lines = compact_cleanup["text"].splitlines()
            for detail in compact_cleanup["details"]:
                result.add("would update" if dry_run else "updated", target_root / ".agentic-workspace/planning/state.toml", detail)

    remaining_todo_refs = [] if cleanup_todo_lines is not None else todo_ref_items
    blocking_todo_refs = [item for item in remaining_todo_refs if _normalize_status(item.fields.get("status", "")) != "completed"]
    if blocking_todo_refs:
        for item in blocking_todo_refs:
            item_id = item.item_id or "?"
            result.warnings.append(
                {
                    "warning_class": "archive_blocked_by_todo_reference",
                    "path": ".agentic-workspace/planning/state.toml",
                    "message": f"TODO item '{item_id}' still references this execplan; remove or redirect it before archiving.",
                }
            )
            result.add(
                "manual review",
                target_root / ".agentic-workspace/planning/state.toml",
                f"TODO item '{item_id}' still references this execplan",
            )
        return result

    cleanup_roadmap_state = _cleanup_state_roadmap_followup(target_root, plan_path)
    if cleanup_roadmap_state["changed"] and apply_cleanup:
        action_kind = "would update" if dry_run else "updated"
        for detail in cleanup_roadmap_state["details"]:
            result.add(action_kind, target_root / PLANNING_STATE_PATH, detail)
    elif cleanup_roadmap_state["changed"] or cleanup_roadmap_state["note"]:
        note = (
            cleanup_roadmap_state["note"]
            or ".agentic-workspace/planning/state.toml has cleanup-ready roadmap residue tied to the archived plan."
        )
        result.warnings.append(
            {
                "warning_class": "roadmap_archive_followup",
                "path": PLANNING_STATE_PATH.as_posix(),
                "message": note,
            }
        )
        result.add("suggested fix", target_root / PLANNING_STATE_PATH, note)

    legacy_roadmap_path = target_root / "ROADMAP.md"
    cleanup_legacy_roadmap = _cleanup_roadmap_archive_followup(legacy_roadmap_path, plan_path)
    if cleanup_legacy_roadmap["changed"] and apply_cleanup:
        action_kind = "would update" if dry_run else "updated"
        for detail in cleanup_legacy_roadmap["details"]:
            result.add(action_kind, legacy_roadmap_path, detail)
    elif cleanup_legacy_roadmap["changed"] or cleanup_legacy_roadmap["note"]:
        note = cleanup_legacy_roadmap["note"] or "ROADMAP.md has cleanup-ready residue tied to the archived plan."
        result.warnings.append(
            {
                "warning_class": "roadmap_archive_followup",
                "path": "ROADMAP.md",
                "message": note,
            }
        )
        result.add("suggested fix", legacy_roadmap_path, note)

    if retain_archive:
        archive_size_warning = _archive_size_guardrail_warning(
            target_root=target_root,
            destination_record=destination_record,
            record_path=record_path,
            plan_path=plan_path,
            has_record=has_record,
        )
        if archive_size_warning is not None:
            result.warnings.append(archive_size_warning)
            result.add(
                "manual review",
                destination_record,
                "archive record would exceed the structured-file inventory max_bytes guardrail before write",
            )
            return result

    if dry_run:
        _add_closeout_distillation_actions(
            result=result,
            target_root=target_root,
            plan_path=plan_path,
            record=closeout_record,
            durable_residue=durable_residue,
            dry_run=True,
        )
        if retain_archive:
            if has_record:
                detail = f"archive {record_path.relative_to(target_root).as_posix()}"
                if destination_record_conflict:
                    detail += " using unique retained archive path"
                result.add("would move", destination_record, detail)
            else:
                detail = "build canonical record from Markdown and archive"
                if destination_record_conflict:
                    detail += " using unique retained archive path"
                result.add("would create", destination_record, detail)
            if plan_path != record_path:
                result.add("would remove", plan_path, "remove active Markdown view")
        else:
            if record_path.exists():
                result.add("would remove", record_path, "remove completed execplan after closeout distillation")
            if plan_path.exists() and plan_path != record_path:
                result.add("would remove", plan_path, "remove completed Markdown execplan view after closeout distillation")
        return result

    _add_closeout_distillation_actions(
        result=result,
        target_root=target_root,
        plan_path=plan_path,
        record=closeout_record,
        durable_residue=durable_residue,
        dry_run=False,
    )
    if retain_archive:
        archive_dir.mkdir(parents=True, exist_ok=True)
        if has_record:
            shutil.move(str(record_path), str(destination_record))
        else:
            _write_execplan_record(record_path=destination_record, record=closeout_record)
        if plan_path.exists() and plan_path != record_path:
            plan_path.unlink()
    else:
        if plan_path.exists() and plan_path != record_path:
            plan_path.unlink()
        if record_path.exists():
            record_path.unlink()
    if cleanup_todo_lines is not None and not (cleanup_roadmap_state["changed"] and apply_cleanup):
        (target_root / ".agentic-workspace/planning/state.toml").write_text("\n".join(cleanup_todo_lines).rstrip() + "\n", encoding="utf-8")
    if cleanup_roadmap_state["changed"] and apply_cleanup:
        state_to_write = cleanup_roadmap_state["state"]
        if cleanup_todo_lines is not None and isinstance(state_to_write, dict):
            state_to_write = _merge_todo_state_from_toml_lines(state_to_write, cleanup_todo_lines)
        _write_state_to_toml(target_root, state_to_write)
    if cleanup_legacy_roadmap["changed"] and apply_cleanup and cleanup_legacy_roadmap["text"] is not None:
        legacy_roadmap_path.write_text(cleanup_legacy_roadmap["text"], encoding="utf-8")
    if retain_archive:
        result.add("archived", destination_record, f"canonical record for {plan_path.relative_to(target_root).as_posix()}")
    else:
        result.add("closed", plan_path, "completed execplan removed from Planning after closeout distillation")
    _stamp_result_action_mutations(result, command="agentic-planning archive-plan", reason=f"archive execplan {plan}")
    return result


def _unique_archive_record_path(destination_record: Path) -> Path:
    """Return a deterministic sibling archive path without overwriting retained evidence."""
    if destination_record.name.endswith(".plan.json"):
        base_name = destination_record.name[: -len(".plan.json")]
        suffix_text = ".plan.json"
    else:
        base_name = destination_record.stem
        suffix_text = destination_record.suffix
    for suffix in range(2, 1000):
        candidate = destination_record.with_name(f"{base_name}-{suffix}{suffix_text}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"unable to choose unique archive path for {destination_record}")


def _archive_size_guardrail_warning(
    *,
    target_root: Path,
    destination_record: Path,
    record_path: Path,
    plan_path: Path,
    has_record: bool,
) -> dict[str, str] | None:
    max_bytes = _structured_file_inventory_max_bytes(target_root, ".agentic-workspace/planning/execplans/archive/*.plan.json")
    if max_bytes is None:
        return None
    if has_record:
        projected_bytes = record_path.stat().st_size if record_path.exists() else 0
    else:
        record = _build_execplan_record_from_markdown(plan_path)
        projected_bytes = len((json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    if projected_bytes <= max_bytes:
        return None
    return {
        "warning_class": "archive_size_guardrail_blocked",
        "path": destination_record.relative_to(target_root).as_posix(),
        "message": (
            f"Archive would write {projected_bytes} bytes, exceeding structured-file inventory max_bytes={max_bytes} "
            "for .agentic-workspace/planning/execplans/archive/*.plan.json; distill or shrink the execplan before archiving."
        ),
    }


def _structured_file_inventory_max_bytes(target_root: Path, pattern: str) -> int | None:
    inventory_path = target_root / "src" / "agentic_workspace" / "contracts" / "structured_file_inventory.json"
    if not inventory_path.exists():
        return None
    try:
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    entries = inventory.get("entries", [])
    if not isinstance(entries, list):
        return None
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("pattern") != pattern:
            continue
        guardrails = entry.get("guardrails", {})
        if isinstance(guardrails, dict) and isinstance(guardrails.get("max_bytes"), int):
            return int(guardrails["max_bytes"])
    return None


def _adaptive_assurance_closeout_warning(*, plan_path: Path, target_root: Path) -> dict[str, str] | None:
    adaptive_assurance = _execplan_raw_dict(plan_path, "adaptive_assurance")
    if not bool(adaptive_assurance.get("strict_closeout", False)):
        return None
    traceability_refs = _execplan_raw_dict(plan_path, "traceability_refs")
    required_refs = [str(item).strip() for item in adaptive_assurance.get("required_refs", []) if str(item).strip()]
    missing_required_refs = [
        f"traceability_refs.{ref_field}"
        for ref_field in required_refs
        if not isinstance(traceability_refs.get(ref_field), list) or not traceability_refs.get(ref_field)
    ]
    required_gate_ids = {str(item).strip() for item in adaptive_assurance.get("required_gates", []) if str(item).strip()}
    pending_blocking_gates: list[str] = []
    for gate in _execplan_raw_list(plan_path, "control_gates"):
        if not isinstance(gate, dict):
            continue
        gate_id = str(gate.get("id", "")).strip()
        status = str(gate.get("status", "")).strip().lower()
        blocking = bool(gate.get("blocking", False)) or gate_id in required_gate_ids
        if blocking and status not in {"satisfied", "waived"}:
            pending_blocking_gates.append(gate_id or "<unnamed-gate>")
    unresolved_blockers: list[str] = []
    for blocker in _execplan_raw_list(plan_path, "implementation_blockers"):
        if not isinstance(blocker, dict):
            continue
        status = str(blocker.get("status", "")).strip().lower()
        if bool(blocker.get("do_not_implement", False)) and status not in {"resolved", "satisfied", "waived"}:
            unresolved_blockers.append(str(blocker.get("id", "")).strip() or "<unnamed-blocker>")
    if not (missing_required_refs or pending_blocking_gates or unresolved_blockers):
        return None
    details = []
    if missing_required_refs:
        details.append(
            f"missing required traceability ref fields: {', '.join(missing_required_refs)} "
            "(adaptive_assurance.required_refs names traceability_refs field names, not literal issue ids or document refs)"
        )
    if pending_blocking_gates:
        details.append(f"pending blocking gates: {', '.join(pending_blocking_gates)}")
    if unresolved_blockers:
        details.append(f"unresolved blockers: {', '.join(unresolved_blockers)}")
    return {
        "warning_class": "archive_adaptive_assurance_blocked",
        "path": plan_path.relative_to(target_root).as_posix(),
        "message": (
            "Strict adaptive-assurance closeout is blocked; "
            + "; ".join(details)
            + ". Rerun after updating those fields, or use `archive-plan --prepare-closeout` first if closeout fields still need normalization."
        ),
    }


def format_actions(actions: list[Action], target_root: Path) -> list[str]:
    lines: list[str] = []
    for action in actions:
        try:
            relative = action.path.relative_to(target_root).as_posix()
        except ValueError:
            relative = action.path.as_posix()
        lines.append(f"{action.kind}: {relative} ({action.detail})")
    return lines


def format_result_json(result: InstallResult) -> str:
    payload: dict[str, Any] = {
        "target_root": str(result.target_root),
        "message": result.message,
        "dry_run": result.dry_run,
        "bootstrap_version": result.bootstrap_version,
        "actions": [{"kind": action.kind, "path": str(action.path), "detail": action.detail} for action in result.actions],
        "warnings": result.warnings,
    }
    if result.completion_options:
        payload["completion_options"] = result.completion_options
    if result.dry_run:
        payload["lifecycle_plan"] = _lifecycle_plan_payload(result)
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _lifecycle_plan_payload(result: InstallResult) -> dict[str, Any]:
    grouped: dict[str, list[str]] = {
        "create": [],
        "update": [],
        "remove": [],
        "preserve": [],
        "review_required": [],
    }
    for action in result.actions:
        try:
            path = action.path.relative_to(result.target_root).as_posix()
        except ValueError:
            path = action.path.as_posix()
        kind = action.kind.lower()
        if "copy" in kind or "create" in kind:
            grouped["create"].append(path)
        elif "overwrite" in kind or "update" in kind:
            grouped["update"].append(path)
        elif "remove" in kind or "delete" in kind:
            grouped["remove"].append(path)
        elif "skip" in kind or "preserve" in kind:
            grouped["preserve"].append(path)
        elif "review" in kind or "warning" in kind:
            grouped["review_required"].append(path)

    return {
        "schema_version": "planning-lifecycle-plan/v1",
        "target": str(result.target_root),
        "operation": _lifecycle_operation_name(result.message),
        "selected_modules": ["planning"],
        "summary": {
            "create_count": len(grouped["create"]),
            "update_count": len(grouped["update"]),
            "remove_count": len(grouped["remove"]),
            "preserve_count": len(grouped["preserve"]),
            "review_required_count": len(grouped["review_required"]),
            "warning_count": len(result.warnings),
        },
        "files": grouped,
        "warnings": result.warnings,
        "local_only_state": {
            "status": "not-authoritative",
            "rule": "Lifecycle dry-run plans do not inspect or mutate ignored local-only integration or memory state.",
        },
        "next_safe_command": _lifecycle_next_safe_command(result),
    }


def _lifecycle_operation_name(message: str) -> str:
    lowered = message.lower()
    if "adoption" in lowered:
        return "adopt"
    if "upgrade" in lowered:
        return "upgrade"
    if "uninstall" in lowered:
        return "uninstall"
    if "archive" in lowered:
        return "archive-plan"
    if "create execplan scaffold" in lowered or "new-plan" in lowered:
        return "new-plan"
    if "promote" in lowered:
        return "promote-to-plan"
    if "create review" in lowered:
        return "create-review"
    if "install" in lowered:
        return "install"
    return "unknown"


def _lifecycle_next_safe_command(result: InstallResult) -> str:
    operation = _lifecycle_operation_name(result.message)
    if operation == "unknown":
        return "Review actions and rerun the same command without --dry-run only if the plan matches intent."
    return f"agentic-planning {operation} --target {result.target_root}"


def format_summary_json(summary: dict[str, Any]) -> str:
    return json.dumps(summary, indent=2)


def _copy_payload(
    *,
    target_root: Path,
    result: InstallResult,
    conservative: bool,
    force: bool,
    files: Iterable[Path] = REQUIRED_PAYLOAD_FILES,
) -> None:
    root = payload_root()
    for relative in sorted(files, key=lambda path: path.as_posix()):
        if relative in GENERATED_PAYLOAD_FILES:
            continue
        source = root / relative
        if not source.exists() or not source.is_file():
            target_relative = relative
            if target_relative.name.endswith(".template.md"):
                target_relative = target_relative.with_name(target_relative.name[:-12] + ".md")
            result.add("manual review", target_root / target_relative, "payload source file is missing")
            continue
        target_relative = relative
        if target_relative.name.endswith(".template.md"):
            target_relative = target_relative.with_name(target_relative.name[:-12] + ".md")
        destination = target_root / target_relative
        existed = destination.exists()
        if existed and conservative:
            result.add("skipped", destination, "already present")
            continue
        if existed and not force:
            result.add("skipped", destination, "already present")
            continue
        if result.dry_run:
            result.add("would copy" if not existed else "would overwrite", destination, source.as_posix())
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        result.add("copied" if not existed else "overwritten", destination, source.as_posix())


def _copy_bundled_skills(*, target_root: Path, result: InstallResult, conservative: bool, force: bool) -> None:
    root = skills_root()
    if not root.exists():
        destination = target_root / PLANNING_SKILLS_MANAGED_ROOT
        result.add("manual review", destination, "bundled planning skills directory is missing")
        return
    for source in sorted(root.rglob("*")):
        if not source.is_file() or "__pycache__" in source.parts or source.suffix == ".pyc":
            continue
        relative = source.relative_to(root)
        destination = target_root / PLANNING_SKILLS_MANAGED_ROOT / relative
        existed = destination.exists()
        if existed and conservative:
            result.add("skipped", destination, "already present")
            continue
        if existed and not force:
            result.add("skipped", destination, "already present")
            continue
        if result.dry_run:
            result.add("would copy" if not existed else "would overwrite", destination, source.as_posix())
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        result.add("copied" if not existed else "overwritten", destination, source.as_posix())


def _copy_payload_file(*, relative: Path, target_root: Path, result: InstallResult, overwrite: bool) -> None:
    source = payload_root() / relative
    target_relative = relative
    if target_relative.name.endswith(".template.md"):
        target_relative = target_relative.with_name(target_relative.name[:-12] + ".md")
    destination = target_root / target_relative
    if not source.exists():
        result.add("manual review", destination, "payload source file is missing")
        return

    if destination.exists():
        if not overwrite:
            result.add("skipped", destination, "repo-owned surface left unchanged")
            return
        if _files_match(source, destination):
            result.add("current", destination, "already matches managed payload")
            return
        if result.dry_run:
            result.add("would overwrite", destination, source.as_posix())
            return
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        result.add("overwritten", destination, source.as_posix())
        return

    if result.dry_run:
        result.add("would copy", destination, source.as_posix())
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    result.add("copied", destination, source.as_posix())


def _remove_bundled_skill_file(*, relative: Path, target_root: Path) -> bool:
    destination = target_root / relative
    if not destination.exists() or not destination.is_file():
        return False
    source = skills_root() / relative.relative_to(PLANNING_SKILLS_MANAGED_ROOT)
    if not source.exists() or not source.is_file():
        return False
    return destination.read_bytes() == source.read_bytes()


def _render_generated_agent_files(*, target_root: Path, result: InstallResult, apply: bool) -> None:
    manifest_path = target_root / PLANNING_MANIFEST_PATH
    if not manifest_path.exists():
        result.add(
            "manual review",
            manifest_path,
            "cannot render generated agent docs because .agentic-workspace/planning/agent-manifest.json is missing",
        )
        return
    for relative, rendered, label in _generated_agent_file_expectations(target_root):
        destination = target_root / relative
        existing = destination.read_text(encoding="utf-8") if destination.exists() else None
        if existing == rendered:
            result.add("current", destination, f"{label} already matches manifest")
            continue
        if not apply:
            result.add("would update", destination, f"render {label} from manifest")
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="utf-8")
        result.add("updated" if existing is not None else "created", destination, f"rendered {label} from manifest")


def _run_planning_checker(target_root: Path) -> list[dict[str, str]]:
    checker_path = SOURCE_PLANNING_CHECKER_SCRIPT_PATH
    if not checker_path.exists():
        return []
    spec = importlib.util.spec_from_file_location("planning_checker", checker_path)
    if spec is None or spec.loader is None:
        return [
            {
                "warning_class": "planning_checker_load_failure",
                "path": checker_path.as_posix(),
                "message": "Unable to load planning checker.",
            }
        ]
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return [warning._asdict() for warning in module.gather_planning_warnings(repo_root=target_root)]


def _render_quickstart_for_repo(target_root: Path) -> str:
    manifest_path = target_root / PLANNING_MANIFEST_PATH
    if not manifest_path.exists():
        return render_quickstart(load_manifest(manifest_path))
    return render_quickstart(load_manifest(manifest_path))


def _render_routing_for_repo(target_root: Path) -> str:
    manifest_path = target_root / PLANNING_MANIFEST_PATH
    if not manifest_path.exists():
        return render_routing(load_manifest(manifest_path))
    return render_routing(load_manifest(manifest_path))


def _generated_agent_file_expectations(target_root: Path) -> list[tuple[Path, str, str]]:
    manifest_path = target_root / PLANNING_MANIFEST_PATH
    if not manifest_path.exists():
        return []
    return []


def _has_unresolved_placeholders(text: str) -> bool:
    return bool(re.search(r"<[A-Z][A-Z0-9_]+>", text))


def _warning_remediation(warning_class: str) -> str | None:
    return {
        "todo_shape_drift": "Keep TODO focused on activation only; move execution detail into an execplan or durable docs.",
        "todo_activation_overflow": "Prune completed or speculative TODO detail until only the bounded active queue remains.",
        "todo_missing_execplan_linkage": "Create or promote this item to a .agentic-workspace/planning/execplans plan and point Surface at it.",
        "todo_plan_required_hint": "This direct task has grown beyond direct-task shape; scaffold an execplan for it.",
        "todo_broken_surface_reference": "Repair Surface so it points at a live .agentic-workspace/planning/execplans path, or remove the stale item.",
        "planning_state_unsupported_activation_shape": (
            "Run `agentic-workspace summary --target . --format json --verbose`, then migrate string execplan references "
            "to supported `todo.active_items` objects or create a replacement with `agentic-planning new-plan`; "
            "do not delete state.toml as the first move."
        ),
        "planning_record_schema_drift": (
            "Preserve the invalid record as evidence, scaffold a valid replacement with `agentic-planning new-plan` "
            "or migrate the record to the current schema, then rerun `agentic-workspace summary --target . --format json`."
        ),
        "execplan_structure_drift": (
            "Restore the current template sections, especially Intent Continuity, Required Continuation, "
            "Delegated Judgment, Active Milestone, and Execution Summary, so the plan matches the newer contract; "
            "compare the plan with .agentic-workspace/planning/execplans/README.md and .agentic-workspace/docs/execution-flow-contract.md."
        ),
        "execplan_immediate_next_action_drift": "Reduce Immediate Next Action to one concrete next step.",
        "execplan_next_action_projection_drift": (
            "Update machine_readable_contract.execution.next_step, or make immediate_next_action[0] match it; "
            "compact summary uses immediate_next_action[0] when both are present."
        ),
        "execplan_stale_mode_residue": (
            "Remove stale prep-only halt gates and validation text from the active plan, or mark the plan explicitly "
            "as prep-only again before handing it off."
        ),
        "execplan_missing_file_reference": (
            "Update active plan next actions and references so they point only to existing files, or create the referenced "
            "checked-in planning artifact before handoff."
        ),
        "execplan_readiness_drift": "Set Ready/Blocked explicitly so the active milestone can be resumed without re-deriving state.",
        "execplan_log_drift": "Compress the drift log into short decision notes or archive the completed plan.",
        "execplan_notebook_drift": "Strip status-journal residue out of the plan and keep only the current execution contract.",
        "execplan_under_specified": (
            "Fill in the missing contract sections so the plan can survive upgrades without extra chat context; "
            "compare the plan with .agentic-workspace/planning/execplans/README.md and .agentic-workspace/docs/execution-flow-contract.md."
        ),
        "roadmap_execution_drift": "Reduce ROADMAP back to candidate framing; keep active sequencing in TODO and execplans.",
        "roadmap_stale_candidate_pressure": "Prune stale candidate detail and leave compact candidate stubs only.",
        "promotion_linkage_drift": "Make the promotion signal explicit in TODO or ROADMAP so activation has a visible trigger.",
        "upgrade_source_stale": (
            "Refresh .agentic-workspace/planning/UPGRADE-SOURCE.toml after intentionally upgrading the bootstrap source."
        ),
        "archive_accumulation_drift": (
            "Archive completed live execplans with `agentic-planning archive-plan <plan> --target .`, "
            "or return the plan to active status if it still owns future execution."
        ),
        "closed_work_history_residue": (
            "Remove reconstructable closed work rows from .agentic-workspace/planning/state.toml; keep closed rows only "
            "when they carry non-reconstructable future routing."
        ),
        "planning_memory_boundary_blur": "Move durable technical facts into memory or canonical docs, then leave planning surfaces lean.",
        "planning_decomposition_artifact_misplaced": (
            "Run `agentic-planning intake-artifact --artifact <path> --route decomposition --id <id> --target . "
            "--remove-source --format json` or recreate it from `TEMPLATE.decomposition.json`."
        ),
        "planning_artifact_freehand": (
            "Run `agentic-planning intake-artifact --artifact <path> --route auto --id <id> --target . "
            "--remove-source --format json` to route the artifact or refuse with a concrete next action."
        ),
        "startup_policy_drift": "Restore the minimal startup order in AGENTS, quickstart, and manifest.",
    }.get(warning_class)


def _detect_adoption_mode(target_root: Path) -> str:
    count = 0
    for relative in _installed_surface_files():
        target_relative = relative
        if target_relative.name.endswith(".template.md"):
            target_relative = target_relative.with_name(target_relative.name[:-12] + ".md")
        if (target_root / target_relative).exists():
            count += 1
    required_present = count
    if required_present == 0:
        return "uninitialised"
    if (target_root / "src" / "repo_planning_bootstrap").exists() and (target_root / "bootstrap").exists():
        return "self-hosted"
    if required_present >= len(_installed_surface_files()) // 2:
        return "installed"
    return "partial"


def _should_include_payload_path(path: Path, root: Path) -> bool:
    if not path.is_file():
        return False
    relative_parts = path.relative_to(root).parts
    if "__pycache__" in relative_parts:
        return False
    return path.suffix != ".pyc"


def _can_remove_payload_file(*, relative: Path, target_root: Path) -> bool:
    target_relative = relative
    if target_relative.name.endswith(".template.md"):
        target_relative = target_relative.with_name(target_relative.name[:-12] + ".md")
    destination = target_root / target_relative
    if not destination.exists() or not destination.is_file():
        return False
    if relative in GENERATED_PAYLOAD_FILES:
        expectations = dict((path, text) for path, text, _ in _generated_agent_file_expectations(target_root))
        expected_text = expectations.get(relative)
        if expected_text is None:
            return False
        return destination.read_text(encoding="utf-8") == expected_text
    expected = _expected_target_file_bytes(relative=relative, target_root=target_root)
    if expected is None:
        return False
    return destination.read_bytes() == expected


def _expected_target_file_bytes(*, relative: Path, target_root: Path) -> bytes | None:
    source = payload_root() / relative
    if not source.exists() or not source.is_file():
        return None
    return source.read_bytes()


def _files_match(source: Path, destination: Path) -> bool:
    return source.is_file() and destination.is_file() and source.read_bytes() == destination.read_bytes()


def _prune_empty_parent_dirs(*, target_root: Path, relatives: list[Path]) -> None:
    candidates = sorted(
        {parent for relative in relatives for parent in relative.parents if parent != Path(".")},
        key=lambda path: len(path.parts),
        reverse=True,
    )
    for relative_dir in candidates:
        directory = target_root / relative_dir
        if directory.exists() and directory.is_dir():
            try:
                directory.rmdir()
            except OSError:
                continue


def _read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def _read_todo_items_from_lines(lines: list[str]) -> list[TodoItem]:
    items: list[TodoItem] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not re.match(r"^\s*-\s*ID\s*:\s*\S+", line):
            index += 1
            continue

        start = index
        fields: dict[str, str] = {}
        field_order: list[str] = []
        while index < len(lines):
            row = lines[index]
            if index != start and re.match(r"^\s*-\s*ID\s*:\s*\S+", row):
                break
            if index != start and row.startswith("## "):
                break
            match = re.match(r"^\s*(?:-\s*)?([^:]+):\s*(.*)\s*$", row)
            if match:
                key = match.group(1).strip().lower()
                if key not in field_order:
                    field_order.append(key)
                fields[key] = match.group(2).strip()
            index += 1
            if index >= len(lines):
                break
            if lines[index].strip() == "":
                break
        items.append(TodoItem(fields=fields, field_order=field_order, start=start, end=index))
        index += 1
    return items


def _section_lines(lines: list[str], heading: str) -> list[str]:
    target = f"## {heading}".lower()
    start = -1
    for index, line in enumerate(lines):
        if line.strip().lower() == target:
            start = index + 1
            break
    if start < 0:
        return []
    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break
    return lines[start:end]


def _extract_kv_fields(lines: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in lines:
        match = re.match(r"^\s*-\s*([^:]+):\s*(.*)\s*$", line)
        if match:
            fields[match.group(1).strip().lower()] = match.group(2).strip()
    return fields


def _extract_section_bullets(path: Path, heading: str) -> list[str]:
    record = _load_execplan_record(path)
    if isinstance(record, dict):
        mapping = {
            "Goal": "goal",
            "Non-Goals": "non_goals",
            "Immediate Next Action": "immediate_next_action",
            "Completion Criteria": "completion_criteria",
            "Blockers": "blockers",
            "Touched Paths": "touched_paths",
            "Validation Commands": "validation_commands",
            "Required Tools": "required_tools",
        }
        key = mapping.get(heading)
        if key:
            values = _record_section_list(record, key)
            if values is not None:
                return values

    values: list[str] = []
    for line in _section_lines(_read_lines(path), heading):
        match = re.match(r"^\s*-\s+(.*\S)\s*$", line)
        if match:
            values.append(match.group(1).strip())
    return values


def _execplan_next_action_projection(plan_path: Path) -> dict[str, str]:
    record = _load_execplan_record(plan_path)
    if isinstance(record, dict):
        canonical_core = record.get("canonical_core", {})
        if isinstance(canonical_core, dict):
            next_action = str(canonical_core.get("next_action", "")).strip()
            if next_action:
                return {
                    "next_action": next_action,
                    "source": "canonical_core.next_action",
                }
        immediate = record.get("immediate_next_action", [])
        if isinstance(immediate, list):
            for item in immediate:
                next_action = str(item).strip()
                if next_action:
                    return {
                        "next_action": next_action,
                        "source": "immediate_next_action[0]",
                    }
        machine_contract = record.get("machine_readable_contract", {})
        if isinstance(machine_contract, dict):
            execution = machine_contract.get("execution", {})
            if isinstance(execution, dict):
                next_step = str(execution.get("next_step", "")).strip()
                if next_step:
                    return {
                        "next_action": next_step,
                        "source": "machine_readable_contract.execution.next_step",
                    }
    immediate = _extract_section_bullets(plan_path, "Immediate Next Action")
    if immediate:
        return {
            "next_action": immediate[0],
            "source": "Immediate Next Action[0]",
        }
    return {"next_action": "", "source": ""}


def _execplan_canonical_core(plan_path: Path) -> dict[str, Any]:
    record = _load_execplan_record(plan_path)
    if not isinstance(record, dict):
        return {}
    canonical_core = record.get("canonical_core", {})
    return dict(canonical_core) if isinstance(canonical_core, dict) else {}


def _execplan_profile(plan_path: Path) -> dict[str, Any]:
    record = _load_execplan_record(plan_path)
    if not isinstance(record, dict):
        return {}
    profile = record.get("execplan_profile", {})
    return dict(profile) if isinstance(profile, dict) else {}


def _canonical_core_string_list(canonical_core: dict[str, Any], key: str) -> list[str] | None:
    value = canonical_core.get(key)
    if not isinstance(value, list):
        return None
    return [str(item).strip() for item in value if str(item).strip()]


def _execplan_next_action_warnings(*, target_root: Path, plan_files: list[Path]) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    for plan_path in plan_files:
        record = _load_execplan_record(plan_path)
        if not isinstance(record, dict):
            continue
        canonical_core = record.get("canonical_core", {})
        machine_contract = record.get("machine_readable_contract", {})
        execution = machine_contract.get("execution", {}) if isinstance(machine_contract, dict) else {}
        machine_next = str(execution.get("next_step", "")).strip() if isinstance(execution, dict) else ""
        raw_immediate = record.get("immediate_next_action", [])
        immediate = [str(item).strip() for item in raw_immediate if str(item).strip()] if isinstance(raw_immediate, list) else []
        canonical_next = str(canonical_core.get("next_action", "")).strip() if isinstance(canonical_core, dict) else ""
        if canonical_next:
            for source, projected in (
                ("immediate_next_action[0]", immediate[0] if immediate else ""),
                ("machine_readable_contract.execution.next_step", machine_next),
            ):
                if projected and projected != canonical_next:
                    warnings.append(
                        {
                            "warning_class": "execplan_canonical_projection_drift",
                            "path": plan_path.relative_to(target_root).as_posix(),
                            "message": (
                                f"{source} diverges from canonical_core.next_action; "
                                "summary uses canonical_core as the authoritative projection source."
                            ),
                        }
                    )
        if isinstance(canonical_core, dict):
            for key, legacy_key in (
                ("proof_expectations", "validation_commands"),
                ("touched_scope", "touched_paths"),
                ("completion_criteria", "completion_criteria"),
            ):
                canonical_values = _canonical_core_string_list(canonical_core, key)
                legacy_raw = record.get(legacy_key, [])
                legacy_values = [str(item).strip() for item in legacy_raw if str(item).strip()] if isinstance(legacy_raw, list) else []
                if canonical_values and legacy_values and canonical_values != legacy_values:
                    warnings.append(
                        {
                            "warning_class": "execplan_canonical_projection_drift",
                            "path": plan_path.relative_to(target_root).as_posix(),
                            "message": (
                                f"{legacy_key} diverges from canonical_core.{key}; "
                                "summary uses canonical_core as the authoritative projection source."
                            ),
                        }
                    )
        if not canonical_next and machine_next and immediate and machine_next != immediate[0]:
            warnings.append(
                {
                    "warning_class": "execplan_next_action_projection_drift",
                    "path": plan_path.relative_to(target_root).as_posix(),
                    "message": (
                        "machine_readable_contract.execution.next_step diverges from immediate_next_action[0]; "
                        "summary uses immediate_next_action[0] as the canonical next-action projection."
                    ),
                }
            )
        warnings.extend(_execplan_missing_reference_warnings(target_root=target_root, plan_path=plan_path, record=record))
    return warnings


def _execplan_mode_residue_warnings(*, target_root: Path, plan_files: list[Path]) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    for plan_path in plan_files:
        record = _load_execplan_record(plan_path)
        if not isinstance(record, dict):
            continue
        machine_contract = record.get("machine_readable_contract", {})
        planning_mode = machine_contract.get("planning_mode", {}) if isinstance(machine_contract, dict) else {}
        prep_only = bool(planning_mode.get("prep_only", False)) if isinstance(planning_mode, dict) else False
        if prep_only:
            continue
        residue_sources: list[str] = []
        for gate in record.get("control_gates", []):
            if not isinstance(gate, dict):
                continue
            gate_id = str(gate.get("id", "")).strip().lower()
            gate_text = json.dumps(gate, sort_keys=True).lower()
            if gate_id == "prep-only-halt" or "prep-only mode active" in gate_text:
                residue_sources.append("control_gates")
                break
        for field_name in ("immediate_next_action", "validation_commands"):
            raw_values = record.get(field_name, [])
            if isinstance(raw_values, list) and any("prep-only mode active" in str(item).lower() for item in raw_values):
                residue_sources.append(field_name)
        if residue_sources:
            warnings.append(
                {
                    "warning_class": "execplan_stale_mode_residue",
                    "path": plan_path.relative_to(target_root).as_posix(),
                    "message": (
                        f"Plan is not marked prep-only but still contains prep-only halt residue in {', '.join(_dedupe(residue_sources))}."
                    ),
                    "suggested_fix": (
                        "Remove stale prep-only halt gates and validation text from the active plan, or mark the plan "
                        "explicitly as prep-only again before handoff."
                    ),
                }
            )
    return warnings


_FILE_REFERENCE_SUFFIXES = {
    ".md",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".txt",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".sh",
    ".ps1",
}


def _file_reference_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    for token in re.findall(r"`([^`]+)`|([^\s,;:]+)", text):
        raw = token[0] or token[1]
        if _looks_like_markup_tag(raw):
            continue
        value = _strip_file_reference_token(raw)
        if not value or "://" in value or value.startswith("-"):
            continue
        normalized = value.replace("\\", "/")
        if normalized.startswith("//"):
            continue
        if _looks_like_conceptual_slash_phrase(normalized):
            continue
        suffix = Path(normalized).suffix.lower()
        if suffix in _FILE_REFERENCE_SUFFIXES or "/" in normalized:
            candidates.append(normalized)
    return _dedupe(candidates)


def _strip_file_reference_token(raw: str) -> str:
    value = raw.strip()
    value = value.lstrip("\"'([{<")
    value = value.rstrip("\"')]}>.,")
    return value


def _looks_like_markup_tag(token: str) -> bool:
    stripped = token.strip().rstrip(".,;:")
    return bool(re.search(r"</?[A-Za-z][A-Za-z0-9:-]*(?:\s+[^<>]*)?/?>", stripped))


def _looks_like_conceptual_slash_phrase(value: str) -> bool:
    if Path(value).suffix:
        return False
    parts = [part for part in value.split("/") if part]
    if len(parts) <= 1:
        return False
    if any(len(part) > 1 and part.isupper() for part in parts):
        return True
    conceptual_terms = {
        "checks",
        "contracts",
        "docs",
        "reports",
        "schemas",
        "skills",
        "tests",
        "tools",
    }
    return len(parts) >= 3 and all(part.lower() in conceptual_terms for part in parts)


def _execplan_missing_reference_warnings(*, target_root: Path, plan_path: Path, record: dict[str, Any]) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    values: list[tuple[str, str]] = []
    raw_immediate = record.get("immediate_next_action", [])
    if isinstance(raw_immediate, list):
        values.extend(("immediate_next_action", str(item)) for item in raw_immediate if str(item).strip())
    machine_contract = record.get("machine_readable_contract", {})
    execution = machine_contract.get("execution", {}) if isinstance(machine_contract, dict) else {}
    if isinstance(execution, dict) and str(execution.get("next_step", "")).strip():
        values.append(("machine_readable_contract.execution.next_step", str(execution["next_step"])))
    for reference in record.get("references", []):
        if not isinstance(reference, dict):
            continue
        for key in ("path", "locator", "source", "target"):
            if str(reference.get(key, "")).strip():
                values.append((f"references[].{key}", str(reference[key])))
    for field_name, value in values:
        for candidate in _file_reference_candidates(value):
            if candidate.startswith("#"):
                continue
            candidate_path = (target_root / candidate).resolve()
            if candidate_path.exists():
                continue
            warnings.append(
                {
                    "warning_class": "execplan_missing_file_reference",
                    "path": plan_path.relative_to(target_root).as_posix(),
                    "message": f"{field_name} references `{candidate}`, but that path does not exist in the target repository.",
                    "suggested_fix": (
                        "Update the active plan so next actions and references point only to existing files, "
                        "or create the referenced checked-in planning artifact before handoff."
                    ),
                }
            )
    return warnings


def _execplan_capability_posture(path: Path) -> dict[str, str]:
    record = _record_section_dict(_load_execplan_record(path), "capability_posture")
    if record is not None:
        return record

    fields = _extract_kv_fields(_section_lines(_read_lines(path), "Capability Posture"))
    required_fields = (
        "execution class",
        "recommended strength",
        "preferred location",
        "delegation friendly",
        "strong external reasoning",
        "why",
    )
    if not any(fields.get(field, "").strip() for field in required_fields):
        return {}
    return {field: fields.get(field, "").strip() for field in required_fields if fields.get(field, "").strip()}


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _read_todo_items(path: Path) -> tuple[list[str], list[TodoItem]]:
    lines = _read_lines(path)
    return lines, _read_todo_items_from_lines(lines)


def _compact_todo_item_from_state(state: dict[str, Any] | None, item_id: str) -> TodoItem | None:
    if not isinstance(state, dict):
        return None
    active = state.get("active")
    if isinstance(active, dict):
        for raw in active.get("execplans", []):
            item = _todo_item_from_compact_record(raw, item_id)
            if item is not None:
                return item
    raw_work_items = state.get("work_items", [])
    if isinstance(raw_work_items, list):
        for raw in raw_work_items:
            item = _todo_item_from_compact_record(raw, item_id)
            if item is not None:
                return item
    todo = state.get("todo")
    if isinstance(todo, dict):
        for bucket in ("active_items", "queued_items"):
            raw_items = todo.get(bucket, [])
            if not isinstance(raw_items, list):
                continue
            for raw in raw_items:
                if not isinstance(raw, dict) or str(raw.get("id", "")) != item_id:
                    continue
                item = _todo_item_from_compact_record(raw, item_id)
                if item is not None:
                    return item
    roadmap = state.get("roadmap")
    if isinstance(roadmap, dict):
        for bucket in ("lanes", "candidates"):
            raw_items = roadmap.get(bucket, [])
            if not isinstance(raw_items, list):
                continue
            for raw in raw_items:
                item = _todo_item_from_compact_record(raw, item_id)
                if item is not None:
                    return item
    return None


def _todo_item_from_compact_record(raw: Any, item_id: str) -> TodoItem | None:
    if not isinstance(raw, dict) or str(raw.get("id", "")) != item_id:
        return None
    fields: dict[str, str] = {}
    field_order: list[str] = []
    for key, value in raw.items():
        normalized_key = str(key).replace("_", " ").lower()
        field_order.append(normalized_key)
        if isinstance(value, list):
            fields[normalized_key] = ", ".join(str(item) for item in value)
        else:
            fields[normalized_key] = str(value)
    if "surface" not in fields and "path" in fields:
        fields["surface"] = fields["path"]
        field_order.append("surface")
    return TodoItem(fields=fields, field_order=field_order, start=-1, end=-1)


def _update_compact_todo_item_in_state(
    state: dict[str, Any] | None,
    item_id: str,
    updated_fields: dict[str, str],
) -> dict[str, Any] | None:
    if not isinstance(state, dict):
        return None
    next_state = dict(state)
    raw_work_items = state.get("work_items", [])
    if isinstance(raw_work_items, list):
        next_items: list[Any] = []
        promoted_item: dict[str, Any] | None = None
        for raw in raw_work_items:
            if not isinstance(raw, dict) or str(raw.get("id", "")) != item_id:
                next_items.append(raw)
                continue
            promoted_item = dict(raw)
            for key in ("next_action", "next action", "done_when", "done when"):
                promoted_item.pop(key, None)
            promoted_item.pop("type", None)
            promoted_item.pop("surface", None)
            surface = updated_fields.get("surface", "").strip()
            if surface:
                promoted_item["path"] = surface
        if promoted_item is not None:
            promoted_item["maturity"] = "active"
            promoted_item["status"] = "active"
            active = dict(next_state.get("active", {})) if isinstance(next_state.get("active"), dict) else {}
            execplans = list(active.get("execplans", [])) if isinstance(active.get("execplans"), list) else []
            execplans.append(promoted_item)
            active["execplans"] = execplans
            next_state["active"] = active
            next_state["work_items"] = next_items
            return next_state

    roadmap = state.get("roadmap")
    if isinstance(roadmap, dict):
        next_roadmap = dict(roadmap)
        promoted_item = None
        for bucket in ("lanes", "candidates"):
            raw_items = next_roadmap.get(bucket, [])
            if not isinstance(raw_items, list):
                continue
            kept_items: list[Any] = []
            for raw in raw_items:
                if not isinstance(raw, dict) or str(raw.get("id", "")) != item_id:
                    kept_items.append(raw)
                    continue
                promoted_item = dict(raw)
            if promoted_item is not None:
                next_roadmap[bucket] = kept_items
                break
        if promoted_item is not None:
            for key in ("next_action", "next action", "done_when", "done when", "promotion_signal", "promotion signal"):
                promoted_item.pop(key, None)
            promoted_item["maturity"] = "active"
            promoted_item["status"] = "active"
            promoted_item.pop("type", None)
            promoted_item.pop("surface", None)
            surface = updated_fields.get("surface", "").strip()
            if surface:
                promoted_item["path"] = surface
            active = dict(next_state.get("active", {})) if isinstance(next_state.get("active"), dict) else {}
            execplans = list(active.get("execplans", [])) if isinstance(active.get("execplans"), list) else []
            execplans.append(promoted_item)
            active["execplans"] = execplans
            next_state["active"] = active
            next_state["roadmap"] = next_roadmap
            return next_state

    active = state.get("active")
    if isinstance(active, dict) and isinstance(active.get("execplans"), list):
        next_execplans: list[Any] = []
        changed = False
        for raw in active["execplans"]:
            if not isinstance(raw, dict) or str(raw.get("id", "")) != item_id:
                next_execplans.append(raw)
                continue
            next_execplans.append(_updated_compact_state_item(raw, updated_fields, mark_active=True))
            changed = True
        if changed:
            next_active = dict(active)
            next_active["execplans"] = next_execplans
            next_state["active"] = next_active
            return next_state

    todo = state.get("todo")
    if not isinstance(todo, dict):
        return None

    next_todo = dict(todo)
    for bucket in ("active_items", "queued_items"):
        raw_items = todo.get(bucket, [])
        if not isinstance(raw_items, list):
            continue
        next_items: list[Any] = []
        changed = False
        for raw in raw_items:
            if not isinstance(raw, dict) or str(raw.get("id", "")) != item_id:
                next_items.append(raw)
                continue

            next_item = _updated_compact_state_item(raw, updated_fields, mark_active=bucket == "active_items")
            next_items.append(next_item)
            changed = True

        if changed:
            next_todo[bucket] = next_items
            next_state["todo"] = next_todo
            return next_state

    return None


def _updated_compact_state_item(
    raw: dict[str, Any],
    updated_fields: dict[str, str],
    *,
    mark_active: bool = False,
) -> dict[str, Any]:
    next_item = dict(raw)
    for key in ("next_action", "next action", "done_when", "done when"):
        next_item.pop(key, None)
    for key, value in updated_fields.items():
        compact_key = key.replace(" ", "_")
        if value:
            next_item[compact_key] = value
        else:
            next_item.pop(compact_key, None)
    if mark_active:
        next_item["maturity"] = "active"
        next_item["status"] = "active"
    return next_item


def _rewrite_todo_item(lines: list[str], item: TodoItem, updated_fields: dict[str, str]) -> list[str]:
    ordered_keys = ["id", "status", "surface", "why now", "next action", "done when"]
    for key in item.field_order:
        if key not in ordered_keys:
            ordered_keys.append(key)

    block_lines: list[str] = []
    for key in ordered_keys:
        value = updated_fields.get(key)
        if not value:
            continue
        prefix = "- " if key == "id" else "  "
        label = "ID" if key == "id" else key.title()
        block_lines.append(f"{prefix}{label}: {value}")
    return lines[: item.start] + block_lines + lines[item.end :]


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "new-plan"


def _title_from_slug(slug: str) -> str:
    return " ".join(token.capitalize() for token in slug.split("-"))


def _normalize_status(status: str) -> str:
    lowered = status.strip().lower()
    if lowered in {"in-progress", "active", "ongoing", "current"}:
        return "in-progress"
    if lowered in {"done", "completed", "closed"}:
        return "completed"
    return "planned"


def _execplan_profile_record(*, task_shape: str) -> dict[str, Any]:
    task_shapes = {
        "bounded": [
            "intent_continuity",
            "intent_interpretation",
            "execution_bounds",
            "stop_conditions",
            "context_budget",
            "delegated_judgment",
            "post_decomposition_delegation",
        ],
        "lane": [
            "intent_continuity",
            "required_continuation",
            "iterative_follow_through",
            "intent_interpretation",
            "execution_bounds",
            "stop_conditions",
            "context_budget",
            "delegated_judgment",
            "post_decomposition_delegation",
        ],
        "delegation": [
            "intent_interpretation",
            "execution_bounds",
            "stop_conditions",
            "context_budget",
            "delegated_judgment",
            "post_decomposition_delegation",
            "required_tools",
        ],
        "high-assurance": [
            "adaptive_assurance",
            "traceability_refs",
            "control_gates",
            "implementation_blockers",
            "test_data_policy",
            "layer_scaffold",
            "architecture_decision_promotion",
            "threat_failure_aids",
        ],
        "closeout": [
            "execution_run",
            "finished_run_review",
            "delegation_outcome_feedback",
            "proof_report",
            "intent_satisfaction",
            "closure_check",
            "generated_closeout",
            "memory_learning_capture",
            "durable_residue",
            "task_intent_promotion",
            "execution_summary",
            "improvement_signal_review",
            "closeout_distillation",
        ],
    }
    optional_sections = task_shapes.get(task_shape, task_shapes["bounded"])
    return {
        "schema": "execplan-profile/v1",
        "task_shape": task_shape,
        "required_core": [
            "kind",
            "title",
            "canonical_core",
            "goal",
            "non_goals",
            "active_milestone",
            "validation_commands",
            "completion_criteria",
        ],
        "optional_sections": optional_sections,
        "projection_rule": (
            "canonical_core is authoritative for intent, scope, next action, proof, continuation, and closeout; "
            "legacy fields remain compatibility projections."
        ),
    }


def _execplan_task_shape_from_fields(fields: Mapping[str, Any] | None) -> str:
    fields = fields or {}
    normalized_keys = {str(key).strip().lower().replace(" ", "_").replace("-", "_") for key in fields}
    if any(key in normalized_keys for key in ("adaptive_assurance", "traceability_refs", "control_gates", "implementation_blockers")):
        return "high-assurance"
    if any(key in normalized_keys for key in ("owner_role", "review_role", "handoff_ready", "required_tools")):
        return "delegation"
    if any(key in normalized_keys for key in ("promotion_signal", "suggested_first_slice", "outcome")):
        return "lane"
    return "bounded"


def _build_execplan_record_from_todo_item(
    *,
    title: str,
    item_id: str,
    status: str,
    why_now: str,
    next_action: str,
    done_when: str,
    source_fields: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    goal = why_now or f"Complete the bounded work for TODO item `{item_id}`."
    immediate = next_action or "Fill the execution contract and begin the first bounded implementation step."
    completion = done_when or f"TODO item `{item_id}` is implemented, validated, and can leave the active queue."
    proof_expectations = ["Fill in the narrowest command that proves the promoted work."]
    touched_scope = ["Fill in the concrete files before implementation starts."]
    blocked = "none" if status != "completed" else "n/a"
    ready = "ready" if status != "completed" else "false"
    return {
        "kind": EXECPLAN_RECORD_KIND,
        "title": title,
        "execplan_profile": _execplan_profile_record(task_shape=_execplan_task_shape_from_fields(source_fields)),
        "canonical_core": {
            "requested_outcome": goal,
            "hard_constraints": "Keep scope bounded to the promoted TODO item and its stated touched paths.",
            "agent_may_decide": "Bounded decomposition, touched-path narrowing, validation tightening, and plan-local residue routing.",
            "escalate_when": "A better-looking fix changes the requested outcome, owned surface, time horizon, or meaningful validation story.",
            "next_action": immediate,
            "proof_expectations": proof_expectations,
            "touched_scope": touched_scope,
            "completion_criteria": [completion],
            "continuation_owner": "none",
            "closeout_decision": "pending",
        },
        "goal": [goal],
        "non_goals": ["Leave adjacent backlog or follow-on work out of this plan."],
        "machine_readable_contract": {
            "intent": {
                "outcome": goal,
                "constraints": "Keep scope bounded to the promoted TODO item and its stated touched paths.",
                "latitude": "Bounded decomposition, touched-path narrowing, validation tightening, and plan-local residue routing.",
                "escalation": "Escalate when a better-looking fix changes the requested outcome, owned surface, time horizon, or meaningful validation story.",
            },
            "execution": {
                "milestone": item_id,
                "status": status,
                "next_step": immediate,
                "proof": proof_expectations[0],
            },
            "scope": {
                "touched": touched_scope,
                "invariants": ["Preserve the planning contract and keep the work bounded to this plan."],
            },
        },
        "intent_continuity": {
            "larger intended outcome": goal,
            "this slice completes the larger intended outcome": "yes",
            "continuation surface": "none",
        },
        "required_continuation": {
            "required follow-on for the larger intended outcome": "no",
            "owner surface": "none",
            "activation trigger": "none",
        },
        "iterative_follow_through": {
            "what this slice enabled": "none yet",
            "intentionally deferred": "none",
            "discovered implications": "none yet",
            "proof achieved now": "pending",
            "validation still needed": "current milestone validation remains pending",
            "next likely slice": "continue the current milestone until the completion criteria are met",
        },
        "intent_interpretation": {
            "literal request": title,
            "inferred intended outcome": goal,
            "chosen concrete what": immediate,
            "interpretation distance": "low",
            "review guidance": "Confirm the scaffolded plan still matches the promoted item before broad implementation.",
        },
        "execution_bounds": {
            "allowed paths": "Fill in the concrete write scope before implementation starts.",
            "max changed files": "Fill in an expected upper bound before implementation starts.",
            "required validation commands": "Fill in the narrowest command that proves the promoted work.",
            "ask-before-refactor threshold": "Ask before broadening beyond the promoted item.",
            "stop before touching": "Unrelated backlog, adjacent modules, or canonical contracts not named by this plan.",
        },
        "stop_conditions": {
            "stop when": "The work no longer matches the promoted item or its completion criteria.",
            "escalate when boundary reached": "A correct fix requires changing the requested outcome or ownership boundary.",
            "escalate on scope drift": "Implementation needs files outside the filled execution bounds.",
            "escalate on proof failure": "The selected proof cannot demonstrate the completion criteria.",
        },
        "context_budget": {
            "live working set": "This execplan, the promoted item, and the narrow files needed for the current implementation step.",
            "recoverable later": "Repo background, historical reviews, and deferred backlog unless compact outputs point there.",
            "externalize before shift": "Update execution_run, proof_report, finished_run_review, and closeout_distillation before pausing.",
            "pre-work config pull": "Use compact config/startup/summary outputs before opening raw planning or routing files.",
            "pre-work memory pull": "Route to the narrowest relevant memory only when the task needs durable repo knowledge.",
            "tiny resumability note": immediate,
            "context-shift triggers": "Proof failure, scope drift, interruption, handoff, or closeout.",
        },
        "delegated_judgment": {
            "requested outcome": goal,
            "hard constraints": "Keep scope bounded to the promoted TODO item and its stated touched paths.",
            "agent may decide locally": "Bounded decomposition, touched-path narrowing, validation tightening, and plan-local residue routing.",
            "escalate when": "A better-looking fix changes the requested outcome, owned surface, time horizon, or meaningful validation story.",
        },
        "post_decomposition_delegation": {
            "status": "pending",
            "decision rule": "After this slice is bounded, decide whether direct work, read-only exploration, implementation handoff, validation handoff, or stronger review improves quality or saves tokens safely.",
            "route candidates": "keep-local|delegate-exploration|delegate-implementation|delegate-validation|escalate-review|no-safe-route",
            "required evidence": "slice id, route, reason, quality risk, token-saving class, read-first refs, write scope, proof burden, stop conditions, and return contract",
        },
        "system_intent_alignment": {
            "relevant system intent": "Preserve the larger intended outcome separately from this bounded slice.",
            "slice shaping bias": "Keep the slice bounded while carrying any larger follow-on through explicit continuation fields.",
            "broader-lane validation question": "Did this slice advance the declared larger outcome, or only complete the local task?",
            "intent evidence source": ".agentic-workspace/docs/system-intent-contract.md",
        },
        "references": [],
        "active_milestone": {
            "id": item_id,
            "status": status,
            "scope": "Keep this execution thread bounded to the promoted TODO item.",
            "ready": ready,
            "blocked": blocked,
            "optional_deps": "none",
        },
        "immediate_next_action": [immediate],
        "blockers": ["None."],
        "touched_paths": touched_scope,
        "invariants": ["Preserve the planning contract and keep the work bounded to this plan."],
        "validation_commands": proof_expectations,
        "required_tools": ["None."],
        "completion_criteria": [completion],
        "execution_run": {
            "run status": "not-run-yet",
            "executor": "",
            "handoff source": "agentic-planning promote-to-plan",
            "what happened": "execution has not started",
            "scope touched": "none yet",
            "changed surfaces": "none yet; execution has not changed files",
            "validations run": "pending",
            "result for continuation": "continue from this scaffolded execplan",
            "next step": immediate,
        },
        "finished_run_review": {
            "review status": "pending",
            "scope respected": "pending",
            "proof status": "pending",
            "intent served": "pending",
            "config compliance": "pending",
            "misinterpretation risk": "pending",
            "follow-on decision": "pending",
        },
        "delegation_outcome_feedback": {
            "route chosen": "pending",
            "route skipped reason": "pending",
            "expected savings": "pending",
            "actual friction": "pending",
            "proof result": "pending",
            "quality concern": "pending",
            "decomposition adjustment": "pending",
        },
        "proof_report": {
            "validation proof": "pending",
            "proof achieved now": "pending",
            'evidence for "proof achieved" state': "",
        },
        "intent_satisfaction": {
            "original intent": goal,
            "was original intent fully satisfied?": "pending",
            "evidence of intent satisfaction": "",
            "unsolved intent passed to": "none yet",
        },
        "execution_summary": {
            "outcome delivered": "not completed yet",
            "validation confirmed": "pending",
            "follow-on routed to": "none yet",
            "post-work posterity capture": "pending",
            "knowledge promoted (Memory/Docs/Config)": "none",
            "resume from": "current milestone",
        },
        "durable_residue": {
            "status": "none",
            "learned constraint": "none yet",
            "motivation worth preserving": "none yet",
            "canonical owner now": "none",
            "promotion trigger": "none",
            "retention after promotion": "retain",
        },
        "task_intent_promotion": {
            "decision": "pending",
            "accepted values": ("do-not-promote|memory|subsystem-intent|system-intent|refine-existing-intent|supersede-existing-intent"),
            "evidence source": "",
            "target scope": "",
            "proposed durable intent": "",
            "confidence": "low",
            "needs review": True,
            "owner surface": "",
        },
        "closure_check": {
            "slice status": "pending",
            "larger-intent status": "pending",
            "closure decision": "pending",
            "accepted values": ARCHIVE_CLOSEOUT_VALUE_HINT,
            "why this decision is honest": "",
            "evidence carried forward": "",
            "reopen trigger": "",
        },
        "improvement_signal_review": {
            "status": "not_checked",
            "accepted statuses": "not_checked|signals_routed|signals_fixed|signals_dismissed|no_signal_found",
            "guidance": (
                "At closeout, report AW smoothness/helpfulness gaps, better-way signals, unused-feature reflections, "
                "and places AW could help more. Route each concrete signal to exactly one owner class unless explicitly "
                "split, or mark no_signal_found after checking."
            ),
            "source": "operating_posture",
            "owner classes": ["issue", "Memory", "Planning", "docs/checks/contracts", "direct fix", "dismissed with reason"],
            "ordinary output cap": 3,
            "signals found": [],
            "signals fixed": [],
            "signals routed": [],
            "signals dismissed": [],
            "next owner": "",
        },
        "closeout_distillation": {
            "buckets": {
                "discard": [],
                "continuation": [],
                "memory": [],
                "config_check": [],
                "docs": [],
                "issue_follow_up": [],
            }
        },
        "drift_log": [f"{date.today().isoformat()}: Promoted from TODO direct-task shape into an execplan."],
    }


def _surface_execplan_reference(surface_value: str) -> str | None:
    inline_path_match = re.search(r".agentic-workspace/planning/execplans/[A-Za-z0-9._/\-]+\.(?:md|plan\.json)", surface_value)
    if inline_path_match:
        return inline_path_match.group(0)
    markdown_target = re.search(r"\]\(([^)]+)\)", surface_value)
    if markdown_target:
        target_match = re.search(r".agentic-workspace/planning/execplans/[A-Za-z0-9._/\-]+\.(?:md|plan\.json)", markdown_target.group(1))
        if target_match:
            return target_match.group(0)
    return None


def _active_execplan_reference(raw: dict[str, Any]) -> str:
    value = str(raw.get("path") or raw.get("surface") or raw.get("execplan") or raw.get("plan") or "")
    return _surface_execplan_reference(value) or value.strip()


def _resolve_execplan_path(target_root: Path, plan: str) -> Path | None:
    candidate = Path(plan)
    if candidate.is_absolute():
        return candidate
    if candidate.suffix == ".md" and (target_root / candidate).exists():
        return (target_root / candidate).resolve()
    if candidate.name.endswith(".plan.json") and (target_root / candidate).exists():
        return (target_root / candidate).resolve()
    # When a .md surface is referenced but only the .plan.json sibling exists
    if candidate.suffix == ".md":
        json_sibling = (target_root / candidate).with_suffix(".plan.json")
        if json_sibling.exists():
            return json_sibling.resolve()
    # Try .md first for backwards compatibility
    normalized_md = plan if plan.endswith(".md") else f"{plan}.md"
    direct_md = target_root / ".agentic-workspace" / "planning" / "execplans" / normalized_md
    if direct_md.exists():
        return direct_md.resolve()
    archive_md = target_root / ".agentic-workspace" / "planning" / "execplans" / "archive" / normalized_md
    if archive_md.exists():
        return archive_md.resolve()
    # Try .plan.json (canonical record without derived .md)
    normalized_json = plan if plan.endswith(".plan.json") else f"{plan}.plan.json"
    direct_json = target_root / ".agentic-workspace" / "planning" / "execplans" / normalized_json
    if direct_json.exists():
        return direct_json.resolve()
    archive_json = target_root / ".agentic-workspace" / "planning" / "execplans" / "archive" / normalized_json
    if archive_json.exists():
        return archive_json.resolve()
    return None


def _execplan_status(path: Path) -> str:
    record = _load_execplan_record(path)
    milestone = _record_section_dict(record, "active_milestone")
    if milestone is not None:
        return milestone.get("status", "").strip().lower()
    lines = _read_lines(path)
    for line in _section_lines(lines, "Active Milestone"):
        match = re.match(r"^\s*-\s*Status\s*:\s*(.*)\s*$", line, re.IGNORECASE)
        if match:
            return match.group(1).strip().lower()
    return ""


def _execplan_item_id(path: Path) -> str:
    record = _load_execplan_record(path)
    milestone = _record_section_dict(record, "active_milestone")
    if milestone is not None:
        return milestone.get("id", "").strip().lower()
    lines = _read_lines(path)
    for line in _section_lines(lines, "Active Milestone"):
        match = re.match(r"^\s*-\s*ID\s*:\s*(.*)\s*$", line, re.IGNORECASE)
        if match:
            return match.group(1).strip().lower()
    return ""


def _execplan_intent_continuity(path: Path) -> dict[str, str]:
    record = _record_section_dict(_load_execplan_record(path), "intent_continuity")
    if record is not None:
        return record
    lines = _read_lines(path)
    return _extract_kv_fields(_section_lines(lines, "Intent Continuity"))


def _execplan_required_continuation(path: Path) -> dict[str, str]:
    record = _record_section_dict(_load_execplan_record(path), "required_continuation")
    if record is not None:
        return record
    lines = _read_lines(path)
    return _extract_kv_fields(_section_lines(lines, "Required Continuation"))


def _execplan_iterative_follow_through(path: Path) -> dict[str, str]:
    record = _record_section_dict(_load_execplan_record(path), "iterative_follow_through")
    if record is not None:
        return record
    lines = _read_lines(path)
    return _extract_kv_fields(_section_lines(lines, "Iterative Follow-Through"))


def _execplan_delegated_judgment(path: Path) -> dict[str, str]:
    record = _record_section_dict(_load_execplan_record(path), "delegated_judgment")
    if record is not None:
        return record
    lines = _read_lines(path)
    return _extract_kv_fields(_section_lines(lines, "Delegated Judgment"))


def _execplan_intent_interpretation(path: Path) -> dict[str, str]:
    record = _record_section_dict(_load_execplan_record(path), "intent_interpretation")
    if record is not None:
        return record
    lines = _read_lines(path)
    return _extract_kv_fields(_section_lines(lines, "Intent Interpretation"))


def _execplan_execution_bounds(path: Path) -> dict[str, str]:
    record = _record_section_dict(_load_execplan_record(path), "execution_bounds")
    if record is not None:
        return record
    lines = _read_lines(path)
    return _extract_kv_fields(_section_lines(lines, "Execution Bounds"))


def _execplan_stop_conditions(path: Path) -> dict[str, str]:
    record = _record_section_dict(_load_execplan_record(path), "stop_conditions")
    if record is not None:
        return record
    lines = _read_lines(path)
    return _extract_kv_fields(_section_lines(lines, "Stop Conditions"))


def _execplan_context_budget(path: Path) -> dict[str, str]:
    record = _record_section_dict(_load_execplan_record(path), "context_budget")
    if record is not None:
        return record
    lines = _read_lines(path)
    return _extract_kv_fields(_section_lines(lines, "Context Budget"))


def _execplan_post_decomposition_delegation(path: Path) -> dict[str, str]:
    record = _record_section_dict(_load_execplan_record(path), "post_decomposition_delegation")
    if record is not None:
        return record
    lines = _read_lines(path)
    return _extract_kv_fields(_section_lines(lines, "Post-Decomposition Delegation"))


def _execplan_prep_only_contract(path: Path) -> dict[str, Any]:
    record = _load_execplan_record(path) or {}
    machine_contract = record.get("machine_readable_contract", {})
    if not isinstance(machine_contract, dict):
        return {}
    planning_mode = machine_contract.get("planning_mode", {})
    if not isinstance(planning_mode, dict) or planning_mode.get("prep_only") is not True:
        return {}
    forbidden = planning_mode.get("forbidden_outputs", [])
    if not isinstance(forbidden, list):
        forbidden = []
    return {
        "is_prep_only": True,
        "halt_after_summary": planning_mode.get("halt_after_summary") is True,
        "halt_instruction": str(planning_mode.get("halt_instruction", "")).strip(),
        "forbidden_outputs": [str(item).strip() for item in forbidden if str(item).strip()],
    }


def _execplan_raw_dict(path: Path, key: str) -> dict[str, Any]:
    value = _record_section_value(_load_execplan_record(path), key)
    return value if isinstance(value, dict) else {}


def _execplan_raw_list(path: Path, key: str) -> list[Any]:
    value = _record_section_value(_load_execplan_record(path), key)
    return value if isinstance(value, list) else []


def _execplan_references(path: Path) -> list[dict[str, str]]:
    record = _record_section_references(_load_execplan_record(path), "references")
    if record is not None:
        return record
    return _extract_reference_section(path, "References")


def _execplan_execution_run(path: Path) -> dict[str, str]:
    record = _record_section_dict(_load_execplan_record(path), "execution_run")
    if record is not None:
        return record
    lines = _read_lines(path)
    return _extract_kv_fields(_section_lines(lines, "Execution Run"))


def _execplan_finished_run_review(path: Path) -> dict[str, str]:
    record = _record_section_dict(_load_execplan_record(path), "finished_run_review")
    if record is not None:
        return record
    lines = _read_lines(path)
    return _extract_kv_fields(_section_lines(lines, "Finished-Run Review"))


def _execplan_delegation_outcome_feedback(path: Path) -> dict[str, str]:
    record = _record_section_dict(_load_execplan_record(path), "delegation_outcome_feedback")
    if record is not None:
        return record
    lines = _read_lines(path)
    return _extract_kv_fields(_section_lines(lines, "Delegation Outcome Feedback"))


def _execplan_active_milestone(path: Path) -> dict[str, str]:
    record = _record_section_dict(_load_execplan_record(path), "active_milestone")
    if record is not None:
        return record
    lines = _read_lines(path)
    return _extract_kv_fields(_section_lines(lines, "Active Milestone"))


def _execplan_execution_summary(path: Path) -> dict[str, str]:
    record = _record_section_dict(_load_execplan_record(path), "execution_summary")
    if record is not None:
        return record
    lines = _read_lines(path)
    return _extract_kv_fields(_section_lines(lines, "Execution Summary"))


def _execplan_proof_report(path: Path) -> dict[str, str]:
    record = _record_section_dict(_load_execplan_record(path), "proof_report")
    if record is not None:
        return record
    lines = _read_lines(path)
    return _extract_kv_fields(_section_lines(lines, "Proof Report"))


def _execplan_intent_satisfaction(path: Path) -> dict[str, str]:
    record = _record_section_dict(_load_execplan_record(path), "intent_satisfaction")
    if record is not None:
        return record
    lines = _read_lines(path)
    return _extract_kv_fields(_section_lines(lines, "Intent Satisfaction"))


def _execplan_system_intent_alignment(path: Path) -> dict[str, str]:
    record = _record_section_dict(_load_execplan_record(path), "system_intent_alignment")
    if record is not None:
        return record
    lines = _read_lines(path)
    return _extract_kv_fields(_section_lines(lines, "System Intent Alignment"))


def _execplan_closure_check(path: Path) -> dict[str, str]:
    record = _record_section_dict(_load_execplan_record(path), "closure_check")
    if record is not None:
        return record
    lines = _read_lines(path)
    return _extract_kv_fields(_section_lines(lines, "Closure Check"))


def _execplan_title(path: Path) -> str:
    record = _load_execplan_record(path)
    if isinstance(record, dict):
        title = str(record.get("title", "")).strip()
        if title:
            return title
    for line in _read_lines(path):
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("-", " ").title()


def _execplan_issue_refs(path: Path) -> set[str]:
    role_summary = _execplan_issue_reference_roles(path)
    if role_summary["status"] == "present":
        return set(role_summary["closure_refs"])
    return _execplan_prose_issue_refs(path)


def _execplan_prose_issue_refs(path: Path) -> set[str]:
    tokens = set(re.findall(r"(?<![A-Za-z0-9_])(?:#[0-9]+|[A-Z][A-Z0-9]+-\d+)(?![A-Za-z0-9_])", path.read_text(encoding="utf-8")))
    return {token.strip() for token in tokens if token.strip()}


def _normalize_reference_role_key(role: str) -> str:
    normalized = role.strip().lower().replace("-", "_").replace(" ", "_")
    return normalized or PLANNING_REFERENCE_ROLE_DEFAULT


def _reference_issue_token(target: str) -> str:
    stripped = target.strip()
    if not stripped:
        return ""
    direct = re.fullmatch(r"(#[0-9]+|[A-Z][A-Z0-9]+-\d+)", stripped)
    if direct:
        return direct.group(1)
    issue_url = re.search(r"/issues/([0-9]+)(?:\b|/|$)", stripped)
    if issue_url:
        return f"#{issue_url.group(1)}"
    tokens = re.findall(r"(?<![A-Za-z0-9_])(?:#[0-9]+|[A-Z][A-Z0-9]+-\d+)(?![A-Za-z0-9_])", stripped)
    return tokens[0].strip() if len(tokens) == 1 else ""


def _execplan_issue_reference_roles(path: Path) -> dict[str, Any]:
    references = _execplan_references(path)
    by_role: dict[str, list[str]] = {}
    labels_by_ref: dict[str, str] = {}
    for reference in references:
        token = _reference_issue_token(str(reference.get("target", "")))
        if not token:
            continue
        role = _normalize_reference_role_key(str(reference.get("role", "")))
        by_role.setdefault(role, [])
        if token not in by_role[role]:
            by_role[role].append(token)
        label = str(reference.get("label", "")).strip()
        if label:
            labels_by_ref[token] = label
    closure_refs = sorted({ref for role, refs in by_role.items() if role in PLANNING_REFERENCE_CLOSURE_ROLES for ref in refs})
    non_closure_refs = sorted({ref for role, refs in by_role.items() if role not in PLANNING_REFERENCE_CLOSURE_ROLES for ref in refs})
    return {
        "status": "present" if by_role else "absent",
        "closure_refs": closure_refs,
        "non_closure_refs": non_closure_refs,
        "by_role": {role: sorted(refs) for role, refs in sorted(by_role.items())},
        "labels_by_ref": labels_by_ref,
        "rule": ("Explicit issue-reference roles override prose scanning; only closure roles are treated as finished-work closure claims."),
    }


def _execplan_validation_commands(path: Path) -> list[str]:
    record = _record_section_list(_load_execplan_record(path), "validation_commands")
    if record is not None:
        return record
    return _extract_section_bullets(path, "Validation Commands")


def _execplan_needs_reference_sweep(path: Path) -> bool:
    record = _load_execplan_record(path)
    if isinstance(record, dict):
        relevant_text: list[str] = []
        relevant_text.extend(record.get("goal", []))
        active_milestone = record.get("active_milestone", {})
        relevant_text.append(active_milestone.get("scope", ""))
        relevant_text.extend(record.get("touched_paths", []))
        execution_summary = record.get("execution_summary", {})
        relevant_text.append(execution_summary.get("outcome delivered", ""))
        text = "\n".join(relevant_text).lower()
    else:
        lines = _read_lines(path)
        relevant = [
            *_section_lines(lines, "Goal"),
            *_section_lines(lines, "Active Milestone"),
            *_section_lines(lines, "Touched Paths"),
            *_section_lines(lines, "Execution Summary"),
        ]
        text = "\n".join(relevant).lower()
    return any(token in text for token in ("rename", "renamed", "refactor", "refactored", "move", "moved", "retire", "retired"))


def _validation_has_reference_sweep(commands: list[str]) -> bool:
    lowered = "\n".join(command.lower() for command in commands)
    return any(token in lowered for token in ("rg ", "ripgrep", "grep "))


def _close_state_active_execplan_for_archive(
    *,
    target_root: Path,
    plan_path: Path,
    archived_record_relative: str,
    durable_residue: dict[str, str],
    closure_decision: str,
) -> dict[str, Any]:
    del archived_record_relative, durable_residue, closure_decision
    state = _read_state_from_toml(target_root)
    if not state:
        return {"changed": False, "state": None, "details": []}

    active = state.get("active")
    if not isinstance(active, dict) or not isinstance(active.get("execplans"), list):
        return {"changed": False, "state": None, "details": []}

    relative = plan_path.relative_to(target_root).as_posix()
    kept_execplans: list[Any] = []
    removed_ids: set[str] = set()
    removed_any = False
    for raw in active["execplans"]:
        if not isinstance(raw, dict):
            kept_execplans.append(raw)
            continue
        item_surface = _active_execplan_reference(raw)
        if item_surface != relative:
            kept_execplans.append(raw)
            continue
        removed_any = True
        raw_id = str(raw.get("id", "")).strip()
        if raw_id:
            removed_ids.add(raw_id)

    if not removed_any:
        return {"changed": False, "state": None, "details": []}

    next_state = dict(state)
    next_active = dict(active)
    next_active["execplans"] = kept_execplans
    next_state["active"] = next_active
    if removed_ids and isinstance(next_state.get("work_items"), list):
        next_state["work_items"] = [
            item for item in next_state["work_items"] if not (isinstance(item, dict) and str(item.get("id", "")) in removed_ids)
        ]
    if isinstance(next_state.get("todo"), dict):
        todo_state = dict(next_state["todo"])
        for bucket in ("active_items", "queued_items"):
            raw_items = todo_state.get(bucket, [])
            if not isinstance(raw_items, list):
                continue
            todo_state[bucket] = [
                item
                for item in raw_items
                if not (isinstance(item, dict) and (_active_execplan_reference(item) == relative or str(item.get("id", "")) in removed_ids))
            ]
        next_state["todo"] = todo_state
    details = [f"remove active execplan '{item_id}' from live planning state after archive" for item_id in sorted(removed_ids)]
    if not details:
        details = [f"remove active execplan reference to {relative} from live planning state after archive"]
    return {"changed": True, "state": next_state, "details": details}


def _todo_referencing_items(todo_path: Path, plan_path: Path, target_root: Path) -> list[TodoItem]:
    if todo_path.name == "state.toml":
        state = _read_state_from_toml(target_root)
        if state:
            relative = plan_path.relative_to(target_root).as_posix()
            matches: list[TodoItem] = []
            active = state.get("active", {})
            if isinstance(active, dict):
                for raw in active.get("execplans", []):
                    if not isinstance(raw, dict):
                        continue
                    item_surface = _active_execplan_reference(raw)
                    if relative != item_surface:
                        continue
                    fields = {str(key): str(value) for key, value in raw.items()}
                    matches.append(TodoItem(fields=fields, field_order=list(fields.keys()), start=0, end=0))
            if isinstance(state.get("todo"), dict):
                for bucket in ("active_items", "queued_items"):
                    for raw in state.get("todo", {}).get(bucket, []):
                        if not isinstance(raw, dict):
                            continue
                        if relative != _active_execplan_reference(raw):
                            continue
                        fields = {str(key): str(value) for key, value in raw.items()}
                        matches.append(TodoItem(fields=fields, field_order=list(fields.keys()), start=0, end=0))
            return matches
    _, items = _read_todo_items(todo_path)
    relative = plan_path.relative_to(target_root).as_posix()
    matches: list[TodoItem] = []
    for item in items:
        if _surface_execplan_reference(item.fields.get("surface", "")) == relative:
            matches.append(item)
    return matches


def _remove_todo_items(todo_path: Path, items_to_remove: list[TodoItem]) -> list[str]:
    if todo_path.name == "state.toml":
        target_root = todo_path.parents[2]
        state = _read_state_from_toml(target_root)
        if state:
            item_ids = {item.item_id for item in items_to_remove if item.item_id}
            if not item_ids:
                return _read_lines(todo_path)
            active = state.get("active")
            if isinstance(active, dict) and isinstance(active.get("execplans"), list):
                active["execplans"] = [
                    item
                    for item in active["execplans"]
                    if not (
                        (isinstance(item, dict) and str(item.get("id", "")) in item_ids)
                        or (isinstance(item, str) and any(item_id in item for item_id in item_ids))
                    )
                ]
            raw_work_items = state.get("work_items", [])
            if isinstance(raw_work_items, list):
                state["work_items"] = [
                    item for item in raw_work_items if not (isinstance(item, dict) and str(item.get("id", "")) in item_ids)
                ]
            if isinstance(state.get("todo"), dict):
                todo_state = state.setdefault("todo", {})
                for bucket in ("active_items", "queued_items"):
                    raw_items = todo_state.get(bucket, [])
                    if not isinstance(raw_items, list):
                        continue
                    todo_state[bucket] = [
                        item for item in raw_items if not (isinstance(item, dict) and str(item.get("id", "")) in item_ids)
                    ]
            return _state_to_toml_lines(state)
    lines, _ = _read_todo_items(todo_path)
    indexes_to_remove: set[int] = set()
    for item in items_to_remove:
        indexes_to_remove.update(range(item.start, item.end))
        if item.end < len(lines) and lines[item.end].strip() == "":
            indexes_to_remove.add(item.end)

    filtered_lines = [line for index, line in enumerate(lines) if index not in indexes_to_remove]
    while filtered_lines and filtered_lines[-1] == "":
        filtered_lines.pop()
    restored = _restore_todo_empty_state(filtered_lines)
    if not _read_todo_items_from_lines(restored):
        restored = _restore_todo_default_action(restored)
    return restored


def _restore_todo_empty_state(lines: list[str]) -> list[str]:
    for heading in ("Now", "Next"):
        lines = _restore_todo_empty_state_for_heading(lines, heading)
    return lines


def _restore_todo_default_action(lines: list[str]) -> list[str]:
    heading_index = next((index for index, line in enumerate(lines) if line.strip().lower() == "## action"), -1)
    if heading_index < 0:
        return lines
    section_end = len(lines)
    for index in range(heading_index + 1, len(lines)):
        if lines[index].startswith("## "):
            section_end = index
            break
    replacement = [
        "",
        "- Promote the next bounded candidate only when fresh repeated friction or explicit maintainer choice justifies activation.",
    ]
    return lines[: heading_index + 1] + replacement + lines[section_end:]


def _restore_todo_empty_state_for_heading(lines: list[str], heading: str) -> list[str]:
    heading_index = next((index for index, line in enumerate(lines) if line.strip().lower() == f"## {heading.lower()}"), -1)
    if heading_index < 0:
        return lines
    section_end = len(lines)
    for index in range(heading_index + 1, len(lines)):
        if lines[index].startswith("## "):
            section_end = index
            break

    section_body = lines[heading_index + 1 : section_end]
    if any(line.strip() and line.strip() != TODO_EMPTY_STATE_LINE for line in section_body):
        return lines

    normalized_lines = lines[: heading_index + 1] + ["", TODO_EMPTY_STATE_LINE] + lines[section_end:]
    while len(normalized_lines) > 2 and normalized_lines[-1] == "" and normalized_lines[-2] == "":
        normalized_lines.pop()
    return normalized_lines


def _cleanup_compact_todo_archive_followup(todo_path: Path, plan_path: Path, target_root: Path) -> dict[str, Any]:
    if not todo_path.exists():
        return {"changed": False, "text": None, "details": []}
    if todo_path.name == "state.toml":
        state_cleanup = _cleanup_state_toml_archive_followup(todo_path, plan_path, target_root)
        if state_cleanup["changed"]:
            return state_cleanup

    lines = _read_lines(todo_path)
    relative = plan_path.relative_to(target_root).as_posix()
    queue_id = _execplan_item_id(plan_path) or plan_path.stem.lower()
    changed = False
    details: list[str] = []

    action_lines, action_removed = _cleanup_todo_action_section(lines, relative)
    if action_removed:
        lines = action_lines
        changed = True
        details.append("remove Action reference to the archived plan")

    now_lines, now_removed = _cleanup_todo_now_section(lines, queue_id)
    if now_removed:
        lines = now_lines
        changed = True
        details.append("remove compact Now item tied to the archived plan")

    if not changed:
        return {"changed": False, "text": None, "details": []}
    lines = _restore_todo_empty_state(lines)
    return {"changed": True, "text": "\n".join(lines).rstrip() + "\n", "details": details}


def _cleanup_state_toml_archive_followup(todo_path: Path, plan_path: Path, target_root: Path) -> dict[str, Any]:
    state = _read_state_from_toml(target_root)
    if not state:
        return {"changed": False, "text": None, "details": []}

    relative = plan_path.relative_to(target_root).as_posix()
    changed = False
    details: list[str] = []
    next_state = dict(state)
    active = next_state.get("active")
    if isinstance(active, dict) and isinstance(active.get("execplans"), list):
        kept_execplans: list[Any] = []
        removed_count = 0
        for raw in active["execplans"]:
            if isinstance(raw, dict):
                matches = _active_execplan_reference(raw) == relative
            else:
                matches = _surface_execplan_reference(str(raw)) == relative or str(raw).strip() == relative
            if matches:
                removed_count += 1
                continue
            kept_execplans.append(raw)
        if removed_count:
            next_active = dict(active)
            next_active["execplans"] = kept_execplans
            next_state["active"] = next_active
            changed = True
            details.append(f"remove {removed_count} active execplan reference(s) to the archived plan")

    for bucket_name in ("work_items",):
        raw_items = next_state.get(bucket_name, [])
        if not isinstance(raw_items, list):
            continue
        kept_items = [item for item in raw_items if not (isinstance(item, dict) and _active_execplan_reference(item) == relative)]
        if len(kept_items) != len(raw_items):
            next_state[bucket_name] = kept_items
            changed = True
            details.append(f"remove {bucket_name} item(s) pointing at the archived plan")

    todo_state = next_state.get("todo")
    if isinstance(todo_state, dict):
        next_todo = dict(todo_state)
        for bucket_name in ("active_items", "queued_items"):
            raw_items = next_todo.get(bucket_name, [])
            if not isinstance(raw_items, list):
                continue
            kept_items = [item for item in raw_items if not (isinstance(item, dict) and _active_execplan_reference(item) == relative)]
            if len(kept_items) != len(raw_items):
                next_todo[bucket_name] = kept_items
                changed = True
                details.append(f"remove todo.{bucket_name} item(s) pointing at the archived plan")
        next_state["todo"] = next_todo

    if not changed:
        return {"changed": False, "text": None, "details": []}
    return {"changed": True, "text": "\n".join(_state_to_toml_lines(next_state)).rstrip() + "\n", "details": details}


def _cleanup_todo_action_section(lines: list[str], relative_plan_path: str) -> tuple[list[str], bool]:
    section = _section_lines(lines, "Action")
    if not section:
        return lines, False
    heading_index = next((index for index, line in enumerate(lines) if line.strip().lower() == "## action"), -1)
    if heading_index < 0:
        return lines, False
    section_start = heading_index + 1
    section_end = section_start + len(section)

    kept_lines: list[str] = []
    removed = False
    for line in section:
        if relative_plan_path in line:
            removed = True
            continue
        kept_lines.append(line)

    if not removed:
        return lines, False
    if not any(line.strip() for line in kept_lines):
        kept_lines = [
            "",
            "- Promote the next bounded candidate only when fresh repeated friction or explicit maintainer choice justifies activation.",
        ]
    return lines[:section_start] + kept_lines + lines[section_end:], True


def _cleanup_todo_now_section(lines: list[str], plan_stem: str) -> tuple[list[str], bool]:
    section = _section_lines(lines, "Now")
    if not section:
        return lines, False
    heading_index = next((index for index, line in enumerate(lines) if line.strip().lower() == "## now"), -1)
    if heading_index < 0:
        return lines, False
    section_start = heading_index + 1
    section_end = section_start + len(section)

    compact_pattern = re.compile(r"^\s*-\s*([a-z0-9._-]+)\s*:\s*(.*)$", re.IGNORECASE)
    kept_lines: list[str] = []
    removed = False
    for line in section:
        match = compact_pattern.match(line)
        if match and match.group(1).strip().lower() == plan_stem:
            removed = True
            continue
        kept_lines.append(line)

    if not removed:
        return lines, False
    return lines[:section_start] + kept_lines + lines[section_end:], True


def _plan_stem_tokens(plan_path: Path) -> list[str]:
    stop_tokens = {"plan", "planning", "lane", "slice", "tranche", "candidate", "native"}
    return [
        token
        for token in re.split(r"[^a-z0-9]+", plan_path.stem.lower())
        if len(token) >= 4 and not token.isdigit() and token not in stop_tokens
    ]


def _label_tokens(value: str | None) -> list[str]:
    if not value:
        return []
    return [token for token in re.split(r"[^a-z0-9]+", value.lower()) if len(token) >= 4 and not token.isdigit()]


def _roadmap_continuation_label(plan_path: Path) -> str | None:
    continuation_surface = _execplan_intent_continuity(plan_path).get("continuation surface", "").strip()
    match = re.search(r"`?roadmap\.md`?\s+candidate(?:\s+lane)?\s+`?([^`]+?)`?$", continuation_surface, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _cleanup_roadmap_archive_followup(roadmap_path: Path, plan_path: Path) -> dict[str, Any]:
    if not roadmap_path.exists():
        return {"changed": False, "text": None, "details": [], "note": None}

    lines = _read_lines(roadmap_path)
    tokens = _plan_stem_tokens(plan_path)
    continuation_label = _roadmap_continuation_label(plan_path)
    details: list[str] = []
    changed = False

    lines, handoff_removed = _cleanup_roadmap_section(
        lines,
        "Active Handoff",
        tokens,
        empty_line="- No active handoff right now.",
        preserve_label=None,
    )
    if handoff_removed:
        changed = True
        details.append("compress Active Handoff residue tied to the archived plan")

    lines, queue_removed = _cleanup_roadmap_section(
        lines,
        "Next Candidate Queue",
        tokens,
        empty_line=None,
        preserve_label=continuation_label,
    )
    if queue_removed:
        changed = True
        details.append("remove archived-plan candidate residue from Next Candidate Queue")

    lines, lane_removed = _cleanup_roadmap_section(
        lines,
        "Candidate Lanes",
        tokens,
        empty_line=None,
        preserve_label=continuation_label,
    )
    if lane_removed:
        changed = True
        details.append("remove archived-plan candidate residue from Candidate Lanes")

    if not changed:
        return {"changed": False, "text": None, "details": [], "note": None}
    return {
        "changed": True,
        "text": "\n".join(lines).rstrip() + "\n",
        "details": details,
        "note": None,
    }


def _cleanup_state_roadmap_followup(target_root: Path, plan_path: Path) -> dict[str, Any]:
    state = _read_state_from_toml(target_root)
    if not state:
        return {"changed": False, "state": None, "details": [], "note": None}

    roadmap = state.get("roadmap")
    if not isinstance(roadmap, dict):
        return {"changed": False, "state": None, "details": [], "note": None}

    tokens = _plan_stem_tokens(plan_path)
    continuation_label = _roadmap_continuation_label(plan_path)
    preserved_tokens = set(_label_tokens(continuation_label))
    changed = False
    details: list[str] = []

    lanes = roadmap.get("lanes", [])
    if isinstance(lanes, list):
        kept_lanes: list[dict[str, Any]] = []
        lane_removed = False
        for lane in lanes:
            if not isinstance(lane, dict):
                kept_lanes.append(lane)
                continue
            lane_identity = " ".join(
                str(value).strip().lower() for value in (lane.get("title", ""), lane.get("id", "")) if str(value).strip()
            )
            if preserved_tokens and all(token in lane_identity for token in preserved_tokens):
                kept_lanes.append(lane)
                continue
            if tokens and all(token in lane_identity for token in tokens):
                lane_removed = True
                continue
            kept_lanes.append(lane)
        if lane_removed:
            roadmap["lanes"] = kept_lanes
            changed = True
            details.append("remove archived-plan candidate residue from roadmap lanes")

    candidates = roadmap.get("candidates", [])
    if isinstance(candidates, list):
        kept_candidates: list[dict[str, Any]] = []
        candidate_removed = False
        for candidate in candidates:
            if not isinstance(candidate, dict):
                kept_candidates.append(candidate)
                continue
            summary = str(candidate.get("summary", "")).strip().lower()
            if preserved_tokens and all(token in summary for token in preserved_tokens):
                kept_candidates.append(candidate)
                continue
            if tokens and all(token in summary for token in tokens):
                candidate_removed = True
                continue
            kept_candidates.append(candidate)
        if candidate_removed:
            roadmap["candidates"] = kept_candidates
            changed = True
            details.append("remove archived-plan candidate residue from roadmap summaries")

    if not changed:
        return {"changed": False, "state": None, "details": [], "note": None}
    return {"changed": True, "state": state, "details": details, "note": None}


def _cleanup_roadmap_section(
    lines: list[str],
    heading: str,
    tokens: list[str],
    *,
    empty_line: str | None,
    preserve_label: str | None,
) -> tuple[list[str], bool]:
    section = _section_lines(lines, heading)
    if not section:
        return lines, False

    start = next((index for index, line in enumerate(lines) if line.strip().lower() == f"## {heading.lower()}"), -1)
    if start < 0:
        return lines, False
    section_start = start + 1
    section_end = section_start + len(section)

    kept_lines: list[str] = []
    removed = False
    preserved_tokens = _label_tokens(preserve_label)
    if heading.lower() == "candidate lanes":
        blocks: list[list[str]] = []
        current_block: list[str] = []
        for line in section:
            if re.match(r"^\s*-\s+", line):
                if current_block:
                    blocks.append(current_block)
                current_block = [line]
            elif current_block:
                current_block.append(line)
            else:
                kept_lines.append(line)
        if current_block:
            blocks.append(current_block)

        for block in blocks:
            lane = _parse_candidate_lane_block(block) or {}
            lane_identity = " ".join(
                value for value in (str(lane.get("title", "")).strip(), str(lane.get("id", "")).strip()) if value
            ).lower()
            if preserved_tokens and all(token in lane_identity for token in preserved_tokens):
                kept_lines.extend(block)
                continue
            if tokens and all(token in lane_identity for token in tokens):
                removed = True
                continue
            kept_lines.extend(block)
    else:
        for line in section:
            if not re.match(r"^\s*-\s+", line):
                kept_lines.append(line)
                continue
            lowered = line.lower()
            if preserved_tokens and all(token in lowered for token in preserved_tokens):
                kept_lines.append(line)
                continue
            if tokens and all(token in lowered for token in tokens):
                removed = True
                continue
            kept_lines.append(line)

    if not removed:
        return lines, False

    replacement = [line for line in kept_lines if line.strip()]
    if empty_line is not None and not any(re.match(r"^\s*-\s+", line) for line in replacement):
        replacement = [empty_line]

    return lines[:section_start] + replacement + lines[section_end:], True


def _read_state_from_toml(target_root: Path) -> dict[str, Any] | None:
    state_path = target_root / PLANNING_STATE_PATH
    if not state_path.exists():
        return None

    try:
        raw = state_path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            raw = raw[3:]
        return tomllib.loads(raw.decode("utf-8"))
    except Exception:
        return None


def _close_item_state_candidates(state: dict[str, Any], *, item_id: str, target_root: Path) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    def add_collection(*, kind: str, bucket: str, path: str, items: Any) -> None:
        if not isinstance(items, list):
            return
        for index, raw in enumerate(items):
            if not isinstance(raw, dict):
                continue
            raw_record = cast(dict[str, Any], raw)
            raw_id = str(raw_record.get("id", "")).strip()
            if not raw_id:
                continue
            match = _close_item_id_match(raw_id, item_id)
            if match is None:
                continue
            candidates.append(
                {
                    "kind": kind,
                    "bucket": bucket,
                    "path": path,
                    "index": index,
                    "id": raw_id,
                    "status": str(raw_record.get("status", "")).strip(),
                    "surface": _active_execplan_reference(raw_record),
                    "match": match,
                    "target_root": target_root,
                }
            )

    todo = state.get("todo")
    if isinstance(todo, dict):
        add_collection(kind="todo", bucket="todo.active_items", path=PLANNING_STATE_PATH.as_posix(), items=todo.get("active_items"))
        add_collection(kind="todo", bucket="todo.queued_items", path=PLANNING_STATE_PATH.as_posix(), items=todo.get("queued_items"))
    roadmap = state.get("roadmap")
    if isinstance(roadmap, dict):
        add_collection(kind="roadmap", bucket="roadmap.lanes", path=PLANNING_STATE_PATH.as_posix(), items=roadmap.get("lanes"))
        add_collection(kind="roadmap", bucket="roadmap.candidates", path=PLANNING_STATE_PATH.as_posix(), items=roadmap.get("candidates"))
    add_collection(kind="work_item", bucket="work_items", path=PLANNING_STATE_PATH.as_posix(), items=state.get("work_items"))
    active = state.get("active")
    if isinstance(active, dict):
        add_collection(
            kind="active_execplan_ref", bucket="active.execplans", path=PLANNING_STATE_PATH.as_posix(), items=active.get("execplans")
        )
    return candidates


def _close_item_execplan_candidates(target_root: Path, *, item_id: str) -> list[dict[str, Any]]:
    execplan_root = target_root / PLANNING_MANAGED_ROOT / "execplans"
    if not execplan_root.exists():
        return []
    candidates: list[dict[str, Any]] = []
    for path in sorted([*execplan_root.glob("*.plan.json"), *execplan_root.glob("*.md")]):
        if path.name in {"README.md", "TEMPLATE.md"}:
            continue
        plan_id = path.name[:-10] if path.name.endswith(".plan.json") else path.stem
        match = _close_item_id_match(plan_id, item_id)
        if match is None:
            continue
        candidates.append(
            {
                "kind": "execplan",
                "bucket": "execplans",
                "path": path.relative_to(target_root).as_posix(),
                "id": plan_id,
                "status": _execplan_status(path),
                "match": match,
                "plan_arg": plan_id,
            }
        )
    return candidates


def _close_item_id_match(candidate_id: str, item_id: str) -> str | None:
    if candidate_id == item_id:
        return "exact"
    if candidate_id.startswith(item_id):
        return "prefix"
    return None


def _collapse_close_item_plan_state_pairs(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    execplans = [candidate for candidate in candidates if candidate["kind"] == "execplan"]
    if not execplans:
        return candidates
    if len(execplans) != 1:
        return candidates
    execplan = execplans[0]
    execplan_path = str(execplan.get("path", ""))
    related_state = []
    unrelated_state = []
    for candidate in candidates:
        if candidate["kind"] == "execplan":
            continue
        surface = str(candidate.get("surface", "")).replace("\\", "/")
        if surface and (surface == execplan_path or surface.endswith("/" + execplan_path) or surface.endswith(execplan_path)):
            related_state.append(candidate)
        else:
            unrelated_state.append(candidate)
    if related_state and not unrelated_state:
        return [execplan]
    return candidates


def _remove_close_item_state_candidate(state: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any] | None:
    updated = copy.deepcopy(state)
    bucket = str(candidate.get("bucket", ""))
    index = int(candidate.get("index", -1))
    if index < 0:
        return None

    if bucket.startswith("todo."):
        parent = updated.get("todo")
        key = bucket.split(".", 1)[1]
    elif bucket.startswith("roadmap."):
        parent = updated.get("roadmap")
        key = bucket.split(".", 1)[1]
    elif bucket == "active.execplans":
        parent = updated.get("active")
        key = "execplans"
    elif bucket == "work_items":
        parent = updated
        key = "work_items"
    else:
        return None

    if not isinstance(parent, dict):
        return None
    items = parent.get(key)
    if not isinstance(items, list) or index >= len(items):
        return None
    raw = items[index]
    if not isinstance(raw, dict) or str(raw.get("id", "")).strip() != str(candidate.get("id", "")):
        return None
    parent[key] = [item for item_index, item in enumerate(items) if item_index != index]
    return updated


def _write_state_to_toml(target_root: Path, state: dict[str, Any]) -> None:
    state_path = target_root / PLANNING_STATE_PATH
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text("\n".join(_state_to_toml_lines(state)), encoding="utf-8")


def _merge_todo_state_from_toml_lines(state: dict[str, Any], lines: list[str]) -> dict[str, Any]:
    try:
        updated = tomllib.loads("\n".join(lines))
    except tomllib.TOMLDecodeError:
        return state
    todo = updated.get("todo")
    if isinstance(todo, dict):
        state = dict(state)
        state["todo"] = todo
    return state


def _state_to_toml_lines(state: dict[str, Any]) -> list[str]:
    def _format_inline_item(item: object) -> str:
        if isinstance(item, dict):
            item_str = ", ".join(f"{k} = {json.dumps(v)}" for k, v in item.items())
            return f"{{ {item_str} }}"
        return json.dumps(item)

    lines = [*MANAGED_STATE_HEADER_LINES, ""]
    for key in ("kind", "schema_version"):
        if key in state:
            lines.append(f"{key} = {json.dumps(state[key])}")
    if lines:
        lines.append("")
    if "work_items" in state:
        items = state["work_items"]
        if not items:
            lines.append("work_items = []")
        else:
            lines.append("work_items = [")
            for item in items:
                lines.append(f"  {_format_inline_item(item)},")
            lines.append("]")
        lines.append("")
    if "active" in state:
        lines.append("[active]")
        execplans = state["active"].get("execplans", []) if isinstance(state["active"], dict) else []
        if not execplans:
            lines.append("execplans = []")
        else:
            lines.append("execplans = [")
            for item in execplans:
                lines.append(f"  {_format_inline_item(item)},")
            lines.append("]")
        lines.append("")
    if "todo" in state:
        lines.append("[todo]")
        for key in ["active_items", "queued_items"]:
            if key in state["todo"]:
                items = state["todo"][key]
                if not items:
                    lines.append(f"{key} = []")
                else:
                    lines.append(f"{key} = [")
                    for item in items:
                        lines.append(f"  {_format_inline_item(item)},")
                    lines.append("]")
        lines.append("")

    if "roadmap" in state:
        lines.append("[roadmap]")
        for key in ["lanes", "candidates"]:
            if key in state["roadmap"]:
                items = state["roadmap"][key]
                if not items:
                    lines.append(f"{key} = []")
                else:
                    lines.append(f"{key} = [")
                    for item in items:
                        lines.append(f"  {_format_inline_item(item)},")
                    lines.append("]")
        lines.append("")
    return lines


def _ensure_state_toml_exists(target_root: Path, *, overwrite: bool = False) -> None:
    """Ensure a baseline state.toml exists in the managed planning root."""
    state_path = target_root / PLANNING_STATE_PATH
    if state_path.exists() and not overwrite:
        return

    state = {
        "kind": PLANNING_STATE_KIND,
        "schema_version": PLANNING_STATE_SCHEMA_VERSION,
        "active": {"execplans": []},
        "work_items": [],
    }
    _write_state_to_toml(target_root, state)


def _is_managed_compatibility_view(path: Path) -> bool:
    if not path.exists():
        return False
    return _COMPATIBILITY_VIEW_NOTICE in path.read_text(encoding="utf-8")


def _remove_generated_planning_views(target_root: Path, *, result: InstallResult | None = None) -> None:
    for relative in (
        Path("TODO.md"),
        Path("ROADMAP.md"),
        Path(".agentic-workspace/planning/TODO.md"),
        Path(".agentic-workspace/planning/ROADMAP.md"),
    ):
        path = target_root / relative
        if _is_managed_compatibility_view(path):
            if result is not None:
                result.add(
                    "manual review",
                    path,
                    "unsupported legacy compatibility view detected; migrate any durable content to .agentic-workspace/planning/state.toml or delete manually",
                )
