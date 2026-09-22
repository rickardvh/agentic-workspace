# Source, Payload, and Root Install Boundary

Use this page when changing packaged files or investigating a difference between
package source and the files installed in this repository. It identifies which
copy to edit and which differences are intentional.

Authority flows from package source and bootstrap payloads into packaged `_payload` files, then into the root operational install through package upgrade commands. Root-local planning state, memory current notes, and dogfooding archives are intentional operational differences, not payload drift.

Generated Python command package metadata lives under `generated/<package>/python` and generated TypeScript CLI metadata lives under `generated/<package>/typescript` as sibling target projections. Generated command adapter metadata lives beside each generated target root as JSON. Package source trees keep no generated command-package source bridge; built wheels may bundle the generated Python projection under a private package-local compatibility module so installed CLIs do not depend on repository layout.

Generated command adapter metadata is not a package-local Python runtime module; checks and conformance load the generated JSON artefacts from the repository generated tree.

The canonical boundary contract is `.agentic-workspace/docs/extraction-and-discovery-contract.md`; this file exists as the stable maintainer entrypoint referenced by package adapters and reports.

## Check the boundary

Run the source/payload/install check from the repository root:

```bash
uv run python src/tooling/check/check_source_payload_operational_install.py --format json --strict
```

Use its report to locate a mismatch in the owning source or generated copy.
Preserve intentional local state differences; the check does not authorise
replacing Planning records or Memory notes with packaged defaults.
