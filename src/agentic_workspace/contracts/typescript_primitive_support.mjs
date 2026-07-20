// AW-owned TypeScript host primitive support.
// Command-generation owns the generated runtime shell; this module owns
// Agentic Workspace primitive behavior that is copied into generated packages.

import {
  copyFileSync,
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  rmSync,
  statSync,
  writeFileSync,
  writeSync,
} from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, isAbsolute, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const resourcesRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../resources');

class RuntimeError extends Error {}

function readText(path) {
  return readFileSync(path, 'utf8');
}

function readJson(path) {
  return JSON.parse(readText(path));
}

function loadJsonResource(path) {
  return readJson(resolveInside(resourcesRoot, path));
}

function clone(value) {
  return JSON.parse(JSON.stringify(value ?? {}));
}

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function resolveInside(root, subpath) {
  const rootPath = resolve(root);
  const candidate = resolve(rootPath, String(subpath ?? ''));
  const rel = relative(rootPath, candidate);
  if (rel === '' || (!rel.startsWith('..') && !isAbsolute(rel))) return candidate;
  throw new RuntimeError(`path escapes primitive root: ${candidate}`);
}

function resourceRoot(name) {
  if (!name) return resourcesRoot;
  if (name.endsWith('.contracts') || name === '_contracts') return resolveInside(resourcesRoot, '_contracts');
  if (name.endsWith('.payload') || name === '_payload') return resolveInside(resourcesRoot, '_payload');
  if (name.endsWith('.skills') || name.endsWith('.package-skills') || name === '_skills') return resolveInside(resourcesRoot, '_skills');
  if (name.endsWith('.package-payload')) return resolveInside(resourcesRoot, '_payload');
  return resolveInside(resourcesRoot, name);
}

function valueRoot(args, values) {
  if (Object.prototype.hasOwnProperty.call(args, 'base_value')) {
    const key = String(args.base_value);
    if (!Object.prototype.hasOwnProperty.call(values, key)) throw new RuntimeError(`unknown primitive base value: ${key}`);
    return resolve(String(values[key]));
  }
  return resourceRoot(String(args.root ?? ''));
}

function listFiles(root, prefix = '') {
  const dir = resolveInside(root, prefix);
  if (!existsSync(dir)) return [];
  const out = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const child = join(prefix, entry.name);
    if (entry.isDirectory()) out.push(...listFiles(root, child));
    else if (entry.isFile()) out.push(child.replace(/\\/g, '/'));
  }
  return out.sort();
}

function globFiles(root, pattern) {
  if (!pattern || isAbsolute(pattern) || pattern.split(/[\\/]+/).includes('..')) {
    throw new RuntimeError(`unsupported filesystem.glob pattern: ${pattern}`);
  }
  const normalized = String(pattern).replace(/\\/g, '/');
  const files = listFiles(root);
  if (normalized === '**/*') return files;
  if (normalized.endsWith('/**/*')) {
    const prefix = normalized.slice(0, -4);
    return files.filter((file) => file.startsWith(prefix));
  }
  if (normalized.startsWith('**/*.')) {
    const suffix = normalized.slice(4);
    return files.filter((file) => file.endsWith(suffix));
  }
  if (!normalized.includes('*')) return files.filter((file) => file === normalized);
  const escaped = normalized.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*\*/g, '.*').replace(/\*/g, '[^/]*');
  const regex = new RegExp(`^${escaped}$`);
  return files.filter((file) => regex.test(file));
}

function parseScalar(raw) {
  const text = raw.trim();
  if (text === 'true') return true;
  if (text === 'false') return false;
  if (/^-?\d+$/.test(text)) return Number(text);
  if (text.startsWith('[') && text.endsWith(']')) {
    return text.slice(1, -1).split(',').map((item) => parseScalar(item.trim())).filter((item) => item !== '');
  }
  const quoted = text.match(/^"(.*)"$/);
  return quoted ? quoted[1] : text;
}

function parseTomlTables(text, tableName) {
  const root = {};
  let current = root;
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;
    const header = line.match(/^\[([^\]]+)\]$/);
    if (header) {
      const parts = header[1].split('.');
      current = root;
      for (const part of parts) {
        if (!isObject(current[part])) current[part] = {};
        current = current[part];
      }
      continue;
    }
    const equals = line.indexOf('=');
    if (equals > 0) current[line.slice(0, equals).trim()] = parseScalar(line.slice(equals + 1));
  }
  const table = root[tableName];
  return isObject(table) ? table : {};
}

function tomlTableCounts(values, args) {
  const root = valueRoot(args, values);
  const relativePath = String(args.path ?? '');
  const path = resolveInside(root, relativePath);
  const tableName = String(args.table ?? '');
  const relevanceField = String(args.relevance_field ?? '');
  const requiredValue = String(args.required_value ?? 'required').trim().toLowerCase();
  const optionalValue = String(args.optional_value ?? 'optional').trim().toLowerCase();
  const routingOnlyField = String(args.routing_only_field ?? 'routing_only');
  const counts = {
    status: 'missing',
    note_count: 0,
    required_count: 0,
    optional_count: 0,
    routing_only_count: 0,
    path: relativePath,
  };
  if (!existsSync(path)) return { table_counts: counts, table_present: false, table_status: counts.status };
  let records;
  try {
    records = Object.values(parseTomlTables(readText(path), tableName));
  } catch {
    counts.status = 'invalid';
    return { table_counts: counts, table_present: false, table_status: counts.status };
  }
  counts.status = 'present';
  counts.note_count = records.length;
  for (const record of records) {
    if (!isObject(record)) continue;
    const relevance = String(record[relevanceField] ?? '').trim().toLowerCase();
    if (relevance === requiredValue) counts.required_count += 1;
    else if (relevance === optionalValue) counts.optional_count += 1;
    if (Boolean(record[routingOnlyField])) counts.routing_only_count += 1;
  }
  return { table_counts: counts, table_present: true, table_status: counts.status };
}

function readVersion(path) {
  if (!existsSync(path)) return null;
  const match = readText(path).match(/^\s*Version:\s*(\d+)\s*$/m);
  return match ? Number(match[1]) : null;
}

function readFirstVersion(root, paths) {
  for (const path of paths) {
    if (!path) continue;
    const version = readVersion(join(root, path));
    if (version !== null) return version;
  }
  return null;
}

function listObjects(value, source) {
  if (!Array.isArray(value) || value.some((item) => !isObject(item))) throw new RuntimeError(`${source} must be a list of objects`);
  return value;
}

function stringList(value, source) {
  if (!Array.isArray(value) || value.some((item) => typeof item !== 'string')) throw new RuntimeError(`${source} must be a list of strings`);
  return value;
}

function relativePathList(value, source) {
  if (!Array.isArray(value)) throw new RuntimeError(`${source} must be a list`);
  return value.map((item) => {
    if (typeof item === 'string') return item;
    if (isObject(item) && typeof item.relative_path === 'string') return item.relative_path;
    throw new RuntimeError(`${source} entries must be strings or objects with relative_path`);
  });
}

function conditionMatches(condition, values) {
  if (condition === undefined || condition === null || (isObject(condition) && Object.keys(condition).length === 0)) return true;
  if (!isObject(condition)) throw new RuntimeError('step when condition must be an object');
  const keys = Object.keys(condition);
  if (keys.length === 1 && keys[0] === 'all') return condition.all.every((item) => conditionMatches(item, values));
  if (keys.length === 1 && keys[0] === 'any') return condition.any.some((item) => conditionMatches(item, values));
  if (keys.length === 1 && keys[0] === 'not') return !conditionMatches(condition.not, values);
  const actual = values[String(condition.value ?? '')];
  if (Object.prototype.hasOwnProperty.call(condition, 'equals')) return actual === condition.equals;
  if (Object.prototype.hasOwnProperty.call(condition, 'present')) return (actual !== undefined && actual !== null) === Boolean(condition.present);
  throw new RuntimeError('step when condition must use all, any, not, equals, or present');
}

function storeStepResult(values, outputs, result) {
  if (result === undefined || result === null) return;
  const names = Array.isArray(outputs) ? outputs.map(String).filter(Boolean) : [];
  if (names.length === 0) {
    values._last = result;
  } else if (names.length === 1) {
    values[names[0]] = result;
  } else {
    if (!isObject(result)) throw new RuntimeError('multi-output primitive results must be objects');
    for (const name of names) {
      if (!Object.prototype.hasOwnProperty.call(result, name)) throw new RuntimeError(`primitive result missing declared output: ${name}`);
      values[name] = result[name];
    }
  }
}

function resolveTemplate(template, values) {
  if (Array.isArray(template)) return template.map((item) => resolveTemplate(item, values));
  if (!isObject(template)) return template;
  const keys = Object.keys(template);
  if (keys.length === 1 && keys[0] === '$value') return values[String(template.$value)];
  if (Object.prototype.hasOwnProperty.call(template, '$field')) {
    const spec = template.$field;
    const parts = Array.isArray(spec.path) ? spec.path.map(String) : String(spec.path ?? '').split('.').filter(Boolean);
    let value = values[String(spec.value ?? '')];
    for (const part of parts) {
      if (!isObject(value) || !Object.prototype.hasOwnProperty.call(value, part)) throw new RuntimeError(`template $field cannot resolve ${spec.value}.${parts.join('.')}`);
      value = value[part];
    }
    return value;
  }
  if (keys.length === 1 && keys[0] === '$count') return Array.isArray(values[String(template.$count)]) ? values[String(template.$count)].length : 0;
  if (Object.prototype.hasOwnProperty.call(template, '$exists_status')) {
    const spec = template.$exists_status;
    return Boolean(values[String(spec.value ?? '')]) ? spec.present : spec.missing;
  }
  if (Object.prototype.hasOwnProperty.call(template, '$count_status')) {
    const spec = template.$count_status;
    const counted = values[String(spec.value ?? '')];
    return Array.isArray(counted) && counted.length ? spec.present : spec.missing;
  }
  if (Object.prototype.hasOwnProperty.call(template, '$join_path')) {
    const spec = template.$join_path;
    return join(String(values[String(spec.base ?? '')] ?? ''), String(spec.path ?? '')).replace(/\\/g, '/');
  }
  return Object.fromEntries(Object.entries(template).map(([key, value]) => [key, resolveTemplate(value, values)]));
}

function statusAction(kind, path, detail, extra = {}) {
  return {
    kind,
    path,
    detail,
    role: extra.role ?? '',
    safety: extra.safety ?? 'safe',
    source: extra.source ?? path,
    category: extra.category ?? '',
    remediation_kind: '',
    remediation_target: '',
    remediation_reason: '',
    remediation_confidence: '',
    memory_action: '',
    match_source: '',
  };
}

function payloadAction(kind, path, detail, safety = 'manual', category = 'contract-drift') {
  return statusAction(kind, path, detail, { role: 'payload-contract', safety, source: path, category });
}

function payloadFileSet(root, policy) {
  const aliases = new Map((policy.payload_path_aliases ?? []).filter(isObject).map((item) => [String(item.source), String(item.target)]));
  return new Set(listFiles(root).map((path) => aliases.get(path) ?? path));
}

function memoryManifestCounts(targetRoot, manifestPath) {
  const counts = { status: 'missing', note_count: 0, required_count: 0, optional_count: 0, routing_only_count: 0, path: manifestPath };
  const path = join(targetRoot, manifestPath);
  if (!existsSync(path)) return counts;
  const notes = Object.values(parseTomlTables(readText(path), 'notes'));
  counts.status = 'present';
  counts.note_count = notes.length;
  for (const note of notes) {
    if (!isObject(note)) continue;
    const relevance = String(note.task_relevance ?? '').trim().toLowerCase();
    if (relevance === 'required') counts.required_count += 1;
    else if (relevance === 'optional') counts.optional_count += 1;
    if (note.routing_only === true) counts.routing_only_count += 1;
  }
  return counts;
}

