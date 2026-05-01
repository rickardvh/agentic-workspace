# Benchmarking Contract

This is a development-only benchmark contract for human-free repo-operating evaluation.

It stays in the monorepo as a dev harness and does not ship into target repos.

Use `packages/planning/src/repo_planning_bootstrap/_benchmark.py` and the checked-in fixtures under `packages/planning/tests/fixtures/benchmark/` to read and exercise the machine-readable contract.

## Canonical Shape

`benchmark_contract/v1` is the canonical contract shape for the first benchmark slice.

It defines:

- `human_policy_spec/v1`
- `judge_rubric/v1`
- `benchmark_scenario/v1`
- `benchmark_run_result/v1`

## Roles

The benchmark uses three roles:

- `human_role`: answers from a structured scenario policy only
- `worker_role`: performs bounded repo discovery, execution, proof selection, and handoff
- `judge_role`: emits structured scores and compact notes

## First Fixture Set

The first fixture tranche is intentionally narrow and operational:

- `blank_or_unmanaged_repo`
- `light_existing_workflow`
- `docs_heavy_existing_repo`
- `partial_or_placeholder_state`
- `ownership_ambiguity`
- `interrupted_bootstrap`
- `mixed_agent_handoff_state`

These states are meant to stay frozen, versioned, and resettable so benchmark runs remain comparable.

## Evaluation Policy

The benchmark should prefer:

- narrow operational questions with allowed answer sets
- structured human policy over ad hoc helpfulness
- structured judge scores over narrative-only evaluations
- proxy retrieval and token-cost metrics over rough qualitative impressions

The benchmark is not a generic code-generation score.
