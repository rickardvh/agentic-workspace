# Release And Versioning

Agentic Workspace uses coordinated workspace releases. The root
`agentic-workspace`, `agentic-workspace-memory`, `agentic-workspace-planning`, and
`agentic-workspace-verification` release together under one coordinated numeric
version, with both Python and TypeScript CLI distributions treated as first-class
release artifacts. Stable/support-bearing tags use `vMAJOR.MINOR.PATCH`; external-
testing previews use the distinct `preview-vMAJOR.MINOR.PATCH` namespace.

## Support-bearing promotion boundary

`master` is protected by a repository ruleset whose required status is the stable `Support-bearing promotion` aggregate from `.github/workflows/ci.yml`. CI also runs on pushes to `master`, so the exact integrated commit receives that server-observed check before release preparation can proceed.

The support-bearing release workflows begin with read-only admission jobs. They query GitHub check runs for the exact source commit through `scripts/release/support_bearing_promotion.py`; only a downstream job receives tag, release, pull-request, or dispatch write permissions. Stable publication additionally composes `support-bearing-promotion.json` from exact-commit server and runtime receipts plus the existing packed-artifact semantic, install, distribution/license, and security receipts. Missing, stale, mismatched, failed, or unsupported evidence fails closed.

Contributors can replay the exact packed npm-artifact semantic lane with `make packed-artifact-conformance`. The Make target and hosted CI invoke the same `run_generated_command_package_proof.py --packed-conformance` authority; its receipt identifies every tarball digest, the Node runtime, the conformance registry, and whether the execution was local or hosted. A local pass proves that semantic lane only. Hosted runner provisioning, permissions, services, artifact upload, other jobs, and required-check aggregation remain host-only evidence, so local replay never claims a hosted CI pass.

The authoritative required check, runtime matrix, Node semantic majors, and receipt names for support-bearing promotion live in `.github/support-bearing-promotion.json`. Domain checkers remain authoritative for their own evidence. Preview publication reuses applicable package, install, semantic, security, SBOM, checksum, and provenance authorities but does not create a support-bearing promotion receipt.

## Stable Release Goal

The ordinary support-bearing downstream path should be:

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
coordinated stable or preview release, every shipped Python package `pyproject.toml`
and generated TypeScript CLI `package.json` must be normalized to the same numeric
version before artifacts are built.

The next coordinated version must be greater than:

- every checked-in shipped package version;
- every existing public `vMAJOR.MINOR.PATCH` stable tag; and
- every existing public `preview-vMAJOR.MINOR.PATCH` package identity.

Every canonical preview tag reserves its numeric package version independently
of later package additions, removals, or moves. Even an invalid subject under a
canonical preview tag burns the version; reservation does not admit publication.
A public preview therefore burns its numeric package version. The same version is
never reused later for different stable or preview bytes.

Existing public tags are never moved or reused by default. Canonical preview
tags reserve versions even when their subjects fail validation; noncanonical
preview spellings are rejected rather than admitted as release identities.

Independent package releases are out of scope until the repo explicitly changes
release model and updates the release ownership manifest, workflows, tests, and
docs together.

## Release Ownership Manifest

`.github/release-ownership.json` owns the machine-readable release policy:

- package-affecting paths;
- semver labels;
- stable and preview release-commit allowed paths;
- shipped Python and TypeScript package lists;
- per-package artifact prefixes;
- TypeScript package roots, tarball prefixes, runtime requirements, and publish
  policy;
- payload schema or installed-state provenance surfaces;
- generated-command contract version;
- release changeset and release-note directories;
- preview subject metadata directory;
- release PR branch; and
- stable and preview publisher triggers and tag rules.

Workflows and tests should read this manifest instead of carrying separate
workflow-local policy lists.

## Preview Releases

A preview is an immutable packaged reconstruction candidate for external testing.
It is explicitly **non-support-bearing**: it does not establish Stable/1.0 support,
does not satisfy #2990 support-bearing admission, and does not create
`support-bearing-promotion.json`.

A maintainer publishes one by choosing an unused numeric coordinated version. By
default the helper refreshes and selects the current `origin/reconstruct/first-stable`
head; an exact older source commit may be supplied only if it is still reachable
from that fetched reconstruction branch:

