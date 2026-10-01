# Maturity model

This page defines AW's public maturity labels. It is not a manually maintained
status page.

The maturity of a published package belongs to that exact release. A newer source
checkout can contain additional fixes or evidence without changing an older
release.

## Alpha

The product or feature is real, tested and used on real work, but behaviour,
names, schemas, compatibility rules or guidance may still change materially.
Early adopters should expect change and pin versions when reproducibility matters.

## Beta

The public interface is broadly usable for early adopters, supported platforms
and compatibility expectations are clear, and expected changes are mostly
additive or refining rather than architectural.

Moving to Beta requires package metadata, release checks and representative use;
changing documentation wording alone cannot change maturity.

## Stable

Compatibility expectations are deliberate enough that incompatible changes are
exceptional and follow the project's versioning and deprecation policy.

Stable does not mean “works everywhere”. Supported operating systems, runtimes,
agent hosts and integrations remain explicit claims for each release.

## Find the status for the thing you are using

For source code, inspect:

- [release ownership](../.github/release-ownership.json) for the package maturity
  classifier and release model;
- [package metadata](../pyproject.toml) for the distribution metadata;
- release checks when assessing a proposed maturity change.

For installed or published packages, use the exact release you installed and its
attached receipts. Do not infer an older package's maturity from a newer branch.

A preview or release candidate is for testing and does not carry the stable
release's compatibility promises. A stable release must pass the project's
required release and compatibility checks.

## Changing maturity

A public maturity change is justified only when all of the following agree:

1. package metadata uses the new maturity;
2. supported platforms and compatibility expectations are documented;
3. deterministic release checks cover those promises;
4. representative ordinary use has not exposed a known architectural blocker;
5. installation, security, removal and failure behaviour are documented at the
   same level;
6. the release identity and supporting evidence are tied to the exact release
   files and source commit;
7. generated references agree with the source files that define them.

Do not invent a second maturity scale for individual features. Record stronger or
weaker evidence in [Compatibility and support](evidence-and-support.md) without
changing the package's public maturity label.

## What evidence means

Maturity is a compatibility and support claim, not a feature-count score.

- An observed agent run shows what happened under those conditions; it does not
  prove deterministic compatibility.
- Automated contracts and tests do not prove that every agent will discover or
  use the product correctly.
- Passing release checks is not the same as publishing packages.
- Publishing a prerelease does not make it stable.
- A stable release does not support platforms or integrations beyond what its
  release evidence covers.

Historical maturity decisions belong in review or release history, not in this
current vocabulary page.

See [Compatibility and support](evidence-and-support.md),
[Installation and setup](agentic-workspace-install.md),
[Documentation style guide](documentation-style-guide.md), and the
[Threat model](security/threat-model.md).
