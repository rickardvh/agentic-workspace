# Compatibility and support

Use the documentation and packages for the same AW release. A newer source checkout can describe behavior that an older installation does not contain.

<a id="published-release-evidence"></a>
<a id="stable-releases"></a>
<a id="release-candidates-and-previews"></a>
## Choose a release

A **stable release** carries the project's supported compatibility and installation claims for its stated platforms. The [stable install reference](reference/support-bearing-install.md) identifies that release.

A **release candidate** or **preview** is available for testing, not stable support. Passing its tests does not turn it into a stable release. [Getting started](agentic-workspace-install.md) provides a pinned prerelease example and the runtime/platform requirements.

Rust, Python and TypeScript are ways to consume the same core, not three independent product implementations. Your project's language need not match the interface used to install or call AW.

<a id="deterministic-source-evidence"></a>
<a id="live-agent-evidence"></a>
<a id="how-to-interpret-a-claim"></a>
## What a successful check tells you

| Evidence | What it establishes | What it does not establish |
| --- | --- | --- |
| Source tests | The tested behavior on that source revision | That older published packages contain it |
| Installed-package checks | The named artifacts worked on the tested environments | Support for every OS, runtime or agent host |
| An observed agent run | That agent's behavior under the recorded conditions | That all models follow guidance or work more cheaply |
| Verification of your project | The claim covered by those checks and inputs | Completion of unrelated requirements or independent approval |

A saved result remains evidence about its actual subject. Changed dependencies can make it unsuitable for a new claim.

## Verify a download or investigate support

Published releases provide artifact checksums and installation evidence. `distribution-install-readiness.json` identifies platform-specific packages and commands. Registry publication evidence, when present, identifies the corresponding published versions and digests; a GitHub asset alone does not prove registry availability.

These files are useful for auditing a release. You do not need to learn the publisher's admission procedure to use the package. Maintainers use [release and versioning](release-and-versioning.md) for that procedure.

<a id="current-support-boundary"></a>
## Boundaries that remain

AW does not sandbox your commands, store provider credentials for you, or guarantee model obedience. A repository-only reader can inspect saved context but cannot establish live machine state or fresh test results.

See [security](security/threat-model.md) for execution and data handling, [Troubleshooting](troubleshooting.md) for failures, and the [maturity vocabulary](maturity-model.md) for release terminology.
