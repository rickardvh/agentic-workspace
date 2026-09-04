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
redefine semantic scope; semantic edits change the revision. Planning retains
multiple named subjects in the same state and derives the current ready
frontier from their dependency relations. Missing or incomplete dependencies
block a subject; completing or materially revising a dependency refreshes the
dependent revision and invalidates only attempts bound to the old revision.

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
Focused conformance exercises this path with the retained Memory and
Verification owners, including fresh-process reuse, owner-local invalidation,
and contribution-call counters that demonstrate avoided reconstruction.

## Trusted human corrections

A host that already has authenticated human custody may create a
`TrustedCorrectionIngress` capability and admit one bounded correction. The
capability, not caller-controlled JSON such as `source=human`, supplies
provenance. Ordinary `start` then returns the selected owner's accepted typed
operation. Memory retention therefore executes as `memory.record`, and a
deterministic owner failure becomes a `planning.set` repair subject; correction
custody never calls another owner's handler.

Existing repository/proof/delegation policy wins over duplicate Memory only
when its exact current owner reference and revision validate. A stale or
unknown hint blocks disposition. A
future-useful advisory may be recorded by Memory, deterministic owner failure
is returned as adaptation evidence for that owner, and a correction with no
future value receives an explicit justified `no-new-durable-record`
disposition. Operation receipts deduplicate host retries; there is no
correction archive, transcript scan, vendor adapter registry, or no-signal
startup work. The generated TypeScript package exposes the same constructible
trusted-ingress capability with an injected current-owner disposition resolver;
providers remain outside AW.
