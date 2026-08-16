from __future__ import annotations

import argparse
import ast
import json
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = Path("src/agentic_workspace/contracts/runtime_implementation_ownership.json")


def _definitions(tree: ast.Module) -> dict[str, ast.AST]:
    return {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)}


def _metrics(node: ast.AST) -> tuple[int, int, int, int]:
    start_line = int(getattr(node, "lineno", 0))
    lines = int(getattr(node, "end_lineno", start_line)) - start_line + 1
    branches = sum(
        isinstance(child, ast.If | ast.For | ast.AsyncFor | ast.While | ast.Try | ast.Match | ast.BoolOp | ast.IfExp)
        for child in ast.walk(node)
    )
    body = getattr(node, "body", [])
    segments = [
        int(getattr(child, "end_lineno", child.lineno)) - int(child.lineno) + 1
        for child in body
        if not isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
    ]
    fan_out = len({child.func.id for child in ast.walk(node) if isinstance(child, ast.Call) and isinstance(child.func, ast.Name)})
    return lines, branches, max(segments, default=lines), fan_out


def _file_metrics(source: str) -> dict[str, int]:
    tree = ast.parse(source)
    direct_calls = {
        child.func.id if isinstance(child.func, ast.Name) else child.func.attr
        for child in ast.walk(tree)
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Name | ast.Attribute)
    }
    return {
        "lines": len(source.splitlines()),
        "top_level_symbols": len(_definitions(tree)),
        "direct_policy_fan_out": len(direct_calls),
    }


def _imported_symbols(tree: ast.Module, module: str) -> set[str]:
    return {
        alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == module
        for alias in node.names
    }


def _alternate_assembler_symbols(tree: ast.Module, decision_fields: set[str], minimum_fields: int) -> list[str]:
    symbols: list[str] = []
    for symbol, node in _definitions(tree).items():
        for child in ast.walk(node):
            if not isinstance(child, ast.Dict):
                continue
            keys = {key.value for key in child.keys if isinstance(key, ast.Constant) and isinstance(key.value, str)}
            if len(keys & decision_fields) >= minimum_fields:
                symbols.append(symbol)
                break
    return sorted(symbols)


