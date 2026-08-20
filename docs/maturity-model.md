# Maturity Model

This page defines the public maturity vocabulary. Package/distribution metadata and public documentation should use the same label unless a deliberately separate dimension is introduced and mechanically kept in sync.

Manual role review: 2026-08-20.

## Labels

### Alpha

The product/capability is real, tested, and dogfooded, but ordinary behavior, naming, schema shape, compatibility boundaries, or guidance may still change materially. Early adopters should expect change and should rely on versioned release contracts rather than broad stability assumptions.

### Beta

The public contract is broadly usable for early adopters, the supported compatibility boundary is explicit, selective adoption works, and expected changes are mostly additive or refining rather than architectural. Moving to beta should be supported by package metadata, release checks, and representative behavioral evidence rather than documentation wording alone.

### Stable

The support and compatibility contract is deliberate enough that incompatible change is exceptional and follows the project's declared versioning/deprecation policy.

## Current public status

The coordinated Python distributions currently advertise `Development Status :: 3 - Alpha`. Until package metadata and release/evidence policy deliberately promote a surface, public documentation should not independently call the same distribution beta.

| Surface | Public maturity | Current interpretation |
| --- | --- | --- |
| `agentic-workspace` root distribution | alpha | substantial dogfooding and contract coverage exist, but the operating kernel, extensibility boundary, closeout composition, and public documentation/support contract are still being simplified |
| Agentic Planning distribution | alpha | active continuity and closeout behavior are substantial, but Planning ownership/reconciliation and stale-state behavior are still changing materially |
| Agentic Memory distribution | alpha | durable anti-rediscovery capability is substantial, but routing/guidance boundaries and integration with the ordinary decision continue to evolve |
| Agentic Verification distribution | alpha | protocols, evidence, and proof-route behavior are real but the module remains less mature than the older first-party capabilities |
| Generated/runtime targets | alpha unless a release explicitly states otherwise | conformance and packaging are substantial but target parity/support claims remain tied to current release evidence |
| Public independent-module contract | not yet support-bearing | extensibility is a core product direction, but the deliberately small third-party module compatibility profile is still being stabilized |

This table describes public support maturity, not feature count. A capability can have strong deterministic or dogfooding evidence and still remain alpha while its compatibility or ownership boundary is changing materially.

## Promotion rule

Promote a public surface only when all relevant owners agree:

1. package/distribution metadata uses the promoted maturity;
2. the public compatibility/support boundary is explicit;
3. deterministic release/conformance evidence covers the promised contract;
4. representative ordinary-agent evidence does not reveal a known architectural blocker to the claimed maturity;
5. installation, security, removal, and failure behavior are documented at the same support level;
6. the documentation status is source-bound rather than asserted only by a review date.

Do not create a separate informal "capability beta" label merely to describe that one subsystem feels more mature. Record stronger capability evidence in the evidence/support summary while keeping one public distribution maturity label.

## Evidence boundary

Live-agent results are behavioral evidence, not deterministic compatibility proof. Deterministic contracts/tests are not proof that real agents use the product cheaply or correctly. Public maturity decisions should consider both and preserve weak or unavailable evidence rather than reporting only successful runs.

See [Documentation status](documentation-status.md), [Threat model](security/threat-model.md), and the maintainer evaluation documentation for the evidence sources behind future promotion decisions.