# Remaining Assumption Authority Migrations

Date: 2026-06-22

Issues: #1673, #1675, #1677, #1678

## Result

- `docs/maintainer/non-enum-keyword-routing-audit.json` now carries enum-backed `decision_authority` for each string-table row.
- `scripts/check/check_contract_tooling_surfaces.py` rejects any `decision-affecting-package-policy` row, forcing migration to structured authority before the audit can pass.
- `.agentic-workspace/agent-aids/scripts/github-issue-body/manifest.json` now records an `authority_boundary` with `runtime_authority: none` and `fact_owner: external-intent-evidence`.
- `scripts/check/check_agent_aids.py` rejects GitHub-specific advisory aids that route behavior-relevant facts anywhere other than external-intent evidence.
- `tools/model-cli-harness/external-agent-evaluation/scorecard-taxonomy.json` now records that harness output is maintainer-evaluation evidence, not runtime authority.
- `scripts/model_cli_harness/external_agent_evaluation_lane.py` validates that the harness authority boundary remains present.

## Boundary

The deleted package-owned assumptions inventory is not restored. These findings now live in their actual owner surfaces:

- string-table risk: maintainer audit plus contract-tooling validator;
- GitHub issue-body helper: checked-in agent-aid manifest plus external-intent evidence contract;
- model CLI harness: external-agent evaluation lane pack plus validator.

Agent judgment remains responsible for applying these facts. The package may surface diagnostics, normalized external intent, or harness evidence, but it does not route work from arbitrary prose markers, GitHub template phrasing, or provider CLI assumptions.

## Follow-Up Rule

Future assumption findings should either be removed, moved into their owning contract/config/state/Memory surface, or recorded as review-only evidence. Do not recreate a maintained package-owned assumptions ledger.
