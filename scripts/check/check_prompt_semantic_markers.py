from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_RUNTIME = REPO_ROOT / "src" / "agentic_workspace" / "workspace_runtime_primitives.py"

GUARDED_FUNCTIONS = {
    "_architecture_decision_signal",
    "_completion_closeout_inspection_payload",
    "_intent_acknowledgement_payload",
    "_intent_discovery_dialogue_payload",
    "_objective_drift_payload",
    "_is_completion_status_task",
    "_is_config_posture_task",
    "_is_prep_only_handoff_task",
    "_task_intent_promotion_guidance_payload",
    "_vague_outcome_orientation_payload",
}

DENIED_FUNCTION_NAMES = {
    "_task_has_removal_intent",
}

DENIED_LOCAL_NAMES = {
    "broad_markers",
    "completion_markers",
    "direct_markers",
    "durable_markers",
    "future_or_handoff",
    "high_stakes_markers",
    "implementation_blocked",
    "non_direct_markers",
    "posture_markers",
    "prep_or_plan",
    "question_starters",
    "question_terms",
    "removal_intent",
    "removal_markers",
    "retirement_markers",
    "scope_terms",
}

DENIED_MODULE_CONSTANTS = {
    "_ARCHITECTURE_DECISION_MARKERS",
}


def _string_sequence(node: ast.AST) -> bool:
    if not isinstance(node, ast.List | ast.Tuple | ast.Set):
        return False
    return len(node.elts) >= 2 and all(isinstance(item, ast.Constant) and isinstance(item.value, str) for item in node.elts)


def _assigned_names(target: ast.AST) -> list[str]:
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, ast.Tuple | ast.List):
        names: list[str] = []
        for item in target.elts:
            names.extend(_assigned_names(item))
        return names
    return []


def prompt_semantic_marker_findings(source_path: Path = WORKSPACE_RUNTIME) -> list[str]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    findings: list[str] = []
    try:
        source_label = source_path.relative_to(REPO_ROOT)
    except ValueError:
        source_label = source_path

    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = [name for target in node.targets for name in _assigned_names(target)]
            for name in names:
                if name in DENIED_MODULE_CONSTANTS and _string_sequence(node.value):
                    findings.append(f"{source_label}:{node.lineno}: denied prompt marker constant {name}")
        if isinstance(node, ast.FunctionDef) and node.name in DENIED_FUNCTION_NAMES:
            findings.append(f"{source_label}:{node.lineno}: denied prompt semantic classifier {node.name}")
        if not isinstance(node, ast.FunctionDef) or node.name not in GUARDED_FUNCTIONS:
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.Assign):
                names = [name for target in child.targets for name in _assigned_names(target)]
                for name in names:
                    if name in DENIED_LOCAL_NAMES:
                        findings.append(
                            f"{source_label}:{child.lineno}: {node.name} assigns denied prompt semantic marker {name}"
                        )
                    elif name.endswith("_markers") and _string_sequence(child.value):
                        findings.append(
                            f"{source_label}:{child.lineno}: {node.name} assigns prompt marker table {name}"
                        )
    return findings


def main() -> int:
    findings = prompt_semantic_marker_findings()
    if findings:
        print("Hardcoded prompt semantic marker findings:")
        for finding in findings:
            print(f"- {finding}")
        print("Use structural parsing or configured/learned surfaces with explicit authority boundaries instead.")
        return 1
    print("[ok] no hardcoded prompt semantic marker tables in guarded startup/routing functions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
