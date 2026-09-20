# Getting started

Install the AW executable, add its integration to a Git repository, then give your coding agent a small task. The installation route does not restrict your project's programming language: Rust, Python and TypeScript consumers use the same core.

<a id="before-execution-trust-boundary"></a>

## Before you start

Use an agent that can read repository files and run commands. Agents with repository read access only can inspect saved context, but cannot perform AW operations.

**AW is not a sandbox.** Its configured commands run with your filesystem access and credentials. Review the repository and proposed commands before allowing execution. See [security](security/threat-model.md) for details.

The commands below pin **v1.0.0-rc.9**, a published release candidate for testing, not stable support. This is an explicit example version, not a moving “latest” alias. For stable use, choose the release in the [stable install reference](reference/support-bearing-install.md). Older releases may not contain the behaviour described here.

<a id="prebuilt-packages-and-source-installs"></a>
<a id="runtime-prerequisites-and-support-boundary"></a>
<a id="stablesupport-bearing-prerequisites"></a>

## 1. Install the runtime

Choose **one** route. Python, npm and native archives contain prebuilt executables; Cargo builds from source.

The RC provides x64 and ARM64 packages for Windows, macOS and Linux. macOS requires 15.0 or later on Intel and 14.0 or later on Apple Silicon. Linux requires glibc 2.39 or newer; Alpine/musl and 32-bit systems are not covered. These limits come from the [platform declaration](../.github/release-platforms.json); check the selected release before using other versions or environments.

### npm / TypeScript

With a tested Node major (20, 24 or 25), install the published archive:

```sh
npm install --global "https://github.com/rickardvh/agentic-workspace/releases/download/v1.0.0-rc.9/agentic-workspace-workspace-cli-1.0.0-rc.9.tgz"
```

The package selects its bundled executables for your operating system and architecture. This command uses the GitHub release asset and does not depend on a matching npm registry publication.

### Python

Use Python 3.11–3.14 and `uv`. Download the wheel matching your machine from the [RC assets](https://github.com/rickardvh/agentic-workspace/releases/tag/v1.0.0-rc.9), then pass that wheel to `uv tool install`.

For example, Linux x64 with glibc 2.39 or newer:

```sh
uv tool install "https://github.com/rickardvh/agentic-workspace/releases/download/v1.0.0-rc.9/agentic_workspace-1.0.0rc9-py3-none-manylinux_2_39_x86_64.whl#sha256=1cfb9a3b241319cce188525ff800d7d941537d73607a0410a3c9849a18e93336"
```

For another supported platform, select its wheel rather than changing only the filename in this hash-bound command. The release's `distribution-install-readiness.json` contains the corresponding platform-specific install commands and digests.

### Rust / Cargo

Install both executables from the same source tag, using the Rust toolchain declared by that tag and a working host linker:

```sh
cargo install --locked --git https://github.com/rickardvh/agentic-workspace --tag v1.0.0-rc.9 agentic-workspace-core agentic-workspace-cli
```

This is a source build, not a compiler-free installation. Rust applications can also use the core as a library; see the [language APIs](architecture/shared-rust-core.md). Use a same-version coordinated pair when installing published crates instead.

### Standalone executable

Download the matching native archive from the same release. Extract **both** `agentic-workspace` and `agentic-workspace-core` together and put their directory on `PATH`. On Windows, the filenames end in `.exe`. This route requires neither Python nor Node.

For any route, confirm the agent's environment can find the installation:

```sh
agentic-workspace --help
```

You should see the installed command help. A missing or mismatched core is an installation error, not a reason to switch to a historical Python command host.

<a id="adopt-a-target-repository"></a>
<a id="current-native-adoption-boundary"></a>

## 2. Add AW to your repository

Open the Git repository where you want the agent to work. Installing the executable has not changed that repository.

Ask your agent:

> Add Agentic Workspace to this repository. Run `agentic-workspace start --target . --task "Adopt AW in this repository" --projection full --format json`. Follow Configuration's returned `repository_adoption_request`, show me the proposed files, and ask for any required authorization. Preserve existing instructions and do not enable optional capabilities yet.

The agent submits the exact returned requests through `start --input` and the authorised action through `invoke`. These are machine requests, not JSON you need to assemble. The [lifecycle reference](package/lifecycle.md) explains the transport for clients that need it.

After successful adoption, inspect the diff. Expect a small managed section in `AGENTS.md` and package integration under `.agentic-workspace/`, including the main skill and ownership metadata. Adoption does not invent project policy, choose optional modules or create task records.

Review and commit the shared integration files. Do not commit ignored machine-local state. [Your repository and data](package/installed-surfaces.md) explains the distinction. An existing conflicting file should be preserved and reported, not overwritten to complete setup.

<a id="use-an-adopted-repository"></a>
<a id="a-small-repository-journey"></a>

## 3. Try a small task

Ask the agent:

> Read this repository's AW entry point. Identify the instructions and checks relevant to correcting one documentation error, then make that correction. Explain what you changed and what you checked. Do not create a plan or lesson unless it has a concrete future use.

The entry point leads to `.agentic-workspace/skills/workspace-startup/SKILL.md`. The agent should use relevant project guidance, make the edit and report its checks. A successful task does not require an extra Planning or Memory record.

In a fresh session, ask the agent to read the same entry point. It should be able to discover the integration without the setup conversation. This checks discovery; it does not guarantee every agent will follow the guidance correctly.

Continue with [Everyday use](everyday-use.md), or [configure project rules](customization.md) when you have a specific requirement.

<a id="choose-a-release-identity"></a>

## Other releases and later maintenance

Use the selected release's version, packages and platform limits together. A prerelease remains experimental even when its installation checks pass. Do not use a bare package name that might resolve to an older, different interface during the v1 transition.

[Compatibility and support](evidence-and-support.md) explains the release evidence. Publishing mechanics belong in the [release guide](release-and-versioning.md), not in repository setup.

<a id="refresh-managed-payload"></a>
<a id="remove-aw-from-a-repository"></a>
<a id="public-host-footprint"></a>
<a id="standard-project-skill-discovery"></a>
<a id="stable-invocation-after-adoption"></a>
For updates, removal and optional host skill discovery, use [Your repository and data](package/installed-surfaces.md). <a id="if-the-cli-is-missing"></a>For a missing executable or unsuccessful setup, use [Troubleshooting](troubleshooting.md).
