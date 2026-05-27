// Generated command package metadata.
// Source: src/agentic_workspace/contracts/command_package_ir.json
// Program: agentic-workspace
// Regenerate with: uv run python scripts/generate/generate_command_packages.py
// DO NOT EDIT DIRECTLY.

import { readFileSync } from 'node:fs';

export type GeneratedCommandPackage = Record<string, unknown>;

export const generatedCommandPackage = JSON.parse(
  readFileSync(new URL('../resources/command_package.json', import.meta.url), 'utf8'),
) as GeneratedCommandPackage;
