from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agentic_workspace.config import DelegationOutcomeRecord
from agentic_workspace.contracts import python_primitive_support
from agentic_workspace.target_evidence import assignment_decision_from_policy, target_evidence_posture

ROOT = Path(__file__).resolve().parents[3]
BRIDGE = Path(__file__).with_name("codex_context_cost_bridge.py")
TASK_CLASS = "validation"
SCOPE_CLASS = "issue-2818-multi-slice"
READ_FIRST = [
    "src/agentic_workspace/contracts/schemas/assignment_context_cost.schema.json",
    "src/agentic_workspace/contracts/python_primitive_support.py",
    "src/agentic_workspace/target_evidence.py",
    "src/agentic_workspace/workspace_runtime_core.py",
    "tests/test_external_operation_clients.py",
    "tests/test_workspace_config_cli.py",
]


def codex_command() -> str:
    return shutil.which("codex.cmd") or shutil.which("codex") or "codex"


def working_tree_fingerprint() -> str:
    digest = hashlib.sha256()
    diff = subprocess.run(["git", "diff", "--binary", "HEAD"], cwd=ROOT, capture_output=True, check=True).stdout
    digest.update(diff)
    untracked = (
        subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard", "-z"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        )
        .stdout.decode("utf-8")
        .split("\0")
    )
    for relative in sorted(path for path in untracked if path):
        digest.update(relative.encode("utf-8"))
        digest.update((ROOT / relative).read_bytes())
    return f"sha256:{digest.hexdigest()}"


def assignment_packet(*, target: str, model: str, head: str) -> dict[str, Any]:
    packet: dict[str, Any] = {
        "kind": "agentic-workspace/assignment-export-packet/v1",
        "assignment_id": f"issue-2818-supported-host-{target}",
        "assignment_revision": f"git:{head}",
        "run_id": f"issue-2818-{target}-{head[:12]}",
        "target": target,
        "assignment_identity": {
            "revision": f"git:{head}",
            "human_intent": (
                "Validate three #2818 slices: the neutral context-cost contract and unknown handling; "
                "capability-first target/transport ranking; and dispatch enforcement of the selected transport. "
                "Use read-only file inspection and focused pytest only. Do not run Agentic Workspace, make, sync, "
                "generators, formatters, or git commands. Report one concise summary without changing files."
            ),
            "task_class": TASK_CLASS,
            "scope_class": SCOPE_CLASS,
            "role": "validator",
            "target": target,
            "allowed_paths": READ_FIRST,
            "allowed_effects": ["read", "execute-focused-validation"],
            "prohibited_effects": ["repo-write", "network", "proof-authority", "completion-authority"],
            "required_inputs": ["current checkout", "the six exact read-first references"],
            "read_first": READ_FIRST,
            "proof_obligation_id": "issue-2818-supported-host-observation",
            "proof_obligation_revision": f"git:{head}",
            "stop_conditions": [
                "a required reference is unavailable",
                "validation would require a repository write or network access",
                "the three bounded slices cannot be evaluated independently",
                "validation would require make, sync, generation, formatting, or a git command",
            ],
            "claim_authority": {
                "worker_result": "evidence-only",
                "proof": "orchestrator-owned",
                "integration": "orchestrator-owned",
                "completion": "orchestrator-owned",
            },
            "dispatch_adapter": {
                "kind": "process",
                "command": [
                    sys.executable,
                    str(BRIDGE),
                    "--metrics-file",
                    "{metrics_file}",
                    "--output-file",
                    "{output_file}",
                    "--output-schema",
                    "{output_schema}",
                    "--target-root",
                    "{target_root}",
                    "--model",
                    "{model}",
                    "--codex-command",
                    codex_command(),
                ],
                "output_mode": "json-file",
                "timeout_seconds": 900,
                "model": model,
                "execution_methods": ["cli"],
            },
        },
        "return_contract": {
            "kind": "agentic-workspace/delegated-return/v1",
            "required_fields": [
                "assignment_revision",
                "run_id",
                "target",
                "changed_paths",
                "summary",
                "stop_conditions_hit",
            ],
            "worker_proof_authority": False,
            "worker_completion_authority": False,
        },
    }
    packet["worker_context"] = python_primitive_support._assignment_worker_context(packet)
    return packet


