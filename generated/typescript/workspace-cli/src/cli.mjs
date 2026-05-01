#!/usr/bin/env node
// Generated runnable read-only adapter.
// Source: src/agentic_workspace/contracts/command_package_ir.json
// Program: agentic-workspace
// Regenerate with: uv run python scripts/generate/generate_command_packages.py
// DO NOT EDIT DIRECTLY.

import { spawnSync } from 'node:child_process';

const supportedCommands = new Set(["config", "defaults", "implement", "modules", "ownership", "preflight", "proof", "skills", "start", "summary"]);
const argv = process.argv.slice(2);
const command = argv[0];

if (!command || command === '--help' || command === '-h') {
  console.log(`Usage: agentic-workspace <command> [options]`);
  console.log(`Supported generated commands: ${Array.from(supportedCommands).join(', ')}`);
  process.exit(0);
}

if (!supportedCommands.has(command)) {
  console.error(`Unsupported generated command: ${command}`);
  process.exit(2);
}

const runtimeCommand = process.env.AGENTIC_WORKSPACE_RUNTIME || "python -m agentic_workspace.cli";
const result = spawnSync(runtimeCommand, argv, { encoding: 'utf8', shell: true });
if (result.error) {
  console.error(`Adapter runtime handoff failed: ${result.error.message}`);
  process.exit(1);
}
if (result.stdout) process.stdout.write(result.stdout);
if (result.stderr) process.stderr.write(result.stderr);
process.exit(result.status ?? 1);
