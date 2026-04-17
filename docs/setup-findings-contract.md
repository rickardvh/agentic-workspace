# Setup Findings Promotion Contract

This page defines the first bounded contract for accepting agent-produced setup or jumpstart findings as optional input.

Use it when an agent has already analyzed a repo and you want Agentic Workspace to decide which findings should stay transient versus which are worth preserving into durable repo state.

## Purpose

- Accept useful setup findings without building a workspace-owned analyzer.
- Preserve only the findings that reduce rediscovery or handoff cost.
- Route preserved findings to an existing durable owner surface.
- Keep low-value or weakly grounded setup analysis transient.

## Rule

- Setup findings input is optional.
- Agentic Workspace does not own how the analysis was produced.
- The first accepted artifact path is `tools/setup-findings.json`.
- The first accepted artifact kind is `workspace-setup-findings/v1`.
- Setup findings should be preserved only when they have a clear durable owner and would still matter after the current session.

## First Accepted Classes

### `repo_friction_evidence`

Preserve when:

- confidence is at least `0.75`
- the finding has a repo-relative `path` or explicit `refs`
- preserving it would reduce rediscovery during later repo work

Route to:

- `agentic-workspace report --target ./repo --format json`
- `repo_friction.external_evidence`

Leave transient when:

- there is no grounding path or refs
- confidence is below `0.75`
- the finding only restates existing report output

### `planning_candidate`

Preserve when:

- confidence is at least `0.75`
- the finding includes a bounded `next_action`
- the follow-on would still matter after the current setup pass ends

Route to:

- `TODO.md` or `docs/execplans/` after bounded planning review

Leave transient when:

- there is no bounded `next_action`
- confidence is below `0.75`
- the finding is only generic analysis with no clear planning owner

## Artifact Shape

Use `agentic-workspace setup --target ./repo --format json` for the queryable contract and accepted-input status.

The optional artifact shape is:

```json
{
  "kind": "workspace-setup-findings/v1",
  "findings": [
    {
      "class": "repo_friction_evidence",
      "summary": "Large shared workspace CLI surface is still a hotspot.",
      "confidence": 0.91,
      "path": "src/agentic_workspace/cli.py",
      "refs": ["docs/reporting-contract.md"]
    },
    {
      "class": "planning_candidate",
      "summary": "One module-reporting follow-on still needs promotion.",
      "confidence": 0.82,
      "next_action": "Promote the next bounded reporting slice into TODO.md when current setup work finishes."
    }
  ]
}
```

## Boundaries

- Do not turn setup findings into a generic analysis exchange format.
- Do not auto-write planning or memory state from setup input in the first slice.
- Do not preserve every finding just because an agent can emit it.
- Keep finding routing subordinate to existing owner surfaces such as reporting or planning.

## Relationship To Other Docs

- Use [`docs/jumpstart-contract.md`](docs/jumpstart-contract.md) for the bounded post-bootstrap setup phase.
- Use [`docs/reporting-contract.md`](docs/reporting-contract.md) when a preserved finding becomes shared repo-friction evidence.
- Use [`docs/default-path-contract.md`](docs/default-path-contract.md) for the front-door route to setup and its compact contract surfaces.
