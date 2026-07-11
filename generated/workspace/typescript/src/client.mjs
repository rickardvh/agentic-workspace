// Generated from command_package_ir.json. Do not edit.
import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

const profileUrl = new URL('../external_consumer_profile.json', import.meta.url);
export function externalConsumerProfile() { return JSON.parse(readFileSync(profileUrl, 'utf8')); }
export function requireOperations(operationIds, { allowRuntimeBacked = false } = {}) {
  const entries = new Map(externalConsumerProfile().operations.map((entry) => [entry.id, entry]));
  const failures = operationIds.flatMap((id) => {
    const status = entries.get(id)?.external_consumption?.status ?? 'unknown';
    return status === 'internal' || status === 'unknown' || (status === 'runtime-backed' && !allowRuntimeBacked) ? [`${id}: ${status}`] : [];
  });
  if (failures.length) throw new Error(`incompatible operation requirements: ${failures.join(', ')}`);
}
export function invokeJson(argv, { target, executable = 'agentic-workspace' } = {}) {
  const args = [...argv];
  if (target !== undefined && !args.includes('--target')) args.push('--target', String(target));
  if (!args.includes('--format')) args.push('--format', 'json');
  const result = spawnSync(executable, args, { encoding: 'utf8' });
  const text = result.stdout || result.stderr;
  let payload;
  try { payload = JSON.parse(text); } catch (error) { throw new Error(`AW returned non-JSON output (exit ${result.status})`, { cause: error }); }
  if (result.status !== 0) throw new Error(JSON.stringify({ exit_code: result.status, error: payload }));
  return payload;
}
