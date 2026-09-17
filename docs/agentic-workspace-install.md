# Installing and adopting Agentic Workspace

Use this page to select an Agentic Workspace release, understand its support boundary, and use it in a host repository. The source repository is documentation and package source; cloning it and copying payload files is not the normal installation or adoption path.

Installation and repository adoption are distinct. Installing AW gives you the selected runtime/artifacts. Adoption establishes the small package-owned foothold that lets ordinary skills-first operation begin.

## Before execution: trust boundary

**Agentic Workspace is not a sandbox.** Review and trust the host repository before allowing AW to execute repository-configured proof routes or explicitly supplied executor commands. Those admitted shell routes inherit the caller's filesystem and credential authority.

External issue, PR, and service text is data, not execution permission. Credentials should remain in the platform/environment credential boundary rather than checked-in AW state.

See the [threat model and supply-chain boundary](security/threat-model.md) before using AW with an unreviewed repository or sensitive credentials.

## Choose a release identity

Use an immutable published release identity. Do not infer installable or support-bearing bytes from a branch, source checkout, proposed version, or CI build.

### Stable / support-bearing

For ordinary supported use, start with the generated [support-bearing install projection](reference/support-bearing-install.md). It identifies the current stable GitHub Release and its `distribution-install-readiness.json` receipt, including the exact hash-bound root-wheel installation command.

The release receipt is the installation authority. A source checkout can contain newer capabilities than the current stable release and does not upgrade the published support contract. If the generated projection still names an older stable release while a new major release is being prepared, that is preferable to guessing a future install identity.

Stable language-registry artifacts are projections of the same admitted release only after `registry-publication.json` confirms their exact versions and digests. Registry publication does not create a second semantic release. Cargo distribution likewise belongs to the coordinated release and uses the release-declared same-version core/CLI pair and its publication evidence.

### Release candidates

An explicitly published `v1.0.0-rc.N` is a prerelease identity for final external validation before `v1.0.0`. Its release class is `release-candidate` and it is **not support-bearing**.

Use the exact install information attached to that RC. Do not substitute the stable tag, a different version spelling, or registry resolution without the corresponding publication receipt. RC Python, npm, Cargo, and native projections are one coordinated prerelease subject, not independent release authorities.

