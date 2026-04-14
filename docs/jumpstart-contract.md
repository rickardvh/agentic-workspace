# Jumpstart Contract

This page defines the bounded post-bootstrap jumpstart phase for mature repos.

Use it when safe install/adopt has finished and the repo should get a small amount of visible value without widening `init`.

## Purpose

- Keep jumpstart separate from `init`.
- Make the first post-bootstrap follow-through bounded and reviewable.
- Seed only the smallest amount of visible value that justifies the extra phase.

## Rule

- Jumpstart happens after bootstrap.
- Jumpstart does not replace `init`.
- Jumpstart does not bulk-import repo context or become a generic analysis pass.

## Seed Order

When jumpstart identifies candidate surfaces, prefer:

- durable Memory boundaries first
- the smallest useful Planning picture second
- ambiguous or long-horizon follow-ons only when they are explicit no-action cases

Use the highest-confidence, lowest-noise candidates first so the first visible value stays small and reviewable.

## Canonical Shape

Use `agentic-workspace defaults --section jumpstart --format json` for the machine-readable contract surface.

```json
{
  "jumpstart": {
    "canonical_doc": "docs/jumpstart-contract.md",
    "command": "agentic-workspace defaults --section jumpstart --format json",
    "rule": "Jumpstart is a bounded post-bootstrap phase that stays separate from init.",
    "phase": "post-bootstrap",
    "scope": [
      "seed one or two high-value surfaces",
      "keep follow-through bounded and reviewable"
    ],
    "secondary": [
      "Do not widen init.",
      "Do not bulk-import repo context.",
      "Do not turn jumpstart into generic analysis."
    ]
  }
}
```

## Concise Text Output

The text form should stay short and stable:

- `doc: docs/jumpstart-contract.md`
- `command: agentic-workspace defaults --section jumpstart --format json`
- `rule: Jumpstart is a bounded post-bootstrap phase that stays separate from init.`
- `phase: post-bootstrap`
- `scope: seed one or two high-value surfaces after safe install/adopt`

## Relationship To Other Docs

- Use [`docs/default-path-contract.md`](docs/default-path-contract.md) for the front-door route selection contract.
- Use [`docs/init-lifecycle.md`](docs/init-lifecycle.md) for the lifecycle boundary between `init` and post-bootstrap follow-through.
- Use [`docs/reporting-contract.md`](docs/reporting-contract.md) for the pre-write discovery report that classifies candidate Memory and Planning seeds before any state is written.
