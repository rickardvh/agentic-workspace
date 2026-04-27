# Source, Payload, and Root Install Boundary

Use `uv run python scripts/check/check_source_payload_operational_install.py --format json --strict` for the compact proof.

Authority flows from package source and bootstrap payloads into packaged `_payload` files, then into the root operational install through package upgrade commands. Root-local planning state, memory current notes, and dogfooding archives are intentional operational differences, not payload drift.

Generated CLI package metadata under `generated_cli_package` is source-checkout maintainer/proof infrastructure, not shipped daily-operation runtime payload. Runtime generated command adapters such as `generated_command_adapters.py` remain shipped only where package CLIs import them directly.

The canonical boundary contract is `.agentic-workspace/docs/extraction-and-discovery-contract.md`; this file exists as the stable maintainer entrypoint referenced by package adapters and reports.
