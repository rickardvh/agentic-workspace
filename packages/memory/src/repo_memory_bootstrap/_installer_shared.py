from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from repo_memory_bootstrap._ownership import module_root

PROJECT_MARKERS = ("pyproject.toml", "package.json", "Cargo.toml", ".hg")
AGENT_ROOT_MARKERS = (Path("AGENTS.md"), Path("memory"))
MANAGED_ROOT = module_root("memory")
WORKSPACE_SHARED_ROOT = Path(".agentic-workspace")
LEGACY_SYSTEM_ROOT = Path("memory/system")
VERSION_PATH = MANAGED_ROOT / "VERSION.md"
LEGACY_VERSION_PATH = LEGACY_SYSTEM_ROOT / "VERSION.md"
WORKFLOW_PATH = MANAGED_ROOT / "WORKFLOW.md"
WORKSPACE_WORKFLOW_PATH = WORKSPACE_SHARED_ROOT / "WORKFLOW.md"
LEGACY_WORKFLOW_PATH = LEGACY_SYSTEM_ROOT / "WORKFLOW.md"
AGENTS_PATH = Path("AGENTS.md")
MANIFEST_PATH = Path("memory/manifest.toml")
UPGRADE_SOURCE_PATH = MANAGED_ROOT / "UPGRADE-SOURCE.toml"
LEGACY_UPGRADE_SOURCE_PATH = LEGACY_SYSTEM_ROOT / "UPGRADE-SOURCE.toml"
AUDIT_SCRIPT_PATH = Path("scripts/check/check_memory_freshness.py")
BOOTSTRAP_VERSION = 47
BUNDLED_SKILLS_ROOT = Path("skills")
BOOTSTRAP_WORKSPACE_ROOT = MANAGED_ROOT / "bootstrap"
LEGACY_BOOTSTRAP_WORKSPACE_ROOT = Path("memory/bootstrap")
SHIPPED_SKILLS_ROOT = MANAGED_ROOT / "skills"
LEGACY_SHIPPED_SKILLS_ROOT = Path("memory/skills")

