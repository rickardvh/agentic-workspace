import assert from 'node:assert/strict';
import test from 'node:test';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { mkdirSync, readFileSync, rmSync } from 'node:fs';

const source = readFileSync(new URL('../src/commandPackage.ts', import.meta.url), 'utf8');
const commandPackage = JSON.parse(readFileSync(new URL('../resources/command_package.json', import.meta.url), 'utf8'));
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('generated package resource exposes expected commands', () => {
  const expected = ["assignment", "autopilot", "checkpoint", "config", "correction-event", "defaults", "doctor", "external-intent", "final-response", "implement", "init", "install", "memory", "modules", "note-delegation-outcome", "ownership", "planning", "preflight", "prompt", "proof", "reconcile", "report", "session-log", "setup", "skills", "start", "status", "summary", "system-intent", "uninstall", "upgrade", "work-thread"];
  assert.deepEqual(commandPackage.commands.map((command) => command.command.name).sort(), expected);
  assert.match(source, /resources\/command_package\.json/);
  assert.doesNotMatch(source, /adapter_id/);
  assert.deepEqual(packageJson.files, ['src', 'resources', 'external_consumer_profile.json', 'external_contract_bundle.json']);
});

test('generated package metadata exposes maturity and weak-agent routing status', () => {
  const metadata = packageJson.agenticWorkspace;
  assert.equal(metadata.generationStatus, 'mutation-capable-adapter');
  assert.equal(metadata.maturity.id, 'mutation-capable-adapter');
  assert.equal(typeof metadata.maturity.summary, 'string');
  assert.ok(metadata.maturity.summary.length > 0);
  assert.ok(Array.isArray(metadata.maturity.promotion_requires));
  assert.ok(metadata.maturity.promotion_requires.length > 0);
  assert.equal(metadata.fixtureOnly, false);
  assert.equal(metadata.maturity.runnable, true);
  assert.equal(metadata.maturity.weak_agent_routing, 'allowed-mutation-with-review');
  assert.ok(packageJson.bin);
});

test('generated runnable adapter executes supported command without Python runtime', () => {
  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));
  const result = spawnSync(process.execPath, [cli, ...["assignment", "admit", "--dry-run", "--run-id", "value", "--format", "json"]], { encoding: 'utf8' });
  assert.equal(result.status, 0);
  const payload = JSON.parse(result.stdout);
  assert.equal(typeof payload, 'object');
  assert.equal(result.stderr, '');
});

test('generated runnable adapter preserves spaced argv values during native execution', () => {
  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));
  const spacedTarget = fileURLToPath(new URL('../tmp target with spaces', import.meta.url));
  mkdirSync(spacedTarget, { recursive: true });
  try {
    const args = ["assignment", "admit", "--dry-run", "--run-id", "__SPACED_TARGET__"].map((token) => token === '__SPACED_TARGET__' ? spacedTarget : token);
    const result = spawnSync(process.execPath, [cli, ...args], { encoding: 'utf8' });
    assert.equal(result.status, 0);
    assert.doesNotMatch(result.stderr, /runtime handoff/i);
  } finally {
    rmSync(spacedTarget, { recursive: true, force: true });
  }
});

test('generated runnable adapter rejects command without required subcommand', () => {
  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));
  const result = spawnSync(process.execPath, [cli, ...["assignment"]], { encoding: 'utf8' });
  assert.equal(result.status, 2);
  assert.equal(result.stdout, '');
  assert.match(result.stderr, /missing subcommand for assignment/);
  assert.doesNotMatch(result.stderr, /runtime handoff/i);
});

test('generated runnable adapter exposes routing status and recovery guidance', () => {
  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));
  const result = spawnSync(process.execPath, [cli, '--help'], { encoding: 'utf8' });
  assert.equal(result.status, 0);
  assert.match(result.stdout, /Supported generated commands:/);
  assert.match(result.stdout, /Weak-agent routing: allowed-mutation-with-review/);
  assert.match(result.stdout, /Node\/TypeScript only/);
  assert.doesNotMatch(result.stdout, /Python runtime handoff/);
  assert.match(result.stdout, /Recovery:/);
});

test('generated runnable adapter renders command help without executing runtime', () => {
  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));
  const result = spawnSync(process.execPath, [cli, ...["assignment", "admit"], '--help'], {
    encoding: 'utf8',
  });
  assert.equal(result.status, 0);
  assert.match(result.stdout, /Usage:/);
  assert.match(result.stdout, /Options:/);
});

test('generated runnable adapter validates choices before command execution', () => {
  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));
  const result = spawnSync(process.execPath, [cli, ...["assignment", "admit", "--run-id", "value"], '--format', '__invalid__'], {
    encoding: 'utf8',
  });
  assert.equal(result.status, 2);
  assert.equal(result.stdout, '');
  assert.match(result.stderr, /TypeScript CLI validation failed:/);
  assert.doesNotMatch(result.stderr, /runtime handoff/i);
});

test('generated runnable adapter validates required options before command execution', () => {
  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));
  const result = spawnSync(process.execPath, [cli, ...["planning", "new-plan"]], {
    encoding: 'utf8',
  });
  assert.equal(result.status, 2);
  assert.equal(result.stdout, '');
  assert.match(result.stderr, /missing required option --id/);
  assert.doesNotMatch(result.stderr, /runtime handoff/i);
});

test('generated runnable adapter rejects unsupported commands with recovery guidance', () => {
  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));
  const result = spawnSync(process.execPath, [cli, '__unsupported__'], { encoding: 'utf8' });
  assert.equal(result.status, 2);
  assert.equal(result.stdout, '');
  assert.match(result.stderr, /TypeScript CLI validation failed: unknown command __unsupported__/);
  assert.match(result.stderr, /Recovery:/);
});
