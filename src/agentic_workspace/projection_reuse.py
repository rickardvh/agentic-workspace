"""Dependency-aware reuse for unchanged AW command projections."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Callable, Iterator, Literal, Mapping, Sequence

_CACHE_KIND = "agentic-workspace/projection-reuse-record/v2"
_CACHE_CONTRACT_VERSION = 6
_MAX_CACHE_RECORDS = 32
_GIT_TIMEOUT_SECONDS = 0.5
_DEPENDENCY_MAX_ENTRIES = 20_000
_DEPENDENCY_TIME_BUDGET_SECONDS = 2.0
_DEFAULT_COMPUTATION_BUDGET_MS = 10_000
_DEFAULT_SERIALIZATION_BUDGET_BYTES = 64 * 1024
_LONG_COMMAND_THRESHOLD_SECONDS = 10.0
_PROGRESS_INTERVAL_SECONDS = 10.0
_IGNORED_DEPENDENCY_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
}
_LOCAL_DECISION_DEPENDENCIES = (
    ".agentic-workspace/local/cache/dogfooding-signal-status.json",
    ".agentic-workspace/local/cache/external-intent-evidence.json",
    ".agentic-workspace/local/cache/pr-comment-delta.json",
    ".agentic-workspace/local/cache/pr-comment-stack.json",
    ".agentic-workspace/local/cache/proof-reuse.json",
)
_OPERATION_DEPENDENCY_ROOTS = {
    "start": ("src/agentic_workspace", "generated/workspace", "generated/planning", "scripts", "packages", "docs"),
    "implement": ("src/agentic_workspace", "generated/workspace", "generated/planning", "scripts", "packages", "docs"),
    "proof": ("src/agentic_workspace", "generated/workspace", "generated/planning", "scripts", "packages", "docs"),
    "doctor": ("src/agentic_workspace", "generated/workspace", "scripts", "packages"),
    "report": ("src/agentic_workspace", "generated/workspace", "scripts", "packages", "docs"),
    "summary": ("src/agentic_workspace", "generated/workspace", "generated/planning", "scripts", "packages/planning", "docs"),
}
_SELECTOR_ENRICHMENT_DEPENDENCIES = {
    "memory_decision_packet": (
        ".agentic-workspace/memory/repo/manifest.toml",
        ".agentic-workspace/memory/repo/index.md",
    ),
    "closeout_trust_inspection": (
        ".agentic-workspace/local/proof-receipts/last.json",
        ".agentic-workspace/planning/archive/index.json",
    ),
    "operating_projection_receipt": (
        ".agentic-workspace/local/proof-receipts/last.json",
        ".agentic-workspace/local/proof-receipts/history.jsonl",
        ".agentic-workspace/local/cache/proof-reuse.json",
        ".agentic-workspace/planning/archive/index.json",
    ),
}

_PROJECTION_CONTEXT_FIELDS = ("branch", "head", "base")
_PROJECTION_INVALIDATION_REASON_BY_FIELD = {
    "branch": "branch-changed",
    "head": "head-changed",
    "base": "base-changed",
    "task": "task-changed",
    "selected_owner": "selected-owner-changed",
    "planning": "planning-revision-changed",
    "changed_paths": "changed-paths-changed",
    "proof_subject": "proof-subject-changed",
    "runtime_compatibility": "runtime-compatibility-changed",
    "external_freshness": "external-freshness-changed",
    "worktree": "admitted-worktree-changed",
    "route_inputs": "route-inputs-changed",
    "verification_inputs": "verification-inputs-changed",
    "proof_inputs": "proof-inputs-changed",
    "closeout_inputs": "closeout-inputs-changed",
    "runtime_mirror_inputs": "runtime-mirror-inputs-changed",
}


def _expose_projection_reuse_receipt(*, operation: str, query: dict[str, Any]) -> bool:
    """Keep proof lineage visible where a caller supplied projection scope."""

    if operation in {"start", "implement"}:
        return bool(str(query.get("select") or "").strip())
    return True


@dataclass(frozen=True)
class DependencyScanBudget:
    max_entries: int = _DEPENDENCY_MAX_ENTRIES
    time_budget_seconds: float = _DEPENDENCY_TIME_BUDGET_SECONDS


@dataclass
class DependencyScanResult:
    status: Literal["complete", "truncated", "unavailable"]
    files: list[Path]
    entries_examined: int
    elapsed_seconds: float
    reason: str = ""


@dataclass(frozen=True)
class GitProbeResult:
    status: Literal["complete", "unavailable", "not_applicable"]
    stdout: str = ""
    reason: str = ""


@dataclass
class DependencyDigestResult:
    digest: str
    dependencies: list[str]
    status: Literal["complete", "truncated", "unavailable"]
    findings: list[dict[str, Any]]
    input_revisions: dict[str, Any] | None = None
    state_read_count: int = 0

    def __iter__(self) -> Iterator[Any]:
        """Keep the historical two-value unpacking contract for direct callers."""
        yield self.digest
        yield self.dependencies


@dataclass(frozen=True)
class ProjectionConstituentSpec:
    """Declare the semantic revision boundary for one canonical projection owner.

    Branch, HEAD, and base are observational context by default.  A constituent
    must opt into them as dependencies before a stack movement can invalidate
    that owner's result.
    """

    constituent_id: str
    dependency_fields: tuple[str, ...]
    required_fields: tuple[str, ...] = ()


STANDARD_PROJECTION_CONSTITUENT_SPECS = (
    ProjectionConstituentSpec(
        "route",
        ("task", "selected_owner", "planning", "changed_paths", "route_inputs"),
    ),
    ProjectionConstituentSpec(
        "verification",
        ("task", "changed_paths", "verification_inputs"),
    ),
    ProjectionConstituentSpec(
        "selected_proof",
        ("task", "changed_paths", "proof_subject", "proof_inputs"),
    ),
    ProjectionConstituentSpec(
        "closeout_trust",
        ("task", "selected_owner", "planning", "changed_paths", "proof_subject", "closeout_inputs"),
    ),
    ProjectionConstituentSpec(
        "runtime_mirror",
        ("runtime_compatibility", "runtime_mirror_inputs"),
    ),
)


def _projection_revision_available(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in {"", "unknown", "unavailable", "truncated"}
    if isinstance(value, dict):
        return str(value.get("status") or "current").strip().lower() not in {"unknown", "unavailable", "truncated"}
    return True


def _projection_identity_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def build_projection_constituent_identity(
    *,
    spec: ProjectionConstituentSpec,
    input_revisions: Mapping[str, Any],
    contextual_fields: Sequence[str] = _PROJECTION_CONTEXT_FIELDS,
) -> dict[str, Any]:
    """Build one owner-scoped input identity without treating stack position as freshness."""

    dependency_fields = tuple(dict.fromkeys(spec.dependency_fields))
    required_fields = tuple(dict.fromkeys(spec.required_fields or dependency_fields))
    dependency_revisions = {
        field: json.loads(json.dumps(input_revisions.get(field), sort_keys=True, default=str))
        for field in dependency_fields
        if field in input_revisions
    }
    missing_fields = [field for field in required_fields if field not in input_revisions]
    unavailable_fields = [
        field for field in required_fields if field in input_revisions and not _projection_revision_available(input_revisions[field])
    ]
    status = "current" if not missing_fields and not unavailable_fields else "unavailable"
    canonical = {
        "constituent_id": spec.constituent_id,
        "dependency_fields": list(dependency_fields),
        "dependency_revisions": dependency_revisions,
    }
    fingerprint = _projection_identity_digest(canonical)
    context = {
        field: json.loads(json.dumps(input_revisions.get(field), sort_keys=True, default=str))
        for field in dict.fromkeys(contextual_fields)
        if field in input_revisions
    }
    return {
        "kind": "agentic-workspace/projection-constituent-identity/v1",
        "status": status,
        "constituent_id": spec.constituent_id,
        "identity_id": f"projection-constituent:{spec.constituent_id}:{fingerprint[:16]}" if status == "current" else "",
        "input_revision": f"sha256:{fingerprint}" if status == "current" else "",
        "dependency_fields": list(dependency_fields),
        "dependency_revisions": dependency_revisions,
        "missing_dependency_fields": missing_fields,
        "unavailable_dependency_fields": unavailable_fields,
        "observed_context": context,
        "observed_context_revision": f"sha256:{_projection_identity_digest(context)}",
        "freshness_rule": (
            "Reuse is governed only by declared semantic dependencies. Branch, HEAD, and base remain observational "
            "unless this constituent explicitly declares them as dependency fields."
        ),
    }


def build_standard_projection_constituent_identities(
    *, input_revisions: Mapping[str, Any], specs: Sequence[ProjectionConstituentSpec] = STANDARD_PROJECTION_CONSTITUENT_SPECS
) -> dict[str, dict[str, Any]]:
    """Build the stable owner set consumed by the later task-scoped composer."""

    return {spec.constituent_id: build_projection_constituent_identity(spec=spec, input_revisions=input_revisions) for spec in specs}


def _projection_context_delta(previous: Mapping[str, Any], current: Mapping[str, Any]) -> list[dict[str, Any]]:
    prior_context = previous.get("observed_context", {}) if isinstance(previous.get("observed_context"), dict) else {}
    current_context = current.get("observed_context", {}) if isinstance(current.get("observed_context"), dict) else {}
    return [
        {
            "field": field,
            "reason": _PROJECTION_INVALIDATION_REASON_BY_FIELD.get(field, f"{field}-changed"),
            "invalidates_constituent": field in current.get("dependency_fields", []),
        }
        for field in sorted(set(prior_context) | set(current_context))
        if prior_context.get(field) != current_context.get(field)
    ]


def compare_projection_constituent_identity(*, previous: Mapping[str, Any] | None, current: Mapping[str, Any] | None) -> dict[str, Any]:
    """Classify one owner result as reusable, invalidated, absent, or unknown."""

    constituent_id = str((current or {}).get("constituent_id") or (previous or {}).get("constituent_id") or "unknown")
    base = {
        "kind": "agentic-workspace/projection-constituent-freshness/v1",
        "constituent_id": constituent_id,
        "context_delta": _projection_context_delta(previous or {}, current or {}),
    }
    if current is None:
        return {
            **base,
            "status": "unavailable",
            "freshness": "unknown",
            "invalidation_reasons": ["current-identity-missing"],
            "required_action": "establish-current-identity",
        }
    if current.get("kind") != "agentic-workspace/projection-constituent-identity/v1" or current.get("status") != "current":
        unavailable = [
            *[f"missing:{field}" for field in current.get("missing_dependency_fields", [])],
            *[f"unavailable:{field}" for field in current.get("unavailable_dependency_fields", [])],
        ]
        return {
            **base,
            "status": "unavailable",
            "freshness": "unknown",
            "invalidation_reasons": unavailable or ["current-identity-unavailable"],
            "required_action": "establish-current-identity",
        }
    if previous is None or previous.get("kind") != "agentic-workspace/projection-constituent-identity/v1":
        return {
            **base,
            "status": "not-recorded",
            "freshness": "not-recorded",
            "invalidation_reasons": ["prior-identity-missing"],
            "required_action": "build-constituent",
        }
    if previous.get("status") != "current":
        return {
            **base,
            "status": "unavailable",
            "freshness": "unknown",
            "invalidation_reasons": ["prior-identity-unavailable"],
            "required_action": "build-constituent",
        }
    if previous.get("constituent_id") != current.get("constituent_id"):
        return {
            **base,
            "status": "invalidated",
            "freshness": "stale",
            "invalidation_reasons": ["constituent-owner-changed"],
            "required_action": "build-constituent",
        }
    previous_revisions = previous.get("dependency_revisions", {}) if isinstance(previous.get("dependency_revisions"), dict) else {}
    current_revisions = current.get("dependency_revisions", {}) if isinstance(current.get("dependency_revisions"), dict) else {}
    changed_fields = [
        field
        for field in sorted(set(previous_revisions) | set(current_revisions))
        if previous_revisions.get(field) != current_revisions.get(field)
    ]
    if not changed_fields and previous.get("input_revision") == current.get("input_revision"):
        return {
            **base,
            "status": "reused",
            "freshness": "current",
            "invalidation_reasons": [],
            "required_action": "reuse-owner-result",
            "input_revision": current.get("input_revision", ""),
        }
    return {
        **base,
        "status": "invalidated",
        "freshness": "stale",
        "changed_dependency_fields": changed_fields,
        "invalidation_reasons": [_PROJECTION_INVALIDATION_REASON_BY_FIELD.get(field, f"{field}-changed") for field in changed_fields]
        or ["constituent-input-revision-changed"],
        "required_action": "build-constituent",
        "previous_input_revision": previous.get("input_revision", ""),
        "current_input_revision": current.get("input_revision", ""),
    }


def compare_projection_constituent_sets(
    *, previous: Mapping[str, Mapping[str, Any]], current: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    """Return an exact partial-invalidation matrix for a composed projection."""

    constituent_ids = sorted(set(previous) | set(current))
    comparisons = {
        constituent_id: compare_projection_constituent_identity(previous=previous.get(constituent_id), current=current.get(constituent_id))
        for constituent_id in constituent_ids
    }
    reused = [key for key, value in comparisons.items() if value["status"] == "reused"]
    invalidated = [key for key, value in comparisons.items() if value["status"] in {"invalidated", "not-recorded"}]
    unknown = [key for key, value in comparisons.items() if value["status"] == "unavailable"]
    if unknown:
        status = "unknown"
    elif invalidated and reused:
        status = "partially-invalidated"
    elif invalidated:
        status = "invalidated"
    else:
        status = "reused"
    return {
        "kind": "agentic-workspace/projection-constituent-delta/v1",
        "status": status,
        "constituents": comparisons,
        "reused_constituents": reused,
        "invalidated_constituents": invalidated,
        "unknown_constituents": unknown,
        "focused_rebuild_constituents": [*invalidated, *unknown],
        "broad_rebuild_required": False,
        "rule": (
            "Rebuild only invalidated or unknown canonical owner results. A broad rebuild requires a separate explicit "
            "escalation decision and is never inferred from stack movement."
        ),
    }


@dataclass(frozen=True)
class ProjectionBudget:
    computation_budget_ms: int = _DEFAULT_COMPUTATION_BUDGET_MS
    serialization_budget_bytes: int = _DEFAULT_SERIALIZATION_BUDGET_BYTES
    long_command_threshold_seconds: float = _LONG_COMMAND_THRESHOLD_SECONDS
    progress_interval_seconds: float = _PROGRESS_INTERVAL_SECONDS


class ProjectionCancelled(RuntimeError):
    """Internal cooperative unwind raised only at Python execution checkpoints."""


class ProjectionCancellationToken:
    """Coordinate cancellation between the adapter and its active projection stage."""

    def __init__(self) -> None:
        self._requested = threading.Event()
        self._acknowledged = threading.Event()

    @property
    def requested(self) -> bool:
        return self._requested.is_set()

    @property
    def acknowledged(self) -> bool:
        return self._acknowledged.is_set()

    def request(self) -> None:
        self._requested.set()

    def acknowledge(self) -> None:
        self._acknowledged.set()

    def checkpoint(self) -> None:
        if self.requested:
            self.acknowledge()
            raise ProjectionCancelled


_ACTIVE_CANCELLATION = threading.local()


def projection_cancellation_checkpoint() -> None:
    """Acknowledge cancellation from a safe boundary inside an active builder."""

    token = getattr(_ACTIVE_CANCELLATION, "token", None)
    if isinstance(token, ProjectionCancellationToken):
        token.checkpoint()


class ProjectionProgress:
    """Bounded stderr heartbeat and cooperative cancel contract for long work."""

    def __init__(self, *, root: Path, operation: str, budget: ProjectionBudget | None = None) -> None:
        self.root = root
        self.operation = operation
        self.budget = budget or ProjectionBudget()
        self.cancel_path = root / ".agentic-workspace" / "local" / "cancellation" / f"{operation}.cancel"
        self.started_at = time.monotonic()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self) -> ProjectionProgress:
        self._thread = threading.Thread(target=self._emit_heartbeats, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=0.1)

    @property
    def cancel_requested(self) -> bool:
        return self.cancel_path.is_file()

    def cancellation_payload(self) -> dict[str, Any] | None:
        """Return the shared cancellation envelope at a cooperative checkpoint."""

        if not self.cancel_requested:
            return None
        return {
            "kind": "agentic-workspace/projection-cancelled/v1",
            "status": "cancelled",
            "operation": self.operation,
            "next_action": "Remove the cancellation request and rerun the same scoped command when ready.",
        }

    def run_cancellable(self, builder: Callable[[], dict[str, Any]], *, stage: str) -> dict[str, Any]:
        """Run one stage until it completes or acknowledges cooperative cancellation."""

        cancelled = self.cancellation_payload()
        if cancelled is not None:
            return cancelled
        result: list[dict[str, Any]] = []
        failure: list[BaseException] = []
        token = ProjectionCancellationToken()

        def run() -> None:
            try:
                _ACTIVE_CANCELLATION.token = token
                projection_cancellation_checkpoint()
                built = builder()
                projection_cancellation_checkpoint()
                result.append(built)
            except ProjectionCancelled:
                token.acknowledge()
            except BaseException as exc:  # pragma: no cover - re-raised on the caller thread
                failure.append(exc)
            finally:
                _ACTIVE_CANCELLATION.token = None

        worker = threading.Thread(target=run, name=f"aw-{self.operation}-{stage}")
        worker.start()
        while worker.is_alive():
            worker.join(timeout=min(0.025, self.budget.progress_interval_seconds))
            if self.cancel_requested:
                token.request()
        if token.acknowledged:
            payload = self.cancellation_payload() or {}
            payload["cancelled_stage"] = stage
            payload["later_stages_skipped"] = True
            payload["cancellation_observed_during_work"] = True
            payload["active_stage_stopped"] = True
            return payload
        if failure:
            raise failure[0]
        return result[0]

    def contract(self) -> dict[str, Any]:
        return {
            "kind": "agentic-workspace/projection-progress-contract/v1",
            "status": "cancel-requested" if self.cancel_requested else "complete",
            "operation": self.operation,
            "elapsed_ms": round((time.monotonic() - self.started_at) * 1000, 3),
            "long_command_threshold_ms": round(self.budget.long_command_threshold_seconds * 1000),
            "heartbeat_interval_ms": round(self.budget.progress_interval_seconds * 1000),
            "cancel": {
                "path": self.cancel_path.relative_to(self.root).as_posix(),
                "action": f"Create {self.cancel_path.relative_to(self.root).as_posix()} to request cancellation at the next checkpoint.",
                "semantics": "cooperative-checkpoint",
            },
            "drill_down": f"agentic-workspace {self.operation} --target . --verbose --format json",
        }

    def _emit_heartbeats(self) -> None:
        if self._stop.wait(self.budget.long_command_threshold_seconds):
            return
        sequence = 1
        while not self._stop.is_set():
            packet = {
                "kind": "agentic-workspace/projection-progress/v1",
                "operation": self.operation,
                "status": "cancel-requested" if self.cancel_requested else "running",
                "sequence": sequence,
                "elapsed_ms": round((time.monotonic() - self.started_at) * 1000, 3),
                "cancel_path": self.cancel_path.relative_to(self.root).as_posix(),
            }
            print(json.dumps(packet, sort_keys=True), file=sys.stderr, flush=True)
            sequence += 1
            if self._stop.wait(self.budget.progress_interval_seconds):
                return


def _scan_exhausted(*, started_at: float, entries_examined: int, budget: DependencyScanBudget) -> str:
    if entries_examined >= budget.max_entries:
        return f"dependency entry budget exhausted after {entries_examined} entries"
    if time.monotonic() - started_at >= budget.time_budget_seconds:
        return f"dependency time budget exhausted after {budget.time_budget_seconds:g}s"
    return ""


def _files_under(
    path: Path,
    *,
    started_at: float,
    entries_examined: int,
    budget: DependencyScanBudget,
) -> DependencyScanResult:
    if not path.is_dir():
        return DependencyScanResult("complete", [], entries_examined, time.monotonic() - started_at)
    files: list[Path] = []
    try:
        for current, directories, filenames in os.walk(path):
            exhaustion = _scan_exhausted(started_at=started_at, entries_examined=entries_examined, budget=budget)
            if exhaustion:
                return DependencyScanResult("truncated", files, entries_examined, time.monotonic() - started_at, exhaustion)
            directories[:] = sorted(name for name in directories if name not in _IGNORED_DEPENDENCY_DIRS)
            current_path = Path(current)
            for filename in sorted(filenames):
                exhaustion = _scan_exhausted(started_at=started_at, entries_examined=entries_examined, budget=budget)
                if exhaustion:
                    return DependencyScanResult("truncated", files, entries_examined, time.monotonic() - started_at, exhaustion)
                entries_examined += 1
                files.append(current_path / filename)
    except OSError as exc:
        return DependencyScanResult(
            "unavailable",
            files,
            entries_examined,
            time.monotonic() - started_at,
            f"dependency traversal failed for {path}: {exc}",
        )
    return DependencyScanResult("complete", files, entries_examined, time.monotonic() - started_at)


def _dependency_files(root: Path, operation: str, *, budget: DependencyScanBudget | None = None) -> DependencyScanResult:
    budget = budget or DependencyScanBudget()
    started_at = time.monotonic()
    entries_examined = 0
    candidates = [root / "AGENTS.md", root / "pyproject.toml", root / "uv.lock", root / "Makefile"]
    candidates.extend(root.glob("*/AGENTS.md"))
    aw_root = root / ".agentic-workspace"
    try:
        if aw_root.is_dir():
            for child in aw_root.iterdir():
                exhaustion = _scan_exhausted(started_at=started_at, entries_examined=entries_examined, budget=budget)
                if exhaustion:
                    return DependencyScanResult("truncated", candidates, entries_examined, time.monotonic() - started_at, exhaustion)
                entries_examined += 1
                if child.name in {"local", "logs", "projection-cache", "session-logging"}:
                    continue
                if child.is_file():
                    candidates.append(child)
                else:
                    result = _files_under(
                        child,
                        started_at=started_at,
                        entries_examined=entries_examined,
                        budget=budget,
                    )
                    candidates.extend(result.files)
                    entries_examined = result.entries_examined
                    if result.status != "complete":
                        return DependencyScanResult(
                            result.status,
                            candidates,
                            entries_examined,
                            result.elapsed_seconds,
                            result.reason,
                        )
            candidates.extend(root / relative for relative in _LOCAL_DECISION_DEPENDENCIES)
        for relative_root in _OPERATION_DEPENDENCY_ROOTS.get(operation, ()):
            result = _files_under(
                root / relative_root,
                started_at=started_at,
                entries_examined=entries_examined,
                budget=budget,
            )
            candidates.extend(result.files)
            entries_examined = result.entries_examined
            if result.status != "complete":
                return DependencyScanResult(
                    result.status,
                    candidates,
                    entries_examined,
                    result.elapsed_seconds,
                    result.reason,
                )
    except OSError as exc:
        return DependencyScanResult(
            "unavailable",
            candidates,
            entries_examined,
            time.monotonic() - started_at,
            f"dependency discovery failed: {exc}",
        )
    files = sorted({path for path in candidates if path.is_file()}, key=lambda path: path.as_posix())
    return DependencyScanResult("complete", files, entries_examined, time.monotonic() - started_at)


def _git(root: Path, *args: str) -> GitProbeResult:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return GitProbeResult("unavailable", reason=f"git {' '.join(args)} timed out after {_GIT_TIMEOUT_SECONDS}s")
    except (OSError, subprocess.SubprocessError, TypeError) as exc:
        return GitProbeResult("unavailable", reason=f"git {' '.join(args)} failed: {exc}")
    if result.returncode != 0:
        detail = result.stderr.strip() or f"exit code {result.returncode}"
        if "not a git repository" in detail.lower():
            return GitProbeResult("not_applicable", reason="target is not a Git worktree")
        if args == ("rev-parse", "HEAD") and ("ambiguous argument 'head'" in detail.lower() or "unknown revision" in detail.lower()):
            return GitProbeResult("not_applicable", stdout="unborn", reason="Git HEAD has no commit yet")
        return GitProbeResult("unavailable", reason=f"git {' '.join(args)} failed: {detail}")
    return GitProbeResult("complete", stdout=result.stdout.strip())


def _content_revision(root: Path, relatives: list[str], *, max_files: int = 64) -> tuple[str, list[str]]:
    digest = hashlib.sha256()
    dependencies: list[str] = []
    for index, relative in enumerate(sorted(dict.fromkeys(relatives))):
        path = root / relative
        digest.update(relative.encode())
        if index >= max_files:
            digest.update(b"<content-read-budget-exceeded>")
            continue
        if not path.is_file():
            digest.update(b"<missing>")
            continue
        dependencies.append(relative)
        try:
            digest.update(hashlib.sha256(path.read_bytes()).digest())
        except OSError:
            digest.update(b"<unavailable>")
    return digest.hexdigest()[:20], dependencies


def _planning_revision(root: Path) -> tuple[str, list[str]]:
    state_relative = ".agentic-workspace/planning/state.toml"
    relatives = [state_relative]
    planning_patterns = (
        ".agentic-workspace/planning/execplans/*.plan.json",
        ".agentic-workspace/planning/lanes/*.lane.json",
        ".agentic-workspace/planning/decompositions/*.decomposition.json",
        ".agentic-workspace/planning/issue-relations/*.issue-relation.json",
        ".agentic-workspace/planning/integration/proposals/*.integration-proposal.json",
        ".agentic-workspace/planning/integration/receipts/*.integration-receipt.json",
    )
    for pattern in planning_patterns:
        relatives.extend(path.relative_to(root).as_posix() for path in sorted(root.glob(pattern)) if path.is_file())
    selection_relative = ".agentic-workspace/local/planning/owner-selection.json"
    if (root / selection_relative).is_file():
        relatives.append(selection_relative)
    return _content_revision(root, relatives)


def _changed_path_revision(root: Path, changed_paths: list[str]) -> tuple[str, list[str]]:
    normalized: list[str] = []
    for value in changed_paths:
        candidate = Path(str(value))
        if candidate.is_absolute():
            try:
                candidate = candidate.resolve().relative_to(root)
            except (OSError, ValueError):
                normalized.append(candidate.as_posix())
                continue
        normalized.append(candidate.as_posix().lstrip("./"))
    return _content_revision(root, normalized)


def _selector_enrichment_revision(root: Path, query: dict[str, Any]) -> tuple[str, list[str]]:
    """Read only canonical sources required by explicitly selected enrichment."""

    selected = {token.strip() for token in str(query.get("select") or "").split(",") if token.strip()}
    section = str(query.get("section") or "").strip()
    if section:
        selected.add(section)
    relatives: list[str] = []
    for selector, dependencies in _SELECTOR_ENRICHMENT_DEPENDENCIES.items():
        if any(token == selector or token.startswith(f"{selector}.") for token in selected):
            relatives.extend(dependencies)
    return _content_revision(root, relatives)


def admitted_projection_revisions(
    *, root: Path, operation: str, query: dict[str, Any]
) -> tuple[dict[str, Any], list[str], list[dict[str, Any]]]:
    """Resolve the bounded authoritative inputs shared by ordinary projections."""

    root = root.resolve()
    findings: list[dict[str, Any]] = []
    dependencies: list[str] = []
    branch_probe = _git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    head_probe = _git(root, "rev-parse", "HEAD")
    status_probe = _git(
        root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--",
        ".agentic-workspace",
        "src/agentic_workspace",
        "generated/workspace",
        "generated/planning",
        "packages",
        "scripts",
        "docs",
        "AGENTS.md",
        "pyproject.toml",
        "uv.lock",
        "Makefile",
    )
    for name, probe in (("branch", branch_probe), ("head", head_probe), ("worktree", status_probe)):
        if probe.status == "unavailable":
            findings.append(
                {
                    "kind": "agentic-workspace/projection-degraded-finding/v1",
                    "section": f"projection_{name}_revision",
                    "status": "unavailable",
                    "reason": probe.reason,
                    "retry": "Retry after Git repository access is responsive; projection reuse is disabled meanwhile.",
                }
            )

    dirty_relatives: list[str] = []
    admitted_local_paths = {*_LOCAL_DECISION_DEPENDENCIES, ".agentic-workspace/local/planning/owner-selection.json"}
    if status_probe.status == "complete":
        for line in status_probe.stdout.splitlines():
            relative = line[3:].replace("\\", "/")
            if " -> " in relative:
                relative = relative.rsplit(" -> ", 1)[-1]
            if relative.startswith(".agentic-workspace/local/") and relative not in admitted_local_paths:
                continue
            if relative:
                dirty_relatives.append(relative)
    worktree_revision, worktree_dependencies = _content_revision(root, dirty_relatives)
    if len(set(dirty_relatives)) > 64:
        findings.append(
            {
                "kind": "agentic-workspace/projection-degraded-finding/v1",
                "section": "projection_worktree_revision",
                "status": "unavailable",
                "reason": "admitted worktree input exceeds the 64-file content-read budget",
                "retry": "Narrow the changed worktree or use the explicit verbose/detail route; projection reuse is disabled meanwhile.",
            }
        )
    dependencies.extend(worktree_dependencies)
    planning_revision, planning_dependencies = _planning_revision(root)
    dependencies.extend(planning_dependencies)
    query_changed_paths = [str(item) for item in query.get("changed", [])]
    changed_revision, changed_dependencies = _changed_path_revision(root, query_changed_paths)
    if len(set(query_changed_paths)) > 64:
        findings.append(
            {
                "kind": "agentic-workspace/projection-degraded-finding/v1",
                "section": "projection_changed_path_revision",
                "status": "unavailable",
                "reason": "changed-path input exceeds the 64-file content-read budget",
                "retry": "Split the query into a bounded changed-path set; projection reuse is disabled meanwhile.",
            }
        )
    dependencies.extend(changed_dependencies)
    runtime_relatives = [
        ".agentic-workspace/config.toml",
        ".agentic-workspace/config.local.toml",
        ".agentic-workspace/payload-provenance.json",
        ".agentic-workspace/memory/UPGRADE-SOURCE.toml",
        ".agentic-workspace/planning/UPGRADE-SOURCE.toml",
        "pyproject.toml",
        "uv.lock",
    ]
    runtime_revision, runtime_dependencies = _content_revision(root, runtime_relatives)
    dependencies.extend(runtime_dependencies)
    external_relatives = list(_LOCAL_DECISION_DEPENDENCIES)
    external_revision, external_dependencies = _content_revision(root, external_relatives)
    dependencies.extend(external_dependencies)
    selector_enrichment_revision, selector_enrichment_dependencies = _selector_enrichment_revision(root, query)
    dependencies.extend(selector_enrichment_dependencies)
    try:
        package_version = version("agentic-workspace")
    except PackageNotFoundError:
        package_version = "source-checkout"
    selected_owner = str(query.get("selected_owner") or "")
    if not selected_owner:
        selection_path = root / ".agentic-workspace/local/planning/owner-selection.json"
        try:
            selection = json.loads(selection_path.read_text(encoding="utf-8"))
            selected_owner = str(selection.get("selected_owner_ref") or selection.get("owner_ref") or "")
        except (OSError, json.JSONDecodeError):
            selected_owner = ""
    revisions: dict[str, Any] = {
        "branch": branch_probe.stdout if branch_probe.status == "complete" else branch_probe.status,
        "head": head_probe.stdout if head_probe.status in {"complete", "not_applicable"} else head_probe.status,
        "task": hashlib.sha256(str(query.get("task") or "").encode()).hexdigest()[:20],
        "selected_owner": selected_owner,
        "planning": planning_revision,
        "changed_paths": changed_revision,
        "proof_subject": str(query.get("proof_subject") or changed_revision),
        "runtime_compatibility": f"{package_version}:{runtime_revision}",
        "external_freshness": external_revision,
        "worktree": worktree_revision,
    }
    if query.get("decision_context_revision"):
        revisions["decision_context_revision"] = query["decision_context_revision"]
    if selector_enrichment_dependencies:
        revisions["selector_enrichment"] = selector_enrichment_revision
    return revisions, sorted(set(dependencies)), findings


_OPERATING_DECISION_REVISION_FIELDS = (
    "branch",
    "head",
    "task",
    "selected_owner",
    "planning",
    "changed_paths",
    "proof_subject",
    "runtime_compatibility",
)


def _operating_decision_revisions(input_revisions: dict[str, Any]) -> dict[str, Any]:
    """Keep enrichment-only freshness outside operating-decision identity."""

    revisions = {field: input_revisions.get(field) for field in _OPERATING_DECISION_REVISION_FIELDS}
    if "decision_context_revision" in input_revisions:
        revisions["decision_context_revision"] = input_revisions["decision_context_revision"]
    return revisions


def _invalidation_reasons(previous: dict[str, Any], current: dict[str, Any]) -> list[str]:
    return [
        _PROJECTION_INVALIDATION_REASON_BY_FIELD.get(field, f"{field}-changed")
        for field in sorted(set(previous) | set(current))
        if previous.get(field) != current.get(field)
    ]


def dependency_digest(
    *,
    root: Path,
    operation: str,
    query: dict[str, Any],
    budget: DependencyScanBudget | None = None,
) -> DependencyDigestResult:
    del budget  # Kept for compatibility; admitted revision reads are inherently bounded.
    revisions, dependencies, findings = admitted_projection_revisions(root=root, operation=operation, query=query)
    digest = hashlib.sha256()
    digest.update(str(_CACHE_CONTRACT_VERSION).encode())
    digest.update(json.dumps(revisions, sort_keys=True, ensure_ascii=True).encode())
    status: Literal["complete", "truncated", "unavailable"] = "unavailable" if findings else "complete"
    return DependencyDigestResult(
        digest.hexdigest()[:20],
        dependencies,
        status,
        findings,
        revisions,
        state_read_count=len(dependencies) + 3,
    )


def _cache_path(root: Path, operation: str, query: dict[str, Any]) -> Path:
    key = hashlib.sha256(json.dumps({"operation": operation, "query": query}, sort_keys=True).encode()).hexdigest()[:16]
    return root / ".agentic-workspace" / "local" / "projection-cache" / f"{operation}-{key}.json"


def prepare_projection_reuse(*, root: Path, operation: str, query: dict[str, Any], force_refresh: bool = False) -> dict[str, Any]:
    """Resolve bounded decision and enrichment inputs before materialization."""

    lookup_started_at = time.monotonic()
    forced = force_refresh or os.environ.get("AW_PROJECTION_FORCE_REFRESH", "").lower() in {"1", "true", "yes"}
    volatile = (
        operation not in _OPERATION_DEPENDENCY_ROOTS
        or bool(query.get("volatile") or query.get("external_freshness_required"))
        or os.environ.get("AW_PROJECTION_VOLATILE", "").lower() in {"1", "true", "yes"}
    )
    path = _cache_path(root, operation, query)
    if volatile:
        return {
            "digest": "",
            "dependencies": [],
            "path": path,
            "forced": forced,
            "volatile": True,
            "dependency_contract": operation,
            "dependency_status": "complete",
            "degraded_findings": [],
            "input_revisions": {},
            "decision_input_revisions": {},
            "enrichment_input_revisions": {},
            "canonical_input_revision": "",
            "decision_id": "",
            "lookup_started_at": lookup_started_at,
            "invalidation_reasons": ["external-freshness-required"],
        }
    digest_result = dependency_digest(root=root, operation=operation, query=query)
    digest, dependencies = digest_result
    input_revisions = digest_result.input_revisions or {}
    context = {
        "digest": digest,
        "dependencies": dependencies,
        "path": path,
        "forced": forced,
        "volatile": volatile,
        "dependency_contract": operation,
        "dependency_status": digest_result.status,
        "degraded_findings": digest_result.findings,
        "input_revisions": input_revisions,
        "decision_input_revisions": _operating_decision_revisions(input_revisions),
        "enrichment_input_revisions": {
            field: value for field, value in input_revisions.items() if field not in _operating_decision_revisions(input_revisions)
        },
        "canonical_input_revision": "",
        "decision_id": "",
        "lookup_started_at": lookup_started_at,
        "invalidation_reasons": [],
        "state_read_count": digest_result.state_read_count,
    }
    return context


def lookup_projection_reuse(
    *,
    root: Path,
    operation: str,
    query: dict[str, Any],
    full_detail_command: str,
    force_refresh: bool = False,
    context: dict[str, Any] | None = None,
    admitted_input: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    context = context or prepare_projection_reuse(
        root=root,
        operation=operation,
        query=query,
        force_refresh=force_refresh,
    )
    path = context["path"]
    digest = str(context.get("digest") or "")
    dependencies = list(context.get("dependencies") or [])
    forced = bool(context.get("forced"))
    volatile = bool(context.get("volatile"))
    input_revisions = context.get("input_revisions", {})
    lookup_started_at = float(context.get("lookup_started_at") or time.monotonic())
    decision_input = admitted_input if isinstance(admitted_input, dict) else {}
    if decision_input.get("status") != "admitted" or not decision_input.get("admitted_input_revision"):
        context["invalidation_reasons"] = ["surface-decision-input-unavailable"]
        return None, context
    if forced or volatile or context.get("dependency_status") != "complete" or not path.is_file():
        return None, context
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, context
    if record.get("kind") != _CACHE_KIND:
        return None, context
    context["invalidation_reasons"] = _invalidation_reasons(
        record.get("input_revisions", {}) if isinstance(record.get("input_revisions"), dict) else {},
        input_revisions,
    )
    if record.get("dependency_digest") != digest:
        return None, context
    decision_id = str(record.get("decision_id") or "")
    canonical_input_revision = str(record.get("canonical_decision_input_revision") or "")
    projection_input_revision = str(record.get("projection_input_revision") or "")
    admitted_input_revision = str(decision_input.get("admitted_input_revision") or "")
    if not decision_id or projection_input_revision != admitted_input_revision:
        context["invalidation_reasons"] = ["surface-decision-input-changed"]
        return None, context
    context["decision_id"] = decision_id
    context["canonical_input_revision"] = canonical_input_revision
    prior = record.get("decision_snapshot", {}) if isinstance(record.get("decision_snapshot"), dict) else {}
    prior_cost = record.get("observed_cost", {}) if isinstance(record.get("observed_cost"), dict) else {}
    warm_state_reads = context.get("state_read_count", 0)
    cold_state_reads = prior_cost.get("state_read_count", 0)
    cached_projection = record.get("projection") if isinstance(record.get("projection"), dict) else None
    if cached_projection is not None and operation in {"start", "summary", "implement", "proof", "report"}:
        reused_projection = json.loads(json.dumps(cached_projection, sort_keys=True, default=str))
        if _expose_projection_reuse_receipt(operation=operation, query=query):
            reused_projection["projection_reuse"] = {
                "decision_id": decision_id,
                "status": "decision+enrichment-reused",
                "freshness": "current",
                "authority": "agentic_workspace.operating_decision.compile_operating_decision",
                "projection_input_revision": projection_input_revision,
            }
        else:
            reused_projection.pop("projection_reuse", None)
        return reused_projection, context
    return {
        "kind": "agentic-workspace/unchanged-projection/v1",
        "status": "unchanged",
        "operation": operation,
        "dependency_digest": digest,
        "decision_id": decision_id,
        "canonical_decision_input_revision": canonical_input_revision,
        "projection_input_revision": projection_input_revision,
        "actionability_delta": "unchanged",
        "decision_delta": "unchanged",
        "proof_delta": "unchanged",
        "residue_delta": "unchanged",
        "next_action_delta": "unchanged",
        "prior_decision": prior,
        "work_avoided": {
            "full_projection_builder_skipped": True,
            "serialization_of_full_projection_skipped": True,
            "dependency_count": len(dependencies),
            "decision_reused": True,
            "enrichment_reused": True,
        },
        "observed_cost": {
            "elapsed_ms": round((time.monotonic() - lookup_started_at) * 1000, 3),
            "serialized_bytes": 0,
            "state_read_count": warm_state_reads if isinstance(warm_state_reads, int) else 0,
            "cold_state_read_count": cold_state_reads if isinstance(cold_state_reads, int) else 0,
        },
        "reuse": {
            "decision": "reused",
            "enrichment": "reused",
            "invalidation_reasons": [],
            "authority": "operating_decision.compile_operating_decision",
        },
        "budgets": {
            "computation_budget_ms": _DEFAULT_COMPUTATION_BUDGET_MS,
            "serialization_budget_bytes": _DEFAULT_SERIALIZATION_BUDGET_BYTES,
        },
        "progress": {
            "long_command_threshold_ms": round(_LONG_COMMAND_THRESHOLD_SECONDS * 1000),
            "cancel_path": f".agentic-workspace/local/cancellation/{operation}.cancel",
            "drill_down": full_detail_command,
        },
        "full_detail": {"command": full_detail_command, "force_recompute": True},
    }, context


def _strip_projection_authority_context(*, payload: dict[str, Any], payload_context: dict[str, Any], revalidation: dict[str, Any]) -> None:
    """Hide admitted authority internals while retaining evidence for a rejected race."""

    payload_context.pop("projection_decision_input", None)
    payload_context.pop("projection_decision_authority", None)
    if revalidation.get("status") in {None, "", "current"}:
        payload_context.pop("projection_decision_input_consumption", None)
        payload_context.pop("projection_decision_input_revalidation", None)
    if not payload_context and isinstance(payload.get("context"), dict):
        payload.pop("context", None)


def record_projection_reuse(
    *,
    root: Path,
    operation: str,
    query: dict[str, Any],
    context: dict[str, Any],
    payload: dict[str, Any],
    operating_decision: dict[str, Any],
) -> dict[str, Any]:
    if payload.get("status") == "cancelled":
        return {}
    path = context["path"]
    actionability = payload.get("actionability", {}) if isinstance(payload.get("actionability"), dict) else {}
    next_action = payload.get("next_action", {}) if isinstance(payload.get("next_action"), dict) else {}
    decision_packet = payload.get("decision_packet", {}) if isinstance(payload.get("decision_packet"), dict) else {}
    planning_health = payload.get("planning_surface_health", {}) if isinstance(payload.get("planning_surface_health"), dict) else {}
    execution_readiness = payload.get("execution_readiness", {}) if isinstance(payload.get("execution_readiness"), dict) else {}
    current_pressure = payload.get("current_execution_pressure", {}) if isinstance(payload.get("current_execution_pressure"), dict) else {}
    continuation_view = payload.get("continuation_view", {}) if isinstance(payload.get("continuation_view"), dict) else {}
    proof_state = continuation_view.get("proof_state", {}) if isinstance(continuation_view.get("proof_state"), dict) else {}
    residue_governance = payload.get("residue_governance", {}) if isinstance(payload.get("residue_governance"), dict) else {}
    payload_context = payload.get("context", {}) if isinstance(payload.get("context"), dict) else {}
    projection_authority = (
        payload_context.get("projection_decision_authority", {})
        if isinstance(payload_context.get("projection_decision_authority"), dict)
        else {}
    )
    if (
        not operating_decision.get("decision_id")
        or projection_authority.get("status") != "admitted"
        or projection_authority.get("decision_id") != operating_decision.get("decision_id")
        or projection_authority.get("projection_input_revision") != operating_decision.get("projection_input_revision")
    ):
        return {}
    revalidation = (
        payload_context.get("projection_decision_input_revalidation", {})
        if isinstance(payload_context.get("projection_decision_input_revalidation"), dict)
        else {}
    )
    cache_disabled = context.get("volatile") or context.get("dependency_status") != "complete" or not (root / ".agentic-workspace").is_dir()
    if cache_disabled:
        _strip_projection_authority_context(payload=payload, payload_context=payload_context, revalidation=revalidation)
        return {}
    context["decision_id"] = operating_decision["decision_id"]
    context["canonical_input_revision"] = operating_decision.get("admitted_input_revision", "")
    serialized_bytes = len(json.dumps(payload, sort_keys=True, default=str, indent=2).encode())
    elapsed_ms = round((time.monotonic() - float(context.get("lookup_started_at") or time.monotonic())) * 1000, 3)
    budget = ProjectionBudget()
    reuse_result = {
        "kind": "agentic-workspace/projection-reuse-result/v1",
        "status": "rebuilt",
        "decision_id": context.get("decision_id", ""),
        "canonical_decision_input_revision": context.get("canonical_input_revision", ""),
        "decision_reuse": "rebuilt",
        "enrichment_reuse": "rebuilt",
        "invalidation_reasons": list(context.get("invalidation_reasons") or ["no-prior-projection"]),
        "observed_cost": {
            "elapsed_ms": elapsed_ms,
            "serialized_bytes": serialized_bytes,
            "dependency_count": len(context.get("dependencies", [])),
            "state_read_count": int(context.get("state_read_count", 0) or 0),
        },
        "budgets": {
            "computation_budget_ms": budget.computation_budget_ms,
            "serialization_budget_bytes": budget.serialization_budget_bytes,
            "computation_status": "within-budget" if elapsed_ms <= budget.computation_budget_ms else "exceeded",
            "serialization_status": "within-budget" if serialized_bytes <= budget.serialization_budget_bytes else "exceeded",
        },
        "progress": {
            "required": elapsed_ms > budget.long_command_threshold_seconds * 1000,
            "long_command_threshold_ms": round(budget.long_command_threshold_seconds * 1000),
            "cancel_path": f".agentic-workspace/local/cancellation/{operation}.cancel",
            "drill_down": f"agentic-workspace {operation} --target . --verbose --format json",
        },
        "authority": "operating_decision.compile_operating_decision",
        "operating_decision": {
            key: operating_decision.get(key)
            for key in (
                "kind",
                "producer_module",
                "producer_function",
                "decision_id",
                "admitted_input_revision",
                "status",
                "input_revisions",
                "canonical_decision_input_revision",
                "terminal_state",
                "external_blocker",
                "blocked_claim_classes",
                "projection_input_id",
                "projection_input_revision",
                "projection_posture_revision",
                "projection_posture",
            )
            if operating_decision.get(key) not in (None, "")
        },
    }
    compact_receipt = {
        "decision_id": context.get("decision_id", ""),
        "status": "decision+enrichment-rebuilt",
        "freshness": str(revalidation.get("status") or "unavailable"),
        "authority": "agentic_workspace.operating_decision.compile_operating_decision",
        "projection_input_revision": operating_decision.get("projection_input_revision", ""),
    }
    _strip_projection_authority_context(payload=payload, payload_context=payload_context, revalidation=revalidation)
    if _expose_projection_reuse_receipt(operation=operation, query=query):
        payload["projection_reuse"] = compact_receipt
    else:
        payload.pop("projection_reuse", None)
    # The budget governs the emitted projection, including its reuse receipt.
    # Recalculate twice so the byte-count field's own width is reflected.
    for _iteration in range(2):
        emitted_bytes = len(json.dumps(payload, sort_keys=True, default=str, indent=2).encode())
        reuse_result["observed_cost"]["serialized_bytes"] = emitted_bytes
        reuse_result["budgets"]["serialization_status"] = (
            "within-budget" if emitted_bytes <= budget.serialization_budget_bytes else "exceeded"
        )
    if reuse_result["budgets"]["serialization_status"] == "exceeded":
        bounded_payload = enforce_projection_serialization_budget(
            payload=payload,
            operation=operation,
            reuse_result=reuse_result,
            full_detail_command=str(reuse_result["progress"]["drill_down"]),
        )
        payload.clear()
        payload.update(bounded_payload)
        emitted_bytes = len(json.dumps(payload, sort_keys=True, default=str, indent=2).encode())
        reuse_result["observed_cost"]["serialized_bytes"] = emitted_bytes
    record = {
        "kind": _CACHE_KIND,
        "contract_version": _CACHE_CONTRACT_VERSION,
        "operation": operation,
        "query": query,
        "dependency_digest": context["digest"],
        "dependencies": context["dependencies"],
        "decision_id": context.get("decision_id", ""),
        "canonical_decision_input_revision": context.get("canonical_input_revision", ""),
        "projection_input_revision": operating_decision.get("projection_input_revision", ""),
        "input_revisions": context.get("input_revisions", {}),
        "authority": "projection index only; operating decision remains authoritative",
        "projection": payload,
        "output_digest": hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:20],
        "observed_cost": reuse_result["observed_cost"],
        "decision_snapshot": {
            "health": payload.get("health", payload.get("status", planning_health.get("status", ""))),
            "action_required": actionability.get("action_required", payload.get("action_required", bool(payload.get("warning_count", 0)))),
            "actionability_status": actionability.get("status", execution_readiness.get("status", "")),
            "decision": decision_packet.get("next_action", ""),
            "next_action": next_action.get(
                "action",
                next_action.get(
                    "summary",
                    current_pressure.get("recommended_next_action", planning_health.get("recommended_next_action", "")),
                ),
            ),
            "proof": proof_state.get("summary", proof_state.get("status", "")),
            "residue": residue_governance.get("status", ""),
        },
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        records = sorted(path.parent.glob("*.json"), key=lambda item: item.stat().st_mtime_ns, reverse=True)
        for stale in records[_MAX_CACHE_RECORDS:]:
            stale.unlink(missing_ok=True)
    except OSError:
        return {}
    return reuse_result


def enforce_projection_serialization_budget(
    *, payload: dict[str, Any], operation: str, reuse_result: dict[str, Any], full_detail_command: str
) -> dict[str, Any]:
    """Return a semantic compact envelope when an ordinary projection exceeds its byte budget."""

    budgets = reuse_result.get("budgets", {}) if isinstance(reuse_result.get("budgets"), dict) else {}
    if budgets.get("serialization_status") != "exceeded":
        return payload

    def _compact(value: Any, *, depth: int = 0) -> Any:
        if isinstance(value, str):
            return value if len(value) <= 320 else f"{value[:317]}..."
        if isinstance(value, list):
            ordered = value
            item_limit = 8
            if value and all(isinstance(item, str) for item in value):
                critical = [item for item in value if "terminal final response" in item.lower()]
                ordered = [*critical, *(item for item in value if item not in critical)]
                item_limit = 32
            items = [_compact(item, depth=depth + 1) for item in ordered[:item_limit]]
            if len(value) > item_limit:
                items.append({"kind": "agentic-workspace/omitted-items/v1", "omitted_count": len(value) - item_limit})
            return items
        if isinstance(value, dict):
            if depth >= 8:
                return {"kind": "agentic-workspace/omitted-detail/v1", "field_count": len(value)}
            priority = (
                "kind",
                "status",
                "health",
                "answer",
                "installed_state_residue",
                "next_action",
                "next",
                "decision",
                "sufficiency",
                "warnings",
            )
            ordered_keys = [key for key in priority if key in value]
            ordered_keys.extend(key for key in value if key not in ordered_keys)
            selected_keys = ordered_keys[:48]
            compacted = {key: _compact(value[key], depth=depth + 1) for key in selected_keys}
            if len(value) > len(selected_keys):
                compacted["omitted_fields"] = {
                    "kind": "agentic-workspace/omitted-fields/v1",
                    "omitted_count": len(value) - len(selected_keys),
                }
            return compacted
        return value

    bounded = _compact(payload)
    bounded["projection_reuse"] = payload.get("projection_reuse", {})
    bounded["serialization_budget"] = {
        "status": "detail-withheld",
        "operation": operation,
        "reason": "serialization-budget-exceeded",
        "serialized_bytes": reuse_result.get("observed_cost", {}).get("serialized_bytes", 0),
        "serialization_budget_bytes": budgets.get("serialization_budget_bytes", _DEFAULT_SERIALIZATION_BUDGET_BYTES),
        "inventories_materialized_in_response": False,
        "detail_command": full_detail_command,
    }
    encoded = json.dumps(bounded, sort_keys=True, default=str, indent=2).encode()
    if len(encoded) > budgets.get("serialization_budget_bytes", _DEFAULT_SERIALIZATION_BUDGET_BYTES):

        def _compact_hard(value: Any, *, depth: int = 0) -> Any:
            if isinstance(value, str):
                return value if len(value) <= 200 else f"{value[:197]}..."
            if isinstance(value, list):
                item_limit = 32 if value and all(isinstance(item, str) for item in value) else 12
                items = [_compact_hard(item, depth=depth + 1) for item in value[:item_limit]]
                if len(value) > item_limit:
                    items.append({"kind": "agentic-workspace/omitted-items/v1", "omitted_count": len(value) - item_limit})
                return items
            if isinstance(value, dict):
                if depth >= 8:
                    return {"kind": "agentic-workspace/omitted-detail/v1", "field_count": len(value)}
                priority = (
                    "kind",
                    "status",
                    "health",
                    "trust",
                    "answer",
                    "completion_gate",
                    "terminal_outcome_contract",
                    "terminal_action",
                    "summary",
                    "next_action",
                    "decision",
                    "proof_confidence",
                    "checks",
                )
                ordered_keys = [key for key in priority if key in value]
                ordered_keys.extend(key for key in value if key not in ordered_keys)
                selected_keys = ordered_keys[:32]
                compacted = {key: _compact_hard(value[key], depth=depth + 1) for key in selected_keys}
                if len(value) > len(selected_keys):
                    compacted["omitted_fields"] = {
                        "kind": "agentic-workspace/omitted-fields/v1",
                        "omitted_count": len(value) - len(selected_keys),
                    }
                return compacted
            return value

        source_context = payload.get("context", {}) if isinstance(payload.get("context"), dict) else {}
        bounded = {
            key: _compact_hard(payload[key])
            for key in (
                "kind",
                "status",
                "health",
                "target",
                "communication_contract",
                "action_signals",
                "next",
                "next_action",
                "decision_packet",
                "current_decision",
                "evidence_bundle",
                "values",
                "missing",
                "payload_locations",
                "answer",
            )
            if key in payload
        }
        bounded["context"] = {
            key: _compact_hard(source_context.get(key, {}))
            for key in (
                "projection_decision_input",
                "projection_decision_input_consumption",
                "projection_decision_authority",
            )
            if source_context.get(key)
        }
        bounded["projection_reuse"] = payload.get("projection_reuse", {})
        bounded["serialization_budget"] = {
            "status": "detail-withheld",
            "operation": operation,
            "reason": "serialization-budget-exceeded",
            "serialized_bytes": reuse_result.get("observed_cost", {}).get("serialized_bytes", 0),
            "serialization_budget_bytes": budgets.get("serialization_budget_bytes", _DEFAULT_SERIALIZATION_BUDGET_BYTES),
            "inventories_materialized_in_response": False,
            "detail_command": full_detail_command,
        }
        bounded["omitted_detail"] = {
            "kind": "agentic-workspace/omitted-detail/v1",
            "reason": "Use the explicit full-detail command for fields withheld by the serialization budget.",
        }
    return bounded
