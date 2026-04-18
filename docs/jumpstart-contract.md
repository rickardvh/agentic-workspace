# Setup Contract

This page defines the bounded post-bootstrap setup phase for mature repos.

Use it when safe install/adopt has finished and the repo should get a small amount of visible value without widening `init`.

## Purpose

- Keep setup separate from `init`.
- Make the first post-bootstrap follow-through bounded and reviewable.
- Seed only the smallest amount of visible value that justifies the extra phase.
- Let mature repos say that no new seed surfaces are needed.

## Rule

- Setup happens after bootstrap.
- Setup does not replace `init`.
- Setup does not bulk-import repo context or become a generic analysis pass.

## Seed Order

When setup identifies candidate surfaces, prefer:

- durable Memory boundaries first
- the smallest useful Planning picture second
- ambiguous or long-horizon follow-ons only when they are explicit no-action cases

Use the highest-confidence, lowest-noise candidates first so the first visible value stays small and reviewable.
If the repo already has the core setup orientation surfaces, report that no new seed surfaces are needed and stop there.

## Agent-Produced Findings Input

Setup may also accept one optional agent-produced findings artifact at `tools/setup-findings.json`.

That input stays bounded:

- the workspace does not own how the analysis was produced
- `tools/setup-findings.json` is the quiet default path because it is local, optional, and easy to leave absent in repos that have nothing worth preserving
- only findings with a clear durable owner should be preserved
- low-value or weakly grounded findings should stay transient

The normal state is that the artifact does not exist.
Create it only when a setup or jumpstart pass already has promotable findings worth handing to the workspace layer.

Use [`docs/setup-findings-contract.md`](docs/setup-findings-contract.md) for the accepted artifact shape, first finding classes, and promotion-versus-transient rules.

## Canonical Shape

Use `agentic-workspace setup --target ./repo --format json` for the machine-readable contract surface.

```json
{
  "setup": {
    "canonical_doc": "docs/jumpstart-contract.md",
    "command": "agentic-workspace setup --target ./repo --format json",
    "rule": "Setup is a bounded post-bootstrap phase that stays separate from init.",
    "phase": "post-bootstrap",
    "scope": [
      "seed one or two high-value surfaces, or stop when none are needed",
      "keep follow-through bounded and reviewable"
    ],
    "secondary": [
      "Do not widen init.",
      "Do not bulk-import repo context.",
      "Do not turn setup into generic analysis."
    ]
  }
}
```

## Concise Text Output

The text form should stay short and stable:

- `doc: docs/jumpstart-contract.md`
- `command: agentic-workspace setup --target ./repo --format json`
- `rule: Setup is a bounded post-bootstrap phase that stays separate from init.`
- `phase: post-bootstrap`
- `scope: seed one or two high-value surfaces after safe install/adopt`

## Relationship To Other Docs

- Use [`docs/default-path-contract.md`](docs/default-path-contract.md) for the front-door route selection contract.
- Use [`docs/init-lifecycle.md`](docs/init-lifecycle.md) for the lifecycle boundary between `init` and post-bootstrap follow-through.
- Use [`docs/reporting-contract.md`](docs/reporting-contract.md) for the pre-write discovery report that classifies candidate Memory and Planning seeds before any state is written.
- Use [`docs/setup-findings-contract.md`](docs/setup-findings-contract.md) when setup should accept agent-produced findings as bounded optional input.
