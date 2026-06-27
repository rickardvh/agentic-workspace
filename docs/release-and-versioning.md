# Release And Versioning

Agentic Workspace uses coordinated workspace releases. The root
`agentic-workspace` package, `agentic-memory`, `agentic-planning`, and
`agentic-verification` release together under one semver tag, with both Python
and TypeScript CLI distributions treated as first-class release artifacts.

## Release Goal

The ordinary downstream path should be:

1. CI proves the source tree.
2. CI builds every workspace wheel, sdist, and TypeScript npm package tarball.
3. CI proves installation from built artifacts outside the source tree,
   including the single-root-wheel public install path.
4. CI publishes a GitHub Release tagged `vMAJOR.MINOR.PATCH`.
5. The release contains all wheels, all sdists, all npm tarballs,
   `SHA256SUMS`, and `agentic-workspace-release-manifest.json`.
6. Host repositories can verify release identity, payload provenance, checksums,
   generated-command contract version, and command-generation dependency from the
   manifest plus checksums.

## Coordinated Version

`pyproject.toml` at the repo root is the canonical version source. During a
coordinated release, every shipped Python package `pyproject.toml` and generated
TypeScript CLI `package.json` must be normalized to that same version before
artifacts are built.

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
- shipped Python and TypeScript package lists;
- per-package artifact prefixes;
- TypeScript package roots, tarball prefixes, runtime requirements, and publish
  policy;
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

After a package-affecting PR merges to `master`, the release workflow runs only
from the `master` push event. It uses GitHub commit-to-PR metadata plus PR file
and label APIs as the release decision source. It must not infer release intent
by parsing merge commit messages, and it must not publish from a PR event
context.

For merged package-affecting PRs, the release workflow:

1. reads `.github/release-ownership.json`;
2. detects package-affecting paths;
3. reads the merged PR semver label;
4. computes the next coordinated version, respecting the first-release floor;
5. rewrites all package `pyproject.toml` and TypeScript `package.json` versions
   to the same value;
6. updates `uv.lock`;
7. runs tests, lint, typecheck, generated package proof, TypeScript package
   tests, and package artifact proof against the release-normalized tree;
8. builds every wheel, sdist, and TypeScript npm tarball;
9. patches the root Python wheel so its sibling AW dependencies resolve from
   same-release GitHub wheel assets;
10. proves the patched root wheel can install the complete workspace stack as a
    single dependency;
11. generates `SHA256SUMS`;
12. generates `agentic-workspace-release-manifest.json`;
13. verifies all release artifacts and metadata before publishing;
14. commits only version normalization and lockfile changes as `Release vX.Y.Z`;
15. pushes the tag and publishes the GitHub Release.

The generated release manifest is intentionally not committed. It belongs to the
release artifact set. The release commit must not mix product behavior changes
with version normalization.

Package-affecting direct pushes to `master` are allowed only as an explicit
version-release path: all shipped Python and TypeScript package versions must
already be updated to the same valid version that does not downgrade below the
coordinated floor. A package-affecting push with neither a merged-PR semver label
context nor an explicit coordinated version bump exits cleanly without
publishing a release.

## Manual Tag Release

A manually pushed `vMAJOR.MINOR.PATCH` tag is allowed only when every shipped
Python and TypeScript package already declares that exact version. The tag
workflow builds the same artifact set, generates checksums and the release
manifest, verifies them, and publishes the GitHub Release.

## Python Install Shape

Python packages are released as GitHub Release assets, not through a package
index. The root `agentic-workspace` wheel is therefore patched during release so
its `Requires-Dist` entries for `agentic-memory`, `agentic-planning`, and
`agentic-verification` point to the same GitHub Release wheel assets with
hashes. Host repositories should be able to depend on the public root wheel as a
single normal dependency and let `uv sync` resolve the coordinated stack.

## Command-Generation Pin Promotion

`command-generation` is consumed as a hash-pinned maintainer dependency for
generated CLI package rendering and proof. When promoting a temporary immutable
git ref or older released wheel to a command-generation release, use:

```bash
uv run python scripts/release/promote_command_generation_release.py --version <version>
```

The helper discovers the GitHub release wheel, verifies or computes its SHA-256
digest, updates `pyproject.toml`, refreshes the generated conformance Dockerfile
install URLs, and runs `uv lock` unless `--no-lock` is supplied. Use `--check`
to fail when the checked-in pin or Dockerfile refs do not match the selected
release.

## All-Or-Nothing Invariant

Coordinated releases are all-or-nothing. If any Python package version,
TypeScript package version, lockfile entry, generated artifact, wheel, sdist, npm
tarball, checksum, release manifest entry, or install proof is inconsistent, the
workflow must fail before creating or publishing the tag or release.

## TypeScript CLI Packages

Generated TypeScript CLI packages under `generated/*/typescript` are release
surfaces, not private fixtures. They must remain publishable package manifests
with explicit Node runtime requirements and public scoped-package publish
configuration. Release workflows run each package's `npm test`, pack each package
with `npm pack`, include the resulting `.tgz` files in `SHA256SUMS`, and list
them in `agentic-workspace-release-manifest.json` with the same coordinated
release version as the Python packages.

## Payload Provenance

The coordinated workspace release version is the AW release identity. Workspace
payload provenance records it as `release_identity`, and installed-state
compatibility compares that payload provenance against the current executable
version. Host repositories should be able to answer which AW release installed or
last refreshed `.agentic-workspace/` without reconstructing state from release
notes or package filenames.
