import assert from 'node:assert/strict';
import test from 'node:test';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { readFileSync } from 'node:fs';

const source = readFileSync(new URL('../src/commandPackage.ts', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('generated package metadata exposes expected commands', () => {
  const expected = ["config", "defaults", "implement", "modules", "ownership", "preflight", "proof", "skills", "start", "summary"];
  for (const command of expected) {
    assert.match(source, new RegExp(`\"name\": \\"${command}\\"`));
  }
});

test('generated package metadata exposes maturity and weak-agent routing status', () => {
  const metadata = packageJson.agenticWorkspace;
  assert.equal(metadata.generationStatus, 'runnable-read-only-adapter');
  assert.equal(metadata.maturity.id, 'runnable-read-only-adapter');
  assert.equal(typeof metadata.maturity.summary, 'string');
  assert.ok(metadata.maturity.summary.length > 0);
  assert.ok(Array.isArray(metadata.maturity.promotion_requires));
  assert.ok(metadata.maturity.promotion_requires.length > 0);
  assert.equal(metadata.fixtureOnly, false);
  assert.equal(metadata.maturity.runnable, true);
  assert.equal(metadata.maturity.weak_agent_routing, 'review-required');
  assert.ok(packageJson.bin);
});

test('generated runnable adapter delegates supported command to runtime process', () => {
  const cli = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));
  const mockRuntime = fileURLToPath(new URL('./mock-runtime.mjs', import.meta.url));
  const runtime = `"${process.execPath}" "${mockRuntime}"`;
  const result = spawnSync(process.execPath, [cli, 'defaults', '--format', 'json'], {
    encoding: 'utf8',
    env: { ...process.env, AGENTIC_WORKSPACE_RUNTIME: runtime },
  });
  assert.equal(result.status, 0);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.command, 'defaults');
  assert.deepEqual(payload.args, ['defaults', '--format', 'json']);
});
