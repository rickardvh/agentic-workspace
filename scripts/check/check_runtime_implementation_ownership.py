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
    return {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
    }


def _metrics(node: ast.AST) -> tuple[int, int]:
    lines = int(getattr(node, "end_lineno", node.lineno)) - int(node.lineno) + 1
    branches = sum(
        isinstance(child, ast.If | ast.For | ast.AsyncFor | ast.While | ast.Try | ast.Match | ast.BoolOp | ast.IfExp)
        for child in ast.walk(node)
    )
    return lines, branches


def ownership_report(root: Path = REPO_ROOT, *, today: date | None = None) -> dict[str, Any]:
    policy = json.loads((root / POLICY_PATH).read_text(encoding="utf-8"))
    core_path = root / policy["canonical_owner"]
    facade_path = root / policy["compatibility_facade"]
    core_source = core_path.read_text(encoding="utf-8")
    facade_source = facade_path.read_text(encoding="utf-8")
    core_defs = _definitions(ast.parse(core_source))
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
    exception_map = {(item["path"], item["symbol"]): item for item in review["exceptions"]}
    metric_records: list[dict[str, Any]] = []
    current_day = today or date.today()
    for relative_path in review["paths"]:
        tree = ast.parse((root / relative_path).read_text(encoding="utf-8"))
        for symbol, node in _definitions(tree).items():
            lines, branches = _metrics(node)
            if lines <= int(review["default_max_function_lines"]) and branches <= int(review["default_max_branch_nodes"]):
                continue
            exception = exception_map.get((relative_path, symbol))
            metric_records.append({"path": relative_path, "symbol": symbol, "lines": lines, "branch_nodes": branches})
            if exception is None:
                findings.append({"control": "review-scale", "detail": f"{relative_path}:{symbol} exceeds the default budget"})
                continue
            if current_day > date.fromisoformat(exception["expires"]):
                findings.append({"control": "review-scale", "detail": f"{relative_path}:{symbol} exception expired"})
            if not str(exception.get("tracking_issue") or "").strip():
                findings.append({"control": "review-scale", "detail": f"{relative_path}:{symbol} exception lacks an owner"})
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