CURRENT_MEMORY_BASELINE = (
    Path("memory/current/project-state.md"),
    Path("memory/current/task-context.md"),
)
OPTIONAL_CURRENT_MEMORY_FILES = (Path("memory/current/routing-feedback.md"),)
ROUTING_BASELINE = (Path("memory/index.md"),)
STARTER_EXAMPLE_FILES = (
    Path("memory/domains/example-runtime-boundary.md"),
    Path("memory/invariants/example-response-contract.md"),
    Path("memory/runbooks/example-release-check.md"),
    Path("memory/decisions/example-cli-selection.md"),
)
BOOTSTRAP_WORKSPACE_FILES = (
    BOOTSTRAP_WORKSPACE_ROOT / "README.md",
    BOOTSTRAP_WORKSPACE_ROOT / "skills/install/SKILL.md",
    BOOTSTRAP_WORKSPACE_ROOT / "skills/install/agents/openai.yaml",
    BOOTSTRAP_WORKSPACE_ROOT / "skills/populate/SKILL.md",
    BOOTSTRAP_WORKSPACE_ROOT / "skills/populate/agents/openai.yaml",
    BOOTSTRAP_WORKSPACE_ROOT / "skills/cleanup/SKILL.md",
    BOOTSTRAP_WORKSPACE_ROOT / "skills/cleanup/agents/openai.yaml",
)
CORE_PAYLOAD_SKILL_FILES = (
    SHIPPED_SKILLS_ROOT / "README.md",
    SHIPPED_SKILLS_ROOT / "REGISTRY.json",
    SHIPPED_SKILLS_ROOT / "memory-capture/SKILL.md",
    SHIPPED_SKILLS_ROOT / "memory-capture/agents/openai.yaml",
    SHIPPED_SKILLS_ROOT / "memory-hygiene/SKILL.md",
    SHIPPED_SKILLS_ROOT / "memory-hygiene/agents/openai.yaml",
    SHIPPED_SKILLS_ROOT / "memory-upgrade/SKILL.md",
    SHIPPED_SKILLS_ROOT / "memory-upgrade/agents/openai.yaml",
    SHIPPED_SKILLS_ROOT / "memory-refresh/SKILL.md",
    SHIPPED_SKILLS_ROOT / "memory-refresh/agents/openai.yaml",
    SHIPPED_SKILLS_ROOT / "memory-router/SKILL.md",
    SHIPPED_SKILLS_ROOT / "memory-router/agents/openai.yaml",
)
PAYLOAD_REQUIRED_FILES = (
    AGENTS_PATH,
    Path("memory/index.md"),
    MANIFEST_PATH,
    MANAGED_ROOT / "SKILLS.md",
    WORKFLOW_PATH,
    UPGRADE_SOURCE_PATH,
    Path("memory/current/project-state.md"),
    Path("memory/current/task-context.md"),
    Path("memory/domains/README.md"),
    *STARTER_EXAMPLE_FILES,
    Path("memory/invariants/README.md"),
    Path("memory/runbooks/README.md"),
    Path("memory/mistakes/recurring-failures.md"),
    Path("memory/decisions/README.md"),
    AUDIT_SCRIPT_PATH,
    *BOOTSTRAP_WORKSPACE_FILES,
    *CORE_PAYLOAD_SKILL_FILES,
)
MEMORY_COMPATIBILITY_CONTRACT_FILES = (
    AGENTS_PATH,
    Path("memory/index.md"),
    MANIFEST_PATH,
    MANAGED_ROOT / "SKILLS.md",
    WORKFLOW_PATH,
    Path("memory/current/project-state.md"),
    Path("memory/current/task-context.md"),
    Path("memory/domains/README.md"),
    Path("memory/invariants/README.md"),
    Path("memory/runbooks/README.md"),
    Path("memory/mistakes/recurring-failures.md"),
    Path("memory/decisions/README.md"),
)
MEMORY_LOWER_STABILITY_HELPER_FILES = tuple(
    relative for relative in PAYLOAD_REQUIRED_FILES if relative not in MEMORY_COMPATIBILITY_CONTRACT_FILES
)
FORBIDDEN_PAYLOAD_FILES = (Path("TODO.md"), Path("memory/current/active-decisions.md"), LEGACY_SYSTEM_ROOT / "UPGRADE.md")
OBSOLETE_SHARED_FILES = (LEGACY_SYSTEM_ROOT / "UPGRADE.md",)
FORBIDDEN_PAYLOAD_PREFIXES = (".agent-work/",)
CURRENT_TASK_STALE_DAYS = 30
CURRENT_TASK_MAX_LINES = 80
CURRENT_PROJECT_STATE_STALE_DAYS = 45
CURRENT_PROJECT_STATE_MAX_LINES = 100
ROUTING_FEEDBACK_STALE_DAYS = 45
ROUTING_FEEDBACK_MAX_LINES = 120
ROUTING_FEEDBACK_MAX_RESOLVED = 3
ROUTE_WORKING_SET_TARGET = 3
ROUTE_WORKING_SET_STRONG_WARNING = 5

PROJECT_STATE_REQUIRED_SECTIONS = (
    "Status",
    "Scope",
    "Applies to",
    "Load when",
    "Review when",
    "Current focus",
    "Recent meaningful progress",
    "Blockers",
    "High-level notes",
    "Failure signals",
    "Verify",
    "Verified against",
    "Last confirmed",
)
TASK_CONTEXT_REQUIRED_SECTIONS = (
    "Status",
    "Scope",
    "Active goal",
    "Touched surfaces",
    "Blocking assumptions",
    "Next validation",
    "Resume cues",
    "Last confirmed",
)
ROUTING_FEEDBACK_REQUIRED_SECTIONS = (
    "Status",
    "Scope",
    "Load when",
    "Review when",
    "Missed-note entries",
    "Over-routing entries",
    "Synthesis",
    "Last confirmed",
)
CURRENT_CONTEXT_SUSPICIOUS_HEADINGS = (
    "backlog",
    "roadmap",
    "done today",
    "completed tasks",
    "timeline",
    "sprint",
    "action items",
    "next steps",
)
CURRENT_CONTEXT_SUSPICIOUS_SECTION_RE = re.compile(
    r"^\s{0,3}##\s+(?:done|todo|to do|in progress|completed|history|timeline)\b",
    re.IGNORECASE,
)
CURRENT_CONTEXT_CHRONOLOGY_RE = re.compile(r"^\s*(?:-|\*|\d+\.)\s+20\d{2}-\d{2}-\d{2}\b")

