# AW proof retry ladder dogfood

Date: 2026-06-23

Related issues: #1680, #1694

## Context

The #1689 dogfooding slice reran broad workspace proof while the active fault was localized to proof-selection behavior. That repeated the expensive `make test-workspace` loop before the repair narrowed to focused proof tests.

## Change

Failed proof receipts now attach `repair_retry_ladder` with three repair-iteration steps:

1. focused failing regression or nearest unit/contract test;
2. affected package or workspace subset;
3. full originally selected proof.

When changed paths include Python tests, the ladder names the focused pytest command. For example, a failed receipt for `make test-workspace` with `tests/test_workspace_proof_cli.py` changed produces:

```text
uv run pytest tests/test_workspace_proof_cli.py -q
```

The full proof command remains recorded as `full_selected_proof`, and `full_proof_still_required` stays true.

## Guardrail

This ladder is repair guidance only. It does not close work, weaken required proof, or allow completion claims without rerunning the originally selected proof after focused repair checks pass.

## Dogfood expectation

Future #1680 repair turns should inspect failed proof receipts before rerunning broad proof. If the ladder is skipped because the failure is cross-cutting, the closeout should say why.
