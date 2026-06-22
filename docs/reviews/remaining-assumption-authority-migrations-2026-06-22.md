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

## GitHub Issue-Body Handoff

The GitHub issue-body aid remains a renderer. Its structured input can carry issue-shaping text, but behavior-relevant facts used by AW runtime surfaces must be promoted into provider-neutral external-intent evidence before they influence routing or scope.

Renderer-owned input example:

```json
{
  "kind": "agentic-workspace/issue-body-request/v1",
  "template": "direction",
  "title": "Inventory current built-in assumptions",
  "fields": {
    "problem_intent": {
      "kind": "markdown",
      "value": "AW should stop relying on built-in repo/provider assumptions that are not owned by a declared contract, config, state, Memory, or review surface."
    },
    "intended_outcome": {
      "kind": "markdown",
      "value": "The current assumptions are inventoried and each finding is routed to its owning surface instead of becoming package policy."
    },
    "acceptance": {
      "kind": "markdown",
      "value": "No package-owned assumptions ledger is recreated; remaining findings name their owner surfaces and authority boundaries."
    }
  },
  "source_refs": [
    {
      "kind": "github_issue",
      "id": "#1675"
    }
  ]
}
```

Behavior-relevant promoted fact shape:

```json
{
  "kind": "planning-external-intent-evidence/v1",
  "items": [
    {
      "system": "github",
      "id": "#1675",
      "title": "Inventory current built-in assumptions",
      "status": "open",
      "kind": "issue",
      "planning_residue_expected": "Route durable findings to their owning contract, config, state, Memory, docs, or review surface; do not recreate a package-owned assumptions ledger.",
      "negative_invariants": [
        "Do not treat GitHub issue template prose as runtime authority.",
        "Do not route work from provider-specific strings unless provider-neutral external-intent evidence owns the fact."
      ],
      "url": "https://github.com/rickardvh/agentic-workspace/issues/1675",
      "source_repository": "rickardvh/agentic-workspace"
    }
  ]
}
```

This handoff is deliberately one-way: the aid renders a GitHub issue body, while external-intent evidence owns the normalized facts that runtime planning and summary surfaces may consume.

## Non-Consumption Proof

The ordinary package runtime does not read `.agentic-workspace/agent-aids/scripts/github-issue-body/` to make routing decisions. Runtime paths that need issue-backed intent read `.agentic-workspace/local/cache/external-intent-evidence.json` or `.agentic-workspace/planning/external-intent-evidence.json`; agent-aid discovery reads manifests as candidate tools and documentation only. Repository search for `github-issue-body` is limited to the aid files, manifest/schema checks, structured-file inventory, docs, and tests, not runtime decision logic.

## Follow-Up Rule

Future assumption findings should either be removed, moved into their owning contract/config/state/Memory surface, or recorded as review-only evidence. Do not recreate a maintained package-owned assumptions ledger.
