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

Configuration is resolved through ordinary `start`; there is no setup command
or questionnaire. A decision may declare narrowly typed `path_exists` or
`fact_equals` inference candidates whose answers are already admitted choices.
Those strong current facts are applied first through `repository.answer`.
Only the next irreducible owner question is surfaced. Optional questions add a
bounded `defer` choice; deferral stores only the rule identity and revision and
may be revisited with `{"configuration":{"resume":true}}`. A changed rule
revision invalidates only that answer or deferral, while unrelated settled
rules stay quiet.

Repository maintainers may use `tools/skills/workspace-configuration` as an
optional guided procedure. It repeatedly invokes only current, safe inferred
actions, surfaces the next irreducible finite or open owner judgment, and then
continues from `next_decision`. The skill owns no state or authority and never
substitutes raw configuration-file writes for Repository, Verification, or
Assignment operations.

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
provenance. Ordinary `start` then returns the selected owner's
correction-specific typed operation. Memory, Repository, Verification,
Assignment, and Planning each validate their own current linkage before
accepting a handoff; correction custody never calls another owner's handler.

Existing repository/proof/delegation policy wins over duplicate Memory only
when its exact current owner reference and revision validate. A stale or
unknown hint blocks disposition. A
future-useful advisory may be recorded by Memory, while deterministic owner
failure becomes a Planning repair bound to the failed owner's current evidence.
An unspecified correction with no applicability asks one revision-bound
retain-or-discard question before the selected owner operation; a correction
with no future value receives an explicit justified `no-new-durable-record`
disposition. Operation receipts deduplicate host retries; there is no
correction archive, transcript scan, vendor adapter registry, or no-signal
startup work. The generated TypeScript package exposes the same constructible
trusted-ingress and owner-admission semantics; providers remain outside AW.
