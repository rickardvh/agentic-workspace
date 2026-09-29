# Release Agentic Workspace

After reviewed changes merge, select **Actions → Release → Run workflow**, choose
**master**, and leave the inputs at their defaults. The run selects the source and
version, builds and checks the packages, publishes the verified files, and
verifies GitHub, PyPI, npm and crates.io. Configured environment approvals remain.

The summary identifies the selected commit, version and each destination's
result. No unconsumed changes means a successful run with nothing to release.

## Declare release intent

Package-affecting PRs need exactly one `semver:major`, `semver:minor` or
`semver:patch` label and a matching fragment under `.release/changes/`:

```toml
schema_version = "agentic-workspace/release-change/v1"
bump = "patch"
summary = "Describe the user-visible change."
```

The label records the compatibility decision. Ordinary PR fragments must match
it. The existing [exact-tree integration exception](../src/tooling/release/pr_semver_integration.py)
requires its own immutable evidence. `Semver admission` and `Merge sufficiency`
remain the branch checks.

Selection uses new fragment revisions since the most recent verified, completed
stable release's source. Retained fragments and unchanged renames or deletions do
not request another release. Consumed fragments may be pruned during normal
maintenance. The highest new bump determines the next version above reserved
public stable and preview identities. Partial publication requires recovery.

## Source and package identity

Development manifests use `0.0.0.dev0` for Python and `0.0.0-dev.0` for Cargo.
They remain usable without Git or network version discovery. Release jobs stamp
one resolved version before compilation, using only allowed identity fields.
Code, file modes and third-party dependency resolution cannot change.

The annotated tag points to the reviewed source. The retained identity and
manifest bind that source to the fragments, stamping transformation and tested
artifact digests. Notes are generated into the GitHub assets. Existing
`.release/releases/` files remain historical records.

## Validate and recover

Select **qualify_only** to build and check without tagging or publication. This
can exercise a candidate branch; publication requires a dispatch on protected
master.

For interruption, use **Re-run failed jobs**. After a tag exists, a later Release
dispatch on master may set **tag** to that exact tag. Recovery retrieves the
original verified bundle and publishes only missing items. Missing retained
material, conflicting digests and uncertain remote responses stop recovery.

A GitHub release alone does not establish coordinated completion. Both registry
receipts must pass before completion is reported. The current-install projection
uses a completed release, so a partial newer release cannot become its boundary.

See [native release topology](maintainer/native-release-topology.md) for package
layouts and platform requirements, and [release validation](maintainer/release-validation.md)
for the replacement's evidence.