function emitInstallResultText(result) {
  const lines = [
    `Target: ${resolve(String(result.target_root ?? ''))}`,
    String(result.message ?? ''),
    `Detected version: ${result.detected_version ?? 'none'} (payload version ${result.bootstrap_version})`,
  ];
  if (result.outcome) {
    lines.push(`Outcome: ${result.outcome} (${result.reason_code ?? ''})`);
    lines.push(`Mutation applied: ${result.mutation_applied ? 'yes' : 'no'}`);
    if (result.conflict_owner) lines.push(`Conflict owner: ${result.conflict_owner}`);
    if (result.recovery_command) lines.push(`Recovery: ${result.recovery_command}`);
  }
  for (const action of listObjects(result.actions ?? [], 'result.actions')) {
    const details = [];
    for (const key of ['detail', 'role', 'safety', 'category', 'remediation_kind', 'remediation_target', 'remediation_confidence', 'memory_action', 'match_source']) {
      if (action[key]) details.push(key === 'detail' ? String(action[key]) : `${key}=${action[key]}`);
    }
    lines.push(`- ${action.kind}: ${action.path}${details.length ? ` (${details.join('; ')})` : ''}`);
  }
  return `${lines.join('\n').trimEnd()}\n`;
}

function emitCurrentMemoryText(result) {
  const lines = [`Target: ${resolve(String(result.target_root ?? ''))}`, `Detected version: ${result.detected_version ?? 'none'} (payload version ${result.bootstrap_version})`];
  for (const note of listObjects(result.notes ?? [], 'result.notes')) {
    lines.push('', `[${note.path ?? ''}]`);
    lines.push(note.exists ? String(note.content ?? '').trimEnd() : '(missing)');
  }
  return `${lines.join('\n').trimEnd()}\n`;
}

function emitMemoryReportText(result) {
  const status = isObject(result.status) ? result.status : {};
  const active = isObject(result.active) ? result.active : {};
  const lines = ['Memory report', `Target: ${result.target_root ?? ''}`, `Health: ${result.health ?? 'unknown'}`];
  lines.push(`Notes: ${status.note_count ?? 0} (${status.manifest_status ?? 'unknown'})`);
  lines.push(`Active: required=${active.required_count ?? 0}, optional=${active.optional_count ?? 0}, routing-only=${active.routing_only_count ?? 0}`);
  if (isObject(result.next_action)) lines.push(`Next: ${result.next_action.summary ?? ''}`);
  if (isObject(result.detail_commands) && result.detail_commands.full) lines.push(String(result.detail_commands.full));
  return `${lines.join('\n').trimEnd()}\n`;
}

function emitPlanningReportText(result) {
  const status = isObject(result.status) ? result.status : {};
  const lines = [`Target: ${result.target_root ?? ''}`, `Command: ${result.module ?? 'planning'}`, `Health: ${result.health ?? 'unknown'}`];
  lines.push(`Status: ${status.active_todo_count ?? 0} active TODO / ${status.queued_todo_count ?? 0} queued TODO / ${status.active_execplan_count ?? 0} active execplans / ${status.roadmap_lane_count ?? 0} roadmap lanes / ${status.roadmap_candidate_count ?? 0} roadmap candidates`);
  if (isObject(result.next_action)) lines.push(`Next action: ${result.next_action.summary ?? ''}`);
  return `${lines.join('\n').trimEnd()}\n`;
}

function emitTinySectionedText(result) {
  const lines = [String(result.summary ?? '')];
  if (Array.isArray(result.common_sections) && result.common_sections.length) {
    lines.push('Common sections:');
    for (const section of result.common_sections) lines.push(`- ${section}`);
  }
  if (isObject(result.detail_commands)) {
    lines.push('Detail commands:');
    for (const [key, value] of Object.entries(result.detail_commands)) lines.push(`- ${key}: ${value}`);
  }
  return `${lines.join('\n').trimEnd()}\n`;
}

function emitSelectedOutputText(result) {
  const lines = [
    `Kind: ${result.kind ?? ''}`,
    `Source command: ${result.source_command ?? ''}`,
    'Values:',
    JSON.stringify(result.values ?? {}, null, 2),
  ];
  if (Array.isArray(result.missing) && result.missing.length) {
    lines.push('Missing:');
    for (const item of result.missing) lines.push(`- ${item}`);
  }
  return `${lines.join('\n').trimEnd()}\n`;
}

function emitDelegationOutcomesText(result) {
  const recorded = isObject(result.recorded) ? result.recorded : {};
  const lines = [
    `Kind: ${result.kind ?? ''}`,
    `Path: ${result.path ?? '.agentic-workspace/delegation-outcomes.json'}`,
    `Record count: ${result.record_count ?? 1}`,
    `Rule: ${result.rule ?? 'local-only delegation outcome evidence'}`,
  ];
  if (Object.keys(recorded).length) {
    lines.push('Recorded:');
    for (const key of ['recorded_at', 'delegation_target', 'task_class', 'outcome', 'handoff_sufficiency', 'review_burden', 'escalation_required']) {
      if (Object.prototype.hasOwnProperty.call(recorded, key)) lines.push(`- ${key}: ${recorded[key]}`);
    }
  }
  return `${lines.join('\n').trimEnd()}\n`;
}

function emitOutput(values, args = {}) {
  const result = values.result;
  if (String(values.format ?? 'text') === 'json') return `${JSON.stringify(result, null, 2)}\n`;
  if (args.text_style === 'install-result' && isObject(result)) return emitInstallResultText(result);
  if (args.text_style === 'current-memory' && isObject(result)) return emitCurrentMemoryText(result);
  if (isObject(result) && result.kind === 'memory-module-report/v1') return emitMemoryReportText(result);
  if (isObject(result) && result.kind === 'planning-module-report/v1' && result.profile === 'tiny') return emitPlanningReportText(result);
  if (isObject(result) && result.kind === 'agentic-workspace/default-route-sections/v1') return emitTinySectionedText(result);
  if (isObject(result) && result.kind === 'agentic-workspace/selected-output/v1') return emitSelectedOutputText(result);
  if (isObject(result) && result.kind === 'agentic-workspace/delegation-outcomes/v1') return emitDelegationOutcomesText(result);
  if (!isObject(result)) return `${result}\n`;
  if (Array.isArray(result.files) && result.files.every((item) => typeof item === 'string')) return `${result.files.join('\n')}\n`;
  const lines = [String(result.message ?? result.kind ?? '')];
  for (const action of listObjects(result.actions ?? [], 'result.actions')) lines.push(`- ${action.path ?? action.id ?? action.kind}`);
  return `${lines.join('\n').trimEnd()}\n`;
}

function assemblePayload(values, args) {
  const fields = args.fields ?? {};
  if (fields.template !== undefined) return resolveTemplate(fields.template, values);
  if (fields.payload_kind === 'package-file-list') {
    const filesFrom = String(fields.files_from ?? 'files');
    const bundledSkillsFrom = String(fields.bundled_skill_files_from ?? 'bundled_skill_files');
    return {
      files: relativePathList(values[filesFrom] ?? [], filesFrom),
      default_files: stringList(fields.default_files ?? [], 'payload.assemble fields.default_files'),
      optional_files: stringList(fields.optional_files ?? [], 'payload.assemble fields.optional_files'),
      bundled_skill_files: relativePathList(values[bundledSkillsFrom] ?? [], bundledSkillsFrom),
      optional_enable_commands: stringList(fields.optional_enable_commands ?? [], 'payload.assemble fields.optional_enable_commands'),
    };
  }
  const targetRoot = values.target_root;
  const payload = { dry_run: Boolean(fields.dry_run ?? true), message: String(fields.message ?? '') };
  if (targetRoot !== undefined) payload.target_root = String(targetRoot);
  if (fields.actions_from === 'files') {
    payload.actions = listObjects(values.files ?? [], 'files').map((item) => ({ kind: 'file', path: String(item.relative_path ?? '') }));
    return payload;
  }
  if (fields.actions_from === 'registry.skills') {
    payload.mode = String(fields.mode ?? 'skills');
    payload.actions = listObjects(values.registry?.skills ?? [], 'registry.skills').map((item) => ({ kind: 'skill', id: String(item.id ?? ''), path: String(item.path ?? '') }));
    return payload;
  }
  throw new RuntimeError(`unsupported payload.assemble actions_from: ${fields.actions_from}`);
}

function payloadStatus(values, args) {
  const policy = readJson(resolveInside(resourceRoot(String(args.policy_root ?? '')), String(args.policy_path ?? '')));
  const targetRoot = resolve(String(values[String(args.target_root_value ?? 'target_root')] ?? process.cwd()));
  const bootstrapVersion = Number(policy.bootstrap_version ?? 0);
  const manifestPath = String(policy.manifest_path ?? '');
  const active = memoryManifestCounts(targetRoot, manifestPath);
  const actions = [];
  const notice = isObject(policy.workspace_orchestrator_notice) ? policy.workspace_orchestrator_notice : {};
  if (notice.marker && !existsSync(join(targetRoot, notice.marker))) actions.push(statusAction('warning', String(notice.marker), String(notice.detail ?? ''), { role: String(notice.role ?? 'workspace-orchestration'), safety: String(notice.safety ?? 'safe'), category: String(notice.category ?? 'safe-update') }));
  for (const entry of listObjects(policy.status_files ?? [], 'memory.payload.status status_files')) {
    const path = String(entry.path ?? '');
    const present = existsSync(join(targetRoot, path));
    actions.push(statusAction(present ? 'present' : 'missing', path, present ? 'file exists' : 'file missing', { role: String(entry.role ?? ''), safety: String(entry.safety ?? 'safe'), category: String(entry[present ? 'present_category' : 'missing_category'] ?? '') }));
  }
  for (const obsolete of stringList(policy.obsolete_files ?? [], 'memory.payload.status obsolete_files')) if (existsSync(join(targetRoot, obsolete))) actions.push(statusAction('obsolete', obsolete, 'legacy shared file should be removed on upgrade', { role: 'shared-replaceable', safety: 'safe', category: 'obsolete-managed-file' }));
  return { target_root: targetRoot, dry_run: Boolean(args.dry_run ?? false), mode: '', message: String(args.message ?? 'Status report'), health: active.status === 'present' ? 'healthy' : 'attention-needed', detected_version: readFirstVersion(targetRoot, [policy.version_path, policy.legacy_version_path]), bootstrap_version: bootstrapVersion, action_count: actions.length, actions, active, detail_command: String(args.detail_command ?? '') };
}

function payloadLifecyclePlan(values, args) {
  const policy = readJson(resolveInside(resourceRoot(String(args.policy_root ?? '')), String(args.policy_path ?? '')));
  const targetRoot = resolve(String(values[String(args.target_root_value ?? 'target_root')] ?? process.cwd()));
  const actions = [];
  for (const entry of listObjects(policy.status_files ?? [], 'memory.payload.lifecycle-plan status_files')) {
    const path = String(entry.path ?? '');
    if (!path) continue;
    const present = existsSync(join(targetRoot, path));
    actions.push(statusAction(present ? 'preserve' : String(args.missing_kind ?? 'would copy'), path, present ? 'already exists' : String(args.missing_detail ?? 'planned change'), { role: String(entry.role ?? ''), safety: String(entry.safety ?? 'safe'), source: String(entry.source ?? path), category: String(entry.category ?? 'safe-update') }));
  }
  return { target_root: targetRoot, dry_run: Boolean(args.dry_run ?? true), mode: String(args.mode ?? ''), message: String(args.message ?? 'Install plan'), detected_version: readFirstVersion(targetRoot, [policy.version_path, policy.legacy_version_path]), bootstrap_version: Number(policy.bootstrap_version ?? 0), actions };
}

