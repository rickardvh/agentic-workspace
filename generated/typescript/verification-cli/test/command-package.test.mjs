import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';

const source = readFileSync(new URL('../src/commandPackage.ts', import.meta.url), 'utf8');
const commandPackage = JSON.parse(readFileSync(new URL('../resources/command_package.json', import.meta.url), 'utf8'));
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('generated package resource exposes expected commands', () => {
  const expected = ["report"];
  assert.deepEqual(commandPackage.commands.map((command) => command.command.name).sort(), expected);
  assert.match(source, /resources\/command_package\.json/);
  assert.doesNotMatch(source, /adapter_id/);
  assert.deepEqual(packageJson.files, ['src', 'resources']);
});

test('generated package metadata exposes maturity and weak-agent routing status', () => {
  const metadata = packageJson.agenticWorkspace;
  assert.equal(metadata.generationStatus, 'runtime-backed-read-only-adapter');
  assert.equal(metadata.maturity.id, 'runtime-backed-read-only-adapter');
  assert.equal(typeof metadata.maturity.summary, 'string');
  assert.ok(metadata.maturity.summary.length > 0);
  assert.ok(Array.isArray(metadata.maturity.promotion_requires));
  assert.ok(metadata.maturity.promotion_requires.length > 0);
  assert.equal(metadata.fixtureOnly, true);
  assert.equal(metadata.maturity.runnable, false);
  assert.equal(metadata.maturity.weak_agent_routing, 'forbidden');
  assert.equal(packageJson.bin, undefined);
});
