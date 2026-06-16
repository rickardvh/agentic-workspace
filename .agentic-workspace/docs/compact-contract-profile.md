# Compact Contract Profile

## Purpose

This page defines the first query-first answer profile for machine-readable workspace contract surfaces.

Use it when one bounded answer is enough and loading a broad contract object would add avoidable token and reread cost.

## Rule

Prefer a narrow selector over a whole-surface dump when the task only needs one answer.

Keep the full JSON surface available for broad inspection, but make the normal retrieval path cheap when the question is already narrow.
Use stable concern-shaped selectors so the agent can ask one question without loading unrelated contract domains.

## Profile

The first profile is an answer envelope on existing commands:

```json
{
  "profile": "compact-contract-answer/v1",
  "surface": "<defaults|proof|ownership>",
  "selector": {"<key>": "<value>"},
  "matched": true,
  "answer": { "...": "..." },
  "refs": ["docs/...", "agentic-workspace ..."],
  "payload_locations": {
    "primary_payload_field": "answer",
    "selected_payload_paths": {"answer": "answer"}
  }
}
```

Rules:

- `profile` identifies the compact answer contract.
- `surface` identifies which command answered the query.
- `selector` records the narrow query that produced the answer.
- `matched` distinguishes a real answer from a clean no-match response.
- `answer` carries only the bounded result.
- `refs` point back to canonical docs or full command surfaces instead of repeating broad explanation.
- `payload_locations` tells agents and tests where the selected payload lives in the output envelope.

## Output Envelopes

Exact-field `--select` output uses the selected-output envelope:

```json
{
  "kind": "agentic-workspace/selected-output/v1",
  "values": {
    "<selector>": { "...": "..." }
  },
  "payload_locations": {
    "primary_payload_field": "values",
    "selected_payload_paths": {
      "<selector>": "values[\"<selector>\"]"
    }
  }
}
```

The `values` object is keyed by the literal selector string. For a selector such as
`context.scope`, the payload path is `values["context.scope"]`, not
`values.context.scope`.

Report `--section` output and other compact contract answers store the selected
payload under `answer`. Both envelope families expose `payload_locations` so
agents and tests can discover the payload path instead of guessing from command
shape.

## First Selectors

Use:

```bash
agentic-workspace defaults --section <section> --format json
agentic-workspace proof --target ./repo --route <id> --format json
agentic-workspace proof --target ./repo --current --format json
agentic-workspace ownership --target ./repo --concern <concern> --format json
agentic-workspace ownership --target ./repo --path <repo-path> --format json
```

These selectors should answer:

- one defaults section
- one proof route
- the current proof state
- one ownership concern
- one ownership answer for a repo-relative path

## Boundaries

- Keep selectors concern-shaped and stable.
- Do not invent a general query language in the first slice.
- Do not replace the full contract dumps.
- Do not duplicate canonical ownership, proof, or defaults authority in a new file.
- Keep refs compact and canonical instead of embedding broad narrative explanation.

## Relationship To Other Docs

- Use [`.agentic-workspace/docs/reporting-contract.md`](reporting-contract.md) for the compact front-door route to combined workspace state.
- Use [`.agentic-workspace/docs/proof-surfaces-contract.md`](proof-surfaces-contract.md) for proof-lane semantics.
- Use [`.agentic-workspace/docs/ownership-authority-contract.md`](ownership-authority-contract.md) for ownership semantics.
- Use [`docs/maintainer/lazy-discovery-measurements.md`](../../docs/maintainer/lazy-discovery-measurements.md) when you want to verify that the selector path is actually cheaper than the broad dump.