function payloadCurrentMemory(values, args) {
  const policy = readJson(resolveInside(resourceRoot(String(args.policy_root ?? '')), String(args.policy_path ?? '')));
  const targetRoot = resolve(String(values[String(args.target_root_value ?? 'target_root')] ?? process.cwd()));
  const current = isObject(policy.current_memory) ? policy.current_memory : {};
  const notes = stringList(current.view_files ?? [], 'memory.payload.current-memory current_memory.view_files').map((path) => {
    const absolute = join(targetRoot, path);
    const present = existsSync(absolute);
    return { path, exists: present, content: present ? readText(absolute) : '' };
  });
  return { target_root: targetRoot, detected_version: readFirstVersion(targetRoot, [policy.version_path, policy.legacy_version_path]), bootstrap_version: Number(policy.bootstrap_version ?? 0), notes };
}

function verifyPayload(values, args) {
  const policy = readJson(resolveInside(resourceRoot(String(args.policy_root ?? '')), String(args.policy_path ?? '')));
  const payloadRoot = resourceRoot(String(args.payload_root ?? '_payload'));
  const targetRoot = resolve(String(values[String(args.target_root_value ?? 'target_root')] ?? process.cwd()));
  const payloadPaths = payloadFileSet(payloadRoot, policy);
  const actions = [];
  for (const required of stringList(policy.required_files ?? [], 'memory.payload.verify required_files')) {
    const present = payloadPaths.has(required);
    actions.push(payloadAction(present ? 'current' : 'manual review', required, present ? 'required payload file present' : 'required payload file missing', present ? 'safe' : 'manual', present ? 'safe-update' : 'contract-drift'));
  }
  for (const forbidden of stringList(policy.forbidden_files ?? [], 'memory.payload.verify forbidden_files')) if (payloadPaths.has(forbidden)) actions.push(payloadAction('manual review', forbidden, 'forbidden file is present in the shipped payload'));
  return { target_root: targetRoot, dry_run: true, mode: 'full', message: 'Payload verification', detected_version: readFirstVersion(targetRoot, [policy.version_path, policy.legacy_version_path]), bootstrap_version: Number(policy.bootstrap_version ?? 0), actions, route_summary: {}, missing_note_hint: '', review_summary: {}, review_cases: [], sync_summary: {}, route_report_summary: {}, route_report_feedback_cases: [], route_report_fixture_results: [] };
}

const WORKSPACE_SELECTOR_LIMITS = {
  max_selectors: 32,
  max_selector_bytes: 256,
  max_selector_request_bytes: 512,
  max_error_envelope_bytes: 6000,
  max_error_items: 8,
};

const WORKSPACE_SELECTOR_DESCRIPTORS = {
  config: [
    'workspace',
    'workspace.enabled',
    'workspace.enabled_modules',
    'workspace.improvement_latitude',
    'workspace.optimization_bias',
    'workspace.optimization_bias_source',
    'workspace.workflow_obligations',
    'warnings',
    'target',
    'config_path',
    'modules',
    'mixed_agent',
    'mixed_agent.runtime_resolution',
    'assurance',
    'config_enforcement',
    'config_effect_audit',
    'cli_compatibility',
    'selector_inventory',
  ],
  defaults: [
    'kind',
    'answer',
    'answer.command',
    'section',
    'sections',
    'startup',
    'startup.canonical_doc',
    'root_cli_authority',
    'root_cli_authority.command',
    'workspace',
    'proof_selection',
    'improvement_intake',
    'optimization_bias',
    'selector_inventory',
  ],
};

const WORKSPACE_DEPRECATED_SELECTOR_REPLACEMENTS = {
  config: {
    'workspace.feature_tier': 'workspace.enabled_modules',
  },
};

function selectorUtf8Bytes(value) {
  return Buffer.byteLength(String(value), 'utf8');
}

function workspaceSelectorInventoryCommand(sourceCommand) {
  return `agentic-workspace ${sourceCommand} --target . --select selector_inventory --format json`;
}

function workspaceSelectorBudget() {
  return {
    max_selectors: WORKSPACE_SELECTOR_LIMITS.max_selectors,
    max_selector_bytes: WORKSPACE_SELECTOR_LIMITS.max_selector_bytes,
    max_selector_request_bytes: WORKSPACE_SELECTOR_LIMITS.max_selector_request_bytes,
    max_error_envelope_bytes: WORKSPACE_SELECTOR_LIMITS.max_error_envelope_bytes,
    max_error_items: WORKSPACE_SELECTOR_LIMITS.max_error_items,
  };
}

function fitWorkspaceSelectorError(payload) {
  if (selectorUtf8Bytes(JSON.stringify(payload)) <= WORKSPACE_SELECTOR_LIMITS.max_error_envelope_bytes) return payload;
  payload.suggestions = {};
  if (selectorUtf8Bytes(JSON.stringify(payload)) <= WORKSPACE_SELECTOR_LIMITS.max_error_envelope_bytes) return payload;
  payload.requested_selectors = Array.isArray(payload.requested_selectors) ? payload.requested_selectors.slice(0, 3) : [];
  payload.unknown_selectors = Array.isArray(payload.unknown_selectors) ? payload.unknown_selectors.slice(0, 3) : [];
  if (isObject(payload.selector_inventory)) {
    payload.selector_inventory.sample = Array.isArray(payload.selector_inventory.sample) ? payload.selector_inventory.sample.slice(0, 3) : [];
  }
  if (selectorUtf8Bytes(JSON.stringify(payload)) <= WORKSPACE_SELECTOR_LIMITS.max_error_envelope_bytes) return payload;
  payload.requested_selectors = [];
  payload.unknown_selectors = [];
  if (isObject(payload.selector_inventory)) payload.selector_inventory.sample = [];
  payload.truncated_to_budget = true;
  return payload;
}

function workspaceSelectorRequest(select, sourceCommand) {
  if (!select) return { selectors: [], error: null };
  const selectors = [];
  let requestedSelectorCount = 0;
  let selectorRequestBytes = 0;
  const seen = new Set();
  for (const raw of String(select).split(',')) {
    const token = raw.trim();
    if (!token) continue;
    requestedSelectorCount += 1;
    const tokenBytes = selectorUtf8Bytes(token);
    if (requestedSelectorCount > WORKSPACE_SELECTOR_LIMITS.max_selectors) {
      return {
        selectors,
        error: workspaceSelectorRequestError(sourceCommand, 'too-many-selectors', selectors, requestedSelectorCount, selectorRequestBytes, requestedSelectorCount - 1, null, token),
      };
    }
    if (tokenBytes > WORKSPACE_SELECTOR_LIMITS.max_selector_bytes) {
      return {
        selectors,
        error: workspaceSelectorRequestError(sourceCommand, 'selector-too-long', selectors, requestedSelectorCount, selectorRequestBytes + tokenBytes, requestedSelectorCount - 1, tokenBytes, token),
      };
    }
    if (selectorRequestBytes + tokenBytes > WORKSPACE_SELECTOR_LIMITS.max_selector_request_bytes) {
      return {
        selectors,
        error: workspaceSelectorRequestError(sourceCommand, 'selector-request-too-large', selectors, requestedSelectorCount, selectorRequestBytes + tokenBytes, requestedSelectorCount - 1, null, token),
      };
    }
    selectorRequestBytes += tokenBytes;
    if (!seen.has(token)) {
      selectors.push(token);
      seen.add(token);
    }
  }
  return { selectors, error: null };
}

function workspaceSelectorRequestError(sourceCommand, reason, selectors, requestedSelectorCount, selectorRequestBytes, selectorIndex, selectorBytes, offendingSelector) {
  const inventoryCommand = workspaceSelectorInventoryCommand(sourceCommand);
  const payload = {
    kind: 'agentic-workspace/selector-validation-error/v1',
    status: 'invalid-selector-request',
    reason,
    source_command: sourceCommand,
    requested_selectors: selectors.slice(0, WORKSPACE_SELECTOR_LIMITS.max_error_items),
    requested_selector_count: requestedSelectorCount,
    requested_selector_omitted_count: Math.max(0, requestedSelectorCount - WORKSPACE_SELECTOR_LIMITS.max_error_items),
    selector_request_bytes: selectorRequestBytes,
    selector_inventory: {
      status: 'omitted-from-validation-error',
      inventory_command: inventoryCommand,
      discovery_command: inventoryCommand,
      rule: 'Selector request limits are enforced before command payload construction; use the inventory route for valid selectors.',
    },
    selector_budget: workspaceSelectorBudget(),
    validation_rule: 'Selector requests are bounded before descriptor lookup or payload construction.',
  };
  if (selectorIndex !== null) {
    payload.selector_index = selectorIndex;
    payload.limit_contributor = 'selector_index';
  }
  if (selectorBytes !== null) {
    payload.selector_bytes = selectorBytes;
    payload.limit_contributor = 'selector_bytes';
  }
  if (offendingSelector) payload.offending_selector = String(offendingSelector).slice(0, 120);
  if (reason === 'selector-too-long') payload.limit_contributor = 'selector_bytes';
  else if (reason === 'selector-request-too-large') payload.limit_contributor = 'selector_request_bytes';
  else if (reason === 'too-many-selectors') payload.limit_contributor = 'requested_selector_count';
  return fitWorkspaceSelectorError(payload);
}

function workspaceSelectorSuggestions(unknown, available) {
  const unknownRoot = String(unknown).split('.', 1)[0];
  const matches = [];
  for (const selector of available) {
    const selectorRoot = String(selector).split('.', 1)[0];
    if (selectorRoot === unknownRoot || String(selector).startsWith(unknown) || String(unknown).startsWith(selectorRoot)) matches.push(selector);
    if (matches.length >= 1) break;
  }
  return matches;
}

function workspaceSelectorReplacements(sourceCommand, selectors) {
  const replacements = WORKSPACE_DEPRECATED_SELECTOR_REPLACEMENTS[sourceCommand] ?? {};
  const entries = [];
  for (const selector of selectors) {
    if (replacements[selector]) entries.push([selector, replacements[selector]]);
    if (entries.length >= WORKSPACE_SELECTOR_LIMITS.max_error_items) break;
  }
  return Object.fromEntries(entries);
}

function workspaceSelectorPrevalidationError(select, sourceCommand) {
  const request = workspaceSelectorRequest(select, sourceCommand);
  if (request.error) return request.error;
  const available = WORKSPACE_SELECTOR_DESCRIPTORS[sourceCommand] ?? [];
  const unknown = request.selectors.filter((selector) => selector !== 'selector_inventory' && !available.includes(selector));
  if (!unknown.length) return null;
  const inventoryCommand = workspaceSelectorInventoryCommand(sourceCommand);
  const suggestions = Object.fromEntries(
    unknown.slice(0, WORKSPACE_SELECTOR_LIMITS.max_error_items)
      .map((selector) => [selector, workspaceSelectorSuggestions(selector, available)])
      .filter(([, matches]) => matches.length),
  );
  const replacementSelectors = workspaceSelectorReplacements(sourceCommand, unknown);
  const payload = {
    kind: 'agentic-workspace/selector-validation-error/v1',
    status: 'invalid-selector',
    source_command: sourceCommand,
    requested_selectors: request.selectors.slice(0, WORKSPACE_SELECTOR_LIMITS.max_error_items),
    requested_selector_count: request.selectors.length,
    requested_selector_omitted_count: Math.max(0, request.selectors.length - WORKSPACE_SELECTOR_LIMITS.max_error_items),
    unknown_selectors: unknown.slice(0, WORKSPACE_SELECTOR_LIMITS.max_error_items),
    unknown_selector_count: unknown.length,
    unknown_selector_omitted_count: Math.max(0, unknown.length - WORKSPACE_SELECTOR_LIMITS.max_error_items),
    selector_inventory: {
      status: 'omitted-from-validation-error',
      available_count: available.length,
      sample: available.slice(0, WORKSPACE_SELECTOR_LIMITS.max_error_items),
      sample_limit: WORKSPACE_SELECTOR_LIMITS.max_error_items,
      discovery_command: inventoryCommand,
      inventory_command: inventoryCommand,
      absence_state: 'hidden_behind_detail_route',
      rule: 'Unknown selectors return a bounded validation envelope; full selector inventory is available only through an explicit detail route.',
    },
    suggestions,
    selector_budget: workspaceSelectorBudget(),
    validation_rule: 'Selector requests are exact: nested selectors must be declared before payload construction.',
  };
  if (Object.keys(replacementSelectors).length) {
    payload.deprecated_selectors = Object.keys(replacementSelectors);
    payload.replacement_selectors = replacementSelectors;
    payload.replacement_rule = 'Deprecated selectors are rejected atomically with a bounded replacement hint.';
  }
  return fitWorkspaceSelectorError(payload);
}

