#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import json
import math
from contextlib import redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from repo_planning_bootstrap import cli as planning_cli

from agentic_workspace import cli as workspace_cli

JsonRunner = Callable[[list[str]], int]


@dataclass(frozen=True)
class ArtifactSpec:
    kind: str
    label: str
    detail: str
    args: tuple[str, ...] = ()
    paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class MeasurementCase:
    label: str
    workflow_class: str
    question: str
    preferred: ArtifactSpec
    baseline: ArtifactSpec


def _capture_json_command(args: list[str], *, runner: JsonRunner) -> dict[str, Any]:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = runner(args)
    if exit_code != 0:
        raise RuntimeError(f"CLI command failed: {' '.join(args)}")
    return json.loads(buffer.getvalue())


def _approx_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / 4))


def _render_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def _capture_artifact(spec: ArtifactSpec, *, target_root: Path) -> dict[str, Any]:
    if spec.kind == "workspace_command_json":
        payload = _capture_json_command(list(spec.args), runner=workspace_cli.main)
        rendered = _render_json(payload)
        return {
            "kind": spec.kind,
            "label": spec.label,
            "detail": spec.detail,
            "paths": [],
            "command": " ".join(spec.args),
            "artifact_count": 1,
            "file_reads": 0,
            "query_count": 1,
            "rendered": rendered,
        }
    if spec.kind == "planning_command_json":
        payload = _capture_json_command(list(spec.args), runner=planning_cli.main)
        rendered = _render_json(payload)
        return {
            "kind": spec.kind,
            "label": spec.label,
            "detail": spec.detail,
            "paths": [],
            "command": " ".join(spec.args),
            "artifact_count": 1,
            "file_reads": 0,
            "query_count": 1,
            "rendered": rendered,
        }
    if spec.kind == "file_bundle":
        resolved_paths = [target_root / relative for relative in spec.paths]
        missing = [path for path in resolved_paths if not path.exists()]
        if missing:
            missing_list = ", ".join(path.relative_to(target_root).as_posix() for path in missing)
            raise FileNotFoundError(f"Baseline file bundle is missing: {missing_list}")
        rendered = "\n\n".join(
            f"## {path.relative_to(target_root).as_posix()}\n\n{path.read_text(encoding='utf-8')}" for path in resolved_paths
        )
        return {
            "kind": spec.kind,
            "label": spec.label,
            "detail": spec.detail,
            "paths": [path.relative_to(target_root).as_posix() for path in resolved_paths],
            "command": None,
            "artifact_count": len(resolved_paths),
            "file_reads": len(resolved_paths),
            "query_count": 0,
            "rendered": rendered,
        }
    raise ValueError(f"Unsupported artifact kind: {spec.kind}")


