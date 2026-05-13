# Source, Payload, and Root Install Boundary

Use `uv run python scripts/check/check_source_payload_operational_install.py --format json --strict` for the compact proof.

Authority flows from package source and bootstrap payloads into packaged `_payload` files, then into the root operational install through package upgrade commands. Root-local planning state, memory current notes, and dogfooding archives are intentional operational differences, not payload drift.

Generated Python CLI package metadata lives under `generated/python/<package>/generated_cli_package` as a peer generated target projection beside `generated/typescript`. Generated command adapter metadata lives beside it as JSON under `generated/python/<package>/generated_command_adapters.json`. Package source trees keep only small `generated_cli_package` import bridges and hand-owned runtime glue. Built wheels may bundle the generated Python projection under a private package-local implementation module so installed CLIs do not depend on repository layout.

Generated command adapter metadata is not a package-local Python runtime module; checks and conformance load the generated JSON artifacts from the repository generated tree.

The canonical boundary contract is `.agentic-workspace/docs/extraction-and-discovery-contract.md`; this file exists as the stable maintainer entrypoint referenced by package adapters and reports.
