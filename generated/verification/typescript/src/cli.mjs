#!/usr/bin/env node
// Generated runnable adapter.
// Source: src/agentic_workspace/contracts/command_package_ir.json
// Program: agentic-verification
// Regenerate with: uv run python scripts/generate/generate_command_packages.py
// DO NOT EDIT DIRECTLY.

import { spawnSync } from 'node:child_process';
import { writeSync } from 'node:fs';

const supportedCommands = new Set(["report"]);
const commandDefinitions = [
  {
    "interface": {
      "help": "Report configured repo-native verification protocols and evidence.",
      "name": "report",
      "options": [
        {
          "flags": [
            "--target"
          ],
          "help": "Target repository path. Defaults to the current directory.",
          "name": "target"
        },
        {
          "default": [],
          "flags": [
            "--changed"
          ],
          "help": "Changed paths used to activate matching verification protocols.",
          "name": "changed_paths",
          "nargs": "*"
        },
        {
          "default": "",
          "flags": [
            "--task"
          ],
          "help": "Task text used to activate matching verification protocols.",
          "name": "task_text"
        },
        {
          "choices": [
            "text",
            "json"
          ],
          "default": "text",
          "flags": [
            "--format"
          ],
          "help": "Output format.",
          "name": "format"
        }
      ]
    },
    "name": "report"
  }
];
const commandByName = new Map(commandDefinitions.map((definition) => [definition.name, definition.interface]));
const argv = process.argv.slice(2);
const command = argv[0];

function optionFlags(option) {
  return Array.isArray(option.flags) ? option.flags : [];
}

function interfaceOptions(iface) {
  return Array.isArray(iface.options) ? iface.options : [];
}

function interfaceArguments(iface) {
  return Array.isArray(iface.arguments) ? iface.arguments : [];
}

function interfaceSubcommands(iface) {
  return Array.isArray(iface.subcommands) ? iface.subcommands : [];
}

function isHelpToken(token) {
  return token === '--help' || token === '-h';
}

function printRootHelp() {
  console.log(`Usage: agentic-verification <command> [options]`);
  console.log(`Supported generated commands: ${Array.from(supportedCommands).join(', ')}`);
  console.log('Weak-agent routing: review-required');
  console.log('TypeScript CLI boundary: generated parser/help/validation, then canonical Python runtime handoff.');
  console.log('Recovery: use a supported generated command or route back to the canonical Python CLI.');
}

function printInterfaceHelp(path, iface) {
  const argumentNames = interfaceArguments(iface).map((argument) => argument.nargs === '?' ? `[${argument.name}]` : `<${argument.name}>`);
  const hasSubcommands = interfaceSubcommands(iface).length > 0;
  const subcommandSuffix = hasSubcommands ? ' <subcommand>' : '';
  const argumentSuffix = argumentNames.length ? ` ${argumentNames.join(' ')}` : '';
  console.log(`Usage: ${path.join(' ')}${subcommandSuffix} [options]${argumentSuffix}`);
  if (iface.help) console.log(String(iface.help));
  const options = interfaceOptions(iface);
  if (options.length) {
    console.log('Options:');
    for (const option of options) {
      const choices = Array.isArray(option.choices) ? ` choices=${option.choices.join('|')}` : '';
      const required = option.required === true ? ' required' : '';
      console.log(`  ${optionFlags(option).join(', ')}${required}${choices}  ${option.help ?? ''}`);
    }
  }
  const subcommands = interfaceSubcommands(iface);
  if (subcommands.length) {
    console.log('Subcommands:');
    for (const subcommand of subcommands) {
      console.log(`  ${subcommand.name}  ${subcommand.help ?? ''}`);
    }
  }
}

function failValidation(message) {
  console.error(`TypeScript CLI validation failed: ${message}`);
  console.error('Recovery: run agentic-verification --help and choose a supported generated command or valid option.');
  process.exit(2);
}

function validateChoice(spec, value, label) {
  if (Array.isArray(spec.choices) && !spec.choices.includes(value)) {
    failValidation(`${label} must be one of: ${spec.choices.join(', ')}`);
  }
  if (spec.type === 'integer' && !/^-?\d+$/.test(value)) {
    failValidation(`${label} must be an integer`);
  }
}

function optionByFlag(iface, flag) {
  return interfaceOptions(iface).find((option) => optionFlags(option).includes(flag));
}

function consumeOption(iface, option, tokens, index, seenOptions) {
  const optionName = option.name ?? optionFlags(option)[0];
  if (optionName) seenOptions.add(optionName);
  if (option.action === 'store_true') return index + 1;
  if (option.nargs === '*') {
    let cursor = index + 1;
    while (cursor < tokens.length && !String(tokens[cursor]).startsWith('-')) {
      validateChoice(option, String(tokens[cursor]), optionFlags(option)[0]);
      cursor += 1;
    }
    return cursor;
  }
  if (index + 1 >= tokens.length || isHelpToken(tokens[index + 1])) {
    failValidation(`${optionFlags(option)[0]} requires a value`);
  }
  const value = String(tokens[index + 1]);
  validateChoice(option, value, optionFlags(option)[0]);
  return index + 2;
}

function validateInterface(iface, tokens, path) {
  const seenOptions = new Set();
  const positional = [];
  let index = 0;
  while (index < tokens.length) {
    const token = String(tokens[index]);
    if (isHelpToken(token)) {
      printInterfaceHelp(path, iface);
      process.exit(0);
    }
    if (token.startsWith('-')) {
      const option = optionByFlag(iface, token);
      if (!option) failValidation(`unknown option ${token} for ${path.join(' ')}`);
      index = consumeOption(iface, option, tokens, index, seenOptions);
      continue;
    }
    const subcommand = interfaceSubcommands(iface).find((candidate) => candidate.name === token);
    if (subcommand) {
      validateInterface(subcommand, tokens.slice(index + 1), [...path, token]);
      return;
    }
    positional.push(token);
    index += 1;
  }
  for (const option of interfaceOptions(iface)) {
    const optionName = option.name ?? optionFlags(option)[0];
    if (option.required === true && optionName && !seenOptions.has(optionName)) {
      failValidation(`missing required option ${optionFlags(option)[0]} for ${path.join(' ')}`);
    }
  }
  const positionalSpecs = interfaceArguments(iface);
  const requiredPositionals = positionalSpecs.filter((argument) => argument.nargs !== '?' && argument.default === undefined);
  if (positional.length < requiredPositionals.length) {
    failValidation(`missing required argument for ${path.join(' ')}`);
  }
  if (positional.length > positionalSpecs.length) {
    failValidation(`unexpected argument ${positional[positionalSpecs.length]} for ${path.join(' ')}`);
  }
  positional.forEach((value, position) => validateChoice(positionalSpecs[position] ?? {}, value, positionalSpecs[position]?.name ?? 'argument'));
  if (interfaceSubcommands(iface).length && iface.subcommands_required !== false && positional.length === 0) {
    failValidation(`missing subcommand for ${path.join(' ')}`);
  }
}

if (!command || command === '--help' || command === '-h') {
  printRootHelp();
  process.exit(0);
}

if (!supportedCommands.has(command)) {
  console.error(`Unsupported generated command: ${command}`);
  console.error('Recovery: run agentic-verification --help and choose one of the supported generated commands.');
  process.exit(2);
}

validateInterface(commandByName.get(command), argv.slice(1), [command]);

const runtimeCommand = process.env.AGENTIC_WORKSPACE_RUNTIME ?? "python -c \"import sys; from repo_verification_bootstrap.cli import main; raise SystemExit(main(sys.argv[1:]))\"";

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
