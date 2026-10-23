# Source, bundled resources and installed files

Use this page when changing packaged files or investigating differences between
AW's source and the integration installed in a repository.

## Edit the source for the material

| Material | Source and maintenance path |
| --- | --- |
| Runtime behaviour and contracts | `src/core/src/`, `src/core/contracts/` and component contracts under `src/core/src/modules/` |
| Language bindings | `src/cli/python/` and `src/cli/typescript/`; see [native release topology](native-release-topology.md) |
| Bundled agent procedures | Portable sources declared in `src/core/contracts/workspace_surfaces.json`, derived into `src/core/payload/` |
| Target-repository integration | Configuration's adoption and refresh operations, using the [installed-surface catalogue](../reference/installed-surface-catalogue.md) |
| Project rules and saved work | Their repository-owned sources and supported component operations |

Python and npm distributions carry the native executable pair. Former generated
Python/TypeScript execution trees are not installed runtime alternatives.
Retained source-only fixtures do not change that boundary.

## Check the derivation

From the source-checkout root:

```sh
uv run python src/tooling/generate/generate_agent_interface.py --check
```

Use the report to locate a mismatch in the owning source or generated copy.
For generated schema and catalogue documentation, use
[Maintainer commands](maintainer-commands.md#refresh-generated-material).

Generation parity does not refresh another repository's integration. Use
Configuration's returned adoption or refresh request for that effect. Preserve
project configuration, Planning records, Memory advice and local state; a payload
check does not authorise replacing them with defaults.

Build both binaries after Rust or bundled-resource changes, as described in the
[contributor guide](contributor-playbook.md#prepare-a-checkout).
