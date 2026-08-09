// Generated public client template backed by command_package_ir.json.
import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { join, resolve } from 'node:path';
import { createHash } from 'node:crypto';

const profileUrl = new URL('../external_consumer_profile.json', import.meta.url);
const conformanceReceiptsUrl = new URL('../external_operation_conformance_receipts.json', import.meta.url);
const bundleUrl = new URL('../external_contract_bundle.json', import.meta.url);
const packageUrl = new URL('../package.json', import.meta.url);
const readinessTransports = ['cli-json', 'python', 'typescript', 'vendor-neutral'];
const readinessExecutors = { 'cli-json': 'direct-cli-json', python: 'generated-python-client', typescript: 'generated-typescript-client', 'vendor-neutral': 'packed-typescript-client' };
const readinessCases = ['absent', 'disabled', 'incompatible', 'malformed', 'retryable', 'additive-field', 'mutation-applied', 'mutation-noop', 'mutation-rejected', 'mutation-failed'];
export class AWClientError extends Error {
  constructor(kind, message, details = {}) { super(message); this.name = 'AWClientError'; this.kind = kind; this.details = details; }
}
export function externalConsumerProfile() { return JSON.parse(readFileSync(profileUrl, 'utf8')); }
function receiptPublicationPayload(payload) {
  const copy = { ...payload };
  delete copy.mirror_publication;
  return copy;
}
function sortedJson(value) {
  if (Array.isArray(value)) return `[${value.map(sortedJson).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${sortedJson(value[key])}`).join(',')}}`;
  return JSON.stringify(value);
}
function validReceiptPublication(payload) {
  const publication = payload?.mirror_publication ?? {};
  if (publication.kind !== 'agentic-workspace/external-operation-conformance-mirror-publication/v1' || publication.status !== 'published') return false;
  const digest = createHash('sha256').update(sortedJson(receiptPublicationPayload(payload))).digest('hex');
  return publication.payload_digest === `sha256:${digest}`;
}
function receiptExpired(receipt) {
  if (!receipt?.expires_at) return false;
  const expiresAt = Date.parse(receipt.expires_at);
  return Number.isFinite(expiresAt) && Date.now() >= expiresAt;
}
export function externalOperationConformanceReceipts() {
  try {
    const payload = JSON.parse(readFileSync(conformanceReceiptsUrl, 'utf8'));
    return payload?.kind === 'agentic-workspace/external-operation-conformance-receipt-store/v1' && validReceiptPublication(payload) ? payload : { kind: 'agentic-workspace/external-operation-conformance-receipt-store/v1', receipts: [], status: 'invalid-publication' };
  } catch {
    return { kind: 'agentic-workspace/external-operation-conformance-receipt-store/v1', receipts: [] };
  }
}
function conformanceReceipt(entry, profile, receiptStore) {
  const candidates = (receiptStore.receipts ?? []).filter((receipt) => {
    const custody = receipt?.custody ?? {};
    return receipt?.kind === 'agentic-workspace/external-operation-conformance-receipt/v1'
      && custody.producer === 'agentic-workspace.operation-conformance-runner'
      && receipt.operation_id === entry.id
      && receipt.operation_fingerprint === entry.operation_compatibility?.fingerprint
      && receipt.profile_fingerprint === profile.compatibility?.fingerprint
      && !['revoked', 'superseded', 'stale'].includes(receipt.status)
      && !receipt.revoked_at
      && !receipt.superseded_by
      && !receiptExpired(receipt);
  });
  return candidates.sort((left, right) => String(left.executed_at ?? left.receipt_ref ?? '').localeCompare(String(right.executed_at ?? right.receipt_ref ?? ''))).at(-1);
}
function conformanceReadiness(entry, profile, receiptStore) {
  const evidence = conformanceReceipt(entry, profile, receiptStore);
  if (!evidence || typeof evidence !== 'object') return {missing: ['executed-conformance-receipt'], result: {}};
  const missing = [];
  if (evidence.status !== 'passed') missing.push('executed-conformance-passed');
  if (evidence.operation_fingerprint !== entry.operation_compatibility?.fingerprint) missing.push('current-operation-fingerprint');
  if (evidence.profile_fingerprint !== profile.compatibility?.fingerprint) missing.push('current-profile-fingerprint');
  const authority = profile.readiness_authority ?? {}, resultIdentity = evidence.result_identity ?? {};
  if (resultIdentity.runner_revision !== authority.runner_revision) missing.push('current-runner-revision');
  if (resultIdentity.client_semantics_revision !== authority.client_semantics_revision) missing.push('current-client-semantics-revision');
  const transports = evidence.transports ?? {}, executors = evidence.executors ?? {}, cases = evidence.cases ?? {};
  for (const transport of readinessTransports) {
    if (transports[transport]?.status !== 'passed') missing.push(`transport-${transport}`);
    if (executors[transport]?.status !== 'passed' || executors[transport]?.executor_id !== readinessExecutors[transport]) missing.push(`executor-${transport}`);
  }
  for (const item of readinessCases) if (cases[item]?.status !== 'passed') missing.push(`case-${item}`);
  const matrix = evidence.case_transport_matrix ?? {}, footprints = evidence.footprints ?? {};
  for (const item of readinessCases) for (const transport of readinessTransports) if (matrix[item]?.[transport]?.status !== 'passed') missing.push(`case-${item}-transport-${transport}`);
  for (const footprint of ['necessary-surfaces', 'full-mirror']) if (footprints[footprint]?.status !== 'passed') missing.push(`footprint-${footprint}`);
  if (footprints['semantic-parity']?.status !== 'passed') missing.push('footprint-semantic-parity');
  if (entry.external_consumption?.runtime_exceptions?.length && !evidence.runtime_exception_revision) missing.push('runtime-exception-current-revision');
  return {missing, result: {status: evidence.status ?? '', operation_fingerprint: evidence.operation_fingerprint ?? '', profile_fingerprint: evidence.profile_fingerprint ?? '', runner_revision: resultIdentity.runner_revision ?? '', client_semantics_revision: resultIdentity.client_semantics_revision ?? '', runtime_exception_revision: evidence.runtime_exception_revision ?? '', transports, executors, cases, case_transport_matrix: matrix, footprints, receipt_ref: evidence.receipt_ref ?? '', producer: evidence.custody?.producer ?? ''}};
}
export function externalReadinessReport(operationIds, { allowRuntimeBacked = false } = {}) {
  const profile = externalConsumerProfile();
  const receiptStore = externalOperationConformanceReceipts();
  const entries = new Map(profile.operations.map((entry) => [entry.id, entry])); const supported = [], supportedEvidence = [], excluded = [];
  for (const id of operationIds) { const entry = entries.get(id) ?? {}, c = entry.external_consumption ?? {}, r = entry.operation_resources ?? {}, t = entry.targets ?? {}, s = entry.schemas ?? {}, refs = entry.conformance ?? [], missing = [];
    for (const lang of ['python', 'typescript']) { if (!r[lang]?.exists) missing.push(`released-${lang}-resource`); if (!['adapter', 'mutation-capable-adapter'].includes(t[lang]?.status)) missing.push(`released-${lang}-adapter`); }
    if (!s.input?.length || !s.output?.length) missing.push('input-output-schema-coverage'); if (!refs.length) missing.push('conformance-reference'); const status = c.status ?? 'unavailable'; if (status === 'runtime-backed' && !c.runtime_exceptions?.length) missing.push('runtime-exception-disposition');
    const conformance = conformanceReadiness(entry, profile, receiptStore); missing.push(...conformance.missing);
    const allowedStatuses = new Set(allowRuntimeBacked ? ['supported', 'runtime-backed'] : ['supported']);
    if (allowedStatuses.has(status) && !missing.length) { supported.push(id); supportedEvidence.push({id, status: 'ready', support_status: status, conformance_refs: refs, conformance_result: conformance.result, receipt_ref: conformance.result.receipt_ref ?? ''}); } else excluded.push({id, status, missing_evidence: missing, conformance_refs: refs, conformance_result: conformance.result}); }
  const notAdvertised = [...entries.values()].filter((entry) => (entry.external_consumption?.status ?? 'unavailable') !== 'supported').sort((left, right) => String(left.id).localeCompare(String(right.id))).map((entry) => ({id: String(entry.id), status: entry.external_consumption?.status ?? 'unavailable', reason: entry.external_consumption?.status === 'runtime-backed' ? 'runtime-backed opt-in required' : 'operation is not declared externally supported'}));
  return {kind: 'agentic-workspace/external-readiness-report/v1', status: !excluded.length ? 'ready' : supported.length ? 'subset-only' : 'not-ready', supported_operations: supported, supported_operation_evidence: supportedEvidence, excluded_operations: excluded, operation_accounting: {profile_operation_count: entries.size, requested_operation_count: operationIds.length, ready_requested_count: supported.length, excluded_requested_count: excluded.length, not_advertised_count: notAdvertised.length, not_advertised_sample: notAdvertised.slice(0, 32), sample_limit: 32}};
}
export function externalContractBundle() { return JSON.parse(readFileSync(bundleUrl, 'utf8')); }
export function externalConformanceProfile(operationIds = null) {
  const profile = { ...(externalContractBundle().external_conformance ?? {}) };
  const requested = operationIds === null ? null : new Set(operationIds.map(String));
  profile.operations = (profile.operations ?? []).filter((item) => requested === null || requested.has(String(item.operation_id)));
  return profile;
}
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
  const oldInputs = new Map((required.contract?.inputs ?? []).map((item) => [String(item.name), item]));
  const newInputs = new Map((available.contract?.inputs ?? []).map((item) => [String(item.name), item]));
  if ([...oldInputs].some(([name]) => !newInputs.has(name))) return false;
  for (const [name, oldInput] of oldInputs) {
    const newInput = newInputs.get(name);
    if (!oldInput.required && newInput.required) return false;
    const oldRest = Object.fromEntries(Object.entries(oldInput).filter(([key]) => key !== 'required'));
    const newRest = Object.fromEntries(Object.entries(newInput).filter(([key]) => key !== 'required'));
    if (!compare(oldRest, newRest, 'input')) return false;
  }
  if ([...newInputs].some(([name, item]) => !oldInputs.has(name) && item.required)) return false;
  const oldContract = Object.fromEntries(Object.entries(required.contract ?? {}).filter(([key]) => key !== 'inputs'));
  const newContract = Object.fromEntries(Object.entries(available.contract ?? {}).filter(([key]) => key !== 'inputs'));
  return compare(oldContract, newContract) && Object.entries(required.schemas ?? {}).every(([role, schemas]) => compare(schemas, available.schemas?.[role], role));
}
export function detectWorkspace(target) {
  const root = resolve(target);
  for (const name of ['config.local.toml', 'config.toml']) {
    const path = join(root, '.agentic-workspace', name);
    try {
      const text = readFileSync(path, 'utf8');
      if (/enabled\s*=\s*false/.test(text)) return { status: 'disabled', target: root, config: name };
      const compatibility = text.match(/^exact_version\s*=\s*["']([^"']+)["']\s*$/m);
      const clientVersion = JSON.parse(readFileSync(packageUrl, 'utf8')).version;
      if (compatibility && compatibility[1] !== clientVersion) return { status: 'incompatible', target: root, config: name, reason: 'exact-client-version-mismatch', expected_version: compatibility[1], client_version: clientVersion };
      return { status: 'enabled', target: root, config: name };
    }
    catch (error) { if (error.code !== 'ENOENT') throw error; }
  }
  return { status: 'absent', target: root };
}
export function resolveInvocation(target, override) {
  if (Array.isArray(override) && override.length) return [...override];
  const unquoteTomlString = (value) => value.replace(/^["']|["']$/g, '').replace(/\\\\/g, '\\').replace(/\\"/g, '"');
  for (const name of ['config.local.toml', 'config.toml']) {
    try {
      const text = readFileSync(join(resolve(target), '.agentic-workspace', name), 'utf8');
      const match = text.match(/^cli_invoke\s*=\s*["'](.+)["']\s*$/m);
      if (match) return match[1].match(/(?:[^\s"']+|"[^"]*"|'[^']*')+/g).map((part) => unquoteTomlString(part));
    } catch (error) { if (error.code !== 'ENOENT') throw error; }
  }
  return ['agentic-workspace'];
}
export function requireOperations(operationIds, { allowRuntimeBacked = false } = {}) {
  const readiness = externalReadinessReport(operationIds, { allowRuntimeBacked });
  const failures = readiness.excluded_operations;
  if (failures.length) throw new AWClientError('incompatible', 'operation requirements lack current external-readiness evidence', { requirements: failures, readiness });
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
  const subcommand = String(contract.command_surface?.subcommand ?? '').trim();
  if (subcommand && argv.at(-1) !== subcommand) argv.push(subcommand);
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
