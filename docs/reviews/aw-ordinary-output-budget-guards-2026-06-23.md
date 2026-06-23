# AW ordinary output budget guards

Date: 2026-06-23

Related issues: #1680, #1695

## Context

Recent #1680 dogfooding showed that ordinary `start` and `implement` payloads can become a token sink when diagnostic packets are emitted by default. The first guardrail should make output-size drift visible before changing more behavior.

## Initial Tiny Budgets

Representative ordinary cases now have explicit JSON payload budgets:

- `start` docs-only first-contact task: under 10 KB.
- `implement` docs-only task: under 15 KB.
- `implement` simple code-change task: under 15 KB.

These are not final product budgets. They are regression guards sized to current compact payloads so later reductions can tighten them without losing blockers, proof, or closeout state.

## Selector-Only Detail Areas

This slice locks three non-essential detail areas behind selectors for ordinary `implement` defaults:

- `change_impact`
- `routine_work_context`
- `generated_surface_trust`

It also keeps `start` default detail for `memory_decision_packet`, `installed_state_compatibility`, and `planning_safety_gate` out of the ordinary payload while preserving action signals and next safe action. For the representative docs-only start case, the asserted drill-down details are `memory_decision_packet`, `routine_work_context`, and `workflow_sufficiency`; other startup diagnostics remain absent from the default payload unless relevant.

## Dogfood Cases

The guard tests cover both requested #1695 dogfood shapes:

- docs-only correction: `README.md` / "Fix one docs typo";
- code-change task: `src/app.py` / "Fix one code path".

## Guardrail

Budget assertions are not permission to hide hard blockers, proof obligations, or closure/residue blockers. If a future reduction needs to remove default fields, it must keep those facts either in the tiny action/proof path or behind exact selectors.