def ownership_report(root: Path = REPO_ROOT, *, today: date | None = None) -> dict[str, Any]:
    policy = json.loads((root / POLICY_PATH).read_text(encoding="utf-8"))
    core_path = root / policy["canonical_owner"]
    facade_path = root / policy["compatibility_facade"]
    core_source = core_path.read_text(encoding="utf-8")
    facade_source = facade_path.read_text(encoding="utf-8")
    core_tree = ast.parse(core_source)
    core_defs = _definitions(core_tree)
    facade_defs = _definitions(ast.parse(facade_source))
    findings: list[dict[str, str]] = []
    facade_contract = policy["facade_contract"]
    facade_lines = len(facade_source.splitlines())
    if facade_lines > int(facade_contract["max_lines"]):
        findings.append({"control": "compatibility-facade", "detail": f"facade has {facade_lines} lines"})
    if len(facade_defs) > int(facade_contract["max_function_or_class_definitions"]):
        findings.append({"control": "compatibility-facade", "detail": "facade contains hand-maintained definitions"})
    required_owner = str(facade_contract["required_owner_module"])
    if required_owner not in facade_source or "sys.modules[__name__] = _canonical_runtime" not in facade_source:
        findings.append({"control": "compatibility-facade", "detail": "canonical module identity alias is missing"})

    shared = sorted(core_defs.keys() & facade_defs.keys())
    if len(shared) > int(policy["duplicate_definition_budget"]):
        findings.append({"control": "duplicate-definitions", "detail": f"shared definitions: {', '.join(shared[:5])}"})

    review = policy["review_scale"]
    lifecycle = review.get("exception_lifecycle", {})
    if lifecycle.get("supersedes_tracking_issue") != "#2455" or not lifecycle.get("removal_owner") or not lifecycle.get("reason"):
        findings.append({"control": "review-scale", "detail": "review-scale exceptions lack a durable post-#2455 removal owner and reason"})
    candidate_inventory = review.get("candidate_inventory", [])
    ranks = [item.get("rank") for item in candidate_inventory]
    if ranks != list(range(1, len(candidate_inventory) + 1)) or not any(item.get("status") == "extracted" for item in candidate_inventory):
        findings.append({"control": "candidate-inventory", "detail": "ranked extraction candidates must include one extracted authority family"})
    extracted = next((item for item in candidate_inventory if item.get("status") == "extracted"), {})
    extracted_owner = root / str(extracted.get("canonical_owner") or "")
    if not extracted_owner.is_file() or str(extracted.get("canonical_owner") or "") not in core_source.replace(".", "/"):
        # Import spelling is checked separately below because paths and module names use different separators.
        if "from agentic_workspace.operating_decision import" not in core_source:
            findings.append({"control": "candidate-inventory", "detail": "extracted operating-decision owner lacks a narrow runtime facade import"})
    extraction_proof = extracted.get("extraction_proof", {})
    owner_module = str(extraction_proof.get("owner_module") or "")
    allowed_imports = set(extraction_proof.get("facade_imports") or [])
    observed_imports = _imported_symbols(core_tree, owner_module)
    if not allowed_imports or observed_imports != allowed_imports:
        findings.append(
            {
                "control": "candidate-extraction-proof",
                "detail": "operating-decision facade imports differ from the recorded canonical-owner boundary",
            }
        )
    decision_fields = set(extraction_proof.get("decision_shaped_fields") or [])
    minimum_fields = int(extraction_proof.get("alternate_assembler_minimum_fields") or 2)
    alternate_assemblers = _alternate_assembler_symbols(core_tree, decision_fields, minimum_fields)
    if alternate_assemblers:
        findings.append(
            {
                "control": "candidate-extraction-proof",
                "detail": f"runtime facade can independently assemble decision authority: {', '.join(alternate_assemblers)}",
            }
        )
    recorded_after = extraction_proof.get("after", {})
    observed_after = {
        "authority_owner_files": 1 if extracted_owner.is_file() else 0,
        "facade_imported_owner_symbols": len(observed_imports),
        "facade_alternate_assembler_symbols": len(alternate_assemblers),
    }
    if recorded_after != observed_after:
        findings.append(
            {
                "control": "candidate-extraction-proof",
                "detail": "recorded operating-decision after-metrics do not match the reachable facade boundary",
            }
        )

    file_metric_records: list[dict[str, Any]] = []
    for ratchet in review.get("file_ratchets", []):
        relative_path = str(ratchet["path"])
        metrics = _file_metrics((root / relative_path).read_text(encoding="utf-8"))
        file_metric_records.append({"path": relative_path, **metrics})
        for metric, limit_key in (
            ("lines", "max_lines"),
            ("top_level_symbols", "max_top_level_symbols"),
            ("direct_policy_fan_out", "max_direct_policy_fan_out"),
        ):
            if metrics[metric] > int(ratchet[limit_key]):
                findings.append({"control": "file-ratchet", "detail": f"{relative_path} {metric} grew beyond its ratchet"})
    exception_map = {(item["path"], item["symbol"]): item for item in review["exceptions"]}
    metric_records: list[dict[str, Any]] = []
    current_day = today or date.today()
    for relative_path in review["paths"]:
        tree = ast.parse((root / relative_path).read_text(encoding="utf-8"))
        for symbol, node in _definitions(tree).items():
            lines, branches, segment_lines, fan_out = _metrics(node)
            if lines <= int(review["default_max_function_lines"]) and branches <= int(review["default_max_branch_nodes"]):
                continue
            exception = exception_map.get((relative_path, symbol))
            metric_records.append(
                {
                    "path": relative_path,
                    "symbol": symbol,
                    "lines": lines,
                    "branch_nodes": branches,
                    "largest_policy_effect_segment_lines": segment_lines,
                    "direct_fan_out": fan_out,
                }
            )
            if exception is None:
                findings.append({"control": "review-scale", "detail": f"{relative_path}:{symbol} exceeds the default budget"})
                continue
            if current_day > date.fromisoformat(exception["expires"]):
                findings.append({"control": "review-scale", "detail": f"{relative_path}:{symbol} exception expired"})
            if not str(exception.get("tracking_issue") or "").strip():
                findings.append({"control": "review-scale", "detail": f"{relative_path}:{symbol} exception lacks an owner"})
            if segment_lines > int(review["max_policy_effect_segment_lines"]):
                findings.append(
                    {"control": "review-scale", "detail": f"{relative_path}:{symbol} has a policy/effect segment of {segment_lines} lines"}
                )
            if lines > int(exception["max_lines"]) or branches > int(exception["max_branch_nodes"]):
                findings.append({"control": "review-scale", "detail": f"{relative_path}:{symbol} grew beyond its ratchet"})

    return {
        "kind": "agentic-workspace/runtime-implementation-ownership-readiness/v1",
        "status": "ready" if not findings else "blocked",
        "canonical_owner": policy["canonical_owner"],
        "compatibility_facade": policy["compatibility_facade"],
        "metrics": {
            "before": policy["migration_baseline"],
            "after": {
                "shared_top_level_definitions": len(shared),
                "primitive_module_lines": facade_lines,
                "canonical_top_level_definitions": len(core_defs),
            },
            "review_scale_exceptions": metric_records,
            "file_ratchets": file_metric_records,
            "representative_working_set": {
                "before": review["representative_working_set"]["before"],
                "after": {
                    "runtime_owner_files": 1,
                    "shared_symbols": len(shared),
                    "largest_audited_segment_lines": max(
                        (item["largest_policy_effect_segment_lines"] for item in metric_records), default=0
                    ),
                    "max_direct_fan_out": max((item["direct_fan_out"] for item in metric_records), default=0),
                },
            },
            "candidate_extraction": {
                "authority_family": extracted.get("authority_family"),
                "before": extraction_proof.get("before", {}),
                "after": observed_after,
                "facade_imports": sorted(observed_imports),
                "alternate_assembler_symbols": alternate_assemblers,
            },
        },
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check canonical runtime ownership and review-scale ratchets.")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    report = ownership_report(args.root.resolve())
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    elif report["status"] == "ready":
        after = report["metrics"]["after"]
        print(
            "Runtime implementation ownership: ready "
            f"(duplicates={after['shared_top_level_definitions']}, facade_lines={after['primitive_module_lines']})"
        )
    else:
        print("Runtime implementation ownership: blocked")
        for finding in report["findings"]:
            print(f"- [{finding['control']}] {finding['detail']}")
    return 0 if report["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