```bash
uv run python scripts/release/preview_release.py --version 0.52.0
```

Inspect the returned exact source/artifact identities first. To publish the same
subject, rerun with `--push`:

```bash
uv run python scripts/release/preview_release.py --version 0.52.0 --push
```

For an explicit candidate:

```bash
uv run python scripts/release/preview_release.py --version 0.52.0 --source-commit <exact-reconstruction-sha> --push
```

The helper does not commit version normalization to the reconstruction branch or
`master`. It creates a detached release-only commit whose single parent is the
selected reconstruction source, permits only the exact release-owned paths listed
by `preview_release_commit_allowed_paths`, writes preview release metadata/notes,
updates the coordinated lockfile, and creates the immutable
`preview-vMAJOR.MINOR.PATCH` tag. With `--push`, only that tag is pushed.

The tag triggers `.github/workflows/preview-release.yml`, which verifies the exact
source/artifact relationship, builds the same coordinated Python and TypeScript
release assets, patches the root wheel to exact same-preview dependency URLs and
digests, exercises packaged install and generated-command semantics, emits security
readiness and an SBOM, creates checksums and artifact attestations, and publishes a
GitHub Release marked prerelease.

`agentic-workspace-preview-release-manifest.json` records both identities:

```text
exact reconstruction source C
  -> release-only artifact commit P (single parent C)
  -> preview-vV
  -> exact packaged artifacts and checksums
```

The manifest and preview install/readiness receipts carry `release_class = preview`
and `support_bearing = false`. Installation still uses an exact root-wheel GitHub
Release URL and digest, so a tester does not need a repository checkout or a
mutable branch install.

Rerunning the helper for the same existing tag/source verifies and reuses that
immutable subject. A reused version with a different source, artifact commit, tag,
or package identity fails closed. If publication fails after the tag is created,
recovery follows that same immutable tag rather than allocating a second package
version.

The stable path remains separate: `vMAJOR.MINOR.PATCH` tags still require the
master-reachable support-bearing subject and its existing admission evidence.
Preview tags cannot enter that stable tag namespace or remove any stable gate.

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
   versions and existing public stable/preview package identities;
5. opens or updates a release PR from `automation/coordinated-release`;
6. rewrites all package `pyproject.toml` and TypeScript `package.json` versions
   to the same value;
7. updates `uv.lock`; and
8. consumes the pending changesets after copying their summaries into
   `.release/releases/vMAJOR.MINOR.PATCH.md`.

The release PR must become current with `master` before merge. If additional
package-affecting PRs merge first, the release workflow updates the same release
PR and recomputes the version from all remaining changesets.

The generated stable release manifest is intentionally not committed. It belongs
to the release artifact set. The release PR must not mix product behavior changes
with version normalization. The committed release note is the durable reviewable
record of consumed changeset summaries and is used as the GitHub Release body.

## Release Tagging

When the release PR merges to `master`, the master workflow computes a pending
tag plan from the current release state, not only from the latest push diff. It
verifies that every coordinated package manifest declares the same version, that
the version is greater than every existing public coordinated stable/preview
package identity, and that the release commit includes
`.release/releases/vMAJOR.MINOR.PATCH.md`. It then creates an annotated
`vMAJOR.MINOR.PATCH` tag at the release commit.

The master workflow never publishes GitHub Release assets. Its only release-side
mutation after a release PR merge is the annotated stable tag. Tag creation and
publisher dispatch are separate decisions: `tag_needed` means the verified tag
does not exist yet, while the publisher remains dispatchable whenever that tag
exists and the GitHub Release assets are absent, draft, or incomplete. Before
dispatching, the master workflow checks the release assets for
`SHA256SUMS` and `agentic-workspace-release-manifest.json`; if they already
exist on a non-draft release, it does not dispatch another publisher run.

After the tag exists and publication is still needed, the master workflow
explicitly dispatches the stable tag publisher with the tag and expected source
commit so publication does not depend on GitHub starting a second workflow from a
repository-token tag push. If tag push succeeds but dispatch or publication
fails, rerunning the preparer computes the same verified tag/source commit and
re-dispatches the publisher without creating another version bump. Once the
release artifacts exist, later preparer runs become no-ops for that tag.

