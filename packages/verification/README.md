# Agentic Verification

Agentic Verification is the Agentic Workspace module for reusable soft-verification protocols, bounded evidence, and known verification gaps.

It is one peer capability in the AW module model. Verification does not define a mandatory core "proof phase"; it contributes only when the current operating contract needs its domain.

Use the root `agentic-workspace` CLI for ordinary host-repo operation. The `agentic-verification` CLI is the module-level maintenance/debugging surface.

## What Verification owns

Verification owns module-domain context such as:

- repeatable verification protocol declarations;
- scenario and proof-route metadata;
- bounded evidence-bundle records and summaries;
- transcript retention/summary policy;
- known verification gaps and residual-risk labels.

Verification does **not** own:

- active Planning state or intent;
- repository assurance policy outside its declared domain;
- global proof or completion authority;
- Memory or other modules' state;
- CI as a system;
- arbitrary raw transcript storage.

Passing a Verification protocol can contribute evidence to the current operating contract. It does not by itself establish semantic intent satisfaction or authorize a broader completion claim.

## How it participates

Verification extends the same generic `resolve -> act -> reconcile` loop as other modules:

- **Resolve:** when changed paths, requirements, known gaps, or an explicit proof need make Verification relevant, it may contribute compact protocol/proof-route/gap context.
- **Act:** it exposes module-owned verification/report/evidence operations with bounded effects.
- **Reconcile:** it contributes evidence, residual risk, stale/gap state, or other Verification-owned result facts back to the current decision.

When Verification is irrelevant, it should stay out of first-line context and ordinary instructions.

The full Verification manifest remains module-owned; Workspace should consume only the bounded current contribution needed for routing, proof/claim composition, or recovery.

## Module CLI

```text
agentic-verification report --target ./repo --format json
```

The AW root can expose routed Verification projections through current supported commands such as:

```text
agentic-workspace report --section verification --format json
agentic-workspace implement --select verification --changed <paths> --format json
agentic-workspace proof --changed <paths> --verbose --format json
```

Treat exact commands/options as current contract/reference facts rather than the conceptual module boundary.

## Boundary

Verification is not a generic test runner, compliance engine, evidence warehouse, or global claim authority. It is a reusable module for verification context and evidence that can enrich AW's existing operating decision when relevant.

A repository can omit Verification entirely, use it alone with the root Workspace layer, or combine it with other modules without changing the ordinary AW mental model.

Public maturity: **alpha**, matching coordinated package metadata. Strong capability evidence does not independently promote the distribution support contract.

## Declaration admission

Native Verification admits `contracts/manifest.schema.json` and the referenced
assurance schema before using source policy. Unknown keys, dangling named
protocol/scenario/profile/requirement references and conflicting profile command
roles require source repair. There is no partial/default policy substitution.
Selected protocol commands are candidates through the same native proof owner.

Purpose, steps, observations, review aids and escalation prose support selected
human/agent judgment. They do not automatically compose lanes, satisfy evidence,
authenticate reviewers or control retention. Retired numeric precedence, role,
composition and escalation-ID knobs are preserved as source review guidance in
existing review aids. Populated measurement requirements remain restrictive with
explicit unavailable admission; their bounded evidence capability is tracked in
#3324; semantic protocol/domain applicability admission is tracked in #3327.
Source validation alone is not satisfaction of either requirement. Static
manifest evidence bundles, authority/concept maps and recorded gap tables are no
longer authorable; current native receipt and review owners remain authoritative.
