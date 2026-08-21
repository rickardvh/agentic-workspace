"""Concrete workspace-owned context-authority operations."""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path
from typing import Any, Callable

from agentic_workspace._context_authority_owner_protocol import _issue_owner_result

_SPECS: dict[str, tuple[str, str, str, str]] = {
    "system-intent": (
        "agentic_workspace.workspace_runtime_core.system_intent",
        "agentic-workspace/system-intent-mirror/v1",
        "system-intent.sync",
        "system-intent durable-purpose contract",
    ),
    "architecture-principles": (
        "agentic_workspace.workspace_runtime_core.architecture_principles",
        "agentic-workspace/architecture-principles-status/v1",
        "architecture-principles.route",
        "system-intent architecture-principles section",
    ),
    "scoped-instructions": (
        "agentic_workspace.workspace_runtime_core.scoped_instruction_routing",
        "agentic-workspace/scoped-instruction-selection/v1",
        "workspace.instructions.route",
        "repository scoped Markdown instruction directory with thin AGENTS fallback",
    ),
    "ownership": (
        "agentic_workspace.workspace_runtime_core.ownership",
        "agentic-workspace/ownership-selection/v1",
        "ownership.classify-paths",
        "ownership manifest schema and authority surfaces",
    ),
    "assignment": (
        "agentic_workspace.assignment_gate",
        "agentic-workspace/assignment-gate/v1",
        "assignment.resolve-target",
        "workspace assignment/target routing config",
    ),
    "autopilot-executor": (
        "agentic_workspace.autopilot_executor",
        "agentic-workspace/autopilot-executor-binding/v1",
        "autopilot.executor.bind",
        "workspace delegated-run executor kernel",
    ),
    "skills": (
        "agentic_workspace.workspace_runtime_core.skill_dependency_resolver",
        "agentic-workspace/skill-dependency-closure/v1",
        "workspace.skills.resolve-dependencies",
        "workspace skill dependency closure contract",
    ),
    "target-guidance": (
        "agentic_workspace.target_guidance",
        "agentic-workspace/target-guidance/v1",
        "target-guidance.resolve",
        "workspace target guidance config",
    ),
    "terminal-outcome": (
        "agentic_workspace.final_response_admission",
        "agentic-workspace/terminal-outcome/v1",
        "terminal-outcome.inspect",
        "workspace final-response outcome admission",
    ),
}