NOTE_TYPE_LINE_LIMITS = {
    "invariant": 80,
    "domain": 160,
    "runbook": 140,
    "recurring-failures": 140,
    "decision": 160,
    "current-overview": CURRENT_PROJECT_STATE_MAX_LINES,
    "current-context": CURRENT_TASK_MAX_LINES,
    "routing-feedback": ROUTING_FEEDBACK_MAX_LINES,
}
ALWAYS_READ_SURFACE = (Path("memory/index.md"),)
ALLOWED_HIGH_LEVEL_NOTES = {
    Path("memory/index.md"),
    Path("memory/current/project-state.md"),
}

WORKFLOW_MARKER_START = "<!-- agentic-memory:workflow:start -->"
WORKFLOW_MARKER_END = "<!-- agentic-memory:workflow:end -->"
WORKFLOW_POINTER_BLOCK = (
    f"{WORKFLOW_MARKER_START}\nRead `.agentic-workspace/memory/WORKFLOW.md` for shared workflow rules.\n{WORKFLOW_MARKER_END}"
)
WORKSPACE_WORKFLOW_MARKER_START = "<!-- agentic-workspace:workflow:start -->"
WORKSPACE_WORKFLOW_MARKER_END = "<!-- agentic-workspace:workflow:end -->"
WORKSPACE_POINTER_BLOCK = (
    f"{WORKSPACE_WORKFLOW_MARKER_START}\nRead `.agentic-workspace/WORKFLOW.md` for shared workflow rules.\n{WORKSPACE_WORKFLOW_MARKER_END}"
)
EMBEDDED_WORKFLOW_HEADINGS = (
    "## Task system boundary",
    "## Memory discipline",
    "## Memory admission rule",
    "## Memory freshness rule",
    "## Memory routing",
    "## Overview file",
    "## Task-context file",
    "## Local working notes (optional)",
)
PLACEHOLDER_RE = re.compile(r"<[A-Z0-9_/-]+>")
DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\b")
VERSION_RE = re.compile(r"^\s*Version:\s*(\d+)\s*$", re.MULTILINE)
MEMORY_PATH_RE = re.compile(r"(?<![A-Za-z0-9_.-])memory/[A-Za-z0-9_./-]+")
MARKDOWN_MEMORY_LINK_RE = re.compile(r"\[[^\]]+\]\((?!https?://)([^)]*memory/[^)]*)\)")
LEGACY_BOOTSTRAP_AGENTS_PHRASES = (
    (
        "Check `memory/skills/README.md` and the skill directories under "
        "`memory/skills/` for a checked-in memory skill whose name or "
        "description matches the task."
    ),
    (
        "Use the matching checked-in skill when it fits; otherwise load only "
        "the memory files routed by `memory/index.md` that are relevant to "
        "the task."
    ),
    (
        "Use the matching checked-in skill when it fits; otherwise read only "
        "the memory files routed by `memory/index.md` that are relevant to "
        "the subsystem you will touch."
    ),
    (
        "Treat a quick `memory/skills/` scan as part of setup in repos that "
        "have checked-in memory skills; this keeps repeatable memory "
        "workflows discoverable instead of implicit."
    ),
    (
        "Treat a quick `memory/skills/` scan as part of setup in repos that "
        "have checked-in memory skills so repeatable procedures are easy to "
        "detect and reuse."
    ),
)