## Stable Tag Publisher

`.github/workflows/release.yml` is the only support-bearing GitHub Release
publisher. It runs either from a manual tag-push event or from the master
workflow's explicit dispatch for an existing `vMAJOR.MINOR.PATCH` tag, and must
verify that:

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

The stable publisher may create or update the GitHub Release for that existing
tag, but it must not implicitly invent a missing tag or accept a preview/non-master
subject in place of the verified support-bearing release commit.

## Stable Release Recovery

Stable publication recovery follows the existing tag, not a new changeset. The
recovery report inspects the `Release` workflow because artifact build and
publication failures happen there. For an active failed publisher run, the
intended repair is to redispatch the same tag and source commit:

```bash
gh workflow run release.yml --ref master -f tag="vMAJOR.MINOR.PATCH" -f source_commit="<release-commit>"
```

Only use a new changeset-backed release PR when the product change itself still
needs a release bump or no verified release tag exists yet.

## Python Install Shape

Python packages are released as GitHub Release assets, not through a package
index. The root `agentic-workspace` wheel is therefore patched during release so
its `Requires-Dist` entries for `agentic-workspace-memory`, `agentic-workspace-planning`, and
`agentic-workspace-verification` point to the same GitHub Release wheel assets with
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

A support-bearing coordinated release is all-or-nothing. If any Python package
version, TypeScript package version, lockfile entry, generated artifact, wheel,
sdist, npm tarball, checksum, release manifest entry, install proof, or support-
bearing evidence is inconsistent, the stable workflow must fail before publishing
the release.

For an existing preview, repeat the helper with the same numeric version and
`--push`. Recovery derives C from the immutable tag's metadata and exact parent,
even after reconstruction advances. An optional `--source-commit C` must match
that recorded source; C must still be reachable from the fetched reconstruction
branch. It verifies the immutable tag using the
current verifier, including the source-owned release-only delta and package
metadata. A complete prerelease with matching source/artifact manifest and asset
checksums is a no-op. Otherwise it selects only the exact preview workflow's
tag-push run for P and that tag. Failed or cancelled runs are rerun in place;
active runs are left running. A missing, mismatched, or otherwise nonrecoverable
run fails closed. The tag is never moved, deleted, or recreated for recovery.

Preview normalization refreshes the four exact generator-owned fingerprint
receipts after version and lockfile normalization, using the existing generator.
These release-only receipt updates stay on P.

Publisher retries inspect existing release bytes before building and again
before upload. Existing assets must be byte-identical; replacement is disabled,
and previews cannot update the latest-release pointer. If a partial publication
cannot reproduce its existing bytes, recovery stops with that precise gap rather
than changing the public identity.

A preview may retain its already-created immutable tag if later artifact
publication fails; that is a recovery identity, not a successful release claim.
The preview publisher must still fail rather than publish a complete prerelease
when its coordinated artifacts, receipts, checksums, or provenance are
inconsistent.

The identity invariants are:

```text
stable:  tag vV -> commit C -> all package manifests declare V -> release manifest source_commit C
preview: tag preview-vV -> artifact commit P -> single parent source C -> all package manifests declare V -> preview manifest records P and C
```

## TypeScript CLI Packages

Generated TypeScript CLI packages under `generated/*/typescript` are release
surfaces, not private fixtures. They must remain publishable package manifests
with explicit Node runtime requirements and public scoped-package publish
configuration. Release workflows run each package's `npm test`, pack each package
with `npm pack`, include the resulting `.tgz` files in `SHA256SUMS`, and list
them in the appropriate release manifest with the same coordinated release
version as the Python packages.

## Payload Provenance

The coordinated workspace release version is the AW release identity. Workspace
payload provenance records it as `release_identity`, including the exact stable
or preview tag, and installed-state compatibility compares that payload
provenance against the current executable version. Host repositories should be
able to answer which AW release installed or last refreshed `.agentic-workspace/`
without reconstructing state from release notes or package filenames.