def execute_run(*, target: str, model: str, head: str) -> dict[str, Any]:
    packet = assignment_packet(target=target, model=model, head=head)
    prompt = python_primitive_support._assignment_export_prompt(packet)
    before_fingerprint = working_tree_fingerprint()
    receipt = python_primitive_support._dispatch_assignment_packet(
        packet=packet,
        prompt=prompt,
        target_root=ROOT,
        transport="cli",
    )
    after_fingerprint = working_tree_fingerprint()
    returned = receipt.get("returned_work") if isinstance(receipt.get("returned_work"), dict) else {}
    return {
        "target": target,
        "model": model,
        "status": receipt.get("status"),
        "reason": receipt.get("reason"),
        "context_cost": receipt.get("context_cost"),
        "return_boundary": {
            "changed_paths": returned.get("changed_paths"),
            "stop_conditions_hit": returned.get("stop_conditions_hit"),
            "summary_present": bool(returned.get("summary")),
            "worker_proof_authority": False,
            "worker_completion_authority": False,
        },
        "raw_transcript_checked_in": False,
        "workspace_mutation_observed": before_fingerprint != after_fingerprint,
    }


def cost_record(run: dict[str, Any], *, recorded_at: str) -> DelegationOutcomeRecord:
    return DelegationOutcomeRecord(
        recorded_at=recorded_at,
        delegation_target=str(run["target"]),
        task_class=TASK_CLASS,
        scope_class=SCOPE_CLASS,
        outcome="success" if run.get("status") == "returned" else "failed",
        handoff_sufficiency="sufficient" if run.get("status") == "returned" else "insufficient",
        review_burden="normal",
        escalation_required=run.get("status") != "returned",
        authority="aw-proof",
        confidence="high",
        context_cost=run.get("context_cost"),
    )


def decision_replay(runs: list[dict[str, Any]], *, recorded_at: str) -> dict[str, Any]:
    posture = target_evidence_posture(
        target_root=None,
        profiles=(),
        records=[cost_record(run, recorded_at=recorded_at) for run in runs],
    )
    decision = assignment_decision_from_policy(
        assignment_policy={
            "assignment_policy": {"value": "required-best-fit"},
            "current_target": {"value": "codex_sol"},
            "binding": {"enforceable": True},
        },
        runtime_resolution={
            "recommendation": "stay-local",
            "capability_context": {"task_class": TASK_CLASS, "scope_class": SCOPE_CLASS},
            "profile_recommendations": [
                {
                    "name": "codex_sol",
                    "target_id": "codex_sol",
                    "recommendation": "recommended",
                    "score": 10,
                    "cost_class": "premium",
                    "latency_class": "slow",
                    "capability_mismatch": False,
                    "location": "local",
                    "execution_methods": ["cli"],
                    "human_control_modes": ["auto"],
                },
                {
                    "name": "codex_luna",
                    "target_id": "codex_luna",
                    "recommendation": "recommended",
                    "score": 10,
                    "cost_class": "cheap",
                    "latency_class": "fast",
                    "capability_mismatch": False,
                    "location": "external",
                    "execution_methods": ["cli"],
                    "human_control_modes": ["auto"],
                },
            ],
        },
        target_evidence=posture,
    )
    return {
        "decision": decision["decision"],
        "selected_target": decision["selected_target"],
        "selected_transport": decision["selected_transport"],
        "candidate_scores": [
            {
                "target": candidate["target"],
                "eligible": candidate["eligible"],
                "expected_burden": candidate["ranking_components"]["expected_burden"],
                "target_cost_class": candidate["ranking_components"]["target_cost_class"],
                "target_latency_class": candidate["ranking_components"]["target_latency_class"],
                "transport_context_cost": candidate["ranking_components"]["transport_context_cost"],
                "total": candidate["ranking_components"]["total"],
                "transport_options": candidate["transport_options"],
            }
            for candidate in decision["candidate_scores"]
        ],
    }


def token_total(run: dict[str, Any]) -> int | None:
    cost = run.get("context_cost")
    if not isinstance(cost, dict):
        return None
    input_tokens = cost.get("effective_input_tokens")
    output_tokens = cost.get("output_tokens")
    if not isinstance(input_tokens, int) or not isinstance(output_tokens, int):
        return None
    return input_tokens + output_tokens