function workspaceDefaultsSelect(payload, values) {
  if (values._selector_prevalidation_failed) return payload;
  let result = {
    kind: 'agentic-workspace/default-route-sections/v1',
    profile: 'tiny',
    summary: 'Default-route contract sections are available on demand; request one section or full detail instead of loading the whole contract.',
    available_sections: Object.keys(payload).sort(),
    common_sections: ['startup', 'validation', 'proof_selection', 'combined_install'],
    detail_commands: {
      section: 'agentic-workspace defaults --section <section> --format json',
      full: 'agentic-workspace defaults --verbose --format json',
    },
  };
  if (values.verbose) result = payload;
  const section = values.section ? String(values.section) : '';
  if (section) {
    const answer = payload[section];
    result = answer === undefined
      ? { profile: 'compact-contract-answer/v1', surface: 'defaults', selector: { section }, matched: false, answer: {}, available_sections: Object.keys(payload).sort() }
      : { profile: 'compact-contract-answer/v1', surface: 'defaults', selector: { section }, matched: true, answer };
  }
  if (values.select) {
    let current = result;
    for (const part of String(values.select).split('.').filter(Boolean)) current = isObject(current) ? current[part] : undefined;
    const valuesBySelector = {};
    const missing = [];
    if (current === undefined) missing.push(String(values.select));
    else valuesBySelector[String(values.select)] = current;
    result = { kind: 'agentic-workspace/selected-output/v1', source_command: 'defaults', values: valuesBySelector };
    if (missing.length) result.missing = missing;
  }
  return result;
}

function selectFields(value, values) {
  if (!values.select) return value;
  let current = value;
  for (const part of String(values.select).split('.').filter(Boolean)) current = isObject(current) ? current[part] : undefined;
  const valuesBySelector = {};
  const missing = [];
  if (current === undefined) missing.push(String(values.select));
  else valuesBySelector[String(values.select)] = current;
  const selected = { kind: 'agentic-workspace/selected-output/v1', source_command: 'config', values: valuesBySelector };
  if (missing.length) selected.missing = missing;
  return selected;
}

function workspaceConfig(values) {
  const targetRoot = resolve(String(values.target ?? '.'));
  const configPath = join(targetRoot, '.agentic-workspace/config.toml');
  const config = existsSync(configPath) ? parseTomlTables(readText(configPath), 'workspace') : {};
  const modulesConfig = existsSync(configPath) ? parseTomlTables(readText(configPath), 'modules') : {};
  const enabledModules = Array.isArray(modulesConfig.enabled) ? modulesConfig.enabled.map(String) : ['planning', 'memory'];
  return {
    kind: 'agentic-workspace/config/v1',
    profile: 'tiny',
    exists: false,
    target_root: targetRoot,
    config_path: configPath.replace(/\\/g, '/'),
    local_config_path: join(targetRoot, '.agentic-workspace/config.local.toml').replace(/\\/g, '/'),
    config_present: existsSync(configPath),
    local_config_present: existsSync(join(targetRoot, '.agentic-workspace/config.local.toml')),
    workspace: {
      cli_invoke: String(config.cli_invoke ?? 'uv run agentic-workspace'),
      enabled_modules: enabledModules,
      agent_instructions_file: String(config.agent_instructions_file ?? 'AGENTS.md'),
      optimization_bias: String(config.optimization_bias ?? 'balanced'),
    },
  };
}

function reportPlanning(values, operationId) {
  const targetRoot = resolve(String(values.target ?? '.'));
  const statePath = join(targetRoot, '.agentic-workspace/planning/state.toml');
  const statePresent = existsSync(statePath);
  const text = statePresent ? readText(statePath) : '';
  const count = (pattern) => (text.match(pattern) ?? []).length;
  return { kind: 'planning-module-report/v1', profile: 'tiny', module: 'planning', target_root: targetRoot, health: statePresent ? 'healthy' : 'attention-needed', status: { active_todo_count: count(/active_items/g), queued_todo_count: count(/queued_items/g), active_execplan_count: count(/active_execplans/g), roadmap_lane_count: count(/roadmap_lanes/g), roadmap_candidate_count: count(/roadmap_candidates/g) }, next_action: { summary: statePresent ? 'No immediate planning action.' : 'Install or initialize Planning to create state.' }, detail_commands: { full: 'agentic-planning report --target . --verbose --format json' }, command: operationId };
}

function lifecycleResult(values, message) {
  const targetRoot = resolve(String(values.target ?? values.target_root ?? '.'));
  const dryRun = values.dry_run !== false;
  return {
    target_root: targetRoot,
    dry_run: dryRun,
    message,
    actions: [],
    detected_version: null,
    bootstrap_version: null,
    outcome: 'noop',
    mutation_applied: false,
    reason_code: dryRun ? 'dry-run' : 'already-satisfied',
    conflict_owner: null,
    recovery_command: null,
  };
}

export function finalizeMutationOutcome(result) {
  const kinds = new Set((result.actions ?? []).map((action) => String(action.kind ?? '').trim().toLowerCase()));
  const failed = kinds.has('failed') || kinds.has('error');
  const blocked = ['blocked', 'blocked-with-reason', 'manual review', 'refused'].some((kind) => kinds.has(kind));
  const applied = !result.dry_run && ['adopted', 'archived', 'closed', 'copied', 'copy', 'created', 'deleted', 'installed', 'moved', 'overwritten', 'removed', 'replaced', 'updated', 'upgraded'].some((kind) => kinds.has(kind));
  result.outcome = failed ? 'failed' : blocked ? 'blocked' : applied ? 'applied' : 'noop';
  result.mutation_applied = applied;
  if (!result.reason_code || ['dry-run', 'already-satisfied'].includes(result.reason_code)) {
    result.reason_code = failed ? 'mutation-failed' : blocked ? 'manual-review-required' : applied ? 'mutation-applied' : result.dry_run ? 'dry-run' : 'already-satisfied';
  }
  return result;
}

