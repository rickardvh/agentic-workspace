"""Generated command module registry.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-verification
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

from __future__ import annotations

# DO NOT EDIT DIRECTLY.
# Command module changes belong in src/agentic_workspace/contracts/command_package_ir.json.
# Regenerate with: uv run python scripts/generate/generate_command_packages.py

from . import verification_report_report as _command_verification_report_report


GENERATED_COMMAND_HANDLERS = {
    'verification.report.report': _command_verification_report_report.run,
}