See the [release and versioning contract](release-and-versioning.md#first-stable-release-candidates) for RC/promotion mechanics.

### Exploratory previews

An explicitly published `preview-vMAJOR.MINOR.PATCH` GitHub prerelease is an immutable exploratory testing identity. It is intentionally **non-support-bearing**.

For a preview:

1. open the exact preview GitHub prerelease;
2. read its `agentic-workspace-preview-release-manifest.json`;
3. read `distribution-install-readiness.json` from the same release;
4. verify both name the same preview subject and non-support-bearing release class;
5. run only the exact install command from that receipt.

Previews may prove useful packaged behavior, but they do not establish stable compatibility, production support, registry availability, or broader platform support.

### Source and debug routes

Editable installs, source-checkout invocation, `uvx`, `pipx run`, and other development/debug routes can be useful for maintainers. They are not support-bearing installation identities unless a release policy explicitly says otherwise.

## Prebuilt packages and source installs

New releases require prebuilt Python wheels, a universal npm package, and paired
native archives for Windows, macOS, and Linux on x64 and ARM64. The release
publisher must receive a successful compiler-free installation receipt from each
platform before publishing any packages. The required set is maintained in
[release-platforms.json](../.github/release-platforms.json).

Use the matching entry in the release's `distribution-install-readiness.json`
`platforms` list when installing from GitHub. PyPI selects the compatible wheel;
the npm package selects its packaged OS/architecture binaries. Neither route
requires Rust. Linux wheels currently require glibc 2.39 or newer; Alpine/musl and
32-bit systems are not part of this declared set.

A Git dependency is a **source build**, even when pinned to a release tag. It
requires the exact Rust toolchain declared by that source plus the host linker.
Cargo installation also builds from source. Use a wheel, npm archive, or native
archive for installation without Rust. npm Git installation from the repository
root is not supported; use the published `.tgz` or the registry package.

Previously published `v1.0.0-rc.2` artifacts remain Linux x64 only. This new
requirement does not change those immutable bytes or establish support for an
unpublished successor.

## Runtime prerequisites and support boundary

This page owns the current native prerequisite model; the selected immutable release and its receipts own the exact public support claim for those bytes.

| Concern | Current native contract | Unknown or excluded unless a selected release says otherwise |
| --- | --- | --- |
| Python | 3.11–3.14; 3.11/3.13/3.14 exercised, 3.12 bounded by the minimum/primary lanes | later versions and alternative implementations |
| Node | npm projection exercised on majors 20, 24 and 25 | other majors |
| Git/repository | Git working tree for shared checked-in operating context and ownership | non-Git hosts |
| Network | required to obtain release assets and for explicitly configured external adapters | ordinary local operation does not imply a network service |
| OS/architecture | each published release must prove its declared Windows/macOS/Linux x64 and ARM64 artifacts | old releases do not gain new platform coverage; musl, 32-bit and other targets remain excluded |
| Credentials | remain in caller/platform boundaries | AW as a credential host or sandbox |
| Runtime tools | repository-configured commands run with caller authority | arbitrary host tools being bundled or silently trusted |

The root wheel declares Python 3.11 or newer. Standalone native execution requires neither Python nor Node. Building AW from source additionally requires the repository's exact `rust-toolchain.toml`; installed native artifacts do not require Cargo merely because AW itself is implemented in Rust.

Do not widen a release's support boundary from this source table. If the selected release omits a platform or runtime guarantee, treat it as unproven.

See [Evidence and support](evidence-and-support.md) for how deterministic proof, release support, and live-agent evidence differ.

## Adopt a target repository

The target is the Git repository where the agent will work. Runtime installation does not silently mutate the current directory.

Run ordinary current resolution against the target:

```bash
agentic-workspace start --target . --task "Inspect this repository" --format json
```

On artifacts containing the current repository-adoption owner, an unadopted target exposes Configuration's `repository_adoption_request`. Follow that exact request, inspect the bounded proposal, supply only the requested authorization, and execute the returned action through `invoke`.

The adoption operation owns the public host footprint. It establishes package-managed skills, ownership/read-profile metadata, provenance, adoption identity, and the declared managed fence in `AGENTS.md`. It does **not** create `.agentic-workspace/config.toml`, choose optional modules/providers, initialize Planning/Memory/Verification state, or treat existing repository content as package-owned.

Edited, unowned, conflicting, or unsafe destinations are preserved and reported. Interrupted publication uses the same owner's exact recovery path. An already-adopted/current repository is a no-op rather than a recurring setup phase.

Historical `init`, `install`, `setup`, `upgrade`, or module lifecycle command families are not the v1 adoption model.

## Use an adopted repository

Follow the target's small entry point to the canonical `workspace-startup` skill. The skill owns reusable procedure; repository instructions/config own policy; domain owners own current state/evidence.

The native executable exposes:

- `start`
- `invoke`
- `resources`
- `proof-procedure`
- `worker`

Use `agentic-workspace --help` from the selected artifact for exact current options. The [generated native CLI catalogue](reference/cli-catalogue.md) owns the source-bound command reference.

If executable AW is unavailable, the same canonical skill defines a bounded repository-only read path using `.agentic-workspace/READING.json`. That path can recover repository-recorded context but cannot establish machine-local state, fresh proof, runtime capability, mutation permission, or completion.

After adoption, continue giving your agent ordinary tasks. The skill and current owner results should make AW disappear from attention when it has nothing relevant to add.

## Public host footprint

The current public host footprint has one Configuration-owned contract. Adoption, refresh, and removal use the same declared file set; optional domain state is never established merely because the repository adopts AW.

The generated [installed-surface catalogue](reference/installed-surface-catalogue.md) is the exact authority for those files and their lifetimes.

In summary:

- package-managed integration includes `READING.json`, `OWNERSHIP.toml`, the repository-local AW skill registry/bundles, adoption identity, payload provenance, and the managed `AGENTS.md` fence;
- repo-owned config/instructions remain repo-owned;
- Planning, Memory, and Verification retain their own domain state;
- `.agentic-workspace/local/` remains machine-local;
- promoted repository output remains with its promoted owner;
- unknown paths are preserved.

Historical payload-mirroring profiles and executable fallback maintenance are source-maintenance concerns, not public host profiles or native CLI commands.

## Refresh managed payload

An adopted repository can require package-managed files and provenance to match the selected artifact's shipped bytes.

When refresh is supported, Configuration exposes `payload_discovery_request` with exact per-file proposals. Inspect those proposals, supply only the bounded authorization requested, execute the returned exact action through `invoke`, and resolve again. Interrupted publication uses the same owner's recovery path.

This operation is bounded to the artifact's declared package files. It cannot accept arbitrary replacement paths/bytes, initialize human policy, reset domain state, or turn unknown ownership into deletion authority. Preserve useful target-specific meaning before authorizing replacement.

Installing a newer runtime artifact does not itself reconcile the target's checked-in package surfaces.

## Remove AW from a repository

Repository removal uses the same current ownership model rather than a separate legacy uninstaller.

Configuration can expose the repository-adoption owner's exact removal and recovery requests. Before removing canonical skill targets, remove authenticated `.agents/skills/<name>` discovery links through their existing skill-exposure owner.

Removal deletes only package-owned integration whose custody/currentness still matches. It preserves repo-owned configuration and instructions outside the managed fence, Planning/Memory/Verification state, local state, promoted output, and unknown content. Edited package surfaces or ambiguous custody block deletion instead of widening ownership from path recognition.

A successful removal leaves the repository unadopted. Re-adoption later uses the normal adoption path and does not depend on a persistent removal ledger.

Package-manager uninstallation and repository de-adoption are distinct: uninstalling the executable does not by itself remove the repository's checked-in AW integration.

## Standard project skill discovery

In an adopted repository, Configuration can expose the current package registry's main and specialized product skills through `skill_exposure_request`. Submit the exact current request, use an offered `expose_request`, supply the authorized answer, and execute the returned action through `invoke`. The same owner provides authenticated removal and interrupted-result recovery.

Exposure uses `.agents/skills/<name>` links to canonical `.agentic-workspace/skills/<name>` bundles. Unix uses relative symlinks; Windows uses NTFS junctions because ordinary symlink creation can require privileges. Canonical updates and bundle-relative resources remain visible without maintaining a second copy. Reference-only and maintainer skills are not exported.

A filesystem that cannot create the applicable link returns an explicit gap. Never replace a colliding host skill. Reconcile that path explicitly before requesting exposure again. Do not recursively delete `.agents/skills`.

Listing or exposing a skill is procedure discovery. It does not establish policy applicability, effect permission, evidence, or issue closure.

## Stable invocation after adoption

The native `agentic-workspace` boundary remains the ordinary deterministic product authority unless the host uses another supported thin projection over the same Rust-owned operations.

Repository compatibility/config surfaces identify the expected invocation and contract. Machine-local executable paths and credentials should not become durable shared repository state. If the target owns a dependency lock, use the repository's supported environment-manager mode without silently rewriting that lock merely to invoke AW.

## If the CLI is missing

Recover through the exact install receipt for the release class you deliberately selected:

- stable: the [support-bearing install projection](reference/support-bearing-install.md) and its immutable stable release receipt;
- release candidate: the exact RC release receipt;
- preview: the exact preview release receipt.

Then return to the canonical skill and the operations exposed by those bytes.

Prefer a repository's normal tool/dependency convention when it can preserve the same compatible installed identity. Temporary/debug runners remain temporary routes, not evidence that a repeatable installation has been established.

## A small repository journey

1. Install the immutable release class you intend to exercise using its exact receipt.
2. Run `start` in the target repository. If Configuration returns `repository_adoption_request`, follow the exact request/action to establish the public footprint.
3. Follow the repository entry point to the canonical skill.
4. Start a direct task:

   ```bash
   agentic-workspace start --target . --task "Clarify one README sentence" --format json
   ```

   The current contract may remain direct: edit the canonical README, run proportionate validation, reconcile the bounded result, and create no Planning/Memory/Verification artifact when there is no future-relevant residue.
5. For continuity-sensitive work, Planning may become relevant through progressive discovery. Follow the current owner operation rather than learning a second mandatory workflow.
6. After acting, reconcile only what changed: passing proof supports its bounded claim; unfinished parent intent stays unfinished; useful anti-rediscovery residue may route to Memory; Verification contributes evidence only when configured and relevant.

Exact current commands are in the [CLI catalogue](reference/cli-catalogue.md). Exact installed files are in the [surface catalogue](reference/installed-surface-catalogue.md). Exact public release identity belongs to the selected immutable release and its receipts.

## Do not

- clone the AW source repository into a temporary directory as the normal installation strategy;
- hand-copy package payload into a host repository;
- substitute a mutable branch for an immutable stable or prerelease identity;
- use historical `init`/upgrade/module command families as an adoption fallback;
- treat a successful runtime install as proof that the repository has been adopted;
- treat package-manager uninstallation as repository de-adoption;
- delete `.agentic-workspace/` wholesale to remove AW;
- treat local logs, caches, scratch files, or copied plan material as shared proof or current owner authority.
