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

The next coordinated version must be greater than both:

- every checked-in shipped package version; and
- every existing public `vMAJOR.MINOR.PATCH` tag.

Existing malformed public tags are treated as burned identities. They are not
moved or reused by default; the next valid release moves forward past them.

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
- release changeset directory;
- release notes directory;
- release PR branch; and
- publisher trigger and tag rule.

Workflows and tests should read this manifest instead of carrying separate
workflow-local path lists.

## Release Changesets

Package-affecting PRs must have exactly one semver label:

- `semver:major`
- `semver:minor`
- `semver:patch`

They must also add at least one source-controlled changeset under
`.release/changes/`:

```toml
schema_version = "agentic-workspace/release-change/v1"
bump = "patch"
summary = "Describe the user-visible release note."
```

The semver label is the maintainer-owned compatibility decision, and every
changeset in the PR must declare the same bump as that label. Docs-only or
planning-only changes can skip a semver label and changeset unless they affect
packaged behavior, compatibility, release policy, generated outputs, shipped
payloads, or release workflow behavior.

## Release PR

After one or more package-affecting PRs merge to `master`, the release workflow
runs from the `master` push event and reads pending changesets from source. It
does not read mutable PR labels after merge, parse merge commit messages, or
publish assets from the `master` push context.

The release workflow:

1. reads `.github/release-ownership.json`;
2. reads pending `.release/changes/*.toml` files;
3. computes the highest requested bump;
4. computes the next coordinated version from the maximum of checked-in package
   versions and existing public release tags;
5. opens or updates a release PR from `automation/coordinated-release`;
6. rewrites all package `pyproject.toml` and TypeScript `package.json` versions
   to the same value;
7. updates `uv.lock`; and
8. consumes the pending changesets after copying their summaries into
   `.release/releases/vMAJOR.MINOR.PATCH.md`.

The release PR must become current with `master` before merge. If additional
package-affecting PRs merge first, the release workflow updates the same release
PR and recomputes the version from all remaining changesets.

The generated release manifest is intentionally not committed. It belongs to the
release artifact set. The release PR must not mix product behavior changes with
version normalization. The committed release note is the durable reviewable
record of consumed changeset summaries and is used as the GitHub Release body.

## Release Tagging

When the release PR merges to `master`, the master workflow computes a pending
tag plan from the current release state, not only from the latest push diff. It
verifies that every coordinated package manifest declares the same version, that
the version is greater than every existing public release tag, and that the
release commit includes `.release/releases/vMAJOR.MINOR.PATCH.md`. It then
creates an annotated `vMAJOR.MINOR.PATCH` tag at the release commit.

The master workflow never publishes GitHub Release assets. Its only release-side
mutation after a release PR merge is the annotated tag. Tag creation and
publisher dispatch are separate decisions: `tag_needed` means the verified tag
does not exist yet, while the publisher remains dispatchable whenever that tag
exists and the GitHub Release assets are absent, draft, or incomplete. Before
dispatching, the master workflow checks the release assets for
`SHA256SUMS` and `agentic-workspace-release-manifest.json`; if they already
exist on a non-draft release, it does not dispatch another publisher run.

After the tag exists and publication is still needed, the master workflow
explicitly dispatches the tag publisher with the tag and expected source commit
so publication does not depend on GitHub starting a second workflow from a
repository-token tag push. If tag push succeeds but dispatch or publication
fails, rerunning the preparer computes the same verified tag/source commit and
re-dispatches the publisher without creating another version bump. Once the
release artifacts exist, later preparer runs become no-ops for that tag.

## Tag Publisher

The tag workflow is the only GitHub Release publisher. It runs either from a
manual tag-push event or from the master workflow's explicit dispatch for an
existing `vMAJOR.MINOR.PATCH` tag, and must verify that:

1. the tag resolves to the checked-out commit;
2. any dispatch-provided expected source commit matches the tag target;
3. the commit is reachable from `origin/master`;
4. every shipped Python and TypeScript package declares the tag version;
5. every TypeScript package remains publishable;
6. `.release/releases/vMAJOR.MINOR.PATCH.md` exists and becomes the GitHub
   Release body;
7. all artifacts and checksums match; and
8. `agentic-workspace-release-manifest.json` records the same tag and source
   commit that were built.

The publisher may create or update the GitHub Release for that existing tag, but
it must not implicitly invent a missing tag or accept a tag whose target does not
match the verified release commit.

## Release Recovery

Publication recovery follows the existing tag, not a new changeset. The recovery
report inspects the `Release` workflow because artifact build and publication
failures happen there. For an active failed publisher run, the intended repair is
to redispatch the same tag and source commit:

```bash
gh workflow run release.yml --ref master -f tag="vMAJOR.MINOR.PATCH" -f source_commit="<release-commit>"
```

Only use a new changeset-backed release PR when the product change itself still
needs a release bump or no verified release tag exists yet.

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
install URLs, and runs `uv lock` unless `--no-lock` is supplied. Explicit
`--wheel-url --sha256` input still verifies the downloaded wheel bytes by
default; use the deliberately named `--trust-supplied-sha256` escape hatch only
for offline/no-network maintenance. Use `--check` to fail when the checked-in pin
or Dockerfile refs do not match the selected release.

## All-Or-Nothing Invariant

Coordinated releases are all-or-nothing. If any Python package version,
TypeScript package version, lockfile entry, generated artifact, wheel, sdist, npm
tarball, checksum, release manifest entry, or install proof is inconsistent, the
workflow must fail before creating or publishing the tag or release.

The hard identity invariant is:

```text
tag vV -> commit C -> all package manifests declare V -> release manifest source_commit C
```

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
