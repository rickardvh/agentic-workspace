import assert from 'node:assert/strict';
import test from 'node:test';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { readFileSync } from 'node:fs';

const source = readFileSync(new URL('../src/commandPackage.ts', import.meta.url), 'utf8');

test('generated package metadata exposes expected commands', () => {
  const expected = ["defaults"];
  for (const command of expected) {
    assert.match(source, new RegExp(`\"name\": \\"${command}\\"`));
  }
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
