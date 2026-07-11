// Generated public client template backed by command_package_ir.json.
import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { join, resolve } from 'node:path';
import { createHash } from 'node:crypto';

const profileUrl = new URL('../external_consumer_profile.json', import.meta.url);
const bundleUrl = new URL('../external_contract_bundle.json', import.meta.url);
export class AWClientError extends Error {
  constructor(kind, message, details = {}) { super(message); this.name = 'AWClientError'; this.kind = kind; this.details = details; }
}
export function externalConsumerProfile() { return JSON.parse(readFileSync(profileUrl, 'utf8')); }
export function externalContractBundle() { return JSON.parse(readFileSync(bundleUrl, 'utf8')); }
export function operationCompatibilityFingerprint(contract) {
  const normalized = Object.fromEntries(['schema_version', 'id', 'classification', 'inputs', 'output', 'effects', 'guards'].map((key) => [key, contract[key] ?? null]));
  const bundle = externalContractBundle(); const operation = bundle.operations[String(contract.id)] ?? {};
  const schemas = operation.compatibility_surface?.schemas ?? {};
  const sortValue = (value) => Array.isArray(value) ? value.map(sortValue) : value && typeof value === 'object' ? Object.fromEntries(Object.keys(value).sort().map((key) => [key, sortValue(value[key])])) : value;
  const normalize = (value) => {
    if (Array.isArray(value)) return value.map(normalize);
    if (!value || typeof value !== 'object') return value;
    return Object.fromEntries(Object.entries(value).filter(([key]) => !['description', 'title', '$id', '$comment', 'examples', 'default'].includes(key)).map(([key, item]) => [key, normalize(item)]));
  };
  const canonical = JSON.stringify(sortValue({ contract: normalized, schemas: normalize(schemas) }));
  return `sha256:${createHash('sha256').update(canonical).digest('hex')}`;
}
export function negotiateRequirements(requirements, { allowRuntimeBacked = false } = {}) {
  const bundle = externalContractBundle(); const results = [];
  const surfaceCompatible = (required, available, role = 'contract', keyword = '') => {
    if (Array.isArray(required)) {
      if (!Array.isArray(available)) return false;
      if (keyword === 'required') return role === 'input' ? available.every((item) => required.includes(item)) : required.every((item) => available.includes(item));
      if (['enum', 'type'].includes(keyword)) return role === 'input' ? required.every((item) => available.includes(item)) : available.every((item) => required.includes(item));
      return JSON.stringify(required) === JSON.stringify(available);
    }
    return required && typeof required === 'object' ? available && typeof available === 'object' && Object.entries(required).every(([key, value]) => key in available && surfaceCompatible(value, available[key], role, key)) : required === available;
  };
  const compatibilitySatisfied = compatibilitySurfaceSatisfied;
  for (const [operationId, fingerprint] of Object.entries(requirements)) {
    const operation = bundle.operations[operationId];
    if (!operation) { results.push({ operation: operationId, status: 'missing', reason: 'operation is not packaged' }); continue; }
    const support = operation.external_consumption.status;
    if (support === 'runtime-backed' && !allowRuntimeBacked) results.push({ operation: operationId, status: 'runtime-backed', reason: 'explicit runtime-backed opt-in required' });
    else if (!['supported', 'runtime-backed'].includes(support)) results.push({ operation: operationId, status: 'unsupported', reason: `support status is ${support}` });
    else if (fingerprint && typeof fingerprint === 'object' && !compatibilitySatisfied(fingerprint.compatibility_surface, operation.compatibility_surface)) results.push({ operation: operationId, status: 'incompatible', reason: 'operation compatibility surface is breaking' });
    else if (typeof fingerprint === 'string' && fingerprint !== operation.compatibility_fingerprint) results.push({ operation: operationId, status: 'incompatible', reason: 'operation compatibility fingerprint mismatch' });
    else results.push({ operation: operationId, status: 'compatible', reason: 'requirement satisfied' });
  }
  return { compatible: results.every((item) => item.status === 'compatible'), requirements: results };
}
export function compatibilitySurfaceSatisfied(required, available) {
  const compare = (oldValue, newValue, role = 'contract', keyword = '') => {
    if (Array.isArray(oldValue)) {
      if (!Array.isArray(newValue)) return false;
      if (keyword === 'required') return role === 'input' ? newValue.every((item) => oldValue.includes(item)) : oldValue.every((item) => newValue.includes(item));
      if (['enum', 'type'].includes(keyword)) return role === 'input' ? oldValue.every((item) => newValue.includes(item)) : newValue.every((item) => oldValue.includes(item));
      return JSON.stringify(oldValue) === JSON.stringify(newValue);
    }
    return oldValue && typeof oldValue === 'object' ? newValue && typeof newValue === 'object' && Object.entries(oldValue).every(([key, value]) => key in newValue && compare(value, newValue[key], role, key)) : oldValue === newValue;
  };
  return compare(required.contract, available.contract) && Object.entries(required.schemas ?? {}).every(([role, schemas]) => compare(schemas, available.schemas?.[role], role));
}
export function detectWorkspace(target) {
  const root = resolve(target); const path = join(root, '.agentic-workspace', 'config.toml');
  try { const text = readFileSync(path, 'utf8'); return { status: /enabled\s*=\s*false/.test(text) ? 'disabled' : 'enabled', target: root }; }
  catch (error) { if (error.code === 'ENOENT') return { status: 'absent', target: root }; throw error; }
}
export function resolveInvocation(target, override) {
  if (Array.isArray(override) && override.length) return [...override];
  for (const name of ['config.local.toml', 'config.toml']) {
    try {
      const text = readFileSync(join(resolve(target), '.agentic-workspace', name), 'utf8');
      const match = text.match(/^cli_invoke\s*=\s*["'](.+)["']\s*$/m);
      if (match) return match[1].match(/(?:[^\s"']+|"[^"]*"|'[^']*')+/g).map((part) => part.replace(/^["']|["']$/g, ''));
    } catch (error) { if (error.code !== 'ENOENT') throw error; }
  }
  return ['agentic-workspace'];
}
export function requireOperations(operationIds, { allowRuntimeBacked = false } = {}) {
  const entries = new Map(externalConsumerProfile().operations.map((entry) => [entry.id, entry]));
  const allowed = new Set(allowRuntimeBacked ? ['supported', 'runtime-backed'] : ['supported']);
  const failures = operationIds.flatMap((id) => {
    const status = entries.get(id)?.external_consumption?.status ?? 'unknown';
    return allowed.has(status) ? [] : [{ operation: id, status }];
  });
  if (failures.length) throw new AWClientError('incompatible', 'operation requirements are not satisfied', { requirements: failures });
}
export function invokeJson(argv, { target, invocation } = {}) {
  const state = detectWorkspace(target); if (state.status !== 'enabled') throw new AWClientError(state.status, 'workspace is not available', state);
  const command = resolveInvocation(target, invocation); const result = spawnSync(command[0], [...command.slice(1), ...argv], { encoding: 'utf8' });
  if (result.error) throw new AWClientError('invocation-unavailable', result.error.message, { command });
  const text = result.stdout || result.stderr; let payload;
  try { payload = JSON.parse(text); } catch { throw new AWClientError('malformed', 'AW returned non-JSON output', { exit_code: result.status }); }
  if (result.status !== 0) {
    const failureSchema = JSON.parse(readFileSync(new URL('../resources/_contracts/operation_failure.schema.json', import.meta.url), 'utf8'));
    const errors = validateSchema(failureSchema, payload); if (errors.length) throw new AWClientError('malformed', 'operation failure failed schema validation', { errors });
    throw new AWClientError(payload.status, 'AW operation failed', { exit_code: result.status, error: payload });
  }
  if (!payload || Array.isArray(payload) || typeof payload !== 'object') throw new AWClientError('malformed', 'AW result envelope must be an object');
  return payload;
}
function validateSchema(schema, value, path = '$') {
  const errors = [];
  const types = Array.isArray(schema.type) ? schema.type : schema.type ? [schema.type] : [];
  const actual = value === null ? 'null' : Array.isArray(value) ? 'array' : Number.isInteger(value) ? 'integer' : typeof value;
  if (types.length && !types.includes(actual)) errors.push(`${path} must be ${types.join(' or ')}`);
  if (schema.enum && !schema.enum.some((item) => JSON.stringify(item) === JSON.stringify(value))) errors.push(`${path} is not an allowed value`);
  if (schema.const !== undefined && JSON.stringify(schema.const) !== JSON.stringify(value)) errors.push(`${path} must equal the declared constant`);
  if (typeof value === 'number' && schema.minimum !== undefined && value < schema.minimum) errors.push(`${path} must be at least ${schema.minimum}`);
  if (typeof value === 'string' && schema.minLength !== undefined && [...value].length < schema.minLength) errors.push(`${path} is shorter than ${schema.minLength}`);
  if (typeof value === 'string' && schema.pattern !== undefined && !(new RegExp(schema.pattern).test(value))) errors.push(`${path} does not match ${schema.pattern}`);
  if (actual === 'array') {
    if (schema.minItems !== undefined && value.length < schema.minItems) errors.push(`${path} has fewer than ${schema.minItems} items`);
    if (schema.items) value.forEach((item, index) => errors.push(...validateSchema(schema.items, item, `${path}[${index}]`)));
  }
  if (actual === 'object') {
    for (const name of schema.required ?? []) if (!(name in value)) errors.push(`${path}.${name} is required`);
    for (const [name, child] of Object.entries(value)) {
      if (schema.properties?.[name]) errors.push(...validateSchema(schema.properties[name], child, `${path}.${name}`));
      else if (schema.additionalProperties === false) errors.push(`${path}.${name} is not allowed`);
    }
  }
  return errors;
}
export function invokeOperation(operationId, values, { target, invocation, allowRuntimeBacked = false } = {}) {
  requireOperations([operationId], { allowRuntimeBacked });
  const entry = externalConsumerProfile().operations.find((item) => item.id === operationId);
  if (entry.operation_resources.typescript.package !== '@agentic-workspace/workspace-cli') {
    throw new AWClientError('unsupported', 'operation belongs to a separate generated package', { operation: operationId });
  }
  const contract = JSON.parse(readFileSync(new URL(`../${entry.operation_resources.typescript.path}`, import.meta.url), 'utf8'));
  for (const schemaName of entry.schemas.input) {
    const schema = JSON.parse(readFileSync(new URL(`../resources/_contracts/${schemaName}`, import.meta.url), 'utf8'));
    const errors = validateSchema(schema, values); if (errors.length) throw new AWClientError('malformed', 'operation input failed schema validation', { schema: schemaName, errors });
  }
  const declared = new Map((contract.inputs ?? []).map((item) => [item.name, item]));
  const unknown = Object.keys(values).filter((name) => !declared.has(name));
  const missing = [...declared].filter(([name, item]) => item.required && !(name in values)).map(([name]) => name);
  if (unknown.length || missing.length) throw new AWClientError('malformed', 'operation input does not match contract', { unknown, missing });
  const argv = String(contract.command_surface?.command ?? '').split(/\s+/).filter(Boolean);
  for (const [name, value] of Object.entries(values)) {
    if (name === 'target') continue; const flag = `--${name.replaceAll('_', '-')}`;
    if (typeof value === 'boolean') { if (value) argv.push(flag); }
    else argv.push(flag, Array.isArray(value) ? value.join(',') : String(value));
  }
  if (declared.has('target')) argv.push('--target', resolve(target));
  if (declared.has('format')) argv.push('--format', 'json');
  const payload = invokeJson(argv, { target, invocation });
  for (const schemaName of entry.schemas.output) {
    const schema = JSON.parse(readFileSync(new URL(`../resources/_contracts/${schemaName}`, import.meta.url), 'utf8'));
    const errors = validateSchema(schema, payload); if (errors.length) throw new AWClientError('malformed', 'operation result failed schema validation', { schema: schemaName, errors });
  }
  return payload;
}