DEFAULT_CORE_DOC_GLOBS = (
    "README.md",
    "docs/**/*.md",
    "CONTRIBUTING.md",
    ".github/**/*.md",
)
DEFAULT_CORE_DOC_EXCLUDE_GLOBS = (
    "AGENTS.md",
    "memory/**/*.md",
    "memory/bootstrap/**/*.md",
)
VALID_CANONICALITY_VALUES = {
    "agent_only",
    "candidate_for_promotion",
    "canonical_elsewhere",
    "deprecated",
}
VALID_TASK_RELEVANCE_VALUES = {"required", "optional"}
VALID_MEMORY_ROLE_VALUES = {"durable_truth", "improvement_signal"}
VALID_SYMPTOM_OF_VALUES = {
    "workflow_friction",
    "guidance_drift",
    "missing_guardrail",
    "architecture_friction",
    "operator_complexity",
}
VALID_PREFERRED_REMEDIATION_VALUES = {
    "docs",
    "skill",
    "script",
    "test",
    "validation",
    "refactor",
    "code",
}
VALID_ELIMINATION_TARGET_VALUES = {"shrink", "promote", "automate", "refactor_away"}
# Six shared terms is a conservative floor that avoids flagging incidental overlap
# while still surfacing likely shadow-doc drift between memory and canonical docs.
SHADOW_DOC_MIN_SHARED_TERMS = 6

OPTIONAL_APPEND_TARGETS = {
    Path("Makefile"): Path("optional/Makefile.fragment.mk"),
    Path("CONTRIBUTING.md"): Path("optional/CONTRIBUTING.fragment.md"),
    Path(".github/pull_request_template.md"): Path("optional/pull_request_template.fragment.md"),
}
OPTIONAL_APPEND_DESCRIPTIONS = {
    Path("Makefile"): "optional convenience target for running the memory freshness audit locally or in CI",
    Path("CONTRIBUTING.md"): "optional contributor guidance fragment",
    Path(".github/pull_request_template.md"): "optional pull request checklist fragment",
}


@dataclass(slots=True)
class Action:
    kind: str
    path: Path
    detail: str = ""
    role: str = ""
    safety: str = ""
    source: str = ""
    category: str = ""
    remediation_kind: str = ""
    remediation_target: str = ""
    remediation_reason: str = ""
    remediation_confidence: str = ""
    memory_action: str = ""
    match_source: str = ""

    def to_dict(self, target_root: Path) -> dict[str, str]:
        relative_path = self.path.relative_to(target_root) if self.path.is_relative_to(target_root) else self.path
        return {
            "kind": self.kind,
            "path": relative_path.as_posix() if isinstance(relative_path, Path) else str(relative_path),
            "detail": self.detail,
            "role": self.role,
            "safety": self.safety,
            "source": self.source,
            "category": self.category,
            "remediation_kind": self.remediation_kind,
            "remediation_target": self.remediation_target,
            "remediation_reason": self.remediation_reason,
            "remediation_confidence": self.remediation_confidence,
            "memory_action": self.memory_action,
            "match_source": self.match_source,
        }


