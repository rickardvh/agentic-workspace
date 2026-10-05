# Release Agentic Workspace

After reviewed changes merge, select **Actions → Release → Run workflow**, choose
**master**, and leave the inputs at their defaults. The run selects the source and
version, builds and checks the packages, publishes the verified files, and
verifies GitHub, PyPI, npm and crates.io. Configured environment approvals remain.

The summary identifies the selected commit, version and each destination's
result. No unconsumed changes means a successful run with nothing to release.

## Declare release intent

Every non-draft PR must choose exactly one release decision: `semver:none`,
`semver:patch`, `semver:minor` or `semver:major`. Choose from the actual change
and its compatibility impact; CI does not infer release intent from file paths.
Independent review can challenge the choice.

## Package compatibility boundary

**A major version means a supported consumer cannot upgrade without a deliberate
incompatible change to its own code or configuration, or without resolving durable
state that AW cannot safely preserve or migrate.** Judge the required consumer
migration, not whether a JSON field, result identity or Rust type changed.

| Class | Promise across minor versions |
| --- | --- |
| User-owned inputs | Supported shared/local configuration, repository-authored instruction or skill contracts and other documented inputs remain usable, or AW deterministically migrates them while preserving user intent. Asking an agent to rewrite intent is not automatic migration. |
| Durable component records | Planning, Memory, Verification and other supported durable records remain readable or safely migratable, preserving their meaning, authority and outstanding obligations. Manual semantic reconstruction or abandonment requires a major. |
| Package-managed integration | Installed skills, generated catalogues, payload and internal owner requests/results may evolve together through normal setup/refresh or deterministic migration. No separately promised stable API may break. Ordinary agents consume current results; they need no adapters for historical internal envelopes. |
| Named public APIs | The entrypoints below retain their documented calling, transport, error and exit behaviour, except evolution explicitly allowed by their declared compatibility contract. Removing or incompatibly changing one requires a major. |
| Independently negotiated operations | Integrations use the operation's declared profile/schema compatibility and fingerprints, not the package version alone. A changed operation fingerprint need not mean a package major; breaking the supported discovery or negotiation mechanism does. |
| Source-only maintainer machinery | Use `semver:none` when the shipped package/runtime is intentionally unaffected. This remains an explicit decision, never a filename heuristic. |

The supported distributions share this boundary:

- **CLI:** npm, Python, paired Cargo executables and standalone archives expose
  `agentic-workspace` commands `setup`, `start`, `invoke`, `worker`, `resources` and
  `activation-index`, with the documented options and errors/exit behaviour in the
  [native CLI reference](reference/native-cli.md) and [CLI catalogue](reference/cli-catalogue.md).
- **Python:** `agentic_workspace` exports `start`, `invoke`, `resources`,
  `select_reference`, `answer_carried`, `invoke_carried` and `DecisionContractError`.
- **TypeScript:** `@agentic-workspace/workspace-cli` root and `./operating` export
  `start`, `invoke`, `resources`, `selectReference`, `answerCarried` and
  `invokeCarried`, with their declared argument types. Private transport files and
  source-only semantic helpers are not additional public exports.
- **Rust/Cargo:** `agentic-workspace-core` and `agentic-workspace-cli` support the
  same-version paired executable/protocol distribution. Direct Rust library
  embedding is not currently a supported stable API. `pub` visibility alone does
  not establish an embedding promise.

These entrypoints transport current component data. Their availability and
documented transport obligations are stable; every nested dynamic request/result
field is not thereby a package ABI. Preserve the #2194/#2197 distinction between
package/client identity, schema identity and operation compatibility. Integrations
must use supported current discovery and exact-reference/carriage mechanisms
and any operation-specific compatibility declaration. An undocumented internal
schema or retained source contract is not a negotiated external API.

Choose **patch** for corrections that preserve these promises and require no new
consumer migration; **minor** for compatible additions or evolution with safe
automatic refresh/migration; **major** for the incompatible supported migration
above; **none** when no shipped change requires a package release.

| Change | Decision under this policy |
| --- | --- |
| Remove `start`, change a documented Python call incompatibly, or break CLI exit guarantees | Major |
| Require rewriting supported user configuration with different meaning | Major |
| Safely migrate a durable Planning record while retaining intent and authority | Minor |
| Replace managed skills/payload through normal refresh | Minor |
| Evolve a runtime-owned result/schema with the current runtime and skills, preserving durable state and separately stable APIs | Minor |
| Correct a bug while preserving the supported contracts | Patch |
| Change repository-only review tooling without changing the shipped package | None |
| #3829 resource creation results: current runtime/skills move together; resource custody remains usable | Minor under this policy, subject to those preservation checks. It actually shipped as **2.0.0** under the earlier decision; that fragment and release identity remain historical facts. |

## Declare the fragment

Use `semver:none` when the PR intentionally requires no package release. It needs
no new release fragment and must not add or modify one. Unchanged fragment renames
and deletion of consumed fragments do not request a release.

For `semver:patch`, `semver:minor` or `semver:major`, add a matching fragment under
`.release/changes/`:

```toml
schema_version = "agentic-workspace/release-change/v1"
bump = "patch"
summary = "Describe the user-visible change."
```

The label records the compatibility decision. Ordinary PR fragments must match
it. The existing [exact-tree integration exception](../src/tooling/release/pr_semver_integration.py)
requires its own immutable evidence and applies only to release-bearing labels.
`Semver admission` and `Merge sufficiency`
remain the branch checks.

Selection uses new fragment revisions since the most recent verified, completed
stable release's source. Retained fragments and unchanged renames or deletions do
not request another release. Consumed fragments may be pruned during normal
maintenance. The highest new bump determines the next version above reserved
public stable and preview identities. Partial publication requires recovery.
The explicit [2.0 version-line correction](#withdraw-200-and-resume-1x) is the
bounded exception; it does not reuse a published version or relabel its fragments.

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
receipts must pass before completion is reported. A partial newer release remains
an interrupted publication to recover; it does not replace the most recent
completed stable release.

See [native release topology](maintainer/native-release-topology.md) for package
layouts and platform requirements, and [release validation](maintainer/release-validation.md)
for the replacement's evidence.

## Withdraw 2.0.0 and resume 1.x

The reviewed `.release/version-line-correction.json` records the authorised
replacement of 2.0.0 by 1.11.0, the exact 2.0 source and the preceding 1.10.2
boundary. Selection verifies the original release and both registry receipts,
consumes fragments through the 2.0 source, and selects the new minor from 1.10.2.
It excludes only the recorded 2.0.0 from the minor/patch version floor. Other
reserved versions and partial publications still block or raise the floor;
2.0.0 remains occupied and cannot be republished. A future major must clear it.

Publish and verify 1.11.0 using the ordinary protected-master workflow first.
Then yank 2.0.0 on PyPI and both Cargo crates, deprecate only npm version 2.0.0,
and point npm `latest` and GitHub's latest release to 1.11.0. Add a withdrawal
notice to the 2.0 GitHub release. Keep its immutable tag, assets, receipts and
original fragment: withdrawal changes availability, not the historical bytes.
The lifecycle accepts yanked files only for this exact recorded release and still
checks their identity, digests and receipts. Unknown remote state fails closed.
