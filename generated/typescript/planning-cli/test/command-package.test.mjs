import assert from 'node:assert/strict';
import test from 'node:test';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { readFileSync } from 'node:fs';

const source = readFileSync(new URL('../src/commandPackage.ts', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('generated package metadata exposes expected commands', () => {
  const expected = ["adopt", "archive-plan", "close-item", "closeout", "create-review", "delegation-decision", "doctor", "handoff", "init", "install", "intake-artifact", "list-files", "new-plan", "promote-to-plan", "prompt", "reconcile", "record-recovery", "report", "status", "summary", "uninstall", "upgrade", "verify-payload"];
  for (const command of expected) {
    assert.match(source, new RegExp(`\"name\": \\"${command}\\"`));
  }
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

test('generated runnable adapter delegates supported command to runtime process', () => {
  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));
  const mockRuntime = fileURLToPath(new URL('./mock-runtime.mjs', import.meta.url));
  const runtime = `"${process.execPath}" "${mockRuntime}"`;
  const result = spawnSync(process.execPath, [cli, 'adopt', '--format', 'json'], {
    encoding: 'utf8',
    env: { ...process.env, AGENTIC_WORKSPACE_RUNTIME: runtime },
  });
  assert.equal(result.status, 0);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.command, 'adopt');
  assert.deepEqual(payload.args, ['adopt', '--format', 'json']);
});

test('generated runnable adapter preserves spaced argv values during runtime handoff', () => {
  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));
  const mockRuntime = fileURLToPath(new URL('./mock-runtime.mjs', import.meta.url));
  const runtime = `"${process.execPath}" "${mockRuntime}"`;
  const result = spawnSync(process.execPath, [cli, 'adopt', '--task', 'value with spaces'], {
    encoding: 'utf8',
    env: { ...process.env, AGENTIC_WORKSPACE_RUNTIME: runtime },
  });
  assert.equal(result.status, 0);
  const payload = JSON.parse(result.stdout);
  assert.deepEqual(payload.args, ['adopt', '--task', 'value with spaces']);
});

test('generated runnable adapter exposes routing status and recovery guidance', () => {
  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));
  const result = spawnSync(process.execPath, [cli, '--help'], { encoding: 'utf8' });
  assert.equal(result.status, 0);
  assert.match(result.stdout, /Supported generated commands:/);
  assert.match(result.stdout, /Weak-agent routing: allowed-mutation-with-review/);
  assert.match(result.stdout, /Recovery:/);
});

test('generated runnable adapter rejects unsupported commands with recovery guidance', () => {
  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));
  const result = spawnSync(process.execPath, [cli, '__unsupported__'], { encoding: 'utf8' });
  assert.equal(result.status, 2);
  assert.equal(result.stdout, '');
  assert.match(result.stderr, /Unsupported generated command: __unsupported__/);
  assert.match(result.stderr, /Recovery:/);
});

test('generated runnable adapter maps runtime handoff failure with recovery guidance', () => {
  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));
  const result = spawnSync(process.execPath, [cli, 'adopt'], {
    encoding: 'utf8',
    env: { ...process.env, AGENTIC_WORKSPACE_RUNTIME: '' },
  });
  assert.equal(result.status, 1);
  assert.match(result.stderr, /Adapter runtime handoff failed:/);
  assert.match(result.stderr, /Recovery:/);
});