function planningNewPlanResult(values, operationId) {
  const result = lifecycleResult(values, operationId);
  const slug = String(values.id ?? '').trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
  const owner = `.agentic-workspace/planning/execplans/${slug}.plan.json`;
  const stateOwner = '.agentic-workspace/planning/state.toml';
  const statePath = join(result.target_root, stateOwner);
  const state = existsSync(statePath) ? parsePlanningState(readText(statePath)) : {
    kind: 'agentic-planning-state',
    schema_version: 'planning-state/v1',
    work_items: [],
    active: { execplans: [] },
    todo: { active_items: [], queued_items: [] },
    roadmap: { lanes: [], candidates: [] },
  };
  state.todo = isObject(state.todo) ? state.todo : {};
  state.todo.active_items = Array.isArray(state.todo.active_items) ? state.todo.active_items : [];
  state.todo.queued_items = Array.isArray(state.todo.queued_items) ? state.todo.queued_items : [];
  state.roadmap = isObject(state.roadmap) ? state.roadmap : {};
  state.roadmap.lanes = Array.isArray(state.roadmap.lanes) ? state.roadmap.lanes : [];
  state.roadmap.candidates = Array.isArray(state.roadmap.candidates) ? state.roadmap.candidates : [];
  const activate = values.activate === true;
  const queue = values.queue === true;
  const switchActive = values.switch_active === true;
  const prepOnly = values.prep_only === true;
  const lane = String(values.owner_lane ?? values.lane ?? '').trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
  const expectedRevision = String(values.expect_planning_revision ?? '').trim();
  const cliInvoke = String(workspaceConfig({ target: result.target_root }).workspace?.cli_invoke ?? 'agentic-workspace');
  if (expectedRevision) {
    const currentRevision = planningRevision(result.target_root, state);
    if (expectedRevision !== currentRevision.revision_id) {
      result.actions = [{ kind: 'manual review', path: stateOwner, detail: 'planning revision changed before mutation; refresh planning context' }];
      result.reason_code = 'planning-revision-mismatch';
      result.conflict_owner = stateOwner;
      result.recovery_command = `${cliInvoke} summary --target . --format json`;
      result.expected_planning_revision = expectedRevision;
      result.current_planning_revision = currentRevision.revision_id;
      return finalizeMutationOutcome(result);
    }
  }
  if (!slug) {
    result.actions = [{ kind: 'manual review', path: stateOwner, detail: '--id must contain at least one alphanumeric character' }];
    result.reason_code = 'invalid-request';
    return finalizeMutationOutcome(result);
  }
  if (activate && queue) {
    result.actions = [{ kind: 'manual review', path: stateOwner, detail: 'choose only one of --activate or --queue' }];
    result.reason_code = 'selector-conflict';
    return finalizeMutationOutcome(result);
  }
  if (switchActive && !activate) {
    result.actions = [{ kind: 'manual review', path: stateOwner, detail: '--switch-active requires --activate' }];
    result.reason_code = 'invalid-request';
    return finalizeMutationOutcome(result);
  }
  if (lane && !activate) {
    result.actions = [{ kind: 'manual review', path: stateOwner, detail: '--lane requires --activate' }];
    result.reason_code = 'invalid-request';
    return finalizeMutationOutcome(result);
  }
  const title = String(values.title ?? '').trim() || slug;
  const source = String(values.source ?? '').trim();
  const recordPath = join(result.target_root, owner);
  const recordExisted = existsSync(recordPath);
  if (recordExisted && values.overwrite !== true) {
    result.reason_code = 'target-already-exists';
    result.conflict_owner = owner;
    result.recovery_command = `${cliInvoke} planning new-plan --id ${JSON.stringify(slug)} --title ${JSON.stringify(title)} --target . --overwrite --format json`;
    result.actions = [{ kind: 'manual review', path: owner, detail: 'target canonical execplan record already exists; pass --overwrite to replace it' }];
    return finalizeMutationOutcome(result);
  }
  const allItems = [...state.todo.active_items, ...state.todo.queued_items];
  if ((activate || queue) && allItems.some((item) => isObject(item) && String(item.id ?? '') === slug)) {
    result.actions = [{ kind: 'manual review', path: stateOwner, detail: `planning item '${slug}' already exists in state.toml` }];
    result.reason_code = 'planning-item-already-exists';
    result.conflict_owner = stateOwner;
    return finalizeMutationOutcome(result);
  }
  if (activate && state.todo.active_items.length && !switchActive) {
    result.actions = [{ kind: 'manual review', path: stateOwner, detail: 'active planning item already exists; rerun with --switch-active to demote existing active items into todo.queued_items' }];
    result.reason_code = 'active-owner-conflict';
    result.conflict_owner = stateOwner;
    return finalizeMutationOutcome(result);
  }
  let laneItem = null;
  if (lane) {
    laneItem = state.roadmap.lanes.find((item) => isObject(item) && String(item.id ?? '') === lane) ?? null;
    if (!laneItem || String(laneItem.status ?? '') !== 'active' || (laneItem.execplan && String(laneItem.execplan) !== owner)) {
      result.actions = [{ kind: 'manual review', path: stateOwner, detail: `lane '${lane}' is not active or already belongs to a different execplan; no plan was created` }];
      result.reason_code = 'lane-owner-conflict';
      result.conflict_owner = stateOwner;
      return finalizeMutationOutcome(result);
    }
  }
  if (result.dry_run) {
    result.actions = [{ kind: existsSync(recordPath) ? 'would update' : 'would create', path: owner, detail: prepOnly ? 'schema-valid prep-only execplan scaffold' : 'schema-valid execplan scaffold' }];
    if (activate || queue) result.actions.push({ kind: 'would update', path: stateOwner, detail: `register '${slug}' in todo.${activate ? 'active_items' : 'queued_items'}` });
    if (activate && switchActive && state.todo.active_items.length) result.actions.push({ kind: 'would update', path: stateOwner, detail: `demote ${state.todo.active_items.length} active planning item(s) into todo.queued_items` });
    if (lane) result.actions.push({ kind: 'would update', path: stateOwner, detail: `attach execplan '${slug}' to active lane '${lane}'` });
    return finalizeMutationOutcome(result);
  }
  const templatePath = join(resourceRoot('_payload'), '.agentic-workspace/planning/execplans/TEMPLATE.plan.json');
  const plan = existsSync(templatePath) ? readJson(templatePath) : {
    kind: 'planning-execplan/v1',
    title: '',
    canonical_core: { requested_outcome: '', hard_constraints: '', agent_may_decide: '', escalate_when: '', next_action: '', proof_expectations: [], touched_scope: [], completion_criteria: [], continuation_owner: '', closeout_decision: '' },
    goal: [''],
    non_goals: [''],
    active_milestone: { id: '', status: '', scope: '' },
    validation_commands: [''],
    completion_criteria: [''],
    machine_readable_contract: {},
    execution_run: {},
  };
  plan.title = title;
  plan.canonical_core.requested_outcome = source || `Create a bounded plan for ${title}.`;
  plan.canonical_core.next_action = 'Fill in execution bounds, touched paths, and validation before implementation starts.';
  plan.canonical_core.completion_criteria = [`${title} is implemented, validated, and closed out honestly.`];
  plan.goal = [plan.canonical_core.requested_outcome];
  plan.active_milestone = { id: 'M1', status: activate ? 'active' : 'planned', scope: plan.canonical_core.next_action };
  plan.completion_criteria = [...plan.canonical_core.completion_criteria];
  plan.execution_run = isObject(plan.execution_run) ? plan.execution_run : {};
  plan.execution_run['handoff source'] = 'agentic-workspace planning new-plan';
  if (source) plan.references = [{ kind: 'source', target: source, label: source, role: 'intake', locator: '' }];
  if (prepOnly) {
    const nextAction = 'Run agentic-workspace summary --target . --verbose --format json, confirm the planning state is clean, then stop without product scaffolding.';
    const doneWhen = 'Canonical Planning state exists, summary verifies it, and no product source, package, dependency, README, handoff, or app scaffold files were created.';
    plan.goal = ['Prepare durable checked-in Planning state for later continuation without implementing or scaffolding the product.'];
    plan.non_goals = ['Do not create product or handoff files outside canonical Planning surfaces.', 'Do not start implementation; stop after summary verification.'];
    plan.immediate_next_action = [nextAction];
    plan.completion_criteria = [doneWhen];
    plan.validation_commands = ['agentic-workspace summary --target . --verbose --format json'];
    plan.touched_paths = ['.agentic-workspace/planning/state.toml', '.agentic-workspace/planning/execplans/', '.agentic-workspace/planning/decompositions/'];
    plan.canonical_core.next_action = nextAction;
    plan.canonical_core.proof_expectations = [...plan.validation_commands];
    plan.canonical_core.touched_scope = [...plan.touched_paths];
    plan.canonical_core.completion_criteria = [...plan.completion_criteria];
    plan.machine_readable_contract = isObject(plan.machine_readable_contract) ? plan.machine_readable_contract : {};
    plan.machine_readable_contract.planning_mode = { prep_only: true, halt_after_summary: true, halt_instruction: 'HALT: prep-only mode active. Run summary, then stop without product scaffolding.' };
    plan.execution_run['what happened'] = 'prep-only scaffold created; implementation has not started';
  }
  const displaced = activate && switchActive ? [...state.todo.active_items] : [];
  if (displaced.length) {
    for (const item of displaced) {
      if (!isObject(item)) continue;
      item.maturity = 'ready';
      item.status = 'next';
      item.switched_from_active_by = slug;
      item.switch_reason = source || `Switched active lane to ${title}.`;
      const displacedSurface = String(item.surface ?? '');
      const displacedPath = displacedSurface ? join(result.target_root, displacedSurface) : '';
      if (displacedPath && existsSync(displacedPath)) {
        const displacedPlan = readJson(displacedPath);
        if (isObject(displacedPlan.active_milestone)) displacedPlan.active_milestone.status = 'planned';
        writeFileSync(displacedPath, `${JSON.stringify(displacedPlan, null, 2)}\n`, 'utf8');
      }
    }
    state.todo.queued_items = [...displaced, ...state.todo.queued_items];
    state.todo.active_items = [];
  }
  if (activate || queue) {
    const stateItem = {
      id: slug,
      title,
      maturity: activate ? 'active' : 'ready',
      status: activate ? 'active' : 'next',
      surface: owner,
      why_now: source || 'Created by new-plan scaffold.',
      owner_role: 'implementation',
      review_role: 'validation',
      handoff_ready: true,
      next_action: 'Tighten scaffold fields, touched paths, and validation before implementation starts.',
      done_when: `${title} is implemented, validated, and closed out honestly.`,
      proof: 'Run the proof selected by implement --changed before claiming completion.',
      ...(source ? { refs: [source] } : {}),
    };
    if (activate) state.todo.active_items.push(stateItem);
    else state.todo.queued_items.push(stateItem);
  }
  if (laneItem) laneItem.execplan = owner;
  mkdirSync(dirname(recordPath), { recursive: true });
  writeFileSync(recordPath, `${JSON.stringify(plan, null, 2)}\n`, 'utf8');
  result.actions = [{ kind: recordExisted ? 'updated' : 'created', path: owner, detail: prepOnly ? 'schema-valid prep-only execplan scaffold' : 'schema-valid execplan scaffold' }];
  if (activate || queue || laneItem) {
    mkdirSync(dirname(statePath), { recursive: true });
    writeFileSync(statePath, renderPlanningState(state), 'utf8');
    result.actions.push({ kind: 'updated', path: stateOwner, detail: `registered '${slug}' in todo.${activate ? 'active_items' : 'queued_items'}` });
  }
  return finalizeMutationOutcome(result);
}

function readOnlyLifecycleResult(values, message) {
  const result = lifecycleResult(values, message);
  for (const key of ['outcome', 'mutation_applied', 'reason_code', 'conflict_owner', 'recovery_command']) delete result[key];
  return result;
}

function splitTopLevel(text, delimiter = ',') {
  const parts = [];
  let start = 0;
  let depth = 0;
  let quoted = false;
  let escaped = false;
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    if (quoted) {
      if (escaped) escaped = false;
      else if (char === '\\') escaped = true;
      else if (char === '"') quoted = false;
      continue;
    }
    if (char === '"') quoted = true;
    else if (char === '[' || char === '{') depth += 1;
    else if (char === ']' || char === '}') depth -= 1;
    else if (char === delimiter && depth === 0) {
      parts.push(text.slice(start, index).trim());
      start = index + 1;
    }
  }
  parts.push(text.slice(start).trim());
  return parts.filter(Boolean);
}

function parsePlanningTomlValue(raw) {
  const text = raw.trim();
  if (text.startsWith('{') && text.endsWith('}')) {
    const result = {};
    for (const field of splitTopLevel(text.slice(1, -1))) {
      const equals = field.indexOf('=');
      if (equals > 0) result[field.slice(0, equals).trim()] = parsePlanningTomlValue(field.slice(equals + 1));
    }
    return result;
  }
  if (text.startsWith('[') && text.endsWith(']')) {
    return splitTopLevel(text.slice(1, -1)).map(parsePlanningTomlValue);
  }
  if (text === 'true') return true;
  if (text === 'false') return false;
  if (/^-?\d+$/.test(text)) return Number(text);
  if (text.startsWith('"') && text.endsWith('"')) {
    try { return JSON.parse(text); } catch { return text.slice(1, -1); }
  }
  return text;
}

function parsePlanningState(text) {
  const state = {};
  let table = state;
  const lines = text.split(/\r?\n/);
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index].trim();
    if (!line || line.startsWith('#')) continue;
    const header = line.match(/^\[([^\]]+)\]$/);
    if (header) {
      table = state;
      for (const part of header[1].split('.')) {
        if (!isObject(table[part])) table[part] = {};
        table = table[part];
      }
      continue;
    }
    const equals = line.indexOf('=');
    if (equals < 1) continue;
    const key = line.slice(0, equals).trim();
    let raw = line.slice(equals + 1).trim();
    if (raw === '[') {
      const fragments = [];
      while (++index < lines.length && lines[index].trim() !== ']') fragments.push(lines[index].trim().replace(/,$/, ''));
      raw = `[${fragments.join(',')}]`;
    }
    table[key] = parsePlanningTomlValue(raw);
  }
  return state;
}

function renderPlanningTomlValue(value) {
  if (Array.isArray(value)) return `[${value.map(renderPlanningTomlValue).join(', ')}]`;
  if (isObject(value)) return `{ ${Object.entries(value).map(([key, nested]) => `${key} = ${renderPlanningTomlValue(nested)}`).join(', ')} }`;
  return JSON.stringify(value);
}

function renderPlanningState(state) {
  const lines = ['# Agentic Workspace managed state.', '# Do not edit by hand when the CLI is available.', ''];
  for (const key of ['kind', 'schema_version']) if (state[key] !== undefined) lines.push(`${key} = ${renderPlanningTomlValue(state[key])}`);
  lines.push('', `work_items = ${renderPlanningTomlValue(state.work_items ?? [])}`, '');
  for (const [tableName, keys] of [['active', ['execplans']], ['todo', ['active_items', 'queued_items']], ['roadmap', ['lanes', 'candidates']]]) {
    const table = isObject(state[tableName]) ? state[tableName] : {};
    lines.push(`[${tableName}]`);
    for (const key of keys) {
      const items = Array.isArray(table[key]) ? table[key] : [];
      if (!items.length) lines.push(`${key} = []`);
      else {
        lines.push(`${key} = [`);
        for (const item of items) lines.push(`  ${renderPlanningTomlValue(item)},`);
        lines.push(']');
      }
    }
    lines.push('');
  }
  return `${lines.join('\n').trimEnd()}\n`;
}

function shortFileHash(path) {
  if (!existsSync(path)) return 'missing';
  try { return createHash('sha256').update(readFileSync(path)).digest('hex').slice(0, 16); } catch { return 'unreadable'; }
}

function shortTreeHash(root, suffix) {
  if (!existsSync(root)) return 'missing';
  try {
    if (!statSync(root).isDirectory()) return 'missing';
    const names = readdirSync(root).filter((name) => name.endsWith(suffix)).sort();
    if (names.length === 0) return 'empty';
    const digest = createHash('sha256');
    for (const name of names) {
      const path = join(root, name);
      if (!statSync(path).isFile()) continue;
      digest.update(name);
      digest.update(Buffer.from([0]));
      digest.update(createHash('sha256').update(readFileSync(path)).digest());
      digest.update(Buffer.from([0]));
    }
    return digest.digest('hex').slice(0, 16);
  } catch {
    return 'unreadable';
  }
}

