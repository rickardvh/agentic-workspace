# Source-owner batteries

V1 keeps four optional source-owner capabilities on the common module contract.
They contribute nothing when irrelevant.

## Repository controls

Repositories may place an explicit JSON control inside a scoped Markdown
comment in `AGENTS.md`:

```markdown
<!-- agentic-workspace:rule
{"id":"release","applies":{"task_terms":["release"]},"procedures":[{"id":"review","locator":"docs/review.md"}],"claims":{"blocked":["publish"]}}
-->
```

The bounded vocabulary supplies facts, resource/procedure references, claim
restrictions, and owner/revision-bound decisions. It cannot execute a workflow
or manufacture operation authority. Shared answers are explicit repo-owned
configuration; local answers remain under ignored `.agentic-workspace/local/`.
Procedure selection is reference-only and creates no usage record.

## Memory

Memory records include stable identity, summary/value, provenance, task/path
applicability, optional dependency revision, advisory/workaround kind, and an
active/promoted/retired disposition. Ordinary `start` selects only applicable,
current summaries and labels them selected rather than used. Promotion names
the stronger owner that absorbed a deterministic workaround. Unmatched records
are absent from the operating decision.

## Planning

Planning preserves a compact semantic subject: outcome, scope, constraints,
dependencies, stops, proof claims, and a semantic revision independent of its
current execution status. Returned or integration-pending work yields one
bounded reconciliation decision. Status changes and retries do not silently
redefine semantic scope; semantic edits change the revision.

## Verification

Verification strategy is repo-owned in `.agentic-workspace/verification.toml`,
separate from Planning. Applicable routes declare claim coverage, breadth, and a
typed producer binding. Verification chooses the least-broad sufficient route.
Missing, stale, or non-executable coverage blocks only the affected claim with
an exact policy route. Evidence records subject, strategy, route, environment
result, and currentness; process success alone does not grant a claim.

## Reuse

Modules may expose the smallest owner/dependency currentness identity for a
material conclusion. Workspace stores only the normalized conclusion in an
ignored per-owner path and reuses it across fresh processes while that identity
is unchanged. There is no transcript, reasoning cache, usage ledger, or global
dependency database. Direct and irrelevant modules create no reuse residue.
