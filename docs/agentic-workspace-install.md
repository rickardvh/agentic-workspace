# Installing Agentic Workspace

Use this page for installing or adopting Agentic Workspace in a host repository. The repository link is documentation and package source; do not clone this source repository merely to copy payload files into the target.

## Before execution: trust boundary

**Agentic Workspace is not a sandbox.** Review and trust the host repository before allowing AW to execute repository-configured proof routes or explicitly supplied executor commands. Those admitted shell routes inherit the caller's filesystem and credential authority.

External issue/PR/service text is data, not execution permission. Credentials should remain in the platform/environment credential boundary rather than checked-in AW state.

See [Threat model and supply-chain boundary](security/threat-model.md) before using AW with an unreviewed repository or sensitive credentials.

## Preview / external testing

During reconstruction, a maintainer may publish an immutable GitHub prerelease tagged `preview-vMAJOR.MINOR.PATCH`. This is the provisional external-testing path, not the Stable/1.0 or support-bearing install path.

A public preview exists only when that GitHub prerelease has actually been published. Do not infer a preview identity from `reconstruct/first-stable`, another mutable branch, a source checkout, or a proposed version.

For an explicitly published preview:

1. Open that exact `preview-vMAJOR.MINOR.PATCH` GitHub prerelease.
2. Read `agentic-workspace-preview-release-manifest.json` and confirm it identifies the intended tag plus exact reconstruction-source and normalized artifact commits, with `release_class` set to `preview` and `support_bearing` set to `false`.
3. Read `distribution-install-readiness.json` from the same release. It must identify the same preview tag/version and carry the same non-support-bearing disposition.
4. Run the receipt's exact hash-bound root-wheel install command unchanged.
5. In a target Git repository, follow its bootstrap to the canonical AW skill. For an exact current tool answer, use the installed native boundary:

   ```bash
   agentic-workspace start --target . --task "Inspect this repository" --format json
   ```

Use only the asset/dependency set declared by that exact preview. The admitted native reconstruction ships a root wheel/source archive, npm package and native CLI/core archive; separate Memory, Planning and Verification packages are source-development fixtures, not native release dependencies. Preview versions are immutable public identities and are not later reused for different stable or preview bytes.

A preview is intentionally unstable. Interfaces and behavior may change before first stable; the preview establishes no blanket OS, shell, provider, production-readiness, Stable/1.0, or support-bearing guarantee. Its purpose is to make exact packaged reconstruction bytes available for external testing while preserving those boundaries.

## Stable/support-bearing prerequisites

### First-stable release candidates