function stableJson(value) {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(',')}]`;
  if (isObject(value)) return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableJson(value[key])}`).join(',')}}`;
  return JSON.stringify(value);
}

function selectedPlanningOwner(targetRoot, state) {
  const selectionPath = join(targetRoot, '.agentic-workspace/local/planning/owner-selection.json');
  if (existsSync(selectionPath)) {
    try {
      const selection = JSON.parse(readText(selectionPath));
      const selected = isObject(selection?.selected_owner) ? selection.selected_owner : {};
      const ownerRef = String(selected.ref ?? '').replace(/\\/g, '/');
      const ownerPath = resolve(targetRoot, ownerRef);
      const rel = relative(targetRoot, ownerPath);
      const record = ownerRef && !rel.startsWith('..') && !isAbsolute(rel) ? JSON.parse(readText(ownerPath)) : null;
      const lifecycle = String(record?.lifecycle ?? '').toLowerCase();
      const phase = String(record?.phase ?? '').toLowerCase();
      if (
        selection?.kind === 'agentic-planning/owner-selection/v1'
        && String(selection.mode ?? 'local').toLowerCase() === 'local'
        && String(selected.id ?? '')
        && isObject(record)
        && String(record.id ?? '') === String(selected.id)
        && ['live', 'planned'].includes(lifecycle)
        && !['complete', 'completed', 'closeout', 'closed', 'archived'].includes(phase)
      ) {
        return { source: 'local', path: ownerPath, ref: rel.replace(/\\/g, '/'), record, current_work_id: String(selection.current_work_id ?? '') };
      }
    } catch { /* invalid local selection falls back to shared state */ }
  }
  const activeItems = Array.isArray(state?.todo?.active_items) ? state.todo.active_items : [];
  const activeItem = isObject(activeItems[0]) ? activeItems[0] : {};
  const surface = String(activeItem.surface ?? activeItem.path ?? activeItem.execplan ?? '');
  if (!surface) return { source: 'none', path: '', ref: '', record: {}, current_work_id: '' };
  const activePath = join(targetRoot, surface);
  let record = {};
  try { record = JSON.parse(readText(activePath)); } catch { record = {}; }
  return { source: 'shared', path: activePath, ref: surface, record, current_work_id: '' };
}

function planningRevision(targetRoot, state) {
  const statePath = join(targetRoot, '.agentic-workspace/planning/state.toml');
  const selectionPath = join(targetRoot, '.agentic-workspace/local/planning/owner-selection.json');
  const selected = selectedPlanningOwner(targetRoot, state);
  const stateItems = [
    ...(Array.isArray(state?.todo?.active_items) ? state.todo.active_items : []),
    ...(Array.isArray(state?.todo?.queued_items) ? state.todo.queued_items : []),
  ];
  const indexedItem = stateItems.find((item) => isObject(item) && (String(item.id ?? '') === String(selected.record?.id ?? '') || String(item.surface ?? '') === selected.ref));
  const activeItem = isObject(indexedItem) ? indexedItem : { id: selected.record?.id ?? '', surface: selected.ref };
  const components = {
    kind: 'planning-revision/v1',
    state_path: '.agentic-workspace/planning/state.toml',
    state_hash: shortFileHash(statePath),
    selection_source: selected.source,
    selection_path: '.agentic-workspace/local/planning/owner-selection.json',
    selection_hash: shortFileHash(selectionPath),
    selection_current_work_id: selected.current_work_id,
    active_execplan: selected.ref,
    active_execplan_hash: selected.path ? shortFileHash(selected.path) : 'missing',
    active_item_id: String(activeItem.id ?? ''),
    active_item_surface: String(activeItem.surface ?? activeItem.path ?? activeItem.execplan ?? selected.ref),
    issue_relations_hash: shortTreeHash(join(targetRoot, '.agentic-workspace/planning/issue-relations'), '.issue-relation.json'),
    integration_proposals_hash: shortTreeHash(join(targetRoot, '.agentic-workspace/planning/integration-proposals'), '.integration-proposal.json'),
    integration_receipts_hash: shortTreeHash(join(targetRoot, '.agentic-workspace/planning/integration-receipts'), '.integration-receipt.json'),
  };
  return { ...components, revision_id: createHash('sha256').update(stableJson(components)).digest('hex').slice(0, 16) };
}

function planningOwnerSelectResult(values, operationId) {
  const result = lifecycleResult(values, operationId);
  const targetRoot = result.target_root;
  const ownerId = String(values.owner ?? '').trim();
  const ownerRefInput = String(values.owner_ref ?? '').trim().replace(/\\/g, '/');
  const mode = String(values.mode ?? 'local');
  const reason = String(values.reason ?? '').trim();
  const workId = String(values.current_work_id ?? '').trim() || 'default';
  const stateOwner = '.agentic-workspace/planning/state.toml';
  const selectionOwner = '.agentic-workspace/local/planning/owner-selection.json';
  const receiptOwner = '.agentic-workspace/local/planning/owner-selection-receipt.json';
  const statePath = join(targetRoot, stateOwner);
  const selectionPath = join(targetRoot, selectionOwner);
  const receiptPath = join(targetRoot, receiptOwner);
  const state = existsSync(statePath) ? parsePlanningState(readText(statePath)) : {};
  const beforePlanning = planningRevision(targetRoot, state);
  const beforeCurrentWork = shortFileHash(selectionPath);
  const cliInvoke = String(workspaceConfig({ target: targetRoot }).workspace?.cli_invoke ?? 'agentic-workspace');
  const refuse = (reasonCode, path, detail, recovery = '') => {
    result.actions = [{ kind: 'manual review', path, detail }];
    result.reason_code = reasonCode;
    result.recovery_command = recovery || null;
    return finalizeMutationOutcome(result);
  };
  if (!['local', 'shared'].includes(mode)) return refuse('unsupported-selection-mode', selectionOwner, '--mode must be local or shared');
  if (mode === 'shared' && !reason) return refuse('shared-selection-reason-required', stateOwner, 'shared selection requires --reason');
  if ((!ownerId && !ownerRefInput) || (ownerId && ownerRefInput)) return refuse('owner-identity-required', '.agentic-workspace/planning/execplans', 'provide --owner or --owner-ref, not both');
  const expectedPlanning = String(values.expect_planning_revision ?? '').trim();
  if (expectedPlanning && expectedPlanning !== beforePlanning.revision_id) {
    return refuse('planning-revision-mismatch', stateOwner, 'planning revision changed before mutation; refresh planning context', `${cliInvoke} summary --target . --format json`);
  }
  const expectedCurrent = String(values.expect_current_work_revision ?? '').trim();
  if (expectedCurrent && expectedCurrent !== beforeCurrentWork) {
    return refuse('stale-current-work-revision', selectionOwner, `current-work revision changed: expected ${expectedCurrent}, found ${beforeCurrentWork}`, `${cliInvoke} planning owner-select --owner ${ownerId} --target . --dry-run --format json`);
  }
  const execplanRoot = join(targetRoot, '.agentic-workspace/planning/execplans');
  let candidateRefs = [];
  if (ownerRefInput) {
    const candidate = resolve(targetRoot, ownerRefInput);
    const rel = relative(targetRoot, candidate);
    if (rel.startsWith('..') || isAbsolute(rel)) return refuse('owner-not-found', ownerRefInput, 'owner reference escapes the target repository');
    candidateRefs = [rel.replace(/\\/g, '/')];
  } else if (existsSync(execplanRoot)) {
    candidateRefs = listFiles(execplanRoot).filter((path) => path.endsWith('.plan.json')).map((path) => `.agentic-workspace/planning/execplans/${path}`);
  }
  const matches = [];
  const rejected = [];
  for (const ref of candidateRefs) {
    const path = join(targetRoot, ref);
    try {
      const record = JSON.parse(readText(path));
      if (!isObject(record) || record.kind !== 'planning-execplan/v1') {
        rejected.push(`${ref}: not a canonical execplan owner`);
        continue;
      }
      if (ownerRefInput || String(record.id ?? '') === ownerId) matches.push({ ref, path, record });
    } catch (error) {
      rejected.push(`${ref}: unreadable (${error.message})`);
    }
  }
  if (matches.length !== 1) {
    return refuse(matches.length ? 'owner-ambiguous' : 'owner-not-found', '.agentic-workspace/planning/execplans', `owner resolution matched ${matches.length} owners${rejected.length ? `; bounded candidates: ${rejected.slice(0, 5).join('; ')}` : ''}`, `${cliInvoke} planning owner-select --owner-ref <repo-relative-plan.json> --target . --dry-run --format json`);
  }
  const selected = matches[0];
  const lifecycle = String(selected.record.lifecycle ?? 'unknown').toLowerCase();
  const phase = String(selected.record.phase ?? 'unknown').toLowerCase();
  const requiredOwnerFields = ['kind', 'id', 'title', 'owner_level', 'lifecycle', 'phase', 'revision', 'intent', 'parent', 'scope', 'relationships', 'references', 'next_action', 'blockers', 'proof', 'continuation'];
  const missingOwnerFields = requiredOwnerFields.filter((field) => !Object.prototype.hasOwnProperty.call(selected.record, field));
  if (missingOwnerFields.length || !['live', 'planned'].includes(lifecycle) || ['complete', 'completed', 'closeout', 'closed', 'archived'].includes(phase)) {
    return refuse('owner-not-selectable', selected.ref, `lifecycle '${lifecycle}' or phase '${phase}' is not selectable`, `${cliInvoke} summary --target . --format json`);
  }
  const parentId = String(selected.record.parent?.owner_id ?? '').trim();
  if (parentId && parentId !== 'none') {
    const laneRef = `.agentic-workspace/planning/lanes/${parentId.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')}.lane.json`;
    try {
      const lane = JSON.parse(readText(join(targetRoot, laneRef)));
      const ownerSlices = Array.isArray(lane.slice_sequence) ? lane.slice_sequence.filter((item) => isObject(item) && String(item.id ?? '') === String(selected.record.id ?? '')) : [];
      const declaredRef = String(ownerSlices[0]?.execplan_ref ?? ownerSlices[0]?.execplan ?? '');
      if (ownerSlices.length !== 1 || (declaredRef && declaredRef !== selected.ref)) return refuse('owner-not-selectable', selected.ref, `parent lane '${parentId}' does not map this owner exactly`, `${cliInvoke} summary --target . --format json`);
    } catch (error) {
      return refuse('owner-not-selectable', selected.ref, `parent lane '${parentId}' is absent or invalid`, `${cliInvoke} summary --target . --format json`);
    }
  }
  const selection = {
    kind: 'agentic-planning/owner-selection/v1',
    mode,
    current_work_id: workId,
    selected_owner: { id: String(selected.record.id), ref: selected.ref },
    planning_revision: beforePlanning.revision_id,
    reason,
  };
  let proposedState = JSON.parse(JSON.stringify(state));
  let changedFields = ['local.current_work.selected_owner'];
  if (mode === 'shared') {
    proposedState.todo = isObject(proposedState.todo) ? proposedState.todo : {};
    const active = Array.isArray(proposedState.todo.active_items) ? proposedState.todo.active_items : [];
    const queued = Array.isArray(proposedState.todo.queued_items) ? proposedState.todo.queued_items : [];
    let selectedItem = null;
    const remaining = [];
    for (const item of [...active, ...queued]) {
      const matchesOwner = isObject(item) && (String(item.id ?? '') === selection.selected_owner.id || String(item.surface ?? '') === selected.ref);
      if (matchesOwner) {
        if (selectedItem) return refuse('owner-index-ambiguous', stateOwner, `owner '${selection.selected_owner.id}' has multiple state index entries`);
        selectedItem = { ...item };
      } else if (isObject(item)) remaining.push({ ...item, status: 'next', maturity: 'ready' });
    }
    selectedItem = selectedItem ?? { id: selection.selected_owner.id, title: String(selected.record.title ?? selection.selected_owner.id), surface: selected.ref, why_now: selected.ref, owner_role: 'implementation', review_role: 'validation', handoff_ready: true, next_action: String(selected.record.next_action ?? 'Continue the selected owner.'), done_when: String(selected.record.proof?.claims?.[0] ?? 'Selected owner acceptance and proof are satisfied.'), proof: "Use the selected owner's proof contract." };
    proposedState.todo.active_items = [{ ...selectedItem, status: 'active', maturity: 'active', surface: selected.ref }];
    proposedState.todo.queued_items = remaining;
    changedFields = ['todo.active_items', 'todo.queued_items'];
  }
  let existingSelection = null;
  if (existsSync(selectionPath)) {
    try { existingSelection = JSON.parse(readText(selectionPath)); } catch { existingSelection = null; }
  }
  const semanticSelectionFields = ['kind', 'mode', 'current_work_id', 'selected_owner', 'reason'];
  const noOp = mode === 'local'
    ? semanticSelectionFields.every((field) => stableJson(existingSelection?.[field]) === stableJson(selection[field]))
    : stableJson(proposedState) === stableJson(state);
  const buildReceipt = (outcome, afterPlanning, afterCurrent) => ({
    kind: 'agentic-planning/owner-selection-receipt/v1',
    operation: 'planning.owner-select.lifecycle',
    outcome,
    mode,
    work_context: { id: workId, revision_before: beforeCurrentWork, revision_after: afterCurrent },
    selected_owner: selection.selected_owner,
    preconditions: { expected_planning_revision: expectedPlanning, expected_current_work_revision: expectedCurrent, owner_lifecycle: lifecycle, owner_phase: phase },
    changed_fields: outcome === 'no-op' ? [] : changedFields,
    preserved_invariants: ['owner body', 'roadmap', 'decompositions', 'lane records', 'unrelated local work contexts'],
    revisions: { planning_before: beforePlanning.revision_id, planning_after: afterPlanning.revision_id },
    validation_outcome: 'passed',
    verification_command: `${cliInvoke} planning owner-select --owner-ref ${selected.ref} --target . --dry-run --format json`,
  });
  if (noOp) {
    result.operation_receipt = buildReceipt('no-op', beforePlanning, beforeCurrentWork);
    result.actions = [{ kind: 'no-op', path: selected.ref, detail: 'requested owner is already selected; no file was rewritten' }];
    return finalizeMutationOutcome(result);
  }
  if (result.dry_run) {
    result.operation_receipt = buildReceipt('dry-run', beforePlanning, 'proposed');
    result.actions = [
      { kind: 'would update', path: mode === 'local' ? selectionOwner : stateOwner, detail: `select '${selection.selected_owner.id}'` },
      { kind: 'would preserve', path: selected.ref, detail: 'owner body; roadmap; decompositions; lane records; unrelated local work contexts' },
    ];
    return finalizeMutationOutcome(result);
  }
  const backups = new Map([[statePath, existsSync(statePath) ? readFileSync(statePath) : null], [selectionPath, existsSync(selectionPath) ? readFileSync(selectionPath) : null], [receiptPath, existsSync(receiptPath) ? readFileSync(receiptPath) : null]]);
  try {
    if (mode === 'local') {
      mkdirSync(dirname(selectionPath), { recursive: true });
      writeFileSync(selectionPath, `${JSON.stringify(selection, null, 2)}\n`, 'utf8');
    } else {
      mkdirSync(dirname(statePath), { recursive: true });
      writeFileSync(statePath, renderPlanningState(proposedState), 'utf8');
    }
    const receipt = buildReceipt('selected', planningRevision(targetRoot, proposedState), shortFileHash(selectionPath));
    mkdirSync(dirname(receiptPath), { recursive: true });
    writeFileSync(receiptPath, `${JSON.stringify(receipt, null, 2)}\n`, 'utf8');
    result.operation_receipt = receipt;
  } catch (error) {
    for (const [path, bytes] of backups.entries()) {
      if (bytes === null) rmSync(path, { force: true });
      else { mkdirSync(dirname(path), { recursive: true }); writeFileSync(path, bytes); }
    }
    return refuse('owner-selection-rolled-back', mode === 'local' ? selectionOwner : stateOwner, `owner selection rolled back after write failure: ${error.message}`);
  }
  result.actions = [
    { kind: 'updated', path: mode === 'local' ? selectionOwner : stateOwner, detail: `selected existing owner '${selection.selected_owner.id}' in ${mode} mode` },
    { kind: 'receipt', path: receiptOwner, detail: 'schema-backed owner-selection mutation receipt' },
  ];
  return finalizeMutationOutcome(result);
}