def build_evidence(*, luna: dict[str, Any], sol: dict[str, Any], head: str, observed_at: str) -> dict[str, Any]:
    luna_total = token_total(luna)
    sol_total = token_total(sol)
    delta = luna_total - sol_total if luna_total is not None and sol_total is not None else None
    luna_elapsed = luna.get("context_cost", {}).get("elapsed_ms")
    sol_elapsed = sol.get("context_cost", {}).get("elapsed_ms")
    elapsed_delta = luna_elapsed - sol_elapsed if isinstance(luna_elapsed, int) and isinstance(sol_elapsed, int) else None
    return {
        "kind": "agentic-workspace/assignment-context-cost-dogfood/v1",
        "issue": "#2818",
        "observed_at": observed_at,
        "source_head": head,
        "supported_host": {
            "adapter": "codex exec JSONL bridge",
            "cli_version": subprocess.run([codex_command(), "--version"], text=True, capture_output=True, check=False).stdout.strip(),
            "portable_core_fields": "agentic-workspace/assignment-context-cost/v1",
            "provider_event_projection_owner": BRIDGE.relative_to(ROOT).as_posix(),
            "provider_event_projection_sha256": hashlib.sha256(BRIDGE.read_bytes()).hexdigest(),
            "adapter_context_controls": [
                "ephemeral session",
                "ignore user configuration while retaining host execution-policy rules",
                "disable broad project-document preload",
                "automatic command review with assignment-level write prohibition",
                "exact assignment read-first references",
            ],
            "raw_transcript_checked_in": False,
            "workspace_mutation_observed": any(run["workspace_mutation_observed"] for run in (luna, sol)),
        },
        "historical_regression": {
            "source": "tools/model-cli-harness/external-agent-evaluation/nonlocal-delegation-dogfood-2026-08-27.json",
            "assignment_packet_bytes": 3662,
            "rendered_prompt_bytes": 3913,
            "effective_input_tokens": 81752,
            "cached_input_tokens": 62464,
            "output_tokens": 1591,
            "inflation_boundary": "between AW semantic prompt rendering and effective supported-host worker input",
            "token_savings_claimed": False,
        },
        "substantive_task": {
            "task_class": TASK_CLASS,
            "scope_class": SCOPE_CLASS,
            "slices": [
                "neutral context-cost contract and explicit unknown handling",
                "capability-first target and transport ranking",
                "dispatch enforcement of the cost-selected transport",
            ],
            "read_first": READ_FIRST,
            "writes_allowed": False,
        },
        "runs": [luna, sol],
        "decision_replay": decision_replay([luna, sol], recorded_at=observed_at),
        "before_after": {
            "delegated_bounded_luna_total_tokens": luna_total,
            "all_strong_local_sol_total_tokens": sol_total,
            "delegated_minus_local_tokens": delta,
            "luna_minus_sol_elapsed_ms": elapsed_delta,
            "comparison_posture": (
                "luna-more-tokens-but-cheaper-and-faster-profile"
                if isinstance(delta, int) and delta > 0 and isinstance(elapsed_delta, int) and elapsed_delta < 0
                else "delegated-lower-worker-token-count"
                if isinstance(delta, int) and delta < 0
                else "delegated-not-lower-on-observed-worker-tokens"
                if isinstance(delta, int)
                else "insufficient-observable-token-data"
            ),
            "economic_context": {
                "codex_luna": {"cost_class": "cheap", "latency_class": "fast"},
                "codex_sol": {"cost_class": "premium", "latency_class": "slow"},
                "authority": "maintainer-confirmed target-profile classification",
                "portable_price_normalization": None,
            },
            "plausibility": (
                "The Sol run is a conservative all-strong/current-target baseline using the same bounded assignment and host. "
                "It excludes the orchestrator's already-spent shaping and integration tokens, so it cannot overstate local cost."
            ),
            "token_savings_claimed": False,
            "claim_limit": (
                "Luna may use more observed tokens while remaining materially cheaper and faster through its target profile. "
                "Without a portable current price table, the evidence may select Luna through declared economic priors but "
                "does not convert that into a numeric savings claim."
            ),
        },
        "claim_boundary": (
            "This evidence proves a current supported-host measurement and cost-aware replay. It does not generalize model quality, "
            "treat worker output as proof, retain raw transcripts, or claim savings unsupported by total successful-completion cost."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Capture current supported-host context-cost evidence for issue #2818.")
    parser.add_argument("--luna-model", default="gpt-5.6-luna")
    parser.add_argument("--sol-model", default="gpt-5.6-sol")
    args = parser.parse_args(argv)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip()
    observed_at = datetime.now(UTC).date().isoformat()
    luna = execute_run(target="codex_luna", model=args.luna_model, head=head)
    sol = execute_run(target="codex_sol", model=args.sol_model, head=head)
    print(json.dumps(build_evidence(luna=luna, sol=sol, head=head, observed_at=observed_at), indent=2, sort_keys=True))
    return (
        0
        if luna["status"] == sol["status"] == "returned"
        and not luna["workspace_mutation_observed"]
        and not sol["workspace_mutation_observed"]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
