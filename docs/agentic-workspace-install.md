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

The root wheel and coordinated module dependencies are bound to exact assets in that same preview release. Preview versions are immutable public identities and are not later reused for different stable or preview bytes.

A preview is intentionally unstable. Interfaces and behavior may change before first stable; the preview establishes no blanket OS, shell, provider, production-readiness, Stable/1.0, or support-bearing guarantee. Its purpose is to make exact packaged reconstruction bytes available for external testing while preserving those boundaries.

## Stable/support-bearing prerequisites

The current coordinated Python distributions require **Python 3.11 or newer**.

Building from source additionally requires the exact repository toolchain in
`rust-toolchain.toml`; no lower Rust MSRV is currently supported. Installed native
artifacts do not require Cargo. See the [maintainer toolchain contract](maintainer/rust-toolchain.md).

This page is the canonical support/prerequisite owner. Exact release identity is projected separately so changing releases does not require copying commands through conceptual prose.

| Concern | Supported contract | Unknown or excluded |
| --- | --- | --- |
| Python | CPython-compatible Python 3.11+ as declared by coordinated package metadata | alternative implementations are not promised unless release evidence says so |
| Installer | `uv tool install` using the exact hash-bound stable release receipt command | ordinary registry resolution, mutable branches, editable/source installs are not support-bearing |
| Git/repository | a Git working tree for shared checked-in operating context and ownership | non-Git hosts are not part of the current public adoption contract |
| Network | required to obtain release assets and for explicitly configured external adapters | ordinary local resolve/act/reconcile does not imply a network service |
| OS/shell | only what the selected stable release evidence actually exercises | no blanket OS, shell, container, or runner guarantee is inferred |
| Credentials | remain in caller/platform boundaries | AW is not a credential host or sandbox |
| Runtime tools | repository-configured commands run with caller authority | arbitrary host tools are not bundled or silently trusted |

The support-bearing public installation identity is a **stable versioned GitHub Release** and the exact command recorded in that release's `distribution-install-readiness.json`. That receipt currently owns the canonical `uv tool install` command, exact root-wheel release URL, and SHA-256 binding. Therefore the support-bearing public path requires a working `uv` installation capable of executing that receipt command.

Mutable branches and ordinary registry resolution are not support-bearing installation identities unless a future release policy explicitly changes that contract. `uvx`, `pipx run`, editable installs, and source-checkout commands are useful development/debug routes but should not be confused with the support-bearing release identity.

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

Ordinary bootstrap should keep the checked-in footprint small: repo-owned config/startup, ownership/routing surfaces, a compact adoption identity, and selected module state anchors. Generic package docs, templates, schemas, bundled skills, and runtime implementation stay package-owned unless a profile explicitly mirrors them.

Payload-mirroring profiles describe source-maintenance packaging. They are not native CLI flags or permission to copy managed state into another repository.

Exact installed files and required/optional degraded references are generated in the [current installed-surface catalogue](reference/installed-surface-catalogue.md).

## Stable invocation after bootstrap

The native `agentic-workspace` CLI remains the ordinary deterministic product authority after bootstrap unless the host uses another supported thin external-consumer projection. Do not assume installation is a one-shot file-copy operation.

The repo-owned compatibility/config surfaces identify the expected contract and configured invocation posture. Ordinary startup/diagnostics should inspect that identity without silently rewriting dependency locks or moving VCS/source revisions. Explicit install/upgrade/sync operations own dependency or expected-identity changes.

If the target owns a dependency lock, use the supported environment-manager mode that preserves it (for example a frozen `uv` invocation when that is the configured adapter). Machine-local executable paths and credentials should not become durable shared repo state.

## If the CLI is missing

Recover through the exact install receipt for the selected immutable release class: the published preview receipt when deliberately testing a preview, or the support-bearing stable receipt when using a stable release. Then rerun the intended lifecycle command.

Prefer the host repo's normal tool/dependency convention when it can preserve the same compatible installed identity. Use `uvx` or `pipx run` only as explicit temporary/debug fallback routes; repeated ordinary work should have a stable configured invocation.

## Do not

- clone the AW source repository into a temporary folder as the normal bootstrap strategy;
- hand-copy package payload into the host repo;
- substitute a mutable branch for the selected immutable preview or stable release;
- let package-level module CLIs become the normal host-repo front door when the root Workspace CLI is available;
- treat a successful bootstrap process as proof that later agents can resolve the same compatible runtime;
- treat local logs, caches, or scratch files as shared proof or Planning authority.

## Follow-up checks

After initialization/adoption, inspect the resolved config and health through the root CLI:

```bash
agentic-workspace config --target . --format json
agentic-workspace doctor --target . --format json
```

Then follow the target repository's thin agent adapter, normally `AGENTS.md`, and start ordinary work through the compact Workspace route rather than reading the entire `.agentic-workspace/` tree.

Temporary finishing briefs or diagnostics under `.agentic-workspace/local/` are local-only and should not be checked in. Mirrored-payload profiles may have additional explicit managed artifacts; their ownership should remain visible in the installed-surface contract.

A repository configured with `payload.target_release = "source-current"` and `payload.dogfood_latest = true` has a stronger committed-state obligation: every commit must carry the workspace payload declared by `workspace_surfaces.json`, module-managed skills from each package's `bootstrap/` source, and release provenance matching the source package version and tag. The upgrade-source records and `.agentic-workspace/payload-provenance.json` are part of that installed-state projection, not local scratch. `check_source_payload_operational_install.py --strict` treats drift in this source-current profile as fatal; refresh through the owning install or upgrade operation rather than editing a mirror or weakening the check.

## Worked adoption example

1. Install with the exact receipt for the immutable release class you intend to exercise. For ordinary support-bearing use, follow [current support-bearing install](reference/support-bearing-install.md); for external preview testing, use only the receipt from the exact published `preview-v...` prerelease.
2. Initialize the smallest footprint that solves a recurring cost, or select no module when routing alone is enough.
3. Start a small direct task:

   ```bash
   agentic-workspace start --target . --task "Clarify one README sentence" --format json
   ```

   The resolved contract can remain direct: edit the canonical README, run proportionate validation, reconcile the bounded result, and create no Planning/Memory/Verification artifact when no future-relevant residue exists.
4. Start a continuity-sensitive task, such as preparing a multi-slice import feature. Progressive discovery may make Planning relevant; follow the typed Planning operation supplied by the current decision rather than learning a second workflow. Planning owns the continuation, not the source implementation.
5. After acting, reconcile the result: passing proof supports only its bounded claim; unfinished parent intent stays with its owner; durable anti-rediscovery residue may route to Memory; Verification contributes evidence only if configured and relevant. Resolve again when a constructible next action remains.

This example intentionally omits an exhaustive command or footprint list. Exact current commands are in the [CLI catalogue](reference/cli-catalogue.md), and exact installed files are in the [surface catalogue](reference/installed-surface-catalogue.md).
