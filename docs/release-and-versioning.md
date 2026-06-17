# Release And Versioning

Agentic Workspace uses coordinated workspace releases. The root
`agentic-workspace` package, `agentic-memory`, `agentic-planning`, and
`agentic-verification` release together under one semver tag.

## Release Goal

The ordinary downstream path should be:

1. CI proves the source tree.
2. CI builds every workspace wheel and sdist.
3. CI proves installation from built artifacts outside the source tree.
4. CI publishes a GitHub Release tagged `vMAJOR.MINOR.PATCH`.
5. The release contains all wheels, all sdists, `SHA256SUMS`, and
   `agentic-workspace-release-manifest.json`.
6. Host repositories can verify release identity, payload provenance, checksums,
   generated-command contract version, and command-generation dependency from the
   manifest plus checksums.

## Coordinated Version

`pyproject.toml` at the repo root is the canonical version source. During a
coordinated release, every shipped package `pyproject.toml` must be normalized to
that same version before artifacts are built.

The current divergent package versions are release debt. The first coordinated
release must choose a workspace-wide version that does not downgrade any shipped
package. The checked-in release ownership manifest records the current floor:
`0.4.0`.

Independent package releases are out of scope until the repo explicitly changes
release model and updates the release ownership manifest, workflows, tests, and
docs together.

## Release Ownership Manifest

`.github/release-ownership.json` owns the machine-readable release policy:

- package-affecting paths;
- semver labels;
- release commit allowed paths;
- shipped package list;
- per-package artifact prefixes;
- payload schema or installed-state provenance surfaces;
- generated-command contract version;
- first coordinated release floor.

Workflows and tests should read this manifest instead of carrying separate
workflow-local path lists.

## Semver Labels

Package-affecting PRs must have exactly one semver label:

- `semver:major`
- `semver:minor`
- `semver:patch`

The semver label is the maintainer-owned compatibility decision. Docs-only or
planning-only changes can skip a semver label unless they affect packaged
behavior, compatibility, release policy, generated outputs, shipped payloads, or
release workflow behavior.

## Post-Merge Release

After a package-affecting PR merges to `master`, the release workflow:

1. reads `.github/release-ownership.json`;
2. detects package-affecting paths;
3. reads the merged PR semver label;
4. computes the next coordinated version, respecting the first-release floor;
5. rewrites all package `pyproject.toml` versions to the same value;
6. updates `uv.lock`;
7. runs tests, lint, typecheck, generated package proof, and package artifact
   proof;
8. builds every wheel and sdist;
9. generates `SHA256SUMS`;
10. generates `agentic-workspace-release-manifest.json`;
11. verifies all release artifacts and metadata before publishing;
12. commits only version normalization and lockfile changes as `Release vX.Y.Z`;
13. pushes the tag and publishes the GitHub Release.

The generated release manifest is intentionally not committed. It belongs to the
release artifact set. The release commit must not mix product behavior changes
with version normalization.

## Manual Tag Release

A manually pushed `vMAJOR.MINOR.PATCH` tag is allowed only when every shipped
package already declares that exact version. The tag workflow builds the same
artifact set, generates checksums and the release manifest, verifies them, and
publishes the GitHub Release.

## All-Or-Nothing Invariant

Coordinated releases are all-or-nothing. If any package version, lockfile entry,
generated artifact, wheel, sdist, checksum, release manifest entry, or install
proof is inconsistent, the workflow must fail before creating or publishing the
tag or release.

## Payload Provenance

The coordinated workspace release version is the AW release identity. Workspace
payload provenance records it as `release_identity`, and installed-state
compatibility compares that payload provenance against the current executable
version. Host repositories should be able to answer which AW release installed or
last refreshed `.agentic-workspace/` without reconstructing state from release
notes or package filenames.
