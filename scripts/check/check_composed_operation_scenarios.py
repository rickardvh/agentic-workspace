"""Validate the compact, release-gating composed-operation scenario contract."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = REPO_ROOT / "tools" / "model-cli-harness" / "external-agent-evaluation" / "composed-operation-scenario-matrix.json"
REQUIRED_SCENARIOS = {
    "fresh-direct-work", "explicit-bounded-work", "selected-owner-resume", "unrelated-task-with-owner",
    "branch-worktree-switch", "completed-owner-residue", "missing-skill-dependency", "dirty-shared-worktree",
    "stale-mutation-owner", "untrusted-imperative-text", "proof-reuse-and-staleness", "partial-finalization",
    "handoff-return-admission", "runtime-unavailable", "runtime-restored-reentry", "projection-digest-mismatch",
}
REQUIRED_GATES = {"owner", "terminal_state", "typed_action", "effect_scope", "mutation_precondition", "proof_claim_boundary", "next_transition", "semantic_parity"}
REQUIRED_METRICS = {"aw_command_count", "wall_clock_aw_ms", "output_bytes", "managed_files_read", "state_records_touched", "unchanged_orientation_repeats", "route_reversals", "clarification_requests", "rejected_mutations", "proof_reruns", "false_completion_authorizations", "package_residue"}


def load_matrix() -> dict[str, object]:
    return json.loads(MATRIX_PATH.read_text(encoding="utf-8"))


def validate_matrix(matrix: dict[str, object]) -> list[str]:
    errors: list[str] = []
    if matrix.get("kind") != "agentic-workspace/composed-operation-scenario-matrix/v1":
        errors.append("matrix kind is invalid")
    if matrix.get("lane") != "#2300" or matrix.get("version") != 1:
        errors.append("matrix lane or version is invalid")
    scenarios = matrix.get("scenarios", [])
    if not isinstance(scenarios, list):
        return [*errors, "scenarios must be a list"]
    ids = {item.get("id") for item in scenarios if isinstance(item, dict)}
    missing = REQUIRED_SCENARIOS.difference(ids)
    if missing:
        errors.append(f"missing scenarios: {', '.join(sorted(missing))}")
    for scenario in scenarios:
        if not isinstance(scenario, dict) or not all(scenario.get(key) for key in ("id", "owner", "terminal_state", "typed_action", "fault")):
            errors.append("every scenario must state owner, terminal state, typed action, and fault")
            break
    if not REQUIRED_GATES.issubset(set(matrix.get("hard_gates", []))):
        errors.append("hard gates do not cover the composed decision contract")
    assertion_contract = matrix.get("scenario_assertion_contract", {})
    if not isinstance(assertion_contract, dict) or not {"owner", "terminal_state", "typed_action", "permitted_effect_scope", "mutation_precondition", "proof_claim_boundary", "next_transition"}.issubset(set(assertion_contract.get("per_scenario", []))):
        errors.append("scenario assertion contract is incomplete")
    if not REQUIRED_METRICS.issubset(set(matrix.get("cost_metrics", []))):
        errors.append("cost metrics do not cover total successful-completion cost")
    return errors


def main() -> int:
    errors = validate_matrix(load_matrix())
    if errors:
        print("[fail] " + "; ".join(errors))
        return 1
    print("[ok] composed operation scenario matrix")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
