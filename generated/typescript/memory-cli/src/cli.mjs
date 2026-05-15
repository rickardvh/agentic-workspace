#!/usr/bin/env node
// Generated runnable read-only adapter.
// Source: src/agentic_workspace/contracts/command_package_ir.json
// Program: agentic-memory
// Regenerate with: uv run python scripts/generate/generate_command_packages.py
// DO NOT EDIT DIRECTLY.

import { spawnSync } from 'node:child_process';
import { writeSync } from 'node:fs';

const supportedCommands = new Set(["capture-note", "current", "doctor", "list-files", "list-skills", "promotion-report", "report", "route", "route-report", "route-review", "search", "status", "sync-memory", "verify-payload"]);
const argv = process.argv.slice(2);
const command = argv[0];

if (!command || command === '--help' || command === '-h') {
  console.log(`Usage: agentic-memory <command> [options]`);
  console.log(`Supported generated commands: ${Array.from(supportedCommands).join(', ')}`);
  console.log('Weak-agent routing: allowed-read-only');
  console.log('Recovery: use a supported generated command or route back to the canonical Python CLI.');
  process.exit(0);
}

if (!supportedCommands.has(command)) {
  console.error(`Unsupported generated command: ${command}`);
  console.error('Recovery: run agentic-memory --help and choose one of the supported generated commands.');
  process.exit(2);
}

const runtimeCommand = process.env.AGENTIC_WORKSPACE_RUNTIME ?? "python -c \"import sys; from command_generation.console import main_for_entrypoint; raise SystemExit(main_for_entrypoint('agentic-memory', sys.argv[1:]))\"";

function splitRuntimeCommand(commandLine) {
  const parts = [];
  let current = '';
  let quote = null;
  for (const char of commandLine.trim()) {
    if (quote) {
      if (char === quote) quote = null;
      else current += char;
    } else if (char === '"' || char === "'") {
      quote = char;
    } else if (/\s/.test(char)) {
      if (current) {
        parts.push(current);
        current = '';
      }
    } else {
      current += char;
    }
  }
  if (quote) throw new Error('runtime command has an unterminated quote');
  if (current) parts.push(current);
  if (parts.length === 0) throw new Error('runtime command is empty');
  return parts;
}

let result;
try {
  const [runtimeExecutable, ...runtimeArgs] = splitRuntimeCommand(runtimeCommand);
  result = spawnSync(runtimeExecutable, [...runtimeArgs, ...argv], { encoding: 'utf8', maxBuffer: 16 * 1024 * 1024 });
} catch (error) {
  console.error(`Adapter runtime handoff failed: ${error.message}`);
  console.error('Recovery: verify AGENTIC_WORKSPACE_RUNTIME or run the canonical Python CLI directly.');
  process.exit(1);
}
if (result.error) {
  console.error(`Adapter runtime handoff failed: ${result.error.message}`);
  console.error('Recovery: verify AGENTIC_WORKSPACE_RUNTIME or run the canonical Python CLI directly.');
  process.exit(1);
}
if (result.stdout) writeSync(1, result.stdout);
if (result.stderr) writeSync(2, result.stderr);
process.exit(result.status ?? 1);