def _text_semantics(path: Path, headings: list[str], terms: list[str] | None = None) -> tuple[str, str, dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return "unavailable", "owner-source-unreadable", {"source_format": "markdown", "parse_status": "invalid", "error": str(exc)}
    declared_headings = {line.strip() for line in text.splitlines() if line.strip().startswith("#")}
    missing_headings = [heading for heading in headings if heading not in declared_headings]
    missing_terms = [term for term in (terms or []) if term.lower() not in text.lower()]
    valid = bool(text.strip()) and not missing_headings and not missing_terms
    return (
        "current" if valid else "invalid",
        "" if valid else "owner-source-contract-marker-missing",
        {
            "source_format": "markdown",
            "parse_status": "valid" if valid else "invalid",
            "required_headings": headings,
            "missing_required_keys": missing_headings + missing_terms,
            "population": {"status": "present" if valid else "invalid"},
        },
    )


def _toml_semantics(path: Path, required: list[str]) -> tuple[str, str, dict[str, Any]]:
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        payload = {}
    missing = [key for key in required if key not in payload]
    valid = bool(payload) and not missing
    return (
        "current" if valid else "invalid",
        "" if valid else "owner-source-schema-invalid" if not payload else "owner-source-required-key-missing",
        {
            "source_format": "toml",
            "parse_status": "valid" if valid else "invalid",
            "required_keys": required,
            "missing_required_keys": missing,
            "population": {"status": "present" if valid else "invalid"},
        },
    )


def _module_semantics(path: Path, symbols: list[str]) -> tuple[str, str, dict[str, Any]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
    except (OSError, SyntaxError):
        tree = None
    defined: set[str] = set()
    if tree is not None:
        defined = {node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
        for node in tree.body:
            if isinstance(node, ast.Assign):
                defined.update(target.id for target in node.targets if isinstance(target, ast.Name))
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                defined.add(node.target.id)
    missing = [symbol for symbol in symbols if symbol not in defined]
    valid = tree is not None and not missing and bool(defined)
    return (
        "current" if valid else "invalid",
        "" if valid else "owner-module-symbol-missing" if tree is not None else "owner-module-syntax-invalid",
        {
            "source_format": "python-module",
            "parse_status": "valid" if valid else "invalid",
            "required_symbols": symbols,
            "missing_symbols": missing,
            "population": {"status": "present" if valid else "invalid"},
        },
    )


def _skill_semantics(root: Path) -> tuple[str, str, dict[str, Any], dict[str, Any]]:
    try:
        from agentic_workspace import workspace_runtime_core as runtime_core

        diagnostics = runtime_core._skill_dependency_diagnostics(target_root=root)  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover - defensive owner boundary.
        diagnostics = [{"reason_code": "skill-dependency-resolution-failed", "message": str(exc)}]
    current = not diagnostics
    closure = {
        "kind": "agentic-workspace/skill-dependency-closure/v1",
        "status": "satisfied" if current else "unsatisfied",
        "diagnostic_count": len(diagnostics),
        "diagnostics": diagnostics[:5],
    }
    return (
        "current" if current else "stale",
        "" if current else "skill-dependency-closure-unsatisfied",
        {
            "source_format": "skill-registry",
            "parse_status": "valid" if current else "invalid",
            "population": {"status": "present" if current else "invalid"},
        },
        {"skill_dependency_closure": closure},
    )


def _scoped_instruction_semantics(path: Path, root: Path) -> tuple[str, str, dict[str, Any], dict[str, Any]]:
    if not path.is_dir():
        status, reason, schema = _text_semantics(path, [], ["Authority marker:", "agentic-workspace:workflow:start", "Ordinary route:"])
        return status, reason, schema, {"compatibility_source": "thin-agent-adapter"}
    from agentic_workspace.scoped_instructions import instruction_documents

    documents = instruction_documents(root)
    diagnostics = [{"source_ref": document.source_ref, **diagnostic} for document in documents for diagnostic in document.diagnostics]
    current = bool(documents) and not diagnostics
    return (
        "current" if current else "invalid",
        "" if current else "owner-source-schema-invalid",
        {
            "source_format": "scoped-markdown-directory",
            "parse_status": "valid" if current else "invalid",
            "instruction_count": len(documents),
            "diagnostic_count": len(diagnostics),
            "population": {"status": "present" if current else "invalid"},
        },
        {"instruction_diagnostics": diagnostics[:10], "compatibility_source": "canonical-scoped-markdown"},
    )


def _semantic_resolver(surface: str, chosen: Path, root: Path) -> tuple[str, str, dict[str, Any], dict[str, Any]]:
    if surface == "system-intent":
        status, reason, schema = _text_semantics(chosen, ["# System Intent", "## Purpose", "## Governing intents"])
    elif surface == "architecture-principles":
        status, reason, schema = _text_semantics(chosen, ["## Governing intents"], ["generated", "runtime", "contract"])
    elif surface == "scoped-instructions":
        return _scoped_instruction_semantics(chosen, root)
    elif surface == "ownership":
        status, reason, schema = _toml_semantics(chosen, ["schema_version", "managed_surfaces", "authority_surfaces"])
    elif surface in {"assignment", "target-guidance"}:
        status, reason, schema = _toml_semantics(chosen, ["schema_version", "workspace"])
    elif surface == "autopilot-executor":
        status, reason, schema = _module_semantics(chosen, ["delegated_worker_kernel", "assignment_lifecycle"])
    elif surface == "terminal-outcome":
        status, reason, schema = _module_semantics(chosen, ["final_response", "terminal"])
    elif surface == "skills":
        return _skill_semantics(root)
    else:  # pragma: no cover - registration guards this path.
        raise ValueError(f"unsupported workspace context owner surface: {surface}")
    return status, reason, schema, {}


def workspace_owner_operation(surface: str) -> Callable[..., dict[str, Any]]:
    spec = _SPECS.get(surface)
    if spec is None:
        raise ValueError(f"workspace context owner is not registered for {surface!r}")

    def run(**kwargs: Any) -> dict[str, Any]:
        if kwargs.get("owner_evidence") is not None or kwargs.get("adapter_id") is not None:
            raise ValueError("owner evidence must not carry caller-provided producer identity or receipts")
        if kwargs.get("source_specific"):
            raise ValueError(f"{surface} owner operation derives semantic evidence from its canonical subsystem")
        status, reason, schema, specific = _semantic_resolver(surface, kwargs["chosen"], kwargs["root"])
        lifecycle = {
            "status": "current" if status == "current" else "repair-required",
            "reason": reason,
            "owner_boundary": spec[3],
            "repair_operation_id": spec[2],
            "repair_owner": spec[0],
        }
        population = dict(schema.get("population") or {"status": "present" if status == "current" else "invalid"})
        supersession = {
            "status": "not-superseded" if status == "current" else "unknown-until-repair",
            "supersedes": "",
            "superseded_by": "",
            "currentness_basis": "owner operation source and selection revisions",
        }
        return _issue_owner_result(
            surface=surface,
            producer=spec[0],
            result_kind=spec[1],
            operation_id=spec[2],
            owner=kwargs.get("owner"),
            root=kwargs["root"],
            chosen=kwargs["chosen"],
            revision=kwargs["revision"],
            git_head=kwargs["git_head"],
            selection=kwargs["selection"],
            status=status,
            reason=reason,
            owner_boundary=spec[3],
            schema_backing=schema,
            lifecycle=lifecycle,
            population=population,
            supersession=supersession,
            surface_specific=specific,
            executor=f"agentic_workspace.context_authority_workspace_owners.{surface}",
        )

    return run
