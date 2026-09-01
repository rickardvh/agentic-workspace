// Generated target-local host primitive support module.
// Source: src/agentic_workspace/contracts/command_package_ir.json
// Host primitive support: src/agentic_workspace/contracts/typescript_primitive_support.mjs
// Regenerate with: uv run python scripts/generate/generate_command_packages.py
// DO NOT EDIT DIRECTLY.

// AW-owned TypeScript host primitive support.
// Command-generation owns the generated runtime shell; this module owns
// Agentic Workspace primitive behavior that is copied into generated packages.

import {
  copyFileSync,
  existsSync,
  mkdtempSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  rmSync,
  statSync,
  writeFileSync,
  writeSync,
} from 'node:fs';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { dirname, isAbsolute, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';

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

// Generated TypeScript command output replaces this compatibility template
// from the canonical Python metadata in workspace_selector_validation.py.
const WORKSPACE_SELECTOR_DESCRIPTORS = {
  "config": [
    "workspace",
    "workspace.enabled",
    "workspace.enabled_source",
    "workspace.enabled_modules",
    "workspace.improvement_latitude",
    "workspace.optimization_bias",
    "workspace.optimization_bias_source",
    "workspace.workflow_obligations",
    "workspace.agent_instructions_file",
    "workspace.workflow_obligation_ids",
    "warnings",
    "target",
    "config_path",
    "modules",
    "mixed_agent",
    "mixed_agent.runtime_resolution",
    "mixed_agent.effective_orchestration",
    "mixed_agent.assignment_policy",
    "mixed_agent.target_identity",
    "mixed_agent.correction_feedback",
    "mixed_agent.target_evidence",
    "mixed_agent.assignment_decision",
    "local_runtime",
    "local_runtime.assignment_policy",
    "assurance",
    "config_enforcement",
    "config_effect_audit",
    "cli_compatibility",
    "selector_inventory"
  ],
  "defaults": [
    "kind",
    "answer",
    "answer.command",
    "section",
    "sections",
    "startup",
    "startup.canonical_doc",
    "root_cli_authority",
    "root_cli_authority.command",
    "workspace",
    "proof_selection",
    "improvement_intake",
    "optimization_bias",
    "selector_inventory"
  ],
  "summary": [
    "todo",
    "todo.active_count",
    "target_root",
    "planning_revision",
    "planning_record",
    "planning_record.proof_report",
    "planning_record.completion_gate",
    "execplans",
    "planning_surface_health",
    "execution_readiness",
    "current_execution_pressure",
    "continuation_view",
    "continuation_view.proof_state",
    "continuation_view.claim_boundary",
    "continuation_view.source_freshness",
    "fresh_session_digest",
    "decision_packet",
    "decision_point_carry_status",
    "planning_route_decision",
    "closeout_trust_inspection",
    "decomposition",
    "lanes",
    "residue_governance",
    "roadmap",
    "detail_commands",
    "warning_count",
    "memory_consult",
    "memory_decision_packet",
    "selector_inventory"
  ],
  "proof": [
    "planning_route_decision",
    "proof_route_strategy_decision",
    "proof_route_escalation_gate",
    "proof_route_strategy_preservation",
    "proof_route_strategy_claim_gate",
    "proof_route_strategy_consumer_gate",
    "proof_receipt_reconciliation",
    "proof_receipt_bridge",
    "proof_closeout_summary",
    "intent_proof",
    "proof_narrowness",
    "proof_decision",
    "proof_route_maintenance",
    "learned_proof_route_model",
    "proof_next_decision",
    "proof_obligations",
    "proof_command_tiers",
    "architecture_principles",
    "verification",
    "requirement_grounding",
    "test_strategy_check",
    "validation_plan",
    "generated_cli_freshness",
    "cli_authority_review",
    "required_commands",
    "selected_lanes",
    "selected_commands",
    "manual_verification",
    "next",
    "sufficiency",
    "route_refinement_required",
    "manual_proof_obligations",
    "focused_route_coverage_audit",
    "release_proof_profile",
    "domain_proof_route_inventory_audit",
    "completion_options",
    "selector_inventory"
  ]
};

const WORKSPACE_DEPRECATED_SELECTOR_REPLACEMENTS = {
  config: {
    'workspace.feature_tier': 'workspace.enabled_modules',
  },
  proof: {
    'target_proof_capabilities': 'proof_next_decision',
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
    exit_status: 2,
    exit_class: 'usage-or-validation-error',
    safe_to_retry: true,
    mutation_occurred: false,
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
    corrected_action: inventoryCommand,
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

function workspaceSelectorReplacementCommand(sourceCommand, selectors, replacements) {
  const corrected = [...new Set(selectors.map((selector) => replacements[selector] ?? selector))];
  return `agentic-workspace ${sourceCommand} --target . --select ${corrected.join(',')} --format json`;
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
    exit_status: 2,
    exit_class: 'usage-or-validation-error',
    safe_to_retry: true,
    mutation_occurred: false,
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
    corrected_action: inventoryCommand,
  };
  if (Object.keys(replacementSelectors).length) {
    const replacementCommand = workspaceSelectorReplacementCommand(sourceCommand, request.selectors, replacementSelectors);
    payload.deprecated_selectors = Object.keys(replacementSelectors);
    payload.replacement_selectors = replacementSelectors;
    payload.replacement_command = replacementCommand;
    payload.corrected_action = replacementCommand;
    payload.replacement_rule = 'Deprecated selectors are rejected atomically with their exact current selector and copyable replacement command.';
  }
  return fitWorkspaceSelectorError(payload);
}

function selectWorkspacePayload(payload, values, sourceCommand) {
  const request = workspaceSelectorRequest(values.select, sourceCommand);
  if (!request.selectors.length) return payload;
  if (request.selectors.length === 1 && request.selectors[0] === 'selector_inventory') {
    const selectors = WORKSPACE_SELECTOR_DESCRIPTORS[sourceCommand] ?? [];
    return {
      kind: 'agentic-workspace/selected-output/v1',
      source_command: sourceCommand,
      values: {
        selector_inventory: {
          kind: 'agentic-workspace/selector-inventory/v1',
          source_command: sourceCommand,
          available_count: selectors.length,
          selectors,
          rule: 'Explicit selector inventory is available through --select selector_inventory; validation errors include only a bounded sample.',
        },
      },
    };
  }
  const valuesBySelector = {};
  const missing = [];
  for (const selector of request.selectors) {
    let current = payload;
    for (const part of selector.split('.').filter(Boolean)) current = isObject(current) ? current[part] : undefined;
    if (current === undefined) missing.push(selector);
    else valuesBySelector[selector] = current;
  }
  const selected = { kind: 'agentic-workspace/selected-output/v1', source_command: sourceCommand, values: valuesBySelector };
  if (missing.length) selected.missing = missing;
  return selected;
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
  const unavailable = (selector) => ({
    kind: 'agentic-workspace/config-projection-unavailable/v1',
    status: 'unavailable-in-generated-typescript-host',
    selector,
    continuation: `agentic-workspace config --target . --select ${selector} --format json`,
    rule: 'The selector is valid and executable; this generated host reports typed unavailability when it cannot reproduce Python host-owned runtime evidence.',
  });
  return {
    kind: 'agentic-workspace/config/v1',
    profile: 'tiny',
    exists: false,
    target_root: targetRoot,
    config_path: configPath.replace(/\\/g, '/'),
    local_config_path: join(targetRoot, '.agentic-workspace/config.local.toml').replace(/\\/g, '/'),
    config_present: existsSync(configPath),
    local_config_present: existsSync(join(targetRoot, '.agentic-workspace/config.local.toml')),
    target: targetRoot,
    warnings: [],
    modules: enabledModules,
    workspace: {
      enabled: true,
      enabled_source: 'generated-typescript-default',
      cli_invoke: String(config.cli_invoke ?? 'uv run agentic-workspace'),
      enabled_modules: enabledModules,
      agent_instructions_file: String(config.agent_instructions_file ?? 'AGENTS.md'),
      workflow_obligation_ids: [],
      workflow_obligations: [],
      improvement_latitude: String(config.improvement_latitude ?? 'report_only'),
      optimization_bias: String(config.optimization_bias ?? 'balanced'),
      optimization_bias_source: 'resolved-config',
    },
    mixed_agent: {
      runtime_resolution: unavailable('mixed_agent.runtime_resolution'),
      effective_orchestration: unavailable('mixed_agent.effective_orchestration'),
      assignment_policy: unavailable('mixed_agent.assignment_policy'),
      target_identity: unavailable('mixed_agent.target_identity'),
      correction_feedback: unavailable('mixed_agent.correction_feedback'),
      target_evidence: unavailable('mixed_agent.target_evidence'),
      assignment_decision: unavailable('mixed_agent.assignment_decision'),
    },
    local_runtime: {
      status: 'unavailable-in-generated-typescript-host',
      assignment_policy: unavailable('local_runtime.assignment_policy'),
    },
    assurance: unavailable('assurance'),
    config_enforcement: unavailable('config_enforcement'),
    config_effect_audit: unavailable('config_effect_audit'),
    cli_compatibility: unavailable('cli_compatibility'),
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
  const ownerSelectionPath = join(result.target_root, '.agentic-workspace/local/planning/owner-selection.json');
  let preservedCurrentWorkId = 'default';
  if (existsSync(ownerSelectionPath)) {
    try {
      const priorSelection = JSON.parse(readText(ownerSelectionPath));
      if (priorSelection?.kind === 'agentic-planning/owner-selection/v1') {
        preservedCurrentWorkId = String(priorSelection.current_work_id ?? '').trim() || 'default';
      }
    } catch { /* invalid prior selection uses deterministic initialization */ }
  }
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
    if (activate) result.actions.push({ kind: 'would update', path: '.agentic-workspace/local/planning/owner-selection.json', detail: `select '${slug}' for local work context '${preservedCurrentWorkId}'` });
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
  if (activate) {
    mkdirSync(dirname(ownerSelectionPath), { recursive: true });
    writeFileSync(ownerSelectionPath, `${JSON.stringify({
      kind: 'agentic-planning/owner-selection/v1',
      mode: 'local',
      current_work_id: preservedCurrentWorkId,
      selected_owner: { id: slug, ref: owner },
      planning_revision: planningRevision(result.target_root, state).revision_id,
      reason: source || `Selected owner ${slug} for current work.`,
    }, null, 2)}\n`, 'utf8');
  }
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

function shortTreeHashRecursive(root, suffix) {
  if (!existsSync(root)) return 'missing';
  try {
    if (!statSync(root).isDirectory()) return 'missing';
    const paths = [];
    const walk = (dir) => {
      const names = readdirSync(dir).sort();
      for (const name of names) {
        const path = join(dir, name);
        const stat = statSync(path);
        if (stat.isDirectory()) {
          walk(path);
        } else if (stat.isFile() && name.endsWith(suffix)) {
          paths.push(relative(root, path).replace(/\\/g, '/'));
        }
      }
    };
    walk(root);
    if (paths.length === 0) return 'empty';
    const digest = createHash('sha256');
    for (const rel of paths.sort()) {
      const path = join(root, rel);
      digest.update(rel);
      digest.update(Buffer.from([0]));
      digest.update(createHash('sha256').update(readFileSync(path)).digest());
      digest.update(Buffer.from([0]));
    }
    return digest.digest('hex').slice(0, 16);
  } catch {
    return 'unreadable';
  }
}

function planningTargetAuthorityRevision(targetRoot) {
  const components = {
    kind: 'planning-target-authority-revision/v1',
    state_path: '.agentic-workspace/planning/state.toml',
    state_hash: shortFileHash(join(targetRoot, '.agentic-workspace/planning/state.toml')),
    execplans_hash: shortTreeHashRecursive(join(targetRoot, '.agentic-workspace/planning/execplans'), '.plan.json'),
    lanes_hash: shortTreeHashRecursive(join(targetRoot, '.agentic-workspace/planning/lanes'), '.lane.json'),
    decompositions_hash: shortTreeHashRecursive(join(targetRoot, '.agentic-workspace/planning/decompositions'), '.decomposition.json'),
    issue_relations_hash: shortTreeHash(join(targetRoot, '.agentic-workspace/planning/issue-relations'), '.issue-relation.json'),
  };
  return { ...components, revision_id: createHash('sha256').update(stableJson(components)).digest('hex').slice(0, 16) };
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
    target_authority_revision: planningTargetAuthorityRevision(targetRoot).revision_id,
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
      next_safe_command: { status: command === 'uninstall' ? 'review-required' : 'ready' },
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
  if (primitive === 'planning.targeted-write.apply') {
    const apply = values.apply === true;
    const rejectedPreflight = apply && String(values.preflight_token ?? '').startsWith('preflight-v1:');
    return {
      ...lifecycleResult(values, operationId),
      status: rejectedPreflight ? 'caller-preflight-token-rejected' : 'ambiguous-or-missing-owner',
      preflight_admission: rejectedPreflight ? { status: 'caller-preflight-token-rejected' } : { status: 'not-requested' },
    };
  }
  if (primitive === 'planning.issue-shape.apply') return {
    ...lifecycleResult(values, operationId),
    operation_receipt: { outcome: values.dry_run === false ? 'applied' : 'dry-run' },
  };
  if (primitive === 'planning.integration-propose.apply') return {
    ...lifecycleResult(values, operationId),
    operation_receipt: { outcome: values.dry_run === false ? 'proposed' : 'dry-run' },
  };
  if (primitive === 'planning.integration-apply.apply') return {
    ...lifecycleResult(values, operationId),
    operation_receipt: { outcome: 'integrated' },
  };
  if (['planning.install.apply', 'planning.init.apply', 'planning.adopt.apply', 'planning.upgrade.apply'].includes(primitive)) {
    const result = lifecycleResult(values, operationId);
    result.actions = applyPayloadCopy(values);
    return finalizeMutationOutcome(result);
  }
  if (primitive.startsWith('planning.') && primitive.endsWith('.apply')) return unsupportedMutationResult(values, operationId);
  if (primitive === 'planning.reconcile.load') return { kind: 'planning-reconcile/v1', status: 'clean', target_root: resolve(String(values.target ?? '.')) };
  if (primitive === 'planning.summary.load') {
    const prevalidationError = workspaceSelectorPrevalidationError(values.select, 'summary');
    if (prevalidationError) return prevalidationError;
    const payload = { ...reportPlanning(values, operationId), kind: 'planning-summary/v1' };
    return selectWorkspacePayload(payload, values, 'summary');
  }
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
  if (primitive === 'config.policy.apply') return applyWorkspaceConfigPolicy(values);
  if (primitive === 'system_intent.config.resolve') return { target_root: resolve(String(values.target ?? '.')) };
  if (primitive === 'system_intent.source_metadata.refresh' || primitive === 'system_intent.mirror.read_or_create') {
    return systemIntentMutationResult(values);
  }
  if (primitive === 'system_intent.result.emit') {
    return emitOutput({ ...values, result: values.result ?? systemIntentMutationResult(values) }, args);
  }
  if (primitive === 'evaluation.definition.register') return {
    kind: 'agentic-workspace/evaluations/v1',
    evaluation_id: values.evaluation_id ?? '',
    outcome: 'registered',
    question: values.question ?? '',
    subject: values.subject ?? '',
    criteria: values.criteria ?? [],
    decision_owner: values.decision_owner ?? '',
    evidence_sources: values.evidence_sources ?? [],
    report_sinks: values.report_sinks ?? [],
  };
  if (primitive === 'evaluation.observation.append') return {
    kind: 'agentic-workspace/evaluation-observation/v1',
    evaluation_id: values.evaluation_id ?? '',
    criterion: values.criterion ?? '',
    result: values.result ?? '',
    evidence_ref: values.evidence_ref ?? '',
    notes: values.notes ?? '',
  };
  if (primitive === 'evaluation.status.derive') return {
    kind: 'agentic-workspace/evaluation-summary/v1',
    status: 'not-evaluated',
    evaluation_id: values.evaluation_id ?? '',
    observations: [],
  };
  if (primitive === 'evaluation.lifecycle.transition') return {
    kind: 'agentic-workspace/evaluation-definition/v1',
    evaluation_id: values.evaluation_id ?? '',
    status: values.status ?? 'active',
    transition_reason: values.reason ?? '',
  };
  if (primitive === 'workspace.selection.resolve') return { selected_modules: values.modules ?? values.module ?? [], target_root: resolve(String(values.target ?? '.')) };
  if (primitive === 'assignment.lifecycle.apply') return assignmentLifecycleApply(values, operationId);
  if (primitive === 'correction.event.apply') return correctionEventApply(values, operationId);
  if (primitive === 'guidance.lifecycle.apply') return guidanceLifecycleApply(values, operationId);
  if (primitive === 'instructions.execute') return instructionsExecute(values, operationId);
  if (primitive === 'toml.table.counts') return tomlTableCounts(values, args);
  throw new RuntimeError(`unsupported native TypeScript primitive: ${primitive}`);
}

function assignmentText(value) {
  return value === undefined || value === null ? '' : String(value).trim();
}

function assignmentFragment(value) {
  return assignmentText(value).replace(/[^A-Za-z0-9_.-]+/g, '-').replace(/^[.-]+|[.-]+$/g, '') || 'assignment-run';
}

function assignmentStableStringify(value) {
  if (Array.isArray(value)) return `[${value.map((item) => assignmentStableStringify(item)).join(',')}]`;
  if (isObject(value)) {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${assignmentStableStringify(value[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

function assignmentDigest(value) {
  return `sha256:${createHash('sha256').update(assignmentStableStringify(value ?? {})).digest('hex')}`;
}

function assignmentParseJson(value, field) {
  if (isObject(value) || Array.isArray(value)) return value;
  const text = assignmentText(value);
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch (error) {
    throw new RuntimeError(`assignment lifecycle ${field} must be valid JSON`);
  }
}

function assignmentWrite(path, payload) {
  mkdirSync(dirname(path), { recursive: true });
  const text = typeof payload === 'string' ? payload : JSON.stringify(payload, null, 2);
  writeFileSync(path, `${text.trimEnd()}\n`, 'utf8');
}

function assignmentReadJsonRef(targetRoot, ref, field, failures) {
  if (!assignmentText(ref)) {
    failures.push({ reason: 'missing-current-authority', field, recovery: 'Resolve the current AW-owned authority ref and retry.' });
    return {};
  }
  try {
    const payload = readJson(resolveInside(targetRoot, ref));
    return isObject(payload) ? payload : {};
  } catch (_error) {
    failures.push({ reason: 'missing-current-authority', field, recovery: `Create or refresh ${ref} before continuing.` });
    return {};
  }
}

function assignmentPlanningRef(values, assignmentId) {
  return assignmentText(values.planning_assignment_ref ?? values.assignment_ref) || `.agentic-workspace/planning/assignments/${assignmentFragment(assignmentId)}.assignment.json`;
}

function assignmentLiveMutationBaseline(targetRoot) {
  const git = spawnSync('git', ['rev-parse', 'HEAD'], { cwd: targetRoot, encoding: 'utf8' });
  if (git.status === 0 && assignmentText(git.stdout)) return assignmentText(git.stdout);
  const baselinePath = resolveInside(targetRoot, '.agentic-workspace/planning/mutation-baseline.json');
  if (!existsSync(baselinePath)) return '';
  try {
    const payload = readJson(baselinePath);
    return assignmentText(payload.current_baseline ?? payload.live_mutation_baseline ?? payload.baseline);
  } catch (_error) {
    return '';
  }
}

function assignmentCurrentRunState(runId, state, planningAssignment) {
  const attempt = isObject(planningAssignment.current_attempt) ? planningAssignment.current_attempt : {};
  if (assignmentText(attempt.run_id) && assignmentText(attempt.run_id) !== runId) return { status: 'superseded', run_id: runId, current_run_id: attempt.run_id };
  return { status: assignmentText(state.current_state) || assignmentText(attempt.status) || 'awaiting-admission', run_id: runId, owner: attempt.owner };
}

function assignmentCurrentAuthorities(targetRoot, values, state, runId, failures) {
  const assignmentId = assignmentText(values.assignment_id ?? state.assignment_id);
  if (!assignmentId) {
    failures.push({ reason: 'missing-current-authority', field: 'assignment_id', recovery: 'Retry with the stable assignment id so AW can resolve Planning authority.' });
    return {};
  }
  const planningRef = assignmentPlanningRef(values, assignmentId);
  const planning = assignmentReadJsonRef(targetRoot, planningRef, 'planning_assignment_ref', failures);
  if (!Object.keys(planning).length) return {};
  if (planning.kind !== 'agentic-workspace/planning-assignment/v1') failures.push({ reason: 'invalid-current-authority', field: 'planning_assignment_ref.kind', recovery: 'Regenerate the checked-in Planning assignment record.' });
  if (assignmentText(planning.assignment_id) !== assignmentId) failures.push({ reason: 'assignment-id-mismatch', field: 'planning_assignment_ref.assignment_id', recovery: 'Retry with the assignment id owned by the Planning assignment record.' });
  const assignmentGate = isObject(planning.assignment_gate) ? planning.assignment_gate : {};
  const assignmentPolicy = isObject(planning.assignment_policy) ? planning.assignment_policy : {};
  const delegationDecision = isObject(planning.delegation_decision) ? planning.delegation_decision : {};
  const identity = assignmentIdentity({ assignment_gate: assignmentGate, assignment_policy: assignmentPolicy, delegation_decision: delegationDecision });
  const currentRevision = assignmentText(planning.current_revision) || assignmentText(identity.revision);
  if (assignmentText(values.assignment_revision) && assignmentText(values.assignment_revision) !== currentRevision) failures.push({ reason: 'assignment-revision-mismatch', field: 'assignment_revision', recovery: 'Refresh from the current checked-in Planning assignment revision.' });
  if (['superseded', 'closed', 'archived'].includes(assignmentText(planning.status))) failures.push({ reason: 'assignment-not-current', field: 'planning_assignment_ref.status', recovery: 'Reassign or reopen a current Planning assignment before continuing.' });
  const proofRef = assignmentText(planning.structural_proof_receipt_ref);
  const proof = assignmentReadJsonRef(targetRoot, proofRef, 'planning_assignment_ref.structural_proof_receipt_ref', failures);
  const liveMutationBaseline = assignmentLiveMutationBaseline(targetRoot);
  if (!liveMutationBaseline) failures.push({ reason: 'missing-current-authority', field: 'live_mutation_baseline', recovery: 'Record an AW mutation baseline file or run inside a Git checkout before admission.' });
  return {
    assignment_gate: assignmentGate,
    assignment_policy: assignmentPolicy,
    delegation_decision: delegationDecision,
    structural_proof_receipt: proof,
    live_mutation_baseline: liveMutationBaseline,
    run_state: assignmentCurrentRunState(runId, state, planning),
    planning_assignment_ref: planningRef,
    proof_receipt_ref: proofRef,
  };
}

function assignmentIdentity(authorities) {
  const gate = authorities.assignment_gate ?? {};
  const policy = authorities.assignment_policy ?? {};
  const decision = authorities.delegation_decision ?? {};
  const scope = isObject(gate.scope) ? gate.scope : {};
  const nextStep = isObject(decision.delegation_next_step) ? decision.delegation_next_step : {};
  const proof = isObject(gate.proof_obligation) ? gate.proof_obligation : isObject(nextStep.proof_obligation) ? nextStep.proof_obligation : {};
  const identity = {
    target: gate.selected_target ?? null,
    target_identity_ref: gate.target_identity_ref ?? gate.selected_target ?? null,
    target_revision: gate.target_revision ?? null,
    task_class: gate.task_class ?? null,
    scope_class: gate.scope_class ?? scope.scope_class ?? null,
    plan_ref: gate.plan_ref ?? nextStep.plan_ref ?? null,
    plan_revision: gate.plan_revision ?? nextStep.plan_revision ?? null,
    slice_id: gate.slice_id ?? nextStep.slice_id ?? null,
    slice_revision: gate.slice_revision ?? nextStep.slice_revision ?? null,
    required_next_action: gate.required_next_action ?? null,
    gate_status: gate.status ?? null,
    assignment_policy: gate.assignment_policy ?? null,
    assignment_decision_revision: gate.assignment_decision_revision ?? null,
    manual_transport_policy: String((isObject(policy.manual_transport_policy) ? policy.manual_transport_policy.value : null) ?? 'allowed'),
    delegation_decision: decision.decision ?? null,
    handoff_run_id: nextStep.handoff_run_id ?? null,
    role: nextStep.role ?? gate.role ?? null,
    allowed_effects: gate.allowed_effects ?? nextStep.allowed_effects ?? [],
    allowed_paths: gate.allowed_paths ?? scope.allowed_paths ?? nextStep.allowed_paths ?? [],
    return_schema: nextStep.return_schema ?? 'delegated-return/v1',
    proof_obligation_id: proof.id ?? null,
    proof_obligation_revision: proof.revision ?? null,
    stop_conditions: gate.stop_conditions ?? nextStep.stop_conditions ?? [],
    mutation_baseline: gate.mutation_baseline ?? nextStep.mutation_baseline ?? null,
    return_admission_owner: 'delegated-return.admit',
    human_intent: gate.human_intent ?? nextStep.human_intent ?? gate.task ?? gate.task_class ?? null,
    required_inputs: gate.required_inputs ?? nextStep.required_inputs ?? [],
    prohibited_effects: gate.prohibited_effects ?? nextStep.prohibited_effects ?? ['scope-widening', 'merge', 'closeout', 'proof-authority', 'human-authority'],
    dispatch_adapter: isObject(gate.dispatch_adapter) ? gate.dispatch_adapter : {},
    claim_authority: { worker_result: 'evidence-only', proof: 'orchestrator-owned', integration: 'orchestrator-owned', completion: 'orchestrator-owned' },
  };
  const required = ['target', 'target_identity_ref', 'task_class', 'scope_class', 'plan_ref', 'plan_revision', 'slice_id', 'slice_revision', 'assignment_decision_revision', 'handoff_run_id', 'role', 'allowed_effects', 'allowed_paths', 'return_schema', 'proof_obligation_id', 'proof_obligation_revision', 'stop_conditions', 'mutation_baseline'];
  identity.missing_required_fields = required.filter((key) => Array.isArray(identity[key]) ? !identity[key].length : !assignmentText(identity[key]));
  identity.complete = identity.missing_required_fields.length === 0;
  identity.revision = assignmentDigest(identity);
  return identity;
}

function assignmentReturnForState(state, targetRoot, runDir, returnId) {
  const returns = isObject(state.returns) ? state.returns : {};
  const meta = isObject(returns[returnId]) ? returns[returnId] : {};
  const artifactRef = assignmentText(meta.artifact_ref);
  if (!artifactRef) throw new RuntimeError('assignment return has not been imported');
  const path = resolveInside(targetRoot, artifactRef);
  const rel = relative(runDir, path);
  if (rel.startsWith('..') || isAbsolute(rel)) throw new RuntimeError('assignment return artifact is outside the assignment run');
  return readJson(path);
}

function assignmentAdmitWithCurrentAuthority(authorities, returned) {
  const failures = [];
  for (const [field, value] of Object.entries({
    assignment_gate: authorities.assignment_gate,
    assignment_policy: authorities.assignment_policy,
    delegation_decision: authorities.delegation_decision,
    structural_proof_receipt: authorities.structural_proof_receipt,
  })) {
    if (!isObject(value) || !Object.keys(value).length) failures.push({ reason: 'missing-current-authority', field: `current_authorities.${field}`, recovery: 'Resolve the current assignment/run/proof/baseline authorities and retry admission.' });
  }
  if (!assignmentText(authorities.live_mutation_baseline)) failures.push({ reason: 'missing-current-authority', field: 'current_authorities.live_mutation_baseline', recovery: 'Resolve the current assignment/run/proof/baseline authorities and retry admission.' });
  const identity = assignmentIdentity(authorities);
  if (!identity.complete) failures.push({ reason: 'incomplete-assignment-identity', field: 'assignment_identity', recovery: 'Regenerate the assignment with all required identity fields.' });
  const proof = isObject(authorities.structural_proof_receipt) ? authorities.structural_proof_receipt : {};
  if (proof.kind !== 'agentic-workspace/assignment-structural-proof-receipt/v1' || proof.result !== 'passed' || proof.verified_by !== 'aw' || assignmentText(proof.assignment_revision) !== assignmentText(identity.revision)) failures.push({ reason: 'assignment-structural-proof-missing-or-stale', field: 'current_authorities.structural_proof_receipt', recovery: 'Prepare the current assignment again so AW can seal its structural identity.' });
  const runState = isObject(authorities.run_state) ? authorities.run_state : {};
  if (['duplicate', 'malformed', 'superseded', 'closed'].includes(assignmentText(runState.status))) failures.push({ reason: 'return-run-not-awaiting-admission', field: 'current_authorities.run_state', recovery: 'Import a fresh return or route repair/reassignment.' });
  if (assignmentText(returned.assignment_revision) !== assignmentText(identity.revision)) failures.push({ reason: 'stale-assignment-revision', field: 'assignment_revision', recovery: 'Refresh the handoff and resubmit against the current assignment revision.' });
  if (assignmentText(returned.target) !== assignmentText(identity.target)) failures.push({ reason: 'target-mismatch', field: 'target', recovery: 'Return work from the selected assignment target only.' });
  if (assignmentText(returned.run_id) !== assignmentText(runState.run_id)) failures.push({ reason: 'return-run-mismatch', field: 'run_id', recovery: 'Return work for the current assignment run only.' });
  if (Array.isArray(returned.stop_conditions_hit) && returned.stop_conditions_hit.length) failures.push({ reason: 'stop-condition-hit', field: 'stop_conditions_hit', recovery: 'Route the reported stop condition before integration.' });
  if (assignmentText(authorities.live_mutation_baseline) !== assignmentText(identity.mutation_baseline)) failures.push({ reason: 'mutation-baseline-mismatch', field: 'live_mutation_baseline', recovery: 'Rebase or regenerate the returned work against the current baseline.' });
  if (identity.role === 'implementer' && !String(returned.patch ?? '').trim()) failures.push({ reason: 'missing-implementation-patch', field: 'patch', recovery: 'Return the proposed unified diff required by the implementer assignment contract.' });
  const allowed = new Set(Array.isArray(identity.allowed_paths) ? identity.allowed_paths : []);
  const changed = Array.isArray(returned.changed_paths) ? returned.changed_paths : [];
  if (!allowed.size) failures.push({ reason: 'missing-canonical-scope', field: 'assignment_identity.allowed_paths', recovery: 'Refresh the assignment so AW can compare returned paths.' });
  for (const path of changed) {
    if (!allowed.has(path)) failures.push({ reason: 'scope-escape', field: 'changed_paths', recovery: 'Repair returned work to stay inside the assigned scope.' });
  }
  for (const path of assignmentPatchPaths(assignmentText(returned.patch))) {
    if (!allowed.has(path)) failures.push({ reason: 'returned-patch-outside-assignment-scope', field: 'patch', recovery: 'Return a unified diff touching only the assignment allowed paths.' });
  }
  return { admitted: failures.length === 0, status: failures.length ? 'rejected' : 'admitted', failures, assignment_revision: identity.revision, assignment_identity: identity, current_authority: { planning_assignment: authorities.planning_assignment_ref, structural_proof_receipt: proof, proof_source: authorities.proof_receipt_ref, mutation_baseline: authorities.live_mutation_baseline, baseline_source: 'host-resolved:git-or-aw-baseline' }, rule: 'Returned delegated work is executable only after AW re-resolves current assignment/run identity, transport authority, canonical scope, structural proof, stop conditions, and baseline immediately before admission.' };
}

function diffGitPathTokens(line) {
  const value = String(line ?? '').slice('diff --git '.length);
  const tokens = [];
  let offset = 0;
  while (tokens.length < 2) {
    while (value[offset] === ' ') offset += 1;
    if (offset >= value.length) return [];
    const start = offset;
    if (value[offset] === '"') {
      offset += 1;
      let escaped = false;
      let closed = false;
      while (offset < value.length) {
        const character = value[offset];
        offset += 1;
        if (escaped) escaped = false;
        else if (character === '\\') escaped = true;
        else if (character === '"') {
          closed = true;
          break;
        }
      }
      if (!closed) return [];
    } else {
      while (offset < value.length && value[offset] !== ' ') offset += 1;
    }
    tokens.push(value.slice(start, offset));
  }
  while (value[offset] === ' ') offset += 1;
  return offset === value.length ? tokens : [];
}

export function assignmentPatchPaths(patchText) {
  const paths = new Set();
  const addPath = (rawValue) => {
    let value = String(rawValue ?? '').split('\t', 1)[0].trim();
    if (!value || value === '/dev/null') return;
    if (value.startsWith('"') && value.endsWith('"')) value = value.slice(1, -1).replaceAll('\\"', '"').replaceAll('\\\\', '\\');
    if (value.startsWith('a/') || value.startsWith('b/')) value = value.slice(2);
    if (value) paths.add(value);
  };
  for (const line of String(patchText ?? '').split(/\r?\n/)) {
    if (line.startsWith('+++ ') || line.startsWith('--- ')) addPath(line.slice(4));
    else if (line.startsWith('rename from ') || line.startsWith('rename to ')) addPath(line.split(' ').slice(2).join(' '));
    else if (line.startsWith('copy from ') || line.startsWith('copy to ')) addPath(line.split(' ').slice(2).join(' '));
    else if (line.startsWith('diff --git ')) {
      for (const path of diffGitPathTokens(line)) addPath(path);
    }
  }
  return [...paths].sort();
}

function assignmentIndexedTaskProof(targetRoot, receiptRef, failures) {
  const storeRoot = resolveInside(targetRoot, '.agentic-workspace/proof/receipts');
  const ref = assignmentText(receiptRef);
  let receiptId = '';
  let receiptPath = '';
  if (ref.startsWith('proof://receipts/')) {
    receiptId = ref.split('/').at(-1) ?? '';
    if (!/^[A-Za-z0-9_.-]+$/.test(receiptId)) return {};
    receiptPath = resolveInside(storeRoot, `${receiptId}.json`);
  } else {
    receiptPath = resolveInside(targetRoot, ref);
    const withinStore = relative(storeRoot, receiptPath);
    if (withinStore.startsWith('..') || isAbsolute(withinStore) || !withinStore.endsWith('.json')) return {};
    receiptId = withinStore.replaceAll('\\', '/').split('/').at(-1).replace(/\.json$/, '');
  }
  try {
    const receipt = readJson(receiptPath);
    const index = readJson(resolveInside(storeRoot, 'index.json'));
    const entry = isObject(index.receipts) && isObject(index.receipts[receiptId]) ? index.receipts[receiptId] : {};
    const indexedPath = assignmentText(entry.path) ? resolveInside(storeRoot, assignmentText(entry.path)) : '';
    if (index.kind !== 'agentic-workspace/trusted-producer-receipt-index/v1' || indexedPath !== receiptPath || !['current', 'fresh', 'accepted'].includes(assignmentText(entry.status) || 'current') || entry.superseded_by) return {};
    if (entry.producer_class !== 'aw-proof' || receipt.producer_class !== 'aw-proof' || assignmentText(entry.revision) !== assignmentText(receipt.revision) || assignmentText(entry.source_ref) !== assignmentText(receipt.source_ref) || assignmentText(receipt.receipt_id) !== receiptId) return {};
    return receipt;
  } catch (_error) {
    failures.push({ reason: 'assignment-task-proof-not-producer-owned', field: 'task_proof_receipt_ref', recovery: 'Supply the current proof:// receipt resolved through the AW proof producer index.' });
    return {};
  }
}

function assignmentTaskProofSufficient(receipt) {
  const command = assignmentText(receipt.command);
  const recordedAt = assignmentText(receipt.recorded_at);
  const changed = Array.isArray(receipt.changed_paths) ? receipt.changed_paths.map(String) : [];
  const unresolved = /<[^<>\r\n]+>|\{\{[^{}\r\n]+\}\}|\$\{[^{}\r\n]+\}/;
  const timestampValid = /(?:Z|[+-]\d{2}:\d{2})$/.test(recordedAt) && !Number.isNaN(Date.parse(recordedAt));
  return receipt.kind === 'agentic-workspace/proof-receipt/v1' && command && !unresolved.test(command) && receipt.result === 'passed' && timestampValid && changed.length > 0 && changed.every((path) => assignmentText(path) && !unresolved.test(String(path))) && receipt.authority === 'aw-proof' && receipt.producer_class === 'aw-proof' && receipt.assignment_proof_obligation?.kind === 'agentic-workspace/assignment-task-proof-obligation/v1' && receipt.assignment_proof_binding === assignmentTaskProofBinding(receipt);
}

function assignmentTaskProofBinding(receipt) {
  const subject = isObject(receipt.proof_subject) ? receipt.proof_subject : {};
  return assignmentDigest({ assignment_proof_obligation: receipt.assignment_proof_obligation, proof_subject_fingerprint: subject.fingerprint, command: receipt.command, result: receipt.result, changed_paths: Array.isArray(receipt.changed_paths) ? [...receipt.changed_paths].map(String).sort() : [], authority: receipt.authority, producer_class: receipt.producer_class });
}

function assignmentDispatch(packet, prompt, targetRoot, transport) {
  const identity = isObject(packet.assignment_identity) ? packet.assignment_identity : {};
  const adapter = isObject(identity.dispatch_adapter) ? identity.dispatch_adapter : {};
  const methods = new Set(Array.isArray(adapter.execution_methods) ? adapter.execution_methods.map(String) : []);
  if (!methods.has(transport)) return { status: 'blocked', reason: 'transport-not-admitted-by-target' };
  const variants = Array.isArray(adapter.transports) ? adapter.transports.filter(isObject) : [];
  const selectedVariant = variants.find((item) => assignmentText(item.method) === transport);
  const variantKind = assignmentText(selectedVariant?.kind);
  const adapterKind = selectedVariant ? (['process', 'api'].includes(variantKind) ? 'process' : variantKind === 'internal' ? 'host-native' : '') : assignmentText(adapter.kind);
  const commandTemplate = Array.isArray(selectedVariant?.command) ? selectedVariant.command.map(String) : Array.isArray(adapter.command) ? adapter.command.map(String) : [];
  const outputMode = assignmentText(selectedVariant?.output_mode) || assignmentText(adapter.output_mode) || 'stdout';
  const timeoutSeconds = Number(selectedVariant?.timeout_seconds ?? adapter.timeout_seconds ?? 1800);
  if (!['process', 'host-native'].includes(adapterKind) || !commandTemplate.length) return { status: 'blocked', reason: 'configured-dispatch-adapter-unavailable' };
  if (!['stdout', 'json-file'].includes(outputMode)) return { status: 'blocked', reason: 'configured-dispatch-output-mode-unsupported' };
  if (!Number.isInteger(timeoutSeconds) || timeoutSeconds <= 0) return { status: 'blocked', reason: 'configured-dispatch-timeout-invalid' };
  const temporaryDirectory = mkdtempSync(join(tmpdir(), 'aw-assignment-dispatch-'));
  const outputFile = join(temporaryDirectory, 'last-message.json');
  const outputSchema = join(temporaryDirectory, 'delegated-return.schema.json');
  const required = ['assignment_revision', 'run_id', 'target', 'changed_paths', 'summary', 'stop_conditions_hit', ...(identity.role === 'implementer' ? ['patch'] : [])];
  writeFileSync(outputSchema, JSON.stringify({ type: 'object', properties: { assignment_revision: { type: 'string' }, run_id: { type: 'string' }, target: { type: 'string' }, changed_paths: { type: 'array', items: { type: 'string' } }, summary: { type: 'string' }, stop_conditions_hit: { type: 'array', items: { type: 'string' } }, patch: { type: 'string' } }, required, additionalProperties: false }), 'utf8');
  const replacements = { '{target_root}': targetRoot, '{output_schema}': outputSchema, '{output_file}': outputFile, '{model}': assignmentText(adapter.model) };
  const command = commandTemplate.map((part) => Object.entries(replacements).reduce((value, [placeholder, replacement]) => value.replaceAll(placeholder, replacement), part)).filter(Boolean);
  const result = spawnSync(command[0], command.slice(1), { cwd: targetRoot, encoding: 'utf8', input: prompt, timeout: timeoutSeconds * 1000 });
  let returned = {};
  try {
    let output = outputMode === 'json-file' && existsSync(outputFile) ? readText(outputFile).trim() : assignmentText(result.stdout);
    if (output.startsWith('```json') && output.endsWith('```')) output = output.slice(7, -3).trim();
    returned = JSON.parse(output);
  } catch (_error) {
    returned = {};
  } finally {
    rmSync(temporaryDirectory, { recursive: true, force: true });
  }
  if (result.status !== 0 || !isObject(returned) || (identity.role === 'implementer' && !assignmentText(returned.patch))) returned = {};
  return { kind: 'agentic-workspace/assignment-dispatch-receipt/v1', status: Object.keys(returned).length ? 'returned' : 'blocked', reason: Object.keys(returned).length ? 'worker-returned-untrusted-evidence' : 'target-adapter-return-invalid', transport, adapter_kind: adapterKind, adapter_revision: assignmentDigest({ kind: adapterKind, command: commandTemplate, output_mode: outputMode, timeout_seconds: timeoutSeconds }), model: adapter.model ?? null, exit_code: result.status, returned_work: returned, claim_boundary: 'transport-only; return still requires AW admission, integration, proof, and closeout' };
}

function assignmentLifecycleApply(values, operationId) {
  const transition = assignmentText(values.assignment_command) || String(operationId).split('.').at(-1);
  const targetRoot = resolve(String(values.target_root ?? values.target ?? '.'));
  const assignmentId = assignmentText(values.assignment_id);
  const assignmentRevision = assignmentText(values.assignment_revision);
  const seed = assignmentId || assignmentRevision ? `${assignmentId}:${assignmentRevision}:${transition}` : transition;
  let canonicalRunId = assignmentText(values.run_id);
  if (!canonicalRunId && assignmentId) {
    try {
      const planning = readJson(resolveInside(targetRoot, assignmentPlanningRef(values, assignmentId)));
      canonicalRunId = assignmentText(isObject(planning.current_attempt) ? planning.current_attempt.run_id : '');
    } catch (_error) {
      canonicalRunId = '';
    }
  }
  const runId = canonicalRunId || `run-${createHash('sha256').update(seed).digest('hex').slice(0, 12)}`;
  const runDir = resolveInside(resolveInside(targetRoot, '.agentic-workspace/local/assignment-runs'), assignmentFragment(runId));
  const statePath = resolveInside(runDir, 'state.json');
  const state = existsSync(statePath) ? readJson(statePath) : {};
  const failures = [];
  const artifactPaths = [];
  const writes = new Map();
  const requireField = (field) => {
    const value = assignmentText(values[field]);
    if (!value) failures.push({ reason: 'missing-required-input', field, recovery: `Retry assignment ${transition} with --${field.replaceAll('_', '-')}.` });
    return value;
  };
  const artifact = (relativePath) => resolveInside(runDir, relativePath);
  if (transition === 'export' || transition === 'dispatch') {
    const id = requireField('assignment_id');
    if (!id && assignmentText(values.task)) failures.push({ reason: 'native-assignment-materialization-unavailable', field: 'assignment_id', recovery: 'Materialize the live assignment through the Python AW host, then retry the TypeScript export with its assignment id and revision.' });
    const rev = assignmentRevision;
    const authorities = assignmentCurrentAuthorities(targetRoot, values, state, runId, failures);
    const identity = assignmentIdentity(authorities);
    if (rev && identity.revision !== rev) failures.push({ reason: 'assignment-revision-mismatch', field: 'assignment_revision', recovery: 'Export from the current Planning assignment identity revision.' });
    const targetName = assignmentText(values.target_name) || assignmentText(identity.target);
    if (!targetName) failures.push({ reason: 'missing-required-input', field: 'target_name', recovery: 'Retry assignment export with a current Planning assignment target.' });
    const transport = assignmentText(values.transport) || 'manual';
    if (transition === 'dispatch' && transport === 'manual') failures.push({ reason: 'automatic-transport-required', field: 'transport', recovery: 'Use assignment export for manual handoff or retry dispatch with an authorized automatic transport.' });
    const effectivePacket = { kind: 'agentic-workspace/assignment-export-packet/v1', assignment_id: id, assignment_revision: identity.revision, run_id: runId, target: targetName, transport, scope: identity.allowed_paths ?? [], assignment_identity: identity, authority_refs: { planning_assignment: authorities.planning_assignment_ref, structural_proof_receipt: authorities.proof_receipt_ref, mutation_baseline: 'host-resolved:git-or-aw-baseline' }, return_contract: { required_fields: ['assignment_revision', 'run_id', 'target', 'changed_paths', 'summary', 'stop_conditions_hit', ...(identity.role === 'implementer' ? ['patch'] : [])], worker_proof_authority: false, worker_completion_authority: false } };
    const packetPath = artifact('export/packet.json');
    const promptPath = artifact('export/prompt.md');
    const manifestPath = artifact('export/manifest.json');
    artifactPaths.push(packetPath, promptPath, manifestPath);
    writes.set(packetPath, effectivePacket);
    const prompt = `You are receiving an Agentic Workspace assignment packet. Do not edit the host checkout. For repo-write assignments, return the proposed unified diff in a patch field. The patch must be a complete git-compatible unified diff beginning with diff --git; generate or verify it with diff tooling so hunk counts are exact, and never use apply_patch markers, ellipses, placeholder @@ markers, or omitted context.\n\n\`\`\`json\n${JSON.stringify(effectivePacket, null, 2)}\n\`\`\``;
    writes.set(promptPath, prompt);
    writes.set(manifestPath, { kind: 'agentic-workspace/assignment-export-manifest/v1', assignment_id: id, assignment_revision: rev, run_id: runId, integrity: assignmentDigest(effectivePacket) });
    Object.assign(state, { assignment: effectivePacket, planning_assignment_ref: authorities.planning_assignment_ref, structural_proof_receipt_ref: authorities.proof_receipt_ref, current_state: 'handoff-prepared', run_id: runId, assignment_id: id });
    if (transport !== 'manual' && !failures.length) {
      const dispatch = assignmentDispatch(effectivePacket, prompt, targetRoot, transport);
      const dispatchPath = artifact('dispatch/receipt.json');
      artifactPaths.push(dispatchPath);
      writes.set(dispatchPath, dispatch);
      if (dispatch.status !== 'returned' || !isObject(dispatch.returned_work) || !Object.keys(dispatch.returned_work).length) failures.push({ reason: dispatch.reason ?? 'automatic-dispatch-failed', field: 'transport', recovery: 'Repair the configured target adapter or use admitted manual transport.' });
      else {
        const returned = dispatch.returned_work;
        const requiredReturnFields = ['assignment_revision', 'run_id', 'target', 'changed_paths', 'summary', 'stop_conditions_hit', ...(identity.role === 'implementer' ? ['patch'] : [])];
        const missingReturnFields = requiredReturnFields.filter((field) => !(field in returned));
        if (missingReturnFields.length) failures.push({ reason: 'malformed-return', field: `returned_work.${missingReturnFields.join(',')}`, recovery: 'Repair the configured target adapter so it returns every required contract field.' });
        if (identity.role === 'implementer' && Array.isArray(returned.changed_paths) && returned.changed_paths.length && !String(returned.patch ?? '').trim()) failures.push({ reason: 'malformed-return', field: 'returned_work.patch', recovery: 'Repair the configured target adapter so implementer returns include a non-empty unified diff.' });
        else if (identity.role === 'implementer' && String(returned.patch ?? '').trim() && !assignmentPatchPaths(String(returned.patch ?? '')).length) failures.push({ reason: 'malformed-return', field: 'returned_work.patch', recovery: 'Repair the configured target adapter so the patch is a complete git-compatible unified diff.' });
        else if (identity.role === 'implementer' && String(returned.patch ?? '').trim()) {
          const patchCheck = spawnSync('git', ['apply', '--check', '-'], { cwd: targetRoot, input: String(returned.patch ?? ''), encoding: 'utf8' });
          if (patchCheck.status !== 0) failures.push({ reason: 'malformed-return', field: 'returned_work.patch', recovery: 'Repair the configured target adapter so the patch applies cleanly to the current checkout.', detail: assignmentText(patchCheck.stderr) });
        }
        if (assignmentText(returned.assignment_revision) !== assignmentText(identity.revision)) failures.push({ reason: 'return-revision-mismatch', field: 'returned_work.assignment_revision', recovery: 'Return work for the exported assignment revision only.' });
        if (assignmentText(returned.run_id) !== runId || assignmentText(returned.target) !== targetName) failures.push({ reason: 'return-identity-mismatch', field: 'returned_work.run_id|target', recovery: 'Return work for the exported run and selected target only.' });
        if (!failures.length) {
          const returnId = assignmentDigest(returned).replace('sha256:', '').slice(0, 16);
          const returnPath = artifact(`received/awaiting-admission/${returnId}.json`);
          artifactPaths.push(returnPath);
          writes.set(returnPath, returned);
          state.returns = { [returnId]: { artifact_ref: relative(targetRoot, returnPath).replaceAll('\\', '/'), integrity: assignmentDigest(returned), state: 'received/awaiting-admission' } };
          Object.assign(state, { current_state: 'awaiting-admission', last_return_id: returnId });
        }
      }
    }
  } else if (transition === 'import') {
    requireField('run_id');
    const returned = assignmentParseJson(requireField('return_json'), 'return_json');
    const returnId = assignmentText(values.return_id) || assignmentDigest(returned).replace('sha256:', '').slice(0, 16);
    const assignment = isObject(state.assignment) ? state.assignment : {};
    const identity = isObject(assignment.assignment_identity) ? assignment.assignment_identity : {};
    const requiredReturnFields = ['assignment_revision', 'run_id', 'target', 'changed_paths', 'summary', 'stop_conditions_hit', ...(identity.role === 'implementer' ? ['patch'] : [])];
    const missingReturnFields = requiredReturnFields.filter((field) => !(field in returned));
    if (missingReturnFields.length) failures.push({ reason: 'malformed-return', field: `return_json.${missingReturnFields.join(',')}`, recovery: 'Return every required field from the exported return contract.' });
    if (identity.role === 'implementer' && Array.isArray(returned.changed_paths) && returned.changed_paths.length && !String(returned.patch ?? '').trim()) failures.push({ reason: 'malformed-return', field: 'return_json.patch', recovery: 'Return a non-empty unified diff when an implementer reports changed paths.' });
    if (assignmentText(returned.run_id) !== runId) failures.push({ reason: 'return-run-mismatch', field: 'return_json.run_id', recovery: 'Return work for the exported assignment run only.' });
    if (!Array.isArray(returned.changed_paths) || !Array.isArray(returned.stop_conditions_hit)) failures.push({ reason: 'malformed-return', field: 'return_json.changed_paths|stop_conditions_hit', recovery: 'Return changed_paths and stop_conditions_hit as JSON arrays.' });
    if (assignment.assignment_revision && assignmentText(returned.assignment_revision) !== assignmentText(assignment.assignment_revision)) failures.push({ reason: 'assignment-revision-mismatch', field: 'return_json.assignment_revision', recovery: 'Return work generated from the current exported assignment packet.' });
    const returnPath = artifact(`received/awaiting-admission/${assignmentFragment(returnId)}.json`);
    const receiptPath = artifact(`received/import-${assignmentFragment(returnId)}.json`);
    artifactPaths.push(returnPath, receiptPath);
    writes.set(returnPath, returned);
    writes.set(receiptPath, { kind: 'agentic-workspace/assignment-return-import-receipt/v1', run_id: runId, return_id: returnId, state: 'received/awaiting-admission', rule: 'Import records returned work only.' });
    state.returns = isObject(state.returns) ? state.returns : {};
    state.returns[returnId] = { artifact_ref: relative(targetRoot, returnPath).replaceAll('\\\\', '/'), integrity: assignmentDigest(returned), state: 'received/awaiting-admission' };
    Object.assign(state, { current_state: 'awaiting-admission', last_return_id: returnId });
  } else if (transition === 'admit') {
    requireField('run_id');
    const returnId = assignmentText(values.return_id) || assignmentText(state.last_return_id) || 'unidentified-return';
    let returned = {};
    try {
      returned = assignmentReturnForState(state, targetRoot, runDir, returnId);
    } catch (error) {
      failures.push({ reason: 'missing-return', field: 'return_id', recovery: 'Import returned work before admission.' });
    }
    const authorities = assignmentCurrentAuthorities(targetRoot, values, state, runId, failures);
    const admission = assignmentAdmitWithCurrentAuthority(authorities, returned);
    if (!admission.admitted) failures.push(...admission.failures);
    const receiptPath = artifact(`admission/${assignmentFragment(returnId)}.admit.json`);
    artifactPaths.push(receiptPath);
    writes.set(receiptPath, { kind: 'agentic-workspace/assignment-admission-receipt/v1', run_id: runId, return_id: returnId, status: admission.admitted ? 'admitted' : 'rejected', admission, worker_reported_proof_trusted: false, worker_reported_baseline_trusted: false });
    Object.assign(state, { current_state: admission.admitted ? 'admitted' : 'rejected', last_admission_status: admission.admitted ? 'admitted' : 'rejected', last_admission: admission, last_return_id: returnId });
  } else if (transition === 'integrate') {
    requireField('run_id');
    const returnId = assignmentText(values.return_id) || assignmentText(state.last_return_id) || 'unidentified-return';
    let returned = {};
    try {
      returned = assignmentReturnForState(state, targetRoot, runDir, returnId);
    } catch (error) {
      failures.push({ reason: 'missing-return', field: 'return_id', recovery: 'Import returned work before integration.' });
    }
    const authorities = assignmentCurrentAuthorities(targetRoot, values, state, runId, failures);
    const admission = assignmentAdmitWithCurrentAuthority(authorities, returned);
    if (!admission.admitted) failures.push(...admission.failures);
    if (state.last_admission_status !== 'admitted') failures.push({ reason: 'return-not-admitted', field: 'state.last_admission_status', recovery: 'Run assignment admit with current authority before integration.' });
    const patch = String(returned.patch ?? '');
    if (!failures.length && patch && !Boolean(values.dry_run)) {
      const integrationPatchPath = artifact('integration/returned.patch');
      mkdirSync(dirname(integrationPatchPath), { recursive: true });
      writeFileSync(integrationPatchPath, patch, 'utf8');
      artifactPaths.push(integrationPatchPath);
      const applied = spawnSync('git', ['apply', '--recount', integrationPatchPath], { cwd: targetRoot, encoding: 'utf8' });
      if (applied.status !== 0) failures.push({ reason: 'assignment-patch-apply-failed', field: 'returned_work.patch', recovery: 'Repair the returned unified diff against the current mutation baseline and retry integration.' });
    }
    const receiptPath = artifact('integration/integration.json');
    artifactPaths.push(receiptPath);
    writes.set(receiptPath, { kind: 'agentic-workspace/assignment-integration-receipt/v1', run_id: runId, status: failures.length ? 'blocked' : 'integrated', admission });
    Object.assign(state, { current_state: failures.length ? 'blocked' : 'integrated' });
  } else if (transition === 'close') {
    requireField('run_id');
    const priorState = assignmentText(state.current_state);
    if (priorState !== 'integrated') failures.push({ reason: 'assignment-run-not-integrated', field: 'state.current_state', recovery: 'Admit and integrate the current return before closing the assignment.' });
    const planningRef = assignmentPlanningRef(values, assignmentId || assignmentText(state.assignment_id));
    const planning = assignmentReadJsonRef(targetRoot, planningRef, 'planning_assignment_ref', failures);
    const currentAttempt = isObject(planning.current_attempt) ? planning.current_attempt : {};
    if (assignmentText(currentAttempt.run_id) && assignmentText(currentAttempt.run_id) !== runId) failures.push({ reason: 'return-run-mismatch', field: 'planning_assignment_ref.current_attempt.run_id', recovery: 'Close only the current assignment run.' });
    const taskProofRef = requireField('task_proof_receipt_ref');
    const taskProof = assignmentIndexedTaskProof(targetRoot, taskProofRef, failures);
    if (!Object.keys(taskProof).length && !failures.some((failure) => failure.reason === 'assignment-task-proof-not-producer-owned')) failures.push({ reason: 'assignment-task-proof-not-producer-owned', field: 'task_proof_receipt_ref', recovery: 'Supply the current proof:// receipt resolved through the AW proof producer index.' });
    const expected = isObject(planning.assignment_gate?.proof_obligation) ? planning.assignment_gate.proof_obligation : {};
    const observed = isObject(taskProof.assignment_proof_obligation) ? taskProof.assignment_proof_obligation : {};
    if (assignmentStableStringify(expected) !== assignmentStableStringify(observed)) failures.push({ reason: 'assignment-proof-obligation-mismatch', field: 'task_proof_receipt_ref.assignment_proof_obligation', recovery: 'Supply the passed AW proof receipt sealed for this exact assignment obligation.' });
    if (!assignmentTaskProofSufficient(taskProof)) failures.push({ reason: 'assignment-task-proof-not-admitted', field: 'task_proof_receipt_ref', recovery: 'Run AW proof for the integrated assignment and supply its admitted passed receipt.' });
    const expectedPaths = new Set(Array.isArray(planning.assignment_gate?.allowed_paths) ? planning.assignment_gate.allowed_paths.map(String) : []);
    const provedPaths = new Set(Array.isArray(taskProof.changed_paths) ? taskProof.changed_paths.map(String) : []);
    if (!expectedPaths.size || [...expectedPaths].some((path) => !provedPaths.has(path))) failures.push({ reason: 'assignment-proof-scope-mismatch', field: 'task_proof_receipt_ref.changed_paths', recovery: 'Record proof covering every allowed path in the integrated assignment.' });
    const receiptPath = artifact('closeout/close.json');
    artifactPaths.push(receiptPath);
    writes.set(receiptPath, { kind: 'agentic-workspace/assignment-closeout-receipt/v1', run_id: runId, status: failures.length ? 'blocked' : 'closed', task_proof_receipt_ref: taskProofRef });
    if (!failures.length) {
      planning.status = 'closed';
      planning.current_attempt = { ...(isObject(planning.current_attempt) ? planning.current_attempt : {}), status: 'closed' };
      planning.closeout = { run_id: runId, receipt_ref: relative(targetRoot, receiptPath).replaceAll('\\', '/'), task_proof_receipt_ref: taskProofRef };
      writes.set(resolveInside(targetRoot, planningRef), planning);
      Object.assign(state, { current_state: 'closed' });
    } else Object.assign(state, { current_state: priorState });
  } else if (transition === 'override') {
    requireField('assignment_id');
    requireField('reason');
    requireField('scope');
    requireField('expires_at');
    const receiptPath = artifact('override/override.json');
    artifactPaths.push(receiptPath);
    writes.set(receiptPath, { kind: 'agentic-workspace/assignment-human-override-receipt/v1', assignment_id: assignmentId, run_id: runId, status: 'override-recorded', scope: assignmentText(values.scope), reason: assignmentText(values.reason), expires_at: assignmentText(values.expires_at), revalidation_required: true, claim_effect: 'downgrade-until-revalidated', proof_effect: 'explicit override receipt required in proof boundary' });
    Object.assign(state, { current_state: 'override-recorded' });
  } else {
    requireField('run_id');
    const receiptPath = artifact(`closeout/${transition}.json`);
    artifactPaths.push(receiptPath);
    writes.set(receiptPath, { kind: 'agentic-workspace/assignment-closeout-receipt/v1', run_id: runId, status: transition });
    const closeoutState = {
      cleanup: 'archived',
      close: 'closed',
      reassign: 'superseded',
      reject: 'blocked',
      repair: 'blocked',
    }[transition] ?? transition;
    Object.assign(state, { current_state: closeoutState });
  }
  const refs = artifactPaths.map((path) => relative(targetRoot, path).replaceAll('\\\\', '/'));
  state.schema_version = 'agentic-workspace/assignment-run-state/v1';
  state.run_id = runId;
  state.locality = 'local-disposable';
  if (!failures.length && !Boolean(values.dry_run)) {
    for (const [path, payload] of writes.entries()) assignmentWrite(path, payload);
    assignmentWrite(statePath, state);
    refs.push(relative(targetRoot, statePath).replaceAll('\\\\', '/'));
  }
  return { kind: 'agentic-workspace/assignment-lifecycle-result/v1', operation_id: operationId, transition, status: failures.length ? 'blocked' : state.current_state, outcome: failures.length ? 'blocked' : Boolean(values.dry_run) ? 'noop' : 'applied', mutation_applied: !failures.length && !Boolean(values.dry_run), target_root: targetRoot, run_id: runId, artifact_refs: refs, state, failures, reason_code: failures[0]?.reason ?? null, recovery_command: failures[0]?.recovery ?? null, message: `assignment ${transition}: ${failures.length ? 'blocked' : state.current_state}`, actions: refs.map((path) => ({ kind: 'write', path })) };
}

function correctionIdentityInit(values, targetRoot, operationId) {
  const configRef = '.agentic-workspace/config.local.toml';
  const configPath = resolveInside(targetRoot, configRef);
  const before = existsSync(configPath) ? readText(configPath) : 'schema_version = 1\n';
  const beforeDigest = `sha256:${createHash('sha256').update(before).digest('hex')}`;
  const targets = parseTomlTables(before, 'delegation_targets');
  const delegation = parseTomlTables(before, 'delegation');
  const profileName = String(values.target_profile ?? delegation.current_target ?? '').trim();
  const matches = Object.entries(targets).filter(([name, profile]) => {
    if (!isObject(profile)) return false;
    return name === profileName || (Array.isArray(profile.aliases) && profile.aliases.includes(profileName));
  });
  const known = matches.filter(([, profile]) => String(profile.target_id ?? '').trim());
  if (known.length === 1) {
    return {
      kind: 'agentic-workspace/target-identity-initialization/v1',
      operation_id: operationId,
      status: 'already-initialized',
      mutation_applied: false,
      target_profile: profileName,
      target_id: String(known[0][1].target_id),
      reason: 'idempotent-replay',
      checked_in_repo_effect: 'none',
    };
  }
  if (matches.length !== 1) {
    return {
      kind: 'agentic-workspace/target-identity-initialization/v1',
      operation_id: operationId,
      status: 'blocked',
      mutation_applied: false,
      repair: {
        status: 'unavailable',
        reason: 'target-profile-not-uniquely-resolvable',
        operation: 'correction-event identity-init',
      },
    };
  }
  const [resolvedName, profile] = matches[0];
  const slug = resolvedName.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'target';
  const seed = stableJson({
    model_family: profile.model_family ?? null,
    profile_name: resolvedName,
    provider: profile.provider ?? null,
    role_identity: resolvedName,
  });
  const proposedId = `user-local:${slug}-${createHash('sha256').update(seed).digest('hex').slice(0, 10)}`;
  const targetId = String(values.target_id ?? proposedId).trim();
  const owner = Object.entries(targets).find(([name, candidate]) => name !== resolvedName && isObject(candidate) && candidate.target_id === targetId);
  if (owner) {
    return {
      kind: 'agentic-workspace/target-identity-initialization/v1',
      operation_id: operationId,
      status: 'blocked',
      mutation_applied: false,
      reason: 'target-id-already-owned-by-another-profile',
      target_id: targetId,
    };
  }
  const expectedDigest = String(values.expected_config_digest ?? '').trim();
  if (expectedDigest && expectedDigest !== beforeDigest) {
    return {
      kind: 'agentic-workspace/target-identity-initialization/v1',
      operation_id: operationId,
      status: 'blocked',
      mutation_applied: false,
      reason: 'local-config-revision-mismatch',
      expected_config_digest: expectedDigest,
      current_config_digest: beforeDigest,
      recovery: 'Rerun identity-init --dry-run and apply the refreshed operation.',
    };
  }
  const header = `[delegation_targets.${resolvedName}]`;
  const lines = before.split(/\r?\n/);
  const tableIndex = lines.findIndex((line) => line.trim() === header);
  if (tableIndex < 0) {
    return {
      kind: 'agentic-workspace/target-identity-initialization/v1',
      operation_id: operationId,
      status: 'blocked',
      mutation_applied: false,
      reason: 'target-profile-config-table-not-found',
    };
  }
  lines.splice(tableIndex + 1, 0, `target_id = "${targetId.replaceAll('"', '\\"')}"`);
  const after = `${lines.join('\n').trimEnd()}\n`;
  const afterDigest = `sha256:${createHash('sha256').update(after).digest('hex')}`;
  if (!Boolean(values.dry_run)) {
    mkdirSync(dirname(configPath), { recursive: true });
    writeFileSync(configPath, after, 'utf8');
  }
  return {
    kind: 'agentic-workspace/target-identity-initialization/v1',
    operation_id: operationId,
    status: Boolean(values.dry_run) ? 'planned' : 'initialized',
    mutation_applied: !Boolean(values.dry_run),
    target_profile: resolvedName,
    target_id: targetId,
    config_path: configRef,
    checked_in_repo_effect: 'none',
    config_digest_before: beforeDigest,
    config_digest_after: afterDigest,
    recheck_command: 'agentic-workspace config --target . --select mixed_agent.target_identity --format json',
    continuity_rule: 'The persisted stable target id survives profile rename; aliases remain migration hints only.',
  };
}

function correctionEventApply(values, operationId) {
  const targetRoot = resolve(String(values.target_root ?? values.target ?? '.'));
  const scriptPath = resolve(process.cwd(), 'scripts/run_agentic_workspace.py');
  const blocked = (reason, recovery) => ({
    kind: 'agentic-workspace/correction-event-operation-result/v1',
    operation_id: operationId,
    status: 'blocked',
    mutation_applied: false,
    store_ref: '.agentic-workspace/local/correction-events.json',
    admission: {
      kind: 'agentic-workspace/correction-event-admission/v1',
      status: 'blocked',
      admitted_events: [],
      low_authority_events: [],
      rejected_events: [{ reason, recovery }],
    },
    checked_in_repo_effect: 'none',
    rule: 'TypeScript correction-event operations delegate to the Python AW authority boundary; reduced TypeScript admission is fail-closed.',
  });
  const operation = String(operationId).replace(/^correction-event\./, '');
  if (!existsSync(scriptPath) && (values.trusted_host_event_json || values.host_event_ref)) {
    return blocked(
      'trusted-host-custody-unavailable',
      'Invoke the AW Python/CLI authority boundary; native TypeScript fallback cannot verify or preserve signed host observations.',
    );
  }
  if (!existsSync(scriptPath)) {
    if (operation === 'identity-init') return correctionIdentityInit(values, targetRoot, operationId);
    const status = operation === 'query' ? 'queried' : operation === 'prune-compact' ? 'compacted' : 'stored';
    const storeRef = '.agentic-workspace/local/correction-events.json';
    const storePath = resolveInside(targetRoot, storeRef);
    if (!Boolean(values.dry_run) && status === 'stored') {
      const existing = existsSync(storePath) ? readJson(storePath) : { kind: 'agentic-workspace/correction-event-store/v1', events: [] };
      existing.events = Array.isArray(existing.events) ? existing.events : [];
      existing.events.push({ operation, delivery_id: values.delivery_id ?? '', source_ref: values.source_ref ?? '', target_identity_ref: values.target_identity_ref ?? '', target_revision: values.target_revision ?? '' });
      mkdirSync(dirname(storePath), { recursive: true });
      writeFileSync(storePath, `${JSON.stringify(existing, null, 2)}\n`, 'utf8');
    }
    return {
      kind: 'agentic-workspace/correction-event-operation-result/v1',
      operation_id: operationId,
      status,
      mutation_applied: !Boolean(values.dry_run) && status === 'stored',
      store_ref: storeRef,
      admission: { kind: 'agentic-workspace/correction-event-admission/v1', status, admitted_events: [], low_authority_events: [], rejected_events: [] },
      checked_in_repo_effect: 'none',
      rule: 'Native TypeScript correction-event operations retain local-only evidence and never create checked-in authority.',
    };
  }
  const args = ['run', 'python', scriptPath, 'correction-event', operation, '--target', targetRoot, '--format', 'json'];
  for (const [key, value] of Object.entries(values)) {
    if (
      ['target', 'target_root', 'format', 'operation_id', 'correction_event_command'].includes(key)
      || key.endsWith('_command')
      || value === undefined
      || value === null
      || value === ''
      || value === false
      || Array.isArray(value)
    ) continue;
    args.push(`--${key.replaceAll('_', '-')}`, String(value));
  }
  const completed = spawnSync('uv', args, { cwd: dirname(dirname(scriptPath)), encoding: 'utf8', maxBuffer: 10 * 1024 * 1024 });
  const text = completed.stdout || completed.stderr || '';
  try {
    const payload = JSON.parse(text);
    return completed.status === 0
      ? payload
      : blocked('authoritative-python-boundary-failed', JSON.stringify(payload).slice(0, 500));
  } catch {
    return blocked('authoritative-python-boundary-non-json', text.slice(0, 500) || 'Install uv/python and retry through AW.');
  }
}

function guidanceLifecycleApply(values, operationId) {
  const targetRoot = resolve(String(values.target_root ?? values.target ?? '.'));
  const scriptPath = resolve(process.cwd(), 'scripts/run_agentic_workspace.py');
  const blocked = (reason, recovery) => ({
    kind: 'agentic-workspace/guidance-lifecycle-result/v1',
    operation_id: operationId,
    status: 'blocked',
    mutation_applied: false,
    failures: [{ reason, field: 'agent-guidance', recovery }],
    rule: 'TypeScript agent-guidance lifecycle operations delegate to the Python AW authority boundary; reduced TypeScript mutation admission is fail-closed.',
  });
  const operation = String(operationId).replace(/^agent-guidance\./, '');
  if (!existsSync(scriptPath)) {
    return {
      kind: 'agentic-workspace/guidance-lifecycle-result/v1',
      operation_id: operationId,
      status: operation === 'promote' ? 'promotion-not-authorized' : 'missing-guidance',
      mutation_applied: false,
      failures: [],
      rule: 'A packaged TypeScript adapter can reject absent or unauthorized guidance locally; authoritative guidance mutation requires an admitted guidance record.',
    };
  }
  const args = ['run', 'python', scriptPath, 'agent-guidance', operation, '--target', targetRoot, '--format', 'json'];
  for (const [key, value] of Object.entries(values)) {
    if (
      ['target', 'target_root', 'format', 'operation_id', 'agent_guidance_command'].includes(key)
      || key.endsWith('_command')
      || value === undefined
      || value === null
      || value === ''
      || value === false
      || Array.isArray(value)
    ) continue;
    args.push(`--${key.replaceAll('_', '-')}`, String(value));
  }
  for (const key of ['merge_guidance_ids', 'split_instructions']) {
    const value = values[key];
    if (Array.isArray(value)) {
      for (const item of value) args.push(`--${key.replaceAll('_', '-')}`, String(item));
    }
  }
  const completed = spawnSync('uv', args, { cwd: targetRoot, encoding: 'utf8', maxBuffer: 10 * 1024 * 1024 });
  const text = completed.stdout || completed.stderr || '';
  try {
    const payload = JSON.parse(text);
    return completed.status === 0
      ? payload
      : blocked('authoritative-python-boundary-failed', JSON.stringify(payload).slice(0, 500));
  } catch {
    return blocked('authoritative-python-boundary-non-json', text.slice(0, 500) || 'Install uv/python and retry through AW.');
  }
}

function instructionsExecute(values, operationId) {
  const targetRoot = resolve(String(values.target_root ?? values.target ?? '.'));
  const blocked = (reason, recovery) => ({
    kind: 'agentic-workspace/scoped-instruction-error/v1',
    operation_id: operationId,
    status: 'failed',
    message: recovery,
    exit_status: 2,
    reason,
  });
  try {
    if (operationId === 'instructions.create') return createInstructionNative(targetRoot, values, operationId);
    if (operationId === 'instructions.migrate') return migrateInstructionNative(targetRoot, values, operationId);
    const payload = inspectInstructionsNative(targetRoot, values, operationId);
    if (operationId === 'instructions.check' && payload.status === 'invalid') payload.exit_status = 2;
    return payload;
  } catch (error) {
    return blocked('instruction-operation-rejected', error instanceof Error ? error.message : String(error));
  }
}

function validInstructionPattern(value) {
  const text = String(value ?? '').trim();
  return Boolean(text) && !text.includes('\\') && !text.startsWith('/') && !text.startsWith('~')
    && !/^[A-Za-z]:/.test(text) && !text.split('/').includes('..');
}

function instructionPatternMatches(path, pattern) {
  const sentinel = '\u0000';
  const escaped = String(pattern).replace(/[.+^${}()|[\]\\]/g, '\\$&').replaceAll('**', sentinel)
    .replaceAll('*', '[^/]*').replaceAll('?', '[^/]').replaceAll(sentinel, '.*');
  return new RegExp(`^${escaped}$`).test(path);
}

function parseInstructionNative(path, targetRoot, loadBody) {
  const fields = new Set(['paths', 'read', 'use', 'checks', 'protect']);
  const metadata = { paths: [], read: [], use: [], checks: [], protect: [] };
  const diagnostics = [];
  const text = readText(path);
  const lines = text.split(/\r?\n/);
  let bodyStart = 0;
  if (lines[0] === '---') {
    let current = '';
    let closed = false;
    for (let index = 1; index < lines.length; index += 1) {
      const line = lines[index];
      if (line === '---') { bodyStart = index + 1; closed = true; break; }
      if (!line.trim() || line.trimStart().startsWith('#')) continue;
      if (!line.startsWith(' ') && line.includes(':')) {
        const separator = line.indexOf(':');
        current = line.slice(0, separator).trim();
        const inline = line.slice(separator + 1).trim();
        if (!fields.has(current)) diagnostics.push({ field: current, code: 'unknown-field', message: 'use only paths, read, use, checks, protect' });
        else if (inline.startsWith('[') && inline.endsWith(']')) metadata[current].push(...inline.slice(1, -1).split(',').map((item) => item.trim().replace(/^['"]|['"]$/g, '')).filter(Boolean));
        else if (inline) diagnostics.push({ field: current, code: 'invalid-shape', message: 'use a YAML list or a short inline list' });
        continue;
      }
      const item = line.trim();
      if (item.startsWith('-') && fields.has(current)) {
        const value = item.slice(1).trim();
        metadata[current].push(current === 'checks' && value.startsWith('run:') ? { run: value.slice(4).trim() } : value.replace(/^['"]|['"]$/g, ''));
      } else diagnostics.push({ field: current || 'frontmatter', code: 'invalid-syntax', message: `cannot parse \`${item}\`` });
    }
    if (!closed) diagnostics.push({ field: 'frontmatter', code: 'unterminated', message: 'add the closing --- line' });
  }
  for (const field of ['paths', 'read', 'protect']) metadata[field].forEach((value, index) => {
    if (typeof value !== 'string' || !validInstructionPattern(value)) diagnostics.push({ field: `${field}[${index}]`, code: 'invalid-repo-pattern', message: 'use a non-empty repo-relative path or glob without `..`, a drive, or a leading slash' });
  });
  const body = lines.slice(bodyStart).join('\n').trim();
  return {
    id: path.split(/[\\/]/).at(-1).replace(/\.md$/, ''), source_ref: relative(targetRoot, path).replaceAll('\\', '/'),
    revision: `sha256:${createHash('sha256').update(text).digest('hex')}`, metadata, diagnostics,
    guidance: loadBody ? body : '', has_guidance: Boolean(body), body_loaded: loadBody,
  };
}

function inspectInstructionsNative(targetRoot, values, operationId) {
  const directory = resolveInside(targetRoot, '.agentic-workspace/instructions');
  const paths = existsSync(directory) ? readdirSync(directory).filter((name) => name.endsWith('.md')).sort().map((name) => join(directory, name)) : [];
  const changed = Array.isArray(values.changed) ? values.changed.map((item) => String(item).replaceAll('\\', '/')) : [];
  const instructions = [];
  const diagnostics = [];
  for (const path of paths) {
    const shallow = parseInstructionNative(path, targetRoot, false);
    const patterns = shallow.metadata.paths.map(String);
    const matched = [...new Set(changed.filter((item) => patterns.some((pattern) => instructionPatternMatches(item, pattern))))].sort();
    const applies = patterns.length === 0 || matched.length > 0;
    const document = parseInstructionNative(path, targetRoot, applies);
    const itemDiagnostics = [...document.diagnostics];
    document.metadata.read.forEach((resource, index) => {
      if (!/[*?[\]]/.test(String(resource)) && !existsSync(resolveInside(targetRoot, String(resource)))) itemDiagnostics.push({ field: `read[${index}]`, code: 'missing-resource', message: `\`${resource}\` is not a readable repo-owned file` });
    });
    diagnostics.push(...itemDiagnostics.map((item) => ({ source_ref: document.source_ref, ...item })));
    instructions.push({
      id: document.id, source_ref: document.source_ref, revision: document.revision,
      scope: patterns.length ? patterns : ['global'], valid: itemDiagnostics.length === 0, applies,
      reason: patterns.length === 0 ? 'global instruction' : applies ? `${matched[0]} matches ${patterns.find((pattern) => instructionPatternMatches(matched[0], pattern))}` : `no changed or target path matches ${patterns.join(', ')}`,
      matched_paths: matched, body_loaded: document.body_loaded,
      features: [['guidance', document.has_guidance], ['read', document.metadata.read.length], ['use', document.metadata.use.length], ['checks', document.metadata.checks.length], ['protect', document.metadata.protect.length]].filter(([, present]) => present).map(([name]) => name),
      guidance: document.guidance, read: applies ? document.metadata.read : [], use: applies ? document.metadata.use : [],
      checks: applies ? document.metadata.checks : [], protect: applies ? document.metadata.protect : [], diagnostics: itemDiagnostics,
    });
  }
  const payload = {
    kind: 'agentic-workspace/scoped-instruction-inspection/v1', operation_id: operationId,
    status: diagnostics.length ? 'invalid' : 'valid', instruction_count: instructions.length,
    applicable_count: instructions.filter((item) => item.applies).length, instructions, diagnostics,
    progressive_disclosure: { irrelevant_bodies_loaded: instructions.filter((item) => !item.applies && item.body_loaded).length, rule: 'Only matching or global instruction bodies enter the current operating contract.' },
    message: instructions.length ? instructions.map((item) => `${item.id} ${item.valid ? 'valid' : 'invalid'}`).join('\n') : 'No scoped repository instructions found.',
  };
  if (values.verbose) payload.instruction_program = { kind: 'agentic-workspace/instruction-program/v1', facts: [], clauses: [], capabilities: [], source_diagnostics: [] };
  return payload;
}

function createInstructionNative(targetRoot, values, operationId) {
  const name = String(values.name ?? '');
  const paths = Array.isArray(values.paths) ? values.paths.map(String) : [];
  if (!/^[a-z0-9][a-z0-9-]*$/.test(name)) throw new RuntimeError('instruction name must use lowercase letters, digits, and hyphens');
  for (const pattern of paths) if (!validInstructionPattern(pattern)) throw new RuntimeError(`invalid repo-relative path pattern: ${pattern}`);
  const sourceRef = `.agentic-workspace/instructions/${name}.md`;
  const destination = resolveInside(targetRoot, sourceRef);
  if (existsSync(destination)) throw new RuntimeError(`instruction already exists: ${sourceRef}`);
  mkdirSync(dirname(destination), { recursive: true });
  const title = name.split('-').map((part) => part[0].toUpperCase() + part.slice(1)).join(' ');
  const frontmatter = paths.length ? `---\npaths:\n${paths.map((pattern) => `  - ${pattern}\n`).join('')}---\n\n` : '';
  writeFileSync(destination, `${frontmatter}# ${title}\n\n<!-- Write the guidance an agent needs in this scope. -->\n`, 'utf8');
  return { kind: 'agentic-workspace/scoped-instruction-create-result/v1', operation_id: operationId, status: 'created', source_ref: sourceRef, scope: paths.length ? paths : ['global'], message: '', outcome: 'applied', mutation_applied: true, reason_code: 'instruction-created', conflict_owner: '', recovery_command: '' };
}

function migrateInstructionNative(targetRoot, values, operationId) {
  const sourcePath = resolveInside(targetRoot, String(values.source ?? ''));
  const candidateHeadings = readText(sourcePath).split(/\r?\n/).filter((line) => line.startsWith('## ')).map((line) => line.slice(3).trim());
  return { kind: 'agentic-workspace/scoped-instruction-migration-advice/v1', operation_id: operationId, status: 'review-required', source_ref: relative(targetRoot, sourcePath).replaceAll('\\', '/'), candidate_headings: candidateHeadings, writes_applied: false, message: '', steps: ['Choose one coherent guidance block and its intended scope.', 'Scaffold a scoped instruction and move the guidance with human or agent judgment.', 'Run instructions check and positive/negative instructions explain scenarios.', 'Remove the static block only after behavior is verified; retain a thin bootstrap.'] };
}

function reportMemory(values) {
  const targetRoot = resolve(String(values.target ?? '.'));
  const active = memoryManifestCounts(targetRoot, '.agentic-workspace/memory/repo/manifest.toml');
  return { kind: 'memory-module-report/v1', profile: 'tiny', module: 'memory', target_root: targetRoot, health: active.status === 'present' ? 'healthy' : 'attention-needed', status: { note_count: active.note_count, manifest_status: active.status }, active, next_action: { summary: active.status === 'present' ? 'No immediate memory action.' : 'Run full memory report for remediation detail.' }, detail_commands: { full: 'agentic-memory report --target . --verbose --format json', route: 'agentic-memory route --target . --files <paths> --format json' } };
}

const configPolicyFields = {
  shared: {
    'workspace.improvement_latitude': ['none', 'reporting', 'conservative', 'balanced', 'proactive'],
    'workspace.optimization_bias': ['agent-efficiency', 'balanced', 'human-legibility'],
    'assurance.default_level': ['low', 'medium', 'high', 'critical'],
    'assurance.strict_closeout': [true, false],
  },
  local: {
    'workspace.cli_invoke': null,
    'delegation.mode': ['off', 'manual', 'suggest', 'auto'],
    'delegation.execution_role': ['ordinary-executor', 'orchestrator', 'bounded-worker'],
    'delegation.assignment_policy': ['local-preferred', 'best-fit-advisory', 'required-best-fit'],
    'delegation.underfit_behavior': ['stay-when-safe', 'prepare-manual-escalation', 'require-delegation'],
    'delegation.down_routing_behavior': ['never', 'bounded-mechanical-work', 'when-cheaper-safe-target-exists'],
    'delegation.human_override_policy': ['explicit-only', 'allowed-with-recorded-reason', 'disallowed'],
    'delegation.manual_transport_policy': ['disabled', 'allowed', 'required'],
    'setup.prompt_disposition': ['active', 'deferred', 'optional-suppressed'],
    'setup.setup_identity': null,
    'setup.context_revision': null,
    'setup.unresolved_concerns': { type: 'string-list' },
    'setup.required_concerns': { type: 'string-list' },
  },
};

function configPolicyRevision(text) {
  return `sha256:${createHash('sha256').update(text).digest('hex')}`;
}

function replaceTomlScalar(source, field, value) {
  const [section, key] = field.split('.', 2);
  const rendered = typeof value === 'boolean' ? String(value) : JSON.stringify(value);
  const lines = source.split(/(?<=\n)/);
  let sectionIndex = -1;
  let nextSection = lines.length;
  const matches = [];
  for (let index = 0; index < lines.length; index += 1) {
    const stripped = lines[index].trim();
    if (stripped === `[${section}]`) {
      if (sectionIndex >= 0) throw new RuntimeError(`config policy apply found duplicate [${section}] tables`);
      sectionIndex = index;
      continue;
    }
    if (sectionIndex >= 0 && index > sectionIndex && /^\s*\[.*\]\s*$/.test(stripped)) { nextSection = index; break; }
    if (sectionIndex >= 0 && index > sectionIndex && new RegExp(`^\\s*${key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*=`).test(lines[index])) matches.push(index);
  }
  if (matches.length > 1) throw new RuntimeError(`config policy apply found duplicate ${field} assignments`);
  if (matches.length === 1) {
    const index = matches[0];
    const newline = lines[index].endsWith('\r\n') ? '\r\n' : lines[index].endsWith('\n') ? '\n' : '';
    const content = newline ? lines[index].slice(0, -newline.length) : lines[index];
    const equals = content.indexOf('=');
    const hash = content.indexOf('#', equals + 1);
    const suffix = hash >= 0 ? ` ${content.slice(hash).trimStart()}` : '';
    lines[index] = `${content.slice(0, equals + 1)} ${rendered}${suffix}${newline}`;
    return lines.join('');
  }
  if (sectionIndex < 0) return `${source}${source.endsWith('\n\n') || source === '' ? '' : source.endsWith('\n') ? '\n' : '\n\n'}[${section}]\n${key} = ${rendered}\n`;
  lines.splice(nextSection, 0, `${key} = ${rendered}\n`);
  return lines.join('');
}

function withoutTomlTable(source, table) {
  const lines = source.match(/[^\n]*(?:\n|$)/g)?.filter((line) => line !== '') ?? [];
  const kept = [];
  let removing = false;
  let found = false;
  for (const line of lines) {
    const content = line.endsWith('\n') ? line.slice(0, -1).replace(/\r$/, '') : line.replace(/\r$/, '');
    const heading = content.match(/^\s*\[([^\]]+)\]\s*(?:#.*)?$/);
    if (heading) {
      removing = heading[1].trim() === table;
      found = found || removing;
    }
    if (!removing) kept.push(line);
  }
  return found ? kept.join('') : source;
}

function applyWorkspaceConfigPolicy(values) {
  const targetRoot = resolve(String(values.target_root ?? values.target ?? '.'));
  let decision;
  try { decision = JSON.parse(String(values.decision_json ?? '')); } catch (error) { throw new RuntimeError(`config-policy --decision-json is invalid JSON: ${error.message}`); }
  if (!isObject(decision) || decision.kind !== 'agentic-workspace/config-policy-decision/v1') throw new RuntimeError('config-policy decision kind must be agentic-workspace/config-policy-decision/v1');
  const scope = String(decision.scope ?? '');
  const allowed = configPolicyFields[scope];
  if (!allowed) throw new RuntimeError('config-policy decision scope must be shared or local');
  if (!['strong-repo-evidence', 'human-answer'].includes(decision.authority)) throw new RuntimeError('config-policy decision authority must be strong-repo-evidence or human-answer');
  const expectedSetupIdentity = String(values.expect_setup_identity ?? '');
  if (!decision.setup_identity || decision.setup_identity !== expectedSetupIdentity) throw new RuntimeError('config-policy decision setup_identity must match --expect-setup-identity');
  const receiptPath = join(targetRoot, '.agentic-workspace/adoption-receipt.json');
  const observedSetupIdentity = existsSync(receiptPath) ? String(readJson(receiptPath)?.configuration_readiness?.identity ?? 'legacy-compatible') : 'legacy-compatible';
  const decisionSetupIdentity = isObject(decision.readiness_basis) ? createHash('sha256').update(stableJson(decision.readiness_basis)).digest('hex').slice(0, 24) : '';
  if (observedSetupIdentity !== expectedSetupIdentity && !(decision.complete_readiness === true && decisionSetupIdentity === expectedSetupIdentity)) throw new RuntimeError(`config-policy setup identity is stale: expected ${expectedSetupIdentity}, observed ${observedSetupIdentity}`);
  const changes = decision.changes ?? {};
  if (!isObject(changes) || (Object.keys(changes).length === 0 && decision.complete_readiness !== true && decision.clear_setup_disposition !== true)) throw new RuntimeError('config-policy decision requires changes, complete_readiness=true, or clear_setup_disposition=true');
  if (decision.complete_readiness !== undefined && typeof decision.complete_readiness !== 'boolean') throw new RuntimeError('config-policy complete_readiness must be a boolean');
  if (decision.clear_setup_disposition !== undefined && typeof decision.clear_setup_disposition !== 'boolean') throw new RuntimeError('config-policy clear_setup_disposition must be a boolean');
  if (decision.clear_setup_disposition === true && scope !== 'local') throw new RuntimeError('config-policy can clear setup disposition only through local scope');
  if (decision.complete_readiness === true && Object.keys(changes).length !== 0) throw new RuntimeError('config-policy readiness completion must be a separate no-change reconciliation decision');
  const relativePath = scope === 'shared' ? '.agentic-workspace/config.toml' : '.agentic-workspace/config.local.toml';
  const configPath = join(targetRoot, relativePath);
  const configExists = existsSync(configPath);
  const source = configExists ? readText(configPath) : 'schema_version = 1\n';
  const observedRevision = configPolicyRevision(configExists ? source : '');
  if (String(values.expect_config_revision ?? '') !== observedRevision) throw new RuntimeError(`config-policy revision is stale for ${relativePath}: expected ${values.expect_config_revision}, observed ${observedRevision}`);
  let rendered = source;
  const effects = [];
  for (const [field, value] of Object.entries(changes)) {
    if (!Object.prototype.hasOwnProperty.call(allowed, field)) throw new RuntimeError(`config-policy field ${JSON.stringify(field)} is not owned by the ${scope} policy operation`);
    const choices = allowed[field];
    const stringList = isObject(choices) && choices.type === 'string-list';
    if ((Array.isArray(choices) && !choices.includes(value)) || (stringList && (!Array.isArray(value) || value.some((item) => typeof item !== 'string' || item.length === 0) || new Set(value).size !== value.length)) || (!choices && typeof value !== 'string')) throw new RuntimeError(`config-policy value for ${field} is invalid`);
    if (/(password|secret|credential|private_key|access_token)/i.test(`${field} ${value}`)) throw new RuntimeError('config-policy refuses credential or secret material');
    if (scope === 'shared' && typeof value === 'string' && (isAbsolute(value) || /^[A-Za-z]:[\\/]/.test(value))) throw new RuntimeError('config-policy refuses absolute machine paths in shared configuration');
    rendered = replaceTomlScalar(rendered, field, value);
    effects.push({ owner: `config.${scope}`, field, value });
  }
  if (decision.clear_setup_disposition === true) {
    const cleared = withoutTomlTable(rendered, 'setup');
    if (cleared !== rendered) effects.push({ owner: 'config.local', field: 'setup', value: 'removed' });
    rendered = cleared;
  }
  let readinessReceipt = null;
  if (decision.complete_readiness === true) {
    if (!existsSync(receiptPath)) throw new RuntimeError('config-policy cannot complete readiness without a valid adoption receipt');
    readinessReceipt = readJson(receiptPath);
    const readiness = readinessReceipt?.configuration_readiness;
    if (!isObject(readiness) || readiness.kind !== 'agentic-workspace/configuration-readiness/v1') throw new RuntimeError('config-policy cannot complete missing or unsupported readiness metadata');
    if (!isObject(decision.readiness_basis) || !isObject(decision.concern_receipts)) throw new RuntimeError('config-policy readiness completion requires exact readiness_basis and concern_receipts from setup');
    const unresolvedSources = Object.values(decision.concern_receipts).filter((receipt) => isObject(receipt) && receipt.materiality !== 'recommended' && typeof receipt.source_obligation_status === 'string' && receipt.source_obligation_status.length > 0 && receipt.source_obligation_status !== 'satisfied');
    if (unresolvedSources.length > 0) throw new RuntimeError('config-policy readiness cannot be completed while required repo-source obligations remain unresolved');
    effects.push({ owner: 'setup.guidance', field: 'configuration_readiness.status', value: 'current' });
  }
  if (values.dry_run !== true && rendered !== source) { mkdirSync(dirname(configPath), { recursive: true }); writeFileSync(configPath, rendered, 'utf8'); }
  if (values.dry_run !== true && readinessReceipt) { readinessReceipt.configuration_readiness.status = 'current'; readinessReceipt.configuration_readiness.identity = expectedSetupIdentity; readinessReceipt.configuration_readiness.basis = decision.readiness_basis; readinessReceipt.configuration_readiness.concern_receipts = decision.concern_receipts; readinessReceipt.configuration_readiness.completed_by = 'config.policy-apply'; writeFileSync(receiptPath, `${JSON.stringify(readinessReceipt, null, 2)}\n`, 'utf8'); }
  const mutationApplied = values.dry_run !== true && (rendered !== source || Boolean(readinessReceipt));
  return { kind: 'agentic-workspace/config-policy-result/v1', status: values.dry_run === true ? 'preview' : rendered !== source ? 'applied' : 'current', scope, authority: decision.authority, concern_id: String(decision.concern_id ?? ''), setup_identity: decision.setup_identity, path: relativePath, previous_revision: observedRevision, revision: configPolicyRevision(rendered), effects, readiness_status: values.dry_run === true && readinessReceipt ? 'preview-current' : readinessReceipt ? 'current' : 'unchanged', outcome: mutationApplied ? 'applied' : 'noop', mutation_applied: mutationApplied, reason_code: values.dry_run === true ? 'dry-run' : mutationApplied ? 'authorised-policy-applied' : 'already-current', conflict_owner: '', recovery_command: 'agentic-workspace setup --target . --format json', re_resolve_command: 'agentic-workspace setup --target . --format json', claim_boundary: 'Only the explicitly authorised bounded policy fields were applied; other setup owners remain independent.' };
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
  if (primitive === 'config.policy.apply') return applyWorkspaceConfigPolicy(values);
  if (primitive === 'output.fields.select') return selectFields(values.config, values);
  return domainPrimitive(primitive, values, args, operationId);
}

function executeTypescriptDomainOperation(operationId, values) {
  const target = resolve(String(values.target ?? '.'));
  if (operationId === 'external-evidence.submit' || operationId === 'external-evidence.query') {
    return {
      kind: 'agentic-workspace/external-evidence-operation-error/v1',
      status: 'rejected',
      message: 'External evidence admission requires the package-trusted runtime-backed host boundary.',
      command: operationId === 'external-evidence.submit' ? 'external-evidence-submit' : 'external-evidence-query',
      exit_status: 2,
    };
  }
  if (operationId === 'final-response.admit') {
    const checkpointRef = '.agentic-workspace/local/chat-checkpoint.json';
    const checkpointPath = resolveInside(target, checkpointRef);
    const checkpoint = {
      kind: 'agentic-workspace/local-chat-checkpoint/v1',
      source: values.source ?? 'generated-typescript-final-response',
      after_compaction: Boolean(values.after_compaction),
      attempt: values.attempt ?? '',
      local_only: true,
    };
    mkdirSync(dirname(checkpointPath), { recursive: true });
    writeFileSync(checkpointPath, `${JSON.stringify(checkpoint, null, 2)}\n`, 'utf8');
    return {
      kind: 'agentic-workspace/final-response-admission-result/v1',
      status: 'recorded',
      checkpoint_write: { path: checkpointRef, local_only: true },
      target_root: target,
    };
  }
  if (operationId === 'autopilot.run') return {
    kind: 'agentic-workspace/final-response-admission-result/v1',
    status: 'blocked',
    exit_status: 2,
    target_root: target,
    reason: 'The packaged TypeScript adapter does not execute an arbitrary caller-supplied autopilot command without a host admission boundary.',
  };
  if (operationId === 'work-thread.prune') return {
    kind: 'agentic-workspace/local-work-thread-prune/v1',
    status: values.dry_run === false ? 'pruned' : 'dry-run',
    path: '.agentic-workspace/local/work-threads',
    thread_id: values.thread_id ?? '',
  };
  if (operationId === 'work-thread.select') {
    const indexRef = '.agentic-workspace/local/work-threads/index.json';
    const indexPath = resolveInside(target, indexRef);
    const payload = { kind: 'agentic-workspace/local-work-thread-selection/v1', selected_thread_id: values.thread_id ?? '' };
    mkdirSync(dirname(indexPath), { recursive: true });
    writeFileSync(indexPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
    return { kind: 'agentic-workspace/local-work-thread-select/v1', status: 'selected', path: indexRef, thread_id: values.thread_id ?? '' };
  }
  if (operationId === 'work-thread.carry-inspect') {
    const carryRoot = resolveInside(target, '.agentic-workspace/local/decision-point-intent');
    const carries = existsSync(carryRoot)
      ? readdirSync(carryRoot).filter((name) => name.endsWith('.json') && name !== 'selection.json').map((name) => readJson(resolveInside(carryRoot, name)))
      : [];
    return { kind: 'agentic-workspace/decision-point-carry-inspect/v1', active_count: carries.filter((item) => item.status === 'active').length, carries };
  }
  if (operationId === 'work-thread.carry-select') {
    const carryRef = `.agentic-workspace/local/decision-point-intent/${String(values.key ?? '')}.json`;
    const carry = readJson(resolveInside(target, carryRef));
    const selectionRef = '.agentic-workspace/local/decision-point-intent/selection.json';
    const contextId = carry.work_binding?.context_id ?? '';
    const payload = { kind: 'agentic-workspace/decision-point-carry-selection/v1', selected_key: values.key ?? '', context_id: contextId, owner_id: carry.work_binding?.owner_binding?.owner_id ?? '' };
    const selectionPath = resolveInside(target, selectionRef);
    mkdirSync(dirname(selectionPath), { recursive: true });
    writeFileSync(selectionPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
    return { kind: 'agentic-workspace/decision-point-carry-select/v1', selected_key: values.key ?? '', context_id: contextId, path: selectionRef };
  }
  if (operationId === 'work-thread.carry-prune') return {
    kind: 'agentic-workspace/decision-point-carry-prune/v1',
    status: values.dry_run === false ? 'pruned' : 'dry-run',
    key: values.key ?? '',
  };
  if (operationId === 'session-log.manage') return {
    kind: 'agentic-workspace/session-logging-status/v1',
    enabled: false,
    local_only: true,
    target_root: target,
  };
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
  if (operationId === 'summary.report') {
    const prevalidationError = workspaceSelectorPrevalidationError(values.select, 'summary');
    if (prevalidationError) return prevalidationError;
    const payload = { kind: 'planning-summary/v1', profile: values.verbose ? 'full' : 'tiny', machine_first_planning: { status: 'no-active-execplan' }, target_root: target };
    return selectWorkspacePayload(payload, values, 'summary');
  }
  if (operationId === 'start.context') return { kind: 'startup-context/v1', target_root: target, drill_down: { rule: 'Compact default omits selector inventory/schemas; use --select or --verbose for detail.' }, context: { proof: { kind: 'proof-selection/v1' } } };
  if (operationId === 'implement.context') return { kind: 'implementer-context-tiny/v1', target_root: target, proof: { kind: 'proof-selection/v1' } };
  if (operationId === 'proof.report') {
    const prevalidationError = workspaceSelectorPrevalidationError(values.select, 'proof');
    if (prevalidationError) return prevalidationError;
    return { kind: 'proof-next-decision/v1', next: { action: 'manual-verification' }, detail_command: 'agentic-workspace proof --verbose --changed <paths> --format json' };
  }
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
