# External-Agent Evaluation Lane

This maintainer-only pack implements the evaluation-to-improvement lane for #1600. It is not an ordinary Agentic Workspace startup surface.

Use it to evaluate whether generic external agents follow the AW operating loop under realistic friction:

- startup routing;
- work shaping;
- Memory pull and capture;
- Planning continuity;
- Verification/proof;
- closeout and residue ownership;
- package/host/generated/local boundary hygiene;
- recovery.

The pack is intentionally compact. It provides machine-readable scorecard/taxonomy data, scenario probes, historical regression fixtures, sample result records, promotion decisions, surface-simplification decisions, evaluator invariants, and a lane-level closure report.

## Commands

Validate the lane pack:

```powershell
uv run python scripts/model_cli_harness/external_agent_evaluation_lane.py validate
```

Generate the maintainer closure report:

```powershell
uv run python scripts/model_cli_harness/external_agent_evaluation_lane.py report --format json
```

The report distinguishes fixture-backed readiness from live-run closure. `ready_for_fixture_closure` means the scorecard, scenarios, records, and report contract are internally consistent. `ready_for_full_closure` additionally requires clean live external-agent runs; unresolved live failures should stay routed through the lane instead of closing the parent issue.

Run a real external-agent scenario only when maintainer evidence is needed. The Codex adapter defaults to GPT-5.3 Codex Spark:

```powershell
uv run python scripts/model_cli_harness/run_model_cli_harness.py `
  --adapter codex `
  --model gpt-5.3-codex-spark `
  --scenario startup-orientation `
  --execute
```

Dry-run remains the default for harness invocations. Checked-in tests use fixtures and sample records rather than spending model calls.

## File Roles

- `scorecard-taxonomy.json`: loop dimensions, pass/partial/fail semantics, stable failure IDs, and owner surfaces.
- `evaluator-invariants.json`: acceptable agent variation rules so harmless differences are not scored as AW failures.
- `scenario-probes.json`: canonical probes and artifact-backed host-install probe definitions.
- `historical-failure-fixtures.json`: compact regression fixtures derived from observed dogfooding failures.
- `result-records.sample.json`: versioned sample result records compatible with the taxonomy.
- `live-results-2026-06-18.json`: real Codex Spark run evidence from the core scenario probes.
- `promotion-decisions.sample.json`: repeated-failure promotion and dismissal examples.
- `surface-decisions.sample.json`: keep/route/merge/generate/remove surface simplification decisions.
- `operational-decision-trace.md`: shareable protocol for observable operational decisions without chain-of-thought disclosure.

## Closure Rule

The lane is ready for parent closure only when the generated report can show:

- a scorecard and failure taxonomy exist;
- canonical scenarios cover the major loop phases;
- compact result records exist and reference the taxonomy;
- repeated failures route to product changes or explicit dismissals;
- at least one historical failure is preserved as a regression fixture;
- artifact-backed host operation has a defined probe;
- surface simplification has evidence-backed decisions;
- safe claim boundaries and closeout residue are represented.