@dataclass(slots=True)
class InstallResult:
    target_root: Path
    dry_run: bool
    mode: str = "augment"
    message: str = ""
    actions: list[Action] = field(default_factory=list)
    detected_version: int | None = None
    bootstrap_version: int = BOOTSTRAP_VERSION
    route_summary: dict[str, object] = field(default_factory=dict)
    missing_note_hint: str = ""
    review_summary: dict[str, object] = field(default_factory=dict)
    review_cases: list[dict[str, object]] = field(default_factory=list)
    sync_summary: dict[str, object] = field(default_factory=dict)
    route_report_summary: dict[str, object] = field(default_factory=dict)
    route_report_feedback_cases: list[dict[str, object]] = field(default_factory=list)
    route_report_fixture_results: list[dict[str, object]] = field(default_factory=list)

    def add(
        self,
        kind: str,
        path: Path,
        detail: str = "",
        *,
        role: str = "",
        safety: str = "",
        source: str = "",
        category: str = "",
        remediation_kind: str = "",
        remediation_target: str = "",
        remediation_reason: str = "",
        remediation_confidence: str = "",
        memory_action: str = "",
        match_source: str = "",
    ) -> None:
        from repo_memory_bootstrap._installer_output import _infer_action_category

        self.actions.append(
            Action(
                kind=kind,
                path=path,
                detail=detail,
                role=role,
                safety=safety,
                source=source,
                category=category or _infer_action_category(kind=kind, path=path, detail=detail, role=role, safety=safety),
                remediation_kind=remediation_kind,
                remediation_target=remediation_target,
                remediation_reason=remediation_reason,
                remediation_confidence=remediation_confidence,
                memory_action=memory_action,
                match_source=match_source,
            )
        )

    def counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for action in self.actions:
            counts[action.kind] = counts.get(action.kind, 0) + 1
        return counts

    def to_dict(self) -> dict[str, object]:
        return {
            "target_root": str(self.target_root),
            "dry_run": self.dry_run,
            "mode": self.mode,
            "message": self.message,
            "detected_version": self.detected_version,
            "bootstrap_version": self.bootstrap_version,
            "actions": [action.to_dict(self.target_root) for action in self.actions],
            "route_summary": self.route_summary,
            "missing_note_hint": self.missing_note_hint,
            "review_summary": self.review_summary,
            "review_cases": self.review_cases,
            "sync_summary": self.sync_summary,
            "route_report_summary": self.route_report_summary,
            "route_report_feedback_cases": self.route_report_feedback_cases,
            "route_report_fixture_results": self.route_report_fixture_results,
        }


@dataclass(frozen=True, slots=True)
class PayloadEntry:
    relative_path: Path
    role: str
    strategy: str
    source_path: Path


@dataclass(frozen=True, slots=True)
class CurrentNoteView:
    path: Path
    exists: bool
    content: str


@dataclass(slots=True)
class CurrentViewResult:
    target_root: Path
    detected_version: int | None = None
    bootstrap_version: int = BOOTSTRAP_VERSION
    notes: list[CurrentNoteView] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "target_root": str(self.target_root),
            "detected_version": self.detected_version,
            "bootstrap_version": self.bootstrap_version,
            "notes": [
                {
                    "path": note.path.as_posix(),
                    "exists": note.exists,
                    "content": note.content,
                }
                for note in self.notes
            ],
        }


@dataclass(frozen=True, slots=True)
class MemoryNoteRecord:
    path: Path
    note_type: str
    canonical_home: Path
    authority: str
    audience: str
    canonicality: str = "agent_only"
    task_relevance: str = "optional"
    subsystems: tuple[str, ...] = ()
    surfaces: tuple[str, ...] = ()
    routes_from: tuple[str, ...] = ()
    stale_when: tuple[str, ...] = ()
    related_validations: tuple[str, ...] = ()
    routing_only: bool = False
    high_level: bool = False
    memory_role: str = ""
    symptom_of: str = ""
    preferred_remediation: str = ""
    improvement_candidate: bool = False
    improvement_note: str = ""
    elimination_target: str = ""
    retention_justification: str = ""


@dataclass(frozen=True, slots=True)
class MemoryManifest:
    path: Path
    version: int
    notes: tuple[MemoryNoteRecord, ...]
    routing_only: tuple[Path, ...] = ()
    high_level: tuple[Path, ...] = ()
    canonical_dirs: tuple[Path, ...] = ()
    task_board_globs: tuple[str, ...] = ()
    core_doc_globs: tuple[str, ...] = ()
    core_doc_exclude_globs: tuple[str, ...] = ()
    forbid_core_docs_depend_on_memory: bool = False


@dataclass(frozen=True, slots=True)
class RemediationRecommendation:
    kind: str
    target_path_hint: str
    reason: str
    confidence: str
    memory_action: str


class RepoDetectionError(ValueError):
    """Raised when the installer cannot safely determine the target root."""
