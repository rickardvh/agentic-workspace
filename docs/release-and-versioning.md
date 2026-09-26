# Prepare and recover a release

Use this guide to take a reviewed AW change through coordinated publication.
For installing AW, use [Getting started](agentic-workspace-install.md).
Exact artefact layouts and platform requirements belong to
[native release topology](maintainer/native-release-topology.md).

## Prepare the change

Package-affecting PRs need exactly one `semver:major`, `semver:minor` or
`semver:patch` label and a matching changeset under `.release/changes/`:

```toml
schema_version = "agentic-workspace/release-change/v1"
bump = "patch"
summary = "Describe the user-visible change."
```

The label is the maintainer's compatibility decision. Ordinary PR changesets must
all match it. Documentation-only work can omit both unless it changes packaged
behaviour, compatibility, release policy, generated output, payloads or workflows.
Do not rewrite accepted changesets to bypass a failed check. The narrowly admitted
mixed-bump stack exception requires an exact previously merged tree and immutable
semver evidence; [the integration checker](../src/tooling/release/pr_semver_integration.py)
owns its identity, expiry and recovery rules. A matching label or branch name is
not that evidence.

## Review the release PR

After changes merge, `release-from-semver-label.yml` reads pending changesets and
qualifies the exact source through explicit exhaustive CI before opening or
updating `automation/coordinated-release`. A source defect stops preparation.
It applies the highest bump,
normalises the shipped package versions and lockfile, and preserves every consumed
summary in `.release/releases/vMAJOR.MINOR.PATCH.md`.

Review that PR against current master. It must contain release normalisation and
notes, not new product behaviour. Newly merged changes update the same PR. The
root `pyproject.toml` is the canonical version source;
[release ownership](../.github/release-ownership.json) declares the shipped set,
allowed paths and triggers. Do not maintain parallel lists in workflow prose.

The generated candidate reuses the named source qualification only after checking
its exact normalisation delta. Candidate artifact and runtime proof still run.
An unrelated product change in that delta fails admission. Ordinary PR CI remains
bounded merge proof; broad proof is an explicit release or high-risk dispatch.

Every coordinated version must exceed the checked-in versions and reserved public
stable/preview identities. A canonical numeric preview reserves its version even
if its subject is invalid. Never move an existing public tag or reuse its version
for different bytes. Independent package releases require an explicit change to
the release model.

## Publish and verify

Merging the release PR lets the master workflow verify the release state, create
the annotated stable tag and explicitly dispatch `release.yml`. The master push
does not itself publish assets. The publisher checks the tag's exact commit,
master ancestry, coordinated versions and release note before building.

`Merge sufficiency` is a source prerequisite, not release readiness. Stable
publication also needs exact-subject runtime, semantic, installation, distribution
and security evidence. Read-only admission precedes write-capable jobs. Missing,
stale, mismatched or failed receipts stop publication. A local packed-conformance
pass does not prove hosted CI or independent acceptance. Required checks and
receipt names come from [promotion policy](../.github/support-bearing-promotion.json)
and its [checker](../src/tooling/release/support_bearing_promotion.py).

Verify the published manifest, checksums and receipts before describing a release
as supported. The coordinated set includes Python, npm, the native pair and Cargo
sources. All declared Windows, macOS and Linux targets must be present; exact
platform/ABI limits come from [the platform declaration](../.github/release-platforms.json).
No registry upload or successful source test extends those support claims.

## Public language registries

PyPI, npm and crates.io receive the admitted release bytes through the existing
registry workflows. Trusted publisher identities and the protected
`package-registries` environment are external prerequisites. Do not put permanent
publisher credentials in the repository. See the
[registry publisher](../src/tooling/release/registry_release.py) and
[Cargo publisher](../src/tooling/release/cargo_release.py) for exact identity checks.

An absent version may be published; an existing version must match the admitted
bytes. Network uncertainty is not absence. A mismatching npm channel requires
bounded reobservation and then deliberate inspection and repair, never automatic
rollback. Newly uploaded versions and their channel are observed for up to five
minutes; immutable identity or digest conflicts stop immediately. Registry receipts add
distribution evidence; they do not rewrite immutable release manifests or grant
stable support.

## Recover the same subject

If publication fails after tagging, inspect the failed `Release` run and recover
the same tag and source commit:

```sh
gh workflow run release.yml --ref master -f tag="vMAJOR.MINOR.PATCH" -f source_commit="<release-commit>"
```

Replace both placeholders with the verified release identity. The publisher must
not invent a missing tag or accept a different subject. Existing complete assets
make later preparation a no-op. Use a new changeset-backed release only for a new
product change or when no verified release tag exists.

## Preview and first-stable recovery

For registry-only recovery of an existing stable release, dispatch `release.yml`
on master with the original `tag` and `source_commit`, adding
`-f registries_only=true`. Python/npm verification uses current reviewed master
tooling, while its release identity is resolved from the immutable tag and checked
against `source_commit`. Ordinary publication remains tag-owned. Recovery fetches
the already-admitted GitHub assets without rebuilding them or moving the tag.

For exploratory external testing, run
`uv run python src/tooling/release/preview_release.py --version <unused-version>`.
Inspect its exact source and release-only artefact commit, then repeat with
`--push` to publish that subject. The helper selects fetched master by default;
an explicit older source must remain reachable from it. Preview tags and receipts
remain non-support-bearing. Recovery reuses the immutable tag and exact assets.
The helper dispatches the shared `release.yml` with an explicit `preview` or
`release-candidate` class. Manual preview recovery supplies `release_class`, `tag`
and `source_commit` to that same workflow. `qualify_only=true` exercises the
candidate stages without publication effects.

The special `v1.0.0-rc.N` promotion path is retained for first-stable recovery,
not ordinary later releases. Its ecosystem version mapping and explicit
`accepted_rc`/proof-reconciliation gates remain in the
[coordinated release owner](../src/tooling/release/coordinated_release.py) and
[retained promotion records](../.release/promotions/). Independent RC acceptance
does not replace fresh stable-subject proof. A product change requires a new
candidate; proof-only reconciliation requires its separately admitted exact tree.

## Keep first contact current

Maintenance observes successful release completion independently. Projection
drift and recurring consumer observations have their own results; they do not
change the publication verdict. Required public registry install checks remain
part of publication. See [hosted automation](maintainer/hosted-automation.md) for
entrypoints, provider boundaries and the contraction audit.

After stable publication, refresh the existing projection and regenerate it:

```sh
python src/tooling/release/current_install.py --refresh
python src/tooling/generate/generate_contract_catalogues.py
```

The checker binds the public release, dereferenced tag, accepted promotion and
receipt digest. CI and the post-publication job report drift until the refresh is
committed. This does not revoke published artefacts or block sibling registry
jobs. Renderer parity alone cannot establish release currentness.

Existing platform, registry and Cargo consumers exercise setup, the installed
startup pointer and a fresh ordinary task. npm-local must work without global AW.
These probes establish delivery, not model obedience or independent acceptance.
Remove a development-only setup notice only after the public journey passes.
