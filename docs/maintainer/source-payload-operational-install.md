# Source, Payload, and Root Install Boundary

Use `uv run python scripts/check/check_source_payload_operational_install.py --format json --strict` for the compact proof.

Authority flows from package source and bootstrap payloads into packaged `_payload` files, then into the root operational install through package upgrade commands. Root-local planning state, memory current notes, and dogfooding archives are intentional operational differences, not payload drift.

Generated Python command package metadata lives under `generated/<package>/python` and generated TypeScript CLI metadata lives under `generated/<package>/typescript` as sibling target projections. Generated command adapter metadata lives beside each generated target root as JSON. Package source trees keep no generated command-package source bridge; built wheels may bundle the generated Python projection under a private package-local compatibility module so installed CLIs do not depend on repository layout.

Generated command adapter metadata is not a package-local Python runtime module; checks and conformance load the generated JSON artifacts from the repository generated tree.

The canonical boundary contract is `.agentic-workspace/docs/extraction-and-discovery-contract.md`; this file exists as the stable maintainer entrypoint referenced by package adapters and reports.