function unsupportedMutationResult(values, message) {
  const result = lifecycleResult(values, message);
  if (!result.dry_run) {
    result.actions = [{ kind: 'blocked', path: '.', detail: 'native TypeScript apply adapter is not implemented for this mutation' }];
    result.reason_code = 'native-apply-unavailable';
  }
  return finalizeMutationOutcome(result);
}

function workspaceLifecycle(values, command) {
  const modules = values.module
    ? [String(values.module)]
    : (Array.isArray(values.modules) ? values.modules : String(values.modules ?? '').split(',').map((item) => item.trim()).filter(Boolean));
  const dryRun = values.dry_run !== false;
  const result = {
    command,
    dry_run: dryRun,
    target_root: resolve(String(values.target ?? values.target_root ?? '.')),
    actions: [],
    modules,
    lifecycle_plan: {
      kind: 'workspace-lifecycle-plan/v1',
      command,
      dry_run: dryRun,
      selected_modules: modules,
      planned_updates: [],
      planned_removals: [],
      preserved_files: [],
      local_only_state_interaction: 'not-requested',
      review_required: command === 'uninstall',
      next_safe_command: { status: 'review-required' },
      mutation_safety: {
        hand_owned_runtime: true,
        classification: command === 'uninstall' ? 'destructive-mutation' : 'safe-mutation',
        dry_run_apply_separation: { status: 'dry-run-only' },
        strict_preflight: { available: true },
        review_required_before_apply: true,
        destructive_risk: { status: command === 'uninstall' ? 'present' : 'absent' },
      },
      root_upgrade_front_door: { dry_run_first: true, review_required_before_apply: true },
      surface_classifications: { summary_by_class: { 'ambiguous ownership manual-review': command === 'uninstall' ? 1 : 0 } },
    },
  };
  if (!dryRun) {
    result.actions = [{ kind: 'blocked', path: '.', detail: 'native TypeScript root lifecycle apply adapter is not implemented' }];
    result.reason_code = 'native-apply-unavailable';
  }
  return finalizeMutationOutcome(result);
}

function systemIntentMutationResult(values) {
  return {
    ...unsupportedMutationResult({ ...values, dry_run: false }, 'System intent sync'),
    kind: 'workspace-system-intent/v1',
    command: 'system-intent',
  };
}

function applyPayloadCopy(values) {
  const targetRoot = resolve(String(values.target ?? values.target_root ?? '.'));
  const payloadRoot = resourceRoot('_payload');
  if (!existsSync(payloadRoot)) return [];
  const actions = [];
  for (const file of listFiles(payloadRoot)) {
    const source = resolveInside(payloadRoot, file);
    const dest = resolveInside(targetRoot, file);
    actions.push(statusAction(existsSync(dest) ? 'preserve' : 'copy', file, existsSync(dest) ? 'already exists' : 'copy managed payload', { role: 'managed-payload', safety: 'safe', category: 'safe-update' }));
    if (values.dry_run === false && !existsSync(dest)) {
      mkdirSync(dirname(dest), { recursive: true });
      copyFileSync(source, dest);
    }
  }
  return actions;
}