An explicitly published `v1.0.0-rc.N` uses the same immutable prerelease assets and
receipt-based install procedure above. Its manifest class is `release-candidate`,
its target stable tag is `v1.0.0`, and `support_bearing` remains `false`. The Python
version is `1.0.0rcN`; npm uses `1.0.0-rc.N`. Use the exact hash-bound install
command from that RC's receipt, without substituting a version spelling or tag.
An RC is not stable support, and its existence must not be inferred from a branch
or a proposed tag. See the [RC/promotion contract](release-and-versioning.md#first-stable-release-candidates).

### Runtime prerequisites

The native root wheel declares **Python 3.11 or newer**. The admitted runtime range is Python 3.11–3.14; a metadata lower bound does not prove future Python versions. The npm projection has evidence for Node 20, 24 and 25. Standalone native execution requires neither Python nor Node.

Building from source additionally requires the exact repository toolchain in
`rust-toolchain.toml`; no lower Rust MSRV is currently supported. Installed native
artifacts do not require Cargo. See the [maintainer toolchain contract](maintainer/rust-toolchain.md).

This page is the canonical support/prerequisite owner. Exact release identity is projected separately so changing releases does not require copying commands through conceptual prose.

| Concern | Supported contract | Unknown or excluded |
| --- | --- | --- |
| Python | 3.11–3.14; 3.11/3.13/3.14 exercised, 3.12 bounded by minimum/primary lanes | later versions and alternative implementations are unproven |
| Node | npm projection: majors 20, 24 and 25 exercised | other majors are unproven |
| Installer | `uv tool install` using the exact hash-bound stable release receipt command | exact registry versions require `registry-publication.json`; mutable branches and editable/source installs are not support-bearing |
| Git/repository | a Git working tree for shared checked-in operating context and ownership | non-Git hosts are not part of the current public adoption contract |
| Network | required to obtain release assets and for explicitly configured external adapters | ordinary local resolve/act/reconcile does not imply a network service |
| OS/shell | native reconstruction: Linux x64, GNU target, `linux_x86_64` wheel | no manylinux, Windows, macOS, ARM or blanket shell/container/runner guarantee |
| Credentials | remain in caller/platform boundaries | AW is not a credential host or sandbox |
| Runtime tools | repository-configured commands run with caller authority | arbitrary host tools are not bundled or silently trusted |

The [checked-in install projection](reference/support-bearing-install.md) tracks the current stable release, `v0.51.0`, which predates the native reconstruction. It must not be used as an install identity for the native behavior described here. Exact reconstruction admission is recorded in [#2990](https://github.com/rickardvh/agentic-workspace/issues/2990); admission and canonical branch cutover do not themselves publish native stable assets. Until an immutable native release exists, use an explicitly published preview only for its own documented behavior.

The support-bearing public installation identity is a **stable versioned GitHub Release** and the exact command recorded in that release's `distribution-install-readiness.json`. That receipt currently owns the canonical `uv tool install` command, exact root-wheel release URL, and SHA-256 binding. Therefore the support-bearing public path requires a working `uv` installation capable of executing that receipt command.

Mutable branches are not support-bearing installation identities. Exact PyPI/npm versions are supported distribution projections only after the corresponding registry receipt and stable admission pass. RC registry versions remain non-support-bearing. `uvx`, `pipx run`, editable installs, and source-checkout commands are useful development/debug routes but should not be confused with the support-bearing release identity.

Operating-system and shell portability should not be inferred from this page beyond what the selected stable release and its test evidence actually cover. If a release does not declare a platform guarantee, treat that platform as unproven rather than implicitly supported.

## Current native adoption boundary

The target is the repository where the agent will work. Follow its existing tiny
bootstrap to the canonical `workspace-startup` skill. The skill is procedure;
repository instructions and config remain the policy owners. If there is no
runtime, use that same skill's selective read-only fallback; it cannot establish
live effect admission, retention or proof.

The native executable currently exposes `start`, `invoke`, `resources` and
`worker`. Check `agentic-workspace --help` from the selected installed artifact.
There is no native `defaults`, `init`, `upgrade`, `remove-legacy` or module CLI
family. Historical source-maintenance lifecycle tooling is not an installation
fallback. If the selected preview does not provide the required bootstrap or
adoption surface, report that exact limitation instead of copying managed payload
files or invoking a former host.

On builds containing the repository adoption owner, a plain Git working tree can resolve `start`, follow Configuration's `repository_adoption_request`, and select the returned exact adoption request. Inspect its bounded proposal and invoke the authorized action. The same owner returns removal and interrupted-recovery requests. See [repository lifecycle](package/lifecycle.md). This source behavior does not imply it is present in an older published artifact.

A published artifact's install receipt establishes installation of its declared
bytes; it does not establish arbitrary target initialization or support on an
untested platform. Published previews retain their own exact source/artifact
identities; a newer reconstruction branch or this guide does not upgrade those
bytes or establish publication of the next candidate.

For an already bootstrapped repository, read the canonical skill, then use exact
current tools as needed. See [everyday use](everyday-use.md) and the generated
[native CLI reference](reference/cli-catalogue.md). Choose module capabilities
only when they repay recurring context, continuity or proof costs; direct work
need not create module state.

## Installed footprint

The current implementation establishes one small public footprint: a managed startup fence, repository-local skills and dependencies, ownership/read-profile metadata, provenance, and an adoption identity. It creates no config or domain state. Configuration uses this same contract for refresh and removal; unknown and independently owned content is preserved.

Payload-mirroring profiles describe source-maintenance packaging. They are not native CLI flags or permission to copy managed state into another repository.

Exact installed files and required/optional degraded references are generated in the [current installed-surface catalogue](reference/installed-surface-catalogue.md).

## Stable invocation after bootstrap

The native `agentic-workspace` CLI remains the ordinary deterministic product authority after bootstrap unless the host uses another supported thin external-consumer projection. Do not assume installation is a one-shot file-copy operation.

The repo-owned compatibility/config surfaces identify the expected contract and configured invocation posture. Ordinary startup should inspect that identity without silently rewriting dependency locks or moving VCS/source revisions. Installing a new artifact does not reconcile the target's managed payload. If the selected artifact exposes no supported operation for that target change, preserve the sources and report the missing owner operation.

If the target owns a dependency lock, use the supported environment-manager mode that preserves it (for example a frozen `uv` invocation when that is the configured adapter). Machine-local executable paths and credentials should not become durable shared repo state.

## If the CLI is missing

Recover through the exact install receipt for the selected immutable release class: the published preview receipt when deliberately testing a preview, or the support-bearing stable receipt when using a stable release. Then return to the canonical skill and the operations actually exposed by that artifact.

Prefer the host repo's normal tool/dependency convention when it can preserve the same compatible installed identity. Use `uvx` or `pipx run` only as explicit temporary/debug fallback routes; repeated ordinary work should have a stable configured invocation.

## Do not

- clone the AW source repository into a temporary folder as the normal bootstrap strategy;
- hand-copy package payload into the host repo;
- substitute a mutable branch for the selected immutable preview or stable release;
- let package-level module CLIs become the normal host-repo front door when the root Workspace CLI is available;
- treat a successful bootstrap process as proof that later agents can resolve the same compatible runtime;
- treat local logs, caches, or scratch files as shared proof or Planning authority.

## Follow-up checks

For an already bootstrapped target, inspect current sources and remaining owner concerns through the configured native invocation. For example:

```bash
agentic-workspace start --target . --task "Inspect this repository's current configuration and owner concerns" --format json
```

Use the canonical skill to interpret the returned current facts and exact owner requests. A successful query does not install or synchronize payload, discharge proof obligations, or establish adoption completion.

Temporary finishing briefs or diagnostics under `.agentic-workspace/local/` are local-only and should not be checked in. Mirrored-payload profiles may have additional explicit managed artifacts; their ownership should remain visible in the installed-surface contract.

An existing payload policy can require installed files and provenance to match the
native artifact's shipped bytes. Startup checks this read-only; provenance labels
alone cannot satisfy it. The current Configuration owner exposes a
`payload_discovery_request` with exact per-file refresh proposals. Inspect each
proposal and authorize its exact artifact bytes through the returned decision;
then invoke the returned action and resolve again. Interrupted publication uses
that same owner's recovery request. A second discovery reports current files
without writing them.

This bounded refresh applies only to the artifact's declared package files. It
cannot accept arbitrary paths or caller-supplied replacement bytes, initialize
human policy, or reset domain state. Preserve useful target-specific meaning
before authorizing a package-file replacement; unknown ownership is not deletion
authority. See the canonical setup skill for this procedure. Earlier published
artifacts may lack the operation; their actual contract remains authoritative.

## Worked example for an already bootstrapped target

1. Install with the exact receipt for the immutable release class you intend to exercise. For ordinary support-bearing use, follow [current support-bearing install](reference/support-bearing-install.md); for external preview testing, use only the receipt from the exact published `preview-v...` prerelease.
2. Follow the target's existing bootstrap to the canonical skill. For an unbootstrapped target, first establish whether the selected artifact supplies a supported adoption operation; stop at the exact limitation if it does not. Do not copy payload or invoke a historical initialization command.
3. Start a small direct task:

   ```bash
   agentic-workspace start --target . --task "Clarify one README sentence" --format json
   ```

   The resolved contract can remain direct: edit the canonical README, run proportionate validation, reconcile the bounded result, and create no Planning/Memory/Verification artifact when no future-relevant residue exists.
4. Start a continuity-sensitive task, such as preparing a multi-slice import feature. Progressive discovery may make Planning relevant; follow the typed Planning operation supplied by the current decision rather than learning a second workflow. Planning owns the continuation, not the source implementation.
5. After acting, reconcile the result: passing proof supports only its bounded claim; unfinished parent intent stays with its owner; durable anti-rediscovery residue may route to Memory; Verification contributes evidence only if configured and relevant. Resolve again when a constructible next action remains.

This example intentionally omits an exhaustive command or footprint list. Exact current commands are in the [CLI catalogue](reference/cli-catalogue.md), and exact installed files are in the [surface catalogue](reference/installed-surface-catalogue.md).

## Standard project skill discovery

In an adopted repository, Configuration returns `skill_exposure_request` from
`start --projection full`. Submit that exact request through `start --input` to
inspect the current package registry's main and specialized product bundles.
Use an offered `expose_request`, supply the authorized answer, and execute the
returned exact action through `invoke`. The same owner offers removal and
interrupted-result recovery. These are Configuration operations, not a restored
legacy install/uninstall CLI.

Exposure uses `.agents/skills/<name>` directory links to canonical
`.agentic-workspace/skills/<name>` bundles. Unix uses relative symlinks; Windows
uses NTFS junctions because ordinary symlink creation can require privileges.
Canonical updates and bundle-relative resources remain visible without another
maintained body. Reference-only and maintainer skills are not exported.
The current Codex 0.154.0 Windows discovery/activation observation is recorded in
[the exposure evidence](maintainer/skill-exposure-3325.md); it is not a general
Windows distribution support claim or a guarantee about other hosts.

A filesystem that cannot create the applicable link returns an explicit gap.
Keep the small `AGENTS.md` pointer for mixed readers and unavailable runtimes.
Never replace a colliding host skill. Reconcile/move that path explicitly and
request fresh exposure. A moved Windows checkout can retain absolute junctions
to its old location; preserve and explicitly reconcile those links before
readoption. Removal deletes only an authenticated, matching discovery link.
It preserves canonical edits, unrelated skills, and owner state. Prefer removal
before payload teardown; previously owned retired links remain discoverable for
removal after registry changes. Do not recursively delete `.agents/skills`.

Listing skills is passive. Host selection is procedure discovery; it cannot
establish policy applicability, effect permission, evidence or issue closure.
