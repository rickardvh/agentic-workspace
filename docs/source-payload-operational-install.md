# Source, Payload, and Root Install Boundary

Use `uv run python scripts/check/check_source_payload_operational_install.py --format json --strict` for the compact proof.

Authority flows from package source and bootstrap payloads into packaged `_payload` files, then into the root operational install through package upgrade commands. Root-local planning state, memory current notes, and dogfooding archives are intentional operational differences, not payload drift.

The canonical boundary contract is `.agentic-workspace/docs/extraction-and-discovery-contract.md`; this file exists as the stable maintainer entrypoint referenced by package adapters and reports.
