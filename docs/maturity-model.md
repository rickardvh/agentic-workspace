# Maturity model

This page defines Agentic Workspace's public maturity vocabulary and promotion rule. It is not a manually maintained status dashboard.

The exact maturity of a source revision or published distribution is owned by coordinated release metadata and the package/release artifacts for that subject. In source, `.github/release-ownership.json` names the coordinated `maturity_classifier`; package metadata must agree. For published bytes, use the selected immutable release and its receipts rather than inferring maturity from a newer source checkout.

## Labels

### Alpha

The product/capability is real, tested, and dogfooded, but ordinary behavior, naming, schema shape, compatibility boundaries, or guidance may still change materially. Early adopters should expect change and rely on versioned release contracts rather than broad stability assumptions.

### Beta

The public contract is broadly usable for early adopters, the supported compatibility boundary is explicit, selective adoption works, and expected changes are mostly additive or refining rather than architectural. Moving to Beta requires package metadata, release checks, and representative behavioral evidence; documentation wording alone cannot promote it.

### Stable

The support and compatibility contract is deliberate enough that incompatible change is exceptional and follows the project's declared versioning/deprecation policy. Stable maturity does not imply support for every operating system, runtime, provider, or host integration: those remain explicit release/support claims.

## Current public status

Do not copy a current maturity label into conceptual pages merely for convenience.

For a source revision, read the coordinated release authority:

- [`.github/release-ownership.json`](../.github/release-ownership.json) for the canonical maturity classifier and release model;
- [`pyproject.toml`](../pyproject.toml) and coordinated package metadata for the distribution projection;
- release checks/receipts for whether a proposed promotion is actually admitted.

For installed or published bytes, use the exact immutable release subject. A source checkout can contain newer evidence or a proposed promotion without changing an older published release's maturity.

Release class and product maturity are related but not interchangeable. A preview or release candidate is explicitly non-support-bearing even when it exercises near-final behavior. A stable support-bearing release must satisfy the project's promotion and compatibility requirements for its exact subject; neither a branch name nor a green source checkout supplies that claim.

## Promotion rule

Promote a public surface only when all relevant owners agree:

1. package/distribution metadata uses the promoted maturity;
2. the public compatibility and support boundary is explicit;
3. deterministic release/conformance evidence covers the promised contract;
4. representative ordinary-agent evidence does not reveal a known architectural blocker to the claimed maturity;
5. installation, security, removal, and failure behavior are documented at the same support level;
6. exact release identity and support evidence are immutable/source-bound rather than asserted only by prose;
7. generated/reference surfaces that project maturity or release identity agree with their source owner.

Do not create a second informal maturity scale for individual capabilities merely because one subsystem has stronger evidence than another. Record stronger or weaker capability evidence in [Evidence and support](evidence-and-support.md) while keeping the public distribution's maturity owned by the coordinated release contract.

## Evidence boundary

Maturity is a compatibility/support claim, not a feature-count score.

- Live-agent results are behavioral evidence, not deterministic compatibility proof.
- Deterministic contracts/tests are not proof that real agents discover or use the product cheaply or correctly.
- Exact artifact admission is not publication.
- Publication of a prerelease is not stable support.
- A stable release does not widen platform/provider support beyond its evidence.

Public maturity decisions should consider both deterministic and representative behavioral evidence while keeping weak, unavailable, and negative evidence visible.

Historical candidate dispositions and migration-era maturity decisions belong in maintainer/review evidence, not in this current vocabulary page.

See [Evidence and support](evidence-and-support.md), [Installation and adoption](agentic-workspace-install.md), [Documentation status](documentation-status.md), and the [Threat model](security/threat-model.md).