def _summarise_pair(*, preferred: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    preferred_text = preferred["rendered"]
    baseline_text = baseline["rendered"]
    preferred_chars = len(preferred_text)
    baseline_chars = len(baseline_text)
    preferred_bytes = len(preferred_text.encode("utf-8"))
    baseline_bytes = len(baseline_text.encode("utf-8"))
    preferred_tokens = _approx_tokens(preferred_text)
    baseline_tokens = _approx_tokens(baseline_text)
    return {
        "preferred": {
            "kind": preferred["kind"],
            "label": preferred["label"],
            "detail": preferred["detail"],
            "command": preferred["command"],
            "paths": preferred["paths"],
            "artifact_count": preferred["artifact_count"],
            "file_reads": preferred["file_reads"],
            "query_count": preferred["query_count"],
            "chars": preferred_chars,
            "bytes": preferred_bytes,
            "approx_tokens": preferred_tokens,
        },
        "baseline": {
            "kind": baseline["kind"],
            "label": baseline["label"],
            "detail": baseline["detail"],
            "command": baseline["command"],
            "paths": baseline["paths"],
            "artifact_count": baseline["artifact_count"],
            "file_reads": baseline["file_reads"],
            "query_count": baseline["query_count"],
            "chars": baseline_chars,
            "bytes": baseline_bytes,
            "approx_tokens": baseline_tokens,
        },
        "savings": {
            "artifacts_saved": baseline["artifact_count"] - preferred["artifact_count"],
            "file_reads_saved": baseline["file_reads"] - preferred["file_reads"],
            "chars_saved": baseline_chars - preferred_chars,
            "char_reduction_percent": round(((baseline_chars - preferred_chars) / baseline_chars) * 100, 1),
            "bytes_saved": baseline_bytes - preferred_bytes,
            "byte_reduction_percent": round(((baseline_bytes - preferred_bytes) / baseline_bytes) * 100, 1),
            "approx_tokens_saved": baseline_tokens - preferred_tokens,
            "approx_token_reduction_percent": round(((baseline_tokens - preferred_tokens) / baseline_tokens) * 100, 1),
        },
    }


def _measure_case(case: MeasurementCase, *, target_root: Path) -> dict[str, Any]:
    preferred = _capture_artifact(case.preferred, target_root=target_root)
    baseline = _capture_artifact(case.baseline, target_root=target_root)
    return {
        "label": case.label,
        "workflow_class": case.workflow_class,
        "question": case.question,
        **_summarise_pair(preferred=preferred, baseline=baseline),
    }


def _build_cases(target_root: Path) -> list[MeasurementCase]:
    target = target_root.as_posix()
    return [
        MeasurementCase(
            label="startup_routing",
            workflow_class="startup and routing",
            question="What is the canonical startup and routing contract for this repo?",
            preferred=ArtifactSpec(
                kind="workspace_command_json",
                label="startup selector",
                detail="Compact startup and routing contract answer.",
                args=("defaults", "--section", "startup", "--format", "json"),
            ),
            baseline=ArtifactSpec(
                kind="file_bundle",
                label="startup prose bundle",
                detail="Broad file-first startup and routing read path.",
                paths=("AGENTS.md", "TODO.md", "tools/AGENT_QUICKSTART.md", "tools/AGENT_ROUTING.md"),
            ),
        ),
        MeasurementCase(
            label="active_planning_restart",
            workflow_class="active planning inspection and restart handoff",
            question="How do I inspect current planning state and continue safely without broad rereading?",
            preferred=ArtifactSpec(
                kind="planning_command_json",
                label="planning summary",
                detail="Compact active planning and resumable state payload.",
                args=("summary", "--target", target, "--format", "json"),
            ),
            baseline=ArtifactSpec(
                kind="file_bundle",
                label="planning prose bundle",
                detail="TODO plus planning prose used as a broad restart path.",
                paths=("TODO.md", "ROADMAP.md", "docs/execplans/README.md", "docs/environment-recovery-contract.md"),
            ),
        ),
        MeasurementCase(
            label="proof_lane_selection",
            workflow_class="proof-lane selection",
            question="What proof lane is enough for the current change shape?",
            preferred=ArtifactSpec(
                kind="workspace_command_json",
                label="proof selector",
                detail="Compact proof-selection answer.",
                args=("defaults", "--section", "proof_selection", "--format", "json"),
            ),
            baseline=ArtifactSpec(
                kind="file_bundle",
                label="proof contract prose bundle",
                detail="Broad prose-first proof guidance read path.",
                paths=("docs/default-path-contract.md", "docs/proof-surfaces-contract.md"),
            ),
        ),
        MeasurementCase(
            label="ownership_lookup",
            workflow_class="ownership lookup",
            question="Who owns active execution state?",
            preferred=ArtifactSpec(
                kind="workspace_command_json",
                label="ownership selector",
                detail="Compact ownership answer for one concern.",
                args=("ownership", "--target", target, "--concern", "active-execution-state", "--format", "json"),
            ),
            baseline=ArtifactSpec(
                kind="file_bundle",
                label="ownership prose bundle",
                detail="Broad ownership contract read path.",
                paths=("AGENTS.md", "docs/ownership-authority-contract.md", ".agentic-workspace/OWNERSHIP.toml"),
            ),
        ),
        MeasurementCase(
            label="setup_jumpstart",
            workflow_class="setup and jumpstart inspection",
            question="What bounded setup or jumpstart follow-through is appropriate in this repo?",
            preferred=ArtifactSpec(
                kind="workspace_command_json",
                label="setup contract answer",
                detail="Compact setup/jumpstart payload for the current repo.",
                args=("setup", "--target", target, "--format", "json"),
            ),
            baseline=ArtifactSpec(
                kind="file_bundle",
                label="setup prose bundle",
                detail="Broader setup/jumpstart and lifecycle guidance read path.",
                paths=("llms.txt", "docs/init-lifecycle.md", "docs/jumpstart-contract.md"),
            ),
        ),
    ]


def measure_lazy_discovery(*, target_root: Path) -> dict[str, Any]:
    measurements = [_measure_case(case, target_root=target_root) for case in _build_cases(target_root)]
    totals = {
        "preferred_artifact_count": sum(item["preferred"]["artifact_count"] for item in measurements),
        "baseline_artifact_count": sum(item["baseline"]["artifact_count"] for item in measurements),
        "artifacts_saved": sum(item["savings"]["artifacts_saved"] for item in measurements),
        "preferred_file_reads": sum(item["preferred"]["file_reads"] for item in measurements),
        "baseline_file_reads": sum(item["baseline"]["file_reads"] for item in measurements),
        "file_reads_saved": sum(item["savings"]["file_reads_saved"] for item in measurements),
        "preferred_queries": sum(item["preferred"]["query_count"] for item in measurements),
        "baseline_queries": sum(item["baseline"]["query_count"] for item in measurements),
        "preferred_bytes": sum(item["preferred"]["bytes"] for item in measurements),
        "baseline_bytes": sum(item["baseline"]["bytes"] for item in measurements),
        "bytes_saved": sum(item["savings"]["bytes_saved"] for item in measurements),
        "preferred_approx_tokens": sum(item["preferred"]["approx_tokens"] for item in measurements),
        "baseline_approx_tokens": sum(item["baseline"]["approx_tokens"] for item in measurements),
        "approx_tokens_saved": sum(item["savings"]["approx_tokens_saved"] for item in measurements),
    }
    totals["artifact_reduction_percent"] = round((totals["artifacts_saved"] / totals["baseline_artifact_count"]) * 100, 1)
    totals["byte_reduction_percent"] = round((totals["bytes_saved"] / totals["baseline_bytes"]) * 100, 1)
    totals["approx_token_reduction_percent"] = round(
        (totals["approx_tokens_saved"] / totals["baseline_approx_tokens"]) * 100,
        1,
    )
    return {
        "schema_version": "lazy-discovery-measurements/v2",
        "target": target_root.as_posix(),
        "method": {
            "rule": (
                "Compare the preferred compact/query-first route for one workflow question against the broader plausible fallback route."
            ),
            "token_proxy": "approx_tokens = ceil(character_count / 4)",
            "artifact_proxy": "count files or query outputs loaded before the first safe action",
            "notes": [
                "This remains a cheap retrieval-size proxy, not model-exact token accounting.",
                (
                    "The expanded tranche mixes compact commands with file-bundle baselines "
                    "when the real fallback path is prose-first rather than a broader "
                    "machine-readable command."
                ),
                (
                    "Correction cost and curation mistakes stay qualitative in the review "
                    "artifact; this script measures retrieval and loading pressure only."
                ),
            ],
        },
        "measurements": measurements,
        "totals": totals,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Measure lazy-discovery savings for compact contract selectors.")
    parser.add_argument("--target", default=".", help="Repository target path for workflow-class measurements.")
    args = parser.parse_args(argv)
    target_root = Path(args.target).resolve()
    print(json.dumps(measure_lazy_discovery(target_root=target_root), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
