from __future__ import annotations

from copy import deepcopy
from typing import Any

BENCHMARK_CONTRACT: dict[str, Any] = {
    "status": "present",
    "schema": "benchmark_contract/v1",
    "purpose": "Provide a human-free benchmark contract for repo-operating evaluation.",
    "roles": {
        "human_role": {
            "purpose": "Answer benchmark escalations strictly from a structured scenario policy.",
            "policy_source": "benchmark_human_policy/v1",
            "boundaries": [
                "Do not broaden the requested outcome.",
                "Do not invent new requirements.",
                "Do not leak extra hints beyond the policy.",
            ],
        },
        "worker_role": {
            "purpose": "Perform repo discovery, planning, execution, proof selection, and handoff.",
            "boundaries": [
                "May improve means locally.",
                "Must escalate changed ends or missing policy.",
                "Should prefer compact selectors and narrow reads.",
            ],
        },
        "judge_role": {
            "purpose": "Score the worker against a fixed rubric and structured result schema.",
            "output_schema": "benchmark_run_result/v1",
            "boundaries": [
                "Emit structured scores first.",
                "Attach notes without replacing the rubric.",
            ],
        },
    },
    "human_policy_spec": {
        "schema": "benchmark_human_policy/v1",
        "required_fields": [
            "requested_outcome",
            "priorities",
            "hard_constraints",
            "prohibitions",
            "approval_rules",
            "allowed_escalation_responses",
            "volunteering_rules",
        ],
        "allowed_escalation_responses": [
            "answer_from_policy",
            "repeat_policy_boundaries",
            "request_missing_field",
            "decline_out_of_policy",
        ],
        "volunteering_rules": [
            "May volunteer only facts and constraints already present in policy.",
            "Must wait to be asked before adding any extra guidance.",
        ],
    },
    "judge_rubric": {
        "schema": "benchmark_judge_rubric/v1",
        "score_scale": {
            "type": "integer",
            "minimum": 0,
            "maximum": 2,
            "labels": {
                0: "incorrect",
                1: "partial",
                2: "correct",
            },
        },
        "dimensions": [
            "correctness",
            "scope_discipline",
            "proof_lane",
            "ownership",
            "escalation",
            "handoff_continuity",
            "retrieval_efficiency",
        ],
        "notes_rule": "Notes supplement scores and do not replace structured scoring.",
    },
    "scenario_spec": {
        "schema": "benchmark_scenario/v1",
        "required_fields": [
            "scenario_id",
            "fixture_id",
            "human_policy_ref",
            "judge_rubric_ref",
            "questions",
            "allowed_answers",
            "trace_fields",
        ],
        "questions_shape": "Narrow operational questions with gold or allowed answer sets.",
        "trace_fields": [
            "human_role_trace",
            "worker_trace",
            "judge_scores",
            "files_opened_before_safe_action",
            "selector_vs_broad_dump_counts",
            "escalation_count",
        ],
    },
    "fixture_spec": {
        "repo_states": [
            {
                "id": "blank_or_unmanaged_repo",
                "purpose": "Exercise initial startup and safe first action.",
            },
            {
                "id": "light_existing_workflow",
                "purpose": "Exercise a repo with a small amount of existing operating structure.",
            },
            {
                "id": "docs_heavy_existing_repo",
                "purpose": "Exercise a mature repo with stable prose, conventions, and latent runbooks.",
            },
            {
                "id": "partial_or_placeholder_state",
                "purpose": "Exercise a repo with mixed managed and unmanaged planning state.",
            },
            {
                "id": "ownership_ambiguity",
                "purpose": "Exercise ownership selection and escalation boundaries.",
            },
            {
                "id": "interrupted_bootstrap",
                "purpose": "Exercise restart continuity after partial setup.",
            },
            {
                "id": "mixed_agent_handoff_state",
                "purpose": "Exercise cross-agent continuation and residue handling.",
            },
        ],
        "fixture_properties": [
            "frozen",
            "versioned",
            "resettable",
        ],
        "first_fixture_set": [
            "blank_or_unmanaged_repo",
            "docs_heavy_existing_repo",
            "partial_or_placeholder_state",
        ],
    },
    "operational_question_families": [
        {
            "id": "startup_path",
            "questions": [
                "What is the canonical startup path here?",
                "What should happen next after interrupted bootstrap?",
            ],
            "allowed_answers": ["canonical path", "defer to escalation", "narrow next action"],
        },
        {
            "id": "ownership_selection",
            "questions": [
                "Who owns this file or concern?",
            ],
            "allowed_answers": ["owner surface path", "no owner yet", "escalate"],
        },
        {
            "id": "proof_lane_selection",
            "questions": [
                "What proof lane is enough?",
            ],
            "allowed_answers": ["narrow proof lane", "broader proof lane", "escalate"],
        },
        {
            "id": "delegated_judgment",
            "questions": [
                "May the worker proceed directly or must it escalate?",
            ],
            "allowed_answers": ["proceed", "escalate", "ask for missing policy"],
        },
    ],
    "efficiency_metrics": [
        {
            "id": "files_opened_before_safe_action",
            "kind": "proxy",
            "description": "How many files were opened before the first safe action.",
        },
        {
            "id": "bytes_read",
            "kind": "proxy",
            "description": "Bytes read where measurable from the structured trace.",
        },
        {
            "id": "selector_vs_broad_dump_counts",
            "kind": "proxy",
            "description": "How often narrow selectors won over broad dumps.",
        },
        {
            "id": "escalation_count",
            "kind": "count",
            "description": "How often the human-role agent had to be consulted.",
        },
        {
            "id": "handoff_reread_cost",
            "kind": "proxy",
            "description": "How much broad rereading was needed to continue a handoff.",
        },
    ],
}


def benchmark_contract() -> dict[str, Any]:
    return deepcopy(BENCHMARK_CONTRACT)
