# Installed Surfaces

An installed repository gets a small checked-in control enclave plus thin routing adapters. The surface exists to preserve only control-relevant operating context; it does not mirror ordinary source, documentation, tests, or repository knowledge for search.

For the exact package-managed file set in every supported footprint/module cell, required versus optional references, ownership classes, and selected-but-unconfigured behavior, use the generated [current installed-surface catalogue](../reference/installed-surface-catalogue.md). The [workspace-surfaces schema](../reference/workspace-surfaces-manifest.md) explains contract shape rather than current values.

## Conceptual ownership

| Class | Owner and role |
| --- | --- |
| Repo-owned | `AGENTS.md` outside managed fences, config, canonical docs/source/tests, and host policy remain repository truth. |
| Package-managed | The base `.agentic-workspace/` routing/contract payload is installed and refreshed by explicit lifecycle operations. |
| Module-owned | Selected modules own only their declared roots and effects. Planning, Memory, and Verification are peer examples. |
| Generated/derived | References and adapters are rebuilt from their named source contract; edit the source, not the projection. |
| Local-only | Ignored overrides, diagnostics, logs, and caches are machine state, not shared authority. |
| Optional/degraded | Absence remains explicit and produces the declared degraded behavior rather than invented policy. |
| Promoted output | A result becomes durable only through an explicit repository or module owner operation. |

The ordinary `necessary-surfaces` profile keeps the checked-in footprint small. `full-mirror` is an explicit larger profile, not a prerequisite for runtime semantics. External clients consume stable package/runtime contracts and do not require a host repository to mirror the full payload.

## Selected but unconfigured

Module selection and repository-owned domain configuration are separate. In particular, selecting Verification does not invent `.agentic-workspace/verification/manifest.toml`; the module reports selected-but-unconfigured and keeps repository proof policy absent until the host supplies it. The generated catalogue exposes this mechanically for every optional reference.

## Ordinary discovery

Start from the repository adapter and compact Workspace decision. Open module roots, raw manifests, generated references, or maintainer machinery only when a selector, skill, operation, or owner routes there.

For live target ownership, run:

```bash
agentic-workspace ownership --target . --format json
```

For the trust boundary around installed code and repo-configured commands, see [Threat model](../security/threat-model.md). For support-bearing installation, see [Installing Agentic Workspace](../agentic-workspace-install.md).