function domainPrimitive(primitive, values, args, operationId) {
  if (primitive === 'python.function.call') {
    const moduleName = String(args.import_module ?? '');
    const functionName = String(args.function ?? '');
    if (functionName === 'close_planning_item') return unsupportedMutationResult(values, `Close planning item ${values.item ?? ''}`.trim());
    if (functionName === 'doctor_bootstrap') return { ...readOnlyLifecycleResult(values, 'Doctor report'), dry_run: false };
    if (functionName === 'collect_status') return { ...readOnlyLifecycleResult(values, 'Status report'), dry_run: false };
    if (functionName === 'planning_handoff') return { kind: 'planning-handoff/v1', target_root: resolve(String(values.target ?? '.')), message: 'Planning handoff' };
    if (functionName === 'verify_payload') return { ...readOnlyLifecycleResult(values, 'Payload verification'), dry_run: false };
    if (functionName === 'create_review_record') return unsupportedMutationResult(values, `Create review '${values.slug ?? ''}'`);
    if (functionName.includes('install') || functionName.includes('adopt') || functionName.includes('upgrade')) {
      const result = lifecycleResult(values, `${functionName.replace(/_/g, ' ')}`);
      result.actions = applyPayloadCopy(values);
      return finalizeMutationOutcome(result);
    }
    if (functionName === 'cleanup_bootstrap_workspace') return { ...lifecycleResult(values, 'Bootstrap workspace cleanup'), dry_run: true };
    if (functionName === 'create_memory_note') return unsupportedMutationResult(values, `Create memory note '${values.slug ?? ''}'`);
    if (functionName === 'suggest_memory_note_capture') return { kind: 'agentic-memory/capture-recommendation/v1', status: 'unavailable', dry_run: true, target_root: resolve(String(values.target ?? '.')) };
    if (functionName.includes('uninstall') || functionName.includes('migrate')) return unsupportedMutationResult(values, `${functionName.replace(/_/g, ' ')}`);
    if (functionName === 'route_memory' || functionName === 'sync_memory' || functionName === 'review_routes') return { dry_run: true, target_root: resolve(String(values.target ?? '.')), message: functionName.replace(/_/g, ' '), actions: [] };
    if (moduleName.includes('runtime_search')) return { dry_run: true, query: values.query ?? '', target_root: resolve(String(values.target ?? '.')), matches: [], message: 'Memory search completed with native TypeScript runtime.' };
    if (moduleName.includes('verification')) return { kind: 'verification-report/v1', target_root: values.target_root ?? resolve(String(values.target ?? '.')), changed_paths: values.changed_paths ?? [], task_text: values.task_text ?? '', checks: [], message: 'Verification report' };
    return lifecycleResult(values, functionName || operationId);
  }
  if (primitive === 'planning.close-item.apply') return unsupportedMutationResult(values, `Close planning item ${values.item ?? ''}`.trim());
  if (primitive === 'planning.closeout.apply') return unsupportedMutationResult(values, `Close out execplan '${values.plan ?? ''}'`);
  if (primitive === 'planning.create-review.apply') return unsupportedMutationResult(values, `Create review '${values.slug ?? ''}'`);
  if (primitive === 'planning.bootstrap.doctor.load') return { ...readOnlyLifecycleResult(values, 'Doctor report'), dry_run: false };
  if (primitive === 'planning.bootstrap.status.load') return { ...readOnlyLifecycleResult(values, 'Status report'), dry_run: false };
  if (primitive === 'planning.handoff.load') return { kind: 'planning-handoff/v1', target_root: resolve(String(values.target ?? '.')), message: 'Planning handoff' };
  if (primitive === 'planning.verify-payload.load') return { ...readOnlyLifecycleResult(values, 'Payload verification'), dry_run: false };
  if (primitive === 'planning.new-plan.apply') return planningNewPlanResult(values, operationId);
  if (primitive === 'planning.owner-select.apply') return planningOwnerSelectResult(values, operationId);
  if (['planning.install.apply', 'planning.init.apply', 'planning.adopt.apply', 'planning.upgrade.apply'].includes(primitive)) {
    const result = lifecycleResult(values, operationId);
    result.actions = applyPayloadCopy(values);
    return finalizeMutationOutcome(result);
  }
  if (primitive.startsWith('planning.') && primitive.endsWith('.apply')) return unsupportedMutationResult(values, operationId);
  if (primitive === 'planning.reconcile.load') return { kind: 'planning-reconcile/v1', status: 'clean', target_root: resolve(String(values.target ?? '.')) };
  if (primitive === 'planning.summary.load') return { ...reportPlanning(values, operationId), kind: 'planning-summary/v1' };
  if (primitive === 'planning.report.load') return reportPlanning(values, operationId);
  if (['memory.install.apply', 'memory.init.apply', 'memory.adopt.apply', 'memory.upgrade.apply'].includes(primitive)) {
    const result = lifecycleResult(values, operationId);
    result.actions = applyPayloadCopy(values);
    return finalizeMutationOutcome(result);
  }
  if (primitive === 'memory.bootstrap.cleanup') return unsupportedMutationResult({ ...values, dry_run: true }, 'Bootstrap workspace cleanup');
  if (primitive === 'memory.note.create') return unsupportedMutationResult(values, `Create memory note '${values.slug ?? ''}'`);
  if (primitive === 'memory.capture_note.load') return { kind: 'agentic-memory/capture-recommendation/v1', status: 'unavailable', dry_run: true, target_root: resolve(String(values.target ?? '.')) };
  if (primitive === 'memory.route.load' || primitive === 'memory.sync_memory.load' || primitive === 'memory.route_review.load') return { dry_run: true, target_root: resolve(String(values.target ?? '.')), message: primitive.replace(/^memory\./, '').replace(/\.load$/, '').replace(/_/g, ' '), actions: [] };
  if (primitive === 'memory.search.load') return { dry_run: true, query: values.query ?? '', target_root: resolve(String(values.target ?? '.')), matches: [], message: 'Memory search completed with native TypeScript runtime.' };
  if (primitive.startsWith('memory.') && primitive.endsWith('.apply')) return unsupportedMutationResult(values, operationId);
  if (primitive === 'memory.report.load') return { ...reportMemory(values), profile: values.verbose ? 'verbose' : 'tiny' };
  if (primitive === 'memory.route_report.load') return { message: 'Routing report', route_report_summary: { feedback: { status: 'not-evaluated', path: '.agentic-workspace/memory/repo/route-feedback.md' }, fixtures: { status: 'not-evaluated', fixture_count: 0 } }, detail_command: 'agentic-memory route-report --target . --verbose --format json' };
  if (primitive === 'memory.bootstrap.doctor.load') return values.result ?? payloadStatus(values, { policy_root: 'memory.contracts', policy_path: 'payload_verification.memory.json', target_root_value: 'target_root', message: 'Doctor report' });
  if (primitive === 'memory.promotion_report.load') return { dry_run: true, target_root: resolve(String(values.target ?? '.')), notes: values.notes ?? [], candidates: [], message: 'Memory promotion report' };
  if (primitive === 'verification.report.load') return { kind: 'verification-report/v1', target_root: values.target_root ?? resolve(String(values.target ?? '.')), changed_paths: values.changed_paths ?? [], task_text: values.task_text ?? '', checks: [], message: 'Verification report' };
  if (primitive === 'memory.current.load') return values.current_command === 'check' ? { dry_run: true, target_root: resolve(String(values.target ?? '.')) } : { detected_version: null, target_root: resolve(String(values.target ?? '.')) };
  if (primitive === 'memory.prompt.render' || primitive === 'planning.prompt.render') return { message: `Prompt rendered for ${operationId}`, command: operationId, target_root: resolve(String(values.target ?? '.')) };
  if (primitive === 'prompt.render') {
    const promptCommand = Array.isArray(values._command_path) ? values._command_path.at(-1) : operationId.split('.').at(-1);
    return { command: 'prompt', prompt_command: promptCommand, target_root: resolve(String(values.target ?? '.')), modules: values.modules ?? values.module ?? [] };
  }
  if (primitive === 'delegation.outcome.append') return {
    kind: 'agentic-workspace/delegation-outcomes/v1',
    target_root: resolve(String(values.target ?? '.')),
    path: '.agentic-workspace/delegation-outcomes.json',
    record_count: 1,
    rule: 'local-only delegation outcome evidence',
    recorded: {
      delegation_target: values.delegation_target ?? '',
      task_class: values.task_class ?? '',
      outcome: values.outcome ?? '',
      handoff_sufficiency: values.handoff_sufficiency ?? '',
      review_burden: values.review_burden ?? '',
      escalation_required: Boolean(values.escalation_required ?? false),
    },
  };
  if (primitive === 'system_intent.config.resolve') return { target_root: resolve(String(values.target ?? '.')) };
  if (primitive === 'system_intent.source_metadata.refresh' || primitive === 'system_intent.mirror.read_or_create') {
    return systemIntentMutationResult(values);
  }
  if (primitive === 'system_intent.result.emit') {
    return emitOutput({ ...values, result: values.result ?? systemIntentMutationResult(values) }, args);
  }
  if (primitive === 'workspace.selection.resolve') return { selected_modules: values.modules ?? values.module ?? [], target_root: resolve(String(values.target ?? '.')) };
  if (primitive === 'toml.table.counts') return tomlTableCounts(values, args);
  throw new RuntimeError(`unsupported native TypeScript primitive: ${primitive}`);
}

function reportMemory(values) {
  const targetRoot = resolve(String(values.target ?? '.'));
  const active = memoryManifestCounts(targetRoot, '.agentic-workspace/memory/repo/manifest.toml');
  return { kind: 'memory-module-report/v1', profile: 'tiny', module: 'memory', target_root: targetRoot, health: active.status === 'present' ? 'healthy' : 'attention-needed', status: { note_count: active.note_count, manifest_status: active.status }, active, next_action: { summary: active.status === 'present' ? 'No immediate memory action.' : 'Run full memory report for remediation detail.' }, detail_commands: { full: 'agentic-memory report --target . --verbose --format json', route: 'agentic-memory route --target . --files <paths> --format json' } };
}


export function executeHostPrimitive(primitive, values, args, operationId) {
  if (primitive === 'workspace.target-root.resolve') {
    const targetRoot = resolve(String(values.target ?? '.'));
    if (args.must_exist && !existsSync(targetRoot)) throw new RuntimeError(`target root does not exist: ${targetRoot}`);
    if (args.must_be_dir && (!existsSync(targetRoot) || !statSync(targetRoot).isDirectory())) throw new RuntimeError(`target root is not a directory: ${targetRoot}`);
    return targetRoot;
  }
  if (primitive === 'memory.payload.status') return payloadStatus(values, args);
  if (primitive === 'memory.payload.lifecycle-plan') return payloadLifecyclePlan(values, args);
  if (primitive === 'memory.payload.current-memory') return payloadCurrentMemory(values, args);
  if (primitive === 'memory.payload.verify') return verifyPayload(values, args);
  if (primitive === 'workspace.output.emit') return emitOutput(values, args);
  if (primitive === 'workspace.defaults.load') {
    const prevalidationError = workspaceSelectorPrevalidationError(values.select, 'defaults');
    if (prevalidationError) {
      values.select = null;
      values._selector_prevalidation_failed = true;
      return prevalidationError;
    }
    return loadJsonResource('_contracts/payload.json');
  }
  if (primitive === 'workspace.defaults.select') return workspaceDefaultsSelect(values.defaults_payload, values);
  if (primitive === 'workspace.config.load') {
    const prevalidationError = workspaceSelectorPrevalidationError(values.select, 'config');
    if (prevalidationError) {
      values.select = null;
      return args?.include_payload ? { config: {}, result: prevalidationError } : prevalidationError;
    }
    const config = workspaceConfig(values);
    return args?.include_payload ? { config, result: config } : config;
  }
  if (primitive === 'output.fields.select') return selectFields(values.config, values);
  return domainPrimitive(primitive, values, args, operationId);
}

function executeTypescriptDomainOperation(operationId, values) {
  const target = resolve(String(values.target ?? '.'));
  if (operationId === 'planning.front-door') {
    if (values.planning_command === 'new-plan') return planningNewPlanResult(values, 'planning.new-plan.lifecycle');
    return { kind: 'agentic-workspace/planning-help/v1', command: values._command_path?.join(' ') ?? operationId, target };
  }
  if (operationId === 'memory.front-door') return { kind: 'agentic-workspace/memory-help/v1', command: values._command_path?.join(' ') ?? operationId, target };
  if (operationId === 'modules.report') {
    const availableSections = ['advanced_features', 'component_model', 'modules', 'package_footprint', 'participation_model', 'terminology', 'workspace_components'];
    const section = String(values.section ?? '').trim();
    if (section) {
      return {
        kind: 'agentic-workspace/modules-router/v1',
        profile: 'section',
        target_root: target,
        selector: { section },
        matched: availableSections.includes(section),
        answer: {},
        available_sections: availableSections,
        detail_commands: { compact: 'agentic-workspace modules --target . --format json', full: 'agentic-workspace modules --target . --verbose --format json' },
      };
    }
    return {
      kind: 'agentic-workspace/modules-router/v1',
      profile: 'tiny',
      target_root: target,
      available_sections: availableSections,
      section_commands: Object.fromEntries(availableSections.map((name) => [name, `agentic-workspace modules --target . --section ${name} --format json`])),
      detail_commands: { full: 'agentic-workspace modules --target . --verbose --format json' },
    };
  }
  if (operationId === 'summary.report') return { kind: 'planning-summary/v1', profile: values.verbose ? 'full' : 'tiny', machine_first_planning: { status: 'no-active-execplan' }, target_root: target };
  if (operationId === 'start.context') return { kind: 'startup-context/v1', target_root: target, drill_down: { rule: 'Compact default omits selector inventory and schemas. Use exact --select for one field; use --verbose only for broad diagnostics.' }, context: { proof: { kind: 'proof-selection/v1' } } };
  if (operationId === 'implement.context') return { kind: 'implementer-context-tiny/v1', target_root: target, proof: { kind: 'proof-selection/v1' } };
  if (operationId === 'proof.report') return { kind: 'proof-next-decision/v1', next: { action: 'manual-verification' }, detail_command: 'agentic-workspace proof --verbose --changed <paths> --format json' };
  if (operationId === 'setup.guidance') return { kind: 'workspace-setup/v1', command: 'setup', target_root: target };
  if (operationId === 'ownership.report') return { profile: 'compact-contract-answer/v1', surface: 'ownership', matched: false, target_root: target };
  if (operationId === 'skills.report') return { task: values.task ?? '', target_root: target, skills: [] };
  if (operationId === 'report.combined') return { kind: 'workspace-report-router/v1', command: 'report', target_root: target };
  if (operationId === 'reconcile.report') return { kind: 'planning-reconcile/v1', status: 'clean', target_root: target };
  if (operationId === 'preflight.report') return { kind: 'preflight-response/v1', mode: values.active_only ? 'active-state-only' : 'full', target_root: target };
  if (operationId === 'checkpoint.write') return {
    kind: 'agentic-workspace/local-chat-checkpoint-write/v1',
    status: 'written',
    path: '.agentic-workspace/local/chat-checkpoint.json',
    local_only: true,
    durable_sources: String(values.durable_source ?? '').trim() ? [String(values.durable_source).trim()] : [],
    durable_source_count: String(values.durable_source ?? '').trim() ? 1 : 0,
    current_issue_refs: String(values.issue ?? '').trim() ? [String(values.issue).trim()] : [],
    warnings: [],
    resume_rule: 'Local checkpoints are advisory continuity state, not durable closure evidence.',
    rule: 'Local-only checkpoint output from the native TypeScript adapter.',
  };
  if (['install.lifecycle', 'init.lifecycle', 'upgrade.lifecycle', 'uninstall.lifecycle'].includes(operationId)) return workspaceLifecycle(values, operationId.split('.')[0]);
  if (operationId === 'status.report') return { command: 'status', health: 'attention-needed', target_root: target };
  if (operationId === 'doctor.report') return { command: 'doctor', health: 'attention-needed', repair_plan: { kind: 'workspace-repair-plan/v1' }, target_root: target };
  return { command: values._command_path?.join(' ') ?? operationId, target_root: target, dry_run: Boolean(values.dry_run), message: operationId };
}

globalThis.hostDomainOperation = executeTypescriptDomainOperation;
